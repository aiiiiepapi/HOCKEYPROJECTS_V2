"""
verify_mestis_lake.py — lake-level verification for the Mestis raw lake
=======================================================================
Runs OFFLINE against the lake directory (works anywhere — cloud or PC).
Checks (lake-level only, no betting logic, no interpretation):

  1. Schedule reconciliation, 1:1 both ways: every ICS game has all 3
     pages saved and structurally valid; every game_* file maps back to
     an ICS match number (no strays).
  2. Manifest integrity: every recorded file exists and its sha256
     matches (i.e. nothing edited since fetch — the lake is immutable).
  3. Structural smoke-read: every saved HTML is complete (</html>) and
     above stub size.
  4. Capability presence counts per season (rule 8 guards): games whose
     seuranta contains an explicit goalie-out event, games whose
     tilastot carries an off-ice interval ('pois:'/'out:'). ZERO games
     with goalie events in a full season = automatic failure.
  5. Prints 5 seeded-random games per season for manual spot-opening.

Writes COMPLETENESS.md into the lake root and exits nonzero on failure.

Usage:
  python verify_mestis_lake.py --lake <dir>          # default: data/raw/mestis
  python verify_mestis_lake.py --lake <dir> --seed 20260803
"""

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

PAGES = ("kokoonpanot", "seuranta", "tilastot")
MIN_HTML_BYTES = 5000


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def unfold_ics(text):
    return re.sub(r"\r?\n[ \t]", "", text)


def ics_matchnos(ics_path):
    txt = unfold_ics(ics_path.read_text(encoding="utf-8", errors="replace"))
    out = set()
    for block in txt.split("BEGIN:VEVENT")[1:]:
        m = re.search(r"runkosarja/(\d+)/", block.split("END:VEVENT")[0])
        if m:
            out.add(int(m.group(1)))
    return out


def check_season(season_dir, seed):
    year = season_dir.name
    fails, notes = [], []
    ics = season_dir / f"schedule_{year}.ics"
    man_path = season_dir / f"manifest_{year}.json"
    if not ics.exists():
        return {"year": year, "fails": [f"missing {ics.name}"]}, None
    sched = ics_matchnos(ics)
    if not sched:
        return {"year": year, "fails": ["0 match numbers parsed from ICS "
                                        "(rule 8)"]}, None

    # 1) schedule -> files
    missing, stub = [], []
    for n in sorted(sched):
        for pg in PAGES:
            f = season_dir / f"game_{year}_{n}_{pg}.html"
            if not f.exists():
                missing.append(f.name)
            elif f.stat().st_size < MIN_HTML_BYTES:
                stub.append(f.name)
    if missing:
        fails.append(f"{len(missing)} schedule pages MISSING "
                     f"(first: {missing[:6]})")
    if stub:
        fails.append(f"{len(stub)} files below stub size (first: {stub[:6]})")

    # files -> schedule (no strays)
    strays = []
    game_files = sorted(season_dir.glob(f"game_{year}_*.html"))
    for f in game_files:
        m = re.match(rf"game_{year}_(\d+)_({'|'.join(PAGES)})\.html$", f.name)
        if not m or int(m.group(1)) not in sched:
            strays.append(f.name)
    if strays:
        fails.append(f"{len(strays)} files not on the schedule "
                     f"(first: {strays[:6]})")

    # 2) manifest integrity (immutability check)
    hash_bad, man_missing = [], []
    if man_path.exists():
        man = json.loads(man_path.read_text(encoding="utf-8"))
        for fname, rec in man.get("files", {}).items():
            fp = season_dir / fname
            if not fp.exists():
                man_missing.append(fname)
            elif sha256_file(fp) != rec["sha256"]:
                hash_bad.append(fname)
        unrecorded = [f.name for f in game_files
                      if f.name not in man.get("files", {})]
        if unrecorded:
            fails.append(f"{len(unrecorded)} files absent from manifest "
                         f"(first: {unrecorded[:6]})")
        if man.get("missing"):
            notes.append(f"manifest carries {len(man['missing'])} recorded "
                         f"problems: {list(man['missing'])[:6]}")
    else:
        fails.append(f"missing {man_path.name}")
    if hash_bad:
        fails.append(f"{len(hash_bad)} sha256 MISMATCHES — lake was edited! "
                     f"(first: {hash_bad[:6]})")
    if man_missing:
        fails.append(f"{len(man_missing)} manifest entries with no file "
                     f"(first: {man_missing[:6]})")

    # 3) smoke-read + 4) capability presence
    incomplete, goalie_ev, pois = [], 0, 0
    rosters, rosters_staff, rosters_hc = 0, 0, 0
    for n in sorted(sched):
        for pg in PAGES:
            f = season_dir / f"game_{year}_{n}_{pg}.html"
            if not f.exists():
                continue
            data = f.read_bytes()
            if b"</html>" not in data[-4096:].lower():
                incomplete.append(f.name)
            if pg == "seuranta":
                if b"Maalivahti ulos" in data:
                    goalie_ev += 1
                # off-ice intervals live in the seuranta goalie section
                if b"pois:" in data or b"out:" in data:
                    pois += 1
        rf = season_dir / f"game_{year}_{n}_rosters.json"
        if rf.exists():
            rosters += 1
            rdata = rf.read_bytes()
            if b'"Staff"' in rdata:
                rosters_staff += 1
            if b"Vastuuvalmentaja" in rdata:
                rosters_hc += 1
    if rosters == 0:
        notes.append("WARN: 0 tilastopalvelu rosters files this season "
                     "(coach source absent — decision for Manager)")
    elif rosters_hc < rosters:
        notes.append(f"rosters without a Vastuuvalmentaja (head coach) "
                     f"marker: {rosters - rosters_hc}/{rosters}")
    if incomplete:
        fails.append(f"{len(incomplete)} truncated HTML files "
                     f"(first: {incomplete[:6]})")
    if sched and goalie_ev == 0:
        fails.append("0 games with 'Maalivahti ulos' in a full season — "
                     "rule 8 automatic failure (format change?)")

    # 5) seeded spot-check sample
    rng = random.Random(seed)
    sample = rng.sample(sorted(sched), min(5, len(sched)))

    return {
        "year": year, "fails": fails, "notes": notes,
        "sched": len(sched),
        "complete": len(sched) - len({f.split("_")[2] for f in missing}),
        "goalie_ev": goalie_ev, "pois": pois, "sample": sample,
        "rosters": rosters, "rosters_hc": rosters_hc,
    }, sched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lake", default=str(Path("data/raw/mestis")))
    ap.add_argument("--seed", type=int, default=20260803)
    args = ap.parse_args()
    lake = Path(args.lake)
    seasons = sorted(d for d in lake.iterdir() if d.is_dir()
                     and re.fullmatch(r"\d{4}", d.name))
    if not seasons:
        print(f"No season dirs found under {lake}")
        sys.exit(2)

    lines = ["# Mestis lake completeness report", ""]
    lines.append("| Season | Games in ICS | Complete (3/3 pages) | "
                 "Seuranta w/ goalie-out | Tilastot w/ pois-interval | "
                 "Rosters (w/ HC) | Status |")
    lines.append("|---|---|---|---|---|---|---|")
    all_ok = True
    details = []
    for sd in seasons:
        r, _ = check_season(sd, args.seed)
        ok = not r["fails"]
        all_ok = all_ok and ok
        lines.append(f"| {int(r['year'])-1}-{r['year'][2:]} "
                     f"| {r.get('sched', '?')} | {r.get('complete', '?')} "
                     f"| {r.get('goalie_ev', '?')} | {r.get('pois', '?')} "
                     f"| {r.get('rosters', '?')} ({r.get('rosters_hc', '?')}) "
                     f"| {'PASS' if ok else 'FAIL'} |")
        details.append(r)
        print(f"[{r['year']}] {'PASS' if ok else 'FAIL'}  "
              f"sched={r.get('sched')}  goalie_ev={r.get('goalie_ev')}  "
              f"pois={r.get('pois')}  rosters={r.get('rosters')} "
              f"(hc {r.get('rosters_hc')})")
        for fl in r["fails"]:
            print(f"    FAIL: {fl}")
        for nt in r.get("notes", []):
            print(f"    note: {nt}")
        if "sample" in r:
            print(f"    spot-open sample (seed {args.seed}): {r['sample']}")

    lines.append("")
    lines.append(f"Spot-check seed: {args.seed}")
    for r in details:
        if r.get("sample"):
            lines.append(f"- {r['year']} sample match numbers: {r['sample']}")
        for fl in r["fails"]:
            lines.append(f"- {r['year']} FAIL: {fl}")
        for nt in r.get("notes", []):
            lines.append(f"- {r['year']} note: {nt}")
    (lake / "COMPLETENESS.md").write_text("\n".join(lines) + "\n",
                                          encoding="utf-8")
    print(f"\nWrote {lake / 'COMPLETENESS.md'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
