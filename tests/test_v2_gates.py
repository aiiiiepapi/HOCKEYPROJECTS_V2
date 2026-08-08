"""All v2 release gates in one pytest run. Any failure blocks release."""
import json, math, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DER = ROOT / "data" / "derived"


def test_ground_truth_13_of_13():
    from hockeycore.gap.extract import load_pbp, extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_nhl.json"))["games"]
    for gid, gtg in gt.items():
        _, insts = extract_instances(load_pbp(ROOT / f"tests/reference_raw/nhl/{gid}_pbp.json"), 3)
        assert len(insts) == len(gtg["instances"]), gid
        for e, a in zip(gtg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["pulled"]) == \
                   (a["opened_secs"], a["closed_secs"], a["pulled"]), (gid, e["n"])
            if e["pulled"]:
                assert e["pull_evidence_secs"] == a["pull_evidence_secs"], (gid, e["n"])


def test_recursion_vs_mc():
    # recursion has no penalty states — compare against penalties=False MC,
    # then assert the penalty mechanism moves prices the right DIRECTION
    from hockeycore.pricing.mc_pricer import price, p_next_goal_recursion
    for R in (300, 600, 900):
        off = price(R, n=100000, penalties=False)
        assert abs(p_next_goal_recursion(R) - off["P_total_ge1"]) < 0.005
        on = price(R, n=100000)
        assert on["P_total_ge1"] > off["P_total_ge1"]      # penalties add goals
        assert on["P_leader_ge1"] > off["P_leader_ge1"]    # mostly leader goals


def test_directions_fits():
    f = json.load(open(DER / "fits.json"))
    r3 = f["rates"]["3"]
    assert r3["EN_ev:against"]["rate_per_60min"] > r3["EV_full:against"]["rate_per_60min"]  # D3
    assert r3["EN_ev:for"]["rate_per_60min"] > r3["EV_full:for"]["rate_per_60min"]          # D4
    assert f["m_PP"]["3"]["m"] > 1                                                          # D6


def test_directions_pricing():
    t = json.load(open(DER / "pricing_table_production.json"))
    avg = [r for r in t if r.get("tier") == 1.0 or r.get("coach") == "league_avg_1.00"]
    ev = sorted([r for r in avg if r["state"] == "not_pulled_EV"], key=lambda r: -r["R"])
    assert all(a["P_total_ge1"] >= b["P_total_ge1"] - 0.01 for a, b in zip(ev, ev[1:]))     # D1
    for R in (600, 300, 180):                                                                # D2
        p = next(r for r in avg if r["R"] == R and r["state"] == "pulled")
        n = next(r for r in avg if r["R"] == R and r["state"] == "not_pulled_EV")
        assert p["P_total_ge1"] > n["P_total_ge1"]
    assert all(r["P_total_ge2"] < r["P_total_ge1"] for r in t)                               # D10


def test_coach_shrinkage_identity():
    c = json.load(open(DER / "coach_table_production.json"))
    assert c["attenuation"] == 0.355
    # D8: zero-evidence coach → both multipliers exactly 1
    k = c["k"]
    assert abs((0 + k) / (0 + k) - 1.0) < 1e-12


def test_backtest_calibration_thresholds():
    """Blind 25-26 calibration, per-market documented bounds (revised
    2026-07-26 after the penalty-generation + R-dependent-rates + attenuated-
    coach-layer upgrade — the lead1 hunt #3 outcome):
    - all markets must keep Brier skill vs base rate
    - lead1: conservative-only bias (Overs-safe), now +2.4pts (was +5..7)
    - remaining known imperfection: extreme-decile compression (bottom decile
      conservative = harmless; top deciles ~6pts hot on total1) -> bad<=3
    - marg4: model runs OPTIMISTIC (-4pts, top-decile hot) -> market is
      CAUTION on the bet card (double edge or skip) until coach-conditional
      hazards replace the multiplier; bias bounded here.
    """
    rows = json.load(open(DER / "backtest_rows.json"))
    n = len(rows)
    bounds = {"p_lead1": (0.0, 0.05, 3), "p_total1": (-0.03, 0.03, 3),
              "p_total2": (-0.04, 0.04, 3), "p_marg4": (-0.05, 0.02, 3)}
    for pk, yk in [("p_total1", "y_total1"), ("p_total2", "y_total2"),
                   ("p_lead1", "y_lead1"), ("p_marg4", "y_marg4")]:
        rs = sorted(rows, key=lambda r: r[pk])
        base = sum(r[yk] for r in rs) / n
        brier = sum((r[pk] - r[yk]) ** 2 for r in rs) / n
        assert brier < base * (1 - base), f"{pk}: no skill vs base rate"
        lo, hi, maxbad = bounds[pk]
        bias = sum(r[yk] - r[pk] for r in rs) / n
        assert lo - 1e-9 <= bias <= hi + 1e-9, f"{pk} bias {bias:+.3f} outside [{lo},{hi}]"
        bad = 0
        for b in range(10):
            ch = rs[b * n // 10:(b + 1) * n // 10]
            mp = sum(r[pk] for r in ch) / len(ch)
            ay = sum(r[yk] for r in ch) / len(ch)
            se = math.sqrt(max(mp * (1 - mp), 1e-9) / len(ch))
            bad += abs(mp - ay) >= 2 * se
        assert bad <= maxbad, f"{pk}: reliability {10-bad}/10 (allowed bad<={maxbad})"


def test_pulled_total2_bounded_and_withdrawn():
    """Pulled-state multi-goal corner: model overshoots (0.253 vs 0.142, n=127).
    Convergence attempt 2026-07-25 FAILED after eliminating 3 hypotheses
    (stint-age rates, late gap-4 rates, re-arm productivity — all check out;
    dead-time mechanism added, small effect). Residual unexplained.
    GATE: overshoot must not GROW, and the market stays WITHDRAWN from the
    bet card until a future block converges this (4-season data doubles n).
    """
    rows = json.load(open(DER / "backtest_rows.json"))
    pu = [r for r in rows if r["pulled"]]
    mp = sum(r["p_total2"] for r in pu) / len(pu)
    ay = sum(r["y_total2"] for r in pu) / len(pu)
    assert mp - ay <= 0.115, f"pulled-total2 overshoot grew: {mp-ay:+.3f}"
    assert (ROOT / "docs" / "WITHDRAWN_MARKETS.md").exists()


def test_roi_at_threshold_lines():
    """Seb's validation (odds ruling c): betting every blind checkpoint at the
    model's exact +10%-EV line must actually win. Gate: point ROI > 0 for the
    two lead markets and total-over, and leaderTT's game-cluster CI floor > 0.
    (roi_at_threshold.json regenerated by hockeycore/fit/roi_at_threshold.py
    whenever backtest_rows changes.)"""
    res = json.load(open(DER / "roi_at_threshold.json"))
    m = res["markets"]
    for k in ("leaderTT_over", "leader_-3.5", "gametotal_over"):
        assert m[k]["roi"] > 0, f"{k}: negative realized ROI at 10%-EV line"
    assert m["leaderTT_over"]["ci95_game_cluster"][0] > 0
    # 0.95 -> 0.94 (Seb ratified 2026-08-01, ruling 23): the density coach
    # law prices tail coaches at their true P_c; 25-26's tail regression
    # (~2sigma season wobble) costs ~1.5 ROI pts on this one season, moving
    # the bootstrap statistic 0.973 -> 0.946. Point ROI +21.3%, CI floor +7.3%.
    assert m["leaderTT_over"]["p_roi_gt_edge"] > 0.94


def test_eihl_ground_truth():
    from hockeycore.leagues.eihl import parse_game, extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_eihl.json"))
    files = gt["_meta"]["games_files"]
    for gid, gg in gt["games"].items():
        insts = extract_instances(parse_game(ROOT / f"tests/reference_raw/eihl/game_{gid}_{files[gid]}.html"), 3)
        assert len(insts) == len(gg["instances"]), gid
        for e, a in zip(gg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["pulled"]) == \
                   (a["opened_secs"], a["closed_secs"], a["pulled"]), (gid, e["n"])
            if e["pulled"]:
                assert e["pull_evidence_secs"] == a["pull_evidence_secs"]
                assert e["pull_classification"] == a["pull_classification"]


def test_liiga_ground_truth():
    from hockeycore.leagues.liiga import parse_game, extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_liiga.json"))
    for num, gg in gt["games"].items():
        insts = extract_instances(parse_game(ROOT / f"tests/reference_raw/liiga/game_2026_{num}.json"), 3)
        assert len(insts) == len(gg["instances"]), num
        for e, a in zip(gg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["pulled"]) == \
                   (a["opened_secs"], a["closed_secs"], a["pulled"]), (num, e["n"])
            if e["pulled"]:
                assert e["pull_evidence_secs"] == a["pull_evidence_secs"]
                assert e["pull_classification"] == a["pull_classification"]


def test_clean_window_consistency():
    """Clean-window coach analysis (Seb directive 2026-07-25): structural
    invariants only (rule 14) — reasons partition the no-pulls, dilution
    removal must RAISE the league rate, per-coach ledgers must be coherent."""
    rows = json.load(open(DER / "clean_window_instances.json"))
    tab = json.load(open(DER / "clean_window_coach.json"))
    nop = [r for r in rows if not r["pulled"]]
    assert all(r["reason"] for r in nop) and all(r["reason"] is None for r in rows if r["pulled"])
    naive = sum(r["pulled"] for r in rows) / len(rows)
    clear = [r for r in rows if r["pulled"] or r["frac"] >= 0.7]
    assert sum(r["pulled"] for r in clear) / len(clear) > naive * 2  # dilution was real
    for t in tab:
        assert 0 <= t["clear_taken"] <= t["clear_chances"] <= t["instances"]
        assert t["clear_taken"] == t["pulls"]  # every pull is a taken chance
        if t["clean_rate"] is not None:
            assert 0 <= t["clean_rate"] <= 1
    # era-denominator regression guard (2026-07-26 bug): a full window in the
    # OLD era must be able to score as a clear chance
    old_fracs = [r["frac_ev"] for r in rows
                 if r["season"] in ("20222023", "20232024") and not r["pulled"]]
    assert max(old_fracs) >= 0.9, "old-era frac capped — era-mismatched denominator is back"


def test_liiga_v2_api_equivalence():
    """api/v2 swapped penaltyEvents nesting between home and away (verified
    2026-08-01: exact array swap on identical games + 1603-vs-16 PP-goal
    cross-check over 1858 games). parse_game must auto-detect the version
    (root-level homeTeamPlayers marker) and yield IDENTICAL adapter output
    for the same game fetched from either API version."""
    from hockeycore.leagues.liiga import parse_game, extract_instances
    for n in (3, 4, 9, 13):
        v1 = parse_game(ROOT / f"tests/reference_raw/liiga/game_2026_{n}.json")
        v2 = parse_game(ROOT / f"tests/reference_raw/liiga_v2/game_2026_{n}.json")
        for k in ("home", "away", "empty"):
            assert v1[k] == v2[k], (n, k)
        assert [(g["t"], g["side"], g["en"]) for g in v1["goals"]] == \
               [(g["t"], g["side"], g["en"]) for g in v2["goals"]], n
        key = lambda p: (p["t"], p["side"], p["begin"], p["end"])
        assert sorted(map(key, v1["penalties"])) == sorted(map(key, v2["penalties"])), n
        assert extract_instances(v1, 3) == extract_instances(v2, 3), n


def test_ahl_ground_truth():
    """AHL batch 1: 3 games / 5 instances hand-traced from raw pxpverbose
    BEFORE the adapter existed (2026-08-01). Covers: carryover-at-open (x3),
    pp_pull via leader minor (x2, incl. same-second penalty), entering-P3 gap,
    ENG widen/narrow closes, no-pull instances."""
    from hockeycore.leagues.ahl import parse_game
    from hockeycore.gap.segments import extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_ahl.json"))
    for gid, gg in gt["games"].items():
        g = parse_game(ROOT / f"tests/reference_raw/ahl/{gid}_pxp.json")
        insts = extract_instances(g, 3)
        assert len(insts) == len(gg["instances"]), (gid, len(insts))
        for e, a in zip(gg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["closed_reason"]) == \
                   (a["opened_secs"], a["closed_secs"], a["closed_reason"]), (gid, e["n"])
            assert e["trailing_name"] == a["trailing_name"], (gid, e["n"])
            assert e["pulled"] == a["pulled"], (gid, e["n"])
            assert e["pull_evidence_secs"] == a["pull_evidence_secs"], (gid, e["n"])
            assert e["pull_classification"] == a["pull_classification"], (gid, e["n"])
            assert e.get("carryover_empty_at_open", False) == \
                   a.get("carryover_empty_at_open", False), (gid, e["n"])


def test_ahl_liiga_derived_instances():
    """Structural gates (rule 14: per-season bounds, never absolute totals)
    over the AHL + Liiga derived instance files."""
    for fname, per_season, seasons in (
            ("ahl_instances_gap3.json", (400, 800), ["77", "81", "86", "90"]),
            ("liiga_instances_gap3.json", (120, 330), ["2023", "2024", "2025", "2026"])):
        rows = json.load(open(DER / fname))
        assert all(r["coach"] for r in rows), fname
        for s in seasons:
            srows = [r for r in rows if r["season"] == s]
            n = len(srows)
            assert per_season[0] <= n <= per_season[1], (fname, s, n)
            if s == "2023":
                # Liiga 2022-23: API has no goalie-event channel -> pull truth
                # unknowable; every instance must be explicitly marked so.
                assert all(r["pulled"] is None and r.get("no_goalie_channel")
                           for r in srows), (fname, s)
                continue
            pulled = sum(1 for r in srows if r["pulled"])
            assert 0.04 <= pulled / n <= 0.40, (fname, s, pulled / n)
        for r in rows:
            assert 0 <= r["opened_secs"] <= r["closed_secs"] <= 1200, (fname, r["game_id"])
            if r.get("no_goalie_channel"):
                continue
            if r["pulled"]:
                assert r["opened_secs"] <= r["pull_evidence_secs"] < r["closed_secs"], \
                    (fname, r["game_id"], r["n"])
                assert r["pull_classification"] in ("pull", "pp_pull")
            else:
                assert r["pull_classification"] is None
        pp = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
        assert pp < sum(1 for r in rows if r["pulled"]), fname


def test_ahl_liiga_clean_window():
    """Structural gates over the interval-league ledgers + profiles (rule 14).
    Mestis added 2026-08-03, same bar."""
    for lg in ("ahl", "liiga", "mestis", "shl", "magnus", "khl"):
        cw = json.load(open(DER / f"{lg}_clean_window.json"))
        prof = json.load(open(DER / f"{lg}_coach_profiles.json"))
        rows, meta = cw["rows"], cw["meta"]
        naive = sum(r["taken"] for r in rows) / len(rows)
        clear = [r for r in rows if r["clear"]]
        assert sum(r["taken"] for r in clear) / len(clear) > naive * 2, lg  # dilution real
        assert all(r["taken"] <= r["clear"] for r in rows), lg              # taken => clear
        assert all(0 <= r["frac_ev"] <= 1.001 for r in rows), lg
        assert 1.0 <= meta["prior_strength"] <= 40.0, lg
        # Per-league mu bounds (rule 14: structural, per league — 2026-08-07).
        # SHL's clean-chance take rate is genuinely ~17%: its pull culture is
        # gap-1/2 pulls (29.8% of gap-3 instances open carryover-empty) and
        # down-3 chances are mostly declined — clean-window controlled, so
        # this IS comparable cross-league (ruling-45 unified baseline:
        # AHL 66.8 / Liiga 55.0 / Mestis 63.6 / SHL 23.0). Bound widened
        # for shl only, evidence in docs/SHL_ADAPTER_VERIFICATION.md;
        # NOT a tuning knob.
        mu_lo = 0.08 if lg == "shl" else 0.30
        assert mu_lo <= meta["prior_mu"] <= 0.70, lg
        # Profile floor also per-league (2026-08-07): in SHL's mu=0.17
        # environment a genuine hard-never-puller (Thomas Berglund, 0/16
        # clear chances over 38 instances) legitimately posts <2%.
        pct_lo = 0.002 if lg == "shl" else 0.02
        # Ceiling raised 0.98 -> 0.995 with ruling 45 (full-period baseline):
        # junk no-pulls no longer dilute perfect records, so a genuine
        # near-deterministic puller (Seth Appert AHL, 13/13 clear chances
        # over 40 instances — verified row-by-row 2026-08-07) legitimately
        # posts 0.988. NOT a tuning knob.
        for p in prof["profiles"]:
            assert pct_lo <= p["expected_pull_pct"] <= 0.995, (lg, p["coach"])
            assert p["clear_taken"] <= p["clear_chances"] <= p["instances"], (lg, p["coach"])
            assert p["band"][0] <= p["expected_pull_pct"] <= p["band"][1], (lg, p["coach"])
            if p["clear_chances"] < 5:
                assert any("RISKY" in f for f in p["flags"]), (lg, p["coach"])
        # posterior sanity: a perfect recent record must clear the prior mean
        best = max(prof["profiles"], key=lambda p: p["expected_pull_pct"])
        if best["clear_chances"] >= 5 and best["clear_taken"] == best["clear_chances"]:
            assert best["expected_pull_pct"] > meta["prior_mu"] + 0.10, lg


def test_liiga_blind_calibration():
    """Liiga walk-forward (fit 2023-2025, price 2026 blind, density coach law).
    Provisional bounds documented from the first blind run 2026-08-01
    (n=553 checkpoints, ONE season — bounds deliberately loose, conservative-
    only where the NHL character repeats): every market must keep Brier skill
    and stay Overs-safe or near-flat; reliability bad<=3."""
    rows = json.load(open(DER / "backtest_rows_liiga.json"))
    n = len(rows)
    bounds = {"p_lead1": (-0.01, 0.08), "p_total1": (-0.03, 0.06),
              "p_total2": (-0.05, 0.05), "p_marg4": (-0.02, 0.12)}
    for pk, yk in [("p_lead1", "y_lead1"), ("p_total1", "y_total1"),
                   ("p_total2", "y_total2"), ("p_marg4", "y_marg4")]:
        rs = sorted(rows, key=lambda r: r[pk])
        base = sum(r[yk] for r in rs) / n
        brier = sum((r[pk] - r[yk]) ** 2 for r in rs) / n
        assert brier < base * (1 - base), f"liiga {pk}: no skill"
        bias = sum(r[yk] - r[pk] for r in rs) / n
        lo, hi = bounds[pk]
        assert lo - 1e-9 <= bias <= hi + 1e-9, f"liiga {pk} bias {bias:+.3f}"
        bad = 0
        for b in range(10):
            ch = rs[b * n // 10:(b + 1) * n // 10]
            mp = sum(r[pk] for r in ch) / len(ch)
            ay = sum(r[yk] for r in ch) / len(ch)
            se = math.sqrt(max(mp * (1 - mp), 1e-9) / len(ch))
            bad += abs(mp - ay) >= 2 * se
        assert bad <= 3, f"liiga {pk}: {bad}/10 bad deciles"


def test_ahl_not_bettable_flagged():
    """AHL blind FAILED every configuration tested (rulings 24): the no-bet
    status must stay visibly flagged until a fitting protocol passes blind.
    This gate exists so no session quietly prices AHL without re-litigating."""
    s = open(ROOT / "docs" / "DECISIONS.md").read()
    assert "AHL: NO-GO for pricing" in s


def test_dp_artifact_rule_17b_pins():
    """Ruling 17b (2026-08-02): dp phantom-pull classes, every case
    hand-verified against the raw feed this session. Exact-value pins on the
    derived instance files — these games must stay exactly as adjudicated."""
    rows = {(r["season"], str(r["game_id"]), r["n"]): r
            for r in json.load(open(DER / "ahl_instances_gap3.json"))}
    # 17b-i: short early leader-whistle enders = dp (26-51s, P3 0:33-11:03)
    for k in [("77", "1024680", 1), ("86", "1026980", 1), ("86", "1027518", 1),
              ("86", "1027594", 1), ("90", "1027844", 1)]:
        assert rows[k]["pulled"] is False, k
    # 17b-ii: dp GOAL (wiped minor, no penalty event) is not pull evidence
    assert rows[("81", "1025867", 1)]["pulled"] is False
    # 17b-iii: whistle-lag (leader penalty assessed inside the segment)
    assert rows[("90", "1028800", 1)]["pulled"] is False
    # evidence moves to the real (late) segment when one exists
    assert rows[("90", "1028774", 1)]["pulled"] is True
    assert rows[("90", "1028774", 1)]["pull_evidence_secs"] == 945
    # late-game long leader-whistle enders remain real pulls (ruling 17)
    for k, ev in [(("90", "1028817", 1), 995), (("90", "1028895", 2), 966),
                  (("90", "1028548", 1), 1101)]:
        assert rows[k]["pulled"] is True and rows[k]["pull_evidence_secs"] == ev, k
    # verified real early pulls (long/corroborated) must NEVER be flagged
    for k, ev in [(("81", "1025222", 1), 598), (("90", "1028306", 1), 705)]:
        assert rows[k]["pulled"] is True and rows[k]["pull_evidence_secs"] == ev, k
    # same-second goalie SWAPS (IN-row-then-OUT-row feed order) are not pulls
    # (2026-08-02 adapter fix; each hand-verified against named goalie rows):
    assert rows[("90", "1028763", 2)]["pulled"] is False      # Milic->DiVincentiis
    assert rows[("90", "1027839", 1)]["pulled"] is False      # Tolopilo->Patera; real pull at 1000 is outside the closed window
    assert rows[("77", "1024882", 1)]["pull_evidence_secs"] == 957  # swap at 520 was phantom; real pull 957
    lrows = {(r["season"], str(r["game_id"]), r["n"]): r
             for r in json.load(open(DER / "liiga_instances_gap3.json"))}
    assert lrows[("2025", "246", 1)]["pulled"] is False        # dp goal (17b-ii)
    assert lrows[("2026", "247", 1)]["pulled"] is True         # real late pull


def test_misconduct_windows_never_shorthand():
    """2026-08-02 fix: 10-min misconducts don't change on-ice strength.
    Pins the 9 classification flips (both directions) + adapter flagging."""
    rows = {(r["season"], str(r["game_id"]), r["n"]): r
            for r in json.load(open(DER / "ahl_instances_gap3.json"))}
    for k, cls in [(("81", "1026058", 1), "pp_pull"),   # trailing misconduct masked leader minor
                   (("77", "1024340", 1), "pp_pull"), (("81", "1025506", 1), "pp_pull"),
                   (("81", "1025878", 2), "pp_pull"), (("86", "1027415", 1), "pp_pull"),
                   (("86", "1027426", 1), "pp_pull"),
                   (("77", "1024678", 1), "pull"),      # leader misconduct faked a PP
                   (("90", "1028615", 1), "pull")]:
        assert rows[k]["pull_classification"] == cls, (k, rows[k]["pull_classification"])
    lrows = {(r["season"], str(r["game_id"]), r["n"]): r
             for r in json.load(open(DER / "liiga_instances_gap3.json"))}
    assert lrows[("2026", "466", 1)]["pull_classification"] == "pull"
    # adapters must flag misconduct rows (kept as whistle markers)
    from hockeycore.leagues.ahl import parse_game
    lake = Path("/home/claude/work/ahl_lake")
    if lake.exists():
        g = parse_game(str(lake / "81" / "1026058_pxp.json"),
                       str(lake / "81" / "1026058_summary.json"))
        assert any(p.get("misconduct") for p in g["penalties"])
        assert all((p["end"] - p["begin"]) < 600 or p["misconduct"]
                   for p in g["penalties"])


def test_nhl_blip_rule_and_order_independence():
    """2026-08-02: single-second net-empty blips at a whistle are flagged
    explicitly (blip_artifact) and extraction is invariant to same-second
    feed ordering (was previously only accidental, shadow_diff_gap3.md)."""
    import copy
    from itertools import groupby
    from hockeycore.gap.extract import load_pbp, extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_nhl.json"))["games"]
    for gid in gt:
        pbp = load_pbp(ROOT / f"tests/reference_raw/nhl/{gid}_pbp.json")
        _, base = extract_instances(pbp, 3)
        pert = copy.deepcopy(pbp)
        out = []
        for _, grp in groupby(pert["plays"],
                              key=lambda p: (p.get("periodDescriptor", {}).get("number"),
                                             p.get("timeInPeriod"))):
            out.extend(reversed(list(grp)))
        pert["plays"] = out
        _, flip = extract_instances(pert, 3)
        for b, f in zip(base, flip):
            assert (b["pulled"], b["pull_evidence_secs"], b["pull_classification"]) == \
                   (f["pulled"], f["pull_evidence_secs"], f["pull_classification"]), gid
    # the logged blip game itself, if the lake is mounted (regression anchor)
    lake_game = Path("/home/claude/work/nhl_lake/20242025/2024020670_pbp.json")
    if lake_game.exists():
        _, insts = extract_instances(load_pbp(lake_game), 3)
        assert insts[0]["pull_evidence_secs"] == 930


def test_random_audit_vs_raw_lakes():
    """Seeded random audits (30 pulls + 30 no-pulls per league) re-verified
    directly against the raw lake goalie channels, bypassing the adapter
    state machine. Runs only when the lakes are mounted (RUNBOOK clones);
    0 disagreements is the standing bar (AHL 2026-08-01, Liiga 2026-08-02)."""
    lakes = Path("/home/claude/work")
    if not (lakes / "ahl_lake").exists() or not (lakes / "liiga_lake").exists():
        import pytest
        pytest.skip("lakes not mounted")
    sys.path.insert(0, str(ROOT / "tools"))
    from audit_interval_random import audit
    for lg in ("ahl", "liiga"):
        sample, bad = audit(lg)
        assert len(sample) == 60, lg
        assert not bad, (lg, bad)


def test_magnus_ground_truth():
    """Magnus batch-0 GT (9 sheets, 5 seasons, hand-traced 2026-08-02; two
    hand-trace errors corrected BY the engine cross-check — see
    ground_truth_traces/magnus_batch0.md). Pins window detection, TOI-fit
    net-empty inference (EN anchors are hard constraints), sheet_empty, OT
    duration, scheduled swaps. Pull-positive in-window logic still requires
    batch 1 from the full lake before Magnus ledgers ship."""
    from hockeycore.leagues.magnus import parse_game
    from hockeycore.gap.segments import extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_magnus.json"))["games"]
    for gid, g in gt.items():
        r = parse_game(str(ROOT / f"tests/reference_raw/magnus/{gid}.pdf"))
        if g.get("sheet_empty"):
            assert r is None, gid
            continue
        insts = extract_instances(r)
        assert len(insts) == len(g["instances"]), gid
        for e, a in zip(g["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["pulled"]) == \
                   (a["opened_secs"], a["closed_secs"], a["pulled"]), (gid, e["n"])
    # Case-1 arithmetic pin (16351): GRE off 126s ends at the J- confirmed
    # EN goal -> [3249, 3375], never the arithmetically-consistent horn fit
    r = parse_game(str(ROOT / "tests/reference_raw/magnus/16351.pdf"))
    assert r["empty"]["away"] == [(3249, 3375)]
    assert r["coach_home"] == "LHENRY Fabrice" and r["coach_away"] == "AHO Jyrki"


def test_mestis_ground_truth():
    """Mestis batch 1: 13 games / 13 instances hand-traced from raw seuranta
    HTML BEFORE the adapter existed (2026-08-03, Manager session). Covers:
    EV pull, pp_pull (leader minor at first evidence, 7441), classification
    at FIRST evidence despite later leader minor (7327), no-pull,
    carryover-at-open x4, widened/narrowed/end_of_game closes, mid-game +
    P3 goalie swaps (vaihto: net never empty), multi-pull, pull-to-horn,
    IM/TM/SR/RL/YV2 flags, real double minors, 5+20 major/misconduct pairs,
    OT + shootout (VL rows excluded), penalty-shot fouls without minutes.
    Trace: docs/ground_truth_traces/mestis_batch1_2026-08-03.md."""
    from hockeycore.leagues.mestis import parse_game
    from hockeycore.gap.segments import extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_mestis.json"))
    for gid, gg in gt["games"].items():
        g = parse_game(ROOT / f"tests/reference_raw/mestis/game_{gid}_seuranta.html")
        assert (g["home"], g["away"], g["date"]) == (gg["home"], gg["away"], gg["date"]), gid
        for sd in ("home", "away"):
            got = [(b, e) for b, e, *_ in g["empty"][sd]]
            assert got == [tuple(x) for x in gg["empty"].get(sd, [])], (gid, sd, got)
        insts = extract_instances(g, 3)
        assert len(insts) == len(gg["instances"]), (gid, len(insts))
        for e, a in zip(gg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["closed_reason"]) == \
                   (a["opened_secs"], a["closed_secs"], a["closed_reason"]), (gid, e["n"])
            assert e["trailing_name"] == a["trailing_name"], (gid, e["n"])
            assert e["pulled"] == a["pulled"], (gid, e["n"])
            assert e["pull_evidence_secs"] == a["pull_evidence_secs"], (gid, e["n"])
            assert e["pull_classification"] == a["pull_classification"], (gid, e["n"])
            assert e["carryover_empty_at_open"] == \
                   a.get("carryover_empty_at_open", False), (gid, e["n"])
    # IM (own-net-empty) goal must NOT read as an ENG (7458 58:04);
    # TM,SR flags carried verbatim (7288 58:37)
    g = parse_game(ROOT / "tests/reference_raw/mestis/game_2023_7458_seuranta.html")
    im = [gl for gl in g["goals"] if gl["t"] == 3484][0]
    assert im["en"] is False and "IM" in im["types"]
    g = parse_game(ROOT / "tests/reference_raw/mestis/game_2023_7288_seuranta.html")
    sr = [gl for gl in g["goals"] if gl["t"] == 3517][0]
    assert sr["en"] is True and "SR" in sr["types"]


def test_mestis_derived_instances():
    """Structural gates (rule 14) over the Mestis derived instance file +
    full coach attribution (game rosters + verified mestis_coaches.csv)."""
    rows = json.load(open(DER / "mestis_instances_gap3.json"))
    assert all(r["coach"] for r in rows)
    for s in ("2023", "2024", "2025", "2026"):
        srows = [r for r in rows if r["season"] == s]
        n = len(srows)
        assert 80 <= n <= 320, (s, n)
        pulled = sum(1 for r in srows if r["pulled"])
        assert 0.04 <= pulled / n <= 0.40, (s, pulled / n)
    for r in rows:
        assert 0 <= r["opened_secs"] <= r["closed_secs"] <= 1200, r["game_id"]
        if r["pulled"]:
            assert r["opened_secs"] <= r["pull_evidence_secs"] < r["closed_secs"], \
                (r["game_id"], r["n"])
            assert r["pull_classification"] in ("pull", "pp_pull")
        else:
            assert r["pull_classification"] is None
    pp = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    assert pp < sum(1 for r in rows if r["pulled"])


def test_mestis_random_audit():
    """Seeded random audit (30 pulls + 30 no-pulls, seed 20260803) against
    the POIS stat-line channel — fully independent of the event rows the
    adapter parses. 0 disagreements is the standing bar (2026-08-03)."""
    lakes = Path("/home/claude/work")
    if not (lakes / "mestis_lake").exists():
        import pytest
        pytest.skip("mestis lake not mounted")
    sys.path.insert(0, str(ROOT / "tools"))
    from audit_interval_random import audit
    sample, bad = audit("mestis")
    assert len(sample) == 60
    assert not bad, bad


def test_mestis_provisional_status():
    """Ruling 43 (Seb, 2026-08-03): Mestis = Liiga-class PROVISIONAL on
    pooled multi-fold evidence; ruling 42 (attribution gate) founded on the
    same episode. Pins: rulings recorded; the pooled forward evidence that
    justified the upgrade (leaderTT CI floor > 0 across 968 checkpoints);
    fold variance record present (all misses noise-compatible); lines CSV
    exists with all three markets."""
    d = open(ROOT / "docs" / "DECISIONS.md").read()
    assert "ATTRIBUTION GATE" in d and "MESTIS UPGRADED to Liiga-class PROVISIONAL" in d
    fv = json.load(open(DER / "mestis_fold_variance.json"))
    assert all(abs(f["z"]) < 2.5 for f in fv["forward"]["lead1"]["folds"])
    folds = json.load(open(DER / "mestis_folds.json"))
    fw = [f["markets"]["p_lead1"]["bias"] for f in folds if f["design"] == "forward"]
    assert len(fw) >= 3            # multi-fold record intact (ruling 42)
    assert (DER / "lines_10ev_mestis.csv").exists()
    import csv as _csv
    with open(DER / "lines_10ev_mestis.csv", newline="") as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) > 1000
    ks = set(rows[0].keys())
    assert {"P_leader_ge1", "P_total_ge1", "P_margin_ge4"} & ks or            any("leader" in k.lower() or "line" in k.lower() for k in ks)


def test_shl_ground_truth():
    """SHL batch 1: 12 games / 12 instances hand-traced from raw Events HTML
    BEFORE the adapter existed (2026-08-06, SHL adapter session). Covers:
    EV pull, pp_pull x2 (leader minor at first evidence 629037; same-second
    leader penalty 6v4 pull 1004370), no-pull, carryover-at-open x6,
    multi-pull (774474), pull-to-horn x2, widened(ate_ENG)/narrowed(incl.
    scored_6v5)/end_of_game closes, OT game (774733, OT-end GK bookkeeping),
    shootout (628968: GWS goal + attempt rows excluded, header off-by-one),
    P1/P2/P3 same-second goalie substitutions (net never empty), ENG-creates-
    instance, PS goal + no-minutes PenaltyShot row (628999), offsetting
    penalties with (00:00 - ) placeholder windows = no box time (628979,
    774444), 5+20 pairs, 60:00 end-of-game GK Out bookkeeping, the
    adjudication game 774444 (SHL_LAKE_VERIFICATION.md).
    Trace: docs/ground_truth_traces/shl_batch1_2026-08-06.md."""
    from hockeycore.leagues.shl import parse_game
    from hockeycore.gap.segments import extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_shl.json"))
    for gid, gg in gt["games"].items():
        g = parse_game(ROOT / f"tests/reference_raw/shl/game_{gid}_events.html")
        assert (g["home"], g["away"], g["date"]) == (gg["home"], gg["away"], gg["date"]), gid
        for sd in ("home", "away"):
            got = [(b, e) for b, e, *_ in g["empty"][sd]]
            assert got == [tuple(x) for x in gg["empty"].get(sd, [])], (gid, sd, got)
        insts = extract_instances(g, 3)
        assert len(insts) == len(gg["instances"]), (gid, len(insts))
        for e, a in zip(gg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["closed_reason"]) == \
                   (a["opened_secs"], a["closed_secs"], a["closed_reason"]), (gid, e["n"])
            assert e["trailing_name"] == a["trailing_name"], (gid, e["n"])
            assert e["pulled"] == a["pulled"], (gid, e["n"])
            assert e["pull_evidence_secs"] == a["pull_evidence_secs"], (gid, e["n"])
            assert e["pull_classification"] == a["pull_classification"], (gid, e["n"])
            assert e["carryover_empty_at_open"] == \
                   a.get("carryover_empty_at_open", False), (gid, e["n"])
        if "coaches" in gg:                       # LineUps parser pin (1004308)
            assert g["coaches"] == gg["coaches"], gid
        if "regulation_goals" in gg:              # shootout exclusion pin (628968)
            assert len([x for x in g["goals"] if x["period"] <= 3]) == gg["regulation_goals"], gid
        for key, want_en in (("eng_goal", True), ("sh_eng_goal", True), ("ps_goal", False)):
            if key in gg:
                gl = [x for x in g["goals"] if x["t"] == gg[key]["t"]][0]
                assert (gl["side"], gl["en"]) == (gg[key]["side"], want_en), (gid, key)
        if "ot_goal" in gg:                       # OT goal present, engine-ignored (774733)
            gl = [x for x in g["goals"] if x["t"] == gg["ot_goal"]["t"]][0]
            assert (gl["side"], gl["period"], gl["en"]) == \
                   (gg["ot_goal"]["side"], gg["ot_goal"]["period"], gg["ot_goal"]["en"]), gid
        if "offsetting_rows_no_box" in gg:        # (00:00 - ) placeholder rule (628979)
            rows = [p for p in g["penalties"] if p["t"] == gg["offsetting_rows_no_box"]["t"]]
            assert len(rows) == gg["offsetting_rows_no_box"]["count"], gid
            assert all(p["begin"] == p["end"] == p["t"] for p in rows), gid


def test_shl_derived_instances():
    """Structural gates (rule 14) over the SHL derived instance file + full
    coach attribution (LineUps + verified shl_coaches.csv covering the 21
    blank sides). Pulled-share band reflects the measured SHL behavior:
    down-3 pulls are rare (40/681 = 5.9% pooled; 2.3-8.2% by season) while
    30% of instances carry gap-2 pull evidence in from before the window
    (carryover) — bands set structurally, not as absolute totals."""
    rows = json.load(open(DER / "shl_instances_gap3.json"))
    assert all(r["coach"] for r in rows)
    assert all(r["leader_coach"] for r in rows)
    for s in ("2023", "2024", "2025", "2026"):
        srows = [r for r in rows if r["season"] == s]
        n = len(srows)
        assert 100 <= n <= 320, (s, n)
        pulled = sum(1 for r in srows if r["pulled"])
        assert 0.005 <= pulled / n <= 0.30, (s, pulled / n)
    for r in rows:
        assert 0 <= r["opened_secs"] <= r["closed_secs"] <= 1200, r["game_id"]
        if r["pulled"]:
            assert r["opened_secs"] <= r["pull_evidence_secs"] < r["closed_secs"], \
                (r["game_id"], r["n"])
            assert r["pull_classification"] in ("pull", "pp_pull")
        else:
            assert r["pull_classification"] is None
    pp = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    assert pp < sum(1 for r in rows if r["pulled"])
    carry = sum(1 for r in rows if r.get("carryover_empty_at_open"))
    assert 0.10 <= carry / len(rows) <= 0.50        # the SHL gap-2-pull signature


def test_shl_random_audit():
    """Seeded random audit (all 27 pulls in 2024-2026 + 33 no-pulls, seed
    20260807) against the shl.se gameday pbp goalkeeper channel — an
    independent recorder from the swe Events channel the adapter parses.
    2023 excluded (pbp archive starts 2023-24; no second channel — liiga
    2023 precedent). 0 disagreements is the standing bar (2026-08-06)."""
    lakes = Path("/home/claude/work")
    if not (lakes / "shl_lake").exists():
        import pytest
        pytest.skip("shl lake not mounted")
    sys.path.insert(0, str(ROOT / "tools"))
    from audit_interval_random import audit
    sample, bad = audit("shl")
    assert len(sample) == 60
    assert not bad, bad


def test_magnus_ground_truth_batch1():
    """Magnus batch 1 (10 sheets from the verified 2025-26 lake, hand-traced
    from raw coordinate dumps 2026-08-08 during the Manager's lake
    verification). Pins the fix round mandated by that verification:
    GK TOI sanity gate (repair fires ONLY above 3900 - 68882 repaired,
    69059 relief-interleave left alone), stretched GK layout variant
    (68861/68987), bench-penalty 'E' (68850), clock-noise floor +
    sub-threshold rule, multi-pull ambiguity honesty (68841/68987 =
    synthetic, never a fabricated single interval), EN-anchor fits
    (68842/68861), OT/shootout no-phantom (69034/68862), and the
    missed-pull recovery 68988. See
    docs/ground_truth_traces/magnus_batch1_2026-08-08.md."""
    from hockeycore.leagues.magnus import parse_game
    gt = json.load(open(ROOT / "tests" / "ground_truth_magnus_batch1.json"))
    for gid, gg in gt["games"].items():
        g = parse_game(str(ROOT / f"tests/reference_raw/magnus/{gid}.pdf"))
        assert (g["home"], g["away"]) == (gg["home"], gg["away"]), gid
        for sd in ("home", "away"):
            got = [tuple(x) for x in g["empty"][sd]]
            assert got == [tuple(x) for x in gg["empty"][sd]], (gid, sd, got)
        for f in gg.get("flags_require", []):
            assert f in g["flags"], (gid, f, g["flags"])
        for f in gg.get("flags_forbid", []):
            assert f not in g["flags"], (gid, f)
        if "coach_home" in gg:
            assert g["coach_home"] == gg["coach_home"], gid
        if "pen_pin" in gg:
            pp = gg["pen_pin"]
            assert any(p["side"] == pp["side"] and p["begin"] == pp["begin"]
                       and p["end"] == pp["end"] for p in g["penalties"]), gid


def test_magnus_derived_instances():
    """Rule-14 structural gate over the Magnus 2025-26 extraction
    (2026-08-08): 314 sheets -> 147 gap-3 instances (0.47/game, Liiga-
    density ~0.45), 17 pulled (14 EV), 100% trailing-coach attribution
    from the sheets themselves, P3 windows within bounds. Magnus is
    COACH INTEL ONLY - NO-GO for real money until a 26-27 blind pass
    or Seb override (no pricer may exist for it; this gate pins that)."""
    rows = json.load(open(DER / "magnus_instances_gap3.json"))
    assert 120 <= len(rows) <= 175, len(rows)
    assert all(r["coach"] for r in rows)
    assert all(0 <= r["opened_secs"] < r["closed_secs"] <= 1200 for r in rows)
    pulled = [r for r in rows if r["pulled"]]
    assert 10 <= len(pulled) <= 30, len(pulled)
    for r in pulled:
        if r.get("pull_evidence_secs") is not None:
            assert r["opened_secs"] <= r["pull_evidence_secs"] <= 1200, r["game_id"]
    # NO-GO pin: a Magnus pricing artifact must not exist
    assert not (DER / "lines_10ev_magnus.csv").exists(), \
        "Magnus lines exist but Magnus is NO-GO (needs Seb override ruling)"

def test_khl_ground_truth():
    """KHL batch 1: 14 games / 16 instances hand-traced from raw text+protocol
    HTML BEFORE the adapter existed (2026-08-07, KHL adapter session; one
    898094 instance initially missed by hand was caught by the engine
    cross-check, re-verified and recorded — Magnus batch-0 precedent).
    Covers: EV pull x3 (incl. a 3s token pull at the horn 889859), pp_pull x6
    (6v3 pull-to-horn 881356, 6v4 re-pull after an ENG-created instance
    886054, penalty_on_trailer ender 889939), no-pull, carryover-at-open x2,
    multi-pull (3 windows 881725), ruling-17 dp artifacts x3 (886161+889859
    bracketed by EXPLICIT dp events — portfolio first; 889995 invisible),
    OT game (881270) + shootout game (889995: RB/bullit rows excluded with
    the score increment consumed), goalie substitutions incl. period-boundary
    swaps (never intervals), EN via 'V pustye vorota' + protocol
    jersey-absence x4 (incl. SH-ENG), own-net-empty goals en=False x3,
    898094 duplicate penalty re-ruled a REAL 2+2 double minor (VPM-exact),
    PS-award rows excluded, coincident cancellation, same-player stacking,
    wall-clock/cumulative collision (881356). Every GT empty-interval list
    reconciles to the second with the protocol team VPPV table (14/14).
    Trace: docs/ground_truth_traces/khl_batch1_2026-08-07.md."""
    from hockeycore.leagues.khl import parse_game
    from hockeycore.gap.segments import extract_instances
    gt = json.load(open(ROOT / "tests" / "ground_truth_khl.json"))
    for gid, gg in gt["games"].items():
        g = parse_game(ROOT / f"tests/reference_raw/khl/game_{gid}_text.html")
        assert (g["home"], g["away"], g["date"]) == (gg["home"], gg["away"], gg["date"]), gid
        assert g["coaches"] == gg["coaches"], gid
        for sd in ("home", "away"):
            got = [(b, e) for b, e, *_ in g["empty"][sd]]
            assert got == [tuple(x) for x in gg["empty"].get(sd, [])], (gid, sd, got)
        insts = extract_instances(g, 3)
        assert len(insts) == len(gg["instances"]), (gid, len(insts))
        for e, a in zip(gg["instances"], insts):
            assert (e["opened_secs"], e["closed_secs"], e["closed_reason"]) == \
                   (a["opened_secs"], a["closed_secs"], a["closed_reason"]), (gid, e["n"])
            assert e["trailing_name"] == a["trailing_name"], (gid, e["n"])
            assert e["pulled"] == a["pulled"], (gid, e["n"])
            assert e["pull_evidence_secs"] == a["pull_evidence_secs"], (gid, e["n"])
            assert e["pull_classification"] == a["pull_classification"], (gid, e["n"])
            assert e.get("carryover_empty_at_open", False) == \
                   a.get("carryover_empty_at_open", False), (gid, e["n"])
            assert e.get("dp_only_empty", False) == a.get("dp_only_empty", False), (gid, e["n"])
        if "regulation_goals" in gg:
            assert len([x for x in g["goals"] if x["period"] <= 3]) == gg["regulation_goals"], gid
        for key, want_en in (("eng_goal", True), ("sh_eng_goal", True),
                             ("extra_attacker_goal", False)):
            if key in gg:
                gl = [x for x in g["goals"] if x["t"] == gg[key]["t"]][0]
                assert (gl["side"], gl["en"]) == (gg[key]["side"], want_en), (gid, key)
        if "ot_goal" in gg:
            gl = [x for x in g["goals"] if x["t"] == gg["ot_goal"]["t"]][0]
            assert (gl["side"], gl["period"], gl["en"]) == \
                   (gg["ot_goal"]["side"], gg["ot_goal"]["period"], gg["ot_goal"]["en"]), gid
        if "dp_events" in gg:
            assert len(g["dp_events"]) == gg["dp_events"], gid
        if "double_minor_pin" in gg:            # real 2+2, never deduped (898094 adjudication)
            p = gg["double_minor_pin"]
            rows = [(x["begin"], x["end"]) for x in g["penalties"]
                    if x["side"] == p["side"] and x["t"] == p["t"]]
            assert sorted(rows) == sorted(tuple(w) for w in p["windows"]), (gid, rows)
        if "ps_zero_min" in gg:                 # PS award: protocol mins 0, no box row
            assert not [x for x in g["penalties"] if x["t"] == gg["ps_zero_min"]["t"]], gid
        if "cancelled_pairs_at" in gg:          # coincident cancellation -> whistle markers
            rows = [x for x in g["penalties"] if x["t"] == gg["cancelled_pairs_at"]]
            assert rows and all(x["begin"] == x["end"] == x["t"] for x in rows), gid
        if "misconduct_pin" in gg:              # >=10min never shorthands (2026-08-02 fix)
            assert [x for x in g["penalties"]
                    if x["t"] == gg["misconduct_pin"]["t"] and x["misconduct"]], gid


def test_khl_derived_instances():
    """Structural gates (rule 14) over the KHL derived instance file + 100%
    coach attribution (preview-frame channel, NO map — census is 100.0% per
    docs/KHL_LAKE_VERIFICATION.md, so any blank is a parser bug). Bands from
    the measured seasons (268-327 instances, pulled 7.9-14.7%, carryover
    20-23%, dp_only_empty 5-16/season) set structurally per season."""
    rows = json.load(open(DER / "khl_instances_gap3.json"))
    assert all(r["coach"] for r in rows)
    assert all(r["leader_coach"] for r in rows)
    for s in ("2023", "2024", "2025", "2026"):
        srows = [r for r in rows if r["season"] == s]
        n = len(srows)
        assert 180 <= n <= 450, (s, n)
        pulled = sum(1 for r in srows if r["pulled"])
        assert 0.03 <= pulled / n <= 0.30, (s, pulled / n)
    for r in rows:
        assert 0 <= r["opened_secs"] <= r["closed_secs"] <= 1200, r["game_id"]
        if r["pulled"]:
            assert r["opened_secs"] <= r["pull_evidence_secs"] < r["closed_secs"], \
                (r["game_id"], r["n"])
            assert r["pull_classification"] in ("pull", "pp_pull")
        else:
            assert r["pull_classification"] is None
    pp = sum(1 for r in rows if r["pull_classification"] == "pp_pull")
    assert pp < sum(1 for r in rows if r["pulled"])
    carry = sum(1 for r in rows if r.get("carryover_empty_at_open"))
    assert 0.08 <= carry / len(rows) <= 0.45
    dponly = sum(1 for r in rows if r.get("dp_only_empty"))
    assert 0.01 <= dponly / len(rows) <= 0.10   # the KHL dp-visibility signature


def test_khl_random_audit():
    """Seeded random audit (30 pulls + 30 no-pulls, seed 20260808) with TWO
    independent checks per sampled instance: (a) net-empty intervals
    re-derived from the raw text pull/return phrases outside the adapter
    state machine vs the derived instance (family standard), and (b) the
    re-derived intervals must reconcile per period TO THE SECOND with the
    protocol page's team VPPV column — the game officials' TOI accounting,
    a fully independent recorder. 0 disagreements is the standing bar
    (first run 2026-08-07)."""
    lake = Path(os.environ.get("KHL_LAKE", "/home/user/work/khl_lake/khl"))
    if not lake.exists():
        import pytest
        pytest.skip("khl lake not mounted")
    sys.path.insert(0, str(ROOT / "tools"))
    from audit_interval_random import audit
    sample, bad = audit("khl")
    assert len(sample) == 60
    assert not bad, bad


def test_del_probe_detector_never_false_no_go():
    """Gate for tools/del_round1_probe.py, the DEL Round-1 capability triage.

    The probe answers one question — does a source show WHEN a goalie was
    pulled — and a (d) verdict means NO-GO: the Manager does not spend a
    session on that adapter. So a FALSE (d) is the expensive failure, and
    the detector is calibrated against the seven lakes whose capability
    class we already know from raw bytes.

    Both false NO-GOs below were real defects caught by this gate while the
    probe was being written: literal token strings missed the AHL feed's
    `goalie_change` key, and an arbitrary GOALS co-requirement sank the NHL.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from del_round1_probe import scan_tokens, verdict
    ref = ROOT / "tests" / "reference_raw"
    explicit = {"ahl", "liiga", "eihl"}      # explicit goalie events in the feed
    onice = {"nhl", "khl", "shl", "mestis"}  # on-ice / lineup lists per goal
    seen = 0
    for league in explicit | onice:
        files = sorted(p for p in (ref / league).glob("*") if p.is_file())
        if not files:
            continue
        seen += 1
        v = verdict({str(p): scan_tokens(str(p)) for p in files})
        assert not v.startswith("(d)"), f"FALSE NO-GO on {league}: {v}"
        assert not v.startswith("INCONCLUSIVE"), f"blind on {league}: {v}"
        if league in explicit:
            assert v.startswith("(a)"), f"{league} is explicit-event class: {v}"
        else:
            assert v.startswith(("(a)", "(b)")), f"{league}: {v}"
    assert seen >= 6, f"only {seen} reference lakes found"


def test_del_fixture_parser_is_scoped():
    """Gate for tools/fetch_del_raw.py fixture discovery (the ticker lesson).

    Mestis was inflated twice by page-wide grepping that swept up numbers
    belonging to other games. DEL fixture discovery must therefore match the
    confirmed STRUCTURAL game-detail URL shape only
    (/statistik/spieldetails/{DDMMYYYY}_{home}_gg_{away}_{gameid}, ruling 51)
    and must ignore loose ids, attendance figures and neighbouring link types.

    This is a parser-scoping unit test on constructed markup, not a claim
    about DEL data -- no counts derived here are reportable (rule 4).
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from fetch_del_raw import parse_fixtures
    html = (
        b'<a href="/statistik/spieldetails/12092025_erc-ingolstadt_gg_iserlohn-roosters_3947">a</a>'
        b'<a href="/statistik/spieldetails/13092025_adler-mannheim_gg_erc-ingolstadt_3964">b</a>'
        b'<a href="/statistik/spieldetails/13092025_adler-mannheim_gg_erc-ingolstadt_3964">dup</a>'
        b'<span>3947</span><div data-id="99999">Zuschauer 4711</div>'
        b'<a href="/statistik/spielerdetails/12092025_someone_9999">decoy</a>'
    )
    fx = parse_fixtures(html)
    assert sorted(fx) == ["3947", "3964"], fx          # decoys excluded, dup collapsed
    assert fx["3947"]["home"] == "erc-ingolstadt"
    assert fx["3947"]["away"] == "iserlohn-roosters"
    assert fx["3947"]["date"] == "12092025"
    # the slug must round-trip into the confirmed URL shape
    assert fx["3964"]["slug"].endswith("_3964")
    assert parse_fixtures(b"<html>no games here, 1234 5678</html>") == {}


def test_channel_check_compares_content_not_status(tmp_path):
    """Ruling 53, portfolio-wide: a 'channel' check must compare CONTENT.

    The DEL probe reported the four game tabs as "10/10 ok" because it
    checked HTTP status. They were one page served five times (game 2580:
    detail, aufstellung and spielerstats all sha256 a6106d4c...), rendered
    client-side by DataTables. Any JS-rendered source springs the same trap,
    so this gate is written against the generic checker, not against DEL.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from del_round1_probe import channel_groups
    same = b"<html><body><div id='dt'></div></body></html>"
    files = []
    for nm in ("2580_detail.html", "2580_aufstellung.html", "2580_spielerstats.html"):
        p = tmp_path / nm
        p.write_bytes(same)          # byte-identical, as the real ones were
        files.append(str(p))
    real = tmp_path / "2580_other.html"
    real.write_bytes(b"<html>genuinely different document</html>")
    files.append(str(real))

    groups = channel_groups(files)
    assert len(groups) == 2, groups          # 4 URLs -> 2 distinct documents
    biggest = max(groups.values(), key=len)
    assert len(biggest) == 3, groups         # the three duplicates collapse
    # and the status-code fallacy: all four "succeeded", only two are channels
    assert sum(len(v) for v in groups.values()) == 4


def test_del_schedule_month_completeness_flag():
    """Ruling 53 Defect 1: a month-paginated season must not pass as complete.

    The fetcher captured the schedule page's DEFAULT month and reported 41
    games as the 2022-23 season -- every one of them September 2022. The
    structural check derives clubs and games/team from the fixtures
    themselves (rule 14: never an absolute total), so it survives
    promotion/relegation and league-size changes.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from fetch_del_raw import completeness, month_histogram
    clubs = ["club%02d" % i for i in range(14)]

    def mk(pairs):
        return {str(i): {"game_id": str(i), "date": d, "home": h, "away": a,
                         "slug": "%s_%s_gg_%s_%s" % (d, h, a, i)}
                for i, (d, h, a) in enumerate(pairs)}

    # one month only -- the Defect-1 signature
    one = mk([("%02d092022" % (1 + i % 28), clubs[i % 14], clubs[(i + 7) % 14])
              for i in range(41)])
    assert len(month_histogram(one)) == 1
    n, gpt, warn = completeness(one)
    assert n == 14 and gpt < 30
    assert any("ONE MONTH" in w for w in warn), warn

    # a full season spread across the real Sep..Mar range
    full, i = [], 0
    for mon, yr in [("09", "2022"), ("10", "2022"), ("11", "2022"), ("12", "2022"),
                    ("01", "2023"), ("02", "2023"), ("03", "2023")]:
        for k in range(52):
            full.append(("%02d%s%s" % (1 + k % 28, mon, yr),
                         clubs[i % 14], clubs[(i + 5) % 14]))
            i += 1
    many = mk(full)
    n2, gpt2, warn2 = completeness(many)
    assert n2 == 14 and gpt2 >= 50, (n2, gpt2)
    assert warn2 == [], warn2
