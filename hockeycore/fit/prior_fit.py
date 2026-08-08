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
import os
from datetime import date as _date

CAL_HL_MONTHS = 12.0
FADE_START, FADE_HL = 3, 3.0
GRID = (2, 3, 4, 5, 6, 7, 9, 12)
HL = 6.0   # legacy per-chance constant; retained only for old references

# Ruling 33 (Seb 2026-08-02): a coach whose raw record is 75%+ pulls with at
# least 2 chances gets the league anchor capped at ONE chance-equivalent.
# ("weight on a 3/5 but not a 3/4; weight on a 1/1 but not on 2/2")
# Pull-side only as ruled; low-side coaches keep the normal fade.
HOT_RATE, HOT_MIN_N, HOT_CAP = 0.75, 2, 1.0


def _anchor_strength(seq, S):
    """effective league pseudo-chances for this coach's raw record."""
    n = len(seq)
    s_eff = S * _fade(n)
    if n >= HOT_MIN_N and sum(t for _, t in seq) / n >= HOT_RATE:
        s_eff = min(s_eff, HOT_CAP)
    return s_eff


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
    mu, S = A / (A + B), A + B
    s_eff = _anchor_strength(seq, S)
    a_e, b_e = mu * s_eff, (1 - mu) * s_eff
    tot = nw + a_e + b_e
    return (kw + a_e) / tot if tot > 0 else mu


def posterior_detail(seq, A, B, asof=None, mode=None):
    """(mean, kw, nw, a_eff, b_eff) — for uncertainty bands.
    RULING 50: under the default no-anchor mode the 'prior' counts are the
    neutral Jeffreys half-chances, NOT league-derived pseudo-chances — the
    bands stay honest without smuggling the league average back in."""
    kw, nw = _weights(seq, asof)
    if (mode or os.environ.get("HP_ESTIMATOR", DEFAULT_MODE)) != "incumbent":
        a_e = b_e = JEFFREYS
        tot = nw + a_e + b_e
        return (kw + a_e) / tot, kw, nw, a_e, b_e
    mu, S = A / (A + B), A + B
    s_eff = _anchor_strength(seq, S)
    a_e, b_e = mu * s_eff, (1 - mu) * s_eff
    tot = nw + a_e + b_e
    m = (kw + a_e) / tot if tot > 0 else mu
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
                s_eff = _anchor_strength(s[:i], S)
                p = min(max((kw + mu * s_eff) / (nw + s_eff), 0.01), 0.99)
                ll += math.log(p if s[i][1] else 1 - p)
                n += 1
        if best is None or ll / n > best[1]:
            best = (S, ll / n)
    S = best[0]
    return mu * S, (1 - mu) * S, mu, S


# ---------------------------------------------------------------------------
# SHEET ESTIMATOR (ruling 44, Seb 2026-08-07, scope: coach-intel sheets only;
# the validated pricing estimator above is UNTOUCHED pending re-exams).
# NO league average in the calculation. Calendar recency unchanged (within-
# career, ruling 32). The ONLY stabilizer is a Jeffreys half-chance each way
# (a=b=0.5) — a neutral 50/50 statistical prior, NOT a league number: it
# stops 2/2 from printing a flat 100% (measured 3-streak continuation is 67%,
# n=79 — Seb heard this and ruled; drop JEFFREYS to 0 for raw records).
# Perfect records weigh heavily as ruled: 2/2 -> ~83%, 0/2 -> ~17%.
JEFFREYS = 0.5


def _season_year(d):
    y, m = int(d[:4]), int(d[5:7])
    return y - 1 if m < 9 else y


def posterior_sheet(seq, asof=None, window_season=None):
    """(mean, lo, hi, n) with NO league anchor. seq: [(date, took)].
    RULING 44b (Seb 2026-08-07, amended same day): the sheet record is
    the NEWEST season; the PREVIOUS season keeps its weight through the
    new season's opening months and drops on JANUARY 1 ("last season
    keeps weight until at least january 1st"). Older seasons carry ZERO
    weight always (career = context on the sheet, never blended).
    Today (post-Jan-1 of the 25-26 season): 2025-26 only — Jan/Mar 2025
    chances are 2024-25 and excluded, per Seb's ruling.
    Returns (None, None, None, 0) for a no-data coach."""
    if window_season is not None:
        cutoff = f"{window_season + 1}-01-01"
        bridge = (asof or "9999")[:10] < cutoff
        seq = [(d, t) for d, t in seq
               if _season_year(d) == window_season
               or (bridge and _season_year(d) == window_season - 1)]
    if not seq:
        return None, None, None, 0
    kw, nw = _weights(seq, asof)
    a, b = kw + JEFFREYS, (nw - kw) + JEFFREYS
    m = a / (a + b)
    sd = (m * (1 - m) / (a + b + 1)) ** 0.5
    return m, max(m - 1.28 * sd, 0.0), min(m + 1.28 * sd, 1.0), len(seq)


# ---------------------------------------------------------------------------
# ESTIMATOR MODE SWITCH (ruling 49 re-exams, 2026-08-08). Rule 15: ONE
# implementation — every pricing consumer (backtest.py NHL, backtest_interval
# .py Liiga/Mestis, backtest_density.py) calls posterior_mode, which selects
# between the incumbent and the ruling-44 candidates. Default is INCUMBENT:
# nothing changes in production unless HP_ESTIMATOR is set, and it only ships
# if Seb rules on the exam numbers.
#   incumbent : rulings 29-33 — league anchor (fitted S, whisper fade, hot cap)
#   noanchor  : ruling 44 stabilizer only (Jeffreys 0.5/0.5), FULL career,
#               calendar decay — the realistic pricing candidate
#   window    : full ruling 44/44b — noanchor + season window w/ Jan-1 bridge;
#               a coach with no chances in the window falls back to the league
#               mean (a pricer must return a number; the SHEET prints NO-BET,
#               which has no pricing analogue — see ruling 49's stated
#               expectation that this config degrades)

# RULING 50 (Seb, 2026-08-08): "dont want league average anywhere, pointless."
# The league anchor is REMOVED from production pricing, not just sheets. The
# re-exams (docs/ESTIMATOR_REEXAM_2026-08-08.md) found no config measurably
# better OR worse than the incumbent on paired skill bootstrap, so this costs
# nothing measurable and satisfies the principle. NOTE the 'window' mode is
# NOT the ruled config: it falls back to the league mean for coaches with no
# window chances, which reintroduces the very number this ruling bans.
DEFAULT_MODE = "noanchor"


def posterior_mode(seq, A, B, asof=None, mode=None):
    mode = mode or os.environ.get("HP_ESTIMATOR", DEFAULT_MODE)
    if mode == "incumbent":
        return posterior(seq, A, B, asof)
    if mode == "noanchor":
        kw, nw = _weights(seq, asof)
        return (kw + JEFFREYS) / (nw + 2 * JEFFREYS)
    if mode == "window":
        ws = _season_year(asof) if asof else None
        m, _, _, n = posterior_sheet(seq, asof=asof, window_season=ws)
        return m if m is not None else A / (A + B)
    raise ValueError(f"unknown HP_ESTIMATOR {mode!r}")
