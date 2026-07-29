# Covariate backlog (Seb + Claude brainstorm, 2026-07-25)
Discipline: 217 pulls total → production supports 3-5 covariates max. Every
candidate: O/E test w/ CI, direction pre-registered, walk-forward before adoption.

## ADOPTED (proven out-of-sample, in production)
- Trailing at HOME: x1.34 | UNDERDOG: x0.64 | favorite: x1.07 (vs even/away)
- Coach level (context-cleaned EB, x0.355 attenuation) + Roy timing shift +67s
- Re-pull dynamics, evidence-lag 9s

## TESTED, REJECTED
- Season phase (early/mid/late): flat league-wide
- Recency weighting (90/180/365d half-lives): no gain vs equal weighting
- Evidence-weighted shrinkage (tau^2 unfittable at n=40 coaches): lost shootout
  to uniform 0.355; heavy-tail prior idea parked below

## WAVE 2 (computable now, pre-registered directions)
- Gap arrival: 4->3 (trailer scored, momentum, maybe already-pulled) > 2->3 (gut punch) [Seb]
- Time-since-gap-opened as hazard covariate (decision lag) [Seb]
- Playoff race alive vs eliminated (proxy: standings percentile after Mar 1) — alive pulls more [Seb]
- Trailing team on back-to-back — pulls less [Seb]
- Already pulled earlier in game (2-gap) — pulls more/earlier (commitment)
- Blown lead (trailing team led earlier) — direction uncertain, exploratory
- LEADING team on back-to-back — trailing pulls more (chase belief)

## WAVE 3 (needs new parsing/data)
- Star player in/out (boxscore lineups + season-to-date scoring) — mainly affects
  6v5/EN conversion rates, not pull decision [Seb]
- Backup vs starter goalie in trailing net — cheaper pull
- Trailing team PP% season-to-date × on-PP pull interaction
- Days-rest differential; post-trade-deadline seller status
- Coach recently burned (EN-against on pull in last N games) — gun-shy autocorrelation
- Heavy-tailed coach prior (t-dist random effects) — revisit at 3+ seasons of data

## TESTED 2026-07-26 — pull-memory covariates: BOTH NULL (drop from backlog)
Q (Seb): does a successful previous pull (cut the gap 6v5) raise the next
3-gap pull rate? And does eating an ENG suppress it?
Method: 2,082 pull events (gap 2+3) classified scored/ENG-punished/neutral,
joined to each coach's next clean 3-gap 5v5 chance; raw + within-coach
(precision-weighted) to kill the aggressive-coach confound.
- after SCORED 6v5:   53% (44/83)   | within-coach vs failure: -3.0pts
- after ENG-punished: 52% (143/274) | within-coach vs neutral: -3.6pts
- after neutral:      57% (86/152)
Verdict: no momentum, no meaningful deflation. Coach identity dominates;
last-pull outcome adds nothing bettable. Memoryless coach hazard VALIDATED.
(Side stat: 52% of all pulls end ENG-punished, 18% succeed, 30% neutral.)
