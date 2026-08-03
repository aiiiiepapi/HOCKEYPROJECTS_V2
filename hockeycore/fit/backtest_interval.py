"""
backtest_interval.py — blind walk-forward for AHL / Liiga.

Fit on training seasons (fits_{league}_train) -> price the newest season's
gap-3 checkpoints blind with the density coach law (ruling 23): each coach at
his leak-free clean-window P_c (chances < 2025-09-01 only), league timing.
Outcomes recomputed from the raw game dicts (rule 0), P3 chain to horn.

Writes data/derived/backtest_rows_{league}.json and prints calibration + ROI
at the +10%-EV line (game-clustered bootstrap).
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import hockeycore.pricing.mc_pricer as MP                          # noqa: E402
from hockeycore.leagues import ahl as ahl_mod, liiga as liiga_mod, mestis as mestis_mod  # noqa: E402

DER = ROOT / "data" / "derived"
CHECKPOINTS = [900, 780, 660, 600, 480, 360, 300, 240, 180]
CUTOFF = "2025-09-01"
HL = 10.0
EDGE = 0.10
LAKES = {"ahl": Path("/home/claude/work/ahl_lake"),
         "liiga": Path("/home/claude/work/liiga_lake"),
         "mestis": Path("/home/claude/work/mestis_lake/mestis")}
HOLDOUT = {"ahl": "90", "liiga": "2026", "mestis": "2026"}


def load_estimator(league):
    cw = json.load(open(DER / f"{league}_clean_window.json"))["rows"]
    pre = [r for r in cw if r["date"] < CUTOFF]
    seqs = defaultdict(list)
    for r in sorted(pre, key=lambda x: x["date"]):
        if r["clear"]:
            seqs[r["coach"]].append((r["date"], 1 if r["taken"] else 0))
    from hockeycore.fit.prior_fit import fit_prior
    A, B, mu, st = fit_prior(list(seqs.values()))

    from hockeycore.fit.prior_fit import posterior
    def p_c(name):
        return posterior(seqs.get(name, []), A, B)
    return p_c, mu, seqs


def main(league, nhl_rates=False):
    fits = json.load(open(DER / f"fits_{league}_train.json"))
    aux = json.load(open(DER / f"fits_{league}_train_aux.json"))
    if nhl_rates:
        # Rulings 26d/40/41 — one implementation (rule 15): see splice.py.
        from hockeycore.fit.splice import apply_nhl_levels
        fits = apply_nhl_levels(fits)
        print(f"[{league}] SPLICE: NHL goal/min levels + {league} pull structure")
    MP.rebuild(fits)
    MP._ret = aux["return_hazard_per_sec"]
    MP._REPULL = aux["h_repull"]
    MP._LAG = aux["evidence_lag"]
    MP._DEAD = aux["dead"]
    p_c, mu, seqs = load_estimator(league)
    print(f"[{league}] pricer on train fits; league mu={mu:.3f}; "
          f"coaches with history: {len(seqs)}")

    holdout = HOLDOUT[league]
    insts = [r for r in json.load(open(DER / f"{league}_instances_gap3.json"))
             if r["season"] == holdout]
    hazc, cache = {}, {}

    def priced(R, pulled, strength, pi):
        key = (R, pulled, strength, round(min(max(pi, 0.05), 0.95), 2))
        if key not in cache:
            pk = key[3]
            if pk not in hazc:
                hazc[pk] = MP.coach_hazard_array(pk)
            cache[key] = MP.price(R, pulled0=pulled, strength0=strength,
                                  m_coach=1.0, n=20000, seed=13,
                                  haz3_override=hazc[pk])
        return cache[key]

    gcache = {}

    def game_of(r):
        key = (r["season"], r["game_id"])
        if key not in gcache:
            if league == "ahl":
                g = ahl_mod.parse_game(
                    LAKES["ahl"] / r["season"] / f"{r['game_id']}_pxp.json",
                    season=r["season"])
            elif league == "mestis":
                g = mestis_mod.parse_game(
                    LAKES["mestis"] / r["season"] /
                    f"game_{r['season']}_{r['game_id']}_seuranta.html")
            else:
                g = liiga_mod.parse_game(
                    LAKES["liiga"] / r["season"] / f"game_{r['season']}_{r['game_id']}.json")
            gcache[key] = g
        return gcache[key]

    rows = []
    for r in insts:
        g = game_of(r)
        tn = r["trailing"]
        boxes_t = [(p["begin"], p["end"]) for p in g["penalties"] if p["side"] == tn]
        boxes_l = [(p["begin"], p["end"]) for p in g["penalties"] if p["side"] != tn]
        segs = r["pull_segments"]
        pi = p_c(r["coach"])
        for R in CHECKPOINTS:
            t_cp = 1200 - R
            if not (r["opened_secs"] <= t_cp < r["closed_secs"]):
                continue
            ua = t_cp + 2400
            pulled = any(s["empty_from"] <= t_cp < s["empty_until"] for s in segs)
            tb = any(b <= ua < e for b, e in boxes_t)
            lb = any(b <= ua < e for b, e in boxes_l)
            strength = "T_PP" if (lb and not tb and not pulled) else \
                       ("T_PK" if (tb and not lb) else "EV")
            if pulled:
                strength = "EV"
            lead = trail = 0
            for gl in g["goals"]:
                if gl.get("period") == 3 and ua < gl["t"] <= 3600:
                    if gl["side"] == tn:
                        trail += 1
                    else:
                        lead += 1
            margin = 3 + lead - trail
            p = priced(R, pulled, strength, pi)
            rows.append({
                "game_id": r["game_id"], "inst": r["n"], "R": R,
                "pulled": pulled, "strength": strength,
                "coach": r["coach"], "m": round(pi, 3),
                "p_total1": p["P_total_ge1"], "p_total2": p["P_total_ge2"],
                "p_lead1": p["P_leader_ge1"], "p_marg4": p["P_margin_ge4"],
                "y_total1": int(lead + trail >= 1), "y_total2": int(lead + trail >= 2),
                "y_lead1": int(lead >= 1), "y_marg4": int(margin >= 4)})
    suffix = "_nhlrates" if nhl_rates else ""
    json.dump(rows, open(DER / f"backtest_rows_{league}{suffix}.json", "w"))
    n = len(rows)
    print(f"[{league}] priced {n} blind checkpoints ({holdout}); cells={len(cache)}")

    for pk, yk in [("p_lead1", "y_lead1"), ("p_total1", "y_total1"),
                   ("p_total2", "y_total2"), ("p_marg4", "y_marg4")]:
        rs = sorted(rows, key=lambda r: r[pk])
        bias = sum(r[yk] - r[pk] for r in rs) / n
        base = sum(r[yk] for r in rs) / n
        brier = sum((r[pk] - r[yk]) ** 2 for r in rs) / n
        skill = 1 - brier / (base * (1 - base))
        bad = 0
        for b in range(10):
            ch = rs[b * n // 10:(b + 1) * n // 10]
            mp_ = sum(r[pk] for r in ch) / len(ch)
            ay = sum(r[yk] for r in ch) / len(ch)
            se = math.sqrt(max(mp_ * (1 - mp_), 1e-9) / len(ch))
            bad += abs(ay - mp_) >= 2 * se
        print(f"  {pk:9} bias {bias:+.4f}  skill {skill:+.3f}  bad {bad}/10")

    games = defaultdict(list)
    for r in rows:
        games[r["game_id"]].append(r)
    gids = list(games)
    random.seed(11)
    for pk, yk, label in [("p_lead1", "y_lead1", "leaderTT_over"),
                          ("p_total1", "y_total1", "gametotal_over"),
                          ("p_marg4", "y_marg4", "leader_-3.5")]:
        def prof(r):
            p = r[pk]
            if p <= 0.02 or p >= 0.98:
                return None
            return r[yk] * (1 + EDGE - p) / p - (1 - r[yk])
        profs = [x for r in rows if (x := prof(r)) is not None]
        pt = sum(profs) / len(profs)
        boots = []
        for _ in range(2000):
            smp = random.choices(gids, k=len(gids))
            ps = [x for gid in smp for r in games[gid] if (x := prof(r)) is not None]
            boots.append(sum(ps) / len(ps))
        boots.sort()
        print(f"  ROI@10%EV {label:14} {pt:+.3f}  CI95 [{boots[50]:+.3f},{boots[1949]:+.3f}]  "
              f"P(>0)={sum(b > 0 for b in boots)/2000:.2f}")


if __name__ == "__main__":
    main(sys.argv[1], nhl_rates="--nhl-rates" in sys.argv[2:])
