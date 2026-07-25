"""Clean-window coach analysis (Seb directive 2026-07-25).

Hypothesis: some coaches pull ~100% of the time; their observed misses are
ruined windows (penalty inside the pull zone, gap closed first, arrived too
late), not decisions. Naive per-instance pull rates dilute intent.

Method — no fixed window needed for the core number:
For each gap-3 instance, PULLABLE seconds = open, pre-pull, full net, not
shorthanded, not delayed-penalty, not within 18s after a goal (dead time).
  q_i = 1 - exp(-sum of league hazard h(R) over pullable seconds)
      = probability a LEAGUE-AVERAGE coach pulls given the same real chance.
q_i ~ 0  -> no real chance existed (whatever the coach wanted).
q_i high -> a real chance existed; not pulling was a DECISION.

Per coach: observed pulls O vs sum(q) (league-expected), plus the discrete
ledger — clear chances (q >= thresholds) taken vs declined — and a reason
taxonomy for every no-pull instance.
Output: data/derived/clean_window_coach.json
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hockeycore.gap.extract import load_pbp
from hockeycore.fit.fit_curves import per_second_frame, state_of

LAKE = Path("/home/claude/work/nhl_lake")
DER = ROOT / "data" / "derived"
DEAD = 18
SEASONS = ("20242025", "20252026")

# league gap-3 hazard per second of R (EV_full bins; PP seconds get m_PP)
_f = json.load(open(DER / "fits.json"))
H = [0.0] * 1200
for r in _f["hazard"]["3"]["EV_full"]:
    v = r["h"] or 0.0
    for R in range(r["R_lo"], min(r["R_hi"], 1200)):
        H[R] = v
M_PP = _f["m_PP"]["3"]["m"]
H_FULL = sum(H)  # total zone hazard mass; frac = Hsum/H_FULL in [0,1]


def analyze():
    insts = [i for i in json.load(open(DER / "instances_gap3.json")) if i["season"] in SEASONS]
    frames = {}
    out = []
    for inst in insts:
        gid, season = inst["game_id"], inst["season"]
        if gid not in frames:
            frames[gid] = per_second_frame(load_pbp(LAKE / season / f"{gid}_pbp.json"))
        g, sits, dpw = frames[gid]
        trail_home = inst["trailing"] == g["home"]
        o, c = inst["opened_secs"], inst["closed_secs"]
        first_pull = inst["pull_segments"][0]["empty_from"] if inst["pull_segments"] else None
        pulled = inst["pulled"]
        goal_secs = [x["secs"] for x in inst["goals_in_window"]]

        Hsum = 0.0
        blocked = defaultdict(int)   # reason -> seconds (inside chance-relevant time)
        pullable_secs = 0
        end = min(c, first_pull) if first_pull is not None else c
        for u in range(max(o, 1), min(end, 1200)):
            R = min(1200 - u, 1199)
            dp = any(s <= u < e for s, e in dpw)
            st, tsk, lsk = state_of(sits[u], trail_home, dp)
            dead = any(gs <= u < gs + DEAD for gs in goal_secs)
            if st in ("EV_full", "TPP_full") and not dead and not dp:
                pullable_secs += 1
                Hsum += H[R] * (M_PP if st == "TPP_full" else 1.0)
            elif H[R] > 0:  # only count blockage where the league actually pulls
                if st == "TPK_full":
                    blocked["shorthanded"] += 1
                elif dp or st == "DP_off":
                    blocked["delayed_penalty"] += 1
                elif dead:
                    blocked["post_goal_dead"] += 1
                elif st.startswith("EN"):
                    blocked["net_already_empty"] += 1
                else:
                    blocked["other"] += 1
        q = 1 - math.exp(-Hsum)
        frac = Hsum / H_FULL

        # reason taxonomy for NO-pull instances with little/no real chance
        reason = None
        if not pulled:
            zone_start = 1200 - 420          # league hazard mass lives under ~7:00
            if frac >= 0.7:
                reason = "CLEAR DECLINE"
            elif frac >= 0.35:
                reason = "partial chance"
            elif c <= zone_start:
                reason = "closed before pull zone"
            elif o >= 1200 - 150:
                reason = "arrived too late (<2:30)"
            elif blocked.get("shorthanded", 0) >= 30:
                reason = "penalty-blocked in zone"
            elif blocked.get("delayed_penalty", 0) + blocked.get("post_goal_dead", 0) >= 20:
                reason = "DP/dead-time blocked"
            elif c < 1200 and any(abs(gs - c) <= 1 for gs in goal_secs):
                reason = "window cut by goal"
            else:
                reason = "short/thin window"

        out.append({
            "game_id": gid, "n": inst["n"], "season": season, "date": inst["date"],
            "coach": inst["trailing_coach"], "team": inst["trailing"],
            "opened_R": 1200 - o, "closed_R": 1200 - c,
            "pulled": pulled, "pull_R": (1200 - first_pull) if first_pull is not None else None,
            "pullable_secs": pullable_secs, "q": round(q, 4), "frac": round(frac, 3),
            "blocked": dict(blocked), "reason": reason,
        })
    return out


def main():
    rows = analyze()
    json.dump(rows, open(DER / "clean_window_instances.json", "w"))

    # ---- league headline
    nop = [r for r in rows if not r["pulled"]]
    pul = [r for r in rows if r["pulled"]]
    print(f"gap-3 instances (both seasons): {len(rows)}  pulled {len(pul)}  no-pull {len(nop)}")
    print(f"naive league pull rate: {len(pul)/len(rows):.1%}")
    reasons = defaultdict(int)
    for r in nop:
        reasons[r["reason"]] += 1
    print("\nno-pull instances by reason:")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {k:28s} {v:4d}  ({v/len(nop):.0%})")
    clear_all = [r for r in rows if r["pulled"] or r["frac"] >= 0.7]
    clear_pulled = [r for r in clear_all if r["pulled"]]
    declined = [r for r in nop if r["reason"] == "CLEAR DECLINE"]
    print(f"\nLEAGUE rate on CLEAR chances (pulled anywhere, or frac>=0.7 unpulled): "
          f"{len(clear_pulled)}/{len(clear_all)} = {len(clear_pulled)/len(clear_all):.1%}"
          f"   (vs naive {len(pul)/len(rows):.1%})")

    # ---- coach table
    co = defaultdict(lambda: {"n": 0, "O": 0, "sumq_nopull": 0.0,
                              "clear": 0, "clear_pulled": 0, "declines": [],
                              "ruined": 0})
    for r in rows:
        d = co[r["coach"]]
        d["n"] += 1
        if r["pulled"]:
            d["O"] += 1
            d["clear"] += 1          # a pull IS a taken chance
            d["clear_pulled"] += 1
        else:
            d["sumq_nopull"] += r["q"]
            if r["frac"] >= 0.7:
                d["clear"] += 1
                d["declines"].append({"date": r["date"], "team": r["team"],
                                      "q": r["q"], "game_id": r["game_id"]})
            elif r["frac"] < 0.35:
                d["ruined"] += 1

    table = []
    for coach, d in co.items():
        # clean rate: taken / (taken + clearly declined); Jeffreys interval
        k, n = d["clear_pulled"], d["clear"]
        if n:
            from statistics import NormalDist
            a, b = k + 0.5, n - k + 0.5
            # Jeffreys via normal approx on Beta mean/var (fine for reporting)
            mu = a / (a + b)
            sd = math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
            lo, hi = max(0, mu - 1.96 * sd), min(1, mu + 1.96 * sd)
        else:
            mu, lo, hi = None, None, None
        table.append({
            "coach": coach, "instances": d["n"], "pulls": d["O"],
            "naive_rate": round(d["O"] / d["n"], 3),
            "clear_chances": n, "clear_taken": k,
            "clean_rate": round(k / n, 3) if n else None,
            "ci": [round(lo, 3), round(hi, 3)] if n else None,
            "ruined_windows": d["ruined"],
            "league_expected_pulls_in_nopull": round(d["sumq_nopull"], 2),
            "declines": d["declines"],
        })
    table.sort(key=lambda x: (-(x["clean_rate"] or 0), -x["clear_chances"]))
    json.dump(table, open(DER / "clean_window_coach.json", "w"), indent=1)

    print(f"\n{'coach':24s} inst pulls naive  clear taken cleanrate      ruined")
    for t in table:
        if t["clear_chances"] == 0:
            continue
        print(f"{t['coach']:24s} {t['instances']:3d}  {t['pulls']:3d}  {t['naive_rate']:.0%}   "
              f"{t['clear_chances']:3d}  {t['clear_taken']:3d}   {t['clean_rate']:.0%} "
              f"[{t['ci'][0]:.0%}-{t['ci'][1]:.0%}]  {t['ruined_windows']:3d}")

    perfect = [t for t in table if t["clear_chances"] >= 4 and t["clean_rate"] == 1.0]
    print(f"\nNEAR-DETERMINISTIC candidates (>=4 clear chances, 100% taken): "
          f"{[t['coach'] for t in perfect]}")


if __name__ == "__main__":
    main()
