"""
clean_window_interval.py — AHL + Liiga clean-window coach ledgers.

Ports the NHL clean-window concept to the interval leagues, self-consistently
per league (rule: league fits from league data; NHL supplies SHAPES only):

  pullable second u (P3 seconds, window [opened, min(closed,1200))):
    - trailing net FULL at u (outside every empty segment, dp artifacts incl.)
    - before the first EV pull / first pp-pull segment of the instance
    - 5v5: no penalty-box window (either side) covers u
    - not within 18s after any goal (dead time — re-measured per league
      2026-08-01: obs ~1.0% vs uniform ~2.8% at 18s, same shape as NHL)

  league hazard h(R): EV pulls at their evidence second over at-risk pullable
  seconds, 60s buckets. AHL pools all 4 seasons (era check 2026-08-01:
  26-35% comparable-window rates, no trend). Liiga uses 2024-26 (2023 has no
  goalie channel).

  chance quality frac = hazard mass over the instance's pullable seconds
  divided by mass over the full [opened, 1200) window (ideal opportunity).
  clear chance if frac >= 0.7. Ledger: taken = EV pull (pp pulls EXCLUDED
  from the bettable number, same ruling as NHL); a no-pull counts against
  the coach only on a clear chance.

  coach expected pull %% = Beta posterior, prior fitted MoM on the league's
  own coach spread; recency decay 0.5^(age/10 chances) on the coach's own
  chance sequence. Band = posterior mean +/- 1.28*sd (normal approx, labeled).

Outputs: data/derived/{league}_clean_window.json, {league}_coach_profiles.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DER = ROOT / "data" / "derived"
DEAD = 18
CLEAR = 0.7
BUCKET = 60
HALF_LIFE = None  # recency is calendar-based in prior_fit (ruling 32)


def build(league, rows_file, skip_seasons=()):
    rows = [r for r in json.load(open(DER / rows_file))
            if r["season"] not in skip_seasons and not r.get("no_goalie_channel")]
    rows.sort(key=lambda r: (r["date"], r["game_id"], r["n"]))

    # per-instance pullable mask + event second ---------------------------------
    def analyze(r):
        o, c = r["opened_secs"], min(r["closed_secs"], 1200)
        segs = r["pull_segments"]
        ev_segs = [s for s in segs if not s.get("dp_artifact")]
        first_seg = min((s["empty_from"] for s in segs), default=None)
        ev_pull = (r["pulled"] and r["pull_classification"] == "pull"
                   and not r.get("synthetic_pull_evidence"))
        pp_pull = r["pulled"] and r["pull_classification"] == "pp_pull"
        stop = c
        if ev_segs and r["pulled"]:
            stop = min(stop, ev_segs[0]["empty_from"])
        elif first_seg is not None and pp_pull:
            stop = min(stop, first_seg)
        goals = [gw["secs"] for gw in r["goals_in_window"]]
        if r["creating_t"] is not None:
            goals.append(o)
        pullable = []
        for u in range(o, stop):
            if any(s["empty_from"] <= u < s["empty_until"] for s in segs):
                continue
            if any(g <= u < g + DEAD for g in goals):
                continue
            if r.get("_box") and any(b <= u < e for b, e in r["_box"]):
                continue
            pullable.append(u)
        return pullable, ev_pull, pp_pull

    # boxes were not exported per-instance; rebuild from penalties is not needed:
    # segments engine already classified pp; for 5v5 seconds we use the exported
    # penalty windows when present (older exports may lack them -> re-extract).
    need_boxes = "penalties_p3" not in rows[0]
    if need_boxes:
        from hockeycore.leagues import ahl as ahl_mod, liiga as liiga_mod, mestis as mestis_mod
        from hockeycore.leagues import shl as shl_mod
        lakes = {"ahl": Path("/home/claude/work/ahl_lake"),
                 "liiga": Path("/home/claude/work/liiga_lake"),
                 "mestis": Path("/home/claude/work/mestis_lake/mestis"),
                 "shl": Path("/home/claude/work/shl_lake/shl")}
        cache = {}
        for r in rows:
            key = (r["season"], r["game_id"])
            if key not in cache:
                if league == "ahl":
                    g = ahl_mod.parse_game(
                        lakes["ahl"] / r["season"] / f"{r['game_id']}_pxp.json",
                        season=r["season"])
                elif league == "mestis":
                    g = mestis_mod.parse_game(
                        lakes["mestis"] / r["season"] /
                        f"game_{r['season']}_{r['game_id']}_seuranta.html")
                elif league == "shl":
                    g = shl_mod.parse_game(
                        lakes["shl"] / r["season"] /
                        f"game_{r['season']}_{r['game_id']}_events.html")
                else:
                    g = liiga_mod.parse_game(
                        lakes["liiga"] / r["season"] / f"game_{r['season']}_{r['game_id']}.json")
                cache[key] = [(max(p["begin"] - 2400, 0), max(p["end"] - 2400, 0))
                              for p in g["penalties"] if p["end"] > 2400]
            r["_box"] = cache[key]

    per = [analyze(r) for r in rows]

    # league hazard -------------------------------------------------------------
    atrisk = defaultdict(int)
    events = defaultdict(int)
    for (pullable, ev_pull, _pp), r in zip(per, rows):
        for u in pullable:
            atrisk[u // BUCKET] += 1
        if ev_pull and r["pull_evidence_secs"] is not None:
            events[r["pull_evidence_secs"] // BUCKET] += 1
    hazard = {b: (events[b] / atrisk[b] if atrisk[b] else 0.0)
              for b in range(1200 // BUCKET)}

    def mass(secs):
        return sum(hazard[u // BUCKET] for u in secs)

    # ledger --------------------------------------------------------------------
    out_rows = []
    for (pullable, ev_pull, pp_pull), r in zip(per, rows):
        o = r["opened_secs"]
        ideal = mass(range(o, 1200))
        frac = (mass(pullable) / ideal) if ideal > 0 else 0.0
        taken = bool(ev_pull or (r["pulled"] and r.get("synthetic_pull_evidence")
                                 and r["pull_classification"] != "pp_pull"))
        clear = taken or frac >= CLEAR
        out_rows.append({
            "season": r["season"], "game_id": r["game_id"], "n": r["n"],
            "date": r["date"], "team": r["home"] if r["trailing"] == "home" else r["away"],
            "coach": r["coach"], "opened_R": 1200 - o,
            "closed_R": 1200 - min(r["closed_secs"], 1200),
            "frac_ev": round(frac, 3), "clear": clear, "taken": taken,
            "pp_pull": pp_pull,
            "pull_R": (1200 - r["pull_evidence_secs"])
                      if taken and r["pull_evidence_secs"] is not None else None})

    # coach table + prior -------------------------------------------------------
    coach = defaultdict(lambda: {"chances": 0, "taken": 0, "pp_pulls": 0,
                                 "instances": 0, "seq": [], "team": None,
                                 "last_seen": ""})
    for cr in out_rows:
        t = coach[cr["coach"]]
        t["instances"] += 1
        if cr["date"] >= t["last_seen"]:
            t["last_seen"], t["team"] = cr["date"], cr["team"]
        if cr["pp_pull"]:
            t["pp_pulls"] += 1
        if cr["clear"]:
            t["chances"] += 1
            t["taken"] += int(cr["taken"])
            t["seq"].append((cr["date"], int(cr["taken"])))

    from hockeycore.fit.prior_fit import fit_prior, posterior_sheet, _season_year
    a, b, mu, strength = fit_prior([t["seq"] for t in coach.values()])
    league_asof = max((cr["date"] for cr in out_rows), default=None)
    league_season = max((_season_year(cr["date"]) for cr in out_rows), default=None)

    profiles = []
    for name, t in coach.items():
        seq = t["seq"]
        from hockeycore.fit.prior_fit import posterior_detail
        m, kw, nw, a_e, b_e = posterior_detail(seq, a, b)
        post_a, post_b = kw + a_e, (nw - kw) + b_e
        sd = (m * (1 - m) / (post_a + post_b + 1)) ** 0.5
        flags = []
        if t["chances"] < 5:
            flags.append("RISKY: <5 clean chances")
        if t["chances"] >= 4 and t["taken"] == 0 and t["pp_pulls"] >= 2:
            flags.append("PP-only puller")
        sp, slo, shi, sn = posterior_sheet(seq, asof=league_asof,
                                           window_season=league_season)
        _cut = f"{league_season + 1}-01-01" if league_season is not None else ""
        _bridge = league_season is not None and (league_asof or "9999")[:10] < _cut
        win = [(d, t) for d, t in seq if league_season is not None
               and (_season_year(d) == league_season
                    or (_bridge and _season_year(d) == league_season - 1))]
        profiles.append({
            "coach": name, "team": t["team"], "last_seen": t["last_seen"],
            "sheet_pct": round(sp, 4) if sp is not None else None,
            "sheet_band": [round(slo, 3), round(shi, 3)] if sp is not None else None,
            "window_taken": sum(t for _, t in win), "window_chances": len(win),
            "clear_chances": t["chances"], "clear_taken": t["taken"],
            "pp_pulls": t["pp_pulls"], "instances": t["instances"],
            "expected_pull_pct": round(m, 4),
            "band": [round(max(m - 1.28 * sd, 0.0), 3), round(min(m + 1.28 * sd, 1.0), 3)],
            "last3": "".join("P" if x else "-" for _, x in seq[-3:]),
            "flags": flags})
    profiles.sort(key=lambda p: -p["expected_pull_pct"])

    meta = {"league": league, "prior_a": round(a, 3), "prior_b": round(b, 3),
            "prior_mu": round(mu, 4), "prior_strength": round(strength, 2),
            "hazard_bucketed": {str(k): round(v, 6) for k, v in hazard.items()},
            "half_life_chances": HALF_LIFE, "clear_threshold": CLEAR,
            "dead_time_s": DEAD}
    json.dump({"meta": meta, "rows": out_rows},
              open(DER / f"{league}_clean_window.json", "w"), indent=0)
    json.dump({"meta": meta, "profiles": profiles},
              open(DER / f"{league}_coach_profiles.json", "w"), indent=0)

    naive = sum(r["taken"] for r in out_rows) / len(out_rows)
    clear_rows = [r for r in out_rows if r["clear"]]
    clear_rate = sum(r["taken"] for r in clear_rows) / len(clear_rows)
    print(f"[{league}] instances={len(out_rows)} clear={len(clear_rows)} "
          f"raw take-rate={naive:.1%} clear-chance take-rate={clear_rate:.1%} "
          f"prior mu={mu:.2f} strength={strength:.1f} coaches={len(profiles)}")
    return profiles


if __name__ == "__main__":
    import sys as _sys
    which = _sys.argv[1] if len(_sys.argv) > 1 else "all"
    if which in ("ahl", "all"):
        build("ahl", "ahl_instances_gap3.json")
    if which in ("liiga", "all"):
        build("liiga", "liiga_instances_gap3.json", skip_seasons=("2023",))
    if which in ("mestis", "all"):
        # Mestis 2022-23 HAS the goalie channel (unlike Liiga) — all 4 seasons in
        build("mestis", "mestis_instances_gap3.json")
    if which in ("shl", "all"):
        # SHL swe Events channel complete all 4 seasons
        build("shl", "shl_instances_gap3.json")
