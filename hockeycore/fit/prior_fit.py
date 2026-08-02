"""
prior_fit.py — coach estimator core (rule 15: ONE implementation, used by
profiles + both backtests in every league).

Sequences are chronological lists of (date_iso, took) tuples.

RECENCY (ruling 32, FITTED 2026-08-02): CALENDAR decay — each chance's weight
halves every 12 months of age. Beat per-chance decay in NHL+AHL, tied Liiga.
"Last season ~half weight, two seasons ago ~quarter" regardless of how many
chances came between.

LEAGUE ANCHOR (rulings 30-32): prior strength fitted predictively per league
(GRID), then FADED with career evidence: S_eff = S * 0.5^(max(n-3,0)/3) —
"league average a whisper past 3 chances" (Seb ruling 2026-08-02, ON RECORD:
predictive cost vs start-6/hl-8 = 0.0076 NHL / 0.0064 AHL / 0.0019 Liiga per
prediction; Seb heard the numbers and ruled for the fast fade — rule 0b
satisfied).
"""
import math
from datetime import date as _date

CAL_HL_MONTHS = 12.0
FADE_START, FADE_HL = 3, 3.0
GRID = (2, 3, 4, 5, 6, 7, 9, 12)
HL = 6.0   # legacy per-chance constant; retained only for old references


def _days(d1, d0):
    y1, m1, dd1 = map(int, d1[:10].split("-"))
    y0, m0, dd0 = map(int, d0[:10].split("-"))
    return (_date(y1, m1, dd1) - _date(y0, m0, dd0)).days


def _weights(seq, asof=None):
    """calendar-decay weights for a (date, took) sequence."""
    if not seq:
        return 0.0, 0.0
    asof = asof or seq[-1][0]
    kw = nw = 0.0
    for d, took in seq:
        w = 0.5 ** (max(_days(asof, d), 0) / (CAL_HL_MONTHS * 30.44))
        kw += w * took
        nw += w
    return kw, nw


def _fade(n):
    return 0.5 ** (max(n - FADE_START, 0) / FADE_HL)


def posterior(seq, A, B, asof=None):
    kw, nw = _weights(seq, asof)
    f = _fade(len(seq))
    a_e, b_e = A * f, B * f
    tot = nw + a_e + b_e
    return (kw + a_e) / tot if tot > 0 else A / (A + B)


def posterior_detail(seq, A, B, asof=None):
    """(mean, kw, nw, a_eff, b_eff) — for uncertainty bands."""
    kw, nw = _weights(seq, asof)
    f = _fade(len(seq))
    a_e, b_e = A * f, B * f
    tot = nw + a_e + b_e
    m = (kw + a_e) / tot if tot > 0 else A / (A + B)
    return m, kw, nw, a_e, b_e


def fit_prior(seqs):
    """seqs: iterable of chronological (date, took) lists.
    Returns (a, b, mu, strength) — strength by out-of-sample prediction."""
    seqs = [s for s in seqs if s]
    allc = [t for s in seqs for _, t in s]
    mu = sum(allc) / len(allc)
    best = None
    for S in GRID:
        ll = n = 0
        for s in seqs:
            for i in range(1, len(s)):
                kw, nw = _weights(s[:i], asof=s[i][0])
                f = _fade(i)
                p = min(max((kw + mu * S * f) / (nw + S * f), 0.01), 0.99)
                ll += math.log(p if s[i][1] else 1 - p)
                n += 1
        if best is None or ll / n > best[1]:
            best = (S, ll / n)
    S = best[0]
    return mu * S, (1 - mu) * S, mu, S
