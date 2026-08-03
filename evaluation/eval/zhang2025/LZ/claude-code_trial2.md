# zhang2025 — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/zhang2025/claude-code/2026-03-24__09-05-04_trial2/verifier/snapshot/`

Outputs identified (K=4): choice, prior, wheel_speed, whisker_motion_energy

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Processes sessions from `data/one_cache/<lab>/Subjects/<subject>/<date>/001/alf/`" (CONVERSION_NOTES.md:237)

**Code** (convert_data.py:58-77, 604-647):
```python
def find_session_dirs():
    """Find all session directories with required data."""
    session_dirs = sorted(glob.glob(str(DATA_ROOT / '*/Subjects/*/*/001')))
    valid = []
    for sdir in session_dirs:
        has_spikes = len(glob.glob(os.path.join(sdir, 'alf/probe*/pykilosort/*/spikes.times.npy'))) > 0
        has_trials = len(glob.glob(os.path.join(sdir, 'alf/*/_ibl_trials.table.pqt'))) > 0
        has_wheel = os.path.exists(os.path.join(sdir, 'alf/_ibl_wheel.timestamps.npy'))
        ...
        if has_spikes and has_trials and has_wheel and has_me:
            valid.append(sdir)
    return valid
...
for i, sdir in enumerate(session_dirs):
    result = process_session(sdir, br, ...)
    if result is not None:
        neural.append(result['neural'])
        ...
```

**What this does:** Globs `data/one_cache/<lab>/Subjects/<mouse>/<date>/001` for sessions that have spikes, trials, wheel, and motion-energy files. Iterates through each valid session, processing one at a time and appending per-trial arrays into per-session lists.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none — only mentions 118 subjects total)"

**Code** (convert_data.py:80-87, 626-671):
```python
def parse_session_info(sdir):
    parts = Path(sdir).parts
    sub_idx = parts.index('Subjects')
    lab = parts[sub_idx - 1]
    subject = parts[sub_idx + 1]
    date = parts[sub_idx + 2]
    return lab, subject, date
...
if subject not in all_subjects:
    all_subjects.append(subject)
subject_per_session.append(subject)
...
subject_idx = np.array([all_subjects.index(s) for s in subject_per_session], dtype=np.int32)
```

**What this does:** Extracts subject name from the directory path; builds a unique subject list and a `subject_idx` mapping per session. Subjects are not nested separately — they are recorded as an integer index per session.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions: 335" (README.md:9); each session = a `<subject>/<date>/001` directory.

**Code** (convert_data.py:60, 383-390, 506-515, 626-647):
```python
session_dirs = sorted(glob.glob(str(DATA_ROOT / '*/Subjects/*/*/001')))
...
def process_session(sdir, br, show_processing=False, session_idx=0):
    lab, subject, date = parse_session_info(sdir)
    session_id = f"{subject}_{date}"
    ...
    return {'neural': neural_list, 'input': input_list, 'output': output_list, ..., 'session_id': session_id}
...
neural.append(result['neural'])
input_data.append(result['input'])
output_data.append(result['output'])
```

**What this does:** Each `001` directory is treated as one session. The outer `neural`/`input`/`output` lists are indexed by session, with each element a list of per-trial arrays for that session.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Align to stimOn_times, window (-0.5, 1.5)s; 20ms bins -> 100 time steps per trial" (convert_data.py:9-10 docstring)

**Code** (convert_data.py:401-411, 437-439, 469-492):
```python
stim_on = trials[ALIGN_TIME].values
interval_begs = stim_on + TIME_WINDOW[0]
interval_ends = stim_on + TIME_WINDOW[1]
binned_spikes = bin_spikes_vectorized(
    spike_times, spike_clusters, n_clusters, interval_begs, interval_ends
)
...
neural_trials = binned_spikes[good_indices]
wheel_trials = wheel_vals[good_indices]
whisker_trials = whisker_vals[good_indices]
...
neural_list = [np.clip(neural_trials[i], 0, 255).astype(np.uint8) for i in range(n_trials)]
```

**What this does:** Each trial is a 2-second interval centered on `stimOn_times` ([-0.5, +1.5]s). Per-trial neural, input, and output arrays are stacked then split back into per-trial entries via list comprehension.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial curation: RT 0.08-2.0s, exclude no-choice, exclude NaN key events; max_trial_len=10.0" (CONVERSION_NOTES.md:149-153)

**Code** (convert_data.py:100-128, 427-433):
```python
def create_trial_mask(trials):
    mask = pd.Series(True, index=trials.index)
    rt = trials['firstMovement_times'] - trials['stimOn_times']
    mask &= (rt >= MIN_RT) & (rt <= MAX_RT)
    if 'goCue_times' in trials.columns and 'feedback_times' in trials.columns:
        trial_len = trials['feedback_times'] - trials['goCue_times']
        mask &= (trial_len <= MAX_TRIAL_LEN) | trial_len.isna()
    mask &= (trials['choice'] != 0)
    for col in NAN_EXCLUDE:
        if col in trials.columns:
            mask &= ~trials[col].isna()
    return mask
...
combined_mask = mask.values & wheel_mask & whisker_mask
good_indices = np.where(combined_mask)[0]
```

**What this does:** Builds a boolean trial mask combining: RT in [0.08, 2.0]s, trial length ≤ 10s, choice ≠ 0 (no-choice excluded), and non-NaN values in 6 key event columns. Combined with behavior availability masks (wheel/whisker coverage).

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "spikes.times + spikes.clusters → neural; Bin into 20ms bins per trial, aligned to stimOn_times (-0.5, 1.5)s" (CONVERSION_NOTES.md:198)

**Code** (convert_data.py:131-189):
```python
def load_spikes(sdir):
    probe_dirs = sorted(glob.glob(os.path.join(sdir, 'alf/probe*/pykilosort/*')))
    ...
    for pdir in probe_dirs:
        st_file = os.path.join(pdir, 'spikes.times.npy')
        sc_file = os.path.join(pdir, 'spikes.clusters.npy')
        cc_file = os.path.join(pdir, 'clusters.channels.npy')
        cb_file = os.path.join(pdir, 'channels.brainLocationIds_ccf_2017.npy')
        ...
        spike_times = np.load(st_file).flatten()
        spike_clusters = np.load(sc_file).flatten()
        cluster_channels = np.load(cc_file).flatten()
        channel_brain_ids = np.load(cb_file).flatten()
```

**What this does:** Neural data is derived from `spikes.times.npy` and `spikes.clusters.npy` per probe (pykilosort output), with `clusters.channels.npy` and `channels.brainLocationIds_ccf_2017.npy` providing cluster-to-region mapping.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Spike binning using `np.searchsorted` + flat indexing for efficiency; Neural data stored as uint8 (spike counts rarely exceed 255) to reduce memory" (CONVERSION_NOTES.md:239-240)

**Code** (convert_data.py:168-189, 192-232):
```python
spike_clusters_offset = spike_clusters + cluster_offset
cluster_offset += n_clusters
all_spike_times.append(spike_times)
all_spike_clusters.append(spike_clusters_offset)
all_cluster_regions.extend(beryl_regions)
...
merged_times = np.concatenate(all_spike_times)
merged_clusters = np.concatenate(all_spike_clusters)
sort_idx = np.argsort(merged_times, kind='stable')
...
def bin_spikes_vectorized(spike_times, spike_clusters, n_clusters, interval_begs, interval_ends):
    binned = np.zeros((n_trials, n_clusters, N_BINS), dtype=np.float32)
    for trial_idx in range(n_trials):
        ...
        i_start = np.searchsorted(spike_times, t_beg, side='left')
        i_end = np.searchsorted(spike_times, t_end, side='left')
        ...
        bin_idx = np.minimum(((times_trial - t_beg) / BINSIZE).astype(np.int32), N_BINS - 1)
        flat_idx = clusters_trial * N_BINS + bin_idx
        counts = np.bincount(flat_idx, minlength=n_clusters * N_BINS)
        binned[trial_idx] = counts[:n_clusters * N_BINS].reshape(n_clusters, N_BINS)
```

**What this does:** Spikes from all probes are merged with offset cluster IDs, sorted by time, then binned per trial via searchsorted + bincount on flat (cluster, bin) indices. Final spike counts are clipped to [0,255] and stored as uint8.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "No QC filter applied in `prepare_data` (qc=None by default); ALL neurons used, not just good ones" (CONVERSION_NOTES.md:67-68); "Neurons: All neurons used (no QC filtering, matching reference code qc=None)" (README.md:80)

**Code** (convert_data.py:131-135):
```python
def load_spikes(sdir):
    """Load and merge spikes from all probes in a session.

    Following reference code: no QC filtering (qc=None).
    """
```

**What this does:** No neuron-level QC filtering is applied; all clusters from pykilosort output are retained. (A separate `reduce_data.py` later subsamples to ≤500 neurons/session for memory.)

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "20ms bins -> 100 time steps per trial" (convert_data.py:10); "Binsize: 20ms uniformly, matching code" (CONVERSION_NOTES.md:185)

**Code** (convert_data.py:36-40, 220-230):
```python
ALIGN_TIME = 'stimOn_times'
TIME_WINDOW = (-0.5, 1.5)  # 2s trial
BINSIZE = 0.02  # 20ms
INTERVAL_LEN = TIME_WINDOW[1] - TIME_WINDOW[0]  # 2.0s
N_BINS = int(np.ceil(INTERVAL_LEN / BINSIZE))  # 100
...
bin_idx = np.minimum(
    ((times_trial - t_beg) / BINSIZE).astype(np.int32),
    N_BINS - 1
)
flat_idx = clusters_trial * N_BINS + bin_idx
counts = np.bincount(flat_idx, minlength=n_clusters * N_BINS)
```

**What this does:** Spike times are converted to bin indices via floor division by 20 ms (clipped to N_BINS-1=99), giving 100 non-overlapping bins per 2-second trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Alignment: stimOn_times for all behaviors (matching reference code + decoder task)" (README.md:78); "Align to stimOn_times, window (-0.5, 1.5)s" (convert_data.py:9)

**Code** (convert_data.py:36-40, 401-411):
```python
ALIGN_TIME = 'stimOn_times'
TIME_WINDOW = (-0.5, 1.5)  # 2s trial
...
stim_on = trials[ALIGN_TIME].values
interval_begs = stim_on + TIME_WINDOW[0]
interval_ends = stim_on + TIME_WINDOW[1]
...
binned_spikes = bin_spikes_vectorized(
    spike_times, spike_clusters, n_clusters, interval_begs, interval_ends
)
```

**What this does:** Trial intervals are computed by adding the [-0.5, +1.5]s window to each trial's `stimOn_times`. Spikes within those intervals are binned, so bin 0 corresponds to -0.5s relative to stimulus onset.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_stimulus_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Time since stimOn | input[0] | Continuous, linspace(-0.5, 1.48, 100) | N/A | Time since stimulus onset |" (CONVERSION_NOTES.md:199); "`time_since_stim_onset`: shape (1, 100) per trial, values from -0.5 to 1.48 (center of each 20ms bin)" (CONVERSION_NOTES.md:207).

**Code** (convert_data.py:36-40, 461-467):
```python
ALIGN_TIME = 'stimOn_times'
TIME_WINDOW = (-0.5, 1.5)  # 2s trial
BINSIZE = 0.02  # 20ms
INTERVAL_LEN = TIME_WINDOW[1] - TIME_WINDOW[0]  # 2.0s
N_BINS = int(np.ceil(INTERVAL_LEN / BINSIZE))  # 100
...
        # 9. Build time input
        # Time since stimulus onset: center of each bin
        time_input = np.linspace(
            TIME_WINDOW[0] + BINSIZE / 2,
            TIME_WINDOW[1] - BINSIZE / 2,
            N_BINS
        ).astype(np.float32)
```

**What this does:** The conversion produces this input as `time_since_stim_onset` (`input_names[0]`, convert_data.py:689). No raw data field is read for it; it is generated from the constants `TIME_WINDOW = (-0.5, 1.5)` and `BINSIZE = 0.02`, which define the window taken around the raw `trials.stimOn_times` used for spike binning.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_stimulus_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Time since stimOn | input[0] | Continuous, linspace(-0.5, 1.48, 100) | N/A |" (CONVERSION_NOTES.md:199); "values from -0.5 to 1.48 (center of each 20ms bin)" (CONVERSION_NOTES.md:207).

**Code** (convert_data.py:461-482):
```python
        # 9. Build time input
        # Time since stimulus onset: center of each bin
        time_input = np.linspace(
            TIME_WINDOW[0] + BINSIZE / 2,
            TIME_WINDOW[1] - BINSIZE / 2,
            N_BINS
        ).astype(np.float32)
        ...
        input_list = []
        for i in range(n_trials):
            inp = np.stack([
                time_input,
                np.full(N_BINS, trial_num_in_block[i], dtype=np.float32)
            ], axis=0)  # (2, 100)
            input_list.append(inp)
```

**What this does:** One 100-element float32 vector is computed per session as `np.linspace(-0.49, 1.49, 100)`, i.e. bin centers spaced 0.02 s apart across the 2 s window. The same vector is stacked as row 0 of every trial's `(2, 100)` input array, identical across trials and sessions. (The notes describe the range as -0.5 to 1.48; the code uses bin centers -0.49 to 1.49.)

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_stimulus_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Alignment: stimOn_times for all, matching code + decoder task instructions" (CONVERSION_NOTES.md:217); metadata `temporal_alignment_event: 'stimulus onset (stimOn_times)'`, `off_start: -0.5`, `off_end: 1.5` (convert_data.py:700-702).

**Code** (convert_data.py:401-411, 461-467):
```python
        # 3. Compute trial intervals aligned to stimOn_times
        stim_on = trials[ALIGN_TIME].values
        interval_begs = stim_on + TIME_WINDOW[0]
        interval_ends = stim_on + TIME_WINDOW[1]

        # 4. Bin spikes for ALL trials first (before masking)
        binned_spikes = bin_spikes_vectorized(
            spike_times, spike_clusters, n_clusters, interval_begs, interval_ends
        )
        ...
        time_input = np.linspace(
            TIME_WINDOW[0] + BINSIZE / 2, TIME_WINDOW[1] - BINSIZE / 2, N_BINS
        ).astype(np.float32)
```

**What this does:** Alignment is by construction rather than by an explicit lookup: spikes are binned into `[stimOn_times - 0.5, stimOn_times + 1.5]` in 100 bins of 20 ms, and the time vector spans the same window with the same 100 entries, so entry *k* corresponds to neural bin *k*. Each entry is the center of its bin (neural bin *k* spans `[start + k*0.02, start + (k+1)*0.02)`).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *trial_number_in_block* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Trial number in block | input[1] | Count trials since last block change | From probabilityLeft | Per-trial value |" (CONVERSION_NOTES.md:200); "Block trial number: Computed as position within contiguous block of same probabilityLeft" (CONVERSION_NOTES.md:222).

**Code** (convert_data.py:441-455):
```python
        # 7. Extract per-trial variables
        trials_good = trials.iloc[good_indices]
        ...
        # Prior: probabilityLeft -> 0.2->0, 0.5->1, 0.8->2
        prob_left = trials_good['probabilityLeft'].values
        ...
        # Trial number in block
        trial_num_in_block = compute_trial_num_in_block(prob_left)
```

**What this does:** The conversion produces this input as `trial_num_in_block` (`input_names[1]`, convert_data.py:689). It is derived from the `probabilityLeft` column of the raw `_ibl_trials.table.pqt` trials table, read from the already-masked subset `trials_good` and its row ordering.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *trial_number_in_block*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Count trials since last block change ... Per-trial value" (CONVERSION_NOTES.md:200); "`trial_num_in_block`: shape (1,) per trial, integer count of trial within current block" (CONVERSION_NOTES.md:208); "Computed as position within contiguous block of same probabilityLeft" (CONVERSION_NOTES.md:222).

**Code** (convert_data.py:351-363, 442-455, 476-482):
```python
def compute_trial_num_in_block(prob_left):
    """Compute trial number within block.
    A block is a contiguous sequence of trials with the same probabilityLeft.
    Trial number resets to 1 at each block boundary."""
    trial_nums = np.ones(len(prob_left), dtype=np.int32)
    for i in range(1, len(prob_left)):
        if prob_left[i] == prob_left[i - 1]:
            trial_nums[i] = trial_nums[i - 1] + 1
        else:
            trial_nums[i] = 1
    return trial_nums
...
        trials_good = trials.iloc[good_indices]
        prob_left = trials_good['probabilityLeft'].values
        trial_num_in_block = compute_trial_num_in_block(prob_left)
...
            inp = np.stack([
                time_input,
                np.full(N_BINS, trial_num_in_block[i], dtype=np.float32)
            ], axis=0)  # (2, 100)
```

**What this does:** A running counter starts at 1 and increments while `probabilityLeft` is unchanged from the previous row, resetting to 1 when it changes. It is run on `trials_good`, the subset remaining after the trial-quality mask and the wheel/whisker availability masks have been applied, so excluded trials are not counted. The resulting per-trial integer is cast to float32 and broadcast with `np.full` across all 100 time bins as row 1 of the input array; no normalization or cap is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "choice → output[0]: Binary: -1(left)->0, 1(right)->1" (CONVERSION_NOTES.md:201)

**Code** (convert_data.py:444-446):
```python
# Choice: -1 (left) -> 0, 1 (right) -> 1
choice = trials_good['choice'].values.copy()
choice_binary = np.where(choice == 1, 1, 0).astype(np.int32)
```

**What this does:** Derived from the `choice` column of `_ibl_trials.table.pqt`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "choice: 0=left, 1=right (per-trial)" (README.md:49)

**Code** (convert_data.py:444-446, 487):
```python
choice = trials_good['choice'].values.copy()
choice_binary = np.where(choice == 1, 1, 0).astype(np.int32)
...
np.full(N_BINS, choice_binary[i], dtype=np.int64),
```

**What this does:** Maps -1 → 0 and 1 → 1, then broadcasts the per-trial scalar across all 100 time bins.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *prior_probability_left* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "probabilityLeft → output[1]: 0.2->0, 0.5->1, 0.8->2" (CONVERSION_NOTES.md:202)

**Code** (convert_data.py:448-452):
```python
# Prior: probabilityLeft -> 0.2->0, 0.5->1, 0.8->2
prob_left = trials_good['probabilityLeft'].values
prior = np.full(len(prob_left), 1, dtype=np.int32)  # default 0.5->1
prior[np.isclose(prob_left, 0.2, atol=0.05)] = 0
prior[np.isclose(prob_left, 0.8, atol=0.05)] = 2
```

**What this does:** Derived from the `probabilityLeft` column of the trials table.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *prior_probability_left*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "prior: 0=0.2, 1=0.5, 2=0.8 probabilityLeft (per-trial)" (README.md:50)

**Code** (convert_data.py:448-452, 488):
```python
prob_left = trials_good['probabilityLeft'].values
prior = np.full(len(prob_left), 1, dtype=np.int32)  # default 0.5->1
prior[np.isclose(prob_left, 0.2, atol=0.05)] = 0
prior[np.isclose(prob_left, 0.8, atol=0.05)] = 2
...
np.full(N_BINS, prior[i], dtype=np.int64),
```

**What this does:** Discretizes the continuous `probabilityLeft` to {0,1,2} using `np.isclose` with tolerance 0.05; broadcasts the per-trial scalar across all 100 time bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *wheel_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "wheel speed → output[2]: abs(velocity), discretize into 3 bins" (CONVERSION_NOTES.md:203); raw inputs: `_ibl_wheel.position.npy`, `_ibl_wheel.timestamps.npy` (CONVERSION_NOTES.md:25)

**Code** (convert_data.py:235-256):
```python
def load_wheel_speed(sdir):
    wh_pos = np.load(os.path.join(sdir, 'alf/_ibl_wheel.position.npy')).flatten()
    wh_times = np.load(os.path.join(sdir, 'alf/_ibl_wheel.timestamps.npy')).flatten()
    dt = 0.001  # 1kHz
    t_uniform = np.arange(wh_times[0], wh_times[-1], dt)
    pos_interp = np.interp(t_uniform, wh_times, wh_pos)
    velocity = np.gradient(pos_interp, dt)
    speed = np.abs(velocity)
    return t_uniform, speed
```

**What this does:** Derived from `_ibl_wheel.position.npy` and `_ibl_wheel.timestamps.npy`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *wheel_speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Discretization: Use session-wide terciles for wheel speed and whisker ME" (CONVERSION_NOTES.md:222)

**Code** (convert_data.py:245-256, 366-380, 458):
```python
t_uniform = np.arange(wh_times[0], wh_times[-1], dt)
pos_interp = np.interp(t_uniform, wh_times, wh_pos)
velocity = np.gradient(pos_interp, dt)
speed = np.abs(velocity)
...
def discretize_to_bins(values, n_bins=3):
    flat = values[~np.isnan(values)].flatten()
    quantiles = np.linspace(0, 100, n_bins + 1)[1:-1]
    boundaries = np.percentile(flat, quantiles)
    result = np.digitize(values, boundaries).astype(np.int32)
    return result
...
wheel_discrete = discretize_to_bins(wheel_trials, n_bins=3)
```

**What this does:** Position interpolated to uniform 1 kHz grid; `np.gradient` gives velocity; absolute value gives speed; speed is interpolated into per-trial 100-bin arrays then discretized into 3 session-wide tercile bins.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 7-c. How is `output` *wheel_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Aligned to stimOn_times same as neural (CONVERSION_NOTES.md:79-80, 217)

**Code** (convert_data.py:297-348, 414-419):
```python
def interpolate_behavior_to_bins(beh_times, beh_vals, interval_begs, interval_ends):
    ...
    x_interp = np.linspace(t_beg + BINSIZE, t_end, N_BINS)
    interp_func = interp1d(beh_t, beh_v, kind='linear', fill_value='extrapolate')
    values[trial_idx] = interp_func(x_interp).astype(np.float32)
    ...
wh_times, wh_speed = load_wheel_speed(sdir)
wheel_vals, wheel_mask = interpolate_behavior_to_bins(
    wh_times, wh_speed, interval_begs, interval_ends
)
```

**What this does:** Wheel speed is linearly interpolated onto the same per-trial bin centers used for spikes (interval_begs/ends derived from stimOn_times ± window). Trials lacking wheel coverage are masked out via `wheel_mask`, combined with the trial mask.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Whisker ME: tries left camera first, falls back to right" (CONVERSION_NOTES.md:73)

**Code** (convert_data.py:259-294):
```python
def load_whisker_me(sdir):
    ...
    left_me_files, left_time_files = _find_files(
        sdir, 'leftCamera.ROIMotionEnergy.npy', '_ibl_leftCamera.times.npy')
    if left_me_files and left_time_files:
        me = np.load(left_me_files[-1]).flatten()
        times = np.load(left_time_files[-1]).flatten()
        ...
    right_me_files, right_time_files = _find_files(
        sdir, 'rightCamera.ROIMotionEnergy.npy', '_ibl_rightCamera.times.npy')
    if right_me_files and right_time_files:
        me = np.load(right_me_files[-1]).flatten()
        ...
```

**What this does:** Derived from `leftCamera.ROIMotionEnergy.npy` (preferred) or `rightCamera.ROIMotionEnergy.npy`, paired with corresponding camera times files.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *whisker_motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "whisker ME → output[3]: Discretize into 3 bins" (CONVERSION_NOTES.md:204)

**Code** (convert_data.py:421-425, 459):
```python
me_times, me_vals_raw = load_whisker_me(sdir)
whisker_vals, whisker_mask = interpolate_behavior_to_bins(
    me_times, me_vals_raw, interval_begs, interval_ends
)
...
whisker_discrete = discretize_to_bins(whisker_trials, n_bins=3)
```

**What this does:** Raw motion energy values (truncated to min(len(me), len(times))) are linearly interpolated onto per-trial bin grids, then discretized into 3 session-wide tercile bins.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *whisker_motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Aligned same as neural via interpolation to stimOn-anchored bins.

**Code** (convert_data.py:421-425, 484-492):
```python
me_times, me_vals_raw = load_whisker_me(sdir)
whisker_vals, whisker_mask = interpolate_behavior_to_bins(
    me_times, me_vals_raw, interval_begs, interval_ends
)
...
out = np.stack([
    ...
    whisker_discrete[i].astype(np.int64)
], axis=0)  # (4, 100)
```

**What this does:** Interpolated onto the same `interval_begs/ends` (stimOn ± window) as neural; trials are filtered by `whisker_mask` ANDed with the trial/wheel masks so per-trial indexing matches neural.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Graceful handling of missing data (skips sessions without wheel/whisker data)" (CONVERSION_NOTES.md:242); "Sessions failed (missing data): 57 (all PL050/hausserlab - missing wheel data)" (CONVERSION_NOTES.md:299)

**Code** (convert_data.py:62-77, 116-126, 208-209, 327-337, 432-435, 517-521):
```python
has_spikes = len(glob.glob(os.path.join(sdir, 'alf/probe*/pykilosort/*/spikes.times.npy'))) > 0
...
if has_spikes and has_trials and has_wheel and has_me:
    valid.append(sdir)
...
for col in NAN_EXCLUDE:
    if col in trials.columns:
        mask &= ~trials[col].isna()
...
if np.isnan(t_beg) or np.isnan(t_end):
    continue
...
if np.abs(t_beg - beh_t[0]) > BINSIZE:
    mask[trial_idx] = False
    continue
...
if len(good_indices) < 2:
    print(f"  WARNING: Only {len(good_indices)} valid trials, skipping session", flush=True)
    return None
...
except Exception as e:
    print(f"  ERROR processing {session_id}: {e}", flush=True)
    traceback.print_exc()
    return None
```

**What this does:** Sessions without required files are skipped at discovery; trials with NaN key events are masked out; trial intervals with NaN endpoints or insufficient behavior coverage are masked; sessions with <2 valid trials or any unhandled exception are skipped (return None) with a logged warning.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Spike binning 0.2-0.3s; Wheel/whisker 0.5-1s; Total per session ~2.5s" (CONVERSION_NOTES.md:269-272)

**Code** (convert_data.py:407-412, 415-425):
```python
print(f"  Binning spikes ({n_clusters} neurons, {len(trials)} trials)...", flush=True)
t_bin = time.time()
binned_spikes = bin_spikes_vectorized(
    spike_times, spike_clusters, n_clusters, interval_begs, interval_ends
)
print(f"  Spike binning: {time.time() - t_bin:.1f}s", flush=True)
...
print(f"  Loading wheel speed...", flush=True)
wh_times, wh_speed = load_wheel_speed(sdir)
wheel_vals, wheel_mask = interpolate_behavior_to_bins(
    wh_times, wh_speed, interval_begs, interval_ends
)
```

**What this does:** Hot paths are spike binning (per-trial loop with searchsorted+bincount) and behavior interpolation (per-trial interp1d construction). Notes report ~0.2–0.3s for binning and ~0.5–1s for wheel/whisker per session.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none — function named 'bin_spikes_vectorized' but still loops over trials)"

**Code** (convert_data.py:204-232, 312-348, 358-362):
```python
for trial_idx in range(n_trials):
    t_beg = interval_begs[trial_idx]
    t_end = interval_ends[trial_idx]
    ...
    i_start = np.searchsorted(spike_times, t_beg, side='left')
    ...
    counts = np.bincount(flat_idx, minlength=n_clusters * N_BINS)
    binned[trial_idx] = counts[:n_clusters * N_BINS].reshape(n_clusters, N_BINS)
...
for trial_idx in range(n_trials):
    ...
    interp_func = interp1d(beh_t, beh_v, kind='linear', fill_value='extrapolate')
    values[trial_idx] = interp_func(x_interp).astype(np.float32)
...
for i in range(1, len(prob_left)):
    if prob_left[i] == prob_left[i - 1]:
        trial_nums[i] = trial_nums[i - 1] + 1
```

**What this does:** Per-trial loops in `bin_spikes_vectorized`, `interpolate_behavior_to_bins`, and `compute_trial_num_in_block` could potentially be vectorized (e.g., one searchsorted call across all trial boundaries; np.where on prob_left changes). The output assembly loops at lines 474-492 also build per-trial arrays one at a time.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:143, 613, 312-348):
```python
br = BrainRegions()       # inside load_spikes (called per session)
...
br = BrainRegions()       # also instantiated in main()
...
for trial_idx in range(n_trials):
    ...
    interp_func = interp1d(beh_t, beh_v, kind='linear', fill_value='extrapolate')
```

**What this does:** `BrainRegions()` is instantiated both in `main()` and inside `load_spikes` (called per session); the `main`-level `br` is never passed to `load_spikes`. A new `interp1d` object is built per trial inside `interpolate_behavior_to_bins`. Mask construction iterates NaN_EXCLUDE columns sequentially.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reduced pickle: `converted_data_reduced.pkl` (7.4 GB); 318 of 335 sessions had neurons subsampled" (CONVERSION_NOTES.md:354)

**Code** (convert_data.py:406-412, 469-474):
```python
# 4. Bin spikes for ALL trials first (before masking)
binned_spikes = bin_spikes_vectorized(
    spike_times, spike_clusters, n_clusters, interval_begs, interval_ends
)
...
# Store as uint8 during accumulation to save memory (spike counts rarely exceed 255)
neural_list = [np.clip(neural_trials[i], 0, 255).astype(np.uint8) for i in range(n_trials)]
```

**What this does:** Spikes are binned for all trials including those later masked out by `combined_mask`. All neurons (~1,400/session) are kept though `reduce_data.py` later subsamples to ≤500. The full 21 GB pickle is produced even though training uses the reduced 7.4 GB version.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural data stored as uint8 (spike counts rarely exceed 255) to reduce memory; Incremental building with `gc.collect()` after each session; Memory monitoring via `resource.getrusage`" (CONVERSION_NOTES.md:240-241)

**Code** (convert_data.py:180-187, 472-474, 636-652, 679):
```python
merged_times = np.concatenate(all_spike_times)
del all_spike_times
merged_clusters = np.concatenate(all_spike_clusters)
del all_spike_clusters
...
neural_list = [np.clip(neural_trials[i], 0, 255).astype(np.uint8) for i in range(n_trials)]
...
if result is not None:
    neural.append(result['neural'])
    ...
    del result  # free memory immediately
gc.collect()
if (i + 1) % 50 == 0:
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
    print(f"  [Memory] RSS: {rss:.0f} MB after {n_success} sessions", flush=True)
...
del cluster_regions_per_session
```

**What this does:** Intermediate arrays are `del`-ed after concatenation; per-trial neural arrays stored as uint8 (clipped at 255); per-session `result` deleted and `gc.collect()` called each iteration; RSS logged every 50 sessions; large lists deleted before pickling.

**Rating:** match

**Note:** _(no note)_---

---
