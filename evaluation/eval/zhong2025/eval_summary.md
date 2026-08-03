# Eval comparison — zhong2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

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

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-c. How are the data split into sessions?

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

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | ok | match | match |
| claude-code / trial2 | ok | incorrect | match | incorrect |
| claude-code / trial3 | ok | concerning | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | ok | ok | match | concerning |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | match | match |
| claude-code / trial2 | concerning | ok | match | match |
| claude-code / trial3 | concerning | ok | concerning | incorrect |
| codex / trial1 | ok | ok | concerning | concerning |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

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

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | concerning |
| claude-code / trial2 | match | match | concerning | concerning |
| claude-code / trial3 | match | match | concerning | incorrect |
| codex / trial1 | match | match | concerning | concerning |
| codex / trial2 | match | match | match | concerning |
| codex / trial3 | match | match | concerning | incorrect |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | ok | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | ok | ok | ok | incorrect |
| codex / trial1 | concerning | concerning | concerning | concerning |
| codex / trial2 | concerning | concerning | concerning | incorrect |
| codex / trial3 | incorrect | concerning | concerning | incorrect |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | better | match | match |
| claude-code / trial2 | concerning | concerning | match | concerning |
| claude-code / trial3 | concerning | concerning | match | incorrect |
| codex / trial1 | concerning | concerning | match | match |
| codex / trial2 | match | better | match | incorrect |
| codex / trial3 | concerning | better | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | ok | — | — |

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | — | — |
| claude-code / trial2 | match | ok | — | — |
| claude-code / trial3 | match | ok | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | ok | — | — |
| codex / trial3 | match | ok | — | — |

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | incorrect | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | match | — | — |
| claude-code / trial2 | incorrect | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | concerning | match | — | — |
| codex / trial2 | concerning | match | — | — |
| codex / trial3 | concerning | match | — | — |

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | ok | — | — |

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | concerning | — | — |
| claude-code / trial2 | match | concerning | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | concerning | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | — | — |
| claude-code / trial2 | match | match | — | — |
| claude-code / trial3 | match | match | — | — |
| codex / trial1 | match | match | — | — |
| codex / trial2 | match | match | — | — |
| codex / trial3 | match | match | — | — |

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | — | — |
| claude-code / trial2 | match | ok | — | — |
| claude-code / trial3 | match | ok | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | ok | — | — |
| codex / trial3 | match | ok | — | — |

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

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

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | incorrect | concerning | match | concerning |
| claude-code / trial3 | match | ok | match | incorrect |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | concerning |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What processing is involved in computing `output` *licking*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | concerning |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | match | match | match | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** The codex judge applies the comparison to the reference paper too literally.

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

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

## Q 9-b. What processing is involved in computing `output` *position*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | ok | match | match | incorrect |
| claude-code / trial3 | incorrect | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 9-d. How is `output` *position* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | incorrect |
| claude-code / trial3 | match | match | match | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

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

## Q 10-b. What processing is involved in computing `output` *running_speed*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | match |
| claude-code / trial2 | concerning | match | concerning | incorrect |
| claude-code / trial3 | concerning | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-d. How is `output` *running_speed* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | match | match | match | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | ok | match | match |
| claude-code / trial2 | ok | ok | match | concerning |
| claude-code / trial3 | ok | ok | ok | match |
| codex / trial1 | match | ok | match | concerning |
| codex / trial2 | match | ok | match | concerning |
| codex / trial3 | ok | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | match |
| claude-code / trial2 | match | concerning | match | match |
| claude-code / trial3 | match | concerning | match | match |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

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

## Q 12-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | concerning | match | match |
| claude-code / trial2 | ok | concerning | match | match |
| claude-code / trial3 | ok | ok | match | match |
| codex / trial1 | ok | ok | match | match |
| codex / trial2 | concerning | concerning | match | match |
| codex / trial3 | ok | concerning | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | concerning | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-e. How is memory usage optimized?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | — | — |
| claude-code / trial2 | match | ok | — | — |
| claude-code / trial3 | match | ok | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | ok | — | — |
| codex / trial3 | match | ok | — | — |

**Overall comment:** _(no overall comment)_
