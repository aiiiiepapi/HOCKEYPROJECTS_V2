# SHL scrape session — handoff to Manager (2026-08-06)

Scope was lake + research only (kickoff docs/KICKOFF_SHL_SCRAPE.md). No
adapters, no models, no bet-relevant conclusions in this session. Per rule 0
everything below is a CLAIM until the Manager re-derives it.

## What exists now

- **Lake branch `shl-data-lake`** (V2 repo, orphan, Mestis convention):
  `shl/<END_YEAR>/` for 2023..2026 + root COMPLETENESS.md + `.gitattributes
  * -text`. **Authoritative tip: `6b77add`** (root 03d8547 had the CRLF
  normalization — see 1b — never read lake bytes from it).
  VERIFIED TWICE with hard-fails 0: on Seb's PC against staging
  (2026-08-06), and cloud-side on the transferred branch content
  (manifest re-hash 5,104/5,104 after PC→GitHub→cloud round trip).
- **Session branch `claude/shl-scrape-ly11nk`** (== the kickoff's
  `shl-scrape`; the cloud harness fixed this name and forbade renaming):
  docs/SHL_SOURCE.md, tools/fetch_shl.py, tools/verify_shl_lake.py,
  tools/probes/shl_probe{1,2}.ps1, data_samples/shl_probe{1,2}/ (raw
  discovery samples, byte-verified).

## Per-season counts (fetch summary 2026-08-06, errors: 0)

| Season | dir | swe events | swe lineups | shl pbp | shl boxscore | manifest files |
|---|---|---|---|---|---|---|
| 2022-23 | 2023 | 364 | 364 | 0 (source-absent) | 0 | 730 |
| 2023-24 | 2024 | 364 | 364 | 364 | 364 | 1458 |
| 2024-25 | 2025 | 364 | 364 | 364 | 364 | 1458 |
| 2025-26 | 2026 | 364 | 364 | 364 | 364 | 1458 |

Verification (verify_shl_lake.py, seed 20260806): all manifests re-hash
clean, 0 stray / 0 missing / 0 truncated, both-direction reconciliation
clean all seasons, every artifact self-identifies, scoped spot-opens 32/32
(goal rows == header score; OT variant tolerance used once, 2026/1004357),
cross-channel GK audit clean 2025+2026 samples, 2 disagreements in the
2024 sample (below).

## Sources (full detail: docs/SHL_SOURCE.md)

- **stats.swehockey.se (federation) = schedule authority + primary events.**
  Series ids: 2023=13469, 2024=14677, 2025=15977, 2026=18263 — verified by
  content (title 'SHL', season label, 364 games, date ranges), NOT by the
  season dropdown, which for historical seasons points at Play Out series
  (14296/15791/17556 — the google-title conflict was real; ruling-42 win).
  Per game: `/Game/Events/{id}` (GK In/Out with cumulative clock incl.
  62:05-style OT times, ENG flag on EN goals, penalties with EXPLICIT
  begin-end windows, strength + on-ice jersey lists per goal; rows
  newest-first) and `/Game/LineUps/{id}` (Head Coach + assistants per team,
  referees, lines). `/Game/Reports/{id}` lists 5 official PDFs per game —
  NOT fetched (open question 3).
- **www.shl.se site API (open, no auth).** `/api/sports-v2/game-schedule`
  (uuid map, OT/SO flags, roundNumber current season only),
  `/api/sports-v2/season-series-game-types-filter` (season uuids back to
  1975-76), `/api/gameday/play-by-play/{uuid}` (shot-level pbp incl.
  goalkeeper in/out events, per-period clock, realWorldTime),
  `/api/gameday/boxscore/{uuid}`. **Gameday archive starts 2023-24**
  (2022-23 returns 0 bytes — measured on 3 probe games, stage 1.5).
  Full route constants extracted from the JS bundle are in
  data_samples/shl_probe2/shl_bundle.js (SPORTS_v2 + GAME_DAY tables).
- **api.shl.se / doc.openapi.shl.se (official OAuth API): DEAD** — 522 from
  origin, 2026-08-05. Path closed, nothing to authenticate against.
- **statistik.swehockey.se: NXDOMAIN** (old host retired). Cloud note: ALL
  Swedish hosts block the cloud workspace (proxy AND WebFetch) — every
  byte of this lake came through Seb's PC (C:\dev\HP_V2 relay clone).

## Capability table (bar from MAGNUS_DATA_GAPS; all rows sample-verified)

| Capability | Status | Verified on |
|---|---|---|
| Goalie in/out with times | YES x2 channels: swe GK rows (cumulative clock) + shl pbp goalkeeper events (2024+) | 1004308, 1004311 (OT), pbp bdhvuc5tex |
| EN identification | YES: ENG flag on goals + GK-window cross-check | 1004308 |
| Penalty windows | YES: explicit begin-end incl. early PP-goal termination (better than AHL) | 1004308, 754666, 875738, 991873 |
| Strength/gap context | YES: (EQ/PPn/SHn) + on-ice jersey lists per goal | 1004308 |
| Coach per game | YES on LineUps, both sides, all 4 seasons — 2,891/2,912 sides = 99.3% | 1004308, 754666 + full census |
| Event timeline | swe: goals/pens/GK/timeouts (shots as totals); shl pbp: shot-level (2024+) | above |
| Schedule authority | swe per-season Schedule page, reconciled 1:1 both directions, + shl.se schedule JSON joined 364/364 all seasons | stage-1 gates |

## Known issues / adapter watch-items (recorded, not fixed — lake is raw)

1. **21 blank coach sides** (7/9/2/3 by season) — AHL/Mestis-class gap
   (99.3% vs Mestis 99.2%). Extracted from the lake (position-based side
   attribution, verified count == census 21/21, 0 parse fails).
   **HV71 accounts for 8 of 21** — club-level reporting habit, so the
   hand-curation map is cheap. Full list (season, gameId, missing side):

   | season | gameId | game | missing |
   |---|---|---|---|
   | 2023 | 628989 | IKO-FRÖ | BOTH |
   | 2023 | 629252 | HV71-BIF | AWAY BIF |
   | 2023 | 629299 | LHF-HV71 | AWAY HV71 |
   | 2023 | 629306 | TIK-HV71 | AWAY HV71 |
   | 2023 | 629318 | HV71-TIK | HOME HV71 |
   | 2023 | 629325 | HV71-MIF | HOME HV71 |
   | 2024 | 774473 | RBK-LHF | AWAY LHF |
   | 2024 | 774528 | HV71-SKE | HOME HV71 |
   | 2024 | 774534 | HV71-MoDo | HOME HV71 |
   | 2024 | 774548 | SKE-VÄX | AWAY VÄX |
   | 2024 | 774556 | RBK-HV71 | AWAY HV71 |
   | 2024 | 774615 | MIF-IKO | BOTH |
   | 2024 | 774783 | LIF-HV71 | AWAY HV71 |
   | 2024 | 774804 | SKE-ÖHK | AWAY ÖHK |
   | 2025 | 882211 | LIF-BIF | AWAY BIF |
   | 2025 | 882278 | MIF-BIF | AWAY BIF |
   | 2026 | 1004650 | VÄX-TIK | AWAY TIK |
   | 2026 | 1004675 | LHC-DIF | HOME LHC |
   | 2026 | 1004741 | TIK-FRÖ | AWAY FRÖ |

1b. **CRLF incident (caught & repaired)**: the first lake push stored
   CRLF→LF-normalized text (Seb's PC git autocrlf; 2,916 html files) —
   detected by the cloud-side manifest re-hash (exact CRLF-restore
   reproduced manifest hashes bit-for-bit), repaired by recommitting from
   staging with `.gitattributes * -text` at the lake branch root.
   STANDING RULE for all future lake branches (KHL, Allsvenskan):
   `.gitattributes * -text` FIRST, and always re-hash after transfer.
2. **GK channel disagreements**: 2024/774444 (swe 8 vs pbp 10 events),
   2024/775029 (swe 8 vs pbp 6) in the 24-game sample. Channels are
   independent recorders; first hypothesis = convention differences
   (mid-game swaps / end-of-game bookkeeping rows). Adjudicate before the
   adapter trusts either count blindly.
3. Events-page parser notes: rows NEWEST-FIRST; 00:00 'GK In' = starters;
   60:00 (or OT-end) 'GK Out' pairs = end-of-game bookkeeping, NOT pulls;
   Swedish decimal commas; away team names render SHORT on some schedule
   rows (join on home side / norm_team()).
4. Shootout games: goal-row count may differ from header by 1 (GWS
   winner variant — tolerated in verifier; adapter must handle).
5. shl.se pbp penalties are begin+minutes only; swe begin-end windows are
   the better penalty channel. pbp clock is PER-PERIOD; swe is cumulative.

## Open questions for Manager/Seb

1. Reports PDFs (5 per game, incl. OfficialGameReport): skipped — HTML/JSON
   covers every capability row; fetch later if adjudication wants them.
2. Delayed-penalty visibility: no dp events observed in any sample; treat
   like Liiga's thin channel until an adapter-side measurement says more.
3. 2022-23 has no shl.se pbp (source-absent). Fine for gap work (swe
   channel is complete); noted for any shot-level analysis.
4. Allsvenskan follow-up: same pipeline verbatim — swehockey series ids
   from the same dropdown mechanism, hockeyallsvenskan.se is the same
   platform (qcz- uuids seen), odds market confirmed in catalog.

## PC relay channel (standing)

- Clone: `C:\dev\HP_V2`, branch claude/shl-scrape-ly11nk. Approved as this
  session's push channel (Manager 2026-08-05); KHL session gets its OWN clone.
- **Token rotation fix** (pushes start failing with 'Invalid username or
  token'): regenerate the V2 fine-grained token, then:
  `git -C C:\dev\HP_V2 remote set-url origin https://x-access-token:<NEWTOKEN>@github.com/aiiiiepapi/HOCKEYPROJECTS_V2.git`
  (One mangled-paste false alarm happened 2026-08-05 — same command fixed it.)
- Lake staging stays at `C:\dev\HP_V2\shl_lake_staging\` until Manager
  accepts the branch; re-running fetch_shl.py resumes/repairs idempotently.
