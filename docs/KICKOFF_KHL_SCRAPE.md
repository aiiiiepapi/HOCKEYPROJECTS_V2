# Kickoff prompt — KHL scraping session (written by Manager, 2026-08-03)

Paste the block below into a NEW session created WITH push capability:
either a desktop Cowork task set to "Run this task: On your computer", or
a cloud session with aiiiiepapi/HOCKEYPROJECTS_V2 attached as a GitHub
source at creation (the cloud git proxy blocks pushes otherwise — two
sessions died on this on 2026-08-03; see the SHL kickoff saga).

Scope fence identical to SHL/Mestis: LAKE + RESEARCH ONLY. Branch
`khl-scrape` for docs/fetchers; raw data to V2-repo orphan branch
`khl-data-lake` (lake-on-V2 convention). Never touch master.

MARKET NOTE (Manager, from the odds catalog 2026-08-03): our odds
provider carries NO KHL market (icehockey_khl absent; NHL/AHL/Liiga/
Mestis/both Swedish leagues present). The lake still serves coach intel
+ model-side lines (ruling 5); Seb ordered the scrape with this on
record. Sizing: KHL is the BIGGEST lake yet — ~20-23 teams, 62-68 games
each, ~650-750 regular-season games/season.

---PASTE FROM HERE---

You are a Scraping session for HOCKEYPROJECTS V2. Your ONLY mission:
build and verify the raw data lake for the KHL. You do NOT build
adapters, models, ledgers, or products — that belongs to the Manager
session. Work on branch `khl-scrape` of the V2 repo (create from master;
never commit to master, never commit tokens).

FIRST ACTION before any discovery: clone
github.com/aiiiiepapi/HOCKEYPROJECTS_V2 (master), create branch
`khl-scrape`, empty commit, PUSH, and confirm the push succeeded. If it
fails with a proxy/403, STOP and tell Seb — the session was created
without push capability and must be recreated.

Then read, in order: CLAUDE.md in full (rules 0, 0b, 1-15b bind you);
docs/DECISIONS.md ruling 42 (attribution gate — every claim verified on
an actual fetched sample; "artifact/noise" is the first hypothesis for
any surprising count); docs/MAGNUS_DATA_GAPS.md (capability bar);
docs/MESTIS_SOURCE.md + docs/MESTIS_LAKE_VERIFICATION.md (quality
template — INCLUDING the ticker lesson: game pages may embed OTHER
games' events; every per-game count must be provably scoped to the
game's own event container); docs/KICKOFF_SHL_SCRAPE.md (the sibling
brief — match its discipline).

Environment facts: raw responses kept VERBATIM, never edited; fetchers
are fetch-only, stdlib-only, and run on Seb's Windows PC when the
session's own network can't reach the source (verify per endpoint).
Seb prefers paste-block PowerShell over .bat downloads.

Mission, in order (rule 1: real data in the first 10 minutes):
1. DISCOVERY — check, never assume:
   (a) khl.ru / en.khl.ru — game pages, text broadcasts, and whatever
       JSON the site or the KHL mobile apps load per game (historically
       the apps use JSON endpoints; find them from page network calls).
   (b) Any official stats portal the KHL exposes (protocol/game-sheet
       pages with events, lineups, coaches).
   (c) GEO/ACCESS check early: verify khl.ru is reachable from the
       session AND from a US/EU residential connection (Seb's PC) —
       Russian sites may geo-block or throttle; document precisely what
       works from where. If a source is unreachable everywhere we can
       run code, STOP and report options.
   (d) LANGUAGE: event feeds may be Russian-only ("вратарь" = goalie;
       goalie-out/in events, empty-net markers). Keep raw text verbatim
       in the lake; translation/decoding is adapter work — but the
       capability table must state exactly which Russian phrases mark
       goalie out/in, EN goals, penalties, verified on named games.
   Deliverable: docs/KHL_SOURCE.md on your branch — endpoints, auth, id
   schemes, season coverage, payload contents, capability table vs the
   MAGNUS bar (goalie in/out with times? EN flags? penalties
   begin+minutes or begin+end? coach per game?), each row verified on a
   NAMED fetched game.
2. COVERAGE — last 4 completed seasons (2022-23..2025-26), regular
   season only. Verify teams/games per season from the source (expect
   ~650-750/season — the biggest lake yet; plan fetch time and lake
   size accordingly, and confirm the repo can take it or propose
   splitting by season branch BEFORE fetching). Identify the official
   schedule authority and reconcile 1:1 both directions.
3. FETCHER — tools/fetch_khl.py: stdlib-only, fetch-only, resume-safe,
   sha256 manifest per season (file/bytes/url/utc), polite delay
   (>=0.5s; KHL volume means a full season takes hours — make resume
   bulletproof). PC-run paste-block PowerShell delivered to
   Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\ via device tools if
   the session can't fetch directly.
4. LAKE — verbatim files to V2-repo orphan branch `khl-data-lake`,
   layout `khl/<END_YEAR>/` + per-season schedule authority + manifest
   + lake-root COMPLETENESS.md.
5. VERIFICATION (lake-level only) — 0 missing vs schedule authority
   both directions, 0 strays, 0 truncated, manifests re-hashed after
   any transfer, seeded-random spot-opens confirming capability rows on
   real games, all counts SCOPED. Ship tools/verify_khl_lake.py.
6. HANDOFF — docs/HANDOFF_KHL.md: per-season counts, quirks, capability
   table, open questions. The Manager verifies per rule 0 and merges —
   your "done" is a claim, not a verification.

Hard rules: no bet-relevant conclusions; never edit raw payloads; every
claim verified on a fetched sample; auth that can't be obtained = STOP
and report; commit+push every working block; answer Seb with concrete
numbers immediately; if something looks off, it IS off (rule 10).

---PASTE ENDS HERE---
