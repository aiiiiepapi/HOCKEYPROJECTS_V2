"""
backtest_density.py — DENSITY-PRESERVING coach law, walk-forward validation.\nScales pull density to hit the coach's P_c with league timing shape preserved.

Candidate production law (2026-08-01): replace {raw-EB multiplier m_raw,
attenuation 1+0.355(m_raw-1)} with a SURVIVAL-MAPPED multiplier derived from
the clean-window Beta-posterior estimator:

    k_coach = ln(1 - P_coach) / ln(1 - P_league)

Scaling a hazard curve by k maps window survival S -> S^k for ANY window, so
k_coach is the unique window-independent multiplier that reproduces the
coach's expected clean-chance pull probability while preserving the league
timing shape. Shrinkage lives in P_coach (league Beta prior + recency decay),
not in an ad-hoc attenuation — determinists stop being crushed (P=0.85 ->
k~2.4 instead of attenuated ~1.5).

LEAK-FREE: P_coach and P_league computed ONLY from chances dated before
2025-09-01 (prior refit MoM on the same subset); prices 2025-26 blind.
Everything else identical to backtest.py. Writes backtest_rows_density.json.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import hockeycore.pricing.mc_pricer as MP                     # noqa: E402
from hockeycore.gap.extract import load_pbp                   # noqa: E402
from hockeycore.fit.fit_curves import per_second_frame        # noqa: E402

DER = ROOT / "data" / "derived"
LAKE = Path("/home/claude/work/nhl_lake")
CHECKPOINTS = [900, 780, 660, 600, 480, 360, 300, 240, 180]
CUTOFF = "2025-09-01"
HL = 10.0

# ---- pricer rewired to 24-25 fits (identical to backtest.py) ----------------
_f = json.load(open(DER / "fits_2425.json"))
MP.rebuild(_f)
insts_2425 = [i for i in json.load(open(DER / "instances_gap3.json")) if i["season"] == "20242025"]
re_ev = 0
ps = 0
for i in insts_2425:
    gs = {g["secs"] for g in i["goals_in_window"]}
    for s in i["pull_segments"]:
        ps += max(s["empty_until"] - s["empty_from"], 1)
        if s["empty_until"] < i["closed_secs"] and s["empty_until"] not in gs:
            re_ev += 1
MP._ret = re_ev / ps
print(f"pricer rewired to 24-25 fits (return hazard {MP._ret:.5f})")

# ---- leak-free coach P estimates as of end 24-25 -----------------------------
cw = [r for r in json.load(open(DER / "clean_window_instances.json"))
      if r["date"] < CUTOFF]
seqs = defaultdict(list)
for r in sorted(cw, key=lambda x: x["date"]):
    took = r["pulled"] and r["pull_type"] == "ev"
    declined = (not took) and r["frac_ev"] >= 0.7
    if took or declined:
        seqs[r["coach"]].append(1 if took else 0)

# prior: MoM on pre-cutoff coach spread (mirrors fit of pull_prior.json)
rates = [(sum(s) / len(s), len(s)) for s in seqs.values() if len(s) >= 8]
w = sum(n for _, n in rates)
mu = sum(rw * n for rw, n in rates) / w
var = sum(n * (rw - mu) ** 2 for rw, n in rates) / w
var = max(var - mu * (1 - mu) / (w / len(rates)), 1e-4)
strength = max(min(mu * (1 - mu) / var - 1, 40.0), 1.0)
A, B = mu * strength, (1 - mu) * strength
P_LEAGUE = sum(sum(s) for s in seqs.values()) / sum(len(s) for s in seqs.values())
LOG_S_LEAGUE = math.log(1.0 - P_LEAGUE)
print(f"leak-free prior: a={A:.2f} b={B:.2f} (mu={mu:.3f}, strength={strength:.1f}); "
      f"league clean take-rate P̄={P_LEAGUE:.3f}")


def p_coach(name):
    s = seqs.get(name, [])
    kw = sum(x * 0.5 ** ((len(s) - 1 - i) / HL) for i, x in enumerate(s))
    nw = sum(0.5 ** ((len(s) - 1 - i) / HL) for i in range(len(s)))
    return (kw + A) / (nw + A + B)


_haz_cache = {}


def haz_for(pi):
    key = round(pi, 2)
    if key not in _haz_cache:
        _haz_cache[key] = MP.coach_hazard_array(key)
    return _haz_cache[key]


_cache = {}


def cached_price(R, pulled, strength, pi):
    key = (R, pulled, strength, round(pi, 2))
    if key not in _cache:
        _cache[key] = MP.price(R, pulled0=pulled, strength0=strength, m_coach=1.0,
                               n=20000, seed=13, coach_shift=0,
                               haz3_override=haz_for(pi))
    return _cache[key]


def outcomes_from_raw(t_cp, leader_is_home, entry, p3goals):
    lead = trail = 0
    a, h = entry
    for gl in p3goals:
        if gl["t"] > t_cp:
            home_scored = gl["details"]["homeScore"] > h
            if home_scored == leader_is_home:
                lead += 1
            else:
                trail += 1
        a, h = gl["details"]["awayScore"], gl["details"]["homeScore"]
    fa, fh = (p3goals[-1]["details"]["awayScore"], p3goals[-1]["details"]["homeScore"]) \
        if p3goals else entry
    margin = (fh - fa) if leader_is_home else (fa - fh)
    return {"lead": lead, "trail": trail, "total": lead + trail, "final_margin": margin}


def main():
    insts = [i for i in json.load(open(DER / "instances_gap3.json"))
             if i["season"] == "20252026"]
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
        km = min(max(p_coach(inst["trailing_coach"]), 0.05), 0.95)  # pi target
        for R in CHECKPOINTS:
            t_cp = 1200 - R
            if not (inst["opened_secs"] <= t_cp < inst["closed_secs"]):
                continue
            pulled = any(s["empty_from"] <= t_cp < s["empty_until"] for s in segs)
            sit = sits[t_cp]
            tsk = int(sit[2] if trail_home else sit[1])
            lsk = int(sit[1] if trail_home else sit[2])
            strength = "T_PP" if tsk > lsk and not pulled else ("T_PK" if tsk < lsk else "EV")
            if pulled:
                strength = "EV"
            p = cached_price(R, pulled, strength, km)
            out = outcomes_from_raw(t_cp, not trail_home, g["p3_entry"], p3goals)
            rows.append({
                "game_id": gid, "inst": inst["n"], "R": R, "pulled": pulled,
                "strength": strength, "coach": inst["trailing_coach"], "m": round(km, 2),
                "p_coach_est": round(p_coach(inst["trailing_coach"]), 3),
                "p_total1": p["P_total_ge1"], "p_total2": p["P_total_ge2"],
                "p_lead1": p["P_leader_ge1"], "p_marg4": p["P_margin_ge4"],
                "y_total1": int(out["total"] >= 1), "y_total2": int(out["total"] >= 2),
                "y_lead1": int(out["lead"] >= 1), "y_marg4": int(out["final_margin"] >= 4),
            })
    json.dump(rows, open(DER / "backtest_rows_density.json", "w"))
    print(f"priced {len(rows)} rows; cache cells: {len(_cache)}")

    # side-by-side calibration vs the current-law rows
    base_rows = json.load(open(DER / "backtest_rows.json"))
    for label, rr in (("CURRENT (0.355 attenuation)", base_rows),
                      ("DENSITY-PRESERVING (pi-law)", rows)):
        print(f"\n== {label} ==")
        n = len(rr)
        for pk, yk in [("p_lead1", "y_lead1"), ("p_total1", "y_total1"),
                       ("p_total2", "y_total2"), ("p_marg4", "y_marg4")]:
            rs = sorted(rr, key=lambda r: r[pk])
            bias = sum(r[yk] - r[pk] for r in rs) / n
            base = sum(r[yk] for r in rs) / n
            brier = sum((r[pk] - r[yk]) ** 2 for r in rs) / n
            skill = 1 - brier / (base * (1 - base))
            bad = 0
            det = []
            for b in range(10):
                ch = rs[b * n // 10:(b + 1) * n // 10]
                mp_ = sum(r[pk] for r in ch) / len(ch)
                ay = sum(r[yk] for r in ch) / len(ch)
                se = math.sqrt(max(mp_ * (1 - mp_), 1e-9) / len(ch))
                z = (ay - mp_) / se
                det.append(f"{z:+.1f}")
                bad += abs(z) >= 2
            print(f"  {pk:9} bias {bias:+.4f}  skill {skill:+.3f}  bad {bad}/10  z: {' '.join(det)}")


if __name__ == "__main__":
    main()
