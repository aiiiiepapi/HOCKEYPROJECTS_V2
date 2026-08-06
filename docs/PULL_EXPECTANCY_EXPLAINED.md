# Pull expectancy — the whole thing in plain words

(Quick reference for Seb. How a chance is counted, when a no-pull counts,
and what goes into the % on the sheet. Written 2026-08-07.)

---

## Part 1 — How we count chances and no-pulls

**Step 1. Find the moment.**
A team is down by 3 in the 3rd period. That opens a "window" — from the
second the score becomes down-3 (or from the start of the 3rd if they were
already down 3) until the game ends, the gap changes, or regulation runs out.

**Step 2. Was there actually room to act?**
Inside that window, we only count the seconds where pulling was truly
possible:

- the net is still full (nobody pulled yet)
- it's 5-on-5 (nobody in the penalty box, either team)
- it's not the first 18 seconds right after a goal (dead time — nobody
  pulls there, the play just restarted)

**Step 3. Was it a real chance or a junk window?**
Not all windows are equal. Being down 3 with 8 minutes left is a real
chance. Being down 3 with 9 seconds left, or with a penalty eating the
whole window, is junk — no coach on earth pulls there.

We measure this by looking at WHEN coaches in that league actually pull
(mostly the last few minutes). If the usable part of his window covers at
least ~70% of the "pulling value" of a FULL 3rd period, it's a **clear
chance**. Below that, it's junk. In practice this means a chance has to
arrive with roughly 4-5 minutes still left (varies slightly by league)
AND stay reasonably intact — a chance that shows up with 2:00 left, or
gets its prime minutes eaten by a penalty, doesn't count against anyone.
(Same bar in every league — unified 2026-08-07, ruling 45.)

**Step 4. Score it.**

- He pulled (at even strength) → counts as a **pull**. Always.
- Clear chance, didn't pull → counts as a **no-pull against him**.
- Junk window, didn't pull → counts for **nobody**. Not held against him.
- He pulled while on the power play → tracked separately (PP pulls),
  NOT part of the bettable number.

So when the sheet says a coach is 2/2, that means: two real, clean
opportunities where he had a full fair chance to pull — and he pulled
both times. Junk games were already thrown out before counting.

---

## Part 2 — What's weighted in the %

Simple list, no math, just what goes in:

1. **The coach.** Everything is about the man behind the bench that game —
   not the team. Coach changes teams, his record follows him.

2. **His clean chances only.** Down 3 in the 3rd, net full, 5-on-5, not
   right after a goal, real window to act. Junk situations don't count
   (Part 1 above is exactly how we decide).

3. **Did he pull on them.** Even-strength pulls only. PP pulls are shown
   beside, not inside.

4. **This season only.** Older seasons are context on the sheet, zero
   weight in the number. Exception: once a new season starts, LAST season
   keeps its weight until January 1st, then drops out.

5. **Recency inside the window.** Among the chances that count, newer ones
   weigh slightly more than older ones.

6. **A tiny neutral stabilizer.** Half a chance each way, 50/50, not a
   league number. This is why 2/2 prints ~81% instead of a flat 100% —
   a perfect 2-for-2 is a strong signal, not a guarantee.

**NOT in the calculation:** league average (removed by your ruling),
career history, pull timing (shown on the sheet, display only),
favorite/underdog, home/away, opponent, standings pressure.

**Flags on the sheet:**

- **HOT FORM** — pulled his last clean chance, or 2 of his last 3 →
  manual review flag.
- **RISKY** — fewer than 3 clean chances this season → number is thin.
- **NO DATA** — zero chances in the window → automatic NO-BET.
- **Under 40%** → NO-BET floor, always, regardless of anything else.

---

One note so nothing surprises you later: this is the SHEET formula (coach
cards). The priced lines (NHL / Liiga / Mestis) still run the older
validated formula until we re-test the new one on those leagues — your
call pending on that.
