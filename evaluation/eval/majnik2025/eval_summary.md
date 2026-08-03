# Eval comparison — majnik2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | concerning | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | ok | — |  |
| codex / trial2 | match | match | match | ok | — |  |
| codex / trial3 | match | match | better | incorrect | LZ |  |

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | concerning | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | match | match | match | — |  |
| codex / trial3 | match | match | match | match | — |  |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | match | match | ok | — |  |
| codex / trial3 | match | match | match | ok | — |  |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | better | better | incorrect | LZ |  |
| claude-code / trial2 | match | better | ok | incorrect | — |  |
| claude-code / trial3 | match | better | concerning | incorrect | LZ |  |
| codex / trial1 | match | better | better | better | LZ |  |
| codex / trial2 | match | better | ok | incorrect | — |  |
| codex / trial3 | match | better | better | incorrect | LZ |  |

**Overall comment:** Judges are inconsistent despite all agent runs producing the same solution.

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | ok | match | match | — |  |
| codex / trial2 | match | match | match | ok | — |  |
| codex / trial3 | match | ok | match | incorrect | — |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | better | match | LZ |  |
| codex / trial2 | match | match | match | ok | — |  |
| codex / trial3 | match | match | match | match | — |  |

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | ok | ok | ok | incorrect | — |  |
| claude-code / trial2 | match | incorrect | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | match | concerning | match | LZ |  |
| codex / trial1 | match | match | better | better | LZ |  |
| codex / trial2 | match | match | ok | ok | — |  |
| codex / trial3 | match | match | better | incorrect | LZ |  |

**Overall comment:** Some agents added the paper's temporal binning step; LLM judge ratings are inconsistent.

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | match | match | match | — |  |
| codex / trial3 | match | match | match | ok | — |  |

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | better | — |  |
| codex / trial2 | match | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | incorrect | — |  |

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | better | incorrect | LZ |  |
| claude-code / trial2 | match | ok | ok | incorrect | — |  |
| claude-code / trial3 | match | ok | incorrect | incorrect | LZ |  |
| codex / trial1 | match | ok | better | better | LZ |  |
| codex / trial2 | match | ok | ok | incorrect | — |  |
| codex / trial3 | match | ok | better | incorrect | LZ |  |

**Overall comment:** LLM judge ratings are inconsistent, ranging from "better" to "incorrect" for the same binning strategy.

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | match | — |  |
| claude-code / trial2 | match | concerning | match | ok | — |  |
| claude-code / trial3 | match | match | concerning | match | LZ |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | ok | match | incorrect | — |  |
| codex / trial3 | match | match | match | incorrect | — |  |

---

## Q 3-b. What processing is involved in computing `input` *Time*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | concerning | incorrect | LZ |  |
| codex / trial1 | match | match | better | better | LZ |  |
| codex / trial2 | match | match | better | incorrect | LZ |  |
| codex / trial3 | match | match | better | incorrect | LZ |  |

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | match | match | — |  |
| claude-code / trial3 | match | match | match | match | — |  |
| codex / trial1 | match | match | match | better | — |  |
| codex / trial2 | match | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | incorrect | — |  |

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match | — |  |
| claude-code / trial2 | match | match | ok | incorrect | — |  |
| claude-code / trial3 | match | match | concerning | incorrect | LZ |  |
| codex / trial1 | match | match | match | match | — |  |
| codex / trial2 | match | match | ok | incorrect | — |  |
| codex / trial3 | match | match | ok | incorrect | — |  |

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | concerning | incorrect | concerning | incorrect | — |  |
| claude-code / trial2 | concerning | incorrect | concerning | incorrect | — |  |
| claude-code / trial3 | concerning | incorrect | incorrect | incorrect | — |  |
| codex / trial1 | match | ok | better | ok | LZ |  |
| codex / trial2 | match | ok | concerning | incorrect | LZ |  |
| codex / trial3 | match | ok | better | incorrect | LZ |  |

**Overall comment:** Judge ratings are inconsistent for the same solutions.

---

## Q 4-d. How is `output` *Motion energy* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | incorrect | — |  |
| claude-code / trial2 | incorrect | incorrect | concerning | incorrect | — |  |
| claude-code / trial3 | incorrect | incorrect | concerning | incorrect | — |  |
| codex / trial1 | match | match | better | better | LZ |  |
| codex / trial2 | match | ok | ok | incorrect | — |  |
| codex / trial3 | match | ok | better | incorrect | LZ |  |

**Overall comment:** Judge ratings are inconsistent.

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | ok | — |  |
| claude-code / trial2 | match | incorrect | ok | concerning | — |  |
| claude-code / trial3 | concerning | incorrect | concerning | incorrect | — |  |
| codex / trial1 | match | match | better | better | LZ |  |
| codex / trial2 | match | incorrect | match | ok | — |  |
| codex / trial3 | match | concerning | better | incorrect | LZ |  |

---

## Q 6-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | ok | ok | match | match | — |  |
| claude-code / trial2 | match | ok | match | match | — |  |
| claude-code / trial3 | match | ok | match | match | — |  |
| codex / trial1 | ok | ok | match | match | — |  |
| codex / trial2 | ok | ok | match | match | — |  |
| codex / trial3 | ok | ok | match | match | — |  |

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | ok | — |  |
| claude-code / trial2 | match | ok | match | ok | — |  |
| claude-code / trial3 | match | ok | match | ok | — |  |
| codex / trial1 | match | ok | better | better | Claude judge |  |
| codex / trial2 | match | ok | match | ok | — |  |
| codex / trial3 | match | ok | ok | match | — |  |

**Overall comment:** Some agents' solutions for detecting missing frames are more efficient.

---

## Q 6-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | ok | — |  |
| claude-code / trial2 | match | ok | match | ok | — |  |
| claude-code / trial3 | match | ok | match | match | — |  |
| codex / trial1 | match | ok | match | ok | — |  |
| codex / trial2 | match | ok | match | ok | — |  |
| codex / trial3 | ok | concerning | match | ok | — |  |

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | ok | — |  |
| claude-code / trial2 | match | ok | match | ok | — |  |
| claude-code / trial3 | match | ok | incorrect | ok | LZ |  |
| codex / trial1 | match | ok | match | concerning | — |  |
| codex / trial2 | match | ok | match | ok | — |  |
| codex / trial3 | match | ok | match | ok | — |  |

---

## Q 6-e. How is memory usage optimized?

| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — | LZ |  |
| claude-code / trial2 | match | — | — | — | LZ |  |
| claude-code / trial3 | match | — | — | — | LZ |  |
| codex / trial1 | match | — | — | — | LZ |  |
| codex / trial2 | match | — | — | — | LZ |  |
| codex / trial3 | match | — | — | — | LZ |  |
