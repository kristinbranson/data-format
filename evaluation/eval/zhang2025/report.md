# Evaluation Report — zhang2025

## Summary

- Dataset: **zhang2025**
- Questions covered: 26
- Trials per question: 6 (3 claude-code + 3 codex)
- Evaluators: Human, Claude judge, Codex judge

**Legend:**  🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating  
A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.

## Comments

#### Agent Performance
- Similar to the allen2p dataset, all of the agents bypassed the ONE API and read the data directly from the local cache folder structure.
- The agents did quite well preprocessing the neural data — all 6 correctly implement the core pipeline (merge probes, align to stimulus onset, and compute binned spike counts).
- 2/6 trials made a critical mistake when converting the choice variable, assuming a `+1 = right`, `-1 = left` convention when IBL's is flipped (`+1 = left`, `-1 = right`). We have seen similar patterns multiple times — agents make assumptions without empirically checking against the data.
- The largest variation appears in the wheel and whisker preprocessing — including one trial where the agent upsampled wheel position and applied `np.gradient` to compute speed without any filtering, and 3/6 trials that applied the wrong alignment when fixing the camera-timestamps vs motion-energy length mismatch.

## Per-question evaluations

| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |
|---|---|---|---|---|---|---|
| 1-a | How are **all the data** for all subjects, sessions, and trials loaded in? | 🔴🔴🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🔴🔴🟢 🟢🟢🟢 | All runs read files directly from the cache directory, bypassing the ONE API. 2/6 trials hardcoded `001` subfolder in the search path instead of using the value from the BWM release CSV. |  |
| 1-b | How are the data split into subjects? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | Subjects are identified from either the BWM CSV or the file path. |  |
| 1-c | How are the data split into sessions? | 🟢🔵🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 1/6 trials did not use the session info from the BWM CSV (relies on filesystem globbing instead). |  |
| 1-d | Are the data correctly split into trials? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 1-e | How are trials filtered based on quality controls? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟡🟢🟢 |  |  |
| 2-a | What variables in the raw data is the final `neural` data derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 2-b | How is the `neural` data processed? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 | All solutions correctly implemented the merge + binning steps. |  |
| 2-c | How is the `neural` data filtered based on quality controls? | 🟡🟡🟡 🟢🟢🟢 | 🟢🟢🟢 🟡🟢🟡 | 🟢🟢🟢 🟡🔴🟡 | The claude agents did not implement cluster-level QC filtering (`label >= 1`); the codex agents did. | The LLM judges rated the no-filter solutions as more "correct". |
| 2-d | How is the `neural` data temporally binned/resampled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 |  |  |
| 2-e | How is the per-trial `neural` data aligned to the event described in the `instructions`? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟢 |  |  |
| 3-a | What variables in the raw data is `output` *choice* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 3-b | What processing is involved in computing `output` *choice*? | 🔴🔴🔴 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🔴🟢 🟢🟢🟢 | There is a small trap: in the IBL data, `+1` corresponds to a left choice and `-1` to a right choice. The claude solutions have the sign flipped. | Only one judge run caught this mistake. |
| 4-a | What variables in the raw data is `output` *prior_probability_left* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 4-b | What processing is involved in computing `output` *prior_probability_left*? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-a | What variables in the raw data is `output` *wheel_speed* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 5-b | What processing is involved in computing `output` *wheel_speed*? | 🟢🔴🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 | 🟢🔴🟢 🟢🟢🟢 | 1/6 trials upsampled to 1 kHz and used `np.gradient` with no low-pass filter, which is quite problematic. The other 5 trials follow the standard reference pipeline (Butterworth lowpass before differentiation). |  |
| 5-c | How is `output` *wheel_speed* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 |  |  |
| 6-a | What variables in the raw data is `output` *whisker_motion_energy* derived from? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 6-b | What processing is involved in computing `output` *whisker_motion_energy*? | 🟡🟡🔵 🟡🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 3/6 trials use the wrong trim direction when fixing the camera-timestamps vs motion-energy length mismatch (trim from end instead of front per IBL convention), causing the whisker ME signal to be misaligned in time with neural and behavior data. | The LLM judges missed this detail. |
| 6-c | How is `output` *whisker_motion_energy* aligned with the neural data? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟡🟢 🟢🟢🟡 |  |  |
| 7 | How are minor mistakes in the data, e.g. missing data, handled? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟡🟡🟢 🟡🟢🟢 |  |  |
| 8-a | What are the most time-consuming steps of the code? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-b | What loops in the code could have been vectorized to improve efficiency? | 🔵🔵🔵 🔵🔵🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-c | What processing does the code repeat multiple times? | 🟢🟢🔵 🟢🟢🔵 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-d | What unnecessary processing does the code do that is discarded in downstream analyses? | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 | 🟢🟢🟢 🟢🟢🟢 |  |  |
| 8-e | How is memory usage optimized? | 🔵🟢🟢 🔵🔵🟡 | ⚫⚫⚫ ⚫⚫⚫ | ⚫⚫⚫ ⚫⚫⚫ |  |  |
