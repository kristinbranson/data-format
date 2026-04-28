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

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | concerning | ok | Human |  |

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | incorrect | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | — |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | ok | ok | — |  |
| codex / trial1 | match | match | incorrect | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | ok | ok | — |  |

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | concerning | — |  |

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | better | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | ok | concerning | — |  |

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | incorrect | Human |  |
| claude-code / trial2 | concerning | concerning | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | Human |  |
| codex / trial1 | concerning | concerning | ok | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | concerning | concerning | better | — |  |

**Overall comment:** Claude caught some potential problems but not others

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | incorrect | match | match | Human |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | incorrect | — |  |
| codex / trial2 | match | concerning | ok | Human |  |
| codex / trial3 | match | match | incorrect | — |  |

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | better | Human |  |
| claude-code / trial2 | match | incorrect | incorrect | Human |  |
| claude-code / trial3 | match | concerning | better | Human |  |
| codex / trial1 | match | concerning | incorrect | Human |  |
| codex / trial2 | match | incorrect | better | Human |  |
| codex / trial3 | match | concerning | incorrect | Human |  |

**Overall comment:** Different choices in choosing bin edges but are all valid solution

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | concerning | match | match | Human |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | better | concerning | Human |  |
| claude-code / trial2 | match | concerning | concerning | Human |  |
| claude-code / trial3 | match | concerning | concerning | Human |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | concerning | match | ok | Human |  |
| codex / trial3 | match | match | ok | — |  |

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | incorrect | Human |  |
| claude-code / trial2 | concerning | concerning | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | Human |  |
| codex / trial1 | concerning | concerning | ok | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | concerning | concerning | better | — |  |

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | incorrect | — |  |
| claude-code / trial2 | match | concerning | incorrect | Human |  |
| claude-code / trial3 | match | concerning | incorrect | Human |  |
| codex / trial1 | match | concerning | ok | Human |  |
| codex / trial2 | match | ok | concerning | — |  |
| codex / trial3 | match | concerning | better | Human |  |

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | better | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | concerning | Human |  |

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | better | ok | concerning | — |  |
| claude-code / trial3 | match | ok | concerning | — |  |
| codex / trial1 | better | ok | concerning | — |  |
| codex / trial2 | better | concerning | ok | Human |  |
| codex / trial3 | better | incorrect | concerning | Human |  |

---

## Q 13-a. What are the most time-consuming steps of the code?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | match | ok | — |  |
| claude-code / trial3 | ok | match | ok | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 13-c. What processing does the code repeat multiple times?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | ok | match | ok | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | Human | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | match | better | incorrect | Human |  |
| codex / trial1 | match | ok | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | match | — |  |
