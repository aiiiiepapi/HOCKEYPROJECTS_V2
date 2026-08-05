#!/usr/bin/env python3
"""KHL raw-lake fetcher — fetch-only, stdlib-only, resume-safe.

Runs on Seb's PC (cloud session cannot reach khl.ru). Per season:
  1. Fetch the calendar page (schedule authority) for the season's
     regular-season tournament id.
  2. Extract the game-id set SCOPED to that tournament id (the page embeds
     slider/widget links to OTHER tournaments — the tid filter is the scope).
  3. Assert the scoped count and contiguity against the verified expectation
     (probe round 1, docs/KHL_SOURCE.md) — refuses to fetch on mismatch.
  4. Fetch per game, verbatim bytes: text broadcast + protocol page.
  5. Append to a per-season manifest (file,url,http_code,bytes,sha256,utc,flag).

Resume-safe: files already on disk with a matching manifest row are skipped.
Artifact-set decision (probe round 2): text + protocol only. resume/ and the
en.khl.ru mirror carry no additional capability content (docs/KHL_SOURCE.md).

Usage (PowerShell, from anywhere):
  python tools/fetch_khl.py --season 2026 --out C:\\dev\\khl_lake
  python tools/fetch_khl.py --season all  --out C:\\dev\\khl_lake
Optional: --limit N (smoke run), --delay 0.7
"""
import argparse
import csv
import hashlib
import http.cookiejar
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Season -> (regular-season tournament id, expected game count), verified
# against fetched calendars 2026-08-05 (scoped counts exact, ids contiguous).
SEASONS = {
    2023: (1154, 748),
    2024: (1217, 782),
    2025: (1288, 782),
    2026: (1369, 748),
}

CAL_URL = 'https://www.khl.ru/calendar/{tid}/00/'
TEXT_URL = 'https://text.khl.ru/text/{gid}.html'
PROTO_URL = 'https://www.khl.ru/game/{tid}/{gid}/protocol/'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru,en;q=0.8',
}
MANIFEST_FIELDS = ['file', 'url', 'http_code', 'bytes', 'sha256', 'utc', 'flag']

# khl.ru fronts a bot-protection layer that answers a cookie-less client
# with 307 + Set-Cookie (observed on the 2026-08-05 smoke run; PowerShell's
# Invoke-WebRequest passed because it keeps cookies across the redirect
# chain). A shared CookieJar makes urllib do the same.
_JAR = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_JAR))


def utcnow():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fetch(url, delay, retries=3):
    """GET url, return (code, bytes). Retries with backoff on network errors
    AND on 3xx-final responses (cookie-challenge second pass usually clears)."""
    last = None
    for attempt in range(retries):
        time.sleep(delay if attempt == 0 else delay + 2 ** attempt)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with _OPENER.open(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            body = e.read() if e.fp else b''
            loc = e.headers.get('Location', '') if e.headers else ''
            last = (e.code, body)
            if 300 <= e.code < 400:
                # challenge redirect: cookies from this response are now in
                # the jar; loop to retry with them. Report Location once.
                if attempt == 0:
                    print(f'    note: {e.code} redirect at {url} '
                          f'(Location: {loc[:120]}) — retrying with cookies')
                continue
            return e.code, body
        except Exception as e:  # URLError, timeout, ConnectionReset...
            last = (f'ERR:{e}', b'')
    return last if last else ('ERR:unknown', b'')


def flag_for(body, code):
    """Heuristic truncation/soft-404 flag — recorded, never blocks the save."""
    if code != 200:
        return 'http_%s' % code
    if len(body) < 50_000:
        return 'small'
    if b'</html>' not in body[-2000:]:
        return 'no_close_tag'
    return ''


def load_manifest(path):
    done = {}
    if os.path.exists(path):
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                done[row['file']] = row
    return done


def append_manifest(path, row):
    new = not os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def save(out_dir, manifest_path, name, url, delay, done):
    """Fetch url -> out_dir/name unless already done. Returns (ok, flag)."""
    fpath = os.path.join(out_dir, name)
    if name in done and os.path.exists(fpath):
        row = done[name]
        if str(os.path.getsize(fpath)) == row['bytes']:
            return True, 'resume_skip'
    code, body = fetch(url, delay)
    if body:
        with open(fpath, 'wb') as f:
            f.write(body)
    flag = flag_for(body, code)
    append_manifest(manifest_path, {
        'file': name, 'url': url, 'http_code': code, 'bytes': len(body),
        'sha256': hashlib.sha256(body).hexdigest(), 'utc': utcnow(), 'flag': flag,
    })
    ok = code == 200 and body
    return bool(ok), flag


def run_season(year, out_root, delay, limit):
    tid, expected = SEASONS[year]
    out_dir = os.path.join(out_root, 'khl', str(year))
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, 'manifest.csv')
    done = load_manifest(manifest_path)
    print(f'== season {year} (tid {tid}, expect {expected} games) -> {out_dir}')

    # 1-2. schedule authority + scoped id set
    cal_name = f'calendar_{tid}.html'
    cal_path = os.path.join(out_dir, cal_name)
    if cal_name in done and os.path.exists(cal_path):
        raw = open(cal_path, 'rb').read()
        print('  calendar: resume_skip')
    else:
        code, raw = fetch(CAL_URL.format(tid=tid), delay)
        if code != 200 or not raw:
            print(f'  FATAL: calendar fetch failed ({code})'); return False
        with open(cal_path, 'wb') as f:
            f.write(raw)
        append_manifest(manifest_path, {
            'file': cal_name, 'url': CAL_URL.format(tid=tid), 'http_code': code,
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'utc': utcnow(), 'flag': ''})
    html = raw.decode('utf-8', errors='replace')
    gids = sorted({int(g) for g in
                   re.findall(r'/game/%d/(\d+)/protocol/' % tid, html)})

    # 3. structural gate BEFORE fetching (rule 14: per-season, never absolute)
    if len(gids) != expected:
        print(f'  FATAL: scoped id count {len(gids)} != expected {expected}. '
              'Investigate before fetching (rule 10).'); return False
    if gids[-1] - gids[0] + 1 != len(gids):
        print(f'  WARNING: id block not contiguous ({gids[0]}..{gids[-1]}, '
              f'{len(gids)} ids) — was contiguous at probe time. Continuing; '
              'reconciliation is vs the id SET, not the range.')

    if limit:
        gids = gids[:limit]
        print(f'  --limit {limit}: fetching first {limit} games only')

    # 4. per-game artifacts
    fails = []
    t0 = time.time()
    for n, gid in enumerate(gids, 1):
        ok1, f1 = save(out_dir, manifest_path, f'{gid}_text.html',
                       TEXT_URL.format(gid=gid), delay, done)
        ok2, f2 = save(out_dir, manifest_path, f'{gid}_protocol.html',
                       PROTO_URL.format(tid=tid, gid=gid), delay, done)
        if not (ok1 and ok2):
            fails.append((gid, f1, f2))
        if n % 25 == 0 or n == len(gids):
            el = time.time() - t0
            print(f'  {n}/{len(gids)} games  ({el/60:.1f} min, '
                  f'{len(fails)} fails)', flush=True)
    print(f'  season {year} done: {len(gids)} games, {len(fails)} fails')
    for gid, f1, f2 in fails[:20]:
        print(f'    FAIL gid {gid}: text={f1} proto={f2}')
    return not fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', required=True,
                    help='2023|2024|2025|2026|all (end-year convention)')
    ap.add_argument('--out', default=r'C:\dev\khl_lake',
                    help='lake root (khl/<year>/ created underneath)')
    ap.add_argument('--delay', type=float, default=0.7)
    ap.add_argument('--limit', type=int, default=0,
                    help='fetch only first N games (smoke run)')
    args = ap.parse_args()
    years = sorted(SEASONS) if args.season == 'all' else [int(args.season)]
    ok = True
    for y in years:
        ok = run_season(y, args.out, args.delay, args.limit) and ok
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
