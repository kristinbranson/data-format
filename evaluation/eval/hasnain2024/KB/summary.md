# Evaluation summary — hasnain2024 · evaluator KB

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | did not completely check that this works, but this seems to use regexps to parse matlab code to figure out the parameters |
| codex / trial2 | incorrect | shorter list than manual |
| codex / trial3 | ok | didn't check completely, parses .m code to get session names |

**Overall comment:** _(no overall comment)_

---

## Q 1-b. How are the data split into subjects?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | subjects coded ok, but original list of sessions is short |
| codex / trial3 | ok | _(no note)_ |

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

**Overall comment:** _(no overall comment)_

---

## Q 1-d. Are the data correctly split into trials?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | filters no response trials, which manual does not |
| claude-code / trial2 | concerning | does not filter trials that run past end of neural recording |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | concerning | filters no response trials, which manual does not, does not filter trials that run past end of neural recording |
| codex / trial3 | concerning | filters no response trials, which manual does not |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?



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

## Q 2-b. How is the `neural` data processed?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | bin width is 10 ms instead of 5 ms,  manual interprets params.smooth to be in ms, while agent interprets this as bins |
| claude-code / trial2 | concerning | bin width is 10 ms instead of 5 ms,  manual interprets params.smooth to be in ms, while agent interprets this as bins |
| claude-code / trial3 | concerning | 10 ms bin width instead of 5 ms,  manual interprets params.smooth to be in ms, while agent interprets this as bins |
| codex / trial1 | concerning | manual interprets params.smooth to be in ms, while agent interprets this as bins |
| codex / trial2 | concerning | manual interprets params.smooth to be in ms, while agent interprets this as bins |
| codex / trial3 | concerning | manual interprets params.smooth to be in ms, while agent interprets this as bins |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | concerning | drops cells with quality '' or nan, while manual does not |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | uses 10 ms bin instead of 5 ms |
| claude-code / trial2 | concerning | uses 10 ms bin instead of 5 ms |
| claude-code / trial3 | concerning | uses 10 ms bin instead of 5 ms |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?



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
| claude-code / trial2 | incorrect | L and R are the instructed direction, but is interpreted as the choice |
| claude-code / trial3 | incorrect | L and R are the instructed direction, but is interpreted as the choice |
| codex / trial1 | incorrect | L and R are the instructed direction, but is interpreted as the choice |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | incorrect | L and R are the instructed direction, but is interpreted as the choice |

**Overall comment:** _(no overall comment)_

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | i |
| claude-code / trial2 | incorrect | L and R are the instructed direction, but is interpreted as the choice |
| claude-code / trial3 | incorrect | L and R are the instructed direction, but is interpreted as the choice |
| codex / trial1 | incorrect | L and R are the instructed direction, but is interpreted as the choice |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | incorrect | L and R are the instructed direction, but is interpreted as the choice |

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
| claude-code / trial1 | ok | only includes hit  \| miss trials, so it is ok that this only uses hit |
| claude-code / trial2 | incorrect | combines miss and ignore |
| claude-code / trial3 | incorrect | combines miss and ignore |
| codex / trial1 | incorrect | combines miss and ignore |
| codex / trial2 | ok | only uses hit \| miss trial, so ok to only use hit here |
| codex / trial3 | incorrect | combines miss and ignore |

**Overall comment:** _(no overall comment)_

---

## Q 6-b. What processing is involved in computing `output` *outcome*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | incorrect | does not account for ignore outcome |
| claude-code / trial2 | incorrect | does not account for ignore outcome |
| claude-code / trial3 | incorrect | does not account for ignore outcome |
| codex / trial1 | incorrect | does not account for ignore outcome |
| codex / trial2 | incorrect | does not account for ignore outcome |
| codex / trial3 | incorrect | does not account for ignore outcome |

**Overall comment:** _(no overall comment)_

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | agent only uses one view of tongue |
| claude-code / trial2 | concerning | agent only uses one view of tongue |
| claude-code / trial3 | concerning | agent only uses one view of tongue |
| codex / trial1 | concerning | agent only uses one view of tongue |
| codex / trial2 | concerning | agent only uses one view of tongue |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | does not combine data from multiple views. does not smooth, fills nans with interpolation |
| claude-code / trial2 | concerning | does not combine data from multiple views. does not smooth, fills nans with interpolation |
| claude-code / trial3 | concerning | does not combine data from multiple views. does not smooth, fills nans with interpolation |
| codex / trial1 | concerning | does not combine data from multiple views. does not smooth, fills nans with interpolation |
| codex / trial2 | concerning | does not combine data from multiple views. does not smooth |
| codex / trial3 | concerning | does not combine data from multiple views. does not smooth, fills nans with interpolation |

**Overall comment:** _(no overall comment)_

---

## Q 7-c. How is `output` *tongue_velocity* aligned with the neural data?



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

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | averages both top and bottom paws |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | concerning | averages both top and bottom paws |
| codex / trial2 | concerning | averages both top and bottom paws |
| codex / trial3 | concerning | averages both top and bottom paws |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | smoothing sigma is much larger |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8-c. How is `output` *paw_velocity* aligned with the neural data?



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

## Q 9-c. How is `output` *motion_energy* aligned with the neural data?



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

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | does not mention  frameTimes entirely NaN, mismatched frame counts between cameras |
| claude-code / trial2 | concerning | does not mention  frameTimes entirely NaN, mismatched frame counts between cameras |
| claude-code / trial3 | concerning | does not mention  frameTimes entirely NaN, mismatched frame counts between cameras |
| codex / trial1 | concerning | does not mention  frameTimes entirely NaN, mismatched frame counts between cameras |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | concerning | does not mention  frameTimes entirely NaN, mismatched frame counts between cameras |

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
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

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
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
