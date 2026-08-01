# RUNBOOK — cheap-session operations (no expensive model needed)

Any Claude session (cheapest model) — or Seb himself — can run everything
below. Setup once per session, in the workspace:

    git clone --branch master https://<TOKEN>@github.com/aiiiiepapi/HOCKEYPROJECTS_V2.git
    git clone --depth 1 --branch nhl-data-lake https://<TOKEN>@github.com/aiiiiepapi/HOCKEYPROJECTS.git nhl_lake
    git clone --depth 1 --branch ahl-data-lake https://<TOKEN>@github.com/aiiiiepapi/HOCKEYPROJECTS.git ahl_lake
    git clone --depth 1 --branch liiga-data-lake https://<TOKEN>@github.com/aiiiiepapi/HOCKEYPROJECTS.git liiga_lake
    pip install pytest numpy openpyxl --break-system-packages
    # hockeycore expects the lake at /home/claude/work/nhl_lake

## The one non-negotiable rule
After ANY rebuild: `python3 -m pytest tests/test_v2_gates.py` — every gate
green or the output does not ship. A pre-commit hook enforces this on commit.

## Standard operations (in dependency order)
| What | Command | When |
|---|---|---|
| Extract instances from lake | `python3 hockeycore/gap/run_lake.py` | new lake data |
| Extract AHL instances (needs ahl_lake clone) | `python3 hockeycore/gap/run_ahl_lake.py` | new AHL lake data |
| Extract Liiga instances (needs liiga_lake clone) | `python3 hockeycore/gap/run_liiga_lake.py` | new Liiga lake data |
| Refit hazards/rates/coaches | `python3 hockeycore/fit/fit_curves.py` | after extraction |
| Walk-forward backtest | `python3 hockeycore/fit/backtest.py` | after refit |
| ROI at 10%-EV lines | `python3 hockeycore/fit/roi_at_threshold.py` | after backtest |
| Clean-window coach ledger | `python3 hockeycore/fit/clean_window.py` | after extraction |
| AHL+Liiga ledgers & coach profiles | `python3 hockeycore/fit/clean_window_interval.py` | after AHL/Liiga extraction |
| PP-pull coach split | `python3 hockeycore/fit/pp_pull_analysis.py` | after extraction |
| Dense pricing grid (~13 min) | `python3 hockeycore/fit/make_dense_grid.py` | after refit |
| Per-second lines CSV | `python3 hockeycore/fit/build_persecond_lines.py` | after grid |
| Calculator xlsx | `python3 hockeycore/io/build_calculator.py` | after grid |
| Coach profiles | `python3 hockeycore/fit/build_coach_profiles.py` | after clean_window + pp analyses |
| 30s friendly lines table (needs profiles) | `python3 hockeycore/io/build_lines_table.py` | after grid |

Formatting/cosmetic changes: edit the two build_* scripts (labels, colors,
intervals are all near the top), rerun, done. No modeling knowledge needed.

## Delivery
Deliverables go to Seb's disk at
`C:\Users\seb_1\OneDrive\Desktop\HOCKEYPROJECTS\_manager\`:
3mapgot_calculator_v2.xlsx, lines_table_30s.xlsx, lines_10ev_per_second.csv,
V2_STATUS.md. (In a Cowork session: SendUserFile then device_commit_files.)
Push every commit to GitHub (`git push v2origin master` or `origin`).

## What must NOT be done in a cheap session (Fable-only)
- Changing model math, thresholds, fitted constants, or gate logic
- Adjudicating data discrepancies / ground-truth edge cases
- Anything where a wrong number silently reaches the bet card
If a gate goes red or data looks weird: STOP, report, wait for a Fable block.
Standing rules 0 and 0b (CLAUDE.md) apply to every session, every model.

## Morning bot (data-mining phase)
`python3 morning_bot.py --slate "AWY@HOM,..." --ml TEAM:-285 ...` after the
standard refresh chain (extraction -> clean_window -> pp -> profiles).
Weighted: coach + strength regime (fav/mid/heavy-dog, one-sided grading,
measured). Displayed only: venue (measured noise), B2B/lineups (no data yet).
Writes morning_cards.md. Cheap-session friendly.
