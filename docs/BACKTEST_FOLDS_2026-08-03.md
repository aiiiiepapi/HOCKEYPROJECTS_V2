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
