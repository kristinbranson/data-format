# Evaluation Report — zhong2025

## Summary

- Dataset: **zhong2025**
- Questions covered: 27
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
- This dataset has a custom format with most of the information contained in nested Python dictionaries and key-value pairs. The agents were generally very good at figuring out the data structure and where to find the relevant information.
- The agents made a few (strange?) mistakes on a subset of trials for which I could not find an obvious explanation — e.g., dropping V1 from the analysis, applying a very strict d-prime filter to select neurons, and merging stimulus categories that are not visually similar (rock and circle).
- Another problem is setting the bin edges incorrectly for running speed (due to a large number of stationary frames), despite the agents themselves explicitly reporting that the resulting bins contain a heavily skewed proportion of the data.

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-d | Are the data correctly split into trials? | 🔵🔵🔵 🟢🔵🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔴🟢 🟢🟡🟢 | Large variation in how trial boundaries are defined; multiple solutions are acceptable. |  |
| 1-e | How are trials filtered based on quality controls? | 🟡🟡🟡 🔵🟢🟢 | 🟢🟢🟡 🟡🟢🟢 | 🟢🟢🔴 🟡🟢🟢 | Should filter out extremely long "trials" where the animal is stationary; this was only implemented in the 3 codex trials. |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟡 🟡🟢🟡 | 🟡🟡🔴 🟡🟡🔴 | The neural data requires little processing beyond combining the imaging planes. The agents tend to store the data as float16, which is unnecessary. |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🔵🟢🔵 🟡🟡🔴 | 🟢🟢🔵 🟡🟡🟡 | 🟢🟢🔴 🟡🔴🔴 | The codex agents used very aggressive selectivity-based filters; one trial even dropped V1 entirely, which is hard to justify. |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🔴 🟢🟢🟢 |  |  |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🔴 🟢🔴🟢 |  |  |
| 3-a | What variables in the raw data is `output` *visual_stimulus* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 3-b | What processing is involved in computing `output` *visual_stimulus*? | 🟢🔴🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡⚫ 🟢🟢🟢 | 1/6 trials remapped and merged stimulus categories (e.g., rock→circle, wood→leaf) for no apparent reason. |  |
| 4-a | What variables in the raw data is `output` *licking* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟡 🟢🟢🟢 |  |  |
| 4-b | What processing is involved in computing `output` *licking*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢⚫ 🟢🟢🟢 |  |  |
| 4-c | How is `output` *licking* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🔴 🟢🟢🟢 |  | The codex judge applies the comparison to the reference paper too literally. |
| 5-a | What variables in the raw data is `output` *position* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-b | What processing is involved in computing `output` *position*? | 🟢🔵🔴 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔴⚫ 🟢🟢🟢 | Two claude trials did not handle the bin edges correctly with respect to the grey-corridor region. |  |
| 5-c | How is `output` *position* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔴🔴 🟢🟢🟢 |  |  |
| 6-a | What variables in the raw data is `output` *running_speed* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 6-b | What processing is involved in computing `output` *running_speed*? | 🔵🟡🟡 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | 🟢🔴⚫ 🟢🟢🟢 | In 2/6 trials the agent did not properly handle the speed-bin edges for frames with near zero speed. |  |
| 6-c | How is `output` *running_speed* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🔴 🟢🟢🟢 |  |  |
| 7 | How are minor mistakes in the data, e.g. missing data, handled? | 🔵🔵🔵 🟢🟢🔵 | 🟢🟢🔵 🟢🟢🟢 | 🟢🟡🟢 🟡🟡🟢 |  |  |
| 8-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-b | What loops in the code could have been vectorized to improve efficiency? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-c | What processing does the code repeat multiple times? | 🔵🔵🔵 🔵🟡🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | All solutions use a multi-pass approach for building metadata, quartiles, etc. 1/6 trials repeatedly does I/O for the same variables instead of caching them in RAM. |  |
| 8-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟡🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-e | How is memory usage optimized? | 🟢🟢🟢 🟢🟢🟢 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
