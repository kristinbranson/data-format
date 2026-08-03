# Eval comparison — zhong2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | ok | match | match |
| claude-code / trial2 | ok | match | incorrect |
| claude-code / trial3 | ok | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | ok | match | concerning |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | concerning | match | match |
| claude-code / trial2 | concerning | match | match |
| claude-code / trial3 | concerning | concerning | incorrect |
| codex / trial1 | ok | concerning | concerning |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | concerning | concerning |
| claude-code / trial2 | match | concerning | concerning |
| claude-code / trial3 | match | concerning | incorrect |
| codex / trial1 | match | concerning | concerning |
| codex / trial2 | match | match | concerning |
| codex / trial3 | match | concerning | incorrect |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | ok | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | ok | ok | incorrect |
| codex / trial1 | concerning | concerning | concerning |
| codex / trial2 | concerning | concerning | incorrect |
| codex / trial3 | incorrect | concerning | incorrect |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | concerning |
| claude-code / trial3 | match | match | incorrect |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | incorrect |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | incorrect |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | incorrect | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | concerning | — | — |
| claude-code / trial2 | incorrect | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | concerning | — | — |
| codex / trial2 | concerning | — | — |
| codex / trial3 | concerning | — | — |

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | incorrect | match | concerning |
| claude-code / trial3 | match | match | incorrect |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | concerning |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What processing is involved in computing `output` *licking*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | concerning |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | concerning |
| claude-code / trial3 | match | match | incorrect |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** The codex judge applies the comparison to the reference paper too literally.

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 9-b. What processing is involved in computing `output` *position*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | ok | match | incorrect |
| claude-code / trial3 | incorrect | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 9-d. How is `output` *position* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | incorrect |
| claude-code / trial3 | match | match | incorrect |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | ok | match | match |
| claude-code / trial2 | concerning | concerning | incorrect |
| claude-code / trial3 | concerning | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 10-d. How is `output` *running_speed* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | concerning |
| claude-code / trial3 | match | match | incorrect |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | ok | match | match |
| claude-code / trial2 | ok | match | concerning |
| claude-code / trial3 | ok | ok | match |
| codex / trial1 | match | match | concerning |
| codex / trial2 | match | match | concerning |
| codex / trial3 | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | match | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | ok | match | match |
| claude-code / trial2 | ok | match | match |
| claude-code / trial3 | ok | match | match |
| codex / trial1 | ok | match | match |
| codex / trial2 | ok | match | match |
| codex / trial3 | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | ok | match | match |
| claude-code / trial2 | ok | match | match |
| claude-code / trial3 | ok | match | match |
| codex / trial1 | ok | match | match |
| codex / trial2 | concerning | match | match |
| codex / trial3 | ok | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | match | match |
| claude-code / trial2 | match | match | match |
| claude-code / trial3 | match | match | match |
| codex / trial1 | match | concerning | match |
| codex / trial2 | match | match | match |
| codex / trial3 | match | match | match |

**Overall comment:** _(no overall comment)_

---

## Q 12-e. How is memory usage optimized?

| Agent / trial | LZ | Claude judge | Codex judge |
|---|---|---|---|
| claude-code / trial1 | match | — | — |
| claude-code / trial2 | match | — | — |
| claude-code / trial3 | match | — | — |
| codex / trial1 | match | — | — |
| codex / trial2 | match | — | — |
| codex / trial3 | match | — | — |

**Overall comment:** _(no overall comment)_
