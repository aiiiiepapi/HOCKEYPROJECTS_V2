# Mestis — data source documentation (Scraping session, 2026-08-03)

Status: LAKE COMPLETE & VERIFIED (same day). 1,166 games / 4 seasons,
0 missing vs ICS schedule, 100% roster coverage w/ head coach, all
sha256-manifested. Lake branch: **HOCKEYPROJECTS_V2 `mestis-data-lake`**
— NOT the v1 HOCKEYPROJECTS repo: the V2 write token has NO access to
that repo (403 even on read; "same token works" in the kickoff was
wrong). Seb ruled "you do it" → pushed where the token works; Manager
can move the branch if the v1-repo convention matters.

Final per-season counts (fetched + reconciled 1:1 vs ICS):

| Season | dir | Games | Teams | goalie-out ev. | pois-intervals | rosters (HC) |
|---|---|---|---|---|---|---|
| 2022-23 | 2023 | 364 | 14 | 303 | 226 | 364 (364) |
| 2023-24 | 2024 | 312 | 13 | 242 | 186 | 312 (312) |
| 2024-25 | 2025 | 245 | 10 | 185 | 155 | 245 (245) |
| 2025-26 | 2026 | 245 | 10 | 205 | 179 | 245 (245) |

(Team counts consistent with schedule sizes: 14x52/2, 13x48/2, 10x49/2.)

Goal-flag vocabulary — decoded by the source itself (every seuranta page
carries this legend; captured verbatim from fetched game 2026/3170):
YV ylivoimamaali (PP goal), AV alivoimamaali (SH goal), VM voittomaali
(game-winner), VT videotarkistus (video review), SR siirretty rangaistus
(DELAYED-PENALTY goal — partial dp visibility), RL rangaistuslaukaus
(penalty shot), TV tasavajaa, VL voittomaalikilpailu (shootout),
TM tyhjä maali (empty-net goal), IM ilman maalivahtia (scored while own
net empty). NOTE for parsers: because the legend is on every page, a
plain grep for a flag always hits ≥1 — count flags from goal rows only.

## TL;DR

Mestis has NO public JSON API found. The official site **mestis.fi**
(platform by Nidos Oy) serves fully **server-rendered HTML** with, per game,
an event timeline that includes **explicit goalie out/in events with times**
("Maalivahti ulos/sisään"), goal flags incl. **TM (empty net)**, penalties
with times+minutes, timeouts — plus a goalie stat line that repeats the
off-ice intervals ("pois: 57:59-58:04, 58:32-59:56" — **multi-pull windows
are separable**). This is AHL-class pull visibility, far above Magnus.
**Coaches are NOT on the game pages** (the one capability-table miss).
Raw lake = saved HTML pages verbatim (like the Magnus lake keeps PDFs).

## 1. Source inventory

### 1.1 mestis.fi (PRIMARY — confirmed for all 4 target seasons)

- Platform: custom site by Nidos Oy (footer credit). No robots.txt (404).
  No auth, no cookies needed, no rate-limit encountered during sampling.
- Server-rendered HTML: all game data below was readable from plain
  fetched HTML (no JS execution needed) — verified via plain fetches on
  games from 2022-23, 2023-24, 2024-25, 2025-26.
- Season coverage in the season dropdown: **2014-2015 through 2026-2027**.

URL scheme (all verified):

| Page | URL |
|---|---|
| Season match list | `https://mestis.fi/fi/ottelut/{YYYY-YYYY}/runkosarja/` |
| Season schedule ICS | `https://mestis.fi/ottelut/{YYYY-YYYY}/runkosarja/kalenterit` |
| Game lineups | `https://mestis.fi/fi/ottelut/{YYYY-YYYY}/runkosarja/{MATCHNO}/kokoonpanot/` |
| Game event timeline | `.../{MATCHNO}/seuranta/` |
| Game boxscore/stats | `.../{MATCHNO}/tilastot/` |

Id schemes (two of them — do not confuse):
- **MATCHNO** (URL id): the league match number. **Unique only within a
  season+series** — e.g. 2965 exists in both 2024-25 and 2025-26. Always
  key games as (season, matchno). Observed ranges: 2022-23 → 7278-7458+,
  2023-24 → 3965-4047+, 2024-25 → 2972-3216+, 2025-26 → 2954-3018+.
- **Internal game id**: in the ICS `UID:` line, e.g.
  `Mestis-Runkosarja-2024-game-95010@mestis.fi` (2024 = season start
  year, 95010 = internal id). No endpoint taking this id was found; we
  record it for reconciliation and future use.
- Player ids: 8-digit (e.g. `/fi/pelaajat/30811890/santanen-eetu`) —
  looks like Finnish-federation-registry style; cross-source join key
  candidate (e.g. against tilastopalvelu) if ever needed.

The ICS calendar is the **official schedule authority** for reconciliation:
one VEVENT per game with teams (SUMMARY), UTC start/end (DTSTART/DTEND),
internal id (UID) and the kokoonpanot/seuranta URLs carrying the MATCHNO
(DESCRIPTION). Verified on 2024-25: first events match the season page 1:1
(3161 IPK-Ketterä 2024-09-12, 3000 Hokki-Hermes, 3166 Ketterä-JoKP...).

### 1.2 tilastopalvelu.fi / Leijonat Tulospalvelu (SECONDARY — confirmed
    to carry Mestis as JSON; game-sheet depth pending probe v5)

Access quirks (all verified on Seb's PC, 2026-08-03):
- `www.tilastopalvelu.fi` is dead to modern clients (TLS
  `SSLV3_ALERT_HANDSHAKE_FAILURE`; plain HTTP → 403).
- **Bare `tilastopalvelu.fi` works** over HTTPS with a permissive legacy
  context (self-signed chain → cert verification off; read-only public
  stats, acceptable). The cloud proxy cannot reach it at all.
- The service is the Finnish federation's 'Leijonat - Tulospalvelu' SPA
  (mirror/alias: `tulospalvelu.leijonat.fi`); static shell is stale
  (Dec-2020 banner) but the app and data are current.

Confirmed by fetched sample (probe v4, `getGames.php` POST
`{season:2025, stgid:0, teamid:0, districtid:-1, gamedays:-1,
dog:2025-01-11}` → 35,767 B JSON):
- **Mestis is hosted**: `LevelName:"Mestis", LevelID:"65",
  StatGroupID:"168"` (2024-25), 5 Mestis games on that date.
- **`GameID` equals the mestis.fi match number** (3016 = KeuPa HT -
  TUTO 4-5, 2025-01-11, attendance 331) — the two sources share an id
  space, so cross-source reconciliation is a trivial join.
- Rich per-game schedule fields: `GameEffTime` (3600), `Spectator`,
  `FinishedType`, `PeriodSummary` per-period goals, rink + lat/long,
  team association ids, `GameRules` vector, `DeniedStats/DeniedResults`.
- Endpoint inventory extracted from the SPA JS (`/ih/helpers/` +
  `MainHelpersPath`): getSeasons, getLevels, getStatGroups, getStatGroup,
  getGames, getStandings, getTeams, getTeamStats, getTeamSerieRoster,
  getPlayers, getGoalkeepers, getgamereportdata, getRinks, getBarometer,
  gamerosters/index.php, plus dwl* CSV-download variants.
- The SPA UI deliberately does NOT open its own gamecentre for LevelID
  65 (Mestis clicks route to mestis.fi) — but the BACKEND serves Mestis
  fine (probe v7, verified on game 3016):
  - **`POST /ih/game/helpers/getRosters.php {gameid, season}` → 86 KB
    JSON with GAME-LEVEL staff rosters incl. Head Coach.** Keys:
    PlayerRoles, StaffRoles, Home/AwayTeamSerieRoster,
    Home/AwayTeamGameRoster — each roster has Players + Staff, staff
    rows carry RoleName/RoleName_EN (Vastuuvalmentaja = Head Coach),
    names, birth years, ids. Game 3016: home HC RAISKIO Niko, away HC
    VIRTANEN Jonne — and TUTO's SERIE roster lists TWO HCs for the
    season (MARJETA + VIRTANEN), so game-level attribution is not just
    nice, it is REQUIRED, and this endpoint provides it. **The coach
    gap is CLOSED** (fetcher saves this per game as
    `game_{year}_{n}_rosters.json`).
  - `POST /ih/serie/helpers/getStatGroups.php {season, levelid:65}` →
    Mestis statgroups 2025: **168 = Mestis (runkosarja)**, 3333 =
    pudotuspelit, 5522 = karsintaottelut, 5563 = harjoitusottelut.
  - `/ih/gamerosters//helper/game.php?game=N&season=Y` (+ gamerosters/
    referees siblings; empty-POST, query-string params) → small JSONs
    (referee names verified; note double-encoded UTF-8 mojibake in
    referees.php — kept verbatim, adapter concern).
  - `getgamereportdata.php` 404s at every helper dir tried — the
    gamecentre event feed endpoint remains unlocated (not needed:
    mestis.fi seuranta is the event source).
  - "season" parameter = season END year (3016+2025 = the 2024-25
    game), same convention as our lake dirs.

### 1.3 v1 Finland research (read 2026-08-03)

`OneDrive .../projects/FINLAND/` contains **Liiga-only** research
(NEW_LEAGUE_CEO_GUIDE.md is a league-agnostic template;
liiga/LIIGA_DATA_ACCESS_RESEARCH.md etc. are liiga.fi API docs). Zero
Mestis leads — grep for mestis/tilastopalvelu/tulospalvelu/leijonat over
all FINLAND .md files returned nothing. Discovery above is from scratch.

## 2. Environment facts (verified 2026-08-03)

- **Cloud Python → mestis.fi: BLOCKED** (`Tunnel connection failed: 403
  Forbidden` — same proxy-403 as other league APIs; verified with a
  stdlib urlopen attempt on a game page). The CLAUDE.md assumption HOLDS
  for Mestis. → fetcher runs on Seb's Windows PC (established pattern).
- Cloud WebFetch tool → mestis.fi: works (used for all discovery
  sampling), but is not a bulk-fetch channel and returns converted
  markdown, not verbatim bytes. The LAKE must come from the PC run.
- tilastopalvelu.fi: unreachable from cloud entirely (TLS, see 1.2).

## 3. What the payloads contain (verified verbatim, by sample)

### seuranta (event timeline) — the money page

Event types observed across samples:
- **Goals** with running score, scorer (#, name, season tally), assists,
  and flag codes. Flags observed: `YV` (3161: 51:18 goal "2-2 YV"),
  `TM` (3000: "59:33 #9 Oliver Suni 7-3 TM"; 2999: "58:49 5-2 TM"),
  `TV` (3161: 36:53 goal, video review), `VL` (3161: shootout winner
  at 65:00), and on 7458 the summary reported `SR`, `VM`, `IM` codes.
  Decoding the full flag vocabulary = adapter work (Manager); the lake
  just has to carry them, and it does.
- **Penalties** with time, player (or team penalty), minutes and offense
  text, e.g. 3000: `42:44 Joukkuerangaistus 2 min liian monta pelaajaa
  jäällä (#46 Eetu Mäki)`; 3161: `16:07 #67 Joona Lehtinen 10 min`.
  **Begin time + minutes only — no explicit end events observed**
  (AHL-style reconstruction, incl. misconduct exclusion, applies).
- **Goalie out/in — EXPLICIT, with times**:
  - 3000 (2024-25): `57:18 Maalivahti ulos: #36 [Jesse Haukka]` /
    `59:33 Maalivahti sisään: #36 [Jesse Haukka]`
  - 2999 (2024-25): out 56:48 / in 58:49 (bracketing the TM goal)
  - 7458 (2022-23): TWO separate pulls by #74 Lipiäinen:
    out 57:59 / in 58:04, out 58:32 / in 59:56
  - 4009 (2023-24): out 57:27, never returns
  - 2965 (2025-26): out 56:51 / in 59:55
  Also observed: a mid-game goalie SWAP recorded (3000: Vedenpää →
  Haukka at 24:33), i.e. the same channel carries both swaps and pulls.
- **Timeouts** (2999: RoKi timeout 56:57).
- Shot maps exist on the page (coordinates embedded in the rendering).

### tilastot (boxscore)

Final + per-period score, game duration (65:00 for OT/SO games — never
assume 3600s), attendance, per-goalie lines: shots faced, goals allowed,
save%, time played, per-period saves, and crucially the **off-ice
intervals repeated in text**: 2999: `#40 Romi Huunonen 6+13+6=25
(out: 56:48-58:49)`; 7458: `#74 Santeri Lipiäinen 8+16+2=26
(pois: 57:59-58:04, 58:32-59:56)`; 4009: `(pois: 57:27-60:00)`.
This redundancy (events + intervals) is a built-in cross-check for the
adapter and the audit harness.

### kokoonpanot (lineups)

Goalies with starter/backup designation, 4 forward lines + D pairs,
referees (head + line). **NO coaches** (checked 3161, 2999 across all
three tabs + game front page: no valmentaja/päävalmentaja/toimihenkilöt
anywhere).

## 4. Capability table (the MAGNUS_DATA_GAPS bar)

| Capability | Mestis (mestis.fi HTML) | Verified on |
|---|---|---|
| Event timeline | PARTIAL — goals, penalties, goalie in/out, timeouts (no faceoffs/stoppages) | 3161, 3000, 2999, 7458, 4009, 2965 |
| Explicit goalie in/out with times | **YES — explicit events AND stat-line intervals; multi-pull separable** | 7458 (2 pulls), 3000, 2999, 4009, 2965 |
| Delayed-penalty visibility | None as events; `SR` flag observed on goals (decode TBD) — whistle-coincidence discriminators unavailable | 7458 |
| EN flag reliability | `TM` flag on goals; cross-checkable against goalie-out intervals | 3000, 2999 |
| Strength at any second | Penalty begin+minutes (AHL-style reconstruction; no explicit end) | 3000, 3161 |
| Coaches on sheet | **YES via tilastopalvelu getRosters.php — GAME-level Staff incl. Head Coach** (not on mestis.fi pages themselves) | 3016 (both teams; dual-HC season resolved) |
| Live in-game feed | Unknown; seuranta page presumably live-updates in season (irrelevant to lake) | — |
| Season volume | TBD exactly at fetch; teams: 2022-23 ≈14-15 listed (incl. HK Zemgale — verify), 2023-24 = 13, 2024-25 = 10 (incl. Jokerit), 2025-26 = 10 | season pages |

## 5. Coverage plan

Target: last 4 completed seasons, regular season (runkosarja) only —
2022-23, 2023-24, 2024-25, 2025-26 (dirs by END year: 2023..2026, Liiga
convention). Playoffs/relegation and Harjoitusottelut excluded (matches
NHL/AHL/Liiga lakes). Per-season game counts come from the fetched ICS
(schedule authority) and must reconcile 1:1 with saved game files;
WebFetch sampling truncates lists, so **no count in this doc is final
until the PC run reports** — expected order of magnitude 250-450/season
given 10-15 teams.

## 6. Lake layout (branch mestis-data-lake of HOCKEYPROJECTS)

```
mestis/
  2023/                       # season END year = 2022-23
    schedule_2023.ics         # verbatim ICS (authority)
    schedule_page_2023.html   # verbatim season list page (secondary)
    statgroups_2023.json      # tilastopalvelu statgroup map (verbatim)
    game_2023_7458_kokoonpanot.html
    game_2023_7458_seuranta.html
    game_2023_7458_tilastot.html
    game_2023_7458_rosters.json   # tilastopalvelu game-level staff/coaches
    ...
    manifest_2023.json        # per-file sha256, bytes, url, fetched_utc
  2024/ 2025/ 2026/           # same layout
```

All files are the raw HTTP response bytes, verbatim, never edited.

## 7. Open questions for Manager / Seb

1. **Coach identity: RESOLVED** — tilastopalvelu getRosters.php,
   game-level (see 1.2). Open sub-question: does it cover ALL 4 target
   seasons? Settled by the fetch run's per-season rosters counts (the
   fetcher WARNs loudly on a zero-roster season; fallback if old seasons
   are absent = hand-curated map, AHL precedent).
2. Flag vocabulary decode (`SR`, `IM`, `AV`, `TV`, `VL`, `VM`) — adapter
   work, needs systematic samples from the lake.
3. Exact per-season game counts + team lists (incl. the HK Zemgale
   2022-23 question) — settled by the fetch run's reconciliation report.
4. Whether penalty *expiry* ever appears as an event in any game
   (none observed in samples; assume AHL-style reconstruction).
5. 2014-2022 history exists on the platform if the portfolio ever wants
   deeper Mestis history (out of current scope).
