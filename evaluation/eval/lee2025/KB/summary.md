# Evaluation summary — lee2025 · evaluator KB

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | agent loads the extension-less data files with joblib.load, while manual uses the mat file. agent hardcodes animal names |
| claude-code / trial2 | ok | agent loads the extension-less data files with joblib.load, while manual uses the mat file. hardcoded animal names |
| claude-code / trial3 | ok | agent loads the extension-less data files with joblib.load, while manual uses the mat file. hardcodes animal names |
| codex / trial1 | ok | agent loads the extension-less data files with joblib.load, while manual uses the mat file |
| codex / trial2 | ok | agent loads the extension-less data files with joblib.load, while manual uses the mat file |
| codex / trial3 | ok | agent loads the extension-less data files with joblib.load, while manual uses the mat file |

**Overall comment:** _(no overall comment)_

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

**Overall comment:** _(no overall comment)_

---

## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | manual truncates after full 60 second trials, while agent rounds |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | manual truncates after full 60 second trials, while agent includes some shorter trials, forces 40 minute window |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

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
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | agent does gaussian smoothing followed by average pooling, which is weird. unclear from snippet if it filters cells |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | agent downsamples to 10 Hz, manual keeps at 30 Hz. neural activity is binary at 30 Hz, so arguably 10 Hz might be better |
| codex / trial2 | concerning | i think dropping frames and then smoothing is problematic. also it does gaussian filtering and pooling which is weird |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | agent uses first time point, manual checks all timepoints, spotchecked that these are the same |
| claude-code / trial2 | ok | agent uses first time point, manual checks all timepoints, spotchecked that these are the same |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | agent uses first time point, manual checks all timepoints, spotchecked that these are the same |
| codex / trial2 | ok | agent uses a threshold of 5, manual uses any, spotchecked that these are the same |
| codex / trial3 | ok | agent uses first time point, manual checks all timepoints, spotchecked that these are the same |

**Overall comment:** _(no overall comment)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | agent downsamples to 10 Hz while manual keeps 30 Hz |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | agent downsamples to 10 Hz while manual keeps at 30 Hz |
| codex / trial2 | ok | agent downsamples to 10 Hz while manual keeps 30 Hz |
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

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | agent uses env name and has a lookup table of block structure for each env name |
| claude-code / trial2 | ok | agent uses env name and has a lookup table of block structure for each env name |
| claude-code / trial3 | ok | agent uses env name and has a lookup table of block structure for each env name |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | uses 1 for accessible, 0 for blocked |
| claude-code / trial2 | ok | uses 1 for accessible, 0 for blocked |
| claude-code / trial3 | ok | uses 1 for accessible, 0 for blocked |
| codex / trial1 | ok | uses 1 for accessible, 0 for blocked |
| codex / trial2 | ok | uses 1 for accessible, 0 for blocked |
| codex / trial3 | ok | uses 1 for accessible, 0 for blocked |

**Overall comment:** _(no overall comment)_

---

## Q 3-c. How is `input` *Blocked positions* aligned with the neural data?

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

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

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

## Q 4-b. What processing is involved in computing `output` *Position*?

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

## Q 4-c. How is `output` *Position* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

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

## Q 8-a. What are the most time-consuming steps of the code?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

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

## Q 8-c. What processing does the code repeat multiple times?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | concerning | loading files is slow, loading twice is unnecessary |

**Overall comment:** _(no overall comment)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

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

