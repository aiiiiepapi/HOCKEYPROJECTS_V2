#!/usr/bin/env python3
"""
magnus_parse_proto.py — Ligue Magnus PDF sheet parser PROTOTYPE (pre-GT).

Coordinate-based (fitz words). The sheet is a spatial layout, NOT sequential:
per team band: roster (x<235) | goals table (x 235-432) | penalties (x 432-575);
below both bands: shared "Gardien en jeu" table where the goalie NUMBER's
x-position picks the team (G.A column ~[188,207), G.B ~[207,224)) — this
replaces v1's alternating-order heuristic (their 25% jersey-collision pain).
Coaches ARE on the sheet (Entraîneur principal), contra the v1 docs.
Prototype: parsing only, no classification (rule 2: GT before logic).
"""
import re
import sys
import fitz

# x-windows measured on 2022 + 2025 sheets (stable; verified per-sample below)
X_ROSTER = (0, 235)
X_GOAL = (235, 432)
X_PEN = (432, 575)
GOAL_COLS = {"idx": (235, 245.5), "heure": (245.5, 262), "scorer": (262, 273.5),
             "a1": (273.5, 284.5), "a2": (284.5, 295), "type": (295, 318),
             "jrun": (315, 432)}
PEN_COLS = {"heure": (434, 462), "num": (462, 477), "mins": (477, 494),
            "code": (494, 517), "debut": (517, 541), "fin": (541, 566)}
GK_COLS = {"start": (150, 188), "ga": (188, 207), "gb": (207, 224.5),
           "total": (224.5, 248), "arrets": (248, 285), "buts": (285, 312)}
PAGE_H = 2000


def _secs(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


def _grid(words, xlo, xhi, ylo, yhi, ytol=4.0):
    rows = {}
    for w in words:
        if xlo <= w[0] < xhi and ylo <= w[1] < yhi:
            key = round(w[1] / ytol)
            rows.setdefault(key, []).append(w)
    return [sorted(v, key=lambda w: w[0]) for _, v in sorted(rows.items())]


def _col(row, cols, name):
    lo, hi = cols[name]
    return [w[4] for w in row if lo <= w[0] < hi]


def parse_sheet(path):
    doc = fitz.open(path)
    words = []
    for pno, page in enumerate(doc):
        for w in page.get_text("words"):
            words.append((w[0], w[1] + pno * PAGE_H, w[2], w[3] + pno * PAGE_H, w[4]))
    doc.close()
    full = " ".join(w[4] for w in words)
    out = {}
    m = re.search(r"N du match (\d+)", full)
    out["match_id"] = int(m.group(1)) if m else None
    m = re.search(r"Championnat (.+?) Lieu", full)
    out["championnat"] = m.group(1) if m else None
    m = re.search(r"Date (\d{2}/\d{2}/\d{4})", full)
    out["date"] = m.group(1) if m else None

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
                if w[4] == "Gardien" and i + 2 < len(words) and words[i + 1][4] == "en"), default=10**9)
    coaches = re.findall(r"Entraîneur principal\s*:\s*(.+?)\s+(?:Entraîneur|Equipe|Gardien|Résultat)",
                         full)

    out["teams"] = []
    for k, (ay, side, name) in enumerate(anchors):
        by = anchors[k + 1][0] if k + 1 < len(anchors) else gk_y
        team = {"side": side, "name": name,
                "coach": coaches[k].strip() if k < len(coaches) else None,
                "roster": {}, "gb": [], "goals": [], "penalties": []}
        for r in _grid(words, *X_ROSTER, ay + 5, by):
            txt = [w[4] for w in r]
            if not txt or not txt[0].isdigit() or txt[0:1] == ["Total"]:
                continue
            num = int(txt[0])
            pos = None
            for t in txt[1:]:
                if t in ("A", "D", "GB"):
                    pos = t  # last positional token wins (captain markers are '(C)')
            nm = " ".join(t for t in txt[1:] if not t.isdigit() and t not in ("A", "D", "GB"))
            if num in team["roster"]:
                continue
            team["roster"][num] = {"name": nm.strip(), "pos": pos}
        team["gb"] = sorted(n for n, v in team["roster"].items() if v["pos"] == "GB")
        for r in _grid(words, *X_GOAL, ay + 16, by):
            heure = _col(r, GOAL_COLS, "heure")
            idx = _col(r, GOAL_COLS, "idx")
            if not heure or not re.match(r"^\d{2}:\d{2}$", heure[0]) or not idx:
                continue
            sc = _col(r, GOAL_COLS, "scorer")
            typ = "".join(t for t in _col(r, GOAL_COLS, "type") if not t.isdigit())
            jrun = [int(x) for x in _col(r, GOAL_COLS, "jrun") if x.isdigit()]
            team["goals"].append({
                "t": _secs(heure[0]),
                "scorer": int(sc[0]) if sc and sc[0].isdigit() else None,
                "assists": [int(x) for x in (_col(r, GOAL_COLS, "a1") + _col(r, GOAL_COLS, "a2")) if x.isdigit()],
                "type": typ, "jrun": jrun})
        for r in _grid(words, *X_PEN, ay + 16, by):
            h = _col(r, PEN_COLS, "heure")
            n = _col(r, PEN_COLS, "num")
            mi = _col(r, PEN_COLS, "mins")
            de = _col(r, PEN_COLS, "debut")
            fi = _col(r, PEN_COLS, "fin")
            if not (h and re.match(r"^\d{2}:\d{2}$", h[0]) and n and mi):
                continue
            team["penalties"].append({
                "t": _secs(h[0]), "num": int(n[0]), "mins": int(mi[0]),
                "code": "".join(_col(r, PEN_COLS, "code")) or None,
                "debut": _secs(de[0]) if de else None,
                "fin": _secs(fi[0]) if fi else None})
        out["teams"].append(team)

    # ---- J+/J- split: SEMANTIC, not spatial (no x-gap exists between the
    # lists). Split point k: first k numbers all on the scoring team's roster,
    # remainder all on the opponent's. Ties broken by plausible on-ice counts
    # (3-6 a side); unresolvable rows flagged (manual lane, v1 two-factor
    # spirit). Roster maps come from the roster tables just parsed.
    if len(out["teams"]) == 2:
        rosters = {t["side"]: set(t["roster"]) for t in out["teams"]}
        other = {"A": "B", "B": "A"}
        for t in out["teams"]:
            own, opp = rosters[t["side"]], rosters[other[t["side"]]]
            for g in t["goals"]:
                run = g.pop("jrun")
                cands = []
                for k in range(len(run) + 1):
                    L, R = run[:k], run[k:]
                    if all(x in own for x in L) and all(x in opp for x in R)                             and 2 <= len(L) <= 6 and 2 <= len(R) <= 6:
                        cands.append(k)
                if len(cands) == 1:
                    k = cands[0]
                    g["jplus"], g["jminus"], g["j_split"] = run[:k], run[k:], "unique"
                elif cands:
                    k = min(cands, key=lambda k: abs(k - (len(run) + 1) // 2))
                    g["jplus"], g["jminus"], g["j_split"] = run[:k], run[k:], f"ambiguous{len(cands)}"
                else:
                    g["jplus"], g["jminus"], g["j_split"] = run, [], "UNSPLIT"

    out["goalie_stints"] = {"A": [], "B": []}
    for r in _grid(words, 150, 315, gk_y + 5, gk_y + 40 + PAGE_H * 2):
        st = _col(r, GK_COLS, "start")
        tot = _col(r, GK_COLS, "total")
        ga = [x for x in _col(r, GK_COLS, "ga") if x.isdigit()]
        gb = [x for x in _col(r, GK_COLS, "gb") if x.isdigit()]
        if not st or not re.match(r"^\d{2}:\d{2}$", st[0]) or not tot:
            continue
        if not re.match(r"^\d{2}:\d{2}$", tot[0]):
            continue
        side = "A" if ga else ("B" if gb else None)
        num = int((ga or gb)[0]) if (ga or gb) else None
        if side:
            out["goalie_stints"][side].append(
                {"start": _secs(st[0]), "num": num, "toi": _secs(tot[0])})
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        r = parse_sheet(p)
        print(f"===== {r['match_id']}: {r['championnat']} {r['date']} =====")
        for t in r["teams"]:
            print(f"  {t['side']} {t['name']:12} coach={t['coach']} gb={t['gb']} roster={len(t['roster'])}")
            for g in t["goals"]:
                print(f"    goal {g['t']//60:02d}:{g['t']%60:02d} sc={g['scorer']} {g['type']:8} J+={g['jplus']} J-={g['jminus']}")
            for pn in t["penalties"]:
                print(f"    pen  {pn['t']//60:02d}:{pn['t']%60:02d} #{pn['num']} {pn['mins']}min {pn['code']} [{pn['debut']}-{pn['fin']}]")
        print(f"  GK A={r['goalie_stints']['A']}  B={r['goalie_stints']['B']}")
