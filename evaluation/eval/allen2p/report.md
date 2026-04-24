# Evaluation Report — allen2p

## Summary

- Dataset: **allen2p**
- Questions covered: 31
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed better than the human.

## Comments

#### Agent Performance
- The agents did a good job overall on this task.
- The agents tend to avoid the AllenSDK interface available to them and prefer to "write their own code" with the NWB files. This is consistent with my impression that agents are prone to dig into code rabbit holes — it just makes the code a bit messy.
- See 1-c, 2-a–d, 4-a, and 9-c for interesting failure cases. There's a recurring theme of agents making strange choices on resampling, time resolution, and time bin size (out of 6 runs, 2 are really bad decisions, 3 are ok choices, and 1 matches the human solution).

#### LLM as Judge
- In general, the LLM judges evaluate the code in a more literal sense — whether it matches the reference solution. Most of the disagreements are cases where I (human) accepted solutions that were different but valid. The Codex judge in this case is close to unusable for being quite extreme on this axis.
- It is hard for LLM judges to evaluate decisions in this relatively open-ended task, since they lack the relevant domain knowledge and context.
- There are a couple of cases where the Claude judge caught minor mistakes that I overlooked as a human judge (this seems to be a general trend: LLMs are better at the details of the code, while I am better at the "big picture" stuff).

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🔵🔵🔵 🔵🔵🔵 | 🔵🔵🔵 🔵🔵🟨 | 🔴🔴🔴 🔴🔴🔴 | Every agent read the data directory directly, using h5py to read the NWB files. The agents had access to both the notebook example code and the data directory, but didn't follow the notebook to use the AllenSDK interface. | The Claude judge caught a minor mistake that I overlooked: one of the solutions was not properly filtering the data based on `project_code`. |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🔵🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Used correct information |  |
| 1-c | How are the data split into sessions? | 🔴🔴🔴 🔴🔴🔴 | 🟡🟡🟡 🟡🟡🟡 | 🔴🔴🔴 🔴🔴🔴 | The Allen dataset has an unusual setup where each session, identified by `ophys_session_id`, is split into multiple `ophys_experiment_id`s for different imaging planes in the same session. This seems to have thrown off all the agents — none of them recombined the data based on the session ID. This is explicitly shown in the tutorial code, which the agents had been instructed to read. |  |
| 1-d | Are the data correctly split into trials? | 🟢🟡🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 | 🔴🔴🟢 🟢🔵🟢 |  |  |
| 1-e | How are trials filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟡🟢🟡 | 🔴🔵🟡 🟡🟡🟡 | All agents followed the main instruction; some introduced additional filtering that is reasonable. |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🔵 🔵🔵🔵 | 🟢🟢🔴 🟡🔴🟡 | 🟢🟢🔴 🔴🔴🔴 | Agents seem to prefer the event data (which is technically ok), but the code and paper example use dF/F instead. | It is hard for the LLM judges to tell whether using event data instead of dF/F is reasonable here (additional context and domain knowledge required). |
| 2-b | How is the `neural` data processed? | 🟢🔴🟢 🟡🔵🔵 | 🟢🔴🟡 🟡🔴🟡 | 🔴🔴🔴 🔴🔴🔴 | Only one agent produced the "really" correct solution — since the experiment timestamps are already aligned, there is no need to resample. Two agents made some very wrong choices on time bin size. |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟢 🟢🟢🟢 | 🟢🟡🔴 🔵🔵🔴 | Some agents used an additional ROI filter based on the `valid_roi` flag. |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🔴🔵 🟡🔵🔵 | 🟡🔴🟡 🟡🔴🟡 | 🟢🔴🔴 🔴🔴🔴 | The data is ~11 Hz, so some agents resampling to a 30 ms time bin is ok, but in principle no resampling is needed. Two agents made some really bad choices (2-b). |  |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🔵🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟡🟡 | 🟢🔴🟢 🟢🟢🔴 |  |  |
| 3-a | What variables in the raw data is `output` *Running speed* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 3-b | What processing is involved in computing `output` *Running speed*? | 🟢🔴🟢 🟢🟢🟢 | 🟨🟡🟡 🟡🟢🟢 | 🔴🔴🔴 ⚫🔴🔴 |  |  |
| 3-c | How is `output` *Running speed* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟢 🟢🟢🟢 | 🟢🔴🔴 🔴🔴🔴 |  |  |
| 4-a | What variables in the raw data is `output` *Pupil diameter* derived from? | 🟡🟡🟡 🟡🔵🔵 | 🟡🟡🔴 🟡🟡🔴 | 🔴🟡🔴 🔴🔴🔴 | Agents really like to compute pupil size from area. |  |
| 4-b | What processing is involved in computing `output` *Pupil diameter*? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟡 🟡🟡🟡 | 🔴🔴🔴 ⚫🔴🔴 |  |  |
| 4-c | How is `output` *Pupil diameter* aligned with the neural data? | 🟢🔴🟢 🟢🟢🟢 | 🟢🔵🟢 🟢🟢🟢 | 🟢🔴🔴 🔴🔴🔴 |  |  |
| 5-a | What variables in the raw data is `output` *Image name* derived from? | 🟢🟢🟢 🔵🔵🔵 | 🔵🔵🔵 🟡🔵🟡 | 🔴🔵🔴 🔴🟡🔴 | Codex agents dig deep into the data structure to find the image ID info instead of using the data table. |  |
| 5-b | What processing is involved in computing `output` *Image name*? | 🟢🟢🟢 🟢🟢🟢 | 🔵🟨🟢 🟡🔵🟡 | 🔴🟡🟡 ⚫🟡🔴 |  |  |
| 5-c | How is `output` *Image name* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟢 🟢🟢🟢 | 🔴🔵🟡 🔴🟡🔴 |  |  |
| 6-a | What variables in the raw data is `output` *Image change* derived from? | 🔵🔵🟢 🔵🔵🔵 | 🔵🔵🔵 🔵🟡🟡 | 🔴🔵🟡 🔴🔴🟡 | Some solutions included the grey screen as an extra image category. |  |
| 6-b | What processing is involved in computing `output` *Image change*? | 🟢🟢🟢 🟢🟢🟢 | 🟨🔵🟢 🟡🟡🟡 | 🔴🔵🟡 ⚫🔴🟡 |  |  |
| 6-c | How is `output` *Image change* aligned with the neural data? | 🟢🔵🟢 🟢🟢🟢 | 🟢🔵🟢 🟢🟢🟢 | 🔴🔵🟡 🔴🟡🔴 |  |  |
| 7-a | What variables in the raw data is `output` *Trial outcome* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 7-b | What processing is involved in computing `output` *Trial outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 ⚫🟢🟢 |  |  |
| 7-c | How is `output` *Trial outcome* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
| 8 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🔵🟢 🟡🟢🟡 | 🔴🟡🔵 🟡🟡🟡 | Some scripts are missing explicit error handling. |  |
| 9-a | What are the most time-consuming steps of the code? | 🟡🟡🟡 🟡🟡🟡 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🔵 🔵🔵🟡 |  |  |
| 9-b | What loops in the code could have been vectorized to improve efficiency? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🔵 🔵🟢🔵 |  |  |
| 9-c | What processing does the code repeat multiple times? | 🟡🟡🔴 🟡🟡🟡 | 🟢🟣🔴 🟢🟢🟡 | 🔴🔴🔴 🟡🔴🟡 | 5/6 did a two-pass approach which is inefficient; 1/6 did a three-pass approach which is just wrong. | The LLM judge seems to have completely misunderstood this question. |
| 9-d | What unnecessary processing does the code do that is discarded in downstream analyses? | ⚪⚪⚪ ⚪⚪⚪ | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
| 9-e | How is memory usage optimized? | 🟢🟢🟢 🟢🟢🟢 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
