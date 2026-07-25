"""
hockeycore.leagues.eihl — EIHL adapter: raw HTML game page → common events →
gap instances (same shape as NHL extractor output).

Verified conventions (from raw data, 2026-07-25):
- Clock: cumulative game time counting UP, "MM:SS", P3 = 40:00-60:00.
- Feed order: newest first (we re-sort ascending).
- Score in goal events: "T1:T2" where T1 = first team in <title> (home).
- Pulls are EXPLICIT: "Goalkeeper change for team X" + "Empty net";
  returns: "Goalkeeper change for team X" + "Incoming goalkeeper #N".
- No delayed-penalty events exist in this feed (0/200 files) — brief empty-net
  windows around opponent penalties are flagged, not classified dp.
"""
import re
from pathlib import Path

P3_START, P3_END = 2400, 3600


def _secs(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def parse_game(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    tm = re.search(r"<title>(.*?)\s*(\d+):(\d+)\s*(.*?)\s*\|", raw, re.S)
    team1, team2 = tm.group(1).strip(), tm.group(4).strip()
    text = re.sub(r"<[^>]+>", "|", raw)
    text = re.sub(r"\s+", " ", text)
    chunks = re.split(r"(\d{2}:\d{2})", text)
    events = []
    for i in range(1, len(chunks) - 1, 2):
        t = _secs(chunks[i])
        body = chunks[i + 1][:260]
        gm = re.search(r"Goal for team\s*\|?\s*([A-Za-z .'-]+?)\s*(\d+):(\d+)", body)
        if gm:
            events.append({"t": t, "type": "goal", "team": gm.group(1).strip(),
                           "s1": int(gm.group(2)), "s2": int(gm.group(3)), "k": i})
            continue
        pm = re.search(r"([A-Za-z .'-]+?),\s*(\d+)-minute penalty", body)
        if pm:
            events.append({"t": t, "type": "penalty", "team": pm.group(1).strip(),
                           "dur": int(pm.group(2)) * 60, "k": i})
            continue
        km = re.search(r"Goalkeeper change for team\s*\|?\s*([A-Za-z .'-]+)", body)
        if km:
            kind = "empty" if "Empty net" in body else ("in" if "Incoming" in body else "?")
            events.append({"t": t, "type": "gk", "team": km.group(1).strip(),
                           "kind": kind, "k": i})
    # feed is newest-first: ascending time, and same-time events reversed feed order
    events.sort(key=lambda e: (e["t"], -e["k"]))
    return {"team1": team1, "team2": team2, "events": events, "file": str(path)}


def _match(team_str, g):
    """map an event's team string to 1 or 2 (names sometimes truncated)."""
    for n, full in ((1, g["team1"]), (2, g["team2"])):
        if team_str and (team_str in full or full in team_str):
            return n
    # fallback: last word match (e.g. 'Storm')
    for n, full in ((1, g["team1"]), (2, g["team2"])):
        if team_str.split()[-1] in full:
            return n
    return None


def extract_instances(g, target_gap=3):
    ev = g["events"]
    goals = [e for e in ev if e["type"] == "goal"]
    # score entering P3
    s1 = s2 = 0
    for e in goals:
        if e["t"] < P3_START:
            s1, s2 = e["s1"], e["s2"]
    instances = []
    cur = None

    def open_inst(t, creating_k, s1_, s2_):
        trailing = 2 if s2_ < s1_ else 1
        return {"opened_secs": max(t - P3_START, 0), "creating_k": creating_k,
                "trailing": g["team2"] if trailing == 2 else g["team1"],
                "trailing_n": trailing}

    if abs(s1 - s2) == target_gap:
        cur = open_inst(P3_START, None, s1, s2)
    for e in goals:
        if e["t"] < P3_START or e["t"] > P3_END:
            continue
        newgap, oldgap = abs(e["s1"] - e["s2"]), abs(s1 - s2)
        if cur is not None and newgap != target_gap:
            cur["closed_secs"] = e["t"] - P3_START
            cur["closed_reason"] = "narrowed" if newgap < oldgap else "widened"
            cur["closing_k"] = e["k"]
            instances.append(cur); cur = None
        elif cur is None and newgap == target_gap:
            cur = open_inst(e["t"], e["k"], e["s1"], e["s2"])
        s1, s2 = e["s1"], e["s2"]
    if cur is not None:
        cur["closed_secs"] = 1200
        cur["closed_reason"] = "end_of_game"
        cur["closing_k"] = None
        instances.append(cur)

    for n, inst in enumerate(instances, 1):
        inst["n"] = n
        o, c = inst["opened_secs"], inst["closed_secs"]
        tn = inst.pop("trailing_n")
        # goals in window (creating excluded, closing included)
        gw = []
        for e in goals:
            if e["k"] == inst["creating_k"]:
                continue
            tp3 = e["t"] - P3_START
            if o <= tp3 <= c and (inst["closing_k"] is None or tp3 < c or e["k"] == inst["closing_k"]):
                gw.append({"secs": tp3, "team": e["team"],
                           "by_trailer": _match(e["team"], g) == tn,
                           "closes": e["k"] == inst["closing_k"]})
        inst["goals_in_window"] = gw
        # pull segments from explicit gk events of the trailing side
        segs = []
        open_seg = None
        # establish state at window open (a pull may already be on — carryover NOT counted, same rule as NHL)
        for e in ev:
            if e["type"] != "gk" or _match(e["team"], g) != tn:
                continue
            tp3 = e["t"] - P3_START
            if tp3 < o or tp3 > c:
                continue
            if e["kind"] == "empty" and open_seg is None:
                open_seg = tp3
            elif e["kind"] == "in" and open_seg is not None:
                segs.append({"empty_from": open_seg, "empty_until": tp3})
                open_seg = None
        if open_seg is not None:
            segs.append({"empty_from": open_seg, "empty_until": c})
        inst["pull_segments"] = segs
        inst["pulled"] = bool(segs)
        inst["pull_evidence_secs"] = segs[0]["empty_from"] if segs else None
        # EN flag on goals: leader goal while trailing net empty
        for x in gw:
            x["en"] = (not x["by_trailer"]) and any(
                s["empty_from"] <= x["secs"] <= s["empty_until"] for s in segs)
        # pp_pull: leader penalty active at pull evidence (minor windows, goal-terminated)
        if segs:
            t0 = segs[0]["empty_from"] + P3_START
            active = False
            for p in (e for e in ev if e["type"] == "penalty"):
                if _match(p["team"], g) == tn:
                    continue  # penalty on trailer doesn't grant them PP
                end = p["t"] + p["dur"]
                for e in goals:  # first goal by trailer inside window ends minor
                    if p["t"] < e["t"] < end and _match(e["team"], g) == tn and p["dur"] == 120:
                        end = e["t"]; break
                if p["t"] <= t0 < end:
                    active = True; break
            inst["pull_classification"] = "pp_pull" if active else "pull"
        else:
            inst["pull_classification"] = None
    return instances


def scan_dir(d):
    """all regular-season main pages -> per-game instance lists."""
    out = {}
    for f in sorted(Path(d).glob("game_*.html")):
        name = f.name
        if any(sfx in name for sfx in ("_gamesheet", "_stats", "_lineups", "_team_stats", "_tracking")):
            continue
        gid = int(name.split("_")[1])
        if not (4713 <= gid <= 4982):
            continue
        try:
            g = parse_game(f)
            out[gid] = (g, extract_instances(g, 3))
        except Exception as e:
            out[gid] = (None, f"ERROR {e}")
    return out
