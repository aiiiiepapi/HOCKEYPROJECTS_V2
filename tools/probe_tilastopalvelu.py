"""
probe_tilastopalvelu.py — OPTIONAL probe v3 (runs on Seb's PC)
==============================================================
v2 result (2026-08-03): https://tilastopalvelu.fi/ih/ (BARE domain only,
legacy-TLS context) serves the Finnish federation's 'Leijonat -
Tulospalvelu' SPA: static shell is stale (Dec-2020 banner) but the JS
app looks maintained. Data loads client-side from backend endpoints
hidden in the JS. www. host is dead to every client tried.

v3 job: grab the SPA's JS + the /serie/ page + two candidate helper
endpoints so the session can map the backend and answer: does it carry
Mestis game sheets (with coaches)? FETCH-ONLY, 8 requests, 1s apart,
everything saved verbatim under probe_out/.

Usage:  python probe_tilastopalvelu.py
"""

import ssl
import time
from pathlib import Path
from urllib.request import Request, build_opener, HTTPSHandler

BASE = "https://tilastopalvelu.fi"          # bare domain ONLY (www is dead)
PATHS = [
    "/ih/js/main.js?2dfe07a9c25f58c97e2a0ecb54e84be4",
    "/ih/js/dev.js?0a809ca78b9aa5393c0cb7dad7eb6a3a",
    "/ih/js/ui.js?0658787985355ad576f92bf63efa2d58",
    "/ih/js/gamescoreboard.js?94cbc36b10837de1040e040b0b0b74c2",
    "/ih/serie/",
    # candidate helper endpoints seen in Finnish-hockey embeds:
    "/ih/modules/mod_schedule/helper/games.php?statgroupid=&select=all",
    "/ih/modules/mod_standings/helper/standings.php?statgroupid=",
    "/ih/modules/mod_teamsselect/helper/teams.php?statgroupid=",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://tilastopalvelu.fi/ih/"}


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

for path in PATHS:
    url = BASE + path
    stem = (path.split("?")[0].strip("/").replace("/", "_")
            .replace(".", "_") or "root")
    fname = out / f"v3_{stem}.txt"
    try:
        data = opener.open(Request(url, headers=HEADERS), timeout=30).read()
        fname.write_bytes(data)
        low = data.lower()
        print(f"OK  {len(data):>8} B  {path}")
        print(f"    'mestis': {b'mestis' in low}   "
              f"'statgroup': {b'statgroup' in low}   "
              f"'valmentaja'/'coach': "
              f"{b'valmentaja' in low or b'coach' in low}")
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}  {path}")
    time.sleep(1.0)

print("\nDone. Paste this output back to the Mestis session. The saved "
      "probe_out/v3_*.txt files will be read by the session directly.")
