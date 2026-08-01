# HOCKEYPROJECTS V2 — Constitution & Status

Every session working in this repo reads this file first. It replaces the v1
registry: the STATUS section below is updated in the SAME session as any change.

## STATUS (update in-session, never later)

| Area | State | Last touched |
|---|---|---|
| Raw data lake — NHL | COMPLETE & VERIFIED: 2,624 games × (pbp + boxscore + rightrail), both seasons, 0 missing, coaches on all games (45 distinct HCs). On GitHub branch nhl-data-lake; audited 2026-07-25 (BOM in rightrail handled with utf-8-sig at read). Lake pbp identical to v1 cache for all 8 ground-truth games | 2026-07-25 |
| Raw data lake — AHL | COMPLETE & VERIFIED: 4 seasons (77/81/86/90) x 1152 games x (pxp+summary), 0 missing, 0 parse fails, goalie_change in every game (explicit pulls — no phantom-inference risk). Branch ahl-data-lake. Coach listings 96%: 8 trailing blank blocks hand-curated+verified in data/coach_maps/ahl_coaches.csv (join rule: listing wins, map fills blanks) | 2026-08-01 |
| Raw data lake — Liiga | COMPLETE & VERIFIED: 450/450/480/480 games (2023-2026), reconciled 1:1 against the official games-list endpoint incl. 2 rescheduled games at odd ids (2023/39699 Tappara-Lukko, 2026/53489 Lukko-Pelicans; both parse through the adapter, one thin gap-3 instance in 39699). Branch liiga-data-lake. api/v2 penaltyEvents swap handled + gated (gate 12) | 2026-08-01 |
| Raw data lake — EIHL | v1 cache only (port when EIHL expansion is greenlit) | 2026-07-24 |
| hockeycore.gap (AHL/Liiga) | ADAPTERS SHIPPED & GATED: shared interval engine (gap/segments.py, rule 15) now backs liiga + new ahl adapter. AHL: 2,313 instances / 461 pulls (114 PP) from 4 seasons, GT batch1 (3 games/5 instances hand-traced first), EN cross-checks both directions adjudicated (4 feed-defect classes, see docs/ground_truth_traces/ahl_batch1.md), 60-instance random audit = 0 disagreements, coach join 100%. Liiga: 837 instances / 98 pulls (27 PP), coach map joined 100% (K-Espoo name fix); 2022-23 has NO goalie channel in the API -> pulled=None + no_goalie_channel flag (rates still usable). Derived files tracked; 14 gates green. OPEN: trailing-team delayed-penalty pulls inside windows (ledger block must rule) | 2026-08-01 |
| hockeycore.pricing | MODEL SPEC WRITTEN (docs/MODEL_SPEC.md): pull hazard × state-dependent goal intensities, exposure-based PK handling (replaces v1 hand weights), Gamma-Poisson coach shrinkage, forward-integration pricing, 10 direction tests D1-D10. Implementation not started. 4 open decisions for Seb in §8 | 2026-07-25 |
| Ground truth | NHL batch 1 DONE: 8 games / 13 instances hand-traced (tests/ground_truth_nhl.json). Confirmed v1 bugs: 1 boundary pull misattribution + 1 delayed-penalty artifact counted as a real pull (both fake "scored" successes, ~3% of that bucket) + 1 instance with missing pbp cache (violates v1 gate 7) + 7 delayed-penalty candidates pending adjudication. Initial "12 phantom pulls / 19%" claim was checked and RETRACTED same day — see corrected batch1_findings.md | 2026-07-24 |
| AHL/Liiga ledgers & profiles | SHIPPED & GATED (2026-08-01): clean_window_interval.py — per-league hazards (AHL 4 seasons pooled, no drift; Liiga 24-26), 18s dead time re-measured per league, dp-artifact rule (ruling 17), pp pulls excluded from bettable number. Clear-chance take rates (composition-controlled): AHL 50.9% (560 clear chances, 66 coaches), Liiga 41.5% (171, 33). Beta priors fitted per league (mu~0.51/0.50, strength ~7). Posterior bug (failures=nw-kw) caught by eyeball + now gated. NEXT: per-league rate fits -> pricer -> blind calibration + ROI before anything is bettable | 2026-08-01 |
| -3.5 root cause | NAILED (2026-08-01, docs/marg4_root_cause.md): EN-against conversion is coach-tier dependent; pooled conversion breaks tier tails. Survival coach law validated as estimator (beta=1.13) but pricing adoption deferred until conversion channel ships. backtest_survival.py = harness. Production unchanged (0.355 law, -3.5 CAUTION) | 2026-08-01 |
| products/mapgot | not started (priority #1; EIHL + Liiga are league adapters of this product) | 2026-07-24 |
| products/ot4v3, nextgoalprop | not started (rebuilt after mapgot) | 2026-07-24 |

## Scope decision (Seb, 2026-07-24)

Everything is re-done and re-verified. NOTHING from v1 is assumed correct —
not pipelines, not calculators, not intermediate CSVs, not even ground truth
files. The ONLY v1 artifacts that carry over are:
1. Raw scraped API/HTML responses (the data lake) — kept verbatim, never edited.
2. League research docs (API endpoints, data-access notes) — as reference.
v1 outputs are used strictly as shadow-comparison references: where v2 disagrees
with v1, the discrepancy is investigated and attributed (v1 bug / v2 bug /
intentional change) in docs/discrepancy_log.md. Agreement with v1 is NEVER
by itself evidence of correctness.

## Standing rules (carried from v1 — these were good)

0. **NEVER assume previous work or data is correct — including your own from
   earlier sessions, including v2's. Think for yourself, from the raw data up.**
   Any number, mapping, or claim you rely on either gets re-derived or gets an
   explicit verification check in the same session. "A previous session
   verified it" is not verification. (Seb, 2026-07-24)
0b. **Do not reflexively agree with Seb.** When analysis, data, or engineering
   judgment points the other way, say so plainly, with evidence, BEFORE doing
   what he asked. He rules after hearing the disagreement — but he must hear
   it. Flattery and deference are defects in this project. (Seb, 2026-07-25)
1. Hit real data in the first 10 minutes. No planning without data contact.
2. Ground truth before logic: hand-trace real cases before writing code.
3. Instance-level always; never aggregate prematurely.
4. Never use mock or fabricated data at any stage.
5. If real data contradicts an assumption, update the assumption.
6. Verification is code, not conversation. Exact-value tests vs ground truth.
7. Test suites are cumulative; later phases include earlier tests.
8. Zero results from a non-empty dataset = automatic failure.
9. Every betting-relevant formula gets a direction sanity test (economic sense,
   not just math sense).
10. Treat suspicious results as failures. If it seems off, it IS off.
11. Never assume continuous state — track from source at every event.
12. Seb bets real money on these numbers. Act accordingly.
13. Every manual step that runs twice gets automated; outputs get their
    downstream delivery (Sheets sync etc.) wired up in the same session.
14. Sanity bounds in tests must be structural (per-season, per-game), never
    absolute totals — absolute bounds silently go stale as data grows
    (v1 lesson: the 802-instances false alarm).
15b. **No uncontrolled interpretation.** Any comparative or behavioral
    claim reported to Seb (league vs league, coach vs coach, era vs era) must
    be composition-controlled (like-for-like windows / clean-window
    conditioning) or explicitly labeled raw-and-not-comparable. Verbal
    conclusions get the same gate discipline as model outputs — the recorded
    failures were all prose attached to correct data (lead1 story, Bednar
    mechanism, dead-time story, Liiga 11.7% dilution artifact, 2026-08-01).
15. One implementation per concept. Gap detection, odds math, Poisson pricing
    exist ONCE in hockeycore. A league is an adapter, not a reimplementation
    (v1 lesson: EIHL/Liiga rewrote gap logic; the EV+10% sign bug came from a
    local reimplementation).

## Architecture

hockeycore/ (installed package: `pip install -e .`)
- gap/      — league-agnostic 3-goal-gap engine over the common event schema
- pricing/  — Poisson, American-odds conversion, shrinkage, EV
- leagues/  — adapters: nhl, ahl, eihl, liiga. Each maps raw source files from
              the data lake into the common event schema. Adapters contain NO
              betting logic.
- io/       — data-lake access, workbook builders, Sheets sync

products/   — thin config + glue per bet product (mapgot, ot4v3, nextgoalprop)
tests/      — ground truth (re-derived) + exact-value gates + direction tests
data/raw/   — the immutable data lake (gitignored; backed up separately)
tools/      — fetchers (fetch-only, stdlib-only, run on Seb's PC or server)

## Environment facts

- The cloud workspace cannot reach league APIs from Python (proxy 403);
  fetchers therefore run on Seb's Windows PC (double-click .bat) or the Ubuntu
  server. All processing/verification runs anywhere, offline, from the lake.
- v1 lives in OneDrive and stays frozen (branch pre-v2-snapshot). v2 lives
  outside OneDrive (default C:\dev\HOCKEYPROJECTS_V2) with GitHub as backup —
  OneDrive placeholder hydration breaks git and bulk reads.

## Verification protocol (every component, no exceptions)

1. Re-derive ground truth by hand-tracing raw pbp for selected games; record in
   tests/ground_truth*.json with the trace notes in docs/ground_truth_traces/.
   Cross-check against v1's ground truth; investigate any disagreement.
2. Build the component fresh. v1 source may be consulted as a reference for
   API quirks, but logic is written and reasoned from raw data, not copied.
3. Exact-value tests vs the new ground truth must pass.
4. Shadow-compare v2 output vs v1 output on identical raw data; attribute every
   discrepancy in docs/discrepancy_log.md.
5. Direction sanity tests for every priced number.
6. Only after 1–5: the component's numbers may be used for betting.
