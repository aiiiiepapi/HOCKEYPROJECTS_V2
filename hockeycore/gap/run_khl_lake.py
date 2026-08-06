"""
run_khl_lake.py — extract all KHL gap-3 instances (4 seasons, 3,060 games)
with game-level coach attribution from the text-page preview frame.

Coach census is 100.0% (Manager-verified, docs/KHL_LAKE_VERIFICATION.md) —
there is NO coach map: an unattributed trailing coach is a parser bug and
aborts the build (silence is how wrong attributions ship).

Lake location: a checkout of branch khl-data-lake (default
/home/user/work/khl_lake/khl in this session's environment; override with
KHL_LAKE env var — earlier sessions used /home/claude/work/...).
Outputs:
  data/derived/khl_instances_gap3.json  — one row per gap-3 instance
  data/derived/khl_dp_events.json       — aux explicit delayed-penalty export
      (game, season, side, period, bracket time, raw text verbatim, linked
      pull window of the NON-OFFENDING side when one overlaps the bracket)
      for the Manager's rulings-17/17b cross-calibration. Rulings untouched.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.leagues.khl import parse_game             # noqa: E402
from hockeycore.gap.segments import extract_instances     # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LAKE = Path(os.environ.get("KHL_LAKE", "/home/user/work/khl_lake/khl"))
OUT = ROOT / "data" / "derived" / "khl_instances_gap3.json"
DP_OUT = ROOT / "data" / "derived" / "khl_dp_events.json"
SEASONS = ["2023", "2024", "2025", "2026"]


def dp_rows(g):
    """Aux export rows for a game's explicit dp events. The dp line carries no
    time; after_t (last timed play event before it) and the next assessment
    are the bracket. linked_pull = a net-empty interval of the NON-offending
    side that begins inside [after_t-2, after_t+90] (dp possessions are
    short); null when no such window exists."""
    rows = []
    for d in g["dp_events"]:
        offender = d["side"]
        puller = ("away" if offender == "home" else "home") if offender else None
        linked = None
        if puller and d["after_t"] is not None:
            for tup in g["empty"][puller]:
                b, e = tup[0], tup[1]
                if d["after_t"] - 2 <= b <= d["after_t"] + 90:
                    linked = [b, e]
                    break
        rows.append({"season": g["season"], "game_id": g["game_id"],
                     "offending_side": offender, "period": d["period"],
                     "after_t": d["after_t"], "raw": d["raw"],
                     "linked_pull_window": linked})
    return rows


def main():
    rows, dps, tot, unattributed, errors = [], [], Counter(), [], []
    for season in SEASONS:
        n_season = 0
        for f in sorted((LAKE / season).glob("*_text.html"),
                        key=lambda p: int(p.stem.split("_")[0])):
            try:
                g = parse_game(f)
            except Exception as e:
                errors.append((season, f.name, repr(e)))
                continue
            tot["games"] += 1
            dps.extend(dp_rows(g))
            for i in extract_instances(g, 3):
                coach = g["coaches"][i["trailing"]]
                if coach is None:
                    unattributed.append((season, g["game_id"], g[i["trailing"]], g["date"]))
                i["season"], i["game_id"] = season, g["game_id"]
                i["date"], i["home"], i["away"] = g["date"], g["home"], g["away"]
                i["coach"] = coach
                i["leader_coach"] = g["coaches"]["home" if i["trailing"] == "away" else "away"]
                rows.append(i)
                n_season += 1
        tot[f"instances_{season}"] = n_season
    assert not errors, f"parse errors: {errors[:5]} (+{max(len(errors)-5,0)} more)"
    assert not unattributed, f"trailing side without coach: {unattributed[:5]}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=0, ensure_ascii=False)
    json.dump(dps, open(DP_OUT, "w"), indent=0, ensure_ascii=False)
    tot["instances"] = len(rows)
    tot["pulled"] = sum(1 for r in rows if r["pulled"])
    tot["pp_pull"] = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    tot["ev_pull"] = sum(1 for r in rows if r["pull_classification"] == "pull")
    tot["dp_only_empty"] = sum(1 for r in rows if r.get("dp_only_empty"))
    tot["dp_events"] = len(dps)
    print(dict(tot))
    print(f"wrote {OUT}")
    print(f"wrote {DP_OUT}")


if __name__ == "__main__":
    main()
