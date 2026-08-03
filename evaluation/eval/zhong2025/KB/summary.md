# Evaluation summary — zhong2025 · evaluator KB

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
## Q 1-b. How are the data split into subjects?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | incorrect | does not filter gray frames between trials |
| claude-code / trial3 | concerning | does not filter out gray space frames |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | agent also checks ft_move |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | concerning | d' selectivity criterion |
| codex / trial2 | concerning | selects neurons with \|d'\| > threshes |
| codex / trial3 | concerning | agent selects discriminating neurons based on d' |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | better | manual makes trials all the same length, which was not necessary for the data spec. this requires padding |
| claude-code / trial2 | concerning | does not filter gray frames in between trials |
| claude-code / trial3 | concerning | does not filter gray frames |
| codex / trial1 | concerning | does not remove gray frames |
| codex / trial2 | better | manual makes trials all the same length, which was not necessary for the data spec. this requires padding shorter trials |
| codex / trial3 | better | manual makes trials all the same length, which was not necessary for the data spec. this requires padding the |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | assumes constant frame rate |
| claude-code / trial2 | concerning | assumes a constant frame rate |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | concerning | assumes constant frame rate |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** c

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | agent uses all unique categories, while manual groups by texture type |
| claude-code / trial2 | concerning | mostly ok, but does some weird mapping for rock and wood stimuli, not sure if these come up:  'rock1': 'circle1', 'rock2': 'circle2', 'wood1': 'leaf1', 'wood2': 'leaf2', 'wood1_swap1': 'leaf1_swap1', 'wood1_swap2': 'leaf1_swap2', 'brick1': 'circle1', 'brick2': 'circle2', 'brick5': 'leaf3', 'wood5': 'leaf3', 'rock5': 'circle3' |
| claude-code / trial3 | ok | agent uses all unique categories, while manual groups by texture type |
| codex / trial1 | ok | agent uses all unique categories, while manual groups by texture type |
| codex / trial2 | ok | agent uses all unique categories, while manual groups by texture type |
| codex / trial3 | ok | agent uses all unique categories, while manual groups by texture type |

**Overall comment:** _(no overall comment)_

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What processing is involved in computing `output` *licking*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-b. What processing is involved in computing `output` *position*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-d. How is `output` *position* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 10-d. How is `output` *running_speed* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 12-a. What are the most time-consuming steps of the code?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | large pkl file |
| claude-code / trial2 | concerning | output pkl file is quite large |
| claude-code / trial3 | concerning | large pkl file output |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 12-c. What processing does the code repeat multiple times?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | concerning | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 12-e. How is memory usage optimized?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

