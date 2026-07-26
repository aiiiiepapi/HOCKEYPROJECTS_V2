"""
hockeycore.pricing.mc_pricer — forward Monte Carlo pricer (CALCULATIONS §5).

Vectorized over paths with numpy. Seeded. Simulates the remaining R seconds:
pull decisions (gap-specific hazard × strength × coach), voluntary returns
(fitted rate), directional goals per state, margin/goal counters; goals reset
pull state and (simplification, logged) end special strength states.
Strength persistence: a given PP/PK persists for `strength_secs` (default 60)
then reverts to EV — refinement over "persists forever", logged in ledger.

Markets: P(leader ≥1 / ≥2 more), P(total ≥1 / ≥2 more), P(final margin ≥ 4).
"""
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "data" / "derived"

_f = json.load(open(DER / "fits.json"))
_ret = json.load(open(DER / "return_fit.json"))["return_hazard_per_sec"]
try:
    _REPULL = json.load(open(DER / "repull_fit.json"))["h_repull"]
except Exception:
    _REPULL = 0.0356
try:
    _LAG = round(json.load(open(DER / "evidence_lag.json"))["evidence_lag_half_2425"])
except Exception:
    _LAG = 9  # evidence-lag midpoint correction: true pull precedes first evidence
try:
    _DEAD = round(json.load(open(DER / "deadtime_fit.json"))["dead_to_play_med"])
except Exception:
    _DEAD = 18  # post-goal reset: median clock secs to first real play event

GAPKEY = {2: "2", 3: "3", 4: "4"}


def _haz_array(gap):
    """per-second EV pull hazard by R (0..899) from 30s bins; 0 outside."""
    h = np.zeros(1200)
    for r in _f["hazard"][GAPKEY[gap]]["EV_full"]:
        v = r["h"] or 0.0
        h[r["R_lo"]:r["R_hi"]] = v
    return h

_HAZ = {g: _haz_array(g) for g in (2, 3, 4)}
_MPP = {g: (_f["m_PP"].get(GAPKEY[g], {}) or {}).get("m", 1.0) for g in (2, 3, 4)}


def _rate(gap, state, direction):
    """per-second rate with fallback chain gap→3→2, EN_pk→EN_ev."""
    for gk in (GAPKEY.get(gap, "4"), "3", "2"):
        rt = _f["rates"][gk].get(f"{state}:{direction}")
        if rt and rt["T"] > 1800 and rt["rate_per_60min"] is not None:
            return rt["rate_per_60min"] / 3600.0
        if state == "EN_pk":
            rt = _f["rates"][gk].get(f"EN_ev:{direction}")
            if rt and rt["T"] > 1800:
                return rt["rate_per_60min"] / 3600.0
    return 2.3 / 3600.0  # EV floor fallback


# Pre-resolve the small rate table we need: (gap_bucket, state, dir)
STATES = ["EV_full", "TPP_full", "TPK_full", "EN_ev", "EN_pp", "EN_pk"]
RATES = {(g, s, d): _rate(g, s, d) for g in (2, 3, 4) for s in STATES for d in ("for", "against")}


def _rate_arrays():
    """Per-second rates over R. Flat (pooled) everywhere, overwritten with
    R-bucketed fits for EV_full/EN_ev where exposure supports them
    (lead1-bias fix 2026-07-26: desperation acceleration is real)."""
    arrs = {}
    rr = _f.get("rates_R", {})
    for (g, s, d), flat in RATES.items():
        a = np.full(1200, flat)
        buckets = (rr.get(str(g)) or rr.get(g) or {}).get(f"{s}:{d}")
        if buckets:
            for b in buckets:
                if b["rate_per_60min"] is not None:
                    a[b["R_lo"]:min(b["R_hi"], 1200)] = b["rate_per_60min"] / 3600.0
        arrs[(g, s, d)] = a
    return arrs

RATES_ARR = _rate_arrays()


def _pen_tab():
    pen = _f.get("pen", {})
    out = {}
    for g in (2, 3, 4):
        e = pen.get(str(g)) or pen.get(g) or {"h_pk": 0.0, "h_pp": 0.0}
        out[g] = (e["h_pk"], e["h_pp"])
    return out

PEN = _pen_tab()


def rebuild(f_new):
    """Re-point the pricer at a different fits dict (backtest rewiring)."""
    global _f, _HAZ, _MPP, RATES, RATES_ARR
    _f = f_new
    _HAZ = {g: _haz_array(g) for g in (2, 3, 4)}
    _MPP = {g: (_f["m_PP"].get(GAPKEY[g], {}) or {}).get("m", 1.0) for g in (2, 3, 4)}
    RATES = {(g, s, d): _rate(g, s, d) for g in (2, 3, 4) for s in STATES for d in ("for", "against")}
    RATES_ARR = _rate_arrays()
    global PEN
    PEN = _pen_tab()


def _pen_tab():
    pen = _f.get("pen", {})
    out = {}
    for g in (2, 3, 4):
        e = pen.get(str(g)) or pen.get(g) or {"h_pk": 0.0, "h_pp": 0.0}
        out[g] = (e["h_pk"], e["h_pp"])
    return out

PEN = _pen_tab()


def price(R0, pulled0=False, strength0="EV", m_coach=1.0, gap0=3,
          n=40000, seed=7, strength_secs=60, coach_shift=0, penalties=True):
    rng = np.random.default_rng(seed)
    lead_goals = np.zeros(n, dtype=np.int32)
    trail_goals = np.zeros(n, dtype=np.int32)
    margin = np.full(n, gap0, dtype=np.int32)          # leader - trailer
    pulled = np.full(n, pulled0, dtype=bool)
    ever_pulled = pulled.copy()
    # strength from the TRAILING team's perspective: +1 PP, -1 PK, 0 EV
    sval = {"EV": 0, "T_PP": 1, "T_PK": -1}[strength0]
    strength = np.full(n, sval, dtype=np.int8)
    s_clock = np.full(n, strength_secs if sval else 0, dtype=np.int32)
    dead = np.zeros(n, dtype=np.int32)     # post-goal reset: no pulls, no goals

    for u in range(R0, 0, -1):
        gb = np.clip(margin, 2, 4)                     # gap bucket (margin 1 -> gap-2 proxy, documented)
        # --- pull / return decisions (margins 1..4 pull; PK can't pull)
        can_pull = (~pulled) & (margin >= 1) & (strength >= 0)
        u3 = min(max(u - 1 - coach_shift - _LAG, 0), 1199)  # coach shift + evidence-lag correction (3-gap)
        uL = min(max(u - 1 - _LAG, 0), 1199)
        hz = np.where(gb == 2, _HAZ[2][uL], np.where(gb == 3, _HAZ[3][u3], _HAZ[4][uL]))
        mpp = np.where(gb == 2, _MPP[2], np.where(gb == 3, _MPP[3], _MPP[4]))
        h_eff = hz * np.where(strength == 1, mpp, 1.0) * m_coach
        # re-pull dynamics: once committed, return to empty net is ~10x faster (fitted 24-25)
        h_eff = np.where(ever_pulled & (margin <= 3), np.maximum(h_eff, _REPULL), h_eff)
        h_eff = np.where(dead > 0, 0.0, h_eff)
        r1 = rng.random(n)
        pulled = pulled | (can_pull & (r1 < h_eff))
        ever_pulled = ever_pulled | pulled
        # voluntary return
        r2 = rng.random(n)
        pulled = pulled & ~(r2 < _ret)
        # --- in-sim penalty generation (lead1-bias fix 2026-07-26: 17% of
        # leader goals come on the PP; the sim must create penalties, not just
        # inherit them). Only from full-net EV, one at a time, 120s minors.
        if penalties:
            ev_open = (~pulled) & (strength == 0) & (dead == 0)
            hpk = np.where(gb == 2, PEN[2][0], np.where(gb == 3, PEN[3][0], PEN[4][0]))
            hpp = np.where(gb == 2, PEN[2][1], np.where(gb == 3, PEN[3][1], PEN[4][1]))
            r5 = rng.random(n)
            new_pk = ev_open & (r5 < hpk)
            new_pp = ev_open & ~new_pk & (r5 < hpk + hpp)
            strength = np.where(new_pk, -1, np.where(new_pp, 1, strength))
            s_clock = np.where(new_pk | new_pp, 120, s_clock)
        # --- state → rates
        lam_f = np.empty(n); lam_a = np.empty(n)
        for g in (2, 3, 4):
            for sv, full_s, en_s in ((0, "EV_full", "EN_ev"), (1, "TPP_full", "EN_pp"), (-1, "TPK_full", "EN_pk")):
                m = (gb == g) & (strength == sv)
                if not m.any():
                    continue
                mp = m & pulled; mf = m & ~pulled
                ui = min(u - 1, 1199)
                lam_f[mp] = RATES_ARR[(g, en_s, "for")][ui];   lam_a[mp] = RATES_ARR[(g, en_s, "against")][ui]
                lam_f[mf] = RATES_ARR[(g, full_s, "for")][ui]; lam_a[mf] = RATES_ARR[(g, full_s, "against")][ui]
        # margins <1 (tied or flipped): EV full-net rates, no pull
        low = margin < 1
        if low.any():
            ui = min(u - 1, 1199)
            lam_f[low] = RATES_ARR[(2, "EV_full", "for")][ui]; lam_a[low] = RATES_ARR[(2, "EV_full", "against")][ui]
            pulled = pulled & ~low
        # --- goals (suppressed during post-goal reset)
        lam_f = np.where(dead > 0, 0.0, lam_f)
        lam_a = np.where(dead > 0, 0.0, lam_a)
        r3 = rng.random(n); r4 = rng.random(n)
        gf = r3 < lam_f
        ga = (~gf) & (r4 < lam_a)                      # at most one goal per second
        trail_goals += gf; lead_goals += ga
        margin = margin - gf.astype(np.int32) + ga.astype(np.int32)
        scored = gf | ga
        dead = np.where(scored, _DEAD, np.maximum(dead - 1, 0))
        pulled = pulled & ~scored
        strength = np.where(scored, 0, strength)       # goals end penalties (simplification)
        # strength clock
        s_clock = np.maximum(s_clock - 1, 0)
        strength = np.where(s_clock == 0, 0, strength)

    total = lead_goals + trail_goals
    out = {
        "P_leader_ge1": float((lead_goals >= 1).mean()),
        "P_leader_ge2": float((lead_goals >= 2).mean()),
        "P_total_ge1": float((total >= 1).mean()),
        "P_total_ge2": float((total >= 2).mean()),
        "P_margin_ge4": float((margin >= 4).mean()),
        "n": n, "seed": seed,
    }
    out["se_max"] = float(np.sqrt(0.25 / n))
    return out


def p_next_goal_recursion(R0, m_coach=1.0, gap0=3, coach_shift=0):
    """Exact P(≥1 goal) before horn from not-pulled EV state — first-goal only,
    so gap is constant until absorption; cross-check for the MC."""
    lam_full_arr = RATES_ARR[(gap0, "EV_full", "for")] + RATES_ARR[(gap0, "EV_full", "against")]
    lam_en_arr = RATES_ARR[(gap0, "EN_ev", "for")] + RATES_ARR[(gap0, "EN_ev", "against")]
    # 3 states: full-never-pulled, full-committed (re-pull hazard), pulled
    Vp = np.zeros(R0 + 1); Vf = np.zeros(R0 + 1); Vc = np.zeros(R0 + 1)
    Vp[0] = Vf[0] = Vc[0] = 1.0
    for u in range(1, R0 + 1):
        ui = min(u - 1, 1199)
        a_full = np.exp(-lam_full_arr[ui]); a_en = np.exp(-lam_en_arr[ui])
        q = _HAZ[gap0][min(max(u - 1 - coach_shift - _LAG, 0), 1199)] * m_coach
        qc = max(q, _REPULL)
        Vp[u] = a_en * (_ret * Vc[u - 1] + (1 - _ret) * Vp[u - 1])
        Vc[u] = a_full * ((1 - qc) * Vc[u - 1] + qc * Vp[u - 1])
        Vf[u] = a_full * ((1 - q) * Vf[u - 1] + q * Vp[u - 1])
    return 1.0 - Vf[R0]


if __name__ == "__main__":
    # toy hand-check: net empty, 100s, no return/pull dynamics beyond formula
    lam = RATES[(3, "EN_ev", "for")] + RATES[(3, "EN_ev", "against")]
    print("toy: P(>=1 | pulled, R=100) closed-form-ish =", 1 - np.exp(-lam * 100))
    print("     MC =", price(100, pulled0=True, n=200000)["P_total_ge1"])
    # recursion vs MC gate
    for R in (300, 600, 900):
        rec = p_next_goal_recursion(R)
        mc = price(R, n=200000)["P_total_ge1"]
        print(f"R={R}: recursion {rec:.4f} vs MC {mc:.4f}  Δ={abs(rec-mc):.4f}")
