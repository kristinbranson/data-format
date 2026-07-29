# lee2025 — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/lee2025/codex/2026-03-11__11-30-50_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Streams animal files one at a time from `data/` to limit memory use." (lines 242-243); "data/ contains 7 per-animal joblib files ... Each per-animal joblib file is a dictionary keyed by animal ID" (lines 74-77)

**Code** (convert_data.py:54-60, 107-108, 245-296):
```python
def get_animals(data_dir: str) -> list[str]:
    animals = []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if os.path.isfile(path) and re.fullmatch(r"QLAK-CA1-\d+", name):
            animals.append(name)
    return animals

def load_animal(path: str, animal: str) -> dict:
    return joblib.load(os.path.join(path, animal))[animal]
...
for animal in animals:
    animal_data = load_animal(data_dir, animal)
    ndays = animal_data["trace"].shape[0]
    for day_idx in range(ndays):
        ...
```

**What this does:** Scans `data/` for files matching the `QLAK-CA1-\d+` pattern, then loads each animal's joblib file individually. For each animal's dictionary, iterates over `n_days` recording sessions stored in the `trace`, `position`, `blocked`, and `envs` fields.

**Rating:** ok

**Note:** agent loads the extension-less data files with joblib.load, while manual uses the mat file

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:197):
> "Animal ID from filename / top-level dict key -> `subjects`, `subject_idx`. Session order will be animals in sorted filename order, days in native order within each animal."

**Code** (convert_data.py:54-60, 247-250):
```python
def get_animals(data_dir: str) -> list[str]:
    animals = []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if os.path.isfile(path) and re.fullmatch(r"QLAK-CA1-\d+", name):
            animals.append(name)
    return animals
...
animals = get_animals(data_dir)
subjects = animals
subject_to_idx = {animal: idx for idx, animal in enumerate(subjects)}
```

**What this does:** Each file matching `QLAK-CA1-\d+` becomes one subject; the filename itself is the subject identifier. A subject-to-index map is built and per-session `subject_idx` values are stored in the converted dict.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:76-79):
> "`trace`: dense array of shape `(n_days, n_registered_cells, n_frames)` ... `position`: `(n_days, 2, n_frames)` ... `envs`: `(n_days, 1)` ... `blocked`: list of length `n_days`"

**Code** (convert_data.py:184-188, 296-303):
```python
day = session.day_idx
trace_day = animal_data["trace"][day]
position_day = animal_data["position"][day]
env_label = animal_data["envs"].reshape(-1)[day]
open_mask = blocked_to_open_vector(animal_data["blocked"][day])
...
ndays = animal_data["trace"].shape[0]
for day_idx in range(ndays):
    ...
    session = SessionRecord(animal=animal, day_idx=day_idx)
```

**What this does:** Iterates over the leading day axis of each per-animal joblib (one session per day index), assigning a `session_id` of `<animal>_day<NN>` and converting that day's `trace`/`position`/`blocked`/`envs` slice independently.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:208-211):
> "Trialization: impose 40 one-minute trials per session using session start as time zero. ... For recordings shorter than 72,000 frames, the 40th trial is shorter; for recordings longer than 72,000 frames, discard the small tail beyond 40 min."

**Code** (convert_data.py:17-23, 96-104):
```python
FPS = 30
TRIAL_SECONDS = 60
TRIAL_FRAMES = FPS * TRIAL_SECONDS
TEMPORAL_BIN_FRAMES = 3
TIME_BIN_MS = 100.0
NOMINAL_SESSION_SECONDS = 40 * 60
NOMINAL_SESSION_FRAMES = NOMINAL_SESSION_SECONDS * FPS
...
def get_trial_slices(n_frames_session: int) -> list[tuple[int, int]]:
    usable_frames = min(n_frames_session, NOMINAL_SESSION_FRAMES)
    slices = []
    for trial_idx in range(NOMINAL_SESSION_SECONDS // TRIAL_SECONDS):
        start = trial_idx * TRIAL_FRAMES
        end = min(start + TRIAL_FRAMES, usable_frames)
        if end - start >= TEMPORAL_BIN_FRAMES:
            slices.append((start, end))
    return slices
```

**What this does:** Caps each session at the nominal 40-minute window (72,000 frames at 30 Hz) and partitions it into 40 consecutive 60-second slices. Recordings slightly shorter than 72,000 frames yield a truncated final trial; slices below the 3-frame temporal bin minimum are dropped.

**Rating:** ok

**Note:** manual truncates after full 60 second trials, while agent includes some shorter trials, forces 40 minute window

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:155-158):
> "No native trial structure exists in the source dataset. ... For within-session decoding in code, low-velocity frames and low-activity cells are excluded inside the decoder (`v_thresh=5`, `cell_threshold=5` events) ..."

**Code** (convert_data.py): (no relevant code found — no per-trial QC filter is applied; only the >=3-frame minimum length check in `get_trial_slices`)

**What this does:** No trial-level quality-control filtering is implemented in the conversion script beyond skipping slices shorter than the temporal bin size. Velocity / activity filters from the reference decoder are not applied here.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:50, 76):
> "the `trace` field is already a rise-extracted event matrix where `1` marks significant calcium events. No code computes `dF/F`; for this conversion the reference neural signal is the provided event trace."
> "`trace`: dense array of shape `(n_days, n_registered_cells, n_frames)` with rise-extracted calcium events."

**Code** (convert_data.py:184-191):
```python
day = session.day_idx
trace_day = animal_data["trace"][day]
...
valid_cells = get_valid_cell_mask(trace_day)
trace_valid = trace_day[valid_cells].astype(np.float32, copy=False)
```

**What this does:** Neural data comes from the per-animal joblib field `trace[day]`, which holds the released binarized rising-phase calcium event matrix (cells x frames).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:194, 211-212):
> "Convert each chunk from 30 Hz binary events to 100 ms bins via non-overlapping 3-frame averaging."
> "Temporal bin size: store data at 100 ms resolution using non-overlapping 3-frame bins."

**Code** (convert_data.py:72-78, 191, 204-211):
```python
def temporal_bin_mean(arr: np.ndarray, bin_size: int) -> np.ndarray:
    usable = (arr.shape[-1] // bin_size) * bin_size
    if usable <= 0:
        raise ValueError("Segment is too short to create at least one temporal bin.")
    trimmed = arr[..., :usable]
    new_shape = arr.shape[:-1] + (usable // bin_size, bin_size)
    return trimmed.reshape(new_shape).mean(axis=-1)
...
trace_valid = trace_day[valid_cells].astype(np.float32, copy=False)
...
neural_raw = trace_valid[:, start:end]
neural_binned = temporal_bin_mean(neural_raw, TEMPORAL_BIN_FRAMES).astype(np.float32, copy=False)
neural_trials.append(neural_binned)
```

**What this does:** Processing keeps the released binary event traces and averages each non-overlapping 3-frame window (100 ms) per neuron, casting to float32. No further denoising or normalization is applied.

**Rating:** ok

**Note:** agent downsamples to 10 Hz, manual keeps at 30 Hz. neural activity is binary at 30 Hz, so arguably 10 Hz might be better

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:67, 205-206):
> "Registration quality is encoded by `NaN` traces/maps for cells absent on a given day."
> "keep all valid registered cells for each session and remove only unregistered (`NaN`) cells on that day."

**Code** (convert_data.py:92-93, 189-191):
```python
def get_valid_cell_mask(trace_day: np.ndarray) -> np.ndarray:
    return ~np.isnan(trace_day[:, 0])
...
valid_cells = get_valid_cell_mask(trace_day)
trace_valid = trace_day[valid_cells].astype(np.float32, copy=False)
```

**What this does:** Only the first time-frame of each cell is checked; cells that are NaN at frame 0 (taken to mean unregistered on that day) are dropped. No additional activity, place-cell, or velocity filter is applied to neurons.

**Rating:** ok

**Note:** agent uses first time point, manual checks all timepoints, spotchecked that these are the same

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:211-212):
> "Temporal bin size: store data at 100 ms resolution using non-overlapping 3-frame bins. Rationale: the reference decoder temporally bins data in 3-frame windows."

**Code** (convert_data.py:17-21, 72-78):
```python
FPS = 30
TRIAL_SECONDS = 60
TRIAL_FRAMES = FPS * TRIAL_SECONDS
TEMPORAL_BIN_FRAMES = 3
TIME_BIN_MS = 100.0
...
def temporal_bin_mean(arr: np.ndarray, bin_size: int) -> np.ndarray:
    usable = (arr.shape[-1] // bin_size) * bin_size
    ...
    trimmed = arr[..., :usable]
    new_shape = arr.shape[:-1] + (usable // bin_size, bin_size)
    return trimmed.reshape(new_shape).mean(axis=-1)
```

**What this does:** Native 30 Hz frames are pooled into non-overlapping 3-frame windows (100 ms bins) by reshaping and taking the mean along the bin axis. `TIME_BIN_MS = 100.0` is recorded in metadata.

**Rating:** ok

**Note:** agent downsamples to 10 Hz while manual keeps at 30 Hz

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (convert_data.py:268-271 metadata):
> `"temporal_alignment_event": "start of each consecutive 1-minute chunk within a session"`, `"off_start": 0.0`, `"off_end": 60.0`

**Code** (convert_data.py:96-104, 204-213):
```python
def get_trial_slices(n_frames_session: int) -> list[tuple[int, int]]:
    usable_frames = min(n_frames_session, NOMINAL_SESSION_FRAMES)
    slices = []
    for trial_idx in range(NOMINAL_SESSION_SECONDS // TRIAL_SECONDS):
        start = trial_idx * TRIAL_FRAMES
        end = min(start + TRIAL_FRAMES, usable_frames)
        if end - start >= TEMPORAL_BIN_FRAMES:
            slices.append((start, end))
    return slices
...
for start, end in trial_slices:
    neural_raw = trace_valid[:, start:end]
```

**What this does:** No external behavioral event alignment; trial start times are simply the boundaries of consecutive 60-second segments measured from session start. The metadata flags this with `temporal_alignment_event = "start of each consecutive 1-minute chunk within a session"`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:79, 195):
> "`blocked`: Python list of length `n_days`; each element is a list containing an array of blocked partition indices in the 3x3 environment layout. `-1` denotes no blocked partitions."
> "Convert blocked-partition indices into a length-9 binary open-mask vector in raw partition order (`1=open`, `0=blocked`)"

**Code** (convert_data.py:63-69, 188):
```python
def blocked_to_open_vector(blocked_entry) -> np.ndarray:
    open_mask = np.ones(9, dtype=np.float32)
    blocked_values = np.array(blocked_entry[0], dtype=np.float32).reshape(-1)
    if not (blocked_values.size == 1 and blocked_values[0] == -1):
        open_mask[blocked_values.astype(int)] = 0.0
    # Raw blocked indices are stored in a y-major 3x3 layout, while output classes use x_bin * 3 + y_bin.
    return open_mask.reshape(3, 3).T.reshape(-1)
...
open_mask = blocked_to_open_vector(animal_data["blocked"][day])
```

**What this does:** The input is derived from the per-day entry of `animal_data["blocked"]`, which lists indices (0-8) of blocked 3x3 partitions (or `[-1]` for no blocking).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

**Notes excerpt** (CONVERSION_NOTES.md:367):
> "Geometry input orientation bug: Initial conversion stored the 9-element geometry vector in the raw blocked-index layout, but output classes used `x_bin * 3 + y_bin`. ... Resolution: transpose the 3 x 3 open-mask before flattening in `blocked_to_open_vector()`."

**Code** (convert_data.py:63-69, 212):
```python
def blocked_to_open_vector(blocked_entry) -> np.ndarray:
    open_mask = np.ones(9, dtype=np.float32)
    blocked_values = np.array(blocked_entry[0], dtype=np.float32).reshape(-1)
    if not (blocked_values.size == 1 and blocked_values[0] == -1):
        open_mask[blocked_values.astype(int)] = 0.0
    # Raw blocked indices are stored in a y-major 3x3 layout, while output classes use x_bin * 3 + y_bin.
    return open_mask.reshape(3, 3).T.reshape(-1)
...
input_trials.append(open_mask.copy())
```

**What this does:** Starts from an all-ones length-9 vector, zeroes the blocked indices, and transposes the reshaped 3x3 mask so the flattened order matches the `x_bin * 3 + y_bin` convention used by the output. The encoding is `1 = open, 0 = blocked` and is replicated once per trial.

**Rating:** ok

**Note:** uses 1 for accessible, 0 for blocked

---

## Q 3-c. How is `input` *Blocked positions* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:223-224):
> "Static input representation: store geometry as a 1D length-9 vector per trial. Rationale: the validator will automatically tile 1D inputs across time. Static 1D storage is compact and faithful because geometry is constant within each trial."

**Code** (convert_data.py:204-212, 260):
```python
for start, end in trial_slices:
    neural_raw = trace_valid[:, start:end]
    ...
    neural_binned = temporal_bin_mean(neural_raw, TEMPORAL_BIN_FRAMES).astype(np.float32, copy=False)
    ...
    neural_trials.append(neural_binned)
    input_trials.append(open_mask.copy())
...
"input_names": [f"open_partition_{idx}" for idx in range(9)],
```

**What this does:** The same length-9 open-mask vector is appended once per trial alongside the neural trial. It is a static (non-time-varying) per-trial input that the downstream framework tiles across the trial's bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:77, 196):
> "`position`: dense array of shape `(n_days, 2, n_frames)` with x-y position sampled at the same frame rate as `trace`."
> "Split into same 1-minute chunks as neural. Average x/y position within each 3-frame bin (100 ms), then discretize to 3 x 3 bins ..."

**Code** (convert_data.py:186, 192, 206):
```python
position_day = animal_data["position"][day]
...
position_valid = position_day.astype(np.float32, copy=False)
...
position_raw = position_valid[:, start:end]
```

**What this does:** Output is derived from the per-day `animal_data["position"]` field, a `(2, n_frames)` array of x-y coordinates from DeepLabCut head tracking, aligned with the same frames as `trace`.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Position*?

**Notes excerpt** (CONVERSION_NOTES.md:217-220):
> "Position discretization: use session-wise maximum-based spatial binning, matching the reference code's flooring rule, but with 3 bins instead of 15. Rationale: the paper's code bins position by dividing by `(session_max + buffer) / n_bins`."

**Code** (convert_data.py:81-89, 192-194, 207-209):
```python
def discretize_position_3x3(position_xy_by_time: np.ndarray, session_max_xy: np.ndarray) -> np.ndarray:
    if position_xy_by_time.shape[0] != 2:
        raise ValueError(f"Expected position shape (2, T), got {position_xy_by_time.shape}")
    denom = (session_max_xy + BUFFER) / POSITION_BINS
    denom = np.where(denom <= 0, 1.0, denom)
    binned = np.floor(position_xy_by_time / denom[:, np.newaxis]).astype(np.int64)
    binned = np.clip(binned, 0, POSITION_BINS - 1)
    classes = binned[0] * POSITION_BINS + binned[1]
    return classes[np.newaxis, :]
...
usable_frames = min(trace_valid.shape[1], NOMINAL_SESSION_FRAMES)
session_max_xy = np.nanmax(position_valid[:, :usable_frames], axis=1)
...
position_binned = temporal_bin_mean(position_raw, TEMPORAL_BIN_FRAMES)
output_binned = discretize_position_3x3(position_binned, session_max_xy).astype(np.int64, copy=False)
```

**What this does:** First, x and y are temporally averaged into 100 ms bins. Then each axis is divided by `(session_max + 1e-5) / 3`, floored, and clipped to `{0,1,2}`; the 9-class label is `x_bin * 3 + y_bin`. The session's per-axis maxima act as the arena scale.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:131):
> "Neural and behavioral streams were acquired simultaneously at 30 Hz and timestamped for post-hoc alignment."

**Code** (convert_data.py:204-213):
```python
for start, end in trial_slices:
    neural_raw = trace_valid[:, start:end]
    position_raw = position_valid[:, start:end]
    neural_binned = temporal_bin_mean(neural_raw, TEMPORAL_BIN_FRAMES).astype(np.float32, copy=False)
    position_binned = temporal_bin_mean(position_raw, TEMPORAL_BIN_FRAMES)
    output_binned = discretize_position_3x3(position_binned, session_max_xy).astype(np.int64, copy=False)

    neural_trials.append(neural_binned)
    input_trials.append(open_mask.copy())
    output_trials.append(output_binned)
```

**What this does:** Both neural and position arrays are sliced with identical `[start:end]` indices and pooled with the same 3-frame averaging, so the binned output and binned neural arrays share the same time axis frame-for-frame.

**Rating:** ok

**Note:** _(no note)_

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:67, 209, 366-368):
> "Registration quality is encoded by `NaN` traces/maps for cells absent on a given day."
> "For recordings shorter than 72,000 frames, the 40th trial is shorter; for recordings longer than 72,000 frames, discard the small tail beyond 40 min."
> "Geometry input orientation bug ... Resolution: transpose the 3 x 3 open-mask before flattening".

**Code** (convert_data.py:84-89, 92-93, 96-104, 193-194):
```python
denom = (session_max_xy + BUFFER) / POSITION_BINS
denom = np.where(denom <= 0, 1.0, denom)
binned = np.floor(position_xy_by_time / denom[:, np.newaxis]).astype(np.int64)
binned = np.clip(binned, 0, POSITION_BINS - 1)
...
def get_valid_cell_mask(trace_day: np.ndarray) -> np.ndarray:
    return ~np.isnan(trace_day[:, 0])
...
usable_frames = min(n_frames_session, NOMINAL_SESSION_FRAMES)
...
session_max_xy = np.nanmax(position_valid[:, :usable_frames], axis=1)
```

**What this does:** NaN-only cells (unregistered on a given day) are dropped via the valid-cell mask. Position max is computed with `nanmax` and a small buffer guards against zero division; clipping handles out-of-range bins. Sessions exceeding 72,000 frames are truncated; shorter sessions yield a shorter final trial. Trial slices below 3 frames are skipped.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:256, 287-294):
> "Full-data runtime will be dominated by decompressing the 7 large joblib animal files."
> "Sample conversion (`--sample --show-processing`) ~0.73 s/session after load; ~12 s for 2 sessions total | ~3-4 min for full conversion".

**Code** (convert_data.py:107-108, 289-336):
```python
def load_animal(path: str, animal: str) -> dict:
    return joblib.load(os.path.join(path, animal))[animal]
...
total_start = time.perf_counter()
...
for animal in animals:
    animal_start = time.perf_counter()
    animal_data = load_animal(data_dir, animal)
    ...
    elapsed = time.perf_counter() - session_start
    print(f"  Converted {session.session_id}: ... {elapsed:.2f}s")
    ...
    animal_elapsed = time.perf_counter() - animal_start
    print(f"Finished {animal} in {animal_elapsed:.2f}s")
```

**What this does:** The script identifies joblib decompression / animal loading as the dominant cost. Per-session and per-animal elapsed times are printed via `time.perf_counter()` so the longest steps are observable in the run log.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md:258-261):
> "Code speedups added: Per-animal streaming instead of loading all animals at once. Vectorized 3-frame temporal binning with reshape/mean. Static per-trial inputs stored as 1D arrays so the validator can tile them automatically."

**Code** (convert_data.py:72-78, 204-213):
```python
def temporal_bin_mean(arr: np.ndarray, bin_size: int) -> np.ndarray:
    usable = (arr.shape[-1] // bin_size) * bin_size
    ...
    trimmed = arr[..., :usable]
    new_shape = arr.shape[:-1] + (usable // bin_size, bin_size)
    return trimmed.reshape(new_shape).mean(axis=-1)
...
for start, end in trial_slices:
    neural_raw = trace_valid[:, start:end]
    position_raw = position_valid[:, start:end]
    neural_binned = temporal_bin_mean(neural_raw, TEMPORAL_BIN_FRAMES)...
```

**What this does:** Temporal binning is already vectorized via reshape+mean. The remaining Python-level loop is over trials within a session; trial slicing/binning could in principle be batched into a single reshape over the whole session before chunking, but is left per-trial.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md:258-260):
> "Per-animal streaming instead of loading all animals at once."

**Code** (convert_data.py:204-213):
```python
for start, end in trial_slices:
    neural_raw = trace_valid[:, start:end]
    position_raw = position_valid[:, start:end]
    neural_binned = temporal_bin_mean(neural_raw, TEMPORAL_BIN_FRAMES).astype(np.float32, copy=False)
    position_binned = temporal_bin_mean(position_raw, TEMPORAL_BIN_FRAMES)
    output_binned = discretize_position_3x3(position_binned, session_max_xy).astype(np.int64, copy=False)

    neural_trials.append(neural_binned)
    input_trials.append(open_mask.copy())
    output_trials.append(output_binned)
```

**What this does:** `temporal_bin_mean` is called separately for each trial's neural and position slices, and `open_mask.copy()` is appended once per trial; the reshape-based binning is repeated per trial rather than batched once over the whole session.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md:368-369):
> "Full-mode inefficiency: The first full conversion attempt did an unnecessary preload over all animal files before conversion. Resolution: removed the redundant `select_sessions()` full-data pass."

**Code** (convert_data.py:111-176, 219-239):
```python
def maybe_plot_processing(...):
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    ...
    fig.savefig(f"processing_{session.session_id}.png", dpi=150)
    plt.close(fig)
...
debug_info = {
    "env_label": str(env_label),
    "open_mask": open_mask,
    "usable_frames": usable_frames,
    "original_frames": int(trace_valid.shape[1]),
    "trial_slices": trial_slices,
    "session_max_xy": session_max_xy,
}
```

**What this does:** Optional plotting (`maybe_plot_processing`) and the per-session `debug_info` dict are computed/persisted (debug_info is local; metadata-only fields stored) but are not consumed by the downstream decoder. Plotting only runs when `--show-processing` is set, capped at 2 sessions.

**Rating:** match

**Note:** _(no note)_

---
