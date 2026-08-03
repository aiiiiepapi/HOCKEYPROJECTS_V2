# Mestis GT batch 1 — hand-traces (Manager session, 2026-08-03)

13 games / 13 instances, traced from raw seuranta HTML (dumb text dump,
no adapter logic) BEFORE hockeycore/leagues/mestis.py existed (rule 2).
Adapter passed 13/13 on first run; exact values pinned by
tests/ground_truth_mestis.json (gate test_mestis_ground_truth).

## The ticker discovery (made during tracing prep — changed everything)

Every seuranta page embeds a league-wide ticker of OTHER games' events
(`div.latest-event`, td classes time-team/text) alongside the main event
table (td classes home/time/away). Consequences, all verified:

- Scrape session's "goalie-out ev." counts (303/242/185/205) were
  page-wide greps = ticker-inflated. TRUE scoped counts: 226/186/155/179
  — exactly equal to the pois-interval game counts, per season, as SETS.
- The two goalie channels are 100% REDUNDANT at game level, not
  complementary. My own verification doc's "complementary" finding
  (2025/2986, 2025/3175, 2026/3142) was the same ticker artifact —
  corrected in docs/MESTIS_LAKE_VERIFICATION.md same day.
- "Sisään-without-ulos" games (29/26/21/16): ALL ticker artifacts;
  scoped count is 0 in every season.
- "Duplicate event rows" (7425): the same-second penalty pairs are REAL
  double minors (the per-team penalty-minute summaries count them
  separately, e.g. 2026/3142 away 4x2=8 with two 58:46 pairs).

## Per-game traces (cumulative secs; P3 secs = t-2400)

### 2025/3000 Hokki - Hermes 2024-09-13 (7-3)
Goals h: 388(1-0), 852 YV(2-1), 1131(3-1), 1331 YV(4-1), 1473(5-1),
2049(6-1), 3573 TM(7-3); a: 728(1-1), 2955(6-2), 3155(6-3).
24:33 "Maalivahdin vaihto" Vedenpää->Haukka = SWAP, net never empty.
P3 entry 6-1 (gap 5, no instance). Gap 3 at 3155 -> inst opens 755;
7-3 at 3573 widens -> closes 1173. Away pull 3438 (ulos) -> 3573
(sisään at the ENG second); pois 57:18-59:33 agrees. No boxes at 3438
(home 46:53 minor ended 48:53) -> EV "pull", evidence 1038, ate_ENG.

### 2023/7458 Ketterä - K-Espoo 2022-09-22 (2-3)
Goals a: 378 SR(0-1), 1172(0-2), 1814 VM(0-3); h: 2625(1-3), 3484 IM(2-3).
IM = scorer's OWN net empty (home had pulled 57:59) — NOT an ENG; en=False.
P3 entry 0-3 -> inst opens 0; 1-3 at 2625 narrows -> closes 225. pulled
False (pulls at 57:59+ are post-close, gap 2). Adapter-level: home empty
(3479,3484) ended by own 6v5 goal, (3512,3596) ended by sisään at the
same second as home's own 59:56 minor (penalty_on_trailer context).
5+20 pair 34:10 (major + pelirangaistus) and 2+10 pair 51:30 (minor +
käytösrangaistus): only the 5/2 affect strength; 10/20 = misconduct class.

### 2024/4009 K-Espoo - TUTO 2023-09-23 (4-2)
Never gap 3 (2-1 entering P3; 3-1/3-2/4-2 inside). NO instances.
Away pull 3447 -> horn: empty (3447,3600); pois 57:27-60:00 agrees.

### 2026/2965 Jokerit - IPK 2025-09-11 (4-1)
P3 entry 3-1. Gap 3 only at 3595 (4-1 TM) -> inst opens 1195,
end_of_game 1200. Away empty (3411,3595) ends AT the open second ->
carryover_empty_at_open, pulled False. Matching 59:15 minors cancel.

### 2023/7297 KeuPa HT - RoKi 2023-03-07 (7-4)
Wild finish: 4-4 at 3320, then 5-4 YV(3477), 6-4 YV,TM(3545),
7-4 YV,TM(3560). Gap 3 only at 3560 -> inst opens 1160, eog. Away
pulled twice DOWN 1-2 while SHORTHANDED (Holopainen 5min major 3413,
+20 misconduct excluded): (3499,3545) ate TM, (3553,3560) ate TM at the
open second -> carryover, pulled False. Both YV+TM goals = 6v4-against-
5-into-empty-net; en=True via TM.

### 2023/7288 TUTO - Ketterä 2023-02-02 (4-1)
Gap 3 only at 3597 (4-1 TM) -> inst opens 1197, eog, carryover via
(3545,3597). Earlier (3512,3517) ended by TM,SR goal at 3517 — SR =
delayed-penalty goal WITH empty net; flags carried verbatim; no penalty
row at 3517 (minor wiped by the goal).

### 2023/7452 JoKP - IPK 2023-02-18 (5-2)
P3 entry 4-1 -> inst 1 opens 0; 5-1 at 2468 widens -> closes 68, pulled
False. Gap 4 until 5-2 YV (3098) -> inst 2 opens 698, eog. TWO vaihto
rows (51:23 Randelin->Jukkola, 51:38 back) = swaps, ignored; real pulls
(3357,3388) returned_no_event + (3415,3600) horn. Evidence 957, no
boxes at 3357 (home 50:37 minor terminated early by the 3098 YV goal)
-> EV "pull". IPK side blank in rosters -> map row (Härkönen, bracketed
by 7347 02-17 / 7571 02-23).

### 2023/7276 KOOVEE - IPK 2023-03-15 (1-5)
P3 entry 1-4 -> inst opens 0 (trailing HOME); 1-5 at 3279 widens ->
closes 879. Home never pulled -> pulled False.

### 2025/3161 IPK - Ketterä 2024-09-12 (2-3 VL)
OT + shootout robustness: Jatkoaika penalties (3716, 3783) skipped
(period 4); Voittomaalikilpailu rows at 65:00 incl. the "2-3 VL"
decision row EXCLUDED from goals (period 5). 4 regulation goals, never
gap 3, no goalie events -> 0 instances, no empty intervals.

### 2025/2999 Hermes - RoKi 2024-09-14 (5-2)
P3 entry 4-1 -> inst 1 opens 0; 4-2 at 2989 narrows -> closes 589,
pulled False. 5-2 TM at 3529 -> inst 2 opens 1129, eog; away empty
(3408,3529) ends at the open second -> carryover, pulled False. The ENG
that CREATES the instance is the classic carryover shape.

### 2023/7327 KOOVEE - RoKi 2022-11-19 (0-4)
Gap 3 at 2452 (0-3 YV) -> inst opens 52; 0-4 AV,TM at 3468 widens ->
closes 1068. Trailing HOME pulled twice: (3316,3350) ends at the 55:50
LEADER minor whistle — 34s > 25s and empty_from 916 >= 720 -> ruling
17/17b clauses do NOT fire, kept as evidence (real pull that drew a
call); (3376,3468) ate the SH-ENG. Evidence 916; NO boxes at 3316 ->
"pull" (the leader minor at 3350 covers only the SECOND segment —
classification is at FIRST evidence). The away 0-4 goal is AV+TM:
shorthanded into the empty net.

### 2023/7441 Peliitat - K-Vantaa 2022-10-14 (4-2)
Penalty-shot quirks: 26:55 foul row WITHOUT minutes (no box) + RL goal
3-0; 36:38 failed PS ("ei maalia", no score row). P3 entry 3-0 ->
inst 1 opens 0; 3-1 at 3098 narrows -> closes 698, pulled False.
4-1 at 3221 -> inst 2 opens 821; 4-2 IM at 3486 narrows -> closes 1086.
Away pull (3432,3486) scored_6v5; home Tuomaala minor 3359-3479 active
at evidence 3432 -> lead_box 1 > trail_box 0 -> **pp_pull** (the one
true pp_pull in the batch). Second pull (3507,3600) is post-close.

### 2026/3142 RoKi - KeuPa HT 2026-01-02 (3-4)
No gap 3 (3-4 from 2376 on) -> 0 instances. Home pull (3388,3600) to
horn; pois 56:28-60:00 agrees. REAL double minors: two 2-min rows each
side at 58:46, counted separately in the team penalty summaries. YV2
flag (5-on-3 goal) at 2376 carried verbatim.

## League-wide extraction (post-GT, gates green)

1,166 games, 0 parse errors, 617 instances (197/165/127/128), 114
pulled = 82 EV + 32 pp_pull. Coach attribution 100% after
data/coach_maps/mestis_coaches.csv (7 rows, every row evidence-noted;
the Ketterä Feb-2026 rows pinned by the Tuunanen firing on 2026-02-09 —
jatkoaika.com/268014, yle.fi/a/74-20209136). Random audit vs the
independent pois channel: 0/60 (seed 20260803), standing gate.
