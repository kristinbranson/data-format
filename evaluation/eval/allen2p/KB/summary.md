# Evaluation summary — allen2p · evaluator KB

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | incorrect | agent filters to passive experiments, not VisualBehavior experiments |
| claude-code / trial2 | incorrect | manual code uses the VisualBehavior project code, while the agent uses experiments for which passive is False |
| claude-code / trial3 | incorrect | manual uses all VisualBehavior project code experiments, while this looks for specific session_types that correspond to active sessions, these don't seem to match |
| codex / trial1 | incorrect | agent does no filtering to project code VisualBehavior |
| codex / trial2 | incorrect | manual code uses the VisualBehavior project code, while the agent uses experiments for which passive is False and for which there is eye tracking. these don't seem to match |
| codex / trial3 | incorrect | manual code uses the VisualBehavior project code, while the agent uses experiments for which passive is False. |

**Overall comment:** it would be good to understand why so many agents wanted to use not passive experiments even though the instructions clearly said "Collect and convert data under the "Visual Behavior" task."

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
| claude-code / trial1 | incorrect | the agent uses ophys_experiment_id instead of the correct ophys_session_id |
| claude-code / trial2 | incorrect | the code snippet doesn't include information about how sessions is created, but the text says that each experiment_id is treated as a session |
| claude-code / trial3 | incorrect | the code snippet doesn't include information about how sessions is created, but the text says that each experiment_id is treated as a session |
| codex / trial1 | incorrect | the code snippet doesn't include information about how sessions is created, but the text says that each experiment_id is treated as a session |
| codex / trial2 | incorrect | the code snippet doesn't include information about how sessions is created, but the text says that each experiment_id is treated as a session |
| codex / trial3 | incorrect | each experiment is treated as a separate session |

**Overall comment:** the use of the word experiment seems to really confuse agents

---

## Q 1-d. Are the data correctly split into trials?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | not comparing filtering as that is in the next question |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | uses go \| catch which is probably the same as change_time.nonna |
| claude-code / trial2 | ok | uses go \| catch which is probably the same as change_time.nonna |
| claude-code / trial3 | ok | uses go \| catch which is probably the same as change_time.nonna |
| codex / trial1 | concerning | does not include check for change_time or go \| change |
| codex / trial2 | ok | uses go \| catch which is probably the same as change_time.nonna |
| codex / trial3 | ok | uses go \| catch which is probably the same as change_time.nonna |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | ok | uses spike events rather than dff |
| codex / trial1 | ok | uses spike events rather than dff |
| codex / trial2 | ok | uses spike events rather than dff |
| codex / trial3 | ok | uses spike events rather than dff |

**Overall comment:** _(no overall comment)_

---

## Q 2-b. How is the `neural` data processed?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | binning is weird, but that is a different question |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** there were things that looked weird here, but they are either because of binning or confusion over plane vs experiment

---

## Q 2-c. How is the `neural` data filtered based on quality controls?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | i think this could be better, since it is also checking for cells to be valid, but i think all neurons are valid based on data i've loaded in |
| claude-code / trial3 | match | i think this could be better, since it is also checking for cells to be valid, but i think all neurons are valid based on data i've loaded in |
| codex / trial1 | match | i think this could be better, since it is also checking for cells to be valid, but i think all neurons are valid based on data i've loaded in |
| codex / trial2 | match | i think this could be better, since it is also checking for cells to be valid, but i think all neurons are valid based on data i've loaded in |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | sets time bin to be way too big, 750 ms is too long |
| claude-code / trial3 | ok | agent uses 30 hz, manual uses native 11 hz for dff data. agent is using events, and 30 hz is the rate of some of the behavior data, so that seems ok |
| codex / trial1 | concerning | it looks to me like this is not interpolating, but rounding, which seems like it could cause problems |
| codex / trial2 | ok | agent uses 30 hz, manual uses native 11 hz for dff data. agent is using events, and 30 hz is the rate of some of the behavior data, so that seems ok |
| codex / trial3 | ok | agent uses 30 hz, manual uses native 11 hz for dff data. agent is using events, and 30 hz is the rate of some of the behavior data, so that seems ok |

**Overall comment:** _(no overall comment)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 3-a. What variables in the raw data is `output` *Image identity* derived from?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | uses stimulus presentations table instead of initial_image_name change_image_name |
| claude-code / trial2 | ok | uses stimulus presentations table instead of initial_image_name change_image_name |
| claude-code / trial3 | ok | uses stimulus presentations table instead of initial_image_name change_image_name |
| codex / trial1 | ok | uses stimulus presentations table instead of initial_image_name change_image_name |
| codex / trial2 | ok | uses stimulus presentations table instead of initial_image_name change_image_name |
| codex / trial3 | ok | uses stimulus presentations table instead of initial_image_name change_image_name |

**Overall comment:** _(no overall comment)_

---

## Q 3-b. What processing is involved in computing `output` *Image identity*?



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

## Q 3-c. How is `output` *Image identity* aligned with the neural data?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | manual uses trial table initial_image_name change_image_name while agent uses image time series |
| claude-code / trial2 | ok | manual uses trial table initial_image_name change_image_name while agent uses image time series |
| claude-code / trial3 | ok | manual uses trial table initial_image_name change_image_name while agent uses image time series |
| codex / trial1 | ok | manual uses trial table initial_image_name change_image_name while agent uses image time series |
| codex / trial2 | ok | manual uses trial table initial_image_name change_image_name while agent uses image time series |
| codex / trial3 | ok | manual uses trial table initial_image_name change_image_name while agent uses image time series |

**Overall comment:** _(no overall comment)_

---

## Q 4-a. What variables in the raw data is `output` *Image change* derived from?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 for one frame |
| claude-code / trial2 | concerning | manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 for one frame |
| claude-code / trial3 | ok | manual uses trial table, but agent uses stimulus presentation intervals |
| codex / trial1 | concerning | manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 for one frame |
| codex / trial2 | ok | manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 250 ms |
| codex / trial3 | ok | manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 for 250ms |

**Overall comment:** _(no overall comment)_

---

## Q 4-b. What processing is involved in computing `output` *Image change*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 4-c. How is `output` *Image change* aligned with the neural data?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 5-a. What variables in the raw data is `output` *Running speed* derived from?



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

## Q 5-b. What processing is involved in computing `output` *Running speed*?



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

## Q 5-c. How is `output` *Running speed* aligned with the neural data?



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

## Q 6-a. What variables in the raw data is `output` *Pupil diameter* derived from?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | uses pupil area to derive diameter instead of width |
| claude-code / trial2 | ok | uses pupil area to derive diameter instead of width |
| claude-code / trial3 | ok | uses pupil area to derive diameter instead of width |
| codex / trial1 | ok | uses pupil area to derive diameter instead of width |
| codex / trial2 | concerning | uses max of width and height, but doesn't filter for likely blinking |
| codex / trial3 | ok | uses max of width and height instead of width |

**Overall comment:** _(no overall comment)_

---

## Q 6-b. What processing is involved in computing `output` *Pupil diameter*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 6-c. How is `output` *Pupil diameter* aligned with the neural data?



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

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?



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

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?



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

## Q 9-a. What are the most time-consuming steps of the code?



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

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | concerning | multiple passes over nwb files sounds problematic |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-c. What processing does the code repeat multiple times?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | not ideal to open each nwb file twice |
| claude-code / trial2 | concerning | not ideal to load and parse multiple times |
| claude-code / trial3 | concerning | not ideal to open each nwb file 3 times |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | concerning | not ideal to load nwb files twice |
| codex / trial3 | concerning | not ideal to open each nwb file twice |

**Overall comment:** _(no overall comment)_

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?



| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-e. How is memory usage optimized?



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
