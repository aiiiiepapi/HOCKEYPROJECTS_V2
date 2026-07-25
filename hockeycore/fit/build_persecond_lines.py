"""Per-second 10%-EV line table (Seb ruling 2026-07-25, odds decision c).

For every second R in [180, 900], every state, every coach tier and every
market: interpolate the dense MC grid (20s mesh, n=30k) to get p, then the
American line at which EV = exactly +EDGE:
    decimal profit b* = (1 + EDGE - p) / p     (EV = p*b - (1-p) = EDGE)
    bet is +EDGE EV at any line >= b*.
Output: data/derived/lines_10ev_per_second.csv (+ .json summary).
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "data" / "derived"
EDGE = 0.10
MARKETS = ["P_leader_ge1", "P_total_ge1", "P_margin_ge4"]
MK_LABEL = {"P_leader_ge1": "leaderTT_over", "P_total_ge1": "gametotal_over",
            "P_margin_ge4": "leader_-3.5", "P_total_ge2": "total2plus"}


def american(b):
    """decimal profit -> American odds string."""
    if b >= 1:
        return f"+{b * 100:.0f}"
    return f"-{100 / b:.0f}"


def line_at_edge(p, edge=EDGE):
    b = (1 + edge - p) / p
    return b, american(b)


def main():
    grid = json.load(open(DER / "pricing_grid_dense.json"))
    states = sorted({r["state"] for r in grid})
    tiers = sorted({r["tier"] for r in grid})
    Rs = np.array(sorted({r["R"] for r in grid}))
    secs = np.arange(180, 901)

    by = {}
    for r in grid:
        by[(r["state"], r["tier"], r["R"])] = r

    out = csv.writer(open(DER / "lines_10ev_per_second.csv", "w", newline=""))
    hdr = ["R", "time_left", "state", "tier"]
    for mk in MARKETS:
        hdr += [f"p_{MK_LABEL[mk]}", f"line10_{MK_LABEL[mk]}"]
    out.writerow(hdr)

    n_rows = 0
    for st in states:
        for tr in tiers:
            curves = {}
            for mk in MARKETS:
                ys = np.array([by[(st, tr, R)][mk] for R in Rs])
                curves[mk] = np.interp(secs, Rs, ys)
            for i, s in enumerate(secs[::-1]):
                row = [int(s), f"{s // 60}:{s % 60:02d}", st, tr]
                for mk in MARKETS:
                    p = float(curves[mk][len(secs) - 1 - i])
                    b, am = line_at_edge(p)
                    row += [round(p, 4), am]
                out.writerow(row)
                n_rows += 1
    print(f"wrote {n_rows} rows -> lines_10ev_per_second.csv")


if __name__ == "__main__":
    main()
