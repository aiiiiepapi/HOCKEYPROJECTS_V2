"""
make_league_lines.py — per-league dense grid + per-second 10%-EV threshold CSV.

Prices the (R x state x coach-pull%%-tier) grid with the league's OWN fits and
the density coach law, then interpolates per-second threshold lines exactly
like the NHL table: for each second 900..180, the worst price that still pays
+10%% EV at the model probability.

Output (tracked, consumed by tools/paper_harness.py on Seb's PC):
  data/derived/pricing_grid_dense_{league}.json
  data/derived/lines_10ev_{league}.csv
Usage: python3 hockeycore/fit/make_league_lines.py ahl|liiga
"""
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import hockeycore.pricing.mc_pricer as MP  # noqa: E402

DER = ROOT / "data" / "derived"
TIERS = [0.25, 0.40, 0.55, 0.70, 0.85]
STATES = [("not_pulled_EV", False, "EV"), ("not_pulled_PP", False, "T_PP"),
          ("pulled", True, "EV")]
RS = list(range(180, 901, 20))
MARKETS = ["P_leader_ge1", "P_total_ge1", "P_margin_ge4"]
EDGE = 0.10


def main(league):
    fits = json.load(open(DER / f"fits_{league}.json"))
    aux = json.load(open(DER / f"fits_{league}_aux.json"))
    MP.rebuild(fits)
    MP._ret = aux["return_hazard_per_sec"]
    MP._REPULL = aux["h_repull"]
    MP._LAG = aux["evidence_lag"]
    MP._DEAD = aux["dead"]

    rows = []
    t0 = time.time()
    for i, R in enumerate(RS):
        for sname, pulled0, strength0 in STATES:
            for tier in TIERS:
                hz = MP.coach_hazard_array(tier)
                p = MP.price(R, pulled0=pulled0, strength0=strength0, m_coach=1.0,
                             n=30000, seed=7, haz3_override=hz)
                rows.append({"R": R, "state": sname, "tier": tier,
                             **{k: round(p[k], 4) for k in
                                ("P_leader_ge1", "P_leader_ge2", "P_total_ge1",
                                 "P_total_ge2", "P_margin_ge4")}})
        print(f"[{league}] {i+1}/{len(RS)} R={R} ({time.time()-t0:.0f}s)", flush=True)
    json.dump(rows, open(DER / f"pricing_grid_dense_{league}.json", "w"))

    by = {(r["state"], r["tier"], r["R"]): r for r in rows}

    def interp(state, tier, R, mk):
        lo = max(180, (R // 20) * 20)
        hi = min(900, lo + 20)
        a, b = by[(state, tier, lo)][mk], by[(state, tier, hi)][mk]
        return a if hi == lo else a + (b - a) * (R - lo) / (hi - lo)

    with open(DER / f"lines_10ev_{league}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["R", "state", "tier"] +
                   [x for mk in MARKETS for x in (f"{mk}_prob", f"{mk}_line10")])
        for R in range(900, 179, -1):
            for state, _, _ in STATES:
                for tier in TIERS:
                    row = [R, state, tier]
                    for mk in MARKETS:
                        pv = interp(state, tier, R, mk)
                        # worst decimal price still paying +10% EV at model prob
                        line = (1 + EDGE) / pv if pv > 0.02 else None
                        row += [round(pv, 4), round(line, 3) if line else ""]
                    w.writerow(row)
    print(f"[{league}] wrote lines_10ev_{league}.csv")


if __name__ == "__main__":
    main(sys.argv[1])
