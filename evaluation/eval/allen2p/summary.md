# Evaluation summary — allen2p

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | ok | _(no note)_ |
| claude-code / trial2 | ok | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** The solution from every agent read the data directory directly, using h5py to read the nwb file. The agent has access to both the notebook example code and data directory, but didn't follow the notebook to use the AllenSDK interface.

---

## Q 1-b. How are the data split into subjects?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | rely on assumptions, more likely to result in error |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** Used correct information

---
## Q 1-c. How are the data split into sessions?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | incorrect | did not combine "experiment id" based on "session id" |
| claude-code / trial2 | incorrect | _(no note)_ |
| claude-code / trial3 | incorrect | _(no note)_ |
| codex / trial1 | incorrect | _(no note)_ |
| codex / trial2 | incorrect | _(no note)_ |
| codex / trial3 | incorrect | _(no note)_ |

**Overall comment:** The Allen Dataset has a unusual setup where each experiment, identified by "ophys_session_id", is split into different "ophys_experiment_id" for different image plane in the same session. This seems to have thrown off all the agents, all of them did not recombine the data based on the session id. These are explicitly shown  in the tutorial code, which the agents has been instructed to read.

---
## Q 1-d. Are the data correctly split into trials?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | concerning | did not use start_time and stop_time explicitly, but using side information that could be inconsistent |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
## Q 1-e. How are trials filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** agent all followed the main instruction, some introduced additional filtering that are reasonable

---
## Q 2-a. What variables in the raw data is the final `neural` data derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** agent seems to prefer the event data (which is technically ok), but the code/paper example use dff instead

---
## Q 2-b. How is the `neural` data processed?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | averge all the neural data within the same stim presentation bin (750 ms), very wrong choice... |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | concerning | 100 ms time bin is a strange choice |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** only one agent did the "really" correct solution - since the experiment timestamps are aligned, there are no need to do any resampling. two agents did very wrong choice for time bin etc.

---
## Q 2-c. How is the `neural` data filtered based on quality controls?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** some agent used additional roi filter based on the valid_roi flag

---
## Q 2-d. How is the `neural` data temporally binned/resampled?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | 750 ms is completely wrong |
| claude-code / trial3 | ok | _(no note)_ |
| codex / trial1 | concerning | 100 ms time bin is a bad choice |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** the data is ~11 Hz, so some agents resampled to 30 ms time bin is ok, but in principle no resample is needed. two agents did some really bad choice though...

---
## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

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
## Q 3-a. What variables in the raw data is `output` *Running speed* derived from?

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
## Q 3-b. What processing is involved in computing `output` *Running speed*?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | same binning error cascade to all the variables |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
## Q 3-c. How is `output` *Running speed* aligned with the neural data?

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
## Q 4-a. What variables in the raw data is `output` *Pupil diameter* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | concerning | used area instead of diameter |
| codex / trial1 | concerning | did now use pupil_width directly but try to compute from area |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** agent really like to compute pupil size from area...

---
## Q 4-b. What processing is involved in computing `output` *Pupil diameter*?

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
## Q 4-c. How is `output` *Pupil diameter* aligned with the neural data?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | incorrect | same error due to time bin definition |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
## Q 5-a. What variables in the raw data is `output` *Image name* derived from?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | ok | _(no note)_ |
| codex / trial2 | ok | _(no note)_ |
| codex / trial3 | ok | _(no note)_ |

**Overall comment:** codex agent goes deep into the data structure to try to find the image id info instead of using the data table

---

## Q 5-b. What processing is involved in computing `output` *Image name*?

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
## Q 5-c. How is `output` *Image name* aligned with the neural data?

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
## Q 6-a. What variables in the raw data is `output` *Image change* derived from?

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
## Q 6-b. What processing is involved in computing `output` *Image change*?

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
## Q 6-c. How is `output` *Image change* aligned with the neural data?

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
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** _(no overall comment)_

---
## Q 7-c. How is `output` *Trial outcome* aligned with the neural data?

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
## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | match | _(no note)_ |
| claude-code / trial2 | match | _(no note)_ |
| claude-code / trial3 | match | _(no note)_ |
| codex / trial1 | match | _(no note)_ |
| codex / trial2 | match | _(no note)_ |
| codex / trial3 | match | _(no note)_ |

**Overall comment:** some script are missing explict error handling

---
## Q 9-a. What are the most time-consuming steps of the code?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | concerning | _(no note)_ |
| codex / trial1 | concerning | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | concerning | _(no note)_ |

**Overall comment:** _(no overall comment)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

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
## Q 9-c. What processing does the code repeat multiple times?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | concerning | _(no note)_ |
| claude-code / trial2 | concerning | _(no note)_ |
| claude-code / trial3 | incorrect | _(no note)_ |
| codex / trial1 | concerning | _(no note)_ |
| codex / trial2 | concerning | _(no note)_ |
| codex / trial3 | concerning | _(no note)_ |

**Overall comment:** 5/6 did a two pass approch which is inefficient, 1/6 did three pass which is just wrong...

---
## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

| Agent / trial | Rating | Note |
|---|---|---|
| claude-code / trial1 | missing | _(no note)_ |
| claude-code / trial2 | missing | _(no note)_ |
| claude-code / trial3 | missing | _(no note)_ |
| codex / trial1 | missing | _(no note)_ |
| codex / trial2 | missing | _(no note)_ |
| codex / trial3 | missing | _(no note)_ |

**Overall comment:** N/A

---
## Q 9-e. How is memory usage optimized?

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
