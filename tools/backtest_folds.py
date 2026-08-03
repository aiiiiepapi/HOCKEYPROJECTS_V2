#!/usr/bin/env python3
"""
backtest_folds.py {league} — multi-fold backtest (2026-08-03, Seb's order:
"find a better way to backtest"). Two designs, complementary:

FORWARD folds (betting-valid, strictly causal): fit on seasons strictly
before the test season, coach estimator cut at the test season's start.
  2024 | fit 2023        2025 | fit 2023-24        2026 | fit 2023-25
Three honest verdicts instead of one. (2023 has no earlier season.)

LOSO level check (diagnostic, NOT betting-valid): fit on the OTHER three
seasons, price the held-out one with a FLAT coach (league mu) — isolates
LEVEL calibration from the coach layer, symmetric across all 4 seasons.
If misses scatter around zero -> model fine, outlier season(s) visible.
If every fold misses the same way -> the model itself is off.

Writes data/derived/{league}_folds.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hockeycore.fit import fit_interval_league as FIT       # noqa: E402
from hockeycore.fit import backtest_interval as BT          # noqa: E402

DER = ROOT / "data" / "derived"


def season_start_cutoff(league, season):
    if league == "ahl":
        return {"77": "2022-09-01", "81": "2023-09-01",
                "86": "2024-09-01", "90": "2025-09-01"}[season]
    return f"{int(season) - 1}-09-01"


def main(league):
    seasons = FIT.CFG[league]["seasons"]
    no_goalie = FIT.CFG[league]["no_goalie"]
    results = []

    print("=" * 30, "FORWARD FOLDS (betting-valid)", "=" * 30)
    for i, hold in enumerate(seasons):
        train = list(seasons[:i])
        if not train:
            continue
        if hold in no_goalie:
            continue
        if all(t in no_goalie for t in train):
            continue        # no goalie channel anywhere in training -> no hazard fit
        tag = f"_fold{hold}"
        FIT.main(league, seasons_override=train)          # writes fits_{lg}_train
        r = BT.main(league, holdout=hold,
                    cutoff=season_start_cutoff(league, hold), tag=tag)
        r["design"], r["train"] = "forward", train
        results.append(r)

    print("=" * 30, "LOSO LEVEL CHECK (flat coach, diagnostic)", "=" * 30)
    for hold in seasons:
        if hold in no_goalie:
            continue
        train = [s for s in seasons if s != hold and s not in no_goalie]
        tag = f"_loso{hold}"
        FIT.main(league, seasons_override=train)
        r = BT.main(league, holdout=hold, cutoff="2099-01-01",
                    tag=tag, flat_coach=True)
        r["design"], r["train"] = "loso_flat", train
        results.append(r)

    # restore the canonical train fit (all-but-last)
    FIT.main(league, train=True)

    json.dump(results, open(DER / f"{league}_folds.json", "w"), indent=1)
    print("\n" + "=" * 24, "SUMMARY", "=" * 24)
    print(f"{'design':10} {'test':6} {'n':>4} | lead1 bias | total1 bias | marg4 bias | bad(l1/t1/m4)")
    for r in results:
        m = r["markets"]
        print(f"{r['design']:10} {r['holdout']:6} {r['n_checkpoints']:4} | "
              f"{m['p_lead1']['bias']:+10.3f} | {m['p_total1']['bias']:+11.3f} | "
              f"{m['p_marg4']['bias']:+10.3f} | "
              f"{m['p_lead1']['bad_deciles']}/{m['p_total1']['bad_deciles']}/{m['p_marg4']['bad_deciles']}")
    print(f"wrote {DER / f'{league}_folds.json'}")


if __name__ == "__main__":
    main(sys.argv[1])
