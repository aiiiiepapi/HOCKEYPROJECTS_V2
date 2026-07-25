# MAPGOT v2 — Model Specification (draft 1, 2026-07-25)

Scope (per Seb 2026-07-25): live pricing, in 3rd-period 3-goal-gap situations,
of the three markets actually bet:
  M1  LEADING TEAM team total OVER      → needs P(leader scores ≥ k more)
  M2  GAME total OVER                   → needs P(total goals ≥ k more)
  M3  LEADING TEAM -3.5 spread          → needs P(final margin ≥ 4)
M3 (and M1/M2 for k ≥ 2) depend on the FULL goal chain to the horn, not just
the next goal — so the core engine is a forward simulation of the remaining
period, and "next goal" is an internal primitive only.
CONSEQUENCE for extraction: the chain passes through other gaps after a goal
(3→2 or 3→4), so pull hazards and goal intensities are ALSO fitted for 2-gap
and 4-gap 3rd-period windows (2-gap pulls are common; 4-gap is give-up
territory — both measured, not assumed). Gap-3 remains the entry state and
the bet trigger.
Pricing range (Seb): R from 900s (15:00) down to 180s (3:00). No prices below
3:00 (books don't offer them); data below 3:00 is still recorded and fitted.
League-agnostic; NHL is the reference implementation. All parameters FITTED —
no hand-picked constants. Every formula gets a direction sanity test (§7).

---

## 1. State space

At any second t of P3 (t = seconds elapsed, 0..1200; R = 1200 - t remaining),
a live 3-gap situation is described by:

  x = (R, pull_state, strength, trailing_side, coach_T, league)

pull_state ∈ {net_full, net_empty}
strength   ∈ {EV (5v5), T_PP (trailer on power play), T_PK (trailer shorthanded)}
             (with net_empty these become 6v5, 6v4, 5v6 skater states)
coach_T    = head coach of the trailing team (from per-game rightrail/gamesummary)

The model is a continuous-time process with two kinds of transitions:
DECISIONS (pull, return) and GOALS (which end the question for the base bet).

## 2. Components

### 2.1 Pull hazard  h(R | z)
Instantaneous rate (per second) that a not-yet-pulled trailing coach pulls,
given covariates z = (strength, coach, league).

  h(R | z) = h0_league(R) · m_strength(strength) · m_coach(coach)

- h0(R): baseline hazard curve over remaining time, estimated by discrete
  hazard on a grid (5-second bins, smoothed; shape unconstrained — the data
  decides where the pull wave peaks).
- EXPOSURE RULE: a team contributes exposure to h only in seconds where a pull
  was feasible — net full, gap still 3, and NOT shorthanded. PK seconds are
  removed from exposure instead of being zero-weighted rows (replaces v1's
  60s/0.5/0.7 hand weights entirely).
- Censoring: gap change and end of regulation censor the pull process. An
  instance that opens with 22s left contributes 22s of exposure — nothing is
  excluded, so v1's 3:00 cutoff disappears (it becomes a *pricing-table* range
  choice, not a data choice).
- m_strength: fitted multiplier (expect pulls earlier/more often on T_PP —
  v1 data: 121/270 pulls were pp_pulls).
- m_coach: hierarchical shrinkage. log m_coach ~ Normal(0, tau^2), tau fitted
  from between-coach variance (empirical Bayes). Coach effects follow the
  person, keyed by coach identity, not team. Coach-team pairs with < N_min
  observed instances carry a NEW_SITUATION flag into pricing (§6).
- Returns and re-pulls (voluntary return with no goal, then re-pull — see
  ground truth 2024020053) are modeled as an off/on process only if they are
  frequent enough to matter; first fit measures their frequency. If rare,
  net_empty is treated as absorbing until a goal or gap change and the error
  is quantified, not assumed.

### 2.2 Goal intensities  mu_s
Poisson rates (goals/second, both directions separately) for each skater
state s, fitted ONLY from 3-gap 3rd-period exposure (garbage-time rates are
not league-average rates):

  mu_EN_against : leader scores into the empty net   (per net-empty second)
  mu_6v5_for    : trailer scores with the extra man  (per net-empty second)
  mu_EV_for/against, mu_PP, mu_PK : net-full states

Each rate = (goal count in state) / (seconds of exposure in state), aggregated
over the lake; league-level, with a season drift check (rates 24-25 vs 25-26
must be statistically compatible or the difference is investigated).

### 2.3 The pricing integral
Given live state x0 at remaining time R0, the probability of NO further goal
by the horn:

  P(no goal | x0) = E over pull-time paths of exp( -∫_0^{R0} mu(state(u)) du )

computed by numerical forward integration on a 1-second grid:
- if net already empty: state evolves only via goals → closed-form-ish decay
- if net full: at each second, pull occurs with hazard h(R|z); integrate over
  the pull-time distribution this induces (discrete mixture over pull seconds
  + never-pull path).
P(≥1 goal) = 1 - P(no goal).  Extension to P(≥k) (for totals lines needing 2+)
runs the same chain forward past the first goal with gap-updated behavior —
phase 2 of the spec; base product prices the next-goal event.

### 2.4 Market layer
Book price (American odds) → implied probability p_mkt (vig-adjusted using the
two-sided market when both sides are quoted; single-sided fallback documented).
  edge = p_model - p_mkt
  EV per unit stake = p_model·(payout) - (1 - p_model)
Bet trigger: edge lower-bound rule (§6), never point-estimate alone.

## 3. Estimation protocol

1. Extraction (hockeycore.gap) produces per-instance event-level records —
   the same schema the ground truth uses, so exact-value gates apply directly.
2. Exposure/event tables built per second-state; fit h0 per league, then
   m_strength, then coach effects (sequential, each step frozen before next).
3. Fit on 2024-25, validate on 2025-26 (walk-forward), then refit on both for
   production with the validation report retained.
4. Every fitted curve is plotted and eyeballed against raw binned data —
   smoothing must never contradict the bins it came from.

## 4. Shrinkage details

- Coach effect: for coach c with e_c weighted exposure and observed/expected
  pulls O_c/E_c, posterior multiplier ≈ (O_c + k) / (E_c + k) where k is set
  by the fitted between-coach variance (Gamma-Poisson empirical Bayes).
  Coaches with tiny samples sit near 1.0 by construction (Roy rule: strong
  priors travel with the coach; new-team evidence updates fast because the
  coach-team pair carries inflated variance until N_min instances observed).
- League rates: no pooling of absolute rates across leagues; structural
  pooling (curve SHAPES) allowed only if EIHL/Liiga samples are too thin and
  the pooling is documented + sensitivity-tested.

## 5. What is deliberately NOT modeled (with reasons)

- Future penalty occurrence as a forecast: self-marginalizing if exposure and
  outcomes come from the same empirical process (measured: trailing-team PK
  affects ~2% of no-pull exposure). Current strength IS conditioned on.
- Shot-level detail, player identity (parked with NEXTGOALPROP).
- Overtime (unreachable from a 3-gap).

## 6. Uncertainty & bet rules

- Every p_model ships with an interval from parameter uncertainty (Poisson
  counts → delta method or bootstrap over games).
- Bet only if (p_model_lower - p_mkt) > threshold_league (thresholds set from
  backtest, not vibes).
- NEW_SITUATION flag (coach-team pair with < N_min instances, rookie coach,
  interim): interval widened; default policy = reduced stake or skip, Seb's
  choice per league.

## 7. Direction sanity tests (each is an automated test in tests/)

D1  p_model(≥1 goal) increases with R (more time, more goals).
D2  p_model increases when net_empty vs net_full at same R.
D3  mu_EN_against > mu_EV_against (empty net concedes more).
D4  mu_6v5_for > mu_EV_for (extra attacker scores more).
D5  Pull hazard integrated over a window increases as R decreases within the
    normal pull band (teams pull more urgently later), until the band ends.
D6  m_strength(T_PP) > m_strength(EV) (pull more readily on the PP) — if data
    contradicts this, investigation before acceptance, not silent acceptance.
D7  Removing PK seconds from exposure raises h0 vs naive (sign check of the
    exposure correction).
D8  A coach with zero instances has multiplier exactly 1.0 (shrinkage sanity).
D9  Edge is antisymmetric: swapping p_model/p_mkt flips the sign of EV.
D10 P(≥2 goals) < P(≥1 goal) everywhere (monotone in k).

## 8. Open decisions for Seb

1. Base market to price first: next-goal-before-horn vs specific totals lines
   (v1 calculator format suggests both; next-goal is the primitive).
2. N_min for the NEW_SITUATION flag and the default action (skip vs half-stake).
3. Edge thresholds per league once the backtest exists.
4. Whether pricing tables surface below 3:00 remaining (data now supports it;
   v1 never priced there).
