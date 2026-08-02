#!/usr/bin/env python3
"""MORNING BOT v1 (data-mining phase) — per-team pull expectancy cards.

Usage:
  python3 morning_bot.py                          # cards for all 32 teams
  python3 morning_bot.py --slate "COL@DAL,TOR@BOS"
  python3 morning_bot.py --slate "COL@DAL" --ml COL:-285 --ml DAL:+240

Weighted INTO the %% (tested, within-coach validated):
  - coach identity: recency-weighted clean-chance record + league Beta prior
  - strength regime tonight (one-sided grading, measured 2026-07-31):
      favorite (implied win >=53%%): logit +0.46   [66%% pooled vs 54.5%%]
      mid                          : logit -0.07
      heavy dog (implied < 40%%)   : logit -0.62   [39%% pooled]
    (slight vs heavy favorite: NO measured difference — not graded up)
Displayed but NOT weighted (untested or measured null):
  venue (+1.6pts within-coach = noise at chance level), B2B, playoff race,
  lineup/injuries (no data source yet), last-pull outcome (measured null).

Requires the repo's derived files to be fresh (RUNBOOK: extraction ->
clean_window -> profiles). Writes morning_cards.md.
"""
import json, math, argparse, sys, datetime
from pathlib import Path
from collections import defaultdict

TEAM_ABBR = {
 "Anaheim Ducks":"ANA","Boston Bruins":"BOS","Buffalo Sabres":"BUF","Calgary Flames":"CGY",
 "Carolina Hurricanes":"CAR","Chicago Blackhawks":"CHI","Colorado Avalanche":"COL",
 "Columbus Blue Jackets":"CBJ","Dallas Stars":"DAL","Detroit Red Wings":"DET",
 "Edmonton Oilers":"EDM","Florida Panthers":"FLA","Los Angeles Kings":"LAK",
 "Minnesota Wild":"MIN","Montreal Canadiens":"MTL","Montréal Canadiens":"MTL",
 "Nashville Predators":"NSH","New Jersey Devils":"NJD","New York Islanders":"NYI",
 "New York Rangers":"NYR","Ottawa Senators":"OTT","Philadelphia Flyers":"PHI",
 "Pittsburgh Penguins":"PIT","San Jose Sharks":"SJS","Seattle Kraken":"SEA",
 "St Louis Blues":"STL","St. Louis Blues":"STL","Tampa Bay Lightning":"TBL",
 "Toronto Maple Leafs":"TOR","Utah Hockey Club":"UTA","Utah Mammoth":"UTA",
 "Vancouver Canucks":"VAN","Vegas Golden Knights":"VGK","Washington Capitals":"WSH",
 "Winnipeg Jets":"WPG"}

ROOT = Path(__file__).resolve().parent
DER = ROOT / "data" / "derived"

SHIFT = {"fav": 0.46, "mid": -0.07, "heavy_dog": -0.62}
POOLED = 0.545

def logit(p): return math.log(p / (1 - p))
def expit(x): return 1 / (1 + math.exp(-x))

def implied(ml):
    ml = int(ml)
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)

def regime(p_win):
    if p_win is None: return None
    if p_win >= 0.53: return "fav"
    if p_win < 0.40: return "heavy_dog"
    return "mid"

def fmt_t(sec):
    return "%d:%02d" % (int(sec) // 60, int(sec) % 60)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slate", default="", help="comma list AWY@HOM")
    ap.add_argument("--ml", action="append", default=[], help="TEAM:americanline")
    ap.add_argument("--odds-json", default="", help="Odds API snapshot (auto slate + lines)")
    ap.add_argument("--hours", type=int, default=30, help="games starting within N hours")
    args = ap.parse_args()

    profiles = json.load(open(DER / "coach_profiles.json"))
    cw = json.load(open(DER / "clean_window_instances.json"))

    cur = {}
    for p in profiles:
        if p["last_seen"] < "2025-06-01":     # ghost teams/coaches (ARI)
            continue
        if p["team"] not in cur or p["last_seen"] > cur[p["team"]]["last_seen"]:
            cur[p["team"]] = p

    # per-coach classified chances: (date, took, pull_R)
    chances = defaultdict(list)
    for r in sorted(cw, key=lambda x: x["date"]):
        took = r["pulled"] and r["pull_type"] == "ev"
        dec = (not r["pulled"]) and r["frac_ev"] >= 0.7
        if took or dec:
            chances[r["coach"]].append((r["date"], took, r.get("pull_R")))

    # manual team-study notes (optional file: team,note)
    notes = {}
    nf = ROOT / "data" / "coach_maps" / "special_notes.csv"
    if nf.exists():
        import csv as _csv
        for row in _csv.DictReader(open(nf, encoding="utf-8")):
            notes[row["team"].strip()] = row["note"].strip()

    slate_teams, opps, venue = {}, {}, {}
    auto_ml = {}
    if args.odds_json:
        now = datetime.datetime.now(datetime.timezone.utc)
        for ev in json.load(open(args.odds_json)):
            try:
                ct = datetime.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
            except Exception:
                continue
            if not (0 <= (ct - now).total_seconds() <= args.hours * 3600):
                continue
            h, a = TEAM_ABBR.get(ev["home_team"]), TEAM_ABBR.get(ev["away_team"])
            if not h or not a:
                continue
            slate_teams[h] = slate_teams[a] = True
            opps[h], opps[a] = a, h
            venue[h], venue[a] = "home", "away"
            prices = defaultdict(list)
            for bk in ev.get("bookmakers", []):
                for mk in bk.get("markets", []):
                    if mk.get("key") != "h2h":
                        continue
                    for o in mk.get("outcomes", []):
                        t = TEAM_ABBR.get(o.get("name"))
                        if t:
                            prices[t].append(int(o["price"]))
            for t, ps in prices.items():
                ps.sort()
                auto_ml[t] = implied(ps[len(ps) // 2])   # median book
    for m in [x for x in args.slate.split(",") if x]:
        a, h = m.strip().upper().split("@")
        slate_teams[a] = True; slate_teams[h] = True
        opps[a], opps[h] = h, a
        venue[a], venue[h] = "away", "home"
    mls = dict(auto_ml)
    for m in args.ml:
        t, v = m.split(":")
        mls[t.strip().upper()] = implied(v)

    SEASON_CUT = "2025-07-01"      # "last year" = 2025-26
    TWOSEA_CUT = "2024-07-01"      # pull-time window = last two seasons
    today = datetime.date.today().isoformat()

    teams = sorted(slate_teams) if slate_teams else sorted(cur)
    out = ["# MORNING PULL CARDS — trailing by 3, 3rd period\n",
           "Card spec (Seb 2026-08-02): expected %, last-year record, last 5 "
           "clean chances, recency-weighted avg pull time (2 seasons), special "
           "notes. Fav/dog effect lives in the notes, NOT in the headline %.\n"]
    for team in teams:
        p = cur.get(team)
        if not p:
            out.append(f"## {team} — no coach data\n"); continue
        seq = chances.get(p["coach"], [])
        base = p["expected_pull_pct"]
        # --- Seb rules 28/28b (2026-08-01); no-bet on the headline (base) % ----
        last5 = seq[-5:]
        l5 = " ".join("P" if t else "NP" for _, t, _ in last5) or "-"
        hot = bool(seq) and (seq[-1][1] or sum(t for _, t, _ in seq[-3:]) >= 2)
        no_bet = base < 0.40
        # last-year classified record
        yr = [(d, t) for d, t, _ in seq if d >= SEASON_CUT]
        yp = sum(t for _, t in yr)
        # avg pull time, last two seasons, slight recency weight (12mo half-life)
        pt_w = pt_s = 0.0
        npt = 0
        for d, t, pr in seq:
            if t and pr is not None and d >= TWOSEA_CUT:
                w = 0.5 ** ((datetime.date.fromisoformat(today)
                             - datetime.date.fromisoformat(d)).days / 365.0)
                pt_w += w; pt_s += w * pr; npt += 1
        timing = f"{fmt_t(pt_s / pt_w)} left ({npt} pulls)" if npt >= 3 else \
                 f"~4:19 (league — only {npt} pull(s) last 2 seasons)"
        # --- special notes ----------------------------------------------------
        sp = []
        pw = mls.get(team)
        reg = regime(pw)
        if reg:
            adj = expit(logit(max(min(base, 0.97), 0.03)) + SHIFT[reg])
            sp.append({"fav": f"FAVORITE tonight ({pw:.0%} implied) — plays like {adj:.0%}",
                       "mid": f"near-even line ({pw:.0%} implied) — no shift",
                       "heavy_dog": f"HEAVY DOG tonight ({pw:.0%} implied) — plays like {adj:.0%}"}[reg])
        sp.extend(p["flags"])
        if team in notes:
            sp.append(notes[team])
        vloc = venue.get(team)
        opp = f" vs {opps[team]}" if team in opps else ""
        badge = ""
        if no_bet:
            badge += "  [NO-BET: <40% (rule 28, amended 2026-08-02)]"
        if hot:
            badge += "  [HOT FORM: " + ("pulled last chance" if seq[-1][1] else "2 of last 3") + " (rule 28b)]"
        out.append(f"## {team}{opp} — {p['coach']}{badge}")
        out.append(f"**Expected pull: {base:.0%}**  (band {p['band'][0]:.0%}-{p['band'][1]:.0%}, "
                   f"career {p['clear_taken']}/{p['clear_chances']})")
        out.append(f"- 2025-26 classified: {yp} pull / {len(yr) - yp} no-pull")
        out.append(f"- Last 5 clean chances: {l5}"
                   + (f"  (oldest {last5[0][0]})" if last5 else ""))
        out.append(f"- Avg pull time (2 seasons, recency-weighted): {timing}")
        out.append(f"- Special notes: {'; '.join(sp) if sp else 'none'}")
        if vloc:
            out.append(f"- Context (not in number): playing {vloc}; lineup/goalie/B2B unknown")
        out.append("")
    Path("morning_cards.md").write_text("\n".join(out))
    print("\n".join(out[:40]))
    print(f"\nwrote morning_cards.md ({len(teams)} teams)")

if __name__ == "__main__":
    main()
