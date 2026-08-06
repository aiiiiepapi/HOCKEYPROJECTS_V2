# Kickoff prompt — SHL ADAPTER session (written by Manager, 2026-08-07)

Build session, not a scrape: the verified lake exists (branch
`shl-data-lake` tip 6b77add — NEVER read root 03d8547, it predates the
CRLF repair). Scope: adapter + ground truth + extraction + audit +
gates, ON YOUR BRANCH. NO ledger, NO pricing, NO bet-relevant
conclusions — bet-facing numbers are Manager work post-merge (Magnus
precedent). Create the session with the repo attached (or run
on-computer); FIRST ACTION: branch `shl-adapter` (environment may
rename it — fine), empty commit, push, confirm success before anything.

## Read, in order (all on master unless noted)

1. CLAUDE.md — rules 0/0b/1-15b bind you. Rule 2 is the spine of this
   job: HAND-TRACE ground truth from raw HTML BEFORE writing adapter
   code. Rule 15: gap detection exists ONCE (hockeycore/gap/segments.py)
   — you write an adapter that emits the interval game dict, never gap
   logic.
2. docs/DECISIONS.md — esp. rulings 17/17b (dp artifact clauses — the
   shared engine applies them; know what they mean), 34-38 (what the
   Mestis finalization fixed), 42 (attribution gate: every surprising
   count is YOUR artifact until proven otherwise).
3. docs/SHL_LAKE_VERIFICATION.md — the Manager's adjudication contains
   THREE BINDING ADAPTER RULES: (i) swe Events channel = PRIMARY (all 4
   seasons); shl.se pbp = independent AUDIT channel (2024+ only);
   (ii) pbp goalkeeper events deduped by (period, time, team) keeping
   the latest revision; (iii) 60:00 / OT-end "GK Out" rows are
   bookkeeping, never pulls, and their absence in pbp is uninformative.
4. docs/HANDOFF_SHL.md + docs/SHL_SOURCE.md on branch
   `claude/shl-scrape-ly11nk` (copy both to your branch so they reach
   master at merge). Quirks that WILL bite: events rows are
   NEWEST-FIRST; 00:00 "GK In" = starters; cumulative clock includes
   OT times (62:05-style); Swedish decimal commas; away team names
   render SHORT on some schedule rows; GWS/shootout goal-row variant
   (winner row may differ from header by 1).
5. hockeycore/leagues/mestis.py + ahl.py + liiga.py — the pattern to
   match. Docstring documents every verified convention with named
   games, like those do.

## The job, in order

1. **GT batch first (rule 2).** Hand-trace ~12 games from raw Events
   HTML (dumb text-dump helper allowed; no adapter logic) covering: EV
   pull, pp_pull (leader minor active at first evidence), no-pull
   gap-3, carryover-at-open, multi-pull, pull-to-horn, widened/narrowed/
   end_of_game closes, an OT and a shootout game, a mid-game goalie
   substitution (must NOT read as a pull), an ENG-creates-instance case,
   and at least one of the 21 blank-coach games. Record
   tests/ground_truth_shl.json + docs/ground_truth_traces/shl_batch1_
   <date>.md + copy the games' raw files to tests/reference_raw/shl/.
   Mestis precedent: tests/ground_truth_mestis.json format, gate
   test_mestis_ground_truth assertion set.
2. **Adapter: hockeycore/leagues/shl.py.** Emits the segments.py
   interval dict: goals (t cumulative secs, side, period, en, types),
   empty{home,away} intervals, penalties (side, t, begin, end,
   misconduct) — SHL gives EXPLICIT begin-end windows: use them
   directly (do NOT copy AHL's minutes-approximation; DO keep the
   >=10min misconduct classification and the same-second OUT-first
   normalization). ENG flag maps to en=True; inherit the AHL/Mestis
   EN evidence-repair rules verbatim (synthetic segment for flagged
   goals with no interval; en-correction for covered goals missing the
   flag). Coaches from LineUps (primary) + data/coach_maps/
   shl_coaches.csv fallback which YOU build for the 21 blank sides
   (adjacent-games bracketing evidence per side, Mestis
   mestis_coaches.csv format with an evidence column; the HV71 8 are
   one habit — check whether one coach spans all of them).
3. **Runner: hockeycore/gap/run_shl_lake.py** (mirror run_mestis_lake:
   lake at /home/claude/work/shl_lake/shl, abort on any instance whose
   trailing side lacks a coach). Output data/derived/
   shl_instances_gap3.json with season/game_id/date/home/away/coach/
   leader_coach.
4. **Audit: extend tools/audit_interval_random.py with "shl"** — the
   independent channel is the shl.se pbp goalkeeper events (2024+;
   apply the dedupe + bookkeeping rules). 2023 has no second channel:
   restrict the audit sample to 2024-2026 and say so in the docstring.
   Seed 20260807, 30+30, 0 disagreements is the bar.
5. **Gates on your branch**: test_shl_ground_truth (exact-value,
   Mestis assertion set + adapter-level empty-interval pins),
   test_shl_derived_instances (structural, rule 14: per-season bounds,
   pulled-share band, coach non-null), test_shl_random_audit (skip if
   lake unmounted). Full suite must be green INCLUDING all existing
   gates before handoff.
6. **Handoff: docs/HANDOFF_SHL_ADAPTER.md** — GT trace summary,
   extraction counts (games, instances/season, pulls EV/pp), audit
   result, quirks discovered during build (there WILL be some — record
   with named games), open adjudications for the Manager. Everything is
   a claim until the Manager re-derives it.

## Environment facts

- Lake: `git worktree` or clone of branch shl-data-lake AT 6b77add;
  symlink /home/claude/work/shl_lake -> the checkout root (the dir
  containing shl/). ~176 MB packed.
- pip install pytest numpy --break-system-packages; pip install -e .
  from the repo root.
- Expected order of magnitude (Manager's raw scan, NOT targets to hit —
  rule 0 means you derive your own): ~5.2-5.5 goals/gm, 59-63% of games
  with a late GK out RAW (unconditioned incl. swaps), median out
  ~57:55-58:07, ENG ~100/season, 19-23 HCs/season. Gap-3 instance
  projection ~600-700 total — if you land wildly off these, suspect
  your parsing FIRST (rule 42), then escalate, never adjust silently.

Hard rules: never edit raw payloads; every convention claim verified on
a named game; commit+push every working block; answer Seb with numbers
immediately; if it looks off, it IS off (rule 10). The Manager verifies
per rule 0 and merges to master — your branch never touches master.
