"""
Walk-forward backtest: fit 2024-25 → price 2025-26 blind.
Outcomes recomputed from RAW pbp goal events (rule 0), full chain to horn.

COACH LAW (production, adopted 2026-08-01, ruling 23, Seb ratified): DENSITY-
PRESERVING — price with mc_pricer.coach_hazard_array(P_c), P_c = clean-window
Beta+recency posterior computed LEAK-FREE from chances before 2025-09-01.
Pull probability hits the coach's number, league timing shape preserved
(timing ruling 14). Replaces raw-EB multipliers + 0.355 attenuation: pooled
cross-season persistence of P_c is 0.99 [0.42..1.50] -> no extra blend; the
attenuation was a patch for the retired raw-EB estimator (persistence 0.36).
"""
import json, sys, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import hockeycore.pricing.mc_pricer as MP
from hockeycore.gap.extract import load_pbp, game_frame
from hockeycore.fit.fit_curves import per_second_frame

DER = ROOT / "data" / "derived"
LAKE = Path("/home/claude/work/nhl_lake")
CHECKPOINTS = [900, 780, 660, 600, 480, 360, 300, 240, 180]

# ---- rewire pricer to 24-25 fits
_f = json.load(open(DER / "fits_2425.json"))
MP.rebuild(_f)
# 24-25 return hazard
insts_2425 = [i for i in json.load(open(DER / "instances_gap3.json")) if i["season"] == "20242025"]
re_ev = 0; ps = 0
for i in insts_2425:
    gs = {g["secs"] for g in i["goals_in_window"]}
    for s in i["pull_segments"]:
        ps += max(s["empty_until"] - s["empty_from"], 1)
        if s["empty_until"] < i["closed_secs"] and s["empty_until"] not in gs:
            re_ev += 1
MP._ret = re_ev / ps
print(f"pricer rewired to 24-25 fits (return hazard {MP._ret:.5f})")

# ---- leak-free coach P_c (Beta+recency, chances < cutoff only) --------------
from collections import defaultdict
CUTOFF = "2025-09-01"
HL = 10.0
_cw = [r for r in json.load(open(DER / "clean_window_instances.json")) if r["date"] < CUTOFF]
_seqs = defaultdict(list)
for _r in sorted(_cw, key=lambda x: x["date"]):
    _took = _r["pulled"] and _r["pull_type"] == "ev"
    if _took or ((not _took) and _r["frac_ev"] >= 0.7):
        _seqs[_r["coach"]].append(1 if _took else 0)
from hockeycore.fit.prior_fit import fit_prior as _fit_prior
_A, _B, _mu, _st = _fit_prior(list(_seqs.values()))

def p_coach(name):
    s = _seqs.get(name, [])
    kw = sum(x * 0.5 ** ((len(s) - 1 - i) / HL) for i, x in enumerate(s))
    nw = sum(0.5 ** ((len(s) - 1 - i) / HL) for i in range(len(s)))
    return (kw + _A) / (nw + _A + _B)

_haz_cache = {}
def _haz_for(pi):
    key = round(min(max(pi, 0.05), 0.95), 2)
    if key not in _haz_cache:
        _haz_cache[key] = MP.coach_hazard_array(key)
    return _haz_cache[key]

_cache = {}
def cached_price(R, pulled, strength, pi):
    key = (R, pulled, strength, round(min(max(pi, 0.05), 0.95), 2))
    if key not in _cache:
        _cache[key] = MP.price(R, pulled0=pulled, strength0=strength, m_coach=1.0,
                               n=20000, seed=13, haz3_override=_haz_for(pi))
    return _cache[key]

def outcomes_from_raw(gid, t_cp, leader_is_home, entry, p3goals):
    lead = trail = 0
    a, h = entry
    for gl in p3goals:
        if gl["t"] > t_cp:
            home_scored = gl["details"]["homeScore"] > h
            if home_scored == leader_is_home: lead += 1
            else: trail += 1
        a, h = gl["details"]["awayScore"], gl["details"]["homeScore"]
    # final margin from last known scores (or entry if no goals)
    fa, fh = (p3goals[-1]["details"]["awayScore"], p3goals[-1]["details"]["homeScore"]) if p3goals else entry
    margin = (fh - fa) if leader_is_home else (fa - fh)
    return {"lead": lead, "trail": trail, "total": lead + trail, "final_margin": margin}

def main():
    insts = [i for i in json.load(open(DER / "instances_gap3.json")) if i["season"] == "20252026"]
    frames = {}
    rows = []
    for inst in insts:
        gid = inst["game_id"]
        if gid not in frames:
            pbp = load_pbp(LAKE / "20252026" / f"{gid}_pbp.json")
            g, sits, dpw = per_second_frame(pbp)
            p3goals = [e for e in g["events"] if e["type"] == "goal"]
            frames[gid] = (g, sits, p3goals)
        g, sits, p3goals = frames[gid]
        trail_home = inst["trailing"] == g["home"]
        segs = inst["pull_segments"]
        for R in CHECKPOINTS:
            t_cp = 1200 - R
            if not (inst["opened_secs"] <= t_cp < inst["closed_secs"]):
                continue
            pulled = any(s["empty_from"] <= t_cp < s["empty_until"] for s in segs)
            sit = sits[t_cp]
            tsk = int(sit[2] if trail_home else sit[1]); lsk = int(sit[1] if trail_home else sit[2])
            strength = "T_PP" if tsk > lsk and not pulled else ("T_PK" if tsk < lsk else "EV")
            if pulled: strength = "EV"  # pulled cells priced at EN of current diff; keep EV entry
            pi = p_coach(inst["trailing_coach"])
            new_coach = inst["trailing_coach"] not in _seqs
            p = cached_price(R, pulled, strength, pi)
            pb = cached_price(R, pulled, strength, _mu)  # coach-blind pseudo-market
            out = outcomes_from_raw(gid, t_cp, not trail_home, g["p3_entry"], p3goals)
            rows.append({
                "game_id": gid, "inst": inst["n"], "R": R, "pulled": pulled,
                "strength": strength, "coach": inst["trailing_coach"], "m": round(pi, 3),
                "new_coach": new_coach,
                "p_total1": p["P_total_ge1"], "p_total2": p["P_total_ge2"],
                "p_lead1": p["P_leader_ge1"], "p_marg4": p["P_margin_ge4"],
                "pb_total1": pb["P_total_ge1"], "pb_lead1": pb["P_leader_ge1"], "pb_marg4": pb["P_margin_ge4"],
                "y_total1": int(out["total"] >= 1), "y_total2": int(out["total"] >= 2),
                "y_lead1": int(out["lead"] >= 1), "y_marg4": int(out["final_margin"] >= 4),
            })
    json.dump(rows, open(DER / "backtest_rows.json", "w"))
    print(f"priced {len(rows)} checkpoint-observations from {len(insts)} instances; cache cells: {len(_cache)}")

if __name__ == "__main__":
    main()
