# HANDOFF — Mestis raw data lake (Scraping session → Manager, 2026-08-03)

Scope fence honored: LAKE + RESEARCH ONLY. No adapter, no model, no
ledger, no bet-relevant conclusions in this session.

## What exists now

**Lake**: branch `mestis-data-lake` on **HOCKEYPROJECTS_V2** (deviation:
the V2 write token cannot even read the v1 HOCKEYPROJECTS repo — 403;
Seb ruled "you do it" → pushed where the token works; move it if the
v1-repo convention matters). Commit 5c57304, ~59 MB packed / 432 MB raw.

Layout `mestis/<END_YEAR>/`, per game FOUR verbatim artifacts:
`game_{y}_{n}_kokoonpanot.html`, `..._seuranta.html`, `..._tilastot.html`
(mestis.fi) + `..._rosters.json` (tilastopalvelu). Per season:
`schedule_{y}.ics` (official schedule = reconciliation authority),
`schedule_page_{y}.html`, `statgroups_{y}.json`, `manifest_{y}.json`
(sha256/bytes/url/utc for every file), plus lake-root `COMPLETENESS.md`.

| Season | Games | goalie-out ev. | pois-intervals | rosters (w/ HC) |
|---|---|---|---|---|
| 2022-23 | 364 | 303 | 226 | 364 (364) |
| 2023-24 | 312 | 242 | 186 | 312 (312) |
| 2024-25 | 245 | 185 | 155 | 245 (245) |
| 2025-26 | 245 | 205 | 179 | 245 (245) |

**Verification done (lake-level)**: 0 missing vs ICS both directions,
0 stray files, 0 truncated HTML, sha256 manifests re-verified after the
PC→cloud transfer (bit-identical), 5 seeded-random spot-opens
(seed 20260803: 2023/7362, 2024/3892, 2025/3191, 2026/3170, 2023/7425)
all carrying the claimed capability rows. Verifier: 4/4 seasons PASS
(`tools/verify_mestis_lake.py`, report in the lake's COMPLETENESS.md).

**Tools on branch `mestis-scrape`**: `tools/fetch_mestis.py` (stdlib,
fetch-only, resume-safe, PC-side — cloud is proxy-403 on mestis.fi,
verified), `tools/verify_mestis_lake.py`, `tools/FETCH_MESTIS.bat`,
`tools/probe_tilastopalvelu.py` (v7, historical — the probe series that
found the coach source). Docs: `docs/MESTIS_SOURCE.md` (the full source
contract — READ IT FIRST).

## Capability table result (vs MAGNUS_DATA_GAPS bar)

- Goalie in/out: **explicit events with times** ("Maalivahti ulos/
  sisään") PLUS goalie stat-line off-ice intervals ("pois: 57:59-58:04,
  58:32-59:56") — redundant channels, multi-pull windows separable.
  AHL-class or better; no Magnus-style inference needed.
- EN: TM flag on goals, cross-checkable vs pull intervals. IM flag =
  goal scored with own net empty. SR flag = delayed-penalty goal
  (partial dp visibility). Full legend decoded in MESTIS_SOURCE.md.
- Penalties: begin time + minutes + offense text (NO end events) →
  AHL-style strength reconstruction, misconduct exclusion applies.
- **Coach: game-level Head Coach per team in every rosters.json
  (Vastuuvalmentaja in Home/AwayTeamGameRoster.Staff), 1,166/1,166.**
  Serie rosters may list multiple HCs per season (TUTO 2024-25:
  MARJETA + VIRTANEN) — always attribute from the GAME roster.
- No faceoff/stoppage timeline; no live feed identified (mestis.fi
  seuranta presumably live-updates in season — a Sept shakedown item
  if Mestis joins the paper harness).

## Quirks the adapter must know

1. Match numbers are unique only within season+series (2965 exists in
   two seasons); key everything (season, matchno). ICS UID carries a
   distinct internal id (`Mestis-Runkosarja-2024-game-95010@mestis.fi`).
2. Every seuranta page embeds the flag LEGEND — never grep flags
   page-wide, read goal rows.
3. OT/SO games: durations 65:00 etc.; shootout winner listed at 65:00
   with VL. Never assume 3600s.
4. tilastopalvelu quirks: bare domain only, legacy-TLS context required
   (self-signed chain, old ciphers; www host dead); "season" = END
   year; referees.php shows double-encoded UTF-8 (rosters.json spot-
   checks looked clean — verify encoding when parsing names).
5. Mid-game goalie swaps ride the same event channel as pulls
   (e.g. 2023/3000: swap at 24:33) — classification is adapter logic.
6. 2022-23 team dropdown on mestis.fi showed 15 names for a 14-team
   schedule (364 = 14x52/2); one listed team (HK Zemgale?) likely
   never played runkosarja — resolve from the lake when building team
   tables, not from the dropdown.
7. One transient 502 during the whole fetch (2024/3864 kokoonpanot),
   retried clean — no residue.

## Open questions for Manager

1. Lake branch lives on V2 repo (token scope) — move to v1 repo or
   amend the convention?
2. Volume check vs MAGNUS doc expectations: Mestis gives 245-364
   games/season (shrinking league), i.e. Liiga-class instance counts
   at best. Portfolio implications are Manager territory.
3. Flag semantics beyond the legend (e.g. TV "tasavajaa") — decode from
   lake samples during adapter work.
4. If richer event data is ever needed: tilastopalvelu endpoint
   inventory in MESTIS_SOURCE.md §1.2 (getGames/getStandings/
   getGoalkeepers/dwl* CSVs...) is mapped and working PC-side; the
   gamecentre report endpoint (getgamereportdata.php) was never
   located — not needed for the current bar.

## Session log pointers

Branch `mestis-scrape` commits: discovery+fetcher (84769fd), probe
series v2-v7 (195173b..b3a112a), coach-gap closure + fetcher v2
(b4bac60), verifier pois fix (2d014dd). Lake: 5c57304 on
`mestis-data-lake`.
