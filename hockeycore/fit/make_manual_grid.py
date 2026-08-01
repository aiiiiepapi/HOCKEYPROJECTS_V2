"""Manual/coach-conditional pricing grid (Seb directives 2026-07-26).

Axes: pull%% on a real chance x timing shift (secs earlier than league) x R.
5v5 state only — pulled-state and PP rows are not bettable (Seb rulings).

pull%% -> hazard multiplier calibration: relative log-survival anchored at the
new-era league clear-chance rate (m=1 <-> 69.5%%):
    m(p) = ln(1-p) / ln(1-0.695)
Timing uses the pricer's native coach_shift mechanism (positive = earlier).
Output: data/derived/pricing_grid_manual.json
"""
import json, math, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hockeycore.pricing.mc_pricer import price

P_LEAGUE = 0.695
P_GRID = [0.10, 0.30, 0.50, 0.695, 0.85, 0.95, 0.99]
SHIFTS = [-60, 0, 60, 120, 180]
RS = list(range(180, 901, 20))


def haz_of(p):
    # density-preserving law (ruling 23): pull % hits p with league timing
    from hockeycore.pricing.mc_pricer import coach_hazard_array
    return coach_hazard_array(min(max(p, 0.05), 0.99))


rows = []
t0 = time.time()
for i, R in enumerate(RS):
    for p in P_GRID:
        hz = haz_of(p)
        for sh in SHIFTS:
            pr = price(R, pulled0=False, strength0="EV", m_coach=1.0,
                       n=30000, seed=7, coach_shift=sh, haz3_override=hz)
            rows.append({"R": R, "pullpct": p, "shift": sh,
                         **{k: round(pr[k], 4) for k in
                            ("P_leader_ge1", "P_total_ge1", "P_margin_ge4")}})
    print(f"{i+1}/{len(RS)} R={R} ({time.time()-t0:.0f}s)", flush=True)

json.dump(rows, open(ROOT / "data/derived/pricing_grid_manual.json", "w"))
print(f"wrote {len(rows)} cells in {time.time()-t0:.0f}s")
