# -3.5 (marg4) root cause — nailed 2026-08-01

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
