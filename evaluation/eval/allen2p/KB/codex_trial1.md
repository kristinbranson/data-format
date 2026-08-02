# allen2p — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/allen2p/codex/2026-04-08__13-38-16_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:88-94: "Root layout inside `data/`: ... `behavior_ophys_experiments/*.nwb`: per-experiment NWB files"; CONVERSION_NOTES.md:289 "Uses direct HDF5 reads from local NWB files rather than `pynwb` because the installed NWB stack is incompatible with these files in this environment."

**Code** (convert_data.py:21-23, 82-83, 658-665):
```python
DATA_ROOT = Path("/app/data/visual-behavior-ophys-1.1.0")
EXPERIMENT_DIR = DATA_ROOT / "behavior_ophys_experiments"
MANIFEST_PATH = Path("/app/data/visual-behavior-ophys_project_manifest_v1.1.0.json")
...
def list_nwb_files() -> List[Path]:
    return sorted(EXPERIMENT_DIR.glob("behavior_ophys_experiment_*.nwb"))
...
files = sort_files_for_mode(list_nwb_files(), sample_mode=args.sample)
log(f"Found {len(files)} NWB experiment files under {EXPERIMENT_DIR}")
```

**What this does:** Discovers every `behavior_ophys_experiment_*.nwb` file under the local Visual Behavior dataset directory and processes each via direct `h5py` reads (no AllenSDK / pynwb). Each NWB file is treated as one experiment (one imaging plane in one session); subject and session IDs are read from `/general/subject/subject_id` and `/general/metadata` per file.

**Rating:** incorrect

**Note:** agent does no filtering to project code VisualBehavior

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:249: "`/general/subject/subject_id` or metadata `mouse_id` → `subjects`, `subject_idx` ... String subject identifiers with session-level index mapping"

**Code** (convert_data.py:353, 702-703, 716-719, 752-753):
```python
subject_id = decode_scalar(f["/general/subject/subject_id"][()])
...
subjects: List[str] = []
subject_to_idx: Dict[str, int] = {}
...
for i, preview in enumerate(eligible, start=1):
    if preview.subject_id not in subject_to_idx:
        subject_to_idx[preview.subject_id] = len(subjects)
        subjects.append(preview.subject_id)
...
"subjects": subjects,
"subject_idx": np.asarray(subject_idx, dtype=np.int64),
```

**What this does:** Each NWB file's `/general/subject/subject_id` is read as a string; unique subject IDs are accumulated in encounter order, and each session is given an integer `subject_idx` pointing into the `subjects` list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:55-56: "One experiment corresponds to one imaging plane in one session." CONVERSION_NOTES.md:128: "Unique local ophys sessions: `247`" — but each NWB experiment file is treated as one session unit in the converted output.

**Code** (convert_data.py:351-354, 393-408):
```python
experiment_id = int(decode_scalar(f["/identifier"][()]))
ophys_session_id = int(f["/general/metadata"].attrs["ophys_session_id"])
...
return SessionPreview(
    path=path,
    experiment_id=experiment_id,
    ophys_session_id=ophys_session_id,
    ...
)
```

**What this does:** Each NWB experiment file becomes one session entry in the converted dataset (one `SessionPreview` per file). Both `experiment_id` and `ophys_session_id` are read but the per-file granularity is what indexes `neural_sessions`/`output_sessions`. No grouping of multi-plane experiments under a shared `ophys_session_id` is performed.

**Rating:** incorrect

**Note:** the code snippet doesn't include information about how sessions is created, but the text says that each experiment_id is treated as a session

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:259: "Alignment event = trial start ... Metadata will therefore use `trial start` as the alignment event with `off_start = 0.0` and variable trial lengths (`off_end = None`)."

**Code** (convert_data.py:201-232, 546-549):
```python
def build_trial_specs(trials: Dict[str, np.ndarray]) -> List[TrialSpec]:
    raw_count = len(trials["id"])
    aborted = np.nan_to_num(trials["aborted"], nan=0.0).astype(bool)
    auto_rewarded = np.nan_to_num(trials["auto_rewarded"], nan=0.0).astype(bool)
    ...
    for idx in range(raw_count):
        if aborted[idx] or auto_rewarded[idx]:
            continue
        ...
        specs.append(TrialSpec(
            trial_idx=idx,
            start_time=float(trials["start_time"][idx]),
            stop_time=float(trials["stop_time"][idx]),
            ...))
...
for spec in preview.trial_specs:
    starts, ends, centers = build_bin_centers(spec.start_time, spec.stop_time, bin_size_sec)
```

**What this does:** Trials are taken directly from the NWB `/intervals/trials` table. Each non-aborted, non-auto-rewarded trial is converted into a per-trial window from `start_time` to `stop_time` (variable length), then rebinned at 100 ms.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:255: "Use SDK-valid trials only: Keep GO and CATCH trials, exclude `aborted` and `auto_rewarded`". CONVERSION_NOTES.md:386-391: session-level exclusions for missing eye tracking, fewer than 2 valid trials, or insufficient pupil samples.

**Code** (convert_data.py:215-220, 385-391, 683-684):
```python
for idx in range(raw_count):
    if aborted[idx] or auto_rewarded[idx]:
        continue
    outcome_flags = [hit[idx], miss[idx], false_alarm[idx], correct_reject[idx]]
    if sum(int(x) for x in outcome_flags) != 1:
        raise ValueError(f"Trial {idx} does not have exactly one valid outcome")
...
excluded_reason = None
if not has_eye_tracking:
    excluded_reason = "missing_eye_tracking"
elif len(specs) < 2:
    excluded_reason = "fewer_than_2_valid_trials"
elif np.isfinite(pupil_values_all).sum() < 2:
    excluded_reason = "insufficient_valid_pupil_samples"
...
if len(eligible) < 2:
    raise RuntimeError("Need at least 2 eligible sessions after filtering")
```

**What this does:** At the trial level, aborted and auto-rewarded trials are excluded; remaining trials must have exactly one of {hit, miss, false_alarm, correct_reject}. At the session level, sessions are excluded if they lack eye tracking, have fewer than 2 valid trials, or have fewer than 2 finite pupil samples.

**Rating:** concerning

**Note:** does not include check for change_time or go | change

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:242: "`/processing/ophys/event_detection` events aligned to ophys frames → `neural`. Use valid-ROI-filtered event traces". CONVERSION_NOTES.md:253: "Neural signal = event-detection output, not dF/F: ... the paper explicitly states that analyses were performed on discrete calcium events."

**Code** (convert_data.py:411-419, 526-529):
```python
def load_neural_events(f: h5py.File) -> Tuple[np.ndarray, np.ndarray]:
    event_data = np.asarray(f["/processing/ophys/event_detection/data"], dtype=np.float32)
    event_rois = np.asarray(f["/processing/ophys/event_detection/rois"], dtype=np.int64)
    valid_roi = np.asarray(
        f["/processing/ophys/image_segmentation/cell_specimen_table/valid_roi"], dtype=bool
    )
    valid_mask = valid_roi[event_rois]
    event_data = event_data[:, valid_mask]
    return event_data, event_rois[valid_mask]
...
ophys_timestamps = np.asarray(
    f["/processing/ophys/dff/traces/timestamps"], dtype=np.float64
)
event_data, _ = load_neural_events(f)
```

**What this does:** Neural data comes from `/processing/ophys/event_detection/data` (discrete calcium event magnitudes per ROI per ophys frame), filtered to ROIs marked `valid_roi == True`. Ophys frame timestamps are read from `/processing/ophys/dff/traces/timestamps`.

**Rating:** ok

**Note:** uses spike events rather than dff

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:782: "binning_rule": "sum event magnitudes within each 100 ms trial bin". CONVERSION_NOTES.md:257-258: "Common time base via uniform rebinned trial bins ... Tentative common bin size = 100 ms".

**Code** (convert_data.py:546-558):
```python
for spec in preview.trial_specs:
    starts, ends, centers = build_bin_centers(spec.start_time, spec.stop_time, bin_size_sec)
    frame_starts = np.searchsorted(ophys_timestamps, starts, side="left")
    frame_ends = np.searchsorted(ophys_timestamps, ends, side="left")
    T = centers.size
    n_neurons = event_data.shape[1]

    neural_trial = np.zeros((n_neurons, T), dtype=np.float32)
    for b in range(T):
        lo = int(frame_starts[b])
        hi = int(frame_ends[b])
        if hi > lo:
            neural_trial[:, b] = event_data[lo:hi].sum(axis=0, dtype=np.float32)
```

**What this does:** Per-trial bins of 100 ms are constructed from `start_time` to `stop_time`. For each bin, all ophys frames whose timestamps fall in `[bin_start, bin_end)` have their event magnitudes summed across frames per neuron.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:217: "Keep SDK `valid_roi` filtering logic even if many local files already appear fully valid."

**Code** (convert_data.py:411-419):
```python
def load_neural_events(f: h5py.File) -> Tuple[np.ndarray, np.ndarray]:
    event_data = np.asarray(f["/processing/ophys/event_detection/data"], dtype=np.float32)
    event_rois = np.asarray(f["/processing/ophys/event_detection/rois"], dtype=np.int64)
    valid_roi = np.asarray(
        f["/processing/ophys/image_segmentation/cell_specimen_table/valid_roi"], dtype=bool
    )
    valid_mask = valid_roi[event_rois]
    event_data = event_data[:, valid_mask]
    return event_data, event_rois[valid_mask]
```

**What this does:** Only ROIs marked as `valid_roi == True` in `cell_specimen_table` are kept. No additional QC (e.g. trial-level neural exclusion, baseline activity, SNR threshold) is applied.

**Rating:** match

**Note:** i think this could be better, since it is also checking for cells to be valid, but i think all neurons are valid based on data i've loaded in

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:258: "Tentative common bin size = 100 ms: This is coarse enough to avoid pathological upsampling of 11 Hz recordings, still resolves 250 ms stimulus flashes, and remains compatible with 30 Hz behavior/eye streams."

**Code** (convert_data.py:25, 235-242, 547-558, 777):
```python
BIN_SIZE_SEC = 0.1
...
def build_bin_centers(start_time: float, stop_time: float, bin_size_sec: float):
    starts = np.arange(start_time, stop_time, bin_size_sec, dtype=np.float64)
    if starts.size == 0:
        starts = np.array([start_time], dtype=np.float64)
    ends = np.minimum(starts + bin_size_sec, stop_time)
    widths = np.maximum(ends - starts, 1e-6)
    centers = starts + 0.5 * widths
    return starts, ends, centers
...
neural_trial[:, b] = event_data[lo:hi].sum(axis=0, dtype=np.float32)
...
"time_bin_size": BIN_SIZE_SEC * 1000.0,
```

**What this does:** Each trial is rebinned to fixed 100 ms bins from `start_time` to `stop_time`. Event magnitudes from raw ophys frames within each bin are summed; the metadata records `time_bin_size = 100.0` ms.

**Rating:** concerning

**Note:** it looks to me like this is not interpolating, but rounding, which seems like it could cause problems

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:259, 778: "Alignment event = trial start ... `off_start = 0.0` and variable trial lengths (`off_end = None`)."

**Code** (convert_data.py:547-549, 778-780):
```python
for spec in preview.trial_specs:
    starts, ends, centers = build_bin_centers(spec.start_time, spec.stop_time, bin_size_sec)
    frame_starts = np.searchsorted(ophys_timestamps, starts, side="left")
...
"temporal_alignment_event": "trial start",
"off_start": 0.0,
"off_end": None,
```

**What this does:** Each trial's neural data spans `[trial start_time, trial stop_time)` from the NWB trials table; the bin grid begins at `start_time` and `np.searchsorted` maps bin edges to ophys frame indices. Trial length is variable; metadata declares the alignment event as `"trial start"`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `output` *Image identity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:244: "Stimulus presentation `image_name` + presentation timing + omission state → `output[0]` (`image_identity`)". CONVERSION_NOTES.md:260: "Image identity will include a `gray` class".

**Code** (convert_data.py:152-198, 287-297):
```python
def read_task_presentations(f):
    ...
    keep_names = ["start_time", "stop_time", "image_name", "omitted", "is_change",
                  "is_sham_change", "trials_id", "active"]
    for key in interval_root.keys():
        if key == "trials":
            continue
        ...
        rows.append(read_interval_group(group, keep_names))
    ...

def unique_nonempty_images(presentations):
    ...
    names = [str(x) for x in presentations["image_name"]
             if str(x) not in {"", "nan", "None", "omitted"}]
    return sorted(set(names))
```

**What this does:** Image names are derived from all `/intervals/*_presentations` tables in the NWB file (concatenated across non-trials presentation groups), using each presentation's `image_name`, `start_time`, `stop_time`, and `omitted` flag. Empty / NaN / "omitted" entries are excluded from the image vocabulary.

**Rating:** ok

**Note:** uses stimulus presentations table instead of initial_image_name change_image_name

---

## Q 3-b. What processing is involved in computing `output` *Image identity*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:244: "Project stimulus presentations onto trial bins; assign image category during image flashes and `gray` during ISI/omissions/no-image periods". CONVERSION_NOTES.md:686-688 (script): builds global image vocabulary across all eligible sessions.

**Code** (convert_data.py:311-334, 686-688):
```python
def make_image_series(presentations, row_idx, centers, image_to_idx):
    image_series = np.full(centers.shape, image_to_idx["gray"], dtype=np.int16)
    change_series = np.zeros(centers.shape, dtype=np.int16)
    for idx in row_idx:
        start = float(presentations["start_time"][idx])
        stop = float(presentations["stop_time"][idx])
        ...
        in_window = (centers >= start) & (centers < stop)
        ...
        omitted = bool(np.nan_to_num(presentations["omitted"][idx], nan=0.0))
        if not omitted:
            image_name = str(presentations["image_name"][idx])
            image_series[in_window] = image_to_idx.get(image_name, image_to_idx["gray"])
        ...
    return image_series, change_series
...
image_names = sorted({img for p in eligible for img in p.unique_images})
image_values = ["gray"] + image_names
image_to_idx = {name: idx for idx, name in enumerate(image_values)}
```

**What this does:** A global integer code vocabulary is built across all eligible sessions; index 0 is `"gray"`, then the sorted set of distinct image names. Per trial, every bin is initialized to `gray` and then overwritten with the corresponding image code for any non-omitted presentation interval whose `[start, stop)` covers that bin center.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `output` *Image identity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:244 (transform): "Project stimulus presentations onto trial bins".

**Code** (convert_data.py:300-308, 547, 560-561):
```python
def find_presentation_rows(presentations, start_time, stop_time):
    ...
    starts = presentations["start_time"]
    ends = presentations["stop_time"]
    mask = (starts < stop_time) & (ends > start_time)
    return np.flatnonzero(mask)
...
starts, ends, centers = build_bin_centers(spec.start_time, spec.stop_time, bin_size_sec)
...
row_idx = find_presentation_rows(presentations, spec.start_time, spec.stop_time)
image_series, change_series = make_image_series(presentations, row_idx, centers, image_to_idx)
```

**What this does:** Presentations overlapping the trial window are selected and assigned to bins whose centers fall inside each presentation's `[start, stop)`. The image series uses the same `centers` time grid as the neural data, so each bin column in `output` aligns with the same column in `neural`.

**Rating:** ok

**Note:** manual uses trial table initial_image_name change_image_name while agent uses image time series

---

## Q 4-a. What variables in the raw data is `output` *Image change* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:245: "Stimulus presentation `is_change` + presentation timing → `output[1]` (`image_change`). Binary series that is 1 during the changed-image presentation immediately after a true image-identity change, else 0".

**Code** (convert_data.py:317-334):
```python
def make_image_series(presentations, row_idx, centers, image_to_idx):
    image_series = np.full(centers.shape, image_to_idx["gray"], dtype=np.int16)
    change_series = np.zeros(centers.shape, dtype=np.int16)
    for idx in row_idx:
        start = float(presentations["start_time"][idx])
        stop = float(presentations["stop_time"][idx])
        ...
        in_window = (centers >= start) & (centers < stop)
        ...
        omitted = bool(np.nan_to_num(presentations["omitted"][idx], nan=0.0))
        ...
        is_change = bool(np.nan_to_num(presentations["is_change"][idx], nan=0.0))
        if is_change and not omitted:
            change_series[in_window] = 1
    return image_series, change_series
```

**What this does:** `image_change` is derived from each presentation row's `is_change` flag combined with `omitted`. Bins fall to 1 only inside a presentation interval flagged `is_change` and not omitted; all other bins remain 0.

**Rating:** concerning

**Note:** manual uses trial table, but agent uses stimulus presentation intervals. manual sets to 1 for 750ms, while agent is only 1 for one frame

---

## Q 4-b. What processing is involved in computing `output` *Image change*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:261: "Image-change target will mark the changed-image presentation, not only a single instant: Marking the post-change image flash interval is more robust after binning".

**Code** (convert_data.py:317-334):
```python
change_series = np.zeros(centers.shape, dtype=np.int16)
for idx in row_idx:
    ...
    in_window = (centers >= start) & (centers < stop)
    ...
    is_change = bool(np.nan_to_num(presentations["is_change"][idx], nan=0.0))
    if is_change and not omitted:
        change_series[in_window] = 1
```

**What this does:** No additional smoothing or expansion: the binary `change_series` is set to 1 only inside the presentation window flagged `is_change` (not omitted). The output is the raw indicator over the changed-image flash interval.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Image change* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none specific; covered by 5-c general alignment language)

**Code** (convert_data.py:560-561, 574-580):
```python
row_idx = find_presentation_rows(presentations, spec.start_time, spec.stop_time)
image_series, change_series = make_image_series(presentations, row_idx, centers, image_to_idx)
...
output_trial = np.vstack([
    image_series.astype(np.int16),
    change_series.astype(np.int16),
    running_bins,
    pupil_bins,
    outcome_series,
])
```

**What this does:** `change_series` is computed on the same `centers` time grid as the neural data, then stacked into row 1 of `output_trial`, so each bin column aligns with the corresponding neural column.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *Running speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:246: "Running speed timeseries → `output[2]` (`running_speed_bin`)". CONVERSION_NOTES.md:178-179: "computed from wheel encoder voltage ... whitepaper explicitly points to AllenSDK running-processing code".

**Code** (convert_data.py:364-365, 530-531):
```python
running_times = np.asarray(f["/processing/running/speed/timestamps"], dtype=np.float64)
running_values = np.asarray(f["/processing/running/speed/data"], dtype=np.float64)
```

**What this does:** Running speed values are read directly from `/processing/running/speed/data` with timestamps from `/processing/running/speed/timestamps` in the NWB file (already-processed running-wheel speed).

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *Running speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:262: "Running and pupil bin edges will be global, not per-session". CONVERSION_NOTES.md:246: "Interpolate running speed to rebinned trial time axis, then discretize into 5 global percentile bins".

**Code** (convert_data.py:245-260, 337-346, 690-699, 563, 570):
```python
def interpolate_series(times, values, query_times):
    ...
    out = np.interp(query_times, t, v, left=v[0], right=v[-1])
    return out.astype(np.float32)
...
def compute_bin_edges(values, nbins):
    quantiles = np.linspace(0.0, 1.0, nbins + 1)[1:-1]
    edges = np.quantile(values, quantiles)
    return np.asarray(edges, dtype=np.float64)

def discretize_with_edges(values, edges):
    bins = np.digitize(values, edges, right=False)
    bins = np.clip(bins, 0, len(edges))
    return bins.astype(np.int16)
...
running_pool = np.concatenate([p.running_values for p in eligible if p.running_values.size > 0])
running_pool = running_pool[np.isfinite(running_pool)]
...
running_edges = compute_bin_edges(running_pool, 5)
...
running_interp = interpolate_series(running_times, running_values, centers)
...
running_bins = discretize_with_edges(running_interp, running_edges)
```

**What this does:** Running speed is linearly interpolated to each trial's bin centers (with edge values held constant beyond the timestamp range), then discretized into 5 quantile bins whose edges are computed once globally from pooled in-trial samples across all eligible sessions. NaN-interpolated values would error (`Non-finite running interpolation` raise).

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `output` *Running speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:216: "Align converted outputs to ophys timestamps by resampling/interpolating from their native synchronized time bases."

**Code** (convert_data.py:547, 563, 570, 574-580):
```python
starts, ends, centers = build_bin_centers(spec.start_time, spec.stop_time, bin_size_sec)
...
running_interp = interpolate_series(running_times, running_values, centers)
...
running_bins = discretize_with_edges(running_interp, running_edges)
...
output_trial = np.vstack([
    image_series.astype(np.int16),
    change_series.astype(np.int16),
    running_bins,
    pupil_bins,
    outcome_series,
])
```

**What this does:** Running values are evaluated at the same per-trial bin centers used for the neural sums, so per-bin running-bin entries are time-aligned to the corresponding neural columns by sharing the same `centers` time grid.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `output` *Pupil diameter* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:247: "Use processed pupil area after blink filtering, convert to equivalent diameter `2*sqrt(area/pi)`". CONVERSION_NOTES.md:181: "whitepaper states pupil size is derived from ellipse fits; major axis is treated as diameter and area is computed from that diameter".

**Code** (convert_data.py:263-268, 369-376, 532-537):
```python
def pupil_area_to_diameter(area):
    area = np.asarray(area, dtype=np.float64)
    out = np.full(area.shape, np.nan, dtype=np.float64)
    valid = np.isfinite(area) & (area >= 0)
    out[valid] = 2.0 * np.sqrt(area[valid] / np.pi)
    return out.astype(np.float32)
...
pupil_times = np.asarray(f["/acquisition/EyeTracking/eye_tracking/timestamps"], ...)
pupil_area = np.asarray(f["/acquisition/EyeTracking/pupil_tracking/area_raw"], ...)
likely_blink = np.asarray(f["/acquisition/EyeTracking/likely_blink/data"], ...).astype(bool)
pupil_area = pupil_area.copy()
pupil_area[likely_blink] = np.nan
pupil_diameter = pupil_area_to_diameter(pupil_area)
```

**What this does:** Pupil diameter is computed from `/acquisition/EyeTracking/pupil_tracking/area_raw` by converting area to diameter via `2*sqrt(area/pi)`, after masking blink frames (`likely_blink`) to NaN. Timestamps come from `/acquisition/EyeTracking/eye_tracking/timestamps`.

**Rating:** ok

**Note:** uses pupil area to derive diameter instead of width

---

## Q 6-b. What processing is involved in computing `output` *Pupil diameter*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:247: "Use processed pupil area after blink filtering, convert to equivalent diameter ... interpolate to rebinned trial axis, discretize into 5 global percentile bins".

**Code** (convert_data.py:535-537, 564, 567-568, 571, 691-700):
```python
pupil_area[likely_blink] = np.nan
pupil_diameter = pupil_area_to_diameter(pupil_area)
...
pupil_interp = interpolate_series(pupil_times, pupil_diameter, centers)
...
if np.any(~np.isfinite(pupil_interp)):
    raise ValueError(f"Non-finite pupil interpolation in experiment {preview.experiment_id}")
...
pupil_bins = discretize_with_edges(pupil_interp, pupil_edges)
...
pupil_pool = np.concatenate([p.pupil_values for p in eligible if p.pupil_values.size > 0])
pupil_pool = pupil_pool[np.isfinite(pupil_pool)]
...
pupil_edges = compute_bin_edges(pupil_pool, 5)
```

**What this does:** After blink masking and area→diameter conversion, pupil diameter is linearly interpolated to per-trial bin centers and then discretized into 5 quantile bins whose edges are computed globally from the pooled in-trial pupil samples across eligible sessions. The interpolation excludes non-finite samples internally.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. How is `output` *Pupil diameter* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:216: "Align converted outputs to ophys timestamps by resampling/interpolating from their native synchronized time bases."

**Code** (convert_data.py:564, 571, 574-580):
```python
pupil_interp = interpolate_series(pupil_times, pupil_diameter, centers)
...
pupil_bins = discretize_with_edges(pupil_interp, pupil_edges)
...
output_trial = np.vstack([
    image_series.astype(np.int16),
    change_series.astype(np.int16),
    running_bins,
    pupil_bins,
    outcome_series,
])
```

**What this does:** Pupil values are evaluated at the same per-trial bin centers as neural and running, so `pupil_bins` becomes one row of `output_trial` aligned column-by-column with the neural data via the shared `centers` time grid.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:248: "Trial outcome flags `hit`, `miss`, `false_alarm`, `correct_reject` → `output[4]` (`trial_outcome`). Single categorical value per trial".

**Code** (convert_data.py:28, 207-220):
```python
TRIAL_OUTCOME_VALUES = ["hit", "miss", "false_alarm", "correct_reject"]
...
hit = np.nan_to_num(trials["hit"], nan=0.0).astype(bool)
miss = np.nan_to_num(trials["miss"], nan=0.0).astype(bool)
false_alarm = np.nan_to_num(trials["false_alarm"], nan=0.0).astype(bool)
correct_reject = np.nan_to_num(trials["correct_reject"], nan=0.0).astype(bool)
...
outcome_flags = [hit[idx], miss[idx], false_alarm[idx], correct_reject[idx]]
if sum(int(x) for x in outcome_flags) != 1:
    raise ValueError(f"Trial {idx} does not have exactly one valid outcome")
outcome_idx = outcome_flags.index(True)
```

**What this does:** Trial outcome is derived from the four mutually-exclusive boolean columns `hit`, `miss`, `false_alarm`, `correct_reject` in `/intervals/trials`. The fixed code order is `[hit, miss, false_alarm, correct_reject] = [0, 1, 2, 3]`.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:263: "Trial outcome will be repeated across time bins: Although static per-trial, repeating it across the trial keeps every `output` array in `(n_output, n_timepoints)` form."

**Code** (convert_data.py:572, 574-582):
```python
outcome_series = np.full(T, spec.outcome_idx, dtype=np.int16)
...
output_trial = np.vstack([
    image_series.astype(np.int16),
    change_series.astype(np.int16),
    running_bins,
    pupil_bins,
    outcome_series,
])
```

**What this does:** The single per-trial outcome integer (0–3) is broadcast across all `T` bins of the trial via `np.full`, producing a constant row in `output_trial`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:386-391 session-level exclusions; CONVERSION_NOTES.md:454-456: "all neural data is zero" warnings investigated and not fixed because direct raw-NWB reconstruction showed those trials are truly all-zero.

**Code** (convert_data.py:202-210, 263-268, 245-260, 535-537, 565-568, 386-391):
```python
aborted = np.nan_to_num(trials["aborted"], nan=0.0).astype(bool)
auto_rewarded = np.nan_to_num(trials["auto_rewarded"], nan=0.0).astype(bool)
go = np.nan_to_num(trials["go"], nan=0.0).astype(bool)
...
def pupil_area_to_diameter(area):
    ...
    valid = np.isfinite(area) & (area >= 0)
    out[valid] = 2.0 * np.sqrt(area[valid] / np.pi)
...
def interpolate_series(times, values, query_times):
    finite = np.isfinite(times) & np.isfinite(values)
    ...
    out = np.interp(query_times, t, v, left=v[0], right=v[-1])
...
pupil_area[likely_blink] = np.nan
...
if np.any(~np.isfinite(running_interp)):
    raise ValueError(f"Non-finite running interpolation in experiment {preview.experiment_id}")
if np.any(~np.isfinite(pupil_interp)):
    raise ValueError(f"Non-finite pupil interpolation in experiment {preview.experiment_id}")
...
if not has_eye_tracking:
    excluded_reason = "missing_eye_tracking"
elif len(specs) < 2:
    excluded_reason = "fewer_than_2_valid_trials"
elif np.isfinite(pupil_values_all).sum() < 2:
    excluded_reason = "insufficient_valid_pupil_samples"
```

**What this does:** Boolean trial flags use `nan_to_num`. Pupil blinks are masked to NaN before area→diameter conversion; interpolation drops non-finite samples and clamps with edge values. Trials with non-finite interpolated running or pupil raise an error. Sessions are excluded for missing eye tracking, <2 valid trials, or insufficient finite pupil samples. No conversion exception handler wraps full sessions.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:392-396 (Step 9 timings): "Preview pass: `65.0 s`. Conversion pass: `686.0 s`. Total elapsed: `757.7 s`". CONVERSION_NOTES.md:303-306: "Full preview scans all NWB files once and the conversion pass opens them again ... Session conversion currently rebins event data with per-bin slice sums".

> conversion_full_out.txt is also present at the snapshot top level for reference.

**Code** (convert_data.py:553-558, 638-655, 663-675, 715-746):
```python
for spec in preview.trial_specs:
    ...
    neural_trial = np.zeros((n_neurons, T), dtype=np.float32)
    for b in range(T):
        lo = int(frame_starts[b])
        hi = int(frame_ends[b])
        if hi > lo:
            neural_trial[:, b] = event_data[lo:hi].sum(axis=0, dtype=np.float32)
...
for idx, path in enumerate(files, start=1):
    preview = session_preview(path, bin_size_sec)
    ...
preview_start = time.perf_counter()
eligible, excluded = collect_previews(...)
...
log(f"Preview pass completed in {time.perf_counter() - preview_start:.1f}s")
...
convert_start = time.perf_counter()
for i, preview in enumerate(eligible, start=1):
    ...
    neural_trials, input_trials, output_trials, region_idx_arr, stats = convert_session(...)
log(f"Conversion pass completed in {time.perf_counter() - convert_start:.1f}s")
```

**What this does:** The script identifies the conversion pass (per-session HDF5 reads + per-trial per-bin event summation) as dominant in Step 7/9 timings; the preview pass is the second largest cost. Per-session and total elapsed times are logged.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:305-306: "Session conversion currently rebins event data with per-bin slice sums instead of using cumulative sums; this reduces peak memory at the cost of some extra CPU."

**Code** (convert_data.py:553-558):
```python
neural_trial = np.zeros((n_neurons, T), dtype=np.float32)
for b in range(T):
    lo = int(frame_starts[b])
    hi = int(frame_ends[b])
    if hi > lo:
        neural_trial[:, b] = event_data[lo:hi].sum(axis=0, dtype=np.float32)
```

**What this does:** The per-bin Python loop summing event slices is explicitly noted as not vectorized; an `np.add.reduceat` or cumulative-sum approach would replace it. The notes acknowledge this is a deliberate memory-vs-speed tradeoff.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:296-298, 304: "Uses a two-pass workflow: 1. lightweight preview pass ... 2. conversion pass". "Full preview scans all NWB files once and the conversion pass opens them again; this is intentional to avoid storing large neural matrices before global percentile/bin definitions are known."

**Code** (convert_data.py:349-408 (preview), 515-615 (convert), 668-674, 716-744):
```python
def session_preview(path, bin_size_sec):
    with h5py.File(path, "r") as f:
        ...
        running_times = np.asarray(f["/processing/running/speed/timestamps"], ...)
        ...
        return SessionPreview(...)

def convert_session(preview, ...):
    with h5py.File(preview.path, "r") as f:
        ophys_timestamps = np.asarray(f["/processing/ophys/dff/traces/timestamps"], ...)
        event_data, _ = load_neural_events(f)
        running_times = np.asarray(f["/processing/running/speed/timestamps"], ...)
        ...
```

**What this does:** Each NWB file is opened twice: once during the preview pass (trials, running, pupil for global stats) and once during the conversion pass (full neural plus re-reads of running/pupil/trials/presentations). The notes call this intentional.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — no explicit discussion of discarded computation)

**Code** (convert_data.py:152-198, 583, 422-512):
```python
def read_task_presentations(f):
    ...
    keep_names = ["start_time", "stop_time", "image_name", "omitted", "is_change",
                  "is_sham_change", "trials_id", "active"]
    ...
input_trial = np.empty((0, T), dtype=np.float32)
...
def plot_processing_summary(...):
    # generates 5-panel diagnostic PNGs per selected experiment
```

**What this does:** `read_task_presentations` reads `is_sham_change`, `trials_id`, and `active` columns that are not used downstream (only `image_name`, `start_time`, `stop_time`, `omitted`, `is_change` are consumed). Empty `(0, T)` `input_trial` arrays are created per trial (no inputs requested). Diagnostic plotting (`--show-processing`) generates PNGs that are not part of the converted pickle.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:309: "Conversion uses direct dataset reads and processes one session at a time to cap peak memory." CONVERSION_NOTES.md:305: per-bin slice sums "reduces peak memory at the cost of some extra CPU."

**Code** (convert_data.py:411-419, 525-538, 553-558, 716-746):
```python
def load_neural_events(f):
    event_data = np.asarray(f["/processing/ophys/event_detection/data"], dtype=np.float32)
    ...
    valid_mask = valid_roi[event_rois]
    event_data = event_data[:, valid_mask]
    return event_data, event_rois[valid_mask]
...
with h5py.File(preview.path, "r") as f:
    ophys_timestamps = ...
    event_data, _ = load_neural_events(f)
    ...
# session HDF5 file closes after the with-block; per-trial outputs accumulate
for spec in preview.trial_specs:
    ...
    neural_trial = np.zeros((n_neurons, T), dtype=np.float32)
    for b in range(T):
        ...
        neural_trial[:, b] = event_data[lo:hi].sum(axis=0, dtype=np.float32)
```

**What this does:** Each session is opened, processed, and closed before the next; raw event arrays drop out of scope after the session's `with` block. Neural arrays are stored as `float32`. The preview pass deliberately avoids loading neural events. Per-bin summation streams over `event_data` slices rather than allocating a full per-trial expansion.

**Rating:** ok

**Note:** _(no note)_

---
