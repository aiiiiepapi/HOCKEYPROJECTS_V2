# -3.5 (marg4) investigation — CORRECTED 2026-08-01 (same day)

RETRACTION: the "coach-tier-dependent EN conversion" claim below was WRONG —
training-season data (22-25) shows conversion FLAT across P_c buckets
(38.8/27.0/35.3, slope ~0). The 25-26 tier gradient was small-n noise; the
original note even carried the rule-15b caveat and still over-claimed. The
measured truth: 25-26 tail coaches regressed ~2sigma against their estimates
(season wobble, pooled persistence 0.99 [0.42..1.50]) — no structural defect
found beyond that. marg4's -4to-5pt optimism REMAINS OPEN; it is not the
coach layer. Next candidate when data grows: direction-mix dynamics after
widening (reality shows more two-way traffic than the sim).


## What was tested and refuted
1. Survival-mapped coach law k = ln(1-P_c)/ln(1-P̄) (window-independent,
   replaces raw-EB m + 0.355 attenuation). The ESTIMATOR is vindicated:
   cross-season slope of realized-on-estimate beta = 1.13 (~1.0; raw-EB
   multipliers were 0.36). But pricing with it made marg4 WORSE
   (-4.0 -> -4.8) and total1 worse (-1.8 -> -2.8): truer pull probabilities
   amplify a downstream defect. NOT adopted for pricing yet.
2. Gap-4 post-ENG repull stickiness: refuted by data (2/217 = 1% real
   repulls; sim agrees). Not the mechanism.

## The actual mechanism (measured, 25-26 diagnostic slice)
Tier-sliced residuals are ANTISYMMETRIC around m=1: low-pull coaches'
games produce MORE leader goals than priced (+11pts lead1), high-pull
coaches' games FEWER (-7..-24pts), same signature on marg4 (-16pts at
m=1.2-1.3, z=-4). Cause: EN-against conversion is coach-tier dependent:

   tier 0.8/0.9:  35-65 ENGs/60 EN-min   (reluctant pullers, small n)
   tier 1.0:      23.3 (= pooled fit 23.5)
   tier 1.2/1.3:  16.6 / 7.3             (aggressive pullers)

The sim charges every coach the POOLED conversion. Aggressive pullers pull
in routine, structured situations (low conversion against); reluctant
pullers' rare pulls are late/desperate (high conversion). CAVEAT (rule 15b):
tail tiers are small-n (1-10 ENGs); direction is consistent but levels are
noisy — production fit must come from training seasons, smoothed in P_c.

## Next block (the real coach-conditional pricer)
1. Fit EN_ev:against as a smooth function of P_c on pre-25-26 data
   (log-linear in P_c or 3 buckets, exposure-weighted).
2. Price with survival-mapped hazard (k from Beta+recency P_c) AND
   coach-conditional EN conversion.
3. Blind re-validation: tier slices must flatten; aggregate marg4 bias
   toward [-2,+1]pts; lead1 stays conservative-only; then -3.5 CAUTION
   can be re-adjudicated.
Until then: production keeps the 0.355 law (it accidentally hedges the
missing conversion channel); -3.5 stays CAUTION.
