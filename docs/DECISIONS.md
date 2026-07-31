# Seb rulings ledger (binding)

## 2026-07-25 (checklist round)

1. **Go/no-go: NO-GO.** Model is NOT ready to be treated as done — "everytime
   I mention something we fix and come to new conclusions, we need to be 99%
   sure." Keep hardening; paper-trading verdict deferred. No real money.
2. **lead1 conservative bias: not acceptable as a permanent exception.**
   "We gotta figure it out." Root-cause hunt #3 stays open (best lead: needs
   the 4-season lake). Gate exception remains only as an interim guard.
3. **Coach small-n policy: RISKY flag only.** N_min=5 gate + half-stake
   REJECTED as too conservative. Coach estimates are used at whatever evidence
   exists (shrinkage + adaptive weighting handle small n); pairs with <5 real
   chances are flagged RISKY with a widened interval. No stake mandates.
4. **Pulled-state multi-goal over: withdrawal RATIFIED.** Off the card.
5. **Odds capture: (c) skip.** No odds feed. The betting deliverable is
   model-side: for every second remaining (15:00→3:00), the line at which a
   bet clears +10% EV — validated by backtesting outcomes at those exact
   lines, NOT by market availability.
6. **Other leagues (incl. AHL): parked.** "Finalize NHL first and make sure
   we are 100% ready and accurate."
7. **2+-more-goals markets DROPPED entirely** ("we dont want the over 1.5
   goals thing"). Removed from calculator and line tables. The pulled-state
   overshoot gate survives as a model-health diagnostic only — no more
   convergence hunts on it.
8. **PP-pull directive**: PP pulls need their own per-coach weighting ("some
   teams only pull on PP" — CONFIRMED: Tortorella/McLellan/Cronin/Huska, 0 EV
   pulls in 35k+ EV secs, league+ rate on PP). Coach layer to become
   (m_EV, m_PP). Covariate backlog to be triaged: keep signal, drop noise.

## Earlier standing rulings
- 2026-07-24: full v2 rebuild, trust nothing from v1 except raw data + docs.
- 2026-07-25: rule 0 (never assume prior work correct) + rule 0b (disagree
  openly before complying).
- Bet products: leader TT over, game total over, leader -3.5. OT4V3 and
  NEXTGOALPROP parked. Prices from 15:00 down to 3:00, never below 3:00.
- Recent-season overweighting: tested and rejected on evidence (Seb accepted).

## 2026-07-26
9. **Aggressiveness estimator rebuilt**: "3/3 is not league average." Beta
   prior fitted on league coach spread (a=2.46, b=1.67) + recency decay
   (half-life 10 chances) on each coach's own 5v5 chance sequence. 3/3 -> 76%.
10. **Recency ruled in** at coach level (last-3 form shown in guide).
11. **Pulled-state rows removed** from lines doc (no lines offered anyway).
12. **Manual override tab**: Seb inputs his own pull % + typical pull time;
    priced through a dedicated MC grid (pull% x timing-shift x time), 5v5 only.
13. **Team/coach-first navigation**: TEAM LINES tab prices every team at its
    own coach's expected % + timing; filter by name.
NOTE: new coach layer is PROVISIONAL until blind re-validation (next block).
14. **Average pull timing REMOVED from production pricing** (2026-07-26):
    observed averages are opportunity-gated noise; the in-window conditioning
    channel (20-26pt swings at 5:00-6:00) overreads silence. Raw timing stays
    visible as context; EARLY-puller flag + stand-down rule replaces the curve
    shift; MANUAL tab keeps the timing knob; Gen-3 threshold+opportunity model
    is the sanctioned way to bring timing back.
15. **lead1 hunt #3 CLOSED (2026-07-26, triggered by Seb's Bednar-at-6:00
    challenge)**: root causes = missing in-sim penalty generation (17% of
    leader goals are PPGs) + flat goal rates (desperation acceleration) +
    backtest running raw-EB coach multipliers. All fixed; bias +5..7 -> +2.4.
    NEW: -3.5 now ~4pts OPTIMISTIC -> CAUTION on card (double edge or skip)
    until coach-conditional hazards. ROI at 10%-EV lines (blind, clustered):
    leaderTT +22.8% [+9.0,+37.9], total +11.0% [+0.6,+21.8], -3.5 +4.1% [n.s.].
16. **Morning bot v1 shipped (2026-07-31)**: real moneylines ruled in for
    DAILY inference (partial reversal of odds:c — historical odds still
    skipped; effect fitted on results-based strength, ML maps to same scale).
    Mining results: strength effect one-sided (favs 66%, heavy dogs 39%,
    slight fav == heavy fav); venue NULL at chance level (+1.6pts) -> display
    only. Card = expected % + why + last-3 chances with outcomes.
