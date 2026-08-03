"""
fetch_mestis.py — Mestis raw data lake builder (v2, fetch-only)
===============================================================
Downloads and caches RAW mestis.fi HTML pages + season ICS schedules.
No processing, no parsing beyond what is needed to enumerate games.

Source (verified 2026-08-03, docs/MESTIS_SOURCE.md):
  Schedule authority: https://mestis.fi/ottelut/{S}/runkosarja/kalenterit
    (ICS; one VEVENT per game; DESCRIPTION carries the match URL with the
    per-season MATCHNO; UID carries the internal game id)
  Per game, 3 pages saved VERBATIM (raw response bytes, never edited):
    https://mestis.fi/fi/ottelut/{S}/runkosarja/{N}/kokoonpanot/
    https://mestis.fi/fi/ottelut/{S}/runkosarja/{N}/seuranta/
    https://mestis.fi/fi/ottelut/{S}/runkosarja/{N}/tilastot/
  {S} = "2024-2025" style season string; {N} = match number (unique only
  within season+series — files are always keyed (season, N)).

Saves: <out>/<END_YEAR>/game_<END_YEAR>_<N>_<page>.html
       <out>/<END_YEAR>/schedule_<END_YEAR>.ics
       <out>/<END_YEAR>/schedule_page_<END_YEAR>.html
       <out>/<END_YEAR>/manifest_<END_YEAR>.json   (sha256/bytes/url/utc)
Seasons: END year (2023 = 2022-23). Default 2023..2026, runkosarja only.
Resumable (existing valid files skipped); stdlib-only; run on Seb's PC.
The cloud workspace CANNOT run this (proxy 403 on mestis.fi, verified).

Usage:
  python fetch_mestis.py
  python fetch_mestis.py --seasons 2025 2026
"""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://mestis.fi"
PAGES = ("kokoonpanot", "seuranta", "tilastot")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Accept": "text/html,application/xhtml+xml,*/*"}
THROTTLE = 0.5           # seconds between requests — be polite, small league
MIN_HTML_BYTES = 5000    # a real game page is far bigger than any stub


def season_str(end_year):
    return f"{end_year - 1}-{end_year}"


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url, retries=3, delay=2.0, verbose=False):
    """Return raw response BYTES, 'MISS' on 404/400, or None on failure."""
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=30) as resp:
                data = resp.read()
                if verbose:
                    print(f"  OK {len(data):>8} B  {url}", flush=True)
                return data
        except HTTPError as e:
            if e.code in (404, 400, 410):
                print(f"  {e.code} (no such page) {url}", flush=True)
                return "MISS"
            print(f"  HTTP {e.code} on {url} (attempt {attempt+1})", flush=True)
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        except (URLError, TimeoutError, ValueError, OSError) as e:
            print(f"  {type(e).__name__}: {e} on {url} (attempt {attempt+1})",
                  flush=True)
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    return None


def unfold_ics(text):
    """RFC5545 unfolding: a CRLF (or LF) followed by SPACE/TAB is removed."""
    return re.sub(r"\r?\n[ \t]", "", text)


def parse_ics_games(ics_text):
    """Yield dicts: matchno, uid, summary, dtstart — one per VEVENT."""
    games = []
    for block in unfold_ics(ics_text).split("BEGIN:VEVENT")[1:]:
        block = block.split("END:VEVENT")[0]
        uid = re.search(r"^UID:(.+)$", block, re.M)
        summ = re.search(r"^SUMMARY:(.+)$", block, re.M)
        dtst = re.search(r"^DTSTART[^:]*:(.+)$", block, re.M)
        mno = re.search(r"runkosarja/(\d+)/", block)
        games.append({
            "matchno": int(mno.group(1)) if mno else None,
            "uid": uid.group(1).strip() if uid else None,
            "summary": summ.group(1).strip() if summ else None,
            "dtstart": dtst.group(1).strip() if dtst else None,
        })
    return games


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_bytes(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    tmp.replace(path)


class Manifest:
    def __init__(self, path):
        self.path = path
        self.data = {"files": {}, "missing": {}, "generated": None}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                print(f"  WARN: unreadable manifest {path}, starting fresh")
        self.data.setdefault("files", {})
        self.data.setdefault("missing", {})

    def record(self, fname, url, fpath):
        self.data["files"][fname] = {
            "sha256": sha256_file(fpath),
            "bytes": fpath.stat().st_size,
            "url": url,
            "fetched_utc": now_utc(),
        }

    def record_missing(self, key, url, reason):
        self.data["missing"][key] = {"url": url, "reason": reason,
                                     "at_utc": now_utc()}

    def save(self):
        self.data["generated"] = now_utc()
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(self.path)


def valid_html_file(path):
    if not path.exists() or path.stat().st_size < MIN_HTML_BYTES:
        return False
    with open(path, "rb") as f:
        f.seek(max(0, path.stat().st_size - 2048))
        return b"</html>" in f.read().lower()


def fetch_season(year, out_root):
    s = season_str(year)
    out_dir = Path(out_root) / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    man = Manifest(out_dir / f"manifest_{year}.json")
    errors_early = 0

    # 1) ICS schedule (authority) — always refetch (cheap, self-dating)
    ics_url = f"{BASE}/ottelut/{s}/runkosarja/kalenterit"
    ics = http_get(ics_url, verbose=True)
    if ics in (None, "MISS") or b"BEGIN:VCALENDAR" not in ics:
        print(f"[{year}] FATAL: schedule ICS not fetchable/parseable "
              f"({ics_url}) — paste this output to the manager.")
        return False
    ics_path = out_dir / f"schedule_{year}.ics"
    atomic_write_bytes(ics_path, ics)
    man.record(ics_path.name, ics_url, ics_path)
    games = parse_ics_games(ics.decode("utf-8", "replace"))
    n_no_matchno = sum(1 for g in games if g["matchno"] is None)
    matchnos = sorted({g["matchno"] for g in games if g["matchno"]})
    print(f"[{year}] ICS: {len(games)} events, {len(matchnos)} distinct "
          f"match numbers, {n_no_matchno} events without a match URL",
          flush=True)
    if not matchnos:
        print(f"[{year}] FATAL: 0 match numbers parsed from a non-empty ICS "
              f"(rule 8) — ICS format changed? First 500 chars:\n"
              f"{ics[:500].decode('utf-8', 'replace')}")
        return False
    time.sleep(THROTTLE)

    # 2) season list page (secondary reconciliation source)
    page_url = f"{BASE}/fi/ottelut/{s}/runkosarja/"
    page = http_get(page_url, verbose=True)
    if isinstance(page, bytes):
        p = out_dir / f"schedule_page_{year}.html"
        atomic_write_bytes(p, page)
        man.record(p.name, page_url, p)
    man.save()
    time.sleep(THROTTLE)

    # 3) per-game pages
    saved = skipped = failed = 0
    for i, n in enumerate(matchnos, 1):
        for pg in PAGES:
            fname = f"game_{year}_{n}_{pg}.html"
            fpath = out_dir / fname
            if valid_html_file(fpath) and fname in man.data["files"]:
                skipped += 1
                continue
            url = f"{BASE}/fi/ottelut/{s}/runkosarja/{n}/{pg}/"
            data = http_get(url)
            time.sleep(THROTTLE)
            if data == "MISS":
                man.record_missing(fname, url, "http 404/400/410")
                failed += 1
                continue
            if data is None:
                man.record_missing(fname, url, "fetch failed after retries")
                failed += 1
                errors_early += 1
                if errors_early >= 10 and saved == 0:
                    man.save()
                    print(f"[{year}] ABORT: first {errors_early} fetches all "
                          f"failed — bot protection or network problem. "
                          f"Paste this output to the manager.", flush=True)
                    return False
                continue
            if len(data) < MIN_HTML_BYTES:
                # keep it verbatim anyway, but flag it — suspicious IS off
                atomic_write_bytes(fpath, data)
                man.record(fname, url, fpath)
                man.record_missing(fname, url,
                                   f"SUSPICIOUS: only {len(data)} bytes")
                failed += 1
                continue
            atomic_write_bytes(fpath, data)
            if fname in man.data["missing"]:
                del man.data["missing"][fname]
            man.record(fname, url, fpath)
            saved += 1
        if i % 10 == 0 or i == len(matchnos):
            man.save()
            print(f"[{year}] {i}/{len(matchnos)} games  "
                  f"(+{saved} files new, {skipped} kept, {failed} problems)",
                  flush=True)
    man.save()

    # 4) season summary — exact numbers for the reconciliation report
    complete = sum(
        1 for n in matchnos
        if all(valid_html_file(out_dir / f"game_{year}_{n}_{p}.html")
               for p in PAGES))
    print(f"[{year}] DONE: {len(matchnos)} games in schedule, "
          f"{complete} with all {len(PAGES)} pages saved, "
          f"{len(matchnos) - complete} incomplete, "
          f"{len(man.data['missing'])} recorded problems", flush=True)
    if complete != len(matchnos):
        bad = [n for n in matchnos
               if not all(valid_html_file(out_dir / f"game_{year}_{n}_{p}.html")
                          for p in PAGES)]
        print(f"[{year}] INCOMPLETE game match numbers: {bad[:40]}"
              f"{' ...' if len(bad) > 40 else ''}")
    return complete == len(matchnos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\dev\HOCKEYPROJECTS_V2\data\raw\mestis"
                    if sys.platform == "win32" else
                    str(Path.home() / "HOCKEYPROJECTS_V2/data/raw/mestis"))
    ap.add_argument("--seasons", nargs="*", type=int,
                    default=[2023, 2024, 2025, 2026])
    args = ap.parse_args()

    ok = True
    for year in args.seasons:
        print(f"\n=== Season {season_str(year)} (dir {year}) ===", flush=True)
        ok = fetch_season(year, args.out) and ok

    print("\nMestis lake fetch finished." if ok else
          "\nMestis lake fetch finished WITH PROBLEMS — paste the full "
          "output to the manager.")
    print("Never edit files inside the lake. Next: run "
          "verify_mestis_lake.py for the completeness report.")


if __name__ == "__main__":
    main()
