"""
verify_shl_lake.py — SHL lake verification (lake-level only, no bet logic)
==========================================================================
Deliberately SELF-CONTAINED: re-derives everything from the raw files
(does not import fetch_shl.py), so it is an independent check of the
fetcher's output. Manager re-derivation per rule 0 stays separate.

Checks:
 A. manifest <-> disk 1:1 (sha256 re-hash, byte counts), 0 strays, 0 missing
 B. schedule reconciliation BOTH directions per season:
    ids on the schedule authority page == game files on disk
 C. every artifact self-identifies (its own game id/uuid inside the payload)
    and parses (HTML marker / JSON loads) — 0 truncated
 D. structural season shape from raw schedule: 364 games, 14 teams x 26 home
 E. coach coverage: 'Head Coach:' count per lineups page (expected 2)
 F. seeded-random spot-opens (seed 20260806): SCOPED per-game counts —
    goal rows counted inside the game's own tables must equal the header
    final score; GK rows listed; penalties have (begin - end) windows
 G. cross-channel GK audit on the seeded sample (2024+): swehockey GK
    events (cumulative clock) vs shl.se pbp goalkeeper events
    ((period-1)*20:00 + period clock) — multiset agreement, mismatches listed

Usage: python verify_shl_lake.py --lake C:\\dev\\HP_V2\\shl_lake_staging\\shl
       [--seasons 2023 2024 2025 2026] [--sample 8] [--write-completeness]
Exit 0 = all hard checks pass; exit 2 otherwise.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
from datetime import datetime, timezone

SHL_PBP_SEASONS = (2024, 2025, 2026)  # measured 2026-08-06 (stage 1.5 probe)
HARD_FAILS = []
WARNS = []


def fail(msg):
    HARD_FAILS.append(msg)
    print("  FAIL " + msg)


def ok(msg):
    print("  ok   " + msg)


def warn(msg):
    WARNS.append(msg)
    print("  WARN " + msg)


def rows_of(html):
    """Row-scoped iteration (ticker-lesson discipline: nothing page-wide)."""
    return html.split("<tr")


def detag(s):
    return re.sub(r"[\s|]+", " ", re.sub(r"<[^>]+>", "|", s))


def cum_seconds(t):
    mm, ss = t.split(":")
    return int(mm) * 60 + int(ss)


def verify_season(root, year, sample_n, rng):
    print("== season %d ==" % year)
    sdir = os.path.join(root, str(year))
    man_path = os.path.join(sdir, "manifest_%d.json" % year)
    if not os.path.exists(man_path):
        fail("%d: manifest missing" % year)
        return
    with open(man_path, encoding="utf-8") as f:
        man = json.load(f)

    # A. manifest <-> disk, re-hash
    on_disk = set()
    for fn in os.listdir(sdir):
        if fn == "manifest_%d.json" % year:
            continue
        on_disk.add("%d/%s" % (year, fn))
    man_keys = set(man.keys())
    stray = on_disk - man_keys
    missing = man_keys - on_disk
    if stray:
        fail("%d: %d stray files (first: %s)" % (year, len(stray), sorted(stray)[:3]))
    if missing:
        fail("%d: %d manifested files missing on disk (first: %s)" % (year, len(missing), sorted(missing)[:3]))
    bad_hash = 0
    for rel, meta in man.items():
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        blob = open(p, "rb").read()
        if hashlib.sha256(blob).hexdigest() != meta["sha256"] or len(blob) != meta["bytes"]:
            bad_hash += 1
            if bad_hash <= 3:
                fail("%d: hash/bytes mismatch %s" % (year, rel))
    if bad_hash == 0:
        ok("%d: %d files re-hashed clean, 0 stray, 0 missing-on-disk" % (year, len(man)))

    # B/D. schedule authority: independent minimal re-parse (row-scoped)
    sched = [fn for fn in os.listdir(sdir) if fn.startswith("schedule_swe_")]
    if len(sched) != 1:
        fail("%d: expected exactly 1 swe schedule file, got %s" % (year, sched))
        return
    html = open(os.path.join(sdir, sched[0]), encoding="utf-8", errors="replace").read()
    ids = []
    homes = {}
    last_date = None
    for chunk in rows_of(html):
        dm = re.findall(r"\b(20\d\d-\d\d-\d\d)\b", chunk)
        if dm:
            last_date = dm[-1]
        g = re.search(r"/Game/Events/(\d+)", chunk)
        if not g:
            continue
        gid = int(g.group(1))
        if gid in homes:
            continue
        ids.append(gid)
        text = detag(chunk)
        best = None
        for tm in re.finditer(r"([A-ZÅÄÖ][A-Za-z0-9ÅÄÖåäöé\.\' ]{2,39}?) - ([A-ZÅÄÖ][A-Za-z0-9ÅÄÖåäöé\.\' ]{2,39}?)(?= |$)", text):
            if best is None or len(tm.group(0)) >= len(best.group(0)):
                best = tm
        homes[gid] = (last_date, best.group(1).strip() if best else None)
    if len(ids) != 364:
        fail("%d: schedule authority has %d games != 364" % (year, len(ids)))
    hc = {}
    for gid, (d, h) in homes.items():
        k = "".join(t for t in re.sub(r"[^a-z0-9åäöé ]", "", (h or "").lower()).split()
                    if t not in {"if", "hc", "bk", "aik", "ik", "hk", "hf", "hockey"})
        hc[k] = hc.get(k, 0) + 1
    if len(hc) == 14 and set(hc.values()) == {26}:
        ok("%d: schedule shape 364 games, 14 teams x 26 home" % year)
    else:
        fail("%d: schedule shape teams=%d homecounts=%s" % (year, len(hc), sorted(set(hc.values()))))

    # B. both directions vs disk
    want_pbp = year in SHL_PBP_SEASONS
    per_game = ["events.html", "lineups.html"] + (["pbp.json", "boxscore.json"] if want_pbp else [])
    disk_ids = set()
    for rel in man_keys:
        m = re.match(r"%d/game_%d_(\d+)_" % (year, year), rel)
        if m:
            disk_ids.add(int(m.group(1)))
    sched_ids = set(ids)
    if disk_ids - sched_ids:
        fail("%d: %d game files NOT on schedule (first: %s)"
             % (year, len(disk_ids - sched_ids), sorted(disk_ids - sched_ids)[:3]))
    if sched_ids - disk_ids:
        fail("%d: %d scheduled games with NO files (first: %s)"
             % (year, len(sched_ids - disk_ids), sorted(sched_ids - disk_ids)[:3]))
    incomplete = [g for g in sched_ids
                  if any("%d/game_%d_%d_%s" % (year, year, g, a) not in man_keys for a in per_game)]
    if incomplete:
        fail("%d: %d games missing artifacts (first: %s)" % (year, len(incomplete), incomplete[:3]))
    else:
        ok("%d: reconciliation both directions clean; %d artifacts/game complete" % (year, len(per_game)))

    # C. self-identification + parse of EVERY artifact; E. coach coverage
    coachless_sides = 0
    self_id_bad = 0
    for gid in sorted(sched_ids):
        for art in per_game:
            rel = "%d/game_%d_%d_%s" % (year, year, gid, art)
            p = os.path.join(root, rel)
            if not os.path.exists(p):
                continue
            blob = open(p, "rb").read()
            if art.endswith(".html"):
                h = blob.decode("utf-8", "replace")
                if "TSMstats" not in h or ("/Game/Events/%d" % gid) not in h and ("/Game/LineUps/%d" % gid) not in h:
                    self_id_bad += 1
                    if self_id_bad <= 3:
                        fail("%d: %s lacks marker/self-id" % (year, rel))
                if art == "lineups.html":
                    n_hc = len(re.findall(r"Head Coach:", h))
                    if n_hc < 2:
                        coachless_sides += 2 - n_hc
            else:
                try:
                    j = json.loads(blob.decode("utf-8"))
                    if art == "pbp.json":
                        uu = {e.get("gameUuid") for e in j if isinstance(e, dict)}
                        url_uuid = man[rel]["url"].rsplit("/", 1)[1]
                        if uu - {None} and uu - {None} != {url_uuid}:
                            self_id_bad += 1
                            fail("%d: %s gameUuid mismatch vs manifest url" % (year, rel))
                except Exception:
                    self_id_bad += 1
                    fail("%d: %s does not parse as JSON" % (year, rel))
    if self_id_bad == 0:
        ok("%d: every artifact parses and self-identifies (0 truncated)" % year)
    sides = 364 * 2
    if coachless_sides == 0:
        ok("%d: coach coverage %d/%d sides (Head Coach on every lineups page, both teams)" % (year, sides, sides))
    else:
        warn("%d: coach coverage %d/%d sides — %d side(s) blank (hand-curation list for Manager)"
             % (year, sides - coachless_sides, sides, coachless_sides))

    # F/G. seeded spot-opens with SCOPED counts + cross-channel GK audit
    sample = rng.sample(sorted(sched_ids), min(sample_n, len(sched_ids)))
    gk_mismatch = 0
    for gid in sample:
        ev = open(os.path.join(sdir, "game_%d_%d_events.html" % (year, gid)),
                  encoding="utf-8", errors="replace").read()
        tmatch = re.search(r"<title>.*?\((\d+)\s*-\s*(\d+)\)", ev, re.S)
        goal_rows = 0
        gk_rows = []
        pen_win = 0
        for chunk in rows_of(ev):
            text = detag(chunk)
            if re.search(r"\b\d+-\d+ \((EQ|PP\d|SH\d|PS)\)", text):
                goal_rows += 1
            gm = re.search(r"(\d\d:\d\d) (GK (?:In|Out))", text)
            if gm:
                gk_rows.append((gm.group(1), gm.group(2), ("HOME" if gid else "")))
            if re.search(r"\(\d\d:\d\d - \d\d:\d\d\)", text):
                pen_win += 1
        score_ok = False
        if tmatch:
            score_ok = goal_rows == int(tmatch.group(1)) + int(tmatch.group(2))
        # shootout winners are listed as a goal row variant; allow +-1 only if OT/SO
        if score_ok:
            ok("%d/%d: scoped goal rows == header score (%d), gk_rows=%d, pen_windows=%d"
               % (year, gid, goal_rows, len(gk_rows), pen_win))
        else:
            is_otso = "GWS" in ev or "vertime" in ev
            if is_otso and tmatch and abs(goal_rows - (int(tmatch.group(1)) + int(tmatch.group(2)))) <= 1:
                ok("%d/%d: scoped goal rows %d ~ header %s-%s (OT/SO variant), gk_rows=%d"
                   % (year, gid, goal_rows, tmatch.group(1), tmatch.group(2), len(gk_rows)))
            else:
                fail("%d/%d: scoped goal rows %d != header score %s"
                     % (year, gid, goal_rows, tmatch.groups() if tmatch else None))
        if year in SHL_PBP_SEASONS:
            pbp = json.loads(open(os.path.join(sdir, "game_%d_%d_pbp.json" % (year, gid)),
                                  encoding="utf-8").read())
            pbp_gk = sorted(
                (e["period"] - 1) * 1200 + cum_seconds(e["time"])
                for e in pbp if isinstance(e, dict) and e.get("type") == "goalkeeper")
            swe_gk = sorted(cum_seconds(t) for t, _k, _s in gk_rows)
            if len(pbp_gk) != len(swe_gk):
                gk_mismatch += 1
                warn("%d/%d: GK event count swe=%d pbp=%d (channels disagree — adjudicate)"
                     % (year, gid, len(swe_gk), len(pbp_gk)))
            else:
                worst = max((abs(a - b) for a, b in zip(swe_gk, pbp_gk)), default=0)
                if worst > 30:
                    gk_mismatch += 1
                    warn("%d/%d: GK time drift up to %ds between channels" % (year, gid, worst))
    if year in SHL_PBP_SEASONS and gk_mismatch == 0:
        ok("%d: cross-channel GK audit clean on %d sampled games" % (year, len(sample)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lake", required=True, help="path to the shl/ lake root")
    ap.add_argument("--seasons", nargs="*", type=int, default=[2023, 2024, 2025, 2026])
    ap.add_argument("--sample", type=int, default=8)
    ap.add_argument("--write-completeness", action="store_true")
    args = ap.parse_args()
    rng = random.Random(20260806)
    for year in args.seasons:
        verify_season(args.lake, year, args.sample, rng)
    print()
    print("===== VERIFY SUMMARY =====")
    print("hard fails: %d" % len(HARD_FAILS))
    for m in HARD_FAILS[:30]:
        print("  FAIL " + m)
    print("warnings: %d" % len(WARNS))
    for m in WARNS[:30]:
        print("  WARN " + m)
    if args.write_completeness and not HARD_FAILS:
        path = os.path.join(args.lake, "COMPLETENESS.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# SHL lake — completeness statement\n\n")
            f.write("Verified %s by tools/verify_shl_lake.py (seed 20260806).\n\n"
                    % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"))
            f.write("- Seasons 2023..2026 (END-year dirs), regular season only, "
                    "364 games each, reconciled 1:1 both directions against the "
                    "swehockey per-season Schedule page (series 13469/14677/15977/18263).\n")
            f.write("- Artifacts per game: swehockey Events+LineUps HTML (all seasons); "
                    "shl.se play-by-play+boxscore JSON for 2024..2026 only — the "
                    "gameday archive does not serve 2022-23 (measured, 0-byte "
                    "responses; stage-1.5 probe 2026-08-06). SOURCE-ABSENT, not a fetch gap.\n")
            f.write("- All files sha256-manifested; raw bytes verbatim, never edited.\n")
        print("wrote " + path)
    sys.exit(2 if HARD_FAILS else 0)


if __name__ == "__main__":
    main()
