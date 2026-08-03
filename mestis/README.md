# Mestis raw data lake (regular season / runkosarja)

Built 2026-08-03 by the Mestis scraping session (V2 branch mestis-scrape).
Raw HTTP response bytes, VERBATIM — never edit any file in this lake.

Sources:
- mestis.fi game pages (kokoonpanot/seuranta/tilastot HTML) + season ICS
  schedules (the reconciliation authority) + season list pages.
- tilastopalvelu.fi /ih/game/helpers/getRosters.php JSON per game
  (game-level staff incl. head coach) + statgroup maps.

Layout: one dir per season END year (2023 = 2022-23).
Per-season manifest_<year>.json: sha256/bytes/url/fetched_utc per file.
COMPLETENESS.md: verification report (0 missing vs schedule, all seasons).
Docs: HOCKEYPROJECTS_V2 docs/MESTIS_SOURCE.md + docs/HANDOFF_MESTIS.md.
