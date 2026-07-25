# HOCKEYPROJECTS V2 — Master Plan

Date: 2026-07-24 (rev 3 — scope hardened per Seb)
Owner: Seb (Manager session: Claude/Fable)
Direction (Seb-approved, final): **full re-do with total re-verification.** Nothing from v1 is assumed correct — no pipelines, no calculators, no intermediate CSVs, not even ground truth files. The ONLY v1 artifacts that carry over are raw scraped API/HTML data and the league research docs. Ground truth is re-derived by hand-tracing raw pbp; v1 outputs serve only as shadow-comparison references whose disagreements get investigated. Priority: MAPGOT product (NHL/AHL + EIHL/Liiga folded in as league adapters). v2 in a new folder outside OneDrive. One Manager session. Freeze of v1: in progress (Seb).

---

## Portfolio verification results (measured 2026-07-24, cloud runs of v1's own test suites)

| Suite | Result | Verdict |
|---|---|---|
| shared/ (test_shared + test_gap_detection) | 42/42 PASS | **Migrate as-is** into hockeycore. |
| OT4V3 Phase 1+2 | 64/64 PASS | **Migrate as-is** (repackage, don't rewrite). |
| NEXTGOALPROP Phase 1+2+3 | 32/32 PASS | **Migrate as-is.** Registry claimed "outputs pending" — false; outputs exist on disk and pass. Registry was stale, not the project. |
| MAPGOTFINAL Phase 1 NHL | 31/32 — 1 fail | **Data is fine, gate is stale.** 802 included instances vs bound <800; the bound was written for ONE season ("~300-400 expected") but the CSV now legitimately holds TWO seasons (434 in 2024-25 + 368 in 2025-26 — each inside the intended band). v2 fix: per-season sanity bounds. |
| MAPGOTFINAL Phase 1 AHL | 42/42 PASS | Clean. |
| MAPGOTFINAL Phase 2 NHL | 60/61 | Only failure is the cumulative gate inheriting the stale Phase 1 bound. Calculator matches model. |
| MAPGOTFINAL Phase 2 AHL | **6 REAL FAILS** | **The one truly broken thing found.** AHL workbook's Over GT probabilities differ from the recomputed model by up to 6.9 pts (T=5:00: workbook 0.4533 vs model 0.3845). Workbook never regenerated after the zero_goal_returned fix. **Do not bet AHL numbers from the current workbook.** v2: regenerate + auto-sync so a workbook can never silently go stale again. |
| EIHL | NOT YET VERIFIED | No test suite exists. Verification = reproduce its workbook from cached raw_data with the unified engine. Next verification target. |
| FINLAND/Liiga | NOT YET VERIFIED | Same as EIHL. |

## What carries into v2 unchanged

Only two things: raw scraped API/HTML responses (verbatim, immutable) and league research docs (API endpoints, access notes). Everything else — including v1 ground truth and `pbp_overrides.json` — is re-derived and re-justified from raw data.

**Critical gap found:** v1 only cached raw pbp for a few hundred reference games; the full-season CSVs were built from API calls that were never saved. So the first v2 step is building a complete raw data lake: `tools/fetch_nhl_raw.py` (fetch-only, stdlib-only, resumable) downloads every completed regular-season game's pbp + boxscore for 2024-25 and 2025-26 (~2,600 games). It must run on Seb's PC (double-click `FETCH_NHL_RAW.bat`) or the Ubuntu server, since the cloud workspace can't reach the NHL API. EIHL and Liiga already have full raw caches in v1 — those port verbatim. AHL needs its own fetcher (M3).

## v2 architecture

```
HOCKEYPROJECTS_V2/
├── pyproject.toml            ← pinned deps, single install
├── CLAUDE.md                 ← constitution + live STATUS section (replaces registry)
├── hockeycore/               ← ONE installable package
│   ├── gap/                  ← league-agnostic 3-goal-gap engine (single impl, from shared/ — verified 42/42)
│   ├── pricing/              ← Poisson, odds math, shrinkage, EV (single impl)
│   ├── leagues/              ← thin adapters: nhl, ahl, eihl, liiga… (map source → common event schema)
│   └── io/                   ← caching, workbook builders, sheets sync
├── products/                 ← thin config+glue per bet product
│   ├── mapgot/               ← PRIORITY — all leagues incl. EIHL & Liiga as adapters
│   ├── ot4v3/                ← migrated as-is
│   └── nextgoalprop/         ← migrated as-is
├── tests/                    ← v1 ground truth ported; per-season sanity bounds
└── data/                     ← cached raw data + outputs (gitignored)
```

Migration ≠ rewrite: OT4V3 and NEXTGOALPROP code moves over with imports repointed at hockeycore and tests kept green. Rebuild effort concentrates where verification failed or never existed: the AHL workbook path, and EIHL/Liiga (which also violate rule 16 by reimplementing gap logic — their local implementations die).

## Verification protocol (for anything rebuilt)

1. v1 ground truth reproduced exactly (same test-gate philosophy).
2. Shadow comparison vs v1 outputs on identical cached data; every discrepancy attributed in a written log (v1 bug / v2 bug / intentional) before trust.
3. Direction sanity tests on every betting-relevant formula.
4. Done = ground truth + shadow diff attributed + direction tests + end-to-end fresh-data run.

## Environment facts (design constraints)

- Cloud workspace cannot reach api-web.nhle.com from Python/shell (proxy 403); WebFetch tool can (single-game verification only). → v2 develops/verifies against cached data in the cloud; bulk fresh pulls run on Seb's PC (double-click script) or the Ubuntu server. Fetchers are separated from processing for this reason.
- OneDrive placeholder files break both git and direct file reads through the device bridge; only staged transfers work. → v2 lives OUTSIDE OneDrive (recommend `C:\dev\HOCKEYPROJECTS_V2`), GitHub as backup. v1 stays in OneDrive as frozen reference.
- Server deployment becomes `git pull`; base64-blob scripts retire.

## Build order

1. **M0 — Freeze v1 + data lake.** Seb: finish the freeze; run `FETCH_NHL_RAW.bat` (resumable, a few hours first run). Claude: port EIHL/Liiga raw caches into the lake.
2. **M1 — hockeycore foundation.** Scaffold (done 2026-07-24), pinned deps, common event schema; gap engine and pricing math written FRESH (v1 consulted only for API quirks); ground truth for the engine re-derived by hand-tracing raw pbp.
3. **M2 — MAPGOT/NHL.** Re-derived ground truth games hand-traced; NHL adapter + extraction over the full lake; exact-value gates vs new ground truth; shadow-diff vs v1 CSVs with every discrepancy attributed; fresh calculator; workbook + Sheets sync automated from day one.
4. **M3 — MAPGOT/AHL.** AHL fetcher → AHL lake → same protocol. (Baseline already proved the v1 AHL workbook is stale by up to 6.9 pts — do not bet it meanwhile.)
5. **M4 — EIHL + Liiga as adapters.** Unified engine over their existing raw caches; re-derived ground truth per league; shadow-diff vs their v1 workbooks (their first-ever real verification).
6. **M5 — OT4V3 + NEXTGOALPROP rebuilt** on hockeycore with the same protocol (their v1 suites passing makes this faster, but nothing is exempt from re-derivation).
7. **M6 — Live monitor + server ops** (git-based deploy; MAPGOT NHL first).
8. **M7 — Backtests re-run** on final v2 code + fresh data. Only then do numbers return to betting use.

## Working model

One Manager session drives everything; subagents used internally for builds and independent adversarial verification. This file + v2 CLAUDE.md's STATUS section are the single source of truth, updated in the same session as any change (the v1 registry went stale precisely because updates were a separate manual step).

## Immediate next steps

- [ ] Seb: run the freeze commands in a Windows terminal; confirm.
- [ ] Seb: confirm v2 location outside OneDrive (`C:\dev\HOCKEYPROJECTS_V2`) — or veto.
- [ ] Claude: M1 scaffold + port gap engine/math with tests.
- [ ] Claude: stage EIHL + Liiga raw data and run their first verification (M4 prep, can start alongside M1).
