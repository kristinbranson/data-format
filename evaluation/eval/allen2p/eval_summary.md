# Eval comparison — allen2p

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | ok | incorrect | Human |  |
| claude-code / trial2 | ok | ok | incorrect | Human |  |
| claude-code / trial3 | ok | ok | incorrect | Human |  |
| codex / trial1 | ok | ok | incorrect | Human |  |
| codex / trial2 | ok | ok | incorrect | Human |  |
| codex / trial3 | ok | concerning | incorrect | Claude judge | Claude caught a small bug with data filtering using project_code |

**Overall comment:** The Claude judge caught a minor mistake that I overlooked: one of the solutions was not properly filtering the data based on `project_code`.

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | incorrect | concerning | incorrect | — |  |
| claude-code / trial2 | incorrect | concerning | incorrect | — |  |
| claude-code / trial3 | incorrect | concerning | incorrect | — |  |
| codex / trial1 | incorrect | concerning | incorrect | — |  |
| codex / trial2 | incorrect | concerning | incorrect | — |  |
| codex / trial3 | incorrect | concerning | incorrect | — |  |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | Human |  |
| claude-code / trial2 | concerning | concerning | incorrect | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | concerning | match | Human |  |

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | Human |  |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | concerning | Human |  |
| codex / trial1 | match | concerning | concerning | Human |  |
| codex / trial2 | match | match | concerning | Human |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | ok | incorrect | incorrect | Human |  |
| codex / trial1 | ok | concerning | incorrect | Human |  |
| codex / trial2 | ok | incorrect | incorrect | Human |  |
| codex / trial3 | ok | concerning | incorrect | Human |  |

**Overall comment:** It is hard for the LLM judges to tell whether using event data instead of dF/F is reasonable here (additional context and domain knowledge required).

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | Human |  |
| claude-code / trial2 | incorrect | incorrect | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | Human |  |
| codex / trial1 | concerning | concerning | incorrect | — |  |
| codex / trial2 | ok | incorrect | incorrect | Human |  |
| codex / trial3 | ok | concerning | incorrect | Human |  |

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | Human |  |
| claude-code / trial2 | match | match | concerning | Human |  |
| claude-code / trial3 | match | match | incorrect | Human |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | incorrect | Human |  |

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | Human |  |
| claude-code / trial2 | incorrect | incorrect | incorrect | — |  |
| claude-code / trial3 | ok | concerning | incorrect | Human |  |
| codex / trial1 | concerning | concerning | incorrect | — |  |
| codex / trial2 | ok | incorrect | incorrect | Human |  |
| codex / trial3 | ok | concerning | incorrect | Human |  |

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | concerning | incorrect | Human |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | concerning | match | Human |  |
| codex / trial3 | match | concerning | incorrect | Human |  |

---

## Q 3-a. What variables in the raw data is `output` *Running speed* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 3-b. What processing is involved in computing `output` *Running speed*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | Claude judge | Claude caught a minor bug |
| claude-code / trial2 | incorrect | concerning | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | Human |  |
| codex / trial1 | match | concerning | — | Human |  |
| codex / trial2 | match | match | incorrect | Human |  |
| codex / trial3 | match | match | incorrect | Human |  |

---

## Q 3-c. How is `output` *Running speed* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | ok | incorrect | Human |  |
| claude-code / trial3 | match | match | incorrect | Human |  |
| codex / trial1 | match | match | incorrect | Human |  |
| codex / trial2 | match | match | incorrect | Human |  |
| codex / trial3 | match | match | incorrect | Human |  |

---

## Q 4-a. What variables in the raw data is `output` *Pupil diameter* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | incorrect | — |  |
| claude-code / trial2 | concerning | concerning | concerning | — |  |
| claude-code / trial3 | concerning | incorrect | incorrect | — |  |
| codex / trial1 | concerning | concerning | incorrect | — |  |
| codex / trial2 | ok | concerning | incorrect | Human |  |
| codex / trial3 | ok | incorrect | incorrect | Human |  |

---

## Q 4-b. What processing is involved in computing `output` *Pupil diameter*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | Human |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | concerning | incorrect | Human |  |
| codex / trial1 | match | concerning | — | Human |  |
| codex / trial2 | match | concerning | incorrect | Human |  |
| codex / trial3 | match | concerning | incorrect | Human |  |

---

## Q 4-c. How is `output` *Pupil diameter* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | incorrect | ok | incorrect | Human |  |
| claude-code / trial3 | match | match | incorrect | Human |  |
| codex / trial1 | match | match | incorrect | Human |  |
| codex / trial2 | match | match | incorrect | Human |  |
| codex / trial3 | match | match | incorrect | Human |  |

---

## Q 5-a. What variables in the raw data is `output` *Image name* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | incorrect | Human |  |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | match | ok | incorrect | Human |  |
| codex / trial1 | ok | concerning | incorrect | Human |  |
| codex / trial2 | ok | ok | concerning | Human |  |
| codex / trial3 | ok | concerning | incorrect | Human |  |

---

## Q 5-b. What processing is involved in computing `output` *Image name*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | incorrect | Human |  |
| claude-code / trial2 | match | concerning | concerning | Claude judge | Claude caught a problem with agent implmentation of image name mapping |
| claude-code / trial3 | match | match | concerning | Human |  |
| codex / trial1 | match | concerning | — | Human |  |
| codex / trial2 | match | ok | concerning | Human |  |
| codex / trial3 | match | concerning | incorrect | Human |  |

---

## Q 5-c. How is `output` *Image name* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | Human |  |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | match | match | concerning | Human |  |
| codex / trial1 | match | match | incorrect | Human |  |
| codex / trial2 | match | match | concerning | Human |  |
| codex / trial3 | match | match | incorrect | Human |  |

---

## Q 6-a. What variables in the raw data is `output` *Image change* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | ok | incorrect | Human |  |
| claude-code / trial2 | ok | ok | ok | — |  |
| claude-code / trial3 | match | ok | concerning | Human |  |
| codex / trial1 | ok | ok | incorrect | Human |  |
| codex / trial2 | ok | concerning | incorrect | Human |  |
| codex / trial3 | ok | concerning | concerning | Human |  |

---

## Q 6-b. What processing is involved in computing `output` *Image change*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | Claude judge | Human error |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | match | match | concerning | Human |  |
| codex / trial1 | match | concerning | — | Human |  |
| codex / trial2 | match | concerning | incorrect | Human |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 6-c. How is `output` *Image change* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | Human |  |
| claude-code / trial2 | ok | ok | ok | — |  |
| claude-code / trial3 | match | match | concerning | Human |  |
| codex / trial1 | match | match | incorrect | Human |  |
| codex / trial2 | match | match | concerning | Human |  |
| codex / trial3 | match | match | incorrect | Human |  |

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | concerning | Human |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | — | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 7-c. How is `output` *Trial outcome* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | Human |  |
| claude-code / trial2 | match | ok | concerning | Human |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | concerning | concerning | Human |  |
| codex / trial2 | match | match | concerning | Human |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 9-a. What are the most time-consuming steps of the code?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | concerning | Human |  |
| claude-code / trial2 | concerning | match | match | Human |  |
| claude-code / trial3 | concerning | match | ok | Human |  |
| codex / trial1 | concerning | match | ok | Human |  |
| codex / trial2 | concerning | match | ok | Human |  |
| codex / trial3 | concerning | match | concerning | Human |  |

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | match | concerning | Human |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | ok | match | ok | — |  |
| codex / trial1 | ok | match | ok | — |  |
| codex / trial2 | ok | match | match | — |  |
| codex / trial3 | ok | match | ok | — |  |

---

## Q 9-c. What processing does the code repeat multiple times?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | match | incorrect | Human |  |
| claude-code / trial2 | concerning | better | incorrect | Human | I think the LLM judge did not parse this Q correctly |
| claude-code / trial3 | incorrect | incorrect | incorrect | — |  |
| codex / trial1 | concerning | match | concerning | Human |  |
| codex / trial2 | concerning | match | incorrect | Human |  |
| codex / trial3 | concerning | concerning | concerning | — |  |

**Overall comment:** The LLM judge seems to have completely misunderstood this question.

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | concerning | better | incorrect | Human |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | match | concerning | — |  |

---

## Q 9-e. How is memory usage optimized?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |
