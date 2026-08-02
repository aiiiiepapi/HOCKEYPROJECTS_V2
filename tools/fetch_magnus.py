#!/usr/bin/env python3
"""
fetch_magnus.py — Ligue Magnus PDF game-sheet fetcher (STDLIB ONLY, runs on
Seb's Windows PC or the Ubuntu server; the cloud workspace cannot reach
hockeynet.fr).

Source: https://hockeynet.fr/sportif/feuille-de-match/recapitulatif/{id}/pdf
No auth. Match IDs are numeric and SHARED across French divisions — the lake
keeps every PDF fetched; Magnus filtering happens offline in v2 from the
Championnat header (fetch-only rule: this script classifies NOTHING).

Modes:
  python fetch_magnus.py --range 68800 69800      # season sweep (25-26 range)
  python fetch_magnus.py --ids ids.txt            # one id per line
  python fetch_magnus.py --probe-new              # nightly: extend past the
                                                  # highest id in the manifest
                                                  # until 40 consecutive 404s
Output: magnus_lake/{id}.pdf + magnus_lake/manifest.csv (id,status,bytes,sha256)
Resume-safe: existing non-empty PDFs are skipped. Retries x3, 0.6s delay.
"""
import argparse, csv, hashlib, os, sys, time
import urllib.request, urllib.error

BASE = "https://hockeynet.fr/sportif/feuille-de-match/recapitulatif/{}/pdf"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "magnus_lake")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(mid):
    req = urllib.request.Request(BASE.format(mid), headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if data[:5] == b"%PDF-" and len(data) > 5000:
                return "ok", data
            return "not_pdf", None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404", None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return "error", None

def manifest_path():
    return os.path.join(OUT, "manifest.csv")

def load_manifest():
    rows = {}
    if os.path.exists(manifest_path()):
        with open(manifest_path(), newline="") as f:
            for row in csv.DictReader(f):
                rows[int(row["id"])] = row
    return rows

def save_manifest(rows):
    with open(manifest_path(), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "status", "bytes", "sha256"])
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])

def run(ids):
    os.makedirs(OUT, exist_ok=True)
    man = load_manifest()
    got = skipped = missed = 0
    consec_404 = 0
    for mid in ids:
        fp = os.path.join(OUT, f"{mid}.pdf")
        if os.path.exists(fp) and os.path.getsize(fp) > 5000:
            skipped += 1
            consec_404 = 0
            continue
        status, data = fetch(mid)
        if status == "ok":
            with open(fp, "wb") as f:
                f.write(data)
            man[mid] = {"id": mid, "status": "ok", "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()}
            got += 1
            consec_404 = 0
        else:
            man[mid] = {"id": mid, "status": status, "bytes": 0, "sha256": ""}
            missed += 1
            consec_404 = consec_404 + 1 if status == "404" else 0
        if (got + missed) % 25 == 0:
            save_manifest(man)
            print(f"  ...{got} fetched, {missed} missing, at id {mid}", flush=True)
        time.sleep(0.6)
        if args.probe_new and consec_404 >= 40:
            print("40 consecutive 404s — assuming end of published ids")
            break
    save_manifest(man)
    print(f"DONE: fetched {got}, skipped(existing) {skipped}, missing/other {missed}")
    print(f"Lake at {OUT} — commit to HOCKEYPROJECTS branch magnus-data-lake")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", nargs=2, type=int)
    ap.add_argument("--ids")
    ap.add_argument("--probe-new", action="store_true")
    args = ap.parse_args()
    if args.range:
        run(range(args.range[0], args.range[1] + 1))
    elif args.ids:
        run([int(x) for x in open(args.ids) if x.strip()])
    elif args.probe_new:
        man = load_manifest()
        start = max([k for k, v in man.items() if v["status"] == "ok"], default=68800) + 1
        run(range(start, start + 5000))
    else:
        ap.error("need --range, --ids, or --probe-new")
