# majnik2025 — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/majnik2025/claude/2026-03-10__19-45-01_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Subjects | 6 (jm031, jm032, jm038, jm039, jm040, jm046) ... Sessions / subject | 7, 7, 7, 7, 6, 7 = 41 total" (CONVERSION_NOTES.md:50-52)

**Code** (convert_data.py:151-162, 261-276):
```python
def load_session(subject_dir, session_name):
    session_dir = os.path.join(subject_dir, session_name)
    s2p_dir = os.path.join(session_dir, 'suite2p', 'plane0')
    move_dir = os.path.join(session_dir, 'move_deve')
    F = np.load(os.path.join(s2p_dir, 'F.npy'))
    Fneu = np.load(os.path.join(s2p_dir, 'Fneu.npy'))
    me = np.load(os.path.join(move_dir, 'motion_energy_glob.npy'))
    interframe = np.load(os.path.join(move_dir, 'interframe_int.npy'))
    return F, Fneu, me, interframe

# Discover subjects and sessions
subjects = sorted([d for d in os.listdir(DATA_DIR)
                   if os.path.isdir(os.path.join(DATA_DIR, d))])
all_sessions = []
for subj in subjects:
    subj_dir = os.path.join(DATA_DIR, subj)
    sessions = sorted([d for d in os.listdir(subj_dir)
                      if os.path.isdir(os.path.join(subj_dir, d))])
    for sess in sessions:
        all_sessions.append((subj, sess))
```

**What this does:** Lists all directories in DATA_DIR as subjects (no `jm` filter), then lists all subdirectories within each subject as sessions. For each session, loads F, Fneu, motion energy, and interframe interval files from suite2p/plane0 and move_deve.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Subjects | 6 (jm031, jm032, jm038, jm039, jm040, jm046)" (CONVERSION_NOTES.md:50)

**Code** (convert_data.py:262-265, 292-293):
```python
subjects = sorted([d for d in os.listdir(DATA_DIR)
                   if os.path.isdir(os.path.join(DATA_DIR, d))])
print(f"Found {len(subjects)} subjects: {subjects}")
...
subject_list = list(dict.fromkeys([s[0] for s in all_sessions]))  # unique, ordered
```

**What this does:** Each top-level directory under DATA_DIR is treated as one subject (sorted alphabetically). The subject_list preserves first-seen order from the session list, and subject_idx is assigned per session via index lookup.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions / subject | 7, 7, 7, 7, 6, 7 = 41 total" (CONVERSION_NOTES.md:51)

**Code** (convert_data.py:268-276):
```python
all_sessions = []
for subj in subjects:
    subj_dir = os.path.join(DATA_DIR, subj)
    sessions = sorted([d for d in os.listdir(subj_dir)
                      if os.path.isdir(os.path.join(subj_dir, d))])
    for sess in sessions:
        all_sessions.append((subj, sess))
print(f"Total sessions: {len(all_sessions)}")
```

**What this does:** Each subdirectory under a subject folder is treated as a session, sorted alphabetically. All sessions are collected into a flat (subject, session) tuple list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trials: 2-minute blocks (360 bins each). 20-min → 10 trials, 30-min → 15 trials." (CONVERSION_NOTES.md:128); "splits were done on consecutive 2 minute blocks" (CONVERSION_NOTES.md:90)

**Code** (convert_data.py:187-209, 295):
```python
def split_into_trials(neural_binned, me_binned, trial_frames):
    n_bins = neural_binned.shape[1]
    n_trials = n_bins // trial_frames
    neural_trials = []
    me_trials = []
    for t in range(n_trials):
        start = t * trial_frames
        end = start + trial_frames
        neural_trials.append(neural_binned[:, start:end].astype(np.float32))
        me_trials.append(me_binned[start:end])
    return neural_trials, me_trials
...
trial_frames = int(TRIAL_DURATION_SEC * FS / BIN_SIZE)  # 120 * 30 / 10 = 360
```

**What this does:** Splits the binned continuous recording into non-overlapping 2-minute (120s) trial segments of 360 binned frames each. Remainder bins that don't fill a complete trial are dropped.

**Rating:** better

**Note:** 2 min is listed in the methods, manual uses 1 min

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trials: No explicit curation; missing video frames interpolated" (CONVERSION_NOTES.md:94)

**Code** (convert_data.py): (no relevant code found — no trial-level QC filtering applied)

**What this does:** No trial-level quality control is performed; all 2-minute segments are kept. Missing video frames are handled at the signal level (interpolation), not by discarding trials.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "F.npy, Fneu.npy | neural | dF/F (neuropil correction + maximin baseline), bin by 10" (CONVERSION_NOTES.md:122)

**Code** (convert_data.py:157-158):
```python
F = np.load(os.path.join(s2p_dir, 'F.npy'))
Fneu = np.load(os.path.join(s2p_dir, 'Fneu.npy'))
```

**What this does:** Neural data is derived from suite2p `F.npy` (raw fluorescence) and `Fneu.npy` (neuropil fluorescence) from the `plane0` directory.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Suite2p processing: Fc = F - 0.7*Fneu → maximin baseline → dF/F = Fc - F0" (CONVERSION_NOTES.md:82); "sig_baseline is used directly as Gaussian sigma in frames" (CONVERSION_NOTES.md:83)

**Code** (convert_data.py:39-85):
```python
def compute_dff(F, Fneu, fs=30.0, neucoeff=0.7, win_baseline=60.0, sig_baseline=10.0,
                prctile_baseline=8.0):
    Fc = F - neucoeff * Fneu
    win_frames = int(win_baseline * fs)  # window in frames
    F0 = _maximin_baseline(Fc, win_frames, sig_baseline)
    dff = Fc - F0
    return dff

def _maximin_baseline(Fc, win_frames, sig_frames):
    Flow = minimum_filter1d(Fc, size=win_frames, axis=1)
    Flow = maximum_filter1d(Flow, size=win_frames, axis=1)
    Flow = gaussian_filter1d(Flow, sigma=sig_frames, axis=1)
    return Flow
```

**What this does:** Applies neuropil subtraction with coefficient 0.7, then computes a "maximin" baseline (rolling min over 60s window, then rolling max, then Gaussian smoothing with sigma=10 frames). dF/F is computed as baseline-subtracted (not divided) fluorescence, mirroring suite2p `dcnv.preprocess`. Re-implemented manually (not via suite2p package).

**Rating:** ok

**Note:** reimplements suite2p preprocess manually

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "All iscell values are 1.0 in the provided data (pre-filtered by track2p)" (CONVERSION_NOTES.md:38); "Neurons: iscell > 0.5 + track2p matching (already applied in data)" (CONVERSION_NOTES.md:94)

**Code** (convert_data.py): (no relevant code found — no iscell filtering performed at conversion time)

**What this does:** No additional neuron-level filtering is applied during conversion; all neurons in F.npy are retained. The notes argue this is acceptable because the data is already pre-filtered by track2p.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "averaging in bins of 10 consecutive timestamps" (effective rate: 3 Hz) (CONVERSION_NOTES.md:89)

**Code** (convert_data.py:129-145, 175-181):
```python
def bin_data(data, bin_size):
    if data.ndim == 1:
        n = len(data)
        n_bins = n // bin_size
        return data[:n_bins * bin_size].reshape(n_bins, bin_size).mean(axis=1)
    else:
        n = data.shape[-1]
        n_bins = n // bin_size
        trimmed = data[..., :n_bins * bin_size]
        new_shape = trimmed.shape[:-1] + (n_bins, bin_size)
        return trimmed.reshape(new_shape).mean(axis=-1)
...
dff_binned = bin_data(dff, bin_size)  # (n_neurons, n_bins)
```

**What this does:** Bins dF/F by averaging consecutive groups of 10 frames, reducing the effective rate from 30 Hz to 3 Hz (333.3 ms bin size). Frames at the end that don't fill a bin are trimmed.

**Rating:** ok

**Note:** agent is closer to the paper which says it averages 10 timepoints

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — alignment is implicit from the 2-min block segmentation)

**Code** (convert_data.py:355-360):
```python
'metadata': {
    'task_description': 'Decode motion energy ...',
    'time_bin_size': BIN_SIZE / FS * 1000,  # in ms = 333.33
    'temporal_alignment_event': 'Start of 2-minute recording block',
    'off_start': 0.0,
    'off_end': TRIAL_DURATION_SEC,
```

**What this does:** Each trial is aligned to the start of its 2-minute block (no external stimulus event). Metadata records this with `temporal_alignment_event = 'Start of 2-minute recording block'`, off_start=0, off_end=120s.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time from start | input[0] | Elapsed time in seconds from start of 2-min trial | [0, 119.7s]" (CONVERSION_NOTES.md:123)

**Code** (convert_data.py:326-334):
```python
input_all = []
for session_trials in neural_all:
    session_inputs = []
    for trial in session_trials:
        n_timepoints = trial.shape[1]
        time_input = np.arange(n_timepoints) * (BIN_SIZE / FS)
        session_inputs.append(time_input.reshape(1, -1).astype(np.float32))
    input_all.append(session_inputs)
```

**What this does:** Time is not derived from a raw variable but constructed from the bin index multiplied by the bin duration (10/30 = 0.333 s).

**Rating:** concerning

**Note:** agent uses time from start of trial not start of experiment

---

## Q 3-b. What processing is involved in computing `input` *Time*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:331-333):
```python
n_timepoints = trial.shape[1]
time_input = np.arange(n_timepoints) * (BIN_SIZE / FS)
session_inputs.append(time_input.reshape(1, -1).astype(np.float32))
```

**What this does:** Computes elapsed time per binned timepoint as `arange(n_bins) * (BIN_SIZE / FS)`, yielding values from 0 to ~119.67s for each trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:329-333):
```python
for trial in session_trials:
    n_timepoints = trial.shape[1]
    time_input = np.arange(n_timepoints) * (BIN_SIZE / FS)
    session_inputs.append(time_input.reshape(1, -1).astype(np.float32))
```

**What this does:** The input array length is taken directly from the per-trial neural array's last dim, ensuring index-by-index alignment with the binned neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "motion_energy_glob.npy | output[0] | Interpolate missing frames, bin by 10, global quintile discretization | 5 bins" (CONVERSION_NOTES.md:124)

**Code** (convert_data.py:159-160):
```python
me = np.load(os.path.join(move_dir, 'motion_energy_glob.npy'))
interframe = np.load(os.path.join(move_dir, 'interframe_int.npy'))
```

**What this does:** Motion energy is loaded from `move_deve/motion_energy_glob.npy`, and `interframe_int.npy` is used to detect dropped video frames.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Discretization: Global quintile bins across all sessions." (CONVERSION_NOTES.md:131)

**Code** (convert_data.py:215-250):
```python
def discretize_motion_energy(all_me_trials, n_bins=N_OUTPUT_BINS):
    all_values = np.concatenate([me for session_trials in all_me_trials for me in session_trials])
    percentiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(all_values, percentiles)
    for i in range(1, len(bin_edges)):
        if bin_edges[i] <= bin_edges[i-1]:
            bin_edges[i] = bin_edges[i-1] + 1e-10
    discretized = []
    for session_trials in all_me_trials:
        session_disc = []
        for me in session_trials:
            binned = np.digitize(me, bin_edges[1:-1])
            binned = np.clip(binned, 0, n_bins - 1)
            session_disc.append(binned.reshape(1, -1).astype(np.int64))
        discretized.append(session_disc)
    bin_labels = [f'{percentiles[i]:.0f}-{percentiles[i+1]:.0f}%ile' for i in range(n_bins)]
    return discretized, bin_edges, bin_labels
```

**What this does:** (1) Missing video frames are interpolated to match neural length (see 4-c); (2) ME is averaged into 10-frame bins (no normalization step); (3) all binned values across all sessions and trials are pooled and split into 5 equal-percentile (quintile) bins via `np.digitize`.

**Rating:** incorrect

**Note:** does not normalize per session, interpolation problematic with dropped frames

---

## Q 4-c. How is `output` *Motion energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Missing frames: Interpolate ME to match neural frame count using interframe intervals." (CONVERSION_NOTES.md:130)

**Code** (convert_data.py:91-123):
```python
def interpolate_missing_frames(motion_energy, interframe_int, n_neural_frames):
    n_me = len(motion_energy)
    if n_me == n_neural_frames:
        return motion_energy.astype(np.float64)
    n_missing = n_neural_frames - n_me
    if n_missing < 0:
        return motion_energy[:n_neural_frames].astype(np.float64)
    median_ifi = np.median(interframe_int)
    ratios = interframe_int / median_ifi
    missed_counts = np.round(ratios).astype(int) - 1
    me_positions = np.zeros(n_me, dtype=int)
    me_positions[0] = 0
    for i in range(1, n_me):
        me_positions[i] = me_positions[i-1] + 1 + missed_counts[i-1]
    neural_positions = np.arange(n_neural_frames)
    me_interp = np.interp(neural_positions, me_positions, motion_energy.astype(np.float64))
    return me_interp
```

**What this does:** Uses interframe intervals normalized by the median to count how many frames were dropped at each point, builds a mapping from ME indices to neural frame positions, then linearly interpolates ME onto the full neural-frame timeline so neural and ME align frame-for-frame at 30 Hz before binning.

**Rating:** match

**Note:** _(no note)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Edge cases: Missing video frames handled via interframe interval detection and interpolation. End-of-session partial bins discarded (correct behavior)." (CONVERSION_NOTES.md:236)

**Code** (convert_data.py:98-105, 138, 198):
```python
n_me = len(motion_energy)
if n_me == n_neural_frames:
    return motion_energy.astype(np.float64)
n_missing = n_neural_frames - n_me
if n_missing < 0:
    return motion_energy[:n_neural_frames].astype(np.float64)
...
return data[:n_bins * bin_size].reshape(n_bins, bin_size).mean(axis=1)
...
n_trials = n_bins // trial_frames
```

**What this does:** Missing video frames are detected and interpolated; if more ME frames than neural exist, they are truncated. Partial bins at the end of a session and partial trials are silently discarded via integer division. No assertions or warnings are raised.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "dF/F + binning | ~1.5s | ~60s for 41 sessions" (CONVERSION_NOTES.md:174); "Total conversion time: 60.5s" (conversion_full_out.txt)

**Code** (convert_data.py:298-313):
```python
for i, (subj, sess) in enumerate(all_sessions):
    t0 = time.time()
    print(f"Processing session {i+1}/{len(all_sessions)}: {subj}/{sess}...", end=" ")
    subj_dir = os.path.join(DATA_DIR, subj)
    F, Fneu, me, interframe = load_session(subj_dir, sess)
    dff_binned, me_binned = process_session(F, Fneu, me, interframe)
    neural_trials, me_trials = split_into_trials(dff_binned, me_binned, trial_frames)
    ...
    dt = time.time() - t0
    print(f"{len(neural_trials)} trials, {F.shape[0]} neurons, {dt:.1f}s")
```

**What this does:** Per-session loop times each session (~1.5s/session, ~60s total). The dominant operations are dF/F maximin baseline (rolling min/max + Gaussian filter) on full-length F arrays, plus npy I/O.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:115-117, 232-234, 237-245):
```python
me_positions = np.zeros(n_me, dtype=int)
me_positions[0] = 0
for i in range(1, n_me):
    me_positions[i] = me_positions[i-1] + 1 + missed_counts[i-1]
...
for i in range(1, len(bin_edges)):
    if bin_edges[i] <= bin_edges[i-1]:
        bin_edges[i] = bin_edges[i-1] + 1e-10
...
for session_trials in all_me_trials:
    session_disc = []
    for me in session_trials:
        binned = np.digitize(me, bin_edges[1:-1])
```

**What this does:** Several Python-level loops exist: cumulative me_positions (could use cumsum), bin_edges monotonization, and per-trial discretization. All operate on small arrays so impact is minor.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py): (no relevant code found — no obvious repeated computation across passes)

**What this does:** Each session is loaded and processed once; ME is collected then discretized in a single global pass. No obvious redundant repetition.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:401-464):
```python
def _plot_processing(subj, sess, F, Fneu, me, interframe,
                     dff_binned, me_binned, neural_trials, me_trials,
                     trial_frames):
    """Plot processing steps for visual inspection."""
    fig, axes = plt.subplots(5, 1, figsize=(16, 20))
    ...
```

**What this does:** A `_plot_processing` helper builds large diagnostic plots when `--show-processing` is set; not used by the conversion output. Otherwise, computed quantities (F0, raw me_binned values pre-discretization) are not stored.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — the notes discuss runtime only, e.g. CONVERSION_NOTES.md:148 "Fix also dramatically improved runtime: 1420s → 60s"; no mention of memory, dtype choice, or streaming)

**Code** (convert_data.py:298-313, with the dtype cast at :206):
```python
    for i, (subj, sess) in enumerate(all_sessions):
        t0 = time.time()
        print(f"Processing session {i+1}/{len(all_sessions)}: {subj}/{sess}...", end=" ")

        subj_dir = os.path.join(DATA_DIR, subj)
        F, Fneu, me, interframe = load_session(subj_dir, sess)

        dff_binned, me_binned = process_session(F, Fneu, me, interframe)
        neural_trials, me_trials = split_into_trials(dff_binned, me_binned, trial_frames)

        neural_all.append(neural_trials)
        me_all_raw.append(me_trials)
        subject_idx.append(subject_list.index(subj))

# :206  neural_trials.append(neural_binned[:, start:end].astype(np.float32))
```

**What this does:** Sessions are loaded and processed one at a time inside the main loop, so full-resolution `F`/`Fneu`/dF/F arrays for the current session are rebound (and released) on the next iteration; only the 10-frame-binned trials are accumulated, cast to `float32` at line 206. There is no memory-mapping, no explicit `del` or `gc` call, and no chunked/streaming read — `np.load` reads each array fully into RAM (lines 157-160), and the motion-energy path upcasts to `float64` (lines 100-121). The `_maximin_baseline` helper allocates several full `(n_neurons, n_frames)` intermediates (`Fc`, `Flow` ×3, `dff`) simultaneously.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
