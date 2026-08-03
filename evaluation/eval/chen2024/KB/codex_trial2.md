# map — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/map/codex/2026-03-23__08-25-17_trial2/verifier/snapshot/`

Outputs identified (K=4): choice, outcome, early_lick, tongue_y_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Loads NWB directly with `h5py` instead of PyNWB for speed and lower overhead." (CONVERSION_NOTES.md:244)
> "Data loading: `convert_data.py` directly reads NWB `units`, `intervals/trials`, `BehavioralEvents`, and `BehavioralTimeSeries`, corresponding to `process_one_sess` and `load_session` in the reference code." (CONVERSION_NOTES.md:368)

**Code** (convert_data.py:186-192, 621-622, 632-642):
```python
def load_candidate_files() -> list[Path]:
    return sorted(DATA_DIR.glob("sub-*/*.nwb"))

# in main():
all_files = load_candidate_files()
session_files, excluded_sessions = select_files(all_files, sample_mode=sample_mode)
...
for i, path in enumerate(session_files, start=1):
    ...
    result = process_session(path, make_plot=make_plot)
```

**What this does:** Globs `/app/data/sub-*/*.nwb` to enumerate all NWB files, filters out sessions with zero classifier-good units, then iterates session-by-session calling `process_session(path)` which opens each file via `h5py.File` and reads units, trials, events, and tracking data.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`subject.subject_id` -> `subjects`, `subject_idx`. Store unique subject IDs and per-session indices" (CONVERSION_NOTES.md:211)

**Code** (convert_data.py:202-205, 524-528):
```python
subject_id = str(f["general"]["subject"]["subject_id"][()])
if subject_id.startswith("b'"):
    subject_id = subject_id[2:-1]
subject_id = f"sub-{subject_id}"
...
for result in results:
    if result.subject_id not in subject_to_idx:
        subject_to_idx[result.subject_id] = len(subjects)
        subjects.append(result.subject_id)
    subject_idx.append(subject_to_idx[result.subject_id])
```

**What this does:** Reads `general/subject/subject_id` from each NWB file to get the subject for each session. In `build_dataset`, accumulates a unique sorted-order list of subjects and assigns each session a `subject_idx`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Base session set: Use the 173 NWB sessions with at least one classifier-labeled good unit." (CONVERSION_NOTES.md:214)
> "Exclude the single session `sub-440958_ses-20190216T162508_behavior+ecephys+ogen.nwb`, which has `classification == nan` for all 1,852 units" (CONVERSION_NOTES.md:186)

**Code** (convert_data.py:206-208, 601-613):
```python
session_id = path.stem.replace("_behavior+ecephys+ogen", "").replace(
    "_behavior+ecephys", ""
)
...
def select_files(all_files: list[Path], sample_mode: bool) -> tuple[list[Path], list[str]]:
    selected: list[Path] = []
    excluded: list[str] = []
    for path in all_files:
        with h5py.File(path, "r") as f:
            classification = decode_strings(f["units"]["classification"])
            if np.sum(classification == "good") == 0:
                excluded.append(path.name)
                continue
        selected.append(path)
```

**What this does:** Each NWB file = one session; session_id is derived from the filename stem with task-suffixes stripped. Sessions with zero classifier-good units are excluded (yields 173 of 174).

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Aligns each trial to go cue by matching event timestamps into the trial interval." (CONVERSION_NOTES.md:247)

**Code** (convert_data.py:222-227, 248-256):
```python
trials = f["intervals"]["trials"]
trial_start = trials["start_time"][:].astype(np.float64)
trial_stop = trials["stop_time"][:].astype(np.float64)
trial_instruction = decode_strings(trials["trial_instruction"])
trial_outcome = decode_strings(trials["outcome"])
trial_early = decode_strings(trials["early_lick"])
...
for trial_idx in range(len(trial_start)):
    start = trial_start[trial_idx]
    stop = trial_stop[trial_idx]
    go_candidates = interval_values(go_times, start, stop)
    if len(go_candidates) == 0:
        raise ValueError(f"{path.name}: no go cue found for trial {trial_idx}")
    go_time = float(go_candidates[-1])
```

**What this does:** Iterates rows of NWB `intervals/trials` table (one row = one trial), using each trial's `start_time`/`stop_time` to slice events within the trial interval and to anchor the go-cue alignment.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trials are excluded unless the full `[-2.5, +1.5] s` window lies inside a good-unit observation interval; this is necessary to avoid invalid all-zero neural windows." (CONVERSION_NOTES.md:354)
> "early lick, outcome, and photostimulation are decoder targets/inputs" (CONVERSION_NOTES.md:56) — i.e., not used to drop trials.

**Code** (convert_data.py:255-263, 344-353):
```python
window_start = go_time + WINDOW_START_S
window_end = go_time + WINDOW_END_S
covered = np.any(
    (window_start >= session_obs_intervals[:, 0])
    & (window_end <= session_obs_intervals[:, 1])
)
if not covered:
    n_trials_dropped_outside_obs += 1
    continue
...
nonzero_trial_mask = np.any(neural_tensor != 0, axis=(1, 2))
n_trials_dropped_all_zero = int((~nonzero_trial_mask).sum())
if n_trials_dropped_all_zero:
    neural_tensor = neural_tensor[nonzero_trial_mask]
```

**What this does:** Drops trials whose full [-2.5, +1.5]s go-aligned window is not entirely inside a good-unit observation interval, plus a final pass dropping any trial whose neural tensor is all zeros. Early-lick, ignore, photostim, etc. are kept and exposed as decoder targets/inputs.

**Rating:** concerning

**Note:** does not exclude free_water

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`units.spike_times` for units with `classification == 'good'` -> `neural`" (CONVERSION_NOTES.md:201)

**Code** (convert_data.py:193-220):
```python
classification = decode_strings(f["units"]["classification"])
good_unit_mask = classification == "good"
...
spike_times_flat = f["units"]["spike_times"][:]
spike_times_index = f["units"]["spike_times_index"][:]
spike_times_ragged = split_ragged(spike_times_flat, spike_times_index)
good_unit_indices = np.flatnonzero(good_unit_mask)
good_spike_times = [np.asarray(spike_times_ragged[i], dtype=np.float64) for i in good_unit_indices]
obs_intervals = f["units"]["obs_intervals"][:].astype(np.float64)
obs_intervals_index = f["units"]["obs_intervals_index"][:]
```

**What this does:** Neural data is built from NWB `units.spike_times` (per-unit ragged spike-time arrays), filtered using `units.classification == "good"`. Also reads `units.obs_intervals` to gate trial inclusion and `units.anno_name` for region labels.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "For each session/trial, bin absolute spike times into go-aligned `[-2.5, 1.5)` windows using 50 ms bins; convert counts to firing rates (`count / 0.05`)" (CONVERSION_NOTES.md:201)
> "Stores neural firing rates as `float16` to keep the full dataset size manageable." (CONVERSION_NOTES.md:251)

**Code** (convert_data.py:325-342):
```python
trial_edge_matrix = np.empty((n_trials, N_BINS + 1), dtype=np.float64)
...
for keep_idx, rec in enumerate(trial_records):
    ...
    trial_edge_matrix[keep_idx] = rec["go_time"] + BIN_EDGES_REL
...
neural_tensor = np.empty((n_trials, n_good_units, N_BINS), dtype=np.float16)
for unit_idx, spikes in enumerate(good_spike_times):
    edge_idx = np.searchsorted(spikes, trial_edge_matrix, side="left")
    counts = np.diff(edge_idx, axis=1)
    neural_tensor[:, unit_idx, :] = (counts / BIN_WIDTH_S).astype(np.float16)
```

**What this does:** For each unit, builds an `(n_trials, 81)` matrix of absolute bin edges (go_time + relative edges), uses `np.searchsorted` to count spikes per bin across all trials at once, divides counts by 0.05 s to obtain firing rates in Hz, stored as `float16`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use `units.classification == 'good'` rather than `units.unit_quality == 'good'`. This is the only local field consistent with the classifier-based QC described in the white paper" (CONVERSION_NOTES.md:215)

**Code** (convert_data.py:193-200):
```python
classification = decode_strings(f["units"]["classification"])
good_unit_mask = classification == "good"
n_good_units = int(good_unit_mask.sum())
if n_good_units == 0:
    return None

anno_name = decode_strings(f["units"]["anno_name"])
brain_region_labels = build_region_labels(anno_name, good_unit_mask)
```

**What this does:** Keeps only units whose `classification` field equals `"good"` (the classifier-based QC label). Sessions with zero good units are dropped entirely.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reference code uses 40 ms width / 3.4 ms stride, while this conversion intentionally uses 50 ms non-overlapping bins to satisfy the decoder task" (CONVERSION_NOTES.md:371)

**Code** (convert_data.py:27-32, 339-342):
```python
BIN_WIDTH_S = 0.05
WINDOW_START_S = -2.5
WINDOW_END_S = 1.5
BIN_EDGES_REL = np.arange(WINDOW_START_S, WINDOW_END_S + 1e-9, BIN_WIDTH_S, dtype=np.float64)
BIN_CENTERS_REL = BIN_EDGES_REL[:-1] + BIN_WIDTH_S / 2.0
N_BINS = len(BIN_CENTERS_REL)
...
edge_idx = np.searchsorted(spikes, trial_edge_matrix, side="left")
counts = np.diff(edge_idx, axis=1)
neural_tensor[:, unit_idx, :] = (counts / BIN_WIDTH_S).astype(np.float16)
```

**What this does:** Uses fixed 50 ms non-overlapping bins from -2.5 s to +1.5 s relative to go cue (80 bins). Spike counts per bin are computed by `np.searchsorted` on edges, then divided by 0.05 s to give Hz.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Aligns each trial to go cue by matching event timestamps into the trial interval." (CONVERSION_NOTES.md:247)
> `metadata["temporal_alignment_event"] = "Go cue onset"` (convert_data.py:553)

**Code** (convert_data.py:248-254, 333):
```python
for trial_idx in range(len(trial_start)):
    start = trial_start[trial_idx]
    stop = trial_stop[trial_idx]
    go_candidates = interval_values(go_times, start, stop)
    if len(go_candidates) == 0:
        raise ValueError(f"{path.name}: no go cue found for trial {trial_idx}")
    go_time = float(go_candidates[-1])
...
trial_edge_matrix[keep_idx] = rec["go_time"] + BIN_EDGES_REL
```

**What this does:** Per trial, finds the go-cue timestamp by intersecting `go_start_times` events with `[trial_start, trial_stop]` (last candidate used if multiple). Bin edges are constructed as `go_time + BIN_EDGES_REL`, placing time zero at go-cue onset.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *time_from_tone_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`acquisition/BehavioralEvents/sample_start_times.timestamps` -> `input[0]` (`time_from_tone_onset_s`). For each trial, use the **last** sample-start event before the go cue as the effective tone/sample onset; store `(bin_center_time - sample_onset_time)` in seconds for every bin" (CONVERSION_NOTES.md:203)
> "**Tone onset handling**: For early-lick replay trials, define tone onset as the last sample-start event before go." (CONVERSION_NOTES.md:217)

**Code** (convert_data.py:232-234, 265-273):
```python
events = f["acquisition"]["BehavioralEvents"]
go_times = events["go_start_times"]["timestamps"][:].astype(np.float64)
sample_start_times = events["sample_start_times"]["timestamps"][:].astype(np.float64)
...
sample_candidates = interval_values(sample_start_times, start, go_time)
if len(sample_candidates) == 0:
    sample_onset = go_time - 1.85
    n_missing_sample_onset_fallback += 1
else:
    sample_onset = float(sample_candidates[-1])

bin_centers_abs = go_time + BIN_CENTERS_REL
time_from_tone = (bin_centers_abs - sample_onset).astype(np.float32)
```

**What this does:** Derived from `acquisition/BehavioralEvents/sample_start_times.timestamps`, bracketed by `intervals/trials.start_time` and the per-trial go-cue timestamp from `go_start_times`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_tone_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "store `(bin_center_time - sample_onset_time)` in seconds for every bin" (CONVERSION_NOTES.md:203)
> "Early-lick trials can contain multiple sample-start events; the last one is the final replay that leads to the observed go cue." (CONVERSION_NOTES.md:203)
> "`n_missing_sample_onset_fallback = 0`, so no trial needed the `go - 1.85 s` default." (CONVERSION_NOTES.md:382)
> `metadata["tone_onset_definition"] = "last sample_start event before go cue within the trial"` (convert_data.py:563)

**Code** (convert_data.py:265-273, 326, 334):
```python
sample_candidates = interval_values(sample_start_times, start, go_time)
if len(sample_candidates) == 0:
    sample_onset = go_time - 1.85
    n_missing_sample_onset_fallback += 1
else:
    sample_onset = float(sample_candidates[-1])

bin_centers_abs = go_time + BIN_CENTERS_REL
time_from_tone = (bin_centers_abs - sample_onset).astype(np.float32)
...
input_tensor = np.empty((n_trials, 2, N_BINS), dtype=np.float32)
input_tensor[keep_idx, 0, :] = rec["time_from_tone"]
```

**What this does:** Selects the last `sample_start` event falling in `[trial_start, go_time]` as tone onset (falling back to `go - 1.85 s` if none), then computes elapsed seconds from that onset to each bin center, giving a continuous float32 ramp stored as `input[0]`.

**Rating:** incorrect

**Note:** uses sample_start_time instead of tone_onset_times

---

## Q 3-c. How is `input` *time_from_tone_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "code aligns task epochs to go cue" (CONVERSION_NOTES.md:203)
> "Spot-checked session indices `0`, `86`, and `172`: all have trial tensors shaped `(n_neurons, 80)`, inputs `(2, 80)`, and outputs `(4, 80)`." (CONVERSION_NOTES.md:352)
> "`time_from_tone_onset_s` range | [-1.5, 9.7] | Plausible" (CONVERSION_NOTES.md:343)

**Code** (convert_data.py:272-273, 326-335, 344-349):
```python
bin_centers_abs = go_time + BIN_CENTERS_REL
time_from_tone = (bin_centers_abs - sample_onset).astype(np.float32)
...
input_tensor = np.empty((n_trials, 2, N_BINS), dtype=np.float32)
for keep_idx, rec in enumerate(trial_records):
    trial_edge_matrix[keep_idx] = rec["go_time"] + BIN_EDGES_REL
    input_tensor[keep_idx, 0, :] = rec["time_from_tone"]
...
nonzero_trial_mask = np.any(neural_tensor != 0, axis=(1, 2))
if n_trials_dropped_all_zero:
    neural_tensor = neural_tensor[nonzero_trial_mask]
    input_tensor = input_tensor[nonzero_trial_mask]
```

**What this does:** Evaluated at the same 80 go-aligned bin centers (`go_time + BIN_CENTERS_REL`) used to build the neural bin edges, so `input[0]` has shape `(80,)` per trial matching the neural time axis; the same trial mask is applied to both tensors.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *photostim* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials.photostim_onset`, `trials.photostim_duration`, `trials.start_time` -> `input[1]` (`photostim_on`)" (CONVERSION_NOTES.md:204)
> "Trials with `photostim_power == N/A` are all zeros." (CONVERSION_NOTES.md:204)
> "Trials with non-`N/A` photostim power: 18,588 / 94,990 (`19.57%`)." (CONVERSION_NOTES.md:97)

**Code** (convert_data.py:223, 228-230, 276-281):
```python
trial_start = trials["start_time"][:].astype(np.float64)
...
trial_photostim_onset = decode_strings(trials["photostim_onset"])
trial_photostim_duration = decode_strings(trials["photostim_duration"])
trial_photostim_power = decode_strings(trials["photostim_power"])
...
stim_onset = parse_optional_float(trial_photostim_onset[trial_idx])
stim_dur = parse_optional_float(trial_photostim_duration[trial_idx])
stim_power = parse_optional_float(trial_photostim_power[trial_idx])
if stim_power is not None and stim_onset is not None and stim_dur is not None:
    stim_start_abs = start + stim_onset
    stim_stop_abs = stim_start_abs + stim_dur
```

**What this does:** Derived from the `intervals/trials` columns `photostim_onset`, `photostim_duration`, and `photostim_power` (as gate), combined with `trials.start_time` to convert trial-relative stim times to absolute times. The `BehavioralEvents/photostim_start_times` event stream is noted in the notes (CONVERSION_NOTES.md:71) but not read by the code.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *photostim*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Convert trial-relative onset/duration to absolute time, then to go-aligned binary series over bins" (CONVERSION_NOTES.md:204)
> "`photostim_on` range | [0.0, 1.0]" (CONVERSION_NOTES.md:279)
> `metadata["photostim_definition"] = "binary at 50 ms bin centers using trial-relative photostim onset/duration"` (convert_data.py:564)

**Code** (convert_data.py:83-86, 275-284, 335):
```python
def parse_optional_float(value: str) -> float | None:
    if value in {"N/A", "", "nan", "None"}:
        return None
    return float(value)
...
photostim_row = np.zeros(N_BINS, dtype=np.float32)
stim_onset = parse_optional_float(trial_photostim_onset[trial_idx])
stim_dur = parse_optional_float(trial_photostim_duration[trial_idx])
stim_power = parse_optional_float(trial_photostim_power[trial_idx])
if stim_power is not None and stim_onset is not None and stim_dur is not None:
    stim_start_abs = start + stim_onset
    stim_stop_abs = stim_start_abs + stim_dur
    photostim_row = (
        (bin_centers_abs >= stim_start_abs) & (bin_centers_abs < stim_stop_abs)
    ).astype(np.float32)
...
input_tensor[keep_idx, 1, :] = rec["photostim_on"]
```

**What this does:** Parses the three photostim string fields to floats (returning `None` for `"N/A"`/`""`/`"nan"`/`"None"`); when all three are present, computes the absolute stim window `[trial_start + onset, +duration)` and marks each bin center inside it as 1.0, else leaves the row all zeros.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `input` *photostim* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "reference preprocessing shifts stimulation times relative to go cue" (CONVERSION_NOTES.md:204)
> "Both sample sessions show plausible go-aligned neural activity and photostim timing" (CONVERSION_NOTES.md:286)
> "recomputed `photostim_on` from raw trial-relative onset/duration fields. All matched the converted arrays with `np.allclose(..., atol=1e-6)`." (CONVERSION_NOTES.md:365)

**Code** (convert_data.py:272, 282-284, 335, 344-349):
```python
bin_centers_abs = go_time + BIN_CENTERS_REL
...
photostim_row = (
    (bin_centers_abs >= stim_start_abs) & (bin_centers_abs < stim_stop_abs)
).astype(np.float32)
...
input_tensor[keep_idx, 1, :] = rec["photostim_on"]
...
nonzero_trial_mask = np.any(neural_tensor != 0, axis=(1, 2))
if n_trials_dropped_all_zero:
    neural_tensor = neural_tensor[nonzero_trial_mask]
    input_tensor = input_tensor[nonzero_trial_mask]
```

**What this does:** The binary stim indicator is sampled on the same 80 go-aligned bin centers (`go_time + BIN_CENTERS_REL`) that define the neural bins, giving one value per neural time bin; the same trial mask is applied to both `neural` and `input`.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "For `hit`/`miss`, infer actual lick choice from instruction and outcome: hit -> instructed side, miss -> opposite side" (CONVERSION_NOTES.md:205)
> "If `outcome == ignore`, ... use earliest lick side anywhere in the trial if present; otherwise use instructed side" (CONVERSION_NOTES.md:206)

**Code** (convert_data.py:225-226, 235-236, 286-294):
```python
trial_instruction = decode_strings(trials["trial_instruction"])
trial_outcome = decode_strings(trials["outcome"])
...
left_lick_times = events["left_lick_times"]["timestamps"][:].astype(np.float64)
right_lick_times = events["right_lick_times"]["timestamps"][:].astype(np.float64)
...
choice_code, choice_source = infer_choice(
    instruction=trial_instruction[trial_idx],
    outcome=trial_outcome[trial_idx],
    trial_start=start,
    trial_stop=stop,
    left_lick_times=left_lick_times,
    right_lick_times=right_lick_times,
)
```

**What this does:** Choice derives from `trials.trial_instruction`, `trials.outcome`, and (only for ignore-outcome trials) the lick event streams `BehavioralEvents/left_lick_times` and `right_lick_times`.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "hit -> instructed side, miss -> opposite side" / "ignore: use earliest lick side ... else instructed side" (CONVERSION_NOTES.md:205-206)

**Code** (convert_data.py:153-176, 305-306):
```python
def infer_choice(instruction, outcome, trial_start, trial_stop,
                 left_lick_times, right_lick_times):
    if outcome == "hit":
        return CHOICE_MAP[instruction], "instruction+outcome"
    if outcome == "miss":
        opposite = "right" if instruction == "left" else "left"
        return CHOICE_MAP[opposite], "instruction+outcome"
    left_trial = interval_values(left_lick_times, trial_start, trial_stop)
    right_trial = interval_values(right_lick_times, trial_start, trial_stop)
    if len(left_trial) and len(right_trial):
        side = "left" if left_trial[0] <= right_trial[0] else "right"
        return CHOICE_MAP[side], "ignore:first_lick_in_trial"
    if len(left_trial):
        return CHOICE_MAP["left"], "ignore:first_lick_in_trial"
    if len(right_trial):
        return CHOICE_MAP["right"], "ignore:first_lick_in_trial"
    return CHOICE_MAP[instruction], "ignore:instruction_fallback"
...
output_row[0, :] = choice_code
```

**What this does:** Computes a single integer choice per trial via `infer_choice`, then broadcasts that constant value across all 80 time bins of `output[0]`.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials.outcome` -> `output[1]` (`outcome`). Map strings to integers: `ignore=0`, `miss=1`, `hit=2`" (CONVERSION_NOTES.md:207)

**Code** (convert_data.py:226, 295):
```python
trial_outcome = decode_strings(trials["outcome"])
...
outcome_code = OUTCOME_MAP[trial_outcome[trial_idx]]
```

**What this does:** Outcome is taken directly from the `intervals/trials/outcome` column of the NWB trial table.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map strings to integers: `ignore=0`, `miss=1`, `hit=2`; replicate across all time bins" (CONVERSION_NOTES.md:207)

**Code** (convert_data.py:36, 295, 307):
```python
OUTCOME_MAP = {"ignore": 0, "miss": 1, "hit": 2}
...
outcome_code = OUTCOME_MAP[trial_outcome[trial_idx]]
...
output_row[1, :] = outcome_code
```

**What this does:** Maps the outcome string to integer via `OUTCOME_MAP`, then broadcasts across all 80 bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *early_lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials.early_lick` -> `output[2]` (`early_lick`). Map `no early=0`, `early=1`" (CONVERSION_NOTES.md:208)

**Code** (convert_data.py:227, 296):
```python
trial_early = decode_strings(trials["early_lick"])
...
early_code = EARLY_MAP[trial_early[trial_idx]]
```

**What this does:** Reads the `intervals/trials/early_lick` column of the NWB trial table directly.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *early_lick*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map `no early=0`, `early=1`; replicate across all time bins" (CONVERSION_NOTES.md:208)

**Code** (convert_data.py:37, 296, 308):
```python
EARLY_MAP = {"no early": 0, "early": 1}
...
early_code = EARLY_MAP[trial_early[trial_idx]]
...
output_row[2, :] = early_code
```

**What this does:** String-to-integer mapping then broadcast across all 80 time bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-a. What variables in the raw data is `output` *tongue_y_position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`BehavioralTimeSeries/Camera0_side_TongueTracking` `(y, likelihood)` -> `output[3]` (`tongue_y_bin`)" (CONVERSION_NOTES.md:209)

**Code** (convert_data.py:238-241):
```python
tongue_group = f["acquisition"]["BehavioralTimeSeries"]["Camera0_side_TongueTracking"]
tongue_data = tongue_group["data"][:].astype(np.float64)
tongue_timestamps = tongue_group["timestamps"][:].astype(np.float64)
processed_tongue_y, tongue_info = process_tongue_trace(tongue_data, tongue_timestamps)
```

**What this does:** Derived from `acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking` — uses the y-coordinate column and likelihood column of the tracking array, plus its timestamps.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What processing is involved in computing `output` *tongue_y_position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Process continuous tongue y per session, resample to trial/bin centers, then discretize with session-level 40th and 60th percentiles into classes 0/1/2" (CONVERSION_NOTES.md:209)
> "5-sigma velocity outlier detection + interpolation; low-likelihood/occluded frames imputed to session mean tongue y." (CONVERSION_NOTES.md:209)

**Code** (convert_data.py:100-150, 298-303):
```python
def process_tongue_trace(tongue_xyzl, tongue_timestamps):
    ...
    velocity = np.linalg.norm(np.diff(xy, axis=0), axis=1) / dt
    ...
    vel_threshold = vel_mean + 5.0 * vel_std
    outlier_mask[1:] = np.isfinite(velocity) & (velocity > vel_threshold)
    low_likelihood_mask = likelihood < LIKELIHOOD_THRESHOLD
    ...
    processed_y[low_likelihood_mask] = session_mean_y
    ...
    processed_y[interp_mask] = np.interp(
        tongue_timestamps[interp_mask], tongue_timestamps[keep_mask],
        processed_y[keep_mask])
    p40, p60 = np.percentile(processed_y, [40.0, 60.0])
...
tongue_frame_idx = np.searchsorted(tongue_timestamps, bin_centers_abs, side="right") - 1
tongue_y = processed_tongue_y[tongue_frame_idx]
tongue_bin = np.zeros(N_BINS, dtype=np.int16)
tongue_bin[tongue_y >= tongue_info["p40"]] = 1
tongue_bin[tongue_y > tongue_info["p60"]] = 2
```

**What this does:** Session-level: detects velocity outliers (>5σ) and low-likelihood frames; fills low-likelihood with session mean tongue y; linearly interpolates outliers; computes session 40th/60th percentiles. Per trial: samples processed tongue y at each bin center via `searchsorted`, then discretizes into 3 classes by percentile thresholds.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-c. How is `output` *tongue_y_position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "For each 50 ms neural bin, assign tongue y from the processed continuous tongue trace at the bin center (or closest preceding frame)." (CONVERSION_NOTES.md:221)

**Code** (convert_data.py:272, 298-303, 309):
```python
bin_centers_abs = go_time + BIN_CENTERS_REL
...
tongue_frame_idx = np.searchsorted(tongue_timestamps, bin_centers_abs, side="right") - 1
tongue_frame_idx = np.clip(tongue_frame_idx, 0, len(processed_tongue_y) - 1)
tongue_y = processed_tongue_y[tongue_frame_idx]
tongue_bin = np.zeros(N_BINS, dtype=np.int16)
tongue_bin[tongue_y >= tongue_info["p40"]] = 1
tongue_bin[tongue_y > tongue_info["p60"]] = 2
...
output_row[3, :] = tongue_bin
```

**What this does:** For each of the 80 go-aligned bin centers (`go_time + BIN_CENTERS_REL`), looks up the closest preceding tracking frame via `searchsorted` and reads its discretized class, producing a per-bin time-varying class series sharing the neural bin grid.

**Rating:** match

**Note:** _(no note)_

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Exclude the single session ... which has `classification == nan` for all 1,852 units" (CONVERSION_NOTES.md:186)
> "n_missing_sample_onset_fallback = 0, so no trial needed the `go - 1.85 s` default." (CONVERSION_NOTES.md:382)
> "ignore trials use earliest lick in trial when present, otherwise instructed side as placeholder" (CONVERSION_NOTES.md:206)
> "low-likelihood/occluded frames imputed to session mean tongue y" (CONVERSION_NOTES.md:209)

**Code** (convert_data.py:83-86, 195-197, 252-253, 261-263, 265-270, 344-353):
```python
def parse_optional_float(value: str) -> float | None:
    if value in {"N/A", "", "nan", "None"}:
        return None
    return float(value)
...
if n_good_units == 0:
    return None
...
if len(go_candidates) == 0:
    raise ValueError(f"{path.name}: no go cue found for trial {trial_idx}")
...
if not covered:
    n_trials_dropped_outside_obs += 1
    continue
...
if len(sample_candidates) == 0:
    sample_onset = go_time - 1.85
    n_missing_sample_onset_fallback += 1
...
nonzero_trial_mask = np.any(neural_tensor != 0, axis=(1, 2))
```

**What this does:** Sessions with zero good units are skipped; missing photostim fields ("N/A", "", "nan", "None") are parsed as None and yield zero-photostim rows; missing sample-onset events fall back to `go - 1.85 s`; ignore-outcome trials get an inferred or fallback choice; low-likelihood/outlier tongue frames are mean-filled or interpolated; trials with incomplete observation windows or all-zero neural tensors are dropped. A missing go cue raises a hard error.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sample conversion 0.70 s per session, 2.01 min projected for 173 sessions" (CONVERSION_NOTES.md:299)
> "Reduced per-session neural binning from projected minute-scale nested loops to sub-second runtime" (CONVERSION_NOTES.md:295)

**Code** (convert_data.py:210-216, 338-342):
```python
spike_times_flat = f["units"]["spike_times"][:]
spike_times_index = f["units"]["spike_times_index"][:]
spike_times_ragged = split_ragged(spike_times_flat, spike_times_index)
good_unit_indices = np.flatnonzero(good_unit_mask)
good_spike_times = [np.asarray(spike_times_ragged[i], dtype=np.float64) for i in good_unit_indices]
...
neural_tensor = np.empty((n_trials, n_good_units, N_BINS), dtype=np.float16)
for unit_idx, spikes in enumerate(good_spike_times):
    edge_idx = np.searchsorted(spikes, trial_edge_matrix, side="left")
    counts = np.diff(edge_idx, axis=1)
    neural_tensor[:, unit_idx, :] = (counts / BIN_WIDTH_S).astype(np.float16)
```

**What this does:** Largest per-session costs are reading the full ragged spike-times array from HDF5 and the per-unit binning loop (n_good_units × searchsorted call); also pickling the final 4.6 GB output.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Vectorized per-unit `searchsorted` binning across all trials at once" (CONVERSION_NOTES.md:258)

**Code** (convert_data.py:248, 339, 95-97):
```python
for trial_idx in range(len(trial_start)):
    ...
for unit_idx, spikes in enumerate(good_spike_times):
    edge_idx = np.searchsorted(spikes, trial_edge_matrix, side="left")
...
def split_ragged(flat: np.ndarray, index: np.ndarray) -> list[np.ndarray]:
    starts = np.concatenate(([0], index[:-1]))
    return [flat[s:e] for s, e in zip(starts, index, strict=True)]
```

**What this does:** Per-trial Python loop builds records (could be vectorized over the trial dimension for input/output construction); per-unit loop for spike binning remains (cross-unit vectorization is harder due to ragged spike arrays); `split_ragged` materializes a Python list of arrays.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:601-613, 621-622):
```python
def select_files(all_files, sample_mode):
    for path in all_files:
        with h5py.File(path, "r") as f:
            classification = decode_strings(f["units"]["classification"])
            if np.sum(classification == "good") == 0:
                excluded.append(path.name)
                continue
        selected.append(path)
...
all_files = load_candidate_files()
session_files, excluded_sessions = select_files(all_files, sample_mode=sample_mode)
...
# Later in main():
est_full_s = mean_session_s * max(1, len(select_files(all_files, sample_mode=False)[0]))
```

**What this does:** `select_files` opens every NWB file once just to read `units.classification`; `process_session` then re-opens each kept NWB file to read the same classification field (and all other data). Also `select_files` is called a second time at the end purely for the `est_full_s` print, re-scanning all files.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:215-220, 376-387):
```python
obs_intervals = f["units"]["obs_intervals"][:].astype(np.float64)
obs_intervals_index = f["units"]["obs_intervals_index"][:]
first_good_unit = int(good_unit_indices[0])
obs_start = 0 if first_good_unit == 0 else int(obs_intervals_index[first_good_unit - 1])
obs_stop = int(obs_intervals_index[first_good_unit])
session_obs_intervals = obs_intervals[obs_start:obs_stop]
...
plot_payload = {
    ...
    "tongue_y_raw": tongue_data[:, 1].astype(np.float32),
    "tongue_y_processed": processed_tongue_y.copy(),
    ...
    "neural_trial": neural_tensor[trial_idx].astype(np.float32),
    ...
}
```

**What this does:** Reads the full `obs_intervals` array but only uses the slice for the first good unit (assumes session-level coverage). Builds `plot_payload` only when `--show-processing` is set, but when set retains large session-length arrays (raw tongue, timestamps) for later plotting. Stats fields (`choice_sources`, `tongue_info`, etc.) are computed but not saved into the output pickle.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Session-by-session processing to bound peak memory." (CONVERSION_NOTES.md:260)
> "`float16` neural storage and preallocated `(n_trials, n_units, n_bins)` session tensors." (CONVERSION_NOTES.md:261)

**Code** (convert_data.py:325-342, 653):
```python
trial_edge_matrix = np.empty((n_trials, N_BINS + 1), dtype=np.float64)
input_tensor = np.empty((n_trials, 2, N_BINS), dtype=np.float32)
output_tensor = np.empty((n_trials, 4, N_BINS), dtype=np.int16)
...
neural_tensor = np.empty((n_trials, n_good_units, N_BINS), dtype=np.float16)
for unit_idx, spikes in enumerate(good_spike_times):
    edge_idx = np.searchsorted(spikes, trial_edge_matrix, side="left")
    counts = np.diff(edge_idx, axis=1)
    neural_tensor[:, unit_idx, :] = (counts / BIN_WIDTH_S).astype(np.float16)
...
gc.collect()
```

**What this does:** Stores firing rates as `float16`, output codes as `int16`, inputs as `float32`; preallocates per-session tensors; processes one session at a time and triggers `gc.collect()` between sessions; uses h5py inside `with` blocks so file handles close after reads.

**Rating:** ok

**Note:** _(no note)_

---
