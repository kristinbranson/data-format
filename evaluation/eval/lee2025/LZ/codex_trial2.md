# lee2025 — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/lee2025/codex/2026-03-11__11-30-50_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Load per-animal joblib files from `data/`." (README.md:22); CONVERSION_NOTES.md:75-91 documents joblib animal files with fields `SFPs`, `blocked`, `centroids`, `envs`, `maps`, `position`, `trace`.

**Code** (convert_data.py:90-101, 460-466):
```python
def get_animal_files(data_dir):
    animals = []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if (
            os.path.isfile(path)
            and not name.endswith(".mat")
            and name not in {"behav_dict"}
            and not name.startswith(".")
        ):
            animals.append(name)
    return animals
...
for animal in selected_animals:
    animal_path = os.path.join(data_dir, animal)
    dat = joblib.load(animal_path)[animal]
```

**What this does:** Lists non-`.mat`, non-`behav_dict` files in `data/` as animal IDs, then loads each animal's joblib file via `joblib.load`, indexed by animal name to retrieve the per-animal dictionary containing `trace`, `position`, `blocked`, `envs`, etc.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "animal ID → `subjects`; `subject_idx`: Unique list of mouse IDs; session-level index into list" (CONVERSION_NOTES.md:200)

**Code** (convert_data.py:504, 555-556):
```python
subject_idx.append(animals.index(animal))
...
"subjects": animals,
"subject_idx": np.array(subject_idx, dtype=np.int64),
```

**What this does:** Each filename in `data/` (e.g. `QLAK-CA1-08`) is treated as a subject ID; per-session subject indices reference the subject list by position.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Joblib files expose `trace (sessions, cells, frames)` and `position (n_sessions, 2, n_frames)` (CONVERSION_NOTES.md:89-90); session loop iterates `dat["position"].shape[0]`.

**Code** (convert_data.py:474-492):
```python
for session_idx in range(dat["position"].shape[0]):
    ...
    session_id = f"{animal}_s{session_idx:02d}"
    env_name = str(dat["envs"][session_idx, 0])
    session_neural, session_input, session_output, ... = preprocess_session(
        trace_session=dat["trace"][session_idx],
        position_session=dat["position"][session_idx],
        blocked_entry=dat["blocked"][session_idx],
        ...
    )
```

**What this does:** Iterates over the leading session axis of the per-animal arrays (`position`, `trace`, `blocked`), processing each as one output session and labeling it `<animal>_s<idx>`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Split each continuous session into consecutive 1-minute chunks." (README.md:26); "8187 derived one-minute trials using floor(`n_frames / 1800`) per session" (CONVERSION_NOTES.md:104).

**Code** (convert_data.py:18-21, 249, 256-261):
```python
FPS = 30
SESSION_SECONDS = 40 * 60
TRIAL_SECONDS = 60
RAW_TRIAL_FRAMES = FPS * TRIAL_SECONDS
...
n_full_trials = trace_session.shape[1] // RAW_TRIAL_FRAMES
...
for trial_idx in range(n_full_trials):
    start = trial_idx * RAW_TRIAL_FRAMES
    end = start + RAW_TRIAL_FRAMES
    chunk_mask = velocity_mask[start:end]
    if int(chunk_mask.sum()) < POOL_SIZE:
        continue
```

**What this does:** Splits each session into `floor(n_frames / 1800)` non-overlapping 60-second (1800-frame) chunks; trailing remainder frames are dropped. Trials with too few movement-valid frames are skipped.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "excluding trials with fewer than 10 pooled samples or no processed neural activity" (CONVERSION_NOTES.md:280, 342); "fewer than 2 valid trials" causes session error (code).

**Code** (convert_data.py:259-276, 316-317):
```python
chunk_mask = velocity_mask[start:end]
if int(chunk_mask.sum()) < POOL_SIZE:
    continue
...
if pooled_trace.shape[1] < MIN_POOLED_SAMPLES_PER_TRIAL:
    continue
if not np.any(pooled_trace):
    continue
...
if len(neural_trials) < 2:
    raise ValueError(f"{session_id}: fewer than 2 valid trials after preprocessing")
```

**What this does:** Drops trials whose movement-valid frame count is less than the pool size, whose pooled length is below 10 samples, or whose pooled neural activity is all zero. Sessions yielding fewer than 2 trials raise an error.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural data are rise-extracted calcium-event traces from hippocampal CA1." (README.md:12); "trace[session, valid_cells, frame] → neural[session][trial]" (CONVERSION_NOTES.md:197).

**Code** (convert_data.py:482-483):
```python
session_neural, session_input, session_output, ... = preprocess_session(
    trace_session=dat["trace"][session_idx],
    ...
)
```

**What this does:** Final neural data derive from the per-animal `trace` array (binary rising-phase calcium events) indexed by session.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Within each chunk, keep movement-valid frames, smooth neural traces, and average-pool every 3 frames." (README.md:27); "Gaussian smoothing of traces; non-overlapping 3-frame average pooling." (CONVERSION_NOTES.md:243-244).

**Code** (convert_data.py:263-268):
```python
chunk_trace = trace_active[:, start:end][:, chunk_mask]
...
chunk_trace = gaussian_filter1d(chunk_trace, sigma=TRACE_SMOOTH_SIGMA, axis=1, mode="nearest")
pooled_trace = trial_average_pool(chunk_trace).astype(np.float32, copy=False)
```

**What this does:** Per trial: select cells already filtered for finiteness/activity, apply velocity mask to keep only movement-valid frames, Gaussian smooth (sigma=3 frames) along time, then non-overlapping 3-frame average pool. Output stored as `(n_active, n_pooled)` float32.

**Rating:** better

**Note:** The agent used additional processing steps used in the paper

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Drop cells with any NaNs within a session before applying the activity filter" (CONVERSION_NOTES.md:209); "session-level low-activity cell filtering (`>5` events during movement-valid frames)" (CONVERSION_NOTES.md:241).

**Code** (convert_data.py:226-234):
```python
finite_cells = np.isfinite(trace_session).all(axis=1)
trace_finite = trace_session[finite_cells].astype(np.float32, copy=False)
if trace_finite.size == 0:
    raise ValueError(f"{session_id}: no finite cells after NaN filtering")

activity_mask = np.sum(trace_finite[:, velocity_mask], axis=1) > CELL_EVENT_THRESHOLD
trace_active = trace_finite[activity_mask]
```

**What this does:** Removes cells with any NaN values across the session, then drops cells whose total event count during movement-valid frames is at most `CELL_EVENT_THRESHOLD` (=5).

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "average-pool every 3 frames"; metadata `time_bin_size: 100.0` (ms) reflects 30 Hz × 3-frame pooling.

**Code** (convert_data.py:22, 130-136, 567):
```python
POOL_SIZE = 3
...
def trial_average_pool(values, pool_size=POOL_SIZE):
    n_full = values.shape[-1] // pool_size
    if n_full <= 0:
        return values[..., :0]
    trimmed = values[..., : n_full * pool_size]
    new_shape = values.shape[:-1] + (n_full, pool_size)
    return trimmed.reshape(new_shape).mean(axis=-1)
...
"time_bin_size": 100.0,
```

**What this does:** After velocity masking and Gaussian smoothing, frames are grouped into non-overlapping 3-frame windows and averaged, yielding ~10 Hz (100 ms) effective temporal bins.

**Rating:** ok

**Note:** followed the processing in the paper

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Metadata sets `temporal_alignment_event: "Start of each consecutive one-minute chunk from a continuous recording session"` (convert_data.py:568).

**Code** (convert_data.py:256-263, 568):
```python
for trial_idx in range(n_full_trials):
    start = trial_idx * RAW_TRIAL_FRAMES
    end = start + RAW_TRIAL_FRAMES
    chunk_mask = velocity_mask[start:end]
    ...
"temporal_alignment_event": "Start of each consecutive one-minute chunk from a continuous recording session",
```

**What this does:** Each trial is anchored to the start of a consecutive 60-second segment of the continuous recording; no external stimulus event is used for alignment.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use raw `blocked` partitions to build decoder inputs." (CONVERSION_NOTES.md:210); "blocked[session] → input[session][trial]" (CONVERSION_NOTES.md:198).

**Code** (convert_data.py:485, 104-119):
```python
blocked_entry=dat["blocked"][session_idx],
...
def parse_blocked_indices(blocked_entry):
    if isinstance(blocked_entry, list):
        if len(blocked_entry) == 0:
            return np.array([], dtype=np.int64)
        blocked_entry = blocked_entry[0]
    arr = np.array(blocked_entry, dtype=np.float64).reshape(-1)
    if arr.size == 1 and arr[0] < 0:
        return np.array([], dtype=np.int64)
    return np.sort(arr.astype(np.int64))

def blocked_to_open_vector(blocked_entry):
    blocked_idx = parse_blocked_indices(blocked_entry)
    open_vec = np.ones(GEOMETRY_SIZE * GEOMETRY_SIZE, dtype=np.float32)
    open_vec[blocked_idx] = 0.0
    return open_vec, blocked_idx
```

**What this does:** Input derives from the per-session `blocked` field (list of blocked partition indices, or `[-1]` for none) in the joblib animal file.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Encode geometry as 9 binary partition features. ... `1 = open`, `0 = blocked`" (CONVERSION_NOTES.md:211); README.md:43-46.

**Code** (convert_data.py:115-119, 286, 559):
```python
def blocked_to_open_vector(blocked_entry):
    blocked_idx = parse_blocked_indices(blocked_entry)
    open_vec = np.ones(GEOMETRY_SIZE * GEOMETRY_SIZE, dtype=np.float32)
    open_vec[blocked_idx] = 0.0
    return open_vec, blocked_idx
...
input_trials.append(geometry_open.copy())
...
"input_names": [f"partition_{idx}_open" for idx in range(GEOMETRY_SIZE * GEOMETRY_SIZE)],
```

**What this does:** Builds a static length-9 vector per session: 1 for open partitions, 0 for blocked partitions (row-major 3x3 order). The same vector is appended once per trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Blocked positions* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Same vector repeated conceptually for every time point, but stored as static per-trial input." (CONVERSION_NOTES.md:198).

**Code** (convert_data.py:285-286):
```python
neural_trials.append(pooled_trace)
input_trials.append(geometry_open.copy())
```

**What this does:** The geometry vector is appended once per trial with shape `(9,)`, treated as static context for the entire trial rather than time-varying.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "position[session, :, frame] → output[session][trial]" (CONVERSION_NOTES.md:199).

**Code** (convert_data.py:484):
```python
position_session=dat["position"][session_idx],
```

**What this does:** Output position derives from the `position` array (x,y per frame) in each animal's joblib file.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "discretize position to aligned 3 x 3 bins, snap blocked bins to nearest open bin, average-pool coordinates in 3-frame groups, and collapse to a 9-class categorical index" (CONVERSION_NOTES.md:199).

**Code** (convert_data.py:122-127, 166-190, 264-283):
```python
def raw_position_to_rc(position_xy, bin_size_cm):
    x = np.floor(position_xy[0] / bin_size_cm).astype(np.int64)
    y = np.floor(position_xy[1] / bin_size_cm).astype(np.int64)
    x = np.clip(x, 0, GEOMETRY_SIZE - 1)
    y = np.clip(y, 0, GEOMETRY_SIZE - 1)
    return y, x
...
def infer_transform(position_all, blocked_all, scale_cm):
    # picks rotation/flip per animal that minimizes occupancy in blocked bins
...
chunk_rows = snapped_rows_all[start:end][chunk_mask]
chunk_cols = snapped_cols_all[start:end][chunk_mask]
...
pooled_rows = np.floor(trial_average_pool(chunk_rows[np.newaxis, :].astype(np.float32))[0]).astype(np.int64)
pooled_cols = np.floor(trial_average_pool(chunk_cols[np.newaxis, :].astype(np.float32))[0]).astype(np.int64)
...
invalid = geometry_mat[pooled_rows, pooled_cols] == 0
if np.any(invalid):
    pooled_rows, pooled_cols = snap_to_open_bins(pooled_rows, pooled_cols, geometry_open)
pooled_bins = (pooled_rows * GEOMETRY_SIZE + pooled_cols)[np.newaxis, :].astype(np.int64)
```

**What this does:** Discretizes (x,y) into a 3x3 grid using a per-animal scale (`max(position)`) and a per-animal inferred rotation/flip transform that aligns occupancy with the blocked geometry; samples in blocked bins are snapped to the nearest open bin; positions are velocity-masked, pool-averaged in 3-frame windows, re-snapped if needed, and stored as `(1, n_pooled)` row-major bin indices 0..8.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Output is time-varying and uses the same temporally pooled samples as the neural data." (CONVERSION_NOTES.md:199).

**Code** (convert_data.py:263-270, 285-287):
```python
chunk_trace = trace_active[:, start:end][:, chunk_mask]
chunk_rows = snapped_rows_all[start:end][chunk_mask]
chunk_cols = snapped_cols_all[start:end][chunk_mask]
...
pooled_trace = trial_average_pool(chunk_trace)...
pooled_rows = np.floor(trial_average_pool(chunk_rows...))...
...
neural_trials.append(pooled_trace)
input_trials.append(geometry_open.copy())
output_trials.append(pooled_bins)
```

**What this does:** Both neural and position streams use the same trial slice, the same velocity mask, and the same 3-frame pooling, ensuring frame-by-frame alignment in the pooled output.

**Rating:** match

**Note:** _(no note)_

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Drop cells with any NaNs within a session"; "Snap blocked-bin position samples to the nearest open partition before export" (CONVERSION_NOTES.md:209-210); "excluding trials with fewer than 10 pooled samples or no processed neural signal" (CONVERSION_NOTES.md:342).

**Code** (convert_data.py:193-207, 226-234, 272-282):
```python
def snap_to_open_bins(row_idx, col_idx, geometry_open):
    ...
    for i in range(row_idx.shape[0]):
        if geometry_mat[row_idx[i], col_idx[i]] == 1:
            continue
        distances = np.sum((open_coords - np.array([row_idx[i], col_idx[i]])) ** 2, axis=1)
        nearest = open_coords[np.argmin(distances)]
        ...
finite_cells = np.isfinite(trace_session).all(axis=1)
...
if pooled_trace.shape[1] < MIN_POOLED_SAMPLES_PER_TRIAL:
    continue
if not np.any(pooled_trace):
    continue
```

**What this does:** Cells with NaNs are dropped per session; positions falling in blocked bins are snapped to the nearest open bin; trials with too few pooled samples or no neural events are skipped; remainder frames not filling 1800 are discarded.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Animal joblib loads are relatively slow (roughly tens of seconds per animal)" (CONVERSION_NOTES.md:249); "first animal load ~62.46 s; ~1.67 s/session afterward" (CONVERSION_NOTES.md:292).

**Code** (convert_data.py:464-467):
```python
animal_load_start = time.time()
dat = joblib.load(animal_path)[animal]
load_seconds = time.time() - animal_load_start
print(f"  loaded in {load_seconds:.2f}s")
```

**What this does:** Primary bottleneck is `joblib.load` of the per-animal files; per-session preprocessing is fast by comparison. Times are logged.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Moved heavy preprocessing to vectorized NumPy/Scipy operations." (CONVERSION_NOTES.md:251). No explicit residual loops flagged.

**Code** (convert_data.py:200-207, 256-288):
```python
for i in range(row_idx.shape[0]):
    if geometry_mat[row_idx[i], col_idx[i]] == 1:
        continue
    distances = np.sum((open_coords - np.array([row_idx[i], col_idx[i]])) ** 2, axis=1)
    ...
for trial_idx in range(n_full_trials):
    start = trial_idx * RAW_TRIAL_FRAMES
    ...
```

**What this does:** Per-frame `snap_to_open_bins` loop and the per-trial preprocessing loop are explicit Python loops; the trial loop performs Gaussian smoothing and pooling per trial rather than vectorized across trials.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Performs one transform inference per animal instead of per session." (CONVERSION_NOTES.md:252).

**Code** (convert_data.py:236-247, 264-265):
```python
raw_rows_all, raw_cols_all = raw_position_to_rc(position_session, bin_size_cm)
raw_ids_all = raw_rows_all * GEOMETRY_SIZE + raw_cols_all
mapped_ids_all = coord_map[raw_ids_all]
mapped_rows_all = mapped_ids_all // GEOMETRY_SIZE
mapped_cols_all = mapped_ids_all % GEOMETRY_SIZE
snapped_rows_all, snapped_cols_all = snap_to_open_bins(mapped_rows_all, mapped_cols_all, geometry_open)
occupancy_raw = occupancy_matrix(position_session, bin_size_cm)
...
chunk_rows = snapped_rows_all[start:end][chunk_mask]
chunk_cols = snapped_cols_all[start:end][chunk_mask]
```

**What this does:** Position binning and snap-to-open are computed once per session over all frames; per-trial loop slices into the precomputed arrays. Occupancy matrices `occupancy_aligned` and `occupancy_snapped` are computed only for plotting payloads but always (not gated on `--show-processing`).

**Rating:** match

**Note:** _(no note)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> No explicit notes about unnecessary discarded processing.

**Code** (convert_data.py:242-247, 290-314, 322-410):
```python
occupancy_raw = occupancy_matrix(position_session, bin_size_cm)
occupancy_aligned = np.zeros_like(occupancy_raw)
np.add.at(occupancy_aligned, (mapped_rows_all, mapped_cols_all), 1)
occupancy_snapped = np.zeros_like(occupancy_raw)
np.add.at(occupancy_snapped, (snapped_rows_all, snapped_cols_all), 1)
...
if plot_payload is None:
    plot_payload = SessionPlotPayload(...)  # always built; only used if --show-processing
...
def save_processing_plot(payload):
    # produces PNG visualizations
```

**What this does:** Builds occupancy matrices and a full `SessionPlotPayload` (with copies of raw trial neural/position arrays) for every session even when `--show-processing` is off; only the first two are actually plotted. The plotting/visualization pathway is not consumed by the decoder.

**Rating:** match

**Note:** _(no note)_

---
