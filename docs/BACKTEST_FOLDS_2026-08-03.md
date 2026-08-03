# Multi-fold backtest — method upgrade (2026-08-03, Seb's order)

Seb rejected the single-fold blind design ("find a better way to backtest")
— and the multi-fold result proves him right (0b on record, 39b pattern):
the single 2026 fold produced a WRONG attribution that the folds corrected.

## Method (tools/backtest_folds.py, one implementation for all interval leagues)

- **FORWARD folds** (betting-valid, strictly causal): for each season, fit
  ONLY on strictly earlier seasons, coach estimator cut at that season's
  start, price it blind. Every season becomes a test season once.
- **LOSO level check** (diagnostic, not betting-valid): fit on the OTHER
  seasons, price the held-out one with a FLAT coach (league mu) — isolates
  LEVEL calibration from the coach layer, symmetric across all seasons.
  Scatter around zero -> model fine, outliers visible. Same-direction miss
  everywhere -> the model itself is off.

## Mestis result — my single-fold attribution CORRECTED (15b)

| design | test | n | lead1 bias | total1 bias | marg4 bias |
|---|---|---|---|---|---|
| forward | 2024 | 390 | +7.5 | -0.9 | +7.0 |
| forward | 2025 | 286 | **-6.6** | **-8.2** | **-6.7** |
| forward | 2026 | 292 | +11.5 | +11.6 | -0.2 |
| loso | 2023 | 507 | +1.6 | +1.0 | -2.4 |
| loso | 2024 | 390 | +5.1 | -2.1 | +3.5 |
| loso | 2025 | 286 | -3.7 | -6.0 | -2.3 |
| loso | 2026 | 292 | +10.6 | +10.6 | -1.1 |

ROI at model lines by forward fold: 2024 +29.6/+7.6/+33.0; **2025
-5.6/-6.0/-9.2 (a betting year at model lines LOSES)**; 2026
+39.8/+33.2/+14.4.

**Corrected attribution:** NOT "2025-26 uniquely drifted" (retracted —
drawn from the one fold that happened to be the largest miss). Mestis
season LEVELS wobble +/-7-12pts fold-to-fold IN BOTH DIRECTIONS at every
training configuration. The distributional shape is fine (LOSO deciles
clean for 2023-25); the wobble is pure season level — what a 245-364-game
league hands you. The "conservative-side safe" framing is DEAD: 2025's
miss was optimistic and would have lost real money.

**Verdict unchanged, foundation stronger: NO-GO for self-priced Mestis
markets** — same structural reason as AHL ruling 24 ("levels unstable at
every tested timescale"), softer flavor (no directional collapse, marg4
shape stable, wobble symmetric). Coach intel unaffected. Paths: paper
harness (if a Mestis market exists), 26-27 re-litigation, coach-delta.

## Liiga re-checked under the same method (rule 0 on our own pass)

| design | test | n | lead1 bias | total1 bias | marg4 bias |
|---|---|---|---|---|---|
| forward | 2025 | 417 | +4.8 | +6.9 | -4.8 |
| forward | 2026 | 553 | +2.0 | +0.1 | +5.9 |
| loso | 2024 | 482 | -8.0 | -8.2 | -8.8 |
| loso | 2025 | 417 | +3.9 | +4.9 | -7.3 |
| loso | 2026 | 553 | +6.0 | +3.5 | +9.3 |

Forward ROI: 2025 +19.8/+23.0/-1.0; 2026 +18.2/+12.7/+30.0.

**Ruling 25's provisional pass SURVIVES a second forward fold** (both
conservative-side, both positive ROI on the two Over markets). Caveat now
on record: LOSO 2024 shows Liiga seasons CAN sit ~8pts on the optimistic
side — half of Mestis's amplitude, but not zero. September paper-trade
data remains the arbiter; the wobble scale is why ruling 25 says
"provisional", and this quantifies it.

## Standing rule going forward

Any future interval-league pricer verdict (incl. Magnus, and the AHL/
Mestis re-litigations) runs tools/backtest_folds.py, not a single fold.
Single-fold blind is retired as the deciding evidence.


## Addendum same day — Seb's variance hypothesis TESTED and CONFIRMED

Seb: "its probably a variance issue on a small sample." Measured
(tools/fold_variance_test.py — game-clustered bootstrap SE per fold,
joint chi-square, random-effects tau):

- Mestis: every fold |z| < 2.0 (max: 2026 total1 z=+1.95); joint p-values
  0.13-0.95 — the fold swings are NOT distinguishable from luck. tau
  (true between-season level spread after removing sampling noise):
  lead1 0.002, marg4 0.000 on LOSO — ~ZERO true season wobble. My
  "season-level wobble is real" attribution from earlier today is hereby
  RETRACTED as unproven (15b — second correction; the forward-fold tau
  0.07-0.08 is inflated by thin-training estimation noise, and the
  cleaner 3-season-trained LOSO shows none).
- Liiga: same picture (taus 0-0.086, joint p mostly > 0.2).

Consequence: the right scoring pools the folds (noise averages out).
POOLED FORWARD results (968 checkpoints / 225 games — same evidence
order as Liiga's ruling-25 basis):

| market | pooled bias | bad deciles | ROI@10%EV | CI95 | P(>0) |
|---|---|---|---|---|---|
| leaderTT | +4.5pts | 3/10 | +22.3% | [+4.7,+38.8] | 0.996 |
| total over | +0.7pts | 0/10 | +11.3% | [-2.0,+24.5] | 0.950 |
| leader -3.5 | +0.8pts | 1/10 | +14.9% | [-6.7,+37.0] | 0.901 |

Liiga pooled two-fold, same method: +3.2/+3.0/+1.3 biases, leaderTT
+18.9% [+2.2,+35.3], total +17.1% [+4.2,+30.3], -3.5 +16.7% [n.s.].

**Manager recommendation (pending Seb): upgrade Mestis NO-GO ->
Liiga-class PROVISIONAL** — paper-trade at model lines from September,
rule-28 floor, with the recorded caveats: any single season can run
6-10pts off pure luck at this sample size (the 2025 fold LOST 6% at
model lines — variance you must be able to sit through), leaderTT tail
deciles 3/10 (2026 tail), total-over CI floor slightly negative, and all
of this is model-line evidence, not market-line evidence. Score: Seb's
challenges overturned two Manager attributions today (single-fold
"drift", multi-fold "wobble") — 39b pattern, recorded.
