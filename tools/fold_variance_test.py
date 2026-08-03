#!/usr/bin/env python3
"""
fold_variance_test.py {league} — Seb's hypothesis (2026-08-03): "the fold
swings are probably a variance issue on a small sample."

Testable. Under the null "the model's probabilities are right and seasons
share one level", each fold's bias is pure outcome noise. Games are the
independent unit (checkpoints within a game share the outcome window), so:

1. Per fold: game-clustered bootstrap SE of the bias -> z = bias / SE.
   |z| < 2 => that fold's miss is inside the luck envelope.
2. Joint: sum(z^2) ~ chi-square(df = #folds) if ALL misses are luck.
3. Random-effects tau: sqrt(max(var(bias) - mean(SE^2), 0)) = the TRUE
   between-season level spread after subtracting sampling noise.
   tau ~ 0 => Seb is right (pure variance); tau >> 0 => real level wobble.

Caveat printed with the result: the null here also absorbs TRAINING-side
sampling error only partially — fitted levels from 1-3 thin seasons move
between folds, which INFLATES observed spread beyond test noise. So tau is
an UPPER bound on true drift; the test is conservative toward "real drift".
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data" / "derived"


def fold_stats(rows, pk, yk, nboot=4000, seed=7):
    games = defaultdict(list)
    for r in rows:
        games[r["game_id"]].append(r)
    gids = list(games)
    n = len(rows)
    bias = sum(r[yk] - r[pk] for r in rows) / n
    rng = random.Random(seed)
    boots = []
    for _ in range(nboot):
        smp = rng.choices(gids, k=len(gids))
        num = den = 0
        for gid in smp:
            for r in games[gid]:
                num += r[yk] - r[pk]
                den += 1
        boots.append(num / den)
    m = sum(boots) / nboot
    se = math.sqrt(sum((b - m) ** 2 for b in boots) / (nboot - 1))
    return bias, se, len(gids)


def run(league, design):
    folds = json.load(open(DER / f"{league}_folds.json"))
    out = {}
    print(f"== {league} / {design} ==")
    for mk, pk, yk in (("lead1", "p_lead1", "y_lead1"),
                       ("total1", "p_total1", "y_total1"),
                       ("marg4", "p_marg4", "y_marg4")):
        zs = []
        rowsline = []
        for f in folds:
            if f["design"] != design:
                continue
            rows = json.load(open(DER / f"backtest_rows_{league}{f['tag']}.json"))
            bias, se, ng = fold_stats(rows, pk, yk)
            z = bias / se if se > 0 else 0.0
            zs.append((f["holdout"], bias, se, z))
            rowsline.append(f"{f['holdout']}: {bias:+.3f}±{se:.3f} z={z:+.2f} ({ng}g)")
        chi2 = sum(z * z for _, _, _, z in zs)
        df = len(zs)
        # chi-square survival via Wilson-Hilferty approx
        wh = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        p_joint = 0.5 * math.erfc(wh / math.sqrt(2))
        biases = [b for _, b, _, _ in zs]
        mean_se2 = sum(se * se for _, _, se, _ in zs) / df
        var_b = sum((b - sum(biases) / df) ** 2 for b in biases) / max(df - 1, 1)
        tau = math.sqrt(max(var_b - mean_se2, 0.0))
        print(f"  {mk:7} " + " | ".join(rowsline))
        print(f"          joint chi2={chi2:.1f} (df={df}) p={p_joint:.3f}  "
              f"tau(true season spread)={tau:.3f}")
        out[mk] = {"folds": [{"h": h, "bias": round(b, 4), "se": round(s, 4),
                              "z": round(z, 2)} for h, b, s, z in zs],
                   "chi2": round(chi2, 2), "df": df, "p_joint": round(p_joint, 4),
                   "tau": round(tau, 4)}
    return out


if __name__ == "__main__":
    league = sys.argv[1]
    res = {d: run(league, d) for d in ("forward", "loso_flat")}
    json.dump(res, open(DER / f"{league}_fold_variance.json", "w"), indent=1)
    print(f"wrote {DER / f'{league}_fold_variance.json'}")
