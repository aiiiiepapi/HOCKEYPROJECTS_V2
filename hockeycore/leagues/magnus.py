"""
hockeycore.leagues.magnus — Ligue Magnus adapter (FFHG PDF sheets -> the
INTERVAL game dict consumed by gap/segments.py; rule 15).

Parsing is coordinate-based (see tools/magnus_parse_proto.py provenance and
docs/MAGNUS_DATA_GAPS.md for the precision doctrine). Key facts:
- Coaches ARE on the sheet (Entraîneur principal) — game-level attribution.
- No explicit goalie events: net-empty intervals are INFERRED from the
  Gardien-en-jeu TOI totals, anchored per the four cases (EN-against goal /
  own goal with no GB in J+ / own penalty début / horn). Deterministic
  single-anchor fits produce exact intervals; anything else flags.
- EN authority = Joueurs lists (CV flag recorded as weak signal only).
- Strength authority = penalty Début/Fin windows; >=10min rows flagged
  misconduct (no strength effect), consistent with segments.py.
- sheet_empty (cancelled games) and OT (duration from stints) handled.
GT: tests/ground_truth_magnus.json (batch 0). Pull-positive in-window logic
must be re-gated on batch 1 from the full lake before ledgers ship.
"""
import re
import fitz

X_ROSTER = (0, 235)
GOAL_COLS = {"idx": (235, 245.5), "heure": (245.5, 262), "scorer": (262, 273.5),
             "a1": (273.5, 284.5), "a2": (284.5, 295), "type": (295, 318),
             "jrun": (315, 432)}
PEN_COLS = {"heure": (434, 462), "num": (462, 477), "mins": (477, 494),
            "code": (494, 517), "debut": (517, 541), "fin": (541, 566)}
GK_COLS = {"start": (150, 188), "ga": (188, 207), "gb": (207, 224.5),
           "total": (224.5, 248)}
PAGE_H = 2000


def _secs(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def _grid(words, xlo, xhi, ylo, yhi, ytol=4.0):
    rows = {}
    for w in words:
        if xlo <= w[0] < xhi and ylo <= w[1] < yhi:
            rows.setdefault(round(w[1] / ytol), []).append(w)
    return [sorted(v, key=lambda w: w[0]) for _, v in sorted(rows.items())]


def _col(row, cols, name):
    lo, hi = cols[name]
    return [w[4] for w in row if lo <= w[0] < hi]


def parse_sheet(path):
    """Low-level sheet -> structured tables (teams, goals, pens, gk stints)."""
    doc = fitz.open(path)
    words = []
    for pno, page in enumerate(doc):
        for w in page.get_text("words"):
            words.append((w[0], w[1] + pno * PAGE_H, w[2], w[3] + pno * PAGE_H, w[4]))
    doc.close()
    full = " ".join(w[4] for w in words)
    out = {"match_id": None, "championnat": None, "date": None, "teams": [],
           "sheet_empty": False}
    m = re.search(r"N du match (\d+)", full)
    out["match_id"] = int(m.group(1)) if m else None
    m = re.search(r"Championnat (.+?) Lieu", full)
    out["championnat"] = (m.group(1) or "").strip() if m else None
    m = re.search(r"Date (\d{2})/(\d{2})/(\d{4})", full)
    out["date"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None

    anchors = []
    for i, w in enumerate(words):
        if w[4] == "Equipe" and i + 1 < len(words) and words[i + 1][4] in ("A", "B") and w[0] < 100:
            nm = []
            for w2 in words[i + 2:i + 7]:
                if w2[4] in ("N°", "Nom") or abs(w2[1] - w[1]) > 6:
                    break
                nm.append(w2[4])
            anchors.append((w[1], words[i + 1][4], " ".join(nm)))
    gk_y = min((w[1] for i, w in enumerate(words)
                if w[4] == "Gardien" and i + 1 < len(words) and words[i + 1][4] == "en"),
               default=10**9)
    # 'Tirs' stop added 2026-08-08: on shootout sheets the "Tirs après
    # prolongation" section header follows the coach name with no other stop
    # word, contaminating the name (seen on ROUEN/CERGY sheets in the
    # 2025-26 census). Coach identity feeds the ledger — must be clean.
    coaches = re.findall(
        r"Entraîneur principal\s*:\s*(.+?)\s+(?:Entraîneur|Equipe|Gardien|Résultat|Tirs|N°)",
        full)

    for k, (ay, side, name) in enumerate(anchors):
        by = anchors[k + 1][0] if k + 1 < len(anchors) else gk_y
        team = {"side": side, "name": name,
                "coach": coaches[k].strip() if k < len(coaches) else None,
                "roster": {}, "goals": [], "penalties": []}
        for r in _grid(words, *X_ROSTER, ay + 5, by):
            txt = [w[4] for w in r]
            if not txt or not txt[0].isdigit():
                continue
            num = int(txt[0])
            pos = None
            for t in txt[1:]:
                if t in ("A", "D", "GB"):
                    pos = t
            nm = " ".join(t for t in txt[1:] if not t.isdigit() and t not in ("A", "D", "GB"))
            if num not in team["roster"]:
                team["roster"][num] = {"name": nm.strip(), "pos": pos}
        for r in _grid(words, GOAL_COLS["idx"][0], GOAL_COLS["jrun"][1], ay + 16, by):
            heure = _col(r, GOAL_COLS, "heure")
            if not heure or not re.match(r"^\d{2}:\d{2}$", heure[0]) or not _col(r, GOAL_COLS, "idx"):
                continue
            sc = _col(r, GOAL_COLS, "scorer")
            team["goals"].append({
                "t": _secs(heure[0]),
                "scorer": int(sc[0]) if sc and sc[0].isdigit() else None,
                "type": "".join(t for t in _col(r, GOAL_COLS, "type") if not t.isdigit()),
                "jrun": [int(x) for x in _col(r, GOAL_COLS, "jrun") if x.isdigit()]})
        for r in _grid(words, PEN_COLS["heure"][0], PEN_COLS["fin"][1], ay + 16, by):
            h = _col(r, PEN_COLS, "heure")
            n = _col(r, PEN_COLS, "num")
            mi = _col(r, PEN_COLS, "mins")
            if not (h and re.match(r"^\d{2}:\d{2}$", h[0]) and n and mi and mi[0].isdigit()):
                continue
            de = _col(r, PEN_COLS, "debut")
            fi = _col(r, PEN_COLS, "fin")
            # num 'E' = Équipe (bench penalty, no jersey — e.g. 68850 NICE
            # 11:35 E 2 JEU 11:34-13:34; 22 sheets in 2025-26 have the class).
            # Served by a skater: the Début/Fin box window is real. num=None.
            team["penalties"].append({
                "t": _secs(h[0]), "num": int(n[0]) if n[0] != "E" else None,
                "mins": int(mi[0]),
                "debut": _secs(de[0]) if de else _secs(h[0]),
                "fin": _secs(fi[0]) if fi else _secs(h[0]) + int(mi[0]) * 60})
        out["teams"].append(team)

    # GK rows: STRUCTURAL parse (2026-08-08). Two sheet layout variants exist
    # in the 2025-26 census — the original fixed ga/gb column bands (68838:
    # jerseys at x~194/212) and a stretched variant (68861/68987/69046/77228:
    # jerseys at x~201/226, where 226 collides with the old 'total' band and
    # the row was silently dropped — 4 games lost their GK table entirely).
    # New rule: a GK row = [start mm:ss ... jersey int ... total mm:ss] in
    # the x window; SIDE comes from roster GB membership (authority), with
    # the two-column x split as fallback for jersey collisions.
    out["gk"] = {"A": [], "B": []}
    gk_rows = []
    for r in _grid(words, 150, 260, gk_y + 5, gk_y + 40 + PAGE_H * 2):
        times = [(w[0], w[4]) for w in r if re.match(r"^\d{2}:\d{2}$", w[4])]
        if len(times) < 2:
            continue
        nums = [(w[0], w[4]) for w in r
                if times[0][0] < w[0] < times[-1][0] and w[4].isdigit()]
        if not nums:
            continue
        gk_rows.append({"start": _secs(times[0][1]), "num": int(nums[0][1]),
                        "x": nums[0][0], "toi": _secs(times[-1][1])})
    gbsets = [{n for n, v in t["roster"].items() if v["pos"] == "GB"}
              for t in out["teams"]] if len(out["teams"]) == 2 else [set(), set()]
    xs = sorted(g["x"] for g in gk_rows)
    for g in gk_rows:
        in_a, in_b = g["num"] in gbsets[0], g["num"] in gbsets[1]
        if in_a != in_b:
            side = "A" if in_a else "B"
        elif xs[-1] - xs[0] > 6:
            side = "A" if g["x"] < (xs[0] + xs[-1]) / 2 else "B"
        else:
            side = "A"  # unresolvable single-column collision; census: none
        out["gk"][side].append({"start": g["start"], "num": g["num"],
                                "toi": g["toi"]})
    if len(out["teams"]) == 2 and not out["teams"][0]["roster"] and not out["teams"][1]["roster"]:
        out["sheet_empty"] = True
    return out


def _split_jrun(run, own, opp):
    cands = []
    for k in range(len(run) + 1):
        L, R = run[:k], run[k:]
        if all(x in own for x in L) and all(x in opp for x in R) \
                and 2 <= len(L) <= 6 and 2 <= len(R) <= 6:
            cands.append(k)
    if len(cands) == 1:
        return run[:cands[0]], run[cands[0]:], "unique"
    if cands:
        k = min(cands, key=lambda k: abs(k - (len(run) + 1) // 2))
        return run[:k], run[k:], "ambiguous"
    return run, [], "unsplit"


def parse_game(path):
    """Sheet -> interval game dict for gap/segments.py, or None if empty/non-Magnus."""
    sh = parse_sheet(path)
    if sh["sheet_empty"] or len(sh["teams"]) != 2:
        return None
    A, B = sh["teams"]
    side_of = {"A": "home", "B": "away"}
    # GK TOI SANITY GATE (2026-08-08, mandated by the Magnus lake
    # verification): the sheet itself can carry impossible TOI — 68882
    # ANGERS #29 shows 90:42 in a 60:00 game (truth: swap at 30:42; the
    # raw-typo read produced a false 1,842s "pull" in the lake session's
    # ledger AND inflated this adapter's duration to 7200). Rules:
    # (a) overlapping stints are repaired: prev.toi := next.start -
    #     prev.start (flag toi_repaired);
    # (b) game length = max(3600, stint sums) but NEVER above 3900
    #     (regulation + 5:00 OT); a post-repair sum > 3900 flags
    #     toi_insane and that side's timing is unusable.
    # NOTE the repair fires ONLY when the side's TOI sum is impossible
    # (> 3900): stint 'start' is a first-entry time and TOI a per-goalie
    # TOTAL, so relief spells legitimately interleave (69059 BORDEAUX:
    # #32 start 0:00 toi 58:52 + #31 start 8:56 toi 1:08 = exactly 60:00
    # — an unconditional overlap-repair corrupted this into a fake 868s
    # pull; caught same day).
    toi_flags = []
    for s in ("A", "B"):
        st = sorted(sh["gk"][s], key=lambda x: x["start"])
        if sum(x["toi"] for x in st) > 3900:
            for j in range(1, len(st)):
                if st[j - 1]["start"] + st[j - 1]["toi"] > st[j]["start"]:
                    st[j - 1]["toi"] = st[j]["start"] - st[j - 1]["start"]
                    toi_flags.append(f"toi_repaired_{s}")
        sh["gk"][s] = st
    duration = 3600
    for s in ("A", "B"):
        tot = sum(x["toi"] for x in sh["gk"][s])
        if duration < tot <= 3900:
            duration = tot          # OT: duration from the sheet, never assumed
        elif tot > 3900:
            toi_flags.append(f"toi_insane_{s}")
    gb = {s: {n for n, v in t["roster"].items() if v["pos"] == "GB"}
          for s, t in (("A", A), ("B", B))}
    rost = {s: set(t["roster"]) for s, t in (("A", A), ("B", B))}
    other = {"A": "B", "B": "A"}

    out = {"id": str(sh["match_id"]), "date": sh["date"],
           "home": A["name"], "away": B["name"],
           "coach_home": A["coach"], "coach_away": B["coach"],
           "goals": [], "empty": {"home": [], "away": []}, "penalties": [],
           "flags": list(toi_flags)}

    # goals with EN from the CONCEDING team's J list (no GB present)
    for s, t in (("A", A), ("B", B)):
        for g in t["goals"]:
            jp, jm, q = _split_jrun(g["jrun"], rost[s], rost[other[s]])
            if q != "unique":
                out["flags"].append(f"jsplit_{q}@{g['t']}")
            en = bool(jm) and not any(x in gb[other[s]] for x in jm)
            own_net_empty = bool(jp) and not any(x in gb[s] for x in jp)
            out["goals"].append({"t": g["t"], "side": side_of[s],
                                 "period": min((g["t"] // 1200) + 1, 4) if g["t"] < 3600 else 4,
                                 "en": en, "types": ([ "EN"] if en else []) +
                                 (["CV"] if "CV" in g["type"] else []) +
                                 (["scorer_net_empty"] if own_net_empty else [])})
    out["goals"].sort(key=lambda g: g["t"])

    for s, t in (("A", A), ("B", B)):
        for p in t["penalties"]:
            out["penalties"].append({"side": side_of[s], "t": p["t"],
                                     "begin": p["debut"], "end": p["fin"],
                                     "misconduct": p["mins"] >= 10})

    # ---- net-empty inference from TOI + anchors (the four cases) ----------
    # CLOCK-NOISE FLOOR (2026-08-08, from the lake cross-derivation): the
    # scorekeeper's stoppage accounting shifts BOTH goalies' TOI equally, so
    # a shortfall common to both sides is clock noise, not two empty nets
    # (68926: raw shortfalls 8s/39s -> real evidence 0s/31s; 8 games in the
    # census show the pattern; no game has two genuine simultaneous pulls).
    # Subtract min(shortfall_A, shortfall_B) from both before inference.
    raw_off = {}
    for s in ("A", "B"):
        st = sh["gk"][s]
        raw_off[s] = (duration - sum(x["toi"] for x in st)) if st else 0
    floor = min(raw_off.values())
    if floor > 0:
        out["flags"].append(f"clock_noise_floor_{floor}s")
    for s, t in (("A", A), ("B", B)):
        stints = sh["gk"][s]
        if not stints:
            out["flags"].append(f"no_gk_rows_{s}")
            continue
        off = raw_off[s] - max(floor, 0)
        if off <= 0:
            continue
        # anchors, latest first: (abs_second, kind)
        anchors = []
        for g in out["goals"]:
            if g["side"] != side_of[s] and g["en"]:
                anchors.append((g["t"], "en_against"))
            if g["side"] == side_of[s] and "scorer_net_empty" in g["types"]:
                anchors.append((g["t"], "own_goal_empty"))
        for p in t["penalties"]:
            anchors.append((p["debut"], "own_pen"))
        anchors.append((duration, "horn"))
        anchors.sort(reverse=True)
        # deterministic fit. HARD CONSTRAINT: every J-confirmed EN moment
        # (en_against / own_goal_empty) PROVES the net was empty at that
        # second, so any valid fit must cover ALL of them (GT 16351 lesson:
        # a horn fit was arithmetically consistent but contradicted the
        # 56:15 EN goal). With EN anchors: single segment ends at the LATEST
        # EN anchor; valid iff it covers every other EN anchor and starts
        # >=0. Without EN anchors: latest own-pen début, else horn.
        en_anchors = sorted(a for a, k in anchors
                            if k in ("en_against", "own_goal_empty"))
        # SUB-THRESHOLD NOISE (2026-08-08): a residual shortfall under 15s
        # with NO J-confirmed EN moment is delayed-penalty scramble or clock
        # slop, not a pull (matches the lake session's dp_or_noise class,
        # now a named adapter rule; 16 such events in the 2025-26 census,
        # all <=15s, none with an EN goal). No interval emitted.
        if off < 15 and not en_anchors:
            out["flags"].append(f"subthreshold_noise_{s}_{off}s")
            continue
        seg = None
        if en_anchors:
            at = en_anchors[-1]
            start = at - off
            if start >= 0 and all(start < a <= at for a in en_anchors):
                seg = (start, at, "en_anchor")
        else:
            for at, kind in anchors:
                if kind in ("own_pen", "horn"):
                    start = at - off
                    if start >= 0:
                        seg = (start, at, kind)
                        break
        if seg is None:
            out["flags"].append(f"multi_pull_ambiguous_{s}")
            # evidence exists (off-ice > 0) but timing unusable
            out["empty"][side_of[s]].append((duration - 1, duration, "synthetic"))
            continue
        out["empty"][side_of[s]].append((seg[0], seg[1]))
    return out
