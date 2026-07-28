# lee2025 — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/lee2025/claude/2026-03-10__11-18-23_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:57-66):
> Each animal has a joblib file in `data/` containing a dict keyed by animal name: `trace`: (n_days, n_cells, n_frames) - binary calcium events (0/1), NaN for unregistered cells on a day; `position`: (n_days, 2, n_frames); `envs`: (n_days, 1); `blocked`: list of n_days arrays.

**Code** (convert_data.py:245-254):
```python
for a_idx, animal in enumerate(animals_to_process):
    t0 = time.time()
    print(f"\nLoading {animal}...")
    dat = joblib.load(os.path.join(data_dir, animal))
    animal_data = dat[animal]
    n_days = animal_data['trace'].shape[0]
    print(f"  {n_days} days, {animal_data['trace'].shape[1]} total cells, "
          f"{animal_data['trace'].shape[2]} frames/day")

    for day in range(n_days):
```

**What this does:** Iterates over a hard-coded list of 7 animal names (ANIMALS), loading each animal's joblib file from the `data/` directory using `joblib.load`. Inside each animal dict, sessions ("days") are indexed by the first axis of `trace`, `position`, `envs`, and `blocked`, and each day is then split into 1-minute trials.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:171):
> Session = day: Each day of recording is one session. Each animal contributes multiple sessions.

**Code** (convert_data.py:29-30, 238, 245):
```python
ANIMALS = ["QLAK-CA1-08", "QLAK-CA1-30", "QLAK-CA1-50", "QLAK-CA1-51",
           "QLAK-CA1-56", "QLAK-CA1-74", "QLAK-CA1-75"]
...
subjects = list(animals_to_process)
...
for a_idx, animal in enumerate(animals_to_process):
```

**What this does:** Subjects are defined by a hard-coded list of 7 animal names; each name corresponds to one joblib file in `data/`. The list is stored directly into `subjects`, and each animal's data is processed under one `subject_idx` (a_idx).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:171):
> Session = day: Each day of recording is one session. Each animal contributes multiple sessions.

**Code** (convert_data.py:250-254, 128-129):
```python
n_days = animal_data['trace'].shape[0]
...
for day in range(n_days):
    ...
    neural_trials, input_trials, output_trials, n_valid = process_session(
        animal_data, day, ...)
...
# inside process_session:
trace = animal_data['trace'][day_idx]     # (n_cells, n_frames)
position = animal_data['position'][day_idx]  # (2, n_frames)
```

**What this does:** Sessions are indexed by the first axis (days) of the animal's `trace`/`position`/`envs` arrays. For each day, `process_session` is called with that day index to produce a list of trials.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:172-173):
> Trial = 1-minute segment: Split each ~40-min session into 1-minute trials. At 30Hz, 1 min = 1800 frames. After temporal binning by 3, each trial = 600 time bins.

**Code** (convert_data.py:33-35, 162-172):
```python
TRIAL_DURATION_SEC = 60  # 1 minute trials
FRAMES_PER_TRIAL = TRIAL_DURATION_SEC * FPS  # 1800 frames per trial
BINS_PER_TRIAL = FRAMES_PER_TRIAL // TEMPORAL_BIN_SIZE  # 600 time bins per trial
...
n_trials = n_total_bins // BINS_PER_TRIAL
for t in range(n_trials):
    start = t * BINS_PER_TRIAL
    end = (t + 1) * BINS_PER_TRIAL
    trial_neural = binned_trace[:, start:end]
    trial_output = pos_bins[start:end].reshape(1, -1).astype(np.int64)
    neural_trials.append(trial_neural)
    input_trials.append(env_input)
    output_trials.append(trial_output)
```

**What this does:** Each session is split into non-overlapping 60-second (1800-frame, or 600 post-binned) trials by integer division of total bins by `BINS_PER_TRIAL`. Remainder bins that don't fill a full trial are discarded.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:128-130):
> No explicit trial filtering in the reference (entire sessions used). Velocity filter: timepoints with smoothed speed > 5 cm/s included for decoding.

**Code** (convert_data.py:273-277):
```python
if len(neural_trials) < 2:
    print(f"  Day {day}: skipped (< 2 trials)")
    if fig is not None:
        plt.close(fig)
    continue
```

**What this does:** Only sessions with fewer than 2 trials are skipped. No per-trial QC/velocity filtering is applied; all 1-minute trials from eligible sessions are kept.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:41, 59):
> Neural data: `trace` is already binarized (0/1) - rising phase of calcium transients, z-scored > 2.5. `trace`: (n_days, n_cells, n_frames) - binary calcium events (0/1), NaN for unregistered cells on a day.

**Code** (convert_data.py:128, 139):
```python
trace = animal_data['trace'][day_idx]  # (n_cells, n_frames)
...
valid_trace = trace[valid_mask]  # (n_valid, n_frames)
```

**What this does:** The `neural` data is derived from the `trace` field of each animal's joblib file, indexed per day.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:180):
> Gaussian smoothing of trace: Reference `fit_decoder` applies `gaussian_filter1d(traces, sigma=temporal_bin_size, axis=0)` before binning. We should do the same (sigma=3 frames along time axis).

**Code** (convert_data.py:66-84):
```python
def temporal_bin_trace(trace_2d, sigma=TEMPORAL_BIN_SIZE, bin_size=TEMPORAL_BIN_SIZE):
    """
    1. Gaussian smooth along time axis (sigma=3 frames)
    2. Average pool with kernel=3, stride=3
    """
    smoothed = gaussian_filter1d(trace_2d.astype(np.float64), sigma=sigma, axis=1)
    n_cells, n_frames = smoothed.shape
    n_bins = n_frames // bin_size
    trimmed = smoothed[:, :n_bins * bin_size]
    binned = trimmed.reshape(n_cells, n_bins, bin_size).mean(axis=2)
    return binned.astype(np.float32)
```

**What this does:** Valid cells' binary trace is gaussian-smoothed along the time axis (sigma=3 frames), then average-pooled with a window/stride of 3 frames, producing a (n_valid_cells, n_bins) float32 array.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:176):
> Cell filtering: Include only registered cells per session (not NaN). No velocity filtering (that's decoder-specific).

**Code** (convert_data.py:138-140):
```python
# Identify valid (registered) cells for this day
valid_mask = ~np.isnan(trace[:, 0])
valid_trace = trace[valid_mask]  # (n_valid, n_frames)
n_valid = valid_mask.sum()
```

**What this does:** Cells not registered for the current day (NaN at frame 0 of that day's trace) are excluded. No event-count or velocity-based filtering is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:109, 178):
> Decoder temporal bin: 3 frames (100ms) - From code: temporal_bin_size=3. Time bin size: 100ms (3 frames at 30Hz) = 0.1s → for metadata.

**Code** (convert_data.py:31-39, 77-84):
```python
FPS = 30
TEMPORAL_BIN_SIZE = 3  # frames per time bin (from reference fit_decoder)
TIME_BIN_MS = (TEMPORAL_BIN_SIZE / FPS) * 1000  # 100 ms
...
smoothed = gaussian_filter1d(trace_2d.astype(np.float64), sigma=sigma, axis=1)
n_bins = n_frames // bin_size
trimmed = smoothed[:, :n_bins * bin_size]
binned = trimmed.reshape(n_cells, n_bins, bin_size).mean(axis=2)
```

**What this does:** The raw 30 Hz trace is gaussian-smoothed (sigma=3 frames) then downsampled by a factor of 3 via mean pooling, yielding 100 ms bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:179, convert_data.py metadata):
> Temporal alignment: Trials start at beginning of session recording. Align to session start.

**Code** (convert_data.py:162-170, 324-326):
```python
n_trials = n_total_bins // BINS_PER_TRIAL
for t in range(n_trials):
    start = t * BINS_PER_TRIAL
    end = (t + 1) * BINS_PER_TRIAL
    trial_neural = binned_trace[:, start:end]
...
'temporal_alignment_event': 'Start of recording session',
'off_start': 0.0,
'off_end': float(TRIAL_DURATION_SEC),
```

**What this does:** Trials are contiguous 60-second windows cut from the session starting at t=0. The metadata records `temporal_alignment_event` as "Start of recording session" with `off_start=0` and `off_end=60` seconds.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:165-168):
> `envs[day]` → `get_env_mat()` → input[0..8]: 3x3 binary matrix flattened to 9 values. Static per trial (same for all timepoints).

**Code** (convert_data.py:44-63, 130-132, 155):
```python
ENV_MATRICES = {
    'square':    np.array([[1,1,1],[1,1,1],[1,1,1]]),
    'o':         np.array([[1,1,1],[1,0,1],[1,1,1]]),
    ...
}

def get_env_input(env_name):
    mat = ENV_MATRICES.get(env_name)
    if mat is None:
        raise ValueError(f"Unknown environment: {env_name}")
    return mat.flatten().astype(np.float32)
...
env_name = str(animal_data['envs'][day_idx].item() if hasattr(...))
...
env_input = get_env_input(env_name)  # (9,)
```

**What this does:** The `input` is derived from the per-day `envs` field (environment name string), looked up in a hard-coded dictionary of 3x3 environment-shape matrices. The `blocked` field is not used.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

**Notes excerpt** (CONVERSION_NOTES.md:50, 175):
> `blocked` field: indicates which partitions of 3x3 grid are blocked. Layout: [[0,1,2],[3,4,5],[6,7,8]]. -1 means no blocks (square). Input: Environment geometry as 3x3 binary matrix (from `get_env_mat`), flattened to 9 values. Static per trial.

**Code** (convert_data.py:58-63, 171):
```python
def get_env_input(env_name):
    """Get flattened 3x3 environment matrix as decoder input (9 values)."""
    mat = ENV_MATRICES.get(env_name)
    if mat is None:
        raise ValueError(f"Unknown environment: {env_name}")
    return mat.flatten().astype(np.float32)
...
input_trials.append(env_input)  # (9,) static
```

**What this does:** The environment-name string is mapped to a hard-coded 3x3 binary geometry matrix (1 = open, 0 = wall/blocked) and flattened into a 9-element float32 vector. The same vector is repeated for every trial of that session. Note this encodes the inverse of "blocked" positions: 1 = accessible.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `input` *Blocked positions* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:167):
> Static per trial (same for all timepoints).

**Code** (convert_data.py:170-172):
```python
neural_trials.append(trial_neural)
input_trials.append(env_input)  # (9,) static
output_trials.append(trial_output)
```

**What this does:** The 9-element environment vector is appended once per trial (one (9,) array per trial), constant across the trial; no per-timepoint alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:60, 168):
> `position`: (n_days, 2, n_frames) - x,y position in cm, range [0, 75]. `position[day, :, :]` → output[0]: Discretize x,y into 3x3 bins → single index 0-8.

**Code** (convert_data.py:129):
```python
position = animal_data['position'][day_idx]  # (2, n_frames)
```

**What this does:** Output position is derived from the per-day `position` field (2 × n_frames x,y in cm) of the animal's joblib file.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `output` *Position*?

**Notes excerpt** (CONVERSION_NOTES.md:174):
> Output discretization: Position (0-75cm) into 3x3 grid (25cm bins). Bin index = floor(pos / 25), clamp to [0,2]. Combined bin = x_bin * 3 + y_bin → values 0-8.

**Code** (convert_data.py:87-115, 149-150):
```python
def discretize_position(position_2d, bin_size=SPATIAL_BIN_SIZE, n_bins=N_SPATIAL_BINS):
    x_bin = np.clip(np.floor(position_2d[0] / bin_size).astype(int), 0, n_bins - 1)
    y_bin = np.clip(np.floor(position_2d[1] / bin_size).astype(int), 0, n_bins - 1)
    return x_bin * n_bins + y_bin

def bin_position(position_2d, bin_size=TEMPORAL_BIN_SIZE):
    n_frames = position_2d.shape[1]
    n_bins = n_frames // bin_size
    trimmed = position_2d[:, :n_bins * bin_size]
    binned = trimmed.reshape(2, n_bins, bin_size).mean(axis=2)
    return binned
...
binned_pos = bin_position(position)
pos_bins = discretize_position(binned_pos)
```

**What this does:** Continuous (x,y) position in cm is first temporally averaged in 3-frame bins (matching the neural binning), then each axis is divided into 3 equal 25 cm bins via `floor(pos / 25)` clipped to [0,2], and combined as `x_bin * 3 + y_bin` to give an integer label 0–8.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:166-168):
> Both trace and position are temporally binned by 3 frames; trials extracted using same bin indices.

**Code** (convert_data.py:146-152, 167-168):
```python
binned_trace = temporal_bin_trace(valid_trace)  # (n_valid, n_total_bins)
binned_pos = bin_position(position)             # (2, n_total_bins)
pos_bins = discretize_position(binned_pos)      # (n_total_bins,)
n_total_bins = binned_trace.shape[1]
...
trial_neural = binned_trace[:, start:end]        # (n_valid, 600)
trial_output = pos_bins[start:end].reshape(1, -1).astype(np.int64)  # (1, 600)
```

**What this does:** Position and trace are both binned at 3-frame resolution, then sliced with identical `start:end` indices per trial, ensuring frame-by-frame alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:176):
> Cell filtering: Include only registered cells per session (not NaN).

**Code** (convert_data.py:138-143, 80-82, 273-277):
```python
valid_mask = ~np.isnan(trace[:, 0])
valid_trace = trace[valid_mask]
n_valid = valid_mask.sum()

if n_valid == 0:
    return [], [], [], 0
...
# remainder frames dropped:
n_bins = n_frames // bin_size
trimmed = smoothed[:, :n_bins * bin_size]
...
if len(neural_trials) < 2:
    print(f"  Day {day}: skipped (< 2 trials)")
    continue
```

**What this does:** Cells with NaN trace at frame 0 of a session are removed; sessions with zero valid cells return empty trials; sessions yielding fewer than 2 trials are skipped; remainder frames not divisible by the bin size or trial length are silently dropped. Unknown environment names raise an error.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:215-219):
> Per animal (avg) ~37s; Full (7 animals) ~4.3 min. Output `converted_data.pkl`: 6353.3 MB.

**Code** (convert_data.py:248, 78, 372-373):
```python
dat = joblib.load(os.path.join(data_dir, animal))
...
smoothed = gaussian_filter1d(trace_2d.astype(np.float64), sigma=sigma, axis=1)
...
with open(args.output, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** The script loads each animal joblib file (large I/O), then for each session runs a gaussian_filter1d on the (cells × frames) trace cast to float64, then pickles a multi-GB result. The notes report ~37 s per animal (~4.3 min total for 7 animals).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (none)

**Code** (convert_data.py:163-172, 245-302):
```python
for t in range(n_trials):
    start = t * BINS_PER_TRIAL
    end = (t + 1) * BINS_PER_TRIAL
    trial_neural = binned_trace[:, start:end]
    trial_output = pos_bins[start:end].reshape(1, -1).astype(np.int64)
    neural_trials.append(trial_neural)
    input_trials.append(env_input)
    output_trials.append(trial_output)
...
for a_idx, animal in enumerate(animals_to_process):
    ...
    for day in range(n_days):
        ...
```

**What this does:** Trials per session are constructed in a Python `for t in range(n_trials)` loop that slices contiguous windows; the per-animal and per-day loops are inherently sequential I/O-bound iterations.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (none)

**Code** (convert_data.py:155, 171, 102-115, 145-150):
```python
env_input = get_env_input(env_name)  # (9,)
...
input_trials.append(env_input)  # (9,) static -- repeated per trial
...
def bin_position(position_2d, ...):
    ...
binned_pos = bin_position(position)
pos_bins = discretize_position(binned_pos)
binned_trace = temporal_bin_trace(valid_trace)
```

**What this does:** The same (9,) environment-input vector is appended once per trial within a session (so the same array is stored multiple times). The trace and position are each binned/smoothed once per session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (none)

**Code** (convert_data.py:174-217, 19-21):
```python
matplotlib.use('Agg')
import matplotlib.pyplot as plt
...
if show_processing and fig_axes is not None and n_trials > 0:
    ax_neural, ax_pos, ax_output, ax_env = fig_axes
    ...
    ax_neural.imshow(binned_trace[:n_show, t_start:t_end], aspect='auto', ...)
    ...
    fig.savefig(f'processing_{animal}_day{day}.png', dpi=100)
```

**What this does:** Optional `--show-processing` plots draw 4-panel figures per session and save PNGs; these are not consumed by the decoder. Otherwise the conversion produces only the fields used downstream.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
