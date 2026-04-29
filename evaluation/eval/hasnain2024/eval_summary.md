# Eval comparison — hasnain2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** LLM judge flagged the extra subject found by the code, but is not consistent

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
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | match | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | concerning | match | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Judge decisions are inconsistent

---
## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | concerning | concerning | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | concerning | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** LLM judges are very inconsistent regarding the time bin choice

---
## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
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

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | incorrect | match | match | — |  |
| claude-code / trial3 | incorrect | concerning | concerning | — |  |
| codex / trial1 | incorrect | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | incorrect | match | match | — |  |

**Overall comment:** LLM judge only flagged one of the incorrect solution but not the others.

---
## Q 3-b. What processing is involved in computing `output` *lick_direction*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | concerning | — |  |
| codex / trial1 | match | — | match | — |  |
| codex / trial2 | match | match | — | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
## Q 4-a. What variables in the raw data is `output` *context* derived from?

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
## Q 4-b. What processing is involved in computing `output` *context*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | — | match | — |  |
| codex / trial2 | match | match | — | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** _(no overall comment)_

---
