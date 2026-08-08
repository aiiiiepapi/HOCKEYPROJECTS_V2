# Kickoff prompt — DEL SCRAPE session (written by Manager, 2026-08-08)

Build session. Scope: **raw data lake for the DEL (Deutsche Eishockey Liga,
sponsor name PENNY DEL) + a source-capability report.** NO adapter, NO
ledger, NO pricing, NO bet conclusions — those are Manager work post-merge.
Create the session WITH THE REPO ATTACHED (a session born without it can
never push — proven twice). FIRST ACTION: branch `del-scrape`, empty commit,
push, confirm success before anything else.

## Read, in order (all on master)

1. CLAUDE.md — rules 0/0b/1-15b are binding. Rule 1: hit real data in the
   first 10 minutes. Rule 10: suspicious = wrong. Rule 4: never fabricate.
2. docs/KICKOFF_KHL_SCRAPE.md + docs/KHL_LAKE_VERIFICATION.md — the most
   recent lake done right, and the standard the Manager verifies against.
3. docs/MESTIS_LAKE_VERIFICATION.md — the TICKER LESSON (a page-wide grep
   counted other games' events; every count must be scoped to the
   structural rows of the game you are on). This has bitten twice.
4. docs/MAGNUS_DATA_GAPS.md + hockeycore/leagues/magnus.py — the fallback
   path if DEL has no explicit goalie events (net-empty inferred from
   goalie TOI totals with EN goals as hard anchors). It works, it is
   gated, and it is much weaker than explicit events. Know it exists;
   do not assume you need it until discovery says so.

## Manager recon (verify everything — this is a lead, not a finding)

- Official site **www.penny-del.org**. Stats are server-rendered, season
  slugs look like `/statistik/saison-2025-26/hauptrunde/...`, and a
  league-wide **player TOI table exists**
  (`/statistik/saison-2025-26/hauptrunde/playerstats/toi`) — which is
  promising for the Magnus-style fallback IF per-game goalie TOI is
  reachable.
- The stats infrastructure appears to be **hockeydata "LOS"**
  (apidocs.hockeydata.net — the Manager could not fetch it, robots).
  Documented widgets include `Game.FullReport`, `Game.LiveBox`,
  `Game.Info`, `LiveGames`, `Schedule`. LiveBox is documented to carry
  **goals, penalties and a play-by-play log**; parameters are
  `apiKey`, `divisionId`, `gameId`, `sport=icehockey`. **Goalie
  substitution is NOT documented anywhere the Manager could reach** —
  that is the single most important unknown in this build.
- MagentaSport game-report links on the DEL homepage carry numeric game
  ids (e.g. `432379`, `432252`, `432080` — April/May 2026), which may or
  may not be the same id space as the stats system. Resolve it.
- The DEL `/spiele` schedule page did not expose per-game hrefs in plain
  HTML — the fixture list may be JS-hydrated. Find the underlying feed
  rather than scraping rendered text.

## ROUND 1 — CAPABILITY BAR (do this BEFORE fetching anything at scale)

Pick **5 named completed games across at least 2 seasons** and prove, with
raw bytes saved to the branch, whether each of these exists per game:

1. **GOALIE PULL EVIDENCE — the go/no-go.** In descending order of value:
   (a) explicit goalie-out/goalie-in events with a game clock;
   (b) on-ice player lists per goal (empty net inferred from goalie
       absence, KHL-style);
   (c) per-game goalie TOI totals (Magnus-style inference — weakest,
       and it forces a whole extra class of GT work);
   (d) an "empty net" flag on goals only (NOT sufficient alone — it
       gives you EN goals but no pull timing).
   **If only (d) exists, STOP and report. That is a NO-GO source and the
   Manager will not spend a session on an adapter for it.**
2. Goals: absolute or period clock, period number, scoring side, running
   score, and strength (EQ/PP/SH) if present.
3. Penalties: player, minutes, and **begin/end times** (explicit ends are
   Liiga/SHL-class; begin+minutes forces the AHL termination convention).
4. Head coach per team per game (a name, from a page you can fetch per
   game — not a season roster you have to join by hand).
5. Overtime and shootout markers, so decider goals can be excluded.

Report the answer as a table, one row per game, with the exact URL and a
verbatim quote of the relevant raw line for every YES.

## ROUND 2 — only after the Manager sees Round 1

- Reconcile the full fixture list per season against an INDEPENDENT
  source (the schedule feed vs the results/archive pages) — 0/0 both
  directions, the KHL/SHL standard. Regular season (`hauptrunde`) is the
  target; note playoff coverage separately.
- **Repo-size check BEFORE the bulk fetch**: fetch 10 games, measure
  bytes/game, multiply by (games/season x 4 seasons), and report the
  projected lake size to the Manager. KHL was 4.14 GB; anything of that
  order needs a heads-up, not a surprise.
- 4 seasons if they exist (2022-23 .. 2025-26). If the archive is
  shallower, say so — do not pad.

## Lake conventions (non-negotiable, all learned the hard way)

- Branch `del-data-lake` on the V2 repo. **FIRST COMMIT = `.gitattributes`
  containing `* -text`** (CRLF incident: a whole lake had to be re-hashed).
- Raw bytes VERBATIM, never edited, never pretty-printed. One directory
  per season, stable filenames including season + game id.
- `SHA256SUMS.txt` per season; **re-hash AFTER transfer** and record the
  result in the handoff.
- Every count you report must be scoped to the game's own structural
  rows (ticker lesson). If a number surprises you, it is your parser
  until proven otherwise (rule 42).
- Never commit tokens; push protection is on.

## Deliverables

1. `docs/DEL_SOURCE.md` — the source contract: every endpoint/URL pattern,
   parameters, what each channel carries, quirks with named games.
2. `docs/HANDOFF_DEL.md` — capability table, fixture reconciliation,
   per-season counts, hash manifest results, projected/actual lake size,
   open questions. Everything framed as a CLAIM for the Manager to
   re-derive (rule 0).
3. The lake itself on `del-data-lake`.

## Scope fence

No adapter, no gap logic, no instances, no ledger, no numbers about
coaches or pull rates. Master is never touched. Your branch only.
Report numbers to Seb immediately as you get them; if it looks off, it IS off.
