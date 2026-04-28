# Evaluation Report — sosa2024

## Summary

- Dataset: **sosa2024**
- Questions covered: 39
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🔵🔵🟢 | All agents used h5py instead of the pynwb interface to read the data |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 |  |  |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟢🟢🟢 | 🟨🟢🟨 🟢🔵🟢 | 🟡🟡🔴 🟢🔴🟢 | Slightly different handling of potential mismatch of trial_start with teleports | Claude identified some implementation that is less robust |
| 1-e | How are trials filtered based on quality controls? | 🟣🔵🟣 🔵🔵🟣 | 🔵🔴🟡 🟡🔴🔴 | 🔴🔴🔴 🔴🔴🔴 | Some agents implemented additional filtering based on a detail in the paper methods |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🔴 🟢🔴🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🔵🔴🟢 | 🔵🟡🟣 🟢🟡🟡 | 🟡🔴🔴 🔵🔴🟢 |  |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟣🟣🟣 🟢🟢🟢 | 🟣🟡🟣 🟢🟢🟢 | 🟡🔴🔴 🟢🟢🟡 |  | AI judege being inconsistent about the same solution |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🔴🟢 | 🟢🟢🟢 🟢🔴🟢 | 🟢🟢🟢 🔵🔴🟣 | Critical mistake albeit due to some confusion wording in the data, only 1/6 agent made the mistake | Both judges caught the mistake |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | no time stamp provided, no additional alignment needed |  |
| 3-a | What variables in the raw data is `input` *Time from start of trial in seconds* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🔵 🟢🟢🟢 | 🟡🔴🔴 🔵🔴🔵 |  | inconsistent rating from AI judges about the same solution |
| 3-b | What processing is involved in computing `input` *Time from start of trial in seconds*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🔵 🟢🟢🟢 | 🟡🔴🔴 🟢🔴🟢 |  |  |
| 3-c | How is the `input` *Time from start of trial in seconds* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🔵 🟡🔵🔵 |  |  |
| 4-a | What variables in the raw data is `input` *Environment type* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | 🟢🔴🟢 🔴🟢🟢 |  |  |
| 4-b | What processing is involved in computing `input` *Environment type*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🔵 🟢🟢🔵 | 🔵🔴🔵 🔴🔵🔵 |  |  |
| 5-a | What variables in the raw data is `input` *Trial number* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🟢 🟢🟢🟡 |  |  |
| 5-b | What processing is involved in computing `input` *Trial number*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🟢 🟢🟢🟡 | Agent sometime does casting between float64 and float 32 for no apperant reasons |  |
| 6-a | What variables in the raw data is `input` *Previous trial outcome* derived from? | 🟢🔵🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🟡 |  |  |
| 6-b | What processing is involved in computing `input` *Previous trial outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🔵 | 🟢🟢🟢 🟣🟢🟡 |  |  |
| 7-a | What variables in the raw data is `output` *Distance to reward zone* derived from? | 🟡🟡🟢 🟡🟢🟡 | 🔵🟡🟡 🟡🟢🟡 | 🔴🔴🔴 🔵🟡🟣 | Agent didn't check the "30-trial switch rule" against data, the correct solution is to identify the reward zone from data, instead of using a hard-coded switch time | Claude caught some potential problems but not others |
| 7-b | What processing is involved in computing `output` *Distance to reward zone*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 7-c | How is `output` *Distance to reward zone* thresholded into categories? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 7-d | How is `output` *Distance to reward zone* aligned with the neural data? | 🟢🟢🟢 🟢🔴🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-a | What variables in the raw data is `output` *Absolute position* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-b | What processing is involved in computing `output` *Absolute position*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟡🟢 | 🟢🟢🟢 🔴🔵🔴 |  |  |
| 8-c | How is `output` *Absolute position* thresholded into categories? | 🟢🟢🟢 🟢🟢🟢 | 🟡🔴🟡 🟡🔴🟡 | 🟣🔴🟣 🔴🟣🔴 |  | Different choices in choosing bin edges but are all valid solution, claude judge being too literal |
| 8-d | How is `output` *Absolute position* aligned with the neural data? | 🟢🟢🟢 🟢🟡🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 9-a | What variables in the raw data is `output` *Lick* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 9-b | What processing is involved in computing `output` *Lick*? | 🟢🟢🟢 🟢🟡🟢 | 🟣🟡🟡 🟢🟢🟢 | 🟡🟡🟡 🔵🔵🔵 |  |  |
| 9-c | How is `output` *Lick* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🔵🟢 |  |  |
| 10-a | What variables in the raw data is `output` *Reward zone location* derived from? | 🟡🟡🟢 🟡🟢🟡 | 🔵🟡🟡 🟡🟢🟡 | 🔴🔴🔴 🔵🟡🟣 | Similar problem to 7-a |  |
| 10-b | What processing is involved in computing `output` *Reward zone location*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🟡 🟡🔵🟡 | 🔴🔴🔴 🔵🟡🟣 |  |  |
| 11-a | What variables in the raw data is `output` *Reward outcome* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 🟢🟢🟢 🟢🔵🟡 |  |  |
| 11-b | What processing is involved in computing `output` *Reward outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟡 | 🔵🟢🟢 🟣🟢🟡 |  |  |
| 12 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟣🟢 🟣🟣🟣 | 🟢🔵🔵 🔵🟡🔴 | 🟡🟡🟡 🟡🔵🟡 | additional lick quality filter implemented by some agents |  |
| 13-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🟢 🟢🟢🟢 | 🟢🔵🔴 🟢🟢🟢 |  |  |
| 13-b | What loops in the code could have been vectorized to improve efficiency? | 🟢🔵🔵 🔵🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🔵 🟢🟢🟢 | Some per-trial loop is not necessary |  |
| 13-c | What processing does the code repeat multiple times? | 🟢🟢🔵 🟢🟢🟢 | 🔵🔵🟢 🟢🟢🟢 | 🟢🔵🔵 🟢🟢🟢 |  |  |
| 13-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟣 🔵🟢🟢 | 🟢🔵🔴 🟢🔵🟢 |  |  |
