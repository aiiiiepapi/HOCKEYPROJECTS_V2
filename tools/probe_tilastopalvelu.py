"""
probe_tilastopalvelu.py — OPTIONAL probe v6 (runs on Seb's PC)
==============================================================
v5 learned: everything lives under /ih/ (the /game/ and /gamerosters/
guesses at host root were 404s; /ih/gamerosters/index.php?season=2025&
gameid=3016 returned a live SPA shell with the gameid embedded, loading
js/gamerosters.js). leijonat.fi mirror is 403 to non-browser clients.

v6 is adaptive, still about ONE question (Mestis game sheets + coaches):
  1. Fetch /ih/gamerosters/js/gamerosters.js, extract its .php AJAX
     endpoints, call each with {gameid:3016, season:2025} (POST, then
     GET fallback) and save the responses.
  2. Fetch the gamecentre shell at /ih/game/?season=2025&gameid=3016,
     extract ITS js includes, fetch them, extract .php endpoints, call
     the report-ish ones the same way.
  3. /ih/serie/helpers/getStatGroups.php POST {season, levelid:65}.
Everything saved verbatim to probe_out/, <=20 requests, 1s apart.
Usage:  python probe_tilastopalvelu.py
"""

import re
import ssl
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPSHandler

BASE = "https://tilastopalvelu.fi"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://tilastopalvelu.fi/ih/"}
GAMEID, SEASON = 3016, 2025
budget = 20


def legacy_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    except ssl.SSLError:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    return ctx


out = Path(__file__).with_name("probe_out")
out.mkdir(exist_ok=True)
opener = build_opener(HTTPSHandler(context=legacy_ctx()))


def get(path, post=None, tag=""):
    global budget
    if budget <= 0:
        print("(request budget exhausted)")
        return None
    budget -= 1
    url = BASE + path
    data = urlencode(post).encode() if post else None
    try:
        got = opener.open(Request(url, data=data, headers=HEADERS),
                          timeout=30).read()
        (out / f"v6_{tag}.txt").write_bytes(got)
        low = got.lower()
        print(f"OK  {len(got):>8} B  {'POST' if post else 'GET '} {path}")
        print(f"    'valmentaja': {b'valmentaja' in low}  "
              f"'coach': {b'coach' in low}  "
              f"'toimihenkil': {b'toimihenkil' in low}  "
              f"'keupa': {b'keupa' in low}")
        return got
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}  {'POST' if post else 'GET'} {path}")
        return None
    finally:
        time.sleep(1.0)


def php_endpoints(js_text):
    return sorted(set(re.findall(r"['\"]([^'\"]*\.php[^'\"]*)['\"]",
                                 js_text)))


def call_endpoints(paths, prefix, tag_prefix):
    for p in paths:
        p = p.split("?")[0]
        if not p.endswith(".php"):
            continue
        full = p if p.startswith("/") else prefix + p
        tag = f"{tag_prefix}_{re.sub(r'[^A-Za-z0-9]+', '_', p)[-40:]}"
        r = get(full, post={"gameid": GAMEID, "season": SEASON}, tag=tag)
        if r is None or len(r) < 3:
            get(f"{full}?gameid={GAMEID}&season={SEASON}", tag=tag + "_get")


# 1) gamerosters JS -> endpoints
js = get(f"/ih/gamerosters/js/gamerosters.js", tag="gamerosters_js")
if js:
    eps = php_endpoints(js.decode("utf-8", "replace"))
    print("  gamerosters.js php refs:", eps)
    call_endpoints(eps, "/ih/gamerosters/", "rosters")

# 2) gamecentre shell under /ih/
shell = get(f"/ih/game/?season={SEASON}&gameid={GAMEID}&lang=fi",
            tag="gamecentre_shell")
if shell:
    stext = shell.decode("utf-8", "replace")
    includes = sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', stext)))
    print("  gamecentre js includes:", includes[:12])
    for inc in includes:
        if inc.startswith(("http", "/system", "/js/lang")):
            continue
        path = inc if inc.startswith("/") else "/ih/game/" + inc
        j = get(path.split("?")[0], tag="gc_" +
                re.sub(r"[^A-Za-z0-9]+", "_", path.split("?")[0])[-40:])
        if j:
            eps = [e for e in php_endpoints(j.decode("utf-8", "replace"))
                   if re.search(r"report|roster|game|official|event",
                                e, re.I)]
            if eps:
                print("    php refs:", eps)
                call_endpoints(eps, "/ih/game/", "gc")

# 3) statgroups via the serie app's own helpers dir
get("/ih/serie/helpers/getStatGroups.php",
    post={"season": SEASON, "levelid": 65, "districtid": 0},
    tag="statgroups")

print("\nDone. Paste this output back to the Mestis session; the session "
      "reads probe_out/v6_*.txt directly.")
