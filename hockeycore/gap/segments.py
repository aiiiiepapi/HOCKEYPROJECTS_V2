"""
hockeycore.gap.segments — shared 3-goal-gap instance engine for leagues whose
adapters produce the INTERVAL game dict (rule 15: gap detection exists once):

    {"id", "home", "away",
     "goals":   [{"t": cumulative_secs, "side": "home"|"away", "period": int,
                  "en": bool, "types": [...]}, ...]   (sorted by t),
     "empty":   {"home": [(begin, end), ...], "away": [...]},   # net-empty
     "penalties": [{"side", "t", "begin", "end"}, ...]}         # box windows

Times are cumulative game seconds; P3 = [2400, 3600]. Used by liiga and ahl.
(NHL uses the per-second gap engine in hockeycore/gap/extract.py — its raw
data is shift-based, not interval-based. EIHL keeps its HTML-specific engine.)

Extracted verbatim from hockeycore/leagues/liiga.py (GT-gated) on 2026-08-01;
the liiga gates pin these semantics.
"""

P3_START, P3_END = 2400, 3600


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
        for tup in sorted(g["empty"][tn], key=lambda x: (x[0], x[1])):
            b, e2 = tup[0], tup[1]
            syn = len(tup) > 2 and tup[2] == "synthetic"
            bp, ep = b - P3_START, e2 - P3_START
            if bp >= o and bp < c:                      # starts inside window
                seg = {"empty_from": bp, "empty_until": min(ep, c)}
                if syn:
                    seg["synthetic"] = True             # EN-goal evidence, timing unknown
                segs.append(seg)
            elif bp < o and ep >= o:
                inst["carryover_empty_at_open"] = True  # noted, not a pull
        # ---- segment end context + delayed-penalty artifact rule ----------
        # Measured 2026-08-01 (AHL 4 seasons): segments ending at a whistled
        # penalty ON THE LEADER with duration <=25s are delayed-penalty
        # extra-attacker moments (median 10s; 85/98 <=25s), not pull
        # decisions. They are net-empty time but NOT pull evidence. Long
        # penalty_on_leader segments (>25s) = real pulls that drew a call.
        opp_side = "home" if tn == "away" else "away"
        for seg in segs:
            e_t = seg["empty_until"] + P3_START
            ctx = "returned_no_event"
            for gl in g["goals"]:
                if abs(gl["t"] - e_t) <= 1:
                    ctx = ("scored_6v5" if gl["side"] == tn
                           else ("ate_ENG" if gl["en"] else "goal_against"))
                    break
            else:
                if seg["empty_until"] >= 1199:
                    ctx = "horn"
                else:
                    for pnl in g["penalties"]:
                        if abs(pnl["t"] - e_t) <= 2:
                            ctx = ("penalty_on_leader" if pnl["side"] == opp_side
                                   else "penalty_on_trailer")
                            break
            seg["end_context"] = ctx
            dur = seg["empty_until"] - seg["empty_from"]
            if seg.get("synthetic"):
                pass
            elif ctx == "penalty_on_leader" and dur <= 25:
                # ruling 17: measured dp extra-attacker moments (median 10s)
                seg["dp_artifact"] = True
            elif ctx == "penalty_on_leader" and seg["empty_from"] < 720 and dur <= 60:
                # ruling 17b-i (2026-08-02): NHL dp truth (n=6,594 possessions)
                # shows 8.7% exceed 25s — duration alone cannot separate dp
                # from pulls. But real down-3 pulls before P3 12:00 are ~0
                # short ones (all 5 verified early pulls are 120s+ continuous;
                # 285-pull audit). Short early leader-whistle enders are dp.
                # Hand-verified: 1024680, 1026980, 1027518, 1027594, 1027844,
                # 1028774 (all 26-51s, P3 0:33-11:03, same-goalie return at
                # the whistle to the second).
                seg["dp_artifact"] = True
            elif (ctx == "scored_6v5" and seg["empty_from"] < 720 and dur <= 25
                  and not any(abs(pnl["t"] - (seg["empty_until"] + P3_START)) <= 2
                              for pnl in g["penalties"])):
                # ruling 17b-ii: dp GOAL — non-offending (trailing) team scores
                # during the delayed call, the minor is WIPED, so no penalty
                # event exists. Not a pull decision; goal stays on the
                # scoreboard/gap logic. Hand-verified: 1025867 (P3 3:07,
                # 19s, scored, no penalty assessed).
                seg["dp_artifact"] = True
            elif seg["empty_from"] < 720 and dur <= 25:
                # ruling 17b-iii: whistle-lag — the leader's penalty is
                # assessed INSIDE the segment near its start (feed lag between
                # assessment row and the goalie-return row). Hand-verified:
                # 1028800 (seg 399-409, leader penalty at 403, SH-ENG during
                # the dp counted as "ate ENG").
                for pnl in g["penalties"]:
                    tp3 = pnl["t"] - P3_START
                    if (pnl["side"] == opp_side
                            and seg["empty_from"] <= tp3 <= seg["empty_from"] + 10
                            and tp3 < seg["empty_until"]):
                        seg["dp_artifact"] = True
                        break
        ev_segs = [x for x in segs if not x.get("dp_artifact")]
        inst["pull_segments"] = segs
        inst["pulled"] = bool(ev_segs)
        inst["pull_evidence_secs"] = ev_segs[0]["empty_from"] if ev_segs else None
        if ev_segs and all(x.get("synthetic") for x in ev_segs):
            inst["synthetic_pull_evidence"] = True      # timing not usable
        if segs and not ev_segs:
            inst["dp_only_empty"] = True                # net was empty, but only via dp
        if ev_segs:
            t0 = ev_segs[0]["empty_from"] + P3_START
            leader = "home" if tn == "away" else "away"
            # Misconducts (adapter-flagged) never make a team shorthanded —
            # excluding them from strength accounting (2026-08-02 fix: 8 AHL
            # + 1 Liiga classifications flipped on phantom 10-min windows,
            # e.g. 1026058: trailing misconduct masked a leader minor -> a
            # 6v4 pp_pull was counted as an EV pull).
            strength = [p for p in g["penalties"] if not p.get("misconduct")]
            lead_box = sum(1 for p in strength if p["side"] == leader and p["begin"] <= t0 < p["end"])
            trail_box = sum(1 for p in strength if p["side"] == tn and p["begin"] <= t0 < p["end"])
            inst["pull_classification"] = "pp_pull" if lead_box > trail_box else "pull"
        else:
            inst["pull_classification"] = None
    return instances
