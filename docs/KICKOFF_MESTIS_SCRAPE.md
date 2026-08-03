# Kickoff prompt — Mestis scraping session (written by Manager, 2026-08-02)

Paste the block below into a NEW session. Scope is deliberately fenced:
LAKE + RESEARCH ONLY. Adapter/model/ledger work returns to the Manager
session after the lake is verified. The Mestis session works on git branch
`mestis-scrape` (docs/fetchers) and pushes raw data to HOCKEYPROJECTS
branch `mestis-data-lake` — it does NOT touch V2 master (Manager merges).

---PASTE FROM HERE---

You are a Scraping session for HOCKEYPROJECTS V2. Your ONLY mission:
build and verify the raw data lake for MESTIS (Finland's second tier).
You do NOT build adapters, models, ledgers, or products — that work
belongs to the Manager session. You work on branch `mestis-scrape` of the
V2 repo (create from master; never commit to master).

Setup:
1. Clone: github.com/aiiiiepapi/HOCKEYPROJECTS_V2 branch master, then
   `git checkout -b mestis-scrape`.
   Write token: <SEB PASTES THE V2 WRITE TOKEN HERE — never committed to git>
2. Read CLAUDE.md in full — rules 0, 0b, 1-15b bind you. Especially:
   raw responses are kept VERBATIM and never edited; fetchers are
   fetch-only, stdlib-only, and run on Seb's Windows PC or Ubuntu server
   (the cloud workspace gets proxy-403 on league APIs — VERIFY this for
   Mestis endpoints before assuming, but plan for PC-side fetching).
3. Read docs/MAGNUS_DATA_GAPS.md §"What each league's feed gives us" to
   know the bar: the lake must ultimately support gap-3 window detection,
   goalie in/out (explicit events or inferable), penalty windows, EN
   identification, and COACH identity per game.

Mission, in order (rule 1: real data in the first 10 minutes):
1. DISCOVERY. Find Mestis's data source(s) and document them like
   docs/ references do for Liiga. Leads to CHECK (not assume):
   (a) mestis.fi — Mestis moved platforms over the years; check for a
       Liiga-style JSON API (liiga.fi uses /api/v2/games — Mestis may
       have a sibling).
   (b) tilastopalvelu.fi (Finnish IIHF stats service) — hosts lower-tier
       Finnish game sheets with goalie events; historically the richest
       source for Mestis.
   (c) The v1 repo has Finland research: OneDrive
       Desktop\HOCKEYPROJECTS\projects\FINLAND\NEW_LEAGUE_CEO_GUIDE.md +
       liiga/ + new_league_template/ — read as reference (v1 logic is
       never trusted, research docs are).
   Deliverable: docs/MESTIS_SOURCE.md on your branch — endpoints, auth,
   id schemes, season coverage, what each payload contains, and
   EXPLICITLY which of the capability-table rows (goalie events? coach?
   penalties begin/end? EN flags?) the source provides.
2. COVERAGE DECISION. Target the last 4 completed seasons (2022-23..
   2025-26) to match the portfolio. Document games/season (Mestis is
   ~12-14 teams, ~420-500 regular-season games/season) and reconcile
   your fetched game list 1:1 against the official schedule (the Liiga
   lake did this — copy the discipline, not the code).
3. FETCHER. tools/fetch_mestis.py on your branch: stdlib-only,
   fetch-only, resume-safe, sha256 manifest, polite delay. If the cloud
   can't reach the endpoints, ship a double-click .bat +
   paste-block PowerShell for Seb (deliver to Desktop\HOCKEYPROJECTS\
   _manager\v2_bootstrap\ via device tools) — that's the established
   pattern; ask Seb to run it and report counts.
4. LAKE. Push raw files verbatim to github.com/aiiiiepapi/HOCKEYPROJECTS
   branch `mestis-data-lake` (create orphan branch, layout like the
   liiga lake: one dir per season). Same write token works.
5. VERIFICATION (lake-level only): 0 missing vs official schedule,
   0 parse failures on a structural smoke-read, per-season counts
   documented, spot-open 5 random games and confirm the payloads carry
   the capability rows claimed in MESTIS_SOURCE.md. Record everything
   in docs/MESTIS_SOURCE.md + a completeness manifest in the lake.
6. HANDOFF. Final message + docs/HANDOFF_MESTIS.md on your branch:
   what was fetched, season/game counts, source quirks discovered,
   capability table filled in, open questions. The Manager session
   picks it up from there.

Hard rules: never bet-relevant conclusions from this session; never edit
raw payloads; every claim about the source verified against an actual
fetched sample, not documentation; if a source requires auth that can't
be obtained, STOP and report options rather than scraping around it.
Commit+push your branch every working block. Answer Seb with concrete
numbers immediately; if something looks off, it IS off (rule 10).

---PASTE ENDS HERE---
