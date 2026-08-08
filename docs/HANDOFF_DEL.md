# HANDOFF — DEL scrape session, Round 1 (2026-08-08)

**Status: ROUND 1 IS NOT ANSWERED. The session was network-blocked before it
could touch a single byte of DEL data.** Everything below is either a
verified statement about *this environment* or an explicitly-labelled
unverified lead. Nothing here is a finding about the DEL source.

Branch: `del-scrape`. Master untouched.

## 1. The blocker (verified, reproducible)

This cloud session cannot reach any DEL-related host. The egress proxy
answers **403 to the CONNECT** for every one of them:

| Host | curl (python/stdlib path) | WebFetch tool |
|---|---|---|
| `www.penny-del.org` | 403 CONNECT tunnel failed | `EGRESS_BLOCKED` |
| `www.hockeydata.net` | 403 CONNECT tunnel failed | `EGRESS_BLOCKED` |
| `apidocs.hockeydata.net` | (not probed by curl) | `EGRESS_BLOCKED` |
| `del.hockeydata.net`, `live.hockeydata.net`, `api.hockeydata.net` | 403 | — |
| `www.magentasport.de` | 403 | — |

The proxy's own status endpoint records the denials verbatim:

```
"recentRelayFailures": [
  {"kind":"connect_rejected",
   "detail":"gateway answered 403 to CONNECT (policy denial or upstream failure)",
   "host":"www.penny-del.org:443"},
  {"kind":"connect_rejected",
   "detail":"gateway answered 403 to CONNECT (policy denial or upstream failure)",
   "host":"www.hockeydata.net:443"}
]
```

`/root/.ccr/README.md` is explicit that this class is an organisation egress
policy denial and must be **reported, not routed around**. So it was.

This is the same constraint CLAUDE.md already records under *Environment
facts* ("the cloud workspace cannot reach league APIs from Python (proxy
403); fetchers therefore run on Seb's Windows PC"). It is not new, and it is
not fixable from inside the session. **Only WebSearch has a route out**, and
a search snippet is not raw bytes — rule 4 forbids reporting it as one.

## 2. What that means for the capability bar

The kickoff's single go/no-go question — *does the DEL source carry goalie
pull evidence with a game clock?* — **remains open.** It cannot be honestly
answered from here, and I am not going to answer it from search snippets and
inference. Per rule 0, a capability claim needs bytes.

The one thing search did establish, as an **unverified lead only**:
hockeydata's `Game.FullReport` widget documents ice-hockey sections named
**`GoalKeeperChanges`** and `GoalKeepers`. That is encouraging — it is the
shape of capability (a). But the same documentation carries the warning that
*"depending on the league, some columns may not contain values since they
aren't recorded"*, which is precisely the DEL-specific unknown. **A
documented column is not a populated column.** Treat this as a lead to
verify, nothing more.

## 3. What was built instead (the thing that unblocks Round 1)

`tools/del_round1_probe.py` + `tools/PROBE_DEL_ROUND1.bat` — a fetch-only,
stdlib-only Round-1 probe that runs on Seb's PC, where the network works.
It follows the established `tools/fetch_*.py` convention.

It is **discovery-first**, because the endpoints genuinely are not known:
rather than guessing REST paths, it downloads the hockeydata widget
JavaScript the DEL site itself loads and extracts the real config
(`apiKey`, `divisionId`) and URL patterns out of it. Guessed endpoints are
additive only and are written to disk with a `GUESS_` filename prefix so
they can never be mistaken for a confirmed contract.

- Saves every response **verbatim** to `tools/del_probe/raw/`, with a
  `manifest.csv` carrying status, bytes and sha256 per file.
- Scans the saved bytes for goalie / play-by-play / penalty / coach /
  overtime evidence in **German and English**, and prints a verbatim quoted
  fragment for every hit — the evidence the kickoff asks for.
- Emits a triage verdict on the kickoff's (a)/(b)/(c)/(d) ladder.
- Re-runnable; already-downloaded files are skipped.

**How to run it:** double-click `tools\PROBE_DEL_ROUND1.bat`. It takes about
a minute and downloads a handful of pages, not a lake. Send back the whole
`tools\del_probe\` folder — the bytes are the evidence, the printed summary
is not. If the site turns out to be JS-hydrated (the kickoff suspects it is)
and stage 2 finds no ids, open one game report in a browser, copy the real
data URL out of the network tab, and re-run with `--games`.

## 4. The verdict function is triage, and it is calibrated

The probe's verdict is **not** a finding — every YES is meant to be
hand-confirmed against the raw bytes. But since a false **(d) NO-GO** would
kill an adapter that should have been built, the detector was calibrated
against the seven lakes whose capability class we already know, and is now a
standing gate: `test_del_probe_detector_never_false_no_go`.

Two real false NO-GOs were caught this way while writing it, both recorded
in the code comments:

1. **The AHL feed returned (d) NO-GO.** The first token table used literal
   strings and missed the feed's actual `goalie_change` / `goalie_out_id`
   keys. Fixed by matching word *parts* separator-blind, so `goalie_change`,
   `goalieChange`, `goalie-change` and `"goalie change"` all hit one entry.
2. **The NHL feed returned (d) NO-GO.** The `(b)` branch required an
   arbitrary `GOALS` co-hit that the NHL pbp does not use. Fixed, and `(d)`
   now fires only when the empty-net flag is genuinely the *only* goalie
   signal present.

Current classification of the known lakes (all at or above their documented
class, **zero false NO-GOs**):

| Lake | Probe verdict | CLAUDE.md class |
|---|---|---|
| AHL | (a) explicit goalie event + clock | explicit `goalie_change` ✔ |
| Liiga | (a) explicit goalie event + clock | explicit ✔ |
| EIHL | (a) explicit goalie event + clock | explicit ✔ |
| NHL | (b) on-ice / lineup lists | on-ice data ✔ (conservative) |
| KHL | (b) on-ice / lineup lists | dual-channel on-ice ✔ |
| SHL | (b) on-ice / lineup lists | dual GK channels — **understated**, safe direction |
| Mestis | (b) on-ice / lineup lists | scoped rows + on-ice ✔ |

Gate suite after the change: **31 passed, 4 skipped** (skips are unmounted
AHL/Liiga/KHL lakes only).

## 5. Open questions for the Manager / Seb

1. **Who runs the probe?** It needs Seb's PC or the Ubuntu server. Nothing
   else in Round 1 can start until it has run.
2. **Is a DEL egress allowlist entry possible?** If `www.penny-del.org` and
   the hockeydata hosts were added to the environment's egress policy, this
   and every future DEL session could do discovery directly instead of
   round-tripping through Seb. Worth asking before the KHL-sized bulk fetch.
3. **Id space.** The MagentaSport game ids on the DEL homepage (`432379`,
   `432252`, `432080`) may or may not be the stats system's id space. The
   probe collects ids from both shapes; the reconciliation is Round 2.
4. **The market question is unchanged and unasked here.** Round 1 is a
   source-capability question only. Whether DEL has an odds market at all is
   a separate check before any pricing ambition (ruling 5 doctrine).

## 6. Scope fence honoured

No adapter, no gap logic, no instances, no ledger, no numbers about coaches
or pull rates. No lake branch was created, because there is no lake yet.
`docs/DEL_SOURCE.md` exists as a stub carrying only labelled leads — it will
become the real source contract when the probe returns bytes.
