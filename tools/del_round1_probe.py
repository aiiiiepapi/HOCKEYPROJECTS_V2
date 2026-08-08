#!/usr/bin/env python3
"""
del_round1_probe.py — DEL (PENNY DEL) ROUND 1 CAPABILITY BAR probe.
STDLIB ONLY. Runs on Seb's Windows PC or the Ubuntu server: the cloud
workspace's egress proxy returns 403 CONNECT for www.penny-del.org,
www.hockeydata.net and apidocs.hockeydata.net, so no cloud session can
answer the capability question (verified 2026-08-08).

ROUND 1 IS ANSWERED (ruling 51, 2026-08-08): DEL is capability (a) —
explicit `Torhüter aus dem Tor` / `Torhüter ins Tor` events on a cumulative
game clock. This script's original job is therefore DONE. It is kept and
still runs because:
  - its detector is a calibrated, gated triage tool for the NEXT league
    (test_del_probe_detector_never_false_no_go), and
  - it writes VERBATIM BYTES with a sha256 manifest, which WebFetch cannot.
For the DEL lake itself use tools/fetch_del_raw.py, which implements the
confirmed URL contract end to end.

THE LADDER it triages against:
  (a) explicit goalie-out/goalie-in events with a clock   -> best
  (b) on-ice player lists per goal (KHL-style)            -> workable
  (c) per-game goalie TOI totals (Magnus-style)           -> weakest
  (d) an "empty net" flag on goals only                   -> NO-GO, stop
It does NOT decide: it saves raw bytes and prints WHERE the evidence is, so
the answer is hand-verified from bytes (rule 2; rule 4).

FETCH-ONLY. It classifies nothing, edits nothing, pretty-prints nothing.
Every response is written verbatim, byte for byte, with a sha256 manifest.

Per-game probing now uses the CONFIRMED pattern from ruling 51:
  /statistik/spieldetails/{DDMMYYYY}_{home}_gg_{away}_{gameid}  + tabs
The earlier guessed LOS REST paths and /spielbericht/{id} shapes are RETIRED.
Stage 2 still mines the widget JavaScript, because an embedded hockeydata
feed is a live candidate for the second audit channel the adapter needs.

USAGE
  python del_round1_probe.py                      # stages 1-2 + 4 (discovery)
  python del_round1_probe.py --games 12092025_ingolstadt_gg_iserlohn_3947
  python del_round1_probe.py --games-file slugs.txt
Output: tools/del_probe/  (raw/, manifest.csv, PROBE_REPORT.txt)

Re-runnable: existing non-empty raw files are skipped unless --refetch.
"""
import argparse, csv, hashlib, os, re, sys, time
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "del_probe")
RAW = os.path.join(OUT, "raw")
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

# ---- Stage 1 seeds. The saison-*/hauptrunde/spielplan shape is CONFIRMED
# (ruling 51); the rest stay as discovery surface.
SEEDS = [
    ("home",           "https://www.penny-del.org/"),
    ("spielplan_2526", "https://www.penny-del.org/statistik/saison-2025-26/hauptrunde/spielplan"),
    ("spielplan_2425", "https://www.penny-del.org/statistik/saison-2024-25/hauptrunde/spielplan"),
    ("toi_2025_26",    "https://www.penny-del.org/statistik/saison-2025-26/hauptrunde/playerstats/toi"),
    ("stats_2025_26",  "https://www.penny-del.org/statistik/saison-2025-26/hauptrunde"),
]

# ---- Stage 4 capability tokens. German AND English: the DEL feed may be either.
# Each token is a tuple of WORD PARTS. Parts are matched with any separator or
# none between them, case-insensitively, so one entry covers goalie_change,
# goalieChange, goalie-change and "goalie change" alike. This is not cosmetic:
# the first version of this table used literal strings, missed the AHL feed's
# real `goalie_change` / `goalie_out_id` keys, and produced a FALSE (d) NO-GO
# on a source we know is explicit-event class. A false NO-GO kills an adapter
# that should have been built, so the matcher is deliberately separator-blind.
TOKENS = {
    "GOALIE_EVENT": [  # (a) the go/no-go
        ("goalie", "change"), ("goalkeeper", "change"), ("keeper", "change"),
        ("goalie", "out"), ("goalie", "in"), ("goalkeeper", "out"),
        ("goalkeeper", "in"), ("keeper", "out"), ("goalie", "pull"),
        ("goalie", "pulled"), ("torwart", "wechsel"), ("torhueter", "wechsel"),
        ("torhüter", "wechsel"), ("goalie", "sub"), ("goalkeeper", "sub"),
        ("torwart", "raus"), ("torwart", "rein"), ("tor", "wechsel"),
    ],
    "GOALIE_ANY": [
        ("goalkeeper",), ("goalie",), ("torwart",), ("torhueter",),
        ("torhüter",), ("keeper",),
    ],
    "ONICE": [  # (b)
        ("on", "ice"), ("players", "on", "ice"), ("eisspieler",),
        ("auf", "dem", "eis"), ("lineup",), ("aufstellung",), ("roster",),
    ],
    "TOI": [  # (c)
        ("toi",), ("time", "on", "ice"), ("eiszeit",), ("playing", "time"),
    ],
    "EMPTYNET": [  # (d) alone = NO-GO
        ("empty", "net"), ("leeres", "tor"), ("ohne", "torwart"), ("en", "goal"),
    ],
    "PBP": [
        ("play", "by", "play"), ("spielverlauf",), ("ticker",), ("events",),
        ("event", "list"), ("game", "events"), ("liveticker",),
    ],
    "GOALS": [
        ("goals",), ("tore",), ("torschuetze",), ("torschütze",), ("scorer",),
        ("strength",), ("power", "play"), ("shorthanded",), ("ueberzahl",),
        ("überzahl",), ("unterzahl",),
    ],
    "PENALTY": [
        ("penalt",), ("strafe",), ("strafzeit",), ("penalty", "minutes"),
        ("strafminuten",), ("vergehen",),
    ],
    "PENALTY_END": [  # explicit ends = Liiga/SHL class
        ("end", "time"), ("penalty", "end"), ("expiry",), ("until",),
    ],
    "COACH": [
        ("coach",), ("trainer",), ("head", "coach"), ("cheftrainer",),
    ],
    "OT_SO": [
        ("overtime",), ("verlaengerung",), ("verlängerung",), ("shootout",),
        ("penaltyschiessen",), ("penaltyschießen",), ("gws",),
    ],
    "CLOCK": [
        ("game", "time"), ("spielzeit",), ("minute",), ("period",),
        ("drittel",), ("abschnitt",), ("clock",),
    ],
}

_SEP = r"[\s_\-\"']*"


def _compile(parts):
    """goalie+change -> matches goalie_change / goalieChange / 'goalie change'.
    A short trailing part gets a word boundary so ('toi',) does not hit
    'toilet' and ('goalie','in') does not hit 'goalieinjury'."""
    pat = _SEP.join(re.escape(p) for p in parts)
    if len(parts[-1]) <= 4:
        pat += r"\b"
    return re.compile(pat, re.I)


TOKEN_RE = {g: [(t, _compile(t)) for t in toks] for g, toks in TOKENS.items()}


def fetch(url, timeout=40):
    """Return (status, bytes, final_url, content_type). Never raises."""
    req = urllib.request.Request(url, headers=UA)
    last = "error"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return "ok", r.read(), r.geturl(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            if e.code in (404, 403, 401):
                return str(e.code), body, url, ""
            last = str(e.code)
        except Exception as e:
            last = "err:%s" % type(e).__name__
        time.sleep(1.5 * (attempt + 1))
    return last, b"", url, ""


def save(name, url, status, data, ctype, manifest):
    """Write raw bytes VERBATIM and record them. No edits, ever."""
    os.makedirs(RAW, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:120]
    path = os.path.join(RAW, safe)
    if data:
        with open(path, "wb") as f:
            f.write(data)
    manifest.append({
        "name": safe, "url": url, "status": status, "bytes": len(data),
        "content_type": ctype,
        "sha256": hashlib.sha256(data).hexdigest() if data else "",
    })
    print("  [%s] %-42s %8d B  %s" % (status, safe, len(data), url))
    return path if data else None


def already(name):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:120]
    p = os.path.join(RAW, safe)
    return p if os.path.exists(p) and os.path.getsize(p) > 0 else None


# ------------------------------------------------------------------ discovery
RE_SCRIPT = re.compile(rb"""<script[^>]+src=["']([^"']+)["']""", re.I)
RE_HDHOST = re.compile(rb"""https?://[A-Za-z0-9.\-]*hockeydata[A-Za-z0-9.\-]*""", re.I)
RE_APIKEY = re.compile(rb"""apiKey["'\s:=]+([A-Za-z0-9\-_]{8,})""", re.I)
RE_DIVID = re.compile(rb"""divisionId["'\s:=]+(\d+)""", re.I)
RE_GAMEID = re.compile(rb"""gameId["'\s:=]+(\d+)""", re.I)
RE_URLISH = re.compile(rb"""["'](/(?:rest|api|los|v\d)[A-Za-z0-9/_.{}$\-]*)["']""")
RE_NUMLINK = re.compile(rb"""/(?:spiel|game|spielbericht|gamereport)[/_-]?(\d{4,8})""", re.I)
# the confirmed game-detail slug (ruling 51)
RE_SLUG = re.compile(r"^\d{8}_[A-Za-z0-9\-]+_gg_[A-Za-z0-9\-]+_\d+$")
RE_SLUGLINK = re.compile(
    rb"""/statistik/spieldetails/(\d{8}_[A-Za-z0-9\-]+_gg_[A-Za-z0-9\-]+_\d+)""")


def discover(paths):
    """Pull config + endpoint shapes out of whatever we actually downloaded."""
    found = {"hosts": set(), "apikeys": set(), "divisions": set(),
             "gameids": set(), "urlish": set(), "scripts": set()}
    for p in paths:
        if not p:
            continue
        try:
            with open(p, "rb") as f:
                b = f.read()
        except Exception:
            continue
        for m in RE_HDHOST.findall(b):
            found["hosts"].add(m.decode("utf-8", "replace"))
        for m in RE_APIKEY.findall(b):
            found["apikeys"].add(m.decode("utf-8", "replace"))
        for m in RE_DIVID.findall(b):
            found["divisions"].add(m.decode("utf-8", "replace"))
        # prefer full spieldetails slugs: they are directly fetchable under
        # the confirmed pattern, whereas a bare numeric id is not
        for m in RE_SLUGLINK.findall(b):
            found["gameids"].add(m.decode("utf-8", "replace"))
        for m in RE_GAMEID.findall(b) + RE_NUMLINK.findall(b):
            found["gameids"].add(m.decode("utf-8", "replace"))
        for m in RE_URLISH.findall(b):
            found["urlish"].add(m.decode("utf-8", "replace"))
        for m in RE_SCRIPT.findall(b):
            s = m.decode("utf-8", "replace")
            if "hockeydata" in s.lower() or "los" in s.lower() or "widget" in s.lower():
                found["scripts"].add(s)
    return found


def absolutize(src, base="https://www.penny-del.org"):
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    if src.startswith("/"):
        return base + src
    return base + "/" + src


# --------------------------------------------------------------- channel check
def channel_groups(paths):
    """Group saved files by CONTENT hash -> {sha256: [names]}."""
    groups = {}
    for p in paths:
        if not p:
            continue
        try:
            with open(p, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            continue
        groups.setdefault(h, []).append(os.path.basename(p))
    return groups


def report_channel_distinctness(paths):
    """Are these URLs actually DIFFERENT channels?

    RULING 53, portfolio-wide lesson. The first version of this probe called
    the DEL tabs "10/10 ok" because it checked HTTP STATUS. They were the
    same page five times over (game 2580: detail, aufstellung and
    spielerstats all sha256 a6106d4c...), client-side rendered by DataTables.
    A status code says the server answered, not that it answered the question
    you asked. Any JS-rendered source will spring the same trap, so the check
    is content-based and lives here rather than in the DEL fetcher.
    """
    groups = channel_groups(paths)
    if not groups:
        return groups
    dupes = {h: n for h, n in groups.items() if len(n) > 1}
    print("    channels: %d URL(s) -> %d DISTINCT document(s)"
          % (sum(len(v) for v in groups.values()), len(groups)))
    for h, names in sorted(dupes.items(), key=lambda kv: -len(kv[1])):
        print("      IDENTICAL BYTES (%s...): %s" % (h[:12], ", ".join(sorted(names))))
        print("      ^ NOT separate channels. Fetch one and move on.")
    if not dupes:
        print("      all distinct -- these are genuinely separate documents")
    return groups


# ------------------------------------------------------------------ capability
def scan_tokens(path, max_hits=3):
    """Return {group: [(token, verbatim_line)]} for one saved file."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return {}
    text = raw.decode("utf-8", "replace")
    hits = {}
    for group, toks in TOKEN_RE.items():
        got = []
        for parts, rx in toks:
            m = rx.search(text)
            if not m:
                continue
            # a window around the match, so a minified one-line feed still
            # yields a quotable fragment rather than one 2 MB "line"
            start, end = max(0, m.start() - 90), min(len(text), m.end() + 150)
            frag = re.sub(r"\s+", " ", text[start:end]).strip()
            got.append((" ".join(parts), frag))
            if len(got) >= max_hits:
                break
        if got:
            hits[group] = got
    return hits


def verdict(all_hits):
    """Map observed evidence onto the kickoff's (a)/(b)/(c)/(d) ladder.

    TRIAGE ONLY -- it points at bytes to read, it does not decide anything.
    Deliberately biased AGAINST returning NO-GO: a false NO-GO kills an
    adapter that should have been built, while a false GO costs one hand
    check of the raw file. Both failure modes were observed while building
    this (the AHL feed and the NHL feed each returned a false NO-GO from an
    earlier, stricter version of this function).
    """
    g = set()
    for h in all_hits.values():
        g.update(h.keys())
    if "GOALIE_EVENT" in g and "CLOCK" in g:
        return "(a) EXPLICIT GOALIE EVENT + CLOCK -> GO (best case)"
    if "GOALIE_EVENT" in g:
        return "(a?) goalie-event words but NO clock token -- read the bytes"
    if "ONICE" in g:
        return "(b) ON-ICE / LINEUP LISTS -> likely GO (KHL-style inference)"
    if "TOI" in g and "GOALIE_ANY" in g:
        return "(c) GOALIE TOI ONLY -> WEAK GO (Magnus-style, extra GT class)"
    # (d) only counts when it is genuinely the ONLY goalie signal present
    if "EMPTYNET" in g and not ({"ONICE", "TOI", "GOALIE_EVENT"} & g):
        return "(d) EMPTY-NET FLAG ONLY -> *** NO-GO *** stop and report"
    if "GOALIE_ANY" in g:
        return "INCONCLUSIVE -> goalie words present but no pull evidence yet"
    return "INCONCLUSIVE -> nothing decisive found; widen discovery"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default="", help="comma-separated game ids to probe")
    ap.add_argument("--games-file", default="")
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    manifest, paths = [], []

    print("\n=== STAGE 1: seed pages (raw bytes saved verbatim) ===")
    for name, url in SEEDS:
        if not args.refetch and already(name):
            print("  [skip] %s (already have it)" % name)
            paths.append(already(name))
            continue
        st, data, furl, ct = fetch(url)
        paths.append(save(name, furl, st, data, ct, manifest))
        time.sleep(0.7)

    print("\n=== STAGE 2: discovery from what we downloaded ===")
    f = discover(paths)
    for k in ("hosts", "apikeys", "divisions", "scripts"):
        print("  %-10s %s" % (k, sorted(f[k])[:8] or "-- none --"))
    print("  gameids   %s%s" % (sorted(f["gameids"])[:10] or "-- none --",
                                " ..." if len(f["gameids"]) > 10 else ""))

    # pull the widget JS itself: it carries the real REST paths
    for i, src in enumerate(sorted(f["scripts"])[:6]):
        url = absolutize(src)
        nm = "widgetjs_%02d.js" % i
        if not args.refetch and already(nm):
            paths.append(already(nm)); continue
        st, data, furl, ct = fetch(url)
        paths.append(save(nm, furl, st, data, ct, manifest))
        time.sleep(0.5)
    f2 = discover(paths)
    if f2["urlish"]:
        print("\n  URL patterns seen inside the JS (the real feed shape):")
        for u in sorted(f2["urlish"])[:30]:
            print("    %s" % u)
    for k in ("hosts", "apikeys", "divisions"):
        f[k] |= f2[k]

    print("\n=== STAGE 3: per-game probes ===")
    ids = [x.strip() for x in args.games.split(",") if x.strip()]
    if args.games_file and os.path.exists(args.games_file):
        with open(args.games_file) as fh:
            ids += [l.strip() for l in fh if l.strip()]
    if not ids:
        ids = sorted(f["gameids"])[:5]
    if not ids:
        print("  no game ids known yet -- rerun with --games once stage 2 or the\n"
              "  network tab gives you real ids (need 5 games across >=2 seasons)")
    else:
        print("  probing: %s" % ", ".join(ids))
        # CONFIRMED pattern (ruling 51). The earlier GUESS_ LOS endpoints and
        # the /spielbericht/{id} + /spiele/{id} shapes are RETIRED: they were
        # guesses made before Round 1 was answered, and this supersedes them.
        # Pass full slugs (DDMMYYYY_home_gg_away_gameid) for the real pattern;
        # a bare numeric id can only be probed as a search fallback.
        for gid in ids:
            if RE_SLUG.match(gid):
                base = "https://www.penny-del.org/statistik/spieldetails/%s" % gid
                targets = [("game_%s_detail.html" % gid, base)] + [
                    ("game_%s_%s.html" % (gid, t), "%s/%s" % (base, t))
                    for t in ("aufstellung", "spielerstats", "schuesse", "bullies")
                ]
            else:
                print("    '%s' is not a spieldetails slug -- the confirmed"
                      " pattern needs DDMMYYYY_home_gg_away_gameid" % gid)
                continue
            got = []
            for nm, url in targets:
                if not args.refetch and already(nm):
                    p = already(nm); paths.append(p); got.append(p); continue
                st, data, furl, ct = fetch(url)
                p = save(nm, furl, st, data, ct, manifest)
                paths.append(p)
                if p:
                    got.append(p)
                time.sleep(0.5)
            report_channel_distinctness(got)

    print("\n=== STAGE 4: capability scan ===")
    all_hits = {}
    for p in paths:
        if not p:
            continue
        h = scan_tokens(p)
        if h:
            all_hits[os.path.basename(p)] = h

    lines = []
    lines.append("DEL ROUND 1 CAPABILITY PROBE")
    lines.append("Generated by tools/del_round1_probe.py (fetch-only, stdlib).")
    lines.append("Every YES below must be hand-verified against the raw bytes in")
    lines.append("tools/del_probe/raw/ before it is reported as a finding (rule 0).")
    lines.append("Files named GUESS_* are unconfirmed endpoint guesses.")
    lines.append("")
    lines.append("VERDICT (mechanical, from tokens -- CONFIRM BY HAND): %s" % verdict(all_hits))
    lines.append("")
    for fname in sorted(all_hits):
        lines.append("-" * 72)
        lines.append("FILE: %s" % fname)
        for group in sorted(all_hits[fname]):
            for tok, frag in all_hits[fname][group]:
                lines.append("  [%s] %r" % (group, tok))
                lines.append("      %s" % frag[:230])
    if not all_hits:
        lines.append("NO TOKENS MATCHED. Either nothing downloaded or the feed is")
        lines.append("JS-hydrated: open a game report in the browser, use the network")
        lines.append("tab, and rerun with the real URL.")

    report = "\n".join(lines)
    with open(os.path.join(OUT, "PROBE_REPORT.txt"), "w", encoding="utf-8") as fh:
        fh.write(report + "\n")

    if manifest:
        mp = os.path.join(OUT, "manifest.csv")
        new = not os.path.exists(mp)
        with open(mp, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=[
                "name", "url", "status", "bytes", "content_type", "sha256"])
            if new:
                w.writeheader()
            w.writerows(manifest)

    print("\n" + report[:3000])
    print("\nFull report: %s" % os.path.join(OUT, "PROBE_REPORT.txt"))
    print("Raw bytes  : %s" % RAW)
    print("\nSend the whole tools/del_probe/ folder back (or commit it to the\n"
          "del-scrape branch) -- the bytes are the evidence, not this summary.")


if __name__ == "__main__":
    sys.exit(main())
