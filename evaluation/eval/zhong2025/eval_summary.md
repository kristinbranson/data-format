# Eval comparison — zhong2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

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
## Q 1-b. How are the data split into subjects?

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
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | incorrect | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | ok | match | concerning | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | match | — |  |
| claude-code / trial2 | concerning | match | match | — |  |
| claude-code / trial3 | concerning | concerning | incorrect | — |  |
| codex / trial1 | ok | concerning | concerning | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-a. What variables in the raw data is the final `neural` data derived from?

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
## Q 2-b. How is the `neural` data processed?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | concerning | — |  |
| claude-code / trial2 | match | concerning | concerning | — |  |
| claude-code / trial3 | match | concerning | incorrect | — |  |
| codex / trial1 | match | concerning | concerning | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | concerning | incorrect | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | ok | ok | incorrect | — |  |
| codex / trial1 | concerning | concerning | concerning | — |  |
| codex / trial2 | concerning | concerning | incorrect | — |  |
| codex / trial3 | incorrect | concerning | incorrect | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 3-a. What variables in the raw data is `output` *visual_stimulus* derived from?

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
## Q 3-b. What processing is involved in computing `output` *visual_stimulus*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | incorrect | match | concerning | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 4-a. What variables in the raw data is `output` *licking* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 4-b. What processing is involved in computing `output` *licking*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 4-c. How is `output` *licking* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** The codex judge applies the comparison to the reference paper too literally.

---
## Q 5-a. What variables in the raw data is `output` *position* derived from?

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
## Q 5-b. What processing is involved in computing `output` *position*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | match | incorrect | — |  |
| claude-code / trial3 | incorrect | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 5-c. How is `output` *position* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 6-a. What variables in the raw data is `output` *running_speed* derived from?

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
## Q 6-b. What processing is involved in computing `output` *running_speed*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | concerning | concerning | incorrect | — |  |
| claude-code / trial3 | concerning | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 6-c. How is `output` *running_speed* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | concerning | — |  |
| claude-code / trial3 | ok | ok | match | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | ok | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 8-a. What are the most time-consuming steps of the code?

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
## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

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
## Q 8-c. What processing does the code repeat multiple times?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | match | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | concerning | match | match | — |  |
| codex / trial3 | ok | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | concerning | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 8-e. How is memory usage optimized?

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
