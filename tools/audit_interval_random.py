#!/usr/bin/env python3
"""
audit_interval_random.py — seeded random instance audit for interval leagues
(AHL / Liiga): re-verifies pulls and no-pulls DIRECTLY against the raw lake
goalie channels, bypassing the adapter state machine (rule 0/6).

Usage: python3 tools/audit_interval_random.py {ahl|liiga} [n_per_side] [seed]
Exit code 0 = no disagreements. Prints each disagreement.
First run (liiga, seed 20260802, 30+30): 0 disagreements, 2026-08-02.
AHL twin (seed 20260801, 30+30): 0 disagreements, 2026-08-01 (ahl_batch1.md).
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
P3 = 2400

def liiga_raw_empty(season, gid, trailing):
    raw = json.load(open(f"/home/claude/work/liiga_lake/{season}/game_{season}_{gid}.json"))["game"]
    t = raw["homeTeam" if trailing == "home" else "awayTeam"]
    out = []
    for e in (t.get("goalKeeperEvents") or []):
        if e.get("emptyNet") in (1, True) and e.get("beginTime") is not None:
            end = e.get("endTime") or e["beginTime"] + 1
            out.append((e["beginTime"], end))
    return out

def ahl_raw_empty(season, gid, trailing_code):
    ev = json.load(open(f"/home/claude/work/ahl_lake/{season}/{gid}_pxp.json"))["GC"]["Pxpverbose"]
    rows = []
    for e in ev:
        if e.get("event") != "goalie_change" or e.get("team_code") != trailing_code:
            continue
        per = int(e.get("period_id") or 0)
        if per > 3:
            continue
        rows.append(((per - 1) * 1200 + int(e["s"]),
                     bool(e.get("goalie_in_id")), bool(e.get("goalie_out_id"))))
    # group rows sharing a second: an in+out pair at one second is a SWAP
    # (net never empty) — e.g. 81/1025596 per2 s738 (audit-tool lesson).
    bysec = {}
    for t, gin, gout in rows:
        a, b = bysec.get(t, (False, False))
        bysec[t] = (a or gin, b or gout)
    out, open_t = [], None
    for t in sorted(bysec):
        gin, gout = bysec[t]
        if gin and gout:
            continue                      # swap at a stoppage: net stays full
        if gout and open_t is None:
            open_t = t
        elif gin and open_t is not None:
            out.append((open_t, t)); open_t = None
    if open_t is not None:
        out.append((open_t, 3600))
    return out

def audit(lg, n_side=30, seed=None):
    seed = seed or {"ahl": 20260801, "liiga": 20260802}[lg]
    rows = json.load(open(ROOT / "data" / "derived" / f"{lg}_instances_gap3.json"))
    pulls = [r for r in rows if r.get("pulled")]
    nops = [r for r in rows if r.get("pulled") is False and r.get("season") != "2023"]
    rng = random.Random(seed)
    sample = rng.sample(pulls, n_side) + rng.sample(nops, n_side)
    bad = []
    for r in sample:
        tr = r["trailing"] if lg == "liiga" else r["trailing_name"]
        ivs = (liiga_raw_empty if lg == "liiga" else ahl_raw_empty)(r["season"], r["game_id"], tr)
        o, c = r["opened_secs"] + P3, r["closed_secs"] + P3
        raw_secs = {u for b, e in ivs for u in range(max(b, o), min(e, c))}
        dp_excused = r.get("dp_only_empty") or any(s.get("dp_artifact") for s in r.get("pull_segments", []))
        if bool(r["pulled"]) != bool(raw_secs) and not (raw_secs and dp_excused):
            bad.append((r["season"], r["game_id"], f'pulled={r["pulled"]} raw_any={bool(raw_secs)}'))
        if r["pulled"] and r.get("pull_evidence_secs") is not None and raw_secs \
                and not r.get("synthetic_pull_evidence") \
                and r["pull_evidence_secs"] + P3 not in raw_secs:
            bad.append((r["season"], r["game_id"], f'evidence {r["pull_evidence_secs"]+P3} not raw-empty'))
    return sample, bad

if __name__ == "__main__":
    lg = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    sample, bad = audit(lg, n, seed)
    print(f"{lg}: checked {len(sample)}, disagreements {len(bad)}")
    for b in bad:
        print(" ", b)
    sys.exit(1 if bad else 0)
