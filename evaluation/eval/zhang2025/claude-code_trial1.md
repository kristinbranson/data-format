# zhang2025 — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/zhang2025/claude-code/2026-03-24__09-05-04_trial1/verifier/snapshot/`

Outputs identified (K=4): choice, prior_probability_left, wheel_speed, whisker_motion_energy

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Direct file loading (no ONE API needed, works offline from cache)" (CONVERSION_NOTES.md:220); "Use BWM release CSV (459 sessions) as ground truth" (CONVERSION_NOTES.md:203)

**Code** (convert_data.py:665-687):
```python
bwm_df = pd.read_csv(BWM_CSV, index_col=0)
sessions = get_session_list(bwm_df)
print(f"Total sessions in BWM release: {len(sessions)}")
...
# Initialize brain atlas
br = BrainRegions()

# Process sessions
all_results = []
for idx in range(len(sessions)):
    sess = sessions.iloc[idx]
    print(f"\nProcessing session {idx+1}/{len(sessions)}: {sess['subject']}/{sess['date']}")
    result = process_session(sess, br, show_processing=args.show_processing)
    if result is not None:
        all_results.append(result)
```

**What this does:** Reads the BWM release CSV to enumerate sessions, then iterates serially over each session calling `process_session` which loads trials, spikes, wheel, motion energy from local ONE cache files.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Subjects: 141 (in data dir)" (CONVERSION_NOTES.md:84); subject names collected per result (no per-subject loading).

**Code** (convert_data.py:706-729):
```python
# Collect all unique subjects
all_subjects = sorted(set(r['subject'] for r in all_results))
subject_to_idx = {s: i for i, s in enumerate(all_subjects)}
...
for r in all_results:
    neural_list.append(r['neural'])
    input_list.append(r['input'])
    output_list.append(r['output'])
    subject_idx.append(subject_to_idx[r['subject']])
    brain_region_idx.append(np.array([region_to_idx[reg] for reg in r['cluster_regions']]))
```

**What this does:** Subjects are derived per session from the BWM CSV `subject` column; after processing, unique subject names are collected and a `subject_idx` array is stored mapping each session to its subject index.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Group by eid to get one row per session" (convert_data.py:644); "Use BWM release CSV (459 sessions) as ground truth" (CONVERSION_NOTES.md:203)

**Code** (convert_data.py:641-645, 49-54):
```python
def get_session_list(bwm_df):
    """Get unique sessions from BWM release CSV."""
    # Group by eid to get one row per session
    sessions = bwm_df.groupby('eid').first().reset_index()
    return sessions

def find_session_path(lab, subject, date, number=1):
    sess_path = DATA_DIR / lab / 'Subjects' / subject / date / f'{number:03d}' / 'alf'
```

**What this does:** Sessions are uniquely identified by `eid` from the BWM CSV; each session is located on disk via the (lab, subject, date, number) tuple to its `alf/` directory.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial events (stimOn, choice, feedback, etc.)" loaded from `_ibl_trials.table.pqt` (CONVERSION_NOTES.md:61); intervals computed per-trial from stimOn_times.

**Code** (convert_data.py:85-91, 426-436):
```python
def load_trials(alf_path):
    """Load trials table from session."""
    trials_file = find_latest_revision(alf_path, '_ibl_trials.table.pqt')
    if trials_file is None:
        raise FileNotFoundError(f"No trials table found in {alf_path}")
    trials = pd.read_parquet(trials_file)
    return trials
...
align_times = valid_trials[ALIGN_TIME].values
interval_starts = align_times + TIME_WINDOW[0]
interval_ends = align_times + TIME_WINDOW[1]
```

**What this does:** Each row in the IBL trials parquet table is treated as one trial; per-trial intervals are constructed by adding `TIME_WINDOW=(-0.5, 1.5)` to each trial's `stimOn_times`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial mask: exclude if RT < 0.08s or > 2.0s, NaN in key events, no choice, max trial len 10s" (CONVERSION_NOTES.md:51)

**Code** (convert_data.py:94-115):
```python
def create_trial_mask(trials):
    mask = pd.Series(True, index=trials.index)
    for event in NAN_EXCLUDE:
        if event in trials.columns:
            mask &= ~trials[event].isna()
    rt = trials['firstMovement_times'] - trials['stimOn_times']
    mask &= (rt >= MIN_RT) & (rt <= MAX_RT)
    mask &= (trials['choice'] != 0)
    if 'goCue_times' in trials.columns:
        trial_len = trials['feedback_times'] - trials['goCue_times']
        mask &= (trial_len <= MAX_TRIAL_LEN) | trial_len.isna()
    return mask
```

**What this does:** Builds a boolean mask excluding trials with NaN in key events (stimOn, choice, feedback, probabilityLeft, firstMovement, feedbackType), reaction times outside [0.08, 2.0]s, no-choice trials, and trial length > 10s. A second pass also removes trials missing wheel/ME data (lines 464-486).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "spikes.times + spikes.clusters → neural" (CONVERSION_NOTES.md:181); spike sorting from probe<XX>/pykilosort (CONVERSION_NOTES.md:68-76).

**Code** (convert_data.py:118-155):
```python
def load_spike_sorting(alf_path, probe_name):
    probe_path = alf_path / probe_name / 'pykilosort'
    spike_times_file = find_latest_revision(probe_path, 'spikes.times.npy')
    ...
    spikes = {
        'times': np.load(rev_dir / 'spikes.times.npy').flatten(),
        'clusters': np.load(rev_dir / 'spikes.clusters.npy').flatten(),
    }
    clusters_channels = np.load(rev_dir / 'clusters.channels.npy').flatten()
    clusters_depths = np.load(rev_dir / 'clusters.depths.npy').flatten()
    ...
    chan_brain_ids = np.load(rev_dir / 'channels.brainLocationIds_ccf_2017.npy').flatten()
```

**What this does:** Neural data is derived from `spikes.times.npy` and `spikes.clusters.npy` (per probe, pykilosort), with `clusters.channels.npy` and `channels.brainLocationIds_ccf_2017.npy` providing brain region assignments.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Bin into 20ms windows aligned to stimOn, shape (n_neurons, 100)" (CONVERSION_NOTES.md:181); probes merged across session (CONVERSION_NOTES.md:50).

**Code** (convert_data.py:226-257):
```python
def bin_spikes_vectorized(spike_times, spike_clusters, n_clusters, interval_starts, interval_ends, binsize, n_bins):
    n_trials = len(interval_starts)
    binned = np.zeros((n_trials, n_clusters, n_bins), dtype=np.float32)
    for trial_idx in range(n_trials):
        t_start = interval_starts[trial_idx]
        t_end = interval_ends[trial_idx]
        ...
        idx_beg = np.searchsorted(spike_times, t_start, side='left')
        idx_end = np.searchsorted(spike_times, t_end, side='left')
        ...
        bin_idx = np.minimum(((t_sel - t_start) / binsize).astype(np.int32), n_bins - 1)
        valid = (c_sel >= 0) & (c_sel < n_clusters)
        flat_idx = c_sel[valid] * n_bins + bin_idx[valid]
        np.add.at(binned[trial_idx].ravel(), flat_idx, 1)
    return binned
```

**What this does:** Spike times/clusters from all probes are merged with global cluster IDs (lines 158-212), then per trial spikes within `[stimOn-0.5, stimOn+1.5]` are binned into 100 × 20 ms bins via `searchsorted` and `np.add.at`. Stored as uint8 (line 491-492).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "qc=None: ALL clusters used (not filtered by quality label)" (CONVERSION_NOTES.md:50); "Reference code uses qc=None: ALL clusters, not just good ones" (CONVERSION_NOTES.md:133).

**Code** (convert_data.py:138-143):
```python
# Load cluster metrics
metrics_file = rev_dir / 'clusters.metrics.pqt'
if metrics_file.exists():
    metrics = pd.read_parquet(metrics_file)
else:
    metrics = None
```

**What this does:** No quality filtering of clusters is applied; metrics are loaded but not used to drop neurons. All clusters from all probes are kept (per task spec/reference code).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "BINSIZE = 0.02  # 20 ms time bins ... N_BINS = int(np.ceil(...)) # 100" (convert_data.py:30-33); "Time bins: 100 (20ms each)" (README.md).

**Code** (convert_data.py:30-33, 248-255):
```python
BINSIZE = 0.02  # 20 ms time bins
ALIGN_TIME = 'stimOn_times'
TIME_WINDOW = (-0.5, 1.5)  # 2s window around stimOn
N_BINS = int(np.ceil((TIME_WINDOW[1] - TIME_WINDOW[0]) / BINSIZE))  # 100
...
bin_idx = np.minimum(((t_sel - t_start) / binsize).astype(np.int32), n_bins - 1)
valid = (c_sel >= 0) & (c_sel < n_clusters)
flat_idx = c_sel[valid] * n_bins + bin_idx[valid]
np.add.at(binned[trial_idx].ravel(), flat_idx, 1)
```

**What this does:** Spikes are binned by integer division of `(t - t_start)/0.02` into 100 fixed-width 20 ms bins per trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Align everything to stimOn_times: Task spec overrides reference code's firstMovement alignment" (CONVERSION_NOTES.md:198); metadata `temporal_alignment_event: 'stimulus onset (stimOn_times)'`.

**Code** (convert_data.py:427-436):
```python
align_times = valid_trials[ALIGN_TIME].values
interval_starts = align_times + TIME_WINDOW[0]
interval_ends = align_times + TIME_WINDOW[1]

# Bin spikes
binned_spikes = bin_spikes_vectorized(
    spikes['times'], spikes['clusters'], n_clusters,
    interval_starts, interval_ends, BINSIZE, N_BINS
)
```

**What this does:** For each trial, the binning interval is `[stimOn_times - 0.5, stimOn_times + 1.5]`, so bins are aligned to stimulus onset.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "trials.choice → output[0]: left(-1)→0, right(1)→1, binary per-trial" (CONVERSION_NOTES.md:184).

**Code** (convert_data.py:514-517):
```python
# Output 0: choice (binary, per-trial) - left=0, right=1
choice = final_trials['choice'].values.copy()
# IBL: -1=left, 1=right -> convert to 0=left, 1=right
choice_encoded = ((choice + 1) // 2).astype(int)  # -1->0, 1->1
```

**What this does:** Choice is taken from the `choice` column of the IBL trials table.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "left=0, right=1 (reference code: left=-1, right=1)" (CONVERSION_NOTES.md:171).

**Code** (convert_data.py:514-517, 537-545):
```python
choice = final_trials['choice'].values.copy()
choice_encoded = ((choice + 1) // 2).astype(int)  # -1->0, 1->1
...
out = np.array([
    np.full(N_BINS, choice_encoded[t], dtype=int),  # per-trial, broadcast
    ...
], dtype=int)
```

**What this does:** Re-encodes IBL choice {-1, +1} into {0, 1} and broadcasts the per-trial scalar across all 100 time bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `output` *choice* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Trial-level scalar broadcast across the same 100 stimOn-aligned bins as `neural`.

**Code** (convert_data.py:537-545):
```python
output_trials = []
for t in range(len(final_trials)):
    out = np.array([
        np.full(N_BINS, choice_encoded[t], dtype=int),  # per-trial, broadcast
        np.full(N_BINS, prior_encoded[t], dtype=int),
        wheel_disc_2d[t],
        me_disc_2d[t],
    ], dtype=int)
    output_trials.append(out)
```

**What this does:** Choice is constant per trial; same trial mask as neural is applied (line 486 `final_trials = valid_trials[combined_mask]`), so trial indices match neural.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `output` *prior_probability_left* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "trials.probabilityLeft → output[1]: 0.2→0, 0.5→1, 0.8→2" (CONVERSION_NOTES.md:185).

**Code** (convert_data.py:519-524):
```python
# Output 1: prior probability of left (per-trial, categorical)
prob_left = final_trials['probabilityLeft'].values
prior_encoded = np.zeros(len(prob_left), dtype=int)
prior_encoded[prob_left == 0.2] = 0
prior_encoded[prob_left == 0.5] = 1
prior_encoded[prob_left == 0.8] = 2
```

**What this does:** Derived from the `probabilityLeft` column of the trials table.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `output` *prior_probability_left*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Prior encoded as categorical (3 classes from probabilityLeft)" (CONVERSION_NOTES.md:169).

**Code** (convert_data.py:519-524):
```python
prob_left = final_trials['probabilityLeft'].values
prior_encoded = np.zeros(len(prob_left), dtype=int)
prior_encoded[prob_left == 0.2] = 0
prior_encoded[prob_left == 0.5] = 1
prior_encoded[prob_left == 0.8] = 2
```

**What this does:** Maps the three discrete block probabilities {0.2, 0.5, 0.8} to integer classes {0, 1, 2} per trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-c. How is `output` *prior_probability_left* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Per-trial scalar broadcast over the 100 stimOn-aligned bins.

**Code** (convert_data.py:540-541):
```python
np.full(N_BINS, prior_encoded[t], dtype=int),  # per-trial, broadcast
```

**What this does:** Constant value per trial replicated across 100 bins; same trial mask as neural keeps trials in correspondence.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `output` *wheel_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "wheel velocity → output[2]: abs(velocity) → discretize into 3 equal-frequency bins" (CONVERSION_NOTES.md:186); raw files `_ibl_wheel.position.npy`, `_ibl_wheel.timestamps.npy`.

**Code** (convert_data.py:441-444):
```python
wheel_pos_raw = np.load(find_latest_revision(alf_path, '_ibl_wheel.position.npy')).flatten()
wheel_ts_raw = np.load(find_latest_revision(alf_path, '_ibl_wheel.timestamps.npy')).flatten()
wheel_times, wheel_speed = interpolate_wheel(wheel_ts_raw, wheel_pos_raw)
```

**What this does:** Derived from raw wheel position and timestamps from the IBL ALF directory.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `output` *wheel_speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Wheel velocity: 1kHz interpolation, Butterworth low-pass (20Hz, order 8), absolute value for speed" (README.md:42); "discretize into 3 equal-frequency bins" (CONVERSION_NOTES.md:186).

**Code** (convert_data.py:260-272, 526-530):
```python
def interpolate_wheel(timestamps, position, fs=WHEEL_FS, corner_freq=WHEEL_CORNER_FREQ, order=WHEEL_FILTER_ORDER):
    t = np.arange(timestamps[0], timestamps[-1], 1.0 / fs)
    ...
    pos_interp = interp1d(timestamps, position, kind='linear')(t)
    sos = signal.butter(N=order, Wn=corner_freq / fs * 2, btype='lowpass', output='sos')
    vel = np.insert(np.diff(signal.sosfiltfilt(sos, pos_interp)), 0, 0) * fs
    return t, np.abs(vel).astype(np.float32)
...
all_wheel_flat = final_wheel.flatten()
wheel_disc, wheel_boundaries = discretize_to_bins(all_wheel_flat, N_DISCRETE_BINS)
wheel_disc_2d = wheel_disc.reshape(final_wheel.shape).astype(int)
```

**What this does:** Wheel position is linearly interpolated to 1 kHz, low-pass Butterworth filtered (20 Hz, order 8), differentiated and absolute-valued to give speed; then per-trial-binned via `interpolate_behavior_to_bins` (lines 295-333) and discretized into 3 quantile bins computed across the session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-c. How is `output` *wheel_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Same `interval_starts/interval_ends` (stimOn ± window) used as for neural; same `combined_mask` ensures matching trials.

**Code** (convert_data.py:444-447, 464-486):
```python
wheel_speed_binned, wheel_good = interpolate_behavior_to_bins(
    wheel_times, wheel_speed, interval_starts, interval_ends, BINSIZE, N_BINS
)
...
combined_mask = np.ones(len(valid_trials), dtype=bool)
if wheel_speed_binned is not None:
    combined_mask &= ~np.any(np.isnan(wheel_speed_binned), axis=1)
...
final_wheel = wheel_speed_binned[combined_mask]
```

**What this does:** Wheel speed is interpolated onto the same 100-bin trial intervals (stimOn-aligned) as the neural data, and trials missing wheel data are dropped from both `neural` and outputs via the shared `combined_mask`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "whisker motion energy → output[3]" (CONVERSION_NOTES.md:187); raw `leftCamera.ROIMotionEnergy.npy` + `_ibl_leftCamera.times.npy` (fallback right).

**Code** (convert_data.py:275-292):
```python
def load_motion_energy(alf_path, side='left'):
    if side == 'left':
        me_file = find_latest_revision(alf_path, 'leftCamera.ROIMotionEnergy.npy')
        times_file = find_latest_revision(alf_path, '_ibl_leftCamera.times.npy')
    else:
        me_file = find_latest_revision(alf_path, 'rightCamera.ROIMotionEnergy.npy')
        times_file = find_latest_revision(alf_path, '_ibl_rightCamera.times.npy')
    ...
    me = np.load(me_file).flatten()
    times = np.load(times_file).flatten()
    min_len = min(len(me), len(times))
    return times[:min_len], me[:min_len].astype(np.float32)
```

**What this does:** Derived from the precomputed left-camera ROI motion-energy npy (with timestamps), falling back to right camera if left missing.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `output` *whisker_motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Discretize into 3 equal-frequency bins, time-varying" (CONVERSION_NOTES.md:187).

**Code** (convert_data.py:452-460, 532-535):
```python
me_times, me_values = load_motion_energy(alf_path, side='left')
if me_times is None:
    me_times, me_values = load_motion_energy(alf_path, side='right')
if me_times is not None:
    me_binned, me_good = interpolate_behavior_to_bins(
        me_times, me_values, interval_starts, interval_ends, BINSIZE, N_BINS
    )
...
all_me_flat = final_me.flatten()
me_disc, me_boundaries = discretize_to_bins(all_me_flat, N_DISCRETE_BINS)
me_disc_2d = me_disc.reshape(final_me.shape).astype(int)
```

**What this does:** ROI motion energy is linearly interpolated onto trial-aligned 20 ms bins, then discretized via session-wise quantiles into 3 equal-frequency bins {low, medium, high}.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-c. How is `output` *whisker_motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Same `interval_starts/interval_ends` and `combined_mask` as neural.

**Code** (convert_data.py:472-486):
```python
if me_binned is not None:
    combined_mask &= ~np.any(np.isnan(me_binned), axis=1)
else:
    combined_mask[:] = False
...
final_me = me_binned[combined_mask]
```

**What this does:** Motion energy is binned to the same stimOn-aligned 100-bin intervals as neural; trials with any NaN bin are excluded from neural and all outputs via the shared mask.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "67 sessions skipped: missing data paths, missing wheel, or <2 valid trials" (CONVERSION_NOTES.md:325); "Handle length mismatch (common in IBL data)" (convert_data.py:290).

**Code** (convert_data.py:376-412, 464-481):
```python
alf_path = find_session_path(lab, subject, date)
if alf_path is None:
    print(f"  Session {eid} ({subject}/{date}): path not found, skipping")
    return None
try:
    trials = load_trials(alf_path)
except Exception as e:
    print(f"  Session {eid}: error loading trials: {e}")
    return None
...
combined_mask = np.ones(len(valid_trials), dtype=bool)
if wheel_speed_binned is not None:
    combined_mask &= ~np.any(np.isnan(wheel_speed_binned), axis=1)
else:
    combined_mask[:] = False
...
n_valid = combined_mask.sum()
if n_valid < 2:
    print(f"  Session {eid}: fewer than 2 trials with all data, skipping")
    return None
```

**What this does:** Sessions/probes with missing files or load errors are caught with try/except and skipped; trials with NaN/missing wheel or ME bins are dropped via `combined_mask`; sessions with <2 valid trials are skipped entirely.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Total: 1741s (29 min) for 459 sessions" (CONVERSION_NOTES.md:286); "~20s/session" (CONVERSION_NOTES.md:255).

**Code** (convert_data.py:226-257, 295-333):
```python
def bin_spikes_vectorized(spike_times, spike_clusters, n_clusters, interval_starts, interval_ends, binsize, n_bins):
    ...
    for trial_idx in range(n_trials):
        ...
        np.add.at(binned[trial_idx].ravel(), flat_idx, 1)
...
def interpolate_behavior_to_bins(beh_times, beh_values, interval_starts, interval_ends, binsize, n_bins):
    for trial_idx in range(n_trials):
        ...
        y_interp = interp1d(t_sel, v_sel, kind='linear', fill_value='extrapolate')(x_interp)
```

**What this does:** Per-trial Python loops for spike binning (`np.add.at`) and behavior interpolation (`interp1d` per trial), plus loading large npy/parquet files per session, dominate session time (~20 s each).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:301-331, 354-364, 491-492, 505-545):
```python
for trial_idx in range(n_trials):
    ...
    y_interp = interp1d(t_sel, v_sel, kind='linear', fill_value='extrapolate')(x_interp)
...
def compute_trial_in_block(prob_left):
    for i in range(len(prob_left)):
        if i > 0 and prob_left[i] != prob_left[i-1]:
            count = 1
        trial_in_block[i] = count
        count += 1
...
for t in range(len(final_spikes)):
    neural_trials.append(final_spikes[t].astype(np.uint8))
...
for t in range(len(final_trials)):
    inp = np.array([...])
    input_trials.append(inp)
for t in range(len(final_trials)):
    out = np.array([...])
    output_trials.append(out)
```

**What this does:** Per-trial loops that build neural/input/output lists, the per-trial `interp1d` call in `interpolate_behavior_to_bins`, the bin_spikes per-trial loop, and `compute_trial_in_block` could all be vectorized (e.g., via 2D interp1d, `np.diff`+`cumsum`, or stacked array assembly).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:57-82, 442-456):
```python
def find_latest_revision(base_path, filename_pattern):
    candidates = []
    if base_path.exists():
        for item in base_path.iterdir():
            ...
    candidates.sort(key=sort_key, reverse=True)
    return candidates[0]
...
wheel_pos_raw = np.load(find_latest_revision(alf_path, '_ibl_wheel.position.npy')).flatten()
wheel_ts_raw = np.load(find_latest_revision(alf_path, '_ibl_wheel.timestamps.npy')).flatten()
...
me_file = find_latest_revision(alf_path, 'leftCamera.ROIMotionEnergy.npy')
times_file = find_latest_revision(alf_path, '_ibl_leftCamera.times.npy')
```

**What this does:** `find_latest_revision` re-iterates the alf directory tree on every file lookup (multiple times per session). `searchsorted` over the same sorted spike-times array is repeated per trial. Brain-region acronym mapping `id2acronym` is recomputed for all channels even though only `clusters['channels']` indices are used.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:138-152, 215-223, 276-292):
```python
metrics_file = rev_dir / 'clusters.metrics.pqt'
if metrics_file.exists():
    metrics = pd.read_parquet(metrics_file)
...
clusters = {
    'channels': clusters_channels,
    'depths': clusters_depths,
    'metrics': metrics,
    'chan_brain_ids': chan_brain_ids,
}
...
def get_brain_regions(clusters, br):
    chan_ids = clusters['chan_brain_ids']
    chan_acronyms = br.id2acronym(chan_ids)
    chan_beryl = br.acronym2acronym(chan_acronyms, mapping='Beryl')
```

**What this does:** Cluster `metrics` parquet and `depths` are loaded and stored in the merged dict but never written to the final pickle. Brain-region acronyms are computed for every channel even though only the cluster-assigned channels are used in `cluster_regions`. `wheel_good`/`me_good` masks returned by `interpolate_behavior_to_bins` are computed but ignored (the NaN-any check is used instead).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "neural stored as uint8 to fit in 64GB container memory" (CONVERSION_NOTES.md:283); "Use uint8 to save memory (spike counts per 20ms bin are small integers, max ~12)" (convert_data.py:489).

**Code** (convert_data.py:488-492):
```python
# Build neural data: list of (n_neurons, n_timepoints) per trial
# Use uint8 to save memory (spike counts per 20ms bin are small integers, max ~12)
neural_trials = []
for t in range(len(final_spikes)):
    neural_trials.append(final_spikes[t].astype(np.uint8))  # (n_clusters, n_bins)
```

**What this does:** Neural arrays are downcast from float32 to uint8 (4× saving) per trial; behavior arrays use float32; pickle protocol 4 is used. No streaming/incremental write — everything is held in `all_results` then dumped at once.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
