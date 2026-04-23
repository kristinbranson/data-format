# allen2p — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/allen2p/codex/2026-04-07__15-15-02_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:202 — "Read NWB files directly with `h5py` and mirror the AllenSDK/whitepaper semantics from the processed NWB contents rather than relying on broken high-level loading in this environment."
> CONVERSION_NOTES.md:267 — "Directly reads local NWB files with `h5py` because the local AllenSDK/NWB stack cannot instantiate these NWB files in this environment."

**Code** (convert_data.py:161-190, 568-575):
```python
def get_local_session_metadata(data_root: Path) -> list[SessionMeta]:
    table_path = data_root / "visual-behavior-ophys-1.1.0" / "project_metadata" / "ophys_experiment_table.csv"
    exp_table = pd.read_csv(table_path)

    experiment_dir = data_root / "visual-behavior-ophys-1.1.0" / "behavior_ophys_experiments"
    available_files = {
        int(path.stem.split("_")[-1]): path
        for path in sorted(experiment_dir.glob("behavior_ophys_experiment_*.nwb"))
    }

    exp_table = exp_table[exp_table["ophys_experiment_id"].isin(available_files)].copy()
    exp_table = exp_table[~exp_table["passive"]].copy()
    exp_table = exp_table.sort_values("ophys_experiment_id")
    ...
all_sessions = get_local_session_metadata(data_root)
```

**What this does:** Reads the local `ophys_experiment_table.csv` and intersects with locally available `behavior_ophys_experiment_*.nwb` files, dropping passive experiments. Each surviving experiment file is later opened directly with `h5py` (not via AllenSDK) to access trials, neural events, running, pupil, and stimulus presentations.

**Rating:** ok

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:227 — "`mouse_id` from `ophys_experiment_table.csv` -> `subjects`, `subject_idx` -> Unique string list + per-session index"

**Code** (convert_data.py:589-590):
```python
subjects = sorted({session.mouse_id for session in kept_sessions})
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
```

**What this does:** Subjects are the sorted set of unique `mouse_id` strings drawn from the experiment metadata of kept sessions; each session is later assigned an integer `subject_idx` via this mapping.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:233 — "Treat each `ophys_experiment_id` file as one converted session: This matches the AllenSDK object granularity (`BehaviorOphysExperiment`) and yields a single imaging plane / neuron set / brain region per session."
> CONVERSION_NOTES.md:477 — "Multiple experiment files can share the same `behavior_session_id` or `ophys_session_id`; the conversion intentionally treats each `ophys_experiment_id` plane as a separate session..."

**Code** (convert_data.py:171-189):
```python
exp_table = exp_table.sort_values("ophys_experiment_id")

sessions = []
for row in exp_table.itertuples(index=False):
    sessions.append(
        SessionMeta(
            ophys_experiment_id=int(row.ophys_experiment_id),
            ophys_session_id=int(row.ophys_session_id),
            behavior_session_id=int(row.behavior_session_id),
            mouse_id=str(row.mouse_id),
            ...
        )
    )
```

**What this does:** Each `ophys_experiment_id` (one imaging plane, one NWB file) is treated as a separate session. Sessions are ordered by `ophys_experiment_id`. Multiple planes from the same `ophys_session_id` become distinct sessions in the output.

**Rating:** incorrect

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:206 — "Trials will be defined by the processed NWB `trials` table, keeping GO and CATCH only, excluding `aborted` and `auto_rewarded`."
> CONVERSION_NOTES.md:221 — "Filter to GO/CATCH with `aborted==False` and `auto_rewarded==False`"

**Code** (convert_data.py:91-97, 471-486):
```python
def build_trial_bins(start_time: float, stop_time: float) -> np.ndarray:
    if not np.isfinite(start_time) or not np.isfinite(stop_time) or stop_time <= start_time:
        return np.asarray([], dtype=np.float64)
    n_bins = max(1, int(np.ceil((stop_time - start_time) / DT)))
    centers = start_time + (np.arange(n_bins, dtype=np.float64) + 0.5) * DT
    valid = centers < (stop_time + 1e-9)
    return centers[valid]
...
trials = get_trial_table(f)
trials = trials[(trials["go"] | trials["catch"]) & (~trials["aborted"]) & (~trials["auto_rewarded"])].copy()
trials = trials.sort_values("id").reset_index(drop=True)
...
for trial_idx, trial in trials.iterrows():
    centers = build_trial_bins(float(trial["start_time"]), float(trial["stop_time"]))
```

**What this does:** Each trial spans the NWB trials-table `start_time` to `stop_time` window, sampled at 30 Hz bin centers (`DT = 1/30`). Only GO|CATCH trials with neither `aborted` nor `auto_rewarded` set are kept.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:178-181 — "Aborted trials are excluded... Auto/free-reward trials are behaviorally present and should be excluded for this decoder task. GO and CATCH trials are the contingent trial types of interest."
> CONVERSION_NOTES.md:242 — "Three active local files lack eye-tracking acquisition entirely; these sessions will be excluded."

**Code** (convert_data.py:317-326, 554-555):
```python
trials = trials[(trials["go"] | trials["catch"]) & (~trials["aborted"]) & (~trials["auto_rewarded"])].copy()
if len(trials) < 2:
    print(f"[pass1 {idx}/{len(sessions)}] skip {session.ophys_experiment_id}: fewer than 2 kept trials")
    continue

presentations = get_task_presentations(f)
if presentations.empty:
    print(f"[pass1 {idx}/{len(sessions)}] skip {session.ophys_experiment_id}: no task presentations")
    continue
...
if len(neural_trials) < 2:
    raise RuntimeError(f"Session {session.ophys_experiment_id} has fewer than 2 usable trials")
```

**What this does:** Drops aborted, auto-rewarded, and non-(go|catch) trials. Sessions with fewer than 2 surviving trials, no task presentations, or missing eye tracking are skipped. Trials whose `build_trial_bins` returns an empty grid are silently dropped.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:198 — "Use raw event magnitude traces from `processing/ophys/event_detection/data` as `neural`. Do not use `filtered_events`... and do not recompute dF/F."
> CONVERSION_NOTES.md:219 — "`processing/ophys/event_detection/data` (NWB, time x ROI) -> `neural`"

**Code** (convert_data.py:263-267):
```python
def get_neural_data(f: h5py.File) -> tuple[np.ndarray, np.ndarray]:
    event_group = f["processing"]["ophys"]["event_detection"]
    timestamps = np.asarray(event_group["timestamps"][:], dtype=np.float64)
    events = np.asarray(event_group["data"][:], dtype=np.float32)
    return timestamps, events
```

**What this does:** Neural activity is the precomputed event-detection magnitudes stored in `processing/ophys/event_detection/data` of each NWB file, paired with their timestamps. dF/F is not used.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:219 — "Transpose to ROI x time, then linearly interpolate event magnitudes from native ophys timestamps onto a common 30 Hz trial grid"
> CONVERSION_NOTES.md:281 — "Vectorized linear interpolation for neural event matrices using `searchsorted` + broadcasting rather than per-neuron `np.interp`."

**Code** (convert_data.py:112-130, 490):
```python
def linear_resample_matrix(src_time, src_value, dst_time):
    if dst_time.size == 0:
        return np.zeros((src_value.shape[1], 0), dtype=np.float32)
    idx_hi = np.searchsorted(src_time, dst_time, side="left")
    idx_hi = np.clip(idx_hi, 1, len(src_time) - 1)
    idx_lo = idx_hi - 1
    t0 = src_time[idx_lo]
    t1 = src_time[idx_hi]
    denom = np.where(t1 > t0, t1 - t0, 1.0)
    w = ((dst_time - t0) / denom).astype(np.float32)
    interp = src_value[idx_lo] * (1.0 - w[:, None]) + src_value[idx_hi] * w[:, None]
    return interp.T.astype(np.float32, copy=False)
...
neural_trial = linear_resample_matrix(ophys_time, events, centers)
```

**What this does:** Per-trial event magnitudes are vectorially linear-interpolated from native ophys timestamps onto the 30 Hz trial-bin centers, producing an `(n_neurons, n_bins)` float32 matrix. No additional smoothing or normalization.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:447-449 — "reference: `CellSpecimens.__init__` keeps `valid_roi == True`; converter: included-session raw NWB files already had all listed cells valid (29,168 total valid of 29,168 total listed), so event matrices matched converted neuron counts exactly"

**Code** (convert_data.py:289-292):
```python
def get_cell_count_and_region_idx(f: h5py.File, region_index: int) -> np.ndarray:
    cell_table = f["processing"]["ophys"]["image_segmentation"]["cell_specimen_table"]
    n_cells = len(cell_table["cell_specimen_id"])
    return np.full(n_cells, region_index, dtype=np.int64)
```

**What this does:** No explicit ROI/cell filtering is applied in the converter. All ROIs in the cell-specimen table are kept and used in the order they appear in the event matrix.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:237 — "Use a common 30 Hz trial grid: Native acquisition rates vary across rigs (31 Hz single-plane, 11 Hz multiplane). Resampling all streams to 30 Hz gives one shared bin size..."

**Code** (convert_data.py:27-28, 91-97):
```python
DT = 1.0 / 30.0
TIME_BIN_MS = DT * 1000.0
...
def build_trial_bins(start_time: float, stop_time: float) -> np.ndarray:
    if not np.isfinite(start_time) or not np.isfinite(stop_time) or stop_time <= start_time:
        return np.asarray([], dtype=np.float64)
    n_bins = max(1, int(np.ceil((stop_time - start_time) / DT)))
    centers = start_time + (np.arange(n_bins, dtype=np.float64) + 0.5) * DT
    valid = centers < (stop_time + 1e-9)
    return centers[valid]
```

**What this does:** Neural data is linearly interpolated to a fixed 30 Hz grid (`DT = 1/30 s`, ≈33.33 ms bin) of bin centers spanning each trial's `[start_time, stop_time)`. Bin centers strictly less than `stop_time + 1e-9` are kept.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:659 (metadata in code) — `"temporal_alignment_event": "trial start"`
> CONVERSION_NOTES.md:238 — "Align by absolute ophys time, then cut into trials: For each trial, create bin centers from trial `start_time` to `stop_time` at 30 Hz and sample/interpolate all streams onto that grid."

**Code** (convert_data.py:486-490, 659-661):
```python
centers = build_trial_bins(float(trial["start_time"]), float(trial["stop_time"]))
if centers.size == 0:
    continue

neural_trial = linear_resample_matrix(ophys_time, events, centers)
...
"temporal_alignment_event": "trial start",
"off_start": 0.0,
"off_end": None,
```

**What this does:** Each trial's bin centers begin at half a 30 Hz bin past `start_time` and tile up to `stop_time`; neural events are interpolated onto this absolute-time grid. Metadata records the alignment event as `"trial start"` with `off_start = 0.0`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `output` *Running speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:224 — "`processing/running/speed` (`data`, `timestamps`) -> `output[running_speed_bin]`"

**Code** (convert_data.py:270-274):
```python
def get_running_data(f: h5py.File) -> tuple[np.ndarray, np.ndarray]:
    running_group = f["processing"]["running"]["speed"]
    timestamps = np.asarray(running_group["timestamps"][:], dtype=np.float64)
    speed = np.asarray(running_group["data"][:], dtype=np.float64)
    return timestamps, speed
```

**What this does:** Running speed is read from `processing/running/speed/{data, timestamps}` in each NWB file (the SDK's filtered speed stream).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `output` *Running speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:241 — "Discretize running and pupil globally across the included dataset: Five equal-percentile bins will be computed from all finite samples across all included sessions/trials"

**Code** (convert_data.py:144-158, 352-356, 491-494):
```python
def compute_quantile_edges(values: np.ndarray, nbins: int) -> np.ndarray:
    probs = np.linspace(0.0, 1.0, nbins + 1)
    edges = np.quantile(values, probs)
    ...
def digitize_with_edges(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, edges[0], edges[-1])
    bins = np.searchsorted(edges[1:-1], clipped, side="right")
    return bins.astype(np.int64, copy=False)
...
running_all = np.concatenate(running_values).astype(np.float64, copy=False)
running_edges = compute_quantile_edges(running_all[np.isfinite(running_all)], 5)
...
running_trial = linear_resample_vector(running_time, running_speed, centers)
running_bin = digitize_with_edges(running_trial, running_edges)
```

**What this does:** Pass 1 collects all per-trial resampled running speeds across kept sessions and computes 5 global equal-frequency quantile edges. Per trial, running speed is linear-interpolated to the 30 Hz grid then digitized into 5 bins (codes 0-4).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `output` *Running speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:208 — "Running speed, pupil diameter, and stimulus variables will be interpolated or sampled onto the same 30 Hz trial grid."

**Code** (convert_data.py:100-109, 490-494):
```python
def linear_resample_vector(src_time, src_value, dst_time):
    if dst_time.size == 0:
        return np.asarray([], dtype=np.float32)
    if src_time.size == 0:
        raise ValueError("Cannot resample from an empty source time series")
    return np.interp(dst_time, src_time, src_value).astype(np.float32, copy=False)
...
neural_trial = linear_resample_matrix(ophys_time, events, centers)
running_trial = linear_resample_vector(running_time, running_speed, centers)
```

**What this does:** Running speed is linearly interpolated onto the same `centers` array (30 Hz bin centers from `start_time` to `stop_time`) used for the neural matrix, so each neural bin has a paired running-bin sample at the same absolute time.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Pupil diameter* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:225 — "`acquisition/EyeTracking/pupil_tracking/{width,height,timestamps}` plus blink-filtered fields -> `output[pupil_diameter_bin]` -> Compute pupil diameter as `2 * max(width, height)`"

**Code** (convert_data.py:277-286):
```python
def get_pupil_data(f: h5py.File) -> tuple[np.ndarray, np.ndarray]:
    if "EyeTracking" not in f["acquisition"]:
        raise KeyError("Missing EyeTracking acquisition")
    eye_group = f["acquisition"]["EyeTracking"]
    timestamps = np.asarray(eye_group["eye_tracking"]["timestamps"][:], dtype=np.float64)
    width = np.asarray(eye_group["pupil_tracking"]["width"][:], dtype=np.float64)
    height = np.asarray(eye_group["pupil_tracking"]["height"][:], dtype=np.float64)
    diameter = 2.0 * np.maximum(width, height)
    diameter = fill_nan_by_time(timestamps, diameter)
    return timestamps, diameter
```

**What this does:** Pupil diameter is computed from `acquisition/EyeTracking/pupil_tracking` ellipse `width` and `height` as `2 * max(width, height)`, paired with `eye_tracking/timestamps`. NaNs (e.g., from blink frames) are filled by time interpolation. Sessions without `EyeTracking` raise `KeyError` and are skipped.

**Rating:** ok

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Pupil diameter*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:225 — "interpolate onto 30 Hz grid; discretize globally into 5 equal-frequency bins"

**Code** (convert_data.py:133-141, 354-355, 492-495):
```python
def fill_nan_by_time(time_axis, values):
    values = values.astype(np.float64, copy=True)
    finite = np.isfinite(values)
    ...
    values[~finite] = np.interp(time_axis[~finite], time_axis[finite], values[finite])
    return values
...
pupil_all = np.concatenate(pupil_values).astype(np.float64, copy=False)
pupil_edges = compute_quantile_edges(pupil_all[np.isfinite(pupil_all)], 5)
...
pupil_trial = linear_resample_vector(pupil_time, pupil_diameter, centers)
pupil_bin = digitize_with_edges(pupil_trial, pupil_edges)
```

**What this does:** NaN pupil samples are filled by time interpolation, the diameter is linearly resampled to the 30 Hz trial grid, and a global 5-quantile binning (computed in pass 1 across all sessions/trials) maps the values to integer codes 0-4.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Pupil diameter* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:208 — "Running speed, pupil diameter, and stimulus variables will be interpolated or sampled onto the same 30 Hz trial grid."

**Code** (convert_data.py:486-495):
```python
centers = build_trial_bins(float(trial["start_time"]), float(trial["stop_time"]))
...
neural_trial = linear_resample_matrix(ophys_time, events, centers)
running_trial = linear_resample_vector(running_time, running_speed, centers)
pupil_trial = linear_resample_vector(pupil_time, pupil_diameter, centers)
running_bin = digitize_with_edges(running_trial, running_edges)
pupil_bin = digitize_with_edges(pupil_trial, pupil_edges)
```

**What this does:** Pupil diameter is interpolated onto the same 30 Hz `centers` array used for neural events, sharing absolute-time alignment within each trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *Image name* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:222 — "`intervals/*_presentations` task image block (`image_name`, `omitted`, `is_change`, `start_time`, `stop_time`, `trials_id`, `stimulus_block_name`) -> `output[image_identity]`"
> CONVERSION_NOTES.md:240 — "`image_identity` will include a `gray` category for ISI and omitted-image periods"

**Code** (convert_data.py:193-230, 497-508):
```python
def get_task_presentations(f: h5py.File) -> pd.DataFrame:
    rows = []
    for name, group in f["intervals"].items():
        if name == "trials":
            continue
        ...
        block_names = decode_str_array(group["stimulus_block_name"][:])
        keep = np.array(["change_detection" in x for x in block_names], dtype=bool)
        ...
        columns = ["start_time", "stop_time", "image_name", "omitted", "is_change",
                   "trials_id", "stimulus_block_name", "active", "duration"]
        df = read_interval_table(group, columns)
...
image_identity = np.full(centers.shape[0], image_value_to_idx["gray"], dtype=np.int64)
trial_presentations = presentations[presentations["trials_id"] == int(trial["id"])].copy()
for row in trial_presentations.itertuples(index=False):
    mask = (centers >= float(row.start_time)) & (centers < float(row.stop_time))
    if bool(row.omitted) or str(row.image_name) == "omitted":
        image_identity[mask] = image_value_to_idx["gray"]
    else:
        image_identity[mask] = image_value_to_idx[str(row.image_name)]
```

**What this does:** Image identity is derived from the per-flash stimulus presentation tables in `intervals/*_presentations` (filtered to blocks whose `stimulus_block_name` contains "change_detection"), using `image_name`, `omitted`, `start_time`, `stop_time`, and `trials_id`. A `"gray"` placeholder fills bins outside any flash window.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *Image name*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:240 — "Encode gray/omission periods explicitly: `image_identity` will include a `gray` category for ISI and omitted-image periods"

**Code** (convert_data.py:584-587, 645-647):
```python
image_values = sorted(image_names)
if "gray" in image_values:
    image_values = ["gray"] + [x for x in image_values if x != "gray"]
image_value_to_idx = {name: idx for idx, name in enumerate(image_values)}
...
"output_values": [
    image_values,
    ["no_change", "change"],
```

**What this does:** A global vocabulary of image names is collected across all sessions, sorted, with `"gray"` forced to index 0. Each per-bin image string is mapped to its integer index. Bin assignment uses `(centers >= row.start_time) & (centers < row.stop_time)`; omitted flashes map to `gray`.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `output` *Image name* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:208 — "Running speed, pupil diameter, and stimulus variables will be interpolated or sampled onto the same 30 Hz trial grid."

**Code** (convert_data.py:497-508):
```python
image_identity = np.full(centers.shape[0], image_value_to_idx["gray"], dtype=np.int64)
image_change = np.zeros(centers.shape[0], dtype=np.int64)

trial_presentations = presentations[presentations["trials_id"] == int(trial["id"])].copy()
for row in trial_presentations.itertuples(index=False):
    mask = (centers >= float(row.start_time)) & (centers < float(row.stop_time))
    if not mask.any():
        continue
    if bool(row.omitted) or str(row.image_name) == "omitted":
        image_identity[mask] = image_value_to_idx["gray"]
    else:
        image_identity[mask] = image_value_to_idx[str(row.image_name)]
```

**What this does:** Image identity is assigned to each 30 Hz bin of the same `centers` array used by the neural matrix, by checking which presentation interval contains each bin center. Alignment is therefore frame-for-frame with neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `output` *Image change* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:223 — "Same stimulus-presentation rows -> `output[image_change]` -> Binary per-bin trace: 1 during change-image flash interval, else 0"

**Code** (convert_data.py:498-510):
```python
image_change = np.zeros(centers.shape[0], dtype=np.int64)

trial_presentations = presentations[presentations["trials_id"] == int(trial["id"])].copy()
for row in trial_presentations.itertuples(index=False):
    mask = (centers >= float(row.start_time)) & (centers < float(row.stop_time))
    if not mask.any():
        continue
    ...
    if bool(row.is_change):
        image_change[mask] = 1
```

**What this does:** Image change is derived from the `is_change` flag on each row of the same task presentation table used for image identity, marking bins inside change-flash intervals with 1.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `output` *Image change*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:223 — "Binary per-bin trace: 1 during change-image flash interval, else 0; Change and pre-change flashes are never omitted"

**Code** (convert_data.py:498, 508-510, 645-647):
```python
image_change = np.zeros(centers.shape[0], dtype=np.int64)
...
    if bool(row.is_change):
        image_change[mask] = 1
...
"output_values": [
    image_values,
    ["no_change", "change"],
```

**What this does:** Initialized to all zeros, then set to 1 only on bins overlapping a presentation row whose `is_change` is True. The 2-class vocabulary is `["no_change", "change"]`. The window equals the change flash's `[start_time, stop_time)` interval; no extra padding is added.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. How is `output` *Image change* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:208 — "Running speed, pupil diameter, and stimulus variables will be interpolated or sampled onto the same 30 Hz trial grid."

**Code** (convert_data.py:498-510):
```python
image_change = np.zeros(centers.shape[0], dtype=np.int64)
trial_presentations = presentations[presentations["trials_id"] == int(trial["id"])].copy()
for row in trial_presentations.itertuples(index=False):
    mask = (centers >= float(row.start_time)) & (centers < float(row.stop_time))
    ...
    if bool(row.is_change):
        image_change[mask] = 1
```

**What this does:** The image-change indicator is built on the same `centers` array (30 Hz bins from `start_time` to `stop_time`) as the neural matrix, so each change-flash bin lines up frame-by-frame with the neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:221 — "outcome encoded as constant categorical trace across each trial"

**Code** (convert_data.py:29, 295-304):
```python
OUTCOME_NAMES = ["hit", "miss", "false_alarm", "correct_reject"]
...
def trial_outcome_index(trial_row: pd.Series) -> int:
    if bool(trial_row["hit"]):
        return 0
    if bool(trial_row["miss"]):
        return 1
    if bool(trial_row["false_alarm"]):
        return 2
    if bool(trial_row["correct_reject"]):
        return 3
    raise ValueError("Trial has no valid outcome label")
```

**What this does:** Trial outcome is read from the four mutually-exclusive boolean columns `hit`, `miss`, `false_alarm`, `correct_reject` in the NWB `intervals/trials` table.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:239 — "`trial_outcome` will be repeated across bins within a trial as a constant categorical trace to keep one consistent `(n_output, T)` format."

**Code** (convert_data.py:512-523, 645-651):
```python
outcome_idx = trial_outcome_index(trial)
outcome_trace = np.full(centers.shape[0], outcome_idx, dtype=np.int64)

output_trial = np.vstack(
    [
        image_identity,
        image_change,
        running_bin,
        pupil_bin,
        outcome_trace,
    ]
)
...
"output_values": [
    image_values,
    ["no_change", "change"],
    RUNNING_BIN_NAMES,
    PUPIL_BIN_NAMES,
    OUTCOME_NAMES,
],
```

**What this does:** The four outcomes map to fixed integer codes 0=hit, 1=miss, 2=false_alarm, 3=correct_reject. The single per-trial code is broadcast across all bins and stacked as the fifth output channel.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-c. How is `output` *Trial outcome* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:239 — "`trial_outcome` will be repeated across bins within a trial as a constant categorical trace to keep one consistent `(n_output, T)` format."

**Code** (convert_data.py:512-513):
```python
outcome_idx = trial_outcome_index(trial)
outcome_trace = np.full(centers.shape[0], outcome_idx, dtype=np.int64)
```

**What this does:** The per-trial outcome is repeated across every 30 Hz bin of the trial, giving the same time-axis length as the neural matrix.

**Rating:** match

**Note:** _(no note)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:242 — "Three active local files lack eye-tracking acquisition entirely; these sessions will be excluded. Remaining sessions have modest blink-related missingness and can be filled by time interpolation before discretization."
> CONVERSION_NOTES.md:476 — "All-zero event trials are retained because they are present in the source data and still have valid behavioral/stimulus labels."

**Code** (convert_data.py:133-141, 156-158, 277-280, 315-326, 346-348):
```python
def fill_nan_by_time(time_axis, values):
    ...
    if finite.sum() == 0:
        raise ValueError("All values are NaN")
    if finite.all():
        return values
    values[~finite] = np.interp(time_axis[~finite], time_axis[finite], values[finite])
    return values
...
def digitize_with_edges(values, edges):
    clipped = np.clip(values, edges[0], edges[-1])
    bins = np.searchsorted(edges[1:-1], clipped, side="right")
...
if "EyeTracking" not in f["acquisition"]:
    raise KeyError("Missing EyeTracking acquisition")
...
if presentations.empty:
    print(f"... no task presentations")
    continue
...
except KeyError as exc:
    print(f"[pass1 {idx}/{len(sessions)}] skip {session.ophys_experiment_id}: {exc}")
```

**What this does:** Pupil NaNs are linearly interpolated; values outside quantile edges are clipped before binning; sessions missing eye tracking or task presentations are skipped via KeyError + try/except. Sessions with <2 valid trials are skipped. Empty trial windows are skipped silently. All-zero neural trials are retained.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:277 — "Full conversion may still be I/O-heavy because each NWB event matrix must be read from disk."
> CONVERSION_NOTES.md:323-326 — "Pass 1 bin-stat collection ~0.36 s / session ~1.2 min for 202 active local sessions; Pass 2 conversion ~1.86 s / session ~6.3 min for 202 active local sessions; Total conversion ~2.22 s / session ~7.5 min"
> conversion_full_out.txt (last line) — "Saved converted_data.pkl with 199 sessions, 51075 trials, 29168 neurons in 395.58s"

**Code** (convert_data.py:316, 470, 263-267):
```python
with h5py.File(session.filepath, "r") as f:           # pass 1
    ...
with h5py.File(session.filepath, "r") as f:           # pass 2 (re-opened)
    ...
event_group = f["processing"]["ophys"]["event_detection"]
events = np.asarray(event_group["data"][:], dtype=np.float32)
```

**What this does:** Per the notes the slowest steps are reading event-detection matrices and other arrays from each NWB file. Each file is opened twice (pass 1 stats; pass 2 conversion). Full run completed in 395.58 s for 199 retained sessions; per-session pass-2 elapsed times were typically 0.7-1.0 s.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:281 — "Vectorized linear interpolation for neural event matrices using `searchsorted` + broadcasting rather than per-neuron `np.interp`."

**Code** (convert_data.py:485-510):
```python
for trial_idx, trial in trials.iterrows():
    centers = build_trial_bins(...)
    ...
    neural_trial = linear_resample_matrix(ophys_time, events, centers)
    ...
    trial_presentations = presentations[presentations["trials_id"] == int(trial["id"])].copy()
    for row in trial_presentations.itertuples(index=False):
        mask = (centers >= float(row.start_time)) & (centers < float(row.stop_time))
        ...
```

**What this does:** The neural resampling is already vectorized across neurons. Two remaining Python loops are the per-trial loop in `convert_session` and the per-presentation-row loop assigning image identity/change masks per trial.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:278 — "Global binning requires a first pass over sessions, so conversion reads each file twice."

**Code** (convert_data.py:316-345, 470-478):
```python
# Pass 1
with h5py.File(session.filepath, "r") as f:
    trials = get_trial_table(f)
    ...
    presentations = get_task_presentations(f)
    running_time, running_speed = get_running_data(f)
    pupil_time, pupil_diameter = get_pupil_data(f)
    for trial in trials.itertuples(index=False):
        centers = build_trial_bins(...)
        running_trial = linear_resample_vector(running_time, running_speed, centers)
        pupil_trial = linear_resample_vector(pupil_time, pupil_diameter, centers)
...
# Pass 2
with h5py.File(session.filepath, "r") as f:
    trials = get_trial_table(f)
    ...
    presentations = get_task_presentations(f)
    ophys_time, events = get_neural_data(f)
    running_time, running_speed = get_running_data(f)
    pupil_time, pupil_diameter = get_pupil_data(f)
```

**What this does:** Each kept NWB file is opened and read twice — once in pass 1 to compute global running/pupil quantile edges and once in pass 2 to actually convert. Trial filtering, presentation loading, running, and pupil reads are repeated across the two passes.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none directly addressing discarded work)

**Code** (convert_data.py:614):
```python
input_trials = [np.zeros((0, trial.shape[1]), dtype=np.float32) for trial in neural_trials]
```

**What this does:** Decoder `input` arrays are built as empty `(0, T)` placeholders for every trial since the task specifies no decoder inputs; the diagnostic `--show-processing` plot rendering is also performed only when explicitly requested. No other clearly unused intermediate is computed.

**Rating:** missing

**Note:** _(no note)_

---

## Q 9-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:282 — "Session-level streaming design avoids storing continuous raw traces for the whole dataset in memory."

**Code** (convert_data.py:316, 470, 525-526):
```python
with h5py.File(session.filepath, "r") as f:
    ...
    # arrays loaded inside the `with` go out of scope when the file is closed
...
neural_trials.append(neural_trial.astype(np.float32, copy=False))
output_trials.append(output_trial)
```

**What this does:** Sessions are processed one at a time inside `with h5py.File(...)` blocks, so full-session event/running/pupil arrays are released between sessions. Only the per-trial sliced arrays are kept and accumulated across sessions. Outputs use `int8`/`int64`/`float32` dtypes; raw events are cast to `float32` with `copy=False` to avoid duplication.

**Rating:** match

**Note:** _(no note)_

---
