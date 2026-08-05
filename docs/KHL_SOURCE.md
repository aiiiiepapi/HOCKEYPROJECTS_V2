# KHL data source discovery (khl-scrape session, started 2026-08-05)

Status: **PHASE 1 — remote discovery done, PC probe pending.** This session
(cloud) cannot reach ANY khl.ru host or mirror: shell egress proxy returns
CONNECT 403 for every non-allowlisted host (including google.com and
web.archive.org — i.e. the block is OUR proxy policy, not necessarily KHL),
and the harness WebFetch tool returns 403 for www.khl.ru, en.khl.ru,
text.khl.ru, mhl.khl.ru, khl.api.webcaster.pro AND en.wikipedia.org (so
WebFetch is also policy-fenced; only WebSearch works). **Conclusion: the
session-side result CANNOT distinguish KHL geo-blocking from local proxy
policy. The real geo/access check happens on Seb's PC via the probe
paste-block (tools/probe_khl.ps1). Nothing below is verified on a fetched
sample yet unless marked otherwise.**

## Reachability matrix (updated as results land)

| Host | Cloud shell (proxy) | Cloud WebFetch | Seb PC (US/EU residential) |
|---|---|---|---|
| www.khl.ru | 403 CONNECT (proxy) | 403 | TBD (probe stage A) |
| en.khl.ru | 403 CONNECT (proxy) | 403 | TBD |
| text.khl.ru | not tested (proxy blocks all) | 403 | TBD |
| online.khl.ru | not tested | not tested | TBD |
| api.khl.ru | 403 CONNECT (proxy) | 403 | TBD |
| khl.api.webcaster.pro | 403 CONNECT (proxy) | 403 | TBD |

Search engines (Google/Bing, US-based) index khl.ru pages as recently as
Feb 2026 (`text.khl.ru/text/898094.html`, indexed) — so a blanket US
geo-block is UNLIKELY, but bot/datacenter-IP filtering is still possible.
Residential probe decides.

## Season structure (external references — re-verify against KHL's own schedule)

Source: Wikipedia season pages + en.khl.ru news pages via search snippets
(2026-08-05). NOT yet reconciled against the schedule authority; the lake
verification will do the 1:1 reconciliation.

| Season | Teams | Games/team | Total RS games | RS window | khl.ru tournament id (regular) |
|---|---|---|---|---|---|
| 2022-23 | 22 | 68 | 748 | 2022-09-01 – 2023-02-26 | **1154** |
| 2023-24 | 23 | 68 | 782 | 2023-09-01 – 2024-02-26 | **1217** (playoffs 1218) |
| 2024-25 | 23 | 68 | 782 | 2024-09-03 – 2025-03-23 | **1288** (playoffs 1289) |
| 2025-26 | 22 | 68 | 748 | 2025-09-05 – 2026-03-20 | **1369** |

Total: **3,060 regular-season games** — bigger than the kickoff's
650-750/season estimate (that range was low; actuals 748-782). Biggest
lake yet by game count (NHL lake: 2,624).

Tournament-id provenance (search-indexed khl.ru URLs, each seen verbatim):
- `www.khl.ru/calendar/1154/00/` — "Расписание матчей КХЛ 2022/2023 ... Регулярный чемпионат"
- `www.khl.ru/standings/1217/conference/` — "Турнирная таблица КХЛ 2023/2024 ... Регулярный чемпионат"
- `www.khl.ru/standings/1288/conference/` + `en.khl.ru/calendar/1288/00/208/` — 2024/2025 regular
- `www.khl.ru/calendar/1369/00/` — "Расписание матчей КХЛ 2025/2026 ... Регулярный чемпионат"
- Sequence sanity: ids are league-wide sequential per stage (1154 → 1217 → 1288 → 1369).

## Candidate endpoints (to verify in probe — none fetched yet)

1. **Calendar / schedule-authority candidate**:
   `https://www.khl.ru/calendar/<tournament_id>/00/` (RU) and
   `https://en.khl.ru/calendar/<tournament_id>/00/` (EN). Expect the games
   list incl. links to game pages. The `00` segment is unexplained (month
   filter? "all"?) — probe fetches it raw; do not assume.
2. **Game center pages**:
   pattern `https://www.khl.ru/game/<tournament_id>/<game_id>/<tab>/`,
   observed verbatim on the sibling MHL site
   (`mhl.khl.ru/game/1373/901786/summary/`, indexed Apr 2026) — same
   platform, so KHL layout is presumed identical with tabs like
   `summary`/`protocol`/`online`; tab names UNVERIFIED for KHL proper.
3. **Text broadcast**: `https://text.khl.ru/text/<game_id>.html` —
   OBSERVED (search-indexed): `text.khl.ru/text/898094.html` = "Игра номер
   604, 14 фев 2026: Барыс-Лада (онлайн трансляция)", i.e. 2025-26 regular
   season game #604. Russian-language event lines expected (вратарь
   phrases for goalie in/out — exact wording TBD from raw sample).
   Also `https://online.khl.ru/online/` (live text platform, indexed).
4. **Mobile-app JSON (webcaster.pro)**: webcaster.pro publicly lists KHL
   apps as their product. Historic community knowledge points at
   `https://khl.api.webcaster.pro/api/khl_mobile/events_v2.json` (games
   list) and `.../event_v2.json?id=<id>` (single game) — **memory-grade,
   zero fetched evidence; probe treats these as guesses.** Alternate host
   guess: `https://api.khl.ru/`.
5. **Enumeration channels**: `www.khl.ru/sitemap.xml`, `robots.txt`
   (politeness + id discovery).

### Game-id scheme — platform-global hypothesis

KHL text id 898094 (Feb 2026) and MHL game id 901786 (Apr 2026) sit in the
same numeric ballpark → the platform likely uses ONE global event-id space
shared across KHL/MHL/VHL/ZhHL. If true, **per-season KHL id ranges are NOT
contiguous and id-range sweeps are the wrong enumeration method** (unlike
Magnus): enumeration must come from the calendar/schedule listing per
tournament id. Probe + first calendar payload will confirm.

## Capability bar (docs/MAGNUS_DATA_GAPS.md) — all rows TBD

| Capability | KHL expectation | Verified on named game? |
|---|---|---|
| Event timeline | text broadcast lines + possible mobile JSON | NO — pending probe |
| Goalie in/out with times | expected in text feed (RU phrases TBD verbatim) | NO |
| EN flags on goals | TBD (protocol page? JSON?) | NO |
| Penalties begin+minutes or begin+end | TBD | NO |
| Coach per game | expected on protocol page | NO |
| Delayed-penalty visibility | TBD | NO |
| Live feed (paper harness) | online.khl.ru / mobile JSON — TBD | NO |

Ticker lesson (Mestis) carries: ANY per-game count from khl.ru pages must
be provably scoped to the game's own event container — KHL pages carry
league-wide score tickers. No page-wide greps, ever.

## Market note (Manager, on record)

Odds provider has NO icehockey_khl market. Lake serves coach intel +
model-side lines (ruling 5). Seb ordered with this heard.

## Sizing & repo check (mandated before fetch)

- V2 repo today: ~3.4 MiB pack on master; `mestis-data-lake` branch exists
  on the same repo (lake-on-V2 convention; ~4.7k files).
- KHL: 3,060 games × est. 3-5 artifacts/game (game page, protocol tab,
  text broadcast, JSON, maybe EN page) ≈ 9-15k files. Byte size UNKNOWN
  until the probe reports real per-artifact sizes — khl.ru pages are
  heavy (likely 100s of KB each).
- Decision rule (proposed to Seb): probe measures real bytes/game →
  projected packed size = 3,060 × measured × git-compression factor.
  If projection > ~1.5 GB packed, split into per-season orphan branches
  `khl-data-lake-2023` … `khl-data-lake-2026`; else single
  `khl-data-lake` with one commit+push per season (every push must stay
  well under GitHub's 2 GB per-push limit either way).
- Artifact-set trimming is also on the table: if the mobile JSON proves to
  contain the full event feed, the heavy HTML tabs may be reduced to
  1 HTML + 1 JSON per game. Decide AFTER the probe, on evidence.

## Next actions

1. Seb runs `tools/probe_khl.ps1` (paste-block) on the PC → raw samples
   land in `tests/reference_raw/khl_probe/` on this branch.
2. This session mines the raw payloads: real endpoints, XHR URLs from
   page source, RU goalie phrases, id scheme, per-artifact bytes.
3. Capability table rows get verified on NAMED games; fetcher
   (tools/fetch_khl.py) gets written against VERIFIED endpoints only.
