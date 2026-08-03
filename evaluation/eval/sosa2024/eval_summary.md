# Eval comparison — sosa2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | ok |
| codex / trial2 | match | match | match | ok |
| codex / trial3 | match | match | match | match |

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | ok |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 1-c. How are the data split into sessions?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | match | concerning | concerning |
| claude-code / trial2 | match | match | match | concerning |
| claude-code / trial3 | concerning | match | concerning | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | ok | incorrect |
| codex / trial3 | match | match | match | match |

**Overall comment:** Claude correctly flagged some implementations as less robust.

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | better | better | ok | incorrect |
| claude-code / trial2 | ok | ok | incorrect | incorrect |
| claude-code / trial3 | better | better | concerning | incorrect |
| codex / trial1 | ok | better | concerning | incorrect |
| codex / trial2 | ok | better | incorrect | incorrect |
| codex / trial3 | better | better | incorrect | incorrect |

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | concerning |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | incorrect |
| codex / trial3 | match | match | match | match |

---

## Q 2-b. How is the `neural` data processed?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | concerning |
| claude-code / trial2 | match | ok | concerning | incorrect |
| claude-code / trial3 | match | ok | better | incorrect |
| codex / trial1 | ok | match | match | ok |
| codex / trial2 | incorrect | incorrect | concerning | incorrect |
| codex / trial3 | match | match | concerning | match |

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | better | ok | better | concerning |
| claude-code / trial2 | better | ok | concerning | incorrect |
| claude-code / trial3 | better | ok | better | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | match | match | concerning |

**Overall comment:** Claude judge gave inconsistent ratings for the same solution.

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | ok |
| codex / trial2 | incorrect | incorrect | incorrect | incorrect |
| codex / trial3 | match | match | match | better |

**Overall comment:** Both judges caught the mistake.

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | concerning | ok | concerning |
| claude-code / trial2 | match | concerning | concerning | incorrect |
| claude-code / trial3 | match | concerning | ok | incorrect |
| codex / trial1 | match | ok | match | ok |
| codex / trial2 | match | concerning | match | incorrect |
| codex / trial3 | match | ok | match | ok |

**Overall comment:** Inconsistent ratings from the LLM judges for the same solution.

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | concerning | ok | concerning |
| claude-code / trial2 | match | concerning | concerning | incorrect |
| claude-code / trial3 | match | concerning | ok | incorrect |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | concerning | match | incorrect |
| codex / trial3 | match | match | match | match |

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | ok |
| codex / trial1 | match | match | match | concerning |
| codex / trial2 | match | match | match | ok |
| codex / trial3 | match | match | concerning | ok |

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | ok | concerning | incorrect |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | ok | match | incorrect |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | ok |
| claude-code / trial2 | match | ok | concerning | incorrect |
| claude-code / trial3 | match | ok | ok | ok |
| codex / trial1 | match | ok | match | incorrect |
| codex / trial2 | match | ok | match | ok |
| codex / trial3 | match | ok | ok | ok |

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | ok | concerning | concerning |

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | concerning | concerning |

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | ok | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | ok |
| codex / trial3 | match | ok | match | concerning |

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | ok | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | better |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | ok | concerning |

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | ok | incorrect |
| claude-code / trial2 | concerning | ok | concerning | incorrect |
| claude-code / trial3 | match | ok | concerning | incorrect |
| codex / trial1 | concerning | ok | concerning | ok |
| codex / trial2 | match | ok | match | concerning |
| codex / trial3 | concerning | ok | concerning | better |

**Overall comment:** Claude caught some of the potential problems but missed others.

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | ok | ok | — | — |
| claude-code / trial2 | ok | ok | — | — |
| claude-code / trial3 | ok | ok | — | — |
| codex / trial1 | ok | ok | — | — |
| codex / trial2 | ok | ok | — | — |
| codex / trial3 | ok | ok | — | — |

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | incorrect | incorrect | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | match | match |
| claude-code / trial3 | match | ok | match | match |
| codex / trial1 | match | ok | match | incorrect |
| codex / trial2 | match | ok | concerning | ok |
| codex / trial3 | match | ok | match | incorrect |

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | — | — |
| claude-code / trial2 | match | ok | — | — |
| claude-code / trial3 | match | ok | — | — |
| codex / trial1 | match | ok | — | — |
| codex / trial2 | match | ok | — | — |
| codex / trial3 | match | ok | — | — |

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | concerning | incorrect | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | match |
| codex / trial3 | match | match | match | match |

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | better | concerning |
| claude-code / trial2 | match | ok | concerning | concerning |
| claude-code / trial3 | match | ok | concerning | concerning |
| codex / trial1 | match | match | match | ok |
| codex / trial2 | concerning | ok | match | ok |
| codex / trial3 | match | match | match | ok |

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | incorrect | match | ok |
| codex / trial3 | match | match | match | match |

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | concerning | ok | ok | incorrect |
| claude-code / trial2 | concerning | ok | concerning | incorrect |
| claude-code / trial3 | match | ok | concerning | incorrect |
| codex / trial1 | concerning | ok | concerning | ok |
| codex / trial2 | match | ok | match | concerning |
| codex / trial3 | concerning | ok | concerning | better |

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | incorrect |
| claude-code / trial2 | match | ok | concerning | incorrect |
| claude-code / trial3 | match | match | concerning | incorrect |
| codex / trial1 | match | ok | concerning | ok |
| codex / trial2 | match | ok | ok | concerning |
| codex / trial3 | match | ok | concerning | better |

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | match | match | match |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | match | match | match |
| codex / trial2 | match | match | match | ok |
| codex / trial3 | match | ok | concerning | concerning |

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | ok |
| claude-code / trial2 | match | match | match | match |
| claude-code / trial3 | match | match | match | match |
| codex / trial1 | match | ok | match | better |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | concerning | concerning |

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | concerning |
| claude-code / trial2 | better | ok | ok | concerning |
| claude-code / trial3 | match | ok | ok | concerning |
| codex / trial1 | better | ok | ok | concerning |
| codex / trial2 | better | ok | concerning | ok |
| codex / trial3 | better | ok | incorrect | concerning |

---

## Q 13-a. What are the most time-consuming steps of the code?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | match |
| claude-code / trial2 | match | ok | match | ok |
| claude-code / trial3 | match | ok | match | incorrect |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | ok | ok | match | ok |
| claude-code / trial3 | ok | ok | match | ok |
| codex / trial1 | ok | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

---

## Q 13-c. What processing does the code repeat multiple times?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | ok | match |
| claude-code / trial2 | match | ok | ok | ok |
| claude-code / trial3 | ok | ok | match | ok |
| codex / trial1 | match | ok | match | match |
| codex / trial2 | match | ok | match | match |
| codex / trial3 | match | ok | match | match |

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | ok | match | match |
| claude-code / trial2 | match | ok | ok | ok |
| claude-code / trial3 | match | ok | better | incorrect |
| codex / trial1 | match | ok | ok | match |
| codex / trial2 | match | ok | match | ok |
| codex / trial3 | match | ok | match | match |

---

## Q 13-e. How is memory usage optimized?

| Agent / trial | LZ | KB | Claude judge | Codex judge |
|---|---|---|---|---|
| claude-code / trial1 | match | — | — | — |
| claude-code / trial2 | match | — | — | — |
| claude-code / trial3 | match | — | — | — |
| codex / trial1 | match | — | — | — |
| codex / trial2 | match | — | — | — |
| codex / trial3 | match | — | — | — |
