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
RECENT = {"ahl": ("86", "90"), "liiga": ("2025", "2026"), "mestis": ("2025", "2026")}[LG]
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
active = sorted([r for r in rows if r["last_seen"] >= SEASON_START],
                key=lambda r: -r["expected_pull_pct"])
stale = sorted([r for r in rows if r["last_seen"] < SEASON_START],
               key=lambda r: -r["expected_pull_pct"])
meta = prof["meta"]
L = [f"# {LG.upper()} MORNING SHEET — coach pull expectancy (ruling-33 estimator)", ""]
if LG == "ahl":
    L.append("STATUS: AHL = COACH INTEL ONLY — no priced markets (ruling 24). "
             "Rule 28: base % < 40 = NO-BET regardless of situation.")
elif LG == "mestis":
    L.append("STATUS: Mestis = COACH INTEL ONLY — no pricer exists yet (no blind "
             "validation; adapter+ledger gated 2026-08-03). Rule 28: base % < 40 = NO-BET.")
else:
    L.append("STATUS: Liiga = paper-trade from September (ruling 25, provisional). "
             "Rule 28: base % < 40 = NO-BET.")
L += ["Teams = last-seen bench; off-season coaching changes NOT applied — "
      "September refresh re-maps before opening night.", "",
      "## Active benches (seen 2025-26), sorted by expected pull %", "",
      "| Coach | Team | Expected % | Band | Career clean | Last 3 | PP pulls | Avg pull time (rec-wt) | Flags |",
      "|---|---|---|---|---|---|---|---|---|"]
for r in active:
    flags = list(r["flags"])
    if r["expected_pull_pct"] < 0.40: flags.append("NO-BET(<40, rule 28)")
    L.append(f'| {r["coach"]} | {r["team"]} | **{r["expected_pull_pct"]:.0%}** | '
             f'{r["band"][0]:.0%}-{r["band"][1]:.0%} | {r["clear_taken"]}/{r["clear_chances"]} | '
             f'{r["last3"] or "—"} | {r["pp_pulls"]} | {clock(r["avg"])} | {", ".join(flags) or "—"} |')
L += ["", f"Active coaches: {len(active)}. Prior mu {meta['prior_mu']:.2f}, "
      f"strength {meta['prior_strength']} (predictive fit).", "",
      "## Departed / stale benches — reference only", "",
      "| Coach | Team | Expected % | Career clean | Last seen |", "|---|---|---|---|---|"]
for r in stale:
    L.append(f'| {r["coach"]} | {r["team"]} | {r["expected_pull_pct"]:.0%} | '
             f'{r["clear_taken"]}/{r["clear_chances"]} | {r["last_seen"]} |')
out = Path(f"/home/claude/work/{LG}_morning_sheet.md")
out.write_text("\n".join(L))
print(f"wrote {out} (active {len(active)}, stale {len(stale)})")
