"""
fetch_nhl_raw.py — NHL raw data lake builder (v2, fetch-only)
==============================================================
Downloads and permanently caches RAW NHL API responses. Does NO processing,
NO filtering, NO calculation — the point is a complete, immutable data lake
that every v2 pipeline can be run and re-run against, offline.

Per game it saves:
  <out>/<season>/schedule_index.json          (one per season — all game metadata)
  <out>/<season>/<gameId>_pbp.json            (gamecenter play-by-play, verbatim)
  <out>/<season>/<gameId>_boxscore.json       (gamecenter boxscore, verbatim)
  <out>/<season>/<gameId>_rightrail.json      (gameInfo incl. HEAD COACHES, linescore)
  <out>/<season>/<gameId>_shifts.json         (shift charts, only with --shifts)

Resumable: already-downloaded files are skipped, so it can be stopped and
re-run at any time. Run it on a machine with normal internet access
(Windows PC or the Ubuntu server) — it needs nothing but Python 3.9+ stdlib.

Usage:
  python fetch_nhl_raw.py                       # both seasons, pbp+boxscore
  python fetch_nhl_raw.py --out D:\\lake\\nhl    # custom output dir
  python fetch_nhl_raw.py --seasons 20252026    # one season only
  python fetch_nhl_raw.py --shifts              # also fetch shift charts
"""

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://api-web.nhle.com/v1"
SHIFTS_URL = "https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={gid}"
HEADERS = {"User-Agent": "HOCKEYPROJECTS-V2/1.0"}
THROTTLE_SECONDS = 0.3

# Regular-season windows (wide on purpose; schedule walk filters precisely)
SEASONS = {
    "20242025": (date(2024, 10, 1), date(2025, 4, 25)),
    "20252026": (date(2025, 10, 1), date(2026, 4, 25)),
}


def api_get(url, retries=4, delay=1.5):
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=30) as resp:
                return json.loads(resp.read().decode())
        except (HTTPError, URLError, TimeoutError, Exception) as e:
            if isinstance(e, HTTPError) and e.code == 404:
                return None
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  FAILED after {retries} tries: {url} — {e}")
                return None


def build_schedule_index(season, start, end, out_dir):
    """Walk the schedule week by week; save every completed regular-season game."""
    index_path = out_dir / "schedule_index.json"
    if index_path.exists():
        with open(index_path) as f:
            idx = json.load(f)
        if idx.get("complete"):
            print(f"[{season}] schedule index already complete "
                  f"({len(idx['games'])} games) — skipping walk")
            return idx["games"]

    print(f"[{season}] walking schedule {start} → {end} ...")
    games = {}
    current = start
    while current <= end:
        data = api_get(f"{API_BASE}/schedule/{current.strftime('%Y-%m-%d')}")
        time.sleep(THROTTLE_SECONDS)
        advanced = False
        if data and "gameWeek" in data:
            for day in data["gameWeek"]:
                for g in day.get("games", []):
                    if g.get("gameType") != 2:
                        continue
                    if str(g.get("season", "")) != season:
                        continue
                    if g.get("gameState", "") not in ("OFF", "FINAL"):
                        continue
                    games[str(g["id"])] = {
                        "id": g["id"],
                        "date": day.get("date", ""),
                        "away": g.get("awayTeam", {}).get("abbrev", ""),
                        "home": g.get("homeTeam", {}).get("abbrev", ""),
                    }
            current += timedelta(days=7)
            advanced = True
        if not advanced:
            current += timedelta(days=1)

    ordered = sorted(games.values(), key=lambda g: (g["date"], g["id"]))
    with open(index_path, "w") as f:
        json.dump({"season": season, "complete": True,
                   "fetched_on": date.today().isoformat(),
                   "count": len(ordered), "games": ordered}, f, indent=2)
    print(f"[{season}] schedule index saved: {len(ordered)} completed games")
    return ordered


def fetch_game(gid, out_dir, want_shifts):
    """Fetch pbp (+boxscore, +shifts) for one game. Returns files fetched."""
    fetched = 0
    targets = [
        (out_dir / f"{gid}_pbp.json", f"{API_BASE}/gamecenter/{gid}/play-by-play"),
        (out_dir / f"{gid}_boxscore.json", f"{API_BASE}/gamecenter/{gid}/boxscore"),
        (out_dir / f"{gid}_rightrail.json", f"{API_BASE}/gamecenter/{gid}/right-rail"),
    ]
    if want_shifts:
        targets.append((out_dir / f"{gid}_shifts.json", SHIFTS_URL.format(gid=gid)))
    for path, url in targets:
        if path.exists() and path.stat().st_size > 200:
            continue
        data = api_get(url)
        time.sleep(THROTTLE_SECONDS)
        if data is None:
            print(f"  WARN game {gid}: no data from {url}")
            continue
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)  # atomic: no half-written files in the lake
        fetched += 1
    return fetched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\dev\HOCKEYPROJECTS_V2\data\raw\nhl"
                    if sys.platform == "win32" else
                    str(Path.home() / "HOCKEYPROJECTS_V2/data/raw/nhl"))
    ap.add_argument("--seasons", nargs="*", default=list(SEASONS.keys()))
    ap.add_argument("--shifts", action="store_true")
    args = ap.parse_args()

    for season in args.seasons:
        if season not in SEASONS:
            sys.exit(f"Unknown season {season}. Known: {list(SEASONS)}")
        start, end = SEASONS[season]
        out_dir = Path(args.out) / season
        out_dir.mkdir(parents=True, exist_ok=True)
        games = build_schedule_index(season, start, end, out_dir)
        total = len(games)
        done_new = 0
        for i, g in enumerate(games, 1):
            done_new += fetch_game(g["id"], out_dir, args.shifts)
            if i % 50 == 0 or i == total:
                print(f"[{season}] {i}/{total} games checked "
                      f"({done_new} new files this run)")
        print(f"[{season}] DONE. Lake dir: {out_dir}")

    print("\nAll requested seasons complete. This folder is now the canonical "
          "raw data lake — never edit files inside it.")


if __name__ == "__main__":
    main()
