# Magnus GT batch 1 — 10 sheets hand-traced (Manager, 2026-08-08)

Traced from raw coordinate dumps of the verified magnus-data-lake PDFs
DURING the lake verification, BEFORE the fix-round parses were pinned
(rule 2). Every number read off the sheet bytes; adapter ran after.

| Game | Class | The trace |
|---|---|---|
| 68882 GAP-ANGERS | TOI typo repair | ANGERS #29 sheet TOI **90:42** — impossible in 60:00. #37 enters 30:42, plays 29:18; 30:42+29:18=60:00 exact. Goalie swap, net never empty. This is the lake session's false 1,842s "pull". Repair fires because side sum 7200 > 3900. |
| 69059 BORDEAUX-AMIENS | Relief interleave (repair must NOT fire) | #32 start 0:00 TOI 58:52; #31 start 8:56 TOI **1:08**. TOI is per-goalie TOTAL, start is first entry: 58:52+1:08=60:00 exact. Sum ≤3900 → no repair. An unconditional overlap-repair fabricated an 868s pull here — caught same day, condition added. |
| 68861 CHAMONIX-BORDEAUX | Stretched GK layout + EN anchor | Jersey column at x≈226 (collides with old 'total' band — row was silently dropped pre-fix). BORDEAUX #34 58:43=3523, off 77s; EN against 59:45=3585 → [3508,3585]. |
| 68987 CERGY-BORDEAUX | Layout variant + TRUE multi-pull | #32 59:10=3550, off 50s, but TWO J-confirmed empty moments: own goal 29:27 with no GB in J+ (dp 6-on-5) AND EN against 58:00. Split unknowable → synthetic, timing unusable. The lake timed it as one 58:00 pull, ignoring 29:27. |
| 68850 NICE-ANGLET | Bench penalty 'E' | Pen row 11:35 num **E** (équipe) 2min JEU, Début 11:34 Fin 13:34 → num None, box window real. NICE off 90s to horn [3510,3600]. Sheet: MARGERIT principal, LEVESQUE adjoint (web preview had them reversed). |
| 68988 CHAMONIX-BRIANÇON | Missed-pull recovery | Stints 0–23:04 + 23:04–57:12 = 3432; off 168s to horn trailing 3-6. A real down-3 pull the lake ledger dropped entirely. [3432,3600]. |
| 69034 BORDEAUX-BRIANÇON | OT sudden death | Both GK exactly 62:57=3777. Sheet's winning-goal clock 63:31 disagrees by 34s (sheet self-inconsistency) — either way nobody's net was empty. The lake's 34s/34s double "pull" is this phantom. |
| 68862 BRIANÇON-GAP | Shootout | Both GK exactly 65:00=3900; decider credited as a 65:00 "goal" (shootout marker). No empty net all game. |
| 68841 MARSEILLE-ANGLET | Multi-pull ambiguity | ANGLET #62 56:58=3418, off 182s; EN against 55:55 AND own goal 59:30 scored with net empty (J+ no GB) → ≥2 episodes, split unknowable → synthetic. The lake's single timed 182s row overstates. |
| 68842 CERGY-AMIENS | Two-EN-anchor fit | AMIENS #1 58:00=3480, off 120s; EN against 58:22 and 59:06 → segment ends at LAST anchor and must cover both: [3426,3546]. |

Adapter rules pinned this batch (all named above): TOI sanity gate
(repair only >3900), structural GK-row parse with roster-GB side
authority, bench-penalty 'E', clock-noise floor (common-mode shortfall
subtracted, 68926-class), sub-threshold rule (<15s residual with no EN
anchor = noise, matches the lake's dp_or_noise class), multi-pull
honesty (synthetic, never a fabricated single interval).

Final cross-derivation vs the lake session's pull_events.csv: 186/191
sides agree; the 5 disagreements + 3 Manager-only pulls are adjudicated
in this doc and the verification STATUS row (lake wrong: 68882, 69034x2,
69074-inconsistent-row, 68843 7s clock convention; Manager-found pulls:
68988 168s, 69078 24s, 77194 16s).
