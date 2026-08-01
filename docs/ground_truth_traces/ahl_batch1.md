# AHL ground truth — batch 1 (2026-08-01)

3 games / 5 instances hand-traced from raw pxpverbose BEFORE the adapter was
written (rule 2). Stored in tests/ground_truth_ahl.json, gated.

Semantics established by the traces:
- "s" = elapsed seconds within period (count-up clock; NHL uses remaining).
- Pulls are EXPLICIT goalie_change events (out set, in null) — no shift
  reconstruction, no NHL-style phantom-inference risk.
- A goalie-return row is logged at the same second as every EN goal and at
  delayed-penalty whistles.
- Delayed-penalty extra-attacker shows as PULL->IN bracketing an opponent
  penalty (observed: LAV pulling while UP 4-0, 17s).
- PP pulls (6-on-4/6-on-3) classified via box windows; observed live in
  1027799 (MB, down 3, on the PP, pulled -> PP goal) and 1027819
  (same-second leader minor).

## Feed-defect classes found and adjudicated (EN cross-checks, 4,608 games)
1. Goalie SUBSTITUTION after a goal logged as PULL+IN same second ->
   297 zero-length intervals -> dropped in adapter.
2. Return row clock skew: logged up to 3s before the EN goal it reacts to ->
   27 cases -> +/-3s tolerance in cross-checks (instance logic unaffected).
3. Missing goalie_change entirely: 15 EN goals (0.3% of games) with no pull
   logged. All 7 near-gap-3 cases proved to be gap-2 pulls whose ENG CREATED
   the gap-3 window (carryover flag correct, no false no-pulls). Adapter
   synthesizes flagged evidence segments should a future mid-window case
   appear (synthetic_pull_evidence=True -> timing unusable).
4. Missing EN flag on a goal into an explicitly empty net (1 case,
   90/1028334): 55s explicit interval beats the flag -> en corrected,
   marked EN_corrected.

## Random audit (60 instances, seed 20260801)
30 random pulls + 30 random no-pulls re-verified directly against raw
goalie_change rows (bypassing the adapter state machine): 0 disagreements.
Boundary cases confirmed: carryover segments at window open, post-goal
substitution rows at window close.

## Open item for the ledger block (NOT yet handled)
Trailing-team delayed-penalty extra-attacker inside a gap-3 window would
register as a real pull segment (signature: return coincides with opponent
penalty event). Must be measured and ruled on before AHL coach ledgers ship —
same class as the NHL dp-window phantoms.
