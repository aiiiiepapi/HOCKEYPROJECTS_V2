"""
fetch_liiga_raw.py — Liiga (Finland) raw data lake builder (v2, fetch-only)
===========================================================================
Downloads and caches RAW liiga.fi API game JSONs. No processing.

Endpoint (verified in v1 research + 1,196 successful v1 fetches):
  https://liiga.fi/api/v1/games/{SEASON_END_YEAR}/{GAME_NUMBER}
Regular-season games are numbered sequentially from 1 (~450-465/season);
playoffs use large ids (55xxx) and are NOT fetched (regular season only,
consistent with the NHL lake). The games-list endpoint is unreliable, so we
walk game numbers and stop after 25 consecutive misses past game 400.

Saves: <out>/<year>/game_<year>_<n>.json
Seasons: year = season END year (2026 = 2025-26). Default 2023..2026.
Resumable; stdlib-only; run on Seb's Windows PC.

Usage:
  python fetch_liiga_raw.py
  python fetch_liiga_raw.py --seasons 2025 2026
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://liiga.fi/api/v1/games"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Accept": "application/json"}
THROTTLE = 0.4
MAX_GID = 620
STOP_AFTER = 25


def api_get(url, retries=3, delay=1.5, verbose=False):
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=20) as resp:
                if verbose:
                    print(f"  OK {url}", flush=True)
                return json.loads(resp.read().decode("utf-8", "replace"))
        except HTTPError as e:
            if e.code in (404, 400):
                if verbose:
                    print(f"  {e.code} (no such game) {url}", flush=True)
                return "MISS"
            print(f"  HTTP {e.code} on {url} (attempt {attempt+1})", flush=True)
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        except (URLError, TimeoutError, ValueError) as e:
            print(f"  {type(e).__name__}: {e} on {url} (attempt {attempt+1})", flush=True)
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\dev\HOCKEYPROJECTS_V2\data\raw\liiga"
                    if sys.platform == "win32" else
                    str(Path.home() / "HOCKEYPROJECTS_V2/data/raw/liiga"))
    ap.add_argument("--seasons", nargs="*", type=int, default=[2023, 2024, 2025, 2026])
    args = ap.parse_args()

    for year in args.seasons:
        out_dir = Path(args.out) / str(year)
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{year}] starting walk (game 1..{MAX_GID}) -> {out_dir}", flush=True)
        misses, saved, checked, errors = 0, 0, 0, 0
        for gid in range(1, MAX_GID + 1):
            path = out_dir / f"game_{year}_{gid}.json"
            checked += 1
            if checked % 20 == 0:
                print(f"[{year}] progress: {checked} checked, {saved} saved, "
                      f"{errors} errors", flush=True)
            if path.exists() and path.stat().st_size > 500:
                misses = 0
                continue
            data = api_get(f"{BASE}/{year}/{gid}", verbose=(checked <= 3))
            if data is None:
                errors += 1
                if errors >= 10 and saved == 0:
                    print(f"[{year}] ABORT: first {errors} requests all failed — "
                          f"the API is refusing this client (bot protection?). "
                          f"Paste this output to the manager.", flush=True)
                    break
            time.sleep(THROTTLE)
            if data == "MISS" or data is None:
                misses += 1
                if gid > 400 and misses >= STOP_AFTER:
                    print(f"[{year}] stopping at game {gid} ({STOP_AFTER} consecutive misses)")
                    break
                continue
            g = (data.get("game") or {})
            if not g.get("ended"):
                misses = 0
                continue  # unfinished game: refetch on a later run
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1)
            tmp.replace(path)
            saved += 1
            misses = 0
            if saved % 50 == 0:
                print(f"[{year}] {saved} new games saved (at game {gid})")
        total = len(list(out_dir.glob("game_*.json")))
        print(f"[{year}] DONE: {total} games in lake ({saved} new this run)")
        if total < 400:
            print(f"  WARNING: expected ~450+ regular-season games — verify "
                  f"(short season / endpoint change / partial run?)")

    print("\nLiiga lake complete. Never edit files inside it.")


if __name__ == "__main__":
    main()
