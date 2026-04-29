# Evaluation Report — hasnain2024

## Summary

- Dataset: **hasnain2024**
- Questions covered: 31
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
A few interesting concern / failure cases in this dataset are worth noting:
- Lick direction: the most accessible data source is the *instructed* (correct) lick direction for each trial — atypical, since usually the behavioral response itself is directly available. One agent derived the actual response direction by combining instructed direction with trial correctness (e.g., hit vs. miss); another used lick event data to derive the first lick direction. 4/6 agents got it wrong.
- Variability in the preprocessing pipeline:
    - Velocity outputs (tongue and paw): deriving these requires several intermediate preprocessing steps. The agents were quite variable here (this question is more open-ended, despite the availability of reference code). None of the agents implemented the sophisticated PCA-based procedure from the original paper, and each run used slightly different solutions and parameter choices.
    - Spike preprocessing (probe → spike train): similarly involves several preprocessing steps, which vary across agents. This variability doesn't show up obviously in the ratings, since the choices are all equally valid.
- Reference code bug: there is a minor bug in the paper's code (7-b, baseline subtraction). It was *replicated* by 1/6 runs, corrected in 3/6 runs, and skipped entirely in 2/6 runs.

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟡🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟢 🟢🟡🟢 | All solutions handled the mix of data formats correctly; 1/6 didn't load the full dataset. |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟡 🟢🟢🟢 | 🟢🟢🟢 🟢🟡🟢 |  | LLM judge flagged the extra subject found by the code, but was inconsistent across runs. |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Session structure is very simple. |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Slightly different exclusion procedures across agents. |  |
| 1-e | How are trials filtered based on quality controls? | 🟢🔵🔵 🟢🟢🟢 | 🟡🟡🔴 🟢🟢🟢 | 🟡🔴🔴 🟢🟢🟡 | Some minor differences in filtering decisions. |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟡🟢🟡 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Overall correct solutions, but most didn't handle the dual-probe sessions correctly. |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟡 🟢🟡🟢 | 🟢🟢🟢 🟡🟢🟢 | Small differences in preprocessing parameters, but all are valid. Agents were able to follow the reference solution using the paper's preprocessing code. | Judge decisions are inconsistent across runs. |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟢🟢🔵 🔵🔵🟢 | 🟡🟡🟡 🟢🟢🟢 | 🟢🟢🟡 🟢🟢🟢 |  |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟢🟡 🟢🟡🟢 | 🟢🟢🟡 🟢🔴🟢 | Two different binning choices appear in the paper; both are valid. | LLM judges are very inconsistent regarding the time-bin choice. |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟡🟢 |  |  |
| 3-a | What variables in the raw data is `output` *lick_direction* derived from? | 🟢🔴🔴 🔴🟢🔴 | 🟢🟢🟡 🟢🟢🟢 | 🟢🟢🟡 🟢🟢🟢 | The lick direction available in the data is the correct/instructed direction. One agent derived the actual response direction by combining instructed direction with trial correctness; another used `bp.ev.Lick` to derive the first lick direction. 4/6 agents got it wrong. | The LLM judge only flagged one of the incorrect solutions, missing the others. |
| 3-b | What processing is involved in computing `output` *lick_direction*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 ⚫🟢🟢 | 🟢🟢🟡 🟢⚫🟢 |  |  |
| 4-a | What variables in the raw data is `output` *context* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 4-b | What processing is involved in computing `output` *context*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 ⚫🟢🟢 | 🟡🟢🟢 🟢⚫🟢 |  |  |
| 5-a | What variables in the raw data is `output` *outcome* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔴🟢 🟢🟢🟢 |  |  |
| 5-b | What processing is involved in computing `output` *outcome*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 ⚫🟢🟢 | 🟢🔴🟡 🟢⚫🟡 |  |  |
| 6-a | What variables in the raw data is `output` *tongue_velocity* derived from? | 🟡🟡🟡 🟡🟡🔵 | 🟡🟢🟢 🟢🟢🟢 | 🟡🟡🟢 🟡🟡🟡 | The paper used a sophisticated PCA-based procedure to estimate tongue velocity from multiple markers across both cameras. None of the agents came close; only one agent attempted to combine information from multiple cameras. |  |
| 6-b | What processing is involved in computing `output` *tongue_velocity*? | 🔵🔵🔵 🔵🔵🔵 | 🟡🟢🟡 ⚫🟢🟡 | 🟡🟢🟡 🔴⚫🟡 | Highly variable choices across agents, but there is no single definitive correct/incorrect solution. |  |
| 6-c | How is `output` *tongue_velocity* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 7-a | What variables in the raw data is `output` *paw_velocity* derived from? | 🟢🟡🟡 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟢 🟡🟡🟡 | 4/6 solutions used both top and bottom paw tracking features; only 1/6 scaled the velocity to physical units. | Claude judge rated all solutions as match and provided justifications for using either single or both features, suggesting it is poor at making consistent judgments here. |
| 7-b | What processing is involved in computing `output` *paw_velocity*? | 🟡🟢🟢 🟡🔴🟢 | 🟡🔴🔴 ⚫🟡🟢 | 🟡🟢🟡 🔴⚫🟡 | The paper's code has a bug in the baseline subtraction (x-axis baseline subtracted from both x and y velocity). One agent faithfully reimplemented the bug, 3/6 agents corrected it, and 2/6 agents skipped baseline subtraction altogether. |  |
| 7-c | How is `output` *paw_velocity* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟡 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-a | What variables in the raw data is `output` *motion_energy* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-b | What processing is involved in computing `output` *motion_energy*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 ⚫🟢🟢 | 🟢🟢🟢 🟢⚫🟢 |  |  |
| 8-c | How is `output` *motion_energy* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Most agents use the bitcode-derived timestamp for alignment, falling back to a hardcoded 0.5s shift (taken from the reference's tutorial code) when bitcode metadata is unavailable. |  |
| 9 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟡 🟢🟢🟢 |  |  |
| 10-a | What are the most time-consuming steps of the code? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 10-b | What loops in the code could have been vectorized to improve efficiency? | 🟡🟡🟡 🔵🟡🔵 | 🟢🟢🟢 ⚫🟢⚫ | 🟢🟢🟢 ⚫🟢⚫ | Heavy use of per-trial loops instead of vectorized solutions. |  |
| 10-c | What processing does the code repeat multiple times? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 ⚫🟢⚫ | 🟢🟢🟢 ⚫🟢⚫ |  |  |
| 10-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 ⚫🟢⚫ | 🟢🟢🟢 ⚫🟢⚫ |  |  |
| 10-e | How is memory usage optimized? | 🟢🟢🟢 🟢🟢🟢 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
