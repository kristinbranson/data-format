# allen2p — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/allen2p/codex/2026-04-07__15-15-02_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:64-72: "Top-level data directory contains: visual-behavior-ophys-1.1.0/behavior_ophys_experiments/*.nwb ... project_metadata/*.csv ... Local data are a subset of the Visual Behavior Ophys 1.1.0 release. Primary session files are NWB/HDF5 files, one per ophys_experiment_id."
> CONVERSION_NOTES.md:216: "Load NWB content with h5py rather than the SDK session object ... the current environment's pynwb/hdmf stack cannot instantiate these NWB 2.6.0 files ... Direct HDF5 reads will therefore mirror the SDK field definitions explicitly."

**Code** (convert_data.py:69-96, 231-330):
```python
def read_metadata_sessions() -> List[SessionInfo]:
    exp_table = pd.read_csv(METADATA_DIR / "ophys_experiment_table.csv")
    file_map = {
        int(path.stem.split("_")[-1]): path
        for path in sorted(EXPERIMENT_DIR.glob("behavior_ophys_experiment_*.nwb"))
    }
    exp_table = exp_table[exp_table["ophys_experiment_id"].isin(file_map)].copy()
    exp_table = exp_table[~exp_table["passive"]].copy()
    ...
    filtered_sessions = [s for s in sessions if has_required_eye_tracking(s.path)]

def read_session_raw(session, load_events=True):
    with h5py.File(session.path, "r") as h5f:
        trial_group = h5f["intervals"]["trials"]
        ...
        events = np.asarray(h5f["processing"]["ophys"]["event_detection"]["data"], ...)
        running_speed = np.asarray(h5f["processing"]["running"]["speed"]["data"], ...)
        pupil_width = np.asarray(h5f["acquisition"]["EyeTracking"]["pupil_tracking"]["width"], ...)
```

**What this does:** Reads `ophys_experiment_table.csv` from local `project_metadata/`, intersects with locally available `behavior_ophys_experiment_*.nwb` files, drops passive experiments, drops sessions lacking eye-tracking, and reads each remaining NWB file directly with `h5py` (not the Allen SDK) to extract trials, events, running, and pupil arrays.

**Rating:** incorrect

**Note:** manual code uses the VisualBehavior project code, while the agent uses experiments for which passive is False and for which there is eye tracking. these don't seem to match

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:204: "NWB general/subject/subject_id / metadata mouse_id -> subjects, subject_idx ... Use mouse identifier strings"

**Code** (convert_data.py:80-90, 591-594):
```python
SessionInfo(
    ...
    mouse_id=str(int(row.mouse_id)),
    ...
)
...
subject_idx = subject_to_idx.setdefault(session.mouse_id, len(subject_to_idx))
if subject_idx == len(data["subjects"]):
    data["subjects"].append(session.mouse_id)
```

**What this does:** Subject identity is taken from the `mouse_id` column of `ophys_experiment_table.csv` (cast to string). Subjects are accumulated incrementally during pass 2 in order of first appearance via a `setdefault`-built mapping.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:181: "Treat each NWB experiment file as one decoder session because neural traces are experiment-specific; preserve subject/session metadata so multiple experiments from one behavior session remain linked through subject/session fields."

**Code** (convert_data.py:69-90, 580-582):
```python
exp_table = pd.read_csv(METADATA_DIR / "ophys_experiment_table.csv")
file_map = { int(path.stem.split("_")[-1]): path
             for path in sorted(EXPERIMENT_DIR.glob("behavior_ophys_experiment_*.nwb")) }
exp_table = exp_table[exp_table["ophys_experiment_id"].isin(file_map)].copy()
exp_table = exp_table[~exp_table["passive"]].copy()
exp_table = exp_table.sort_values("ophys_experiment_id")
...
for sess_num, session in enumerate(sessions, start=1):
    raw = read_session_raw(session)
```

**What this does:** Each NWB file (one `ophys_experiment_id`) is treated as one decoder "session". The session list is built from `ophys_experiment_table.csv` filtered to active rows present on disk, sorted by `ophys_experiment_id`. Sessions are processed one at a time without grouping by `ophys_session_id` or `mouse_id`.

**Rating:** incorrect

**Note:** the code snippet doesn't include information about how sessions is created, but the text says that each experiment_id is treated as a session

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:211: "Segment trials from start_time to stop_time: Trial boundaries will come directly from the NWB intervals/trials table, after filtering to keep only (go or catch) and not aborted and not auto_rewarded."

**Code** (convert_data.py:259, 606-613):
```python
keep = (trials["go"] | trials["catch"]) & (~trials["aborted"]) & (~trials["auto_rewarded"])
...
for trial_idx in np.flatnonzero(raw["keep_mask"]):
    start = float(raw["trials"]["start_time"][trial_idx])
    stop = float(raw["trials"]["stop_time"][trial_idx])
    grid = session_grid(start, stop)

    neural_trial = interpolate_matrix(
        raw["ophys_timestamps"], raw["events"], grid
    ).T.astype(np.float32)
```

**What this does:** Trials are taken from `intervals/trials` in the NWB. Each trial spans `start_time` to `stop_time` and is resampled onto a uniform 30 Hz grid (`TIME_BIN_SIZE_S = 1/30`). The kept set is `(go OR catch) AND NOT aborted AND NOT auto_rewarded`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:185: "Trial inclusion for decoder should follow the common interpretation across sources: include go and catch, exclude aborted and auto_rewarded"
> CONVERSION_NOTES.md:215: "Require at least two valid trials per session after filtering"

**Code** (convert_data.py:259, 584-589, 665-670):
```python
keep = (trials["go"] | trials["catch"]) & (~trials["aborted"]) & (~trials["auto_rewarded"])
...
if int(raw["keep_mask"].sum()) < 2:
    print(f"[pass2] skipping session {session.ophys_experiment_id} because it has "
          f"{int(raw['keep_mask'].sum())} valid trials")
    continue
...
if len(session_neural) < 2:
    print(f"[pass2] skipping session {session.ophys_experiment_id} after conversion "
          f"because it has {len(session_neural)} trials")
    continue
```

**What this does:** Aborted and auto-rewarded trials are excluded; only `go` or `catch` trials are kept. Sessions with fewer than 2 valid trials are skipped (checked both before and after pass-2 conversion).

**Rating:** ok

**Note:** uses go | catch which is probably the same as change_time.nonna

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:197: "processing/ophys/event_detection/data + timestamps -> neural. Use precomputed event traces ... Neural signal will be calcium events, not dF/F"
> CONVERSION_NOTES.md:209: "Use events instead of dff_traces ... the strategy paper explicitly states its neural analyses used detected calcium events."

**Code** (convert_data.py:284-292, 611-613):
```python
ophys_timestamps = np.asarray(
    h5f["processing"]["ophys"]["event_detection"]["timestamps"], dtype=np.float64
)
events = np.asarray(
    h5f["processing"]["ophys"]["event_detection"]["data"], dtype=np.float32
)
...
neural_trial = interpolate_matrix(
    raw["ophys_timestamps"], raw["events"], grid
).T.astype(np.float32)
```

**What this does:** Neural data comes from `processing/ophys/event_detection/data` (precomputed calcium events), with corresponding timestamps from the same group. dF/F is not used.

**Rating:** ok

**Note:** uses spike events rather than dff

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:210: "Use a common 30 Hz time base for all sessions ... linearly interpolates calcium event responses onto common 30 Hz timestamps"
> CONVERSION_NOTES.md:252: "Trial-level interpolation is vectorized over neurons within each trial."

**Code** (convert_data.py:172-198, 611-613):
```python
def interpolate_matrix(source_t, source_values, query_t):
    ...
    right = np.searchsorted(source_t, query_t, side="left")
    right = np.clip(right, 0, n_src - 1)
    left = np.clip(right - 1, 0, n_src - 1)
    same = right == left
    t0 = source_t[left]; t1 = source_t[right]
    denom = np.where(np.abs(t1 - t0) < 1e-12, 1.0, t1 - t0)
    w = np.where(same, 0.0, (query_t - t0) / denom)
    left_vals = source_values[left]; right_vals = source_values[right]
    out = left_vals * (1.0 - w[:, None]) + right_vals * w[:, None]
    return out.astype(np.float32)
...
neural_trial = interpolate_matrix(raw["ophys_timestamps"], raw["events"], grid).T
```

**What this does:** The full event matrix is linearly interpolated (vectorized across neurons) from native ophys timestamps onto the per-trial 30 Hz grid, then transposed to `(N_neurons, T)`. No additional smoothing or normalization is applied.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:184: "Keep only valid ROIs / cells from the released NWB content; do not add extra ad hoc neuron filtering beyond reference QC/filtering already reflected in the files"

**Code** (convert_data.py:310-317):
```python
if load_events:
    cell_table = h5f["processing"]["ophys"]["image_segmentation"]["cell_specimen_table"]
    n_cell_table = len(cell_table["id"])
    if events.shape[1] == n_cell_table and "valid_roi" in cell_table:
        valid_roi = np.asarray(h5_array(cell_table["valid_roi"])).astype(bool)
        if valid_roi.sum() != events.shape[1]:
            events = events[:, valid_roi]
    n_neurons = events.shape[1]
```

**What this does:** If the event matrix's neuron axis matches the full `cell_specimen_table` length and a `valid_roi` mask exists with a different sum, neurons are filtered to `valid_roi == True`. Otherwise no extra QC is applied; the SDK's pre-filtered ROIs are accepted as-is.

**Rating:** match

**Note:** i think this could be better, since it is also checking for cells to be valid, but i think all neurons are valid based on data i've loaded in

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:210: "30 Hz is the most defensible common grid"
> CONVERSION_NOTES.md:572: metadata key `resampling_reference: "common 30 Hz grid derived from source ophys timestamps"`

**Code** (convert_data.py:27-28, 159-161, 609-613):
```python
TIME_BIN_SIZE_S = 1.0 / 30.0
TIME_BIN_SIZE_MS = TIME_BIN_SIZE_S * 1000.0
...
def session_grid(start, stop, dt=TIME_BIN_SIZE_S):
    n_bins = max(1, int(math.ceil((stop - start) / dt)))
    return start + np.arange(n_bins, dtype=np.float64) * dt
...
grid = session_grid(start, stop)
neural_trial = interpolate_matrix(raw["ophys_timestamps"], raw["events"], grid).T
```

**What this does:** A fixed 30 Hz bin size (`1/30 s`, written as `33.333...` ms in metadata) is used for all sessions. Each trial's grid is built from `start_time` to `stop_time` in 30 Hz steps; events are linearly interpolated onto that grid.

**Rating:** ok

**Note:** agent uses 30 hz, manual uses native 11 hz for dff data. agent is using events, and 30 hz is the rate of some of the behavior data, so that seems ok

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:562: metadata key `temporal_alignment_event: "trial start"`, `off_start: 0.0`, `off_end: None`

**Code** (convert_data.py:606-613):
```python
for trial_idx in np.flatnonzero(raw["keep_mask"]):
    start = float(raw["trials"]["start_time"][trial_idx])
    stop = float(raw["trials"]["stop_time"][trial_idx])
    grid = session_grid(start, stop)

    neural_trial = interpolate_matrix(
        raw["ophys_timestamps"], raw["events"], grid
    ).T.astype(np.float32)
```

**What this does:** Each trial's grid begins at the trial's `start_time` (from `intervals/trials`) and ends at `stop_time`. Neural samples are aligned to trial start (offset 0) by interpolating onto this grid. Trial length is variable.

**Rating:** ok

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `output` *Image identity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:199: "stimulus-presentation image_name, start_time, stop_time, omitted, active task block only -> output[image_identity]. Piecewise-constant categorical signal on 30 Hz grid; use actual image name during image display; use 'gray' during gray-screen or omission periods"

**Code** (convert_data.py:126-152, 261-282, 389-413):
```python
def choose_task_presentation_group(h5f):
    ... # picks the *_presentations group with active==True and change_detection block
    if best_name is None:
        raise RuntimeError(...)
    return intervals[best_name]
...
stim_group = choose_task_presentation_group(h5f)
stim = read_interval_table(stim_group,
    ["start_time", "stop_time", "image_name", "is_change", "omitted",
     "trials_id", "active", "flashes_since_change"])
...
def stimulus_identity_codes(stimulus, query_t, image_to_code):
    starts = stimulus["start_time"]; stops = stimulus["stop_time"]
    image_names = stimulus["image_name"]; omitted = stimulus["omitted"]
    idx = np.searchsorted(starts, query_t, side="right") - 1
    codes = np.full(query_t.shape, image_to_code["gray"], dtype=np.int64)
    ... # within an interval, set code to image name (or 'gray' if omitted)
```

**What this does:** Image name is derived from the chosen active stimulus-presentations interval table (`start_time`, `stop_time`, `image_name`, `omitted`). Each query timestamp is mapped to the interval that contains it; outside intervals or during omissions, the label is the explicit `gray` class.

**Rating:** ok

**Note:** uses stimulus presentations table instead of initial_image_name change_image_name

---

## Q 3-b. What processing is involved in computing `output` *Image identity*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:199: "Global categories = 'gray' + all unique image names in included sessions"
> CONVERSION_NOTES.md:213: "Use 'gray' as an explicit image-identity class"

**Code** (convert_data.py:349-354, 377, 528, 397-413):
```python
image_names.update(
    str(x)
    for x, omitted in zip(stim["image_name"], stim["omitted"])
    if (not omitted) and str(x) not in ("", "None", "nan")
)
...
image_values = ["gray"] + sorted(image_names)
...
image_to_code = {name: idx for idx, name in enumerate(image_values)}
...
codes = np.full(query_t.shape, image_to_code["gray"], dtype=np.int64)
... # write per-frame code by stimulus interval; gray everywhere else
```

**What this does:** All non-omitted image names across pass-1 sessions are collected, sorted, and prefixed by `"gray"` (always index 0). For each trial frame, `np.searchsorted` locates the containing stimulus interval and assigns the integer code (or gray if not in an interval / omitted).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `output` *Image identity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:199: "Piecewise-constant categorical signal on 30 Hz grid"

**Code** (convert_data.py:609, 620):
```python
grid = session_grid(start, stop)
...
image_codes = stimulus_identity_codes(raw["stimulus"], grid, image_to_code)
```

**What this does:** Image identity codes are computed at exactly the same per-trial 30 Hz `grid` timestamps as the neural data, so they share the same time bins.

**Rating:** ok

**Note:** manual uses trial table initial_image_name change_image_name while agent uses image time series

---

## Q 4-a. What variables in the raw data is `output` *Image change* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:200: "stimulus-presentation is_change, start_time, stop_time -> output[image_change]. Binary time-varying label: 1 during the changed-image presentation window, else 0 ... Marks the post-change flashed image itself rather than a one-bin impulse; catch trials remain 0"
> CONVERSION_NOTES.md:252: "image_change is constructed from the stimulus table's is_change presentation interval instead of a single-bin impulse at change_time"

**Code** (convert_data.py:416-433):
```python
def stimulus_change_codes(stimulus, query_t):
    starts = stimulus["start_time"]; stops = stimulus["stop_time"]
    is_change = stimulus["is_change"]; omitted = stimulus["omitted"]
    idx = np.searchsorted(starts, query_t, side="right") - 1
    codes = np.zeros(query_t.shape, dtype=np.int64)
    valid = idx >= 0; valid &= idx < len(starts)
    idx_valid = idx[valid]
    in_interval = query_t[valid] < stops[idx_valid]
    if np.any(in_interval):
        sub_idx = idx_valid[in_interval]
        changed = is_change[sub_idx] & (~omitted[sub_idx])
        assign = np.flatnonzero(valid)[in_interval]
        codes[assign] = changed.astype(np.int64)
    return codes
```

**What this does:** Image change is derived from the stimulus-presentation table's `is_change`, `start_time`, `stop_time`, and `omitted` fields. It is 1 only during a stimulus interval where `is_change` is True and `omitted` is False; 0 elsewhere (including during gray periods and catch trials, since catch flashes have `is_change == False`).

**Rating:** ok

**Note:** manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 250 ms

---

## Q 4-b. What processing is involved in computing `output` *Image change*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:200: "Marks the post-change flashed image itself rather than a one-bin impulse"

**Code** (convert_data.py:416-433, 621):
```python
# (see 6-a snippet for stimulus_change_codes)
image_change = stimulus_change_codes(raw["stimulus"], grid)
```

**What this does:** No additional processing beyond mapping each 30 Hz frame to the containing stimulus interval and reading its `is_change & ~omitted` flag.

**Rating:** ok

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Image change* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:609, 621):
```python
grid = session_grid(start, stop)
...
image_change = stimulus_change_codes(raw["stimulus"], grid)
```

**What this does:** Image change is computed at the same per-trial 30 Hz `grid` as the neural data, sharing identical bin indices.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *Running speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:201: "running speed timeseries -> output[running_speed_bin] ... Uses filtered running speed, matching SDK default"

**Code** (convert_data.py:294-297):
```python
running_speed = np.asarray(h5f["processing"]["running"]["speed"]["data"], dtype=np.float32)
running_timestamps = np.asarray(
    h5f["processing"]["running"]["speed"]["timestamps"], dtype=np.float64
)
```

**What this does:** Running speed is read from `processing/running/speed/data` with timestamps from the same group (the SDK's filtered running speed stream).

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *Running speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:214: "Discretize continuous outputs globally, not per session: Running-speed and pupil-diameter bin edges will be computed from all valid included timepoints across the converted dataset so class definitions are shared across sessions."

**Code** (convert_data.py:212-221, 360-376, 614-623):
```python
def robust_quintile_edges(values):
    percentiles = np.nanpercentile(values, [20, 40, 60, 80]).astype(np.float64)
    for i in range(1, len(percentiles)):
        if percentiles[i] <= percentiles[i - 1]:
            percentiles[i] = percentiles[i - 1] + 1e-6
    return percentiles

def digitize_with_edges(values, edges):
    return np.digitize(values, edges, right=False).astype(np.int64)
...
running_values.append(
    interpolate_vector(raw["running_timestamps"], raw["running_speed"], grid)
)
...
running_all = np.concatenate(running_values).astype(np.float32)
running_edges = robust_quintile_edges(running_all)
...
running_cont = interpolate_vector(raw["running_timestamps"], raw["running_speed"], grid)
running_bins = digitize_with_edges(running_cont, running_edges)
```

**What this does:** In pass 1, running speed is linearly interpolated onto each trial's 30 Hz grid and concatenated across all kept trials/sessions; quintile edges (20/40/60/80 percentiles) are computed globally. In pass 2, the same interpolation is repeated and values are digitized into 5 bins using those global edges.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `output` *Running speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:210: "all trial streams are aligned in absolute experiment time and resampled to a common 30 Hz grid from raw trial start_time / stop_time"

**Code** (convert_data.py:164-169, 609-615):
```python
def interpolate_vector(source_t, source_values, query_t):
    return np.interp(query_t, source_t, source_values).astype(np.float32)
...
grid = session_grid(start, stop)
neural_trial = interpolate_matrix(raw["ophys_timestamps"], raw["events"], grid).T
running_cont = interpolate_vector(raw["running_timestamps"], raw["running_speed"], grid)
```

**What this does:** Both the neural matrix and running speed are interpolated onto the same per-trial grid (`grid = session_grid(start, stop)`), so they share identical 30 Hz time bins by construction.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `output` *Pupil diameter* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:202: "eye-tracking pupil width/height + blink mask -> output[pupil_diameter_bin]. Compute pupil diameter as max(width, height); use blink-masked values"

**Code** (convert_data.py:299-308):
```python
pupil_width = np.asarray(
    h5f["acquisition"]["EyeTracking"]["pupil_tracking"]["width"], dtype=np.float32
)
pupil_height = np.asarray(
    h5f["acquisition"]["EyeTracking"]["pupil_tracking"]["height"], dtype=np.float32
)
pupil_timestamps = np.asarray(
    h5f["acquisition"]["EyeTracking"]["eye_tracking"]["timestamps"], dtype=np.float64
)
pupil_diameter = np.maximum(pupil_width, pupil_height).astype(np.float32)
```

**What this does:** Pupil diameter is derived from `acquisition/EyeTracking/pupil_tracking` (`width` and `height`) with timestamps from `acquisition/EyeTracking/eye_tracking/timestamps`. Diameter is taken as the elementwise maximum of width and height. (No explicit blink mask is applied; instead, NaN-finite filtering happens in `interpolate_pupil`.)

**Rating:** concerning

**Note:** uses max of width and height, but doesn't filter for likely blinking

---

## Q 6-b. What processing is involved in computing `output` *Pupil diameter*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:202: "interpolate across valid timestamps onto 30 Hz trial grid; discretize with global quintile bins"

**Code** (convert_data.py:201-209, 363-365, 376, 617-624):
```python
def interpolate_pupil(pupil_t, pupil_diameter, query_t):
    valid = np.isfinite(pupil_diameter)
    if valid.sum() == 0:
        raise ValueError("No valid pupil samples available")
    if valid.sum() == 1:
        return np.full(query_t.shape, float(pupil_diameter[valid][0]), dtype=np.float32)
    return np.interp(query_t, pupil_t[valid], pupil_diameter[valid]).astype(np.float32)
...
pupil_values.append(interpolate_pupil(raw["pupil_timestamps"], raw["pupil_diameter"], grid))
...
pupil_all = np.concatenate(pupil_values).astype(np.float32)
pupil_edges = robust_quintile_edges(pupil_all)
...
pupil_cont = interpolate_pupil(raw["pupil_timestamps"], raw["pupil_diameter"], grid)
pupil_bins = digitize_with_edges(pupil_cont, pupil_edges)
```

**What this does:** Non-finite pupil samples are dropped, and the remaining values are linearly interpolated to each trial's 30 Hz grid. Pupil values pooled across all kept trials/sessions yield global quintile edges (20/40/60/80 percentiles) used to digitize per-trial values into 5 bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. How is `output` *Pupil diameter* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:281: "No visual sign of cross-stream temporal misalignment in the reviewed plots."

**Code** (convert_data.py:609-619):
```python
grid = session_grid(start, stop)

neural_trial = interpolate_matrix(raw["ophys_timestamps"], raw["events"], grid).T
running_cont = interpolate_vector(raw["running_timestamps"], raw["running_speed"], grid)
pupil_cont = interpolate_pupil(raw["pupil_timestamps"], raw["pupil_diameter"], grid)
```

**What this does:** Pupil diameter is interpolated onto the same per-trial 30 Hz `grid` used for neural data, so pupil bins share the same time indices as the neural bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:203: "trial outcome flags (hit, miss, false_alarm, correct_reject) -> output[trial_outcome]. Static trial label, broadcast across trial timepoints on 30 Hz grid"

**Code** (convert_data.py:224-228, 253):
```python
def trial_outcome_code(trials, idx, mapping):
    for name in ("hit", "miss", "false_alarm", "correct_reject"):
        if bool(trials[name][idx]):
            return mapping[name]
    raise ValueError(f"Trial {idx} has no valid outcome label")
...
for key in ("go", "catch", "aborted", "auto_rewarded", "hit", "miss", "false_alarm", "correct_reject"):
    trials[key] = trials[key].astype(bool)
```

**What this does:** Trial outcome is derived from the four boolean trial flags `hit`, `miss`, `false_alarm`, `correct_reject` in `intervals/trials`.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:203: "Categories: hit, miss, false_alarm, correct_reject"

**Code** (convert_data.py:529-530, 625-626):
```python
outcome_values = ["hit", "miss", "false_alarm", "correct_reject"]
outcome_to_code = {name: idx for idx, name in enumerate(outcome_values)}
...
outcome_code = trial_outcome_code(raw["trials"], trial_idx, outcome_to_code)
trial_outcome = np.full(grid.shape, outcome_code, dtype=np.int64)
```

**What this does:** A fixed integer mapping (`hit=0, miss=1, false_alarm=2, correct_reject=3`) is applied per trial; the resulting scalar code is broadcast across all 30 Hz time bins of the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:91-95: "filtered_sessions = [session for session in sessions if has_required_eye_tracking(session.path)] ... excluded N active sessions missing eye-tracking pupil data"
> CONVERSION_NOTES.md:449-451: "Missing eye tracking: Found 3 active sessions with no acquisition/EyeTracking group. Fix: exclude 795953296, 806456687, 833631914 before both conversion passes."
> CONVERSION_NOTES.md:347-349: "Verify-only result: ... warnings were emitted for 2,467 trials with all-zero neural event matrices. ... Spot-check ... matched the raw interpolated event trace exactly; the warning reflects genuine event sparsity"

**Code** (convert_data.py:61-66, 91-96, 159-161, 201-209, 220-221, 584-589):
```python
def has_required_eye_tracking(path):
    with h5py.File(path, "r") as h5f:
        if "acquisition" not in h5f or "EyeTracking" not in h5f["acquisition"]:
            return False
        eye = h5f["acquisition"]["EyeTracking"]
        return "pupil_tracking" in eye and "eye_tracking" in eye
...
filtered_sessions = [s for s in sessions if has_required_eye_tracking(s.path)]
excluded = len(sessions) - len(filtered_sessions)
if excluded:
    print(f"[setup] excluded {excluded} active sessions missing eye-tracking pupil data")
...
def session_grid(start, stop, dt=TIME_BIN_SIZE_S):
    n_bins = max(1, int(math.ceil((stop - start) / dt)))   # at least 1 bin
...
def interpolate_pupil(pupil_t, pupil_diameter, query_t):
    valid = np.isfinite(pupil_diameter)
    if valid.sum() == 0: raise ValueError(...)
    if valid.sum() == 1: return np.full(query_t.shape, ..., dtype=np.float32)
    return np.interp(query_t, pupil_t[valid], pupil_diameter[valid])
...
def digitize_with_edges(values, edges):
    return np.digitize(values, edges, right=False).astype(np.int64)
...
if int(raw["keep_mask"].sum()) < 2:
    print(f"[pass2] skipping session {session.ophys_experiment_id} ...")
    continue
```

**What this does:** Sessions missing the EyeTracking group are excluded up front. Pupil interpolation drops non-finite samples; falls back to a constant if only one valid sample. `np.interp` extrapolates by holding endpoints, so out-of-range times get edge values. Sessions with <2 valid trials are skipped. Trial grids always have at least one bin. All-zero neural trials are not corrected (left as warnings). No try/except wraps session reads; an unexpected error would propagate.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:246: "Neural interpolation is still the dominant expected cost because every kept trial needs event traces resampled onto the common grid."
> conversion_full_out.txt: `[pass1] collected global stats from 199 sessions in 106.36s`; `[done] wrote /app/converted_data.pkl in 364.34s`. Pass-2 per-session times scale with neuron count and trial count (e.g. 142 neurons / 190 trials -> 1.13s; 208 neurons / 151 trials -> 1.29s).

**Code** (convert_data.py:611-613, 333-371):
```python
neural_trial = interpolate_matrix(
    raw["ophys_timestamps"], raw["events"], grid
).T.astype(np.float32)
```
Pass 1 in `collect_global_statistics` reads each NWB and interpolates running and pupil per trial; pass 2 in `convert_sessions` re-reads each NWB and additionally interpolates the full event matrix per trial.

**What this does:** The dominant work is reading NWB files (h5py I/O on `events`, running, pupil, timestamps, trials, stimulus tables) twice (once per pass) and then per-trial linear interpolation of the event matrix onto the 30 Hz grid. Total run was ~364s for 199 sessions; pass 1 alone was ~106s.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:252: "Trial-level interpolation is vectorized over neurons within each trial."

**Code** (convert_data.py:356-365, 606-622):
```python
for trial_idx in np.flatnonzero(raw["keep_mask"]):
    start = float(raw["trials"]["start_time"][trial_idx])
    stop = float(raw["trials"]["stop_time"][trial_idx])
    grid = session_grid(start, stop)
    running_values.append(interpolate_vector(raw["running_timestamps"], raw["running_speed"], grid))
    pupil_values.append(interpolate_pupil(raw["pupil_timestamps"], raw["pupil_diameter"], grid))
...
for trial_idx in np.flatnonzero(raw["keep_mask"]):
    ...
    neural_trial = interpolate_matrix(raw["ophys_timestamps"], raw["events"], grid).T
```

**What this does:** Per-trial Python loops in both passes call `np.interp` / `interpolate_matrix` separately for each trial. The interpolation across neurons within one trial is already vectorized, but the per-trial loop itself is not (each trial pays Python-level overhead).

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:235-237: "two-pass conversion: pass 1 computes global image vocabulary and global quintile edges ... pass 2 builds per-trial neural/output arrays"
> CONVERSION_NOTES.md:248: "Two-pass design avoids storing all neural arrays while computing global bin edges."

**Code** (convert_data.py:333-345, 580-582):
```python
def collect_global_statistics(sessions):
    ...
    for idx, session in enumerate(sessions, start=1):
        raw = read_session_raw(session, load_events=False)
        ...
...
for sess_num, session in enumerate(sessions, start=1):
    raw = read_session_raw(session)
```

**What this does:** Each NWB file is opened and parsed twice -- once in pass 1 (without events) to gather global stats and image vocabulary, and again in pass 2 (with events) to assemble outputs. Per-trial running and pupil interpolation onto the trial grid is also done in both passes.

**Rating:** concerning

**Note:** not ideal to load nwb files twice

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:155-156, 343-346, 442-518):
```python
def session_native_dt(ophys_timestamps):
    return float(np.mean(np.diff(ophys_timestamps)))
...
native_dt_by_session[session.ophys_experiment_id] = session_native_dt(raw["ophys_timestamps"])
valid_trial_counts[session.ophys_experiment_id] = int(raw["keep_mask"].sum())
...
def make_processing_plot(...):  # only when --show-processing
```

**What this does:** Pass 1 computes per-session `native_dt` and `valid_trial_counts` that are only printed (not stored in the output pickle). Optional processing-plot rendering and the running/pupil arrays accumulated in pass 1 (used only to fit edges) are discarded after edges are derived.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:248: "Two-pass design avoids storing all neural arrays while computing global bin edges."

**Code** (convert_data.py:231-235, 287-292, 333-345):
```python
def read_session_raw(session, load_events=True):
    with h5py.File(session.path, "r") as h5f:
        ...
        if load_events:
            events = np.asarray(h5f[...]["event_detection"]["data"], dtype=np.float32)
...
def collect_global_statistics(sessions):
    ...
    for idx, session in enumerate(sessions, start=1):
        raw = read_session_raw(session, load_events=False)  # skip event matrix in pass 1
```

**What this does:** Pass 1 explicitly skips loading the event matrix (`load_events=False`), so only behavior arrays are in memory while computing global stats. Each session's `raw` dict is rebound (and garbage-collected) at the next iteration; only per-trial slices are appended to the cumulative output. Events are also stored as `float32`.

**Rating:** ok

**Note:** _(no note)_

---
