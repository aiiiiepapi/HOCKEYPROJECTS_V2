# Manager-session handoff — 2026-08-02 (evening)

Read CLAUDE.md first (constitution + rules 0/0b/15/15b). This file is the
exact pickup point for the NEW Manager session. It supersedes
HANDOFF_2026-08-02.md (kept for history).

## Session topology (Seb's structure, 2026-08-02)
- **YOU (new chat) = Manager.** Own master, rulings, gates, deliverables,
  portfolio state. Everything routes through you.
- **Magnus-scrape session** (the previous Manager chat) — finishing the
  Ligue Magnus lake + batch-1 GT + extraction + audit on branch
  `magnus-build`; pushes lake to HOCKEYPROJECTS branch `magnus-data-lake`.
  It reports done -> you verify per rule 0 and merge.
- **Mestis-scrape session** — lake + research only, branch `mestis-scrape`,
  lake to `mestis-data-lake`. Kickoff: docs/KICKOFF_MESTIS_SCRAPE.md.
  Same merge discipline.
- Scrape sessions NEVER touch master. You alone commit master.

## Where the portfolio stands (all pushed; 22/22 gates at HEAD)

**NHL** — priced & validated. Rulings 29-33 estimator (prior_fit.py,
calendar recency HL 12mo, whisper-past-3 fade, hot-record cap; strengths
NHL 3/AHL 9/Liiga 4). leaderTT +23.9% P(>edge) 0.973. -3.5 CAUTION.
Blip rule + same-second order-independence added 2026-08-02 (3 corrections,
all 2022-23 — training window untouched).

**AHL** — extraction FINALIZED 2026-08-02 (rulings 34-38: 17b dp clauses,
misconduct fix, swap fix; audits 0/60; 404->395 EV pulls; coach deltas
ratified — McIlvane 84->81, Morrison 25->13, Petersen 68->86).
Failure re-attributed (rulings 39/39b/39c): data exonerated; 90-H2 was a
DIRECTIONAL competitive shift (leader EV -33%, trailer EV +62%, totals
flat) — not 6v5-specific (that claim retracted, 15b); no repeating H2
pattern; race covariate is the mechanism candidate. Blind still FAILS
(ruling 24 pinned).
**CRITICAL CONTEXT — rulings 40/41/41b:** Seb ORDERED AHL production onto
NHL goal/min levels (splice.py) after hearing three rounds of failed-blind
evidence, including -3.5 (overriding his own permanent 26a). The
Manager recommendation AGAINST staking these stands on the record.
lines_10ev_ahl.csv + ahl_lines_30s_UNVALIDATED.xlsx exist BY ORDER, carry
the UNVALIDATED banner (data/derived/AHL_LINES_UNVALIDATED.md), rule-28
40% floor unchanged. Do NOT relitigate unprompted; DO ensure the paper
harness logs AHL model-vs-real-line-vs-outcome from opening night — that
data settles it empirically. December re-litigation gate stands.

**Liiga** — blind PASS post-fix (+17.9/+12.4/+29.6), paper-trade from
September. One thin season; not "99% sure".

**Magnus** — sweep of ~41k hockeynet ids running on Seb's PC (bands:
22-23 15900-32600, 23-24 32600-42400, 24-25 42400-55400, 25-26
68550-69900). Adapter ALREADY SHIPPED & GATED pre-lake (gate 22,
hockeycore/leagues/magnus.py): coordinate parser, coaches ON sheet,
semantic J+/J- split, EN anchors as hard constraints in the TOI fit.
GT batch 0: 9 sheets, 2 hand-trace errors caught by engine (recorded).
Precision doctrine: docs/MAGNUS_DATA_GAPS.md. The Magnus session runs:
classify (PS inflate block already with Seb) -> stage -> lake branch ->
batch-1 GT (pull-positive) -> extraction -> audit -> handoff to you.
Ledger/profiles/morning sheet = YOUR call whether the Magnus session
builds them on-branch or you do post-merge (recommend post-merge: ledger
numbers are bet-facing = Manager work).

**Morning sheets** — AHL delivered (tools/build_morning_sheet_interval.py,
works for liiga too). Coach % on ruling-33 estimator, rule-28 NO-BET tags.

## Queue (Seb's standing order: points 2-6 wait until ALL league scrapes done)
1. Magnus lake -> merge -> ledger -> morning sheet.
2. Mestis lake -> merge -> adapter (Manager builds, Magnus-style) -> ledger.
3. Then the deferred block: playoff-race covariate (elevated — now ALSO the
   prime AHL-failure mechanism candidate, rulings 39/39b), group-conditional
   fav/dog on clean chances, special notes system, September automation
   (nightly fetchers incl. magnus --probe-new + odds, Task Scheduler,
   paper-harness shakedown, settlement join), October paper-trade month,
   ~Dec AHL re-litigation (150-200 fresh 26-27 instances).

## Working protocol with Seb (hard-learned; keep verbatim)
- Answer with numbers IMMEDIATELY; validate silently; interrupt only if a
  gate goes red. Always END turns with visible text.
- 0b is real work here: Seb challenges numbers hard ("we've bet AHL for
  years", "3/3 is not league average") and is RIGHT often enough that every
  challenge gets measured, not deflected — today his H2-aggressiveness
  claim overturned a recorded metric (39b). Disagree with evidence, then
  he rules; record overrides faithfully (rulings 40/41/41b pattern).
- Deliverables: SendUserFile + device_commit_files to
  C:\Users\seb_1\OneDrive\Desktop\HOCKEYPROJECTS\_manager\ (force=true).
- Seb prefers paste-block PowerShell over .bat downloads for his PC.
- Long jobs: setsid nohup + marker files; bash timeout 10 min. Beware:
  pgrep -f matches your own compound commands.
- NEVER commit tokens (push protection will block you — amend, keep
  tokens in Seb-delivered files only). Commit+push every block; re-run
  the full gate suite (python3 -m pytest tests/test_v2_gates.py) before
  relying on ANYTHING (rule 0), and after any rebuild.
- Setup per RUNBOOK.md: clone V2 + 3 lakes (+magnus/mestis lakes when
  they exist), symlink /home/claude/work/{nhl,ahl,liiga}_lake,
  pip install pytest numpy openpyxl pymupdf --break-system-packages.
