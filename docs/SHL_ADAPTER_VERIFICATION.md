# SHL adapter — Manager rule-0 verification & merge record (2026-08-07)

Branch claude/shl-adapter-hockeyprojects-lbeked, 6 commits, merged after
independent re-derivation. Gate suite in the Manager environment (ALL
lakes mounted, unlike the build session's): 29/29 GREEN.

## Re-derived, all reproduce exactly

- Extraction re-run: 681 instances (170/171/174/166), 40 pulled (28 EV
  + 12 pp), 0 parse errors, 100% attribution — identical to handoff.
- Audit: their seed (20260807) 0/60 AND a fresh Manager seed (20260808)
  0/60; mestis regression with the modified tool 0/60.
- Independent hand-trace of GT pp_pull game 2023/629037 from raw HTML:
  open 803 / evidence 967 / leader minor (Laleggia, delay of game
  54:25-56:25) covering the pull second / 5+20 Forsberg pair with the
  GM correctly inert -> pp_pull. Matches GT and adapter output exactly.
- Coach-map evidence spot-check: 629318 confirmed HV71-TIK home,
  matching the SVT-pinned "Lindbom's first game 01-31 home vs Timrå".

## Adjudications (Manager rulings; Seb may override)

1. **pbp dedupe amendment RATIFIED**: (period, time, team, playerId) +
   keep-latest-revision + OUT-first. Evidence complete both directions
   (774444 same-player revision dupes; 882274 cross-goalie period-break
   swap that the 3-field key wrongly collapsed).
2. **"Johan Lindholm" = Johan Lindbom**: spelling normalization applied
   in the RUNNER (COACH_SPELLING_FIX, liiga NAME_FIX precedent) — a
   one-sheet misspelling is the same person; identity convention
   (listing wins) untouched. Extraction re-run, counts unchanged.
   **Burström stays as listed** (plausible caretaker, no counter-evidence).
3. **HV71 Oct-2023 (3 games): LISTING WINS maintained.** Davidsson (x2)
   and Gustafsson (x1) stay attributed as the sheets say, against press
   reports that Lindbom was already HC. Overriding a non-blank listing
   with press would breach the standing join rule (AHL/Mestis: the
   game's own listing ALWAYS wins; maps fill BLANKS only). The tiny-n
   identities this creates are handled by shrinkage. 3-line map override
   available if Seb rules otherwise.
4. **Audit pull-side cap accepted**: all 27 pulls in 2024-2026 audited
   (2023 has no second channel); future seasons lift the cap.

## Ledger + profiles + morning sheet (Manager work, built at merge)

clean_window_interval shl: 681 instances -> **161 clear chances,
clear-chance take rate 17.4%**, prior mu 0.17 / S 6.0 predictive, 36
coaches, 17 active benches. THE SHL PERSONALITY, clean-window
controlled and therefore comparable (15b satisfied): SHL coaches take
clear down-3 chances at 17.4% vs AHL 50.2 / Mestis 45.6 / Liiga 41.9 —
they pull EARLY at gap 1-2 instead (29.8% of gap-3 instances open with
the net already empty, the highest carryover share in the portfolio).
Two per-league gate bounds widened for SHL with evidence (mu floor
0.30->0.08; profile floor 0.02->0.002 — Thomas Berglund is a genuine
0/16-over-38-instances never-puller). Morning sheet delivered with
COACH-INTEL-ONLY banner + the gap-1/2 signature note; every active
coach is currently sub-40 = rule-28 NO-BET, which is itself the
headline: SHL down-3 coach edges are thin — the interesting SHL
product, if any, lives at gap 1-2 (a NEW product class, not priced by
the current gap-3 pipeline; Seb's call whether to queue it).

## Status

Adapter MERGED. SHL = coach intel only; NO pricer (a gap-3 pricer needs
blind multi-fold validation AND faces 28-EV-pull training data — thin;
any SHL pricing discussion starts from that number). dp channel
near-vacuous (n=2 in 4 seasons; rulings 17/17b applied symmetrically,
KHL cross-calibration pending).
