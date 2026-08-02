# map — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/map/codex/2026-03-23__08-25-17_trial1/verifier/snapshot/`

Outputs identified (K=4): choice, outcome, early_lick, tongue_y_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Session discovery from `data/sub-*/*.nwb`" (CONVERSION_NOTES.md:225); "Used `h5py` directly instead of PyNWB for the conversion path." (CONVERSION_NOTES.md:247)

**Code** (convert_data.py:46-47, 239-262, 594-598):
```python
def get_session_files(data_dir: Path) -> list[Path]:
    return sorted(data_dir.glob("sub-*/*.nwb"))

# in process_session:
with h5py.File(file_path, "r") as h5:
    subject_id, session_id = get_session_identity(file_path)
    units = h5["units"]
    ...
    trials = h5["intervals"]["trials"]
    ...
    go_times_all = h5["acquisition"]["BehavioralEvents"]["go_start_times"]["timestamps"][:n_behavior_trials].astype(np.float64)

# main:
all_files = get_session_files(data_dir)   # data_dir = /app/data
target_files = all_files[:12] if sample else all_files
for idx, file_path in enumerate(target_files, start=1):
    result = process_session(file_path, ...)
```

**What this does:** Globs `data/sub-*/*.nwb` to enumerate one NWB file per (subject, session). Each file is opened with `h5py` and processed sequentially in `process_session`, which reads trial table, units, behavioral events, and tongue tracking groups directly from HDF5.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`subject.subject_id` or folder name `sub-<id>` → `subjects`, `subject_idx`; Deduplicate subjects; map each session to subject index" (CONVERSION_NOTES.md:192)

**Code** (convert_data.py:50-53, 512-514, 561-562):
```python
def get_session_identity(file_path: Path) -> tuple[str, str]:
    subject_id = file_path.parent.name.replace("sub-", "")
    session_id = file_path.stem
    return subject_id, session_id

# in build_dataset:
subjects = sorted({r.subject_id for r in results})
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
...
"subjects": subjects,
"subject_idx": np.array([subject_to_idx[r.subject_id] for r in results], dtype=np.int64),
```

**What this does:** Subject ID is parsed from the parent folder name (`sub-<id>`). After all sessions are processed, unique subject IDs are sorted and a `subject_idx` array maps each session to its subject index.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Each subject folder contains one NWB file per session" (CONVERSION_NOTES.md:73)

**Code** (convert_data.py:46-53, 538-539):
```python
def get_session_files(data_dir: Path) -> list[Path]:
    return sorted(data_dir.glob("sub-*/*.nwb"))

def get_session_identity(file_path: Path) -> tuple[str, str]:
    subject_id = file_path.parent.name.replace("sub-", "")
    session_id = file_path.stem
    return subject_id, session_id

# build_dataset metadata:
"session_ids": [r.session_id for r in results],
"source_files": [r.source_file for r in results],
```

**What this does:** Each `.nwb` file is treated as one session, with the session ID derived from the file stem. One `SessionResult` is produced per file.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`intervals/trials`: trial table with columns ... plus `start_time` and `stop_time`." (CONVERSION_NOTES.md:77); "Per-trial go cue absolute timestamp" (CONVERSION_NOTES.md:185)

**Code** (convert_data.py:248-258, 285-292):
```python
trials = h5["intervals"]["trials"]
n_behavior_trials = int(len(trials["id"]))
trial_start_all = trials["start_time"][:].astype(np.float64)
trial_stop_all = trials["stop_time"][:].astype(np.float64)
trial_instruction_all = np.char.lower(decode_str_array(trials["trial_instruction"][:]))
early_lick_all = np.char.lower(decode_str_array(trials["early_lick"][:]))
outcome_all = np.char.lower(decode_str_array(trials["outcome"][:]))
photostim_onset_all = decode_str_array(trials["photostim_onset"][:])
photostim_duration_all = decode_str_array(trials["photostim_duration"][:])

go_times_all = h5["acquisition"]["BehavioralEvents"]["go_start_times"]["timestamps"][:n_behavior_trials].astype(np.float64)
...
trial_start = trial_start_all[selected_trial_idx]
trial_stop = trial_stop_all[selected_trial_idx]
go_times = go_times_all[selected_trial_idx]
```

**What this does:** Trials come from the NWB `intervals/trials` table, with one row per trial. Each trial keeps its `start_time`, `stop_time`, and per-trial go cue from `BehavioralEvents/go_start_times` (truncated to the number of behavioral trials). Output is one `(units, bins)` matrix per kept trial.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "A trial is kept only if its full `[-2.5 s, +1.5 s]` neural window is supported by the raw session observation interval." (README.md:54); "Retain early-lick, miss, hit, ignore, and photostimulation trials because these are either decoder outputs or decoder inputs." (CONVERSION_NOTES.md:203)

**Code** (convert_data.py:70-83, 294-299, 404-407):
```python
def select_trial_indices(go_times_all, good_unit_obs_intervals):
    session_obs_start = float(np.min(good_unit_obs_intervals[:, 0]))
    session_obs_stop = float(np.max(good_unit_obs_intervals[:, 1]))
    full_window_mask = (
        (go_times_all + WINDOW_START_S >= session_obs_start)
        & (go_times_all + WINDOW_END_S <= session_obs_stop)
    )
    trial_idx = np.flatnonzero(full_window_mask)
    ...

is_good_trials_raw = units["is_good_trials"][good_unit_idx, :n_recorded_trials].astype(bool)
uses_direct_is_good_trials = is_good_trials_raw.shape[1] == len(selected_trial_idx)

# After neural binning, drop all-zero-neural trials:
nonzero_trial_mask = np.any(neural_session > 0, axis=(1, 2))
if dropped_zero_trials:
    neural_session = neural_session[nonzero_trial_mask]
    ...
```

**What this does:** Trial QC is two-stage. First, only trials whose full `[-2.5, +1.5] s` window lies within the union of good-unit `obs_intervals` are kept. Second, any trial with all-zero neural activity is dropped. `is_good_trials` is used per-(unit, trial) only when its column count matches the selected trial set; otherwise per-unit `obs_intervals` overlap is recomputed and out-of-range bins are zeroed. Early-lick / photostim / ignore trials are intentionally retained.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`units/spike_times` for units with `classification == good` → `neural`" (CONVERSION_NOTES.md:183); "Go-cue alignment from `BehavioralEvents/go_start_times`" (CONVERSION_NOTES.md:226)

**Code** (convert_data.py:242, 270-271, 280, 300-302, 258):
```python
units = h5["units"]
...
classification = np.char.lower(decode_str_array(units["classification"][:]))
good_unit_idx = np.flatnonzero(classification == "good")
...
unit_obs_intervals = units["obs_intervals"][good_unit_idx].astype(np.float64)
...
spike_times = units["spike_times"][:].astype(np.float64)
spike_times_index = units["spike_times_index"][:]

go_times_all = h5["acquisition"]["BehavioralEvents"]["go_start_times"]["timestamps"][:n_behavior_trials].astype(np.float64)
```

**What this does:** `neural` is built from `units/spike_times` (with `units/spike_times_index` for ragged-row offsets) for units flagged `classification == "good"`, aligned to per-trial go cues from `BehavioralEvents/go_start_times`. `units/obs_intervals` and `units/is_good_trials` are used for validity masking.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural binning: Use 50 ms non-overlapping bins and convert to firing rates in Hz." (CONVERSION_NOTES.md:199); "Stored neural firing rates as `float16` to reduce pickle size" (CONVERSION_NOTES.md:250)

**Code** (convert_data.py:384-402):
```python
neural_session = np.zeros((n_trials, n_units, n_bins), dtype=np.float16)
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
flat_edges = abs_edges.reshape(-1)

for unit_pos, unit_idx in enumerate(good_unit_idx):
    spikes = spike_times[spike_starts[unit_idx]:spike_ends[unit_idx]]
    edge_indices = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_bins + 1)
    counts = np.diff(edge_indices, axis=1).astype(np.float32)
    fr = counts / bin_width
    if uses_direct_is_good_trials:
        invalid_trials = ~is_good_trials[unit_pos]
    else:
        obs_start = unit_obs_intervals[unit_pos, 0]
        obs_stop = unit_obs_intervals[unit_pos, 1]
        valid_obs = (go_times + WINDOW_START_S >= obs_start) & (go_times + WINDOW_END_S <= obs_stop)
        invalid_trials = ~valid_obs
    if np.any(invalid_trials):
        fr[invalid_trials] = 0.0
    neural_session[:, unit_pos, :] = fr.astype(np.float16)
```

**What this does:** For each good unit, spike times are binned by `np.searchsorted` against absolute bin edges (per-trial go cue + relative edge grid). Counts are divided by `0.05 s` to give firing rates in Hz, invalid trials are zeroed, and the result is cast to `float16`.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use units with `classification == good` as the primary QC filter" (CONVERSION_NOTES.md:197); "Sessions with zero good units are excluded" (README.md:52)

**Code** (convert_data.py:270-274, 294-299, 393-401):
```python
classification = np.char.lower(decode_str_array(units["classification"][:]))
good_unit_idx = np.flatnonzero(classification == "good")
if len(good_unit_idx) == 0:
    print(f"Skipping {session_id}: zero good units")
    return None
...
is_good_trials_raw = units["is_good_trials"][good_unit_idx, :n_recorded_trials].astype(bool)
uses_direct_is_good_trials = is_good_trials_raw.shape[1] == len(selected_trial_idx)
...
if uses_direct_is_good_trials:
    invalid_trials = ~is_good_trials[unit_pos]
else:
    valid_obs = (go_times + WINDOW_START_S >= obs_start) & (go_times + WINDOW_END_S <= obs_stop)
    invalid_trials = ~valid_obs
if np.any(invalid_trials):
    fr[invalid_trials] = 0.0
```

**What this does:** Units are kept only if `units/classification == "good"`. Per-(unit, trial) validity uses `units/is_good_trials` when it aligns with the selected trial set, otherwise per-unit `obs_intervals` coverage; invalid bins are zeroed. Sessions with zero good units are skipped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Window: `[-2.5 s, +1.5 s]`; Bin size: `50 ms`" (README.md:13-14); "non-overlapping 50 ms bins over [-2.5, 1.5) s relative to go cue" (CONVERSION_NOTES.md:227)

**Code** (convert_data.py:14-16, 40-43, 384-392):
```python
BIN_WIDTH_S = 0.05
WINDOW_START_S = -2.5
WINDOW_END_S = 1.5

def bin_edges_and_centers():
    edges = np.arange(WINDOW_START_S, WINDOW_END_S + BIN_WIDTH_S * 0.5, BIN_WIDTH_S, dtype=np.float64)
    centers = edges[:-1] + BIN_WIDTH_S / 2.0
    return edges, centers

# binning:
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
flat_edges = abs_edges.reshape(-1)
edge_indices = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_bins + 1)
counts = np.diff(edge_indices, axis=1).astype(np.float32)
fr = counts / bin_width
```

**What this does:** 80 non-overlapping 50 ms bins span `[-2.5, +1.5] s` relative to go cue. Spike counts per bin are computed by `np.searchsorted` between absolute edges, then divided by bin width to get Hz.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Alignment: go cue onset" (README.md:12); "`acquisition/BehavioralEvents/go_start_times.timestamps` → temporal alignment anchor; Per-trial go cue absolute timestamp; subtract from neural/behavioral timestamps" (CONVERSION_NOTES.md:185)

**Code** (convert_data.py:258, 292, 385):
```python
go_times_all = h5["acquisition"]["BehavioralEvents"]["go_start_times"]["timestamps"][:n_behavior_trials].astype(np.float64)
...
go_times = go_times_all[selected_trial_idx]
...
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
```

**What this does:** Each trial's bin edges are computed as `go_time[trial] + bin_edges_rel`, so spike-time binning is naturally anchored to per-trial go cue onset.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_tone_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:186 — "| Earliest `sample_start_times` event within trial window | `input[0]` (`time_from_tone_onset_s`) | For each bin, set value to `(bin_center_rel_go - sample_onset_rel_go)` in seconds | ... | Normal trials give ~-1.85 s tone onset; early-lick trials can have earlier tone onset because replay extends trial structure. |"
> CONVERSION_NOTES.md:200 — "**Tone-onset input**: Use the earliest sample-start event in each trial as tone onset."
> README.md:28-31 — "Order of `input_names`: 1. `time_from_tone_onset_s` 2. `photostim_on`"

**Code** (convert_data.py:250-260):
```python
trial_start_all = trials["start_time"][:].astype(np.float64)
trial_stop_all = trials["stop_time"][:].astype(np.float64)
...
go_times_all = h5["acquisition"]["BehavioralEvents"]["go_start_times"]["timestamps"][:n_behavior_trials].astype(np.float64)
sample_start_times = h5["acquisition"]["BehavioralEvents"]["sample_start_times"]["timestamps"][:].astype(np.float64)
```

**What this does:** The input is built from `acquisition/BehavioralEvents/sample_start_times` (tone/sample onset event timestamps), `acquisition/BehavioralEvents/go_start_times` (per-trial go cue), and the `intervals/trials` `start_time`/`stop_time` columns used to window which sample events belong to each trial. A constant fallback `EXPECTED_SAMPLE_ONSET_REL_GO = -1.85` (convert_data.py:17) is used for trials with no sample event.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_tone_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:186 — "For each bin, set value to `(bin_center_rel_go - sample_onset_rel_go)` in seconds"
> CONVERSION_NOTES.md:200 — "Use the earliest sample-start event in each trial as tone onset. This preserves replay-induced timing shifts visible in early-lick trials..."
> CONVERSION_NOTES.md:229 — "`time_from_tone_onset_s` from per-trial earliest sample onset"
> CONVERSION_NOTES.md:266 — "| `time_from_tone_onset_s` range | [-0.625, 5.723] |" (sample); CONVERSION_NOTES.md:331 — full-run range "[-1.525, 11.894]"

**Code** (convert_data.py:309-330):
```python
sample_slice_starts, sample_slice_ends = event_slices_for_trials(sample_start_times, trial_start, trial_stop)
...
sample_onset_abs = np.empty(n_trials, dtype=np.float64)
sample_onset_fallbacks = 0
for trial in range(n_trials):
    events = sample_start_times[sample_slice_starts[trial]:sample_slice_ends[trial]]
    if len(events):
        sample_onset_abs[trial] = events[0]
    else:
        sample_onset_abs[trial] = go_times[trial] + EXPECTED_SAMPLE_ONSET_REL_GO
        sample_onset_fallbacks += 1

sample_onset_rel_go = sample_onset_abs - go_times

# Inputs
input_trials = []
for trial in range(n_trials):
    inp = np.zeros((2, n_bins), dtype=np.float32)
    inp[0] = (bin_centers_rel - sample_onset_rel_go[trial]).astype(np.float32)
```

**What this does:** For each trial, `searchsorted` selects the sample-start events falling inside `[trial_start, trial_stop]` and takes the earliest as tone onset; that absolute time is converted to a go-cue-relative offset and subtracted from each bin center, producing a continuous per-bin elapsed-time-since-tone value in seconds (negative before tone onset). Trials with no in-window sample event fall back to a fixed -1.85 s offset from the go cue, counted in `sample_onset_fallbacks`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `input` *time_from_tone_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:185 — "`acquisition/BehavioralEvents/go_start_times.timestamps` | temporal alignment anchor | Per-trial go cue absolute timestamp; subtract from neural/behavioral timestamps"
> CONVERSION_NOTES.md:226-229 — "Go-cue alignment from `BehavioralEvents/go_start_times`... Neural binning ... into 50 ms firing-rate bins over [-2.5, 1.5) s ... Time-varying decoder inputs: `time_from_tone_onset_s` from per-trial earliest sample onset"

**Code** (convert_data.py:14-17, 40-43, 328-329, 384-386):
```python
BIN_WIDTH_S = 0.05
WINDOW_START_S = -2.5
WINDOW_END_S = 1.5
...
def bin_edges_and_centers():
    edges = np.arange(WINDOW_START_S, WINDOW_END_S + BIN_WIDTH_S * 0.5, BIN_WIDTH_S, dtype=np.float64)
    centers = edges[:-1] + BIN_WIDTH_S / 2.0
    return edges, centers
...
    inp = np.zeros((2, n_bins), dtype=np.float32)
    inp[0] = (bin_centers_rel - sample_onset_rel_go[trial]).astype(np.float32)
...
neural_session = np.zeros((n_trials, n_units, n_bins), dtype=np.float16)
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
```

**What this does:** The input uses the same go-cue-relative bin grid (`bin_centers_rel`, 80 bins of 50 ms over [-2.5, 1.5) s) that defines the neural binning edges, so input bin *i* corresponds to the same go-aligned time window as neural bin *i* within each trial. Trials dropped for all-zero neural data are also dropped from `input_trials` (convert_data.py:414), keeping the trial lists index-matched.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `input` *photostim* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:187 — "| `photostim_onset`, `photostim_duration`, `photostim_power` trial-table columns | `input[1]` (`photostim_on`) | Binary time series: 1 during `[onset, onset+duration)` relative to go cue, else 0 | ... | Trial-table onset/duration matched the event-series timestamps in spot checks. |"
> CONVERSION_NOTES.md:86 — "`photostim_*` trial-table fields are strings such as `N/A` on no-stim trials."
> CONVERSION_NOTES.md:230 — "`photostim_on` from trial-table photostim onset/duration"

**Code** (convert_data.py:248-258):
```python
trials = h5["intervals"]["trials"]
n_behavior_trials = int(len(trials["id"]))
trial_start_all = trials["start_time"][:].astype(np.float64)
...
photostim_onset_all = decode_str_array(trials["photostim_onset"][:])
photostim_duration_all = decode_str_array(trials["photostim_duration"][:])

go_times_all = h5["acquisition"]["BehavioralEvents"]["go_start_times"]["timestamps"][:n_behavior_trials].astype(np.float64)
```

**What this does:** The photostim input comes from the `intervals/trials` table columns `photostim_onset` and `photostim_duration` (stored as strings, `"N/A"` on no-stim trials), combined with the trial `start_time` and the per-trial go cue timestamp from `acquisition/BehavioralEvents/go_start_times`. The `photostim_start_times`/`photostim_stop_times` event series are not read by the converter (CONVERSION_NOTES.md:187 states they were used only as a spot check).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `input` *photostim*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:201 — "**Photostim input**: Represent photostimulation as a time-varying binary series, not a static trial label, because the decoder task requests the on/off state at every time point."
> CONVERSION_NOTES.md:187 — "Binary time series: 1 during `[onset, onset+duration)` relative to go cue, else 0"
> CONVERSION_NOTES.md:267 / 332 — "| `photostim_on` range | [0, 1] |"

**Code** (convert_data.py:325-336):
```python
input_trials = []
photostim_trial_count = 0
for trial in range(n_trials):
    inp = np.zeros((2, n_bins), dtype=np.float32)
    inp[0] = (bin_centers_rel - sample_onset_rel_go[trial]).astype(np.float32)

    if str(photostim_onset[trial]) != "N/A":
        stim_rel_on = trial_start[trial] + float(photostim_onset[trial]) - go_times[trial]
        stim_rel_off = stim_rel_on + float(photostim_duration[trial])
        inp[1] = ((bin_centers_rel >= stim_rel_on) & (bin_centers_rel < stim_rel_off)).astype(np.float32)
        photostim_trial_count += 1
    input_trials.append(inp)
```

**What this does:** For trials whose `photostim_onset` string is not `"N/A"`, the onset (interpreted as an offset from `trial_start`) is converted to a go-cue-relative time, the offset time is onset plus `photostim_duration`, and each bin center inside `[on, off)` is set to 1.0 (float32); all other bins and all non-stim trials stay 0.0. The number of stim trials per session is recorded as `photostim_trials` in the stats dict (convert_data.py:481).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-c. How is `input` *photostim* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:187 — "Binary time series: 1 during `[onset, onset+duration)` relative to go cue, else 0"
> CONVERSION_NOTES.md:226-230 — "Go-cue alignment from `BehavioralEvents/go_start_times` ... Time-varying decoder inputs: ... `photostim_on` from trial-table photostim onset/duration"
> CONVERSION_NOTES.md:351 — "Input check: for the same session/trial, the full `time_from_tone_onset_s` vector and full `photostim_on` vector matched direct raw recomputation exactly (`np.allclose == True`, max abs diff `0.0`)."

**Code** (convert_data.py:331-334, 384-385, 414):
```python
    if str(photostim_onset[trial]) != "N/A":
        stim_rel_on = trial_start[trial] + float(photostim_onset[trial]) - go_times[trial]
        stim_rel_off = stim_rel_on + float(photostim_duration[trial])
        inp[1] = ((bin_centers_rel >= stim_rel_on) & (bin_centers_rel < stim_rel_off)).astype(np.float32)
...
neural_session = np.zeros((n_trials, n_units, n_bins), dtype=np.float16)
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
...
        input_trials = [trial for keep, trial in zip(nonzero_trial_mask, input_trials) if keep]
```

**What this does:** The stim window is expressed in the same go-cue-relative coordinates as the neural bin grid, and membership is tested against `bin_centers_rel` — the centers of the same 50 ms edges used for spike binning — so the `(2, 80)` input array is bin-for-bin aligned with the `(n_units, 80)` neural array of the same trial. The same `nonzero_trial_mask` prunes neural and input trial lists together.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "First post-go lick direction inferred from left/right lick events → `output[0]` (`choice`); Encode left=0, right=1 ... Fallback 1: first lick anywhere in trial. Fallback 2: trial instruction for no-lick ignore trials." (CONVERSION_NOTES.md:188)

**Code** (convert_data.py:86-115, 261-262, 252):
```python
left_lick_times = h5["acquisition"]["BehavioralEvents"]["left_lick_times"]["timestamps"][:].astype(np.float64)
right_lick_times = h5["acquisition"]["BehavioralEvents"]["right_lick_times"]["timestamps"][:].astype(np.float64)
trial_instruction_all = np.char.lower(decode_str_array(trials["trial_instruction"][:]))

def infer_choice_for_trial(trial_start, trial_stop, go_time, instruction, left_lick_times, right_lick_times):
    ...
    left_post = left_lick_times[left_go:left_stop]
    right_post = right_lick_times[right_go:right_stop]
    if len(left_post) or len(right_post):
        return (0, "post_go_lick") if first_left < first_right else (1, "post_go_lick")
    ...
    return (0 if instruction == "left" else 1, "instruction_fallback")
```

**What this does:** Derived from `BehavioralEvents/left_lick_times` and `right_lick_times`, plus `intervals/trials/trial_instruction` as a fallback when no lick occurs in the trial.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Primary rule: first post-go lick. Fallback 1: first lick anywhere in trial. Fallback 2: trial instruction for no-lick ignore trials." (CONVERSION_NOTES.md:188)

**Code** (convert_data.py:86-115, 339-351):
```python
def infer_choice_for_trial(trial_start, trial_stop, go_time, instruction, left_lick_times, right_lick_times):
    left_go = np.searchsorted(left_lick_times, go_time, side="left")
    left_stop = np.searchsorted(left_lick_times, trial_stop, side="right")
    ...
    left_post = left_lick_times[left_go:left_stop]
    right_post = right_lick_times[right_go:right_stop]
    if len(left_post) or len(right_post):
        first_left = left_post[0] if len(left_post) else np.inf
        first_right = right_post[0] if len(right_post) else np.inf
        return (0, "post_go_lick") if first_left < first_right else (1, "post_go_lick")
    left_any = left_lick_times[left_start:left_stop]
    right_any = right_lick_times[right_start:right_stop]
    if len(left_any) or len(right_any):
        return (0, "any_lick") if first_left < first_right else (1, "any_lick")
    return (0 if instruction == "left" else 1, "instruction_fallback")

choice_trials = np.empty(n_trials, dtype=np.int8)
for trial in range(n_trials):
    choice_val, source = infer_choice_for_trial(...)
    choice_trials[trial] = choice_val
```

**What this does:** For each trial, look at the first post-go lick across left/right streams. Earlier side wins (left=0, right=1). If no post-go lick, fall back to the first lick anywhere in `[trial_start, trial_stop]`. If no lick at all, fall back to `trial_instruction` (left/right).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials/outcome` → `output[1]` (`outcome`); Map `ignore -> 0`, `miss -> 1`, `hit -> 2`" (CONVERSION_NOTES.md:189)

**Code** (convert_data.py:254, 289, 353-355):
```python
outcome_all = np.char.lower(decode_str_array(trials["outcome"][:]))
...
outcome = outcome_all[selected_trial_idx]
...
outcome_map = {"ignore": 0, "miss": 1, "hit": 2}
outcome_trials = np.array([outcome_map[str(x)] for x in outcome], dtype=np.int8)
```

**What this does:** Read directly from `intervals/trials/outcome` string column.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map `ignore -> 0`, `miss -> 1`, `hit -> 2`" (CONVERSION_NOTES.md:189)

**Code** (convert_data.py:353-355):
```python
outcome_map = {"ignore": 0, "miss": 1, "hit": 2}
early_map = {"no early": 0, "early": 1}
outcome_trials = np.array([outcome_map[str(x)] for x in outcome], dtype=np.int8)
```

**What this does:** Lowercased string outcome labels are mapped to integers 0/1/2 via a dict lookup; no other processing.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *early_lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials/early_lick` → `output[2]` (`early_lick`); Map `no early -> 0`, `early -> 1`" (CONVERSION_NOTES.md:190)

**Code** (convert_data.py:253, 288, 354, 356):
```python
early_lick_all = np.char.lower(decode_str_array(trials["early_lick"][:]))
...
early_lick = early_lick_all[selected_trial_idx]
...
early_map = {"no early": 0, "early": 1}
early_trials = np.array([early_map[str(x)] for x in early_lick], dtype=np.int8)
```

**What this does:** Read from `intervals/trials/early_lick` string column.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *early_lick*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map `no early -> 0`, `early -> 1`" (CONVERSION_NOTES.md:190)

**Code** (convert_data.py:354, 356):
```python
early_map = {"no early": 0, "early": 1}
early_trials = np.array([early_map[str(x)] for x in early_lick], dtype=np.int8)
```

**What this does:** Lowercased label mapped to 0/1 by dict lookup.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *tongue_y_position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`BehavioralTimeSeries/Camera0_side_TongueTracking[:,1]` with timestamps → `output[3]` (`tongue_y_bin`)" (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:264-268):
```python
tongue_group = h5["acquisition"]["BehavioralTimeSeries"]["Camera0_side_TongueTracking"]
tongue_values = tongue_group["data"][:].astype(np.float64)
tongue_y = tongue_values[:, 1]
tongue_likelihood = tongue_values[:, 2]
tongue_timestamps = tongue_group["timestamps"][:].astype(np.float64)
```

**What this does:** Derived from the `y` column (index 1) of `BehavioralTimeSeries/Camera0_side_TongueTracking/data` plus its timestamps. The likelihood column is loaded but used only for plotting.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *tongue_y_position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Align absolute timestamps to go cue; within each 50 ms bin take the last available `tongue_y` sample; discretize within session using 40th and 60th percentiles over all aligned binned values" (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:118-132, 358-372):
```python
def bin_tongue_y(tongue_timestamps, tongue_y, go_times, bin_edges_rel):
    abs_edges = go_times[:, None] + bin_edges_rel[None, :]
    start_idx = np.searchsorted(tongue_timestamps, abs_edges[:, :-1], side="left")
    end_idx = np.searchsorted(tongue_timestamps, abs_edges[:, 1:], side="left") - 1
    clipped_end = np.clip(end_idx, 0, len(tongue_y) - 1)
    valid = end_idx >= start_idx
    binned = np.full(end_idx.shape, np.nan, dtype=np.float32)
    binned[valid] = tongue_y[clipped_end[valid]].astype(np.float32)
    return binned, valid

tongue_y_binned, tongue_valid = bin_tongue_y(...)
valid_values = tongue_y_binned[np.isfinite(tongue_y_binned)]
tongue_p40 = float(np.percentile(valid_values, 40))
tongue_p60 = float(np.percentile(valid_values, 60))
tongue_discrete = np.zeros_like(tongue_y_binned, dtype=np.int8)
tongue_discrete[(tongue_y_binned >= tongue_p40) & (tongue_y_binned <= tongue_p60)] = 1
tongue_discrete[tongue_y_binned > tongue_p60] = 2
```

**What this does:** For each (trial, 50 ms bin), take the last tongue-y sample in the bin (NaN if none). Then per-session compute 40th and 60th percentiles across all valid bins and discretize into {0=low, 1=mid, 2=high}.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *tongue_y_position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Align absolute timestamps to go cue" (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:124, 374-381):
```python
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
...
out[3] = tongue_discrete[trial]
```

**What this does:** Tongue alignment uses the same `go_times[:, None] + bin_edges_rel[None, :]` edge grid as the neural binning, so each trial's 80 tongue bins land in the same time bins as the neural rows; the discretized array is then placed in output row 3.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions with zero good units are excluded" (README.md:52); "Skipping {session_id}: zero recorded trials"; CONVERSION_NOTES.md:191 notes use of `tongue_likelihood` only as diagnostic.

**Code** (convert_data.py:243-274, 312-320, 331-335, 365-369, 404-407):
```python
n_recorded_trials = int(units["is_good_trials"].shape[1])
if n_recorded_trials == 0:
    print(f"Skipping {session_id}: zero recorded trials in units/is_good_trials")
    return None
...
if len(good_unit_idx) == 0:
    print(f"Skipping {session_id}: zero good units")
    return None
if np.any(brain_region_names == ""):
    raise ValueError(f"{session_id}: found kept good units with empty anno_name")
...
# Sample-onset fallback when no sample event found in trial window:
if len(events):
    sample_onset_abs[trial] = events[0]
else:
    sample_onset_abs[trial] = go_times[trial] + EXPECTED_SAMPLE_ONSET_REL_GO
    sample_onset_fallbacks += 1
...
# photostim N/A handled as no-stim:
if str(photostim_onset[trial]) != "N/A":
    ...
...
# Tongue: NaN where no samples in bin; raise if entire session has none:
if len(valid_values) == 0:
    raise ValueError(f"{session_id}: no valid tongue_y values after alignment")
...
# Drop trials with all-zero neural activity:
nonzero_trial_mask = np.any(neural_session > 0, axis=(1, 2))
```

**What this does:** Sessions with zero recorded trials or zero good units are skipped. Empty unit annotations raise. Missing sample-onset events fall back to a fixed offset (`-1.85 s`). `photostim_onset == "N/A"` is treated as no stimulation. Bins with no tongue sample are NaN, but a session with no valid tongue samples raises. Trials with completely zero neural activity are dropped.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sample conversion observed ~1.60 s / kept session; ~4.6 minutes for 173 kept sessions" (CONVERSION_NOTES.md:294); "Used vectorized `np.searchsorted` across all trial/bin edges per unit for spike binning." (CONVERSION_NOTES.md:248)

**Code** (convert_data.py:300, 384-402):
```python
spike_times = units["spike_times"][:].astype(np.float64)
...
neural_session = np.zeros((n_trials, n_units, n_bins), dtype=np.float16)
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
flat_edges = abs_edges.reshape(-1)
for unit_pos, unit_idx in enumerate(good_unit_idx):
    spikes = spike_times[spike_starts[unit_idx]:spike_ends[unit_idx]]
    edge_indices = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_bins + 1)
    counts = np.diff(edge_indices, axis=1).astype(np.float32)
    fr = counts / bin_width
    ...
    neural_session[:, unit_pos, :] = fr.astype(np.float16)
```

**What this does:** The dominant per-session cost is reading all `spike_times` from HDF5 and the per-unit Python loop that calls `np.searchsorted` on the unit's spike train against all trial/bin edges. Pickle dump of the final dataset (~3.7 GB) is also non-trivial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Per-spike/per-trial Python loops would be too slow for the full dataset." (CONVERSION_NOTES.md:243)

**Code** (convert_data.py:314-320, 327-336, 341-351, 388-402):
```python
for trial in range(n_trials):
    events = sample_start_times[sample_slice_starts[trial]:sample_slice_ends[trial]]
    if len(events):
        sample_onset_abs[trial] = events[0]
    ...
for trial in range(n_trials):
    inp = np.zeros((2, n_bins), dtype=np.float32)
    inp[0] = (bin_centers_rel - sample_onset_rel_go[trial]).astype(np.float32)
    if str(photostim_onset[trial]) != "N/A":
        ...
for trial in range(n_trials):
    choice_val, source = infer_choice_for_trial(...)
    choice_trials[trial] = choice_val
...
for unit_pos, unit_idx in enumerate(good_unit_idx):
    spikes = spike_times[spike_starts[unit_idx]:spike_ends[unit_idx]]
    edge_indices = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_bins + 1)
```

**What this does:** Per-trial loops over sample-onset selection, input construction, photostim window construction, and choice inference are written in pure Python; they could be vectorized with `np.searchsorted` plus broadcasting over the trial axis. The per-unit binning loop could also be done as a single multi-segment `searchsorted` on the concatenated spike arrays.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:64-67, 94-99, 124-126, 309-310, 443-446):
```python
def event_slices_for_trials(event_times, trial_starts, trial_stops):
    start_idx = np.searchsorted(event_times, trial_starts, side="left")
    stop_idx = np.searchsorted(event_times, trial_stops, side="right")

# infer_choice_for_trial recomputes searchsorted per trial:
left_start = np.searchsorted(left_lick_times, trial_start, side="left")
left_go = np.searchsorted(left_lick_times, go_time, side="left")
left_stop = np.searchsorted(left_lick_times, trial_stop, side="right")

# bin_tongue_y and neural binning each rebuild abs_edges = go_times[:, None] + bin_edges_rel[None, :]
abs_edges = go_times[:, None] + bin_edges_rel[None, :]
```

**What this does:** `np.searchsorted` against `left_lick_times` / `right_lick_times` is invoked six times per trial inside `infer_choice_for_trial`, instead of once in batch. The `abs_edges` grid `go_times[:, None] + bin_edges_rel[None, :]` is rebuilt independently in `bin_tongue_y` and in the neural-binning loop. Per-trial `event_slices_for_trials` is computed twice (once for sample, once for delay) but the delay slice indices are only used in the optional plot path.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use `tongue_likelihood` only for QC diagnostics, not thresholding" (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:267, 309-310, 469, 472-497):
```python
tongue_likelihood = tongue_values[:, 2]
...
sample_slice_starts, sample_slice_ends = event_slices_for_trials(sample_start_times, trial_start, trial_stop)
delay_slice_starts, delay_slice_ends = event_slices_for_trials(delay_start_times, trial_start, trial_stop)
...
"tongue_likelihood_window": tongue_likelihood[tongue_window],
...
stats = {
    "session_id": session_id,
    ...
    "fraction_invalid_unit_trials": float(np.mean(~is_good_trials)),
    "mean_good_trial_fraction_per_good_unit": float(np.mean(is_good_trials.mean(axis=1))),
}
```

**What this does:** `tongue_likelihood` is loaded but only used in plotting. `delay_start_times` slicing is computed for every trial but only consumed in optional plots. Per-session `stats` dict (with many summary numbers and fallback counters) is computed even though it is not surfaced in the final pickle. `is_good_trials_raw` is loaded even when not used directly.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Stored neural firing rates as `float16` to reduce pickle size while remaining valid floating-point input for the decoder (training code converts to `float32`)." (CONVERSION_NOTES.md:250); "Used `h5py` directly instead of PyNWB for the conversion path." (CONVERSION_NOTES.md:247)

**Code** (convert_data.py:7, 239, 339, 355-356, 376, 384, 402):
```python
import h5py
...
with h5py.File(file_path, "r") as h5:
    ...
choice_trials = np.empty(n_trials, dtype=np.int8)
outcome_trials = np.array([outcome_map[str(x)] for x in outcome], dtype=np.int8)
early_trials = np.array([early_map[str(x)] for x in early_lick], dtype=np.int8)
out = np.empty((4, n_bins), dtype=np.int8)
neural_session = np.zeros((n_trials, n_units, n_bins), dtype=np.float16)
...
neural_session[:, unit_pos, :] = fr.astype(np.float16)
```

**What this does:** Neural firing rates are stored as `float16`; categorical outputs as `int8`. HDF5 files are opened with `h5py` rather than PyNWB to avoid PyNWB's full-object materialization. Spike-time slabs are loaded once per session. Sessions are processed one at a time but all `SessionResult` objects are held in memory until the final pickle dump.

**Rating:** ok

**Note:** _(no note)_---

---
