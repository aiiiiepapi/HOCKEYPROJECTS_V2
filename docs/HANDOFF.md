# HOCKEYPROJECTS V2 — Session Handoff (2026-07-25)

Any session (or human) can resume the project from this document + this repo.
Read CLAUDE.md first (constitution + STATUS table + standing rules 0/0b).

## How to resume in a fresh session
1. Clone this repo, plus the two data sources:
   - v1 frozen reference: github.com/aiiiiepapi/HOCKEYPROJECTS @ pre-v2-snapshot
   - NHL raw lake:        github.com/aiiiiepapi/HOCKEYPROJECTS @ nhl-data-lake
     (read-only fine-grained token from Seb; EIHL/Liiga raw live inside the
     pre-v2-snapshot branch under projects/EIHL and projects/FINLAND)
2. Wire paths: hockeycore expects the NHL lake at /home/claude/work/nhl_lake
   and raw symlinks under data/raw/ (see data/README if present, else
   hockeycore/gap/run_lake.py LAKE constant).
3. `pip install pytest pandas openpyxl numpy --break-system-packages`
4. Regenerate derived tables: `python3 hockeycore/gap/run_lake.py` (15s),
   then `python3 hockeycore/fit/fit_curves.py` (fits.json).
5. RUN THE GATES: `python3 -m pytest tests/test_v2_gates.py` — 8 tests, all
   must pass before touching anything. This is non-negotiable (rule: every
   release gate green or no release).

## State of the world (what's DONE and verified)
- NHL: extraction engine (hockeycore/gap/extract.py) validated vs 13
  hand-traced instances + shadow-diff vs v1 (94.7% agree; all 65 diffs
  attributed → 3 systematic v1 bug classes; 10.4% of v1 pull records wrong).
- Model: MODEL_SPEC.md + CALCULATIONS.md are the law; MC pricer
  (hockeycore/pricing/mc_pricer.py) with re-pull dynamics + margin-1 pulls;
  recursion cross-check gate |Δ|<0.005.
- Walk-forward backtest (fit 24-25 → blind 25-26, 1,442 obs): ALL FOUR
  markets calibrated (docs/backtest_report.md). Leakage disclosure inside.
- Coach layer: cross-season persistence only 0.355 → production multipliers
  attenuated (coach_table_production.json). Roy validated as real outlier.
- Deliverable: live_model/3mapgot_calculator_v2.xlsx (also on Seb's disk).
- EIHL + Liiga: adapters (hockeycore/leagues/), ground truths, full
  extraction, shadow-diffs vs v1: EIHL 124/124, Liiga 235/235 — v1's European
  EXTRACTIONS verified correct. European PRICING not yet built.
- League pull cultures: Liiga 18.3% / NHL 16.6% / EIHL 8.1%.

## Honesty ledger (open items, do not silently drop)
- Coach shrinkage k estimated crudely (floor 2.0) — refine derivation.
- Coach-name encoding mangled for accented names (cosmetic, normalize).
- Single-second net-empty blips at penalty whistles w/o delayed-penalty event
  (NHL): handled by event ordering, needs explicit rule + regression test.
- Backtest leakage: 3 diagnostic passes on test season during mechanism
  discovery (disclosed in backtest_report.md); clean confirmation = 2026-27.
- Liiga: 4 games unparseable (444,473,474,475 — v1-era corrupt pulls; their
  data exists in api_game_* pagination files, deep-parse possible).
- leader≥1 market retains ~5pt conservative bias out-of-sample (post-fix);
  monitor, don't hand-tune.
- Sim simplifications: strength decays to EV after 60s; goals end penalties;
  margin<1 = no pulls, EV rates.

## Not done yet (ordered)
1. EIHL/Liiga pricing: rate fits (their own levels, NHL curve SHAPES where
   thin), pricer runs, verify v1's European workbooks (the EV-sign-bug layer
   was never validated!).
2. AHL: full fetcher + lake + same treatment (blocked on Seb running fetcher).
3. Odds capture + paper trading (blocked on Seb decision) → THEN systematic
   betting gate.
4. Live monitor + server deploy (git pull based).
5. OT4V3 + NEXTGOALPROP rebuild on hockeycore (parked by Seb).
6. Hardening pass: honesty-ledger items above.

## Working agreements with Seb (do not violate)
- Rule 0 (verify everything, incl. own prior work), rule 0b (disagree openly).
- No file attachments in chat for working docs; deliverables to his disk at
  HOCKEYPROJECTS\_manager\; status = V2_STATUS.md there, updated every block.
- He bets real money: betting-stance line always present and honest in STATUS.
