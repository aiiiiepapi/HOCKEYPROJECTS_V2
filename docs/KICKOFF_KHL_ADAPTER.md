# Kickoff prompt — KHL ADAPTER session (written by Manager, 2026-08-07)

Build session: the verified lake exists (branch `khl-data-lake` tip
4ed99df — 3,060 games, 4.14 GB, biggest in the portfolio). Scope:
adapter + ground truth + extraction + audit + gates ON YOUR BRANCH.
NO ledger, NO pricing, NO bet conclusions (Manager work post-merge).
Create the session with the repo attached; FIRST ACTION: branch
`khl-adapter` (environment may rename — fine), empty commit, push,
confirm success before anything.

## Read, in order (all on master)

1. CLAUDE.md — rules 0/0b/1-15b. Rule 2: HAND-TRACE ground truth from
   raw HTML BEFORE adapter code. Rule 15: gap logic exists once
   (hockeycore/gap/segments.py) — you emit its interval dict, nothing
   else.
2. docs/DECISIONS.md — esp. rulings 17/17b (dp clauses), 42
   (attribution gate — a surprising count is YOUR parser's fault until
   proven otherwise), 44/44b (sheet estimator — context; ledger is not
   your scope).
3. docs/KHL_LAKE_VERIFICATION.md + docs/HANDOFF_KHL.md +
   docs/KHL_SOURCE.md — the verified source contract. The Manager's
   coach census is 3,060/3,060 (both sides, text-page preview frame) —
   NO coach map needed; if your parse lands under 100%, suspect your
   regex (the Manager's first attempt failed by scoping to broadcast
   items — coaches live in the preview frame).
4. hockeycore/leagues/shl.py + mestis.py — the pattern: every verified
   convention documented in the docstring with named games.

## KHL-specific build facts (all verified in the lake docs; re-verify on
## named games as you go)

- **Two channels, split duties**: TEXT (text.khl.ru) = goalie pull/
  return events with game clock, explicit DELAYED-PENALTY events,
  penalty END events ("играет в полном составе"), substitutions
  ("Замена вратаря. <Team>. <new> вместо <old>" — a swap class like
  Mestis vaihto, NEVER a pull), coaches, per-player EN-TOI (ВППВ).
  Goal lines in text carry NO time. PROTOCOL (www.khl.ru) = goals with
  period + cumulative clock + running score + strength (рав/бол/мен/
  буллит) + on-ice jersey lists both teams (EN goals resolve via
  goalie-number absence), penalty table (begin time/player/minutes/
  offense). Coaches NOT on protocol.
- **Clock semantics are MIXED in text**: play events = cumulative game
  clock; period/game boundary lines = WALL clock (MSK). Protocol goal
  clock = cumulative (01′23′′ format). Reconcile explicitly; error
  loudly on impossible times (rule 10).
- **Scoping is mandatory**: every text count scopes to
  div.textBroadcast-item structured lines (a page-wide grep showed "15
  pulls" where 3 are real — proven on 885442). Calendar quirk 5 does
  not affect you (games are already fetched) but the same discipline
  applies inside pages.
- **Known feed quirks**: duplicate penalty line (898094 51:57 — dedupe);
  degenerate/offsetting patterns unknown — census them like the SHL
  session censused placeholder windows before deciding handling.
- **Penalties**: protocol gives begin+minutes; text gives end events.
  Prefer explicit ends where present (SHL-class); fall back to
  begin+minutes with the AHL minor-termination convention where absent;
  >=10 min = misconduct class (no strength effect). Document which path
  fires how often.
- **EN goals**: no TM-style flag — resolve from on-ice goalie absence
  (protocol lists) cross-checked against text pull windows + ВППВ
  EN-TOI. Inherit the AHL/Mestis EN evidence-repair rules adapted to
  this resolution (synthetic segment when channels prove EN with no
  interval; correction when an interval covers a goal).
- **DELAYED-PENALTY EVENTS ARE EXPLICIT — the portfolio first.** Do NOT
  modify rulings 17/17b or segments.py. DO: (a) parse dp events into an
  auxiliary export data/derived/khl_dp_events.json (game, time, side,
  linked pull window if any); (b) include >=2 dp cases in the GT batch;
  (c) report the dp census in your handoff (count/season, duration
  distribution, share ending in leader-whistle). The Manager uses this
  to cross-calibrate 17/17b for ALL interval leagues post-merge.
- **Russian vocabulary**: pin the exact phrases for every event class in
  the adapter docstring, each with a named game. Keep raw text verbatim
  in any aux exports.

## The job, in order

1. **GT batch (rule 2)**: ~12 games hand-traced from raw text+protocol
   BEFORE adapter code. Cover: EV pull, pp_pull, no-pull gap-3,
   carryover-at-open, multi-pull, pull-to-horn, OT + shootout (буллит),
   mid-game substitution (never a pull), an explicit-dp case or two, an
   EN goal resolved by jersey-absence, a duplicate-line game (898094).
   tests/ground_truth_khl.json + trace doc + tests/reference_raw/khl/
   (text+protocol per GT game — mind repo size, ~1.5 MB/game is fine).
2. **Adapter hockeycore/leagues/khl.py**: emits the segments.py dict
   (goals t/side/period/en/types; empty intervals; penalties side/t/
   begin/end/misconduct; coaches both sides). Times cumulative; P3 =
   [2400,3600]; OT rows period>3.
3. **Runner hockeycore/gap/run_khl_lake.py** (lake at /home/claude/work/
   khl_lake/khl; abort on unattributed trailing coach — with the 100%
   census there is NO map fallback: a miss is a parser bug).
4. **Audit**: extend tools/audit_interval_random.py with "khl" — the
   independent channel is the PROTOCOL side (on-ice lists + ВППВ
   EN-TOI) vs the text events the adapter parses. Seed 20260808,
   30+30, 0 disagreements.
5. **Gates**: test_khl_ground_truth / test_khl_derived_instances
   (rule-14 structural; expect roughly 1,300-1,600 instances from 3,060
   games if Liiga-density holds — derive your own, suspect yourself if
   wildly off) / test_khl_random_audit. Full suite green.
6. **Handoff docs/HANDOFF_KHL_ADAPTER.md**: GT summary, extraction
   counts, audit, dp census, quirks with named games, open
   adjudications. Everything is a claim until the Manager re-derives.

Hard rules: never edit raw payloads; every convention verified on a
named game; commit+push every block; numbers to Seb immediately; if it
looks off, it IS off. Your branch never touches master.
