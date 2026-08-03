# lee2025 — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/lee2025/codex/2026-03-11__11-30-50_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`data/` contains 7 primary subject datasets, each available in two formats: joblib file with subject name only, e.g. `data/QLAK-CA1-08`" (lines 64-66)
> "Use primary joblib animal files, not cached analysis results: This matches the reference loading path in `load_dat(..., format=\"joblib\")`" (line 188)

**Code** (convert_data.py:52-77):
```python
def get_animal_ids(data_dir: str) -> list[str]:
    return sorted(
        filename
        for filename in os.listdir(data_dir)
        if filename.startswith("QLAK-CA1-") and "." not in filename
    )

def load_animal_dataset(data_dir: str, animal: str) -> dict:
    return joblib.load(os.path.join(data_dir, animal))[animal]

def iter_session_refs(data_dir: str, sample: bool) -> tuple[list[str], list[SessionRef]]:
    animals = get_animal_ids(data_dir)
    session_refs: list[SessionRef] = []
    for animal in animals:
        dat = load_animal_dataset(data_dir, animal)
        for day_index in range(dat["envs"].shape[0]):
            session_refs.append(SessionRef(animal=animal, day_index=day_index))
```

**What this does:** Lists per-animal joblib files (no extension) in `data/`, loads each with `joblib.load`, and enumerates sessions by iterating the `envs` first dimension for each animal. Each animal file is then re-loaded once during processing and cached in `animal_cache` (lines 291-298).

**Rating:** ok

**Note:** agent loads the extension-less data files with joblib.load, while manual uses the mat file

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:184):
> "Animal file name / key | `subjects`, `subject_idx` | Unique sorted subject IDs; one target session per original recording day"

**Code** (convert_data.py:52-58, 259):
```python
def get_animal_ids(data_dir: str) -> list[str]:
    return sorted(
        filename
        for filename in os.listdir(data_dir)
        if filename.startswith("QLAK-CA1-") and "." not in filename
    )
...
subject_lookup = {animal: idx for idx, animal in enumerate(animals)}
```

**What this does:** Each subject corresponds to one joblib file matching `QLAK-CA1-*` with no extension. Subject IDs are the file names; `subject_idx` is the index into the sorted animal list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:189):
> "Keep one target session per original recording day: The raw data are organized by day/session, and the target format supports multiple trials within each session."

**Code** (convert_data.py:64-77, 188-192):
```python
for animal in animals:
    dat = load_animal_dataset(data_dir, animal)
    for day_index in range(dat["envs"].shape[0]):
        session_refs.append(SessionRef(animal=animal, day_index=day_index))
...
day = session_ref.day_index
env_name = str(dat["envs"][day, 0])
position_day = np.asarray(dat["position"][day], dtype=np.float64)
trace_day = np.asarray(dat["trace"][day], dtype=np.float64)
```

**What this does:** Sessions are enumerated by iterating `day_index` from `0` to `dat["envs"].shape[0]-1` per animal. Per-session arrays (`position`, `trace`, `maps`) are indexed by `day`. Session ID is `f"{animal}_day{day:02d}"`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:190):
> "Create trials by splitting each continuous 40-minute session into non-overlapping 1-minute windows: ... Trial length will be exactly 1800 frames at 30 Hz; any trailing partial minute will be discarded."

**Code** (convert_data.py:16-18, 116-118):
```python
FPS = 30.0
TRIAL_SECONDS = 60
TRIAL_FRAMES = int(FPS * TRIAL_SECONDS)
...
def trial_slices(n_frames: int, trial_frames: int = TRIAL_FRAMES) -> list[slice]:
    n_trials = n_frames // trial_frames
    return [slice(i * trial_frames, (i + 1) * trial_frames) for i in range(n_trials)]
```

**What this does:** Splits each continuous session into non-overlapping 1800-frame (60 s at 30 Hz) windows via integer division; tail frames are discarded. Same slices are reused for `neural` and `output`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt:** No trial-level QC filtering described. CONVERSION_NOTES.md:208 states "all sessions had at least 2 trials" as the only trial-count check; sessions with `< 2` trials would raise.

**Code** (convert_data.py:208-209):
```python
if len(slices) < 2:
    raise ValueError(f"{session_ref.session_id}: fewer than 2 full 1-minute trials available")
```

**What this does:** No per-trial quality filtering. The only check rejects an entire session if it produces fewer than 2 full trials.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:181):
> "`dat[animal]['trace'][day, present_cells, frame_start:frame_end]` | `neural` | Keep session-present cells only ... No delta-F/F. Use released binary rising-phase event traces directly."

**Code** (convert_data.py:191, 215):
```python
trace_day = np.asarray(dat["trace"][day], dtype=np.float64)
...
session_trace = trace_day[present_mask].astype(np.float16, copy=False)
```

**What this does:** `neural` is derived from the `trace` field of the per-animal joblib dictionary, indexed by `day_index`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:193):
> "Do not compute new calcium features: The released `trace` is already the binary rising-phase representation used in the paper/code."

**Code** (convert_data.py:215-219):
```python
session_trace = trace_day[present_mask].astype(np.float16, copy=False)
for trial_slice in slices:
    neural_trial = session_trace[:, trial_slice].astype(np.float16, copy=False)
    ...
    neural_trials.append(neural_trial)
```

**What this does:** After NaN-cell removal, the trace is cast to `float16` and sliced per trial. No further smoothing, deconvolution, or normalization is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:191):
> "Use all session-present cells: This matches the paper's statement that all cells were included in subsequent analyses. Cells absent on a day are removed by excluding `NaN` rows for that session."

**Code** (convert_data.py:98-99, 194-196):
```python
def session_present_cell_mask(trace_day: np.ndarray) -> np.ndarray:
    return ~np.isnan(trace_day[:, 0])
...
present_mask = session_present_cell_mask(trace_day)
if not np.any(present_mask):
    raise ValueError(f"{session_ref.session_id}: no present cells after NaN filtering")
```

**What this does:** A neuron is considered present in a session if its first frame in `trace` is not NaN; absent cells are dropped. No place-cell or activity-based filtering is applied.

**Rating:** ok

**Note:** agent uses first time point, manual checks all timepoints, spotchecked that these are the same

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (convert_data.py:276-278 metadata):
> `"temporal_alignment_event": "start of each non-overlapping 1-minute within-session segment"`, `off_start=0.0`, `off_end=60.0`.

**Code** (convert_data.py:116-118, 215-219):
```python
def trial_slices(n_frames: int, trial_frames: int = TRIAL_FRAMES) -> list[slice]:
    n_trials = n_frames // trial_frames
    return [slice(i * trial_frames, (i + 1) * trial_frames) for i in range(n_trials)]
...
for trial_slice in slices:
    neural_trial = session_trace[:, trial_slice].astype(np.float16, copy=False)
```

**What this does:** No external event alignment; trials are 1-minute contiguous windows aligned to the start of each segment within a continuous session.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:182):
> Mapping table — no temporal resampling listed. Metadata sets `time_bin_size = 1000.0/FPS` (≈33.33 ms).

**Code** (convert_data.py:16, 275):
```python
FPS = 30.0
...
"time_bin_size": 1000.0 / FPS,
```

**What this does:** The native 30 Hz frame rate is preserved; no temporal binning or resampling is applied to `neural`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:182):
> "`dat[animal]['blocked'][day]` | `input[trial]` | Convert blocked partition IDs to 3x3 binary open/blocked matrix, transpose to align with map/position axes, flatten to 9-dim float vector"

**Code** (convert_data.py:80-95, 198):
```python
def extract_day_blocked_entry(blocked_list: list, day_index: int) -> np.ndarray:
    entry = blocked_list[day_index]
    if isinstance(entry, list) and len(entry) == 1:
        entry = entry[0]
    return np.atleast_1d(np.asarray(entry)).astype(int)
...
geometry_grid, geometry_vector = blocked_to_geometry_vector(dat["blocked"], day)
```

**What this does:** Input is derived from `dat["blocked"][day]`, the per-day list of blocked partition IDs in the README's 3x3 indexing scheme.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

**Notes excerpt** (CONVERSION_NOTES.md:194):
> "Align geometry input to the map/position frame by transposing the 3x3 blocked matrix: This is required for asymmetric geometries and was verified against the non-NaN support of `maps['smoothed']` for every session."

**Code** (convert_data.py:87-95, 199-203):
```python
def blocked_to_geometry_vector(blocked_list, day_index):
    blocked = extract_day_blocked_entry(blocked_list, day_index)
    geometry = np.ones(GEOMETRY_BINS * GEOMETRY_BINS, dtype=np.float32)
    if not (blocked.size == 1 and blocked[0] == -1):
        geometry[blocked] = 0.0
    geometry_grid = geometry.reshape(GEOMETRY_BINS, GEOMETRY_BINS).T.astype(np.float32)
    return geometry_grid, geometry_grid.reshape(-1).astype(np.float32)
...
valid_grid = aggregate_valid_map(smoothed_day)
if not np.array_equal(geometry_grid, valid_grid):
    raise ValueError(...)
```

**What this does:** Builds a length-9 float32 vector with `1.0` for open partitions and `0.0` for blocked ones (`-1` means none blocked). The 3x3 grid is transposed before flattening to align with map/position axes, and is cross-checked against the valid mask of `maps['smoothed']`.

**Rating:** ok

**Note:** uses 1 for accessible, 0 for blocked

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:183):
> "`dat[animal]['position'][day, :, frame_start:frame_end]` | `output[trial]` | Compute 3x3 spatial bins ..."

**Code** (convert_data.py:190, 205):
```python
position_day = np.asarray(dat["position"][day], dtype=np.float64)
...
position_bins, output_class = compute_position_bins(position_day)
```

**What this does:** Output is derived from the `position` field indexed by `day`, giving the continuous (x,y) trajectory for the session.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Position*?

**Notes excerpt** (CONVERSION_NOTES.md:195):
> "Use session-wide position normalization when binning to 3x3 outputs: The reference code bins position using maxima from the full session/day, not from smaller windows."

**Code** (convert_data.py:102-108):
```python
def compute_position_bins(position_day, n_bins=POSITION_BINS):
    coords = np.asarray(position_day, dtype=np.float64).T
    scale = (np.nanmax(coords, axis=0) + POSITION_BUFFER) / float(n_bins)
    binned = np.floor(coords / scale).astype(np.int64)
    binned = np.clip(binned, 0, n_bins - 1)
    class_idx = (binned[:, 0] * n_bins + binned[:, 1]).astype(np.int64)
    return binned, class_idx
```

**What this does:** Position is divided per-axis by `(session_max + 1e-5) / 3`, floored to integer bins, clipped to `[0, 2]`, and combined into a single 9-class label `xbin*3 + ybin`. Stored as `int8` with shape `(1, T)` per trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-d. How is `output` *Position* aligned with the neural data?

**Notes excerpt:** Both `position` and `trace` are at 30 Hz (CONVERSION_NOTES.md:122-123); same trial slices are used for both.

**Code** (convert_data.py:206-218):
```python
n_frames = position_day.shape[1]
slices = trial_slices(n_frames)
...
for trial_slice in slices:
    neural_trial = session_trace[:, trial_slice].astype(np.float16, copy=False)
    output_trial = output_class[trial_slice][np.newaxis, :].astype(np.int8, copy=False)
```

**What this does:** Per-frame alignment is implicit in the raw data (both at 30 Hz); the same slice indices are applied to both `output_class` and `session_trace`.

**Rating:** match

**Note:** _(no note)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:330-334):
> "discarded_tail_frames values were exactly the raw remainders [60, 71, 91, 219, 1666]; all converted trials had length 1800; ... no NaN/Inf values remained in neural, input, or output arrays"

**Code** (convert_data.py:98-99, 117, 194-203, 251):
```python
def session_present_cell_mask(trace_day):
    return ~np.isnan(trace_day[:, 0])
...
n_trials = n_frames // trial_frames
...
if not np.any(present_mask):
    raise ValueError(...)
geometry_grid, valid_grid = ...
if not np.array_equal(geometry_grid, valid_grid):
    raise ValueError(...)
...
"discarded_tail_frames": int(n_frames - len(slices) * TRIAL_FRAMES),
```

**What this does:** NaN rows in `trace` (cells absent on a day) are dropped; trailing frames not filling a full 1-minute trial are discarded and recorded as `discarded_tail_frames`. Sessions with no present cells, fewer than 2 full trials, or where the blocked geometry disagrees with the maps' valid mask raise `ValueError`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:223-228, 261-269):
> "Loading the full animal files is the main runtime cost because each file contains all sessions and registered cells for one subject." Sample timing: ~6.51 s/session over 2 sessions; refined estimate ~2-3 s/session effective.

**Code** (convert_data.py:292-320):
```python
total_start = time.time()
for session_index, session_ref in enumerate(session_refs):
    session_start = time.time()
    if session_ref.animal not in animal_cache:
        animal_cache.clear()
        gc.collect()
        animal_cache[session_ref.animal] = load_animal_dataset(data_dir, session_ref.animal)
    ...
    elapsed = time.time() - session_start
    print(f"Processed {session_ref.session_id}: ...{elapsed:.2f}s")
```

**What this does:** Per-session timing is printed; loading the per-animal joblib file is the dominant cost and is amortized via an `animal_cache` that holds one animal at a time.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt:** None explicitly; speedups noted include slicing full-session binned outputs directly (CONVERSION_NOTES.md:229).

**Code** (convert_data.py:216-221):
```python
for trial_slice in slices:
    neural_trial = session_trace[:, trial_slice].astype(np.float16, copy=False)
    output_trial = output_class[trial_slice][np.newaxis, :].astype(np.int8, copy=False)
    neural_trials.append(neural_trial)
    input_trials.append(geometry_vector.copy())
    output_trials.append(output_trial)
```

**What this does:** Per-trial loop slices precomputed session-wide arrays into trial chunks; binning and present-cell masking are computed once per session outside the loop.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md:228):
> "Reuse one loaded animal dataset across all of its sessions before releasing it."

**Code** (convert_data.py:64-77, 295-298):
```python
def iter_session_refs(data_dir: str, sample: bool):
    animals = get_animal_ids(data_dir)
    session_refs = []
    for animal in animals:
        dat = load_animal_dataset(data_dir, animal)
        for day_index in range(dat["envs"].shape[0]):
            session_refs.append(SessionRef(animal=animal, day_index=day_index))
...
if session_ref.animal not in animal_cache:
    animal_cache.clear()
    gc.collect()
    animal_cache[session_ref.animal] = load_animal_dataset(data_dir, session_ref.animal)
```

**What this does:** Each animal's joblib file is loaded twice — once during enumeration in `iter_session_refs` (then released) and again during processing (cached across that animal's sessions).

**Rating:** concerning

**Note:** loading files is slow, loading twice is unnecessary

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt:** None marked explicitly. The script computes `valid_grid` from `maps['smoothed']` purely as a consistency check (raises if mismatched) and optionally renders processing plots.

**Code** (convert_data.py:111-113, 199-203, 222-234):
```python
def aggregate_valid_map(smoothed_maps_day):
    valid_mask = np.any(~np.isnan(smoothed_maps_day), axis=2).astype(np.float32)
    return valid_mask.reshape(3, 5, 3, 5).max(axis=(1, 3))
...
valid_grid = aggregate_valid_map(smoothed_day)
if not np.array_equal(geometry_grid, valid_grid):
    raise ValueError(...)
...
if show_processing and session_ref.session_id in plot_session_ids:
    plot_processing_figure(...)
```

**What this does:** `aggregate_valid_map` loads and reduces the `maps['smoothed']` 15x15-per-cell array purely to validate the geometry vector; the result is not stored in the output. Plot generation is gated on `--show-processing`.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:227-230 — "Process sessions animal-by-animal so only one large subject file is kept in memory at a time. / Reuse one loaded animal dataset across all of its sessions before releasing it. / Slice full-session binned outputs and present-cell traces directly without redundant recomputation inside trials. / Store neural trials as `float16` and outputs as `int8` to reduce disk footprint and improve the chances that the full dataset remains tractable during downstream validation."
>
> CONVERSION_NOTES.md:264 — "Save neural trials as `float16` instead of `float32` | Reduced `sample_data.pkl` from about 92 MB to 46 MB"

**Code** (convert_data.py:190-192, 215-221, 291-298):
```python
    position_day = np.asarray(dat["position"][day], dtype=np.float64)
    trace_day = np.asarray(dat["trace"][day], dtype=np.float64)
    smoothed_day = np.asarray(dat["maps"]["smoothed"][:, :, :, day], dtype=np.float64)
...
    session_trace = trace_day[present_mask].astype(np.float16, copy=False)
    for trial_slice in slices:
        neural_trial = session_trace[:, trial_slice].astype(np.float16, copy=False)
        output_trial = output_class[trial_slice][np.newaxis, :].astype(np.int8, copy=False)
...
    animal_cache: dict[str, dict] = {}
    for session_index, session_ref in enumerate(session_refs):
        if session_ref.animal not in animal_cache:
            animal_cache.clear()
            gc.collect()
            animal_cache[session_ref.animal] = load_animal_dataset(data_dir, session_ref.animal)
```

**What this does:** A single-entry `animal_cache` holds one animal's joblib dict at a time, cleared with an explicit `gc.collect()` before the next animal loads; the index-building pass also `del`s each animal after reading its session count. Stored trials use `float16` for neural and `int8` for output, while intermediate per-day arrays are first materialized as `float64`. Trials are direct slices of a session-wide `float16` trace and of a precomputed session-wide output class array; trials remain at the native 1800-frame length.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
