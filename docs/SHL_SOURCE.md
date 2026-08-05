# SHL — data source documentation (Scraping session, started 2026-08-05)

Status: **DISCOVERY IN PROGRESS — probe 1 awaiting PC run.** Nothing in
this doc is capability-verified yet unless a NAMED fetched game is cited
(rule: every claim verified on a fetched sample, not documentation).
Session branch: `claude/shl-scrape-ly11nk` (the cloud harness maps the
kickoff's `shl-scrape` branch name to this; Manager note in HANDOFF).

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

## 3. Capability table (MAGNUS_DATA_GAPS bar) — ALL ROWS PENDING PROBE

| Capability | stats.swehockey.se | shl.se | Verified on |
|---|---|---|---|
| Event timeline | expected (goals/penalties/shots) | unknown | — |
| Explicit goalie in/out with times | unknown | unknown | — |
| Delayed-penalty visibility | unknown | unknown | — |
| EN flag on goals | unknown | unknown | — |
| Penalties begin+minutes or begin+end | unknown | unknown | — |
| Coaches per game | unknown | unknown | — |
| Schedule authority | per-season Schedule page | schedule JSON | — |

No row gets filled without a named fetched game (ticker lesson applies:
any per-game count must be proven scoped to the game's own container).

## 4. Probe log

- **Probe 1** (2026-08-05, `tools/probes/shl_probe1.ps1`): shl.se
  schedule HTML + auto-extracted `/api/` endpoints + one game page +
  its endpoints; api.shl.se root + docs; stats.swehockey.se root +
  schedule 18263 + one Events + one LineUps page; historical root; DNS
  re-check of the dead old host. AWAITING RUN.
