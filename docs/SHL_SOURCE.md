# SHL — data source documentation (Scraping session, started 2026-08-05)

Status: **DISCOVERY ROUND 1 COMPLETE (probe 1 fetched on PC 2026-08-05).**
Claims below cite the fetched sample that verifies them; anything not yet
sample-verified is marked TBD.
Session branch: `claude/shl-scrape-ly11nk` (the cloud harness maps the
kickoff's `shl-scrape` branch name to this; Manager note in HANDOFF).
PC push channel: `C:\dev\HP_V2` clone on this branch (Seb-approved,
2026-08-05; separate clone per session, never shared).

## Probe 1 headline results (all verified on fetched files)

1. **shl.se has an OPEN JSON schedule API** (no auth):
   `GET https://www.shl.se/api/sports-v2/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B`
   → 429,484 B JSON: `gameInfo[364]` (uuid, rawStartDateTime UTC, state,
   overtime/shootout bools, home/away code+score, venue, roundNumber
   1-52, seriesInfo SHL), `teamList[14]`, `ssgtUuid`. Season resolved
   from content: **xs4m9qupsi = 2025-26** (2025-09-13 → 2026-03-14, all
   364 post-game, every team exactly 52 games — 14×52 bar VERIFIED for
   25-26). Other seasons' uuids NOT in page payload (runtime API) —
   probe 2 target: `/assets/index-RNjyxFdd.js` (single Vite bundle, all
   routes). Naive guesses 404: /api/sports-v2/seasons, /api/site-settings.
2. **stats.swehockey.se serves everything server-rendered, no auth**:
   series **18263 = SHL 2025-26**; Schedule page (459,991 B) lists all
   364 games with date/time/teams/result+periods/spectators/venue and
   exactly one `/Game/Events/{gameId}` link per game (ids 1004308-1004853,
   unique 364). Cross-source: both sources open the season 2025-09-13. ✔
3. **Game Events sheet = capability WIN** (verified on fetched game
   **1004308**, Brynäs IF - Växjö Lakers 4-7, 2025-09-13):
   see capability table below.
4. **api.shl.se / doc.openapi.shl.se: DEAD** — both 522 (Cloudflare,
   origin down) from Seb's PC 2026-08-05. Official Open API path CLOSED
   (nothing to authenticate against; no scraping around auth needed).
5. **statistik.swehockey.se: NXDOMAIN** from both cloud and Seb's PC —
   old host retired. `historical.stats.swehockey.se` exists (933 B
   redirect/stub fetched; role TBD).

## Environment facts (verified 2026-08-05)

- **Cloud → ALL Swedish hosts: BLOCKED.** curl/Python via the session
  proxy: `CONNECT tunnel failed, 403` on www.shl.se, shl.se, api.shl.se,
  statistik.swehockey.se, stats.swehockey.se, www.swehockey.se. The
  cloud WebFetch channel (which worked for mestis.fi discovery) gets
  HTTP 403 from shl.se and stats.swehockey.se as well (site-side WAF /
  geo-block), and web.archive.org is not fetchable from the session.
  → **Discovery samples AND the lake both come from Seb's PC** (probe
  pack pattern, like Mestis probes v1-v7). This is a harder block than
  Mestis had (there, WebFetch could sample the site).
- **statistik.swehockey.se (the old federation host) is GONE from DNS**
  (ENOTFOUND from two independent resolvers: cloud session + WebFetch).
  The live service is **stats.swehockey.se**; an archive host
  **historical.stats.swehockey.se** also exists (search-indexed).
  PC probe re-checks DNS from Sweden-side network to confirm.

## 1. Source inventory (pre-probe knowledge — search-indexed only)

### 1.1 stats.swehockey.se (Swedish federation stats service)

URL scheme (from search-indexed pages + the swehockey-scraper package
docs on PyPI; NOT yet verified on our own fetched sample):

| Page | URL |
|---|---|
| Series schedule/results | `https://stats.swehockey.se/ScheduleAndResults/Schedule/{seriesId}` |
| Series overview / live / standings | `.../ScheduleAndResults/{Overview|Live|Standings}/{seriesId}` |
| Game event sheet | `https://stats.swehockey.se/Game/Events/{gameId}` |
| Game lineups | `https://stats.swehockey.se/Game/LineUps/{gameId}` |
| Games by date | `https://stats.swehockey.se/GamesByDate` |

- `seriesId` identifies (competition, season) — one id per SHL season.
  Candidate observed in search results: 18263 (recent SHL; season TBD by
  probe). Old Elitserien ids (9024, 9146, 13469, 14677) confirm the
  service reaches back years; 2022-23..2025-26 expected on the main host.
- `gameId` is a site-global numeric id (search-observed examples:
  252961, 291719 — competition/season unknown).
- Event sheet content per the scraper package docs: goals, penalties,
  shot statistics. **Goalie in/out, EN flags, penalty end times, coaches:
  UNKNOWN until probe 1 returns a real Events page.** (v1 had no Sweden
  research folder to consult — Mestis precedent: discovery from scratch.)
- Expected quirks (tilastopalvelu lesson): possible legacy TLS/host
  issues; probe uses default modern TLS first and records failures.

### 1.2 shl.se (league site — likely the richer event source)

- JS app (same platform family as hockeyallsvenskan.se — shared
  `qcz-`-style uuid scheme seen in both sites' URLs). Schedule page URL
  (search-indexed, live as of 2026):
  `https://www.shl.se/game-schedule?seasonUuid=xs4m9qupsi&seriesUuid=qQ9-bb0bzEWUk&gameTypeUuid=qQ9-af37Ti40B&completeSeason=all&homeAway=all&allGames=all`
  → `seriesUuid=qQ9-bb0bzEWUk` = SHL; `gameTypeUuid=qQ9-af37Ti40B` =
  (probably) regular season; `seasonUuid=xs4m9qupsi` = a season (which
  one TBD). Stats pages use `ssgtUuid` (season+series+gametype combo id).
- The page loads JSON from `/api/...` endpoints (exact paths unknown —
  probe 1 extracts every `/api/` reference from the served HTML and
  auto-fetches the first 12, plus a game page's endpoints if a game link
  is present).
- Game-page event depth (pbp with goalie events? EN flags? coaches):
  UNKNOWN until probe.

### 1.3 api.shl.se (official SHL Open API, OAuth)

- Historically OAuth2 client-credentials (doc.openapi.shl.se). Community
  wrappers exist (nuget Shl.OpenApi, various node wrappers) — content
  historically: standings/games/articles, NOT event-level pbp.
- Cloud cannot reach the doc host (403). Probe 1 fetches the doc page
  and API root from the PC. **If credentials cannot be obtained, this
  path is documented and STOPPED — no scraping around auth** (kickoff
  hard rule). It is likely unnecessary if 1.1/1.2 deliver events.

## 2. Coverage target (to verify, not assume)

- Last 4 completed seasons, regular season only: 2022-23 .. 2025-26,
  lake dirs by END year 2023..2026 (Liiga/Mestis convention).
- SHL nominal: 14 teams × 52 rounds = 364 games/season. VERIFY per
  season from the schedule authority (team churn: Timrå/Modo relegation
  swaps etc. don't change N=14 since 2015, but verify anyway).
- Schedule authority: TBD after probe — candidates: (a) federation
  series schedule page per season (stats.swehockey.se), (b) shl.se
  schedule JSON. Two independent sources available → both-direction
  reconciliation between them AND vs fetched games.

## 3. Capability table (MAGNUS_DATA_GAPS bar)

| Capability | stats.swehockey.se (Game/Events HTML) | shl.se | Verified on |
|---|---|---|---|
| Event timeline | YES: goals, penalties, GK in/out, per period (NEWEST-FIRST order; shots as period totals only) | TBD (game endpoints unknown; probe 2) | 1004308 |
| Explicit goalie in/out with times | **YES — "GK Out"/"GK In" rows with cumulative clock**: 1004308 has 00:00 GK In (both starters), 57:12 GK Out BIF (pull, down 4-6), 57:39 GK In BIF (after EN goal), 60:00 GK Out both (END-OF-GAME rows — adapter must not read as pulls) | TBD | 1004308 |
| Delayed-penalty visibility | none observed yet (no dp events in sample; TBD across more games) | TBD | 1004308 (absence) |
| EN flag on goals | **YES — "ENG" flag** on the 57:39 goal (4-7 EQ), cross-checkable against the GK-out window (57:12-57:39) — dual-channel like Mestis | TBD | 1004308 |
| Penalties begin+end | **YES — EXPLICIT begin AND end** "(46:03 - 47:10)" incl. early termination at PP goal, and team penalties "(03:05 - 05:05)". Liiga-class, better than AHL | TBD | 1004308 |
| Strength on goals | YES: (EQ)/(PP1)/(SH1) + on-ice jersey lists both teams ("Pos. Part."/"Neg. Part.") — independent strength cross-check | TBD | 1004308 |
| Coaches per game | NOT on Events page; LineUps page verdict PENDING (file fetched, in transfer) | TBD | 1004308 (Events negative) |
| Schedule authority | per-season Schedule page (server-rendered, has ALL games + ids) | schedule JSON (has uuids, rounds, OT/SO flags) | 18263 / xs4m9qupsi |
| Live in-game feed | Live/{seriesId} pages exist (irrelevant to lake; paper-harness question later) | site is live-scoring capable | — |

Parser/verification notes from 1004308 (recorded now, adapter's problem later):
- Period sections and rows are listed newest-first; clock is cumulative (57:12 not 17:12).
- 60:00 "GK Out" pair = end-of-game bookkeeping, NOT pulls; 00:00 "GK In" = starters.
- Swedish decimal commas ("15,38%"), NBSP in team headers, `&#xD;&#xA;` inline styles.
- A third per-game artifact exists: `/Game/Reports/{gameId}` (content TBD, probe 2).
- Scoping (ticker lesson): Events page structure is single-game server-rendered
  tables — but scoping is PROVEN only when the verifier counts rows inside the
  game's own table element and matches header totals (PIM/goals). Standing item
  for verify_shl_lake.py, not assumed.

## 4. Probe log

- **Probe 1** (2026-08-05, `tools/probes/shl_probe1.ps1`): shl.se
  schedule HTML + auto-extracted `/api/` endpoints + one game page +
  its endpoints; api.shl.se root + docs; stats.swehockey.se root +
  schedule 18263 + one Events + one LineUps page; historical root; DNS
  re-check of the dead old host. AWAITING RUN.
