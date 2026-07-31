"""
hockeycore.gap.extract — 3rd-period gap-window extraction (NHL schema).

Implements docs/CALCULATIONS.md §0-§1 exactly. Written fresh from raw pbp
facts (verified against ground truth games); v1 code not consulted.

Definitions implemented:
- Instance: maximal interval in P3 with |gap| == target_gap (2, 3 or 4).
- Gap-creating goal excluded from the scoring window; gap-closing included.
- Per-second state via carry-forward of situationCode from ordered events.
- Delayed-penalty windows: from the delayed-penalty event until the next
  play-stopping event (penalty/stoppage/goal/faceoff/period-end). Trailing
  net-empty seconds inside such a window are DP_off — never pull time.
- Pull segment: maximal run of trailing-net-empty seconds not DP_off.
  Evidence second = first second of the segment (= its first event's time).
"""
import json
from pathlib import Path

STOPPING = {"penalty", "stoppage", "goal", "faceoff", "period-end", "game-end"}


def _secs(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def load_pbp(path):
    return json.load(open(path, encoding="utf-8-sig"))


def game_frame(pbp):
    """Ordered P3 event frame + entering score + team mapping."""
    away_id, home_id = pbp["awayTeam"]["id"], pbp["homeTeam"]["id"]
    a = h = 0
    p3 = []
    for i, p in enumerate(pbp.get("plays", [])):
        per = p.get("periodDescriptor", {}).get("number", 0)
        if p.get("typeDescKey") == "goal" and per <= 2:
            a, h = p["details"]["awayScore"], p["details"]["homeScore"]
        if per == 3:
            p3.append({
                "i": i, "eventId": p.get("eventId"),
                "type": p.get("typeDescKey", ""),
                "t": _secs(p.get("timeInPeriod", "00:00")),
                "sit": str(p.get("situationCode", "") or ""),
                "details": p.get("details", {}) or {},
            })
    p3.sort(key=lambda e: (e["t"], e["i"]))  # stable: sequence resolves ties
    return {
        "game_id": pbp.get("id"),
        "away": pbp["awayTeam"]["abbrev"], "home": pbp["homeTeam"]["abbrev"],
        "away_id": away_id, "home_id": home_id,
        "p3_entry": (a, h), "events": p3,
    }


def delayed_penalty_windows(events):
    """[(start_t, end_t)] from each delayed-penalty event to the next FACEOFF.
    (2026-07-31 fix, credit fresh-eyes audit: play can only resume at a
    faceoff; whistles/goals inside the window still carry auto-6v5 codes.
    end_t is exclusive-of-faceoff: the faceoff itself is decision-relevant.
    Old next-stopping-event rule let delayed-penalty goals seconds after the
    call register as pull evidence — 3 confirmed phantoms in 4 seasons.)"""
    wins = []
    for k, e in enumerate(events):
        if e["type"] != "delayed-penalty":
            continue
        end = 1200
        for e2 in events[k + 1:]:
            if e2["type"] == "faceoff":
                end = e2["t"]
                break
        # +1: the resumption faceoff shares the clock second with any goal that
        # ended the delayed penalty (stop clock) — the window must cover it.
        wins.append((e["t"], end + 1))
    return wins


def sit_at(events, u):
    """situationCode in force at second u (last event at t <= u; ties by order)."""
    sit = None
    for e in events:
        if e["t"] > u:
            break
        if len(e["sit"]) == 4:
            sit = e["sit"]
    return sit or "1551"


def extract_instances(pbp, target_gap=3):
    g = game_frame(pbp)
    ev = g["events"]
    dp_wins = delayed_penalty_windows(ev)
    a, h = g["p3_entry"]

    # build gap timeline from P3 goals
    goals = [e for e in ev if e["type"] == "goal"]
    instances = []
    cur = None  # open instance dict

    def open_inst(t, creating_event, a_, h_):
        trail_home = h_ < a_
        return {
            "opened_secs": t,
            "creating_event": creating_event,
            "trailing": g["home"] if trail_home else g["away"],
            "trailing_is_home": trail_home,
            "score_at_open": (a_, h_),
        }

    if abs(a - h) == target_gap:
        cur = open_inst(0, None, a, h)
    for goal in goals:
        na, nh = goal["details"]["awayScore"], goal["details"]["homeScore"]
        newgap, oldgap = abs(na - nh), abs(a - h)
        if cur is not None and newgap != target_gap:
            cur["closed_secs"] = goal["t"]
            cur["closed_reason"] = "narrowed" if newgap < oldgap else "widened"
            cur["closing_event"] = goal["eventId"]
            instances.append(cur)
            cur = None
        elif cur is None and newgap == target_gap:
            cur = open_inst(goal["t"], goal["eventId"], na, nh)
        a, h = na, nh
    if cur is not None:
        cur["closed_secs"] = 1200
        cur["closed_reason"] = "end_of_game"
        cur["closing_event"] = None
        instances.append(cur)

    # per-instance detail
    for n, inst in enumerate(instances, 1):
        inst["n"] = n
        o, c = inst["opened_secs"], inst["closed_secs"]
        gidx = 3 if inst["trailing_is_home"] else 0

        # goals in window: strictly after creating event, up to & incl. closing
        gw = []
        for goal in goals:
            if goal["eventId"] == inst["creating_event"]:
                continue
            if o <= goal["t"] <= c:
                if inst["closing_event"] is not None and goal["t"] == c and goal["eventId"] != inst["closing_event"]:
                    continue  # same-second goal that belongs to the next state
                sit = goal["sit"] if len(goal["sit"]) == 4 else sit_at(ev, goal["t"])
                gw.append({
                    "secs": goal["t"], "event": goal["eventId"],
                    "team_id": goal["details"].get("eventOwnerTeamId"),
                    "en": sit[gidx] == "0",
                    "closes": goal["eventId"] == inst["closing_event"],
                })
        inst["goals_in_window"] = gw

        # per-second net-empty scan for the trailing side
        segs = []
        run = None
        dp_secs = []
        for u in range(o, c):
            sit = sit_at(ev, u)
            empty = len(sit) == 4 and sit[gidx] == "0"
            in_dp = any(s <= u < e2 for s, e2 in dp_wins)
            if empty and in_dp:
                dp_secs.append(u)
                empty = False  # DP_off — never pull time
            if empty and run is None:
                run = [u, u]
            elif empty:
                run[1] = u
            elif run is not None:
                segs.append({"empty_from": run[0], "empty_until": u})
                run = None
        if run is not None:
            segs.append({"empty_from": run[0], "empty_until": c})
        # Closing-goal own-code rule (CALCULATIONS §4 / Bug-A lesson): the
        # closing goal's OWN situation code is authoritative for second c.
        # If it shows the trailing net empty and no segment reaches c, the
        # pull's first (and only) evidence is the closing goal itself.
        if inst["closing_event"] is not None:
            cg = next((x for x in ev if x["eventId"] == inst["closing_event"]), None)
            if cg and len(cg["sit"]) == 4 and cg["sit"][gidx] == "0":
                # 2026-07-31 (fresh-eyes audit): a closing goal scored during a
                # delayed-penalty window shows the net auto-empty — that is the
                # automatic extra attacker, not a pull. 3 confirmed phantoms.
                in_dp = any(s <= c < e2 for s, e2 in dp_wins)
                if not in_dp and not any(s["empty_until"] >= c for s in segs):
                    segs.append({"empty_from": c, "empty_until": c,
                                 "evidence_is_closing_goal": True})
        inst["dp_off_secs"] = len(dp_secs)
        inst["dp_off_range"] = (dp_secs[0], dp_secs[-1] + 1) if dp_secs else None
        inst["pull_segments"] = segs
        inst["pulled"] = bool(segs)

        if segs:
            first = segs[0]
            t0 = first["empty_from"]
            if first.get("evidence_is_closing_goal"):
                cg = next(x for x in ev if x["eventId"] == inst["closing_event"])
                sit0 = cg["sit"]
            else:
                sit0 = sit_at(ev, t0)
            trail_sk = int(sit0[2] if inst["trailing_is_home"] else sit0[1])
            lead_sk = int(sit0[1] if inst["trailing_is_home"] else sit0[2])
            if lead_sk <= 4:
                cls = "pp_pull"
            elif trail_sk <= lead_sk:
                cls = "sh_pull"
            else:
                cls = "pull"
            inst["pull_evidence_secs"] = t0
            inst["pull_classification"] = cls
            last = segs[-1]
            # end reason of final segment
            end_t = last["empty_until"]
            reason = "gap_end" if end_t >= c and inst["closed_reason"] == "end_of_game" else None
            if reason is None:
                en_goal = next((x for x in gw if x["secs"] == end_t or (x["en"] and last["empty_from"] <= x["secs"] <= end_t)), None)
                if en_goal and en_goal["en"]:
                    reason = "en_goal_against" if en_goal["team_id"] != (g["home_id"] if inst["trailing_is_home"] else g["away_id"]) else "scored_during_pull"
                elif any(x["secs"] == end_t and x["closes"] for x in gw):
                    x = next(x for x in gw if x["secs"] == end_t and x["closes"])
                    trail_id = g["home_id"] if inst["trailing_is_home"] else g["away_id"]
                    reason = "scored" if x["team_id"] == trail_id else "goal_against"
                else:
                    reason = "goalie_returned"
            inst["pull_end"] = {"secs": end_t, "reason": reason}
        else:
            inst["pull_evidence_secs"] = None
            inst["pull_classification"] = "delayed_penalty" if dp_secs else None
    for inst in instances:
        inst.pop("trailing_is_home", None)
    return g, instances
