# MAPGOT v2 — Exact Calculation Definitions (draft 1, 2026-07-25)

Companion to MODEL_SPEC.md. Every important quantity, defined to the second,
BEFORE the engine is built — so the code implements this document, never the
other way around. Anything marked [FIT] gets its value from the lake; anything
marked [AFTER-FIRST-FIT] is a structural decision deferred until the relevant
frequency is measured. Nothing here may be changed silently: edits to this
file are logged decisions.

## 0. Conventions

- t  = seconds elapsed in P3, integer grid 0..1200. R = 1200 - t.
- All times from pbp `timeInPeriod` (elapsed), event order by event sequence
  within identical timestamps.
- situationCode = [awayGoalieIn][awaySkaters][homeSkaters][homeGoalieIn].
- An INSTANCE is a maximal interval with |score gap| == 3 inside P3
  (see ground truth _meta rules). Gap-creating goal excluded from its window;
  gap-closing goal included.
- trailing side fixed per instance; all "for/against" are from the trailing
  team's perspective.

## 1. Per-second state assignment (extraction output)

For every instance, for every second u in [open, close):
  state(u) ∈ {EV_full, TPP_full, TPK_full, EN_ev (6v5), EN_pp (6v4), EN_pk (5v6),
              DP_off (net empty solely due to delayed penalty), OTHER}
Assignment from the situation code in force at u (last event's code carries
forward; codes change ONLY at events — no interpolation of strength).
Net-empty attribution: trailing net empty AND no delayed-penalty event whose
window (event time → next stoppage/penalty event) covers u ⇒ EN_*;
if a delayed-penalty window covers u ⇒ DP_off (never counts as pull time).
Pull evidence second = first u with state ∈ EN_*.

## 2. Pull hazard

Bins: B_j = 30-second bins of R over the pull band [FIT: band = where pulls
actually occur; provisional 0..600].
  exposure_j = Σ over instances of seconds in bin j with state ∈
               {EV_full, TPP_full} and no pull yet in this instance
               (TPK_full seconds EXCLUDED from exposure; DP_off excluded)
  pulls_j    = count of first-pull evidence seconds falling in bin j
  ĥ_j        = pulls_j / exposure_j        (per-second hazard, binned)
Smoothed h0(R): monotone-respecting spline through (bin centers, ĥ_j) [FIT];
ACCEPTANCE RULE: |spline - ĥ_j| must stay within the bin's 95% Poisson CI for
every bin, else bins are used raw.
Survival to R: S(R) = Π over seconds u from open to R of (1 - h(u)).

Strength multiplier m_PP [FIT]: single-parameter Poisson MLE with offset:
  pulls ~ Poisson( h0(R) · m_PP^[state=TPP_full] · exposure ), profile MLE, CI
  by likelihood ratio.

Re-pull handling [AFTER-FIRST-FIT]: measure f_repull = (instances with ≥2
empty segments)/(instances with ≥1 pull). If f_repull < 0.05 treat first pull
as absorbing and add its bias to the error budget; else model return/re-pull
as a two-state alternating process with its own rates.

## 3. Coach effect

For coach c: E_c = Σ over c's no-pull-yet exposure seconds of h0(R)·m_strength
(expected pulls under the no-coach-effect model), O_c = observed pulls.
Empirical Bayes Gamma prior with mean 1, shape k:
  m̂_c = (O_c + k) / (E_c + k)
k [FIT] by method of moments: Var_between = Var(O_c/E_c weighted) - Σ Poisson
noise; k = 1 / Var_between (floor k at 4 if Var_between ≤ 0 — i.e., no
detectable coach signal ⇒ heavy shrinkage, and D8 still holds).
Coach-team pair with instances < N_min [Seb decision, provisional 5]:
NEW_SITUATION flag; pricing interval widened by refitting with m_c set to both
its 10th and 90th percentile posterior quantiles.

## 4. Goal intensities

For each state s and direction d ∈ {for, against}:
  μ̂_{s,d} = G_{s,d} / T_s
  G_{s,d} = goals by direction d in seconds assigned state s (goal assigned to
            the state in force at its OWN event's situation code — the goal
            event's code is authoritative, per the Bug-A lesson)
  T_s     = total exposure seconds in state s across all instances
CI: exact Poisson on G given T. League-level. Season-drift gate: two-season
rate ratio CI must contain 1, else investigation before pooling seasons.
Combined next-goal intensity at state s: λ_s = μ̂_{s,for} + μ̂_{s,against}.

## 5. Pricing (exact recursion)

Inputs: R0, current pull state, strength path assumption (current strength
persists — documented simplification), coach c, league.
Grid u = R0, R0-1, ..., 1. Define per-second:
  q(u)  = 1 - exp(-h0(u)·m_strength·m̂_c)   (pull prob this second | not yet)
  a_s   = exp(-λ_s)                          (no-goal survival this second in s)
NET ALREADY EMPTY:  P_nogoal = Π_u a_{EN(strength)}  = a^{R0} (constant state).
NET FULL: backward recursion. V(u) = P(no goal in remaining u seconds | net
full now):
  V(0) = 1
  V(u) = a_full · [ (1 - q(u)) · V(u-1) + q(u) · a_EN^{u-1} ]
  (pull takes effect next second; a_full = a of current full-net state)
  P(next goal) = 1 - V(R0)   — internal primitive + fast sanity cross-check.

PRODUCTION PRICER (all three markets, per Seb 2026-07-25): forward Monte
Carlo from live state to the horn, 100k paths, seed logged. Each path steps
1s: pull decision via gap-specific hazard h_gap(R|z) for the CURRENT gap
(gap ∈ {2,3,4}; beyond 4 → 4-gap params; gap ≤1 → EN behavior of the 1-gap
band is out of scope, path continues with full-net rates and this truncation
is in the error budget), goalie return on goal against per measured behavior,
goals via directional λ of the current state, margin/goal counters updated.
Outputs per run: P(leader ≥k more), P(total ≥k more), P(final margin ≥4)
with MC standard errors (≤0.15% at 100k). D10 and a recursion-vs-MC agreement
check (|Δ| < 0.005 on P(next goal)) gate every release.

## 6. Market math

American A → decimal: A>0: dec = 1 + A/100 ; A<0: dec = 1 + 100/|A|.
Implied prob (single side): p_imp = 1/dec.
Two-sided de-vig (proportional): p_fair = p_over/(p_over + p_under).
[Sensitivity: power method computed alongside; if |proportional - power| >
0.01 in live spots, flag — don't average.]
  b = dec - 1
  EV per unit = p_model·b - (1 - p_model)
  edge = p_model - p_fair
Kelly fraction f* = (p_model·b - (1-p_model))/b ; stake policy = min(f*·F, cap)
with fractional multiplier F and cap [Seb decisions].

## 7. Uncertainty

Game-level bootstrap: resample GAMES (not instances) with replacement,
B = 1000, refit h0 (binned), m_PP, μ's (coach effects held at point estimates
— documented shortcut, revisit if coach CIs matter); percentile 5-95 interval
on p_model. Bet rule uses p_model_5th percentile.

## 8. Backtest & calibration (definitions)

- Walk-forward: fit on 2024-25 only → price every 2025-26 instance at decision
  checkpoints R ∈ {900, 780, 660, 600, 480, 360, 300, 240, 180} (15:00 down
  to 3:00 per Seb; nothing priced below 3:00, data below still fitted).
- Brier = mean (p_model - outcome)²; log-loss = mean -[y·ln p + (1-y)·ln(1-p)].
- Reliability: 10 equal-count bins of p_model; |bin mean p - bin outcome rate|
  must be < 2·bin SE for ≥ 8/10 bins to pass.
- P&L: flat 1u stakes at recorded/synthetic lines (line source documented per
  backtest run); report total units, ROI, max drawdown, and the same with
  quarter-Kelly.

## 9. Numeric constants status ledger

| Constant | Status |
|---|---|
| hazard bin width 30s | provisional; sensitivity-test 15/60s |
| pull band 0-600s | [FIT] from data |
| k (coach shrinkage) | [FIT] §3 |
| N_min = 5 | Seb decision pending |
| bootstrap B=1000, MC 100k | fixed, seed-logged |
| de-vig method | proportional + power sensitivity |
| checkpoints R set | provisional, match v1 calculator rows for shadow-diff |
| edge threshold, Kelly F, cap | from backtest + Seb |
