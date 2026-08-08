# DEL Round 2 — Manager findings from the sampled bytes (2026-08-08)

Seb ran steps 1-3. The Manager then pulled the sampled lake off his PC and
checked it directly. **Three defects, one of which would have shipped a lake
containing ~10% of the league.** Nothing here is the fetcher's fault in
design — every one of these is the kind of thing only real bytes reveal,
which is exactly why the sample stage exists.

## DEFECT 1 (critical) — fixture discovery is ~10% complete

Reported: 41 / 36 / 27 / 42 games = 146 across four seasons.
Truth: a DEL season is ~364 games. **The schedule page is MONTH-PAGINATED.**

Evidence from the saved bytes: every game link in the 2022-23
`_spielplan.html` is dated **September 2022** — 41 games, one month, and the
saved file has no others. The live 2025-26 page carries a month selector
with options `September 2025 ... März 2026` (7 months) plus a team filter.
The fetcher captured the DEFAULT month per season and nothing else.

So "41 games in 2022-23" is not archive depth — it is one month of it. The
`--full` run would have built a lake that looked complete and was not.
**Fix: iterate the month selector per season.** The mechanism is not in the
static HTML (no visible ?monat= / ?spieltag= / ?page=), so it must be
discovered — try query-param shapes first, then read the DataTables/jQuery
call in `/_assets/.../js/custom.js` which the page loads.

## DEFECT 2 — the five "channels" are ONE page fetched five times

sha256 of game 2580's tab files:

    a6106d4cef0ddd442a01e35555716d6879024b7eadfcf8ea583a62cd4a66dd42  2580_aufstellung.html
    a6106d4cef0ddd442a01e35555716d6879024b7eadfcf8ea583a62cd4a66dd42  2580_detail.html
    a6106d4cef0ddd442a01e35555716d6879024b7eadfcf8ea583a62cd4a66dd42  2580_spielerstats.html

Byte-identical. Every sampled game shows all five files at the same size.
The probe's "tabs 10/10 ok" was a **false positive: it checked HTTP status,
not content distinctness.** The tabs are client-side rendered (the page
loads DataTables + jQuery and hydrates them), so the server returns the same
shell for every tab URL.

Consequences: (a) fetch ONE page per game, not five — `bytes/game` is
**246,946 B (~247 KB)**, not the reported 1.07 MB; (b) goalie TOI, lineups
and any per-tab tables are NOT reachable over plain HTTP; (c) the probe's
tab check needs a content-hash comparison, not a status code — a defect
worth fixing in the tool since the same trap will recur on other leagues.

## DEFECT 3 — projection arithmetic

The sample stage printed `2023-24 0 games`, `2024-25 0`, `2025-26 0` and a
0.04 GB total, while the schedule stage had already found 36 / 27 / 42 in
those seasons. The projector only counts seasons it sampled. Cosmetic next
to Defect 1, but it made a broken number look precise.

**Corrected projection**: ~364 games/season x 4 seasons x 247 KB
= **~360 MB**. An order of magnitude under KHL's 4.14 GB. Size is a
non-issue; completeness was the real risk.

## CONFIRMED GOOD — the (a) verdict now rests on lake bytes, not WebFetch

The saved `2580_detail.html` contains a clean structured event table
(time | description), cumulative clock, extracted verbatim:

    60:00 | Drittelende
    58:31 | Torhüter ins Tor : Mathias Niederberger (#35)
    56:56 | Torhüter aus dem Tor : Mathias Niederberger (#35)
    56:28 | Torhüter ins Tor : Mathias Niederberger (#35)
    56:04 | Torhüter aus dem Tor : Mathias Niederberger (#35)
    55:50 | Torhüter ins Tor : Mathias Niederberger (#35)
    55:40 | Torhüter aus dem Tor : Mathias Niederberger (#35)
    52:36 | 2 Min. Strafe gegen Nicolas Appendino (#32) wegen DELAY
    40:00 | Drittelende
    40:00 | Drittelstart

Also present and not previously known: **explicit period markers**
(`Drittelstart` / `Drittelende`), and penalty rows carrying an offence code
(`DELAY`, `TRIP`, `ROUGH`, `SLASH`, `CROSS`).

Note the goalie pattern in this game: out 55:40 / in 55:50 (10s), out 56:04 /
in 56:28 (24s), out 56:56 / in 58:31 (95s). Three cycles, two of them very
short — the signature of ruling-17 delayed-penalty extra-attacker moments
rather than three separate pull decisions. DEL will exercise rulings 17/17b
from day one; the adapter session must be told so and must not treat every
`aus dem Tor` as a pull.

## STILL OPEN — the second audit channel (5a)

No independent recorder found. The tabs are duplicates, the page embeds no
JSON blob, and there is no `hockeydata` / `apiKey` / `divisionId` string
anywhere in the saved bytes. Per **ruling 52 the lake proceeds anyway** —
this is an adapter-stage blocker, and having the full bytes is what will
make it solvable (or provably unsolvable, in which case the audit is scoped
and the limit stated, as SHL 2023 was).

## Order of work

1. Fix Defect 1 (month iteration) — nothing else matters until fixtures are
   complete. Re-run `--schedule` and report the REAL per-season depth.
2. Fix Defect 2 (single page per game) and Defect 3 (projection counts all
   seasons with fixtures). Add a content-hash check to the probe's tab test.
3. Re-run `--sample`, confirm ~247 KB/game and a sane projection.
4. THEN `--full`.
