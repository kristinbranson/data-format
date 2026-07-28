# Eval comparison — sosa2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | concerning | concerning | Claude judge | AI Correctly identified that the agent code is less robust |
| claude-code / trial2 | match | match | concerning | — |  |
| claude-code / trial3 | match | concerning | incorrect | Claude judge |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | ok | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

**Overall comment:** Claude correctly flagged some implementations as less robust.

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | better | ok | incorrect | — |  |
| claude-code / trial2 | ok | incorrect | incorrect | LZ |  |
| claude-code / trial3 | better | concerning | incorrect | LZ |  |
| codex / trial1 | ok | concerning | incorrect | LZ |  |
| codex / trial2 | ok | incorrect | incorrect | LZ |  |
| codex / trial3 | better | incorrect | incorrect | LZ |  |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | concerning | — |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | better | incorrect | LZ |  |
| codex / trial1 | ok | match | ok | — |  |
| codex / trial2 | incorrect | concerning | incorrect | — |  |
| codex / trial3 | match | concerning | match | LZ |  |

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | better | better | concerning | — |  |
| claude-code / trial2 | better | concerning | incorrect | LZ |  |
| claude-code / trial3 | better | better | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | concerning | — |  |

**Overall comment:** Claude judge gave inconsistent ratings for the same solution.

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | incorrect | incorrect | incorrect | — |  |
| codex / trial3 | match | match | better | — |  |

**Overall comment:** Both judges caught the mistake.

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | concerning | — |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | ok | incorrect | — |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | ok | — |  |

**Overall comment:** Inconsistent ratings from the LLM judges for the same solution.

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | concerning | — |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | ok | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | incorrect | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | ok | — |  |
| codex / trial1 | match | match | concerning | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | concerning | ok | LZ |  |

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | incorrect | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | — |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | ok | ok | — |  |
| codex / trial1 | match | match | incorrect | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | ok | ok | — |  |

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | concerning | LZ |  |

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | concerning | LZ |  |

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | concerning | — |  |

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | better | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | ok | concerning | — |  |

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | incorrect | LZ |  |
| claude-code / trial2 | concerning | concerning | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | LZ |  |
| codex / trial1 | concerning | concerning | ok | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | concerning | concerning | better | — |  |

**Overall comment:** Claude caught some of the potential problems but missed others.

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | incorrect | match | match | LZ |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | incorrect | — |  |
| codex / trial2 | match | concerning | ok | LZ |  |
| codex / trial3 | match | match | incorrect | — |  |

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | concerning | match | match | LZ |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | better | concerning | LZ |  |
| claude-code / trial2 | match | concerning | concerning | LZ |  |
| claude-code / trial3 | match | concerning | concerning | LZ |  |
| codex / trial1 | match | match | ok | — |  |
| codex / trial2 | concerning | match | ok | LZ |  |
| codex / trial3 | match | match | ok | — |  |

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | incorrect | LZ |  |
| claude-code / trial2 | concerning | concerning | incorrect | — |  |
| claude-code / trial3 | match | concerning | incorrect | LZ |  |
| codex / trial1 | concerning | concerning | ok | — |  |
| codex / trial2 | match | match | concerning | — |  |
| codex / trial3 | concerning | concerning | better | — |  |

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | incorrect | — |  |
| claude-code / trial2 | match | concerning | incorrect | LZ |  |
| claude-code / trial3 | match | concerning | incorrect | LZ |  |
| codex / trial1 | match | concerning | ok | LZ |  |
| codex / trial2 | match | ok | concerning | — |  |
| codex / trial3 | match | concerning | better | LZ |  |

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | concerning | concerning | LZ |  |

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | — |  |
| claude-code / trial2 | match | match | match | — |  |
| claude-code / trial3 | match | match | match | — |  |
| codex / trial1 | match | match | better | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | concerning | concerning | LZ |  |

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | concerning | — |  |
| claude-code / trial2 | better | ok | concerning | — |  |
| claude-code / trial3 | match | ok | concerning | — |  |
| codex / trial1 | better | ok | concerning | — |  |
| codex / trial2 | better | concerning | ok | LZ |  |
| codex / trial3 | better | incorrect | concerning | LZ |  |

---

## Q 13-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | match | ok | — |  |
| claude-code / trial3 | match | match | incorrect | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | ok | match | ok | — |  |
| claude-code / trial3 | ok | match | ok | — |  |
| codex / trial1 | ok | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 13-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | — |  |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | ok | match | ok | — |  |
| codex / trial1 | match | match | match | — |  |
| codex / trial2 | match | match | match | — |  |
| codex / trial3 | match | match | match | — |  |

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|
| claude-code / trial1 | match | match | match | — |  |
| claude-code / trial2 | match | ok | ok | — |  |
| claude-code / trial3 | match | better | incorrect | LZ |  |
| codex / trial1 | match | ok | match | — |  |
| codex / trial2 | match | match | ok | — |  |
| codex / trial3 | match | match | match | — |  |
