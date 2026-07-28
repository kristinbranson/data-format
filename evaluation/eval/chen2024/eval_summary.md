# Eval comparison — chen2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | ok | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 1-b. How are the data split into subjects?

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

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | concerning | concerning | match | — |  |
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
| codex / trial1 | concerning | concerning | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | ok | concerning | concerning | — |  |
| codex / trial2 | ok | match | concerning | — |  |
| codex / trial3 | incorrect | concerning | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

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

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | concerning | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

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

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

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

## Q 3-a. What variables in the raw data is `output` *choice* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | incorrect | match | match | — |  |
| claude-code / trial2 | incorrect | match | incorrect | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | ok | concerning | concerning | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** The LLM judges failed to flag the trials where this mistake was made.

---

## Q 3-b. What processing is involved in computing `output` *choice*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | incorrect | match | match | — |  |
| claude-code / trial2 | incorrect | match | incorrect | — |  |
| claude-code / trial3 | concerning | concerning | concerning | — |  |
| codex / trial1 | ok | concerning | concerning | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | concerning | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 4-a. What variables in the raw data is `output` *outcome* derived from?

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

## Q 4-b. What processing is involved in computing `output` *outcome*?

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

## Q 5-a. What variables in the raw data is `output` *early_lick* derived from?

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

## Q 5-b. What processing is involved in computing `output` *early_lick*?

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

## Q 6-a. What variables in the raw data is `output` *tongue_y_position* derived from?

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

## Q 6-b. What processing is involved in computing `output` *tongue_y_position*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | concerning | — |  |
| claude-code / trial2 | ok | concerning | concerning | — |  |
| claude-code / trial3 | concerning | concerning | match | — |  |
| codex / trial1 | concerning | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 6-c. How is `output` *tongue_y_position* aligned with the neural data?

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

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | concerning | concerning | — |  |
| claude-code / trial3 | match | concerning | concerning | — |  |
| codex / trial1 | ok | concerning | concerning | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 8-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 8-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---

## Q 8-e. How is memory usage optimized?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | ok | — | — | — |  |
| codex / trial2 | ok | — | — | — |  |
| codex / trial3 | ok | — | — | — |  |

**Overall comment:** _(no overall comment)_
