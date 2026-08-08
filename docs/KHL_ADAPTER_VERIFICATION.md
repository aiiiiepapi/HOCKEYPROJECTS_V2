# KHL adapter — Manager verification & merge (2026-08-08)

Branch `claude/khl-adapter-setup-gd4nhx` (tip d44a656f) re-derived per rule 0
before merge. The session's handoff (docs/HANDOFF_KHL_ADAPTER.md) is a CLAIM
set; this file records what the Manager independently reproduced, what was
adjudicated, and what changed.

## Independently reproduced (full 4.14 GB lake, fresh Manager clone)

| Claim | Manager result |
|---|---|
| 3,060 games / 0 parse errors | REPRODUCED exactly |
| 1,223 instances (268/324/304/327) | REPRODUCED exactly, per season |
| 136 pulled = 74 EV + 62 pp | REPRODUCED exactly |
| 100.0% coach attribution, no map | REPRODUCED (runner aborts on any miss) |
| 42 dp_only_empty, 1,571 dp events | REPRODUCED exactly |
| GT 14 games / 16 instances | Gate re-run green on a clean checkout |
| Random audit 0 disagreements | REPRODUCED on their seed AND on a FRESH
  Manager seed 20260809 (30+30, 0/60) — dual-channel incl. per-period ВППВ
  second-exact equality |
| Full suite | 32 green with the lake mounted (their env skipped 3) |

## Adjudications (the five open items)

1. **Dedupe REFUTED — RATIFIED.** The scrape-round instruction to dedupe
   898094's 51:57 pair was WRONG; the Manager re-read the protocol bytes
   independently: two separate `24. Бреус Дмитрий / 2 / Игра высоко
   поднятой клюшкой` rows at 51:57, and the period penalty-minute total
   moves by 4. A real 2+2. The adapter keeps both rows (stacked windows).
   Kickoff line superseded; this doc is the authority.
2. **Coach patronymic identity — RULED: canonicalize in the RUNNER.**
   2025+ pages add patronymics, splitting 24 coaches across the season
   boundary (Никитин Игорь vs Никитин Игорь Валерьевич). Census: ZERO
   two-token collisions between distinct people in 3,060 games, so the
   key "Surname Firstname" is loss-free. Implemented as `_canon()` in
   run_khl_lake.py; the adapter keeps emitting verbatim (identity fixes
   live in the runner — SHL Lindholm/Lindbom precedent). Effect: 64
   coach identities instead of 88 fragments; cross-season records join.
3. **Clock-wins rule (886068) — RATIFIED.** Same convention as SHL
   774455; protocol goal periods stay strictly checked.
4. **dp census reading — see cross-calibration below. Rulings 17/17b
   UNCHANGED.**
5. **Lake path env override — ACCEPTED** (KHL_LAKE, session homes differ).

## Rulings 17/17b cross-calibration (the kickoff's purpose)

KHL is the only interval league with EXPLICIT delayed-penalty events, so its
438 dp-linked net-empty windows are the portfolio's first direct dp truth.
The session reported "18.8% of dp windows exceed ruling 17's 25s bar vs NHL's
8.7%" — read alone that reads like the convention is too tight. It is not.
Decomposed by the clause that would actually fire:

- 409 dp windows end at the offender's whistle; median 12s.
- 77 (18.8%) exceed 25s — but **69 of those start EARLY (before P3 12:00),
  where ruling 17b-i already classifies them as dp regardless of duration.**
- Only **8 (2.0%)** are both >25s AND late — the one class our convention
  currently counts as a REAL pull.

Exposure in the shipped ledgers (late leader-whistle-ended segments >25s
currently counted as real EV pulls): AHL 7/272 (2.6%), Liiga 2/72 (2.8%),
Mestis 1/82 (1.2%), SHL 1/28 (3.6%) — **11 instances portfolio-wide, max
2-4% of any league's EV pulls, and that is an upper bound (each is only
*possibly* dp).** The KHL truth says ~2% of dp windows would land there.

VERDICT: rulings 17/17b are VALIDATED by direct dp evidence — no change.
The CLAUDE.md standing limitation ("~2-4 possible dp residue, unresolvable
without possession data") is now QUANTIFIED rather than merely suspected.
Design limits (rule 42): the KHL dp channel is PARTIAL (0/193/647/731 by
season — 2023 absent), the bracket linkage is heuristic, and a 90s link
window can co-opt a genuine adjacent pull. Those all bias toward
over-counting dp, which makes the 2.0% an upper bound too.

## Ledger (Manager scope, built post-merge)

1,223 instances -> **186 clear chances, clear-chance take rate 39.8%**,
64 coaches, prior mu 0.40 / S 2.0. Composition-controlled portfolio table
(ruling-45 baseline, so these ARE comparable):

| League | instances | clear | take rate | pp share of pulls |
|---|---|---|---|---|
| AHL | 2,313 | 407 | 66.8% | 31.1% |
| Mestis | 617 | 129 | 63.6% | 28.1% |
| Magnus | 147 | 23 | 60.9% | 17.6% |
| Liiga | 653 | 131 | 55.0% | 25.8% |
| **KHL** | **1,223** | **186** | **39.8%** | **45.6%** |
| SHL | 681 | 122 | 23.0% | 30.0% |

The session's raw pp-share flag survives composition control: **KHL's 45.6%
pp share is the highest in the portfolio** (next is AHL at 31.1%), and its
clean-chance take rate sits well below the western-European leagues. KHL
coaches pull, but they disproportionately wait for a power play to do it.

Morning sheet delivered (35 active benches; Буше 92% 7/7, Люзенков 86% 3/3,
Гатиятулин 85% 3/3 — all HOT FORM). NO pricer, NO lines: there is no
icehockey_khl market at our provider (ruling 5 model-side doctrine) and no
blind validation exists. COACH INTEL ONLY.
