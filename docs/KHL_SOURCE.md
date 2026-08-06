# KHL data source discovery (khl-scrape session, started 2026-08-05)

Status: **LAKE SHIPPED & VERIFIED (2026-08-06)** — branch `khl-data-lake`
tip 4ed99df: 3,060 games × (text+protocol), 4.14 GB payloads, fetched on
Seb's PC (0 fails), verified twice: PC-side (seed 20260805) and
cloud-side on the PUSHED content (seed 20260806, full re-hash all 6,124
files, scoped reconciliation, 8 spot-opens/season — all PASS). Discovery
record below; capability bar fully met on named games in all 4 seasons.
Everything marked VERIFIED is verified on named fetched files, per rule 6
/ ruling 42.

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

### www.khl.ru/game/<tid>/<gid>/protocol/ — the goal-times channel (VERIFIED round 2)
(NB: the tab-less form `/game/<tid>/<gid>/` is a 404 — tabs are mandatory.)
Verified on 898094 (517 KB) + openers 881261/885442/889850 (498-523 KB):
- **«Заброшенные шайбы» table**: per goal — number, period, cumulative
  game clock (`01′23′′` format), running score, strength state (glossary:
  рав./бол./мен./буллит — NO empty-net state), scorer + up to 2 assists
  (with season totals), and **on-ice jersey lists for BOTH teams** ->
  EN goals resolve from goalie-number absence in the scoring context
  (Magnus Joueurs-list method, but with full on-ice data). Solves the
  text channel's missing goal times.
- **«Штраф» fineTable**: per team — time (cumulative), player, minutes,
  offense text, per-period totals. Together with the text channel's
  back-to-full-strength events: penalty begin AND end covered.
- Full per-player stat tables (incl. goalie TOI), team stats,
  special-teams section. **Coaches NOT on this page** (nav-menu hits
  only) — the TEXT page is the coach channel.

### /resume/ — summary page, NOT in artifact set (decision, round 2)
317 KB on 898094: video highlights, match stats, goals recap, post-game
standings. No capability content beyond protocol+text -> not fetched for
the lake.

### en.khl.ru — English mirror exists (proto verified on 898094, 494 KB,
"Goals" table with glossary). RU stays the authority; EN NOT in the
artifact set (no additional content, doubles size).

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

## Capability bar vs MAGNUS_DATA_GAPS — COMPLETE (rounds 1+2)

| Capability | KHL finding | Verified on (named) |
|---|---|---|
| Goalie in/out with times | YES — explicit paired events, game clock, ALL 4 seasons | 898094; 885442 (3 pairs); 889850; 881700 |
| Multi-pull windows | YES — each out/in event explicit | 898094 (58:33/58:47/59:11); 889850 |
| Mid-game substitution vs pull | separable: `Замена вратаря. <Team>. <new> вместо <old>` distinct class | 881261 (Паскуале за Кошечкина) |
| Delayed-penalty visibility | YES — explicit dp event + observed dp-pull episode | 898094 |
| Penalties | protocol table (time+player+minutes+offense per team) + text back-to-full-strength END events | 898094 both channels |
| Goal times + strength | protocol goals table: period, cumulative clock, running score, рав/бол/мен/буллит | 898094 (8 goals) |
| EN goals | on-ice jersey lists per goal (goalie absent) + ВППВ per-player EN-TOI | 898094 |
| Coach per game | YES — text-page preview-frame, both teams | 898094 (Кравец/Десятков); 881261 (Фёдоров, 2022-23) |
| Event timeline granularity | curated broadcast 42-90 events/game + protocol tables | all 6 sampled games |
| Live feed | online.khl.ru + webcaster video API (Sept shakedown scope) | — |
| Archive depth 2022-25 | CONFIRMED: full-weight pages, structured events present | 881261/881700/885442/889850 |

Known feed quirks for the adapter (recorded now, handled later): duplicate
penalty line (898094 51:57), mixed clock semantics (play events = game
clock, period boundaries = wall clock), goal lines in text channel carry
no time (protocol is the time authority), free-text commentary mentions
goalies constantly (counts must scope to structured `textBroadcast-item`
lines — ticker lesson analogue, proven on 885442's "15 page-wide pulls"
that are 3 real ones).

## Sizing (FINAL, real bytes from rounds 1+2)

Artifact set per game: text (720-870 KB) + protocol (500-525 KB) ≈
**1.3 MB/game raw** -> 3,060 games ≈ **4.0 GB raw**, ~1 GB/season.
Boilerplate-heavy HTML compresses ~5-6x in git packs -> est. 150-250 MB
packed per season.
**Proposed lake plan (Seb to ratify by running the fetch)**: single orphan
branch `khl-data-lake` (Mestis convention), ONE COMMIT + PUSH PER SEASON
(each push est. <300 MB, safely under GitHub's 2 GB/push limit). Cloud
verification uses per-season sparse-checkout (session disk allowance
can't hold 4 GB + workspace). Fallback if a push is rejected on size:
per-season branches `khl-data-lake-<year>` — decision recorded here
before fetch per kickoff §2.
Fetch time: 6,120 game fetches + 4 calendars at 0.7 s delay ≈ **2.5-3.5 h
full run**; per-season runs ~40-50 min. fetch_khl.py is resume-safe
(manifest+disk skip), retries 3x with backoff, flags small/truncated
payloads, and REFUSES to fetch a season whose scoped calendar count
mismatches the verified expectation.

## Market note (Manager, on record)

Odds provider has NO icehockey_khl market. Lake serves coach intel +
model-side lines (ruling 5). Seb ordered with this heard.

## Open items (fetch phase)

1. Smoke run (`--season 2026 --limit 3`), verify payloads + manifest, then
   full per-season runs on the PC.
2. Lake branch mechanics paste-block (orphan `khl-data-lake`, per-season
   commits, .gitattributes carried, manifest re-hash after every
   push/pull — the autocrlf incident makes this non-negotiable).
3. tools/verify_khl_lake.py: 0 missing/0 stray vs scoped calendar id set
   both directions, 0 truncation flags, manifest re-hash, seeded-random
   spot-opens re-checking capability rows on real games (scoped counts).
4. Round-2 manifest re-hash on cloud: 0/10 altered (.gitattributes works).
