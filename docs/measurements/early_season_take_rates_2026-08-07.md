# Early-season pull behavior — measurement record (2026-08-07, Manager)

Question (Seb): do teams take clean down-3 chances at the same rate in
their first 20 games as the rest of the season? Possibly league-by-league.

Method: team game number derived from lake schedules (all four interval
leagues, every team matched incl. SHL name aliases); clean-window ledger
chances split at game 20; two-proportion z per league; within-coach
Cochran-Mantel-Haenszel stratified by (coach, season) to control coach
churn (ruling 42: null test + competing explanation + design limits).

## Team-level (first-20 vs rest, clean-chance take rate)

| league | early | late | diff | z |
|---|---|---|---|---|
| NHL | 61.7% (95/154) | 61.6% (298/484) | +0.1 | +0.03 |
| AHL | 46.5% (60/129) | 51.3% (212/413) | -4.8 | -0.96 |
| Liiga | 50.0% (28/56) | 37.9% (44/116) | +12.1 | +1.50 |
| Mestis | 50.0% (35/70) | 42.7% (47/110) | +7.3 | +0.96 |
| SHL | 22.6% (14/62) | 14.1% (14/99) | +8.4 | +1.37 |
| POOLED | 43.2% | 43.0% | +0.3 | +0.08 |

## Within-coach CMH (churn-controlled)

NHL z=+0.49 (80 strata — the largest, added at Seb's ask); AHL +0.30; Liiga +1.29; Mestis +1.76; SHL +0.94;
**European pool (Liiga+Mestis+SHL, 86 strata): obs-exp = +8.94 takes,
z = +2.35**; all-league pool +1.87 (AHL dilutes).

## Standing interpretation (attribution-gate compliant)

- Per-league and all-league pooled: NO detectable effect (consistent
  with ruling 30's within-coach calendar NULL for NHL/AHL/Liiga).
- SHARPENED CONTRAST with NHL added: BOTH North American leagues are
  cleanly null (NHL z=+0.03 team / +0.49 within-coach on 638 chances;
  AHL likewise) while all three European leagues lean early. The
  NA-vs-EU framing remains post-hoc — same caution applies.
- The EUROPEAN-pool early-lean survives the coach-churn control at
  z=+2.35 (~+6-8pts early) BUT the grouping was formed post-hoc after
  seeing team-level signs — significance is overstated by selection.
- Design cannot distinguish "early-season aggression" from other
  calendar-correlated forces (late-season points pressure, playoff-race
  dynamics = the queue-2 covariate, schedule composition).
- STATUS: PRE-REGISTERED HYPOTHESIS for the 2026-27 season:
  "EU-league coaches take clean down-3 chances ~6-8pts more often in
  their team's first 20 games." Test on 26-27 data (which had no vote
  in forming this) via the same CMH; paper-harness season provides it
  for free. NO model or card change until then unless Seb rules.
