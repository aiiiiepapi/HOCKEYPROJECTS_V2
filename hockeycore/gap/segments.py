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
        inst["pull_segments"] = segs
        inst["pulled"] = bool(segs)
        inst["pull_evidence_secs"] = segs[0]["empty_from"] if segs else None
        if segs and all(x.get("synthetic") for x in segs):
            inst["synthetic_pull_evidence"] = True      # timing not usable
        if segs:
            t0 = segs[0]["empty_from"] + P3_START
            leader = "home" if tn == "away" else "away"
            lead_box = sum(1 for p in g["penalties"] if p["side"] == leader and p["begin"] <= t0 < p["end"])
            trail_box = sum(1 for p in g["penalties"] if p["side"] == tn and p["begin"] <= t0 < p["end"])
            inst["pull_classification"] = "pp_pull" if lead_box > trail_box else "pull"
        else:
            inst["pull_classification"] = None
    return instances
