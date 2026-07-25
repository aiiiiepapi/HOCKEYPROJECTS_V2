"""Run gap extraction over the whole NHL lake; emit instance tables."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hockeycore.gap.extract import load_pbp, extract_instances

LAKE = Path("/home/claude/work/nhl_lake")
OUT = Path(__file__).resolve().parents[2] / "data" / "derived"
OUT.mkdir(parents=True, exist_ok=True)


def coaches(season_dir, gid):
    try:
        rr = json.load(open(season_dir / f"{gid}_rightrail.json", encoding="utf-8-sig"))
        gi = rr.get("gameInfo", {})
        return (gi.get("awayTeam", {}).get("headCoach", {}).get("default"),
                gi.get("homeTeam", {}).get("headCoach", {}).get("default"))
    except Exception:
        return (None, None)


def main():
    tables = {2: [], 3: [], 4: []}
    errors = []
    t0 = time.time()
    n = 0
    for season in ["20222023", "20232024", "20242025", "20252026"]:
        sd = LAKE / season
        idx = json.load(open(sd / "schedule_index.json", encoding="utf-8-sig"))
        for gmeta in idx["games"]:
            gid = gmeta["id"]
            n += 1
            try:
                pbp = load_pbp(sd / f"{gid}_pbp.json")
                ac, hc = coaches(sd, gid)
                for gap in (2, 3, 4):
                    g, insts = extract_instances(pbp, target_gap=gap)
                    for inst in insts:
                        inst["game_id"] = gid
                        inst["season"] = season
                        inst["date"] = gmeta.get("date", "")
                        inst["away"], inst["home"] = g["away"], g["home"]
                        inst["trailing_coach"] = hc if inst["trailing"] == g["home"] else ac
                        inst["leading_coach"] = ac if inst["trailing"] == g["home"] else hc
                        tables[gap].append(inst)
            except Exception as e:
                errors.append((gid, repr(e)[:100]))
    for gap, rows in tables.items():
        with open(OUT / f"instances_gap{gap}.json", "w") as f:
            json.dump(rows, f)
        print(f"gap {gap}: {len(rows)} instances")
    print(f"games processed: {n}, errors: {len(errors)}, {time.time()-t0:.0f}s")
    if errors:
        json.dump(errors, open(OUT / "extract_errors.json", "w"), indent=1)
        for e in errors[:10]:
            print("  ERR", e)


if __name__ == "__main__":
    main()
