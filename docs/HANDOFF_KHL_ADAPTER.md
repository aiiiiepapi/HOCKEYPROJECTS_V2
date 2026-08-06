# KHL adapter session — HANDOFF to Manager (2026-08-07)

Session branch: **claude/khl-adapter-setup-gd4nhx** (environment renamed the
kickoff's `khl-adapter`). Mission per docs/KICKOFF_KHL_ADAPTER.md: GT +
adapter + extraction + audit + gates — COMPLETE. NO ledger, NO pricing, NO
bet conclusions (Manager scope post-merge). Everything below is a claim
until the Manager re-derives (rule 0). Lake: branch `khl-data-lake` @
4ed99df, worktreed at /home/user/work/khl_lake (this environment's home is
/home/user, not the kickoff's /home/claude — runner/audit/gate take a
`KHL_LAKE` env override).

## Ground truth (rule 2 — traced BEFORE adapter code)

14 games / 16 instances, tests/ground_truth_khl.json, trace notes
docs/ground_truth_traces/khl_batch1_2026-08-07.md, raws in
tests/reference_raw/khl/ (~19 MB). First adapter run: 13/14 games exact;
the one miss was a HAND-TRACE error (898094's instance overlooked), caught
by the engine cross-check, re-verified by hand, recorded in the trace doc
(Magnus batch-0 precedent) — after the GT fix, 14/14.

Independent verification inside GT: every hand-derived empty-interval list
reconciles TO THE SECOND with the protocol team per-period ВППВ table
(officials' TOI accounting) — 14/14 games. The box-window model was pinned
the same way (ВПМ/ВПБ decompositions exact on 881261/881270/881725/898094).

Coverage: EV pull ×3 (incl. a real 3-second horn pull, 889859), pp_pull ×6
(6v3 pull-to-horn 881356; 6v4 re-pull after an ENG-created instance 886054;
penalty-on-trailer ender 889939), no-pull, carryover-at-open ×2, multi-pull
(3 windows, 881725), ruling-17 dp artifacts ×3 — **two bracketed by
EXPLICIT dp events (886161, 889859), the first direct confirmations of the
ruling-17 convention in any interval league**, one invisible (889995) —
OT game (881270), shootout game (889995), goalie substitutions incl.
period-boundary swaps, EN via text flag + protocol jersey-absence ×4
(incl. SH-ENG 886054), own-net-empty goals (en=False) ×3, the 898094
"duplicate" penalty (re-ruled: REAL 2+2 — below), PS awards, 5+20,
coincident cancellation, same-player stacking, wall-clock collision.

## Adapter (hockeycore/leagues/khl.py — emits segments.py dict, rule 15)

Dual-channel: TEXT (events: pulls/returns/subs/penalties/dp/coaches) +
PROTOCOL (goal authority: period/time/score/strength/on-ice lists; goalie
numbers; penalty multiset cross-check). Cross-checks that RAISE (rule 10):
goal count/time/side text-vs-protocol 1:1, running-score increments (both
channels), penalty (side,t,mins) multiset equality, protocol goal
period-vs-clock, starting-goalie numbers vs goalie tables, EN-vs-
extra-attacker contradiction, missing coach. Full conventions with named
games in the module docstring.

## Extraction (hockeycore/gap/run_khl_lake.py)

**3,060 games / 0 parse errors / 1,223 instances** (268 / 324 / 304 / 327
by season) / **136 pulled = 74 EV + 62 pp_pull** / 42 dp_only_empty /
**100.0% coach attribution both sides, no map** (an unattributed trailing
coach aborts the build). Output data/derived/khl_instances_gap3.json.
Density 0.40 inst/game vs Liiga 0.45 (kickoff band ~1,300-1,600 assumed
Liiga density; KHL is the lower-scoring league — 1,223 is consistent, and
the rough pre-adapter scout landed on the same per-season counts from the
text channel alone, i.e. both goal channels agree league-wide).
Raw observation, NOT composition-controlled (15b): pp_pull is 46% of
pulled instances — far above the other interval leagues' shares; KHL
down-3 pulls usually ride a power play. Clean-window comparability is
ledger work (Manager).

## Random audit (tools/audit_interval_random.py "khl")

Seed 20260808, 30 pulls + 30 no-pulls, **0 disagreements** (first run).
TWO independent checks per sampled instance: (a) family standard — net-empty
intervals re-derived from raw text phrases outside the adapter state
machine vs the derived row (with the dp/carryover excuses); (b) the
re-derived intervals must equal the protocol ВППВ column per period TO THE
SECOND (fully independent recorder). Gate: test_khl_random_audit.

## Gates

+3 (test_khl_ground_truth / test_khl_derived_instances rule-14 structural /
test_khl_random_audit). Full suite on this branch: **29 passed, 3 skipped**
(the skips are the other leagues' random audits — their lakes are not
mounted in this environment).

## dp census (data/derived/khl_dp_events.json — the portfolio first)

Explicit `Отложенный штраф у команды <Team>` events, verbatim raw text
kept per row. **The channel is PARTIAL** — structured dp items per season:
**0 / 193 / 647 / 731** (2023 has none; page-wide "mentions" in 2/748 2023
games are commentary, not structured items). Every event carries a
position bracket (last timed event before it) since dp lines have NO time.

Linkage (rule stated in the export): a net-empty window of the
NON-offending side beginning within [-2s, +90s] of the bracket:
- 438/1,571 events link to a pull window; median duration 13s.
- **409/438 (93.4%) end at an offender-penalty whistle** (the
  leader-whistle analogue): median 12s, **332 ≤25s, 77 (18.8%) >25s**,
  max 123s. The 29 non-whistle enders median 40s (dp resolved by goal /
  possession loss / etc.).
Calibration reading for the Manager (NOT a rulings change — kickoff order,
rulings 17/17b untouched): direct KHL dp truth shows ~19% of known-dp
extra-attacker windows exceed ruling 17's 25s bar, vs the NHL
possession-based 8.7%. Caveats: partial channel (selection unknown), the
bracket linkage is heuristic, and the 90s window can co-opt a genuine pull
adjacent to a dp announcement. GT's three in-window cases were all ruled
correctly by the existing clauses.

## Quirks (recorded, each on a named game)

1. **Mixed clocks collide**: play events cumulative, boundary lines wall
   clock — same displayed value can be either (881356: goal 19:58 P1 vs
   `Начало 2 периода` 19:58). Classification keys on text only.
2. **Misfiled period marker**: 886068 inserts `Начало 3 периода` mid-P2
   (P2 events continue to `Окончание 2 периода`). CLOCK WINS for consumed
   events (SHL 774455 precedent) — adjudication 3 below.
3. **Typo'd times on unconsumed rows**: 897556 `Игра 4 на 4` at 55:51-for-
   25:51; 898039 penend at 23:05-for-43:05. Unconsumed classes never gate
   the period check.
4. **Same-second duplicate penalty rows are REAL double minors** (898094
   Бреус, 881261 Минулин, 889859 Джозефс, 889939 Бокун, 897655 Томпсон) —
   adjudication 1 below.
5. **Penalty-end lines are corroboration only**: minute-only (2023/2024) or
   absent (881270) or reworded («Куньлунь Ред Стар» 889939; quoted
   `Команда "Нефтехимик" в полном составе.` 889995); ends are computed
   (cancellation + stacking + net-short single release), every exact-time
   2025/2026 end event in GT matched the computation to the second.
6. **PS awards** carry minutes 0 in the protocol table (881270, 886161) —
   no box row either side.
7. **РБ shootout row** increments the running score and must be skipped
   knowingly (889995); `Послематчевый буллит` attempt rows are timeless.
8. **Own-net-empty goals** `С экстра-полевым игроком` are NOT ENGs
   (881270/881827/886161) — en stays False; `В пустые ворота` + protocol
   jersey-absence are the EN evidence (both agreed on every GT case).
9. **Goalie-serving penalties** (889859 Исаев minor served by Радулов,
   886068 Серебряков served by Зыков) — ordinary rows, nothing special
   needed.
10. **KHL_SOURCE correction**: text goal lines DO carry time + running
    score + strength in every season of the lake — the discovery-round
    "goal lines carry NO time" claim is wrong as fetched (possibly a
    live-vs-archive difference; irrelevant for the lake).

## Open adjudications for the Manager

1. **Dedupe REFUTED** (contradicts the scrape handoff + kickoff line
   "duplicate penalty line 898094 51:57 — dedupe"): both channels carry
   the pair, and the protocol ВПМ table proves 4:00 was served (898094
   6:41 = 0:55+1:46+4:00 exact; independent 881261 confirmation 1:34/2:06
   exact). The adapter keeps both rows (stacked windows). Ratify.
2. **Coach identity across seasons**: 2025+ adds patronymics («Никитин
   Игорь» 2024 == «Никитин Игорь Валерьевич» 2025; «Кравец Михаил» ==
   «Кравец Михаил Григорьевич»). Adapter emits verbatim; the ledger keying
   (strip patronymic? canonical map?) is a post-merge call — affects
   cross-season coach records.
3. **Clock-wins rule** for consumed events when the running marker
   disagrees with the cumulative clock (886068; SHL precedent). Protocol
   goal periods stay strictly checked. Ratify.
4. **dp census reading** (above): whether/how to fold the KHL dp truth
   into rulings 17/17b calibration for AHL/Liiga/Mestis — Manager +
   ruling-42 discipline (the census ships numbers, not a story).
5. **Lake path convention**: runner/audit/gate default
   /home/user/work/khl_lake/khl with KHL_LAKE env override (kickoff
   assumed /home/claude/work — environment homes differ per session).

## What was NOT done (scope fence)

No ledger, no clean-window numbers, no morning sheet, no pricer, no lines,
no cross-league comparisons (the pp_pull share above is flagged raw). No
modification to segments.py or rulings 17/17b. Master untouched.
