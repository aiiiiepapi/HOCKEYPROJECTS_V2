# SHL lake — Manager rule-0 verification (2026-08-06)

Independent verification of lake branch `shl-data-lake` tip `6b77add`
(never read root 03d8547 — pre-CRLF-repair). Verifier re-derived from raw
files (/root/verify_shl_independent.py logic), NOT the session's
tools/verify_shl_lake.py.

## PASS — structural layer (all 4 seasons)

| Season | Federation schedule | Games on disk | Artifacts | sha256 re-hash | GK-row games | Coach sides |
|---|---|---|---|---|---|---|
| 2023 | 364 | 364 | 2/2 all | 730/730 | 364/364 | 721/728 |
| 2024 | 364 | 364 | 4/4 all | 1458/1458 | 364/364 | 719/728 |
| 2025 | 364 | 364 | 4/4 all | 1458/1458 | 364/364 | 726/728 |
| 2026 | 364 | 364 | 4/4 all | 1458/1458 | 364/364 | 725/728 |

- Schedule reconciliation: game ids independently re-extracted from the
  federation Schedule pages in the lake; 0 missing / 0 extra both
  directions, every season. TOTAL 5,104/5,104 hashes bit-exact — the
  CRLF repair is confirmed genuine.
- Ticker check: 0 foreign /Game/Events/{id} links inside any of the
  1,456 events pages — single-game server-rendered confirmed; the
  Mestis contamination mode does not exist on this source.
- Coach census reproduces the handoff EXACTLY: same 19 games, same 21
  blank sides (7/9/2/3 by season), 2,891/2,912 = 99.3%. Hand-curation
  map is the adapter-stage fix (HV71 habit = 8 of 21).
- ENG-flag games per season (scoped): 102/89/105/98 — plausible density,
  recorded as the pre-adapter baseline (rule 42: number on record before
  any extraction exists to be compared against).

## Adjudication 1: the two GK-channel "disagreements" — RESOLVED, no defect

Hand-traced both channels of both games:

- **2024/774444** (HV71-FBK): swe 8 rows vs pbp 10. The pbp extras are
  same-second DUPLICATE rows with differing `revision` numbers (two at
  P3 17:55, two at 18:16) — live-feed corrections. Every pull-relevant
  moment matches to the second across channels (57:44 Out / 57:55 In /
  58:16 Out / 59:13 In / 60:00 x2 end-of-game).
- **2024/775029** (LIF-MODO): swe 8 vs pbp 6. The pbp is MISSING only
  the two 60:00 end-of-game bookkeeping rows (present in 774444 —
  optional in the feed). All real moments match exactly
  (55:03 / 57:40 / 57:58 / 58:14).

**Adapter rules derived (binding when the SHL adapter is built):**
(1) swe Events channel = PRIMARY (complete all 4 seasons, cumulative
clock, internally consistent); shl pbp = independent AUDIT channel
(2024+), Mestis events-vs-pois pattern. (2) pbp goalkeeper events must
be deduped by (period, time, team) keeping the latest revision.
(3) 60:00 / OT-end "GK Out" rows are bookkeeping, never pulls, and their
absence in pbp is uninformative.

## Adjudication 2: Reports PDFs — SKIP ratified

The 5 per-game official PDFs stay unfetched: every capability row is
covered by the HTML/JSON channels, and PDFs are fetchable on demand if a
future adjudication wants a specific game's official sheet. No bulk value.

## Verdict

Lake ACCEPTED as raw-data authority for SHL. Handoff claims verified
without exception — first lake to reproduce 100% of its claimed numbers
under independent re-derivation (Mestis needed two corrections).
Capability class: Liiga-plus (explicit penalty begin-end, dual GK
channels, on-ice lists) — the richest non-NHL source in the portfolio.
Standing rule adopted from the CRLF incident: every future lake branch
starts with `.gitattributes * -text`, and manifests are re-hashed after
every transfer (KHL session must be told).
Adapter not started (Manager work, sequenced with Magnus/KHL per queue).
