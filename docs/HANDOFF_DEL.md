# HANDOFF — DEL scrape session, Round 2 corrections (2026-08-08)

Branch `del-scrape`, rebased onto master at ruling 53. Master untouched.
Lake branch `del-data-lake` exists (`.gitattributes` `* -text` only).

**All three defects from `docs/DEL_ROUND2_FINDINGS.md` are fixed, plus a
fourth of the same family that I found while testing the fix.** Nothing is
re-run here — this session still has no egress — so every number below is
the Manager's from the sampled bytes, not mine.

## Defect 1 (critical) — month pagination. FIXED.

`--schedule` now fetches **every month**, not the default one.

The mechanism isn't in the static HTML, so it's discovered at runtime:
parse the month `<select>` if present, else synthesise Sep–Apr from the
season slug; then try each candidate parameter shape (`monat`, `month`, `m`,
`spieltag`, `page`, `date`, `zeitraum`).

**The acceptance test is the important part.** A candidate is accepted only
when the response **content hash differs from the default page AND it yields
fixtures the default page didn't have.** That is deliberately the same
lesson as Defect 2: an ignored query parameter returns a cheerful HTTP 200
with the default month, so status codes would re-create the original bug in
a new place. If no shape works, it saves the DataTables JS asset, prints
every URL-ish and param-ish string found inside it, and tells the operator
to read those or watch the network tab — it does **not** quietly proceed.

**Completeness check** (rule 14 — structural, never an absolute total):
clubs and games/team are derived from the fixtures themselves, so it
survives promotion/relegation and league-size change. A season is flagged
INCOMPLETE if all fixtures fall in one month, if fewer than 5 months are
covered, or if games/team is under 30 (a full DEL season is ~52; one month
is ~6). Any flag prints `*** DO NOT RUN --full`.

My earlier "seasons that return 0 may not exist in the archive" caveat was
wrong and is gone — those seasons exist, we had fetched one month of each.

## Defect 2 — five copies of one page. FIXED.

One page per game now. The four tab URLs are never fetched, and
`TABS_NOT_FETCHED` documents why with the sha256 so nobody re-adds them.

The probe's channel check is rewritten to compare **content hashes**, and
per your instruction the lesson is a gate rather than a comment:
`test_channel_check_compares_content_not_status` builds three byte-identical
"channels" plus one genuinely different document and asserts that four
successful URLs collapse to two distinct documents. It's written against the
generic checker, not against DEL, because the next JS-rendered source will
spring the identical trap.

## Defect 3 — projection arithmetic. FIXED.

The projector counts **every season with a fixture list**, not just sampled
ones, and marks which seasons are projected from another season's average.
It also refuses to dress up a broken number: if any season is flagged
incomplete it prints `projection is meaningless for <seasons>`.

## Defect 4 — found while testing the fix, same family

With the network dead, `--schedule` printed `TOTAL 0 games` and then **"All
seasons pass the structural completeness check."** A total fetch failure was
reporting as a pass. Fixed: failed seasons are tracked separately, and the
pass line only prints when at least one season actually produced fixtures
and nothing was flagged. Worth naming because it's the Defect-3 failure mode
exactly — a summary line that looks precise and means nothing.

## Recorded in `DEL_SOURCE.md`

- The event table verbatim, with the cumulative clock.
- **`Drittelstart` / `Drittelende`** — period boundaries are explicit and
  don't need to be inferred from the clock.
- Penalty offence codes `DELAY` / `TRIP` / `ROUGH` / `SLASH` / `CROSS`, and
  that goalie rows carry name + shirt number, so goalie identity is
  available per event.
- Month pagination and the duplicate-tab sha256, both as confirmed findings.
- Corrected size: ~247 KB/game, **~360 MB** for the whole four-season lake.
- The provenance header now separates byte-derived facts from
  WebFetch-derived ones, since those are no longer the same evidence class.

### The ruling-17 warning, carried into the source contract

Game 2580's three cycles — 10s, 24s, 95s inside three minutes — are written
into `DEL_SOURCE.md` under an explicit warning heading: **do not read
`Torhüter aus dem Tor` as "pull"**. DEL exercises rulings 17/17b from day
one, and an adapter that counts every `aus dem Tor` will manufacture phantom
pulls at scale. Ruling 46's KHL dp cross-calibration is cited as the
reference. It should be repeated in the adapter kickoff, not left to whoever
reads the source doc carefully.

## Gates

**34 passed, 4 skipped** (skips are unmounted AHL/Liiga/KHL lakes). Four DEL
gates now: the ratified detector calibration, fixture-parser scoping, the
new content-vs-status channel check, and the new month-completeness flag.

## What I could not do, and what I need

Still no egress from this session — WebFetch returns `EGRESS_BLOCKED` for
`penny-del.org`, `eliteprospects.com` and `en.wikipedia.org` alike, so the
corrected fetcher is **unrun**. I have deliberately reported no fixture
counts, no reconciliation and no projection of my own.

**The corrected fetcher is ready for Seb.** Order of work as you set it:

1. `FETCH_DEL_LAKE.bat schedule` — the one that matters. It will either
   discover the month mechanism and report real per-season depth, or fail
   loudly with the JS strings needed to find it by hand. Send the console
   output either way; if it can't find the mechanism, the network tab while
   changing the month selector is the fastest path and the shape goes into
   `MONTH_PARAMS`.
2. `reconcile`, then `sample` — expect ~247 KB/game and ~360 MB.
3. `full`, `verify`, then the lake onto `del-data-lake`.

Two things stay open and neither blocks the lake: the second audit channel
(ruling 52 — proceed) and the coach map, which still needs primary sources
per row and is now confirmed unavoidable, since the per-tab tables aren't
reachable over plain HTTP at all.

Scope fence held: no adapter, no gap logic, no instances, no ledger, no
coach numbers. Everything is a claim for the Manager to re-derive.
