# Ligue Magnus — data gaps vs mainstream leagues & precision doctrine

Written 2026-08-02 (Manager session), from the v1 April-2026 research docs
(read in full) + the four mainstream feeds we operate. Seb directive: "figure
out what we will be lacking... work with what we got and stay as precise as
possible." This doc is the contract for how the Magnus adapter stays honest.

## What each league's feed gives us

| Capability | NHL (pbp+shifts) | AHL (pxpverbose) | Liiga (api/v2) | **Magnus (PDF sheets)** |
|---|---|---|---|---|
| Event timeline (shots/stoppages/faceoffs) | YES | partial (4 event types) | partial | **NO — box-score tables only** |
| Explicit goalie in/out with times | situation codes | explicit rows | explicit intervals | **NO — per-goalie TOI totals + Joueurs lists on goals** |
| Delayed-penalty visibility | explicit dp events | whistle-coincidence (17/17b) | thin channel | **NONE** |
| EN flag reliability | good | good (+1 repaired class) | good (TM flags) | **CV flag 67% MISS — Joueurs list is authority** |
| Strength at any second | situation codes | penalty rows (begin+mins) | explicit begin/end | **penalty Début/Fin explicit (GOOD — better than AHL)** |
| Coaches on sheet | yes (rightrail) | 96% + map | yes + map | **unknown, likely NO -> hand-curated map required** |
| Live in-game feed | score/now | scorebar | api/v2 live | **NONE known (odds-api scores TBD for paper harness)** |
| Season volume (games) | 1,312 | 1,152 | 450-480 | **264** |

## The five real losses, and the doctrine for each

### 1. Pull timing is INFERRED, not observed (the big one)
The Gardien en jeu table gives total off-ice seconds; pull_start is
back-calculated from an anchor (EN goal / trailing goal with empty net /
trailing penalty Début / period end). Consequences:
- **Single-pull windows with an anchor: timing is exact** (to sheet clock).
- **Multi-pull windows CANNOT be separated**: TOI is one total, anchors are
  per-goal. If a coach pulled, returned (for a reason other than his own
  penalty), and re-pulled, the sheet cannot express it. Doctrine: the
  adapter detects arithmetic inconsistency (off-ice total incompatible with
  a single segment against the anchors) and flags `multi_pull_ambiguous` —
  pull=True stands (evidence is real), TIMING is marked unusable
  (synthetic_pull_evidence convention, same as AHL's repaired class).
  These instances feed the pull-% ledger but never the hazard fit.
- **Pull with no anchor at all** cannot exist in Cases 1-4 logic (period end
  is always an anchor) — but a goalie returning for a NON-modeled reason
  breaks the case system. Doctrine: manual-review lane, never auto-classify
  (v1 already did this; we keep it and GATE it: flagged instances excluded
  from derived files until adjudicated in a trace doc).

### 2. Delayed penalties are invisible
No whistle events, no dp events. Ruling 17/17b's discriminators (segment
ends at leader-whistle) are UNAVAILABLE. What we know from our own NHL
measurement: dp possessions median ~4s, P(>25s)=8.7%, P(>60s)=0.5%.
Doctrine: the v1 <30s noise floor is REPLACED by our measured rule —
an inferred off-ice interval with duration <=25s and NO confirming goal
(no Joueurs-verified EN goal inside it) is dp/noise, not pull evidence;
25-60s unconfirmed intervals get flagged for review instead of auto-kept
(NHL tail says ~9% of dp runs live there). Confirmed-by-goal intervals are
pulls regardless of duration. Expected residual contamination after this:
<1% of pull records (vs the 2.2% we just excised from AHL) — SMALLER than
mainstream leagues because Magnus timing anchors are goal-confirmed.

### 3. Strength labels lie; penalty windows don't
Type field misses SH and CV flags (proven: 68933). Doctrine: strength is
ALWAYS reconstructed from penalty Début/Fin windows — which Magnus gives
EXPLICITLY (better than AHL's begin+minutes approximation). Misconducts
(10/20 min) excluded from strength per the fix we just shipped league-wide.
pp_pull classification therefore transfers at FULL precision.

### 4. Coach identity — RESOLVED BETTER THAN EXPECTED (2026-08-02)
The sheets DO carry coaches ("Entraîneur principal : ..."), per team per
game — the v1 docs missed this. Game-level attribution equal to NHL/AHL.
Verified on samples across 2021-2025 (LHENRY/AHO/VAS/PAREDES...). A
hand-curated map is demoted to a CROSS-CHECK artifact, not a source.

### 5. Volume: ~264 games/season
Projection from v1's season: ~110 gap-3 instances -> ~35-55 in-window
usable/season. With 3-4 seasons: roughly 150-220 instances, ~60-100 clear
chances, ~25-35 coaches. That is Liiga-class (172 clear/3 seasons) — enough
for: league prior + coach posteriors (ruling-33 estimator), morning sheet,
clear-chance take rate. NOT enough for: a within-Magnus blind walk-forward
until 26-27 completes (same as Liiga's one-thin-season caveat, worse).
Pricing doctrine: coach intel ships first; any priced Magnus market needs
either (a) 26-27 blind pass, or (b) a Seb override a la ruling 41 —
his call when the ledger exists, with the record in front of him.

## What transfers for free (why the shared engine wins)
Window detection (interval dict -> segments.py), ruling 17b's dp philosophy
(adapted per §2), misconduct exclusion, pp_pull classification, ruling-33
estimator, clean-window ledger machinery, random-audit harness (audit target:
re-verify TOI arithmetic + Joueurs lists per sampled instance), morning-sheet
builder (already league-parameterized), 21-gate discipline.

## Parser findings from the scan samples (2026-08-02, 8 sheets, 5 seasons)
- Format STABLE 2021->2025: one parser covers the whole lake.
- Tables are spatial columns, not sequential text. Coordinate windows work
  for roster/goals/penalties; the shared Gardien-en-jeu table assigns team
  by the goalie number's x-column (G.A vs G.B) — deterministic, replaces
  v1's alternating-order heuristic (their 25% collision pain).
- J+/J- have NO spatial boundary (lists typeset as one flow — the v1 "J+
  fragmentation" root cause). Split is SEMANTIC: prefix must be scoring-team
  roster numbers, suffix opponent's; on-ice-count constraints break ties;
  unresolvable rows flag to the manual lane. Handled a live cross-team
  jersey collision (#11 both rosters) on the first sample.
- Scheduled goalie changes appear as multiple stints summing to game
  duration (verified 41851, 68851). OT games show TOI > 3600 (11101:
  3796s) -> game duration must come from the sheet, never assumed 3600.
- Empty sheets exist (1051, cancelled COVID-era game): sheet_empty class,
  skipped with reason, kept in the lake verbatim.
- Live pull visible in sample 16351: Grenoble TOI 57:54 (126s off) with
  Rouen EG+CV at 56:15 — the TOI-anchor arithmetic checks out end-to-end.

## What we will NOT be able to do (stated now, so nobody discovers it later)
- Live in-game pricing from a Magnus feed (no live event source identified;
  paper harness can only log odds-api scores if the book carries Magnus).
- Hazard curves at NHL/AHL fidelity: fewer usable timing points (anchored
  singles only) -> wider bands; hazard SHAPE may need the Liiga shape as
  prior with Magnus level fit on its own (shapes-not-levels, ruling 26d).
- Dead-time (18s) measurement at second resolution: insufficient events;
  transfer the interval-league value as an assumption, documented.
- Sub-second pull-time precision: sheet clock is minute:second, anchors only.
