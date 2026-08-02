# Seb rulings ledger (binding)

## 2026-07-25 (checklist round)

1. **Go/no-go: NO-GO.** Model is NOT ready to be treated as done — "everytime
   I mention something we fix and come to new conclusions, we need to be 99%
   sure." Keep hardening; paper-trading verdict deferred. No real money.
2. **lead1 conservative bias: not acceptable as a permanent exception.**
   "We gotta figure it out." Root-cause hunt #3 stays open (best lead: needs
   the 4-season lake). Gate exception remains only as an interim guard.
3. **Coach small-n policy: RISKY flag only.** N_min=5 gate + half-stake
   REJECTED as too conservative. Coach estimates are used at whatever evidence
   exists (shrinkage + adaptive weighting handle small n); pairs with <5 real
   chances are flagged RISKY with a widened interval. No stake mandates.
4. **Pulled-state multi-goal over: withdrawal RATIFIED.** Off the card.
5. **Odds capture: (c) skip.** No odds feed. The betting deliverable is
   model-side: for every second remaining (15:00→3:00), the line at which a
   bet clears +10% EV — validated by backtesting outcomes at those exact
   lines, NOT by market availability.
6. **Other leagues (incl. AHL): parked.** "Finalize NHL first and make sure
   we are 100% ready and accurate."
7. **2+-more-goals markets DROPPED entirely** ("we dont want the over 1.5
   goals thing"). Removed from calculator and line tables. The pulled-state
   overshoot gate survives as a model-health diagnostic only — no more
   convergence hunts on it.
8. **PP-pull directive**: PP pulls need their own per-coach weighting ("some
   teams only pull on PP" — CONFIRMED: Tortorella/McLellan/Cronin/Huska, 0 EV
   pulls in 35k+ EV secs, league+ rate on PP). Coach layer to become
   (m_EV, m_PP). Covariate backlog to be triaged: keep signal, drop noise.

## Earlier standing rulings
- 2026-07-24: full v2 rebuild, trust nothing from v1 except raw data + docs.
- 2026-07-25: rule 0 (never assume prior work correct) + rule 0b (disagree
  openly before complying).
- Bet products: leader TT over, game total over, leader -3.5. OT4V3 and
  NEXTGOALPROP parked. Prices from 15:00 down to 3:00, never below 3:00.
- Recent-season overweighting: tested and rejected on evidence (Seb accepted).

## 2026-07-26
9. **Aggressiveness estimator rebuilt**: "3/3 is not league average." Beta
   prior fitted on league coach spread (a=2.46, b=1.67) + recency decay
   (half-life 10 chances) on each coach's own 5v5 chance sequence. 3/3 -> 76%.
10. **Recency ruled in** at coach level (last-3 form shown in guide).
11. **Pulled-state rows removed** from lines doc (no lines offered anyway).
12. **Manual override tab**: Seb inputs his own pull % + typical pull time;
    priced through a dedicated MC grid (pull% x timing-shift x time), 5v5 only.
13. **Team/coach-first navigation**: TEAM LINES tab prices every team at its
    own coach's expected % + timing; filter by name.
NOTE: new coach layer is PROVISIONAL until blind re-validation (next block).
14. **Average pull timing REMOVED from production pricing** (2026-07-26):
    observed averages are opportunity-gated noise; the in-window conditioning
    channel (20-26pt swings at 5:00-6:00) overreads silence. Raw timing stays
    visible as context; EARLY-puller flag + stand-down rule replaces the curve
    shift; MANUAL tab keeps the timing knob; Gen-3 threshold+opportunity model
    is the sanctioned way to bring timing back.
15. **lead1 hunt #3 CLOSED (2026-07-26, triggered by Seb's Bednar-at-6:00
    challenge)**: root causes = missing in-sim penalty generation (17% of
    leader goals are PPGs) + flat goal rates (desperation acceleration) +
    backtest running raw-EB coach multipliers. All fixed; bias +5..7 -> +2.4.
    NEW: -3.5 now ~4pts OPTIMISTIC -> CAUTION on card (double edge or skip)
    until coach-conditional hazards. ROI at 10%-EV lines (blind, clustered):
    leaderTT +22.8% [+9.0,+37.9], total +11.0% [+0.6,+21.8], -3.5 +4.1% [n.s.].
16. **Morning bot v1 shipped (2026-07-31)**: real moneylines ruled in for
    DAILY inference (partial reversal of odds:c — historical odds still
    skipped; effect fitted on results-based strength, ML maps to same scale).
    Mining results: strength effect one-sided (favs 66%, heavy dogs 39%,
    slight fav == heavy fav); venue NULL at chance level (+1.6pts) -> display
    only. Card = expected % + why + last-3 chances with outcomes.

## 2026-08-01 (AHL/Liiga expansion block)
17. **Delayed-penalty artifact rule (interval leagues)**: gap-3 empty-net
    segments ending at a whistled penalty ON THE LEADER with duration <=25s
    are dp extra-attacker moments (AHL: median 10s, 85/98 <=25s), NOT pull
    decisions. Excluded from pull evidence in the shared engine. AHL pulls
    461 -> 404. Liiga channel barely logs these (n=2) — rule applied
    symmetrically anyway.
18. **Liiga 2022-23 pull truth = UNKNOWABLE** (API has no goalie-event
    channel that season, both fields empty league-wide). Instances marked
    pulled=None + no_goalie_channel; season still feeds rate fits.
19. **18s post-goal dead time transfers** to AHL and Liiga (re-measured per
    league, ~1.0%% obs vs ~2.8%% uniform at 18s — same shape as NHL, applied
    per league from its own measurement, not assumed).
20. **AHL hazard pooling**: all 4 seasons (comparable-window rates 26-35%%,
    no era trend — unlike NHL's 1.48x drift).
21. **League ledgers are self-contained**: prior, hazards, dead time fitted
    per league from its own data; NHL contributes shapes only.
    Composition-controlled clear-chance take rates: NHL 54.5%%, AHL 50.9%%,
    Liiga 41.5%%.

22. **Survival-mapped coach law: estimator vindicated, pricing adoption
    DEFERRED (2026-08-01).** Beta+recency P_c is fully persistent
    cross-season (beta=1.13 vs 0.36 for raw-EB). But pricing with true k
    worsens marg4/total1 because EN-against conversion is coach-tier
    dependent (35-65/60 reluctant, 23 average, 7-17 aggressive) while the
    sim pools it. Root cause of -3.5 CAUTION identified; fix = coach-
    conditional conversion + survival hazard, next Fable block
    (docs/marg4_root_cause.md). Production stays on 0.355 law meanwhile.

23. **DENSITY-PRESERVING COACH LAW ADOPTED (2026-08-01, Seb ratified).**
    Production prices every coach via coach_hazard_array(P_c): pull
    probability = the clean-window Beta+recency posterior, league timing
    shape preserved exactly. Raw-EB multipliers + 0.355 attenuation RETIRED.
    Evidence: pooled cross-season persistence of P_c = 0.99 [0.42..1.50];
    survival-k scaling shifts pulls ~26s early (rejected); EN-conversion-by-
    tier hypothesis RETRACTED (training data flat — the 25-26 gradient was
    small-n noise, a rule-15b violation caught next block). Blind 25-26:
    all calibration gates pass, lead1 bias +2.4 -> +1.5pts; leaderTT ROI
    +21.3% (P(>edge) 0.973 -> 0.946; gate moved 0.95 -> 0.94 with Seb's
    ratification). -3.5 stays CAUTION (bias -4.9pts, season-wobble limited).
    Grids/tables re-keyed to pull-%% tiers (25/40/55/70/85).

24. **AHL: NO-GO for pricing (2026-08-01).** Blind walk-forward failed every
    fitting protocol: 4-season pool (marg4 -11.1pts, ROI -21%% at -3.5),
    recent-2-seasons, in-season rolling (fit 86+90H1 -> price 90H2), and
    season-local (fit 90H1 only). Model-free confirmation at matched
    checkpoints: 90-H2 outcomes collapsed vs 86 AND 90-H1 (marg4@R600
    0.40/0.40/0.23, ~3sigma) — levels unstable at every tested timescale
    (development-league roster churn; the 26-Feb Olympic window is an
    unproven suspect). AHL stays: coach profiles + morning-bot intel
    (outcome-based, valid) — NO priced markets until a future season
    passes blind. Gate test_ahl_not_bettable_flagged pins this.
25. **Liiga: blind PASS, provisional (2026-08-01).** Fit 2023-2025, price
    2026 blind, density coach law: all markets conservative-side (lead1
    +2.8, total1 +1.2, marg4 +6.5pts — Overs-safe), 0/10 bad deciles
    everywhere, ROI@10%%EV leaderTT +19.1%% / total +14.3%% / -3.5 +30.2%%
    (P(>0) 0.95/0.93/0.96 — ONE thin season, n=553, CIs wide). Status:
    paper-trade alongside NHL when the season starts (Sept); NOT "99%%
    sure"; Liiga -3.5 is conservative unlike NHL's (their EN dynamics
    differ — rarely pulled nets make marg4 rare and the model under-calls
    it). Calibration gate added with provisional documented bounds.

26. **AHL fix attempts, round 2 (2026-08-01) — oracle viable, anchors refuted.**
    (a) ORACLE test: refit levels on 90-H2 itself (perfect level knowledge,
    coach layer leak-free) -> calibration recovers to NHL-like (lead1 -2.9,
    total1 -2.8, 1/10 bad; marg4 -5.3 with ~0 skill -> AHL -3.5 = no-bet
    under ANY fix, same as NHL CAUTION). Levels ARE the failure.
    (b) BUT the level that moved is 6v5-SPECIFIC: 90-H2 EN-against fell
    22.1 -> 15.6 /60 while EN-for rose 5.9 -> 7.5; full-game scoring was
    normal (leak-free team-environment anchor: scales ~1.00, biases
    unchanged -8.0/-6.6/-15.6 -> REFUTED). Pre-game market totals carry the
    same kind of information -> market-total anchoring REFUTED as the fix.
    (c) CAVEAT (15b): the H1/H2 decomposition is post-hoc; the primary
    pre-registered result remains "AHL 25-26 failed blind." The H2 6v5
    shift may itself be selection-inflated noise.
    Fix path that survives: (1) auto re-litigation as 26-27 accrues
    (existing gate); (2) paper-trade harness from opening night logging
    model prices vs REAL lines vs outcomes — the only data that can
    validate a market-relative product; (3) coach-delta product design
    (price only the coach-knowledge delta vs the book's implied baseline)
    once paper data exists. rate_scale stays in the pricer (harmless,
    market-anchor-ready if paper data later justifies it).
    (d) NHL-rates splice (Seb's question, tested 2026-08-01): NHL goal
    rates + AHL pull structure on 90-H2 -> WORSE everywhere (lead1
    -10.3, total1 -8.9, marg4 -17.8). Foreign level + equally static.
    NHL contributes SHAPES to other leagues, never LEVELS.

27. **EN-rate shrinkage + Liiga league-table retraction (2026-08-01, Seb's
    challenge "our Finland numbers are wrong").** Verification: Liiga EN
    measurement is CORRECT (TM-flag agreement 79/79, 90/90, 95/95; rates
    stable across 3 seasons). But the quoted league table used the gap-3-only
    cell (SIX 6v5-for events -> "3.9/60, half of AHL") — RETRACTED (15b).
    Well-sampled truth: Liiga 6v5-for 5.9-8.8/60 ~= AHL/NHL ~8; against
    22-25.5 ~= NHL 22.4. Finland's EN behavior is normal; only pull
    FREQUENCY differs. Fix shipped: interval-league fitter shrinks each
    gap's EN rates toward the cross-gap pool (TAU=20000s pseudo-exposure;
    NHL large-T shows 6v5-for flat across gaps). Liiga blind re-run:
    calibration unchanged-to-hair-better, all gates green.

28. **50%% floor (Seb, 2026-08-01): NEVER bet when expected pull %% < 50.**
    Recorded as BETTING POLICY (cards marked NO-BET below 50%%). Evidence
    note (0b, on record): blind backtests AT MODEL LINES show sub-50 spots
    did not lose (NHL leaderTT +35.7%%, Liiga positive) — but at REAL market
    lines sub-50 Overs rarely clear the +10%% threshold anyway (our number
    sits below the market's), so the rule mostly formalizes the natural
    mechanism and concentrates risk where the coach edge is positive-side.
    Paper harness still LOGS sub-50 spots for real-line evidence.
28b. **Hot-form override (Seb, same ruling): any coach who PULLED HIS LAST
    clean chance, or pulled 2 of his last 3, appears on the morning report
    regardless of expected %%, flagged HOT FORM for manual review. Flag does
    not by itself authorize a bet below the 50%% floor.**

29. **PREDICTIVE PRIOR ADOPTED (2026-08-02, Seb's UTC challenge).** Coach-
    prior strength now fitted by out-of-sample next-chance log-likelihood
    (hockeycore/fit/prior_fit.py, rule 15 — one implementation for profiles
    and both backtests), prior mean = league clean take rate. NHL strength
    4.1->2, AHL 6.9->5, Liiga 7.0->5. Evidence: hot-established coaches
    (>=80%% over >=5) continued at 75%% observed vs ~65%% modeled (Seb right);
    perfect 3-streaks continued at 67%% (n=79) so small-n shrinkage stands
    (TPS ~63%% unchanged). Blind re-validation IMPROVED: NHL leaderTT ROI
    +21.3%% -> +24.0%%, P(>edge) 0.946 -> 0.973 (clears even the pre-ruling-23
    0.95 bar); total-over CI floor now positive; Liiga all gates green,
    biases smaller. 17 gates green.
