"""
probe_tilastopalvelu.py — OPTIONAL one-shot probe (runs on Seb's PC)
===================================================================
Question it answers: does tilastopalvelu.fi still host Mestis game
sheets (which would carry COACH names — the one capability mestis.fi
lacks, see docs/MESTIS_SOURCE.md §4)?

The cloud workspace cannot reach tilastopalvelu.fi at all (TLS handshake
failure at the proxy), so this must run PC-side. It is FETCH-ONLY: it
saves raw responses under probe_out/ and prints whether 'mestis' appears.
It scrapes nothing in bulk — 3 requests total, 1s apart.

Usage:  python probe_tilastopalvelu.py
Then:   paste the printed summary back to the Mestis session and (if
        asked) share the probe_out/ files.
"""

import ssl
import time
from pathlib import Path
from urllib.request import Request, urlopen

URLS = [
    # front page: lists the series/statgroups the service hosts
    "https://www.tilastopalvelu.fi/ih/",
    # schedule module used by Finnish-hockey sites embedding the service
    "https://www.tilastopalvelu.fi/ih/modules/mod_schedule/helper/games.php?statgroupid=&select=all",
    # legacy landing without www
    "https://tilastopalvelu.fi/ih/",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

out = Path(__file__).with_name("probe_out")
out.mkdir(exist_ok=True)
ctx = ssl.create_default_context()

for i, url in enumerate(URLS):
    fname = out / f"probe_{i}.html"
    try:
        with urlopen(Request(url, headers=HEADERS), timeout=30,
                     context=ctx) as resp:
            data = resp.read()
        fname.write_bytes(data)
        low = data.lower()
        print(f"[{i}] OK {len(data):>7} B  {url}")
        print(f"    contains 'mestis': {b'mestis' in low}   "
              f"contains 'statgroup': {b'statgroup' in low}")
    except Exception as e:
        print(f"[{i}] FAIL {type(e).__name__}: {e}  {url}")
    time.sleep(1.0)

print("\nDone. Paste this output back to the Mestis session; keep "
      "probe_out/ around in case the session asks for the files.")
