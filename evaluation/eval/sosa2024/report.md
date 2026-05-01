# Evaluation Report — sosa2024

## Summary

- Dataset: **sosa2024**
- Questions covered: 39
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
- 🟣 Some agents implemented more detailed data filtering (e.g., lick-detection failure and interneuron exclusion) based on the descriptions in the paper and the reference code. (The agents are detail-oriented when the associated code and text are available.)
- A key issue in this dataset was that most agents adopted a hard-coded "30-trial switch" rule for the reward zone, based on the paper description. In general, agents are less inclined than an experienced researcher to verify such assumptions against the data and write defensive code.

#### LLM as Judge
- There is substantial inconsistency in the ratings for nearly identical solutions across runs (e.g., 2-c, 3-a, 7-a).
- The judges can be good at catching detailed mistakes, but sometimes miss things as well.

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🔵🟢 | All agents used `h5py` directly instead of the `pynwb` interface to read the data. |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 |  |  |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟢🟢🟢 | 🟨🟢🟨 🟢🔵🟢 | 🟡🟡🔴 🟢🔴🟢 | Slightly different handling of potential mismatches between `trial_start` and teleport events. | Claude correctly flagged some implementations as less robust. |
| 1-e | How are trials filtered based on quality controls? | 🟣🔵🟣 🔵🔵🟣 | 🔵🔴🟡 🟡🔴🔴 | 🔴🔴🔴 🔴🔴🔴 | Some agents implemented additional filtering based on a detail in the paper's methods. |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🔴 🟢🔴🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🔵🔴🟢 | 🔵🟡🟣 🟢🟡🟡 | 🟡🔴🔴 🔵🔴🟢 |  |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟣🟣🟣 🟢🟢🟢 | 🟣🟡🟣 🟢🟢🟢 | 🟡🔴🔴 🟢🟢🟡 |  | Claude judge gave inconsistent ratings for the same solution. |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🔴🟢 | 🟢🟢🟢 🟢🔴🟢 | 🟢🟢🟢 🔵🔴🟣 | A critical mistake — but only 1/6 agents made it, although the wording in the data description is somewhat confusing. | Both judges caught the mistake. |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | No timestamp is provided, so no additional alignment is needed. |  |
| 3-a | What variables in the raw data is `input` *Time from start of trial in seconds* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🔵 🟢🟢🟢 | 🟡🔴🔴 🔵🔴🔵 |  | Inconsistent ratings from the LLM judges for the same solution. |
| 3-b | What processing is involved in computing `input` *Time from start of trial in seconds*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🔵 🟢🟢🟢 | 🟡🔴🔴 🟢🔴🟢 |  |  |
| 3-c | How is the `input` *Time from start of trial in seconds* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🔵 🟡🔵🔵 |  |  |
| 4-a | What variables in the raw data is `input` *Environment type* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | 🟢🔴🟢 🔴🟢🟢 |  |  |
| 4-b | What processing is involved in computing `input` *Environment type*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🔵 🟢🟢🔵 | 🔵🔴🔵 🔴🔵🔵 |  |  |
| 5-a | What variables in the raw data is `input` *Trial number* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🟢 🟢🟢🟡 |  |  |
| 5-b | What processing is involved in computing `input` *Trial number*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🟢 🟢🟢🟡 | Some agents cast between `float64` and `float32` for no apparent reason. |  |
| 6-a | What variables in the raw data is `input` *Previous trial outcome* derived from? | 🟢🔵🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🟡 |  |  |
| 6-b | What processing is involved in computing `input` *Previous trial outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🔵 | 🟢🟢🟢 🟣🟢🟡 |  |  |
| 7-a | What variables in the raw data is `output` *Distance to reward zone* derived from? | 🟡🟡🟢 🟡🟢🟡 | 🔵🟡🟡 🟡🟢🟡 | 🔴🔴🔴 🔵🟡🟣 | Agents didn't verify the "30-trial switch rule" against the data — the correct approach is to identify the reward zone from the data rather than using a hard-coded switch time. | Claude caught some of the potential problems but missed others. |
| 7-b | What processing is involved in computing `output` *Distance to reward zone*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 7-c | How is `output` *Distance to reward zone* aligned with the neural data? | 🟢🟢🟢 🟢🔴🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-a | What variables in the raw data is `output` *Absolute position* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-b | What processing is involved in computing `output` *Absolute position*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟡🟢 | 🟢🟢🟢 🔴🔵🔴 |  |  |
| 8-c | How is `output` *Absolute position* aligned with the neural data? | 🟢🟢🟢 🟢🟡🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 9-a | What variables in the raw data is `output` *Lick* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 9-b | What processing is involved in computing `output` *Lick*? | 🟢🟢🟢 🟢🟡🟢 | 🟣🟡🟡 🟢🟢🟢 | 🟡🟡🟡 🔵🔵🔵 |  |  |
| 9-c | How is `output` *Lick* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🟢 |  |  |
| 10-a | What variables in the raw data is `output` *Reward zone location* derived from? | 🟡🟡🟢 🟡🟢🟡 | 🔵🟡🟡 🟡🟢🟡 | 🔴🔴🔴 🔵🟡🟣 | Same issue as 7-a. |  |
| 10-b | What processing is involved in computing `output` *Reward zone location*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🟡 🟡🔵🟡 | 🔴🔴🔴 🔵🟡🟣 |  |  |
| 11-a | What variables in the raw data is `output` *Reward outcome* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🟢 🟢🔵🟡 |  |  |
| 11-b | What processing is involved in computing `output` *Reward outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟡 | 🔵🟢🟢 🟣🟢🟡 |  |  |
| 12 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟣🟢 🟣🟣🟣 | 🟢🔵🔵 🔵🟡🔴 | 🟡🟡🟡 🟡🔵🟡 | Some agents implemented an additional lick-quality filter. |  |
| 13-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 | 🟢🔵🔴 🟢🟢🟢 |  |  |
| 13-b | What loops in the code could have been vectorized to improve efficiency? | 🟢🔵🔵 🔵🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🔵 🟢🟢🟢 | Some per-trial loops are unnecessary. |  |
| 13-c | What processing does the code repeat multiple times? | 🟢🟢🔵 🟢🟢🟢 | 🔵🔵🟢 🟢🟢🟢 | 🟢🔵🔵 🟢🟢🟢 |  |  |
| 13-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟣 🔵🟢🟢 | 🟢🔵🔴 🟢🔵🟢 |  |  |
