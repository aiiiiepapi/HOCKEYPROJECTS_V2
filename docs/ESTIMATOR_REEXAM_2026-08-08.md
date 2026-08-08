# Ruling-49 re-exams — should the sheet estimator price the lines?

Ordered by Seb 2026-08-08 ("yes"). Question: does the ruling-44 no-league-
anchor estimator beat the validated rulings-29-33 incumbent in PRICING?
Deciding evidence per the multi-fold law: forward folds only, pooled,
game-clustered bootstrap. Corrected (ruling-45) ledger throughout.

## Configs (rule 15: one implementation, prior_fit.posterior_mode)

- **incumbent** — league anchor (fitted strength, whisper-past-3 fade,
  ruling-33 hot cap), calendar decay, full career.
- **noanchor** — Jeffreys 0.5/0.5 stabilizer only, full career, calendar
  decay. The realistic pricing candidate.
- **window** — noanchor + season window with Jan-1 bridge (full 44/44b),
  **with a league-mean fallback for coaches with no window chances.**
  DISCLOSURE: that fallback makes this a HYBRID, not the pure sheet
  formula — a sheet prints NO DATA = NO-BET, which has no pricing
  analogue. My pre-stated prediction (ruling 49) that this config would
  degrade from missing data was therefore testing something I had
  already patched around; the degradation it does show is real but the
  stated mechanism was wrong. On record per rule 42.

## Pooled forward folds (Liiga 970 cp / 201 games; Mestis 968 / 209)

| League | Config | Market | bias | Brier skill | ROI@10%EV | P(>0) |
|---|---|---|---|---|---|---|
| Liiga | incumbent | leaderTT | -0.004 | +0.092 | +9.9% | 0.896 |
| Liiga | noanchor | leaderTT | -0.009 | +0.088 | +9.3% | 0.878 |
| Liiga | window | leaderTT | -0.003 | +0.092 | +10.2% | 0.897 |
| Liiga | incumbent | total over | -0.006 | +0.104 | +9.9% | 0.948 |
| Liiga | noanchor | total over | -0.010 | +0.108 | +9.0% | 0.933 |
| Liiga | window | total over | -0.005 | +0.113 | +9.7% | 0.946 |
| Mestis | incumbent | leaderTT | +0.011 | +0.084 | +12.3% | 0.944 |
| Mestis | noanchor | leaderTT | +0.038 | +0.087 | **+18.7%** | 0.986 |
| Mestis | window | leaderTT | +0.022 | +0.073 | +15.1% | 0.967 |
| Mestis | incumbent | total over | -0.029 | +0.136 | +4.0% | 0.759 |
| Mestis | noanchor | total over | -0.001 | +0.149 | +8.8% | 0.914 |
| Mestis | window | total over | -0.018 | +0.133 | +5.9% | 0.832 |

## The trap, and the deciding test (rule 42)

Mestis/noanchor looks like a win: leaderTT ROI +12.3% -> +18.7%, P 0.944
-> 0.986. But its BIAS also moved +1.1pts -> +3.8pts — i.e. the model got
MORE CONSERVATIVE — while Brier skill barely moved (+0.084 -> +0.087).
That is exactly the mechanism named three hours earlier in ruling 45: at
the model's own +10%-EV line, conservative bias pays itself back and
*looks* like edge. Competing hypothesis, tested rather than narrated.

Deciding test = PAIRED game-clustered bootstrap on the Brier-skill
difference (same checkpoints, 1,500 resamples):

| League | Config vs incumbent | Market | skill diff | CI95 | P(better) |
|---|---|---|---|---|---|
| Liiga | noanchor | leaderTT | -0.0041 | [-0.017,+0.009] | 0.265 |
| Liiga | noanchor | total over | +0.0036 | [-0.012,+0.019] | 0.679 |
| Liiga | window | leaderTT | -0.0001 | [-0.011,+0.011] | 0.489 |
| Liiga | window | total over | +0.0091 | [-0.005,+0.022] | 0.908 |
| Mestis | noanchor | leaderTT | +0.0029 | [-0.014,+0.020] | 0.613 |
| Mestis | noanchor | total over | +0.0132 | [-0.008,+0.031] | 0.904 |
| Mestis | window | leaderTT | **-0.0114** | **[-0.021,-0.002]** | **0.011** |
| Mestis | window | total over | -0.0033 | [-0.014,+0.007] | 0.262 |

Every interval straddles zero EXCEPT ONE: the window config is
significantly WORSE on Mestis's flagship market. Nothing is significantly
better anywhere.

## VERDICT (Manager recommendation, Seb rules)

**Do not move the sheet estimator into pricing. Keep the split.** The
no-anchor candidate buys no measurable forecasting skill in either
league; its one attractive number is conservative bias in ROI clothing,
and the season-window variant actively costs skill where it is
measurable. The incumbent rulings-29-33 estimator stays in NHL/Liiga/
Mestis lines, backtests and the paper harness; ruling 44/44b stays
sheets-only. NHL was NOT re-run: with both interval leagues showing no
signal, spending the flagship's compute to chase a null is not
justified — say the word and it runs.

Design limits: 2 and 3 forward folds respectively (all that exist);
skill differences of this size need far more data to resolve; both
candidates were tested only on the corrected ledger, so this says
nothing about pre-ruling-45 behaviour. Production artifacts were
restored to incumbent byte-for-byte after the exams; the mode switch
defaults to incumbent and nothing shipped.
