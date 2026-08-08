# DEL coach map — build notes

**Status: SCHEMA ONLY, ZERO ROWS.** Nothing is populated, because this
session cannot reach any source to populate it from (see
`docs/HANDOFF_DEL.md`). An unpopulated map is the honest state; a map filled
in from memory would be fabricated data (rule 4) and coach identity is the
join key for every downstream coach number.

## Why DEL needs a full map, not a fallback map

Every other league's map is a *patch*: the listing wins and the map fills
blanks (AHL 8 blank blocks, Mestis 19, SHL 21). DEL is different — ruling 51
established that head coaches appear on **neither the game pages nor the
squad pages**. So this map is not a patch, it is the **only** coach source,
and it has to cover every team in every season with dated spells.

That raises the bar in one specific way: **mid-season changes must be dated
correctly or games get attributed to the wrong bench.** A season-level
"team X → coach Y" mapping is not good enough and must not be accepted.

## Schema

| column | meaning |
|---|---|
| `season` | as the lake names it, e.g. `2025-26` |
| `team` | the club slug exactly as it appears in the fixture URLs (e.g. `erc-ingolstadt`), so the join needs no name normalisation |
| `coach` | head coach, one name |
| `start_date` | first date this coach is HC (`YYYY-MM-DD`), inclusive |
| `end_date` | last date inclusive; season end if never replaced |
| `source_url` | **primary source, one per row, mandatory** |
| `notes` | anything a re-deriver needs (interim, caretaker, announcement vs first game behind the bench) |

Spells within a team-season must be contiguous and non-overlapping, and
together must cover the whole season. That is a checkable property and
should become a gate once rows exist.

## Do not invent the team list

Derive it from the lake: the fixture URLs carry `{home}` and `{away}` club
slugs, so `tools/fetch_del_raw.py --schedule` yields the exact set of clubs
per season, including promotion/relegation churn. Do not type a team list
from memory — that is precisely how a stale club set silently drops games.

## Leads to verify (NOT to trust)

Ruling 51 names Elite Prospects team-staff-history pages as the lead, e.g.
`eliteprospects.com/team/445/erc-ingolstadt/team-staff-history` and
`/team/475/iserlohn-roosters/team-staff-history`. Treat these as a starting
point that still needs a primary source per row:

- Elite Prospects is **user-maintained**, so it is a lead, not a primary
  source. For a mid-season firing, cite the club's own announcement or a
  named news report with a date.
- Prefer the **first game behind the bench** over the announcement date when
  they differ — the map joins to games, not to press releases. Record which
  one the row used in `notes`; the two are often days apart.
- Interim/caretaker spells are real spells. Give them their own rows.

## Verification before this map is used for anything

1. Every team-season fully covered, no gaps and no overlaps.
2. Every row carries a working `source_url`.
3. Club slugs match the fixture slugs exactly (join test against the lake).
4. Spot-check a sample of mid-season changes against a second independent
   source, the way `mestis_coaches.csv` pinned the Tuunanen firing.
