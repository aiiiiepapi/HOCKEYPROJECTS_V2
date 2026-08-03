"""
probe_tilastopalvelu.py — OPTIONAL one-shot probe v2 (runs on Seb's PC)
=======================================================================
Question: does tilastopalvelu.fi still host Mestis game sheets (with
COACH names — the one capability mestis.fi lacks)?

v2 finding (probe v1, 2026-08-03, Seb's PC): the server's TLS is broken
for modern clients — www. host throws SSLV3_ALERT_HANDSHAKE_FAILURE
(legacy-cipher-only server) and the bare host presents a self-signed
chain. So v2 tries, in order per host: plain HTTP, then HTTPS with a
permissive legacy context (TLS1.0+, SECLEVEL=0, no cert verification —
acceptable for a read-only public-stats probe; nothing sensitive is
sent, and any data used later gets verified against real games anyway).

FETCH-ONLY: saves raw responses under probe_out/, prints a summary.

Usage:  python probe_tilastopalvelu.py
"""

import ssl
import time
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, HTTPSHandler

TARGETS = [
    "www.tilastopalvelu.fi/ih/",
    "tilastopalvelu.fi/ih/",
    "www.tilastopalvelu.fi/ih/modules/mod_schedule/helper/games.php?statgroupid=&select=all",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

out = Path(__file__).with_name("probe_out")
out.mkdir(exist_ok=True)


def legacy_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    except ssl.SSLError:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    return ctx


def try_fetch(url, ctx=None):
    req = Request(url, headers=HEADERS)
    if ctx is not None:
        opener = build_opener(HTTPSHandler(context=ctx))
        return opener.open(req, timeout=30).read()
    return urlopen(req, timeout=30).read()


for i, tgt in enumerate(TARGETS):
    got = None
    for scheme, ctx, label in (("http", None, "plain-http"),
                               ("https", legacy_ctx(), "legacy-tls")):
        url = f"{scheme}://{tgt}"
        try:
            got = try_fetch(url, ctx)
            fname = out / f"probe_{i}_{label}.html"
            fname.write_bytes(got)
            low = got.lower()
            print(f"[{i}] OK ({label}) {len(got):>7} B  {url}")
            print(f"    contains 'mestis': {b'mestis' in low}   "
                  f"'statgroup': {b'statgroup' in low}   "
                  f"'valmentaja': {b'valmentaja' in low}")
            break
        except Exception as e:
            print(f"[{i}] FAIL ({label}) {type(e).__name__}: {e}  {url}")
        time.sleep(1.0)
    time.sleep(1.0)

print("\nDone. Paste this output back to the Mestis session; keep "
      "probe_out/ around in case the session asks for the files.")
