# KHL scrape session — handoff (living doc, updated per working block)

Session branch: **claude/khl-scrape-f5emx6** (the environment renamed the
kickoff's `khl-scrape` at creation — Manager: treat this as the khl-scrape
branch). Push capability CONFIRMED 2026-08-05 (empty commit + this block
pushed via session GitHub App auth; no token involved).

## State (2026-08-05, block 1)

- Required reading done. NOTE for Manager: `docs/MESTIS_SOURCE.md` does
  NOT exist on master (kickoff points to it) — presumably it lives only on
  the `mestis-scrape` branch; the ticker lesson was absorbed from
  `docs/MESTIS_LAKE_VERIFICATION.md` + the SHL kickoff instead.
- **Cloud session cannot fetch KHL at all**: shell proxy CONNECT-403s every
  non-allowlisted host; WebFetch 403s all khl.ru hosts AND wikipedia/
  archive.org, so the block is (at least partly) our egress policy —
  geo-block vs bot-block vs proxy CANNOT be distinguished from here.
  Full detail: docs/KHL_SOURCE.md reachability matrix. All fetching runs
  on Seb's PC (standing convention; kickoff anticipated this).
- Discovery via search (no fetched samples yet): season structure + all 4
  regular-season tournament ids pinned (1154/1217/1288/1369 = 748/782/782/
  748 games, **3,060 total** — above the kickoff's 650-750/season
  estimate), khl.ru URL patterns (calendar/standings/game), text.khl.ru
  format with a named 2025-26 sample (898094 Barys-Lada), platform-global
  game-id hypothesis (id-range sweeps wrong; enumerate from calendar).
- **tools/probe_khl.ps1 shipped** — paste-block for Seb: reachability
  stage + verbatim named samples (4 calendars, text broadcast, game-page
  guesses, mobile-API candidates) into tests/reference_raw/khl_probe/ with
  a manifest, then commits+pushes this branch. AWAITING PC RUN.
- Repo-size check (mandated): master pack ~3.4 MiB; decision rule for the
  lake documented in KHL_SOURCE.md §Sizing (per-season branch split if
  projected packed size >~1.5 GB; final numbers after probe measures real
  bytes/game).

## Open questions

1. Seb: run tools/probe_khl.ps1 (paste-block also delivered in chat).
2. If khl.ru blocks even residential — options to discuss: mobile-API
   host (webcaster.pro may be served from EU CDN), or a VPN egress; NOT
   proceeding without Seb's call (kickoff: unreachable everywhere = STOP).
3. Lake branch layout (single vs per-season) — decision after probe sizes.

## Not started (blocked on probe)

Capability-table verification on named games, tools/fetch_khl.py against
verified endpoints, schedule-authority reconciliation, lake fetch,
tools/verify_khl_lake.py.
