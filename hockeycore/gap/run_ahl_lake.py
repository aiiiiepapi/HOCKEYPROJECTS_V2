"""
run_ahl_lake.py — extract all AHL gap-3 instances from the lake, with the
EN cross-checks (both directions) enforced as build-time assertions.

Lake location: /home/claude/work/ahl_lake (clone of branch ahl-data-lake).
Output: data/derived/ahl_instances_gap3.json

Cross-checks (adjudicated 2026-08-01, see ahl.py header):
  LEG A  every empty_net-flagged goal (P1-P3) lies inside a reconstructed
         net-empty interval of the conceding side, tolerance +/-3s (feed clock
         skew), counting synthetic evidence segments. Violations = 0 or abort.
  LEG B  every non-synthetic empty interval that ends exactly at a goal-against
         second has that goal flagged EN. Violations = 0 or abort.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.leagues.ahl import parse_game            # noqa: E402
from hockeycore.gap.segments import extract_instances    # noqa: E402

LAKE = Path("/home/claude/work/ahl_lake")
OUT = Path(__file__).resolve().parents[2] / "data" / "derived" / "ahl_instances_gap3.json"
SEASONS = ["77", "81", "86", "90"]


def main():
    rows, tot = [], Counter()
    bad_a, bad_b = [], []
    for season in SEASONS:
        n_season = 0
        for f in sorted((LAKE / season).glob("*_pxp.json")):
            gid = f.name.split("_")[0]
            g = parse_game(f, season=season)
            tot["games"] += 1
            for gl in g["goals"]:
                if gl["period"] > 3 or not gl["en"]:
                    continue
                opp = "away" if gl["side"] == "home" else "home"
                if not any(b - 3 <= gl["t"] <= e2 + 3 for b, e2, *_ in g["empty"][opp]):
                    bad_a.append((season, gid, gl["t"]))
            for sd in ("home", "away"):
                opp = "away" if sd == "home" else "home"
                for tup in g["empty"][sd]:
                    if len(tup) > 2:
                        continue  # synthetic evidence: exempt by construction
                    for gl in g["goals"]:
                        if gl["t"] == tup[1] and gl["side"] == opp and gl["period"] <= 3 \
                                and not gl["en"]:
                            bad_b.append((season, gid, gl["t"]))
            for i in extract_instances(g, 3):
                i["season"], i["game_id"], i["date"] = season, gid, g["date"]
                i["home"], i["away"] = g["home"], g["away"]
                i["coach"] = g["coaches"]["home" if i["trailing"] == "home" else "away"]
                rows.append(i)
                n_season += 1
        tot[f"instances_{season}"] = n_season
    assert not bad_a, f"EN cross-check LEG A violations: {bad_a[:10]}"
    assert not bad_b, f"EN cross-check LEG B violations: {bad_b[:10]}"
    assert all(r["coach"] for r in rows), "instance without coach attribution"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=0)
    tot["instances"] = len(rows)
    tot["pulled"] = sum(r["pulled"] for r in rows)
    tot["pp_pull"] = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    tot["synthetic"] = sum(1 for r in rows if r.get("synthetic_pull_evidence"))
    print(dict(tot))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
