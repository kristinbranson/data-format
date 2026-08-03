# Evaluation summary — zhang2025 · evaluator KB

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | manual loads all data in the database, while agent reads data list csv for zhang2025, and looks for that data in the cache |
| claude-code / trial2 | ok | manual loads all data in the database, while agent reads data list csv for zhang2025, and looks for that data in the cache |
| claude-code / trial3 | ok | manual loads all data in the database, while agent reads data list csv for zhang2025, and looks for that data in the cache |
| codex / trial1 | ok | loads from three pqt manifest files |
| codex / trial2 | ok | manual loads all data in the database, while agent reads data list csv for zhang2025, and looks for that data in the cache |
| codex / trial3 | ok | manual loads all data in the database, while agent reads data list csv for zhang2025, and looks for that data in the cache |

**Overall comment:** _(no overall comment)_

---

## Q 1-b. How are the data split into subjects?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | agent uses csv file rather than one api |
| claude-code / trial2 | ok | agent uses directory name rather than one api |
| claude-code / trial3 | ok | agent uses csv file rather than one api |
| codex / trial1 | ok | subject comes from directory structure |
| codex / trial2 | ok | agent uses csv file rather than one api |
| codex / trial3 | ok | agent uses csv file rather than one api |

**Overall comment:** _(no overall comment)_

---

## Q 1-c. How are the data split into sessions?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | from directory structure |
| claude-code / trial3 | ok | from csv file |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-d. Are the data correctly split into trials?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | from file structure |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | agent also checks feedback_times-goCue_times < MAX_TRIAL_LEN, feedback_times non-nan |
| claude-code / trial2 | ok | agent checks feedback_Times which manual does not |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | concerning | does not check covered(wheel_times, stim_on) & covered(camera_times, stim_on) |
| codex / trial2 | ok | also checks feedback_times and feedback_type |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?


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

## Q 2-b. How is the `neural` data processed?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | agent uses binning function rather than just dividing by rounding to the nearest bin, which is more efficient since bins are evenly spaced |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | incorrect | no filtering |
| claude-code / trial2 | incorrect | does not do qc filtering, subsamples data later for memory (!!) |
| claude-code / trial3 | incorrect | no filtering |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
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

**Overall comment:** _(no overall comment)_

---

## Q 3-a. What variables in the raw data is `input` *time_from_stimulus_onset* derived from?


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

## Q 3-b. What processing is involved in computing `input` *time_from_stimulus_onset*?


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

## Q 3-c. How is `input` *time_from_stimulus_onset* aligned with the neural data?


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

## Q 4-a. What variables in the raw data is `input` *trial_number_in_block* derived from?


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

## Q 4-b. What processing is involved in computing `input` *trial_number_in_block*?


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

## Q 5-a. What variables in the raw data is `output` *choice* derived from?


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

## Q 5-b. What processing is involved in computing `output` *choice*?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | incorrect | mixes up left and right |
| claude-code / trial2 | incorrect | mixes up left and right |
| claude-code / trial3 | incorrect | mixes up left and right |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 6-a. What variables in the raw data is `output` *prior_probability_left* derived from?


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

## Q 6-b. What processing is involved in computing `output` *prior_probability_left*?


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

## Q 7-a. What variables in the raw data is `output` *wheel_speed* derived from?


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

## Q 7-b. What processing is involved in computing `output` *wheel_speed*?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | does not low pass filter |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 7-d. How is `output` *wheel_speed* aligned with the neural data?


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

## Q 8-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?


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

## Q 8-b. What processing is involved in computing `output` *whisker_motion_energy*?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | crops timestamps from the end rather than the start |
| claude-code / trial2 | concerning | truncated mismatches by cropping from the end rather than the start |
| claude-code / trial3 | concerning | drops sessions where lengths of whisker motion energy data and timestamps mismatch |
| codex / trial1 | ok | uses brainbox's interpolate_position which hopefully does this right |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8-d. How is `output` *whisker_motion_energy* aligned with the neural data?


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

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?


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

## Q 10-a. What are the most time-consuming steps of the code?


| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | spike binning can be avoided by just rounding to the nearest 20ms |
| claude-code / trial2 | concerning | spike binning can be avoided by just rounding to the nearest 20ms |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | concerning | spike binning can be avoided by just rounding to the nearest 20ms |
| codex / trial2 | concerning | spike binning can be avoided by just rounding to the nearest 20ms |
| codex / trial3 | concerning | spike binning can be avoided by just rounding to the nearest 20ms |

**Overall comment:** _(no overall comment)_

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?


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

## Q 10-c. What processing does the code repeat multiple times?


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

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?


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

## Q 10-e. How is memory usage optimized?


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
