"""PP-pull behavior per coach (Seb directive 2026-07-25).

'Some teams only pull on PP' — test it. For every gap-3 instance, split
pre-pull pullable exposure into EV seconds and PP seconds (hazard-mass
weighted, same H(R) as clean_window). Per coach:
  E_ev / E_pp   = league-expected pulls from his EV / PP exposure
  O_ev / O_pp   = his observed pulls by classification (pull vs pp_pull)
League m_PP cross-check + per-coach PP skew with exact-ish binomial test:
under his own overall pull intensity, is his PP share of pulls higher than
his PP share of expected pulls?
Output: data/derived/pp_pull_coach.json
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
SEASONS = ("20222023", "20232024", "20242025", "20252026")
OLD = ("20222023", "20232024")

def _load_H(path):
    f = json.load(open(path))
    h = [0.0] * 1200
    for r in f["hazard"]["3"]["EV_full"]:
        v = r["h"] or 0.0
        for R in range(r["R_lo"], min(r["R_hi"], 1200)):
            h[R] = v
    return h, f["m_PP"]["3"]["m"]

H, M_PP = _load_H(DER / "fits.json")            # new-era hazard (24-26)
H_OLD, M_PP_OLD = _load_H(DER / "fits_old2.json")  # old-era hazard (22-24)


def main():
    insts = [i for i in json.load(open(DER / "instances_gap3.json")) if i["season"] in SEASONS]
    frames = {}
    co = defaultdict(lambda: {"E_ev": 0.0, "E_pp": 0.0, "O_ev": 0, "O_pp": 0,
                              "pp_secs": 0, "ev_secs": 0, "pp_pull_Rs": [], "ev_pull_Rs": []})
    for inst in insts:
        gid, season = inst["game_id"], inst["season"]
        if gid not in frames:
            frames[gid] = per_second_frame(load_pbp(LAKE / season / f"{gid}_pbp.json"))
        g, sits, dpw = frames[gid]
        Hx, Mx = (H_OLD, M_PP_OLD) if season in OLD else (H, M_PP)
        trail_home = inst["trailing"] == g["home"]
        o, c = inst["opened_secs"], inst["closed_secs"]
        first_pull = inst["pull_segments"][0]["empty_from"] if inst["pull_segments"] else None
        goal_secs = [x["secs"] for x in inst["goals_in_window"]]
        d = co[inst["trailing_coach"]]
        end = min(c, first_pull) if first_pull is not None else c
        for u in range(max(o, 1), min(end, 1200)):
            R = min(1200 - u, 1199)
            dp = any(s <= u < e for s, e in dpw)
            st, _, _ = state_of(sits[u], trail_home, dp)
            dead = any(gs <= u < gs + DEAD for gs in goal_secs)
            if dead or dp:
                continue
            if st == "EV_full":
                d["E_ev"] += Hx[R]; d["ev_secs"] += 1
            elif st == "TPP_full":
                d["E_pp"] += Hx[R] * Mx; d["pp_secs"] += 1
        if inst["pulled"]:
            R_pull = 1200 - first_pull if first_pull is not None else None
            if inst["pull_classification"] == "pp_pull":
                d["O_pp"] += 1
                if R_pull: d["pp_pull_Rs"].append(R_pull)
            else:
                d["O_ev"] += 1
                if R_pull: d["ev_pull_Rs"].append(R_pull)

    # league totals
    LE_ev = sum(d["E_ev"] for d in co.values()); LE_pp = sum(d["E_pp"] for d in co.values())
    LO_ev = sum(d["O_ev"] for d in co.values()); LO_pp = sum(d["O_pp"] for d in co.values())
    print(f"league: EV pulls {LO_ev} (expected {LE_ev:.1f}) | PP pulls {LO_pp} (expected {LE_pp:.1f})")
    print(f"implied m_PP re-check: {(LO_pp/LE_pp)/(LO_ev/LE_ev):.2f} x (fitted m_PP {M_PP:.2f} already inside E_pp)")
    all_pp = sorted([r for d in co.values() for r in d["pp_pull_Rs"]], reverse=True)
    all_ev = sorted([r for d in co.values() for r in d["ev_pull_Rs"]], reverse=True)
    if all_pp and all_ev:
        print(f"pull timing: PP pulls median R={all_pp[len(all_pp)//2]}s | EV pulls median R={all_ev[len(all_ev)//2]}s")

    def binom_p_ge(k, n, p):
        return sum(math.comb(n, j) * p**j * (1-p)**(n-j) for j in range(k, n + 1))

    table = []
    for coach, d in co.items():
        n = d["O_ev"] + d["O_pp"]
        if n == 0 and d["E_pp"] < 0.2:
            continue
        p_pp_expected = d["E_pp"] / (d["E_ev"] + d["E_pp"]) if (d["E_ev"] + d["E_pp"]) else 0
        p_skew = binom_p_ge(d["O_pp"], n, p_pp_expected) if n else None
        table.append({
            "coach": coach, "pulls_ev": d["O_ev"], "pulls_pp": d["O_pp"],
            "pp_share_of_pulls": round(d["O_pp"] / n, 2) if n else None,
            "pp_share_expected": round(p_pp_expected, 2),
            "pp_exposure_secs": d["pp_secs"], "ev_exposure_secs": d["ev_secs"],
            "p_value_pp_skew": round(p_skew, 3) if p_skew is not None else None,
            "pp_only": d["O_pp"] >= 2 and d["O_ev"] == 0,
        })
    table.sort(key=lambda t: (-(t["pp_share_of_pulls"] or 0), -(t["pulls_pp"])))
    json.dump(table, open(DER / "pp_pull_coach.json", "w"), indent=1)

    print(f"\n{'coach':22s} EVpull PPpull share expect  p-skew  flags")
    for t in table:
        if (t["pulls_ev"] + t["pulls_pp"]) == 0:
            continue
        fl = "PP-ONLY" if t["pp_only"] else ""
        print(f"{t['coach']:22s}  {t['pulls_ev']:3d}   {t['pulls_pp']:3d}   "
              f"{t['pp_share_of_pulls']:.0%}   {t['pp_share_expected']:.0%}   "
              f"{t['p_value_pp_skew']:.3f}  {fl}")


if __name__ == "__main__":
    main()
