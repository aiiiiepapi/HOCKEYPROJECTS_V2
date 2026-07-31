"""
fetch_ahl_raw.py — AHL raw data lake builder (v2, fetch-only)
=============================================================
Downloads and permanently caches RAW HockeyTech API responses. No processing,
no filtering — the immutable AHL lake, mirror of the NHL one.

Per season it saves:
  <out>/<season_id>/schedule.json                (full season schedule)
  <out>/<season_id>/<gameId>_pxp.json            (pxpverbose play-by-play:
                                                  goalie_change events with
                                                  in/out ids, goals with
                                                  PP/EN/SH flags, penalties)
  <out>/<season_id>/<gameId>_summary.json        (head coaches, final score,
                                                  goalies)

Resumable; stdlib-only; run on Seb's Windows PC (cloud proxy blocks it).

Usage:
  python fetch_ahl_raw.py                        # all four seasons
  python fetch_ahl_raw.py --seasons 86 90        # subset
  python fetch_ahl_raw.py --out D:\\lake\\ahl
Season IDs (verified against the live API 2026-07-31):
  77 = 2022-23 regular, 81 = 2023-24, 86 = 2024-25, 90 = 2025-26
  (94 = 2026-27, add when the season starts)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://lscluster.hockeytech.com/feed/index.php"
KEY = "ccb91f29d6744675"
CLIENT = "ahl"
THROTTLE = 0.4
SEASONS = ["77", "81", "86", "90"]
SEASON_LABEL = {"77": "2022-23", "81": "2023-24", "86": "2024-25", "90": "2025-26",
                "94": "2026-27"}


def api_get(url, retries=4, delay=1.5):
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers={"User-Agent": "HOCKEYPROJECTS-V2/1.0"}),
                         timeout=40) as resp:
                txt = resp.read().decode("utf-8", "replace")
                # HockeyTech sometimes wraps JSON in a JS callback; strip if so
                if txt.startswith("("):
                    txt = txt.strip("()")
                return json.loads(txt)
        except (HTTPError, URLError, TimeoutError, ValueError) as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  FAILED after {retries} tries: {url} -- {e}")
                return None


def save_atomic(path, data):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\dev\HOCKEYPROJECTS_V2\data\raw\ahl"
                    if sys.platform == "win32" else
                    str(Path.home() / "HOCKEYPROJECTS_V2/data/raw/ahl"))
    ap.add_argument("--seasons", nargs="*", default=SEASONS)
    args = ap.parse_args()

    for season in args.seasons:
        out_dir = Path(args.out) / season
        out_dir.mkdir(parents=True, exist_ok=True)
        sched_path = out_dir / "schedule.json"
        if sched_path.exists():
            sched = json.load(open(sched_path, encoding="utf-8"))
        else:
            sched = api_get(f"{BASE}?feed=modulekit&view=schedule&client_code={CLIENT}"
                            f"&season_id={season}&key={KEY}&fmt=json")
            time.sleep(THROTTLE)
            if sched is None:
                print(f"[{season}] schedule fetch failed, skipping season")
                continue
            save_atomic(sched_path, sched)
        rows = (sched.get("SiteKit") or {}).get("Schedule") or []
        games = [r for r in rows if str(r.get("final")) == "1"]
        label = SEASON_LABEL.get(season, season)
        print(f"[{season} = {label}] schedule rows: {len(rows)}, final games: {len(games)}")
        if len(games) < 500 and season != "94":
            print(f"  WARNING: expected ~1100+ final games for a full AHL season — "
                  f"verify before trusting this season (partial season or API change?)")
        done_new = 0
        for i, g in enumerate(games, 1):
            gid = g.get("game_id") or g.get("id")
            for suffix, url in (
                ("_pxp.json", f"{BASE}?feed=gc&tab=pxpverbose&game_id={gid}"
                              f"&key={KEY}&client_code={CLIENT}&fmt=json&lang_code=en"),
                ("_summary.json", f"{BASE}?feed=gc&tab=gamesummary&game_id={gid}"
                                  f"&key={KEY}&client_code={CLIENT}&fmt=json&lang_code=en"),
            ):
                path = out_dir / f"{gid}{suffix}"
                if path.exists() and path.stat().st_size > 200:
                    continue
                data = api_get(url)
                time.sleep(THROTTLE)
                if data is None:
                    print(f"  WARN game {gid}: no data ({suffix})")
                    continue
                save_atomic(path, data)
                done_new += 1
            if i % 50 == 0 or i == len(games):
                print(f"[{season}] {i}/{len(games)} games checked ({done_new} new files)")
        print(f"[{season}] DONE. Lake dir: {out_dir}")

    print("\nAll requested seasons complete. This folder is the canonical raw "
          "AHL lake — never edit files inside it.")


if __name__ == "__main__":
    main()
