"""
hockeycore.leagues.ahl — AHL (HockeyTech) adapter: raw lake files → the
interval game dict consumed by hockeycore.gap.segments (rule 15: adapter only,
no gap or betting logic here).

Verified conventions (hand-traced from raw, 2026-08-01 — games 1027795,
1027799, 1027819 of season 90):
- pxpverbose events: shot / penalty / goal / goalie_change / shootout /
  penaltyshot. NO faceoff or stoppage events.
- "s" = ELAPSED seconds within the period (counts up); period_id 1..3, 4=OT.
  Cumulative t = (period_id-1)*1200 + s for periods 1..3.
- goalie_change: goalie_out_id set + goalie_in_id null = net empty (PULL);
  goalie_in_id set = net occupied again; both set = substitution (net never
  empty). A goalie-return row is logged at the same second as every EN goal
  and at delayed-penalty whistles; explicit events = no phantom-inference
  risk (unlike NHL shift reconstruction).
- goal: power_play / empty_net / short_handed / penalty_shot flags ("1"/"0");
  disallowed goals do not appear (no VT0-style rows seen in 27k+ goals).
- penalty: "s" is the penalty clock-time; minutes "2.00"/"5.00"/"10.00".
  No explicit end time -> box windows are begin + minutes*60, with minors
  (2:00) terminated early by the first goal of a NON-penalized side inside
  the window (same approximation as the EIHL adapter; used only for the
  pp_pull-vs-pull classification at the pull second).
- gamesummary: coaches.home/.visitor lists with description "Head Coach";
  ~96% coverage. data/coach_maps/ahl_coaches.csv fills the 8 verified blank
  blocks (join rule: the game's own listing ALWAYS wins; map is fallback).

Open item for the ledger stage (NOT handled here, by design — the adapter
reports segments verbatim): a trailing-team delayed-penalty extra-attacker
inside a gap-3 window would register as a pull segment. Signature = the
return row coincides with an opponent penalty event. The clean-window /
ledger block must measure and rule on these before AHL coach ledgers ship.
"""
import csv
import json
from pathlib import Path

P3_START, P3_END = 2400, 3600
PERIOD_LEN = 1200

_COACH_MAP = None


def _coach_map():
    """(season, team_code) -> [(start, end, coach)] from the verified CSV."""
    global _COACH_MAP
    if _COACH_MAP is None:
        _COACH_MAP = {}
        p = Path(__file__).resolve().parents[2] / "data" / "coach_maps" / "ahl_coaches.csv"
        if p.exists():
            for r in csv.DictReader(open(p, encoding="utf-8")):
                key = (r["season"], r["team_code"])
                _COACH_MAP.setdefault(key, []).append(
                    (r["start_date"], r["end_date"], r["coach"]))
    return _COACH_MAP


SEASON_LABEL = {"77": "20222023", "81": "20232024", "86": "20242025",
                "90": "20252026", "94": "20262027"}


def _cum(e):
    return (int(e["period_id"]) - 1) * PERIOD_LEN + int(e["s"])


def parse_game(pxp_path, summary_path=None, season=None):
    pxp_path = Path(pxp_path)
    if summary_path is None:
        summary_path = pxp_path.with_name(pxp_path.name.replace("_pxp", "_summary"))
    evs = (json.load(open(pxp_path)).get("GC") or {}).get("Pxpverbose") or []
    gs = (json.load(open(summary_path)).get("GC") or {}).get("Gamesummary") or {}

    home_code = (gs.get("home") or {}).get("code")
    away_code = (gs.get("visitor") or {}).get("code")
    date = (gs.get("game_date_iso_8601") or gs.get("game_date") or "")[:10]

    # team_id -> side, from any event carrying the "home" flag
    side_of = {}
    for e in evs:
        if e.get("team_id") and e.get("home") in ("0", "1", 0, 1):
            side_of[str(e["team_id"])] = "home" if str(e["home"]) == "1" else "away"
    # fallback: goalie_change team_code vs summary codes
    code_side = {home_code: "home", away_code: "away"}

    def side(e):
        s = side_of.get(str(e.get("team_id")))
        if s is None:
            s = code_side.get(e.get("team_code"))
        if s is None:
            raise ValueError(f"cannot side event team_id={e.get('team_id')} "
                             f"in {pxp_path.name}")
        return s

    out = {"id": pxp_path.name.split("_")[0], "date": date,
           "home": home_code, "away": away_code,
           "goals": [], "empty": {"home": [], "away": []}, "penalties": []}

    # ---- goals (regulation periods only; OT/shootout never touch P3 logic) --
    for e in evs:
        if e.get("event") != "goal":
            continue
        pid = int(e["period_id"])
        if pid > 4:
            continue  # shootout rows are a separate event type anyway
        out["goals"].append({"t": _cum(e) if pid <= 3 else 3600 + int(e["s"]),
                             "side": side(e), "period": pid,
                             "en": str(e.get("empty_net")) == "1",
                             "types": [f for f, k in
                                       (("PP", "power_play"), ("EN", "empty_net"),
                                        ("SH", "short_handed"), ("PS", "penalty_shot"))
                                       if str(e.get(k)) == "1"]})
    out["goals"].sort(key=lambda e: e["t"])

    # ---- net-empty intervals from explicit goalie_change events -------------
    per_side = {"home": [], "away": []}
    for i, e in enumerate(evs):
        if e.get("event") != "goalie_change":
            continue
        pid = int(e["period_id"])
        if pid > 3:
            continue
        per_side[side(e)].append((pid, _cum(e), i, e))
    for sd, rows in per_side.items():
        rows.sort(key=lambda r: (r[1], r[2]))
        open_at = None
        open_pid = None
        for pid, t, _i, e in rows:
            pulled = e.get("goalie_out_id") and not e.get("goalie_in_id")
            filled = bool(e.get("goalie_in_id"))
            if open_at is not None and pid != open_pid:
                # no return row before intermission: close at period end
                out["empty"][sd].append((open_at, open_pid * PERIOD_LEN))
                open_at = None
            if pulled and open_at is None:
                open_at, open_pid = t, pid
            elif filled and open_at is not None:
                out["empty"][sd].append((open_at, t))
                open_at = None
        if open_at is not None:
            out["empty"][sd].append((open_at, min(open_pid * PERIOD_LEN, 3600)))
        # goalie SUBSTITUTION after a goal against is logged as PULL+IN at the
        # same second -> zero-length interval = never actually empty (found via
        # EN cross-check leg B, 297 cases / 4 seasons). Drop them.
        out["empty"][sd] = [(b, e2) for b, e2 in out["empty"][sd] if e2 > b]

    # ---- EN-goal evidence repair (measured 2026-08-01) ----------------------
    # 15 games / 4 seasons (0.3%) have an empty_net-flagged goal with NO
    # goalie_change logged at all (feed failure). The EN flag is itself proof
    # the net was empty (rule 5), so synthesize a 1-second evidence segment,
    # marked synthetic=True -> pull TRUE for the ledger, timing UNKNOWN.
    # (Return rows logged up to 3s before the goal are mere clock skew, not
    # missing pulls -> covered by the tolerance below, no synthesis.)
    for gl in out["goals"]:
        if gl["period"] > 3 or not gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if not any(b - 3 <= gl["t"] <= e2 + 3 for b, e2, *_ in out["empty"][opp]):
            out["empty"][opp].append((gl["t"] - 1, gl["t"], "synthetic"))
    for sd in ("home", "away"):
        out["empty"][sd].sort(key=lambda x: (x[0], x[1]))

    # ---- EN-flag repair (the symmetric feed failure, 1 case / 4 seasons) ----
    # A goal scored while the conceding side's net is explicitly empty (real
    # goalie_change interval, not synthetic) but missing the empty_net flag:
    # the 55s-explicit-interval evidence beats the flag. Correct and mark.
    for gl in out["goals"]:
        if gl["period"] > 3 or gl["en"]:
            continue
        opp = "away" if gl["side"] == "home" else "home"
        if any(len(tup) == 2 and tup[0] < gl["t"] <= tup[1] for tup in out["empty"][opp]):
            gl["en"] = True
            gl["types"] = gl["types"] + ["EN_corrected"]

    # ---- penalty box windows (for pp_pull classification only) --------------
    pens = []
    for e in evs:
        if e.get("event") != "penalty":
            continue
        pid = int(e["period_id"])
        if pid > 3:
            continue
        try:
            mins = float(e.get("minutes") or 0)
        except ValueError:
            mins = 0.0
        if mins <= 0:
            continue
        pens.append({"side": side(e), "t": _cum(e),
                     "begin": _cum(e), "end": _cum(e) + int(mins * 60),
                     "minor": mins == 2.0})
    # minors end early on the first goal by a non-penalized side in-window
    for p in pens:
        if not p["minor"]:
            continue
        for gl in out["goals"]:
            if p["begin"] < gl["t"] < p["end"] and gl["side"] != p["side"]:
                p["end"] = gl["t"]
                break
    out["penalties"] = [{k: p[k] for k in ("side", "t", "begin", "end")} for p in pens]

    # ---- head coaches: game listing first, verified map as fallback ---------
    coaches = {}
    co = gs.get("coaches") or {}
    for sd, key in (("home", "home"), ("away", "visitor")):
        hcs = [f'{c["first_name"]} {c["last_name"]}' for c in (co.get(key) or [])
               if c.get("description") == "Head Coach"]
        name = hcs[0] if hcs else None
        if name is None and season is not None and date:
            slabel = SEASON_LABEL.get(str(season), str(season))
            code = home_code if sd == "home" else away_code
            for d0, d1, coach in _coach_map().get((slabel, code), []):
                if d0 <= date <= d1:
                    name = coach
                    break
        coaches[sd] = name
    out["coaches"] = coaches
    return out


def scan_dir(season_dir):
    """One lake season directory -> {game_id: (game_dict, instances)}."""
    from hockeycore.gap.segments import extract_instances
    season_dir = Path(season_dir)
    season = season_dir.name
    out = {}
    for f in sorted(season_dir.glob("*_pxp.json")):
        gid = f.name.split("_")[0]
        try:
            g = parse_game(f, season=season)
            out[gid] = (g, extract_instances(g, 3))
        except Exception as e:
            out[gid] = (None, f"ERROR {e!r}")
    return out
