# SHL adapter session — handoff to Manager (2026-08-06)

Scope per docs/KICKOFF_SHL_ADAPTER.md: adapter + ground truth + extraction +
audit + gates on branch `claude/shl-adapter-hockeyprojects-lbeked` (the
harness's name for the kickoff's `shl-adapter`). NO ledger, NO pricing, NO
bet conclusions. Per rule 0 everything below is a CLAIM until re-derived.
Lake read at shl-data-lake tip 6b77add throughout.

## What exists now (all on the session branch)

| Piece | File(s) | State |
|---|---|---|
| Ground truth | tests/ground_truth_shl.json + docs/ground_truth_traces/shl_batch1_2026-08-06.md + tests/reference_raw/shl/ (12 games x events+lineups) | 12 games / 12 instances hand-traced PRE-adapter (rule 2); adapter passed 12/12 first run |
| Adapter | hockeycore/leagues/shl.py | emits the segments.py interval dict; no gap logic (rule 15) |
| Coach map | data/coach_maps/shl_coaches.csv | all 21 blank sides, bracketing + primary-source evidence |
| Runner | hockeycore/gap/run_shl_lake.py | mirror of run_mestis_lake; aborts on unattributed trailing side |
| Extraction | data/derived/shl_instances_gap3.json | 1,456 games, 0 parse errors, 681 instances, 100% coach attribution |
| Audit | tools/audit_interval_random.py ("shl" mode) | 0/60, seed 20260807 (details below) |
| Gates | tests/test_v2_gates.py: test_shl_ground_truth / test_shl_derived_instances / test_shl_random_audit | full suite 28 passed / 1 skipped (skip = ahl+liiga lakes not mounted here; mestis + shl audits ran live) |
| Docs | docs/HANDOFF_SHL.md + docs/SHL_SOURCE.md copied from the scrape branch | reach master at merge per kickoff |

## Extraction numbers

- **681 gap-3 instances**: 170 / 171 / 174 / 166 by season (2023/2024/2025/2026).
  Kickoff projection was ~600-700 — inside the band.
- **40 pulled**: 28 EV pulls + 12 pp_pulls. By season: 13/170, 14/171,
  4/174, 9/166.
- **203/681 (29.8%) carryover_empty_at_open** — the SHL signature: teams
  pull at gap 1-2, eat an ENG, and the gap-3 instance opens with the net
  already empty (187 of the 221 instances opening at P3 >= 1000s are
  carryover). Down-3 pulls are RARE here (5.9% pooled vs Liiga 11.6%,
  Mestis 18.5%, AHL ~17%). 15b note: any cross-league quote of these
  shares needs clean-window composition control — the raw shares above
  are raw-and-not-comparable.
- Manager's pre-adapter baselines ALL reproduce from the adapter output:
  games with a real P3 net-empty interval 59.3/59.6/59.6/63.7% (band
  59-63%); median first-out 57:58 (band 57:55-58:07); goals/gm 5.23-5.41
  (band 5.2-5.5); ENG-flag goals 111/97/109/107 per season (~100);
  coach census 2,891/2,912 blank-count-exact, 2,912/2,912 with map.
- Segment end contexts (rule-42 dp baseline, promised in the GT trace):
  ate_ENG 19, scored_6v5 12, returned_no_event 8, horn 4,
  penalty_on_trailer 3, **penalty_on_leader 1** (2024/774501: 31s ender
  at 1114-1145, late + >25s → ruling 17 keeps it a real pull),
  **dp_artifact / dp_only_empty 1** (2024/774720: 10s scored_6v5 segment
  at 676 with no penalty event — the 17b-ii dp-goal clause fired).
  SHL's swe channel logs essentially NO
  delayed-penalty extra-attacker moments (Liiga-like n=2; vs AHL 98).
  Rulings 17/17b are close to vacuous here — applied symmetrically anyway.
  When the KHL adapter lands (explicit dp events), SHL is another league
  whose dp-thin channel could be cross-calibrated.
- 2025's 4/174 pulled is the low outlier (pooled rate implies ~10.2
  expected; P(X<=4)~1.6% uncorrected, one of four seasons tested). Ruling
  42 discipline — numbers only, competing hypotheses tested: feed change
  REFUTED (per-season density stable: intervals/gm 0.78-0.90, goals
  5.2-5.4, EN share stable); parser misses REFUTED as far as the audit
  reaches (all 4 of 2025's pulls and 2025 no-pulls in the audited sample,
  0 disagreements). What the design cannot distinguish: real behavioral
  wobble vs sampling noise at n=170/season. No story shipped.

## Audit (tools/audit_interval_random.py shl)

Independent channel: www.shl.se gameday pbp goalkeeper events (2024+;
adjudication 1 in docs/SHL_LAKE_VERIFICATION.md). Season 2023 excluded —
no second channel exists (liiga-2023 precedent). **Only 27 pulled
instances exist in 2024-2026**, so the kickoff's 30+30 is not reachable
on the pull side: the audit takes ALL 27 pulls + 33 no-pulls (total 60),
seed 20260807. Result **0/60 disagreements**.

The first run flagged 2 items; both adjudicated as audit-tool blind spots,
NOT adapter defects (fixes are in the tool, commit f53ba79):

1. **pbp dedupe key needs the player** — refinement of binding rule (ii).
   (period, time, team) collapses same-second cross-goalie pairs:
   2025/882274 P3 00:00 has Clara `isEntering=false` + Lindbäck
   `isEntering=true` (a period-break goalie SWAP) which the 3-field key
   collapsed into a phantom net-empty open covering all of P3. Revision
   duplicates (774444's case) repeat the SAME player, so
   (period, time, team, playerId) + keep-latest-revision handles both,
   with OUT-first at the same second (swaps become zero-length).
   → Manager: please ratify the amended dedupe rule.
2. **Carryover excuse** — 2024/774518: both channels agree the net was
   empty (3326,3580); the ENG-created window opens at 3544 inside it.
   The engine's GT-pinned semantics (carryover noted, never pull
   evidence) now excuse in-window raw seconds when NO raw interval
   begins inside the window. Generic across leagues; mestis standing
   audit re-run with the modified tool on a mounted lake: still 0/60.

## Quirks discovered during build (named games)

- **Offsetting/coincident penalties carry placeholder windows** —
  `(00:00 - )` or `(00:00 - MM:SS-duration)` — meaning NO box time was
  served (scrum cancellations). League-wide census: 1,218 zero-begin
  open-end rows, 1,214 with a same-second opposite-team penalty; the 4
  unpaired are near-second scrum rows (882280 34:56 window vs 34:27
  scrum; 1004594 2s-apart pair; 1004662 goalie UC). The feed nets out
  cancellation itself: in 882280's 5-penalty scrum only the ONE
  uncancelled minor got a real window. Adapter: begin==0 with t>0 →
  begin=end=t (whistle marker, no strength effect). Verified in GT
  (628979 59:07 quad, 774444 x3 pairs).
- **Section-vs-clock misfiling, exactly one game**: 774455 has P3 GK
  rows (57:10 Out / 58:30 In) filed under "1st period". Clock is
  cumulative and league-verified → clock priority; league-wide scan
  found no other instance in 1,456 pages.
- **GWS sections**: every shootout game has BOTH "Game Winning Shot"
  (winner row, EMPTY time cell, `H-A (GWS)`) and "Game Winning Shots"
  (attempt rows with Missed/Scored in the time cell). Winner row is the
  header-score off-by-one (628968). Excluded by section, plus the empty
  time cell never parses as an event.
- **Degenerate penalty windows are inert by construction**: GM windows
  like `(05:00 - 60:00)` / `(60:00 - 60:00)` (774444), OT-clamped
  `(61:40 - 60:00)` end<begin (774479) — misconducts have no strength
  effect and end<begin never covers an evidence time.
- **Double minors** = two same-second rows with consecutive explicit
  windows (628964 24:48). Real, both kept.
- **60:00 / OT-end GK Out bookkeeping needs NO special-casing** in the
  interval machine: an Out at the period boundary opens a zero-length
  interval that is dropped; OT rows are per>3. (Binding rule iii holds
  without code.)
- **Names**: team full names from `<h2>` are stable across all 4 seasons
  (16 clubs incl. relegation churn); "HV 71" has a space in full-name
  form. Coach names arrive "Last, First" → emitted "First Last".

## Open adjudications for the Manager

1. **pbp dedupe rule amendment** (above) — ratify (period, time, team,
   playerId).
2. **"Johan Lindholm" = Johan Lindbom** (629332, 2023-02-14 sheet spells
   the HC "Lindholm, Johan"; every neighboring game says "Lindbom").
   Listing-wins keeps the raw spelling in that game's attribution → one
   phantom coach identity if profiles ever key on this game. Needs a
   normalization ruling (adapter-side alias vs ledger-side merge).
   Same shape: **"Anders Burström" one-off** (629012, 2022-10-08)
   between Rönnberg listings — plausibly a real caretaker listing,
   plausibly a sheet error; left as listed.
3. **HV71 Oct-2023 HC slot vs press**: sheets list Davidsson (774602
   10-24, 774511 10-26) and Gustafsson (774521 10-28) as Head Coach
   while club/press sources say Lindbom took over from 10-23 with both
   as assistants (hv71.se "Johan Lindbom ny huvudtränare i HV71";
   hockeysverige.se 2023-10-22). Join rule says listing wins, so those
   three games attribute to the listed names. If the Manager prefers
   press-truth here, it's a 3-game map override.
4. **Audit pull-side cap**: 27 pulls (2024+) < the kickoff's 30. All 27
   audited; no sampling on the pull side. Future seasons lift this.
5. Coach map decisions taken (for review): all 8 HV71 blanks = Johan
   Lindbom — Feb-2023 window pinned by SVT (first game 01-31 HOME vs
   Timrå = 629318 exactly, with Per Gustafsson) + smp.se/hockeysverige
   (Samuelsson fired 01-30, Lindbom announced 02-02); Nov-2023 window
   pinned by hv71.se/hockeysverige (HC from Mon 10-23, listed himself
   from 11-18). Remaining 13 sides are same-coach-both-brackets, most
   with a sole-coach-all-season backstop.

## Environment notes for re-derivation

- Lake worktree: `git worktree add /home/claude/work/shl_lake_checkout
  6b77add` + symlink /home/claude/work/shl_lake → it. Mestis lake
  mounted the same way for the cross-check re-run.
- Swedish web hosts (incl. Wikipedia mirrors of them) 403 through both
  the proxy and WebFetch; the coach-map primary sources were pinned via
  search-snippet evidence (URLs in the CSV evidence column). The
  underlying articles are PC-fetchable if the Manager wants the bytes.
