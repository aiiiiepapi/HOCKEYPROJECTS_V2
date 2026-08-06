#!/usr/bin/env python3
"""
audit_interval_random.py — seeded random instance audit for interval leagues
(AHL / Liiga): re-verifies pulls and no-pulls DIRECTLY against the raw lake
goalie channels, bypassing the adapter state machine (rule 0/6).

Usage: python3 tools/audit_interval_random.py {ahl|liiga|mestis|shl} [n_per_side] [seed]
Exit code 0 = no disagreements. Prints each disagreement.
First run (liiga, seed 20260802, 30+30): 0 disagreements, 2026-08-02.
AHL twin (seed 20260801, 30+30): 0 disagreements, 2026-08-01 (ahl_batch1.md).
Mestis (seed 20260803, 30+30): audits against the POIS stat-line channel —
fully independent of the event channel the adapter parses (the two channels
are redundant per docs/MESTIS_LAKE_VERIFICATION.md).
SHL (seed 20260807): audits against the www.shl.se gameday play-by-play
goalkeeper events — an independent recorder from the swe federation Events
channel the adapter parses (docs/SHL_LAKE_VERIFICATION.md adjudication 1).
The pbp archive starts 2023-24, so season 2023 is EXCLUDED from the sample
(no second channel exists — like liiga 2023). Only 27 pulled instances
exist in 2024-2026, so the pull side is capped at all of them and the
no-pull side is topped up to keep the total at 2*n_side (27+33 at n=30).
pbp rules (binding, from the Manager's adjudication): dedupe goalkeeper
events by (period, time, team) keeping the latest revision; end-of-game
GK-out rows are bookkeeping (they fall at the period boundary and produce
zero-length intervals here, so no special-casing is needed).
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

def mestis_raw_empty(season, gid, trailing):
    """Net-empty intervals from the goalie STAT-LINE 'pois:'/'out:' channel
    (seuranta Maalivahdit section + tilastot) — independent of the event
    rows the adapter consumes. Side attribution via the home/away cells."""
    import re, html as _h
    txt = ""
    for suf in ("seuranta", "tilastot"):
        p = Path(f"/home/claude/work/mestis_lake/mestis/{season}/game_{season}_{gid}_{suf}.html")
        if p.exists():
            txt += p.read_text(encoding="utf-8", errors="replace")
    out = []
    for row in re.finditer(r"<tr[^>]*>(.*?)</tr>", txt, re.S):
        for cls, c in re.findall(r'<t[dh][^>]*class="(home|away)"[^>]*>(.*?)</t[dh]>',
                                 row.group(1), re.S):
            if cls != trailing:
                continue
            plain = re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", c)))
            m = re.search(r"(?:pois|out):\s*([\d:.,\s\-–]+)", plain)
            if not m:
                continue
            for iv in m.group(1).split(","):
                iv = iv.strip().replace("–", "-")
                if not iv:
                    continue
                b, e = iv.split("-")
                def s(x):
                    mm, ss = x.strip().replace(".", ":").split(":")
                    return int(mm) * 60 + int(ss)
                out.append((s(b), min(s(e), 3600)))
    return sorted(set(out))


def shl_raw_empty(season, gid, trailing):
    """Net-empty intervals from the shl.se gameday pbp goalkeeper events
    (2024+ only) — independent recorder from the swe Events channel the
    adapter parses. Per-period elapsed clock -> cumulative; dedupe by
    (period, time, team) keeping the latest revision (adjudication rule)."""
    ev = json.load(open(f"/home/claude/work/shl_lake/shl/{season}/game_{season}_{gid}_pbp.json"))
    # Dedupe key REFINED from the adjudication's (period, time, team): the
    # player must be part of it — revision dupes repeat the SAME player
    # (774444 P3 17:55/18:16), while a same-second Out+In pair of DIFFERENT
    # goalies is a period-break/stoppage SWAP (882274 P3 00:00 Clara out /
    # Lindbäck in) that (period, time, team) would collapse into a phantom
    # open. OUT-first at the same second → swaps become zero-length.
    best = {}
    for e in ev:
        if e.get("type") != "goalkeeper":
            continue
        place = (e.get("eventTeam") or {}).get("place")
        per = int(e.get("period") or 0)
        if place != trailing or per > 3:
            continue
        mm, ss = str(e["time"]).split(":")
        t = (per - 1) * 1200 + int(mm) * 60 + int(ss)
        key = (per, t, (e.get("player") or {}).get("playerId"))
        if key not in best or int(e.get("revision") or 0) >= int(best[key][0]):
            best[key] = (int(e.get("revision") or 0), bool(e.get("isEntering")))
    rows = sorted(((per, t, best[(per, t, pid)][1]) for (per, t, pid) in best),
                  key=lambda r: (r[0], r[1], r[2]))          # OUT-first at same second
    out, open_t, open_per = [], None, None
    for per, t, entering in rows:
        if open_t is not None and per != open_per:
            out.append((open_t, open_per * 1200)); open_t = None
        if not entering and open_t is None:
            open_t, open_per = t, per
        elif entering and open_t is not None:
            out.append((open_t, t)); open_t = None
    if open_t is not None:
        out.append((open_t, min(open_per * 1200, 3600)))
    return [(b, e) for b, e in out if e > b]


def audit(lg, n_side=30, seed=None):
    seed = seed or {"ahl": 20260801, "liiga": 20260802, "mestis": 20260803,
                    "shl": 20260807}[lg]
    rows = json.load(open(ROOT / "data" / "derived" / f"{lg}_instances_gap3.json"))
    pulls = [r for r in rows if r.get("pulled")
             and not (lg == "shl" and r.get("season") == "2023")]
    nops = [r for r in rows if r.get("pulled") is False
            and not (lg == "liiga" and r.get("season") == "2023")
            and not (lg == "shl" and r.get("season") == "2023")]
    rng = random.Random(seed)
    n_pull = min(n_side, len(pulls))          # shl 2024+: 27 pulls exist, take all
    sample = rng.sample(pulls, n_pull) + rng.sample(nops, 2 * n_side - n_pull)
    bad = []
    for r in sample:
        if lg == "mestis":
            tr = r["trailing"]                       # side string: pois lines carry side cells
            ivs = mestis_raw_empty(r["season"], r["game_id"], tr)
        elif lg == "shl":
            tr = r["trailing"]                       # pbp eventTeam.place is home/away
            ivs = shl_raw_empty(r["season"], r["game_id"], tr)
        elif lg == "liiga":
            tr = r["trailing"]
            ivs = liiga_raw_empty(r["season"], r["game_id"], tr)
        else:
            tr = r["trailing_name"]
            ivs = ahl_raw_empty(r["season"], r["game_id"], tr)
        o, c = r["opened_secs"] + P3, r["closed_secs"] + P3
        raw_secs = {u for b, e in ivs for u in range(max(b, o), min(e, c))}
        dp_excused = r.get("dp_only_empty") or any(s.get("dp_artifact") for s in r.get("pull_segments", []))
        # Carryover excuse: in-window raw seconds coming ONLY from intervals
        # that BEGAN before the window opened match the engine's GT-gated
        # semantics (carryover_empty_at_open is noted, never pull evidence —
        # segments.py counts only bp >= o). SHL 774518: both channels agree
        # on (3326,3580); the ENG-created window opens at 3544 inside it.
        carry_excused = (r.get("carryover_empty_at_open")
                         and not any(b >= o and b < c for b, e in ivs))
        if bool(r["pulled"]) != bool(raw_secs) and not (raw_secs and (dp_excused or carry_excused)):
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
