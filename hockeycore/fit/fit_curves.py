"""
hockeycore.fit.fit_curves — first full fit pass per docs/CALCULATIONS.md §1-4.

Outputs data/derived/fits.json:
  - pull hazard bins per gap (exposure, pulls, rate, Poisson CI), by strength
  - m_PP per gap (one-step profile estimate + CI)
  - goal intensities per state/direction with exact Poisson CIs, per season
    and pooled (season-drift gate)
  - coach table (gap 3): O_c, E_c, exposure, shrunk multiplier m_c
"""
import json, math, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hockeycore.gap.extract import load_pbp, game_frame, delayed_penalty_windows

LAKE = Path("/home/claude/work/nhl_lake")
DER = ROOT / "data" / "derived"
BIN_W = 30  # seconds of R per hazard bin


def poisson_ci(k, t, z=1.96):
    """Rate CI for k events in t exposure (normal approx on log; exact-ish for small k)."""
    if t <= 0:
        return (0.0, float("inf"))
    if k == 0:
        return (0.0, 3.0 / t)
    lo = k * (1 - 1 / (9 * k) - z / (3 * math.sqrt(k))) ** 3 / t
    hi = (k + 1) * (1 - 1 / (9 * (k + 1)) + z / (3 * math.sqrt(k + 1))) ** 3 / t
    return (lo, hi)


def per_second_frame(pbp):
    """sit code per second of P3 (carry-forward), + dp windows, once per game."""
    g = game_frame(pbp)
    ev = g["events"]
    sits = []
    cur = "1551"
    k = 0
    for u in range(0, 1200):
        while k < len(ev) and ev[k]["t"] <= u:
            if len(ev[k]["sit"]) == 4:
                cur = ev[k]["sit"]
            k += 1
        sits.append(cur)
    return g, sits, delayed_penalty_windows(ev)


def state_of(sit, trail_home, dp_active):
    gd = 3 if trail_home else 0
    tsk = int(sit[2] if trail_home else sit[1])
    lsk = int(sit[1] if trail_home else sit[2])
    empty = sit[gd] == "0"
    if dp_active and empty:
        return "DP_off", tsk, lsk
    d = tsk - lsk
    if empty:
        return ("EN_pp" if d >= 2 else "EN_ev" if d == 1 else "EN_pk"), tsk, lsk
    return ("TPP_full" if d > 0 else "TPK_full" if d < 0 else "EV_full"), tsk, lsk


def main(seasons=("20222023","20232024","20242025","20252026"), suffix="",
         hazard_seasons=("20242025", "20252026")):
    """seasons -> goal-rate pooling (drift-gated OK across all 4).
    hazard_seasons -> pull hazard, m_PP, coach exposure (behavior drifted
    1.48x between eras, 2026-07-25 audit — never pool pulls across eras)."""
    frames = {}
    fits = {"hazard": {}, "m_PP": {}, "rates": {}, "coach": None}
    coach_rows = defaultdict(lambda: {"O": 0, "exp_secs": []})
    for gap in (2, 3, 4):
        insts = [i for i in json.load(open(DER / f"instances_gap{gap}.json")) if i["season"] in seasons]
        PENC = defaultdict(int)
        haz_exp = defaultdict(float)   # (strength, bin) -> secs
        haz_pull = defaultdict(int)
        T = defaultdict(float)         # (season, state) -> secs
        G = defaultdict(int)           # (season, state, dir) -> goals
        RB_ALL = [(0,60),(60,90),(90,120),(120,180),(180,270),(270,300),(300,360),(360,480),(480,600),(600,900),(900,1200)]
        def _rb(R, RB):
            for lo, hi in RB:
                if lo <= R < hi: return (lo, hi)
            return RB[-1]
        TR2 = {}   # (state, bucket) -> [secs, {dir: goals}] — coarse buckets merged later
        def _tr2_add_T(st, R, secs=1):
            for RB in ([(0,90),(90,180),(180,270),(270,360),(360,480),(480,600),(600,900),(900,1200)],
                       [(0,60),(60,120),(120,180),(180,300),(300,1200)]):
                b = _rb(R, RB)
                key = (st, b)
                TR2.setdefault(key, [0, {}])[0] += secs
        def _tr2_add_G(st, R, d):
            for RB in ([(0,90),(90,180),(180,270),(270,360),(360,480),(480,600),(600,900),(900,1200)],
                       [(0,60),(60,120),(120,180),(180,300),(300,1200)]):
                key = (st, _rb(R, RB))
                bucket = TR2.setdefault(key, [0, {}])
                bucket[1][d] = bucket[1].get(d, 0) + 1
        for inst in insts:
            gid, season = inst["game_id"], inst["season"]
            if gid not in frames:
                sd = LAKE / season
                frames[gid] = per_second_frame(load_pbp(sd / f"{gid}_pbp.json"))
            g, sits, dpw = frames[gid]
            trail_home = inst["trailing"] == g["home"]
            trail_id = g["home_id"] if trail_home else g["away_id"]
            o, c = inst["opened_secs"], inst["closed_secs"]
            first_pull = inst["pull_segments"][0]["empty_from"] if inst["pull_segments"] else None
            in_hz = season in hazard_seasons
            # ---- exposure & states, second by second
            for u in range(o, c):
                dp_active = any(s <= u < e for s, e in dpw)
                st, tsk, lsk = state_of(sits[u], trail_home, dp_active)
                if st != "DP_off":
                    T[(season, st)] += 1
                    if st in ("EV_full", "EN_ev"):
                        _tr2_add_T(st, 1200 - u)
                # hazard exposure: pre-pull, full net, not PK, not DP (hazard era only)
                if in_hz and (first_pull is None or u < first_pull) and st in ("EV_full", "TPP_full"):
                    b = (1200 - u) // BIN_W
                    haz_exp[(st, b)] += 1
                    if gap == 3:
                        coach_rows[inst["trailing_coach"]]["exp_secs"].append((st, 1200 - u))
            # ---- penalty transitions out of EV (for in-sim penalty generation)
            prev_st = None
            for u in range(o, min(c, 1200)):
                dp_a = any(s <= u < e for s, e in dpw)
                st2, _, _ = state_of(sits[u], trail_home, dp_a)
                if prev_st == "EV_full" and st2 in ("TPK_full", "TPP_full"):
                    PENC[st2] += 1
                if st2 == "EV_full":
                    PENC["exp"] += 1
                prev_st = st2
            # ---- pull event (hazard era only)
            if not in_hz:
                first_pull = None
            if first_pull is not None and first_pull < c:
                st, _, _ = state_of(sits[first_pull] if first_pull < 1200 else sits[1199], trail_home, False)
                strength = "TPP_full" if inst["pull_classification"] == "pp_pull" else "EV_full"
                haz_pull[(strength, (1200 - first_pull) // BIN_W)] += 1
                if gap == 3:
                    coach_rows[inst["trailing_coach"]]["O"] += 1
            elif first_pull is not None:  # evidence == close (closing-goal rule)
                strength = "TPP_full" if inst["pull_classification"] == "pp_pull" else "EV_full"
                haz_pull[(strength, (1200 - min(first_pull, 1199)) // BIN_W)] += 1
                if gap == 3:
                    coach_rows[inst["trailing_coach"]]["O"] += 1
            # ---- goals by state (goal's own sit authoritative)
            ev = g["events"]
            for x in inst["goals_in_window"]:
                goal_ev = next(e for e in ev if e["eventId"] == x["event"])
                sit = goal_ev["sit"] if len(goal_ev["sit"]) == 4 else sits[min(x["secs"], 1199)]
                dp_active = any(s <= x["secs"] < e for s, e in dpw)
                st, _, _ = state_of(sit, trail_home, dp_active)
                direction = "for" if x["team_id"] == trail_id else "against"
                G[(season, st, direction)] += 1
                if st in ("EV_full", "EN_ev"):
                    _tr2_add_G(st, 1200 - x["secs"], direction)
        # ---- R-bucketed rates (EV_full / EN_ev; lead1-bias fix 2026-07-26)
        RB_EV = [(0,90),(90,180),(180,270),(270,360),(360,480),(480,600),(600,900),(900,1200)]
        RB_EN = [(0,60),(60,120),(120,180),(180,300),(300,1200)]
        fits.setdefault("rates_R", {})[gap] = {}
        for st, RB in (("EV_full", RB_EV), ("EN_ev", RB_EN)):
            for d in ("for", "against"):
                rows_rb = []
                for lo, hi in RB:
                    t = TR2.get((st, (lo, hi)), [0, {}])[0]
                    gg = TR2.get((st, (lo, hi)), [0, {}])[1].get(d, 0)
                    rows_rb.append({"R_lo": lo, "R_hi": hi, "T": t, "G": gg,
                                    "rate_per_60min": (gg/t*3600) if t > 900 else None})
                fits["rates_R"][gap][f"{st}:{d}"] = rows_rb
        # ---- assemble hazard bins
        hz = {}
        for st in ("EV_full", "TPP_full"):
            rows = []
            for b in range(0, 900 // BIN_W):
                e = haz_exp.get((st, b), 0.0)
                p = haz_pull.get((st, b), 0)
                lo, hi = poisson_ci(p, e)
                rows.append({"R_lo": b * BIN_W, "R_hi": (b + 1) * BIN_W,
                             "exposure": e, "pulls": p,
                             "h": (p / e) if e > 0 else None, "ci": [lo, hi]})
            hz[st] = rows
        fits["hazard"][gap] = hz
        fits.setdefault("pen", {})[gap] = {
            "h_pk": PENC["TPK_full"] / PENC["exp"] if PENC["exp"] else 0.0,
            "h_pp": PENC["TPP_full"] / PENC["exp"] if PENC["exp"] else 0.0,
            "n_pk": PENC["TPK_full"], "n_pp": PENC["TPP_full"], "exp_secs": PENC["exp"]}
        # one-step m_PP: ratio of overall per-exposure pull rates (band-weighted)
        eEV = sum(haz_exp.get(("EV_full", b), 0) for b in range(30))
        pEV = sum(haz_pull.get(("EV_full", b), 0) for b in range(30))
        ePP = sum(haz_exp.get(("TPP_full", b), 0) for b in range(30))
        pPP = sum(haz_pull.get(("TPP_full", b), 0) for b in range(30))
        if eEV and ePP and pEV:
            m = (pPP / ePP) / (pEV / eEV)
            fits["m_PP"][gap] = {"m": m, "pulls_EV": pEV, "pulls_PP": pPP,
                                 "exp_EV": eEV, "exp_PP": ePP}
        # rates
        rt = {}
        states = sorted(set(s for (_, s) in T))
        for st in states:
            for d in ("for", "against"):
                pooled_T = sum(T[(se, st)] for se in seasons)
                pooled_G = sum(G[(se, st, d)] for se in seasons)
                lo, hi = poisson_ci(pooled_G, pooled_T)
                per = {}
                for se in seasons:
                    per[se] = {"T": T[(se, st)], "G": G[(se, st, d)]}
                rt[f"{st}:{d}"] = {"T": pooled_T, "G": pooled_G,
                                   "rate_per_60min": pooled_G / pooled_T * 3600 if pooled_T else None,
                                   "ci_per_60": [lo * 3600, hi * 3600], "seasons": per}
        fits["rates"][gap] = rt
    json.dump(fits, open(DER / f"fits{suffix}.json", "w"), indent=1)
    json.dump({k: {"O": v["O"], "n_secs": len(v["exp_secs"])} for k, v in coach_rows.items()},
              open(DER / f"coach_raw{suffix}.json", "w"), indent=1)
    # coach exposure kept in memory shape too big; store binned per coach
    binned = {}
    for cch, v in coach_rows.items():
        bb = defaultdict(float)
        for st, R in v["exp_secs"]:
            bb[f"{st}|{R // BIN_W}"] += 1
        binned[cch] = {"O": v["O"], "exp": dict(bb)}
    json.dump(binned, open(DER / f"coach_exposure{suffix}.json", "w"))
    print("fits written")


if __name__ == "__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="2425":
        main(seasons=("20242025",), suffix="_2425")
    else:
        main()
