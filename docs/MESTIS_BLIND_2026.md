# Mestis pricer — blind walk-forward record (2026-08-03, Manager session)

Fit 2023-2025 (fits_mestis_train, hbin 120, ruling-27 EN shrinkage), price
2025-26 blind: density coach law (ruling 23), ruling-33 estimator at
CUTOFF 2025-09-01, one pricer (rule 15). 292 checkpoints / 74 instances /
61 games. Rows: data/derived/backtest_rows_mestis.json.

## Result: NO-GO for self-priced markets (Manager verdict, pending Seb)

| market | bias | bad deciles | ROI@10%EV (model lines) | P(>0) |
|---|---|---|---|---|
| leaderTT (lead1) | +11.5pts | 2/10 | +39.8% [+9.8,+71.5] | 0.99 |
| game total over | +11.6pts | 3/10 | +33.2% [+9.4,+55.6] | 1.00 |
| leader -3.5 (marg4) | -0.2pts | 1/10 | +14.4% [-27.8,+56.3] | 0.77 |

Fails the ruling-25 bar (Liiga pass: biases +1..+6, 0/10 bad deciles).
The big positive ROIs are the BIAS, not skill (skill ~0 everywhere): a
conservative model's own lines are too easy to clear. At real market
lines this evidence does not transfer.

## Attribution (each hypothesis tested, in order)

1. Hazard-bin artifact — REFUTED: all bins T=10-12k s, real zeros early,
   same shape as Liiga's passing fit.
2. Estimator chasing the 2025 take-rate dip (31.8% vs 50.9/50.0/48.6) —
   REFUTED: pooled no-recency posterior moves lead1 bias +11.5 -> +11.0.
3. Data artifact (2026 empty-interval pollution) — REFUTED: interval
   duration distributions comparable across seasons; the alarming
   "gap-3 EN 21.6k s" readout was the TAU=20000 pseudo-exposure
   (ruling 27) in the printout, not real exposure.
4. Model defect (in-sample miscalibration) — REFUTED: at matched
   alive-pre-pull checkpoints the sim matches TRAIN actuals (R=300:
   sim 0.39-0.43 vs train actual 0.377).
5. ~~"REAL 25-26 LATE-WINDOW DRIFT"~~ — **CORRECTED same day by the
   multi-fold backtest Seb ordered (docs/BACKTEST_FOLDS_2026-08-03.md,
   15b):** the single 2026 fold couldn't distinguish "2026 drifted" from
   "every Mestis season wobbles". Folds show the latter: forward biases
   +7.5 / -6.6 / +11.5 across 2024/2025/2026 — BOTH directions, every
   fold bigger than Liiga's pass margin, and the 2025 fold would have
   LOST money at model lines. Season-level wobble is the standing
   attribution; the 2026-specific late-window numbers above remain true
   but are one draw from that wobble, not a regime change.

## How this differs from the AHL failure (rulings 24/39)

- EV full-net levels are STABLE (never-pull instances calibrated at
  +2.7pts; AHL's failure was a broad directional competitive shift).
- marg4 is dead-on calibrated (-0.2pts); no sign flips anywhere.
- Drift is one-sided CONSERVATIVE and confined to the pull-conditional
  late-window channel (pulls slightly more frequent, spells longer,
  conversion hotter in 25-26).

## Standing state

- Self-priced Mestis markets: NO-GO. No lines_10ev_mestis.csv may exist
  until a blind pass is recorded here (gate test_mestis_not_bettable_flagged).
- Coach intel (ledger/profiles/morning sheet): STANDS — outcome-based,
  same validity class as AHL intel under ruling 24.
- Path to money: (1) September — check the Odds API catalog for a Mestis
  market; if books price it, wire Mestis into the paper harness and log
  model-vs-real-line-vs-outcome from opening night; (2) re-litigate blind
  with 26-27 as it accrues (two blind seasons double the evidence);
  (3) coach-delta product path (ruling 26c) applies here as it does to AHL.
- Superseded in method by docs/BACKTEST_FOLDS_2026-08-03.md (multi-fold):
  verdict unchanged, attribution corrected to symmetric season-level
  wobble (+/-7-12pts), "conservative-safe" framing retracted.
