"""
run_mestis_lake.py — extract all Mestis gap-3 instances (4 seasons) with
game-level coach attribution from rosters.json (map fallback for the 19
verified blank sides — docs/MESTIS_LAKE_VERIFICATION.md).

Lake location: /home/claude/work/mestis_lake/mestis (clone of branch
mestis-data-lake on the V2 repo). Output: data/derived/mestis_instances_gap3.json

Build aborts if any instance's TRAILING side has no coach (silence is how
wrong attributions ship — liiga runner precedent).
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.leagues.mestis import parse_game          # noqa: E402
from hockeycore.gap.segments import extract_instances     # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LAKE = Path("/home/claude/work/mestis_lake/mestis")
OUT = ROOT / "data" / "derived" / "mestis_instances_gap3.json"
SEASON_LABEL = {"2023": "2022-23", "2024": "2023-24", "2025": "2024-25", "2026": "2025-26"}


def main():
    rows, tot, unattributed, errors = [], Counter(), [], []
    for season in ["2023", "2024", "2025", "2026"]:
        n_season = 0
        for f in sorted((LAKE / season).glob("game_*_seuranta.html"),
                        key=lambda p: int(p.stem.split("_")[2])):
            try:
                g = parse_game(f)
            except Exception as e:
                errors.append((season, f.name, repr(e)))
                continue
            tot["games"] += 1
            for i in extract_instances(g, 3):
                coach = g["coaches"][i["trailing"]]
                if coach is None:
                    unattributed.append((season, g["matchno"], g[i["trailing"]], g["date"]))
                i["season"], i["game_id"] = season, g["matchno"]
                i["date"], i["home"], i["away"] = g["date"], g["home"], g["away"]
                i["coach"] = coach
                i["leader_coach"] = g["coaches"]["home" if i["trailing"] == "away" else "away"]
                rows.append(i)
                n_season += 1
        tot[f"instances_{season}"] = n_season
    assert not errors, f"parse errors: {errors[:5]} (+{max(len(errors)-5,0)} more)"
    assert not unattributed, f"trailing side without coach: {unattributed}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=0)
    tot["instances"] = len(rows)
    tot["pulled"] = sum(1 for r in rows if r["pulled"])
    tot["pp_pull"] = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    tot["ev_pull"] = sum(1 for r in rows if r["pull_classification"] == "pull")
    print(dict(tot))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
