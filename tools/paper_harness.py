"""
paper_harness.py — live paper-trading logger (runs on Seb's Windows PC).

WHAT IT DOES, every ~60s while games are live:
  1. Watches live scores/clocks for NHL + AHL + Liiga (free league feeds).
  2. When a tracked game is in a MONEY MOMENT — 3rd period, 3-goal gap,
     3:00..15:00 left — it logs a row with: game state, trailing coach,
     expected pull %% (from repo profiles), rule-28 NO-BET status, hot-form
     flag, and the model's +10%%-EV threshold lines (precomputed CSVs, no
     MC on this machine).
  3. Fetches the bookmakers' CURRENT odds for that league (Odds API) and
     stores the raw JSON next to the log — measuring what lines actually
     exist live is half the point of the paper month.
  4. Credit discipline: odds calls fire ONLY during money moments, at most
     one per league per ODDS_COOLDOWN seconds, hard nightly cap.

SETTLEMENT is NOT done here: the nightly lake fetch + a cheap session join
outcomes to the log offline (RUNBOOK). This file only ever appends.

Usage (from a clone of HOCKEYPROJECTS_V2):
  python tools\\paper_harness.py               # run until no live games
  python tools\\paper_harness.py --once        # single scan (testing)
  python tools\\paper_harness.py --leagues nhl liiga
Output: paper_log\\paper_YYYY-MM-DD.jsonl + paper_log\\odds\\*.json

SHAKEDOWN NOTES (September, preseason/Liiga): the live clock parsing for
AHL/Liiga is best-effort until verified against real live feeds — every raw
scoreboard payload is cached on first sight per game so parsing can be fixed
offline without losing evidence. NHL uses /v1/score/now (one call, all games).
"""
import argparse
import csv
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOGDIR = ROOT / "paper_log"
ODDS_KEY = (ROOT / "config" / "odds_api_key.txt").read_text().strip()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

SCAN_EVERY = 60          # seconds between scoreboard scans
ODDS_COOLDOWN = 150      # min seconds between odds calls per league
ODDS_NIGHT_CAP = 120     # max odds calls per night, total
R_LO, R_HI = 180, 900    # bettable window (15:00 -> 3:00)
ODDS_MARKETS = "h2h,totals,spreads,team_totals,alternate_totals,alternate_spreads"

LEAGUES = {
    "nhl":   {"sport": "icehockey_nhl"},
    "ahl":   {"sport": "icehockey_ahl",
              "ht_key": "ccb91f29d6744675", "ht_client": "ahl"},
    "liiga": {"sport": "icehockey_liiga", "season": 2027},
}


def get(url, timeout=15):
    try:
        with urlopen(Request(url, headers=UA), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print(f"  [warn] {type(e).__name__} {url[:90]}")
        return None


def load_tables():
    """threshold lines + coach profiles per league (from the repo checkout)."""
    tables, profiles = {}, {}
    files = {"nhl": ("lines_10ev_per_second.csv", "coach_profiles.json"),
             "ahl": ("lines_10ev_ahl.csv", "ahl_coach_profiles.json"),
             "liiga": ("lines_10ev_liiga.csv", "liiga_coach_profiles.json")}
    for lg, (lines_f, prof_f) in files.items():
        lp = ROOT / "data" / "derived" / lines_f
        pp = ROOT / "data" / "derived" / prof_f
        if lp.exists():
            tab = {}
            with open(lp, newline="", encoding="utf-8") as f:
                rd = csv.DictReader(f)
                for row in rd:
                    tab[(int(float(row["R"])), row["state"],
                         float(row["tier"]))] = row
            tables[lg] = tab
        if pp.exists():
            raw = json.load(open(pp, encoding="utf-8"))
            plist = raw["profiles"] if isinstance(raw, dict) else raw
            # latest coach per team
            cur = {}
            for p in plist:
                t = p.get("team")
                if t and (t not in cur or p.get("last_seen", "") > cur[t].get("last_seen", "")):
                    cur[t] = p
            profiles[lg] = cur
    return tables, profiles


def tier_of(pct):
    return min([0.25, 0.40, 0.55, 0.70, 0.85], key=lambda t: abs(t - pct))


# ---------------- live scoreboards (one function per league) -----------------
def live_nhl():
    """NHL /v1/score/now -> list of live game states."""
    d = get("https://api-web.nhle.com/v1/score/now")
    out = []
    for g in (d or {}).get("games", []):
        if g.get("gameState") not in ("LIVE", "CRIT"):
            continue
        per = (g.get("periodDescriptor") or {}).get("number")
        clock = (g.get("clock") or {}).get("timeRemaining") or ""
        try:
            m, s = clock.split(":")
            R = int(m) * 60 + int(s)
        except Exception:
            continue
        out.append({"league": "nhl", "gid": str(g.get("id")),
                    "home": (g.get("homeTeam") or {}).get("abbrev"),
                    "away": (g.get("awayTeam") or {}).get("abbrev"),
                    "hs": (g.get("homeTeam") or {}).get("score", 0),
                    "as": (g.get("awayTeam") or {}).get("score", 0),
                    "period": per, "R": R, "raw": g})
    return out


def live_ahl():
    cfg = LEAGUES["ahl"]
    d = get("https://lscluster.hockeytech.com/feed/index.php?feed=modulekit"
            f"&view=scorebar&client_code={cfg['ht_client']}&key={cfg['ht_key']}"
            "&fmt=json&numberofdaysahead=0&numberofdaysback=0")
    out = []
    rows = ((d or {}).get("SiteKit") or {}).get("Scorebar") or []
    for g in rows:
        if str(g.get("GameStatus")) != "2":       # 2 = in progress (verify in shakedown)
            continue
        per_s = str(g.get("Period") or "")
        clock = str(g.get("GameClock") or "")
        try:
            per = int(per_s)
            m, s = clock.split(":")
            R = int(m) * 60 + int(s)
        except Exception:
            continue
        out.append({"league": "ahl", "gid": str(g.get("ID")),
                    "home": g.get("HomeCode"), "away": g.get("VisitorCode"),
                    "hs": int(g.get("HomeGoals") or 0),
                    "as": int(g.get("VisitorGoals") or 0),
                    "period": per, "R": R, "raw": g})
    return out


def live_liiga():
    cfg = LEAGUES["liiga"]
    d = get(f"https://liiga.fi/api/v2/games?tournament=runkosarja&season={cfg['season']}")
    out = []
    entries = (d.get("games") if isinstance(d, dict) else d) or []
    for g in entries:
        if not g.get("started") or g.get("ended"):
            continue
        gid = g.get("id")
        det = get(f"https://liiga.fi/api/v2/games/{cfg['season']}/{gid}")
        game = (det or {}).get("game") or {}
        # live clock field to be verified in shakedown; log raw regardless
        out.append({"league": "liiga", "gid": str(gid),
                    "home": (game.get("homeTeam") or {}).get("teamName"),
                    "away": (game.get("awayTeam") or {}).get("teamName"),
                    "hs": (game.get("homeTeam") or {}).get("goals", 0),
                    "as": (game.get("awayTeam") or {}).get("goals", 0),
                    "period": None, "R": None, "raw": game,
                    "clock_unverified": True})
    return out


LIVE = {"nhl": live_nhl, "ahl": live_ahl, "liiga": live_liiga}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--leagues", nargs="*", default=["nhl", "ahl", "liiga"])
    args = ap.parse_args()

    LOGDIR.mkdir(exist_ok=True)
    (LOGDIR / "odds").mkdir(exist_ok=True)
    tables, profiles = load_tables()
    print(f"tables loaded: {sorted(tables)} | profiles: {sorted(profiles)}")
    logf = LOGDIR / f"paper_{date.today().isoformat()}.jsonl"
    seen_raw = set()
    last_odds = {}
    odds_calls = 0
    empty_scans = 0

    while True:
        any_live = False
        for lg in args.leagues:
            games = LIVE[lg]() or []
            any_live = any_live or bool(games)
            for g in games:
                if g["gid"] not in seen_raw:      # cache one raw payload per game
                    seen_raw.add(g["gid"])
                    (LOGDIR / f"raw_{lg}_{g['gid']}.json").write_text(
                        json.dumps(g["raw"], indent=1))
                if g.get("period") != 3 or g.get("R") is None:
                    continue
                gap = abs(g["hs"] - g["as"])
                if gap != 3 or not (R_LO <= g["R"] <= R_HI):
                    continue
                # ---- MONEY MOMENT ------------------------------------------
                trailing = g["home"] if g["hs"] < g["as"] else g["away"]
                prof = (profiles.get(lg) or {}).get(trailing)
                pct = prof.get("expected_pull_pct") if prof else None
                last3 = (prof or {}).get("last3", "") or ""
                hot = bool(last3) and (last3[-1] == "P" or last3.count("P") >= 2)
                row = {"ts": datetime.now().isoformat(timespec="seconds"),
                       "league": lg, "gid": g["gid"], "home": g["home"],
                       "away": g["away"], "score": [g["as"], g["hs"]],
                       "R": g["R"], "trailing": trailing,
                       "coach": (prof or {}).get("coach"),
                       "expected_pull_pct": pct,
                       "rule28_no_bet": (pct is not None and pct < 0.40),
                       "hot_form": hot}
                tab = tables.get(lg)
                if tab and pct is not None:
                    tr = tier_of(pct)
                    for state in ("not_pulled_EV", "pulled"):
                        cell = tab.get((g["R"], state, tr))
                        if cell:
                            row[f"thresholds_{state}"] = {
                                k: cell[k] for k in cell
                                if k.endswith("_prob") or k.endswith("_line10")}
                # odds snapshot (credit-disciplined)
                now = time.time()
                if (odds_calls < ODDS_NIGHT_CAP
                        and now - last_odds.get(lg, 0) > ODDS_COOLDOWN):
                    sport = LEAGUES[lg]["sport"]
                    od = get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
                             f"?apiKey={ODDS_KEY}&regions=us,eu"
                             f"&markets={ODDS_MARKETS}&oddsFormat=decimal")
                    last_odds[lg] = now
                    odds_calls += 1
                    fn = f"odds/{lg}_{datetime.now().strftime('%H%M%S')}.json"
                    (LOGDIR / fn).write_text(json.dumps(od, indent=0))
                    row["odds_file"] = fn
                with open(logf, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
                print(f"MONEY {lg} {g['away']}@{g['home']} {g['as']}-{g['hs']} "
                      f"R={g['R']} {trailing} coach={row['coach']} "
                      f"pull%={pct} no_bet={row['rule28_no_bet']} hot={hot}")
        if args.once:
            break
        empty_scans = empty_scans + 1 if not any_live else 0
        if empty_scans > 30:                      # ~30 min with nothing live
            print("no live games for 30 min — done for tonight")
            break
        time.sleep(SCAN_EVERY)


if __name__ == "__main__":
    main()
