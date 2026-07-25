"""
scan_gaps.py — independent 3-gap moment finder for trace-game SELECTION only.
Written from the raw pbp schema, not from v1 code. This is NOT the extraction
pipeline and produces no model data — it only helps choose which games to
hand-trace, and prints raw third-period event logs for manual tracing.

NHL pbp facts used (verified against raw JSONs):
- plays[].periodDescriptor.number, timeInPeriod "MM:SS" (elapsed within period)
- typeDescKey: goal, penalty, delayed-penalty, stoppage, etc.
- situationCode: 4 chars [awayGoalieIn][awaySkaters][homeSkaters][homeGoalieIn]
  goalie digit 0 = net empty for that side
- details.awayScore/homeScore on goal events = score AFTER the goal
"""
import json, sys, os
from pathlib import Path

def mmss_to_secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)

def load(path):
    j = json.load(open(path))
    return j

def third_period_events(j):
    return [p for p in j.get("plays", [])
            if p.get("periodDescriptor", {}).get("number") == 3]

def scan_game(path):
    j = load(path)
    gid = j.get("id")
    away, home = j["awayTeam"]["abbrev"], j["homeTeam"]["abbrev"]
    # score entering P3: last goal event before P3
    a = h = 0
    for p in j.get("plays", []):
        if p.get("periodDescriptor", {}).get("number", 9) >= 4:
            break
        if p.get("typeDescKey") == "goal" and p["periodDescriptor"]["number"] <= 2:
            a = p["details"]["awayScore"]; h = p["details"]["homeScore"]
    feats = {"game": gid, "away": away, "home": home, "p3_start": f"{a}-{h}",
             "instances": 0, "pull_evidence": False, "delayed_penalty_ev": False,
             "pp_during_gap": False, "multi": False, "late_open": False,
             "closed_by_trailer": False, "closed_by_leader": False}
    gap = abs(a - h)
    in_gap = gap == 3
    if in_gap:
        feats["instances"] = 1
    for p in third_period_events(j):
        t = mmss_to_secs(p.get("timeInPeriod", "0:00"))
        sit = str(p.get("situationCode", "") or "")
        if in_gap and len(sit) == 4:
            if sit[0] == "0" or sit[3] == "0":
                feats["pull_evidence"] = True
            if sit[1] != sit[2] and sit[0] != "0" and sit[3] != "0":
                feats["pp_during_gap"] = True
        if in_gap and p.get("typeDescKey") == "delayed-penalty":
            feats["delayed_penalty_ev"] = True
        if p.get("typeDescKey") == "goal":
            a2, h2 = p["details"]["awayScore"], p["details"]["homeScore"]
            newgap = abs(a2 - h2)
            if in_gap and newgap != 3:
                if newgap < 3: feats["closed_by_trailer"] = True
                else: feats["closed_by_leader"] = True
            if not in_gap and newgap == 3:
                feats["instances"] += 1
                if feats["instances"] > 1: feats["multi"] = True
                if t > 1200 - 180: feats["late_open"] = True
            in_gap = newgap == 3
            a, h = a2, h2
    return feats

def print_trace_log(path):
    """Condensed 3rd-period raw event log for manual hand-tracing."""
    j = load(path)
    away, home = j["awayTeam"]["abbrev"], j["homeTeam"]["abbrev"]
    a = h = 0
    for p in j.get("plays", []):
        if p.get("typeDescKey") == "goal" and p["periodDescriptor"]["number"] <= 2:
            a = p["details"]["awayScore"]; h = p["details"]["homeScore"]
    print(f"GAME {j.get('id')}  {away}(away) @ {home}(home)   entering P3: {a}-{h}")
    prev_sit = None
    for p in third_period_events(j):
        t = p.get("timeInPeriod", "?")
        typ = p.get("typeDescKey", "?")
        sit = str(p.get("situationCode", "") or "")
        eid = p.get("eventId", "?")
        d = p.get("details", {}) or {}
        show = False
        line = f"  {t} [{sit}] #{eid} {typ}"
        if typ == "goal":
            line += f" {d.get('awayScore')}-{d.get('homeScore')} team={d.get('eventOwnerTeamId')}"
            show = True
        elif typ in ("penalty", "delayed-penalty"):
            line += f" team={d.get('eventOwnerTeamId')} dur={d.get('duration')} {d.get('descKey','')}"
            show = True
        elif sit != prev_sit and len(sit) == 4:
            show = True  # any strength/goalie state change
        if show:
            print(line)
        if len(sit) == 4:
            prev_sit = sit
    ids = {j["awayTeam"]["id"]: away, j["homeTeam"]["id"]: home}
    print(f"  teamIds: {ids}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "log":
        print_trace_log(sys.argv[2])
    else:
        d = Path(sys.argv[1])
        out = []
        for f in sorted(d.glob("*_pbp.json")):
            try:
                out.append(scan_game(f))
            except Exception as e:
                print(f"SCAN ERROR {f.name}: {e}", file=sys.stderr)
        json.dump(out, open("scan_results.json", "w"), indent=1)
        n = len(out)
        print(f"scanned {n} games")
        for k in ["pull_evidence", "delayed_penalty_ev", "pp_during_gap",
                  "multi", "late_open", "closed_by_trailer", "closed_by_leader"]:
            print(f"  {k}: {sum(1 for o in out if o[k])}")
