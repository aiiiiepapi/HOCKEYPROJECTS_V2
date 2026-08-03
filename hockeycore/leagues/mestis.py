"""
hockeycore.leagues.mestis — Mestis adapter: raw mestis.fi seuranta HTML (+
tilastopalvelu rosters.json) → the interval game dict consumed by
hockeycore.gap.segments (rule 15: adapter only, no gap or betting logic).

Verified conventions (hand-traced from raw lake, 2026-08-03 — GT batch 1,
13 games, tests/ground_truth_mestis.json):

- The seuranta page's MAIN event table rows are <tr> with
  <td class="home">, <td class="time"><i>MM:SS</i></td>, <td class="away">.
  Event side = which cell carries the text. Times are CUMULATIVE game
  seconds (65:00 for shootout rows).
- CRITICAL: the page also embeds a league-wide TICKER of OTHER games'
  events (div.latest-event, td classes time-team/text) — page-wide greps
  are contaminated (this inflated the scrape session's goalie-out counts
  303/242/185/205; the true scoped counts are 226/186/155/179 == the
  pois-interval game counts exactly, both channels fully redundant at
  game level). Only home/time/away-cell rows are parsed here.
- Period from section marker rows ("1. erä", "2. erä", "3. erä",
  "Jatkoaika", "Voittomaalikilpailu"), cross-checked against time//1200;
  mismatch raises (rule 10).
- Goals: <strong> in the side cell containing the running score "H-A"
  (home-away always), optional flag list after it (YV, YV2, AV, VM, VT,
  SR, RL, TV, TM, IM, VL...). en = TM (conceding net empty). IM = scorer's
  OWN net was empty — NOT an ENG. Score increments are cross-checked
  against the cell side every goal (rule 10). "Videotarkistus - ei maalia"
  and "Rangaistuslaukaus - ei maalia" rows carry no score → not goals.
  Shootout rows (period 5) are excluded from the goals list.
- Penalties: side cell = PENALIZED team (verified vs the per-team
  penalty-minute summaries). Text "N min <offense>"; rows WITHOUT minutes
  are penalty-shot-awarded fouls (no box time, e.g. 2023/7441 26:55).
  Double minors appear as two same-second rows (real, e.g. 2026/3142
  58:46 — the summary counts them separately); 5+20 pairs = major +
  game misconduct. minutes>=10 = misconduct class (no strength effect,
  kept as whistle marker, cf. 2026-08-02 fix). Minors end early on the
  first goal by a non-penalized side in-window (AHL approximation,
  used only for pull classification).
- Goalie events, EXPLICIT with times: "Maalivahti ulos: #N Name" (net
  empty), "Maalivahti sisään: #N Name" (net occupied). "Maalivahdin
  vaihto: #A ulos, #B sisään" is a SUBSTITUTION — net never empty,
  ignored for intervals (e.g. 2025/3000 24:33, 2023/7452 51:23+51:38).
  AHL interval conventions inherited: OUT-first same-second
  normalization, close at period end when no return logged, zero-length
  intervals dropped. The tilastot/seuranta goalie stat lines repeat the
  intervals as "(pois: MM:SS-MM:SS, ...)" — NOT parsed here; they are
  the independent channel for the random audit (parity with AHL/Liiga).
- EN evidence repair rules inherited verbatim from the AHL adapter
  (rule 5): TM goal with no covering interval → synthetic 1s segment;
  interval-covered goal missing TM → en corrected.
- Coaches: game-level rosters.json (tilastopalvelu getRosters.php),
  Staff RoleName "Vastuuvalmentaja". 19/1166 games lack it on one side
  (docs/MESTIS_LAKE_VERIFICATION.md); data/coach_maps/mestis_coaches.csv
  fills blanks (join rule: game listing ALWAYS wins; map is fallback).
- Games keyed (season, matchno) — matchnos repeat across seasons.
"""
import csv
import html as _html
import json
import re
from pathlib import Path

P3_START, P3_END = 2400, 3600
PERIOD_LEN = 1200

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r'<t[dh][^>]*class="(home|time|away)"[^>]*>(.*?)</t[dh]>', re.S)
_STRONG = re.compile(r"<strong>(.*?)</strong>", re.S)
_SCORE = re.compile(r"(\d+)-(\d+)\s*([A-Z0-9, ]*?)\s*$")
_TIME = re.compile(r"\d{1,3}[:.]\d{2}$")
_PEN_MIN = re.compile(r"(\d+)\s*min\b")
_TITLE = re.compile(r"<title>\s*Otteluseuranta\s*\|\s*(.+?)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\s*\|", re.S)
_MARKER = re.compile(r"^(?:(\d)\. erä|(Jatkoaika)|(Voittomaalikilpailu))$")

_COACH_MAP = None


def _coach_map():
    """(season, team) -> [(from_date, to_date, coach)] verified fallback CSV."""
    global _COACH_MAP
    if _COACH_MAP is None:
        _COACH_MAP = {}
        p = Path(__file__).resolve().parents[2] / "data" / "coach_maps" / "mestis_coaches.csv"
        if p.exists():
            for r in csv.DictReader(open(p, encoding="utf-8")):
                _COACH_MAP.setdefault((r["season"], r["team"]), []).append(
                    (r["from_date"], r["to_date"], r["coach"]))
    return _COACH_MAP


def _strip(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _secs(t):
    m, s = t.replace(".", ":").split(":")
    return int(m) * 60 + int(s)


def parse_game(seuranta_path, rosters_path=None, season=None):
    seuranta_path = Path(seuranta_path)
    raw = seuranta_path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"game_(\d{4})_(\d+)_seuranta", seuranta_path.stem)
    if season is None and m:
        season = m.group(1)
    matchno = m.group(2) if m else seuranta_path.stem

    tm = _TITLE.search(raw)
    if not tm:
        raise ValueError(f"no title header in {seuranta_path.name}")
    home, away = [x.strip() for x in tm.group(1).split(" - ", 1)]
    date = f"{tm.group(4)}-{int(tm.group(3)):02d}-{int(tm.group(2)):02d}"

    out = {"id": f"{season}_{matchno}", "season": season, "matchno": int(matchno),
           "date": date, "home": home, "away": away,
           "goals": [], "empty": {"home": [], "away": []}, "penalties": []}

    # ---- sequential scan of the MAIN table (ticker rows have no home/away cells)
    period = 0
    events = []          # (t, period, side, text_cell_raw)
    for row in _ROW.finditer(raw):
        inner = row.group(1)
        cells = _CELL.findall(inner)
        if not cells:
            mk = _MARKER.match(_strip(inner))
            if mk:
                period = int(mk.group(1)) if mk.group(1) else (4 if mk.group(2) else 5)
            continue
        t_txt = side = content = None
        for cls, c in cells:
            if cls == "time":
                t_txt = _strip(c)
            elif _strip(c):
                side, content = cls, c
        if not (t_txt and _TIME.fullmatch(t_txt) and content is not None):
            continue
        t = _secs(t_txt)
        if period == 0:
            raise ValueError(f"event before any period marker in {seuranta_path.name}")
        # rule 10: marker period must agree with the clock (boundary seconds
        # 1200/2400/3600 legitimately belong to the closing period)
        t_per = 1 if t < 1200 else 2 if t < 2400 else 3 if t < 3600 else 4
        if period <= 3 and not (t_per == period or (t in (1200, 2400, 3600) and t_per == period + 1)
                                or (t == PERIOD_LEN * (period - 1))):
            raise ValueError(f"period marker {period} vs clock {t_txt} in {seuranta_path.name}")
        events.append((t, period, side, content))

    # ---- goals with running-score side cross-check --------------------------
    h = a = 0
    for t, per, side, content in events:
        sm = None
        for st in _STRONG.findall(content):
            sm = _SCORE.search(_strip(st))
            if sm:
                break
        if not sm:
            continue
        if per >= 5:
            continue                     # shootout decision row (VL) — not a goal
        nh, na = int(sm.group(1)), int(sm.group(2))
        types = [f.strip() for f in sm.group(3).split(",") if f.strip()]
        if not (nh == h + (side == "home") and na == a + (side == "away")):
            raise ValueError(f"score {nh}-{na} does not increment {h}-{a} on {side} "
                             f"at {t}s in {seuranta_path.name}")
        h, a = nh, na
        out["goals"].append({"t": t, "side": side, "period": per,
                             "en": "TM" in types, "types": types})
    out["goals"].sort(key=lambda e: e["t"])

    # ---- net-empty intervals from explicit goalie events --------------------
    per_side = {"home": [], "away": []}
    for i, (t, per, side, content) in enumerate(events):
        if per > 3:
            continue
        txt = _strip(content)
        if txt.startswith("Maalivahdin vaihto"):
            continue                     # substitution: net never empty
        if txt.startswith("Maalivahti ulos"):
            per_side[side].append((per, t, i, "out"))
        elif txt.startswith("Maalivahti sis"):
            per_side[side].append((per, t, i, "in"))
    for sd, rows in per_side.items():
        rows.sort(key=lambda r: (r[1], r[3] == "in", r[2]))   # OUT-first at same second
        open_at = open_pid = None
        for pid, t, _i, kind in rows:
            if open_at is not None and pid != open_pid:
                out["empty"][sd].append((open_at, open_pid * PERIOD_LEN))
                open_at = None
            if kind == "out" and open_at is None:
                open_at, open_pid = t, pid
            elif kind == "in" and open_at is not None:
                out["empty"][sd].append((open_at, t))
                open_at = None
        if open_at is not None:
            out["empty"][sd].append((open_at, min(open_pid * PERIOD_LEN, 3600)))
        out["empty"][sd] = [(b, e) for b, e in out["empty"][sd] if e > b]

    # ---- EN-goal evidence repair (AHL rule, inherited verbatim) -------------
    for gl in out["goals"]:
        if gl["period"] > 3 or not gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if not any(b - 3 <= gl["t"] <= e + 3 for b, e, *_ in out["empty"][opp]):
            out["empty"][opp].append((gl["t"] - 1, gl["t"], "synthetic"))
    for sd in ("home", "away"):
        out["empty"][sd].sort(key=lambda x: (x[0], x[1]))

    # ---- EN-flag repair (interval evidence beats a missing TM flag) ---------
    for gl in out["goals"]:
        if gl["period"] > 3 or gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if any(len(tup) == 2 and tup[0] < gl["t"] <= tup[1] for tup in out["empty"][opp]):
            gl["en"] = True
            gl["types"] = gl["types"] + ["EN_corrected"]

    # ---- penalty box windows (pp_pull classification only) ------------------
    pens = []
    for t, per, side, content in events:
        if per > 3:
            continue
        txt = _strip(content)
        if txt.startswith(("Maalivahti", "Maalivahdin", "Videotarkistus", "Rangaistuslaukaus")):
            continue
        if _STRONG.search(content) and _SCORE.search(_strip(_STRONG.search(content).group(1))):
            continue                     # goal row
        pm = _PEN_MIN.search(txt)
        if not pm:
            continue                     # timeout / PS-awarded foul: no box time
        mins = int(pm.group(1))
        pens.append({"side": side, "t": t, "begin": t, "end": t + mins * 60,
                     "minor": mins == 2, "misconduct": mins >= 10})
    for p in pens:
        if not p["minor"]:
            continue
        for gl in out["goals"]:
            if p["begin"] < gl["t"] < p["end"] and gl["side"] != p["side"]:
                p["end"] = gl["t"]
                break
    out["penalties"] = [{k: p[k] for k in ("side", "t", "begin", "end", "misconduct")}
                        for p in pens]

    # ---- head coaches: game rosters first, verified map as fallback ---------
    if rosters_path is None:
        rp = seuranta_path.with_name(seuranta_path.name.replace("_seuranta.html", "_rosters.json"))
        rosters_path = rp if rp.exists() else None
    coaches = {"home": None, "away": None}
    if rosters_path is not None:
        ros = json.loads(Path(rosters_path).read_text(encoding="utf-8", errors="replace"))
        for sd, key in (("home", "HomeTeamGameRoster"), ("away", "AwayTeamGameRoster")):
            staff = (ros.get(key) or {}).get("Staff") or []
            hcs = [s for s in staff if "astuuvalmentaja" in str(s.get("RoleName", ""))]
            if hcs:
                fn = str(hcs[0].get("FirstName") or "").strip()
                ln = str(hcs[0].get("LastName") or "").strip().title()
                coaches[sd] = f"{fn} {ln}".strip()
    for sd in ("home", "away"):
        if coaches[sd] is None and season is not None:
            team = out[sd]
            for d0, d1, coach in _coach_map().get((str(season), team), []):
                if d0 <= date <= d1:
                    coaches[sd] = coach
                    break
    out["coaches"] = coaches
    return out


from hockeycore.gap.segments import extract_instances  # noqa: E402  (rule 15)


def scan_dir(season_dir):
    """One lake season directory -> {matchno: (game_dict, instances)}."""
    season_dir = Path(season_dir)
    out = {}
    for f in sorted(season_dir.glob("game_*_seuranta.html"),
                    key=lambda p: int(p.stem.split("_")[2])):
        num = int(f.stem.split("_")[2])
        try:
            g = parse_game(f)
            out[num] = (g, extract_instances(g, 3))
        except Exception as e:
            out[num] = (None, f"ERROR {e!r}")
    return out
