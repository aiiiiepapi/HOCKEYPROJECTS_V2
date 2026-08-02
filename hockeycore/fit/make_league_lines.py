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


def main(league, nhl_rates=False):
    fits = json.load(open(DER / f"fits_{league}.json"))
    aux = json.load(open(DER / f"fits_{league}_aux.json"))
    if nhl_rates:
        # Ruling 41 (Seb, 2026-08-02): AHL production runs on NHL goal/min
        # levels "for now" — ordered with the failed-blind record heard
        # (rulings 26d + 40). Output files carry the UNVALIDATED banner and
        # leader -3.5 is EXCLUDED (ruling 26a: permanent no-bet).
        from hockeycore.fit.splice import apply_nhl_levels
        fits = apply_nhl_levels(fits)
        print(f"[{league}] RULING-41 SPLICE ACTIVE: NHL goal/min levels")
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
    if nhl_rates and league == "ahl":
        # Ruling 41b (Seb, 2026-08-02): -3.5 INCLUDED on NHL numbers too —
        # Seb overrode his own ruling 26a after re-hearing the oracle/blind
        # record. Full config: AHL coach pull %% + AHL pull structure + NHL
        # scoring rates, all three markets live on the sheet.
        (DER / "AHL_LINES_UNVALIDATED.md").write_text(
            "# AHL lines: UNVALIDATED (rulings 41 + 41b)\n\n"
            "lines_10ev_ahl.csv = AHL coach pull %% + AHL pull structure +\n"
            "NHL goal/min scoring rates, BY SEB'S ORDER (2026-08-02), with\n"
            "the failed-blind record heard first (rulings 26d + 40: marg4\n"
            "-12.1pts 9/10 bad deciles, -3.5 ROI -22.3%% P(>0)=0.00,\n"
            "leaderTT -3.4%% at model lines). -3.5 is INCLUDED by ruling 41b\n"
            "(Seb override of ruling 26a's permanent no-bet, oracle record\n"
            "re-heard). These numbers did NOT pass verification protocol\n"
            "step 6. Rule 28 floor (base coach %% < 40 = NO-BET) unchanged.\n"
            "Paper harness logs model-vs-real-line-vs-outcome to settle\n"
            "this empirically; December re-litigation unchanged.\n")
        print(f"[{league}] ruling-41b: all three markets live; UNVALIDATED banner written")
    print(f"[{league}] wrote lines_10ev_{league}.csv")


if __name__ == "__main__":
    main(sys.argv[1], nhl_rates="--nhl-rates" in sys.argv[2:])
