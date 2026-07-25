# Shadow-diff: v2 engine vs v1 extraction (gap-3, NHL) — 2026-07-25

Scope: 987 common games / 1,225 v1 instances. v2 additionally covers 67 games
v1 never processed (post 2026-03-28) → 1,309 gap-3 instances total, plus
2,077 gap-2 and 594 gap-4 (new, for the chain model).

## Agreement
1,160 / 1,225 instance records match exactly (94.7%): window bounds, pull
presence, pull evidence time. Instance counts and windows match on ALL
common games (the window logic of v1 was sound).

## Attributed discrepancies (every one individually verified against raw pbp)

| Class | Total | In v1's INCLUDED (model-feeding) data |
|---|---|---|
| Bug C — carryover pull: v1 counted the dead pull from the previous gap (team pulled at 1/2-gap, conceded EN goal creating the 3-gap, goalie returned at faceoff; v1 stamped a pull at instance open) | 43 | 8 |
| Bug B — delayed-penalty goalie-off recorded as the pull (real pull happened later or never; worst case v1 time off by 11 minutes: 2025020484, 232s vs real 890s) | 5 + most of the 9 "phantom_other" + several "pull_time_other" on inspection | 5 + 9 + 5 |
| Bug A — pull after the gap had already closed, credited as pull success | 1 | 1 |
| **Total wrong pull records** | **65** | **28 of 270 = 10.4%** |

Engine-side: 1 defect found and fixed during the diff (pull evidence occurring
only on the closing goal's own event — 11 legitimate pulls initially missed;
CALCULATIONS §4 rule now implemented; ground truth regression stayed green).

## Delayed-penalty adjudication (the 7 pending from batch 1)
- v1 WRONG (pull time = delayed-penalty artifact; real pull later, found by
  v2): 2024020813, 2025020188, 2025020484, 2025020524, 2025020715
- v1 CORRECT (genuine pulls; dp flag was proximity noise): 2024020791, 2024020799

## Impact on v1 model (final, replaces both earlier estimates)
10.4% of the pull records feeding v1's NHL pull rates and pull-timing curves
were wrong — mostly pulls counted at times no pull decision existed, i.e.,
v1 overstates pull frequency and mis-shapes pull timing. Combined with the
included-instances weighting scheme, v1 NHL prices are optimistic on the
Over side. v1 numbers remain retired for betting.

## v2 known edge (logged, low priority)
Single-second net-empty blips at a penalty whistle when the API emitted no
delayed-penalty event (e.g., 2024020670 at 724s) are currently avoided by
same-second event ordering; add an explicit rule + regression test in the
engine hardening pass.
