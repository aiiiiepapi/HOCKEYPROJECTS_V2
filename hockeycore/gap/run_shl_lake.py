"""
run_shl_lake.py — extract all SHL gap-3 instances (4 seasons) with game-level
coach attribution from LineUps (map fallback for the 21 verified blank sides —
data/coach_maps/shl_coaches.csv, docs/SHL_LAKE_VERIFICATION.md census).

Lake location: /home/claude/work/shl_lake/shl (checkout of branch
shl-data-lake @ 6b77add). Output: data/derived/shl_instances_gap3.json

Build aborts if any instance's TRAILING side has no coach (silence is how
wrong attributions ship — liiga runner precedent).
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.leagues.shl import parse_game             # noqa: E402
from hockeycore.gap.segments import extract_instances     # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LAKE = Path("/home/claude/work/shl_lake/shl")
OUT = ROOT / "data" / "derived" / "shl_instances_gap3.json"
SEASON_LABEL = {"2023": "2022-23", "2024": "2023-24", "2025": "2024-25", "2026": "2025-26"}


# Spelling normalization (Manager adjudication 2026-08-07, docs/
# SHL_LAKE_VERIFICATION_ADAPTER.md): a one-game sheet misspelling is the SAME
# person, not a different coach — 629332's "Johan Lindholm" is Johan Lindbom
# (every neighboring listing; liiga NAME_FIX precedent). Identity unchanged,
# listing-wins convention intact. Burström (629012) stays as listed
# (plausible caretaker, no counter-evidence).
COACH_SPELLING_FIX = {"Johan Lindholm": "Johan Lindbom"}


def main():
    rows, tot, unattributed, errors = [], Counter(), [], []
    for season in ["2023", "2024", "2025", "2026"]:
        n_season = 0
        for f in sorted((LAKE / season).glob("game_*_events.html"),
                        key=lambda p: int(p.stem.split("_")[2])):
            try:
                g = parse_game(f)
            except Exception as e:
                errors.append((season, f.name, repr(e)))
                continue
            tot["games"] += 1
            for i in extract_instances(g, 3):
                coach = g["coaches"][i["trailing"]]
                coach = COACH_SPELLING_FIX.get(coach, coach)
                if coach is None:
                    unattributed.append((season, g["game_id"], g[i["trailing"]], g["date"]))
                i["season"], i["game_id"] = season, g["game_id"]
                i["date"], i["home"], i["away"] = g["date"], g["home"], g["away"]
                i["coach"] = coach
                lc = g["coaches"]["home" if i["trailing"] == "away" else "away"]
                i["leader_coach"] = COACH_SPELLING_FIX.get(lc, lc)
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
