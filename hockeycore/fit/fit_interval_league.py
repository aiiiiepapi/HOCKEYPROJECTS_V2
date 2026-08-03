"""
fit_interval_league.py — AHL / Liiga pricer fits in the mc_pricer schema.

One pricer, league fit dicts (rule 15): emits data/derived/fits_{league}{sfx}.json
with the exact keys mc_pricer.rebuild() consumes (hazard / m_PP / rates /
rates_R / pen) plus an aux dict (return, repull, lag, dead) the backtest wires
into MP._ret/_REPULL/_LAG/_DEAD.

League specifics (all measured 2026-08-01):
- evidence lag = 0 (explicit goalie_change / goalKeeperEvents; NHL's 9s lag is
  a shift-inference artifact that does not exist here; AHL clock skew <=3s).
- dead time = 18s (re-measured per league, same shape as NHL).
- AHL pools all listed seasons (no era drift 26-35%); Liiga 2023 has no goalie
  channel and is EXCLUDED from hazard/EN fits but INCLUDED in full-net goal
  rates (goal flags exist).
- hazard bins: 60s (AHL), 120s (Liiga — 98 gap-3 pulls total, thin).

Usage:
  python3 hockeycore/fit/fit_interval_league.py ahl              # all seasons
  python3 hockeycore/fit/fit_interval_league.py ahl --train      # drop last season
  python3 hockeycore/fit/fit_interval_league.py liiga [--train]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hockeycore.gap.segments import extract_instances          # noqa: E402
from hockeycore.leagues import ahl as ahl_mod, liiga as liiga_mod, mestis as mestis_mod  # noqa: E402

DER = ROOT / "data" / "derived"

CFG = {
    "ahl": {"lake": Path("/home/claude/work/ahl_lake"),
            "seasons": ["77", "81", "86", "90"], "holdout": "90",
            "no_goalie": set(), "hbin": 60},
    "liiga": {"lake": Path("/home/claude/work/liiga_lake"),
              "seasons": ["2023", "2024", "2025", "2026"], "holdout": "2026",
              "no_goalie": {"2023"}, "hbin": 120},
    # Mestis (added 2026-08-03): goalie channel present in ALL 4 seasons;
    # 82 gap-3 EV pulls total -> Liiga-thin, hbin 120.
    "mestis": {"lake": Path("/home/claude/work/mestis_lake/mestis"),
               "seasons": ["2023", "2024", "2025", "2026"], "holdout": "2026",
               "no_goalie": set(), "hbin": 120},
}


def iter_games(league, seasons):
    cfg = CFG[league]
    for season in seasons:
        d = cfg["lake"] / season
        if league == "ahl":
            files = sorted(d.glob("*_pxp.json"))
        elif league == "mestis":
            files = sorted(d.glob("game_*_seuranta.html"),
                           key=lambda p: int(p.stem.split("_")[2]))
        else:
            files = sorted(d.glob("game_*.json"), key=lambda p: int(p.stem.split("_")[2]))
        for f in files:
            if league == "ahl":
                g = ahl_mod.parse_game(f, season=season)
            elif league == "mestis":
                g = mestis_mod.parse_game(f)
            else:
                g = liiga_mod.parse_game(f)
            yield season, g


def state_of(u_abs, empty_iv, boxes_t, boxes_l):
    """state at absolute second u for the TRAILING side."""
    en = any(b <= u_abs < e for b, e in empty_iv)
    tb = any(b <= u_abs < e for b, e in boxes_t)
    lb = any(b <= u_abs < e for b, e in boxes_l)
    if tb and not lb:
        return "EN_pk" if en else "TPK_full"
    if lb and not tb:
        return "EN_pp" if en else "TPP_full"
    return "EN_ev" if en else "EV_full"


def main(league, train=False, seasons_override=None):
    cfg = CFG[league]
    seasons = seasons_override or (cfg["seasons"][:-1] if train else cfg["seasons"])
    sfx = ("_train" if train else "") if not seasons_override else "_train"
    hbin = cfg["hbin"]

    exp = defaultdict(float)        # (gap, state) -> seconds
    goals = defaultdict(int)        # (gap, state, dir) -> n
    expR = defaultdict(float)       # (gap, state, Rbin) -> seconds (EV_full/EN_ev)
    goalsR = defaultdict(int)
    atrisk = defaultdict(float)     # (gap, hbin_idx) EV full-net pre-pull secs
    pulls = defaultdict(int)        # (gap, hbin_idx) EV pull events
    pp_secs = defaultdict(float)    # gap -> TPP full-net pre-pull secs
    pp_pulls = defaultdict(int)
    ev_secs_prepull = defaultdict(float)
    ev_pulls_n = defaultdict(int)
    pen_ev_secs = defaultdict(float)
    pen_events = defaultdict(lambda: [0, 0])   # gap -> [on_trailer, on_leader]
    ret_events = 0
    pulled_secs = 0.0
    repull_events = 0
    between_secs = 0.0

    RBINS = {"EV_full": [(0, 150), (150, 300), (300, 450), (450, 600),
                         (600, 750), (750, 900), (900, 1050), (1050, 1200)],
             "EN_ev": [(0, 60), (60, 120), (120, 180), (180, 300), (300, 1200)]}

    for season, g in iter_games(league, seasons):
        has_goalie = season not in cfg["no_goalie"]
        for gap in (2, 3, 4):
            for inst in extract_instances(g, gap):
                tn = inst["trailing"]
                o, c = inst["opened_secs"], min(inst["closed_secs"], 1200)
                segs = inst["pull_segments"] if has_goalie else []
                empty_iv = [(s["empty_from"] + 2400, s["empty_until"] + 2400)
                            for s in segs]
                boxes_t = [(p["begin"], p["end"]) for p in g["penalties"]
                           if p["side"] == tn and p["end"] > 2400]
                boxes_l = [(p["begin"], p["end"]) for p in g["penalties"]
                           if p["side"] != tn and p["end"] > 2400]
                gset = {gl["t"]: gl for gl in g["goals"]
                        if gl.get("period") == 3 and o < gl["t"] - 2400 <= c}
                dead_from = sorted([o] + [gl - 2400 for gl in gset])
                ev_first = next((s for s in segs if not s.get("dp_artifact")), None)
                first_pull_u = ev_first["empty_from"] if ev_first else None
                for u in range(o, c):
                    ua = u + 2400
                    if any(d <= u < d + 18 for d in dead_from):
                        continue
                    st = "EV_full" if not has_goalie else \
                        state_of(ua, empty_iv, boxes_t, boxes_l)
                    if not has_goalie and (any(b <= ua < e for b, e in boxes_t)
                                           or any(b <= ua < e for b, e in boxes_l)):
                        continue    # no-goalie season: only unambiguous full-net EV
                    exp[(gap, st)] += 1
                    gl = gset.get(ua + 1)
                    scored = gl is not None
                    d = None
                    if scored:
                        d = "for" if gl["side"] == tn else "against"
                        goals[(gap, st, d)] += 1
                    R = 1200 - u
                    if st in RBINS:
                        for lo, hi in RBINS[st]:
                            if lo <= R < hi:
                                expR[(gap, st, (lo, hi))] += 1
                                if scored:
                                    goalsR[(gap, st, (lo, hi), d)] += 1
                                break
                    # hazard exposure: full net, 5v5, pre-first-EV-pull
                    if has_goalie and st == "EV_full" and \
                            (first_pull_u is None or u < first_pull_u):
                        atrisk[(gap, (R - 1) // hbin)] += 1
                        pen_ev_secs[gap] += 1
                    if has_goalie and st == "TPP_full" and \
                            (first_pull_u is None or u < first_pull_u):
                        pp_secs[gap] += 1
                if not has_goalie:
                    continue
                # events
                for si, s in enumerate(segs):
                    if s.get("dp_artifact"):
                        continue
                    R_ev = 1200 - s["empty_from"]
                    at_pp = any(b <= s["empty_from"] + 2400 < e for b, e in boxes_l)
                    if si == 0 or not segs[si - 1].get("dp_artifact") is False:
                        pass
                    if s is ev_first:
                        if at_pp:
                            pp_pulls[gap] += 1
                        else:
                            pulls[(gap, (R_ev - 1) // hbin)] += 1
                            ev_pulls_n[gap] += 1
                    else:
                        repull_events += 1
                    pulled_secs += max(s["empty_until"] - s["empty_from"], 1)
                    if s["empty_until"] < c and (s["empty_until"] + 2400 + 1) not in gset \
                            and (s["empty_until"] + 2400) not in gset:
                        ret_events += 1
                # seconds between segments (repull exposure)
                real = [s for s in segs if not s.get("dp_artifact")]
                for a, b in zip(real, real[1:]):
                    between_secs += max(b["empty_from"] - a["empty_until"], 0)
                for p in g["penalties"]:
                    if 2400 + o <= p["begin"] < 2400 + c:
                        pen_events[gap][0 if p["side"] == tn else 1] += 1

    # ---- EN-rate shrinkage toward the cross-gap pool (2026-08-01) ----------
    # Rare-event rates from thin gap cells are noise (Liiga gap-3 'for' = 6
    # events -> 3.9/60 vs pooled truth ~7). NHL (large T) shows 6v5-for is
    # flat across gaps and 'against' differs mildly, so shrink each gap cell
    # toward the pooled(2-4) rate with pseudo-exposure TAU: big cells keep
    # their own number, thin cells inherit the pool.
    TAU = 20000.0
    for st in ("EN_ev", "EN_pp", "EN_pk"):
        for d in ("for", "against"):
            Tp = sum(exp[(g, st)] for g in (2, 3, 4))
            Gp = sum(goals[(g, st, d)] for g in (2, 3, 4))
            if Tp <= 0:
                continue
            r_pool = Gp / Tp
            for g in (2, 3, 4):
                T = exp[(g, st)]
                goals[(g, st, d)] = goals[(g, st, d)] + r_pool * TAU
                # exposure inflated symmetrically at build below via _shrunkT
            _ = r_pool
    _shrunkT = {}
    for st in ("EN_ev", "EN_pp", "EN_pk"):
        for g in (2, 3, 4):
            _shrunkT[(g, st)] = exp[(g, st)] + TAU

    GK = {2: "2", 3: "3", 4: "4"}
    fits = {"hazard": {}, "m_PP": {}, "rates": {}, "rates_R": {}, "pen": {}}
    for gap in (2, 3, 4):
        bins = []
        for bi in range(0, 1200 // hbin):
            T = atrisk[(gap, bi)]
            h = pulls[(gap, bi)] / T if T >= 300 else None
            bins.append({"R_lo": bi * hbin, "R_hi": (bi + 1) * hbin,
                         "h": h if h is not None else 0.0, "T": T})
        fits["hazard"][GK[gap]] = {"EV_full": bins}
        ev_rate = ev_pulls_n[gap] / max(pen_ev_secs[gap], 1)
        pp_rate = pp_pulls[gap] / max(pp_secs[gap], 1)
        fits["m_PP"][GK[gap]] = {"m": (pp_rate / ev_rate) if ev_rate > 0 else 1.0}
        fits["rates"][GK[gap]] = {}
        for st in ("EV_full", "TPP_full", "TPK_full", "EN_ev", "EN_pp", "EN_pk"):
            for d in ("for", "against"):
                T = _shrunkT.get((gap, st), exp[(gap, st)])
                fits["rates"][GK[gap]][f"{st}:{d}"] = {
                    "T": T, "rate_per_60min":
                        (goals[(gap, st, d)] / T * 3600) if T > 0 else None}
        fits["rates_R"][GK[gap]] = {}
        for st, bl in RBINS.items():
            for d in ("for", "against"):
                rows = []
                for lo, hi in bl:
                    T = expR[(gap, st, (lo, hi))]
                    rows.append({"R_lo": lo, "R_hi": hi, "T": T,
                                 "rate_per_60min":
                                     (goalsR[(gap, st, (lo, hi), d)] / T * 3600)
                                     if T >= 900 else None})
                fits["rates_R"][GK[gap]][f"{st}:{d}"] = rows
        T = pen_ev_secs[gap]
        fits["pen"][GK[gap]] = {"h_pk": pen_events[gap][0] / max(T, 1),
                                "h_pp": pen_events[gap][1] / max(T, 1)}
    aux = {"return_hazard_per_sec": ret_events / max(pulled_secs, 1),
           "h_repull": repull_events / max(between_secs, 1),
           "evidence_lag": 0, "dead": 18,
           "seasons": seasons, "league": league}
    json.dump(fits, open(DER / f"fits_{league}{sfx}.json", "w"), indent=0)
    json.dump(aux, open(DER / f"fits_{league}{sfx}_aux.json", "w"), indent=1)
    p3 = fits["rates"]["3"]
    print(f"[{league}{sfx}] seasons={seasons}")
    print(f"  gap3 EV_full: for {p3['EV_full:for']['rate_per_60min']:.2f}/60 "
          f"against {p3['EV_full:against']['rate_per_60min']:.2f}/60 (T={p3['EV_full:for']['T']:.0f}s)")
    print(f"  gap3 EN_ev:  for {p3['EN_ev:for']['rate_per_60min']:.1f}/60 "
          f"against {p3['EN_ev:against']['rate_per_60min']:.1f}/60 (T={p3['EN_ev:for']['T']:.0f}s)")
    print(f"  m_PP gap3 = {fits['m_PP']['3']['m']:.2f}; pen h_pk/h_pp = "
          f"{fits['pen']['3']['h_pk']*3600:.2f}/{fits['pen']['3']['h_pp']*3600:.2f} per 60")
    print(f"  return {aux['return_hazard_per_sec']:.5f}/s, repull {aux['h_repull']:.4f}/s")


if __name__ == "__main__":
    lg = sys.argv[1]
    ov = None
    if "--seasons" in sys.argv:
        ov = sys.argv[sys.argv.index("--seasons") + 1:]
    main(lg, train="--train" in sys.argv, seasons_override=ov)
