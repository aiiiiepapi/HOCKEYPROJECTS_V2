# DEL Round 1 — ANSWERED: GO, capability (a)

Manager, 2026-08-08. The scrape session could not answer this (its egress
refused every DEL host) and correctly refused to guess. The Manager session's
WebFetch tool DOES reach these hosts, so Round 1 was answered here instead —
from live pages, with verbatim quotes, on named games.

## The go/no-go: EXPLICIT GOALIE IN/OUT EVENTS WITH A GAME CLOCK

Source: `penny-del.org` game pages.
URL pattern (confirmed on the 2025-26 schedule):
`https://www.penny-del.org/statistik/spieldetails/{DDMMYYYY}_{home-slug}_gg_{away-slug}_{gameid}`
with tabs `/aufstellung`, `/spielerstats`, `/schuesse`, `/bullies`.

**Game 3947 — ERC Ingolstadt 2:3 Iserlohn Roosters, 12.09.2025** (verbatim):

    0:00  | Torhüter ins Tor : Devin Williams (#31)
    0:00  | Torhüter ins Tor : Andreas Jenike (#92)
    57:34 | Torhüter aus dem Tor : Devin Williams (#31)
    57:51 | Torhüter ins Tor : Devin Williams (#31)
    58:22 | Torhüter aus dem Tor : Devin Williams (#31)

A pull, a return, and a re-pull inside the last 2:26 — the exact multi-pull
structure segments.py already models.

**Game 3964 — Adler Mannheim 2:1 ERC Ingolstadt, 21.09.2025** (verbatim):

    0:00  | Torhüter ins Tor : Johan Christer Mattsson (#33)
    0:00  | Torhüter ins Tor : Devin Williams (#31)
    58:18 | Torhüter aus dem Tor : Devin Williams (#31)

Single clean pull, 1:42 left, trailing by one.

Clock is CUMULATIVE game time (57:34 = P3 17:34), same convention as KHL
protocol time. Capability class: **(a)** — the best tier in the kickoff's
ladder, equal to Liiga/SHL/AHL. No Magnus-style TOI inference needed.

## Confirmed alongside

- **Goals**: time + scorer + assists + team, on the same event timeline
  (game 3947: 13:51, 21:54, 24:32, 39:17, 40:45 with names/assists).
- **Penalties**: `2 Min. Strafe gegen Eric Cornel (#18) wegen TRIP` at
  43:32 — offender, minutes, offence code, **START TIME ONLY**.
  Consequence: DEL is AHL-class on penalties, not Liiga/SHL-class. The
  adapter must apply the AHL minor-termination convention (box window =
  begin + nominal minutes, early release on PP goal), NOT explicit ends.
  This is a known, solved convention — but it must be stated in the
  adapter docstring and gated.

## Gaps that are now Round-2 work, not unknowns

1. **COACHES ARE NOT ON THE GAME PAGE** — checked the overview and the
   team `/kader` page; neither names a Trainer. This is the SHL/Mestis
   problem: it needs a coach map with DATED spells and a primary source
   per row (`data/coach_maps/mestis_coaches.csv` is the template; mid-
   season changes need dated evidence, not a season-level guess).
   Lead worth checking first: Elite Prospects publishes per-club
   "team-staff-history" pages (e.g. `/team/445/erc-ingolstadt/
   team-staff-history`, `/team/475/iserlohn-roosters/team-staff-history`)
   with head-coach spells. Verify against club sources before trusting.
2. **No empty-net marker on goals was visible.** Not fatal — with
   explicit intervals, EN is derivable (goal inside the opponent's
   net-empty window). But the AHL/Mestis EN-repair cross-check loses one
   independent channel, so the audit must lean on a second source.
3. **Second channel for the random audit**: unresolved. The `/spielerstats`
   tab (goalie saves/TOI?) and the hockeydata LiveBox feed are the two
   candidates. The portfolio standard is 0/60 against an INDEPENDENT
   channel — find one before the adapter session, or the audit gate has
   nothing to compare against.

## Verdict

**GO.** DEL clears the capability bar at the top tier. Proceed to Round 2
(fixture reconciliation, repo-size projection, bulk fetch on Seb's PC).
