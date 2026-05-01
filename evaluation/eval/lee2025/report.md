# Evaluation Report — lee2025

## Summary

- Dataset: **lee2025**
- Questions covered: 21
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
- The agents completed all required tasks without issue.
- 🟣 In two trials, the agents used a preprocessing pipeline that follows the paper more closely. In general, we have found the agents are better at details within the code.
- Potential concerns:
    - 2-b: large variability in the preprocessing pipeline across runs.
    - 2-c: only the first frame is used to check for NaN — not robust.

#### LLM as Judge
- The Codex judge is again unusable, being too rigid and literal in its judgments.
- The Claude judge is relatively ok, but in a couple of cases it is very inconsistent (e.g., scores ranging from "concerning" to "better" for the same solution across different runs).

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🟢🟢🟢 🟢🟢🟢 | 🔵🔵🟢 🔵🟡🟣 | 🔴🔴🔴 🔴🟢🔴 | All agent solutions used the joblib files instead of the .mat files, but this is correct. | Judge ratings are *very inconsistent* for the same agent implementation across 6 runs. |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🔴🔵 🟢🟢🟢 |  |  |
| 1-c | How are the data split into sessions? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔵🔴🟢 🟢🟢🟢 |  |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟡🟢🟢 | 🟡🟢🟢 🟣🟡🟢 | 🔴🔵🟢 🔴🟢🟢 | 1/6 implementations were not robust because they followed the paper description too literally (40-min recording session). |  |
| 1-e | How are trials filtered based on quality controls? | 🟢🟢🟢 🟢🔵🟢 | 🟢🟢🟢 🟢🟡🟣 | 🔴🟢🟢 🟢🟢🔵 |  |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔵🟢🔵 🟢🟢🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟣🟢 🟡🟣🟢 | 🟢🟡🟢 🟣🟡🟢 | 🟡🔴🔵 🔴🟢🟡 | Largest variability across runs/agents — some performed additional processing steps following the paper. | Claude's ratings don't make sense to me here. |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟡🟡🟢 🟡🔵🟡 | 🟡🟢🟢 🟢🟡🟢 | 🟡🔴🟡 🔵🟢🔴 | One-frame NaN check is not robust (4/6). |  |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🔵🟢 🟡🔵🟢 | 🟢🟡🟢 🟣🟡🟢 | 🟢🔴🟢 🔴🟢🟢 |  | Same as 2-b: Claude rated a partial solution "better" but the complete solution "concerning". |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔴🔵🟡 🔵🟢🟡 |  |  |
| 3-a | What variables in the raw data is `input` *Blocked positions* derived from? | 🔵🔵🔵 🟢🟢🟢 | 🟡🔵🟡 🟢🟢🟢 | 🔴🔴🔴 🟢🟢🟢 | All claude agents used the environment-geometry-to-name mapping, which is a bit more complicated but correct. | Two possible solutions; Claude judge is inconsistent. |
| 3-b | What processing is involved in computing `input` *Blocked positions*? | 🟢🟢🟢 🟢🟢🟢 | 🟡🔵🟡 🔵🟡🟣 | 🔴🔴🔴 🔴🟢⚫ | Some used different conventions, but the same information is represented. | Same as above. |
| 4-a | What variables in the raw data is `output` *Position* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 4-b | What processing is involved in computing `output` *Position*? | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🔵 🔵🟡🟪 | 🔴🔴🔴 🔴🟢⚫ | The grid/bin conventions differ across some solutions but are all valid. |  |
| 4-c | How is `output` *Position* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟡🟢 | 🟢🟡🟢 🔵🟢🟢 |  |  |
| 7 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟢 🟢🟢🟢 | 🟨🟢🟢 🟢🟡🟪 | 🔴🟡🟡 🟡🟢🔵 | One agent's solution is more robust. |  |
| 8-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🔵🟡🟢 🔵🟢🔵 |  |  |
| 8-b | What loops in the code could have been vectorized to improve efficiency? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🔵 🟢🟢🟢 | 🟡🟡🟡 🔵🟢🔵 |  |  |
| 8-c | What processing does the code repeat multiple times? | 🟢🟢🔵 🔵🟢🔴 | 🟢🟢🔵 🟢🟢🟢 | 🔴🟡🟡 🔵🟢🔵 | One inefficient "two-pass" solution. |  |
| 8-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟨 | 🔴🔵🟡 🔵🟢🔵 |  |  |
