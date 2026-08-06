"""
hockeycore.leagues.shl — SHL adapter: raw stats.swehockey.se Game/Events HTML
(+ Game/LineUps HTML) → the interval game dict consumed by
hockeycore.gap.segments (rule 15: adapter only, no gap or betting logic).

Verified conventions (hand-traced from raw lake, 2026-08-06 — GT batch 1,
12 games, tests/ground_truth_shl.json; league-wide scans in
docs/ground_truth_traces/shl_batch1_2026-08-06.md):

- Events page rows are `[time, type, team-code, player, detail]` cells
  (`td.tdOdd`), grouped under section headers `1st/2nd/3rd period`,
  `Overtime`, `Game Winning Shot(s)`, `Goalkeeper Summary`. Sections AND
  rows are NEWEST-FIRST; both are reversed here. Only period sections are
  parsed; GWS sections (shootout winner row `H-A (GWS)` + `Missed/Scored`
  attempt rows) are never events (628968 — events total 4-4 vs header 5-4,
  the winner is the off-by-one).
- Clock is CUMULATIVE MM:SS (57:12 = 3432; OT rows 60:52-style). Home =
  first code in `<title>HOME - AWAY (H-A)</title>`, full names from `<h2>`;
  proven by running-score side cross-check with 0 failures across all
  1,456 events pages (2026-08-06 scan). Every goal row's `H-A` must
  increment the tracked score on the scorer's side or parsing raises
  (rule 10). `(PS)` = penalty-shot goal, real (628999); en = `ENG` flag.
- GK rows: `GK In` / `GK Out` with goalie name. 00:00 In = starters.
  60:00 / OT-end `GK Out` rows are END-OF-GAME BOOKKEEPING, never pulls
  (binding rule, docs/SHL_LAKE_VERIFICATION.md) — they need no special
  case: an Out at 3600 opens a zero-length interval that is dropped, and
  period>3 rows are never intervals. Same-second Out+In = substitution
  (different goalie: 629020 56:56, 882278 07:11, 629037 22:18) or feed
  blip (same goalie, e.g. 628973) — OUT-first normalization makes them
  zero-length, net never empty (AHL convention, inherited). An interval
  left open at period end closes at the period boundary (AHL convention).
- EN evidence repair inherited verbatim from the AHL/Mestis adapters:
  ENG goal with no covering interval → synthetic 1s segment; interval-
  covered goal missing the flag → en corrected.
- Penalties `N min` carry EXPLICIT `(begin - end)` windows — used
  directly (better than AHL's minutes approximation): early PP-goal
  termination (1004308 14:50-14:55), stacked/deferred starts (628964
  double minor: consecutive windows), end-clamps at game end (629011
  59:52-60:00). mins>=10 = misconduct class (no strength effect, kept as
  whistle marker — 2026-08-02 fix). OFFSETTING/coincident penalties carry
  placeholder windows `(00:00 - )` or `(00:00 - MM:SS)` — no box time
  served (628979 59:07 quad UC, 774444 fighting pair; league-wide census:
  1,214/1,218 zero-begin open-end rows have a same-second opposite-team
  penalty). Any window with begin==0 while t>0 → begin=end=t (whistle
  marker only, no strength effect). `PS` (missed penalty shot), type-less
  `Team penalty PenaltyShot` (awarded foul, no minutes) and `TO` rows are
  not penalties.
- Coaches: Game/LineUps `Head Coach:` per team section (`<h3>Name
  (Color)</h3>`, matched to home/away by name, "Last, First" → "First
  Last"). 21 sides blank league-wide (HANDOFF_SHL.md census);
  data/coach_maps/shl_coaches.csv fills blanks (join rule: game listing
  ALWAYS wins; map is fallback).
- Games keyed (season, gameId); gameIds are site-global (do not repeat),
  season kept for lake layout parity.
"""
import csv
import html as _html
import re
from pathlib import Path

P3_START, P3_END = 2400, 3600
PERIOD_LEN = 1200

_ROW = re.compile(
    r'<tr><td class="tdOdd" style="[^"]*">([^<]*)</td>'
    r'<td class="tdOdd" style="[^"]*">(.*?)</td>'
    r'<td class="tdOdd" style="[^"]*">(.*?)</td>(.*?)</tr>', re.S)
_SECTION = re.compile(r'<th class="tdSubTitle" colspan="5"><h3>(.*?)</h3></th>', re.S)
_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
_H2 = re.compile(r"<h2>(.*?)</h2>", re.S)
_DATE = re.compile(r"<h3>\s*(\d{4}-\d{2}-\d{2})")
_GOAL = re.compile(r"^(\d+)-(\d+) \(([A-Z0-9]+)\)(\|ENG)?$")
_PEN = re.compile(r"^(\d+) min$")
_WINDOW = re.compile(r"\((\d{1,3}:\d{2}) - (\d{1,3}:\d{2})?\s*\)\s*$")
_TIME = re.compile(r"^\d{1,3}:\d{2}$")
_PERIODS = {"1st period": 1, "2nd period": 2, "3rd period": 3, "Overtime": 4}

_COACH_MAP = None


def _coach_map():
    """(season, team_full_name) -> [(from_date, to_date, coach)] fallback CSV."""
    global _COACH_MAP
    if _COACH_MAP is None:
        _COACH_MAP = {}
        p = Path(__file__).resolve().parents[2] / "data" / "coach_maps" / "shl_coaches.csv"
        if p.exists():
            for r in csv.DictReader(open(p, encoding="utf-8")):
                _COACH_MAP.setdefault((r["season"], r["team"]), []).append(
                    (r["from_date"], r["to_date"], r["coach"]))
    return _COACH_MAP


def _strip(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<br\s*/?>", "|",
                  re.sub(r"<(?!br)[^>]+>", " ", s)))).strip()


def _secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def _coach_name(raw_name):
    """'Gällstedt, Niklas' -> 'Niklas Gällstedt' (kept verbatim otherwise)."""
    parts = [x.strip() for x in raw_name.split(",", 1)]
    return f"{parts[1]} {parts[0]}" if len(parts) == 2 and parts[1] else parts[0]


def parse_lineups(lineups_path, home, away):
    """Head coach per side from the LineUps page; None where blank."""
    raw = Path(lineups_path).read_text(encoding="utf-8", errors="replace")
    coaches = {"home": None, "away": None}
    # team sections: <h3>Full Name (Color)</h3> ... Head Coach:</strong> Last, First
    heads = [(m.start(), _strip(m.group(1))) for m in re.finditer(r"<h3>(.*?)</h3>", raw, re.S)]
    team_secs = []
    for pos, h in heads:
        name = re.sub(r"\s*\([^)]*\)\s*$", "", h)
        if name in (home, away):
            team_secs.append((pos, "home" if name == home else "away"))
    for i, (pos, side) in enumerate(team_secs):
        end = team_secs[i + 1][0] if i + 1 < len(team_secs) else len(raw)
        m = re.search(r"Head Coach:\s*</strong>\s*([^<]*)", raw[pos:end])
        if m:
            nm = _strip(m.group(1))
            if nm:
                coaches[side] = _coach_name(nm)
    return coaches


def parse_game(events_path, lineups_path=None, season=None):
    events_path = Path(events_path)
    raw = events_path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"game_(\d{4})_(\d+)_events", events_path.stem)
    if season is None and m:
        season = m.group(1)
    gid = m.group(2) if m else events_path.stem

    tm = _TITLE.search(raw)
    tt = _strip(tm.group(1))
    tmm = re.match(r"^(.*?) - (.*?) \((\d+)-(\d+)\)$", tt)
    if not tmm:
        raise ValueError(f"unparseable title {tt!r} in {events_path.name}")
    hcode, acode = tmm.group(1), tmm.group(2)
    h2 = _strip(_H2.search(raw).group(1))
    home, away = [x.strip() for x in h2.split(" - ", 1)]
    dm = _DATE.search(raw)
    date = dm.group(1) if dm else None

    out = {"id": f"{season}_{gid}", "season": season, "game_id": int(gid),
           "date": date, "home": home, "away": away,
           "home_code": hcode, "away_code": acode,
           "goals": [], "empty": {"home": [], "away": []}, "penalties": []}

    def side_of(code):
        if code == hcode:
            return "home"
        if code == acode:
            return "away"
        raise ValueError(f"unknown team code {code!r} in {events_path.name}")

    # ---- sections + rows, both newest-first in the HTML → reversed ---------
    parts = _SECTION.split(raw)
    events = []                       # (period, t, type, team_code, detail)
    section_pairs = []
    for i in range(1, len(parts), 2):
        per = _PERIODS.get(_strip(parts[i]))
        if per is None:               # Goalkeeper Summary / GWS sections
            continue
        section_pairs.append((per, parts[i + 1]))
    for per, body in reversed(section_pairs):
        for t_txt, ty, team, rest in reversed(_ROW.findall(body)):
            t_txt = _strip(t_txt)
            if not _TIME.match(t_txt):
                continue              # GWS attempt rows etc. never reach here
            t = _secs(t_txt)
            # Section period vs the cumulative clock: boundary seconds belong
            # to the closing period; rows logged AT a section's period start
            # (GK In 40:00 in the 3rd-period section — intermission goalie
            # change, 1004355) are legitimate. When they truly disagree the
            # CLOCK wins — it is cumulative and league-verified, the section
            # label is presentation. Exactly one game misfiles rows: 774455
            # (P3 GK Out 57:10 / In 58:30 filed under "1st period"); scan
            # 2026-08-06 found no other instance in 1,456 pages.
            t_per = min(t // PERIOD_LEN + 1, 4) if t % PERIOD_LEN else max(t // PERIOD_LEN, 1)
            if per <= 3 and not (t_per == per or t == (per - 1) * PERIOD_LEN):
                per = t_per
            events.append((per, t, _strip(ty), _strip(team), _strip(rest)))

    # ---- goals with running-score side cross-check --------------------------
    h = a = 0
    for per, t, ty, team, rest in events:
        gm = _GOAL.match(ty)
        if not gm:
            continue
        nh, na = int(gm.group(1)), int(gm.group(2))
        side = side_of(team)
        if not (nh == h + (side == "home") and na == a + (side == "away")):
            raise ValueError(f"score {nh}-{na} does not increment {h}-{a} on {side} "
                             f"at {t}s in {events_path.name}")
        h, a = nh, na
        types = [gm.group(3)] + (["ENG"] if gm.group(4) else [])
        out["goals"].append({"t": t, "side": side, "period": per,
                             "en": bool(gm.group(4)), "types": types})
    out["goals"].sort(key=lambda e: e["t"])

    # ---- net-empty intervals from explicit GK events ------------------------
    per_side = {"home": [], "away": []}
    for i, (per, t, ty, team, rest) in enumerate(events):
        if per > 3 or ty not in ("GK In", "GK Out"):
            continue
        per_side[side_of(team)].append((per, t, i, "out" if ty == "GK Out" else "in"))
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

    # ---- EN-flag repair (interval evidence beats a missing ENG flag) --------
    for gl in out["goals"]:
        if gl["period"] > 3 or gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if any(len(tup) == 2 and tup[0] < gl["t"] <= tup[1] for tup in out["empty"][opp]):
            gl["en"] = True
            gl["types"] = gl["types"] + ["EN_corrected"]

    # ---- penalty box windows (explicit begin-end, used directly) ------------
    for per, t, ty, team, rest in events:
        pm = _PEN.match(ty)
        if not pm or per > 3:
            continue
        mins = int(pm.group(1))
        wm = _WINDOW.search(rest)
        if wm:
            begin = _secs(wm.group(1))
            end = _secs(wm.group(2)) if wm.group(2) else None
        else:
            begin = end = None
        if begin is None or (begin == 0 and t > 0):
            # offsetting/coincident (placeholder window) — whistle marker only
            begin, end = t, t
        elif end is None:
            end = begin + mins * 60
        out["penalties"].append({"side": side_of(team), "t": t,
                                 "begin": begin, "end": end,
                                 "misconduct": mins >= 10})

    # ---- head coaches: LineUps first, verified map as fallback --------------
    if lineups_path is None:
        lp = events_path.with_name(events_path.name.replace("_events.html", "_lineups.html"))
        lineups_path = lp if lp.exists() else None
    coaches = {"home": None, "away": None}
    if lineups_path is not None:
        coaches = parse_lineups(lineups_path, home, away)
    for sd in ("home", "away"):
        if coaches[sd] is None and season is not None and date is not None:
            for d0, d1, coach in _coach_map().get((str(season), out[sd]), []):
                if d0 <= date <= d1:
                    coaches[sd] = coach
                    break
    out["coaches"] = coaches
    return out


from hockeycore.gap.segments import extract_instances  # noqa: E402  (rule 15)


def scan_dir(season_dir):
    """One lake season directory -> {game_id: (game_dict, instances)}."""
    season_dir = Path(season_dir)
    out = {}
    for f in sorted(season_dir.glob("game_*_events.html"),
                    key=lambda p: int(p.stem.split("_")[2])):
        num = int(f.stem.split("_")[2])
        try:
            g = parse_game(f)
            out[num] = (g, extract_instances(g, 3))
        except Exception as e:
            out[num] = (None, f"ERROR {e!r}")
    return out
