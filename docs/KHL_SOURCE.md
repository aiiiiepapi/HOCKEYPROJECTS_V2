# KHL data source discovery (khl-scrape session, started 2026-08-05)

Status: **PHASE 2 — probe round 1 analyzed (18 raw files in
tests/reference_raw/khl_probe/, commit 5f6b07b), round 2 pending
(tools/probe2_khl.ps1).** Everything marked VERIFIED below is verified on
the named fetched files, per rule 6 / ruling 42.

## Reachability (VERIFIED 2026-08-05)

| Host | Cloud shell/WebFetch | Seb PC (residential) |
|---|---|---|
| www.khl.ru, en.khl.ru, text.khl.ru, online.khl.ru | 403 (our egress policy fence) | **200, full payloads** |
| khl.api.webcaster.pro | 403 | 200 |
| api.khl.ru | 403 | **NXDOMAIN — host does not exist** |

No geo-block for Seb's connection. ALL fetching runs on the PC (standing
convention). The cloud session analyzes raw files pushed to the branch.

**Transfer integrity lesson (VERIFIED)**: Seb's git autocrlf ALTERED 2 of
18 round-1 files in transit (A_robots.txt 9255->8914 B, A_sitemap.xml -1 B
— CRLF->LF normalization; sha256 mismatch vs manifest). `.gitattributes`
with `-text` for `tests/reference_raw/**` and `khl/**` added 2026-08-05.
**The lake fetch must re-verify manifests AFTER push+pull, and the lake
branch MUST carry the same .gitattributes** (manifest re-hash after
transfer was already a standing gate; here it caught a real alteration).

## Schedule authority & coverage (VERIFIED on fetched calendars)

`https://www.khl.ru/calendar/<tid>/00/` is server-rendered (~2.3 MB) and
lists every regular-season game with hrefs `/game/<tid>/<gid>/protocol/` +
`/game/<tid>/<gid>/resume/` + a `text.khl.ru/text/<gid>.html` link.

**Ticker lesson applies literally (rule: scope every count)**: each page
embeds a 24-game `slider-item` carousel (upcoming 2026-27 preseason, tid
1436) and a 4-game adjacent-tournament widget (tids 1145/1279/1353/1423 on
the four pages respectively). Page-wide counts are inflated by exactly
those; scoped-to-own-tid counts are exact:

| Season | tid | game-id range | games (scoped) | External expectation | Text links |
|---|---|---|---|---|---|
| 2022-23 | 1154 | 881261..882008 (contiguous) | **748** | 748 ✓ | 752 = 748+4 widget ✓ |
| 2023-24 | 1217 | 885442..886223 (contiguous) | **782** | 782 ✓ | 786 = 782+4 ✓ |
| 2024-25 | 1288 | 889850..890631 (contiguous) | **782** | 782 ✓ | 786 = 782+4 ✓ |
| 2025-26 | 1369 | 897491..898238 (contiguous) | **748** | 748 ✓ | 752 = 748+4 ✓ |

Total **3,060 regular-season games**; every RS game in all four seasons
has a text-broadcast link (existence of link ≠ existence of content for
2022-25 — that's probe round 2's archive-depth check). Game-id blocks are
CONTIGUOUS per season (the earlier platform-global interleaving worry is
moot for enumeration; the calendar id-set is still the reconciliation
anchor, both directions, per standing lake protocol). Month tokens on the
calendar pages match the known season windows (Sep-Feb / Sep-Mar).

## Channels (VERIFIED on named games)

### text.khl.ru/text/<gid>.html — the primary event channel
Verified on **898094** (Барыс-Лада, 2025-26 game #604, 866 KB, round-1
file B_text_898094.html). Server-rendered, one `div.textBroadcast-item`
per event with `time.textBroadcast-item__left-time` + team logo
(`img.khl.ru/teams/ru/<tid>/<team_id>/…`) + text. 80 events this game.
Verbatim vocabulary (capability table anchors):

- **Pull**: `Лада. Замена вратаря на экстра-полевого игрока` (59:11, 58:33;
  Барыс 08:47)
- **Return**: `Лада. Вратарь в воротах` (58:47; Барыс 10:01)
  -> a real re-pull sequence (58:33 out / 58:47 in / 59:11 out) is captured
  explicitly; a dp-driven extra-attacker episode (Барыс 08:47-10:01 during
  `Отложенный штраф у команды Лада`) is captured too.
- **Delayed penalty**: `Отложенный штраф у команды <Team>` (no time on line)
- **Penalty begin**: `Удаление. <Team>. <#>. <Фамилия Имя> . 2 мин. <offense>.`
  team-penalty variant: `Командный штраф . 2 мин. … Отбывал: <#. Name>`
- **Penalty end / back to full strength**: `Команда <Team> играет в полном
  составе` (explicit END events — begin+end, better than AHL's begin+minutes)
- **Strength notes**: `Игра 4 на 4`
- **Goal**: `Изменение счета: <Team>. <#. Scorer> , ассистенты: …` —
  **NO TIME on goal lines** (left-time empty). Goal times must come from
  another channel (protocol page — round 2) or ordering-only.
- Period boundaries: `Начало/Окончание N периода` — **WALL-CLOCK times**
  (17:01, 18:45, 19:16 = MSK evening), while play events carry cumulative
  GAME-CLOCK mm:ss. Mixed semantics — adapter must key on event text, never
  trust the time column's meaning blindly.
- Extras: icing/offside lines, `Рекламная пауза` (ad-break dead-time
  channel), per-period + match stat lines, starting lineups, preview prose.
- **Known defect**: duplicate penalty line observed (51:57 Бреус twice) —
  dedupe is adapter work.
- Same page also embeds: full per-player stat tables incl. **ВППВ = TOI
  with empty net** ("Время на площадке при игре без вратаря (пустые
  ворота)") — an independent EN-exposure channel; goalie section
  («Вратари»); line combinations; and **coaches** («Тренер» rows:
  Кравец Михаил Григорьевич / Десятков Павел Николаевич on 898094 —
  both are the actual 2025-26 HCs of Lada/Barys).

### www.khl.ru/game/<tid>/<gid>/protocol/ and /resume/
Link pattern verified from calendars; **payloads NOT yet fetched**
(round-1 guesses used the WRONG url form `/game/<tid>/<gid>/` -> 404;
tabs are mandatory). Round 2 fetches protocol+resume for named games.
Expected to carry goal times + official protocol. UNVERIFIED.

### en.khl.ru — English mirror
Root reachable (435 KB). Game-page equivalence UNVERIFIED (round 2).

### khl.api.webcaster.pro — VIDEO platform, not pbp (VERIFIED)
`/api/khl_mobile/events_v2.json` returns the KHL **video/stream** event
list (m3u8/iframe fields, 16 upcoming 2026-27 preseason entries at probe
time; `q[tournament_id_eq]` ignored). Carries `khl_id` per game and team
`khl_id`s — possible live-harness aid later, NOT a lake channel. The old
`api.khl.ru` host is dead (NXDOMAIN).

### Enumeration side-channels
robots.txt: no global crawl-delay directive (politeness stays at our
>=0.5 s). sitemap.xml: news/clubs/players, not games — irrelevant for
enumeration. online.khl.ru: live text platform (10 KB shell), not needed
for historical lake.

## Capability bar vs MAGNUS_DATA_GAPS (state after round 1)

| Capability | KHL finding | Verified on |
|---|---|---|
| Goalie in/out with times | YES — explicit paired events, game clock | 898094 |
| Multi-pull windows | YES — each out/in event explicit | 898094 (58:33/58:47/59:11) |
| Delayed-penalty visibility | YES — explicit dp event + observed dp-pull episode | 898094 |
| Penalties | begin (time+minutes+offense) AND explicit back-to-full-strength events | 898094 |
| EN flags on goals | INDIRECT so far (goal lines lack times/flags; ВППВ TOI table = EN exposure per player) | 898094; protocol page TBD |
| Goal times | **MISSING in text channel** — round-2 protocol check | — |
| Coach per game | YES — Тренер rows on text page | 898094 |
| Event timeline granularity | curated broadcast (~80 events/game): goals, penalties+ends, pulls, dp, icings, ad breaks, periods | 898094 |
| Live feed | online.khl.ru + webcaster (Sept shakedown scope) | — |
| Archive depth 2022-25 | links exist for 100% of games; CONTENT unverified | round 2 |

## Sizing (updated with real bytes)

Text page: 866 KB raw. 3,060 texts ≈ 2.6 GB raw + protocol/resume pages
(sizes TBD round 2). HTML compresses well in git packs, but this is the
biggest lake yet by bytes. Decision after round 2: likely **per-season
orphan branches** `khl-data-lake-<END_YEAR>` (each ~650 MB raw / est.
100-200 MB packed) instead of one branch; every push well under GitHub's
2 GB per-push limit. Cloud-side verification can sparse-checkout one
season at a time (session disk allowance).
Fetch time: ~2-3 artifacts × 3,060 games at ~1.5 s/request ≈ **3-5 h per
full run** — resume-safety in fetch_khl.py is mandatory, per-season runs
recommended.

## Market note (Manager, on record)

Odds provider has NO icehockey_khl market. Lake serves coach intel +
model-side lines (ruling 5). Seb ordered with this heard.

## Open items (round 2 + fetcher)

1. Protocol/resume payloads: goal times, EN/PP flags on goals, official
   lineups/coaches, shootout format. (probe2_khl.ps1 — awaiting PC run)
2. Text-broadcast CONTENT depth for 2022-23/2023-24/2024-25 (named first
   games + one mid-season spot). Risk: old seasons may have empty
   broadcast pages; then protocol pages become the primary event source —
   capability re-check required.
3. en.khl.ru protocol equivalence (English event texts would ease adapter
   work but RU stays the authority).
4. Artifact set per game (text + protocol + resume vs subset) — decide on
   round-2 evidence, then write tools/fetch_khl.py.
