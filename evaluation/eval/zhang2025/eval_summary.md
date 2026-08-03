# Eval comparison — zhang2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | incorrect | ok | match | incorrect |
| claude-code / trial2 | incorrect | ok | match | incorrect |
| claude-code / trial3 | ok | ok | match | match |
| codex / trial1 | ok | ok | match | match |
| codex / trial2 | ok | ok | match | match |
| codex / trial3 | ok | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | ok | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | concerning | match | concerning |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | concerning | concerning |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | incorrect | match | match |
| claude-code / trial2 | concerning | incorrect | match | match |
| claude-code / trial3 | concerning | incorrect | match | match |
| codex / trial1 | match | match | concerning | concerning |
| codex / trial2 | match | match | match | incorrect |
| codex / trial3 | match | match | concerning | concerning |

**Overall comment:** The LLM judges rated the no-filter solutions as more "correct".

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | concerning |

**Overall comment:** _(no overall comment)_

---

## Q 3-a. What variables in the raw data is `input` *time_from_stimulus_onset* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 3-b. What processing is involved in computing `input` *time_from_stimulus_onset*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 3-c. How is `input` *time_from_stimulus_onset* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 4-a. What variables in the raw data is `input` *trial_number_in_block* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 4-b. What processing is involved in computing `input` *trial_number_in_block*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | — | — |
| claude-code / trial2 | match | ok | — | — |
| claude-code / trial3 | match | ok | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | ok | — | — |
| codex / trial3 | match | ok | — | — |

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 5-b. What processing is involved in computing `output` *choice*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | incorrect | incorrect | match | match |
| claude-code / trial2 | incorrect | incorrect | match | incorrect |
| claude-code / trial3 | incorrect | incorrect | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** Only one judge run caught this mistake.

---

## Q 6-a. What variables in the raw data is `output` *prior_probability_left* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 6-b. What processing is involved in computing `output` *prior_probability_left*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 7-a. What variables in the raw data is `output` *wheel_speed* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 7-b. What processing is involved in computing `output` *wheel_speed*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | incorrect | ok | concerning | incorrect |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | concerning | match |

**Overall comment:** _(no overall comment)_

---

## Q 7-d. How is `output` *wheel_speed* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | concerning |

**Overall comment:** _(no overall comment)_

---

## Q 8-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What processing is involved in computing `output` *whisker_motion_energy*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | match | match |
| claude-code / trial2 | concerning | concerning | match | match |
| claude-code / trial3 | ok | concerning | match | match |
| codex / trial1 | concerning | ok | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** The LLM judges missed this detail.

---

## Q 8-d. How is `output` *whisker_motion_energy* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | concerning |

**Overall comment:** _(no overall comment)_

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | concerning |
| claude-code / trial2 | match | ok | match | concerning |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | concerning |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | match |
| claude-code / trial2 | match | concerning | match | match |
| claude-code / trial3 | match | concerning | match | match |
| codex / trial1 | match | concerning | match | match |
| codex / trial2 | match | concerning | match | match |
| codex / trial3 | match | concerning | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | ok | match | match |
| claude-code / trial2 | ok | ok | match | match |
| claude-code / trial3 | ok | ok | match | match |
| codex / trial1 | ok | ok | match | match |
| codex / trial2 | ok | ok | match | match |
| codex / trial3 | ok | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | ok | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | ok | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-e. How is memory usage optimized?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | ok | — | — |
| claude-code / trial2 | match | ok | — | — |
| claude-code / trial3 | match | ok | — | — |
| codex / trial1 | ok | ok | — | — |
| codex / trial2 | ok | ok | — | — |
| codex / trial3 | concerning | ok | — | — |

**Overall comment:** _(no overall comment)_
