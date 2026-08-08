# DEL (PENNY DEL) — source contract

Round 1 is **ANSWERED: GO, capability (a)** (ruling 51, Manager, 2026-08-08).

Provenance of everything below: the CONFIRMED rows come from the Manager's
Round 1 verdict (ruling 51 in `docs/DECISIONS.md`), which quotes verbatim
evidence from two named games. Rows marked UNCONFIRMED were not observed by
anyone yet and are settled by the first real run of
`tools/fetch_del_raw.py`. Nothing here was derived by this session from raw
bytes — its egress is blocked (see `docs/HANDOFF_DEL.md` §1), so per rule 0
every line is a claim awaiting re-derivation against the lake.

> **Note for the Manager:** ruling 51 and the CLAUDE.md STATUS row both cite
> `docs/DEL_ROUND1_VERDICT.md`, but commit `c669f48` added only `CLAUDE.md`
> and `docs/DECISIONS.md` — **the verdict document is not on master.** The
> headline evidence survives inline in ruling 51 and is used here; the full
> per-game trace does not. Worth pushing, since it is the primary evidence
> for the (a) verdict.

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
| Season schedule | `/statistik/saison-{YYYY-YY}/hauptrunde/spielplan` | CONFIRMED |
| Game detail | `/statistik/spieldetails/{DDMMYYYY}_{home}_gg_{away}_{gameid}` | CONFIRMED |
| Tabs | `aufstellung`, `spielerstats`, `schuesse`, `bullies` | tabs CONFIRMED to exist; **how they compose onto the detail URL is UNCONFIRMED** |
| League TOI table | `/statistik/{saison}/hauptrunde/playerstats/toi` | UNCONFIRMED (Manager recon lead) |

Host `https://www.penny-del.org`. Example detail slug shape:
`12092025_erc-ingolstadt_gg_iserlohn-roosters_3947`.

The tab composition is the one open URL question. `fetch_del_raw.py` appends
tabs as a path suffix (`.../{slug}/aufstellung`) and prints per-tab HTTP
status on `--sample`, so the first run settles it from response codes; if
they 404, re-run with `--tab-mode=query`. The club slugs in the URL are also
the club identifiers — derive the team list from them, never from memory.

**Retired guesses** (made before Round 1 was answered, superseded — do not
resurrect): `/spielbericht/{id}`, `/spiele/{id}`, and the invented
hockeydata LOS REST paths `/rest/icehockey/los/game/{id}/{fullreport,livebox,events}`.

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

1. **No second audit channel identified.** The adapter's 0/60 random audit
   needs an independent recorder to compare against. Candidates to test:
   the `spielerstats` tab (does it carry goalie TOI or saves?) and any
   hockeydata feed the page embeds. `fetch_del_raw.py --sample` probes both.
   **This is an adapter blocker, not a lake blocker** — the lake can be
   built while it is open.
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
→ `--sample 10` → **report the projected size to the Manager and wait**
→ `--full` → `--verify`. KHL was 4.14 GB; a surprise of that order is not
acceptable.
