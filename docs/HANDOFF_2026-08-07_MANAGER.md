# Manager-session handoff — 2026-08-07

Read CLAUDE.md first (constitution; rules 0/0b/15/15b/42 + rulings 1-44b
in docs/DECISIONS.md are binding). This file is the exact pickup point
for a NEW Manager session; it supersedes HANDOFF_2026-08-02_MANAGER.md.

## Session topology (current)

- **YOU = Manager.** Own master, rulings, verification, models, ledgers,
  deliverables. Everything routes through you.
- Scrape/adapter work is DELEGATED to fenced build sessions (one per
  job, branch-fenced, never touch master) — pattern proven 4x (Mestis
  scrape, SHL scrape, KHL scrape, SHL adapter; kickoff docs in docs/).
  Their "done" is a CLAIM: you re-derive independently (rule 0) before
  merging — the record shows their handoffs are good but not perfect
  (Mestis ticker inflation, SHL CRLF incident — both caught by
  verification, never by trust).
- **Session creation matters**: cloud sessions can push to GitHub ONLY
  if the repo was ATTACHED at creation (Claude GitHub App). A session
  born without it (like the 2026-08-03 Manager) is push-blocked forever
  and uses the PC relay: bundle in Seb's
  OneDrive\Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\<name>\ + a
  push_<name>.ps1 Seb runs (HOW_TO_PUSH.txt in his _manager folder).
- Seb's PC facts: OneDrive Desktop is the visible one
  (C:\Users\seb_1\OneDrive\Desktop); a HIDDEN local Desktop exists —
  scripts must use explicit OneDrive paths. C:\dev\HOCKEYPROJECTS_V2 is
  NOT a git repo (data only); working PC clones live elsewhere
  (C:\dev\HP_V2 = SHL session's). Git repos NEVER inside OneDrive.
  Every lake branch starts `.gitattributes * -text` + re-hash after
  transfer (CRLF lesson).

## Portfolio state (verify per rule 0 before relying; gates: 29 green)

- **NHL** — priced & validated (rulings 29-33 estimator). leaderTT
  flagship; -3.5 CAUTION. Untouched by ruling 44 (see below).
- **Liiga** — provisional pass (ruling 25 + 2nd forward fold). Paper-
  trade from September.
- **Mestis** — provisional (ruling 43, pooled multi-fold). Lines
  shipped. Paper-trade from September.
- **AHL** — self-priced NO-GO (ruling 24); Seb-ordered NHL-level lines
  exist UNVALIDATED (rulings 40/41/41b); coach intel valid; Dec
  re-litigation.
- **SHL** — lake + adapter + ledger DONE (verifications in docs/). NO
  pricer: 28 EV pulls = too thin, and the league personality is
  gap-1/2 pulls (29.8% carryover-open; clean-chance take 17.4%). The
  bettable SHL product, if any, is the UNBUILT gap-1/2 class — open
  strategic question for Seb.
- **KHL** — lake verified (3,060 games, coach census 100%). Adapter
  kickoff written (docs/KICKOFF_KHL_ADAPTER.md), session may be
  running — its dp-event census feeds a 17/17b cross-calibration
  (Manager work post-merge). NO odds market at our provider (ruling 5
  model-side doctrine).
- **Magnus** — adapter gated pre-lake; Seb's PC sweep still pending.
- **EIHL** — v1 cache, parked.

## Estimator split (ruling 44/44b — IMPORTANT)

- **Sheets** (coach cards, all interval leagues): NO league average;
  season-window record (newest season; previous season rides until
  Jan 1 then drops); Jeffreys half-chance stabilizer only; RISKY <3
  season chances; NO DATA = NO-BET; 28b HOT FORM flag printed.
  Implementation: prior_fit.posterior_sheet.
- **Pricing** (NHL/Liiga/Mestis lines, backtests, paper harness):
  STILL the validated rulings-29-33 estimator. "Everywhere" upgrade
  requires multi-fold re-exams first — pending Seb.

## Method law

- Multi-fold backtest (tools/backtest_folds.py: forward folds + LOSO)
  is the ONLY deciding evidence for league verdicts. Single-fold
  retired. Variance test: tools/fold_variance_test.py.
- Ruling 42 (attribution gate): no causal claim ships without a null
  test + a tested competing explanation + stated design limits.
  "It's noise" and "it's my parser" are always the first hypotheses.
  History: Seb's challenges overturned 5+ Manager attributions —
  measure before you narrate.

## Pre-registered hypothesis (docs/measurements/)

EU leagues (Liiga/Mestis/SHL) take clean chances ~6-8pts more in the
team's first 20 games (within-coach z=+2.35, post-hoc grouping);
NHL+AHL cleanly null. TEST on 26-27 data when it accrues; no model/card
change until then unless Seb rules.

## Queue

1. KHL adapter session -> verify per rule 0 -> merge -> ledger/sheet
   (Manager) + 17/17b dp cross-calibration from its dp census.
2. Magnus lake when Seb's sweep lands -> verify -> merge -> ledger.
3. September block: fetcher automation, paper-harness shakedown (NHL/
   Liiga/Mestis + AHL logging; Mestis live-parser stub needs real
   in-season pages), settlement join, sheet refresh with new benches.
4. October: paper-trade month. ~Dec: AHL re-litigation; EU early-season
   hypothesis test; Mestis/Liiga re-exams with 26-27 folds.
5. Open Seb decisions: SHL gap-1/2 product class; "everywhere" scope
   for ruling 44; token regeneration (the write token is in several
   old transcripts).

## Working protocol with Seb (keep verbatim)

- Answer with numbers IMMEDIATELY; validate silently; end turns with
  visible text. 0b is real: he challenges hard and is right often —
  measure every challenge, record faithfully either way.
- Plain language on request — he will say "robot language" when you
  drift. Deliverables: SendUserFile + device_commit_files to
  OneDrive\Desktop\HOCKEYPROJECTS\_manager\ (force=true).
- **NEVER name a script without the full copy-paste line.** Every "run
  X" instruction to Seb is the complete one-liner, ready to paste:
  powershell -ExecutionPolicy Bypass -File "C:\Users\seb_1\OneDrive\Desktop\HOCKEYPROJECTS\_manager\v2_bootstrap\<NAME>\push_<NAME>.ps1"
  (Seb ruled this 2026-08-07 after being handed bare script names twice.
  His account has no persistent AI memory — THIS FILE is the memory.)
- Setup per RUNBOOK + lakes: clone V2; lake branches nhl/ahl/liiga on
  the v1 repo (READ-ONLY token), mestis/shl/khl-data-lake on the V2
  repo; symlink /home/claude/work/{nhl,ahl,liiga}_lake,
  mestis_lake -> <checkout>, shl_lake -> <checkout>, khl worktree.
  pip install pytest numpy openpyxl pymupdf --break-system-packages;
  pip install -e . ; python3 -m pytest tests/test_v2_gates.py FIRST.
