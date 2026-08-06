# KHL scrape session — HANDOFF to Manager (final, 2026-08-06)

Session branch: **claude/khl-scrape-f5emx6** (environment renamed the
kickoff's `khl-scrape` at creation). Lake branch: **khl-data-lake**
(orphan, V2 repo, tip 4ed99df). Mission per docs/KICKOFF_KHL_SCRAPE.md:
lake + research only — COMPLETE. No adapter/model/ledger work done, none
attempted. My "done" below is a claim; Manager verifies per rule 0
(tools/verify_khl_lake.py re-runs anywhere; independent re-derivation
recommended as with Mestis).

## The lake

| Season | tid | game ids | Games | Payloads | Bytes |
|---|---|---|---|---|---|
| 2022-23 | 1154 | 881261..882008 | 748 | 1,496 | 0.93 GB |
| 2023-24 | 1217 | 885442..886223 | 782 | 1,564 | 1.04 GB |
| 2024-25 | 1288 | 889850..890631 | 782 | 1,564 | 1.10 GB |
| 2025-26 | 1369 | 897491..898238 | 748 | 1,496 | 1.07 GB |

Total 3,060 regular-season games × 2 artifacts (`<gid>_text.html` +
`<gid>_protocol.html`) + per-season `calendar_<tid>.html` (schedule
authority) + `manifest.csv` (sha256/bytes/url/utc/flag per file) +
lake-root `COMPLETENESS.md`. Fetched 2026-08-05/06 on Seb's PC
(tools/fetch_khl.py, 0.7 s delay, ~57 min/season, ZERO fetch failures).

## Verification (both PASS, lake-level only)

1. PC-side: verify_khl_lake.py, seed 20260805, 5 spots/season.
2. Cloud-side ON THE PUSHED BRANCH (this session, seed 20260806, 8
   spots/season, per-season sparse checkouts): scoped calendar id set ==
   disk set both directions (0 missing / 0 stray), ALL 6,124 files
   re-hashed against manifests (0 altered — transfer integrity through
   PC->GitHub->cloud), 0 truncation flags, spot-opens confirm structured
   broadcast events + coach blocks + protocol tables on real games.
   Size distributions tight (texts 596K-1.15M, protos 470-570K — no
   soft-404-sized outliers).

## What the channels give (full detail + verbatim vocabulary: docs/KHL_SOURCE.md)

- **text channel**: explicit goalie pull/return events with game clock
  (all 4 seasons, incl. multi-pull sequences and dp-driven pulls),
  explicit delayed-penalty events, penalty END events ("играет в полном
  составе"), coaches per game-side, per-player EN-TOI tables, ad-break/
  icing/offside lines. Goal lines carry NO time here.
- **protocol channel**: goals with period + cumulative clock + running
  score + strength (рав/бол/мен/буллит) + on-ice jersey lists BOTH teams
  (EN goals resolve via goalie absence), penalty table (time/player/min/
  offense). Coaches NOT on this page.

## Quirks the adapter must handle (recorded, NOT fixed — lake is verbatim)

1. Mixed clock semantics in text channel: play events = cumulative game
   clock; period/game boundaries = WALL clock (MSK).
2. Duplicate event lines exist (898094: same penalty twice at 51:57).
3. Goalie mid-game substitution is its own text class ("Замена вратаря.
   <Team>. <new> вместо <old>") — distinct from pulls, like Mestis vaihto.
4. Free-text commentary mentions goalies constantly — every count must
   scope to `div.textBroadcast-item` structured lines (ticker-lesson
   analogue, proven: a page-wide grep showed "15 pulls" where 3 are real).
5. Calendar pages embed a site-wide slider (other tournaments) + a
   4-game adjacent-tournament widget — scope by tid, never page-wide.
6. Season tid on the 2022-23 calendar URL is 1154 but a widget links tid
   1145 games (adjacent stage) — the scoped sets are clean.

## Environment/process notes for the Manager

- The cloud egress fence blocks ALL khl hosts AND WebFetch generally;
  every fetch ran on Seb's PC via paste-blocks (probe rounds 1-2, smoke,
  full fetch, lake push). Scripts: tools/probe_khl.ps1, probe2_khl.ps1,
  fetch_khl.py, verify_khl_lake.py, push_khl_lake.ps1.
- khl.ru fronts a cookie-challenge bot layer (307 + Set-Cookie): python
  urllib needs a CookieJar (fetch_khl.py has it); plain PowerShell IWR
  passes natively.
- **Transfer-alteration incident (resolved)**: Seb's git autocrlf ALTERED
  2 probe files in transit before `.gitattributes -text` was added (repo
  root, scrape branch; the lake branch got its own as its FIRST commit,
  before any payload). Manifest re-hash after transfer caught it — keep
  that gate standing for every future lake.
- PS 5.1 lessons baked into the scripts: ASCII-only (em-dashes break ANSI
  parsing), `${var}:` interpolation, ErrorActionPreference 'Continue' +
  explicit $LASTEXITCODE asserts (git writes progress to stderr).
- `C:\dev\HOCKEYPROJECTS_V2` on Seb's PC exists but is NOT a git repo
  (contains only data/ + data_samples/) — the working clone is
  **C:\dev\HOCKEYPROJECTS_V2_scrape**; local lake copies at
  C:\dev\khl_lake (raw) and C:\dev\khl_lake_repo (push clone).

## Open questions for Seb / Manager

1. docs/MESTIS_SOURCE.md is referenced by the KHL kickoff but does not
   exist on master (likely never merged from mestis-scrape). Cosmetic,
   but the next kickoff template should point at files that exist.
2. Market note stands (no icehockey_khl at the odds provider): lake
   serves coach intel + model-side lines (ruling 5) — Seb ordered with
   this heard, re-recorded here.
3. Live-feed channel for the paper harness (online.khl.ru / webcaster
   video API with khl_id linkage) was mapped but NOT built — September
   shakedown scope, Manager's call.
4. STATUS row in CLAUDE.md: Manager updates on merge (scrape session
   does not touch master).

## Superseded history (blocks 1-3, 2026-08-05)

Earlier states of this doc tracked discovery in progress; the full
discovery record (reachability matrix, candidate elimination, probe
evidence, capability table with named games, sizing math) lives in
docs/KHL_SOURCE.md and the probe raw files in tests/reference_raw/
khl_probe*/ on this branch.
