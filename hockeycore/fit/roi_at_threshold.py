"""Realized ROI when betting every blind 25-26 checkpoint at the model's
exact +10%-EV line (Seb's validation: 'backtest to see if it really wins at
that line' — market availability irrelevant by ruling, odds decision c).

Writes data/derived/roi_at_threshold.json; gated in test_v2_gates.
"""
import json, math, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "data" / "derived"
EDGE = 0.10
MARKETS = [("p_lead1", "y_lead1", "leaderTT_over"),
           ("p_marg4", "y_marg4", "leader_-3.5"),
           ("p_total1", "y_total1", "gametotal_over")]


def profit(r, pk, yk, edge=EDGE):
    p = r[pk]
    if p <= 0.02 or p >= 0.98:
        return None
    b = (1 + edge - p) / p
    return r[yk] * b - (1 - r[yk])


def main():
    rows = json.load(open(DER / "backtest_rows.json"))
    games = {}
    for r in rows:
        games.setdefault(r["game_id"], []).append(r)
    gids = list(games)
    random.seed(11)

    res = {"edge": EDGE, "n_rows": len(rows), "n_games": len(gids), "markets": {}}
    for pk, yk, label in MARKETS:
        profs = [x for r in rows if (x := profit(r, pk, yk)) is not None]
        pt = sum(profs) / len(profs)
        boots = []
        for _ in range(2000):
            sample = random.choices(gids, k=len(gids))
            ps = [x for g in sample for r in games[g] if (x := profit(r, pk, yk)) is not None]
            boots.append(sum(ps) / len(ps))
        boots.sort()
        res["markets"][label] = {
            "roi": round(pt, 4), "n": len(profs),
            "ci95_game_cluster": [round(boots[50], 4), round(boots[1949], 4)],
            "p_roi_gt_0": round(sum(b > 0 for b in boots) / 2000, 4),
            "p_roi_gt_edge": round(sum(b > EDGE for b in boots) / 2000, 4),
        }
    json.dump(res, open(DER / "roi_at_threshold.json", "w"), indent=1)
    for k, v in res["markets"].items():
        print(k, v)


if __name__ == "__main__":
    main()
