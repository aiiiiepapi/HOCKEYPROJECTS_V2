# Mestis lake — Manager rule-0 verification (2026-08-03)

Independent verification of lake commit `5c57304` (branch
`mestis-data-lake`, V2 repo). Verifier re-derived from raw files
(`/root/verify_mestis_independent.py` logic, NOT the scrape session's
`tools/verify_mestis_lake.py`).

## PASS — structural layer (all 4 seasons)

| Season | ICS events | Games on disk | Artifacts | sha256 re-hash | Stray | Truncated |
|---|---|---|---|---|---|---|
| 2023 | 364 | 364 | 4/4 all | 1459/1459 ok | 0 | 0 |
| 2024 | 312 | 312 | 4/4 all | 1251/1251 ok | 0 | 0 |
| 2025 | 245 | 245 | 4/4 all | 983/983 ok | 0 | 0 |
| 2026 | 245 | 245 | 4/4 all | 983/983 ok | 0 | 0 |

ICS↔disk reconciliation 0 missing / 0 extra both directions (matchnos
extracted from ICS DESCRIPTION URLs, independent of the manifests).
Manifest coverage complete (no unmanifested files).

## Content claims reproduced

- goalie-out games ("Maalivahti ulos" in seuranta): 303/242/185/205 —
  matches handoff exactly.
- pois-interval games: 226/186/155/179 — matches exactly.
- rosters.json present: 1,166/1,166 — matches.
- Spot checks (seed 20260803, 2/season): event channel and pois channel
  AGREE where both exist (e.g. 2023/7362 ulos 57:30 / sisään 59:28 ↔
  pois 57:30-59:28; 2023/7425 multi-pull windows line up).

## CORRECTION to the handoff (15b): HC coverage is NOT 1,166/1,166

"Game-level Head Coach per team in every rosters.json" fails at the
per-side granularity: **19 games are missing Vastuuvalmentaja (RoleID 7)
on exactly one side** — side-level coverage 2,313/2,332 = 99.2%.
No hidden HC under another role (role inventory checked; Valmentaja=8 is
assistant). AHL-style handling applies: game listing wins, hand-curated
map fills blanks (cf. data/coach_maps/ahl_coaches.csv).

Missing-HC games (season/matchno, side missing):
- 2023: 7315 Home, 7363 Away, 7452 Away
- 2024: 3899 Home, 3944 Home, 4105 Home
- 2025: 3014 Home, 3159 Home, 3176 Home
- 2026: 2949 Home, 2970 Away, 2976 Home, 3002 Away, 3094 Away,
  3099 Home, 3124 Away, 3129 Home, 3144 Away, 3173 Home

## Adapter-relevant findings (recorded now, handled at adapter build)

1. **The two goalie channels are COMPLEMENTARY, not redundant-complete.**
   Games with ulos events but no pois interval exist (e.g. 2025/2986,
   2025/3175), and at least one game has a pois interval with no
   matching ulos event at that time (2026/3142: ulos only at 47:01 —
   likely a swap — but pois 56:28-60:00). The adapter must UNION the
   channels, then classify (pull vs swap) per quirk 5.
2. **Sisään-without-ulos games**: 29/26/21/16 per season — in-events
   with no out-event in the same feed (swap semantics suspected).
   Classification is adapter logic; counted here so the number is on
   record before any extraction.
3. Duplicate event rows exist (2023/7425 shows "Maalivahti ulos" twice
   at 58:41 plus a stray 58:29 row) — adapter needs dedup.

## Verdict

Lake ACCEPTED as raw-data authority for Mestis. Handoff table accurate
except the HC-100% claim (corrected above; raw data itself is fine —
the gap is real absence on the source, not a fetch defect).
Open question for Seb: lake branch lives on the V2 repo (v1 write token
unavailable to sessions); amend the convention or move it.
