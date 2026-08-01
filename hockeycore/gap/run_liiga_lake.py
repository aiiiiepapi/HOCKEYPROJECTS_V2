"""
run_liiga_lake.py — extract all Liiga gap-3 instances (4 seasons) with the
hand-curated coach map joined by team + game date.

Lake location: /home/claude/work/liiga_lake (clone of branch liiga-data-lake).
Output: data/derived/liiga_instances_gap3.json

The Liiga API has NO coach field; data/coach_maps/liiga_coaches.csv (verified
against primary Finnish sources 2026-08-01) is the ONLY attribution source.
Build aborts if any instance lands outside every coach window — silence is
how wrong attributions ship.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.leagues.liiga import parse_game          # noqa: E402
from hockeycore.gap.segments import extract_instances    # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LAKE = Path("/home/claude/work/liiga_lake")
OUT = ROOT / "data" / "derived" / "liiga_instances_gap3.json"
SEASON_LABEL = {"2023": "2022-23", "2024": "2023-24", "2025": "2024-25", "2026": "2025-26"}
# API team name -> coach-map team name (only divergence found, verified 2026-08-01)
NAME_FIX = {"K-Espoo": "Kiekko-Espoo"}


def load_coach_map():
    m = {}
    for r in csv.DictReader(open(ROOT / "data/coach_maps/liiga_coaches.csv", encoding="utf-8")):
        m.setdefault((r["team"], r["season"]), []).append(
            (r["from_date"], r["to_date"], r["coach"]))
    return m


def coach_for(cmap, team, season_label, date):
    for d0, d1, coach in cmap.get((team, season_label), []):
        if d0 <= date <= d1:
            return coach
    return None


def main():
    cmap = load_coach_map()
    rows, tot, unattributed = [], Counter(), []
    for season in ["2023", "2024", "2025", "2026"]:
        label = SEASON_LABEL[season]
        n_season = 0
        for f in sorted((LAKE / season).glob("game_*.json"),
                        key=lambda p: int(p.stem.split("_")[2])):
            g = parse_game(f)
            raw = json.load(open(f))["game"]
            date = (raw.get("start") or "")[:10]
            tot["games"] += 1
            for i in extract_instances(g, 3):
                if season == "2023":
                    # 2022-23 has NO goalie-event channel in the API at all
                    # (goalKeeperEvents AND goalKeeperChanges empty league-wide,
                    # verified 2026-08-01). Pull truth is UNKNOWABLE for this
                    # season — instances stay (goal/penalty rates remain valid)
                    # but must never read as no-pulls in a coach ledger.
                    i["pulled"] = None
                    i["pull_evidence_secs"] = None
                    i["pull_classification"] = None
                    i["pull_segments"] = []
                    i["no_goalie_channel"] = True
                team = NAME_FIX.get(g[i["trailing"]], g[i["trailing"]])
                coach = coach_for(cmap, team, label, date)
                if coach is None:
                    unattributed.append((season, f.name, team, date))
                i["season"], i["game_id"] = season, int(f.stem.split("_")[2])
                i["date"], i["home"], i["away"] = date, g["home"], g["away"]
                i["coach"] = coach
                rows.append(i)
                n_season += 1
        tot[f"instances_{season}"] = n_season
    assert not unattributed, f"instances without coach attribution: {unattributed[:10]}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=0)
    tot["instances"] = len(rows)
    tot["pulled"] = sum(1 for r in rows if r["pulled"])
    tot["pp_pull"] = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    print(dict(tot))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
