# AHL coach map — verification notes (2026-08-01)

Fills the 8 team-season blocks where clubs stopped filing head coaches in the
HockeyTech gamesummary feed. JOIN RULE: the gamesummary head-coach listing
always wins; this map is a FALLBACK for blank games only. Codes are LAKE codes
(BEL, HFD, SPR, CGY, UTC, RFD, CHI), not the curator's originals.

Corrections applied to the cheap-session curation (all re-verified):
1. Team codes SEN->BEL, UTA->UTC (curation codes did not match the lake; a
   join would have matched zero rows).
2. CGY: "Cirella from early December" was WRONG. Official Flames announcement
   (nhl.com/flames, dated 2024-12-22): Cull to Flames as interim assistant,
   Cirella interim HC of the Wranglers. Lake listings agree (Cull listed
   through the 2024-12-22 game). Cirella effective 2024-12-23.
3. CGY: Brett Sutter ran the bench 2025-02-01..~2025-02-14 (Cirella eye
   surgery, "next two weeks", announced Feb 1 — Yahoo/THN). The curator's
   "Sutter reports Jan 1" was wrong. This window contains TWO games with
   gap-3 pull situations (2025-02-01 gid 1027135 pull at 14:41; 2025-02-07
   gid 1027153 pull at 19:02) — those decisions are attributed to SUTTER.
   The 2025-02-15 boundary game has no gap-3 chance, so the edge is moot.
4. Final-stint end dates extended to 04-30 (curation ended some stints a week
   before the season did, leaving blank games uncovered — e.g. HFD games to
   2024-04-21 vs curation end 2024-04-14).
5. HFD 2023-11-12 game (Knoblauch announced gone that day, Smith announced
   Nov 13): attributed to Smith. No gap-3 chance in that game — immaterial.
6. SPR 2023-12-13 game: Bannister promoted + Tkaczuk appointed same day;
   that evening's game attributed to Tkaczuk.

Ambiguity ledger (what a chance in these zones would carry):
- CGY 2025-02-15: Cirella-vs-Sutter edge, no chance present -> no flag needed.
- All other blocks: single successor, exact dates from primary sources.

92 games with P3 gap-3 (trailing) situations fall inside the 8 blank blocks —
this map is what keeps ~4% of AHL chances attributable.
