"""Dense pricing grid for the per-second 10%-EV line table.

R = 180..900 step 20 (37 points) x 3 states x 6 coach tiers, n=30k MC.
Output: data/derived/pricing_grid_dense.json (then interpolated per second).
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hockeycore.pricing.mc_pricer import price

TIERS = [0.25, 0.40, 0.55, 0.70, 0.85]  # coach expected pull % (density law, ruling 23)
STATES = [("not_pulled_EV", False, "EV"), ("not_pulled_PP", False, "T_PP"), ("pulled", True, "EV")]
RS = list(range(180, 901, 20))

rows = []
t0 = time.time()
for i, R in enumerate(RS):
    for sname, pulled0, strength0 in STATES:
        for m in TIERS:
            from hockeycore.pricing.mc_pricer import coach_hazard_array
            p = price(R, pulled0=pulled0, strength0=strength0, m_coach=1.0,
                      n=30000, seed=7, haz3_override=coach_hazard_array(m))
            rows.append({"R": R, "state": sname, "tier": m,
                         **{k: round(p[k], 4) for k in
                            ("P_leader_ge1", "P_leader_ge2", "P_total_ge1", "P_total_ge2", "P_margin_ge4")}})
    print(f"{i+1}/{len(RS)} R={R} done ({time.time()-t0:.0f}s)", flush=True)

json.dump(rows, open(ROOT / "data/derived/pricing_grid_dense.json", "w"))
print(f"wrote {len(rows)} cells in {time.time()-t0:.0f}s")
