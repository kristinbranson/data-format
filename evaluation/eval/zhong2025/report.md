# Evaluation Report — zhong2025

## Summary

- Dataset: **zhong2025**
- Questions covered: 37
- Trials per question: 6 (3 claude-code + 3 codex)
- Human evaluators: **LZ** (this report's comments and notes), KB
- Judges: Claude, Codex (supervised run, from `judge_supervised/`)

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
Ratings are evaluator LZ's, including the few questions where a judge was found more accurate and that judgement was adopted.

## Comments

#### Agent Performance
- This dataset has a custom format with most of the information contained in nested Python dictionaries and key-value pairs. The agents were generally very good at figuring out the data structure and where to find the relevant information.
- The agents made a few (strange?) mistakes on a subset of trials for which I could not find an obvious explanation — e.g., dropping V1 from the analysis, applying a very strict d-prime filter to select neurons, and merging stimulus categories that are not visually similar (rock and circle).
- Another problem is setting the bin edges incorrectly for running speed (due to a large number of stationary frames), despite the agents themselves explicitly reporting that the resulting bins contain a heavily skewed proportion of the data.

## Per-question evaluations

| Q | Question | LZ | KB | Claude judge | Codex judge | Solution comment | LLM judge comment | Difference categories |
|---|---|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🔵🟢🟢 | 🔵🟢🟢 🔴🟢🟢 |  |  |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🟢🟢 | 🟢🔵🟢 🟢🔵🔵 |  |  |  |
| 1-d | Are the data correctly split into trials? | 🔵🔵🔵 🟢🔵🟢 | 🔵🔴🟡 🟢🔵🔵 | 🟡🔴🔴 🟡🟡🟡 | 🔴🔴🔴 🔴🔴🔴 | Large variation in how trial boundaries are defined; multiple solutions are acceptable. |  |  |
| 1-e | How are trials filtered based on quality controls? | 🟡🟡🟡 🔵🟢🟢 | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟡🟢🟡 | 🔴🔴🟡 🔴🔴🔴 | Filtering out extremely long "trials" where the animal is stationary is required; this was only implemented in the 3 codex trials. |  | `FILTER=3` |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟡 🔴🟡🟢 | 🔴🔴🔴 🔴🔴🔴 | The neural data requires little processing beyond combining the imaging planes. The agents tend to store the data as float16, which is unnecessary. |  |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🔵🟢🔵 🟡🟡🔴 | 🔵🟢🔵 🟡🟡🟡 | 🔴🟢🔴 🔴🔴🔴 | 🔴🟢🔴 🔴🔴🔴 | The codex agents used very aggressive selectivity-based filters; one trial even dropped V1 entirely, which is hard to justify. |  | `FILTER=3` |
| 2-d | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟡🟡 🟡🟢🟡 | 🟣🟡🟡 🟡🟣🟣 | 🟡🔴🟡 🟡🟡🟢 | 🔴🔴🔴 🔴🟡🔴 | Some agents didn't pick the correct end of trial. But the instruction and the data structure is pretty clear on this, so not sure why it happened. |  | `MISC=3` |
| 2-e | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🔵 🟢🟡🟢 |  |  |  |
| 3-a | What variables in the raw data is `input` *time_to_sound_cue* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🟢🔵 | 🟢🟢🟡 🔵🟢🔵 | 🟡🔵🔵 🔵🟡🔵 |  |  |  |
| 3-b | What processing is involved in computing `input` *time_to_sound_cue*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🔵🔵 🔵🔵🔵 | 🔵🟡🟡 🔵🟡🔵 | 🟡🔴🟡 🔵🔴🔵 | Both solutions are valid - use frame index diffrence + frame rate, or use time stamp and convert |  |  |
| 3-c | How is `input` *time_to_sound_cue* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 4-a | What variables in the raw data is `input` *day_of_training* derived from? | 🟢🔴🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🔴🟢 🔵🔵🟢 | 🟢🔴🟢 🟢🟢🔴 | sess# can't be used since it's an index within an experiment type, and it resets |  |  |
| 4-b | What processing is involved in computing `input` *day_of_training*? | 🟡🔴🟢 🟡🟡🟡 | 🟢🟢🟢 🟢🟢🟢 | 🟡🔴🟡 🔵🔵🟡 | 🔴🔴🟢 🟡🔴🔴 | The wording is a bit ambiguous but we are asking for number of training days, not actual date difference. I don't think a typical neuroscientist will incorrectly interpret what we are asking for here. |  | `VARNAME=4` |
| 5-a | What variables in the raw data is `input` *time_since_trial_start* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🟢🔵 | 🟢🟡🟡 🔵🟡🔵 | 🟡🔵🔵 🔵🔵🔵 |  |  |  |
| 5-b | What processing is involved in computing `input` *time_since_trial_start*? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟢 🟢🟡🟢 | 🔵🟡🟡 🔵🟡🔵 | 🟡🟡🟡 🔵🔴🔵 |  |  |  |
| 5-c | How is `input` *time_since_trial_start* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 6-a | What variables in the raw data is `input` *reward_availability* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 6-b | What processing is involved in computing `input` *reward_availability*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 7-a | What variables in the raw data is `output` *visual_stimulus* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 7-b | What processing is involved in computing `output` *visual_stimulus*? | 🔵🔴🔵 🔵🔵🔵 | 🔵🟡🔵 🔵🔵🔵 | 🔴🔴🔴 🟡🔴🟡 | 🔵🔴🔴 🔵🔴🔴 | 5/6 agents used the fine stimulus category; 1/6 agent did a strange mapping (e.g., rock to circle) |  | `MISC=1` |
| 8-a | What variables in the raw data is `output` *licking* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🟢 |  |  |  |
| 8-b | What processing is involved in computing `output` *licking*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🔵🔵 | 🔵🟢🟡 🟢🟢🟢 | 🟡🟢🟡 🟢🔵🔵 |  |  |  |
| 8-c | How is `output` *licking* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  | The codex judge applies the comparison to the reference paper too literally. |  |
| 9-a | What variables in the raw data is `output` *position* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟢 🟢🟢🟢 |  |  |  |
| 9-b | What processing is involved in computing `output` *position*? | 🟢🔵🔴 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🟡 🟢🟢🟢 | 🟢🔴🔴 🟢🟢🟢 | Two claude trials did not handle the bin edges correctly with respect to the grey-corridor region (one collapsed grey-space frames into the last texture bin; the other added a non-standard 5th bin). |  | `PROCESS=2` |
| 9-d | How is `output` *position* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 10-a | What variables in the raw data is `output` *running_speed* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 10-b | What processing is involved in computing `output` *running_speed*? | 🔵🟡🟡 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔴🔴🔴 🟡🔵🟡 | 🔴🔴🔴 🟡🔴🔴 | In 2/6 trials the agent did not properly handle the speed-bin edges for frames near zero, leading to heavy stationary-frame contamination of the lower bins. |  | `PROCESS=2` |
| 10-d | How is `output` *running_speed* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |  |
| 11 | How are minor mistakes in the data, e.g. missing data, handled? | 🔵🔵🔵 🟢🟢🔵 | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🔵🟢🟢 | 🟡🟡🟡 🟡🟡🔴 |  |  |  |
| 12-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟡 🔵🔵🔵 | 🔵🟢🟢 🟢🟢🟡 | 🔵🟢🟢 🟢🔵🟡 |  |  |  |
| 12-b | What loops in the code could have been vectorized to improve efficiency? | 🔵🔵🔵 🔵🔵🔵 | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🟡 🟢🔵🟡 |  |  |  |
| 12-c | What processing does the code repeat multiple times? | 🔵🔵🔵 🔵🟡🔵 | 🟡🟡🔵 🔵🟡🟡 | 🟢🟢🟢 🟢🟢🟢 | 🟡🔴🟡 🟡🟣🟡 | All solutions use a multi-pass approach for building metadata, quartiles, etc. 1/6 trials repeatedly does I/O for the same variables instead of caching them in RAM. |  |  |
| 12-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🔵🔵🔵 🔵🔵🔵 | 🔵🟢🟡 🟢🔵🟢 | 🟡🟡🟢 🟡🟣🔴 |  |  |  |
| 12-e | How is memory usage optimized? | 🟢🟢🟢 🟢🟢🟢 | 🔵🔵🔵 🔵🔵🔵 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |  |
