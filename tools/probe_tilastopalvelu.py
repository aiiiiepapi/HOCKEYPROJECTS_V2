"""
probe_tilastopalvelu.py — OPTIONAL probe v5 (runs on Seb's PC)
==============================================================
v4 CONFIRMED: the federation Tulospalvelu hosts Mestis schedule/results
as JSON — getGames.php returned LevelID 65 'Mestis', StatGroupID 168,
GameID 3016 (KeuPa HT - TUTO 2025-01-11) — and GameID matches the
mestis.fi match number. BUT the UI never opens its own gamecentre for
LevelID 65 (clicks go to mestis.fi), so whether game-level sheets
(rosters/officials/COACHES) exist here for Mestis must be tested
directly. That is v5's job, using known-good game 3016 / season 2025:

  1. Gamecentre page  /game/?season=2025&gameid=3016&lang=fi
     on BOTH hosts (tilastopalvelu.fi, tulospalvelu.leijonat.fi).
  2. Game report data  getgamereportdata.php POST {gameid, season}
     at the likely helper dirs.
  3. Rosters page  gamerosters/index.php?season=2025&gameid=3016.
  4. getStatGroups.php POST {season:2025, levelid:65} — enumerate the
     Mestis statgroup ids (schedule cross-check source).

FETCH-ONLY, ~12 requests, 1s apart, saved verbatim to probe_out/.
Usage:  python probe_tilastopalvelu.py
"""

import ssl
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPSHandler

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
           "Referer": "https://tilastopalvelu.fi/ih/serie/"}
GAMEID, SEASON = 3016, 2025


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
openers = [("default", build_opener()),
           ("legacy", build_opener(HTTPSHandler(context=legacy_ctx())))]


def get(url, post=None, tag=""):
    data = urlencode(post).encode() if post else None
    for label, op in openers:
        try:
            got = op.open(Request(url, data=data, headers=HEADERS),
                          timeout=30).read()
            (out / f"v5_{tag}.txt").write_bytes(got)
            low = got.lower()
            print(f"OK ({label}) {len(got):>8} B  "
                  f"{'POST' if post else 'GET '} {url}")
            print(f"    'valmentaja': {b'valmentaja' in low}   "
                  f"'coach': {b'coach' in low}   "
                  f"'toimihenkil': {b'toimihenkil' in low}   "
                  f"'mestis': {b'mestis' in low}   "
                  f"'keupa': {b'keupa' in low}")
            return got
        except Exception as e:
            print(f"FAIL ({label}) {type(e).__name__}: {e}  {url}")
    time.sleep(1.0)
    return None


# 1) gamecentre page, both hosts
for host, htag in (("https://tilastopalvelu.fi", "tp"),
                   ("https://tulospalvelu.leijonat.fi", "lj")):
    get(f"{host}/game/?season={SEASON}&gameid={GAMEID}&lang=fi",
        tag=f"gamecentre_{htag}")
    time.sleep(1.0)

# 2) game report data endpoint, likely helper dirs
for host, htag in (("https://tilastopalvelu.fi", "tp"),
                   ("https://tulospalvelu.leijonat.fi", "lj")):
    for hp, ptag in (("/game/helpers/", "game"), ("/ih/helpers/", "ih"),
                     ("/helpers/", "root")):
        r = get(f"{host}{hp}getgamereportdata.php",
                post={"gameid": GAMEID, "season": SEASON},
                tag=f"report_{htag}_{ptag}")
        time.sleep(1.0)
        if r and len(r) > 200:
            break

# 3) rosters page
get(f"https://tilastopalvelu.fi/gamerosters/index.php?season={SEASON}"
    f"&gameid={GAMEID}", tag="rosters_tp")
time.sleep(1.0)
get(f"https://tilastopalvelu.fi/ih/gamerosters/index.php?season={SEASON}"
    f"&gameid={GAMEID}", tag="rosters_tp_ih")
time.sleep(1.0)

# 4) Mestis statgroups for the season
get("https://tilastopalvelu.fi/ih/helpers/getStatGroups.php",
    post={"season": SEASON, "levelid": 65, "districtid": 0},
    tag="statgroups_mestis")

print("\nDone. Paste this output back to the Mestis session; the session "
      "reads probe_out/v5_*.txt directly.")
