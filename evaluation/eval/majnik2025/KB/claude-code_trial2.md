# majnik2025 — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/majnik2025/claude/2026-03-10__11-18-23_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Each session: YYYY-MM-DD_a/ suite2p/plane0/ F.npy ... move_deve/ motion_energy_glob.npy, tstamps.npy, interframe_int.npy" (CONVERSION_NOTES.md:57-69)

**Code** (convert_data.py:41-51, 156-166, 333-361):
```python
SUBJECTS = ['jm031', 'jm032', 'jm038', 'jm039', 'jm040', 'jm046']

def get_sessions(subject_dir):
    sessions = []
    for d in sorted(os.listdir(subject_dir)):
        full = os.path.join(subject_dir, d)
        if os.path.isdir(full) and not d.startswith('.'):
            sessions.append(full)
    return sessions

# in process_session:
s2p_dir = os.path.join(session_dir, 'suite2p', 'plane0')
me_dir = os.path.join(session_dir, 'move_deve')
F = np.load(os.path.join(s2p_dir, 'F.npy'))
Fneu = np.load(os.path.join(s2p_dir, 'Fneu.npy'))
me = np.load(os.path.join(me_dir, 'motion_energy_glob.npy'))
tstamps = np.load(os.path.join(me_dir, 'tstamps.npy'))
```

**What this does:** Subjects are an explicit hardcoded list of 6 mouse IDs (jm031–jm046). Sessions are obtained by sorting subdirectories (excluding hidden) within each subject. For each session, neural data (`F.npy`, `Fneu.npy`) is loaded from `suite2p/plane0` and motion-energy/timestamps from `move_deve`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "data/ jm031/ (Mouse A - 7 sessions, 221 neurons) ... jm046/" (CONVERSION_NOTES.md:50-56)

**Code** (convert_data.py:41, 339-341):
```python
SUBJECTS = ['jm031', 'jm032', 'jm038', 'jm039', 'jm040', 'jm046']
...
for subj_idx, subject in enumerate(subjects_to_process):
    subject_dir = os.path.join(DATA_DIR, subject)
```

**What this does:** Subjects are defined by an explicit hardcoded list of 6 IDs. Each ID corresponds to a top-level directory under `data/`. Subject index is the position in `SUBJECTS`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions/mouse | min 6 consecutive days" (CONVERSION_NOTES.md:91)

**Code** (convert_data.py:44-51, 345-347):
```python
def get_sessions(subject_dir):
    sessions = []
    for d in sorted(os.listdir(subject_dir)):
        full = os.path.join(subject_dir, d)
        if os.path.isdir(full) and not d.startswith('.'):
            sessions.append(full)
    return sessions
...
sessions = get_sessions(subject_dir)
```

**What this does:** Sessions are subdirectories of each subject directory, sorted alphabetically; hidden entries are skipped. Each session corresponds to one daily recording.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Each session split into 2-minute blocks (matching paper's CV structure). 20-min sessions: 10 trials x 360 time bins. 30-min sessions: 15 trials x 360 time bins." (CONVERSION_NOTES.md:151-153)

**Code** (convert_data.py:36, 182-203):
```python
TRIAL_DURATION_S = 120.0  # 2 minutes per trial (paper: "consecutive 2 minute blocks")
...
def split_into_trials(dff_binned, me_binned):
    bins_per_trial = int(TRIAL_DURATION_S * FS / BIN_SIZE)  # 360
    n_bins = dff_binned.shape[1]
    n_trials = n_bins // bins_per_trial
    neural_trials = []
    me_trials = []
    for t in range(n_trials):
        start = t * bins_per_trial
        end = start + bins_per_trial
        neural_trials.append(dff_binned[:, start:end].astype(np.float32))
        me_trials.append(me_binned[start:end])
    return neural_trials, me_trials
```

**What this does:** Trials are non-overlapping 2-minute (120s) blocks of the binned recording, equating to 360 time bins per trial. The number of trials per session is `n_bins // 360`; remainder bins are discarded.

**Rating:** better

**Note:** 2 min is listed in the methods, manual uses 1 min

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial curation: No explicit trial curation mentioned - continuous recording" (CONVERSION_NOTES.md:117)

**Code** (convert_data.py): (no relevant code found)

**What this does:** No trial-level quality filtering is applied. Trials are taken as consecutive 2-minute blocks; only the trailing partial-bin remainder is dropped via integer division.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "F.npy, Fneu.npy | neural | Neuropil subtract, baseline correct (dF/F), bin by 10 frames" (CONVERSION_NOTES.md:146)

**Code** (convert_data.py:160-161):
```python
F = np.load(os.path.join(s2p_dir, 'F.npy'))
Fneu = np.load(os.path.join(s2p_dir, 'Fneu.npy'))
```

**What this does:** Neural data is derived from suite2p `F.npy` (raw fluorescence) and `Fneu.npy` (neuropil fluorescence) in `suite2p/plane0`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neuropil subtraction: F_corr = F - 0.7 * Fneu; Baseline correction: maximin filter (win=60s, sig=10 frames); dF/F = (F_corr - baseline) / baseline" (CONVERSION_NOTES.md:108-110, 266)

**Code** (convert_data.py:54-88):
```python
def compute_dff(F, Fneu, device=None):
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # Neuropil subtraction
    F_corr = F - NEUCOEFF * Fneu
    F_corr_copy = F_corr.copy()
    F_subtracted = preprocess(
        F_corr_copy, BASELINE, WIN_BASELINE, SIG_BASELINE, FS,
        prctile_baseline=PRCTILE_BASELINE, device=device
    )
    baseline = F_corr - F_subtracted
    baseline_safe = np.clip(baseline, 1e-6, None)
    dff = F_subtracted / baseline_safe
    return dff.astype(np.float32)
```

**What this does:** Neuropil subtraction with coefficient 0.7, then suite2p `preprocess` (maximin baseline, win 60s, sigma 10, 8th percentile) computes baseline-subtracted fluorescence. dF/F is computed as `(F_corr - baseline) / baseline`, with the baseline clipped to 1e-6 to avoid division by zero. The continuous trace is then bin-averaged over 10 frames (see Q 2-d).

**Rating:** incorrect

**Note:** i think this double subtracts the baseline

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "All neurons are already filtered to cells tracked across ALL days for each mouse. iscell.npy has all values = 1.0 (all cells marked as cells since they're pre-filtered)" (CONVERSION_NOTES.md:38-39)

**Code** (convert_data.py): (no relevant code found — no additional filtering applied)

**What this does:** No additional cell-level filtering is performed. All neurons in `F.npy` are kept; the data is already pre-filtered by the upstream Track2p pipeline.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Temporal alignment: ME is already synced to neural (camera triggered by microscope)" (CONVERSION_NOTES.md:161)

**Code** (convert_data.py:447-449):
```python
'temporal_alignment_event': 'Start of recording session',
'off_start': 0.0,
'off_end': None,
```

**What this does:** Each trial is a contiguous 2-minute block beginning at the start of the recording session; alignment metadata is set to `'Start of recording session'` with `off_start=0.0`. There is no event-driven alignment.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Binning: Both dF/F and motion energy averaged in bins of 10 frames" (CONVERSION_NOTES.md:110); "Time bin size: 10 frames / 30 Hz = 333.33 ms" (CONVERSION_NOTES.md:154)

**Code** (convert_data.py:35, 123-143, 176):
```python
BIN_SIZE = 10        # number of frames per bin

def bin_traces(data, bin_size):
    if data.ndim == 1:
        n_frames = len(data)
        n_bins = n_frames // bin_size
        trimmed = data[:n_bins * bin_size]
        return trimmed.reshape(n_bins, bin_size).mean(axis=1)
    else:
        n_features, n_frames = data.shape
        n_bins = n_frames // bin_size
        trimmed = data[:, :n_bins * bin_size]
        return trimmed.reshape(n_features, n_bins, bin_size).mean(axis=2)
...
dff_binned = bin_traces(dff, BIN_SIZE)
```

**What this does:** dF/F (and motion energy) are averaged within non-overlapping 10-frame bins via reshape+mean, yielding a time bin size of 10/30 = 333.33 ms. Trailing frames that don't fill a full bin are trimmed.

**Rating:** ok

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time index | input[0] | Time in seconds from start of trial" (CONVERSION_NOTES.md:147)

**Code** (convert_data.py:228-236):
```python
def make_time_input(n_timebins):
    """
    Create time-elapsed input for a trial.
    Task: "Time elapsed from the beginning of the experiment. Time-varying."
    Time in seconds from start of trial.
    """
    time_bin_s = BIN_SIZE / FS  # seconds per bin
    return (np.arange(n_timebins) * time_bin_s).astype(np.float32).reshape(1, -1)
```

**What this does:** Time is not derived from any raw data variable; it is computed from the bin index multiplied by the bin duration (10/30 = 0.333 s).

**Rating:** concerning

**Note:** agent uses time from start of trial not start of experiment

---

## Q 3-b. What processing is involved in computing `input` *Time*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none specific beyond mapping table)

**Code** (convert_data.py:228-236):
```python
def make_time_input(n_timebins):
    time_bin_s = BIN_SIZE / FS  # seconds per bin
    return (np.arange(n_timebins) * time_bin_s).astype(np.float32).reshape(1, -1)
```

**What this does:** Time vector is `arange(n_timebins) * (10/30)` seconds, reshaped to (1, n_timebins) and cast to float32. Time resets to 0 at the start of each trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none specific)

**Code** (convert_data.py:397-402):
```python
for neural_t, me_t in zip(neural_trials, me_trials):
    n_timebins = neural_t.shape[1]
    # Input: time elapsed
    time_input = make_time_input(n_timebins)
    input_trials.append(time_input)
```

**What this does:** The input time vector length is set to match each trial's neural shape (`neural_t.shape[1]`), so it is aligned bin-for-bin with the neural array within each trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "motion_energy_glob.npy | output[0] | Interpolate missing frames, bin by 10, normalize, discretize into 5 equal-percentile bins" (CONVERSION_NOTES.md:148)

**Code** (convert_data.py:164-165):
```python
me = np.load(os.path.join(me_dir, 'motion_energy_glob.npy'))
tstamps = np.load(os.path.join(me_dir, 'tstamps.npy'))
```

**What this does:** Motion energy is loaded from `move_deve/motion_energy_glob.npy` per session. `tstamps.npy` is also loaded but only the length is used (for interpolation; see Q 4-c).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Compute percentile bins globally across all sessions" (CONVERSION_NOTES.md:158); "Output bins | - | - | 5 equal-percentile" (CONVERSION_NOTES.md:241)

**Code** (convert_data.py:177, 206-225, 369-371, 404-406):
```python
me_binned = bin_traces(me_interp, BIN_SIZE)
...
def compute_me_percentile_bins(all_me_values, n_bins=N_OUTPUT_BINS):
    percentiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(all_me_values, percentiles)
    return bin_edges

def discretize_me(me_values, bin_edges):
    n_bins = len(bin_edges) - 1
    labels = np.digitize(me_values, bin_edges[1:-1])
    labels = np.clip(labels, 0, n_bins - 1)
    return labels.astype(np.int64)
...
all_me_concat = np.concatenate(all_me_binned_values)
bin_edges = compute_me_percentile_bins(all_me_concat, N_OUTPUT_BINS)
...
me_disc = discretize_me(me_t, bin_edges)
```

**What this does:** Motion energy is bin-averaged over 10-frame bins (matching the neural binning), then concatenated across all sessions to compute 5 equal-percentile bin edges globally. Each per-trial motion-energy vector is then discretized into integer labels 0–4 via `np.digitize` against those global edges. No per-session normalization is applied.

**Rating:** incorrect

**Note:** does not normalize per session

---

## Q 4-d. How is `output` *Motion energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Camera sync: Video at 30Hz triggered by microscope acquisition -> 1:1 frame correspondence; Missing frames: Some sessions have fewer ME frames than neural frames" (CONVERSION_NOTES.md:111-113); "Missing ME frames: Interpolate to match neural frame count using timestamps" (CONVERSION_NOTES.md:159)

**Code** (convert_data.py:91-120, 173):
```python
def interpolate_motion_energy(me, n_neural_frames, tstamps):
    n_me = len(me)
    if n_me == n_neural_frames:
        return me.astype(np.float64)
    if n_me < n_neural_frames:
        neural_indices = np.arange(n_neural_frames)
        # Use linear interpolation to fill in missing frames
        me_indices = np.linspace(0, n_neural_frames - 1, n_me)
        me_interp = np.interp(neural_indices, me_indices, me.astype(np.float64))
        return me_interp
    else:
        return me[:n_neural_frames].astype(np.float64)
...
me_interp = interpolate_motion_energy(me, n_frames, tstamps)
```

**What this does:** When motion-energy has fewer samples than neural frames, the ME signal is linearly interpolated by mapping its existing samples uniformly across the full neural frame index (`np.linspace(0, n_neural-1, n_me)` then `np.interp`). When ME is longer it is truncated. Resulting ME has one sample per neural frame, then both are bin-averaged to align bin-for-bin within trials. Note: although `tstamps` is loaded and passed in, it is not actually used inside the interpolation routine.

**Rating:** incorrect

**Note:** incorrect interpolation when frames are dropped

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Missing ME frames: handled via interpolation (affects 7 sessions); Partial bins at end of sessions: discarded (consistent with integer division)" (CONVERSION_NOTES.md:274-275)

**Code** (convert_data.py:82-83, 101-117, 136-138, 192):
```python
# Avoid division by zero (clip baseline to small positive value)
baseline_safe = np.clip(baseline, 1e-6, None)
...
if n_me < n_neural_frames:
    me_indices = np.linspace(0, n_neural_frames - 1, n_me)
    me_interp = np.interp(neural_indices, me_indices, me.astype(np.float64))
...
n_bins = n_frames // bin_size
trimmed = data[:n_bins * bin_size]
...
n_trials = n_bins // bins_per_trial
```

**What this does:** Missing motion-energy frames are linearly interpolated to match neural length (or truncated if longer). Baseline values are floored at 1e-6 to avoid division by zero in dF/F. Trailing frames that don't fill a full bin (and bins that don't fill a full trial) are discarded via integer division. No explicit assertion verifies post-interpolation length equality.

**Rating:** incorrect

**Note:** doesn't detect missing video frames

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Processing time: ~1s per session" (CONVERSION_NOTES.md:179); "Sample: 2.5s for 2 sessions (~1.25s/session); Estimated full: ~50s for 41 sessions" (CONVERSION_NOTES.md:202-203)

**Code** (convert_data.py:73-78):
```python
F_subtracted = preprocess(
    F_corr_copy, BASELINE, WIN_BASELINE, SIG_BASELINE, FS,
    prctile_baseline=PRCTILE_BASELINE, device=device
)
```

**What this does:** The most expensive step per session is the suite2p `preprocess` baseline correction; it is run with GPU acceleration when CUDA is available. File I/O for `F.npy`/`Fneu.npy`/`motion_energy_glob.npy` is the next contributor.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Vectorized binning (reshape + mean)" (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:197-202, 397-407):
```python
for t in range(n_trials):
    start = t * bins_per_trial
    end = start + bins_per_trial
    neural_trials.append(dff_binned[:, start:end].astype(np.float32))
    me_trials.append(me_binned[start:end])
...
for neural_t, me_t in zip(neural_trials, me_trials):
    n_timebins = neural_t.shape[1]
    time_input = make_time_input(n_timebins)
    input_trials.append(time_input)
    me_disc = discretize_me(me_t, bin_edges)
    output_trials.append(me_disc.reshape(1, -1))
```

**What this does:** Trial-splitting and per-trial input/output construction use Python `for` loops over trials and sessions; these slicing and discretization steps could be done as a single reshape/array operation. Binning itself is already vectorized via reshape+mean.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none specific)

**Code** (convert_data.py:239-247, 354-356):
```python
def plot_processing(session_dir, dff_binned, me_binned, me_disc_trials,
                    neural_trials, n_frames_raw, save_path):
    ...
    F = np.load(os.path.join(s2p_dir, 'F.npy'))
    Fneu = np.load(os.path.join(s2p_dir, 'Fneu.npy'))
    me_raw = np.load(os.path.join(me_dir, 'motion_energy_glob.npy'))
...
dff_binned, me_binned, n_neurons, n_frames_raw = process_session(
    sess_dir, device=device
)
```

**What this does:** When `--show-processing` is enabled, `plot_processing` re-loads `F.npy`, `Fneu.npy`, and `motion_energy_glob.npy` from disk for plotting in addition to the loads already performed inside `process_session`. The two-pass design (process all sessions, then split into trials) keeps all binned session data in memory rather than recomputing.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none specific)

**Code** (convert_data.py:165, 173):
```python
tstamps = np.load(os.path.join(me_dir, 'tstamps.npy'))
...
me_interp = interpolate_motion_energy(me, n_frames, tstamps)
```

**What this does:** `tstamps.npy` is loaded and passed into `interpolate_motion_energy`, but the function body never uses the `tstamps` argument (interpolation is purely length-based). Beyond that, no other clearly unused processing is present; the `me_disc_trials` accumulation is only used when plotting is enabled.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — the notes report only timing, e.g. CONVERSION_NOTES.md:180 "Processing time: ~1s per session"; no memory, dtype, or streaming discussion)

**Code** (convert_data.py:68-88, with the dtype cast at :200):
```python
    # Neuropil subtraction
    F_corr = F - NEUCOEFF * Fneu

    F_corr_copy = F_corr.copy()
    F_subtracted = preprocess(
        F_corr_copy, BASELINE, WIN_BASELINE, SIG_BASELINE, FS,
        prctile_baseline=PRCTILE_BASELINE, device=device
    )
    # F_subtracted = F_corr - baseline => baseline = F_corr - F_subtracted
    baseline = F_corr - F_subtracted

    # Avoid division by zero (clip baseline to small positive value)
    baseline_safe = np.clip(baseline, 1e-6, None)

    # dF/F = (F_corr - baseline) / baseline = F_subtracted / baseline
    dff = F_subtracted / baseline_safe

    return dff.astype(np.float32)

# :200  neural_trials.append(dff_binned[:, start:end].astype(np.float32))
```

**What this does:** Sessions are loaded and processed one at a time (`process_session`, lines 146-179), and only 10-frame-binned results are accumulated into `session_data` (line 358); stored trials are cast to `float32` at line 200. Inside `compute_dff` five full `(n_neurons, n_frames)` intermediates are live at once (`F_corr`, `F_corr_copy`, `F_subtracted`, `baseline`, `baseline_safe`) with no in-place operations or `del`; the Suite2p `preprocess` call is optionally routed to CUDA (lines 65-66). No memory-mapping or chunked reads — `np.load` reads each array in full (lines 160-165) — and the motion-energy path works in `float64` (lines 102-120).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
