# FRESH-EYES FACTS PACK — definitions, no conclusions

Everything here is a COUNT from raw NHL play-by-play (4 regular seasons,
2022-23 .. 2025-26, 5,248 games), stamped with the exact definition used to
count it. No model choices, no interpretations, no recommendations. Accept
these definitions or re-derive from raw — the raw lake is available.

## Raw data
- github.com/aiiiiepapi/HOCKEYPROJECTS branch `nhl-data-lake`
  (per game: gamecenter play-by-play + boxscore + right-rail with head coaches)
- Known raw-data facts (verified, not opinions):
  * situationCode = [awayGoalieIn][awaySkaters][homeSkaters][homeGoalieIn];
    a goal event's own code is authoritative for the state it was scored in
  * right-rail JSON files carry a UTF-8 BOM — read with encoding utf-8-sig
  * the game clock STOPS at every whistle/goal (faceoff after a goal occurs
    at the same clock second)
  * delayed-penalty sequences put the goalie off without a decision being made
  * shift-chart files were not fetched (only pbp/box/right-rail exist)

## Definitions behind each CSV
- goal_rates_by_state.csv: exposure = every 3rd-period second in which the
  score gap was exactly N (gap column) from the trailing team's perspective;
  state classified from situationCode each second (carry-forward between
  events); delayed-penalty goalie-off seconds excluded. "for" = trailing team
  scored, "against" = leading team scored. CI = Poisson.
- goal_rates_by_time_bucket.csv: same, split by seconds remaining in the
  3rd period. Blank rate = exposure under 900s (too thin to publish).
- penalty_rates.csv: transitions out of 5-on-5 full-net seconds into the
  trailing team being short-handed / on the power play.
- pull_events.csv: every net-empty-by-choice episode by the trailing team at
  gaps 2/3/4 (first second with net-empty evidence in situation codes;
  delayed-penalty artifacts excluded; a net emptied by a delayed penalty is
  NOT a pull). during_own_powerplay = trailing team had a man advantage at
  the pull.

## Market/business constraints (context, not modeling advice)
- Products: live 3rd-period bets when a team trails by 3 — leading team's
  team-total over, game-total over, leading team -3.5.
- Prices are needed from 15:00 down to 3:00 remaining; books do not hang
  these lines below ~3:00 or while the trailing team is on a power play or
  after the goalie is already out.
- There is NO odds feed: the deliverable per second/state is the fair
  probability and the American line at which a bet clears a chosen EV edge.
- Real money is bet on the output. Standards: derive from raw, verify by
  hand-tracing games before trusting any pipeline, exact-value tests,
  never assume prior work is correct.
