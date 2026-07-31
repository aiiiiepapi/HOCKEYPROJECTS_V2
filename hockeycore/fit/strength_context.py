"""Graded team-strength effect on pull behavior (Seb 2026-07-31: 'a -130 fav
isn't the same as a -300 fav'). Data-mining phase: no historical market lines
exist, so strength = results-based rating; tonight's real moneyline maps onto
the same win-prob scale at inference.

1) Results from boxscores -> exponentially-decayed win-share rating per team
   per date (half-life 40 games, cross-season carry).
2) Each clean 5v5 gap-3 chance gets the trailing team's pre-game log5 win
   probability vs that opponent.
3) League pull rate per strength bucket + within-coach controlled contrast.
Output: data/derived/strength_context.json
"""
import json, glob, math, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "data" / "derived"
LAKE = Path("/home/claude/work/nhl_lake")
HL_GAMES = 40.0

def build_results():
    res = []
    for season in ("20222023", "20232024", "20242025", "20252026"):
        for f in glob.glob(str(LAKE / season / "*_boxscore.json")):
            try:
                b = json.load(open(f, encoding="utf-8-sig"))
            except Exception:
                continue
            if b.get("gameState") not in ("OFF", "FINAL"):
                continue
            res.append({"date": b["gameDate"], "gid": b["id"],
                        "home": b["homeTeam"]["abbrev"], "away": b["awayTeam"]["abbrev"],
                        "hs": b["homeTeam"]["score"], "as": b["awayTeam"]["score"]})
    res.sort(key=lambda r: (r["date"], r["gid"]))
    return res

def ratings_before(res):
    """team -> list of (date, decayed win share BEFORE that game)."""
    hist = defaultdict(list)          # team -> list of (win_value)
    pre = {}                          # (gid, team) -> rating before game
    wsum = defaultdict(float); wn = defaultdict(float)
    for r in res:
        for team, won in ((r["home"], r["hs"] > r["as"]), (r["away"], r["as"] > r["hs"])):
            pre[(r["gid"], team)] = (wsum[team] / wn[team]) if wn[team] > 3 else 0.5
        d = 0.5 ** (1 / HL_GAMES)
        for team, won in ((r["home"], r["hs"] > r["as"]), (r["away"], r["as"] > r["hs"])):
            wsum[team] = wsum[team] * d + (1.0 if won else 0.0)
            wn[team] = wn[team] * d + 1.0
    return pre

def log5(a, b):
    a = min(max(a, 0.05), 0.95); b = min(max(b, 0.05), 0.95)
    return (a * (1 - b)) / (a * (1 - b) + b * (1 - a))

def main():
    res = build_results()
    pre = ratings_before(res)
    game_team = {}
    for r in res:
        game_team[r["gid"]] = r

    rows = json.load(open(DER / "clean_window_instances.json"))
    chances = []
    for r in rows:
        took = r["pulled"] and r["pull_type"] == "ev"
        dec = (not r["pulled"]) and r["frac_ev"] >= 0.7
        if not (took or dec):
            continue
        g = game_team.get(r["game_id"])
        if not g:
            continue
        opp = g["away"] if r["team"] == g["home"] else g["home"]
        pa = pre.get((r["game_id"], r["team"]), 0.5)
        pb = pre.get((r["game_id"], opp), 0.5)
        chances.append({"coach": r["coach"], "pulled": int(took),
                        "p_win": log5(pa, pb)})

    BUCKETS = [(-1.0, 0.40, "heavy dog (<40%)"), (0.40, 0.47, "dog (40-47%)"),
               (0.47, 0.53, "even (47-53%)"), (0.53, 0.60, "fav (53-60%)"),
               (0.60, 1.01, "heavy fav (>60%)")]
    out = {"buckets": []}
    print(f"clean 5v5 chances with ratings: {len(chances)}")
    print(f"{'bucket':22s}  pulls/chances  rate")
    for lo, hi, lbl in BUCKETS:
        sub = [c for c in chances if lo <= c["p_win"] < hi]
        k = sum(c["pulled"] for c in sub)
        rate = k / len(sub) if sub else None
        out["buckets"].append({"label": lbl, "lo": lo, "hi": hi, "n": len(sub),
                               "pulls": k, "rate": rate})
        print(f"{lbl:22s}  {k:3d}/{len(sub):3d}       {rate:.0%}" if sub else f"{lbl}: empty")

    # within-coach control: precision-weighted contrast, favorites vs dogs
    bycoach = defaultdict(lambda: {"f": [0, 0], "d": [0, 0]})
    for c in chances:
        if c["p_win"] >= 0.53: key = "f"
        elif c["p_win"] < 0.47: key = "d"
        else: continue
        bycoach[c["coach"]][key][0] += c["pulled"]
        bycoach[c["coach"]][key][1] += 1
    wf = wd = den = 0.0; nb = 0
    for d in bycoach.values():
        kf, nf = d["f"]; kd, nd = d["d"]
        if nf == 0 or nd == 0:
            continue
        nb += 1
        w = 1 / (1 / nf + 1 / nd)
        wf += w * (kf / nf); wd += w * (kd / nd); den += w
    if den:
        out["within_coach"] = {"n_coaches": nb, "fav_rate": round(wf / den, 3),
                               "dog_rate": round(wd / den, 3)}
        print(f"\nwithin-coach ({nb} coaches with both): favorites {wf/den:.0%} vs dogs {wd/den:.0%} "
              f"-> diff {100*(wf-wd)/den:+.1f}pts")
    # graded check inside favorites: slight vs heavy
    for lo, hi, lbl in [(0.53, 0.60, "slight fav"), (0.60, 1.01, "heavy fav")]:
        sub = [c for c in chances if lo <= c["p_win"] < hi]
        if sub:
            print(f"graded: {lbl} {sum(c['pulled'] for c in sub)}/{len(sub)} = "
                  f"{sum(c['pulled'] for c in sub)/len(sub):.0%}")
    json.dump(out, open(DER / "strength_context.json", "w"), indent=1)

if __name__ == "__main__":
    main()
