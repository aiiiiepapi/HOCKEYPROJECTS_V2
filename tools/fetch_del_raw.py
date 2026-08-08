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

CONFIRMED URL CONTRACT (ruling 51 — do not guess around this)
  season schedule : /statistik/saison-{YYYY-YY}/hauptrunde/spielplan
  game detail     : /statistik/spieldetails/{DDMMYYYY}_{home}_gg_{away}_{gameid}
  tabs            : + /aufstellung /spielerstats /schuesse /bullies

TAB URL SHAPE IS THE ONE THING STILL UNCONFIRMED. Ruling 51 names the tabs
but not how they compose onto the detail URL. This script appends them as a
path suffix (the likeliest shape) and PRINTS THE STATUS OF EVERY TAB, so the
first real run settles it from response codes instead of from my guess. If
the tabs 404, run --sample again with --tab-mode=query.

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
TABS = ["aufstellung", "spielerstats", "schuesse", "bullies"]

# the confirmed game-detail shape, used both to build and to recognise URLs
RE_GAME = re.compile(
    r"/statistik/spieldetails/(\d{8})_([A-Za-z0-9\-]+)_gg_([A-Za-z0-9\-]+)_(\d+)")


def sched_url(season):
    return "%s/statistik/saison-%s/hauptrunde/spielplan" % (BASE, season)


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
    print("\n=== SCHEDULE: fixture discovery ===")
    total = 0
    for s in seasons:
        st, data, url, _ = fetch(sched_url(s))
        if st != "ok" or not data:
            print("  %-8s FETCH FAILED (%s) %s" % (s, st, url))
            continue
        d = season_dir(s)
        write_raw(os.path.join(d, "_spielplan.html"), data)
        fx = parse_fixtures(data)
        save_fixtures(s, fx)
        total += len(fx)
        print("  %-8s %4d games  (%d B saved)" % (s, len(fx), len(data)))
        if not fx:
            print("           NO FIXTURES PARSED -- page is probably JS-hydrated.")
            print("           Open it in a browser, find the real feed in the")
            print("           network tab, and report the URL. Do NOT scrape")
            print("           rendered text as a substitute.")
        time.sleep(1.0)
    print("  TOTAL %d games across %d seasons" % (total, len(seasons)))
    print("  NOTE: seasons that return 0 may simply not exist in the archive.")
    print("        Report the real depth; do not pad to four.")


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
    """Fetch a game's detail page + every tab. Returns bytes written."""
    d = season_dir(season)
    got = 0
    for tab in [None] + TABS:
        name = "%s_%s.html" % (fx["game_id"], tab or "detail")
        path = os.path.join(d, name)
        if os.path.exists(path) and os.path.getsize(path) > 0 and not refetch:
            got += os.path.getsize(path)
            continue
        url = game_url(fx, tab, mode)
        st, data, furl, _ = fetch(url)
        if st == "ok" and data:
            write_raw(path, data)
            got += len(data)
            manifest.append({"season": season, "game_id": fx["game_id"],
                             "file": name, "url": furl, "status": st,
                             "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
        else:
            manifest.append({"season": season, "game_id": fx["game_id"],
                             "file": name, "url": url, "status": st,
                             "bytes": 0, "sha256": ""})
        time.sleep(0.4)
    return got


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
    print("\n  bytes/game (all %d channels): %.0f  (%.2f MB)"
          % (len(TABS) + 1, avg, avg / 1e6))

    print("\n  --- TAB STATUS (settles the unconfirmed tab URL shape) ---")
    by_tab = {}
    for m in manifest:
        t = m["file"].split("_", 1)[1].replace(".html", "")
        by_tab.setdefault(t, []).append(m["status"])
    for t, sts in sorted(by_tab.items()):
        ok = sum(1 for x in sts if x == "ok")
        print("    %-14s %d/%d ok  %s" % (t, ok, len(sts),
              "" if ok else "<-- 404s: retry with --tab-mode=query"))

    print("\n  --- PROJECTED LAKE SIZE ---")
    total = 0
    for s in seasons:
        g = per_season.get(s, 0)
        total += g * avg
        print("    %-8s %4d games x %.2f MB = %7.1f MB" % (s, g, avg / 1e6, g * avg / 1e6))
    print("    %-8s %s %7.2f GB" % ("TOTAL", " " * 22, total / 1e9))
    print("    (KHL was 4.14 GB. Report this to the Manager BEFORE --full.)")

    print("\n  --- SECOND AUDIT CHANNEL HUNT (Round-2 deliverable 5a) ---")
    hunt_channels(seasons, sampled)

    print("\n  --- EN MARKERS ON GOALS (Round-2 deliverable 5c) ---")
    hunt_en(seasons, sampled)
    write_manifest(manifest)


def hunt_channels(seasons, sampled):
    """Is /spielerstats (or an embedded hockeydata feed) an INDEPENDENT
    recorder we can audit the adapter against? Reports evidence, not a verdict."""
    found = False
    for s, gid in sampled[:5]:
        p = os.path.join(season_dir(s), "%s_spielerstats.html" % gid)
        if not os.path.exists(p):
            continue
        h = scan_tokens(p)
        groups = sorted(h.keys())
        print("    %s/%s spielerstats groups: %s" % (s, gid, groups or "none"))
        if {"TOI", "GOALIE_ANY"} <= set(groups):
            found = True
            for g in ("TOI", "GOALIE_ANY"):
                print("      [%s] %s" % (g, h[g][0][1][:150]))
    # the site's own hockeydata widget feed, if it embeds one
    paths = []
    for s, gid in sampled[:5]:
        p = os.path.join(season_dir(s), "%s_detail.html" % gid)
        if os.path.exists(p):
            paths.append(p)
    f = discover(paths)
    if f["hosts"] or f["apikeys"]:
        print("    embedded hockeydata feed: hosts=%s apiKey=%s divisionId=%s"
              % (sorted(f["hosts"])[:3], sorted(f["apikeys"])[:2],
                 sorted(f["divisions"])[:3]))
        print("    ^ that is a candidate INDEPENDENT channel -- fetch it and")
        print("      compare goalie timings against the detail page.")
        found = True
    if not found:
        print("    NO independent channel evidenced yet. Say so plainly: without")
        print("    one the adapter's 0/60 random audit has nothing to compare")
        print("    against, and that is an adapter blocker (ruling 51).")


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
    ap.add_argument("--tab-mode", choices=["path", "query"], default="path")
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
        do_sample(seasons, a.sample, a.tab_mode)
    if a.full:
        do_full(seasons, a.tab_mode, a.refetch)
    if a.verify:
        do_verify(seasons)
    return 0


if __name__ == "__main__":
    sys.exit(main())
