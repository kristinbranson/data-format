# allen2p — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/allen2p/claude-code/2026-03-26__07-49-34_trial1`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:227-234 — "Loads NWB files directly via h5py (fast, no AllenSDK overhead). Filters to active sessions (excludes passive). Filters trials to Go+Catch, excluding Aborted and Auto-rewarded."

**Code** (convert_data.py:41-61, 64-67, 304-314):
```python
def load_experiment_table():
    exp_table = pd.read_csv(os.path.join(METADATA_DIR, 'ophys_experiment_table.csv'))
    nwb_files = glob.glob(os.path.join(NWB_DIR, '*.nwb'))
    downloaded_ids = set()
    for f in nwb_files:
        eid = int(os.path.basename(f).replace('behavior_ophys_experiment_', '').replace('.nwb', ''))
        downloaded_ids.add(eid)
    exp_table = exp_table[exp_table['ophys_experiment_id'].isin(downloaded_ids)].copy()
    exp_table = exp_table[~exp_table['session_type'].str.contains('passive', case=False)].copy()
    exp_table = exp_table.sort_values('ophys_experiment_id').reset_index(drop=True)
    return exp_table

def load_nwb_data(nwb_path):
    with h5py.File(nwb_path, 'r') as f:
        ...

nwb_path = os.path.join(NWB_DIR, f'behavior_ophys_experiment_{exp_id}.nwb')
nwb_data = load_nwb_data(nwb_path)
```

**What this does:** Reads the `ophys_experiment_table.csv` from the local metadata directory, intersects with NWB files actually present on disk, then drops "passive" session types. Each remaining experiment is loaded by opening its NWB file directly with h5py (rather than via the AllenSDK).

**Rating:** ok

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:198 — "`mouse_id` | `subjects`, `subject_idx` | Map unique mice to indices"

**Code** (convert_data.py:441, 664-668, 727-728):
```python
mouse_id = str(exp_row['mouse_id'])
...
mouse_id = result['mouse_id']
if mouse_id not in subject_map:
    subject_map[mouse_id] = len(all_subjects)
    all_subjects.append(mouse_id)
...
'subjects': all_subjects,
'subject_idx': np.array(all_subject_idx, dtype=np.int64),
```

**What this does:** Subjects are identified by the `mouse_id` field in the experiment table. As experiments are processed, each new `mouse_id` is appended to `all_subjects` and assigned an index in `subject_map`; per-experiment subject indices are stored in `subject_idx`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:210 — "Multiscope handling: Each experiment (plane) is a separate 'session' in the output, since they have different neurons but share the same behavioral data."

**Code** (convert_data.py:644-654, 688-699):
```python
for idx, (_, row) in enumerate(exp_table.iterrows()):
    exp_id = row['ophys_experiment_id']
    ...
    result = process_experiment(
        exp_id, row, image_names_list, outcome_names,
        show_processing=args.show_processing
    )
    ...
session_metadata.append({
    'exp_id': result['exp_id'],
    'ophys_session_id': result['ophys_session_id'],
    'session_type': result['session_type'],
    ...
})
```

**What this does:** Each row of the experiment table (one `ophys_experiment_id`, i.e. one imaging plane) is treated as a separate session in the output. The original `ophys_session_id` is recorded only in the per-session metadata dict, not used for grouping.

**Rating:** incorrect

**Note:** did not combine "experiment id" based on "session id"

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:204 — "Trial definition: Use `start_time` and `stop_time` from trials table for Go and Catch trials only."

**Code** (convert_data.py:139-147, 374-387):
```python
def get_valid_trials(trial_data):
    go = trial_data['go'].astype(bool)
    catch = trial_data['catch'].astype(bool)
    aborted = trial_data['aborted'].astype(bool)
    auto_rewarded = trial_data['auto_rewarded'].astype(bool)
    valid = (go | catch) & ~aborted & ~auto_rewarded
    return np.where(valid)[0]

for trial_idx in valid_trial_idx:
    t_start = trial_data['start_time'][trial_idx]
    t_stop = trial_data['stop_time'][trial_idx]
    frame_mask = (ophys_ts >= t_start) & (ophys_ts < t_stop)
    trial_ts = ophys_ts[frame_mask]
    n_trial_frames = frame_mask.sum()
    if n_trial_frames < 2:
        continue
    neural = dff[:, frame_mask].astype(np.float32)
```

**What this does:** Trials come from the NWB `intervals/trials` table. Valid trials are those flagged as `go` or `catch` and not `aborted` or `auto_rewarded`. For each valid trial, ophys frames between `start_time` and `stop_time` are extracted as the trial window (variable length).

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:144-147 — "Include: Go trials and Catch trials. Exclude: Aborted trials and Auto-rewarded trials."
> CONVERSION_NOTES.md:354 — "Sessions with very few valid trials (e.g., 39) are retained if >=2 trials"

**Code** (convert_data.py:139-147, 333-337, 383-384, 435-437):
```python
valid = (go | catch) & ~aborted & ~auto_rewarded
...
valid_trial_idx = get_valid_trials(trial_data)
if len(valid_trial_idx) < 2:
    print(f"  WARNING: Only {len(valid_trial_idx)} valid trials in experiment {exp_id}")
    return None
...
if n_trial_frames < 2:
    continue
...
if len(neural_trials) < 2:
    print(f"  WARNING: Only {len(neural_trials)} valid trials after processing for experiment {exp_id}")
    return None
```

**What this does:** Filters out aborted and auto-rewarded trials at trial level. Skips trials whose ophys window contains fewer than 2 frames. Drops the entire experiment if fewer than 2 valid trials remain (both before and after processing).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:202 — "Neural data: Use dF/F traces (not events/deconvolved). dF/F is the standard calcium imaging signal."
> CONVERSION_NOTES.md:71 — "Neural: `processing/ophys/dff/traces/data` (n_frames x n_cells)"

**Code** (convert_data.py:69-73, 317-318, 387):
```python
data['ophys_timestamps'] = f['processing']['ophys']['dff']['traces']['timestamps'][:]
dff_raw = f['processing']['ophys']['dff']['traces']['data'][:]
data['dff_traces'] = dff_raw.T  # (n_cells, n_frames)
...
ophys_ts = nwb_data['ophys_timestamps']
dff = nwb_data['dff_traces']  # (n_cells, n_frames)
...
neural = dff[:, frame_mask].astype(np.float32)
```

**What this does:** Neural data is the pre-computed dF/F traces from `processing/ophys/dff/traces/data` in each NWB file, transposed to `(n_cells, n_frames)`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:340 — "dF/F computation | Pre-computed in NWB | Pre-computed (600s median filter + detrending)"

**Code** (convert_data.py:69-73, 387):
```python
dff_raw = f['processing']['ophys']['dff']['traces']['data'][:]
data['dff_traces'] = dff_raw.T  # (n_cells, n_frames)
...
neural = dff[:, frame_mask].astype(np.float32)
```

**What this does:** No additional processing is applied to the dF/F values beyond loading, transposing to `(n_cells, n_frames)`, casting to float32, and slicing the trial-window frames.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:337 — "ROI filtering | No explicit valid_roi filter | exclude_invalid_rois=True (default) | OK - all ROIs in downloaded NWB files are valid"

**Code** (convert_data.py:319-323):
```python
n_cells, n_frames = dff.shape
if n_cells == 0:
    print(f"  WARNING: No cells in experiment {exp_id}")
    return None
```

**What this does:** No explicit ROI/QC filtering is applied; the script relies on the NWB files (which the SDK exports with `exclude_invalid_rois=True`). The only check is that the experiment has at least 1 cell.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:203 — "Time bin: Use native ophys timestamps (~31 Hz for Scientifica, ~11 Hz for Multiscope). Each session's time bin is consistent within itself."

**Code** (convert_data.py:372, 379-380, 387, 710-711, 736):
```python
dt = np.median(np.diff(ophys_ts))  # time bin size
...
frame_mask = (ophys_ts >= t_start) & (ophys_ts < t_stop)
trial_ts = ophys_ts[frame_mask]
...
neural = dff[:, frame_mask].astype(np.float32)
...
all_dts = [m['dt_ms'] for m in session_metadata]
median_dt = np.median(all_dts)
...
'time_bin_size': median_dt,
```

**What this does:** Neural data is kept at the native ophys frame rate; no resampling. Per-session bin size is `np.median(np.diff(ophys_ts))`, and the global `time_bin_size` reported in metadata is the median across sessions (~32.3 ms).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:205 — "Temporal alignment: Align to ophys timestamps. For each trial, extract the ophys frames between trial start_time and stop_time."

**Code** (convert_data.py:374-387, 737):
```python
for trial_idx in valid_trial_idx:
    t_start = trial_data['start_time'][trial_idx]
    t_stop = trial_data['stop_time'][trial_idx]
    frame_mask = (ophys_ts >= t_start) & (ophys_ts < t_stop)
    trial_ts = ophys_ts[frame_mask]
    n_trial_frames = frame_mask.sum()
    if n_trial_frames < 2:
        continue
    neural = dff[:, frame_mask].astype(np.float32)
...
'temporal_alignment_event': 'Aligned to ophys (2-photon imaging) timestamps. Each trial spans from trial start_time to stop_time.',
```

**What this does:** Each trial's neural slice is the dF/F columns whose ophys timestamps fall in `[start_time, stop_time)` of the trial. Alignment is to the trial start, with a variable-length window per trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `output` *Image identity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:76 — "Stimulus: `intervals/Natural_Images_*_presentations` (image_name, is_change, omitted, start_time, stop_time)"
> CONVERSION_NOTES.md:206 — "Image identity: Map stimulus presentations to ophys timepoints. During gray screen (ISI), use a 'gray' category."

**Code** (convert_data.py:111-134, 164-214):
```python
stim_key = None
for key in f['intervals'].keys():
    if 'Natural_Images' in key or 'natural_images' in key:
        stim_key = key
        break
...
stim = f['intervals'][stim_key]
stim_data = {}
for key in ['start_time', 'stop_time', 'image_name', 'is_change', 'omitted']:
    if key in stim:
        stim_data[key] = stim[key][:]
data['stimulus'] = stim_data
...
def build_image_identity_trace(ophys_ts, stim_data, trial_start, trial_stop, image_names_list):
    ...
    gray_idx = image_names_list.index(GRAY_LABEL)
    trace = np.full(n_frames, gray_idx, dtype=np.int64)
    stim_starts = stim_data['start_time']
    stim_stops = stim_data['stop_time']
    stim_names = stim_data['image_name']
    for si in range(len(stim_starts)):
        ...
        if name == 'omitted':
            continue
        if name in image_names_list:
            img_idx = image_names_list.index(name)
        ...
        frame_mask = (trial_ts >= s_start) & (trial_ts < s_stop)
        trace[frame_mask] = img_idx
```

**What this does:** Image identity comes from the stimulus presentations interval (`Natural_Images_*_presentations`), specifically the `image_name`, `start_time`, and `stop_time` columns (with `omitted` flashes treated as gray). Trial-level `initial_image_name`/`change_image_name` are loaded but not used to build the trace.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `output` *Image identity*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:192 — "Map to categorical integer, time-varying at ophys rate. 8 images + gray screen."

**Code** (convert_data.py:473-493, 605-611, 178-212):
```python
def get_all_image_names(exp_table):
    all_names = set()
    for _, row in exp_table.iterrows():
        ...
        with h5py.File(nwb_path, 'r') as f:
            for key in f['intervals'].keys():
                if 'Natural_Images' in key or 'natural_images' in key:
                    names = f['intervals'][key]['image_name'][:]
                    for n in names:
                        ...
                        if n != 'omitted':
                            all_names.add(n)
    return sorted(all_names)
...
all_image_names = get_all_image_names(exp_table)
image_names_list = [GRAY_LABEL] + all_image_names
...
gray_idx = image_names_list.index(GRAY_LABEL)
trace = np.full(n_frames, gray_idx, dtype=np.int64)
...
img_idx = image_names_list.index(name)
...
frame_mask = (trial_ts >= s_start) & (trial_ts < s_stop)
trace[frame_mask] = img_idx
```

**What this does:** A global sorted image-name list is built across all experiments, prefixed with a `'gray'` label. For each trial, a per-frame integer trace is initialized to the gray index, and frames falling within each presentation interval are overwritten with that presentation's image index. Omitted flashes are left as gray.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `output` *Image identity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none specifically; alignment via shared ophys timestamps is implied)

**Code** (convert_data.py:171-172, 210-212, 389-392):
```python
trial_mask = (ophys_ts >= trial_start) & (ophys_ts < trial_stop)
trial_ts = ophys_ts[trial_mask]
...
frame_mask = (trial_ts >= s_start) & (trial_ts < s_stop)
trace[frame_mask] = img_idx
...
img_trace, _ = build_image_identity_trace(
    ophys_ts, stim_data, t_start, t_stop, image_names_list
)
```

**What this does:** The image-identity trace is built on the same set of ophys frames inside `[trial_start, trial_stop)` that the neural slice uses, so each frame of `output[0]` corresponds to the same ophys frame as the matching column of `neural`.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Image change* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:193 — "`is_change` from stimulus presentations | `output[1]`: image_change | Binary, 1 at change onset frame, 0 otherwise"

**Code** (convert_data.py:217-244):
```python
def build_image_change_trace(ophys_ts, stim_data, trial_start, trial_stop):
    trial_mask = (ophys_ts >= trial_start) & (ophys_ts < trial_stop)
    trial_ts = ophys_ts[trial_mask]
    n_frames = len(trial_ts)
    if n_frames == 0:
        return np.array([], dtype=np.int64)
    trace = np.zeros(n_frames, dtype=np.int64)
    stim_starts = stim_data['start_time']
    is_change = stim_data['is_change']
    for si in range(len(stim_starts)):
        if not is_change[si]:
            continue
        s_start = stim_starts[si]
        if s_start < trial_start or s_start >= trial_stop:
            continue
        frame_idx = np.searchsorted(trial_ts, s_start)
        if frame_idx < n_frames:
            trace[frame_idx] = 1
    return trace
```

**What this does:** `image_change` is derived from the `is_change` and `start_time` columns of the stimulus presentations table. Trial-level `change_time` and `go` columns are not used.

**Rating:** ok

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Image change*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:193 — "Binary, 1 at change onset frame, 0 otherwise"

**Code** (convert_data.py:226-244, 394-395):
```python
trace = np.zeros(n_frames, dtype=np.int64)
...
for si in range(len(stim_starts)):
    if not is_change[si]:
        continue
    s_start = stim_starts[si]
    if s_start < trial_start or s_start >= trial_stop:
        continue
    frame_idx = np.searchsorted(trial_ts, s_start)
    if frame_idx < n_frames:
        trace[frame_idx] = 1
...
change_trace = build_image_change_trace(ophys_ts, stim_data, t_start, t_stop)
```

**What this does:** A zero trace is initialized over the trial's ophys frames. For each stimulus presentation flagged `is_change`, the single ophys frame at or after its `start_time` (via `np.searchsorted`) is set to 1. The "1" is one ophys frame wide, not a 750 ms window.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Image change* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — same alignment scheme as image identity)

**Code** (convert_data.py:219-220, 240-242):
```python
trial_mask = (ophys_ts >= trial_start) & (ophys_ts < trial_stop)
trial_ts = ophys_ts[trial_mask]
...
frame_idx = np.searchsorted(trial_ts, s_start)
if frame_idx < n_frames:
    trace[frame_idx] = 1
```

**What this does:** The change trace is built on the same trial-window ophys frames used for the neural slice; `np.searchsorted(trial_ts, s_start)` places each change at the matching ophys frame index, so it shares per-frame alignment with the neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *Running speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:72 — "Running: `processing/running/speed` (270K samples @ 60 Hz)"
> CONVERSION_NOTES.md:194 — "`running_speed` | `output[2]`: running_speed_bin"

**Code** (convert_data.py:85-86, 341-343):
```python
data['running_timestamps'] = f['processing']['running']['speed']['timestamps'][:]
data['running_speed'] = f['processing']['running']['speed']['data'][:]
...
running_at_ophys = interpolate_to_ophys(
    nwb_data['running_speed'], nwb_data['running_timestamps'], ophys_ts
)
```

**What this does:** Running speed is read directly from `processing/running/speed/data` (with companion timestamps) in each NWB file.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *Running speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:209 — "Percentile bins for running/pupil: Compute percentiles across the entire session (all valid timepoints), then apply per-trial. Use 5 equal bins (0-20th, 20-40th, ..., 80-100th percentile)."

**Code** (convert_data.py:247-254, 281-301, 341-343, 365, 398-399):
```python
def interpolate_to_ophys(signal, signal_ts, ophys_ts_trial):
    ...
    f = interpolate.interp1d(signal_ts, signal, kind='linear',
                             bounds_error=False, fill_value=np.nan)
    return f(ophys_ts_trial)

def compute_session_percentile_edges(values, n_bins=5):
    ...
    percentiles = np.linspace(0, 100, n_bins + 1)
    edges = np.percentile(valid, percentiles)
    edges[0] = -np.inf
    edges[-1] = np.inf
    return edges

def apply_percentile_bins(values, edges, n_bins=5):
    ...
    result[valid] = np.clip(np.digitize(values[valid], edges[1:-1]), 0, n_bins - 1)
    result[~valid] = 0
    return result

running_at_ophys = interpolate_to_ophys(
    nwb_data['running_speed'], nwb_data['running_timestamps'], ophys_ts
)
running_edges = compute_session_percentile_edges(running_at_ophys, n_bins=5)
...
running_binned = apply_percentile_bins(running_trial, running_edges, n_bins=5)
```

**What this does:** Running speed is linearly interpolated from its native (~60 Hz) timebase to the ophys timestamps, then discretized into 5 percentile bins. Bin edges are computed per session (not globally across sessions). NaNs map to bin 0.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `output` *Running speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:208 — "Running speed: Interpolate from 60 Hz to ophys timestamps using linear interpolation."

**Code** (convert_data.py:341-343, 379, 398-399):
```python
running_at_ophys = interpolate_to_ophys(
    nwb_data['running_speed'], nwb_data['running_timestamps'], ophys_ts
)
...
frame_mask = (ophys_ts >= t_start) & (ophys_ts < t_stop)
...
running_trial = running_at_ophys[frame_mask]
running_binned = apply_percentile_bins(running_trial, running_edges, n_bins=5)
```

**What this does:** Running speed is interpolated session-wide onto the ophys timestamps once, then sliced with the same `frame_mask` used for the neural data, guaranteeing per-frame alignment with the neural trial window.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `output` *Pupil diameter* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:73-74 — "Eye tracking: `acquisition/EyeTracking/pupil_tracking` (area, height, width @ 30 Hz). Blinks: `acquisition/EyeTracking/likely_blink`"
> CONVERSION_NOTES.md:207 — "Pupil diameter: Compute from pupil area as `2*sqrt(area/pi)`."

**Code** (convert_data.py:88-99):
```python
if 'EyeTracking' in f.get('acquisition', {}):
    et = f['acquisition']['EyeTracking']
    if 'pupil_tracking' in et:
        pt = et['pupil_tracking']
        data['pupil_area'] = pt['area']['data'][:] if 'data' in pt['area'] else pt['area'][:]
        data['pupil_timestamps'] = pt['timestamps'][:]
        data['likely_blink'] = et['likely_blink']['data'][:]
    else:
        data['pupil_area'] = None
else:
    data['pupil_area'] = None
```

**What this does:** Pupil diameter is derived from the pupil `area` field of `acquisition/EyeTracking/pupil_tracking` (with timestamps), plus `likely_blink` flags. There is no use of `pupil_width` directly.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `output` *Pupil diameter*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:207 — "Compute diameter from area as `2*sqrt(area/pi)`. Set blink frames to NaN, then interpolate. Discretize non-NaN values."

**Code** (convert_data.py:346-366, 402-403):
```python
if nwb_data['pupil_area'] is not None:
    pupil_area = nwb_data['pupil_area'].copy()
    likely_blink = nwb_data['likely_blink']
    pupil_ts = nwb_data['pupil_timestamps']
    pupil_area[likely_blink] = np.nan
    pupil_diameter = np.full_like(pupil_area, np.nan)
    valid_pupil = ~np.isnan(pupil_area) & (pupil_area > 0)
    pupil_diameter[valid_pupil] = 2.0 * np.sqrt(pupil_area[valid_pupil] / np.pi)
    pupil_at_ophys = interpolate_to_ophys(pupil_diameter, pupil_ts, ophys_ts)
else:
    pupil_at_ophys = np.full(len(ophys_ts), np.nan)
...
pupil_edges = compute_session_percentile_edges(pupil_at_ophys, n_bins=5)
...
pupil_binned = apply_percentile_bins(pupil_trial, pupil_edges, n_bins=5)
```

**What this does:** Blink frames are masked to NaN in the pupil area trace. Diameter is computed as `2*sqrt(area/pi)` for valid samples. The diameter is linearly interpolated onto the ophys timestamps and discretized into 5 per-session percentile bins, with NaNs mapped to bin 0.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. How is `output` *Pupil diameter* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — same approach as running speed; not separately documented)

**Code** (convert_data.py:360, 402-403):
```python
pupil_at_ophys = interpolate_to_ophys(pupil_diameter, pupil_ts, ophys_ts)
...
pupil_trial = pupil_at_ophys[frame_mask]
pupil_binned = apply_percentile_bins(pupil_trial, pupil_edges, n_bins=5)
```

**What this does:** Pupil diameter is interpolated session-wide to the ophys timestamps, then sliced by the same `frame_mask` used for the neural data, giving per-frame alignment within each trial window.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:196 — "Trial outcome (hit/miss/FA/CR) | `output[4]`: trial_outcome | Categorical, static per trial | 4 categories"

**Code** (convert_data.py:150-161):
```python
def get_trial_outcome(trial_data, idx):
    if trial_data['hit'][idx]:
        return 'hit'
    elif trial_data['miss'][idx]:
        return 'miss'
    elif trial_data['false_alarm'][idx]:
        return 'false_alarm'
    elif trial_data['correct_reject'][idx]:
        return 'correct_reject'
    else:
        return 'unknown'
```

**What this does:** Trial outcome is derived from the four boolean columns `hit`, `miss`, `false_alarm`, `correct_reject` in the trials table, checked in that order with an `'unknown'` fallback.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:615 — "outcome_names = ['hit', 'miss', 'false_alarm', 'correct_reject']"

**Code** (convert_data.py:405-407, 423-428, 615):
```python
outcome = get_trial_outcome(trial_data, trial_idx)
outcome_idx = outcome_names.index(outcome) if outcome in outcome_names else 0
...
output_full = np.zeros((5, n_trial_frames), dtype=np.int64)
output_full[0] = img_trace
output_full[1] = change_trace
output_full[2] = running_binned
output_full[3] = pupil_binned
output_full[4] = outcome_idx  # broadcast scalar to all timepoints
...
outcome_names = ['hit', 'miss', 'false_alarm', 'correct_reject']
```

**What this does:** The string outcome is mapped to an integer index via the fixed list `['hit','miss','false_alarm','correct_reject']` (unknown falls back to 0 = hit). This per-trial scalar is broadcast across all time bins of the trial as row 4 of the `(5, T)` output array.

**Rating:** match

**Note:** _(no note)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:354-356 — "Sessions with very few valid trials (e.g., 39) are retained if >=2 trials. NaN pupil values (blinks) mapped to bin 0 - design choice, not bug (5 bins specified)"

**Code** (convert_data.py:96-99, 274-277, 309-311, 321-323, 328-330, 335-337, 383-384, 435-437, 487-491):
```python
if 'pupil_tracking' in et: ...
else: data['pupil_area'] = None
...
result[valid] = np.clip(np.digitize(values[valid], bin_edges[1:-1]), 0, n_bins - 1)
result[~valid] = 0  # NaN gets bin 0
...
if not os.path.exists(nwb_path):
    print(f"  WARNING: NWB file not found for experiment {exp_id}")
    return None
...
if n_cells == 0: return None
...
if stim_data is None: return None
...
if len(valid_trial_idx) < 2: return None
...
if n_trial_frames < 2: continue
...
if len(neural_trials) < 2: return None
...
try: ...
except Exception as e:
    print(f"  WARNING: Could not read images from {eid}: {e}")
```

**What this does:** Missing pupil data falls through to an all-NaN array (later mapped to bin 0). NaN behavioral samples discretize to bin 0. Missing NWB files, zero-cell experiments, missing stimulus, fewer than 2 valid trials, and degenerate trial windows are skipped with warnings. Image-name scanning is wrapped in try/except.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:251-258 — "Load NWB | ~1.7s/session | ~340s. Process trials | ~0.4s/session | ~80s. Total | ~3.7s | ~750s. Image name collection adds ~14s overhead."
> conversion_full_out.txt — per-experiment lines like "Time: 2.2s (load=1.7s, process=0.5s)"; image-name collection "Time: 14.4s".

**Code** (convert_data.py:306-307, 314-315, 433):
```python
t0 = time.time()
...
nwb_data = load_nwb_data(nwb_path)
t_load = time.time() - t0
...
t_process = time.time() - t0 - t_load
```

**What this does:** The script self-times each experiment with separate `t_load` (NWB read) and `t_process` (trial extraction) timers. In the full-run log, `t_load` (~1.5–3.4 s per experiment) dominates `t_process` (~0.5–1.1 s); the one-off `get_all_image_names` scan takes ~14 s.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:188-212, 231-242, 374):
```python
for si in range(len(stim_starts)):
    s_start = stim_starts[si]
    s_stop = stim_stops[si]
    ...
    frame_mask = (trial_ts >= s_start) & (trial_ts < s_stop)
    trace[frame_mask] = img_idx
...
for si in range(len(stim_starts)):
    if not is_change[si]:
        continue
    ...
    frame_idx = np.searchsorted(trial_ts, s_start)
    if frame_idx < n_frames:
        trace[frame_idx] = 1
...
for trial_idx in valid_trial_idx:
```

**What this does:** Per-trial Python loops iterate over stimulus presentations to build the image-identity and image-change traces (each presentation does its own boolean-mask assignment / `np.searchsorted`). A separate per-trial loop iterates over `valid_trial_idx`. None of these are vectorized across stimuli or trials.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:473-493, 188-212, 231-242):
```python
def get_all_image_names(exp_table):
    all_names = set()
    for _, row in exp_table.iterrows():
        eid = row['ophys_experiment_id']
        nwb_path = os.path.join(NWB_DIR, f'behavior_ophys_experiment_{eid}.nwb')
        try:
            with h5py.File(nwb_path, 'r') as f:
                for key in f['intervals'].keys():
                    if 'Natural_Images' in key or 'natural_images' in key:
                        names = f['intervals'][key]['image_name'][:]
                        ...
...
# build_image_identity_trace and build_image_change_trace each iterate over
# the full stimulus presentations list per trial
for si in range(len(stim_starts)):
    if s_stop < trial_start: continue
    if s_start >= trial_stop: break
    ...
```

**What this does:** Each NWB file is opened twice — once in `get_all_image_names` to collect labels, then again in `load_nwb_data` during processing. Within a session, both `build_image_identity_trace` and `build_image_change_trace` iterate over the entire session's stimulus-presentations list separately for every trial.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:75-83, 104-109):
```python
if 'image_segmentation' in f['processing']['ophys']:
    seg = f['processing']['ophys']['image_segmentation']
    for key in seg.keys():
        if 'id' in seg[key]:
            data['cell_roi_ids'] = seg[key]['id'][:]
            break
...
for key in ['start_time', 'stop_time', 'go', 'catch', 'aborted', 'auto_rewarded',
             'hit', 'miss', 'false_alarm', 'correct_reject', 'change_time',
             'initial_image_name', 'change_image_name', 'is_change']:
    if key in trials:
        trial_data[key] = trials[key][:]
```

**What this does:** `cell_roi_ids` is loaded but never used downstream. Trial columns `change_time`, `initial_image_name`, `change_image_name`, and `is_change` are loaded but never read after loading (image identity/change come from the stimulus presentations table instead).

**Rating:** match

**Note:** _(no note)_

---

## Q 9-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — no explicit memory-optimization section)

**Code** (convert_data.py:67, 304-470):
```python
with h5py.File(nwb_path, 'r') as f:
    ...
# load_nwb_data returns only the arrays it explicitly extracts;
# the file handle is closed via the `with` block.

# process_experiment iterates one experiment at a time; nwb_data,
# dff, and the per-session interpolated arrays go out of scope when
# the function returns. Only per-trial slices (neural_trials,
# output_trials) are kept and returned in `result`.
neural = dff[:, frame_mask].astype(np.float32)
...
result = {
    'neural': neural_trials,
    'output': output_trials,
    ...
}
```

**What this does:** Experiments are processed one at a time inside `process_experiment`; full-session dF/F and interpolated behavioral arrays are local variables that go out of scope when the function returns, leaving only the per-trial slices in memory. Per-trial neural data is cast to float32. There is no explicit `del` or chunked NWB read — full session arrays are loaded into RAM during processing.

**Rating:** match

**Note:** _(no note)_

---
