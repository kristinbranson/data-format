# zhang2025 — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/zhang2025/claude-code/2026-04-09__06-58-15_trial3/verifier/snapshot/`

Outputs identified (K=4): choice, prior_probability_left, wheel_speed, whisker_motion_energy

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Direct disk loading (bypasses ONE API since cache is read-only)" (line 219); "Data is organized as ONE cache at `/app/data/one_cache/`: `{lab}/Subjects/{subject}/{date}/{number}/alf/`" (lines 72-83)

**Code** (convert_data.py:820-832):
```python
# Load BWM release info
bwm_df = pd.read_csv(BWM_CSV, index_col=0)

# Group probes by session
session_groups = bwm_df.groupby('eid')
session_list = []
for eid, group in session_groups:
    row = group.iloc[0]
    probe_names = list(group['probe_name'])
    session_list.append((
        eid, row['lab'], row['subject'], row['date'],
        row['session_number'], probe_names
    ))
```

**What this does:** Reads the BWM release CSV listing all sessions/probes, groups rows by session eid, then iterates the session list calling `process_session()` for each (loop at line 852). Each session is loaded directly from disk paths under `/app/data/one_cache/{lab}/Subjects/{subject}/{date}/{session_num}/`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none — subject split is implicit via metadata)

**Code** (convert_data.py:873-877, 985-986):
```python
subject = result['subject']
if subject not in subject_set:
    subject_set.append(subject)
subject_idx = subject_set.index(subject)
...
'subjects': subject_set,
'subject_idx': np.array(all_subject_idx, dtype=np.int64),
```

**What this does:** Each session result carries the subject name (from BWM CSV). The script maintains an ordered `subject_set` list and assigns each session a `subject_idx` referencing it. Subjects are stored as a list with a parallel per-session subject_idx array; trials are not separately split — they remain grouped by session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sessions: 438 processed (95.4% of 459)" (line 321); "All 21 skipped sessions had 'Too few valid trials (0)'" (line 307)

**Code** (convert_data.py:824-832, 852-872):
```python
session_groups = bwm_df.groupby('eid')
session_list = []
for eid, group in session_groups:
    row = group.iloc[0]
    probe_names = list(group['probe_name'])
    session_list.append((eid, row['lab'], row['subject'], row['date'],
        row['session_number'], probe_names))
...
for i, session_info in enumerate(session_list):
    ...
    result = process_session(session_info, show_processing=show)
    ...
    if result is None:
        n_skipped += 1
        continue
```

**What this does:** Each unique `eid` from BWM CSV defines one session; sessions are processed independently and each yields its own per-trial neural/input/output lists. The final pickle stores per-session lists indexed by session order; eids are recorded in `metadata['session_eids']`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trial mask: excludes RT < 0.08s or > 2.0s, NaN in key events, no-choice (choice==0), max_trial_len=10s" (line 63)

**Code** (convert_data.py:565-568, 654-680):
```python
stim_times = trials_df[ALIGN_TIME].values
interval_begs = stim_times + TIME_WINDOW[0]
interval_ends = stim_times + TIME_WINDOW[1]
...
for trial_idx in range(n_trials):
    neural_trial = neural_data[trial_idx].astype(np.uint8)
    neural_list.append(neural_trial)
    input_trial = np.zeros((2, N_BINS), dtype=np.float32)
    ...
    output_trial = np.zeros((4, N_BINS), dtype=np.int32)
    ...
```

**What this does:** Each row of the IBL trials table is one trial. Trial intervals are defined as `[stimOn - 0.5, stimOn + 1.5]` seconds. After mask filtering, each remaining trial becomes a separate entry in the per-session `neural`/`input`/`output` lists.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Exclude if NaN in: stimOn_times, choice, feedback_times, probabilityLeft, firstMovement_times, feedbackType. Exclude if RT (firstMovement_times - stimOn_times) < 0.08s or > 2.0s. Exclude if choice == 0. Exclude if trial length > 10s" (lines 135-138)

**Code** (convert_data.py:205-233, 600-610):
```python
def create_trials_mask(trials_df):
    mask = np.ones(n_trials, dtype=bool)
    for event in NAN_EXCLUDE:
        if event in trials_df.columns:
            mask &= ~trials_df[event].isna()
    if MIN_RT is not None:
        rt = trials_df['firstMovement_times'] - trials_df['stimOn_times']
        mask &= (rt >= MIN_RT)
    if MAX_RT is not None:
        mask &= (rt <= MAX_RT)
    if MAX_TRIAL_LEN is not None:
        trial_len = trials_df['feedback_times'] - trials_df['goCue_times']
        mask &= (trial_len <= MAX_TRIAL_LEN) | trial_len.isna()
    if EXCLUDE_NOCHOICE:
        mask &= (trials_df['choice'] != 0)
    return mask
...
combined_mask = mask & wheel_mask & me_mask
```

**What this does:** Builds a boolean mask combining: NaN exclusion on six event columns, RT in [0.08, 2.0]s, trial length ≤ 10s, choice ≠ 0, plus per-trial behavior interpolation success masks (wheel + whisker ME). Sessions with fewer than 2 surviving trials are skipped entirely (line 605-607).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "spikes.times + spikes.clusters → neural | Bin into 20ms bins, align to stimOn_times" (line 184); "spikes.times.npy, spikes.clusters.npy ... clusters.channels.npy" (lines 81-82)

**Code** (convert_data.py:99-108):
```python
times_file = os.path.join(spike_dir, 'spikes.times.npy')
clusters_file = os.path.join(spike_dir, 'spikes.clusters.npy')
...
spikes = {
    'times': np.load(times_file).flatten(),
    'clusters': np.load(clusters_file).flatten(),
}
```

**What this does:** Neural data is derived from `spikes.times.npy` and `spikes.clusters.npy` files in each probe's `pykilosort/<latest revision>/` directory. Cluster channels and brainLocationIds are loaded for region mapping but not used in the spike-count tensor itself.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Spike binning uses np.bincount with linear indexing (4x faster than np.add.at)" (line 224); "Use uint8 for neural arrays (spike counts in 20ms bins are small integers 0-255)" (line 304)

**Code** (convert_data.py:357-395):
```python
def bin_spikes_fast(spike_times, spike_clusters, interval_begs, interval_ends, n_clusters_total):
    binned = np.zeros((n_trials, n_clusters_total, N_BINS), dtype=np.float32)
    valid_idx = np.where(valid_trials)[0]
    starts = np.searchsorted(spike_times, interval_begs[valid_idx], side='left')
    ends = np.searchsorted(spike_times, interval_ends[valid_idx], side='right')
    minlength = n_clusters_total * N_BINS
    for i, trial_idx in enumerate(valid_idx):
        s, e = starts[i], ends[i]
        ...
        b = np.clip(((t - interval_begs[trial_idx]) / BINSIZE).astype(np.int32), 0, N_BINS - 1)
        ...
        lin_idx = c * N_BINS + b
        counts = np.bincount(lin_idx, minlength=minlength)
        binned[trial_idx] = counts[:minlength].reshape(n_clusters_total, N_BINS)
    return binned
```

**What this does:** Spikes from all probes in a session are merged (cluster IDs offset to be unique), sorted by time, then binned per trial into a `(n_trials, n_clusters, 100)` array. For each trial, spike times in `[stimOn-0.5, stimOn+1.5]` are binned with floor((t-t_beg)/0.02) and accumulated via `np.bincount` on a linearized (cluster, bin) index. Final stored as uint8.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "No neuron quality filtering: load_spiking_data() called with default qc=None → ALL clusters used" (line 60); "We follow Zhang code: use ALL neurons (cluster label filtering is NOT applied)" (line 143)

**Code** (convert_data.py:1012):
```python
'neuron_filtering': 'none (all clusters used, matching Zhang et al. 2025)',
```

**What this does:** No neuron-level QC is applied. All clusters from `spikes.clusters` are kept regardless of cluster label, refractory period violations, or amplitude. Cluster metrics are loaded but not used for filtering.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "binsize: 0.02 # 20ms bins" (line 50); "Neural data time bin | 20ms" (line 114); "T = 100" (line 116)

**Code** (convert_data.py:31-35, 383):
```python
BINSIZE = 0.02          # 20ms bins
ALIGN_TIME = 'stimOn_times'
TIME_WINDOW = (-0.5, 1.5)  # seconds relative to alignment event
INTERVAL_LEN = TIME_WINDOW[1] - TIME_WINDOW[0]  # 2.0 seconds
N_BINS = int(np.ceil(INTERVAL_LEN / BINSIZE))  # 100 time bins
...
b = np.clip(((t - interval_begs[trial_idx]) / BINSIZE).astype(np.int32), 0, N_BINS - 1)
```

**What this does:** Spikes within the 2-second per-trial window are binned into 100 fixed 20ms bins by computing `floor((spike_time - interval_beg) / 0.02)`. No further smoothing or resampling.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Alignment event | stimOn_times" (line 117); "align_time: 'stimOn_times', time_window: (-.5, 1.5)" (lines 53-54)

**Code** (convert_data.py:565-568):
```python
stim_times = trials_df[ALIGN_TIME].values
interval_begs = stim_times + TIME_WINDOW[0]
interval_ends = stim_times + TIME_WINDOW[1]
```

**What this does:** Each trial interval is computed as `stimOn_times ± [-0.5, +1.5]` seconds. Spikes are binned relative to `interval_beg`, so bin 0 corresponds to t=−0.5s before stimulus onset and bin 99 to t=+1.5s after. The same window is used for behavior interpolation, ensuring temporal alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `input` *time_from_stimulus_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| stimOn_times | input[0]: \"time_since_stim_onset\" | np.linspace(-0.48, 1.5, 100) | Computed from bin edges | Time-varying, same for all trials |" (CONVERSION_NOTES.md:185); verification table "| time_since_stim_onset range | [-0.5, 1.5] |" (CONVERSION_NOTES.md:245).

**Code** (convert_data.py:31-35, 645-650):
```python
BINSIZE = 0.02          # 20ms bins
ALIGN_TIME = 'stimOn_times'
TIME_WINDOW = (-0.5, 1.5)  # seconds relative to alignment event
INTERVAL_LEN = TIME_WINDOW[1] - TIME_WINDOW[0]  # 2.0 seconds
N_BINS = int(np.ceil(INTERVAL_LEN / BINSIZE))  # 100 time bins
...
    # 11. Format as lists of trials
    # Time since stimulus onset (same for all trials)
    # Matching reference code: bin centers from interval_beg + binsize to interval_end
    time_since_onset = np.linspace(
        TIME_WINDOW[0] + BINSIZE, TIME_WINDOW[1], N_BINS
    ).astype(np.float32)
```

**What this does:** The conversion produces this input as `time_since_stim_onset` (`input_names[0]`, convert_data.py:989). It is not read from a raw column; it is constructed from the constants `TIME_WINDOW = (-0.5, 1.5)` and `BINSIZE = 0.02`. The notes attribute it to `stimOn_times`, which is the raw field defining the window the bins are placed in.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_stimulus_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "np.linspace(-0.48, 1.5, 100) | Computed from bin edges | Time-varying, same for all trials" (CONVERSION_NOTES.md:185).

**Code** (convert_data.py:645-670):
```python
    # 11. Format as lists of trials
    # Time since stimulus onset (same for all trials)
    # Matching reference code: bin centers from interval_beg + binsize to interval_end
    time_since_onset = np.linspace(
        TIME_WINDOW[0] + BINSIZE, TIME_WINDOW[1], N_BINS
    ).astype(np.float32)
    ...
    for trial_idx in range(n_trials):
        ...
        input_trial = np.zeros((2, N_BINS), dtype=np.float32)
        input_trial[0, :] = time_since_onset
        input_trial[1, :] = trial_num_in_block[trial_idx]  # broadcast scalar
        input_list.append(input_trial)
```

**What this does:** A single 100-element float32 vector is built once per session as `np.linspace(-0.48, 1.5, 100)`, i.e. 0.02 s steps from -0.48 to 1.5 (the upper edge of each 20 ms bin, though the comment calls them bin centers). The same vector is written to row 0 of every trial's `(2, 100)` input array, so it is identical across trials and sessions.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `input` *time_from_stimulus_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Unified alignment to stimOn_times: All variables aligned to stimulus onset, window -0.5 to 1.5s" (CONVERSION_NOTES.md:194); "Spike binning: ... 20ms bins, stimOn alignment, (-0.5, 1.5)s window" (CONVERSION_NOTES.md:332).

**Code** (convert_data.py:565-575, 648-650):
```python
    # 5. Compute trial intervals
    stim_times = trials_df[ALIGN_TIME].values
    interval_begs = stim_times + TIME_WINDOW[0]
    interval_ends = stim_times + TIME_WINDOW[1]

    # 6. Bin spikes
    binned_spikes = bin_spikes_fast(
        merged_spikes['times'], merged_spikes['clusters'],
        interval_begs, interval_ends, n_clusters
    )
    ...
    time_since_onset = np.linspace(
        TIME_WINDOW[0] + BINSIZE, TIME_WINDOW[1], N_BINS
    ).astype(np.float32)
```

**What this does:** Alignment is implicit in shared constants: spikes are binned into `[stimOn_times - 0.5, stimOn_times + 1.5]` with `bin_idx = clip(((t - interval_beg)/0.02), 0, 99)` (convert_data.py:383), and the time vector spans the same 2 s window in the same 100 steps, so element *k* corresponds to neural bin *k*. The stored value is the bin's upper edge, with -0.48 for the first bin.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `input` *trial_number_in_block* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Trial index within block | input[1]: \"trial_number_in_block\" | Compute from probabilityLeft transitions | Custom computation | Per-trial scalar |" (CONVERSION_NOTES.md:186); "Trial number in block: Compute from transitions in probabilityLeft values" (CONVERSION_NOTES.md:199); verification "| trial_number_in_block range | [0, 94] |" (CONVERSION_NOTES.md:246).

**Code** (convert_data.py:630-633):
```python
    # Trial number in block (use full trials_df for correct block computation)
    all_prob_left = trials_df['probabilityLeft'].values
    all_trial_nums = compute_trial_number_in_block(all_prob_left)
    trial_num_in_block = all_trial_nums[good_indices].astype(np.float32)
```

**What this does:** The conversion produces this input as `trial_number_in_block` (`input_names[1]`, convert_data.py:989). It is derived from the `probabilityLeft` column of the raw trials table (`trials_df`) together with that table's row ordering.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `input` *trial_number_in_block*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Compute from probabilityLeft transitions | Custom computation | Per-trial scalar" (CONVERSION_NOTES.md:186); "| trial_number_in_block range | [0, 94] |" (CONVERSION_NOTES.md:246).

**Code** (convert_data.py:455-470, 630-633, 667-669):
```python
def compute_trial_number_in_block(prob_left):
    """
    Compute trial number within the current block.
    A block change occurs when probabilityLeft changes value.
    """
    trial_numbers = np.zeros(len(prob_left), dtype=np.float32)
    current_block_start = 0
    current_val = prob_left[0]

    for i in range(len(prob_left)):
        if prob_left[i] != current_val:
            current_block_start = i
            current_val = prob_left[i]
        trial_numbers[i] = i - current_block_start

    return trial_numbers
...
    all_trial_nums = compute_trial_number_in_block(all_prob_left)
    trial_num_in_block = all_trial_nums[good_indices].astype(np.float32)
...
        input_trial[1, :] = trial_num_in_block[trial_idx]  # broadcast scalar
```

**What this does:** The function scans the full unfiltered trials table in order, records the index where `probabilityLeft` last changed, and stores `i - current_block_start`, so the count is 0-based (first trial of a block is 0) and reflects position among all trials including those later excluded. The per-trial value is then subset by `good_indices` (trial-quality plus wheel/motion-energy masks), cast to float32, and broadcast across all 100 time bins as row 1 of the input array; verification reports a range of [0, 94].

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "trials.choice → output[0]: 'choice' | Map: -1→0 (left), 1→1 (right)" (line 187)

**Code** (convert_data.py:617, 622):
```python
choice_raw = trials_df['choice'].values[good_indices]       # -1 or 1
...
choice = ((choice_raw + 1) / 2).astype(np.int32)  # 0 or 1
```

**What this does:** Derived solely from the `choice` column of `_ibl_trials.table.pqt`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Choice mapping: IBL choice -1 (left) → 0, choice 1 (right) → 1" (line 200)

**Code** (convert_data.py:621-622, 676):
```python
# Choice: -1 (left) -> 0, 1 (right) -> 1
choice = ((choice_raw + 1) / 2).astype(np.int32)  # 0 or 1
...
output_trial[0, :] = choice[trial_idx]
```

**What this does:** Maps raw choice {-1, +1} → {0, 1} (no-choice trials excluded by mask). The per-trial scalar is broadcast to all 100 time bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `output` *prior_probability_left* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "trials.probabilityLeft → output[1]: 'prior_probability_left' | Map: 0.2→0, 0.5→1, 0.8→2" (line 188)

**Code** (convert_data.py:618, 625-628):
```python
prob_left = trials_df['probabilityLeft'].values[good_indices]  # 0.2, 0.5, 0.8
...
prior = np.zeros(len(prob_left), dtype=np.int32)
prior[prob_left == 0.2] = 0
prior[prob_left == 0.5] = 1
prior[prob_left == 0.8] = 2
```

**What this does:** Derived from the `probabilityLeft` column of the trials table.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `output` *prior_probability_left*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Prior distribution | 0.2: 0.42, 0.5: 0.12, 0.8: 0.46" (line 248)

**Code** (convert_data.py:625-628, 677):
```python
prior = np.zeros(len(prob_left), dtype=np.int32)
prior[prob_left == 0.2] = 0
prior[prob_left == 0.5] = 1
prior[prob_left == 0.8] = 2
...
output_trial[1, :] = prior[trial_idx]
```

**What this does:** Maps the three discrete `probabilityLeft` values {0.2, 0.5, 0.8} to integer class labels {0, 1, 2}; broadcast across all 100 time bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-a. What variables in the raw data is `output` *wheel_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "abs(wheel.velocity) → output[2]: 'wheel_speed'" (line 189); "_ibl_wheel.position.npy, _ibl_wheel.timestamps.npy" (line 76)

**Code** (convert_data.py:248-256):
```python
alf_path = os.path.join(session_path, 'alf')
pos_file = find_file(alf_path, '_ibl_wheel.position.npy')
ts_file = find_file(alf_path, '_ibl_wheel.timestamps.npy')
...
re_pos = np.load(pos_file).flatten()
re_ts = np.load(ts_file).flatten()
```

**What this does:** Derived from `_ibl_wheel.position.npy` and `_ibl_wheel.timestamps.npy`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-b. What processing is involved in computing `output` *wheel_speed*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Wheel velocity computed matching brainbox: interpolate to 1000Hz uniform, Butterworth LP filter (order=8, corner=20Hz), diff * fs" (line 220); "Discretize wheel speed and whisker ME into 3 equal-frequency bins across all trials in a session" (line 198)

**Code** (convert_data.py:262-282, 636-639):
```python
fs = 1000
t = np.arange(re_ts[0], re_ts[-1], 1.0 / fs)
position = scipy_interp1d(re_ts, re_pos, kind='linear')(t)
sos = scipy.signal.butter(N=order, Wn=corner_frequency / fs * 2,
                           btype='lowpass', output='sos')
vel = np.insert(np.diff(scipy.signal.sosfiltfilt(sos, position)), 0, 0) * fs
speed = np.abs(vel).astype(np.float32)
...
wheel_flat = wheel_data.flatten()
wheel_discrete = discretize_to_bins(wheel_flat, n_bins=3)
```

**What this does:** (1) Linearly interpolate wheel position to 1 kHz uniform; (2) Butterworth low-pass filter (order 8, 20 Hz); (3) finite-difference scaled by fs → velocity; (4) take absolute value → speed; (5) interpolate to per-trial bin times via `interpolate_behavior`; (6) discretize all session bin values into 3 equal-frequency quantile bins {0, 1, 2}.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-c. How is `output` *wheel_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavior interpolation: linear interpolation to bin centers at interval_beg + binsize, ..., interval_end" (line 62)

**Code** (convert_data.py:419-447, 678):
```python
for trial_idx in range(n_trials):
    t_beg = interval_begs[trial_idx]
    t_end = interval_ends[trial_idx]
    ...
    x_interp = np.linspace(t_beg + BINSIZE, t_end, N_BINS)
    y_interp = interp1d(trial_times, trial_vals, kind='linear',
                       fill_value='extrapolate')(x_interp)
    binned_beh[trial_idx] = y_interp.astype(np.float32)
...
output_trial[2, :] = wheel_discrete_2d[trial_idx]
```

**What this does:** Wheel speed is interpolated onto the same 100 bin times spanning `[stimOn-0.5, stimOn+1.5]` used for the neural tensor. Trials whose wheel coverage doesn't bracket the interval (gap > BINSIZE) are excluded from the combined mask.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "whiskerMotionEnergy → output[3]: 'whisker_motion_energy'" (line 190); "Whisker ME: tries left camera first, falls back to right" (line 61)

**Code** (convert_data.py:285-307):
```python
me_file = find_file(alf_path, 'leftCamera.ROIMotionEnergy.npy')
times_file = find_file(alf_path, '_ibl_leftCamera.times.npy')
if me_file is not None and times_file is not None:
    me = np.load(me_file).flatten()
    times = np.load(times_file).flatten()
    if len(me) == len(times):
        return times, me
# Fall back to right camera
me_file = find_file(alf_path, 'rightCamera.ROIMotionEnergy.npy')
times_file = find_file(alf_path, '_ibl_rightCamera.times.npy')
```

**What this does:** Derived from `leftCamera.ROIMotionEnergy.npy` (paired with `_ibl_leftCamera.times.npy`); falls back to right camera files if left unavailable.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What processing is involved in computing `output` *whisker_motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretization of wheel speed and whisker ME: Use 3 equal-frequency (quantile) bins across all trials in a session" (line 198)

**Code** (convert_data.py:590-596, 641-643):
```python
me_times, me_values = load_whisker_motion_energy(session_path)
if me_times is not None:
    binned_me, me_mask = interpolate_behavior(
        me_times, me_values, interval_begs, interval_ends)
...
me_flat = me_data.flatten()
me_discrete = discretize_to_bins(me_flat, n_bins=3)
me_discrete_2d = me_discrete.reshape(me_data.shape).astype(np.int32)
```

**What this does:** Raw motion-energy values are loaded directly (no filtering), interpolated linearly to per-trial bin times, then discretized via 3 equal-frequency quantile bins computed over all valid (trial, bin) values in the session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. How is `output` *whisker_motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (same alignment as wheel speed via `interpolate_behavior`)

**Code** (convert_data.py:592-593, 679):
```python
binned_me, me_mask = interpolate_behavior(
    me_times, me_values, interval_begs, interval_ends)
...
output_trial[3, :] = me_discrete_2d[trial_idx]
```

**What this does:** Interpolated to the same 100 bin times in `[stimOn-0.5, stimOn+1.5]` used for neural data. Trials with insufficient ME coverage are dropped via `me_mask` in the combined session mask.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "21 skipped (0 valid trials)" (line 290); "All 21 skipped sessions had 'Too few valid trials (0)' after applying the trial filtering mask ... AND behavior interpolation mask" (line 307)

**Code** (convert_data.py:511-519, 600-607, 862-871):
```python
if not os.path.exists(session_path):
    print(f"  Session path not found: {session_path}")
    return None
trials_df = load_trials(session_path)
if trials_df is None:
    return None
...
combined_mask = mask & wheel_mask & me_mask
n_good_trials = np.sum(combined_mask)
if n_good_trials < 2:
    print(f"  Too few valid trials ({n_good_trials}) for {eid}")
    return None
...
try:
    result = process_session(session_info, show_processing=show)
except Exception as e:
    print(f"  ERROR processing {eid}: {type(e).__name__}: {e}")
    n_skipped += 1
    continue
```

**What this does:** Missing files, missing probes, NaN trials, behavior gaps, and any unhandled exceptions cause the affected trial or whole session to be skipped (returning None) with a logged message. Sessions with < 2 valid trials are dropped. Cluster channels are clipped to valid ranges; cluster brain region defaults to 'void' if unavailable.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Load spikes | 0.9s | 413s; Bin spikes | 0.4s | 184s; Load wheel | 0.5s | 230s; Total | ~1.9s | ~15 min" (lines 261-265); "Total time: 2,149s (~36 min)" (line 298)

**Code** (convert_data.py:570-577, 581-596):
```python
t_spike = time.time()
binned_spikes = bin_spikes_fast(...)
t_spike_done = time.time()
# 7. Load and bin continuous behaviors
wheel_times, wheel_speed = load_wheel_speed(session_path)
if wheel_times is not None:
    binned_wheel, wheel_mask = interpolate_behavior(...)
...
me_times, me_values = load_whisker_motion_energy(session_path)
if me_times is not None:
    binned_me, me_mask = interpolate_behavior(...)
```

**What this does:** Per the notes, dominant per-session costs are spike loading from disk (~0.9s), wheel loading + Butterworth filtering (~0.5s), and spike binning (~0.4s). The full run also has substantial I/O overhead from temp-file pickling per session and final reassembly batches.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "np.bincount linear indexing for spike binning: 1.6s → 0.4s per session" (line 226); "Vectorized searchsorted for trial boundaries" (line 227)

**Code** (convert_data.py:419-450, 455-470, 658-680):
```python
for trial_idx in range(n_trials):
    ...
    x_interp = np.linspace(t_beg + BINSIZE, t_end, N_BINS)
    y_interp = interp1d(trial_times, trial_vals, kind='linear', ...)(x_interp)
    binned_beh[trial_idx] = y_interp.astype(np.float32)
...
def compute_trial_number_in_block(prob_left):
    for i in range(len(prob_left)):
        if prob_left[i] != current_val:
            ...
        trial_numbers[i] = i - current_block_start
...
for trial_idx in range(n_trials):
    neural_trial = neural_data[trial_idx].astype(np.uint8)
    neural_list.append(neural_trial)
    input_trial = ...
```

**What this does:** Three remaining per-trial Python loops — `interpolate_behavior` (one interp1d call per trial), `compute_trial_number_in_block` (could use `np.diff` + `cumsum`), and the final neural/input/output formatting loop (could use array slicing + tile/broadcast).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:216-221, 558, 933-942, 965-977):
```python
if MIN_RT is not None:
    rt = trials_df['firstMovement_times'] - trials_df['stimOn_times']
    mask &= (rt >= MIN_RT)
if MAX_RT is not None:
    rt = trials_df['firstMovement_times'] - trials_df['stimOn_times']
    mask &= (rt <= MAX_RT)
...
br = BrainRegions()
...
for meta in session_meta:
    with open(meta['tmp_file'], 'rb') as f:
        sess = pickle.load(f)
    ...
for batch_start in range(0, len(session_meta), BATCH_SIZE):
    for idx in range(batch_start, batch_end):
        with open(session_meta[idx]['tmp_file'], 'rb') as f:
            sess = pickle.load(f)
```

**What this does:** RT is recomputed twice (min/max). `BrainRegions()` is instantiated per session inside `process_session`. Each session's temp pickle is loaded twice during reassembly — once in the metadata pass, once in the batch loading pass.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:111-121, 707-802):
```python
# Load cluster info
if os.path.exists(channels_file):
    clusters['channels'] = np.load(channels_file).flatten()
if os.path.exists(depths_file):
    clusters['depths'] = np.load(depths_file).flatten()
if os.path.exists(metrics_file):
    clusters['metrics'] = pd.read_parquet(metrics_file)
...
def plot_processing(eid, neural_data, ...):
    ...
    plt.savefig(f'processing_{eid}.png', dpi=100)
```

**What this does:** Cluster `depths` and `metrics` parquet are loaded but not used downstream (no QC filter, no depth-based selection). The `plot_processing` path generates large PNGs only when `--show-processing` flag is set. Spikes are loaded with `.depths.npy` and `.amps.npy` available but only times+clusters are used in the pipeline.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Saving each session to a temporary pickle file during processing; Reassembling from temp files at the end in batches of 50; Using uint8 for neural arrays ... float32 for input, int32 for output" (lines 302-304)

**Code** (convert_data.py:660-661, 887-908, 955, 965-979):
```python
neural_trial = neural_data[trial_idx].astype(np.uint8)
...
tmp_file = os.path.join(tmp_dir, f'session_{n_processed:04d}.pkl')
with open(tmp_file, 'wb') as f:
    pickle.dump({...}, f, protocol=pickle.HIGHEST_PROTOCOL)
...
del result
gc.collect()
...
BATCH_SIZE = 50  # sessions per batch
for batch_start in range(0, len(session_meta), BATCH_SIZE):
    for idx in range(batch_start, batch_end):
        with open(session_meta[idx]['tmp_file'], 'rb') as f:
            sess = pickle.load(f)
        ...
    gc.collect()
```

**What this does:** (1) Neural stored as uint8 (input float32, output int32); (2) Each session's data is dumped to a temp pickle and freed via `del`+`gc.collect()` to keep peak RAM under the 64 GB cgroup limit; (3) Reassembly proceeds in 50-session batches with explicit gc; (4) Spikes are processed one session at a time rather than concatenated globally.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
