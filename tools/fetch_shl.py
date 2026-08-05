"""
fetch_shl.py — SHL raw data lake fetcher (runs on Seb's Windows PC)
===================================================================
Fetch-only, stdlib-only, resume-safe, verbatim bytes, sha256 manifest.

Two sources, four artifacts per game + per-season schedule authorities:
  stats.swehockey.se  Game/Events/{id}   (goalie in/out, ENG, penalties begin+end)
                      Game/LineUps/{id}  (head coach per team, lines, refs)
  www.shl.se          /api/gameday/play-by-play/{uuid}  (shot-level pbp JSON)
                      /api/gameday/boxscore/{uuid}
Schedule authorities per season:
  swehockey ScheduleAndResults/Schedule/{seriesId}  (PRIMARY authority)
  shl.se    /api/sports-v2/game-schedule?...        (uuid map, OT/SO, rounds)

STAGE 1 fetches schedules and HARD-GATES before any game fetch:
  - swehockey page title is SHL (not Play Out/SM-slutspel), label matches season
  - exactly 364 unique game ids, 14 teams x 52 games, date range sane
  - shl.se schedule: 364 games, all post-game, rounds 1..52
  - date+home-team join swehockey<->shl.se = 364/364 per season
Any gate failure = stop before stage 2 (report and exit 2).
--swe-only skips the shl.se channel (only on explicit session instruction).

Usage:
  python fetch_shl.py --out C:\\dev\\HP_V2\\shl_lake_staging [--seasons 2023 2024 2025 2026]
                      [--delay 0.7] [--swe-only]
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
SWE = "https://stats.swehockey.se"
SHL = "https://www.shl.se"

# season END year -> swehockey SHL regular-season seriesId
# (extracted from the series dropdowns of the fetched 14296/15791/17556 pages
#  + 18263 verified directly on content, 2026-08-05; stage 1 re-verifies all)
SWE_SERIES = {2023: 13469, 2024: 14677, 2025: 15977, 2026: 18263}
SHL_SERIES_UUID = "qQ9-bb0bzEWUk"      # SHL
SHL_GAMETYPE_UUID = "qQ9-af37Ti40B"    # regular season (verified: returns the
                                       # 364-game runkosarja-equivalent for 25-26)
KNOWN_SEASON_UUIDS = {2026: "xs4m9qupsi"}  # verified by content 2026-08-05

EXPECTED_GAMES = 364
EXPECTED_TEAMS = 14


def log(msg):
    print(msg, flush=True)


def fetch_bytes(url, delay, tries=3):
    last = None
    for i in range(tries):
        time.sleep(delay if i == 0 else 2 ** (i + 1))
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — record and retry
            last = e
    raise RuntimeError("FETCH FAILED %s :: %r" % (url, last))


class Manifest:
    def __init__(self, path):
        self.path = path
        self.data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        self.dirty = 0

    def has(self, rel):
        return rel in self.data

    def add(self, rel, blob, url):
        self.data[rel] = {
            "sha256": hashlib.sha256(blob).hexdigest(),
            "bytes": len(blob),
            "url": url,
            "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.dirty += 1
        if self.dirty >= 25:
            self.flush()

    def flush(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)
        self.dirty = 0


def save(root, rel, blob, url, manifest):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    manifest.add(rel, blob, url)


TEAM_RE = r"([A-ZÅÄÖ][A-Za-z0-9ÅÄÖåäöé\.\' ]{2,39}?)"
GENERIC_TOKENS = {"if", "hc", "bk", "aik", "ik", "hk", "hf", "hockey"}


def norm_team(name):
    """Canonical join key: lowercase, drop generic club tokens, join the rest.
    'IF Malmö Redhawks'/'Malmö Redhawks' -> 'malmöredhawks';
    'Luleå HF'/'Luleå Hockey' -> 'luleå'; 'HV 71'/'HV71' -> 'hv71'."""
    toks = re.sub(r"[^a-z0-9åäöé ]", "", name.lower()).split()
    keep = [t for t in toks if t not in GENERIC_TOKENS]
    return "".join(keep) if keep else "".join(toks)


def parse_swe_schedule(html):
    """ROW-SCOPED parse (no cross-row windows — the ticker lesson generalized):
    split on <tr; a game row is the chunk containing its /Game/Events/{id}.
    The date lives in the first row of each day; carried forward in document
    order. Rows render short- and long-name team variants -> longest pair wins.
    Result pairs ('5 - 7') can't match: team side must start with a letter."""
    games = []
    seen = set()
    last_date = None
    date_re = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
    pair_re = re.compile(TEAM_RE + r" - " + TEAM_RE + r"(?= |$)")
    for chunk in html.split("<tr"):
        dm = date_re.findall(chunk)
        if dm:
            last_date = dm[-1]
        gm = re.search(r"/Game/Events/(\d+)", chunk)
        if not gm:
            continue
        gid = int(gm.group(1))
        if gid in seen:
            continue
        seen.add(gid)
        text = re.sub(r"<[^>]+>", "|", chunk)
        text = re.sub(r"[\s|]+", " ", text)
        best = None
        for tm in pair_re.finditer(text):
            if best is None or len(tm.group(0)) >= len(best.group(0)):
                best = tm
        home = best.group(1).strip() if best else None
        away = best.group(2).strip() if best else None
        games.append({"gid": gid, "date": last_date, "home": home, "away": away})
    return games


def gate(cond, msg, failures):
    status = "PASS" if cond else "FAIL"
    log("  GATE %s: %s" % (status, msg))
    if not cond:
        failures.append(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seasons", nargs="*", type=int, default=[2023, 2024, 2025, 2026])
    ap.add_argument("--delay", type=float, default=0.7)
    ap.add_argument("--swe-only", action="store_true")
    args = ap.parse_args()
    root = os.path.join(args.out, "shl")
    os.makedirs(root, exist_ok=True)
    failures = []
    plan = {}   # year -> {games: [...], uuid_by_key: {...}}

    # ---------- stage 0: resolve shl.se season uuids ----------
    season_uuids = dict(KNOWN_SEASON_UUIDS)
    if not args.swe_only:
        got = None
        for suffix in ("", "?seriesUuid=" + SHL_SERIES_UUID):
            url = SHL + "/api/sports-v2/season-series-game-types-filter" + suffix
            try:
                got = fetch_bytes(url, args.delay)
                man0 = Manifest(os.path.join(root, "manifest_root.json"))
                save(root, "season_series_game_types.json", got, url, man0)
                man0.flush()
                break
            except RuntimeError as e:
                log(str(e))
        if got:
            try:
                tree = json.loads(got.decode("utf-8"))
                # season[].code = season START year; lake dirs use END year
                for s in tree.get("season", []):
                    if s.get("uuid") and str(s.get("code", "")).isdigit():
                        season_uuids.setdefault(int(s["code"]) + 1, s["uuid"])
                # sanity: the regular-season gameType uuid we hardcode must be
                # the one the endpoint calls 'regular' (Grundserie)
                for gt in tree.get("gameType", []):
                    if gt.get("code") == "regular" and gt.get("uuid") != SHL_GAMETYPE_UUID:
                        log("stage0 WARNING: regular gameType uuid %s != expected %s — using endpoint value"
                            % (gt.get("uuid"), SHL_GAMETYPE_UUID))
                        globals()["SHL_GAMETYPE_UUID"] = gt["uuid"]
            except Exception as e:  # noqa: BLE001
                log("stage0: could not parse season list: %r" % e)
        log("stage0 season uuids resolved: %s" % json.dumps(season_uuids))
        missing = [y for y in args.seasons if y not in season_uuids]
        if missing:
            log("stage0 FAIL: no seasonUuid for %s — STOP. Options: report the"
                " saved season_series_game_types.json back to the session, or"
                " rerun with --swe-only ONLY on session instruction." % missing)
            sys.exit(2)

    # ---------- stage 1: schedule authorities + gates ----------
    for year in args.seasons:
        log("== STAGE 1 season %d ==" % year)
        sid = SWE_SERIES[year]
        man = Manifest(os.path.join(root, str(year), "manifest_%d.json" % year))
        url = SWE + "/ScheduleAndResults/Schedule/%d" % sid
        blob = fetch_bytes(url, args.delay)
        save(root, "%d/schedule_swe_%d.html" % (year, sid), blob, url, man)
        html = blob.decode("utf-8", "replace")
        title = re.search(r"<title>\s*(.*?)\s*</title>", html, re.S)
        title = re.sub(r"\s+", " ", title.group(1)) if title else ""
        label = re.search(r"<label>\s*(20\d\d-\d\d)\s*-\s*SHL\s*</label>", html)
        games = parse_swe_schedule(html)
        # count HOME side only (away names render short on some rows):
        # 14 teams x 26 home games == 364
        teams = {}
        for g in games:
            k = norm_team(g["home"]) if g["home"] else "?"
            teams[k] = teams.get(k, 0) + 1
        dates = sorted(g["date"] for g in games if g["date"])
        exp_label = "%d-%s" % (year - 1, str(year)[2:])
        gate(title.startswith("SHL"), "swe %d title='%s' is SHL" % (sid, title), failures)
        gate(bool(label) and label.group(1) == exp_label,
             "swe %d season label %s == %s" % (sid, label.group(1) if label else None, exp_label), failures)
        gate(len(games) == EXPECTED_GAMES, "swe %d games %d == 364" % (sid, len(games)), failures)
        gate(len(teams) == EXPECTED_TEAMS, "swe %d home teams %d == 14" % (sid, len(teams)), failures)
        gate(all(c == 26 for c in teams.values()),
             "swe %d every team 26 home games (got %s)" % (sid, sorted(set(teams.values()))), failures)
        gate(bool(dates) and dates[0][:4] == str(year - 1) and dates[-1][:4] == str(year),
             "swe %d date range %s..%s" % (sid, dates[0] if dates else None, dates[-1] if dates else None), failures)
        plan[year] = {"games": games, "uuid_by_key": {}}

        if not args.swe_only:
            surl = (SHL + "/api/sports-v2/game-schedule?seasonUuid=%s&seriesUuid=%s&gameTypeUuid=%s"
                    % (season_uuids[year], SHL_SERIES_UUID, SHL_GAMETYPE_UUID))
            sblob = fetch_bytes(surl, args.delay)
            save(root, "%d/schedule_shl_%d.json" % (year, year), sblob, surl, man)
            sj = json.loads(sblob.decode("utf-8"))
            ginfo = sj.get("gameInfo", [])
            gate(len(ginfo) == EXPECTED_GAMES, "shl %d games %d == 364" % (year, len(ginfo)), failures)
            gate(all(g.get("state") == "post-game" for g in ginfo),
                 "shl %d all post-game" % year, failures)
            # roundNumber is only populated for the current season on shl.se —
            # absent rounds are a WARN, wrong rounds are a FAIL
            rounds = sorted({g.get("roundNumber") for g in ginfo if g.get("roundNumber")})
            if rounds:
                gate(rounds[0] == 1 and rounds[-1] == 52,
                     "shl %d rounds present -> 1..52 (got %s..%s)" % (year, rounds[0], rounds[-1]), failures)
            else:
                log("  WARN: shl %d has no roundNumber data (historical season)" % year)
            # join on (date, NORMALIZED home) — raw names differ between the
            # sources for 5 of 14 clubs (HV71, Luleå, Malmö, Växjö, Örebro)
            for g in ginfo:
                key = (g["startDateTime"][:10], norm_team(g["homeTeamInfo"]["names"]["long"]))
                plan[year]["uuid_by_key"][key] = g["uuid"]
            joined = sum(1 for g in games
                         if (g["date"], norm_team(g["home"] or "")) in plan[year]["uuid_by_key"])
            gate(joined == EXPECTED_GAMES,
                 "join swe<->shl %d/%d (date+norm home)" % (joined, EXPECTED_GAMES), failures)
            if joined != EXPECTED_GAMES:
                miss = sorted({(g["date"], g["home"]) for g in games
                               if (g["date"], norm_team(g["home"] or "")) not in plan[year]["uuid_by_key"]})
                for mk in miss[:10]:
                    log("    unmatched: %s %s" % mk)
        man.flush()

    if failures:
        log("STAGE 1 FAILED %d gate(s) — NOT fetching games. Report to session:" % len(failures))
        for f in failures:
            log("  FAILED: " + f)
        sys.exit(2)
    log("STAGE 1: ALL GATES PASS — starting per-game fetch")

    # ---------- stage 2: per-game artifacts (resume-safe) ----------
    err = []
    for year in args.seasons:
        man = Manifest(os.path.join(root, str(year), "manifest_%d.json" % year))
        games = plan[year]["games"]
        umap = plan[year]["uuid_by_key"]
        done = 0
        for g in games:
            gid = g["gid"]
            arts = [
                ("game_%d_%d_events.html" % (year, gid), SWE + "/Game/Events/%d" % gid, b"TSMstats"),
                ("game_%d_%d_lineups.html" % (year, gid), SWE + "/Game/LineUps/%d" % gid, b"TSMstats"),
            ]
            if not args.swe_only:
                uuid = umap.get((g["date"], norm_team(g["home"] or "")))
                arts += [
                    ("game_%d_%d_pbp.json" % (year, gid), SHL + "/api/gameday/play-by-play/" + uuid, b"["),
                    ("game_%d_%d_boxscore.json" % (year, gid), SHL + "/api/gameday/boxscore/" + uuid, b"{"),
                ]
            for fn, url, marker in arts:
                rel = "%d/%s" % (year, fn)
                if man.has(rel) and os.path.exists(os.path.join(root, rel)):
                    continue
                try:
                    blob = fetch_bytes(url, args.delay)
                    if len(blob) < 500 or (marker and marker not in blob[:4000]):
                        raise RuntimeError("suspicious payload %d B %s" % (len(blob), url))
                    save(root, rel, blob, url, man)
                except RuntimeError as e:
                    err.append(str(e))
                    log("  ERROR " + str(e))
            done += 1
            if done % 25 == 0:
                log("  season %d: %d/%d games" % (year, done, len(games)))
        man.flush()
        log("== season %d done: %d games, manifest %d files ==" % (year, done, len(man.data)))

    log("")
    log("===== FETCH SUMMARY =====")
    for year in args.seasons:
        man = Manifest(os.path.join(root, str(year), "manifest_%d.json" % year))
        n_ev = sum(1 for k in man.data if k.endswith("_events.html"))
        n_lu = sum(1 for k in man.data if k.endswith("_lineups.html"))
        n_pbp = sum(1 for k in man.data if k.endswith("_pbp.json"))
        n_box = sum(1 for k in man.data if k.endswith("_boxscore.json"))
        log("season %d: events=%d lineups=%d pbp=%d boxscore=%d manifest=%d"
            % (year, n_ev, n_lu, n_pbp, n_box, len(man.data)))
    log("errors: %d" % len(err))
    for e in err[:40]:
        log("  " + e)
    log("Re-run the same command to resume/repair; then paste this summary back.")


if __name__ == "__main__":
    main()
