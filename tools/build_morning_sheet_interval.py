#!/usr/bin/env python3
"""
build_morning_sheet_interval.py {ahl|liiga|mestis} — standing coach-expectancy
morning sheet (ruling-33 estimator) from {lg}_coach_profiles.json.
Rule 13: scripted delivery artifact; output -> /home/claude/work/{lg}_morning_sheet.md
Rule 28 floor (40%) marked; AHL carries the ruling-24 intel-only banner.
Avg pull time = recency-weighted (HL 5 pulls, display-only) over last 2 seasons' EV pulls.
"""
import json, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LG = sys.argv[1]
RECENT = {"ahl": ("86", "90"), "liiga": ("2025", "2026"), "mestis": ("2025", "2026"), "shl": ("2025", "2026"), "magnus": ("2025", "2026"), "khl": ("2025", "2026")}[LG]
SEASON_START = "2025-09-01"
prof = json.load(open(ROOT / f"data/derived/{LG}_coach_profiles.json"))
inst = json.load(open(ROOT / f"data/derived/{LG}_instances_gap3.json"))
times = defaultdict(list)
for r in inst:
    if r["season"] in RECENT and r.get("pulled") and r.get("pull_classification") == "pull" \
            and r.get("pull_evidence_secs") is not None and not r.get("synthetic_pull_evidence"):
        times[r["coach"]].append((r.get("date", ""), r["pull_evidence_secs"]))
def wavg(items):
    if not items: return None
    items = sorted(items); n = len(items); ws = vs = 0.0
    for i, (_, t) in enumerate(items):
        w = 0.5 ** ((n - 1 - i) / 5); ws += w; vs += w * t
    return vs / ws
def clock(s):
    if s is None: return "n/a (no recent EV pulls)"
    return f"{int(s//60)}:{int(s%60):02d} P3 ({int((1200-s)//60)}:{int((1200-s)%60):02d} left)"
rows = [{**p, "avg": wavg(times.get(p["coach"]))} for p in prof["profiles"]]
def _sk(r):
    p = r.get("sheet_pct")
    return -(p if p is not None else -1.0)
active = sorted([r for r in rows if r["last_seen"] >= SEASON_START], key=_sk)
stale = sorted([r for r in rows if r["last_seen"] < SEASON_START], key=_sk)
meta = prof["meta"]
L = [f"# {LG.upper()} MORNING SHEET — coach pull expectancy (ruling-33 estimator)", ""]
if LG == "ahl":
    L.append("STATUS: AHL = COACH INTEL ONLY — no priced markets (ruling 24). "
             "Rule 28: base % < 40 = NO-BET regardless of situation.")
elif LG == "shl":
    L.append("STATUS: SHL = COACH INTEL ONLY — no pricer exists (no blind validation; "
             "adapter merged 2026-08-07). NOTE the SHL signature: pulls happen at gap 1-2 "
             "(29.8%% of gap-3 instances open with net already empty); down-3 pulls are rare. "
             "Rule 28: base %% < 40 = NO-BET.")
elif LG == "mestis":
    L.append("STATUS: Mestis = PROVISIONAL paper-trade from September (ruling 43, "
             "pooled multi-fold pass 2026-08-03). Rule 28: base % < 40 = NO-BET.")
elif LG == "khl":
    L.append("STATUS: KHL = COACH INTEL ONLY — no odds market at our provider "
             "(ruling 5 model-side doctrine), no pricer, no blind validation. "
             "NOTE the KHL signature: 46% of pulls ride a power play (highest in "
             "the portfolio) — pp pulls are tracked beside, never inside, the "
             "bettable number. Rule 28: base % < 40 = NO-BET.")
elif LG == "magnus":
    L.append("STATUS: Magnus = COACH INTEL ONLY, NO-GO for real money until a 26-27 "
             "blind pass or Seb override. ONE season of data (2025-26), pull timing "
             "TOI-inferred from the sheets (not evented); multi-pull games carry "
             "timing-unusable synthetic evidence. Rule 28: base % < 40 = NO-BET.")
else:
    L.append("STATUS: Liiga = paper-trade from September (ruling 25, provisional). "
             "Rule 28: base % < 40 = NO-BET.")
L += ["Teams = last-seen bench; off-season coaching changes NOT applied — "
      "September refresh re-maps before opening night.", "",
      "## Active benches (seen 2025-26), sorted by expected pull %", "",
      "| Coach | Team | Expected % | Band | This season | Career | Last 3 | PP pulls | Avg pull time (rec-wt) | Flags |",
      "|---|---|---|---|---|---|---|---|---|---|"]
# Ruling 44 (Seb 2026-08-07, sheets-first scope): display the NO-ANCHOR sheet
# estimator (sheet_pct); RISKY at <3 clean chances (was <5); a 0-chance coach
# shows NO DATA and is automatic NO-BET. League clean take rate = context only.
for r in active:
    pct = r.get("sheet_pct")
    band = r.get("sheet_band")
    flags = [f for f in r["flags"] if not f.startswith("RISKY")]
    if r.get("window_chances", 0) < 3:
        flags.append("RISKY: <3 season chances (ruling 44)")
    if pct is None:
        flags.append("NO DATA = NO-BET (ruling 44)")
    elif pct < 0.40:
        flags.append("NO-BET(<40, rule 28)")
    # Ruling 28b: pulled last clean chance OR 2 of last 3 -> HOT FORM flag
    # for manual review, regardless of % (does not authorize below floor).
    l3 = r.get("last3") or ""
    if l3.endswith("P") or l3.count("P") >= 2:
        flags.insert(0, "HOT FORM (28b: manual review)")
    pct_s = f"{pct:.0%}" if pct is not None else "NO DATA"
    band_s = f"{band[0]:.0%}-{band[1]:.0%}" if band else "—"
    win_s = f'{r.get("window_taken", 0)}/{r.get("window_chances", 0)}'
    L.append(f'| {r["coach"]} | {r["team"]} | **{pct_s}** | '
             f'{band_s} | {win_s} | {r["clear_taken"]}/{r["clear_chances"]} | '
             f'{r["last3"] or "—"} | {r["pp_pulls"]} | {clock(r["avg"])} | {", ".join(flags) or "—"} |')
L += ["", f"Active coaches: {len(active)}. Sheet estimator = coach record ONLY, "
      f"no league average (ruling 44), season window w/ Jan-1 bridge (ruling 44b; career = context, never blended); league clean take rate {meta['prior_mu']:.0%} "
      "is context, not an input.", "",
      "## Departed / stale benches — reference only", "",
      "| Coach | Team | Expected % | Career clean | Last seen |", "|---|---|---|---|---|"]
for r in stale:
    spct = f'{r["sheet_pct"]:.0%}' if r.get("sheet_pct") is not None else "NO DATA"
    L.append(f'| {r["coach"]} | {r["team"]} | {spct} | '
             f'{r["clear_taken"]}/{r["clear_chances"]} | {r["last_seen"]} |')
out = Path(f"/home/claude/work/{LG}_morning_sheet.md")
out.write_text("\n".join(L))
print(f"wrote {out} (active {len(active)}, stale {len(stale)})")
