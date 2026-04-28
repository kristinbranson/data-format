# Eval comparison — sosa2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

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

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | concerning | Claude judge | AI Correctly identified that the agent code is less robust |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | concerning | incorrect | Claude judge |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | ok | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Claude identified some implementation that is less robust

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | better | ok | incorrect | — |  |
| claude-code / trial2 | ok | incorrect | incorrect | Human |  |
| claude-code / trial3 | better | concerning | incorrect | Human |  |
| codex / trial1 | ok | concerning | incorrect | Human |  |
| codex / trial2 | ok | incorrect | incorrect | Human |  |
| codex / trial3 | better | incorrect | incorrect | Human |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | concerning | — |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | better | incorrect | Human |  |
| codex / trial1 | ok | match | ok | — |  |
| codex / trial2 | incorrect | concerning | incorrect | — |  |
| codex / trial3 | match | concerning | match | Human |  |

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | better | better | concerning | — |  |
| claude-code / trial2 | better | concerning | incorrect | Human |  |
| claude-code / trial3 | better | better | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** AI judege being very inconsistent

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | incorrect | incorrect | incorrect | — |  |
| codex / trial3 | match | match | better | — |  |

**Overall comment:** Both judges caught the mistake

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | concerning | — |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | ok | incorrect | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | ok | — |  |

**Overall comment:** inconsistent rating from AI judges

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | concerning | — |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | ok | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

---

