"""Coach profiles for the COACH GUIDE tab (rebuild after any refit).

Merges: clean_window_coach.json (pull % on real chances), pp_pull_coach.json
(PP-only flags), coach_table_production.json (pricing tier), instances
(current team by latest appearance, median pull time).
Output: data/derived/coach_profiles.json
Run:    python3 hockeycore/fit/build_coach_profiles.py
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DER = ROOT / "data" / "derived"


def main():
    insts = json.load(open(DER / "instances_gap3.json"))
    clean = {t["coach"]: t for t in json.load(open(DER / "clean_window_coach.json"))}
    pp = {t["coach"]: t for t in json.load(open(DER / "pp_pull_coach.json"))}
    prod = {c["coach"]: c for c in json.load(open(DER / "coach_table_production.json"))["coaches"]}
    _lt = json.load(open(DER / "low_tail_coaches.json")) if (DER / "low_tail_coaches.json").exists() else []
    low_tail = set(_lt["coaches"] if isinstance(_lt, dict) else _lt)

    latest = {}
    for i in insts:
        lead_team = i["home"] if i["trailing"] != i["home"] else i["away"]
        for coach, team in ((i["trailing_coach"], i["trailing"]), (i["leading_coach"], lead_team)):
            if coach not in latest or i["date"] > latest[coach][0]:
                latest[coach] = (i["date"], team)

    pull_Rs = {}
    for i in insts:
        if i["pulled"] and i["pull_segments"] and i["pull_classification"] != "pp_pull":
            pull_Rs.setdefault(i["trailing_coach"], []).append(
                1200 - i["pull_segments"][0]["empty_from"])

    def jeffreys(k, n):
        if not n:
            return None
        a, b = k + 0.5, n - k + 0.5
        mu = a / (a + b)
        sd = math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
        return [max(0, round(mu - 1.96 * sd, 3)), min(1, round(mu + 1.96 * sd, 3))]

    profiles = []
    for coach, c in clean.items():
        n, k = c["ev_clear"], c["ev_taken"]          # 5v5-ONLY: the bettable number
        date, team = latest.get(coach, ("", "?"))
        rs = sorted(pull_Rs.get(coach, []))
        med = rs[len(rs) // 2] if rs else None
        p = pp.get(coach, {})
        flags = []
        if p.get("pp_only"):
            flags.append("pulls ONLY on PP (0% at 5v5 = the bettable number)")
        elif coach in low_tail:
            flags.append("rarely pulls")
        if n < 5:
            flags.append(f"small sample ({n} chances)")
        if n and k == n and n >= 5:
            flags.append("pulls EVERY clean 5v5 chance so far")
        ppl = p.get("pulls_pp", 0)
        if ppl and not p.get("pp_only"):
            flags.append(f"+{ppl} PP pulls (excluded above)")
        profiles.append({
            "team": team, "coach": coach, "last_seen": date,
            "clear_chances": n, "clear_taken": k,
            "clean_rate": (round(k / n, 3) if n else None), "ci": jeffreys(k, n),
            "overall_rate": c["clean_rate"],
            "median_pull_R": med, "n_pulls": len(rs),
            "m_prod": prod.get(coach, {}).get("m_prod", 1.0),
            "pp_share": p.get("pp_share_of_pulls"), "flags": flags,
        })
    profiles.sort(key=lambda x: x["team"])
    json.dump(profiles, open(DER / "coach_profiles.json", "w"), indent=1)
    print(f"{len(profiles)} coach profiles written")


if __name__ == "__main__":
    main()
