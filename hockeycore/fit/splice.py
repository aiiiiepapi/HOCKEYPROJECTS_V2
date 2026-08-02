"""
splice.py — NHL goal/min LEVELS onto a league's own pull structure (rule 15:
the splice exists ONCE; used by backtest_interval --nhl-rates and, per ruling
41, the AHL production line builder).

History: proposed by Seb 2026-08-01 (tested, FAILED blind — ruling 26d),
re-tested on corrected data 2026-08-02 (FAILED blind again — ruling 40),
then ORDERED into AHL production "for now" by Seb 2026-08-02 (ruling 41)
with the disagreement heard and recorded. Goal levels = rates, rates_R,
m_PP, pen. Pull structure (hazard + aux) stays league-fitted.
"""
import json
from pathlib import Path

DER = Path(__file__).resolve().parents[2] / "data" / "derived"


def apply_nhl_levels(fits):
    nhl = json.load(open(DER / "fits.json"))
    for k in ("rates", "rates_R", "m_PP", "pen"):
        if k in nhl:
            fits[k] = nhl[k]
    return fits
