"""
probe_tilastopalvelu.py — OPTIONAL probe v7 (runs on Seb's PC)
==============================================================
Exact AJAX signatures now known from the apps' own JS (v6 captures):
  gamecentre  : HelpersPath = MAINPATH + '/game/helpers/'
                POST getgamereportdata.php {gameid, season}
                POST getRosters.php        {gameid, season}
  gamerosters : POST '/gamerosters//helper/game.php?game=N&season=Y'
                POST '/gamerosters//helper/gamerosters.php?team=home...'
                (params in the QUERY STRING, empty POST body)
v7 calls exactly these for Mestis game 3016 / season 2025, under /ih/
first then host-root. ~10 requests, saved verbatim to probe_out/.
Usage:  python probe_tilastopalvelu.py
"""

import ssl
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPSHandler

BASE = "https://tilastopalvelu.fi"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://tilastopalvelu.fi/ih/game/",
           "X-Requested-With": "XMLHttpRequest"}
G, S = 3016, 2025


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


def call(path, body=None, empty_post=False, tag=""):
    url = BASE + path
    data = (urlencode(body).encode() if body
            else (b"" if empty_post else None))
    try:
        got = opener.open(Request(url, data=data, headers=HEADERS),
                          timeout=30).read()
        (out / f"v7_{tag}.txt").write_bytes(got)
        low = got.lower()
        print(f"OK  {len(got):>8} B  "
              f"{'POST' if data is not None else 'GET '} {path}")
        print(f"    'valmentaja': {b'valmentaja' in low}  "
              f"'coach': {b'coach' in low}  "
              f"'toimihenkil': {b'toimihenkil' in low}  "
              f"'keupa': {b'keupa' in low}  "
              f"'maalivahti': {b'maalivahti' in low}")
        return got
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}  {path}")
        return None
    finally:
        time.sleep(1.0)


# gamecentre helpers (POST with form body)
for pre in ("/ih", ""):
    r = call(f"{pre}/game/helpers/getgamereportdata.php",
             body={"gameid": G, "season": S},
             tag=f"report{pre.replace('/', '_')}")
    if r and len(r) > 100:
        break
for pre in ("/ih", ""):
    r = call(f"{pre}/game/helpers/getRosters.php",
             body={"gameid": G, "season": S},
             tag=f"rosters{pre.replace('/', '_')}")
    if r and len(r) > 100:
        break

# gamerosters helpers (query-string params, empty POST body)
for pre in ("/ih", ""):
    r = call(f"{pre}/gamerosters//helper/game.php?game={G}&season={S}",
             empty_post=True, tag=f"gr_game{pre.replace('/', '_')}")
    if r and len(r) > 50:
        call(f"{pre}/gamerosters//helper/gamerosters.php"
             f"?team=home&game={G}&season={S}", empty_post=True,
             tag=f"gr_home{pre.replace('/', '_')}")
        call(f"{pre}/gamerosters//helper/referees.php?game={G}&season={S}",
             empty_post=True, tag=f"gr_refs{pre.replace('/', '_')}")
        break

# statgroups enumeration (didn't run in v6 — budget)
call("/ih/serie/helpers/getStatGroups.php",
     body={"season": S, "levelid": 65, "districtid": 0}, tag="statgroups")

print("\nDone. Paste this output back to the Mestis session; the session "
      "reads probe_out/v7_*.txt directly.")
