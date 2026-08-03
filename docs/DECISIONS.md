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

28. **Betting floor (Seb, 2026-08-01; AMENDED 2026-08-02: 50%% -> 40%%):
    NEVER bet when expected pull %% < 40.** Floor applies to the BASE coach %%
    (fav/dog effect lives in special notes since the 2026-08-02 card spec,
    so a sub-40 coach stays NO-BET even as a big favorite). Evidence
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

30. **CAREER-FADED LEAGUE ANCHOR (Seb, 2026-08-02: 'league standards bring
    little to no value as a whole').** The anchor's pseudo-count now fades
    with career evidence: S_eff = S * 0.5^(max(career_n-8,0)/8), one shared
    implementation (prior_fit.posterior) in profiles + both backtests.
    Evidence: established-coach (>=10 chances) predictions are FLAT in NHL
    with or without the anchor and BETTER faded in AHL; small-n shrinkage
    unchanged (perfect 3-streaks continue at 67%, n=79). Also fixes the
    recency-decay artifact where veterans kept a permanent 12-26%% league
    weight. Blind re-validation: NHL leaderTT +23.9%% P(>edge)=0.973,
    Liiga all green (biases +2.2/+0.3/-0.9/+6.1), 17 gates green.
    Related measurements same night: calendar stage-of-season NULL in all
    3 leagues (within-coach); fav/dog swing concentrates in sub-50%%
    pullers (+11pts z=2.6, diluted-sample — clean-chance confirmation
    queued); playoff-race proper test needs standings-as-of-date (next
    block, elevated by Seb's doctrine).

31. **Recency half-life FITTED = 6 chances; fade start = 6 (2026-08-02).**
    Recency HL was 10 by ruling, never fitted; predictive test prefers 6 in
    ALL THREE leagues independently -> adopted. Fade start: data mildly
    prefers 8 (NHL/AHL monotone), Seb ruled <8; complying at 6 costs
    ~0.0004 nats (noise) — recorded as Seb's call over a weak data
    preference, revisit if 26-27 sharpens the gradient.

32. **CALENDAR RECENCY + WHISPER-PAST-3 FADE (Seb, 2026-08-02).**
    (a) Recency re-based from per-chance to CALENDAR decay, half-life 12
    months — FITTED: beats per-chance in NHL+AHL, ties Liiga. (b) League-
    anchor fade start 6->3, half-life 8->3 ("league average a whisper past
    3 chances") — Seb ruled WITH the predictive cost on the table
    (0.0076/0.0064/0.0019 per league vs start-6: rule 0b satisfied).
    Estimator API: sequences are (date, took) tuples, one implementation
    (prior_fit) for profiles + both backtests.

33. **HOT-RECORD ANCHOR CAP (Seb, 2026-08-02).** A coach whose RAW career
    record is 75%+ pulls on >= 2 chances gets the league anchor capped at
    ONE chance-equivalent (S_eff = min(S*fade, 1)). Seb's examples, now
    exact code behavior: weight league on 3/5 (60%) but not 3/4 (75%);
    weight on 1/1 (n too small) but not 2/2. Pull-side only as ruled —
    low-side coaches keep the normal whisper-past-3 fade (they're NO-BET
    territory anyway under rule 28). Effect: identical records now score
    nearly identically across leagues (3/3 recent: NHL 87-88%, Liiga
    84-85%). League S refit predictively under the new rule: NHL 3->3,
    AHL 5->9, Liiga 5->4 (the fit re-spends anchor weight on the non-hot
    majority once hot coaches are released). ONE implementation:
    prior_fit._anchor_strength backs profiles, cards, and all backtests.

## 2026-08-02 (league finalization block — Manager session)

34. **Ruling 17b — dp artifact rule COMPLETED (2026-08-02; Seb RATIFIED
    same day, conditional on dp-certainty — condition closed by the
    stays-in behavioral check below).** Ruling 17's ">25s at a leader whistle = real pull"
    convention was tested against NHL dp ground truth (6,594 explicit dp
    possessions: 8.7% exceed 25s) and hand-verified case by case — three new
    artifact clauses in the shared engine (segments.py):
    (i) leader-whistle enders starting before P3 12:00 with dur<=60s;
    (ii) early dp GOALS (trailing 6v5 goal, <=25s, no penalty event — the
    goal wipes the minor); (iii) whistle-lag (leader penalty assessed inside
    the segment's first 10s, <=25s, early). 7 AHL + 1 Liiga phantom pulls
    removed, incl. 2 phantom successes. Late/middle-band long enders keep
    ruling 17 (conservative: no removals where genuine doubt exists).
    RATIFICATION CHECK (behavioral): in all 8 removed cases the goalie
    returned at the whistle and STAYED IN through the team's own ensuing
    power play (or re-pulled only at normal late-game pull times — 15:45,
    16:50 — which is the evidence that was kept); the 2 kept contrast cases
    re-pulled 8s/15s after the whistle. A deliberate puller does not hand
    back the net upon GAINING a 6-on-4. All 8 pinned by exact-value gates.
    Full trace: docs/ground_truth_traces/interval_dp_audit_2026-08-02.md.
35. **Misconduct fix (bug, no ruling needed):** 10-min misconducts never
    shorthand a team; excluded from box-strength classification in both
    interval adapters (kept as whistle markers). 8 AHL + 1 Liiga
    classification flips, both directions (2 hidden EV pulls RECOVERED as
    bettable: 77/1024678, 90/1028615; plus liiga 2026/466).
36. **Same-second swap fix (bug):** IN-then-OUT feed order at one second is
    a goalie substitution, not a pull; OUT-first normalization (534/534
    same-second pairs in the lake have the net full — loss-free). Removed
    two 6-12-minute phantom "pulls" (90/1028763, 90/1027839) and fixed one
    evidence time (77/1024882: 520->957).
37. **NHL blip rule + order-independence (closes the logged v2 edge):**
    faceoff codes are authoritative within a second; <=2s empty runs at a
    penalty with no dp window are blip artifacts. 3 corrections, all
    2022-23 (outside the training window); production numbers unchanged.
    D.J. Smith ledger row corrected (7/12 -> 6/11).
38. **Liiga random audit shipped at AHL parity** (seed 20260802, 30+30 vs
    raw goalKeeperEvents): 0/60. Both leagues' audits are now a standing
    gate (tools/audit_interval_random.py). Gate count 17 -> 21.

39. **AHL failure mechanism RE-ATTRIBUTED on corrected data (2026-08-02,
    triggered by Seb's challenge "we've bet AHL for years — find the issue").**
    Re-ran the full H1/H2 forensics on the post-ruling-34 extraction:
    (a) DATA IS CLEAN: instance audit 0/60 vs raw; feed stable by month
    (goalie rows 5.3-5.9/gm, penalties ~10/gm, EN-flag share ~0.08-0.10,
    no January discontinuity). The blind failure is NOT a data defect.
    (b) Ruling 26(b)'s "the moving level is 6v5-SPECIFIC" does NOT replicate
    on corrected data (15b correction — it was drawn pre-fix): gap-3-window
    EN rates moved only modestly (ENG-against 18.9->16.6/60, n=20/25,
    within Poisson noise). The outcome collapse at matched checkpoints is
    REAL (marg4@R600 0.404 H1 -> 0.233 H2) but decomposes as a BROAD
    competitive shift inside gap-3 games after the checkpoint: leader EV
    goals/inst 0.28->0.19 (-33%), trailer EV goals/inst 0.21->0.34 (+62%),
    pulls-after-600 32%->26%. H2 blowout games got more competitive across
    all channels — leaders eased / trailers pushed — not a 6v5 physics change.
    This also EXPLAINS ruling 26(b)'s anchor refutation: the leak-free
    anchor used full-game scoring, which was normal (H2 goals/gm ~6.2-7.2,
    unchanged) — the shift lives in leader/trailer dynamics within trailing
    games, invisible to a full-game anchor.
    (c) Candidate mechanisms for the 26-27 re-litigation (post-hoc, 15b —
    flagged, untested): playoff-race desperation of trailing teams (matches
    Seb's queue-2 doctrine — the race covariate is the missing-variable
    candidate), trade-deadline/callup churn, Olympic window (Feb 2026 is an
    outlier month: 7.20 goals/gm, EN share 0.052).
    (d) Reconciliation with Seb's live AHL betting: what fails blind is
    absolute-level self-pricing across half-seasons. Betting at MARKET
    lines with coach knowledge is not exposed to that instability — the
    book re-prices levels continuously. This is exactly the coach-delta
    product (ruling 26c): price only the coach-knowledge delta vs the
    book's implied baseline. Paper harness logs the needed data from
    opening night. NO-GO on self-priced AHL markets STANDS (ruling 24);
    the coach-delta path is the sanctioned route to AHL money.

39b. **Seb correction ACCEPTED (2026-08-02): "teams pull more aggressively in
    H2" is TRUE.** Clean-chance take rates (composition-controlled) H1 vs H2:
    77: 60.0->63.3, 81: 49.0->43.0, 86: 43.3->54.2, 90: 40.0->46.7 (pooled
    47.9% -> 51.7%). Ruling 39's "pulls-after-600 32->26%" was a crude
    composition-confounded slice — retracted as a pull-aggressiveness claim.
    This SHARPENS the 90-H2 anomaly instead of resolving it: leader-stretch
    (widened-to-4 after R600) by half: 77 .385->.515 UP, 81 .446->.365 down,
    86 .377->.462 UP, 90 .439->.279 (lowest of all 8 halves; 77-H2 is the
    highest). No repeating H2 pattern -> a stage covariate cannot model it
    (consistent with ruling 30's calendar-stage NULL). The 90-H2 signature:
    trailing teams pulled MORE, ate HALF the ENGs (0.16->0.09/inst), scored
    more at EV (0.30->0.41/inst), leaders scored less — desperation that
    WORKED, concentrated in one half-season. Reinforces the race-covariate
    (standings-aware, team-level) as the only candidate that could capture
    WHICH trailing teams push; blanket H2 adjustments would damage 77/86.
    NO-GO unchanged; re-litigation path unchanged.

39c. **Seb's stability claim CONFIRMED for totals, refined for direction
    (2026-08-02):** league-wide P3 goals/min stable every month (0.12-0.13,
    Nov-Apr); gap-3 window totals stable across halves (0.100 vs 0.108/min).
    The 90-H2 shift is DIRECTIONAL only: leader 0.055->0.055/min flat,
    trailer 0.045->0.053 (+18%), leader goal share 55%->51%, ENG/inst
    halved. Directional products (leaderTT, -3.5, marg4) price the split,
    not the total — which is why total-anchored fixes all tested null.

40. **Seb ordered the NHL-rates splice deployed for AHL (2026-08-02, "use
    NHL goal/min numbers for AHL as of now"); built and re-run blind on the
    corrected extraction per rule 0 (26d was pre-fix). RESULT: FAIL —
    marg4 -12.1pts / 9-of-10 bad deciles (worse than AHL's own fits -10.9),
    leader -3.5 ROI -22.3% P(>0)=0.00 (worse than -20.5% own), leaderTT
    -3.4% P(>0)=0.32, lead1 bias -6.1. Total-over +3.8% P(>0)=0.74 (noise).
    Mechanism: NHL levels are equally static (90-H2 directional shift bites
    identically) and foreign (NHL EN-against ~22/60 vs AHL ~18 makes marg4
    MORE optimistic). Per verification protocol step 6 + ruling 1 + ruling
    24's lifting condition, the config cannot reach a bet card. The splice
    is permanently reproducible: backtest_interval.py {league} --nhl-rates
    (rows in backtest_rows_ahl_nhlrates.json). Ruling 26d's verdict stands
    on corrected data: NHL contributes SHAPES, never LEVELS.**

41. **SEB OVERRIDE (2026-08-02): AHL production runs on NHL goal/min levels
    "for now."** Ordered after hearing the full failed-blind record three
    times (rulings 26d + 40 — marg4 -12.1pts / 9-of-10 bad deciles, -3.5
    ROI -22.3%, leaderTT -3.4% at model lines on corrected data). Manager
    recommendation AGAINST staking these prices stands on the record (0b
    satisfied both ways: disagreement heard, principal ruled). Implemented:
    lines_10ev_ahl.csv priced via splice.py (ONE implementation, rule 15)
    on full AHL fits + NHL levels; leader -3.5 thresholds BLANKED (ruling
    26a is permanent and survives this override); UNVALIDATED banner at
    data/derived/AHL_LINES_UNVALIDATED.md; rule 28 floor unchanged.
    Ruling 24's no-go remains as the verification-status record: these
    lines exist BY ORDER, not by passed validation. December re-litigation
    + paper harness (which logs model-vs-real-line-vs-outcome and will
    settle this empirically) continue unchanged.

41b. **SEB OVERRIDE EXTENDED (2026-08-02): -3.5 runs on NHL numbers too.**
    Seb overrode his own ruling 26a ("AHL -3.5 permanently no-bet under ANY
    fix") after re-hearing the oracle record (perfect-level refit still ~0
    skill on marg4) and the splice blind (-22.3% ROI, P(>0)=0.00). Manager
    recommendation against staking -3.5 stands on the record. Production
    config now: AHL coach pull % (ruling-33 estimator) + AHL pull structure
    (hazards, dead time, return/repull) + NHL scoring rates (rates, rates_R,
    m_PP, pen via splice.py) — all three markets on lines_10ev_ahl.csv.
    Direction sanity checks pass (rule 9). UNVALIDATED banner updated.
    Paper harness + December re-litigation remain the empirical arbiters.

## 2026-08-03 (Mestis block — Manager session)

42. **ATTRIBUTION GATE (Seb, 2026-08-03: "almost every one of my challenges
    overturns your conclusions, that's an issue").** Extends 15b from
    comparative claims to CAUSAL/attribution claims. No attribution or
    verdict ships without, attached: (a) a NULL TEST — the effect must be
    distinguishable from sampling noise at the correct clustering level,
    computed, never eyeballed ("it's noise" is permanently the first
    candidate hypothesis); (b) at least one competing explanation
    explicitly tested; (c) a stated limit of what the test design cannot
    distinguish — if the design can't separate the claim from an
    alternative, only the numbers ship, not the story. Context: the
    pipeline layer has never been overturned (audits 0/60, GT first-run
    passes); the overturned claims were all interpretation-layer (rulings
    27, 29, 39b, and twice on 2026-08-03: "25-26 drift" then "season
    wobble" — both fell to Seb's variance hypothesis, confirmed by
    tools/fold_variance_test.py: all folds |z|<2, tau~0). Multi-fold
    backtest (tools/backtest_folds.py) replaces single-fold blind as
    deciding evidence for every future league verdict.

43. **MESTIS UPGRADED to Liiga-class PROVISIONAL (Seb ratified 2026-08-03).**
    Basis: pooled forward folds (3 blind seasons, 968 checkpoints / 225
    games — evidence order of Liiga's ruling-25 basis): leaderTT bias
    +4.5pts / ROI@10%EV +22.3% [+4.7,+38.8] P(>0)=0.996; total over
    +0.7pts / +11.3% [-2.0,+24.5] 0.95; leader -3.5 +0.8pts / +14.9%
    [n.s. 0.90]. Per-fold swings confirmed pure sampling variance
    (ruling 42's founding case). Production: lines_10ev_mestis.csv from
    the full 4-season fit, all three markets (no -3.5 exclusion — unlike
    AHL, Mestis marg4 is calibrated), rule-28 40%% floor, paper-trade from
    September alongside NHL+Liiga. Recorded caveats: single-season luck
    band is 6-10pts at this sample size (the 2025 fold LOSES ~6%% at model
    lines — sit-through variance), leaderTT tail deciles 3/10 (2026 tail),
    total-over pooled CI floor -2%%, all model-line (not market-line)
    evidence; September paper log is the arbiter. NO-GO pin replaced by
    the provisional-status gate; re-blind when 26-27 accrues (standing).
