"""Friendly 30-second lines workbook (Seb 2026-07-25).

One filterable table: time (30s steps, 15:00->3:00) x state x coach tier,
probabilities as %, 10%-EV American lines, color-coded, frozen header,
autofilter. Pure values (no formulas) — cheap-session rebuildable:
    python3 hockeycore/io/build_lines_table.py
"""
import json
from pathlib import Path
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import ColorScaleRule

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "data" / "derived"
OUT = ROOT / "live_model" / "lines_table_30s.xlsx"
EDGE = 0.10

STATE_LABEL = {
    "not_pulled_EV": "Net in — 5v5",
    "not_pulled_PP": "Net in — POWER PLAY",
    "pulled": "GOALIE PULLED",
}
STATE_FILL = {
    "not_pulled_EV": PatternFill("solid", fgColor="F5F5F5"),
    "not_pulled_PP": PatternFill("solid", fgColor="DCE9F7"),
    "pulled": PatternFill("solid", fgColor="FCE4D6"),
}
TIER_LABEL = {0.55: "0.55 very passive", 0.80: "0.80 passive", 1.00: "1.00 league avg",
              1.30: "1.30 aggressive", 1.85: "1.85 very aggressive", 2.40: "2.40 extreme"}
MARKETS = [("P_total_ge1", "Game total OVER"), ("P_leader_ge1", "Leader TT OVER"),
           ("P_margin_ge4", "Leader -3.5")]

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name="Arial", bold=True, color="FFFFFF")
ARIAL = Font(name="Arial")
BOLD = Font(name="Arial", bold=True)
THIN = Border(bottom=Side(style="thin", color="D9D9D9"))


def american(p, edge=EDGE):
    b = (1 + edge - p) / p
    return f"+{b*100:.0f}" if b >= 1 else f"-{100/b:.0f}"


def main():
    grid = json.load(open(DER / "pricing_grid_dense.json"))
    Rs = np.array(sorted({r["R"] for r in grid}))
    by = {(r["state"], r["tier"], r["R"]): r for r in grid}
    states = ["not_pulled_EV", "not_pulled_PP", "pulled"]
    tiers = sorted({r["tier"] for r in grid})
    times = list(range(900, 179, -30))

    wb = Workbook()
    ws = wb.active
    ws.title = "LINES"
    ws.sheet_view.showGridLines = False

    ws["A1"] = ("3-GOAL GAP, 3rd PERIOD — model probability + the line that pays +10% EV "
                "(bet only at that number or BETTER). Filter any column. NO-GO for real money; "
                "leader market = Overs only.")
    ws["A1"].font = Font(name="Arial", bold=True, size=11)
    ws.merge_cells("A1:I1")

    headers = ["Time left", "Situation", "Coach type"]
    for _, lbl in MARKETS:
        headers += [f"{lbl} — prob", f"{lbl} — line @10%"]
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=j, value=h)
        c.font = HDR_FONT; c.fill = HDR_FILL
        c.alignment = Alignment(horizontal="center", wrap_text=True)

    row = 3
    for st in states:
        for tr in tiers:
            curves = {}
            for mk, _ in MARKETS:
                ys = np.array([by[(st, tr, R)][mk] for R in Rs])
                curves[mk] = {t: float(np.interp(t, Rs, ys)) for t in times}
            for t in times:
                vals = [f"{t//60}:{t%60:02d}", STATE_LABEL[st], TIER_LABEL[tr]]
                cells = []
                for mk, _ in MARKETS:
                    p = curves[mk][t]
                    cells += [p, american(p)]
                for j, v in enumerate(vals + cells, 1):
                    c = ws.cell(row=row, column=j, value=v)
                    c.font = ARIAL
                    c.border = THIN
                    if j <= 3:
                        c.fill = STATE_FILL[st]
                    if j in (4, 6, 8):
                        c.number_format = "0.0%"
                    if j in (5, 7, 9):
                        c.font = BOLD
                        c.alignment = Alignment(horizontal="center")
                row += 1

    last = row - 1
    ws.auto_filter.ref = f"A2:I{last}"
    ws.freeze_panes = "A3"
    for col, w in zip("ABCDEFGHI", (9, 22, 20, 14, 13, 14, 13, 14, 13)):
        ws.column_dimensions[col].width = w
    # green->red scale on each probability column (high prob = green)
    for col in ("D", "F", "H"):
        ws.conditional_formatting.add(
            f"{col}3:{col}{last}",
            ColorScaleRule(start_type="min", start_color="F8696B",
                           mid_type="percentile", mid_value=50, mid_color="FFEB84",
                           end_type="max", end_color="63BE7B"))

    # legend sheet
    lg = wb.create_sheet("HOW TO USE")
    notes = [
        "HOW TO USE",
        "1. Filter 'Situation' to the current state and 'Coach type' to the trailing coach's tier (COACHES tab of the calculator).",
        "2. Find the time remaining (rows are 30-second steps; for in-between times use the calculator, which takes any mm:ss).",
        "3. The LINE column is the worst price at which the bet still clears +10% EV. Better than that number = bet; worse = pass.",
        "",
        "Reading lines: -196 means bet only at -196 or better (e.g. -180, -150, +110). +150 means +150 or longer.",
        "Coach type: multiplier applied to pull aggressiveness. 1.00 = league average. Bednar-class ~1.3-1.85; "
        "PP-only coaches (Tortorella, McLellan, Cronin, Huska): use 'Net in — POWER PLAY' rows when they have a PP, else assume near-zero pull.",
        "Colors: green = likely, red = unlikely. Blue rows = trailing team on power play. Orange rows = net already empty.",
        "Provenance: dense MC grid n=30k seed 7, fits both seasons, blind-validated 25-26 (leader TT +30.7% ROI at these lines).",
        "Rebuild (cheap session): python3 hockeycore/io/build_lines_table.py",
    ]
    for i, t in enumerate(notes, 1):
        lg.cell(row=i, column=1, value=t).font = BOLD if i == 1 else ARIAL
    lg.column_dimensions["A"].width = 130

    wb.save(OUT)
    print("saved", OUT, f"({last-2} data rows)")


if __name__ == "__main__":
    main()
