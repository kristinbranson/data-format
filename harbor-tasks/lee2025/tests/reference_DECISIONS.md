# Decisions

## 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

i. Each subject's data is stored in a separate HDF5-format MATLAB v7.3 `.mat` file (one file per mouse). The files are discovered by globbing `data/*.mat` and sorted alphabetically. Each file is opened with `h5py.File()`. Inside each file, the `trace`, `position`, and `blocked` fields are accessed via HDF5 object references — the top-level arrays contain references that must be dereferenced to read the actual data (e.g., `f[trace_refs[i][0]][:]`).

ii.
```python
mat_files = sorted(glob.glob(os.path.join(args.datadir, '*.mat')))
# ...
f = h5py.File(filepath, 'r')
trace_refs = f['trace']
pos_refs = f['position']
blk_refs = f['blocked'][:][0]
n_trials = trace_refs.shape[0]
for i in range(n_trials):
    trace = f[trace_refs[i][0]][:]
    position = f[pos_refs[i][0]][:].T
    blk_indices = f[blk_refs[i]][:].flatten()
```

iii. The data files are MATLAB v7.3 format (HDF5-based), so `h5py` is the appropriate library. The reference code (`georepca1/src/utils.py`) uses `mat73.loadmat()` for the same files, but `h5py` provides equivalent low-level access. The HDF5 reference-based storage requires dereferencing each trial's data individually.

## 1-b. How are the data split into subjects?

i. Each `.mat` file corresponds to one subject. The subject ID is extracted from the filename by stripping the `.mat` extension (e.g., `QLAK-CA1-08.mat` → `QLAK-CA1-08`). All data from one file is grouped as one session in the output structure.

ii.
```python
for mat_file in mat_files:
    name = mat_file.split('/')[-1].replace('.mat', '')
    subjects.append(name)
    neural_trials, input_trials, output_trials = process_mat_file(mat_file)
    all_neural.append(neural_trials)
    all_input.append(input_trials)
    all_output.append(output_trials)
```

iii. The dataset README states data is organized as one file per animal. Subject IDs match the filenames used in the original study (QLAK-CA1-08, QLAK-CA1-30, etc.). There are 7 subjects total.

## 1-c. How are the data split into sessions?

i. Each subject maps to exactly one session in the output format. Within each `.mat` file, there are multiple recordings (days/environments), which become the trials within that session. The outer list in `neural`, `input`, `output` is indexed by session (= subject), and the inner list by trial (= day/environment).

ii.
```python
all_neural.append(neural_trials)   # one session per subject
# ...
'subject_idx': np.arange(len(subjects)),  # session i belongs to subject i
```

iii. The target data format requires a list-of-sessions structure. Since all neurons for a given subject are tracked across all days (same neuron set), it is natural to treat the entire subject as one session with consistent `n_neurons` across trials.

## 1-d. How are the data split into trials?

i. Each recording day within a subject is one trial. Within each `.mat` file, `trace_refs.shape[0]` gives the number of days (typically 31: 3 sequences × 10 environments + 1 start/end square). Each day is iterated over and becomes one trial in the inner list.

ii.
```python
n_trials = trace_refs.shape[0]
for i in range(n_trials):
    trace = f[trace_refs[i][0]][:]
    # ...
    neural_trials.append(trace_int8.T)
```

iii. The paper states animals were exposed to sequences of environments across days, with one session recorded per day. Each 40-minute recording session is a natural trial boundary.

## 1-e. How are trials filtered based on quality controls?

i. No trials are filtered or excluded. All days present in each `.mat` file are included.

ii. No filtering code is present — every trial from 0 to `n_trials` is processed.

iii. The data has already been preprocessed through the authors' pipeline (motion correction, cell segmentation, manual inspection). No additional trial-level quality filtering is applied by the conversion code.

## 2-a. What variables in the raw data is the `neural` data derived from?

i. The `neural` data is derived from the `trace` field in each `.mat` file. This contains the rising-phase-extracted calcium transients, where 1 indicates a significant calcium event and 0 indicates no event. NaN indicates a neuron that was not registered on that day.

ii.
```python
trace = f[trace_refs[i][0]][:]
```

iii. The paper describes a preprocessing pipeline that extracts the rising phase of calcium transients: the derivative of the calcium signal is smoothed with a 5-frame Gaussian kernel, z-scored based on noise estimated from a half-normal distribution, and binarized at a threshold of 2.5σ. The `trace` field contains the result of this pipeline. The README confirms: "rise-extracted calcium traces, where '1' indicates a significant event."

## 2-b. How is the `neural` data processed?

i. No additional processing is applied to the neural data beyond what is already in the `.mat` files. The data is already binarized (0/1/NaN). The code only handles the NaN→-1 conversion and transposes from `(timepoints, neurons)` to `(neurons, timepoints)`.

ii.
```python
trace = f[trace_refs[i][0]][:]
nan_mask = np.isnan(trace)
trace[nan_mask] = -1
trace_int8 = trace.astype(np.int8)
neural_trials.append(trace_int8.T)
```

iii. The data arrives already preprocessed (rising-phase extraction, binarization at 2.5σ). No smoothing, filtering, or additional thresholding is applied. The paper states "All analyses were conducted using the binary vector of the rising phases of transients, treating this vector as if it were the firing rate of the cell." The conversion preserves this.

## 2-c. How is the `neural` data filtered based on quality controls?

i. No neurons are filtered or excluded. All neurons present in the `.mat` file are included, including those with NaN values on certain days (indicating the neuron was not registered on that day).

ii. No filtering code is present. All neurons are retained.

iii. The preprocessing pipeline already includes manual verification of spatial footprints and motion correction. Neurons not registered on a given day are represented as NaN (stored as -1 in int8) rather than being excluded entirely.

## 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

i. No explicit temporal alignment is performed. Each trial's neural data starts at the beginning of the recording session and runs for its full duration. The instruction specifies no specific alignment event — the data is used as-is from the start of each session.

ii.
```python
neural_trials.append(trace_int8.T)  # full recording, no trimming or alignment
```

iii. The instruction.md does not specify a temporal alignment event for this task (unlike sosa2024 which aligns to trial start). Each recording session is a continuous 40-minute exploration period with no discrete trial events to align to.

## 2-e. What is the temporal resolution (time bin size) of the converted data? Is any temporal rebinning applied?

i. The temporal resolution is the native 30 Hz acquisition rate, giving a time bin size of ~33.33 ms (1000/30). No temporal rebinning is applied.

ii.
```python
TIME_BIN_SIZE = 1000.0 / 30.0  # ~33.33 ms
# ...
'metadata': {
    'time_bin_size': TIME_BIN_SIZE,
}
```

iii. The paper states "The DAQ simultaneously acquired behavioral and cellular imaging streams at 30 Hz." The neural traces and position data are already sampled at this rate, so no rebinning is needed.

## 3-a. What variables in the raw data is `input` *Environment geometry* derived from?

i. The input is derived from the `blocked` field in each `.mat` file. This field contains the indices of which partitions in the 3×3 grid are walled off (occluded) for each day's environment. The grid positions are indexed as [[0,1,2],[3,4,5],[6,7,8]]. A value of -1 indicates no partitions are blocked (open square).

ii.
```python
blk_refs = f['blocked'][:][0]
# ...
blk_indices = f[blk_refs[i]][:].flatten()
input_trials.append(encode_blocked(blk_indices))
```

iii. The README states: "blocked: location of blocked (occluded) partitions in 3x3 design of environment. Location of partitions are shown in paper, but are organized in the following way – [[0, 1, 2], [3, 4, 5], [6, 7, 8]]. If no partitions are blocked, value is -1."

## 3-b. What processing is involved in computing `input` *Environment geometry*?

i. The blocked partition indices are converted to a 9-dimensional one-hot binary vector. Each dimension represents one cell in the 3×3 grid. A value of 1 means that partition is walled, 0 means it is open. The special case of `[-1]` (no partitions blocked, i.e., open square) results in an all-zeros vector.

ii.
```python
def encode_blocked(blk_indices, n_positions=N_BLOCKED_POSITIONS):
    blocked = np.zeros(n_positions, dtype=np.int8)
    if not (len(blk_indices) == 1 and blk_indices[0] == -1):
        blocked[blk_indices.astype(int)] = 1
    return blocked
```

iii. The instruction specifies "Environment geometry as 9-dimensional binary vector, each dimension representing a grid location. Its value should be 1 if walled and 0 if open." The encoding directly maps blocked indices to a binary vector. The -1 sentinel is handled as a special case for the open square environment.

## 3-c. How is the `input` *Environment geometry* aligned with the neural data?

i. The environment geometry is static per trial — it does not vary over time. It is stored as a 1D array of shape `(9,)` rather than `(9, n_timepoints)`. No temporal alignment is needed.

ii.
```python
input_trials.append(encode_blocked(blk_indices))  # shape: (9,), not time-varying
```

iii. The instruction specifies the environment geometry is "static per-trial." Each recording session uses one fixed environment geometry, so there is no time dimension.

## 4-a. What variables in the raw data is `output` *Mouse position* derived from?

i. The output is derived from the `position` field in each `.mat` file. This contains continuous (x, y) coordinates of the mouse's head position, tracked at 30 Hz, within the 75×75 cm arena.

ii.
```python
position = f[pos_refs[i][0]][:].T
output_trials.append(discretize_position(position)[np.newaxis, :])
```

iii. The README states: "position: x-y position data for all days." The paper describes position tracking via DeepLabCut pose-estimation software applied to overhead webcam video.

## 4-b. What processing is involved in computing `output` *Mouse position*?

i. The continuous (x, y) position is discretized into spatial grid bins. The 75 cm arena is divided into equal-sized bins along each axis. Each (x, y) coordinate is independently binned using `np.digitize()`, then the 2D bin indices are combined into a single 1D class label using row-major ordering: `label = y_bin * n_grid + x_bin`.

ii.
```python
def discretize_position(position, n_grid=N_GRID, arena_size=ARENA_SIZE):
    edges = np.linspace(0, arena_size, n_grid + 1)[1:-1]
    x_bin = np.clip(np.digitize(position[0], edges), 0, n_grid - 1)
    y_bin = np.clip(np.digitize(position[1], edges), 0, n_grid - 1)
    return (y_bin * n_grid + x_bin).astype(np.int8)
```

iii. The instruction requires position discretized into spatial bins. The bin edges are computed as evenly spaced divisions of the arena, and `np.digitize` assigns each coordinate to the appropriate bin.

## 4-c. How is `output` *Mouse position* thresholded into categories?

i. A 5×5 grid is used, producing 25 position categories (labels 0–24). Each bin is 15×15 cm (75/5). The bin edges are at [15, 30, 45, 60] cm. This **differs from the instruction**, which specifies "3 × 3 = 9 spatial bins, each of length 25cm." The code uses `N_GRID = 5` instead of 3.

ii.
```python
N_GRID = 5
# edges = np.linspace(0, 75, 6)[1:-1]  →  [15, 30, 45, 60]
# produces 25 classes: 0..24
n_classes = N_GRID ** 2  # 25
output_values = [[f"grid_{i}" for i in range(n_classes)]]
```

iii. The choice of 5×5 over the instructed 3×3 provides finer spatial resolution. This may have been chosen to better match the reference code's decoding analysis, which uses `n_bins=15` (even finer). However, it deviates from the explicit instruction. The reference paper's Bayesian decoder uses 15×15 spatial bins (2.5 cm Gaussian smoothing on rate maps), but the instruction asked for 3×3 = 9 bins of 25 cm each.

## 4-d. How is `output` *Mouse position* aligned with the neural data?

i. Position is sampled at the same 30 Hz rate as the neural data by the acquisition system, so the arrays are already temporally aligned frame-by-frame. No interpolation or resampling is applied.

ii.
```python
# Both trace and position have the same n_timepoints per trial
# trace shape: (timepoints, neurons), position shape: (2, timepoints)
```

iii. The paper states both behavioral and cellular imaging streams were acquired simultaneously at 30 Hz and timestamped for post-hoc alignment. The data in the `.mat` files is already aligned.

## 5-a. What is the temporal resolution (time bin size) of the converted data? Is any temporal rebinning applied?

i. Same as 2-e. The native 30 Hz rate (~33.33 ms bins) is preserved. No rebinning is applied.

ii.
```python
TIME_BIN_SIZE = 1000.0 / 30.0  # ~33.33 ms
```

iii. Both neural and behavioral data are acquired at 30 Hz. No rebinning is needed since all streams share the same temporal resolution.

## 5-b. How are the neural, input, and output data temporally aligned?

i. Neural (trace) and output (position) are both sampled at 30 Hz and stored with matching timepoints per trial. The input (environment geometry) is static per trial and does not require temporal alignment. No explicit alignment step is performed — the data is already synchronized from acquisition.

ii.
```python
# Per trial:
# neural: (n_neurons, n_timepoints) from trace
# output: (1, n_timepoints) from position, same n_timepoints
# input: (9,) static, no time dimension
```

iii. The DAQ simultaneously records both streams at 30 Hz with timestamped frames.

## 6. How are minor issues in the data (e.g., missing data, malformed entries) handled?

i. NaN values in the neural trace data (indicating neurons not registered on a given day) are replaced with -1 before converting to int8. No other missing data handling is performed. Position data and blocked indices are assumed to be complete.

ii.
```python
nan_mask = np.isnan(trace)
trace[nan_mask] = -1
trace_int8 = trace.astype(np.int8)
```

iii. The NaN→-1 encoding preserves the distinction between inactive neurons (0) and missing neurons (-1) while allowing int8 storage. The metadata documents this encoding: `'neural_encoding': 'int8: 0=inactive, 1=active, -1=missing (NaN)'`.

## 7-a. What are the most time-consuming steps of the code?

i. Loading and reading the HDF5 `.mat` files is the most time-consuming step, as each file is hundreds of MB (296–794 MB). Within each file, dereferencing and reading each trial's `trace` array (shape: ~71866 timepoints × ~515 neurons) dominates I/O time.

ii.
```python
for i in range(n_trials):
    trace = f[trace_refs[i][0]][:]  # reads large array from disk
```

iii. The data is I/O-bound. Each subject has ~31 trials, each with ~37M elements in the trace array alone.

## 7-b. What loops in the code could have been vectorized to improve efficiency?

i. The per-trial loop within `process_mat_file` iterates over trials sequentially. However, this is largely unavoidable because each trial's data is stored as an HDF5 object reference that must be dereferenced individually. The `discretize_position` and `encode_blocked` functions are already vectorized within each trial.

ii.
```python
for i in range(n_trials):  # must iterate due to HDF5 reference structure
    trace = f[trace_refs[i][0]][:]
```

iii. The HDF5 reference-based storage prevents bulk reads across trials. The computation per trial (NaN masking, type casting, transpose, digitize) is already vectorized over timepoints/neurons.

## 7-c. What processing does the code repeat multiple times?

i. No processing is repeated. Each trial's data is read, processed, and stored exactly once. The `discretize_position` function computes `np.linspace` bin edges on each call, but this is trivially fast.

ii. N/A — no redundant processing.

iii. The code is straightforward single-pass processing.

## 7-d. What unnecessary processing does the code do that is discarded in downstream analyses?

i. No unnecessary processing is performed. The code reads only the fields needed (`trace`, `position`, `blocked`) and does not load `SFPs`, `centroids`, `envs`, or `maps`. All processed data is included in the output.

ii. N/A — no discarded processing.

iii. The code is minimal and only computes what is needed for the target format.

## 8. How are minor mistakes in the data, e.g. missing data, handled?

i. Same as question 6. NaN values in neural traces are encoded as -1 in int8. No other error handling for data issues is present. Position values outside the arena range [0, 75] are clipped to valid bin indices via `np.clip()`.

ii.
```python
x_bin = np.clip(np.digitize(position[0], edges), 0, n_grid - 1)
y_bin = np.clip(np.digitize(position[1], edges), 0, n_grid - 1)
```

iii. Clipping ensures position values at or beyond arena boundaries are assigned to the nearest valid bin rather than producing out-of-range indices.

## 9-a. What are the most time-consuming steps of the code?

i. Same as 7-a. HDF5 file I/O dominates — reading large trace and position arrays from disk.

ii. See 7-a.

iii. See 7-a.

## 9-b. What loops in the code could have been vectorized to improve efficiency?

i. Same as 7-b. The per-trial loop is required by the HDF5 reference structure. Inner operations are already vectorized.

ii. See 7-b.

iii. See 7-b.

## 9-c. What processing does the code repeat multiple times?

i. Same as 7-c. No redundant processing.

ii. See 7-c.

iii. See 7-c.

## 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

i. Same as 7-d. No unnecessary processing.

ii. See 7-d.

iii. See 7-d.
