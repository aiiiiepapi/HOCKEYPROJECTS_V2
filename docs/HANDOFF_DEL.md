# HANDOFF — DEL scrape session, Round 2 (2026-08-08)

Branch `del-scrape`, rebased onto master at `c669f48` (ruling 51). Master
untouched. Lake branch `del-data-lake` created.

**Summary: every Round-2 item that is code has been built and gated. Every
Round-2 item that requires FETCHING is blocked in this session and must run
on Seb's PC.** Numbers — fixture counts, reconciliation, size projection —
are therefore *not* reported here, because I have not fetched a byte. They
come out of the first run.

## 1. The egress correction, corrected back

Ruling 51's standing rule is accepted and was followed: **try WebFetch
before declaring a host unreachable, and name the channel tested.** I did
test both channels in Round 1 and reported both, so the rule costs nothing
here — but my Round-1 write-up did generalise "my session is blocked" into
"the environment is blocked", and that was over-reach. Corrected.

The factual half of the correction does not hold for this session, and it
matters for who can do Round 2. Re-tested this session, naming each channel:

| Host | WebFetch tool | python/curl |
|---|---|---|
| `www.penny-del.org` | `EGRESS_BLOCKED` | 403 CONNECT |
| `www.eliteprospects.com` | `EGRESS_BLOCKED` | — |
| `en.wikipedia.org` (control) | `EGRESS_BLOCKED` | — |

The control is the decisive one: **WebFetch in this session cannot reach
Wikipedia either.** So this is not a DEL-host policy — this session has no
WebFetch egress at all, while the Manager session evidently does. The
difference is per-session, not per-tool. WebSearch remains my only route out.

Consequence, stated plainly: **I cannot run the schedule fetch, the fixture
reconciliation, the size projection, the second-channel test, or the EN-marker
check from here.** Not "it would be slow" — the bytes are unreachable. Those
five items are built and ready to run, and they need Seb's PC or the Ubuntu
server. I have not guessed at any of their outputs.

## 2. Built this round

### `tools/fetch_del_raw.py` (+ `FETCH_DEL_LAKE.bat`)
The Round-2 lake fetcher, on the **confirmed** URL contract. Stdlib-only,
fetch-only, verbatim bytes, sha256 manifest. Staged deliberately so the
size projection lands before any bulk fetch:

```
FETCH_DEL_LAKE.bat schedule     # fixtures per season -> fixtures_{season}.csv
FETCH_DEL_LAKE.bat reconcile    # 0/0 both directions vs an independent list
FETCH_DEL_LAKE.bat sample       # bytes/game -> PROJECTED LAKE SIZE. STOP HERE.
FETCH_DEL_LAKE.bat full         # builds the lake, per-season SHA256SUMS.txt
FETCH_DEL_LAKE.bat verify       # re-hash AFTER transfer
```

Behaviours worth knowing before someone runs it:

- **Reconciliation refuses to fake a pass.** It tries a list of candidate
  independent sources; if none resolves it prints
  `NO INDEPENDENT LIST RESOLVED -- reconciliation NOT done` rather than
  comparing the schedule against itself and reporting a meaningless 0/0.
- **Season depth is not padded.** A season that yields 0 games is reported
  as 0, with a note that the archive may simply be shallower than four
  seasons. Ruling 51 did not establish archive depth and neither do I.
- **The tab URL shape is the one thing I could not confirm.** Ruling 51
  names the tabs but not how they compose onto the detail URL. The script
  appends them as a path suffix, prints per-tab HTTP status on `--sample`,
  and tells you to re-run with `--tab-mode=query` if they 404. First run
  settles it from response codes rather than from my guess.
- **Retired guesses are gone**, per your order: `/spielbericht/{id}`,
  `/spiele/{id}` and the invented LOS REST paths are deleted from the probe,
  and listed as retired in `DEL_SOURCE.md` so nobody resurrects them.

### `tools/del_round1_probe.py` — repurposed, not discarded
Re-pointed at the confirmed `spieldetails` pattern + tabs. Its detector and
gate stay as calibrated triage for the **next** league. Stage 2 still mines
the page's widget JavaScript, because an embedded hockeydata feed is a live
candidate for the missing audit channel.

### `data/coach_maps/del_coaches.csv` + `_notes.md`
Schema and build rules, **zero rows** — I cannot reach Elite Prospects or
any primary source, and inventing coach spells would be fabricated data on
the join key for every downstream coach number.

The notes record the thing that makes DEL different: for every other league
the map is a blank-filler and the listing wins. Here it is the **only**
coach source, so it must cover every team-season with contiguous,
non-overlapping, dated spells. Two build rules recorded: derive the club
list from the fixture slugs rather than typing it from memory (promotion and
relegation silently break a hardcoded list), and prefer **first game behind
the bench** over announcement date, since the map joins to games.

### `del-data-lake` branch
Created, first and only commit is `.gitattributes` containing `* -text`,
pushed. The CRLF protection is in place *before* any bytes land, which is
the whole point of the rule.

## 3. Gates

Two DEL gates, both green, added to the cumulative suite:

- `test_del_probe_detector_never_false_no_go` — ratified in ruling 51, kept.
- `test_del_fixture_parser_is_scoped` — **new.** Fixture discovery must match
  the structural game-detail URL shape only and ignore loose ids, attendance
  numbers and neighbouring link types. This is the ticker lesson written as
  a test, since it has now bitten twice; it also collapses duplicate links,
  which a schedule page will contain.

Full suite: **32 passed, 4 skipped** (skips are unmounted AHL/Liiga/KHL lakes).

## 4. Three Round-2 questions — status

**(a) Second audit channel — BUILT, UNRUN.** `--sample` saves the
`spielerstats` tab and scans it for goalie TOI/saves, and separately mines
the detail page for an embedded hockeydata feed (host + apiKey + divisionId).
If neither yields an independent recorder it says so plainly rather than
reporting a weak one as a pass. I cannot tell you the answer without bytes,
and I am not going to infer it from documentation.

**(b) Coaches — SCAFFOLDED, UNPOPULATED.** Schema, build rules and
verification criteria written; rows need network. Elite Prospects is
recorded as a **lead, not a primary source** — it is user-maintained, so
each row still needs a club announcement or dated report behind it.

**(c) EN markers — BUILT, UNRUN.** `--sample` scans sampled goal rows for
empty-net markers and, if none are found, records the consequence: the
adapter loses one cross-check, and the (a) verdict is unaffected because
pull timing comes from the explicit `Torhüter` events.

## 5. One discrepancy to flag

Ruling 51 and the CLAUDE.md STATUS row both cite
**`docs/DEL_ROUND1_VERDICT.md`**, but commit `c669f48` added only
`CLAUDE.md` and `docs/DECISIONS.md`. **The verdict document is not on
master.** The headline evidence survives inline in ruling 51 — the 3947
`57:34 / 57:51 / 58:22` sequence and 3964's `58:18` — and I used it. The
full per-game trace does not, and it is the primary evidence for the (a)
verdict. Probably an unstaged file in the PC push.

## 6. What I need back

1. **Someone runs steps 1-3 on Seb's PC** and sends the console output plus
   `tools/del_lake/fixtures_*.csv`. That gives fixture counts, real archive
   depth, the reconciliation result, the tab-shape answer and the size
   projection — the numbers this handoff deliberately does not contain.
2. **`docs/DEL_ROUND1_VERDICT.md` pushed**, so the (a) verdict has its
   primary evidence in the repo.
3. Then `--full`, `--verify`, and the lake commits onto `del-data-lake`.

Scope fence held: no adapter, no gap logic, no instances, no ledger, no
coach numbers, no pull rates. Everything above is a claim for the Manager to
re-derive.
