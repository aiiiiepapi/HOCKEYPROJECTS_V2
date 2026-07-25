# Ground Truth Batch 1 — 8 NHL games hand-traced (2026-07-24)

Games: 2024020001, 2024020004, 2024020005, 2024020010, 2024020027, 2024020047,
2024020048, 2024020053. Selected by independent scanner (tools/scan_gaps.py) to
cover: plain pull, early pull, triple re-pull, zero-goal goalie-return,
delayed-penalty goalie-off (both by trailing and by leading team), PP during gap
without pull, multi-instance, gap reopened by EN goal, 22-second late open.

Records: tests/ground_truth_nhl.json (13 instances, evidence event IDs included).

## Cross-check vs v1 extraction

11/13 instances match v1 field-for-field (open, close, pull time). The 2
mismatches are v1 errors, and scanning the full 1,225-row v1 CSV shows both are
SYSTEMATIC:

### Bug A — boundary pull misattribution (CORRECTED 2026-07-24, same day)
Initial claim of 12 phantom pulls was WRONG — retracted after checking net
state on the closing goal event for all 12 (the decisive raw-data test):
- 10/12: net WAS empty at the closing goal → legitimate pulls, trailer scored
  during the pull, goal is simply the first empty-net evidence event. v1 correct.
- 1/12 (2024020004): net FULL at closing goal (sit 1541) → pull came after the
  gap closed; v1 wrongly credited a pull-then-scored success. CONFIRMED bug,
  scope ~1 instance.
- 1/12 (2025021164): CANNOT VERIFY — pbp not cached, which itself violates v1
  test gate #7 (cache completeness is a blocking requirement). Separate finding.
Lesson recorded: one verified case + a pattern is NOT verification of the
pattern (rule 0). v2 spec rule: when pull evidence coincides with the closing
goal, classification is decided by the net state ON the goal event itself.

### Bug B — delayed-penalty pulls counted as real (8 included instances)
delayed_penalty_flag=True but classification left as pull/pp_pull → calculator
weights them 1.0 (it only zero-weights class=="delayed_penalty"). The flag was
computed and then never used. Verified by hand in 2024020048: VAN's net was
empty for SIX SECONDS (129-135s), solely during the delayed call on TBL; v1
recorded a pull running to 254s and credited the PP goal at 254s as a pull
"scored" success. v1 also missed the goalie's return entirely.

### Impact (corrected)
Confirmed contamination so far: 1 Bug-A instance + 1 confirmed Bug-B artifact,
both in the "scored" success bucket (2/64 ≈ 3%), + 1 unverifiable instance with
missing pbp + up to 7 Bug-B candidates pending individual adjudication.
Worst case if all 7 fall: ~10/64 of the success bucket. Direction of bias is
still optimistic (overprices the Over) but magnitude is materially smaller than
the initially claimed 19%. Exact figure lands when the v2 engine runs over the
full lake and each candidate is adjudicated.

## Rules confirmed/added for the v2 spec
1. Pull evidence must be strictly BEFORE the gap-closing event (sequence-aware,
   not timestamp-aware — same-timestamp events resolve by event order).
2. delayed-penalty goalie-off is never a pull, for either team; detection uses
   the delayed-penalty event + net-empty interval containment, not a 30s
   proximity flag bolted on after classification.
3. Pull segments are tracked individually (2024020053 has THREE in one
   instance); "pulled" is a sequence of [empty_from, empty_until] intervals.
4. Late-open instances recorded with duration; no extraction-level exclusion.
5. Pull evidence time = first event showing net empty; true pull time is
   at-or-before this (interpolation is a MODEL choice, documented, not hidden
   in extraction).

## Still to trace
- ~17-22 more NHL games (incl. 2025-26 season spread, pp_pull true positives,
  the remaining 6 Bug-B instances to adjudicate one by one)
- AHL batch (8 cached games available now)
- EIHL + Liiga batches (full raw data available now)
