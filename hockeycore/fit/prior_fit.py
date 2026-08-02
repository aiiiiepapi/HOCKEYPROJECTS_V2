"""
prior_fit.py — coach-prior strength fitted by PREDICTION, not spread-matching
(rule 15: one implementation, used by profiles + backtests in every league).

Ruling 29 (Seb's UTC challenge, 2026-08-01): MoM strengths over-shrank
established hot coaches (80%+ over 5+ chances continued at 75% observed vs
~65% modeled). Strength is now chosen to maximize out-of-sample next-chance
log-likelihood on the league's own chance sequences; prior mean = the league
clean-chance take rate. Small-n records are UNCHANGED by design: perfect
3-streaks continued at 67% (n=79) — the shrinkage there is correct.
"""
import math

HL = 10.0
GRID = (2, 3, 4, 5, 6, 7, 9, 12)


def fit_prior(seqs):
    """seqs: iterable of chronological 0/1 chance lists (one per coach).
    Returns (a, b, mu, strength)."""
    seqs = [s for s in seqs if s]
    allc = [x for s in seqs for x in s]
    mu = sum(allc) / len(allc)
    best = None
    for S in GRID:
        ll = n = 0
        for s in seqs:
            kw = nw = 0.0
            for i in range(1, len(s)):
                # incremental recency-weighted counts of s[:i]
                kw = kw * 0.5 ** (1 / HL) + s[i - 1]
                nw = nw * 0.5 ** (1 / HL) + 1
                p = min(max((kw + mu * S) / (nw + S), 0.01), 0.99)
                ll += math.log(p if s[i] else 1 - p)
                n += 1
        if best is None or ll / n > best[1]:
            best = (S, ll / n)
    S = best[0]
    return mu * S, (1 - mu) * S, mu, S
