# Eval comparison — allen2p

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | ok | incorrect | ok | incorrect | LZ |  |
| claude-code / trial2 | ok | incorrect | ok | incorrect | LZ |  |
| claude-code / trial3 | ok | incorrect | ok | incorrect | LZ |  |
| codex / trial1 | ok | incorrect | ok | incorrect | LZ |  |
| codex / trial2 | ok | incorrect | ok | incorrect | LZ |  |
| codex / trial3 | ok | incorrect | concerning | incorrect | Claude judge | Claude caught a small bug with data filtering using project_code |

**Overall comment:** The Claude judge caught a minor mistake that I overlooked: one of the solutions was not properly filtering the data based on `project_code`.

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | ok | match | match | match | — |  |
| codex / trial2 | match | match | match | match | — |  |
| codex / trial3 | match | match | match | match | — |  |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | incorrect | incorrect | concerning | incorrect | — |  |
| claude-code / trial2 | incorrect | incorrect | concerning | incorrect | — |  |
| claude-code / trial3 | incorrect | incorrect | concerning | incorrect | — |  |
| codex / trial1 | incorrect | incorrect | concerning | incorrect | — |  |
| codex / trial2 | incorrect | incorrect | concerning | incorrect | — |  |
| codex / trial3 | incorrect | incorrect | concerning | incorrect | — |  |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | incorrect | LZ |  |
| claude-code / trial2 | concerning | match | concerning | incorrect | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | ok | match | ok | — |  |
| codex / trial3 | match | match | concerning | match | LZ |  |

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | incorrect | LZ |  |
| claude-code / trial2 | match | ok | match | ok | — |  |
| claude-code / trial3 | match | ok | match | concerning | LZ |  |
| codex / trial1 | match | concerning | concerning | concerning | LZ |  |
| codex / trial2 | match | ok | match | concerning | LZ |  |
| codex / trial3 | match | ok | concerning | concerning | LZ |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | ok | ok | incorrect | incorrect | LZ |  |
| codex / trial1 | ok | ok | concerning | incorrect | LZ |  |
| codex / trial2 | ok | ok | incorrect | incorrect | LZ |  |
| codex / trial3 | ok | ok | concerning | incorrect | LZ |  |

**Overall comment:** It is hard for the LLM judges to tell whether using event data instead of dF/F is reasonable here (additional context and domain knowledge required).

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | incorrect | LZ |  |
| claude-code / trial2 | incorrect | ok | incorrect | incorrect | — |  |
| claude-code / trial3 | match | ok | concerning | incorrect | LZ |  |
| codex / trial1 | concerning | ok | concerning | incorrect | — |  |
| codex / trial2 | ok | ok | incorrect | incorrect | LZ |  |
| codex / trial3 | ok | ok | concerning | incorrect | LZ |  |

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | match | LZ |  |
| claude-code / trial2 | match | match | match | concerning | LZ |  |
| claude-code / trial3 | match | match | match | incorrect | LZ |  |
| codex / trial1 | match | match | match | ok | — |  |
| codex / trial2 | match | match | match | ok | — |  |
| codex / trial3 | match | match | match | incorrect | LZ |  |

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | ok | ok | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | ok | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | ok | concerning | match | LZ |  |
| codex / trial3 | match | ok | concerning | incorrect | LZ |  |

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | match | LZ |  |
| claude-code / trial2 | incorrect | incorrect | incorrect | incorrect | — |  |
| claude-code / trial3 | ok | ok | concerning | incorrect | LZ |  |
| codex / trial1 | concerning | concerning | concerning | incorrect | — |  |
| codex / trial2 | ok | ok | incorrect | incorrect | LZ |  |
| codex / trial3 | ok | ok | concerning | incorrect | LZ |  |

---

## Q 3-a. What variables in the raw data is `output` *Image identity* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | incorrect | LZ |  |
| claude-code / trial2 | match | ok | ok | ok | — |  |
| claude-code / trial3 | match | ok | ok | incorrect | LZ |  |
| codex / trial1 | ok | ok | concerning | incorrect | LZ |  |
| codex / trial2 | ok | ok | ok | concerning | LZ |  |
| codex / trial3 | ok | ok | concerning | incorrect | LZ |  |

---

## Q 3-b. What processing is involved in computing `output` *Image identity*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | incorrect | LZ |  |
| claude-code / trial2 | match | match | concerning | concerning | Claude judge | Claude caught a problem with agent implmentation of image name mapping |
| claude-code / trial3 | match | match | match | concerning | LZ |  |
| codex / trial1 | match | match | concerning | incorrect | LZ |  |
| codex / trial2 | match | match | ok | concerning | LZ |  |
| codex / trial3 | match | match | concerning | incorrect | LZ |  |

---

## Q 3-c. How is `output` *Image identity* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | incorrect | LZ |  |
| claude-code / trial2 | match | ok | ok | ok | — |  |
| claude-code / trial3 | match | ok | match | concerning | LZ |  |
| codex / trial1 | match | ok | match | incorrect | LZ |  |
| codex / trial2 | match | ok | match | concerning | LZ |  |
| codex / trial3 | match | ok | match | incorrect | LZ |  |

---

## Q 4-a. What variables in the raw data is `output` *Image change* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | ok | concerning | ok | incorrect | LZ |  |
| claude-code / trial2 | ok | concerning | ok | ok | — |  |
| claude-code / trial3 | match | ok | ok | concerning | LZ |  |
| codex / trial1 | ok | concerning | ok | incorrect | LZ |  |
| codex / trial2 | ok | ok | concerning | incorrect | LZ |  |
| codex / trial3 | ok | ok | concerning | concerning | LZ |  |

---

## Q 4-b. What processing is involved in computing `output` *Image change*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | incorrect | Claude judge | Human error |
| claude-code / trial2 | match | match | ok | ok | — |  |
| claude-code / trial3 | match | match | match | concerning | LZ |  |
| codex / trial1 | match | match | concerning | incorrect | LZ |  |
| codex / trial2 | match | ok | concerning | incorrect | LZ |  |
| codex / trial3 | match | match | concerning | concerning | LZ |  |

---

## Q 4-d. How is `output` *Image change* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | incorrect | LZ |  |
| claude-code / trial2 | ok | ok | ok | ok | — |  |
| claude-code / trial3 | match | ok | match | concerning | LZ |  |
| codex / trial1 | match | ok | match | incorrect | LZ |  |
| codex / trial2 | match | ok | match | concerning | LZ |  |
| codex / trial3 | match | match | match | incorrect | LZ |  |

---

## Q 5-a. What variables in the raw data is `output` *Running speed* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | match | match | match | — |  |
| codex / trial3 | match | match | match | match | — |  |

---

## Q 5-b. What processing is involved in computing `output` *Running speed*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | incorrect | Claude judge | Claude caught a minor bug |
| claude-code / trial2 | incorrect | match | concerning | incorrect | — |  |
| claude-code / trial3 | match | match | concerning | incorrect | LZ |  |
| codex / trial1 | match | match | concerning | incorrect | LZ |  |
| codex / trial2 | match | match | match | incorrect | LZ |  |
| codex / trial3 | match | match | match | incorrect | LZ |  |

---

## Q 5-d. How is `output` *Running speed* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | ok | incorrect | LZ |  |
| claude-code / trial3 | match | match | match | incorrect | LZ |  |
| codex / trial1 | match | match | match | incorrect | LZ |  |
| codex / trial2 | match | match | match | incorrect | LZ |  |
| codex / trial3 | match | match | match | incorrect | LZ |  |

---

## Q 6-a. What variables in the raw data is `output` *Pupil diameter* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | concerning | incorrect | — |  |
| claude-code / trial2 | concerning | ok | concerning | concerning | — |  |
| claude-code / trial3 | concerning | ok | incorrect | incorrect | — |  |
| codex / trial1 | concerning | ok | concerning | incorrect | — |  |
| codex / trial2 | ok | concerning | concerning | incorrect | LZ |  |
| codex / trial3 | ok | ok | incorrect | incorrect | LZ |  |

---

## Q 6-b. What processing is involved in computing `output` *Pupil diameter*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | incorrect | LZ |  |
| claude-code / trial2 | match | ok | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | match | concerning | incorrect | LZ |  |
| codex / trial1 | match | match | concerning | incorrect | LZ |  |
| codex / trial2 | match | match | concerning | incorrect | LZ |  |
| codex / trial3 | match | match | concerning | incorrect | LZ |  |

---

## Q 6-d. How is `output` *Pupil diameter* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | incorrect | match | ok | incorrect | LZ |  |
| claude-code / trial3 | match | match | match | incorrect | LZ |  |
| codex / trial1 | match | match | match | incorrect | LZ |  |
| codex / trial2 | match | match | match | incorrect | LZ |  |
| codex / trial3 | match | match | match | incorrect | LZ |  |

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | match | match | match | — |  |
| codex / trial3 | match | match | match | match | — |  |

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | concerning | LZ |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | ok | match | match | — |  |
| codex / trial2 | match | match | match | match | — |  |
| codex / trial3 | match | match | match | match | — |  |

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | incorrect | LZ |  |
| claude-code / trial2 | match | ok | ok | concerning | LZ |  |
| claude-code / trial3 | match | ok | match | ok | — |  |
| codex / trial1 | match | ok | concerning | concerning | LZ |  |
| codex / trial2 | match | ok | match | concerning | LZ |  |
| codex / trial3 | match | ok | concerning | concerning | LZ |  |

---

## Q 9-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | match | concerning | LZ |  |
| claude-code / trial2 | concerning | ok | match | match | LZ |  |
| claude-code / trial3 | concerning | ok | match | ok | LZ |  |
| codex / trial1 | concerning | ok | match | ok | LZ |  |
| codex / trial2 | concerning | ok | match | ok | LZ |  |
| codex / trial3 | concerning | ok | match | concerning | LZ |  |

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | ok | ok | match | concerning | LZ |  |
| claude-code / trial2 | ok | ok | match | match | — |  |
| claude-code / trial3 | ok | concerning | match | ok | — |  |
| codex / trial1 | ok | ok | match | ok | — |  |
| codex / trial2 | ok | ok | match | match | — |  |
| codex / trial3 | ok | ok | match | ok | — |  |

---

## Q 9-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | match | incorrect | LZ |  |
| claude-code / trial2 | concerning | concerning | better | incorrect | LZ | I think the LLM judge did not parse this Q correctly |
| claude-code / trial3 | incorrect | concerning | incorrect | incorrect | — |  |
| codex / trial1 | concerning | ok | match | concerning | LZ |  |
| codex / trial2 | concerning | concerning | match | incorrect | LZ |  |
| codex / trial3 | concerning | concerning | concerning | concerning | — |  |

**Overall comment:** The LLM judge seems to have completely misunderstood this question.

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | incorrect | — |  |
| claude-code / trial2 | concerning | concerning | better | incorrect | LZ |  |
| claude-code / trial3 | match | ok | match | incorrect | — |  |
| codex / trial1 | match | ok | match | concerning | — |  |
| codex / trial2 | match | ok | match | concerning | — |  |
| codex / trial3 | match | ok | match | concerning | — |  |

---

## Q 9-e. How is memory usage optimized?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | — | — | — |  |
| claude-code / trial2 | match | ok | — | — | — |  |
| claude-code / trial3 | match | ok | — | — | — |  |
| codex / trial1 | match | ok | — | — | — |  |
| codex / trial2 | match | ok | — | — | — |  |
| codex / trial3 | match | ok | — | — | — |  |
