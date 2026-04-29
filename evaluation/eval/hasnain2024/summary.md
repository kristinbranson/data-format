# Evaluation summary — hasnain2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** All solution handled the mix of data format correctly. 1/6 didn't load the full dataset

---
## Q 1-b. How are the data split into subjects?

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
## Q 1-c. How are the data split into sessions?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Very simple session structure

---
## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Sightly different exclusion procedure across agents

---
## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Some minor differences in filtering decisions

---
## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** Overall correct solutions, but most of them didn't deal with the dual probe correctly

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

**Overall comment:** Small differences in preprocessing parameters, but are all valid. Agents were able to follow the correct solution using the paper's preprocessing code.

---
## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Two different binning choice in the paper, both are valid.

---
## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

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
## Q 3-a. What variables in the raw data is `output` *lick_direction* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | _(no note)_ |
| claude-code / trial3 | incorrect | _(no note)_ |
| codex / trial1 | incorrect | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | incorrect | _(no note)_ |

**Overall comment:** The lick direction avialible in the data is the correct direction. One agent derived the actual response direction by looking up the trial correctness info, another agent used bp.ev.Lick to derive the first lick direction. 4/6 agent got it incorrectly.

---
## Q 3-b. What processing is involved in computing `output` *lick_direction*?

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
## Q 4-a. What variables in the raw data is `output` *context* derived from?

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
## Q 4-b. What processing is involved in computing `output` *context*?

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
