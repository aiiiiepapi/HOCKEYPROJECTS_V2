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
import json, math, argparse, sys
from pathlib import Path
from collections import defaultdict

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
    args = ap.parse_args()

    profiles = json.load(open(DER / "coach_profiles.json"))
    cw = json.load(open(DER / "clean_window_instances.json"))
    insts = {(i["game_id"], i["n"]): i for i in json.load(open(DER / "instances_gap3.json"))}

    cur = {}
    for p in profiles:
        if p["team"] not in cur or p["last_seen"] > cur[p["team"]]["last_seen"]:
            cur[p["team"]] = p

    # last-3 chance stories per coach
    stories = defaultdict(list)
    for r in sorted(cw, key=lambda x: x["date"]):
        took = r["pulled"] and r["pull_type"] == "ev"
        dec = (not r["pulled"]) and r["frac_ev"] >= 0.7
        if not (took or dec):
            continue
        inst = insts.get((r["game_id"], r["n"]), {})
        opp = (inst.get("away") if r["team"] == inst.get("home") else inst.get("home")) or "?"
        ha = "vs" if r["team"] == inst.get("home") else "@"
        if took:
            reason = (inst.get("pull_end") or {}).get("reason", "")
            what = {"en_goal_against": "ate ENG", "scored_during_pull": "SCORED 6v5",
                    "goalie_returned": "goalie returned", "gap_end": "to the horn"}.get(reason, reason or "")
            s = f"{r['date']} {ha} {opp} — PULLED {fmt_t(r['pull_R'])} left, {what}"
        else:
            end = "horn" if r["closed_R"] == 0 else f"{fmt_t(r['closed_R'])} left"
            s = (f"{r['date']} {ha} {opp} — NO PULL (clean window "
                 f"{fmt_t(min(r['opened_R'],900))}->{end}, quality {r['frac_ev']:.0%})")
        stories[r["coach"]].append(s)

    slate_teams, opps, venue = {}, {}, {}
    for m in [x for x in args.slate.split(",") if x]:
        a, h = m.strip().upper().split("@")
        slate_teams[a] = True; slate_teams[h] = True
        opps[a], opps[h] = h, a
        venue[a], venue[h] = "away", "home"
    mls = {}
    for m in args.ml:
        t, v = m.split(":")
        mls[t.strip().upper()] = implied(v)

    teams = sorted(slate_teams) if slate_teams else sorted(cur)
    out = ["# MORNING PULL CARDS — trailing by 3, 3rd period\n",
           f"League baseline on a clean 5v5 chance: {POOLED:.0%}. "
           "Strength regime is the only situational factor weighted into the % "
           "(favorite +, heavy dog −−; venue/B2B/lineups shown as context only — "
           "measured noise or no data). P>0.75 reads as '0.75+' (known hot zone).\n"]
    for team in teams:
        p = cur.get(team)
        if not p:
            out.append(f"## {team} — no coach data\n"); continue
        base = p["expected_pull_pct"]
        pw = mls.get(team)
        reg = regime(pw)
        adj = base
        why_adj = "no line given — base number"
        if reg:
            adj = expit(logit(max(min(base, 0.97), 0.03)) + SHIFT[reg])
            why_adj = {"fav": f"favorite tonight ({pw:.0%} implied) -> pulled UP",
                       "mid": f"near even ({pw:.0%} implied) -> ~unchanged",
                       "heavy_dog": f"heavy underdog ({pw:.0%} implied) -> pulled DOWN hard"}[reg]
        vloc = venue.get(team)
        med = p["median_pull_R"]
        timing = f"{fmt_t(med)}" if med and p["n_pulls"] >= 3 else "~4:19 (league)"
        flags = "; ".join(p["flags"]) or "none"
        opp = f" vs {opps[team]}" if team in opps else ""
        out.append(f"## {team}{opp} — {p['coach']}")
        out.append(f"**Expected pull tonight: {adj:.0%}**  (base {base:.0%}, band "
                   f"{p['band'][0]:.0%}-{p['band'][1]:.0%}; {why_adj})")
        out.append(f"- Record on clean 5v5 chances: {p['clear_taken']}/{p['clear_chances']}"
                   f" | last 3: {p.get('last3','-')} | typical pull time: {timing}")
        out.append(f"- Flags: {flags}")
        if vloc:
            out.append(f"- Context (NOT in the number): playing {vloc} (venue = measured noise); "
                       "lineup/goalie/B2B unknown — adjust in MANUAL if you know something")
        out.append("- Last 3 real chances:")
        for s in stories.get(p["coach"], [])[-3:][::-1]:
            out.append(f"    - {s}")
        out.append("")
    Path("morning_cards.md").write_text("\n".join(out))
    print("\n".join(out[:40]))
    print(f"\nwrote morning_cards.md ({len(teams)} teams)")

if __name__ == "__main__":
    main()
