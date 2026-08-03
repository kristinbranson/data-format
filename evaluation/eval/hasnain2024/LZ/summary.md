# Evaluation summary — hasnain2024

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** All solutions handled the mix of data formats correctly; 1/6 didn't load the full dataset.

---

## Q 1-b. How are the data split into subjects?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-c. How are the data split into sessions?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Session structure is very simple.

---

## Q 1-d. Are the data correctly split into trials?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Slightly different exclusion procedures across agents.

---

## Q 1-e. How are trials filtered based on quality controls?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Some minor differences in filtering decisions.

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** Overall correct solutions, but most didn't handle the dual-probe sessions correctly.

---

## Q 2-b. How is the `neural` data processed?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Small differences in preprocessing parameters, but all are valid. Agents were able to follow the reference solution using the paper's preprocessing code.

---

## Q 2-c. How is the `neural` data filtered based on quality controls?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Two different binning choices appear in the paper; both are valid.

---

## Q 3-a. What variables in the raw data is `input` *time_from_go_cue* derived from?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_go_cue*?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** The temporal resolution (dt) varies between agents

---

## Q 3-c. How is `input` *time_from_go_cue* aligned with the neural data?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 4-a. What variables in the raw data is `output` *lick_direction* derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | _(no note)_ |
| claude-code / trial3 | incorrect | _(no note)_ |
| codex / trial1 | incorrect | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | incorrect | _(no note)_ |

**Overall comment:** The lick direction available in the data is the correct/instructed direction. One agent derived the actual response direction by combining instructed direction with trial correctness; another used `bp.ev.Lick` to derive the first lick direction. 4/6 agents got it wrong.

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 5-a. What variables in the raw data is `output` *context* derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 5-b. What processing is involved in computing `output` *context*?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 6-b. What processing is involved in computing `output` *outcome*?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | concerning | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** The paper used a sophisticated PCA-based procedure to estimate tongue velocity from multiple markers across both cameras. None of the agents came close; only one agent attempted to combine information from multiple cameras.

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** Highly variable choices across agents, but there is no single definitive correct/incorrect solution.

---

## Q 7-d. How is `output` *tongue_velocity* aligned with the neural data?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** 4/6 solutions used both top and bottom paw tracking features; only 1/6 scaled the velocity to physical units.

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | concerning | _(no note)_ |
| codex / trial2 | incorrect | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** The paper's code has a bug in the baseline subtraction (x-axis baseline subtracted from both x and y velocity). One agent faithfully reimplemented the bug, 3/6 agents corrected it, and 2/6 agents skipped baseline subtraction altogether.

---

## Q 8-d. How is `output` *paw_velocity* aligned with the neural data?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-a. What variables in the raw data is `output` *motion_energy* derived from?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-b. What processing is involved in computing `output` *motion_energy*?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-d. How is `output` *motion_energy* aligned with the neural data?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Most agents use the bitcode-derived timestamp for alignment, falling back to a hardcoded 0.5s shift (taken from the reference's tutorial code) when bitcode metadata is unavailable.

---

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 11-a. What are the most time-consuming steps of the code?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 11-b. What loops in the code could have been vectorized to improve efficiency?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** Heavy use of per-trial loops instead of vectorized solutions.

---

## Q 11-c. What processing does the code repeat multiple times?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 11-d. What unnecessary processing does the code do that is discarded in downstream analyses?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 11-e. How is memory usage optimized?




| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
