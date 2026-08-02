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

HL = 6.0    # ruling 31: recency half-life FITTED predictively (was 10 by ruling)
GRID = (2, 3, 4, 5, 6, 7, 9, 12)
FADE_START, FADE_HL = 6, 8.0   # rulings 30+31: fade from 6 (Seb constraint <8; data mildly preferred 8, cost ~0.0004 — on record)


def posterior(seq, A, B):
    """Recency-weighted Beta posterior with CAREER-FADED league anchor
    (ruling 30, Seb 2026-08-02: 'league standards bring little to no value'
    once a coach has a real record — confirmed predictively: established-
    coach forecasts are flat-to-better with the anchor faded; small-n
    shrinkage unchanged). S_eff = S * 0.5^(max(career_n - 6, 0)/8)."""
    n = len(seq)
    kw = sum(x * 0.5 ** ((n - 1 - i) / HL) for i, x in enumerate(seq))
    nw = sum(0.5 ** ((n - 1 - i) / HL) for i in range(n))
    fade = 0.5 ** (max(n - FADE_START, 0) / FADE_HL)
    a_e, b_e = A * fade, B * fade
    return (kw + a_e) / (nw + a_e + b_e)


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
