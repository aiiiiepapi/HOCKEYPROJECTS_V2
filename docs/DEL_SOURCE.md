# DEL (PENNY DEL) — source contract

**STATUS: STUB. NOTHING IN THIS FILE IS VERIFIED.**

This file is the intended home of the DEL source contract (every endpoint,
its parameters, what each channel carries, quirks with named games), in the
shape of `docs/KHL_SOURCE.md`, `docs/SHL_SOURCE.md` and
`docs/MESTIS_SOURCE.md`.

It is empty of findings because the Round 1 scrape session (2026-08-08) was
blocked by the environment's egress policy before it could fetch a single
byte — `www.penny-del.org`, `www.hockeydata.net` and `apidocs.hockeydata.net`
all answer 403 to the proxy CONNECT. See `docs/HANDOFF_DEL.md` for the
reproduction and the proxy's own log of the denials.

**Do not treat anything below as a finding.** Per rule 0 every line here gets
re-derived from raw bytes before it earns a place in the contract, and per
rule 4 nothing gets written down that was not observed.

## Unverified leads (Manager recon + web search only)

| Lead | Source of the claim | Status |
|---|---|---|
| Official site `www.penny-del.org`, stats server-rendered | Manager recon | UNVERIFIED |
| Season slugs `/statistik/saison-2025-26/hauptrunde/...` | Manager recon | UNVERIFIED |
| League-wide player TOI table at `/statistik/<saison>/hauptrunde/playerstats/toi` | Manager recon | UNVERIFIED |
| Stats infrastructure is hockeydata "LOS" | Manager recon | UNVERIFIED |
| LOS widgets take `apiKey`, `divisionId`, `gameId`, `sport=icehockey` | apidocs.hockeydata.net (via search snippet) | UNVERIFIED |
| `Game.LiveBox` carries goals, penalties and a play-by-play log | apidocs (via search snippet) | UNVERIFIED |
| `Game.FullReport` documents ice-hockey sections `GoalKeeperChanges` and `GoalKeepers` | apidocs (via search snippet, 2026-08-08) | UNVERIFIED — **and the same docs warn columns may be empty depending on the league.** A documented column is not a populated column. |
| MagentaSport game ids on the DEL homepage (`432379`, `432252`, `432080`) | Manager recon | UNVERIFIED, and it is unknown whether this is the stats id space |
| `/spiele` exposes no per-game hrefs in plain HTML (likely JS-hydrated) | Manager recon | UNVERIFIED |

## The one question this file exists to answer

Does the DEL source carry **goalie pull evidence with a game clock**?

- (a) explicit goalie-out/goalie-in events with a clock — best
- (b) on-ice player lists per goal — workable, KHL-style
- (c) per-game goalie TOI totals — weakest, Magnus-style, extra GT class
- (d) an "empty net" flag on goals only — **NO-GO**

**Currently unanswered.** `tools/del_round1_probe.py` (run it from
`tools\PROBE_DEL_ROUND1.bat` on Seb's PC) fetches the evidence and saves the
raw bytes needed to answer it by hand.

## Conventions already fixed for the eventual lake

- Branch `del-data-lake` on the V2 repo.
- **First commit is `.gitattributes` containing `* -text`** (CRLF incident).
- Raw bytes verbatim, never edited, never pretty-printed; one directory per
  season; filenames carry season + game id.
- `SHA256SUMS.txt` per season, re-hashed *after* transfer.
- Every count scoped to the game's own structural rows (the ticker lesson,
  which has bitten twice).
