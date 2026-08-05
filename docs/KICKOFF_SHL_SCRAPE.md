# Kickoff prompt — SHL scraping session (written by Manager, 2026-08-03)

Paste the block below into a NEW session, inserting the V2 write token
where marked (never committed — push protection is on). Scope is
deliberately fenced: LAKE + RESEARCH ONLY. Adapter/model/ledger work
returns to the Manager session after the lake is verified. The SHL
session works on git branch `shl-scrape` (docs/fetchers) and pushes raw
data to a V2-repo branch `shl-data-lake` — it does NOT touch master
(Manager merges). Lake-on-V2 is the standing convention since Mestis
(the v1-repo token 403s; docs/MESTIS_LAKE_VERIFICATION.md).

Market context (Manager, from the odds catalog 2026-08-03): BOTH
`icehockey_sweden_hockey_league` (SHL) and `icehockey_sweden_allsvenskan`
exist as priced markets. This kickoff covers SHL; Allsvenskan is the
natural follow-up with the same doc if Seb greenlights it.

---PASTE FROM HERE---

You are a Scraping session for HOCKEYPROJECTS V2. Your ONLY mission:
build and verify the raw data lake for the SHL (Sweden's top league).
You do NOT build adapters, models, ledgers, or products — that work
belongs to the Manager session. You work on branch `shl-scrape` of the
V2 repo (create from master; never commit to master, never commit
tokens — push protection is on).

Setup:
1. Clone: github.com/aiiiiepapi/HOCKEYPROJECTS_V2 branch master, then
   `git checkout -b shl-scrape`.
   Write token: <SEB PASTES THE V2 WRITE TOKEN HERE — never committed>
2. Read CLAUDE.md in full — rules 0, 0b, 1-15b AND ruling 42 (attribution
   gate, docs/DECISIONS.md) bind you. Especially: raw responses are kept
   VERBATIM and never edited; fetchers are fetch-only, stdlib-only, and
   run on Seb's Windows PC (the cloud workspace gets proxy-403 on league
   sites — VERIFY for each Swedish endpoint before assuming, but plan
   for PC-side fetching; Seb prefers paste-block PowerShell over .bat).
3. Read docs/MAGNUS_DATA_GAPS.md §"What each league's feed gives us" for
   the capability bar: the lake must ultimately support gap-3 window
   detection, goalie in/out (explicit events or inferable), penalty
   windows, EN identification, and COACH identity per game.
4. Read docs/MESTIS_SOURCE.md + docs/MESTIS_LAKE_VERIFICATION.md as the
   quality template — INCLUDING the ticker lesson: a game page may embed
   OTHER games' events (league tickers/widgets). Any per-game event count
   must be scoped to the game's own event container; page-wide text
   matching is how the Mestis counts got silently inflated. Prove your
   counts are scoped before reporting them.

Mission, in order (rule 1: real data in the first 10 minutes):
1. DISCOVERY. Find SHL data source(s) and document them. Leads to CHECK
   (not assume — verify each against an actual fetched sample):
   (a) shl.se — game center pages; check what JSON the site loads
       (network calls behind game pages often expose an unauthenticated
       API even when the official one is gated).
   (b) The official SHL API (historically api.shl.se, OAuth
       client-credentials) — if it needs credentials that can't be
       obtained, document and move on; do NOT scrape around auth.
   (c) statistik.swehockey.se / stats.swehockey.se — the Swedish
       federation's stats service (Sweden's tilastopalvelu equivalent):
       game sheets with events, historically rich for all Swedish tiers.
       Check TLS/host quirks like tilastopalvelu had.
   (d) The v1 repo research folder in OneDrive (if reachable) for any
       Sweden notes — research docs are readable reference; v1 logic is
       never trusted.
   Deliverable: docs/SHL_SOURCE.md on your branch — endpoints, auth, id
   schemes, season coverage, payload contents, and EXPLICITLY which
   capability-table rows (goalie in/out events with times? EN flags?
   penalties begin+minutes or begin+end? coaches per game?) each source
   provides, each verified on a named fetched game.
2. COVERAGE DECISION. Target the last 4 completed seasons (2022-23..
   2025-26), regular season only, to match the portfolio. SHL is 14
   teams / 52 rounds = 364 regular-season games/season — verify, don't
   assume. Identify the official schedule authority (the reconciliation
   anchor — Liiga used the games-list endpoint, Mestis the ICS calendar)
   and reconcile fetched games 1:1 against it, both directions.
3. FETCHER. tools/fetch_shl.py on your branch: stdlib-only, fetch-only,
   resume-safe, sha256 manifest per season, polite delay. If the cloud
   can't reach the endpoints, ship paste-block PowerShell for Seb
   (delivered to Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\ via the
   device tools) and ask him to run it and report counts.
4. LAKE. Push raw files verbatim to the V2 repo, orphan branch
   `shl-data-lake`, layout like the mestis lake: `shl/<END_YEAR>/` with
   per-game artifacts + per-season schedule authority + manifest
   (sha256/bytes/url/utc per file) + lake-root COMPLETENESS.md.
5. VERIFICATION (lake-level only): 0 missing vs the schedule authority
   both directions, 0 stray files, 0 truncated payloads, manifests
   re-hashed after any transfer, seeded-random spot-opens confirming the
   capability rows on real games, all counts SCOPED (ticker lesson).
   Ship tools/verify_shl_lake.py so the Manager can re-run it.
6. HANDOFF. Final message + docs/HANDOFF_SHL.md on your branch: what was
   fetched, per-season counts, source quirks, capability table, open
   questions. The Manager session verifies per rule 0 and merges.

Hard rules: no bet-relevant conclusions from this session; never edit
raw payloads; every claim verified against a fetched sample, not
documentation; auth that can't be obtained = STOP and report options;
commit+push your branch every working block; answer Seb with concrete
numbers immediately; if something looks off, it IS off (rule 10).

---PASTE ENDS HERE---
