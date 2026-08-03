"""
probe_tilastopalvelu.py — OPTIONAL probe v4 (runs on Seb's PC)
==============================================================
Purpose unchanged: does the federation Tulospalvelu carry Mestis game
data (with coaches)? v3 found the /ih/serie/ SPA and its AJAX layer
(MainHelpersPath + getGames.php POST, gamecentre pages). v3 also found a
hint AGAINST: the scoreboard special-cases Mestis (StatGroupID 5563
checks, clicks open mestis.fi externally). v4 settles it:

  1. Fetch the serie app's own JS (js/ui.js, js/statgroup.js, js/main.js
     relative to /ih/serie/ — different builds than the root page's).
  2. Regex MAINPATH / MainHelpersPath / GAMECENTREPATH / season-source
     out of the fetched JS at runtime.
  3. POST getGames.php with a few payloads (a known Mestis game day,
     2025-01-11, and a Liiga-era Saturday) and save the JSON verbatim.

FETCH-ONLY, <=12 requests, 1s apart, everything saved to probe_out/.
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
           "Referer": "https://tilastopalvelu.fi/ih/serie/"}


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


def get(path, post=None, tag=None):
    url = BASE + path
    data = urlencode(post).encode() if post else None
    try:
        got = opener.open(Request(url, data=data, headers=HEADERS),
                          timeout=30).read()
        tag = tag or re.sub(r"\W+", "_", path.split("?")[0])[:60]
        (out / f"v4_{tag}.txt").write_bytes(got)
        low = got.lower()
        print(f"OK  {len(got):>8} B  {'POST' if post else 'GET '} {path}"
              f"{'  data=' + str(post) if post else ''}")
        print(f"    'mestis': {b'mestis' in low}   "
              f"'valmentaja'/'coach': "
              f"{b'valmentaja' in low or b'coach' in low}")
        return got
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}  {path}")
        return None
    finally:
        time.sleep(1.0)


# 1) the serie app's own JS builds
js = {}
for name in ("ui", "statgroup", "main", "lang"):
    got = get(f"/ih/serie/js/{name}.js", tag=f"serie_js_{name}")
    if got:
        js[name] = got.decode("utf-8", "replace")

# 2) extract the real paths from the fetched JS
blob = "\n".join(js.values())
finds = {}
for var in ("MAINPATH", "MainHelpersPath", "GAMECENTREPATH",
            "MobileHelpersPath", "SeasonNumber"):
    for m in re.finditer(var + r"\s*=\s*([^;\n]+)", blob):
        finds.setdefault(var, []).append(m.group(1).strip()[:100])
print("\nExtracted path variables:")
for k, v in finds.items():
    print(f"  {k} = {v}")

# every .php mentioned anywhere in the serie JS
phps = sorted(set(re.findall(r"['\"]([^'\"]*\.php[^'\"]*)['\"]", blob)))
print("  .php refs:", phps[:25])

# 3) live getGames.php attempts — helpers path best guess: /ih/helpers/
for helpers in ("/ih/helpers/", "/ih/serie/helpers/"):
    ok = get(helpers + "getGames.php",
             post={"season": 2025, "stgid": 0, "teamid": 0,
                   "districtid": -1, "gamedays": -1, "dog": "2025-01-11"},
             tag=f"getGames_{helpers.strip('/').replace('/', '_')}")
    if ok and len(ok) > 50:
        break

print("\nDone. Paste this output back to the Mestis session; the session "
      "reads probe_out/v4_*.txt directly.")
