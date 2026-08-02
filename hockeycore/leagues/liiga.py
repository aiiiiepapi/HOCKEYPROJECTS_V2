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
            beg = e.get("penaltyBegintime", e["gameTime"])
            end = e.get("penaltyEndtime", e["gameTime"] + 120)
            out["penalties"].append({"side": pen_side, "t": e["gameTime"],
                                     "begin": beg, "end": end,
                                     # >=10-min box time = misconduct class; no
                                     # strength effect (2026-08-02 fix, see
                                     # segments.py). Row kept as whistle marker.
                                     "misconduct": (end - beg) >= 600})
    out["goals"].sort(key=lambda e: e["t"])
    return out


from hockeycore.gap.segments import extract_instances  # shared engine (rule 15)


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
