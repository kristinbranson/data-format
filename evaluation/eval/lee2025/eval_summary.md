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

**Overall comment:** Claude rating inconsistent for the same agent implementation

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
