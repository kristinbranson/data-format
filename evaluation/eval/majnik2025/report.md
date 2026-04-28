# Evaluation Report — majnik2025

## Summary

- Dataset: **majnik2025**
- Questions covered: 21
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
- The agents did a good job overall on this relatively simple dataset.
- The one tricky problem is missing frames in the motion-energy data. The correct approach is to identify the missing frames from the timestamps and interpolate at the correct positions. Agents implemented this correctly in 4/6 runs and incorrectly in 2/6 runs.
- In 5/6 runs the agents used the `suite2p` package for the calcium-data preprocessing (1/6 wrote the code from scratch instead), but only 2/6 used CUDA to speed up the computation.

#### LLM as Judge
- The Claude judge is quite inconsistent on this dataset, sometimes giving very different ratings (ranging from "better" to "incorrect") for the exact same solution across trials.

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟣 | 🟢🟡🟢 🔵🔵🔴 |  |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 |  |  |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🔵 |  |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟢🟢🟢 | 🟣🔵🟡 🟣🔵🟣 | 🔴🔴🔴 🟣🔴🔴 | The trial length is underspecified in the instructions; all agents adopted the paper's two-minute trial length. | Judges are inconsistent despite all agent runs producing the same solution. |
| 1-e | How are trials filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🔴 |  |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟣🟢🟢 | 🟢🟢🟢 🟢🔵🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🔵🟢🟢 🟢🟢🟢 | 🔵🟡🟡 🟣🔵🟣 | 🔴🔴🟢 🟣🔵🔴 | One agent skipped `suite2p` preprocessing and wrote its own code instead. | Some agents added the paper's temporal binning step; LLM judge ratings are inconsistent. |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🔵 |  |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟣🔵🔴 🟣🔵🟣 | 🔴🔴🔴 🟣🔴🔴 | All agents implemented the paper's 10-frame binning strategy, which is acceptable. | LLM judge ratings are inconsistent, ranging from "better" to "incorrect" for the same binning strategy. |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔴🟢🟢 🟣🔴🔴 |  |  |
| 3-a | What variables in the raw data is `input` *Time* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟡 🟢🟢🟢 | 🟢🔵🟢 🟢🔴🔴 |  |  |
| 3-b | What processing is involved in computing `input` *Time*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟡 🟣🟣🟣 | ⚫🔴🔴 🟣🔴⚫ |  |  |
| 3-c | How is `input` *Time* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔴🟢🟢 🟣🔴🔴 |  |  |
| 4-a | What variables in the raw data is `output` *Motion energy* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟡 🟢🔵🔵 | 🟢🔴🔴 🟢🔴🔴 |  |  |
| 4-b | What processing is involved in computing `output` *Motion energy*? | 🟡🟡🟡 🟢🟢🟢 | 🟡🟡🔴 🟣🟡🟣 | ⚫🔴🔴 🔵🔴⚫ | Claude agents skipped normalization steps; Codex agents used min-max normalization. | Judge ratings are inconsistent for the same solutions. |
| 4-c | How is `output` *Motion energy* aligned with the neural data? | 🟢🔴🔴 🟢🟢🟢 | 🔵🟡🟡 🟣🔵🟣 | 🔴🔴🔴 🟣🔴🔴 | 2/6 incorrect solutions (did not attempt to identify missing frames); 4/6 correct solutions using a different approach to detect missing frames. | Judge ratings are inconsistent. |
| 7 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟡 🟢🟢🟢 | 🔵🔵🟡 🟣🟢🟣 | 🔵🟡🔴 🟣🔵🔴 |  |  |
| 8-a | What are the most time-consuming steps of the code? | 🔵🟢🟢 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Only two solutions used GPU/CUDA via `suite2p`. |  |
| 8-b | What loops in the code could have been vectorized to improve efficiency? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟪🟢🔵 | 🔵🔵🔵 🟣🔵🟢 |  | Some agents' solutions for detecting missing frames are more efficient. |
| 8-c | What processing does the code repeat multiple times? | 🟢🟢🟢 🟢🟢🔵 | 🟢🟢🟢 🟢🟢🟢 | 🔵🔵🟢 🔵🔵🔵 |  |  |
| 8-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🔴 🟢🟢🟢 | 🔵🔵🔵 🟡🔵🔵 |  |  |
