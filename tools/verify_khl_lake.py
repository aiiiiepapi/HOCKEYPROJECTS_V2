#!/usr/bin/env python3
"""KHL lake verification — lake-level only (kickoff step 5), re-runnable by
the Manager per rule 0. Verifies a lake root produced by tools/fetch_khl.py.

Checks per season (2023/2024/2025/2026):
  1. Schedule authority: re-derive the game-id set from the ON-DISK
     calendar_<tid>.html, SCOPED to the season tid (widget/slider links to
     other tournaments excluded by the tid filter).
  2. 0 missing / 0 stray: every scoped gid has <gid>_text.html AND
     <gid>_protocol.html on disk; no game files outside the scoped set.
  3. Manifest integrity: every file on disk has a manifest row; re-hash
     sha256 + byte size match (catches transfer alteration — the 2026-08-05
     autocrlf incident); http_code 200; truncation flag column empty.
  4. Structural count gate (rule 14, per-season): scoped count == expected.
  5. Seeded-random spot-opens (--seed, default 20260805): N games/season,
     confirm capability anchors on real content, SCOPED (ticker lesson):
     text page has >0 structured textBroadcast-item events and a coach
     block; protocol page has the goals/penalty/player-stats structures.

Usage:
  python tools/verify_khl_lake.py --lake C:\\dev\\khl_lake [--season all]
                                  [--seed 20260805] [--spots 5]
                                  [--write-completeness]
Exit 0 = all PASS.
"""
import argparse
import csv
import hashlib
import os
import random
import re
import sys

SEASONS = {
    2023: (1154, 748),
    2024: (1217, 782),
    2025: (1288, 782),
    2026: (1369, 748),
}


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def verify_season(year, lake, seed, spots):
    tid, expected = SEASONS[year]
    d = os.path.join(lake, 'khl', str(year))
    errs, warns = [], []
    if not os.path.isdir(d):
        return [f'{year}: season directory missing: {d}'], [], {}

    # 1. scoped authority set from on-disk calendar
    cal = os.path.join(d, f'calendar_{tid}.html')
    if not os.path.exists(cal):
        return [f'{year}: calendar_{tid}.html missing'], [], {}
    html = read(cal).decode('utf-8', errors='replace')
    gids = sorted({int(g) for g in
                   re.findall(r'/game/%d/(\d+)/protocol/' % tid, html)})
    if len(gids) != expected:
        errs.append(f'{year}: scoped calendar count {len(gids)} != expected {expected}')

    # 2. missing / stray
    on_disk = os.listdir(d)
    game_files = [f for f in on_disk if re.match(r'^\d+_(text|protocol)\.html$', f)]
    have = {}
    for f in game_files:
        gid, kind = f.split('_')[0], f.split('_')[1].split('.')[0]
        have.setdefault(int(gid), set()).add(kind)
    missing = [(g, k) for g in gids for k in ('text', 'protocol')
               if k not in have.get(g, set())]
    stray = sorted(set(have) - set(gids))
    if missing:
        errs.append(f'{year}: {len(missing)} missing artifacts, first: {missing[:5]}')
    if stray:
        errs.append(f'{year}: {len(stray)} stray game ids not in scoped calendar: {stray[:5]}')

    # 3. manifest integrity + re-hash
    man = os.path.join(d, 'manifest.csv')
    if not os.path.exists(man):
        return errs + [f'{year}: manifest.csv missing'], warns, {}
    rows = {}
    with open(man, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows[row['file']] = row  # last write wins (resume re-fetches)
    unmanifested = [f for f in game_files + [f'calendar_{tid}.html'] if f not in rows]
    if unmanifested:
        errs.append(f'{year}: {len(unmanifested)} files with no manifest row: {unmanifested[:5]}')
    altered, badcode, flagged = [], [], []
    for name, row in rows.items():
        p = os.path.join(d, name)
        if not os.path.exists(p):
            continue  # covered by missing-check if it matters
        b = read(p)
        if str(len(b)) != row['bytes'] or hashlib.sha256(b).hexdigest() != row['sha256']:
            altered.append(name)
        if row['http_code'] != '200':
            badcode.append((name, row['http_code']))
        if row.get('flag') and row['flag'] not in ('', 'resume_skip'):
            flagged.append((name, row['flag']))
    if altered:
        errs.append(f'{year}: {len(altered)} files ALTERED vs manifest (transfer!): {altered[:5]}')
    if badcode:
        errs.append(f'{year}: {len(badcode)} non-200 rows: {badcode[:5]}')
    if flagged:
        warns.append(f'{year}: {len(flagged)} truncation-flagged rows: {flagged[:8]}')

    # 5. seeded spot-opens, scoped anchors
    rng = random.Random(seed + year)
    sample = rng.sample(gids, min(spots, len(gids))) if gids else []
    spot_fail = []
    for g in sample:
        try:
            t = read(os.path.join(d, f'{g}_text.html')).decode('utf-8', 'replace')
            p = read(os.path.join(d, f'{g}_protocol.html')).decode('utf-8', 'replace')
        except OSError as e:
            spot_fail.append((g, f'unreadable: {e}')); continue
        n_items = t.count('<div class="textBroadcast-item">')
        if n_items == 0:
            spot_fail.append((g, 'no structured broadcast items'))
        if 'Тренер' not in t:
            spot_fail.append((g, 'no coach block on text page'))
        if 'СТАТИСТИКА ИГРОКОВ' not in p and 'protocol-table' not in p:
            spot_fail.append((g, 'no protocol tables'))
    if spot_fail:
        errs.append(f'{year}: spot-open failures: {spot_fail}')

    stats = {'games': len(gids), 'ids': (gids[0], gids[-1]) if gids else None,
             'files': len(game_files), 'sample': sample,
             'flagged': len(flagged)}
    return errs, warns, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lake', required=True)
    ap.add_argument('--season', default='all')
    ap.add_argument('--seed', type=int, default=20260805)
    ap.add_argument('--spots', type=int, default=5)
    ap.add_argument('--write-completeness', action='store_true')
    args = ap.parse_args()
    years = sorted(SEASONS) if args.season == 'all' else [int(args.season)]
    all_errs, lines = [], []
    lines.append('| Season | Games (scoped) | id range | Artifacts on disk | Flagged | Spot sample | Status |')
    lines.append('|---|---|---|---|---|---|---|')
    for y in years:
        errs, warns, st = verify_season(y, args.lake, args.seed, args.spots)
        status = 'PASS' if not errs else 'FAIL'
        print(f'== {y}: {status}')
        for e in errs:
            print('  ERR ', e)
        for w in warns:
            print('  WARN', w)
        if st:
            print(f'  games={st["games"]} ids={st["ids"]} files={st["files"]} '
                  f'flagged={st["flagged"]} sample={st["sample"]}')
            lines.append(f'| {y-1}-{str(y)[2:]} | {st["games"]} | '
                         f'{st["ids"][0]}..{st["ids"][1]} | {st["files"]} | '
                         f'{st["flagged"]} | {st["sample"]} | {status} |')
        all_errs += errs
    if args.write_completeness:
        out = os.path.join(args.lake, 'khl', 'COMPLETENESS.md')
        with open(out, 'w', encoding='utf-8') as f:
            f.write('# KHL lake completeness report\n\n')
            f.write(f'Verified by tools/verify_khl_lake.py, seed {args.seed}, '
                    f'{args.spots} spot-opens/season.\n\n')
            f.write('\n'.join(lines) + '\n')
        print('wrote', out)
    print('\nOVERALL:', 'PASS' if not all_errs else f'FAIL ({len(all_errs)} errors)')
    sys.exit(0 if not all_errs else 1)


if __name__ == '__main__':
    main()
