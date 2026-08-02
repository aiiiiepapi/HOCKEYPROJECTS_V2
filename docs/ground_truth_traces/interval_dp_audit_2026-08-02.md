# Interval-league finalization audit — 2026-08-02 (Manager session)

Trigger: Seb directive "finalize what we need so that these 3 leagues are
perfect." Scope: close every open adjudication in the extraction layer for
NHL / AHL / Liiga. Every case below was hand-verified against the raw lake
feed in-session (rule 0: nothing assumed, including our own prior audits).

## 1. The ruled >25s convention was WRONG for early segments (ruling 17b)

Ruling 17 excluded leader-whistle-ended segments <=25s as delayed-penalty
artifacts and declared longer ones "real pulls that drew a call." NHL lake
ground truth (6,594 dp possessions, 2024-26, explicit dp events):

    P(dur > 25s | dp) = 8.7%   P(>40s) = 2.6%   P(>60s) = 0.5%

So duration alone CANNOT separate dp from pulls. The working discriminator is
pull-time plausibility: among 285 verified AHL EV pulls, everything before
P3 12:00 is either a long continuous segment (120s+) or corroborated by a
later real segment. All six early-short leader-whistle enders were dp
(same goalie returns at the whistle TO THE SECOND):

| game | trail | seg (P3) | dur | verdict |
|---|---|---|---|---|
| 77/1024680 | BEL | 0:54-1:20 | 26s | dp artifact (pull at 0:54 down 3 does not exist) |
| 86/1026980 | IA | 0:33-1:07 | 34s | dp artifact |
| 86/1027518 | SD | 1:16-1:51 | 35s | dp artifact |
| 86/1027594 | SD | 1:13-1:46 | 33s | dp artifact |
| 90/1027844 | HFD | 5:49-6:40 | 51s | dp artifact |
| 90/1028774 | SD | 11:03-11:46 | 43s | dp artifact; instance keeps REAL pull at 945 (ev 663->945) |

Late-game long enders confirmed REAL (kept): 90/1028817 (995-1189),
90/1028895 (966-1184), 90/1028548 (1101, P3 18:21), liiga 2026/247 (1046).
Ambiguous middle band [12:00-17:00] left on ruling-17 convention; estimated
residual dp contamination ~2-4 instances league-wide (documented limitation —
not resolvable without possession data).

## 2. dp GOALS wipe the minor -> no penalty event exists (ruling 17b-ii)

81/1025867 (MB, P3 3:07): goalie off 19s, MB scores "6v5", goalie back, NO
penalty assessed — the non-offending team scoring during a delayed MINOR
wipes it. Was counted as a pull WITH a success. Removed (both the pull and
the fake "scored" outcome). Liiga twin: 2025/246 (pp_pull, seg 600-604).

## 3. Whistle-lag: leader penalty assessed INSIDE the segment (17b-iii)

90/1028800 (BAK, P3 6:39): goalie off 399, leader penalty row at 403, BAK
concedes SH-ENG at 409 during the dp, then real 6v4 pp_pull at 420 (outside
the gap-3 window: the ENG widened the gap at 409). The 399 "pull" that "ate
an ENG" was a dp artifact; both the phantom pull and the phantom eaten-ENG
removed from the coach.

## 4. Misconduct box windows (adapter bug, both interval leagues)

10-minute misconducts created phantom box windows although a misconduct
never makes a team shorthanded. 8 AHL + 1 Liiga pull classifications
flipped — BOTH directions:
- EV->pp_pull (was hiding a real PP): 81/1026058 (trailing misconduct masked
  the leader's simultaneous minor — 6v4 pull counted as EV), 77/1024340,
  81/1025506, 81/1025878, 86/1027415, 86/1027426
- pp_pull->EV (leader misconduct faked a PP; these are BETTABLE EV pulls
  that were wrongly excluded): 77/1024678, 90/1028615, liiga 2026/466
Fix: adapters flag misconduct rows (kept as whistle markers for end-context);
segments.py excludes them from strength classification.

## 5. Same-second goalie swaps logged IN-then-OUT (adapter bug)

A substitution can be fed as IN-row-then-OUT-row at one second; the state
machine opened a phantom empty-net interval to the period horn. 534
same-second in+out pairs across 4 AHL seasons — ALL with the net full
(plain substitutions); zero occur mid-pull, so OUT-first normalization is
loss-free. Three gap-3 records were wrong:
- 90/1028763 (Milic->DiVincentiis at P3 8:00): 720s phantom "pull to the
  horn" -> not pulled. (Previously survived the 60-audit because the naive
  audit reader had the same bug — fixed in tools/audit_interval_random.py.)
- 90/1027839 (Tolopilo->Patera at 459): phantom 459-854 "pull + scored_6v5";
  ABB's REAL pull (Patera out at 1000) falls outside the window (closed at
  854) -> instance not pulled.
- 77/1024882 (Källgren->Petruzzelli at 520): phantom; real pull evidence
  957 (ate ENG 968 stands, timing 520->957).

## 6. NHL: blip rule made explicit + order-independence (closes logged edge)

Two engine changes, ZERO effect on the 2024-26 training window:
- Same-second normalization: faceoff situation codes are authoritative
  within a second (clock stopped between whistle and faceoff), so sit_at()
  no longer depends on feed array order. Perturbation test added to gates.
- blip_artifact: <=2s net-empty runs at a penalty event with no dp window =
  situation-code noise. Catches 3 pre-training-window (2022-23) phantoms,
  each hand-verified: 2022020406 (ev 987->1048, pull->pp_pull; D.J. Smith
  7/12 -> 6/11), 2022020791 (739->890), 2022020433 (207->882!).

## 7. Liiga random audit (parity with AHL)

tools/audit_interval_random.py, seed 20260802: 30 pulls + 30 no-pulls
re-verified directly against raw goalKeeperEvents, bypassing the adapter:
0/60 disagreements. AHL re-run on the corrected extraction (seed 20260801):
0/60. Both now run as a permanent gate when the lakes are mounted.

## Net effect

- AHL: 404 -> 395 EV-pull instances (7 dp phantoms + 2 swap phantoms
  removed); 8 classification flips; 2 phantom successes removed; 2 evidence
  times corrected (663->945, 520->957).
- Liiga: 98 -> 97 pulls (dp goal removed); 1 pp_pull->EV (2026/466).
- NHL: 3 instances corrected, all 2022-23 (outside training window);
  production pricing numbers UNCHANGED.
- Gates: 17 -> 21 (17b pins, misconduct pins, blip + order-perturbation,
  random audits).
- Blind backtests after rebuild: Liiga PASS (ROI@10%EV +17.9/+12.4/+29.6),
  AHL FAIL exactly as ruling 24 pins (no-go stands).
- Coach cards: 24 AHL + 5 Liiga records moved. Largest: Mark Morrison
  25%->13% (2 phantoms), Toby Petersen 68%->86%, Trent Cull 73%->68%,
  Groulx 72%->66%, McIlvane 84%->81% (3 of Seb's challenged reference
  points moved slightly — see profiles).
