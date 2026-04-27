# Eval comparison — lee2025

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | incorrect | — |  |
| claude-code / trial2 | match | ok | incorrect | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | ok | incorrect | — |  |
| codex / trial2 | match | concerning | match | Human |  |
| codex / trial3 | match | better | incorrect | Human |  |

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | — |  |
| claude-code / trial2 | match | match | incorrect | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | incorrect | Human | minor difference, no need to flag |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | concerning | better | incorrect | should't assume human is always right :) |  |
| codex / trial2 | match | concerning | match | Human |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | ok | concerning | match | Human |  |
| codex / trial3 | match | better | ok | Human |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | better | concerning | incorrect | Human |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | concerning | better | incorrect | Human | AI judge is not doing great here |
| codex / trial2 | better | concerning | match | Human |  |
| codex / trial3 | match | match | concerning | — |  |

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | concerning | concerning | — |  |
| claude-code / trial2 | concerning | match | incorrect | Human |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | concerning | match | ok | Human |  |
| codex / trial2 | ok | concerning | match | Human |  |
| codex / trial3 | concerning | match | incorrect | Human |  |

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | concerning | incorrect | Human |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | concerning | better | incorrect | Human |  |
| codex / trial2 | ok | concerning | match | Human |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | incorrect | — |  |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | ok | — | — | — |  |
| claude-code / trial2 | ok | — | — | — |  |
| claude-code / trial3 | ok | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

---

## Q 3-c. How is `input` *Blocked positions* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

---

## Q 4-b. What processing is involved in computing `output` *Position*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |  |
| claude-code / trial2 | match | — | — | — |  |
| claude-code / trial3 | match | — | — | — |  |
| codex / trial1 | match | — | — | — |  |
| codex / trial2 | match | — | — | — |  |
| codex / trial3 | match | — | — | — |  |
