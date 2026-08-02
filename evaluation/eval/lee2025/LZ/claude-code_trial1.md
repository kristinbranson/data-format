# lee2025 — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/lee2025/claude/2026-03-10__11-18-23_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:59-67 — "Each animal stored as joblib file: `data/{animal_id}` -> dict with animal_id key containing: `trace`: shape (n_days, n_cells, n_frames) ... `position`: shape (n_days, 2, n_frames) ... `envs`: shape (n_days, 1) ..."

**Code** (convert_data.py:26-30, 84-88, 281-296):
```python
ANIMALS = [
    "QLAK-CA1-08", "QLAK-CA1-30", "QLAK-CA1-50", "QLAK-CA1-51",
    "QLAK-CA1-56", "QLAK-CA1-74", "QLAK-CA1-75"
]
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
...
def load_animal_data(animal):
    """Load preprocessed data for one animal from joblib file."""
    filepath = os.path.join(DATA_DIR, animal)
    dat = joblib.load(filepath)
    return dat[animal]
...
for animal in animals:
    neural, inp, out, sess_info = process_animal(
        animal, show_processing=show_processing
    )
```

**What this does:** Loads each of 7 hardcoded animals from preprocessed joblib files in the `data/` directory using `joblib.load`, then iterates over animals and sessions (days) within each.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:59 — "Each animal stored as joblib file: `data/{animal_id}` -> dict with animal_id key"

**Code** (convert_data.py:26-29, 286, 311-312):
```python
ANIMALS = [
    "QLAK-CA1-08", "QLAK-CA1-30", "QLAK-CA1-50", "QLAK-CA1-51",
    "QLAK-CA1-56", "QLAK-CA1-74", "QLAK-CA1-75"
]
...
subject_id = ANIMALS.index(animal)
...
'subjects': ANIMALS,
'subject_idx': np.array(subject_idx_list, dtype=np.int64),
```

**What this does:** Subjects are an explicit hardcoded list of 7 animal IDs. Each `.mat`/joblib file corresponds to one subject; subject_idx maps each session to its position in the ANIMALS list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:60 — "trace: shape (n_days, n_cells, n_frames) - binary calcium events"; CONVERSION_NOTES.md:110 — "Each session (day) is one continuous 40-min recording"

**Code** (convert_data.py:102-120):
```python
n_days = d['trace'].shape[0]
n_cells_total = d['trace'].shape[1]
n_frames_total = d['trace'].shape[2]
envs = d['envs'].squeeze()
...
for day in range(n_days):
    t_day = time.time()
    env_name = envs[day]

    # Get trace for this day: (n_cells, n_frames)
    trace = d['trace'][day]
    position = d['position'][day]  # (2, n_frames)
```

**What this does:** Each day index along the first axis of `trace`/`position`/`envs` is treated as one session. The script iterates `for day in range(n_days)` to produce a session per day per animal.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:144 — "Trial definition: 1-minute segments (1800 frames at 30Hz), ~40 trials per session"; CONVERSION_NOTES.md:266 — "Last trial has fewer frames when session length isn't divisible by 1800 (min T=1666). Partial trials <900 frames (30s) are dropped"

**Code** (convert_data.py:31-34, 141-152):
```python
FPS = 30  # Recording frame rate (Hz)
TRIAL_DURATION_S = 60  # 1-minute trials
FRAMES_PER_TRIAL = FPS * TRIAL_DURATION_S  # 1800 frames
MIN_TRIAL_FRAMES = FPS * 30  # Minimum 30s for a partial trial at end
...
trial_starts = list(range(0, n_frames, FRAMES_PER_TRIAL))
neural_trials = []
input_trials = []
output_trials = []

for start in trial_starts:
    end = min(start + FRAMES_PER_TRIAL, n_frames)
    trial_len = end - start

    # Skip short partial trials
    if trial_len < MIN_TRIAL_FRAMES:
        continue
```

**What this does:** Sessions are split into non-overlapping 1800-frame (60-second) trials. The final partial trial is kept if it is at least 900 frames (30 s); shorter remainders are dropped. Sessions yielding fewer than 2 trials are skipped entirely.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:110 — "Trial curation rules: No trial filtering."; CONVERSION_NOTES.md:266-269 — "Partial trials <900 frames (30s) are dropped ... All sessions produce >=2 trials"

**Code** (convert_data.py:150-152, 167-170):
```python
# Skip short partial trials
if trial_len < MIN_TRIAL_FRAMES:
    continue
...
n_trials = len(neural_trials)
if n_trials < 2:
    print(f"  Day {day} ({env_name}): Only {n_trials} trial(s), skipping (need >=2)")
    continue
```

**What this does:** No QC-based trial filtering is applied; the only exclusions are length-based (drop final partial trials shorter than 30 s, drop entire sessions producing fewer than 2 trials).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:60 — "trace: shape (n_days, n_cells, n_frames) - binary calcium events (0/1), NaN for unregistered cells"; CONVERSION_NOTES.md:139 — "trace[day] (binary events) -> neural"

**Code** (convert_data.py:118-119, 154-155):
```python
trace = d['trace'][day]
position = d['position'][day]  # (2, n_frames)
...
# Neural: (n_registered, trial_len)
neural_trial = trace_registered[:, start:end].astype(np.float32)
```

**What this does:** Neural data comes from the `trace` field of the per-animal joblib dictionary, which holds preprocessed binary calcium events with shape `(n_days, n_cells, n_frames)`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:46 — "Data is already preprocessed: binary calcium trace (0/1 for significant events from rising-phase extraction)"; CONVERSION_NOTES.md:47 — "No delta F/F computation needed - trace is already binarized"; CONVERSION_NOTES.md:148 — "Neural data: Raw binary trace (0/1), only registered cells per session"

**Code** (convert_data.py:124-132, 154-155):
```python
# Identify registered cells (non-NaN on this day)
registered_mask = ~np.isnan(trace[:, 0])
n_registered = np.sum(registered_mask)
...
# Extract registered cells' traces
trace_registered = trace[registered_mask]  # (n_registered, n_frames)
...
# Neural: (n_registered, trial_len)
neural_trial = trace_registered[:, start:end].astype(np.float32)
```

**What this does:** No additional transformation is applied beyond selecting registered cells and casting to float32. The trace is used as-is (binary 0/1 events) at native shape `(n_registered, trial_len)` per trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:108 — "Neuron curation rules: Use ALL registered cells on each day (non-NaN trace). No place-cell filtering."

**Code** (convert_data.py:124-132):
```python
# Identify registered cells (non-NaN on this day)
registered_mask = ~np.isnan(trace[:, 0])
n_registered = np.sum(registered_mask)

if n_registered == 0:
    print(f"  Day {day} ({env_name}): No registered cells, skipping")
    continue

# Extract registered cells' traces
trace_registered = trace[registered_mask]  # (n_registered, n_frames)
```

**What this does:** Cells with NaN in their first frame on a given day (i.e. unregistered for that session) are removed; all remaining registered cells are kept. No place-cell or other QC filtering is applied. Sessions with zero registered cells are skipped.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:147 — "Time bin: 30Hz native sampling (33.33ms)"

**Code** (convert_data.py:31-33, 320-321):
```python
FPS = 30  # Recording frame rate (Hz)
TRIAL_DURATION_S = 60  # 1-minute trials
FRAMES_PER_TRIAL = FPS * TRIAL_DURATION_S  # 1800 frames
...
'time_bin_size': 1000.0 / FPS,  # ~33.33 ms
```

**What this does:** No resampling. The neural trace is kept at native 30 Hz; the metadata reports `time_bin_size = 33.33 ms`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:144 — "Trial definition: 1-minute segments (1800 frames at 30Hz)"

**Code** (convert_data.py:141-155, 320-323):
```python
trial_starts = list(range(0, n_frames, FRAMES_PER_TRIAL))
...
for start in trial_starts:
    end = min(start + FRAMES_PER_TRIAL, n_frames)
    trial_len = end - start
    ...
    neural_trial = trace_registered[:, start:end].astype(np.float32)
...
'temporal_alignment_event': 'Start of each 1-minute trial segment within a 40-minute recording session',
'off_start': 0.0,
'off_end': float(TRIAL_DURATION_S),
```

**What this does:** There is no external event to align to; trials are defined as fixed 1-minute slices of the continuous recording. Metadata declares the alignment event as the start of each trial segment, with `off_start=0.0` and `off_end=60.0` seconds.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Blocked positions* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:140 — "Environment geometry 3x3 -> input[0-8] | get_env_mat(env) -> flatten to 9 values, static per trial | 1=accessible, 0=blocked"; CONVERSION_NOTES.md:63 — "blocked: list of n_days arrays - blocked partition indices (-1 for square)"

**Code** (convert_data.py:41-65, 116, 134-135):
```python
def get_env_mat(env):
    """Get binary 3x3 matrix for environment geometry. From reference code."""
    if env == 'square':
        return np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]]).astype(float)
    elif env == 'o':
        return np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]]).astype(float)
    ...
...
env_name = envs[day]
...
# Get environment geometry as input (3x3 flattened to 9)
env_mat = get_env_mat(env_name).flatten()  # (9,)
```

**What this does:** Rather than using the raw `blocked` field, the input is derived from `envs[day]` (the environment name string) by mapping it through `get_env_mat`, which returns a hardcoded 3x3 binary mask of accessible vs. blocked partitions for each of 10 environment shapes.

**Rating:** ok

**Note:** valid solution but a bit complicted

---

## Q 3-b. What processing is involved in computing `input` *Blocked positions*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:140 — "Environment geometry 3x3 -> input[0-8] | get_env_mat(env) -> flatten to 9 values, static per trial | 1=accessible, 0=blocked"

**Code** (convert_data.py:134-135, 157-158, 304-305):
```python
# Get environment geometry as input (3x3 flattened to 9)
env_mat = get_env_mat(env_name).flatten()  # (9,)
...
# Input: environment geometry, static per trial -> (9,)
input_trial = env_mat.astype(np.float32)
...
# Input names: environment geometry partitions
input_names = [f"env_partition_{r}{c}" for r in range(N_POS_BINS) for c in range(N_POS_BINS)]
```

**What this does:** The 3x3 environment matrix is flattened to a length-9 float32 vector (1=accessible, 0=blocked) and assigned as a static per-trial input. Input feature names are `env_partition_rc` for r,c in 0..2. The encoding is the inverse of "blocked" (it marks accessible cells).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:61 — "position: shape (n_days, 2, n_frames) - x,y position in cm (0-75 range)"; CONVERSION_NOTES.md:141 — "Position binned to 3x3 -> output[0]"

**Code** (convert_data.py:120, 137-138):
```python
position = d['position'][day]  # (2, n_frames)
...
# Bin position to 3x3 grid
pos_bins = bin_position_3x3(position)  # (n_frames,)
```

**What this does:** Position is taken from the `position` field of the per-animal joblib dictionary, which holds (2, n_frames) x,y coordinates per day in cm.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:147 — "Position discretization: 3x3 grid, row-major ordering (bin_idx = x_bin*3 + y_bin)"

**Code** (convert_data.py:67-81, 160-161):
```python
def bin_position_3x3(position, env_size=ENV_SIZE_CM):
    """
    Bin x,y position into 3x3 grid. Returns integer bin index 0-8 (row-major).
    position: (2, n_frames) array of x, y coordinates
    Returns: (n_frames,) array of bin indices 0-8
    """
    buffer = 1e-5
    bin_size = (env_size + buffer) / N_POS_BINS
    x_bin = np.clip(np.floor(position[0] / bin_size).astype(int), 0, N_POS_BINS - 1)
    y_bin = np.clip(np.floor(position[1] / bin_size).astype(int), 0, N_POS_BINS - 1)
    # Row-major: bin_idx = x_bin * 3 + y_bin
    bin_idx = x_bin * N_POS_BINS + y_bin
    return bin_idx
...
# Output: position bin, time-varying -> (1, trial_len)
output_trial = pos_bins[start:end].astype(np.int64).reshape(1, -1)
```

**What this does:** The 2D x,y position is discretized into a 3x3 grid across the 75 cm arena by `floor(pos / (75/3))`, clipping to [0, 2], and combining as `x_bin*3 + y_bin` to yield an integer bin index 0-8. The per-trial output has shape `(1, trial_len)` and dtype int64. Output values are labeled `x{r}y{c}` for r,c in 0..2.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:60-61 — both `trace` and `position` share the `n_frames` dimension per day

**Code** (convert_data.py:118-121, 146-161):
```python
trace = d['trace'][day]
position = d['position'][day]  # (2, n_frames)
n_frames = trace.shape[1]
...
for start in trial_starts:
    end = min(start + FRAMES_PER_TRIAL, n_frames)
    ...
    neural_trial = trace_registered[:, start:end].astype(np.float32)
    ...
    output_trial = pos_bins[start:end].astype(np.int64).reshape(1, -1)
```

**What this does:** Position is sampled at the same 30 Hz as the neural trace and is sliced with identical `[start:end]` indices per trial, giving frame-for-frame alignment with the neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:60 — "NaN for unregistered cells"; CONVERSION_NOTES.md:266-269 — "Last trial has fewer frames when session length isn't divisible by 1800 ... Partial trials <900 frames (30s) are dropped ... All sessions produce >=2 trials"

**Code** (convert_data.py:124-132, 146-152, 167-170):
```python
registered_mask = ~np.isnan(trace[:, 0])
n_registered = np.sum(registered_mask)

if n_registered == 0:
    print(f"  Day {day} ({env_name}): No registered cells, skipping")
    continue
...
for start in trial_starts:
    end = min(start + FRAMES_PER_TRIAL, n_frames)
    trial_len = end - start

    if trial_len < MIN_TRIAL_FRAMES:
        continue
...
n_trials = len(neural_trials)
if n_trials < 2:
    print(f"  Day {day} ({env_name}): Only {n_trials} trial(s), skipping (need >=2)")
    continue
```

**What this does:** Unregistered cells (NaN traces for that day) are dropped via `~np.isnan(trace[:, 0])`. Days with zero registered cells or fewer than 2 produced trials are skipped. Final partial trials shorter than 30 s are dropped. No imputation of missing position frames is performed.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:185-187 — "~21s per animal average, 42.5s for 2 animals. Full run estimated: ~160s (actual: 159.8s)"; CONVERSION_NOTES.md:99 — print statements wrap each animal/day with `time.time()` timings

**Code** (convert_data.py:84-88, 98-100, 183-184, 189-190):
```python
def load_animal_data(animal):
    """Load preprocessed data for one animal from joblib file."""
    filepath = os.path.join(DATA_DIR, animal)
    dat = joblib.load(filepath)
    return dat[animal]
...
def process_animal(animal, show_processing=False):
    t0 = time.time()
    print(f"\nProcessing {animal}...")
    d = load_animal_data(animal)
...
        dt = time.time() - t_day
        print(f"  Day {day} ({env_name}): {n_registered} cells, {n_trials} trials, {dt:.1f}s")
...
    dt_total = time.time() - t0
    print(f"  {animal} done: {len(all_neural)} sessions, {dt_total:.1f}s total")
```

Conversion full output (conversion_full_out.txt) reports per-animal totals around 20-25 s each, with total `Dataset built` ~160 s; saving the pickle takes additional time and produces a ~19 GB file (per CONVERSION_NOTES.md:211).

**What this does:** The script instruments per-animal and per-day wall-clock times via `time.time()`. The dominant cost is loading the per-animal joblib files (`load_animal_data`) and writing the large output pickle.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:160 — "Efficient vectorized operations (no inner loops for trace/position)"

**Code** (convert_data.py:114-165):
```python
for day in range(n_days):
    ...
    trace = d['trace'][day]
    position = d['position'][day]
    ...
    pos_bins = bin_position_3x3(position)  # vectorized
    trial_starts = list(range(0, n_frames, FRAMES_PER_TRIAL))
    ...
    for start in trial_starts:
        end = min(start + FRAMES_PER_TRIAL, n_frames)
        ...
        neural_trial = trace_registered[:, start:end].astype(np.float32)
        ...
        output_trial = pos_bins[start:end].astype(np.int64).reshape(1, -1)
        ...
        neural_trials.append(neural_trial)
        input_trials.append(input_trial)
        output_trials.append(output_trial)
```

**What this does:** The remaining loops are an outer animal loop, an outer day/session loop, and an inner trial-slicing loop that builds Python lists of array slices. Position binning is already vectorized via NumPy. The trial-splitting loop could in principle be replaced by a single reshape on the truncated trace.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:134-135, 157-158):
```python
# Get environment geometry as input (3x3 flattened to 9)
env_mat = get_env_mat(env_name).flatten()  # (9,)
...
# Input: environment geometry, static per trial -> (9,)
input_trial = env_mat.astype(np.float32)
```

**What this does:** The same constant `env_mat` is appended once per trial in the input list (so it is duplicated per trial within a session). Per-day cell registration and position binning are computed once per session.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:65-66 — fields like `maps`, `SFPs`, `centroids` exist in the source data but are not used; CONVERSION_NOTES.md:60 — `blocked` field is loaded by source but trial1 derives input from `envs` instead

**Code** (convert_data.py:100-119, 196-260):
```python
d = load_animal_data(animal)

n_days = d['trace'].shape[0]
n_cells_total = d['trace'].shape[1]
n_frames_total = d['trace'].shape[2]
envs = d['envs'].squeeze()
...
trace = d['trace'][day]
position = d['position'][day]  # (2, n_frames)
...
def plot_processing(animal, d, all_neural, all_input, all_output, session_info):
    """Plot processing visualizations for up to 2 sessions."""
    ...
```

**What this does:** Only `trace`, `position`, and `envs` are read from `d`; the source-data fields `blocked`, `maps`, `SFPs`, `centroids` are loaded into memory (as part of the joblib dict) but never used for the converted output. The optional `plot_processing` path produces PNGs that are not part of the output dataset (gated behind `--show-processing`).

**Rating:** match

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:160 — "Efficient vectorized operations (no inner loops for trace/position)"
>
> No section of CONVERSION_NOTES.md or README.md discusses memory, RAM, dtype sizing, or streaming; the "Run Time Estimates" section (CONVERSION_NOTES.md:185-188) reports wall-clock only.

**Code** (convert_data.py:100, 132, 155-161, 192):
```python
    d = load_animal_data(animal)          # whole animal joblib dict held in RAM
    ...
        trace_registered = trace[registered_mask]  # (n_registered, n_frames)
    ...
            # Neural: (n_registered, trial_len)
            neural_trial = trace_registered[:, start:end].astype(np.float32)

            # Input: environment geometry, static per trial -> (9,)
            input_trial = env_mat.astype(np.float32)

            # Output: position bin, time-varying -> (1, trial_len)
            output_trial = pos_bins[start:end].astype(np.int64).reshape(1, -1)
    ...
    del d  # Free memory
    return all_neural, all_input, all_output, session_info
```

**What this does:** Animals are loaded and converted one at a time, with `del d` at the end of `convert_animal` releasing that animal's joblib dict before the next is loaded; there is no `gc.collect()`, memory-mapping, or chunked read. Per-trial neural slices are cast to `float32` and outputs to `int64`; trials are stored at the native 30 Hz frame rate (1800 frames each) with no temporal pooling. Converted trials accumulate in Python lists and the whole dataset is held in memory until the final pickle dump.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
