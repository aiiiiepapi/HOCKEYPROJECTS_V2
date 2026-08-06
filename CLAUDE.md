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
| hockeycore.gap (AHL/Liiga) | FINALIZED 2026-08-02: shared interval engine (gap/segments.py, rule 15) backs liiga + ahl adapters. Trailing-team dp item CLOSED — ruling 17 (<=25s) + ruling 17b (early-window clauses, NHL-dp-truth-calibrated, every case hand-verified). Misconduct box-window bug + same-second swap bug fixed (9 classification flips, 2 phantom horn-length "pulls" removed). AHL: 2,313 instances / 395 EV pulls; Liiga: 837 / 97. Random audits vs raw feed: AHL 0/60, Liiga 0/60 (seeds 20260801/20260802), now a standing gate. Residual known limitation: middle-band [12:00-17:00] long leader-whistle enders keep ruling-17 convention (~2-4 possible dp residue, unresolvable without possession data). Full trace: docs/ground_truth_traces/interval_dp_audit_2026-08-02.md | 2026-08-02 |
| hockeycore.pricing | MODEL SPEC WRITTEN (docs/MODEL_SPEC.md): pull hazard × state-dependent goal intensities, exposure-based PK handling (replaces v1 hand weights), Gamma-Poisson coach shrinkage, forward-integration pricing, 10 direction tests D1-D10. Implementation not started. 4 open decisions for Seb in §8 | 2026-07-25 |
| Ground truth | NHL batch 1 DONE: 8 games / 13 instances hand-traced (tests/ground_truth_nhl.json). Confirmed v1 bugs: 1 boundary pull misattribution + 1 delayed-penalty artifact counted as a real pull (both fake "scored" successes, ~3% of that bucket) + 1 instance with missing pbp cache (violates v1 gate 7). The 7 dp candidates were adjudicated 2026-07-25 in shadow_diff_gap3.md (5 v1-wrong / 2 v1-correct) — status row was stale until 2026-08-02. NHL blip rule + same-second order-independence added 2026-08-02 (3 corrections, all 2022-23, training window untouched). Initial "12 phantom pulls / 19%" claim was checked and RETRACTED same day — see corrected batch1_findings.md | 2026-08-02 |
| AHL/Liiga ledgers & profiles | SHIPPED & GATED; REBUILT 2026-08-02 on the finalized extraction (rulings 17b + misconduct/swap fixes): clean_window_interval.py — per-league hazards, 18s dead time per league, pp pulls excluded from bettable number. Clear-chance take rates (composition-controlled): AHL 50.2% (542 clear chances, 66 coaches), Liiga 41.9% (172, 33). 24 AHL + 5 Liiga coach card records moved (largest: Morrison 25->13%, Petersen 68->86%, McIlvane 84->81%) — Seb RATIFIED 2026-08-02 (ruling 34, stays-in check). Blind re-run post-fix: Liiga PASS (+17.9/+12.4/+29.6), AHL FAIL per ruling 24 (no-go stands) | 2026-08-02 |
| Coach law (production) | DENSITY-PRESERVING ADOPTED (ruling 23, Seb ratified 2026-08-01): coach_hazard_array(P_c), timing preserved, raw-EB + 0.355 attenuation retired. Blind: all gates pass, lead1 bias +1.5pts, leaderTT ROI +21.3% (gate 0.95->0.94 ratified). Conversion-by-tier claim RETRACTED same day (training data flat; 15b violation). -3.5 stays CAUTION — remaining optimism is season-wobble-limited, not coach layer. Grids re-keyed to pull-% tiers; rebuild chain in RUNBOOK | 2026-08-01 |
| AHL/Liiga pricing | VALIDATED SPLIT (2026-08-01): ONE pricer + league fit dicts (fit_interval_league.py, rule 15). LIIGA blind PASS (ruling 25): conservative every market, 0/10 bad deciles, ROI@10%EV +19/+14/+30 (one season, wide CIs) -> paper-trade from Sept. AHL NO-GO (ruling 24): levels unstable at every timescale (4-season pool, rolling, season-local all fail blind; 90-H2 outcome collapse confirmed model-free) -> coach intel only, re-litigate with 26-27 data. Gates: liiga blind calibration + AHL no-bet pin | 2026-08-01 |
| AHL fix status | Round 3 (2026-08-02, ruling 39): data exonerated (audit 0/60, feed stable by month). "6v5-specific" attribution RETRACTED (15b, drawn pre-fix): corrected decomposition shows a BROAD H2 competitive shift inside gap-3 games (leader EV -33%, trailer EV +62% per instance after R600) with full-game totals normal — which is why the full-game anchor couldn't see it. Top mechanism candidate: playoff-race desperation (= queue-2 covariate), plus deadline churn / Feb Olympic window. Path unchanged: 26-27 re-litigation gate, paper harness vs real lines, coach-delta product (the route that matches how Seb actually bets AHL). Self-priced markets stay NO-GO (ruling 24) | 2026-08-02 |
| Paper-trade harness | v1 BUILT (2026-08-01): tools/paper_harness.py — live score watch (NHL score/now, AHL scorebar, Liiga api/v2), money-moment detection, threshold lookup from per-league lines CSVs, rule-28/hot-form flags, credit-capped raw odds snapshots. Odds catalog CONFIRMED: icehockey_nhl/ahl/liiga all exist (AHL+Liiga dormant until season). Liiga/AHL live-clock parsing = September shakedown items (raw payloads cached for offline fixes). Settlement = offline cheap-session join | 2026-08-01 |
| products/mapgot | not started (priority #1; EIHL + Liiga are league adapters of this product) | 2026-07-24 |
| Raw data lake — Mestis | COMPLETE & MANAGER-VERIFIED 2026-08-03: 1,166 games / 4 seasons (364/312/245/245), ICS-reconciled 0/0, all manifests re-hashed ok. Branch mestis-data-lake on the V2 REPO (v1 token 403 — convention question open with Seb). TICKER DISCOVERY: seuranta pages embed other games' events — page-wide counts were inflated; scoped goalie-out games = 226/186/155/179 == pois sets exactly (channels fully REDUNDANT; my "complementary" claim retracted same day, 15b). HC per game-side 2,313/2,332 — 19 blanks covered by data/coach_maps/mestis_coaches.csv (evidence-noted, Tuunanen-firing rows pinned by primary sources) | 2026-08-03 |
| hockeycore.leagues.mestis | SHIPPED & GATED 2026-08-03 (Manager): seuranta HTML scoped-row parser (ticker excluded), score-increment side cross-check (rule 10), vaihto=swap never empty, AHL interval conventions + EN repair rules inherited, penalties AHL-style (PS fouls without minutes = no box, real double minors kept, >=10min misconduct class), coaches from game rosters.json + map fallback. GT batch 1: 13 games / 13 instances hand-traced pre-adapter, 13/13 first run (incl. pp_pull 7441, first-evidence classification 7327). Extraction: 617 instances (197/165/127/128), 114 pulled (82 EV + 32 pp), 0 parse errors, 100% coach attribution. Random audit vs independent pois channel 0/60 (seed 20260803). Gates 22 -> 25. LEDGER & SHEET SHIPPED same day: clean_window_interval mestis — 180 clear chances, clear-chance take rate 45.6% (between Liiga 41.9/AHL 50.2, composition-controlled), prior mu 0.46 / S 4.0 predictive, 39 coaches; morning sheet delivered (COACH-INTEL-ONLY banner, rule-28 tags; top: Karjalainen 80% 7/8 PPP, Rautakorpi 73%). Clean-window gate now covers mestis. PRICER TESTED same day (Seb asked): blind walk-forward (fit 2023-25, price 2026, 292 checkpoints/74 inst) FAILS ruling-25 bar — lead1/total1 +11.5/+11.6pts conservative, 2-3/10 bad deciles; marg4 dead-on; ROIs at model lines (+40/+33%) are the bias, not skill. Attribution nailed: NOT hazard bins, NOT estimator recency, NOT data, NOT model defect (in-sample calibrated) — REAL 25-26 late-window drift (lead1@R300 0.607 vs 0.377 train; pulls 46% vs 36%, EN rates up, spells longer). Differs from AHL: EV levels stable, marg4 calibrated, one-sided conservative. NO-GO pinned (gate 26). METHOD UPGRADED same day on Seb's order (tools/backtest_folds.py, docs/BACKTEST_FOLDS_2026-08-03.md): forward folds EVERY season + LOSO flat-coach level check. Mestis attribution CORRECTED (15b): symmetric season wobble +/-7-12pts BOTH directions (2025 fold loses money at model lines), not a 25-26 regime change; conservative-safe framing retracted. Liiga re-checked under same method: ruling-25 pass survives a 2nd forward fold (+4.8/+6.9 biases, ROI +19.8/+23.0), LOSO 2024 quantifies its wobble at ~8pts optimistic-capable. Single-fold blind retired as deciding evidence for interval leagues. THEN Seb's variance hypothesis CONFIRMED (fold_variance_test.py): all folds |z|<2, joint p 0.13-0.95, tau~0 — NO true season wobble either; POOLED forward (968cp/225g): leaderTT +4.5pts bias, ROI +22.3% [+4.7,+38.8] P=0.996; total +0.7pts +11.3%; -3.5 +0.8pts +14.9%. SEB RATIFIED (rulings 42+43): ruling 42 = ATTRIBUTION GATE (null test + competing hypothesis + design-limit statement mandatory on every causal claim; multi-fold replaces single-fold as deciding evidence); ruling 43 = Mestis UPGRADED to Liiga-class PROVISIONAL — lines_10ev_mestis.csv SHIPPED (full 4-season fit, all 3 markets, rule-28 floor, direction checks pass), icehockey_mestis CONFIRMED in odds catalog, paper harness wired (live_mestis stub, Sept shakedown), morning sheet banner updated, gate swapped to test_mestis_provisional_status. Paper-trade Sept alongside NHL+Liiga; 26-27 re-blind standing | 2026-08-03 |
| Raw data lake — Magnus | SWEEP RUNNING on Seb's PC (4 season bands mapped from coarse scan: 22-23 ~15900-32600, 23-24 ~32600-42400, 24-25 ~42400-55400, 25-26 ~68550-69900; ~41k ids, all-division PDFs kept verbatim). ADAPTER ALREADY SHIPPED & GATED (2026-08-02, gate 22): hockeycore/leagues/magnus.py — coordinate-based sheet parser (format stable 2021-2025), coaches ON sheet (v1 docs wrong), semantic J+/J- split, EN authority = Joueurs lists, strength = penalty Debut/Fin + misconduct flag, TOI-fit net-empty inference with EN anchors as HARD constraints, sheet_empty/OT/swap classes. GT batch 0: 9 sheets hand-traced, 2 hand-trace errors caught by engine cross-check (recorded). NEXT when lake lands: classify headers (PS inflate block), stage Magnus games, push magnus-data-lake, GT batch 1 (pull-positive), league-wide extraction, audit, ledger, morning sheet. Precision doctrine: docs/MAGNUS_DATA_GAPS.md | 2026-08-02 |
| products/ot4v3, nextgoalprop | not started (rebuilt after mapgot) | 2026-07-24 |
| Raw data lake — SHL | KICKOFF WRITTEN (docs/KICKOFF_SHL_SCRAPE.md, 2026-08-03, Seb ordered Sweden next): scrape session on branch shl-scrape, lake to V2 branch shl-data-lake (Mestis convention), 4 seasons runkosarja-equivalent, capability bar + ticker lesson baked in. BOTH Swedish markets confirmed in odds catalog (icehockey_sweden_hockey_league + icehockey_sweden_allsvenskan — Allsvenskan is the natural follow-up). COMPLETE & MANAGER-VERIFIED 2026-08-06: 4 seasons x 364 games (schedule ids independently re-extracted, 0/0 both directions), 5,104/5,104 hashes bit-exact (CRLF repair confirmed genuine), 0 foreign links in events pages (no Mestis-style ticker on this source), coach census reproduces handoff exactly (2,891/2,912 = 99.3%, 21 blank sides listed, HV71=8). Branch shl-data-lake tip 6b77add (NEVER read root 03d8547 — pre-CRLF-repair). GK-channel 'disagreements' adjudicated: revision duplicates + optional end-of-game rows, channels agree on every pull-relevant second — adapter rules recorded in docs/SHL_LAKE_VERIFICATION.md. Capability class Liiga-plus (explicit penalty begin-end, dual GK channels, on-ice lists). Reports-PDF skip ratified. STANDING RULE from CRLF incident: every lake branch starts .gitattributes * -text + re-hash after transfer. ADAPTER KICKOFF WRITTEN 2026-08-07 (docs/KICKOFF_SHL_ADAPTER.md, Seb ordered): delegated build session, GT-first per rule 2, three binding adapter rules from the verification adjudication baked in, audit vs pbp channel 2024+, coach map for the 21 blanks in scope; ledger/pricing stay Manager post-merge | 2026-08-06 |
| hockeycore.leagues.shl | BUILT ON SESSION BRANCH claude/shl-adapter-hockeyprojects-lbeked, AWAITING MANAGER VERIFY+MERGE (2026-08-06): GT batch 1 = 12 games / 12 instances hand-traced pre-adapter (rule 2), 12/12 first run. Adapter: explicit penalty begin-end used directly; offsetting (00:00 - ) placeholder windows = no box (1,214/1,218 census); GWS excluded; clock-priority on the one misfiled game (774455); AHL/Mestis EN repair + OUT-first inherited. Extraction: 1,456 games / 0 errors / 681 instances (170/171/174/166) / 40 pulled (28 EV + 12 pp) / 100% coach attribution (shl_coaches.csv covers all 21 blanks; all 8 HV71 = Lindbom, primary-sourced). Carryover signature 29.8% (gap-2 pulls eat ENGs); dp channel ~absent (1 ruling-17 keep 774501, 1 17b-ii artifact 774720). Audit 0/60 (ALL 27 pulls 2024+ + 33 no-pulls, seed 20260807, 2023 has no 2nd channel) after 2 tool fixes: pbp dedupe key needs playerId (882274 period-break swap — adjudication rule ii amendment for Manager), carryover excuse (774518). Manager baselines all reproduce (59.3-63.7% real-P3-interval games, median out 57:58, census exact). Gates +3, suite 28 pass / 1 skip (unmounted ahl+liiga lakes). Open adjudications in docs/HANDOFF_SHL_ADAPTER.md: dedupe amendment, Lindholm/Lindbom + Burström name variants, HV71 Oct-2023 listing-vs-press (3 games) | 2026-08-06 |
| Raw data lake — KHL | KICKOFF WRITTEN (docs/KICKOFF_KHL_SCRAPE.md, 2026-08-03, Seb ordered): branch khl-scrape, lake to V2 branch khl-data-lake, 4 seasons, ~650-750 games/season (biggest lake yet — repo-size check mandated before fetch). MARKET NOTE on record: odds provider has NO icehockey_khl — lake serves coach intel + model-side lines (ruling 5); Seb ordered with this heard. COMPLETE & MANAGER-VERIFIED 2026-08-07: 3,060 RS games / 4 seasons (748/782/782/748), text+protocol per game, 4.14 GB — biggest lake in the portfolio. Calendar reconciliation re-derived tid-scoped 0/0 both directions; 6,124/6,124 hashes bit-exact; id ranges exact. COACH CENSUS 3,060/3,060 = 100.0% (full census, best in portfolio — no coach map needed). Branch khl-data-lake tip 4ed99df. STANDOUT CAPABILITY: explicit delayed-penalty events in the text channel — no other interval league has dp visibility; potential calibration source for rulings 17/17b at adapter time. Quirks recorded (mixed clock semantics, dup lines, substitution class, textBroadcast-item scoping). No odds market (ruling-5 model-side doctrine). Adapter not started (Russian event vocabulary = main build cost) | 2026-08-07 |

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
