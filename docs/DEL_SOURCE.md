# DEL (PENNY DEL) — source contract

Round 1 is **ANSWERED: GO, capability (a)** (ruling 51, Manager, 2026-08-08).

Provenance, since it now differs by section:

- **From LAKE BYTES** (strongest): the event table, period markers, penalty
  offence codes, the month-pagination and duplicate-tab findings, and
  bytes/game. These come from the sample Seb fetched and the Manager checked
  directly — `docs/DEL_ROUND2_FINDINGS.md`, ruling 53.
- **From the Round 1 verdict**: the capability call and the penalty
  convention — `docs/DEL_ROUND1_VERDICT.md`, ruling 51 (WebFetch-derived).
- **UNCONFIRMED** rows were observed by nobody yet and are settled by the
  next `tools/fetch_del_raw.py` run.

This session derived none of it from bytes itself — its egress is blocked
(see `docs/HANDOFF_DEL.md` §1) — so per rule 0 every line stays a claim
awaiting re-derivation against the full lake.

## 1. Capability verdict — (a), top of the ladder

DEL publishes **explicit goalie-out / goalie-in events on a cumulative game
clock**. No Magnus-style TOI inference is needed. This is Liiga/SHL/AHL tier.

Event wording (German), quoted in ruling 51:

- `Torhüter aus dem Tor` — goalie leaves the net (the pull)
- `Torhüter ins Tor` — goalie returns

Named evidence:

| Game | Fixture | Date | Evidence |
|---|---|---|---|
| 3947 | ERC Ingolstadt vs Iserlohn Roosters | 12.09.2025 | `aus dem Tor` **57:34**, `ins Tor` **57:51**, `aus dem Tor` **58:22** — a pull, a return, and a re-pull |
| 3964 | Adler Mannheim vs ERC Ingolstadt | — | clean pull at **58:18** |

The 3947 sequence matters beyond confirming the verdict: **the adapter must
handle multiple pull/return cycles inside one gap-3 window**, not assume one
pull per instance. Clock is cumulative game time, so no period-relative
conversion is needed — but that is exactly the kind of assumption ground
truth batch 1 must confirm rather than inherit.

## 2. URL contract

| Channel | Pattern | Status |
|---|---|---|
| Season schedule | `/statistik/saison-{YYYY-YY}/hauptrunde/spielplan` | CONFIRMED — **MONTH-PAGINATED** |
| Game detail | `/statistik/spieldetails/{DDMMYYYY}_{home}_gg_{away}_{gameid}` | CONFIRMED — one page carries everything |
| Tabs | `aufstellung`, `spielerstats`, `schuesse`, `bullies` | CONFIRMED **NOT separate channels** — see below |
| League TOI table | `/statistik/{saison}/hauptrunde/playerstats/toi` | UNCONFIRMED (Manager recon lead) |

Host `https://www.penny-del.org`. Example detail slug shape:
`12092025_erc-ingolstadt_gg_iserlohn-roosters_3947`. The club slugs in the
URL are also the club identifiers — derive the team list from them, never
from memory (promotion/relegation silently breaks a hardcoded list).

### The schedule is month-paginated (ruling 53, Defect 1)

The page serves **one month at a time**. The 2025-26 page carries a month
selector spanning `September 2025 … März 2026` (7 months) plus a team
filter. The first fetcher took the default month for a whole season and
reported 41 games for 2022-23 — every one of them dated September 2022,
about 10% of the league. A `--full` run on that would have produced a lake
that looked complete and was not.

The paging mechanism is **not** in the static HTML (no visible `?monat=`,
`?spieltag=` or `?page=`). `fetch_del_raw.py` discovers it at runtime,
falling back to reading the DataTables JS asset, and applies a structural
completeness check (clubs and games/team derived from the fixtures
themselves) that refuses to call a one-month season complete.

### The four tabs are one page fetched four times (ruling 53, Defect 2)

For game 2580, `detail`, `aufstellung` and `spielerstats` are byte-identical:

```
a6106d4cef0ddd442a01e35555716d6879024b7eadfcf8ea583a62cd4a66dd42
```

The tabs are rendered client-side (DataTables + jQuery), so the server
returns the same shell for every tab URL. The first probe passed them as
"10/10 ok" because it compared **HTTP status, not content** — a false
positive now gated portfolio-wide by
`test_channel_check_compares_content_not_status`.

Consequences: fetch **one page per game** (~247 KB, not the ~1.07 MB first
reported, giving a whole-lake projection of ~360 MB); and per-tab tables
(goalie TOI, lineups) are **not reachable over plain HTTP** — which is also
why coaches are absent and the coach map stands.

**Retired guesses** (made before Round 1 was answered, superseded — do not
resurrect): `/spielbericht/{id}`, `/spiele/{id}`, and the invented
hockeydata LOS REST paths `/rest/icehockey/los/game/{id}/{fullreport,livebox,events}`.

## 2b. The event table (confirmed from lake bytes, ruling 53)

The game detail page carries a structured `time | description` table on a
**cumulative game clock**, verbatim from the saved `2580_detail.html`:

```
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
```

This is what the capability-(a) verdict now rests on — lake bytes, not a
WebFetch summary. Two things found here that were not previously known:

- **Explicit period markers**: `Drittelstart` / `Drittelende`. Period
  boundaries do not have to be inferred from the clock.
- **Penalty rows carry an offence code**: `DELAY`, `TRIP`, `ROUGH`,
  `SLASH`, `CROSS`.

Goalie rows name the goalie and shirt number, so goalie identity is
available per event, not just the fact of a change.

### ⚠ Warning for the adapter session — do not read `aus dem Tor` as "pull"

Game 2580 has **three out/in cycles inside three minutes**: out 55:40 / in
55:50 (10s), out 56:04 / in 56:28 (24s), out 56:56 / in 58:31 (95s). Two of
those are far too short to be pull decisions — that is the **ruling-17
delayed-penalty extra-attacker signature**, not three separate pulls.

**DEL will exercise rulings 17 / 17b from day one.** Any adapter that treats
every `Torhüter aus dem Tor` as a pull will manufacture phantom pulls at
scale. The KHL dp cross-calibration (ruling 46) is the reference for how
these get classified.

## 3. Penalties — START-TIME-ONLY (settled, do not go looking)

Penalties carry a player, an offence and a **start time only**:

```
2 Min. Strafe gegen X wegen TRIP at 43:32
```

There are **no Von/Bis columns**. DEL is therefore **AHL-class on penalties**
and the adapter inherits the **AHL minor-termination convention** — not the
Liiga/SHL explicit-end path. Ruling 51 settled this; it is not to be
re-derived, and no session should spend time hunting for end times.

## 4. Known gaps (Round-2 work, ruling 51)

1. **No second audit channel — still open after ruling 53.** The tab
   candidate is dead (the tabs are duplicates), and the saved bytes contain
   no embedded JSON and no `hockeydata` / `apiKey` / `divisionId` string
   anywhere. `fetch_del_raw.py --sample` re-checks both on every run.
   **Ruling 52: the lake proceeds regardless.** This is an adapter-stage
   blocker, and having the full bytes is what will make it solvable — or
   provably unsolvable, in which case the audit is scoped and the limit
   stated, as SHL 2023 was.
2. **Coaches are on neither game nor squad pages.** A coach map with dated
   spells and a primary source per row is mandatory:
   `data/coach_maps/del_coaches.csv` (schema written, zero rows) with
   build rules in `del_coaches_notes.md`. Unlike every other league this is
   the *only* coach source, not a blank-filler.
3. **No empty-net flag on goals seen.** If confirmed absent, EN goals cannot
   corroborate the pull interval — the adapter loses one cross-check. It
   does **not** affect the (a) verdict, since pull timing comes from the
   explicit events.

## 5. Lake conventions (non-negotiable)

- Branch `del-data-lake` on the V2 repo.
- **First commit is `.gitattributes` containing `* -text`** (CRLF incident).
- Raw bytes verbatim: never edited, never pretty-printed, never normalised.
- One directory per season; filenames carry season + game id + channel.
- `SHA256SUMS.txt` per season, **re-hashed after transfer**, result recorded
  in the handoff (`fetch_del_raw.py --verify`).
- Every count scoped to the game's own structural rows. Fixture discovery
  matches the game-detail URL shape only and is gated
  (`test_del_fixture_parser_is_scoped`) — the ticker lesson has bitten twice.

## 6. Order of operations

`--schedule` → `--reconcile` (0/0 both directions vs an independent list)
→ `--sample 10` → **report the projection to the Manager and wait**
→ `--full` → `--verify`.

`--schedule` must now clear its structural completeness check before
anything else runs: a season served one month at a time looks complete and
is not. Size turned out never to be the risk — at ~247 KB/game the whole
four-season lake projects to **~360 MB**, an order of magnitude under KHL's
4.14 GB. Completeness was the risk, and that is what the check defends.
