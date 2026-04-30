# Evaluation Report — zhang2025

## Summary

- Dataset: **zhang2025**
- Questions covered: 26
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🔴🔴🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🔴🔴🟢 🟢🟢🟢 | All runs directly read the files in the cache directory, bypassing the ONE API interface. 2/6 trials didn't use the correct session number information. |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Identify subjects from either the csv file or the filepath |  |
| 1-c | How are the data split into sessions? | 🟢🔵🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 1/6 trial the agent didn't use the session info from the CSV file |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-e | How are trials filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟡🟢🟢 |  |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | All solution implemented the merge + binning steps correctly |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟡🟡🟡 🟢🟢🟢 | 🟢🟢🟢 🟡🟢🟡 | 🟢🟢🟢 🟡🔴🟡 | Cluade did not implement the quality (QC) filtering |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 |  |  |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 |  |  |
| 3-a | What variables in the raw data is `output` *choice* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 3-b | What processing is involved in computing `output` *choice*? | 🔴🔴🔴 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔴🟢 🟢🟢🟢 | There is a small trap: in the original data, +1 is the left choice, and -1 is the right choice. The solution from the claude agents are sign flipped | Only one of the judge run caught the mistake |
| 4-a | What variables in the raw data is `output` *prior_probability_left* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 4-b | What processing is involved in computing `output` *prior_probability_left*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-a | What variables in the raw data is `output` *wheel_speed* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-b | What processing is involved in computing `output` *wheel_speed*? | 🟢🔴🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 | 🟢🔴🟢 🟢🟢🟢 | 1/6 trial did upsampling (to 1 kHz) + gradient with NO filtering, which is quite bad. The solutions from other trials are sensible |  |
| 5-c | How is `output` *wheel_speed* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 |  |  |
| 6-a | What variables in the raw data is `output` *whisker_motion_energy* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 6-b | What processing is involved in computing `output` *whisker_motion_energy*? | 🟡🟡🔵 🟡🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Incorrect trimming causes whisker ME data to misalign with neural and behavior data in time |  |
| 6-c | How is `output` *whisker_motion_energy* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 |  |  |
| 7 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟢 🟡🟢🟢 |  |  |
| 8-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-b | What loops in the code could have been vectorized to improve efficiency? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-c | What processing does the code repeat multiple times? | 🟢🟢🔵 🟢🟢🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-e | How is memory usage optimized? | 🔵🟢🟢 🔵🔵🟡 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
