#!/usr/bin/env python3
"""
fetch_del_raw.py — DEL (PENNY DEL) ROUND 2 lake fetcher.
STDLIB ONLY. Runs on Seb's Windows PC or the Ubuntu server.

Round 1 is ANSWERED (ruling 51): DEL is capability (a) — explicit
`Torhüter aus dem Tor` / `Torhüter ins Tor` events on a cumulative game
clock. This script does NOT re-litigate that. It builds the lake.

WHY THIS EXISTS AND WEBFETCH DOES NOT REPLACE IT
WebFetch answered the capability question, but it returns model-summarised
markdown. A lake needs VERBATIM BYTES plus a sha256 manifest, which is what
this writes. Every response is saved byte-for-byte, never edited, never
pretty-printed.

CONFIRMED URL CONTRACT (rulings 51 + 53 — do not guess around this)
  season schedule : /statistik/saison-{YYYY-YY}/hauptrunde/spielplan
                    ...MONTH-PAGINATED. Serves ONE month by default.
  game detail     : /statistik/spieldetails/{DDMMYYYY}_{home}_gg_{away}_{gameid}
                    ...ONE page per game. The tabs are the same page.

THE TWO DEFECTS THIS VERSION FIXES (ruling 53, found in Seb's sampled bytes)
1. The schedule is month-paginated, so the first version captured the default
   month and called it a season: 41 games for 2022-23, every one of them
   September 2022. --full would have shipped a lake holding ~10% of the
   league that looked complete. Fixed: the month mechanism is discovered at
   runtime and every month is fetched, with a structural completeness check
   (games/team derived from the fixture clubs) that refuses to call a
   one-month season done.
2. The four tabs returned byte-identical pages -- the old check compared HTTP
   status, not content, so five copies of one page passed as five channels.
   Fixed: one page per game, ~247 KB not ~1.07 MB.

Both defects share one root cause worth remembering on the next league: HTTP
200 means the server answered, not that it answered the question you asked.
Validate by CONTENT.

MODES
  python fetch_del_raw.py --schedule                  # fixtures per season
  python fetch_del_raw.py --reconcile                 # 0/0 both directions
  python fetch_del_raw.py --sample 10                 # SIZE PROJECTION first
  python fetch_del_raw.py --full                      # build the lake
  python fetch_del_raw.py --verify                    # re-hash AFTER transfer
Add --seasons 2022-23,2023-24,2024-25,2025-26 to any of them.

ORDER OF OPERATIONS IS NOT OPTIONAL: --schedule, then --reconcile, then
--sample (report the projection to the Manager and WAIT), then --full.
Output: tools/del_lake/{season}/... + SHA256SUMS.txt per season.
"""
import argparse, csv, hashlib, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from del_round1_probe import fetch, scan_tokens, discover  # rule 15: one impl

LAKE = os.path.join(HERE, "del_lake")
BASE = "https://www.penny-del.org"
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]
# Kept for the record only -- ruling 53 proved these are NOT separate
# channels: the server returns the identical shell for every one and
# DataTables hydrates them in the browser. They are never fetched.
TABS_NOT_FETCHED = ["aufstellung", "spielerstats", "schuesse", "bullies"]

# the confirmed game-detail shape, used both to build and to recognise URLs
RE_GAME = re.compile(
    r"/statistik/spieldetails/(\d{8})_([A-Za-z0-9\-]+)_gg_([A-Za-z0-9\-]+)_(\d+)")


def sched_url(season):
    return "%s/statistik/saison-%s/hauptrunde/spielplan" % (BASE, season)


# ---------------------------------------------------------- month pagination
# DEFECT 1 (ruling 53): the schedule page is MONTH-PAGINATED and serves one
# month by default. The first version of this fetcher took that default as
# the whole season -- 41 games for 2022-23, all of them September 2022 -- and
# --full would have built a lake holding ~10% of the league while looking
# complete. The paging mechanism is NOT in the static HTML, so it is
# discovered at runtime.
#
# THE TRAP, and it is the same one as Defect 2: an ignored query parameter
# still returns HTTP 200 with the default month. So a candidate shape is
# only accepted when the RESPONSE CONTENT DIFFERS and it yields fixtures the
# default page did not have. Status codes prove nothing here.
MONTHS_DE = ["januar", "februar", "märz", "maerz", "april", "mai", "juni",
             "juli", "august", "september", "oktober", "november", "dezember"]
MONTH_NUM = {"januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
             "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
             "oktober": 10, "november": 11, "dezember": 12}
RE_OPTION = re.compile(
    r"<option[^>]*value=[\"']([^\"']*)[\"'][^>]*>\s*([^<]{3,40}?)\s*</option>", re.I)
# parameter names to try, cheapest/likeliest first
MONTH_PARAMS = ["monat", "month", "m", "spieltag", "page", "date", "zeitraum"]


def parse_month_options(data):
    """(value, label) for every <option> whose label names a German month."""
    out = []
    for value, label in RE_OPTION.findall(data.decode("utf-8", "replace")):
        low = label.lower()
        if any(mn in low for mn in MONTHS_DE):
            out.append((value, label.strip()))
    return out


def synth_month_values(season):
    """Fallback when the selector is JS-built: a DEL season runs Sep..Mar.
    Returns [(YYYY-MM, 'YYYY-MM'), ...] spanning that range, derived from the
    season slug rather than typed from memory."""
    y1 = int("20" + season.split("-")[0][-2:]) if len(season.split("-")[0]) == 2 \
        else int(season.split("-")[0])
    out = []
    for mth in (9, 10, 11, 12):
        out.append(("%04d-%02d" % (y1, mth),) * 2)
    for mth in (1, 2, 3, 4):
        out.append(("%04d-%02d" % (y1 + 1, mth),) * 2)
    return out


def month_of(ddmmyyyy):
    return "%s-%s" % (ddmmyyyy[4:8], ddmmyyyy[2:4])


def month_histogram(fx):
    hist = {}
    for r in fx.values():
        hist[month_of(r["date"])] = hist.get(month_of(r["date"]), 0) + 1
    return dict(sorted(hist.items()))


def completeness(fx):
    """Structural, derived-from-the-data completeness check (rule 14: never an
    absolute total). Clubs come from the fixture slugs, so games-per-team is
    computable without hardcoding league size -- which also survives
    promotion/relegation. A full DEL season is ~52 games/team; ONE MONTH is
    ~6, which is the Defect-1 signature."""
    if not fx:
        return 0, 0.0, ["no fixtures"]
    teams = set()
    for r in fx.values():
        teams.add(r["home"])
        teams.add(r["away"])
    hist = month_histogram(fx)
    gpt = (2.0 * len(fx) / len(teams)) if teams else 0.0
    warn = []
    if len(hist) <= 1:
        warn.append("ALL FIXTURES IN ONE MONTH -- this is the Defect-1 signature")
    if len(hist) < 5:
        warn.append("only %d month(s) covered; a DEL season spans ~7" % len(hist))
    if gpt < 30:
        warn.append("%.1f games/team is far below a full season (~52)" % gpt)
    return len(teams), gpt, warn


def discover_month_mechanism(season, base_data, base_url):
    """Find how to ask for a specific month. Returns (param, options) or
    (None, options). Accepts a candidate ONLY on new content + new fixtures."""
    options = parse_month_options(base_data)
    src = "page <select>"
    if not options:
        options = synth_month_values(season)
        src = "synthesised Sep..Apr (selector not in static HTML)"
    base_fx = set(parse_fixtures(base_data))
    base_hash = hashlib.sha256(base_data).hexdigest()
    print("    month options: %d (%s)" % (len(options), src))
    for param in MONTH_PARAMS:
        for value, _label in options[:4]:
            if not value:
                continue
            sep = "&" if "?" in base_url else "?"
            url = "%s%s%s=%s" % (base_url, sep, param, value)
            st, data, _u, _c = fetch(url)
            time.sleep(0.4)
            if st != "ok" or not data:
                continue
            if hashlib.sha256(data).hexdigest() == base_hash:
                continue                      # ignored param -> identical page
            new = set(parse_fixtures(data)) - base_fx
            if new:
                print("    MECHANISM FOUND: ?%s=  (value %r -> %d new games)"
                      % (param, value, len(new)))
                return param, options
    print("    NO MONTH MECHANISM FOUND by query-parameter probing.")
    return None, options


def mine_schedule_js(season, base_data):
    """Defect-1 fallback: the page drives DataTables from a JS asset. Save it
    verbatim and surface any URL-ish strings so a human can read the real
    request shape instead of guessing further."""
    srcs = re.findall(rb"""<script[^>]+src=["']([^"']+)["']""", base_data)
    hits = []
    for s in srcs:
        u = s.decode("utf-8", "replace")
        if not any(k in u.lower() for k in ("custom", "app", "main", "spielplan")):
            continue
        full = u if u.startswith("http") else (BASE + ("" if u.startswith("/") else "/") + u)
        st, data, furl, _ = fetch(full)
        time.sleep(0.3)
        if st != "ok" or not data:
            continue
        p = os.path.join(season_dir(season), "_js_" + re.sub(r"[^A-Za-z0-9._-]", "_", u)[-60:])
        write_raw(p, data)
        for m in re.findall(rb"""["'](/[A-Za-z0-9/_.\-]*(?:spielplan|ajax|api|json|data)[A-Za-z0-9/_.\-]*)["']""",
                            data, re.I):
            hits.append(m.decode("utf-8", "replace"))
        for m in re.findall(rb"""(monat|month|spieltag|zeitraum)\s*[:=]""", data, re.I):
            hits.append("param-ish: " + m.decode("utf-8", "replace"))
    return sorted(set(hits))


# Independent second lists for the reconciliation. Tried in order; the first
# that returns bytes AND yields fixtures is used. If none resolve, the script
# says so rather than reporting a fake 0/0 against itself.
def alt_urls(season):
    return [
        "%s/statistik/saison-%s/hauptrunde/ergebnisse" % (BASE, season),
        "%s/statistik/saison-%s/hauptrunde/tabelle" % (BASE, season),
        "%s/statistik/saison-%s/hauptrunde" % (BASE, season),
        "%s/spielplan?saison=%s" % (BASE, season),
    ]


def season_dir(season):
    d = os.path.join(LAKE, season)
    os.makedirs(d, exist_ok=True)
    return d


def write_raw(path, data):
    """Verbatim. No decode, no reformat, no normalisation."""
    with open(path, "wb") as f:
        f.write(data)


def parse_fixtures(data):
    """Every game-detail link, scoped to the confirmed pattern.

    TICKER LESSON: this matches the structural game-detail URL shape only.
    It never counts loose numbers off the page, which is how the Mestis
    page-wide grep inflated its counts twice.
    """
    out = {}
    for ddmmyyyy, home, away, gid in RE_GAME.findall(data.decode("utf-8", "replace")):
        out[gid] = {"game_id": gid, "date": ddmmyyyy, "home": home, "away": away,
                    "slug": "%s_%s_gg_%s_%s" % (ddmmyyyy, home, away, gid)}
    return out


def game_url(fx, tab=None, mode="path"):
    u = "%s/statistik/spieldetails/%s" % (BASE, fx["slug"])
    if not tab:
        return u
    return u + ("/" + tab if mode == "path" else "?tab=" + tab)


def fixtures_csv(season):
    return os.path.join(LAKE, "fixtures_%s.csv" % season)


def load_fixtures(season):
    p = fixtures_csv(season)
    if not os.path.exists(p):
        return {}
    with open(p, newline="", encoding="utf-8") as f:
        return {r["game_id"]: r for r in csv.DictReader(f)}


def save_fixtures(season, fx):
    os.makedirs(LAKE, exist_ok=True)
    with open(fixtures_csv(season), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["game_id", "date", "home", "away", "slug"])
        w.writeheader()
        for gid in sorted(fx, key=lambda x: int(x)):
            w.writerow(fx[gid])


# ---------------------------------------------------------------- stages
def do_schedule(seasons):
    """Fixture discovery ACROSS ALL MONTHS (Defect 1 fix, ruling 53)."""
    print("\n=== SCHEDULE: fixture discovery (month-aware) ===")
    total, incomplete, failed = 0, [], []
    for s in seasons:
        base_url = sched_url(s)
        st, data, url, _ = fetch(base_url)
        if st != "ok" or not data:
            print("  %-8s FETCH FAILED (%s) %s" % (s, st, url))
            failed.append(s)
            continue
        d = season_dir(s)
        write_raw(os.path.join(d, "_spielplan.html"), data)
        fx = parse_fixtures(data)
        print("  %-8s default page: %d games" % (s, len(fx)))
        if not fx:
            print("           NO FIXTURES PARSED -- page is probably JS-hydrated.")
            print("           Find the real feed in the browser network tab and")
            print("           report the URL. Do NOT scrape rendered text.")

        param, options = discover_month_mechanism(s, data, base_url)
        if param:
            for value, label in options:
                if not value:
                    continue
                sep = "&" if "?" in base_url else "?"
                murl = "%s%s%s=%s" % (base_url, sep, param, value)
                mst, mdata, _u, _c = fetch(murl)
                time.sleep(0.5)
                if mst != "ok" or not mdata:
                    print("    %-18s FETCH FAILED (%s)" % (label, mst))
                    continue
                write_raw(os.path.join(d, "_spielplan_%s.html"
                                       % re.sub(r"[^A-Za-z0-9_-]", "_", str(value))), mdata)
                before = len(fx)
                fx.update(parse_fixtures(mdata))
                print("    %-18s +%d  (running %d)" % (label, len(fx) - before, len(fx)))
        else:
            js_hits = mine_schedule_js(s, data)
            print("    JS assets saved. URL-ish strings found in them:")
            for h in js_hits[:20] or ["    (none)"]:
                print("      %s" % h)
            print("    ACTION: read those, or open the page and watch the")
            print("    network tab while changing the month selector, then")
            print("    add the real shape to MONTH_PARAMS.")

        save_fixtures(s, fx)
        total += len(fx)
        nteams, gpt, warn = completeness(fx)
        hist = month_histogram(fx)
        print("    -> %d games | %d clubs | %.1f games/team" % (len(fx), nteams, gpt))
        print("       by month: %s" % (hist or "-"))
        for w in warn:
            print("       *** INCOMPLETE: %s" % w)
        if warn:
            incomplete.append(s)
        time.sleep(1.0)

    ok_seasons = [s for s in seasons if s not in failed and s not in incomplete
                  and load_fixtures(s)]
    print("\n  TOTAL %d games across %d/%d seasons"
          % (total, len(ok_seasons), len(seasons)))
    if failed:
        # never let a failed fetch read as a pass -- that is the Defect-3
        # failure mode (a broken number that looks precise)
        print("  *** FETCH FAILED, nothing checked: %s" % ", ".join(failed))
    if incomplete:
        print("  *** DO NOT RUN --full. Seasons flagged incomplete: %s"
              % ", ".join(incomplete))
        print("  *** A season served one month at a time looks complete and is")
        print("      not. Fix discovery first, then re-run --schedule.")
    if ok_seasons and not failed and not incomplete:
        print("  All %d seasons pass the structural completeness check."
              % len(ok_seasons))
    elif not ok_seasons:
        print("  NO season passed. Nothing to fetch; do not proceed to --full.")
    print("  Report the REAL depth. A season genuinely absent from the archive")
    print("  is reported as absent; a season we only partly fetched is NOT.")


def do_reconcile(seasons):
    """0/0 both directions against an INDEPENDENT list (KHL/SHL standard)."""
    print("\n=== RECONCILE: schedule vs independent list ===")
    for s in seasons:
        primary = load_fixtures(s)
        if not primary:
            print("  %-8s no fixtures yet -- run --schedule first" % s)
            continue
        alt, used = {}, None
        for u in alt_urls(s):
            st, data, furl, _ = fetch(u)
            if st == "ok" and data:
                cand = parse_fixtures(data)
                if cand:
                    alt, used = cand, furl
                    d = season_dir(s)
                    write_raw(os.path.join(d, "_reconcile_source.html"), data)
                    break
            time.sleep(0.6)
        if not used:
            print("  %-8s NO INDEPENDENT LIST RESOLVED -- reconciliation NOT done."
                  % s)
            print("           Reporting this as unreconciled is correct; a set")
            print("           compared against itself is not a check.")
            continue
        miss_alt = sorted(set(primary) - set(alt), key=int)
        miss_pri = sorted(set(alt) - set(primary), key=int)
        flag = "OK 0/0" if not miss_alt and not miss_pri else "*** MISMATCH ***"
        print("  %-8s primary %4d | independent %4d | missing %d/%d  %s"
              % (s, len(primary), len(alt), len(miss_alt), len(miss_pri), flag))
        print("           source: %s" % used)
        if miss_alt:
            print("           in schedule, not in independent: %s" % miss_alt[:12])
        if miss_pri:
            print("           in independent, not in schedule: %s" % miss_pri[:12])


def fetch_game(season, fx, mode, manifest, refetch=False):
    """Fetch ONE page per game. Returns bytes written.

    DEFECT 2 (ruling 53): the four tabs are NOT separate channels. The server
    returns the identical shell for every tab URL and DataTables/jQuery
    hydrates them client-side -- game 2580's detail, aufstellung and
    spielerstats were byte-identical
    (a6106d4cef0ddd442a01e35555716d6879024b7eadfcf8ea583a62cd4a66dd42).
    The old code fetched five copies of one page and the tab check passed
    them because it compared HTTP STATUS, not content. So: one page per game,
    and bytes/game is ~247 KB rather than the ~1.07 MB first reported.
    Per-tab tables (goalie TOI, lineups) are simply not reachable over plain
    HTTP -- which is also why coaches are absent and the coach map stands.
    """
    d = season_dir(season)
    name = "%s_detail.html" % fx["game_id"]
    path = os.path.join(d, name)
    if os.path.exists(path) and os.path.getsize(path) > 0 and not refetch:
        return os.path.getsize(path)
    url = game_url(fx, None, mode)
    st, data, furl, _ = fetch(url)
    if st == "ok" and data:
        write_raw(path, data)
        manifest.append({"season": season, "game_id": fx["game_id"],
                         "file": name, "url": furl, "status": st,
                         "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
        return len(data)
    manifest.append({"season": season, "game_id": fx["game_id"], "file": name,
                     "url": url, "status": st, "bytes": 0, "sha256": ""})
    return 0


def channel_distinctness(paths):
    """Group files by CONTENT hash. Returns {sha256: [names]}.

    The lesson from Defect 2, generalised: a channel check must compare
    content, never status codes. Any JS-rendered source will happily return
    200 and the same shell for every 'channel' URL.
    """
    groups = {}
    for p in paths:
        try:
            with open(p, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            continue
        groups.setdefault(h, []).append(os.path.basename(p))
    return groups


def do_sample(seasons, n, mode):
    """Measure bytes/game and PROJECT the lake size. Report BEFORE --full."""
    print("\n=== SAMPLE %d: size projection + channel hunt ===" % n)
    manifest, sizes, per_season, sampled = [], [], {}, []
    for s in seasons:
        fx = load_fixtures(s)
        per_season[s] = len(fx)
        if not fx:
            continue
        for gid in sorted(fx, key=int)[:n]:
            b = fetch_game(s, fx[gid], mode, manifest)
            sizes.append(b)
            sampled.append((s, gid))
            print("  %s/%s  %8d B" % (s, gid, b))
        if sizes:
            break   # one season's sample is enough to project
    if not sizes:
        print("  nothing sampled -- run --schedule first")
        return
    avg = sum(sizes) / len(sizes)
    print("\n  bytes/game (ONE page per game): %.0f  (%.0f KB)" % (avg, avg / 1e3))

    print("\n  --- PROJECTED LAKE SIZE ---")
    # DEFECT 3 (ruling 53): the old projector multiplied only the seasons it
    # had SAMPLED, printing "0 games" for three seasons whose fixtures the
    # schedule stage had already found -- a broken number that looked precise.
    # It now counts every season with a fixture list, and says which are
    # projected from another season's average.
    total, counted = 0.0, 0
    for s in seasons:
        g = len(load_fixtures(s))
        per_season[s] = g
        if not g:
            print("    %-8s no fixture list -- run --schedule (NOT counted)" % s)
            continue
        counted += 1
        total += g * avg
        print("    %-8s %4d games x %.0f KB = %8.1f MB%s"
              % (s, g, avg / 1e3, g * avg / 1e6,
                 "" if any(x[0] == s for x in sampled) else "   (projected)"))
    print("    %-8s %d seasons %19.2f GB" % ("TOTAL", counted, total / 1e9))
    print("    (KHL was 4.14 GB. Report this to the Manager BEFORE --full.)")

    inc = [s for s in seasons if load_fixtures(s) and completeness(load_fixtures(s))[2]]
    if inc:
        print("    *** projection is meaningless for %s: fixtures incomplete"
              % ", ".join(inc))

    print("\n  --- SECOND AUDIT CHANNEL HUNT (Round-2 deliverable 5a) ---")
    hunt_channels(seasons, sampled)

    print("\n  --- EN MARKERS ON GOALS (Round-2 deliverable 5c) ---")
    hunt_en(seasons, sampled)
    write_manifest(manifest)


def hunt_channels(seasons, sampled):
    """Is there ANY independent recorder to audit the adapter against?

    Ruling 53 settled the tab question: they are the same page five times, so
    they are not fetched any more and cannot be a second channel. What is
    still worth re-checking on every sample is whether the detail page embeds
    a JSON blob or a hockeydata feed (host / apiKey / divisionId).
    """
    paths = [os.path.join(season_dir(s), "%s_detail.html" % gid)
             for s, gid in sampled[:5]]
    paths = [p for p in paths if os.path.exists(p)]
    f = discover(paths)
    if f["hosts"] or f["apikeys"] or f["divisions"]:
        print("    embedded feed found: hosts=%s apiKey=%s divisionId=%s"
              % (sorted(f["hosts"])[:3], sorted(f["apikeys"])[:2],
                 sorted(f["divisions"])[:3]))
        print("    ^ CANDIDATE INDEPENDENT CHANNEL -- fetch it and compare")
        print("      goalie timings against the detail page's event table.")
        return
    # look for any inline JSON payload big enough to be a game feed
    for p in paths:
        with open(p, "rb") as fh:
            b = fh.read()
        for m in re.findall(rb"""(\{[^{}]{400,}\})""", b)[:1]:
            print("    inline JSON-ish blob in %s (%d B) -- inspect it"
                  % (os.path.basename(p), len(m)))
            return
    print("    NO independent channel found (matches ruling 53: no embedded")
    print("    JSON, no hockeydata/apiKey/divisionId in the bytes).")
    print("    Ruling 52 stands: THE LAKE PROCEEDS. This is an adapter-stage")
    print("    blocker -- full bytes are what make it solvable, or provably")
    print("    unsolvable, in which case the audit is scoped and the limit")
    print("    stated (the SHL-2023 precedent).")


def hunt_en(seasons, sampled):
    any_en = False
    for s, gid in sampled[:5]:
        p = os.path.join(season_dir(s), "%s_detail.html" % gid)
        if not os.path.exists(p):
            continue
        h = scan_tokens(p)
        if "EMPTYNET" in h:
            any_en = True
            print("    %s/%s EN marker: %s" % (s, gid, h["EMPTYNET"][0][1][:160]))
    if not any_en:
        print("    No empty-net marker found on any sampled goal row.")
        print("    Ruling 51 expects this. Confirm it and record it: it costs")
        print("    the adapter one cross-check (EN goals cannot corroborate")
        print("    the pull interval), it does NOT change the (a) verdict.")


def do_full(seasons, mode, refetch):
    print("\n=== FULL FETCH ===")
    manifest = []
    for s in seasons:
        fx = load_fixtures(s)
        if not fx:
            print("  %-8s no fixtures -- run --schedule first" % s)
            continue
        print("  %s: %d games" % (s, len(fx)))
        for i, gid in enumerate(sorted(fx, key=int), 1):
            fetch_game(s, fx[gid], mode, manifest, refetch)
            if i % 25 == 0:
                print("    %d/%d" % (i, len(fx)))
        write_sha256(s)
    write_manifest(manifest)
    print("\n  Lake built. Now: commit .gitattributes FIRST (containing '* -text'),")
    print("  then the bytes, then run --verify AFTER transfer and record the result.")


def write_sha256(season):
    d = season_dir(season)
    rows = []
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if os.path.isfile(p) and fn != "SHA256SUMS.txt":
            with open(p, "rb") as f:
                rows.append("%s  %s" % (hashlib.sha256(f.read()).hexdigest(), fn))
    with open(os.path.join(d, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    print("    %s: SHA256SUMS.txt written (%d files)" % (season, len(rows)))


def do_verify(seasons):
    """Re-hash AFTER transfer. This is the step the CRLF incident exists for."""
    print("\n=== VERIFY: re-hash after transfer ===")
    allok = True
    for s in seasons:
        d = os.path.join(LAKE, s)
        man = os.path.join(d, "SHA256SUMS.txt")
        if not os.path.exists(man):
            print("  %-8s no SHA256SUMS.txt" % s)
            continue
        bad = miss = n = 0
        for line in open(man, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            want, fn = line.split("  ", 1)
            p = os.path.join(d, fn)
            n += 1
            if not os.path.exists(p):
                miss += 1
                continue
            with open(p, "rb") as f:
                if hashlib.sha256(f.read()).hexdigest() != want:
                    bad += 1
                    print("    MISMATCH %s (CRLF damage? .gitattributes '* -text')" % fn)
        ok = not bad and not miss
        allok &= ok
        print("  %-8s %d/%d bit-exact  missing=%d  %s"
              % (s, n - bad - miss, n, miss, "OK" if ok else "*** FAIL ***"))
    print("  RESULT: %s" % ("all seasons bit-exact" if allok else "FAILURES ABOVE"))


def write_manifest(manifest):
    if not manifest:
        return
    os.makedirs(LAKE, exist_ok=True)
    p = os.path.join(LAKE, "manifest.csv")
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["season", "game_id", "file", "url",
                                          "status", "bytes", "sha256"])
        if new:
            w.writeheader()
        w.writerows(manifest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default=",".join(SEASONS))
    ap.add_argument("--schedule", action="store_true")
    ap.add_argument("--reconcile", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--refetch", action="store_true")
    a = ap.parse_args()
    seasons = [s.strip() for s in a.seasons.split(",") if s.strip()]
    os.makedirs(LAKE, exist_ok=True)

    if not any([a.schedule, a.reconcile, a.sample, a.full, a.verify]):
        ap.print_help()
        print("\nStart with --schedule, then --reconcile, then --sample 10,")
        print("report the projection, and only then --full.")
        return 0
    if a.schedule:
        do_schedule(seasons)
    if a.reconcile:
        do_reconcile(seasons)
    if a.sample:
        do_sample(seasons, a.sample, "path")
    if a.full:
        do_full(seasons, "path", a.refetch)
    if a.verify:
        do_verify(seasons)
    return 0


if __name__ == "__main__":
    sys.exit(main())
