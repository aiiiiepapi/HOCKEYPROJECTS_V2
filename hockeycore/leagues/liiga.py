"""
hockeycore.leagues.liiga — Liiga adapter: game JSON → gap instances.

Verified conventions (raw data, 2026-07-25):
- gameTime = cumulative SECONDS; periods explicit; P3 = 2400-3600; P4 = OT.
- goalEvents per team side; goalTypes: YV=powerplay, AV=shorthanded,
  TM=empty-net, RL0/VT etc.
- goalKeeperEvents per team: intervals with emptyNet 1/0, beginTime/endTime —
  exact segment-level pull truth (best of the three leagues).
- penaltyEvents: penaltyBegintime/penaltyEndtime explicit.

API VERSION QUIRK (verified 2026-08-01, shadow-check v1 vs v2 on identical
games): /api/v2 responses nest penaltyEvents under the OPPOSITE team relative
to /api/v1 — v1 lists a penalty under the penalized team, v2 under the team it
benefits. Proven two ways: exact array swap on 4 v1/v2 pairs of the same game,
and 1603-vs-16 across all 1858 lake games on "which side's list holds the
minor that a YV (PP) goal terminates at the same second". Goal and goalkeeper
events are NOT swapped. Detection: v2 payloads carry root-level
homeTeamPlayers/awayTeamPlayers; v1 payloads do not. NOTE the field
goalKeeperChanges exists in BOTH versions — it is not a version marker.
"""
import json
from pathlib import Path

P3_START, P3_END = 2400, 3600


def parse_game(path):
    raw = json.load(open(path))
    g = raw["game"]
    v2_api = "homeTeamPlayers" in raw or "awayTeamPlayers" in raw
    out = {"id": g["id"], "home": g["homeTeam"]["teamName"] or g["homeTeam"]["teamPlaceholder"],
           "away": g["awayTeam"]["teamName"] or g["awayTeam"]["teamPlaceholder"],
           "goals": [], "empty": {"home": [], "away": []}, "penalties": []}
    for side, key in (("home", "homeTeam"), ("away", "awayTeam")):
        t = g[key]
        for e in t.get("goalEvents") or []:
            if any(x.endswith("0") for x in (e.get("goalTypes") or [])):
                continue  # VT0/RL0 = disallowed / failed penalty shot — NOT goals (verified vs official period totals)
            out["goals"].append({"t": e["gameTime"], "side": side,
                                 "period": e.get("period"),
                                 "en": "TM" in (e.get("goalTypes") or []),
                                 "types": e.get("goalTypes") or []})
        for e in t.get("goalKeeperEvents") or []:
            if e.get("emptyNet") == 1:
                out["empty"][side].append((e["beginTime"], e["endTime"]))
        pen_side = side if not v2_api else ("away" if side == "home" else "home")
        for e in t.get("penaltyEvents") or []:
            out["penalties"].append({"side": pen_side, "t": e["gameTime"],
                                     "begin": e.get("penaltyBegintime", e["gameTime"]),
                                     "end": e.get("penaltyEndtime", e["gameTime"] + 120)})
    out["goals"].sort(key=lambda e: e["t"])
    return out


def extract_instances(g, target_gap=3):
    hs = as_ = 0
    score = []
    for e in g["goals"]:
        if e["side"] == "home":
            hs += 1
        else:
            as_ += 1
        score.append((e["t"], hs, as_, e))
    # entering P3
    h = a = 0
    for t, hh, aa, _ in score:
        if t < P3_START:
            h, a = hh, aa
    instances = []
    cur = None

    def open_inst(t, creating, h_, a_):
        return {"opened_secs": max(t - P3_START, 0),
                "creating_t": creating,
                "trailing": "home" if h_ < a_ else "away"}

    if abs(h - a) == target_gap:
        cur = open_inst(P3_START, None, h, a)
    for t, hh, aa, e in score:
        if t < P3_START or t > P3_END or e.get("period", 3) != 3:
            if t >= P3_START:
                continue
            h, a = hh, aa
            continue
        newgap, oldgap = abs(hh - aa), abs(h - a)
        if cur is not None and newgap != target_gap:
            cur["closed_secs"] = t - P3_START
            cur["closed_reason"] = "narrowed" if newgap < oldgap else "widened"
            cur["closing_t"] = t
            instances.append(cur)
            cur = None
        elif cur is None and newgap == target_gap:
            cur = open_inst(t, t, hh, aa)
        h, a = hh, aa
    if cur is not None:
        cur["closed_secs"] = 1200
        cur["closed_reason"] = "end_of_game"
        cur["closing_t"] = None
        instances.append(cur)

    for n, inst in enumerate(instances, 1):
        inst["n"] = n
        o, c = inst["opened_secs"], inst["closed_secs"]
        tn = inst["trailing"]
        inst["trailing_name"] = g[tn]
        gw = []
        for e in g["goals"]:
            tp3 = e["t"] - P3_START
            if e["t"] == inst["creating_t"]:
                continue
            if o <= tp3 <= c and e.get("period", 3) == 3:
                if inst["closing_t"] is not None and tp3 == c and e["t"] != inst["closing_t"]:
                    continue
                gw.append({"secs": tp3, "by_trailer": e["side"] == tn,
                           "en": e["en"], "closes": e["t"] == inst["closing_t"]})
        inst["goals_in_window"] = gw
        segs = []
        for b, e2 in sorted(g["empty"][tn]):
            bp, ep = b - P3_START, e2 - P3_START
            if bp >= o and bp < c:                      # starts inside window
                segs.append({"empty_from": bp, "empty_until": min(ep, c)})
            elif bp < o and ep >= o:
                inst["carryover_empty_at_open"] = True  # noted, not a pull
        inst["pull_segments"] = segs
        inst["pulled"] = bool(segs)
        inst["pull_evidence_secs"] = segs[0]["empty_from"] if segs else None
        if segs:
            t0 = segs[0]["empty_from"] + P3_START
            leader = "home" if tn == "away" else "away"
            lead_box = sum(1 for p in g["penalties"] if p["side"] == leader and p["begin"] <= t0 < p["end"])
            trail_box = sum(1 for p in g["penalties"] if p["side"] == tn and p["begin"] <= t0 < p["end"])
            inst["pull_classification"] = "pp_pull" if lead_box > trail_box else "pull"
        else:
            inst["pull_classification"] = None
    return instances


def scan_dir(d):
    out = {}
    for f in sorted(Path(d).glob("game_2026_*.json")):
        num = int(f.stem.split("_")[-1])
        if num > 480:  # 55xxx ids = playoffs/other
            continue
        try:
            g = parse_game(f)
            out[num] = (g, extract_instances(g, 3))
        except Exception as e:
            out[num] = (None, f"ERROR {e!r}")
    return out
