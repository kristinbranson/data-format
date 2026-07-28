# Eval comparison — lee2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | incorrect | — |  |
| claude-code / trial2 | match | ok | incorrect | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | ok | incorrect | — |  |
| codex / trial2 | match | concerning | match | LZ |  |
| codex / trial3 | match | better | incorrect | LZ |  |

**Overall comment:** Judge ratings are *very inconsistent* for the same agent implementation across 6 runs.

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | LZ | minor inconsistency |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | concerning | better | incorrect | LZ | Shouldn't assume human is correct :) |
| codex / trial2 | match | concerning | match | LZ |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | ok | concerning | match | LZ |  |
| codex / trial3 | match | better | ok | LZ |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | better | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | concerning | better | incorrect | LZ |  |
| codex / trial2 | better | concerning | match | LZ |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** Claude's ratings don't make sense to me here.

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | concerning | — |  |
| claude-code / trial2 | concerning | match | incorrect | LZ |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | concerning | match | ok | LZ |  |
| codex / trial2 | ok | concerning | match | LZ |  |
| codex / trial3 | concerning | match | incorrect | LZ |  |

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | concerning | better | incorrect | LZ |  |
| codex / trial2 | ok | concerning | match | LZ |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Same as 2-b: Claude rated a partial solution "better" but the complete solution "concerning".

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | concerning | incorrect | LZ | Both are ok |
| claude-code / trial2 | ok | ok | incorrect | — |  |
| claude-code / trial3 | ok | concerning | incorrect | LZ |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Two possible solutions; Claude judge is inconsistent.

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | LZ |  |
| claude-code / trial2 | match | ok | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | LZ |  |
| codex / trial1 | match | ok | incorrect | — |  |
| codex / trial2 | match | concerning | match | LZ |  |
| codex / trial3 | match | better | incorrect | LZ |  |

**Overall comment:** Same as above.

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 4-b. What processing is involved in computing `output` *Position*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | LZ |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | ok | incorrect | — |  |
| codex / trial1 | match | ok | incorrect | — |  |
| codex / trial2 | match | concerning | match | LZ |  |
| codex / trial3 | match | better | incorrect | Claude judge |  |

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | concerning | match | LZ |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | Claude judge |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | concerning | match | LZ |  |
| codex / trial3 | match | better | ok | Claude judge |  |

---

## Q 8-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | ok | — |  |

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | ok | concerning | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | ok | — |  |

---

## Q 8-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | ok | ok | concerning | — |  |
| codex / trial1 | ok | match | ok | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | incorrect | match | ok | LZ |  |

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | ok | Claude judge |  |
