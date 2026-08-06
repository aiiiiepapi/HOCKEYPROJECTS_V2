"""
hockeycore.leagues.khl — KHL adapter: raw text.khl.ru broadcast HTML +
www.khl.ru protocol HTML → the interval game dict consumed by
hockeycore.gap.segments (rule 15: adapter only, no gap or betting logic).

Verified conventions (hand-traced from raw lake, 2026-08-07 — GT batch 1,
14 games / 15 instances, tests/ground_truth_khl.json; full trace notes in
docs/ground_truth_traces/khl_batch1_2026-08-07.md; every GT empty-interval
list reconciles to the second with the protocol team per-period ВППВ table):

- TEXT channel: one `div.textBroadcast-item[ filter-ready]` per event,
  NEWEST-FIRST (reversed here). Play events carry cumulative game-clock
  MM:SS; period/game boundary lines (`Начало/Окончание N периода|игры|
  овертайма|серии бросков`) carry WALL clock — the two ranges collide
  (881356: P1 goal 19:58 cumulative vs `Начало 2 периода` 19:58 wall), so
  every classification keys on event TEXT, never on the time column.
  Free-text commentary also carries times; only exact phrases are events.
- Sides: preview frame order (left club = home = first team in <title>);
  event text carries the team name (`<Team>. Замена вратаря…`,
  `Изменение счета: <Team>. …`, `Удаление. <Team>. …`, `Отложенный штраф у
  команды <Team>`) — matched longest-name-first (Динамо М / Динамо Мн).
- Pull = `<Team>. Замена вратаря на экстра-полевого игрока`; return =
  `<Team>. Вратарь в воротах`. Mid-game goalie SUBSTITUTION is the other
  word order — `Замена вратаря. <Team>. <new> вместо <old>` — never an
  interval (881261 27:43; 886161 period-boundary swaps at 20:00/40:00).
  AHL interval conventions inherited: OUT-first same-second normalization,
  close at period end when no return logged, zero-length dropped,
  period>3 never intervals.
- GOALS from the PROTOCOL `Заброшенные шайбы` table (authority: period col
  `1/2/3/1 ОТ/РБ`, cumulative `MM′SS′′` clock, running score `H:A`,
  strength `рав./бол./мен./бул.`, scorer, on-ice jersey lists BOTH teams).
  `РБ` (shootout decision) rows are excluded but their score increment is
  consumed knowingly (889995). Side = which component of the running score
  incremented (rule 10: raises otherwise). The TEXT goal lines (which DO
  carry time+score+strength in all four seasons — the scrape-round "no
  time on goals" claim is wrong) are fully cross-checked 1:1 against the
  protocol rows: count, time, side; mismatch raises.
- EN: text flag `В пустые ворота.` on the goal line OR protocol
  jersey-absence (conceding team's on-ice list non-empty and missing all
  its goalie numbers from the «Вратари» tables; home table listed first,
  checked against the `В воротах:` starting line when present). The two
  agreed on every GT case; either is evidence (EN_jersey type notes a
  jersey-only detection). `С экстра-полевым игроком.` = scorer's OWN net
  empty (881270/881827/886161) — NOT an ENG, never sets en. Interval-based
  EN evidence repair inherited verbatim from the AHL/Mestis adapters:
  en goal with no covering interval → synthetic 1s segment; interval-
  covered goal missing the flag → en corrected.
- PENALTIES from the text `Удаление.` rows (exact MM:SS in all seasons),
  cross-checked as a (side,t,mins) multiset against the protocol fineTable
  (its mins-0 rows = penalty-shot awards, no box, excluded both sides —
  881270 19:13, 886161 05:49). Same-second same-player duplicate rows are
  REAL double minors, NOT feed dupes — refuted the scrape-session dedupe
  note with the protocol team ВПМ tables (898094 Бреус 2+2: full strength
  at +4:00, ВПМ 6:41 exact; 881261 Минулин 2+2: ВПМ 1:34/2:06 exact).
  Box-window model (verified to the second against team ВПМ/ВПБ on
  881261/881270/881725/898094, corroborated on 881827/897536/897655):
    * >=10 min (incl. 20-min disciplinary) = misconduct class — window
      kept as whistle marker, no strength effect (2026-08-02 fix);
    * coincident equal-length penalties cancel pairwise across teams at
      one second (offense-matched pairs first) — cancelled rows become
      zero-length whistle markers (881270 quad 2+2v2+2; 898094 «Игра 4 на
      4» pair; 889939 fighting 5v5);
    * same player's multiple remaining minors at one second are served
      CONSECUTIVELY (stacked windows — 898094/889859/889939/897655);
    * a goal by the team whose opponent holds MORE active windows releases
      the opponent's earliest-ending active minor (net-short single
      release; majors never release — 881261 Полтапов, 897655 Колесников;
      equal boxes never release — 881827 18:26). Explicit `полном составе`
      end events (minute-only or absent in 2023/2024, exact 2025/2026,
      wording varies incl. «Куньлунь Ред Стар» for Куньлунь РС) are NOT
      parsed for logic — every exact-time one in GT matched the computed
      release to the second.
- DELAYED PENALTIES: `Отложенный штраф у команды <Team>` is explicit but
  carries NO time and the channel is PARTIAL (games with >=1: 2/748,
  110/782, 382/782, 425/748 by season). Parsed into game["dp_events"]
  with the neighbouring timed events as a position bracket — consumed by
  the runner's aux export (data/derived/khl_dp_events.json) for the
  Manager's rulings-17/17b cross-calibration. Rulings 17/17b themselves
  are NOT modified (kickoff order); GT holds three in-window dp cases the
  engine rules correctly (886161 + 889859 explicit, 889995 invisible).
- COACHES: preview frame `preview-frame__club-nameTrainer` rows (left =
  home). Census is 100.0% (Manager-verified) — NO map fallback exists; a
  missing coach raises. Name-format drift across seasons («Никитин Игорь»
  2024 vs «Никитин Игорь Валерьевич» 2025 — same person) is a ledger-side
  identity question recorded in the handoff; emitted verbatim.
- Shootout attempt rows (`Послематчевый буллит: …`), PS awards
  (`Буллит (<Team>). Наказан. …`), timeouts, ad breaks, icing/offside and
  commentary are never events. OT goals: protocol `1 ОТ` → period 4
  (881270 63:35, engine-ignored).
- Games keyed (season, gameId); gameIds are site-global.
"""
import html as _html
import re
from collections import defaultdict
from pathlib import Path

P3_START, P3_END = 2400, 3600
PERIOD_LEN = 1200

_ITEM = re.compile(
    r'<div class="textBroadcast-item(?: filter-ready)?">(.*?)'
    r'(?=<div class="textBroadcast-item(?: filter-ready)?">|'
    r'<div class="textBroadcast-statistics)', re.S)
_TIME_EL = re.compile(r'left-time[^"]*">\s*(.*?)\s*</', re.S)
_TEXT_EL = re.compile(r'right-text[^"]*">(.*?)</div>', re.S)
_CLUB = re.compile(r'preview-frame__club-nameClub[^>]*>\s*([^<]+?)\s*</p>')
_TRAINER = re.compile(r'preview-frame__club-nameTrainer[^>]*>\s*([^<]+?)\s*</p>')
_MMSS = re.compile(r"^(\d{1,3}):(\d{2})$")
_PROTO_T = re.compile(r"^(\d{1,3})\D+(\d{2})\D*$")          # 01′23′′
_PEN_TXT = re.compile(r"^Удаление\.\s*(.+?)\.\s*(?:(\d+)\.\s*)?(.*?)\.?\s*(\d+)\s*мин\.\s*(.*?)\.?(?:\s*Отбывал:.*)?$")
_TITLE_DATE = re.compile(r"матч КХЛ (\d{1,2}) (\w+) (\d{4})")
_MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
           "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
           "ноября": 11, "декабря": 12}


def _strip(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _secs(mm, ss):
    return int(mm) * 60 + int(ss)


def _parse_protocol(praw, home, away):
    """Goals (authoritative), goalie numbers per side, penalty multiset."""
    # --- goalie numbers: two «Вратари» player tables, home first ------------
    gk = []
    for m in re.finditer(r"Вратари</h3>", praw):
        seg = praw[m.start():m.start() + 60000]
        tb, te = seg.find("<tbody"), seg.find("</tbody>")
        nums = set()
        for r in re.findall(r"<tr>(.*?)</tr>", seg[tb:te], re.S):
            cells = [_strip(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", r, re.S)]
            if len(cells) >= 2 and cells[0].isdigit():
                nums.add(int(cells[0]))
        gk.append(nums)
    if len(gk) < 2 or not gk[0] or not gk[1]:
        raise ValueError("protocol goalie tables missing")
    goalies = {"home": gk[0], "away": gk[1]}

    # --- goals table --------------------------------------------------------
    i = praw.find("Заброшенные шайбы</h3>")
    if i < 0:
        raise ValueError("protocol goals header missing")
    j = praw.find("</table>", i)
    goals = []
    h = a = 0
    for r in re.findall(r"<tr>(.*?)</tr>", praw[i:j], re.S)[1:]:
        cells = [_strip(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(cells) < 10:
            raise ValueError(f"goal row with {len(cells)} cells")
        per_txt, t_txt, score, strength = cells[1], cells[2], cells[3], cells[4]
        nh, na = (int(x) for x in score.split(":"))
        if per_txt == "РБ":                      # shootout decision: not a goal,
            h, a = nh, na                        # but the score increment is real
            continue
        tm = _PROTO_T.match(t_txt)
        if not tm:
            raise ValueError(f"unparseable goal time {t_txt!r}")
        t = _secs(tm.group(1), tm.group(2))
        period = 4 if "ОТ" in per_txt else int(per_txt)
        if period <= 3:
            t_per = min((t - 1) // PERIOD_LEN + 1, 3) if t > 0 else 1
            if t_per != period:
                raise ValueError(f"goal period {period} vs clock {t_txt}")
        if nh == h + 1 and na == a:
            side = "home"
        elif na == a + 1 and nh == h:
            side = "away"
        else:
            raise ValueError(f"score {score} does not increment {h}:{a}")
        h, a = nh, na
        onice = {"home": cells[8], "away": cells[9]}
        conceder = "away" if side == "home" else "home"
        lst = {int(x) for x in re.findall(r"\d+", onice[conceder])}
        en_jersey = bool(lst) and not (lst & goalies[conceder])
        st = {"рав.": "EV", "бол.": "PP", "мен.": "SH"}.get(strength, strength)
        goals.append({"t": t, "side": side, "period": period,
                      "en": en_jersey, "types": [st] + (["EN_jersey"] if en_jersey else [])})

    # --- penalty multiset from fineTable (both team columns) ---------------
    i = praw.find("Штраф</h3>")
    seg = praw[i:]
    seg = seg[:seg.find("</section>")] if "</section>" in seg else seg[:40000]
    li, ri = seg.find("fineTable-table_left"), seg.find("fineTable-table_right")
    pens = []
    for side, body in (("home", seg[li:ri]), ("away", seg[ri:])):
        for lw in re.findall(r'<div class="fineTable-table__line-wrapp">(.*?)</div>\s*</div>\s*</div>', body, re.S):
            cells = [_strip(c) for c in re.findall(r'<p class="fineTable-table__line-text[^"]*">(.*?)</p>', lw, re.S)]
            if len(cells) >= 3 and _MMSS.match(cells[0]) and cells[2].isdigit():
                mins = int(cells[2])
                if mins == 0:
                    continue                      # penalty-shot award, no box
                mm, ss = cells[0].split(":")
                pens.append((side, _secs(mm, ss), mins))
    return goals, goalies, pens


def parse_game(text_path, protocol_path=None, season=None):
    text_path = Path(text_path)
    m = re.match(r"(?:game_(\d{4})_)?(\d+)_text", text_path.stem)
    if season is None and m and m.group(1):
        season = m.group(1)
    gid = m.group(2) if m else text_path.stem
    if protocol_path is None:
        protocol_path = text_path.with_name(text_path.name.replace("_text.html", "_protocol.html"))
    traw = text_path.read_text(encoding="utf-8", errors="replace")
    praw = Path(protocol_path).read_text(encoding="utf-8", errors="replace")

    clubs = [_strip(c) for c in _CLUB.findall(traw)]
    if len(clubs) < 2:
        raise ValueError(f"preview clubs missing in {text_path.name}")
    home, away = clubs[0], clubs[1]
    dm = _TITLE_DATE.search(_strip(re.search(r"<title>(.*?)</title>", praw, re.S).group(1)))
    date = (f"{dm.group(3)}-{_MONTHS[dm.group(2)]:02d}-{int(dm.group(1)):02d}"
            if dm and dm.group(2) in _MONTHS else None)
    if date is None:
        raise ValueError(f"protocol title date unparseable for {gid}")

    out = {"id": f"{season}_{gid}", "season": season, "game_id": int(gid),
           "date": date, "home": home, "away": away,
           "goals": [], "empty": {"home": [], "away": []}, "penalties": [],
           "dp_events": []}
    names = sorted([(home, "home"), (away, "away")], key=lambda x: -len(x[0]))

    def side_of(txt, pat):
        for nm, sd in names:
            if txt.startswith(pat.format(nm)) or pat.format(nm) in txt:
                return sd
        return None

    # ---- text items, chronological ----------------------------------------
    items = []
    for im in _ITEM.finditer(traw):
        body = im.group(1)
        tm, tx = _TIME_EL.search(body), _TEXT_EL.search(body)
        t_txt = _strip(tm.group(1)) if tm else ""
        txt = _strip(tx.group(1)) if tx else ""
        if txt:
            items.append((t_txt, txt))
    items.reverse()

    period = 0
    last_t = None                                  # last timed play event (dp bracket)
    text_goals, pulls, text_pens = [], [], []
    for t_txt, txt in items:
        pm = re.match(r"^Начало (\d) периода", txt)
        if pm:
            period = int(pm.group(1))
            continue
        if txt.startswith("Начало овертайма"):
            period = 4
            continue
        if txt.startswith("Начало серии бросков"):
            period = 5
            continue
        if txt.startswith(("Окончание", "Начало игры")):
            continue                               # wall-clock boundary lines
        mm = _MMSS.match(t_txt)
        t = _secs(*t_txt.split(":")) if mm else None
        if txt.startswith("Отложенный штраф у команды"):
            sd = side_of(txt, "Отложенный штраф у команды {}")
            out["dp_events"].append({"side": sd, "period": period,
                                     "after_t": last_t, "raw": txt})
            continue
        if t is None or period == 0 or period == 5:
            continue                               # untimed/minute-only/SO rows
        # rule 10: cumulative clock must agree with the running period
        if period <= 3:
            t_per = min((t - 1) // PERIOD_LEN + 1, 3) if t > 0 else 1
            if not (t_per == period or t == (period - 1) * PERIOD_LEN):
                # minute-only times ("NN мин") never reach here (regex is MM:SS)
                raise ValueError(f"period {period} vs clock {t_txt} in {text_path.name}: {txt[:60]!r}")
        if txt.startswith("Изменение счета"):
            sd = side_of(txt, "Изменение счета: {}.")
            if sd is None:
                raise ValueError(f"goal side unmatched: {txt[:80]!r}")
            text_goals.append({"t": t, "side": sd, "period": period,
                               "pv": "В пустые ворота" in txt,
                               "ea": "С экстра-полевым игроком" in txt})
            last_t = t
            continue
        if "Замена вратаря на экстра-полевого игрока" in txt and not txt.startswith("Замена вратаря."):
            sd = side_of(txt, "{}. Замена вратаря")
            if sd is None:
                raise ValueError(f"pull side unmatched: {txt[:80]!r}")
            pulls.append((period, t, len(pulls), sd, "out"))
            last_t = t
            continue
        if re.match(r"^.+?\. Вратарь в воротах", txt) and not txt.startswith("Замена вратаря."):
            sd = side_of(txt, "{}. Вратарь в воротах")
            if sd is not None:                     # None = commentary mention
                pulls.append((period, t, len(pulls), sd, "in"))
                last_t = t
                continue
        if txt.startswith("Удаление."):
            pmt = _PEN_TXT.match(txt)
            sd = side_of(txt, "Удаление. {}.")
            if sd is None or not pmt:
                raise ValueError(f"penalty unparsed: {txt[:90]!r}")
            mins = int(pmt.group(4))
            offense = pmt.group(5)
            player = f"{pmt.group(2) or ''} {pmt.group(3)}".strip()
            text_pens.append({"side": sd, "t": t, "period": period,
                              "mins": mins, "player": player, "offense": offense})
            last_t = t
            continue
        last_t = t if t is not None else last_t

    # ---- protocol authority + cross-checks (rule 10) -----------------------
    goals, goalies, proto_pens = _parse_protocol(praw, home, away)
    reg_text = [g for g in text_goals if g["period"] <= 4]
    reg_proto = [g for g in goals]
    if len(reg_text) != len(reg_proto):
        raise ValueError(f"goal count text {len(reg_text)} != protocol {len(reg_proto)} in {gid}")
    for tg, pg in zip(sorted(reg_text, key=lambda g: g["t"]), reg_proto):
        if tg["t"] != pg["t"] or tg["side"] != pg["side"]:
            raise ValueError(f"goal mismatch text {tg} vs protocol {pg} in {gid}")
        if tg["pv"] and not pg["en"]:
            pg["en"] = True                        # text EN flag is evidence too
            pg["types"] = pg["types"] + ["EN_text"]
        if pg["en"] and tg["ea"]:
            raise ValueError(f"EN vs extra-attacker contradiction at {pg['t']} in {gid}")
    out["goals"] = sorted(goals, key=lambda e: e["t"])
    if sorted((p["side"], p["t"], p["mins"]) for p in text_pens) != sorted(proto_pens):
        raise ValueError(f"penalty multiset text != protocol in {gid}")

    # ---- net-empty intervals (AHL conventions inherited) -------------------
    per_side = {"home": [], "away": []}
    for per, t, i, sd, kind in pulls:
        if per <= 3:
            per_side[sd].append((per, t, i, kind))
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

    # ---- EN-goal evidence repair (AHL rule, inherited verbatim) ------------
    for gl in out["goals"]:
        if gl["period"] > 3 or not gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if not any(b - 3 <= gl["t"] <= e + 3 for b, e, *_ in out["empty"][opp]):
            out["empty"][opp].append((gl["t"] - 1, gl["t"], "synthetic"))
    for sd in ("home", "away"):
        out["empty"][sd].sort(key=lambda x: (x[0], x[1]))

    # ---- EN-flag repair (interval evidence beats a missing flag) -----------
    for gl in out["goals"]:
        if gl["period"] > 3 or gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if any(len(tup) == 2 and tup[0] < gl["t"] <= tup[1] for tup in out["empty"][opp]):
            gl["en"] = True
            gl["types"] = gl["types"] + ["EN_corrected"]

    # ---- starting goalies cross-check (rule 10) ----------------------------
    for t_txt, txt in items:
        sm = re.match(r"^Начало 1 периода В воротах:\s*(.*)$", txt)
        if sm:
            for num, team in re.findall(r"(\d+)\.\s*[^(]+?\(([^)]+)\)", sm.group(1)):
                sd = "home" if team == home else "away" if team == away else None
                if sd and int(num) not in goalies[sd]:
                    raise ValueError(f"starting goalie {num} not in protocol "
                                     f"{sd} goalie table in {gid}")
            break

    # ---- penalty box windows: cancellation, stacking, net-short release ----
    for p in text_pens:
        p["misconduct"] = p["mins"] >= 10
        p["begin"] = p["t"]
        p["end"] = p["t"] + p["mins"] * 60
    strength_rows = [p for p in text_pens if not p["misconduct"]]
    # coincident cancellation: per (t, mins) bucket, offense-matched pairs first
    buckets = defaultdict(lambda: {"home": [], "away": []})
    for p in strength_rows:
        buckets[(p["t"], p["mins"])][p["side"]].append(p)
    for (_t, _m), sides in buckets.items():
        hs, as_ = sides["home"], sides["away"]
        n = min(len(hs), len(as_))
        for _ in range(n):
            hp = next((x for x in hs for y in as_ if x["offense"] == y["offense"]), hs[0])
            ap = next((y for y in as_ if y["offense"] == hp["offense"]), as_[0])
            hs.remove(hp); as_.remove(ap)
            hp["end"] = hp["begin"] = hp["t"]      # cancelled: whistle marker only
            ap["end"] = ap["begin"] = ap["t"]
    # same-player stacking (remaining rows sharing side+player+t serve consecutively)
    bypp = defaultdict(list)
    for p in strength_rows:
        if p["end"] > p["begin"]:
            bypp[(p["side"], p["t"], p["player"])].append(p)
    for rows in bypp.values():
        for k, p in enumerate(rows):
            p["begin"] = p["t"] + k * p["mins"] * 60
            p["end"] = p["begin"] + p["mins"] * 60
    # net-short single release on goals (minors only, earliest-ending active)
    live = [p for p in strength_rows if p["end"] > p["begin"]]
    for gl in out["goals"]:
        t = gl["t"]
        opp = "away" if gl["side"] == "home" else "home"
        n_opp = [p for p in live if p["side"] == opp and p["begin"] <= t < p["end"]]
        n_own = [p for p in live if p["side"] == gl["side"] and p["begin"] <= t < p["end"]]
        if len(n_opp) > len(n_own):
            rel = min((p for p in n_opp if p["mins"] == 2), default=None,
                      key=lambda p: p["end"])
            if rel is not None:
                rel["end"] = t
    out["penalties"] = [{"side": p["side"], "t": p["t"], "begin": p["begin"],
                         "end": p["end"], "misconduct": p["misconduct"]}
                        for p in text_pens]

    # ---- coaches: preview frame, left = home; 100% census, no map ----------
    trainers = [_strip(c) for c in _TRAINER.findall(traw)]
    if len(trainers) < 2 or not trainers[0] or not trainers[1]:
        raise ValueError(f"coach rows missing in {text_path.name} (census says 100% — parser bug)")
    out["coaches"] = {"home": trainers[0], "away": trainers[1]}
    return out


from hockeycore.gap.segments import extract_instances  # noqa: E402  (rule 15)


def scan_dir(season_dir):
    """One lake season directory -> {game_id: (game_dict, instances)}."""
    season_dir = Path(season_dir)
    out = {}
    for f in sorted(season_dir.glob("*_text.html"),
                    key=lambda p: int(p.stem.split("_")[0])):
        num = int(f.stem.split("_")[0])
        try:
            g = parse_game(f)
            out[num] = (g, extract_instances(g, 3))
        except Exception as e:
            out[num] = (None, f"ERROR {e!r}")
    return out
