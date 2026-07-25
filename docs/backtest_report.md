# Walk-forward Backtest Report — NHL gap-3, v2 model (2026-07-25)

Design: ALL parameters fitted on 2024-25 only; every 2025-26 gap-3 instance
priced blind at up to 9 checkpoints (15:00→3:00 remaining) = 1,442
out-of-sample observations from 657 instances. Outcomes recomputed from raw
pbp goal events (10/10 hand spot-checks passed; leader attribution
cross-validated by two independent methods, 0/1,442 mismatches).

## Calibration verdict: PASS on all four markets
| Market | Brier | Skill vs base rate | Reliability |
|---|---|---|---|
| total ≥1 more goal | 0.1987 | +10.6% | 8/10 PASS |
| total ≥2 more | 0.1999 | +8.0% | 8/10 PASS |
| leader scores ≥1 | 0.2273 | +5.3% | 8/10 PASS |
| leader -3.5 (margin ≥4) | 0.2310 | +2.9% | 8/10 PASS |
Segments: pulled 10/10, not-pulled 10/10, new-coach 9/10 — all PASS.
Residual bias: leader≥1 still ~5 pts low on average — logged, see §Model changes.

## Model changes made DURING the backtest (leakage disclosure)
Two mechanisms were added after diagnostics on the test season, both fitted
on 24-25 data only, both mechanism-based (not free parameters):
1. Re-pull dynamics: once a team has pulled, re-pull comes ~10x faster
   (median 17s; fitted hazard 0.0356/s), active at margins 1-3 only.
2. Pulls at margin 1 (gap-2 hazard proxy).
Three diagnostic passes on the test season were used total. This is soft
leakage; the mitigation is that both mechanisms are structural and their
parameters come from 24-25. A clean re-validation on future data (2026-27)
is the true confirmation.

## Coach layer verdict: REAL BUT MUCH WEAKER THAN FITTED — attenuate
Synthetic P&L (coach-adjusted model vs identical coach-blind pricer as
pseudo-market at -105/-105): NEGATIVE at every threshold, worst for extreme
coaches (-18.7%). Root cause measured directly: cross-season persistence of
coach pull tendencies is slope 0.355 (r 0.29, n=17 coaches) — only ~1/3 of a
measured coach deviation is real signal. Patrick Roy is the strongest
persister (1.86 → 3.11, more extreme in 25-26); Cassidy/Montgomery/Hynes
regressed to ordinary.
PRODUCTION RULE: coach multiplier = 1 + 0.355 × (EB multiplier - 1).
Roy at attenuated ~1.4x remains the top live adjustment; nobody gets 3x again.

## What this backtest CANNOT tell us (odds gap)
No historical odds exist in the repo, so this proves the model is CALIBRATED
(its probabilities mean what they say) but not that it BEATS REAL BOOKS.
The pseudo-market here (coach-blind version of ourselves) is far sharper than
a real book's live 3-gap pricing is likely to be — books must price pull
dynamics generically across thousands of markets. The edge thesis vs real
books remains plausible and UNPROVEN. Required next: capture real live odds
(the API/odds-feed decision for Seb) and paper-trade before real stakes.

## GO/NO-GO recommendation
- GO: model quality (calibrated, all gates green, fully reproducible).
- GO: use v2 prices as the reference number for manual live betting judgment.
- NO-GO: automated/systematic betting until real-odds paper trading exists.
- Betting stance: v1 numbers stay retired; v2 numbers usable as DECISION
  SUPPORT with Seb's own market read, sized conservatively.
