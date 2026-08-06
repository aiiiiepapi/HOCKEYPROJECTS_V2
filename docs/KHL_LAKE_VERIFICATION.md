# KHL lake — Manager rule-0 verification (2026-08-07)

Independent verification of lake branch `khl-data-lake` tip `4ed99df`.
Verifier re-derived from raw files (/root/verify_khl_independent.py
logic), NOT the session's tools/verify_khl_lake.py. Own seed 20260807.

## PASS — structural layer (all 4 seasons)

| Season | Calendar-scoped ids | Games on disk | id range | sha256 re-hash |
|---|---|---|---|---|
| 2023 | 748 | 748 | 881261..882008 exact | 1497/1497 |
| 2024 | 782 | 782 | 885442..886223 exact | 1565/1565 |
| 2025 | 782 | 782 | 889850..890631 exact | 1565/1565 |
| 2026 | 748 | 748 | 897491..898238 exact | 1497/1497 |

- Calendar reconciliation re-derived with tid-scoped extraction (quirk-5
  slider/widget contamination avoided): 0 missing / 0 extra both
  directions, every season. TOTAL 6,124/6,124 hashes bit-exact —
  transfer integrity confirmed through PC→GitHub→cloud.
- Artifact pairs (text + protocol) complete on every game, 0 strays,
  no suspicious sizes in my samples, strength labels present on every
  sampled protocol.

## Coach census — 100.0%, upgraded from the handoff's sample claim

Full census across all 3,060 text pages (regex: game-coach «Тренер»
rows with Cyrillic full names, nav «Тренеры» excluded):
**3,060/3,060 games carry BOTH coach rows** (748/782/782/748).
Best coach coverage in the portfolio (SHL 99.3%, Mestis 99.2%, AHL 96%).
NO hand-curation map needed. Named-game sanity: 898094 = Кравец/
Десятков, 881261 = Фёдоров/Воробьёв — matches the source doc.
(Manager's first spot-check produced 0-2/6 coach hits — that was MY
regex scoped to broadcast items while coach rows live in the
preview-frame; checked per rule 42 before concluding. Recorded.)

## Content spot-checks (seed 20260807, 6 games/season)

Goalie-related structured events present in 24/24 sampled games;
delayed-penalty mentions in 2025/2026 samples (channel exists; density
measurement = adapter work). Duplicate-line quirk (898094 51:57) and
mixed clock semantics accepted as recorded feed quirks — adapter
handles, lake stays verbatim.

## Notable capability (flag for the adapter/engine stage)

The text channel carries EXPLICIT delayed-penalty events — no other
interval league has this (rulings 17/17b exist precisely because
AHL/Mestis dp truth is invisible). If the density holds up at adapter
time, KHL becomes the first interval league where dp artifacts are
directly observable rather than convention-ruled — and a potential
CALIBRATION source for the 17/17b clauses themselves.

## Housekeeping fixed with this commit

docs/MESTIS_SOURCE.md + docs/HANDOFF_MESTIS.md copied to master from
the mestis-scrape branch (the KHL kickoff referenced a file that only
lived on a side branch — handoff open question 1).

## Verdict

Lake ACCEPTED as raw-data authority for KHL. All handoff claims
verified; the coach claim UPGRADED by full census (sample-verified ->
100.0% measured). Second consecutive lake with zero corrections.
Biggest lake in the portfolio (3,060 games, 4.14 GB). Market note
stands (no KHL odds market at our provider — coach intel + model-side
lines per ruling 5). Adapter not started; Russian-vocabulary event
parsing is the main new build cost. Live-feed channel = September
shakedown scope, Manager's call at that time.
