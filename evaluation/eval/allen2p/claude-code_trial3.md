# allen2p — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/allen2p/claude-code/2026-03-26__07-49-34_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:14-16 "284 NWB experiment files"; CONVERSION_NOTES.md:236 "convert_data.py loads NWB files via h5py, extracts events (valid_roi only), trials, running speed, pupil"; CONVERSION_NOTES.md:219 "Each NWB experiment = one 'session' in output format"

**Code** (convert_data.py:427-471):
```python
def get_experiment_list(sample=False):
    exp_table = pd.read_csv(META_DIR / 'ophys_experiment_table.csv')
    nwb_files = list(NWB_DIR.glob('*.nwb'))
    nwb_ids = set()
    for f in nwb_files:
        try:
            eid = int(f.stem.split('_')[-1])
            nwb_ids.add(eid)
        except ValueError:
            pass
    mask = (
        exp_table['ophys_experiment_id'].isin(nwb_ids) &
        exp_table['session_type'].isin(ACTIVE_SESSION_TYPES)
    )
    active_exps = exp_table[mask].copy()
    ...
```

And per experiment (convert_data.py:117-226):
```python
def load_experiment_data(nwb_path, experiment_id):
    with h5py.File(nwb_path, 'r') as f:
        cell_table = f['processing']['ophys']['image_segmentation']['cell_specimen_table']
        ...
        events_data = f['processing']['ophys']['event_detection']['data'][()]
        trials_grp = f['intervals']['trials']
        ...
        running_speed = f['processing']['running']['speed']['data'][()]
        pupil_tracking = f['acquisition']['EyeTracking']['pupil_tracking']
```

**What this does:** Reads NWB files directly with h5py (not via AllenSDK), discovering experiment IDs by globbing the `behavior_ophys_experiments/` directory and joining against `ophys_experiment_table.csv`. Filters to ACTIVE_SESSION_TYPES (OPHYS_1/3/4/6, images A and B). For each experiment, opens the NWB file and pulls cell_specimen_table, event detection traces, ophys timestamps, trials table, stimulus presentations, running speed, and pupil tracking.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:218 "Subject IDs: Use mouse_id from experiment table."

**Code** (convert_data.py:483-484):
```python
subjects = sorted(exp_table['mouse_id'].unique().astype(str))
subject_to_idx = {s: i for i, s in enumerate(subjects)}
```

And per-experiment subject indexing (convert_data.py:635):
```python
all_subject_idx.append(subject_to_idx[str(row['mouse_id'])])
```

**What this does:** Subjects are unique `mouse_id` values from the experiment table CSV, sorted as strings. Each session (NWB experiment) is tagged with its subject index via `subject_to_idx`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:219 "Each NWB experiment = one 'session' in output format (one imaging plane with its own neurons)."

**Code** (convert_data.py:557-559):
```python
for idx, (_, row) in enumerate(exp_table.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = NWB_DIR / f'behavior_ophys_experiment_{eid}.nwb'
```

**What this does:** Each NWB file (one `ophys_experiment_id`) is treated as an independent session in the output. Multi-plane experiments from the same `ophys_session_id` are not grouped — each imaging plane becomes a separate output session. Iteration order follows the order of the experiment table rows after filtering.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:211 "Trial window: Use trial start_time to stop_time from trials table. Variable length across trials."

**Code** (convert_data.py:299-307, 354-366):
```python
trials = raw_data['trials']
valid_mask = (trials['go'] | trials['catch']) & ~trials['aborted'] & ~trials['auto_rewarded']
valid_indices = np.where(valid_mask)[0]
...
for trial_idx in valid_indices:
    t_trial_start = trials['start_time'][trial_idx]
    t_trial_stop = trials['stop_time'][trial_idx]
    trial_mask = (regular_ts >= t_trial_start) & (regular_ts < t_trial_stop)
    trial_time_indices = np.where(trial_mask)[0]
    if len(trial_time_indices) < 3:
        continue
    trial_ts = regular_ts[trial_time_indices]
```

**What this does:** Trials come from the NWB `intervals/trials` table. A valid trial is Go or Catch and not Aborted and not Auto-rewarded. The trial window spans `start_time` to `stop_time` (variable length); the resampled 30 Hz timestamps falling inside this window define the trial frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:139 "Per task instructions: include Go and Catch trials, exclude Aborted and Auto-rewarded"; CONVERSION_NOTES.md:208 "Exclude aborted and auto-rewarded trials: Per task instructions."

**Code** (convert_data.py:301-307, 362-363, 408-410):
```python
valid_mask = (trials['go'] | trials['catch']) & ~trials['aborted'] & ~trials['auto_rewarded']
valid_indices = np.where(valid_mask)[0]
if len(valid_indices) < 2:
    print(f"  WARNING: Only {len(valid_indices)} valid trials in experiment {raw_data['experiment_id']}, skipping")
    return None
...
if len(trial_time_indices) < 3:
    continue
...
if len(neural_trials) < 2:
    print(f"  WARNING: Only {len(neural_trials)} processed trials in experiment {raw_data['experiment_id']}, skipping")
    return None
```

Also outcome filter (convert_data.py:387-396):
```python
if trials['hit'][trial_idx]:
    outcome = 0
elif trials['miss'][trial_idx]:
    outcome = 1
elif trials['false_alarm'][trial_idx]:
    outcome = 2
elif trials['correct_reject'][trial_idx]:
    outcome = 3
else:
    continue  # Unknown outcome, skip
```

**What this does:** Excludes Aborted and Auto-rewarded trials; requires Go or Catch flag. Trials with fewer than 3 resampled timepoints are skipped. Trials lacking a hit/miss/false_alarm/correct_reject outcome are skipped. Sessions with fewer than 2 valid trials before processing or fewer than 2 processed trials after the loop are dropped.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:200 "`event_detection/data` (filtered by valid_roi) → neural"; CONVERSION_NOTES.md:207 "Neural signal: events (not dF/F): Paper says 'We performed our analyses on discrete calcium events.' Use raw events from event_detection."

**Code** (convert_data.py:124-140):
```python
cell_table = f['processing']['ophys']['image_segmentation']['cell_specimen_table']
valid_roi = cell_table['valid_roi'][()].astype(bool)
cell_specimen_ids = cell_table['cell_specimen_id'][()]
n_valid = valid_roi.sum()
...
ophys_ts = f['processing']['ophys']['dff']['traces']['timestamps'][()]
events_data = f['processing']['ophys']['event_detection']['data'][()]
events_valid = events_data[:, valid_roi]
```

**What this does:** Neural data comes from the NWB `processing/ophys/event_detection/data` (FastLZeroSpikeInference calcium events), restricted to ROIs flagged `valid_roi=True` in the cell_specimen_table.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:240 "Resamples all data streams to 30 Hz via linear interpolation"; CONVERSION_NOTES.md:242 "Events are clipped to >=0 after interpolation"

**Code** (convert_data.py:309-322):
```python
ophys_ts = raw_data['ophys_ts']
events = raw_data['events']  # (n_timepoints, n_cells)

t_start = ophys_ts[0]
t_end = ophys_ts[-1]
dt = 1.0 / target_rate
regular_ts = np.arange(t_start, t_end, dt)

events_resampled = interpolate_to_regular_grid(ophys_ts, events, regular_ts)
events_resampled = np.maximum(events_resampled, 0)
```

`interpolate_to_regular_grid` (convert_data.py:47-64):
```python
def interpolate_to_regular_grid(timestamps, data, target_timestamps):
    if data.ndim == 1:
        return np.interp(target_timestamps, timestamps, data)
    else:
        result = np.zeros((len(target_timestamps), data.shape[1]), dtype=np.float32)
        for i in range(data.shape[1]):
            result[:, i] = np.interp(target_timestamps, timestamps, data[:, i])
        return result
```

**What this does:** Per-neuron event traces are linearly interpolated from native ophys timestamps onto a regular 30 Hz grid spanning `[ophys_ts[0], ophys_ts[-1])`, then clipped to be non-negative. No additional smoothing or normalization is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:131-132 "Neuron curation rules: valid_roi == True (SVM classifier output)"; CONVERSION_NOTES.md:217 "valid_roi filtering: Only include neurons with valid_roi=True."

**Code** (convert_data.py:126-132):
```python
valid_roi = cell_table['valid_roi'][()].astype(bool)
cell_specimen_ids = cell_table['cell_specimen_id'][()]
n_valid = valid_roi.sum()
if n_valid == 0:
    print(f"  WARNING: No valid ROIs in experiment {experiment_id}, skipping")
    return None
```

**What this does:** Neurons are filtered to those with `valid_roi=True` from the NWB cell_specimen_table (the SDK's SVM-based ROI quality flag). Experiments with zero valid ROIs are skipped entirely. No further per-neuron filtering is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:210 "Resample to 30 Hz: Paper interpolates to 30 Hz. Needed for consistent time bins across Scientifica (31 Hz) and Multiscope (11 Hz). time_bin_size = 33.33 ms."

**Code** (convert_data.py:30-31, 313-320):
```python
TARGET_RATE_HZ = 30.0  # Paper: "linearly interpolating onto a consistent set of 30hz timestamps"
TIME_BIN_MS = 1000.0 / TARGET_RATE_HZ  # ~33.33 ms
...
t_start = ophys_ts[0]
t_end = ophys_ts[-1]
dt = 1.0 / target_rate
regular_ts = np.arange(t_start, t_end, dt)
events_resampled = interpolate_to_regular_grid(ophys_ts, events, regular_ts)
```

**What this does:** Neural events are resampled (linear interpolation) to a fixed 30 Hz regular grid (~33.33 ms bin). All other streams (running, pupil) are interpolated onto the same grid, so neural and behavior share timestamps.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:212 "Alignment event: Trial start time (stimulus onset). off_start=0, off_end=None (variable)."

**Code** (convert_data.py:354-369, 686-687):
```python
for trial_idx in valid_indices:
    t_trial_start = trials['start_time'][trial_idx]
    t_trial_stop = trials['stop_time'][trial_idx]
    trial_mask = (regular_ts >= t_trial_start) & (regular_ts < t_trial_stop)
    trial_time_indices = np.where(trial_mask)[0]
    ...
    neural_trial = events_resampled[trial_time_indices, :].T.astype(np.float32)
...
'temporal_alignment_event': 'Trial start time (first stimulus onset of trial)',
'off_start': 0.0,
'off_end': None,
```

**What this does:** For each trial, neural frames are selected by indexing the 30 Hz grid with samples whose timestamps fall in `[start_time, stop_time)` of the NWB trials table. The alignment event is recorded as trial start with `off_start=0` and `off_end=None`. Trial length is variable.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `output` *Running speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:202 "`running/speed/data` → output[2]: running_speed"

**Code** (convert_data.py:194-195):
```python
running_speed = f['processing']['running']['speed']['data'][()]
running_ts = f['processing']['running']['speed']['timestamps'][()]
```

**What this does:** Pulled directly from the NWB `processing/running/speed/data` array (cm/s) with corresponding `timestamps`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `output` *Running speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:202 "Interpolate to 30 Hz, discretize into 5 percentile bins, time-varying"; CONVERSION_NOTES.md:238 "3-pass approach: ... (2) compute global percentile bins for running/pupil"

**Code** (convert_data.py:67-97, 324-325, 540-547, 612):
```python
def compute_percentile_bins(values, n_bins=5):
    valid = values[~np.isnan(values)]
    ...
    percentiles = np.linspace(0, 100, n_bins + 1)
    edges = np.percentile(valid, percentiles)
    for i in range(1, len(edges)):
        if edges[i] <= edges[i-1]:
            edges[i] = edges[i-1] + 1e-10
    return edges

def digitize_to_bins(values, bin_edges):
    n_bins = len(bin_edges) - 1
    binned = np.digitize(values, bin_edges[1:-1])
    binned = np.clip(binned, 0, n_bins - 1)
    binned[np.isnan(values)] = 0
    return binned.astype(np.int64)
...
running_resampled = np.interp(regular_ts, raw_data['running_ts'], raw_data['running_speed'])
...
all_running_cat = np.concatenate(all_running_values) if all_running_values else np.array([0.0])
running_bin_edges = compute_percentile_bins(all_running_cat, n_bins=5)
...
running_binned = digitize_to_bins(trial_data_out['running_speed'], running_bin_edges)
```

**What this does:** Running speed is linearly interpolated to the 30 Hz grid. In an earlier pass, all-session running values are concatenated and used to compute 5 global percentile bin edges. Per-trial values are then digitized into those bin indices (NaNs map to bin 0).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `output` *Running speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:325, 354-378):
```python
running_resampled = np.interp(regular_ts, raw_data['running_ts'], raw_data['running_speed'])
...
trial_mask = (regular_ts >= t_trial_start) & (regular_ts < t_trial_stop)
trial_time_indices = np.where(trial_mask)[0]
...
neural_trial = events_resampled[trial_time_indices, :].T.astype(np.float32)
...
running_trial = running_resampled[trial_time_indices]
```

**What this does:** Running speed is interpolated onto the same 30 Hz `regular_ts` grid used for neural events, and the same `trial_time_indices` slice is then applied to both arrays, so they share frame indices within a trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `output` *Pupil diameter* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:203 "`EyeTracking/pupil_tracking/area` → output[3]: pupil_diameter ... Use pupil area as proxy for diameter"

**Code** (convert_data.py:198-208):
```python
pupil_area = None
pupil_ts = None
likely_blink = None
try:
    pupil_tracking = f['acquisition']['EyeTracking']['pupil_tracking']
    pupil_area = pupil_tracking['area'][()]
    pupil_ts = pupil_tracking['timestamps'][()]
    likely_blink = f['acquisition']['EyeTracking']['likely_blink']['data'][()].astype(bool)
except (KeyError, Exception):
    print(f"  WARNING: No pupil tracking data in {experiment_id}")
```

**What this does:** Reads `acquisition/EyeTracking/pupil_tracking/area` (used as a proxy for diameter) along with its timestamps and the `likely_blink` boolean mask. If pupil tracking is missing, the experiment continues without pupil data.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `output` *Pupil diameter*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:215 "Pupil NaN handling: During blinks (likely_blink=True or NaN), linearly interpolate. Compute percentile bins from non-blink data."; CONVERSION_NOTES.md:241 "Pupil blinks (likely_blink=True) set to NaN and interpolated before resampling"

**Code** (convert_data.py:100-110, 327-342, 528-544, 615):
```python
def interpolate_nans(arr):
    nans = np.isnan(arr)
    if not nans.any():
        return arr.copy()
    if nans.all():
        return np.zeros_like(arr)
    result = arr.copy()
    x = np.arange(len(arr))
    result[nans] = np.interp(x[nans], x[~nans], arr[~nans])
    return result
...
pupil_area = raw_data['pupil_area'].copy().astype(float)
if likely_blink is not None:
    pupil_area[likely_blink] = np.nan
pupil_area = interpolate_nans(pupil_area)
pupil_resampled = np.interp(regular_ts, pupil_ts, pupil_area)
...
pupil_area[blink] = np.nan
valid_pupil = pupil_area[~np.isnan(pupil_area)]
...
pupil_bin_edges = compute_percentile_bins(all_pupil_cat, n_bins=5)
...
pupil_binned = digitize_to_bins(trial_data_out['pupil_area'], pupil_bin_edges)
```

**What this does:** Blink frames are set to NaN, NaNs are linearly interpolated (over sample-index, not time), then the cleaned trace is interpolated to the 30 Hz grid. Bin edges are computed globally from non-blink pupil values across all sessions, and per-trial values are digitized into 5 percentile bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-c. How is `output` *Pupil diameter* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:342, 354-385):
```python
pupil_resampled = np.interp(regular_ts, pupil_ts, pupil_area)
...
trial_mask = (regular_ts >= t_trial_start) & (regular_ts < t_trial_stop)
trial_time_indices = np.where(trial_mask)[0]
...
if pupil_resampled is not None:
    pupil_trial = pupil_resampled[trial_time_indices]
else:
    pupil_trial = np.full(n_tp, np.nan)
```

**What this does:** Pupil area is interpolated onto the same `regular_ts` 30 Hz grid as the neural data, then sliced with the same `trial_time_indices`. If pupil data is missing for an experiment, an all-NaN per-trial vector is used, which then maps to bin 0 during digitization.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `output` *Image name* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:201 "`stimulus_presentations.image_name` → output[0]: image_identity"; CONVERSION_NOTES.md:213 "Image identity during gray screen: Use the identity of the image that was just shown (last presented image)."; CONVERSION_NOTES.md:214 "Image identity for omitted flashes: Continue with previous image identity."

**Code** (convert_data.py:166-191, 233-262):
```python
stim = f['intervals'][stim_key]
stim_data = {
    'start_time': stim['start_time'][()],
    'stop_time': stim['stop_time'][()],
    'image_name': stim['image_name'][()],
    'is_change': stim['is_change'][()].astype(bool),
    'omitted': stim['omitted'][()],
}
...
def get_image_at_timepoints(timepoints, stim_data, all_image_names):
    n_tp = len(timepoints)
    image_idx = np.zeros(n_tp, dtype=np.int64)
    non_omitted = ~stim_data['omitted']
    stim_starts = stim_data['start_time'][non_omitted]
    stim_names = stim_data['image_name'][non_omitted]
    name_to_idx = {name: i for i, name in enumerate(all_image_names)}
    insert_idx = np.searchsorted(stim_starts, timepoints, side='right') - 1
    for i in range(n_tp):
        if insert_idx[i] >= 0:
            img_name = stim_names[insert_idx[i]]
            image_idx[i] = name_to_idx.get(img_name, 0)
        else:
            image_idx[i] = 0
    return image_idx
```

**What this does:** Image identity at each timepoint is the `image_name` of the most recent non-omitted stimulus presentation (from the NWB stimulus_presentations interval), found via `searchsorted` on stimulus start times. Omitted flashes carry forward the previous image; pre-first-stimulus timepoints get index 0.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `output` *Image name*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:238 "(1) collect global image names"; CONVERSION_NOTES.md:331 "Image identity classes | 16 (8 per image set, 2 image sets)"

**Code** (convert_data.py:489-513, 588-606):
```python
all_image_names_set = set()
for _, row in exp_table.iterrows():
    eid = row['ophys_experiment_id']
    nwb_path = NWB_DIR / f'behavior_ophys_experiment_{eid}.nwb'
    try:
        with h5py.File(nwb_path, 'r') as f:
            for k in f['intervals'].keys():
                if k != 'trials' and 'spontaneous' not in k.lower() and 'movie' not in k.lower():
                    img_names = f['intervals'][k]['image_name'][()]
                    if isinstance(img_names[0], bytes):
                        img_names = [x.decode() for x in img_names]
                    all_image_names_set.update([n for n in img_names if n != 'omitted'])
                    break
    except Exception as e:
        ...
global_image_names = sorted(all_image_names_set)
...
local_to_global = {}
for local_idx, name in enumerate(result['all_image_names']):
    if name in global_image_names:
        local_to_global[local_idx] = global_image_names.index(name)
    else:
        local_to_global[local_idx] = 0
...
img_id_global = np.array([local_to_global.get(v, 0) for v in trial_data_out['image_identity']], dtype=np.int64)
```

**What this does:** A global, sorted list of all unique non-omitted image names is built by scanning every NWB file in Pass 1. Each session's per-frame image identities are mapped (via local→global index) into the shared categorical space. The mapping yields ~16 classes across image sets A and B.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-c. How is `output` *Image name* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:365-372):
```python
trial_ts = regular_ts[trial_time_indices]
n_tp = len(trial_ts)
neural_trial = events_resampled[trial_time_indices, :].T.astype(np.float32)
image_idx = get_image_at_timepoints(trial_ts, raw_data['stim'], all_stim_images)
```

**What this does:** Image identity is computed per timepoint at the trial's `trial_ts` (the 30 Hz timestamps for that trial), so it is one image label per neural frame in the same trial slice.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `output` *Image change* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:201 "`trials.is_change` + stimulus timing → output[1]: image_change ... Binary 1 at change timepoint, 0 otherwise, time-varying ... 1 for one 750ms window at change"; CONVERSION_NOTES.md:243 "Image change signal: 1 during 750ms window starting at change onset"

**Code** (convert_data.py:265-285):
```python
def get_image_change_at_timepoints(timepoints, stim_data):
    n_tp = len(timepoints)
    change_signal = np.zeros(n_tp, dtype=np.int64)
    change_mask = stim_data['is_change'] & ~stim_data['omitted']
    change_starts = stim_data['start_time'][change_mask]
    change_stops = stim_data['stop_time'][change_mask]
    for cs, ce in zip(change_starts, change_stops):
        # Mark the full image interval (stimulus + gray) as change
        # Use 750ms window from change start
        mask = (timepoints >= cs) & (timepoints < cs + 0.75)
        change_signal[mask] = 1
    return change_signal
```

**What this does:** Image change is derived from the stimulus_presentations table, taking presentations where `is_change=True` and `omitted=False`. For each such presentation, a 750 ms window starting at its `start_time` is marked 1 (covering the 250 ms image flash plus 500 ms gray). Catch-trial sham changes are excluded because the stim table's `is_change` flag only fires on real changes.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `output` *Image change*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:374-375, 609):
```python
change_signal = get_image_change_at_timepoints(trial_ts, raw_data['stim'])
...
img_change = trial_data_out['image_change'].astype(np.int64)
```

**What this does:** No further processing beyond the binary windowing in `get_image_change_at_timepoints`. The result is cast to int64 and stored as the image_change output channel.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-c. How is `output` *Image change* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:365-375):
```python
trial_ts = regular_ts[trial_time_indices]
n_tp = len(trial_ts)
neural_trial = events_resampled[trial_time_indices, :].T.astype(np.float32)
image_idx = get_image_at_timepoints(trial_ts, raw_data['stim'], all_stim_images)
change_signal = get_image_change_at_timepoints(trial_ts, raw_data['stim'])
```

**What this does:** Computed at the same per-trial 30 Hz timestamps used for neural data, so frame indices match exactly within the trial slice.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:204 "`trials.hit/miss/false_alarm/correct_reject` → output[4]: trial_outcome | Static per-trial categorical | 4 classes"

**Code** (convert_data.py:148-156, 387-396):
```python
trials = {
    ...
    'hit': trials_grp['hit'][()].astype(bool),
    'miss': trials_grp['miss'][()].astype(bool),
    'false_alarm': trials_grp['false_alarm'][()].astype(bool),
    'correct_reject': trials_grp['correct_reject'][()].astype(bool),
    ...
}
...
if trials['hit'][trial_idx]:
    outcome = 0  # hit
elif trials['miss'][trial_idx]:
    outcome = 1  # miss
elif trials['false_alarm'][trial_idx]:
    outcome = 2  # false_alarm
elif trials['correct_reject'][trial_idx]:
    outcome = 3  # correct_reject
else:
    continue  # Unknown outcome, skip
```

**What this does:** Trial outcome is read from the four boolean columns of the NWB trials table (`hit`, `miss`, `false_alarm`, `correct_reject`) and mapped to integers 0–3. Trials with none of the four flags set are skipped.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:618, 625-630, 669):
```python
trial_outcome = np.array([trial_data_out['trial_outcome']], dtype=np.int64)
...
output_tv = np.stack([img_id_global, img_change, running_binned, pupil_binned], axis=0)
outcome_broadcast = np.full((1, n_tp), trial_data_out['trial_outcome'], dtype=np.int64)
output_combined = np.concatenate([output_tv, outcome_broadcast], axis=0)
...
['hit', 'miss', 'false_alarm', 'correct_reject'],  # trial outcomes
```

**What this does:** Trial outcome integer (0–3) is broadcast to a constant value across all trial timepoints, producing a `(1, n_tp)` row that is concatenated with the time-varying outputs. The label vocabulary is stored in `output_values` as `['hit', 'miss', 'false_alarm', 'correct_reject']`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-c. How is `output` *Trial outcome* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:625-630):
```python
output_tv = np.stack([img_id_global, img_change, running_binned, pupil_binned], axis=0)  # (4, n_tp)
outcome_broadcast = np.full((1, n_tp), trial_data_out['trial_outcome'], dtype=np.int64)
output_combined = np.concatenate([output_tv, outcome_broadcast], axis=0)  # (5, n_tp)
```

**What this does:** Trial outcome is a per-trial constant tiled across all `n_tp` timepoints of the trial, so its shape and frame indexing match the neural data; the actual outcome value does not change within a trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:215 "Pupil NaN handling: During blinks ... linearly interpolate."; CONVERSION_NOTES.md:241 "Pupil blinks (likely_blink=True) set to NaN and interpolated before resampling"

**Code** (convert_data.py:122-132, 167-176, 198-208, 224-226, 305-307, 362-363, 396, 408-410, 535-538):
```python
try:
    with h5py.File(nwb_path, 'r') as f:
        ...
        n_valid = valid_roi.sum()
        if n_valid == 0:
            print(f"  WARNING: No valid ROIs in experiment {experiment_id}, skipping")
            return None
        ...
        if stim_key is None:
            print(f"  WARNING: No stimulus presentations found in {experiment_id}, skipping")
            return None
        ...
        try:
            pupil_tracking = f['acquisition']['EyeTracking']['pupil_tracking']
            ...
        except (KeyError, Exception):
            print(f"  WARNING: No pupil tracking data in {experiment_id}")
except Exception as e:
    print(f"  ERROR loading {experiment_id}: {e}")
    return None
...
if len(valid_indices) < 2:
    return None
...
if len(trial_time_indices) < 3:
    continue
...
else:
    continue  # Unknown outcome, skip
...
if len(neural_trials) < 2:
    return None
```

Also `digitize_to_bins` maps NaN values to bin 0 (lines 96-97).

**What this does:** Loading and per-experiment processing are wrapped in try/except so any failure skips the experiment with a warning. Missing components (no valid ROIs, no stim table, no pupil) are gracefully skipped or substituted with NaN. Trials shorter than 3 frames or without an outcome are dropped. Sessions with fewer than 2 valid trials are dropped. Pupil blinks are NaN-filled then linearly interpolated; remaining NaNs after digitization map to bin 0. Events resampled below zero are clipped to 0.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:282-288 "Load ~0.25s/session ~50s total; Process ~0.25s/session ~50s total; Total ~0.5s/session ~2 min"; CONVERSION_NOTES.md:319 "Conversion time: 6 minutes (358s)"

From `conversion_full_out.txt`:
> "Total conversion time: 358.2s (6.0 min)"; per-experiment lines like "Loaded in 0.2s, processed in 0.3s, total 0.5s" (CAM2P) and up to "Loaded in 2.9s, processed in 1.7s, total 4.7s" for multi-plane (MESO) experiments; "Saved 8325.7 MB in 9.1s".

**Code** (convert_data.py:561-580, 850-855):
```python
t0 = time.time()
print(f"\n[{idx+1}/{len(exp_table)}] Processing experiment {eid}...", flush=True)
raw_data = load_experiment_data(nwb_path, eid)
...
t_load = time.time() - t0
...
result = process_single_experiment(raw_data, exp_meta)
...
t_process = time.time() - t0 - t_load
...
with open(args.output, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** Code instruments per-experiment load and process times. From the run log, NWB loading dominates for MESO multi-plane experiments (2-3s each); single-plane CAM2P loads in ~0.2s. Total conversion was 358s across 202 experiments, plus 9.1s pickling an 8.3 GB output file. Pass 1 (image-name scan) and Pass 2 (running/pupil collection) also re-open every NWB file.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:244-250 "Code inefficiencies identified: Sequential processing of experiments (could parallelize); Multiple passes over NWB files. Code speedups added: Vectorized interpolation using np.interp; Efficient searchsorted for image identity assignment"

**Code** (convert_data.py:60-64, 255-262, 279-283):
```python
# interpolate_to_regular_grid: per-channel python loop
for i in range(data.shape[1]):
    result[:, i] = np.interp(target_timestamps, timestamps, data[:, i])
...
# get_image_at_timepoints: per-timepoint loop (after vectorized searchsorted)
for i in range(n_tp):
    if insert_idx[i] >= 0:
        img_name = stim_names[insert_idx[i]]
        image_idx[i] = name_to_idx.get(img_name, 0)
    else:
        image_idx[i] = 0
...
# get_image_change_at_timepoints: per-change-event loop
for cs, ce in zip(change_starts, change_stops):
    mask = (timepoints >= cs) & (timepoints < cs + 0.75)
    change_signal[mask] = 1
```

Also `from concurrent.futures import ProcessPoolExecutor, as_completed` is imported (line 19) but never actually used; experiments are processed sequentially.

**What this does:** Several inner loops are present that could be vectorized: the per-cell `np.interp` loop in `interpolate_to_regular_grid`, the per-timepoint dict lookup in `get_image_at_timepoints` (could be `stim_names[insert_idx]` then a vector map), and the per-change-event mask in `get_image_change_at_timepoints`. The main per-experiment loop is also serial despite the futures import.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:238 "3-pass approach: (1) collect global image names, (2) compute global percentile bins for running/pupil, (3) process experiments"; CONVERSION_NOTES.md:245 "Multiple passes over NWB files"

**Code** (convert_data.py:493-548, 557-565):
```python
# Pass 1: open every NWB file just for image names
for _, row in exp_table.iterrows():
    eid = row['ophys_experiment_id']
    nwb_path = NWB_DIR / f'behavior_ophys_experiment_{eid}.nwb'
    try:
        with h5py.File(nwb_path, 'r') as f:
            ...
            img_names = f['intervals'][k]['image_name'][()]

# Pass 2: open every NWB file just for running speed + pupil area
for idx, (_, row) in enumerate(exp_table.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = NWB_DIR / f'behavior_ophys_experiment_{eid}.nwb'
    try:
        with h5py.File(nwb_path, 'r') as f:
            running = f['processing']['running']['speed']['data'][()]
            ...
            pupil_area = f['acquisition']['EyeTracking']['pupil_tracking']['area'][()].astype(float)

# Pass 3: open every NWB file again to extract everything
for idx, (_, row) in enumerate(exp_table.iterrows()):
    ...
    raw_data = load_experiment_data(nwb_path, eid)
```

**What this does:** Each NWB file is opened three separate times — once to collect image names, once to collect running/pupil values for global percentile bins, and once for full per-experiment processing. Running speed and pupil arrays are read in both Pass 2 and Pass 3.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:124-129, 142-164):
```python
cell_table = f['processing']['ophys']['image_segmentation']['cell_specimen_table']
valid_roi = cell_table['valid_roi'][()].astype(bool)
cell_specimen_ids = cell_table['cell_specimen_id'][()]
...
trials = {
    'start_time': trials_grp['start_time'][()],
    'stop_time': trials_grp['stop_time'][()],
    'change_time': trials_grp['change_time'][()],
    'go': trials_grp['go'][()].astype(bool),
    'catch': trials_grp['catch'][()].astype(bool),
    'aborted': trials_grp['aborted'][()].astype(bool),
    'auto_rewarded': trials_grp['auto_rewarded'][()].astype(bool),
    ...
    'is_change': trials_grp['is_change'][()].astype(bool),
    'initial_image_name': trials_grp['initial_image_name'][()],
    'change_image_name': trials_grp['change_image_name'][()],
}
```

And (convert_data.py:209-223):
```python
return {
    ...
    'cell_specimen_ids': cell_specimen_ids[valid_roi],
    ...
}
```

**What this does:** A few raw fields are loaded but never used downstream: `cell_specimen_ids` are returned in `raw_data` but never written into the output pickle; `change_time`, `is_change`, `initial_image_name`, and `change_image_name` from the trials table are loaded but the image-change signal is computed from the stim_presentations table instead, so these per-trial fields go unused.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:540-548, 595-633):
```python
all_running_cat = np.concatenate(all_running_values) if all_running_values else np.array([0.0])
all_pupil_cat = np.concatenate(all_pupil_values) if all_pupil_values else np.array([0.0])

running_bin_edges = compute_percentile_bins(all_running_cat, n_bins=5)
pupil_bin_edges = compute_percentile_bins(all_pupil_cat, n_bins=5)
...
del all_running_values, all_pupil_values, all_running_cat, all_pupil_cat
...
session_neural = []
session_output = []
session_input = []
...
for trial_data_neural, trial_data_out in zip(result['neural_trials'], result['output_trials']):
    n_tp = trial_data_neural.shape[1]
    session_neural.append(trial_data_neural)
    ...
all_neural.append(session_neural)
```

**What this does:** After computing global percentile bin edges, the bulk Pass-2 arrays (`all_running_values`, `all_pupil_values`, and their concatenations) are explicitly `del`'d. Per-experiment, the full session arrays go out of scope after the function returns; only per-trial slices are appended to the global lists. Neural per-trial arrays are cast to `float32` and outputs to `int64`, but no other explicit memory tuning is done; the final pickle is 8.3 GB.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
