# Magnus ground truth — batch 0 (scan samples, 2026-08-02)

Hand-traced from the raw sheets (rule 2: trace BEFORE adapter logic; the
parser prototype was used only to transcribe table rows — every window/pull
judgment below was made by hand from score progressions, TOI arithmetic,
penalty windows, and Joueurs lists). 9 sheets spanning 2020-21..2025-26;
fixtures in tests/reference_raw/magnus/.

## Traces (P3 = 2400-3600 abs; windows in P3-relative seconds)

- **901** (2021, ROUEN 5-0 NICE): P3 entry 4-0, 57:40 -> 5-0. Gap never 3.
  NO gap-3 instance. Goalies never off.
- **1051** (2021, MULHOUSE-NICE): EMPTY SHEET (cancelled, COVID era).
  sheet_empty class — no data, kept verbatim.
- **11101** (2021, BRIANÇON 2-1 OT CHAMONIX): 1-1 through P3, OT winner.
  Gap never 3. NO instance. OT: TOI 3796s — duration from sheet, not 3600.
- **16351** (2022, ROUEN 7-4 GRENOBLE) — the gold case:
  - P3: 46:22 4-3, 50:04 5-3, 50:24 6-3 (GAP 3 -> window1 opens 624),
    52:37 GRE SUP1 6-4 (window1 CLOSES 757, narrowed).
  - 56:15 ROU EG+CV 7-4 (GAP 3 again -> window2 opens 975, to horn 1200).
  - GRE goalie #30 TOI 57:54 (126s off). Case-1 arithmetic: pull_start =
    EN-goal 3375 - 126 = 3249 (54:09) — a GAP-2 pull (down 6-4), ended by
    the EN goal that CREATED window2. J- on the 56:15 goal = [3,10,18,58,
    64,78], no GB — empty net confirmed (two-factor agreement).
  - Window1 [624,757]: net full (off-ice interval lies outside) -> NO pull.
  - Window2 [975,1200): goalie returned at the creating goal (TOI fully
    accounted) -> NO pull; note GRE shorthanded 3421-3541(+5min to horn)
    most of the window (clean-chance quality low). NOT carryover (return
    coincides with window open).
- **32701** (2023, ANGLET 4-0 GAP): P3 entry 3-0 -> window opens 0;
  57:29 ANGLET goal -> 4-0, window CLOSES 1049 (widened). GAP goalie #83
  TOI 3600 -> NO pull. DATA-QUALITY CATCH: the 57:29 goal is typed SUP1 but
  ANGLET was the penalized team (pen 3415-3535 covers 3449) -> true INF1.
  Type field unreliable, live example — penalty windows are authority.
- **41851** (2024, ROUEN 5-2 CERGY): P3 entry 5-1 (gap 4); 57:44 CGY -> 5-2
  (GAP 3 -> window opens 1064, to horn). CGY #37 1494s + #1 2106s = 3600
  (scheduled swap, fully accounted) -> NO pull.
- **46501** (2024, GAP 1-5 BORDEAUX): P3 entry 0-5; 43:55 -> 1-5 (gap 4).
  Gap never 3 in P3. NO instance.
- **68851** (2025, BRIANÇON 0-5 AMIENS): P3 entry 0-4; 58:17 -> 0-5.
  Gap 4->5, never 3. NO instance. BRI scheduled goalie swap at P3 start
  (#34 2400s -> #31 1200s), fully accounted.
- **69001** (2025, ANGERS 4-1 AMIENS): 56:59 -> 4-1 (GAP 3 -> window opens
  1019, to horn). AMI #1 (Kozun) TOI 3600 -> NO pull (down 3, 3:01 left,
  stayed in).

## Batch-0 truth set
5 gap-3 windows / 4 games; 0 in-window pulls; 1 adjacent gap-2 pull with
exact Case-1 arithmetic + J- confirmation; 1 empty sheet; 1 OT duration
case; 2 scheduled-swap cases; 1 Type-field lie caught by penalty windows.
Next: batch 1 from the full lake targets PULL-positive windows (batch 0 is
pull-negative-heavy by luck of the scan) before any adapter classification
logic ships.
