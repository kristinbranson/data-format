# Evaluation Report — chen2024

## Summary

- Dataset: **chen2024**
- Questions covered: 25
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
One major failure case:
- Choice derivation: the most accessible data source is the *instructed* lick direction (the correct/required side), not the actual behavioral response. 2/6 trials used the instructed direction directly as the choice output, which is incorrect. The other 4 either combined `trial_instruction` with `outcome` (hit → instructed; miss → opposite) or read the per-trial lick events directly. This is the same trap as hasnain2024.

A few notable observations on variability across agent solutions:
- Explicit vs open-ended specs drive variability: when the task spec is explicit (e.g., "use 50 ms non-overlapping bins" for the neural binning), all 6 agents converge on the same solution. When the spec is open-ended (e.g., tongue-position preprocessing), the agents produce quite different pipelines — for example, different occlusion handling (impute vs NaN-out vs ignore), different velocity-outlier policies (5σ interpolation vs none), and different per-bin sampling strategies (mean vs nearest vs last-frame).
- The codex agents store firing rates as `float16`, roughly halving the pickle size (~4 GB vs ~10 GB). Acceptable here, but an unusual design choice that the task instructions did not constrain.

#### LLM as Judge
- The LLM judges sometimes rate functionally identical solutions inconsistently across trials — most visibly for Q 3-a, where two trials used the same (incorrect) instructed-direction approach but the judges flagged only one of them and rated the other as *match*. In these cases, the judge produces reasonable-sounding justifications with the opposite underlying logic.

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🔵🟢🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟡 | 4/6 trials used the `pynwb` interface; 2/6 used `h5py` directly. Unclear what drove the difference compared to the sosa2024 dataset. |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-c | How are the data split into sessions? | 🟡🟢🟡 🟢🟢🟢 | 🟢🟢🟡 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Performance-based session filtering is not necessary. |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟡🟢🟢 | 🟢🟢🟢 🟡🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-e | How are trials filtered based on quality controls? | 🟢🟢🟢 🔵🔵🔴 | 🟢🟢🟡 🟡🟢🟡 | 🟢🟡🟢 🟡🟡🟡 | Slightly different filtering procedures across agents; 1/6 was incorrect (used the observation window from only a *single* good unit). |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟢 🟢🟢🟢 | Codex cast the data to float16; not strictly necessary, but acceptable for this data type. |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | 🟡🟢🟢 🟢🟢🟡 | All agents apply good-unit filtering; the claude agents add an additional histology-based filter. |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟢 🟢🟢🟢 | 50 ms binning per the task instructions — no variability across agents, presumably because the spec is explicit. |  |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | All agents correctly aligned the data using the go-cue onset time. |  |
| 3-a | What variables in the raw data is `output` *choice* derived from? | 🔴🔴🟢 🔵🟢🟢 | 🟢🟢🟢 🟡🟢🟢 | 🟢🔴🟡 🟡🟢🟢 | 2/6 trials used the *instructed* lick direction instead of the *actual* behavioral response. | The LLM judges failed to flag the trials where this mistake was made. |
| 3-b | What processing is involved in computing `output` *choice*? | 🔴🔴🟡 🔵🟢🟢 | 🟢🟢🟡 🟡🟢🟡 | 🟢🔴🟡 🟡🟡🟡 | This part is also tricky — the agent must derive the actual behavioral response and additionally handle the case where the animal did not respond. |  |
| 4-a | What variables in the raw data is `output` *outcome* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 4-b | What processing is involved in computing `output` *outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-a | What variables in the raw data is `output` *early_lick* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-b | What processing is involved in computing `output` *early_lick*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 6-a | What variables in the raw data is `output` *tongue_y_position* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 6-b | What processing is involved in computing `output` *tongue_y_position*? | 🔵🔵🟡 🟡🟢🟢 | 🟢🟡🟡 🟢🟢🟢 | 🟡🟡🟢 🟢🟢🟢 | Agents differ in how they handle issues in the tracking data (e.g., occlusion, velocity outliers). |  |
| 6-c | How is `output` *tongue_y_position* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Nominally identical procedure across all agents; slight variation in implementation details. |  |
| 7 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟢 🔵🟢🟢 | 🟢🟡🟡 🟡🟢🟢 | 🟡🟡🟡 🟡🟡🟡 |  |  |
| 8-a | What are the most time-consuming steps of the code? | 🔵🔵🔵 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | The claude variants are less efficient — they keep a per-trial spike-binning loop instead of vectorizing across trials. |  |
| 8-b | What loops in the code could have been vectorized to improve efficiency? | 🔵🔵🔵 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-c | What processing does the code repeat multiple times? | 🟢🟢🔵 🟢🔵🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🔵🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-e | How is memory usage optimized? | 🟢🟢🟢 🔵🔵🔵 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ | Codex used float16, which is unnecessary but acceptable for this kind of data. |  |
