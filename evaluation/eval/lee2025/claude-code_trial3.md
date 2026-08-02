# lee2025 — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/lee2025/claude/2026-04-08__18-25-48_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Each animal is stored as a joblib file (extensionless) in `data/`. Structure: `{animal_id: {SFPs, blocked, centroids, envs, maps, position, trace}}`" (lines 66-67)

**Code** (convert_data.py:90-101, 264-266, 293-298):
```python
dat = joblib.load(os.path.join(data_dir, animal_name))
d = dat[animal_name]
...
trace = d['trace']       # (n_days, n_cells, n_frames)
position = d['position'] # (n_days, 2, n_frames)
envs = d['envs'].flatten()  # (n_days,) string array
n_days, n_cells_total, n_frames_total = trace.shape
...
animals = ['QLAK-CA1-08', 'QLAK-CA1-30', 'QLAK-CA1-50', 'QLAK-CA1-51',
           'QLAK-CA1-56', 'QLAK-CA1-74', 'QLAK-CA1-75']
...
for animal in animals_to_process:
    ...
    result = process_animal(animal, data_dir, trial_duration_frames, ...)
```

**What this does:** Loads each animal's data from the (extensionless) joblib file in `data/` using `joblib.load`, indexed by the animal name. The hardcoded list of 7 animals is iterated; each animal contains `trace`, `position`, and `envs` arrays whose first axis is the day/session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "7 animals: QLAK-CA1-{08,30,50,51,56,74,75}" (line 53)

**Code** (convert_data.py:265-266, 287, 293-294, 308):
```python
animals = ['QLAK-CA1-08', 'QLAK-CA1-30', 'QLAK-CA1-50', 'QLAK-CA1-51',
           'QLAK-CA1-56', 'QLAK-CA1-74', 'QLAK-CA1-75']
...
subjects = animals  # All 7 animals are subjects
...
for animal in animals_to_process:
    subject_id = animals.index(animal)
    ...
    subject_idx_list.append(subject_id)
```

**What this does:** The 7 animals (QLAK-CA1-*) are hardcoded as the subjects list, and each session's `subject_idx` is set to the animal's index in that list.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sessions are ~40 min at 30 Hz (~72000 frames). Each animal has 3 repetitions of 10 geometries + bookend squares." (lines 77-78); "One session = one decoder session: Each recording day is a separate session in our output" (line 215)

**Code** (convert_data.py:97-115, 304-307):
```python
trace = d['trace']       # (n_days, n_cells, n_frames)
position = d['position'] # (n_days, 2, n_frames)
envs = d['envs'].flatten()  # (n_days,) string array
n_days, n_cells_total, n_frames_total = trace.shape
...
for day in range(n_days):
    ...
    trace_day = trace[day]       # (n_cells, n_frames)
    pos_day = position[day]      # (2, n_frames)
    env_name = str(envs[day])
...
for s in range(n_sessions):
    all_neural.append(result['neural'][s])
    all_input.append(result['input'][s])
    all_output.append(result['output'][s])
```

**What this does:** Each "day" axis index of the per-animal arrays is treated as one session; the loop iterates over `n_days` and appends each day's data as a separate session in the output lists.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Each session (~40 min at 30 Hz ≈ 71866-72219 frames) split into 1-minute trials. 1 minute = 1800 frames at 30 Hz. ~40 trials per session (last partial trial discarded if < 1800 frames)." (lines 187-189)

**Code** (convert_data.py:132-155, 268-270):
```python
fps = 30  # recording frame rate
trial_duration_sec = 60  # 1 minute trials
trial_duration_frames = fps * trial_duration_sec  # 1800 frames
...
# Split into 1-minute trials
n_trials = n_frames_total // trial_duration_frames

trials_neural = []
trials_input = []
trials_output = []

for trial_idx in range(n_trials):
    start = trial_idx * trial_duration_frames
    end = start + trial_duration_frames
    # Neural: (n_active, trial_duration_frames)
    trial_neural = active_trace[:, start:end].astype(np.float32)
    # Input: environment geometry, static per trial (9,)
    trial_input = env_mat.astype(np.float32)
    # Output: position bin, time-varying (1, trial_duration_frames)
    trial_output = bin_ids[start:end].reshape(1, -1).astype(np.int64)
```

**What this does:** Each session is sliced into non-overlapping 1800-frame (60-second @ 30 Hz) trials by integer division of total frame count. Any remainder frames at the end of the session are discarded.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "No velocity filtering: The paper's velocity filter was for decoding within their pipeline; we let the decoder handle this" (line 213); "Trial curation: None in original (1 session = 1 day). We split into 1-min trials." (line 134)

**Code** (convert_data.py): (no relevant code found — no per-trial QC filtering)

**What this does:** No trial-level quality control is applied; every contiguous 1800-frame block is kept (only the trailing partial trial is dropped by integer division).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "trace: shape (n_days, n_cells, n_frames), binary {0,1}, NaN for unregistered cells" (line 69); "Neural data: Binary trace vector (1=significant rising-phase event, 0=no event). Already preprocessed." (line 46)

**Code** (convert_data.py:97, 113, 144):
```python
trace = d['trace']       # (n_days, n_cells, n_frames)
...
trace_day = trace[day]       # (n_cells, n_frames)
...
trial_neural = active_trace[:, start:end].astype(np.float32)
```

**What this does:** Neural data is derived from the per-animal `trace` array (binarized calcium events) loaded from each animal's joblib file.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use raw binary trace (0/1 events) at native 30 Hz — NO additional processing needed. Trace is already binarized by the original authors." (lines 205-206)

**Code** (convert_data.py:117-124, 144):
```python
# Identify active (registered) cells for this day
# A cell is registered if its trace is not all NaN
active_mask = ~np.all(np.isnan(trace_day), axis=1)
active_trace = trace_day[active_mask]  # (n_active, n_frames)
n_active = active_mask.sum()

# Replace any remaining NaN with 0 (shouldn't happen for active cells, but safety)
active_trace = np.nan_to_num(active_trace, nan=0.0)
...
trial_neural = active_trace[:, start:end].astype(np.float32)
```

**What this does:** Inactive (all-NaN) cells are removed, any residual NaN values are replaced with 0, and the binary trace is cast to float32 and sliced per trial. No further processing (smoothing, normalization, deconvolution) is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Include only cells registered on that specific day (non-NaN rows). All registered cells included (no place cell filtering, matching paper's approach)" (lines 207-208)

**Code** (convert_data.py:117-121):
```python
# Identify active (registered) cells for this day
# A cell is registered if its trace is not all NaN
active_mask = ~np.all(np.isnan(trace_day), axis=1)
active_trace = trace_day[active_mask]  # (n_active, n_frames)
n_active = active_mask.sum()
```

**What this does:** Cells whose trace for the entire session is NaN (i.e., not registered on that day) are excluded; all remaining registered cells are kept with no place-cell or activity-based filtering.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Time bin size = 1/30 s ≈ 33.33 ms (raw frame rate)" (line 190)

**Code** (convert_data.py:268-270, 358):
```python
fps = 30  # recording frame rate
trial_duration_sec = 60  # 1 minute trials
trial_duration_frames = fps * trial_duration_sec  # 1800 frames
...
'time_bin_size': 1000.0 / fps,  # ~33.33 ms
```

**What this does:** The neural trace is kept at the native 30 Hz frame rate (≈33.33 ms bins); no resampling or temporal binning is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / convert_data.py metadata):
> "temporal_alignment_event: 'Start of 1-minute trial segment within recording session'" (convert_data.py:359)

**Code** (convert_data.py:139-144, 357-360):
```python
for trial_idx in range(n_trials):
    start = trial_idx * trial_duration_frames
    end = start + trial_duration_frames
    # Neural: (n_active, trial_duration_frames)
    trial_neural = active_trace[:, start:end].astype(np.float32)
...
'temporal_alignment_event': 'Start of 1-minute trial segment within recording session',
'off_start': 0.0,
'off_end': float(trial_duration_sec),
```

**What this does:** There is no stimulus event; trials are aligned to the start of each contiguous 60-second segment of the continuous recording (frame index 0 of the trial = `trial_idx * 1800`).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "envs[day] → get_env_mat(env): input[0] (9,). Flatten 3x3 binary geometry matrix to 9-element vector. Static per trial. Decoder input: which partitions are accessible." (line 184); "get_env_mat() returns 3x3 binary matrix: 1=accessible partition, 0=blocked." (line 59)

**Code** (convert_data.py:99, 115, 127, 31-49):
```python
envs = d['envs'].flatten()  # (n_days,) string array
...
env_name = str(envs[day])
...
# Get environment geometry as input (flattened 3x3 binary matrix)
env_mat = get_env_mat(env_name).flatten()  # (9,)
...
# in get_env_mat:
env_mats = {
    'square':    np.array([[1,1,1],[1,1,1],[1,1,1]]),
    'o':         np.array([[1,1,1],[1,0,1],[1,1,1]]),
    ...
}
```

**What this does:** The input is derived from the `envs` string array (one environment-shape name per day), which is mapped through a hardcoded `get_env_mat` lookup table to a 3×3 binary accessibility matrix. The `blocked` raw variable is not used directly.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Environment geometry as flattened 3x3 binary matrix (9 values). Static per trial (doesn't change within a trial). Shape: (9,) per trial — no time dimension since static." (lines 200-202)

**Code** (convert_data.py:127, 147, 337):
```python
# Get environment geometry as input (flattened 3x3 binary matrix)
env_mat = get_env_mat(env_name).flatten()  # (9,)
...
# Input: environment geometry, static per trial (9,)
trial_input = env_mat.astype(np.float32)
...
input_names = [f'partition_{i}' for i in range(9)]
```

**What this does:** The 3×3 binary accessibility matrix from `get_env_mat` is flattened to a 9-element vector, cast to float32, and used as a constant per-trial input (1 = accessible partition, 0 = blocked partition). It is repeated identically for every trial in the session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "position: shape (n_days, 2, n_frames), x-y coordinates in [0, 75] cm" (line 70)

**Code** (convert_data.py:98, 114, 130):
```python
position = d['position'] # (n_days, 2, n_frames)
...
pos_day = position[day]      # (2, n_frames)
...
# Discretize position into 3x3 grid
bin_ids = discretize_position_3x3(pos_day)  # (n_frames,)
```

**What this does:** Output is derived from the `position` array (2D x,y coordinates per frame, in cm) loaded from each animal's joblib file.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `output` *Position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Position (x,y) in [0, 75] cm → 3x3 grid of 25 cm bins. Bin edges: [0, 25, 50, 75]. Combine x_bin and y_bin into single label: bin_id = x_bin * 3 + y_bin (0-8)." (lines 193-195)

**Code** (convert_data.py:52-74, 151):
```python
def discretize_position_3x3(position, env_size=75.0):
    bin_size = env_size / 3.0
    # Clip to valid range and compute bin indices
    x = np.clip(position[0], 0, env_size - 1e-10)
    y = np.clip(position[1], 0, env_size - 1e-10)
    x_bin = np.floor(x / bin_size).astype(int)
    y_bin = np.floor(y / bin_size).astype(int)
    # Clamp to [0, 2]
    x_bin = np.clip(x_bin, 0, 2)
    y_bin = np.clip(y_bin, 0, 2)
    # Combine into single bin ID: row-major order
    bin_ids = x_bin * 3 + y_bin
    return bin_ids
...
trial_output = bin_ids[start:end].reshape(1, -1).astype(np.int64)
```

**What this does:** x and y are clipped to [0, 75) cm, divided by 25 cm bin size, floored and clipped to {0,1,2}, then combined as `x_bin * 3 + y_bin` to give a single integer bin id 0-8 per frame.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "All streams synchronous at 30 Hz" (line 128)

**Code** (convert_data.py:139-151):
```python
for trial_idx in range(n_trials):
    start = trial_idx * trial_duration_frames
    end = start + trial_duration_frames
    # Neural: (n_active, trial_duration_frames)
    trial_neural = active_trace[:, start:end].astype(np.float32)
    ...
    # Output: position bin, time-varying (1, trial_duration_frames)
    trial_output = bin_ids[start:end].reshape(1, -1).astype(np.int64)
```

**What this does:** Position bins and neural traces are sliced with identical `start:end` indices per trial, so they are aligned frame-for-frame at the native 30 Hz sampling rate.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "~1666 frames discarded per session (last partial minute) — acceptable" (line 369); "Replace any remaining NaN with 0 (shouldn't happen for active cells, but safety)" (convert_data.py:123)

**Code** (convert_data.py:117-124, 132-133):
```python
active_mask = ~np.all(np.isnan(trace_day), axis=1)
active_trace = trace_day[active_mask]  # (n_active, n_frames)
n_active = active_mask.sum()

# Replace any remaining NaN with 0 (shouldn't happen for active cells, but safety)
active_trace = np.nan_to_num(active_trace, nan=0.0)
...
# Split into 1-minute trials
n_trials = n_frames_total // trial_duration_frames
```

**What this does:** All-NaN cells are filtered out, residual NaNs (if any) are replaced with 0, and the trailing partial minute of frames in each session is discarded by integer division.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Load 1 animal | ~13s; Process 31 sessions | ~9s; Total per animal | ~22s; Estimated full (7 animals) | ~3-4 min" (lines 277-281); actual full conversion "215s (~3.6 min)" (line 327)

**Code** (convert_data.py:90-96):
```python
t0 = time.time()
print(f"Loading {animal_name}...", flush=True)
dat = joblib.load(os.path.join(data_dir, animal_name))
d = dat[animal_name]
t_load = time.time() - t0
print(f"  Loaded in {t_load:.1f}s", flush=True)
```

**What this does:** Per the notes' timing table, the joblib load step (~13 s/animal) dominates over per-session processing (~9 s for ~31 days). Total full-dataset conversion took ~215 s.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Direct numpy array slicing for trial splitting (no loops over frames). Vectorized position discretization." (lines 240, 242)

**Code** (convert_data.py:139-155):
```python
for trial_idx in range(n_trials):
    start = trial_idx * trial_duration_frames
    end = start + trial_duration_frames
    trial_neural = active_trace[:, start:end].astype(np.float32)
    trial_input = env_mat.astype(np.float32)
    trial_output = bin_ids[start:end].reshape(1, -1).astype(np.int64)
    trials_neural.append(trial_neural)
    trials_input.append(trial_input)
    trials_output.append(trial_output)
```

**What this does:** Trial-splitting is done with a Python `for` loop over `n_trials` (~40 iterations per session) appending sliced views to lists; this could be expressed as a single reshape/stack operation across trials, but the loop is short and not flagged as a bottleneck in the notes.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md): (none directly addressing repeated processing)

**Code** (convert_data.py:147):
```python
# Input: environment geometry, static per trial (9,)
trial_input = env_mat.astype(np.float32)
```

**What this does:** The same per-session `env_mat` vector is appended (as a fresh cast) into `trials_input` once per trial, so the identical (9,) array is duplicated ~40× per session in the output structure.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:189-253):
```python
def plot_processing(animal_name, raw_data, sessions_neural, sessions_input,
                   sessions_output, sessions_env, active_cells, trial_duration):
    """Plot processing visualizations for an animal."""
    ...
    fig.savefig(f'processing_{animal_name}.png', dpi=150)
```

**What this does:** A `plot_processing` routine generates per-animal PNG visualizations (only when `--show-processing` is passed); these plots are diagnostic outputs not consumed by the decoder. No other obvious unused processing is performed in the main path.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:239-242 — "### Code efficiencies / - Direct numpy array slicing for trial splitting (no loops over frames) / - Memory freed after each animal with `del` / - Vectorized position discretization"
>
> CONVERSION_NOTES.md:383 — "Used --cpu flag (GPU insufficient memory)" (decoder training, not conversion)

**Code** (convert_data.py:143-151, 178):
```python
            # Neural: (n_active, trial_duration_frames)
            trial_neural = active_trace[:, start:end].astype(np.float32)

            # Input: environment geometry, static per trial (9,)
            trial_input = env_mat.astype(np.float32)

            # Output: position bin, time-varying (1, trial_duration_frames)
            # Must be integer-valued for indexing into output_values
            trial_output = bin_ids[start:end].reshape(1, -1).astype(np.int64)
...
    del dat, d  # Free memory
```

**What this does:** One animal file is loaded per iteration and released with `del dat, d` once its sessions are converted; no `gc.collect()`, memmap, or chunked read. Neural trials are cast to `float32` and outputs to `int64`, and trials are sliced directly out of the session array rather than built by concatenation. Trials are stored at the native 30 Hz rate (1800 frames per trial, no temporal pooling), and all sessions accumulate in memory until the final pickle dump.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
