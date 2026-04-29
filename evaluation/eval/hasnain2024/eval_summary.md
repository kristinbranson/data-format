# Eval comparison — hasnain2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | concerning | match | concerning | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 1-b. How are the data split into subjects?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** LLM judge flagged the extra subject found by the code, but is not consistent

---
## Q 1-c. How are the data split into sessions?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | concerning | — |  |
| claude-code / trial2 | ok | concerning | incorrect | — |  |
| claude-code / trial3 | ok | incorrect | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-b. How is the `neural` data processed?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | concerning | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Judge decisions are inconsistent

---
## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | concerning | match | — |  |
| claude-code / trial3 | ok | concerning | concerning | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | concerning | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** LLM judges are very inconsistent regarding the time bin choice

---
## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 3-a. What variables in the raw data is `output` *lick_direction* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | incorrect | match | match | — |  |
| claude-code / trial3 | incorrect | concerning | concerning | — |  |
| codex / trial1 | incorrect | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | incorrect | match | match | — |  |

**Overall comment:** LLM judge only flagged one of the incorrect solution but not the others.

---
## Q 3-b. What processing is involved in computing `output` *lick_direction*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | — | match | — |  |
| codex / trial2 | match | match | — | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 4-a. What variables in the raw data is `output` *context* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 4-b. What processing is involved in computing `output` *context*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | — | match | — |  |
| codex / trial2 | match | match | — | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 5-a. What variables in the raw data is `output` *outcome* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 5-b. What processing is involved in computing `output` *outcome*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | — | match | — |  |
| codex / trial2 | match | match | — | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 6-a. What variables in the raw data is `output` *tongue_velocity* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | concerning | — |  |
| claude-code / trial2 | concerning | match | concerning | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | concerning | match | concerning | — |  |
| codex / trial2 | concerning | match | concerning | — |  |
| codex / trial3 | ok | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 6-b. What processing is involved in computing `output` *tongue_velocity*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | concerning | concerning | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | concerning | concerning | — |  |
| codex / trial1 | ok | — | incorrect | — |  |
| codex / trial2 | ok | match | — | — |  |
| codex / trial3 | ok | concerning | concerning | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 6-c. How is `output` *tongue_velocity* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 7-a. What variables in the raw data is `output` *paw_velocity* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | concerning | match | concerning | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | ok | match | concerning | — |  |
| codex / trial2 | ok | match | concerning | — |  |
| codex / trial3 | ok | match | concerning | — |  |

**Overall comment:** Claude rate all solution as match and provided justification for using single or both features, seems quite bad at making consistent judgement.

---
## Q 7-b. What processing is involved in computing `output` *paw_velocity*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | concerning | — |  |
| claude-code / trial2 | match | incorrect | match | — |  |
| claude-code / trial3 | match | incorrect | concerning | — |  |
| codex / trial1 | concerning | — | incorrect | — |  |
| codex / trial2 | incorrect | concerning | — | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 7-c. How is `output` *paw_velocity* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 8-a. What variables in the raw data is `output` *motion_energy* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 8-b. What processing is involved in computing `output` *motion_energy*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | — | match | — |  |
| codex / trial2 | match | match | — | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 8-c. How is `output` *motion_energy* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 10-a. What are the most time-consuming steps of the code?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | match | — |  |
| claude-code / trial2 | concerning | match | match | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | ok | — | — | — |  |
| codex / trial2 | concerning | match | match | — |  |
| codex / trial3 | ok | — | — | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 10-c. What processing does the code repeat multiple times?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | ok | — | — | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | — | — | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | ok | — | — | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | — | — | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 10-e. How is memory usage optimized?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

**Overall comment:** _(no overall comment)_

---
