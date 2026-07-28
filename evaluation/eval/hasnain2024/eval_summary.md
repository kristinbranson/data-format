# Eval comparison — hasnain2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** LLM judge flagged the extra subject found by the code, but was inconsistent across runs.

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | concerning | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Judge decisions are inconsistent across runs.

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | concerning | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** LLM judges are very inconsistent regarding the time-bin choice.

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | incorrect | match | match | — |  |
| claude-code / trial3 | incorrect | concerning | concerning | — |  |
| codex / trial1 | incorrect | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | incorrect | match | match | — |  |

**Overall comment:** The LLM judge only flagged one of the incorrect solutions, missing the others.

---

## Q 3-b. What processing is involved in computing `output` *lick_direction*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 4-a. What variables in the raw data is `output` *context* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 5-a. What variables in the raw data is `output` *outcome* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 6-a. What variables in the raw data is `output` *tongue_velocity* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | concerning | concerning | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | concerning | concerning | — |  |
| codex / trial1 | ok | match | incorrect | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | concerning | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 6-c. How is `output` *tongue_velocity* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | concerning | match | concerning | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | ok | match | concerning | — |  |
| codex / trial2 | ok | match | concerning | — |  |
| codex / trial3 | ok | match | concerning | — |  |

**Overall comment:** Claude judge rated all solutions as match and provided justifications for using either single or both features, suggesting it is poor at making consistent judgments here.

---

## Q 7-b. What processing is involved in computing `output` *paw_velocity*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | concerning | — |  |
| claude-code / trial2 | match | incorrect | match | — |  |
| claude-code / trial3 | match | incorrect | concerning | — |  |
| codex / trial1 | concerning | match | incorrect | — |  |
| codex / trial2 | incorrect | concerning | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 7-c. How is `output` *paw_velocity* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | concerning | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 8-c. How is `output` *motion_energy* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | match | — |  |
| claude-code / trial2 | concerning | match | match | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | ok | — | match | — |  |
| codex / trial2 | concerning | match | match | — |  |
| codex / trial3 | ok | — | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 10-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | ok | — | match | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | — | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | ok | — | concerning | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | — | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 10-e. How is memory usage optimized?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

**Overall comment:** _(no overall comment)_
