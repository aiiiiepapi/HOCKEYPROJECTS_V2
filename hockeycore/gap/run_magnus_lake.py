"""
run_magnus_lake.py — extract all Magnus 2025-26 gap-3 instances with
game-level coach attribution FROM THE SHEETS (the feuille de match names the
Entraîneur principal per team; no coach map needed — sheet authority per the
2026-08-08 lake verification, which corroborated the map on all spot-checked
clubs and overturned four web previews).

Lake location: /home/claude/work/magnus_lake_v/_manager/v2_bootstrap/
magnus_lake/pdf_2025-26 (checkout of v1-repo branch magnus-data-lake).
Output: data/derived/magnus_instances_gap3.json

Rows carry "_box"/"penalties_p3" (P3 penalty windows) directly so the ledger
builder does not need lake re-parse. Build aborts if any instance's TRAILING
side has no coach (runner-family convention).

MAGNUS INTEL DOCTRINE: one season of data, TOI-inferred (not evented) pull
timing, 7 multi-pull-ambiguous games carry synthetic (timing-unusable)
evidence. Coach intel ONLY; NO-GO for real money until a 26-27 blind pass
or Seb override.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.leagues.magnus import parse_game          # noqa: E402
from hockeycore.gap.segments import extract_instances     # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LAKE = Path("/home/claude/work/magnus_lake_v/_manager/v2_bootstrap/"
            "magnus_lake/pdf_2025-26")
OUT = ROOT / "data" / "derived" / "magnus_instances_gap3.json"


def main():
    rows, tot, unattributed, errors = [], Counter(), [], []
    for f in sorted(LAKE.glob("*.pdf"), key=lambda p: int(p.stem)):
        try:
            g = parse_game(str(f))
        except Exception as e:
            errors.append((f.name, repr(e)))
            continue
        if g is None:
            tot["empty_sheets"] += 1
            continue
        tot["games"] += 1
        coaches = {"home": g["coach_home"], "away": g["coach_away"]}
        box = [(max(p["begin"] - 2400, 0), max(p["end"] - 2400, 0))
               for p in g["penalties"] if p["end"] > 2400 and not p["misconduct"]]
        for i in extract_instances(g, 3):
            coach = coaches[i["trailing"]]
            if coach is None:
                unattributed.append((g["id"], g[i["trailing"]], g["date"]))
            i["season"] = "2026"
            i["game_id"] = g["id"]
            i["date"], i["home"], i["away"] = g["date"], g["home"], g["away"]
            i["coach"] = coach
            i["leader_coach"] = coaches["home" if i["trailing"] == "away" else "away"]
            i["penalties_p3"] = box
            i["_box"] = box
            rows.append(i)
            tot["instances"] += 1
    if errors:
        print(f"ABORT: {len(errors)} parse errors, first: {errors[:3]}")
        sys.exit(1)
    if unattributed:
        print(f"ABORT: {len(unattributed)} unattributed trailing coaches: "
              f"{unattributed[:5]}")
        sys.exit(1)
    pulled = sum(1 for r in rows if r["pulled"])
    ev = sum(1 for r in rows if r["pulled"] and r["pull_classification"] == "pull")
    json.dump(rows, open(OUT, "w"), indent=0, default=str)
    print(f"games {tot['games']} (+{tot['empty_sheets']} empty) "
          f"instances {tot['instances']} pulled {pulled} (EV {ev}) -> {OUT}")


if __name__ == "__main__":
    main()
