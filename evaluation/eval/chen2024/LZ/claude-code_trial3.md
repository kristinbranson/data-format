# map — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/map/claude/2026-03-22__18-40-41_trial3/verifier/snapshot/`

Outputs identified (K=4): choice, outcome, early_lick, tongue_y

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "NWB files organized by subject directories: `data/sub-XXXXXX/`. Each NWB file = one behavioral session..." (CONVERSION_NOTES.md:57-59)

**Code** (convert_data.py:291-302, 807-808, 829-848):
```python
def list_nwb_files(data_dir):
    subjects = sorted([d for d in os.listdir(data_dir)
                      if os.path.isdir(os.path.join(data_dir, d)) and d.startswith('sub-')])
    all_files = []
    for sub in subjects:
        sub_dir = os.path.join(data_dir, sub)
        nwb_files = sorted([os.path.join(sub_dir, f)
                           for f in os.listdir(sub_dir) if f.endswith('.nwb')])
        for nwb_file in nwb_files:
            all_files.append((sub, nwb_file))
    return all_files
...
all_files = list_nwb_files(DATA_DIR)
...
for i, (subject, nwb_path) in enumerate(all_files):
    result = process_session(nwb_path, ...)
```

**What this does:** Lists `sub-*` directories, collects all `.nwb` files per subject, then iterates and processes each NWB file (one session) sequentially via `process_session`.

**Rating:** match

**Note:** _(no note)_---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "NWB files organized by subject directories: `data/sub-XXXXXX/`" (CONVERSION_NOTES.md:58)

**Code** (convert_data.py:354, 718-725, 754-755):
```python
subject_id = nwb.subject.subject_id if nwb.subject else os.path.basename(nwb_path).split('_')[0]
...
subjects = []
subject_idx = []
for sess in session_results:
    if sess['subject_id'] not in subjects:
        subjects.append(sess['subject_id'])
    subject_idx.append(subjects.index(sess['subject_id']))
...
'subjects': subjects,
'subject_idx': np.array(subject_idx),
```

**What this does:** Subject ID is read from each NWB file's `subject.subject_id`. A unique-subject list and per-session subject index array are built and stored as `subjects` / `subject_idx`.

**Rating:** match

**Note:** _(no note)_---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Each NWB file = one behavioral session with behavior + ecephys + (usually) ogen data" (CONVERSION_NOTES.md:58)

**Code** (convert_data.py:341-355, 738-741):
```python
def process_session(nwb_path, show_processing=False, session_idx=0):
    io = pynwb.NWBHDF5IO(nwb_path, 'r')
    nwb = io.read()
    ...
    session_id = nwb.identifier
...
for sess in session_results:
    neural.append(sess['neural_trials'])
    inputs.append(sess['input_trials'])
    outputs.append(sess['output_trials'])
```

**What this does:** Each NWB file is treated as one session; `process_session` returns a per-session dict, and the final `neural`/`input`/`output` are lists indexed by session.

**Rating:** concerning

**Note:** _(no note)_---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "trials: start_time, stop_time, trial_instruction (left/right), early_lick, outcome (hit/miss/ignore), auto_water, free_water, photostim_onset/power/duration" (CONVERSION_NOTES.md:62-63)

**Code** (convert_data.py:360-376, 498-505):
```python
trials = nwb.trials
n_trials = len(trials)
trial_starts = trials['start_time'][:]
trial_stops = trials['stop_time'][:]
...
go_times = be.time_series['go_start_times'].timestamps[:]
assert len(go_times) == n_trials, f"Go times ({len(go_times)}) != trials ({n_trials})"
...
for trial_idx in valid_indices:
    go_time = go_times[trial_idx]
    fr = compute_firing_rates_vectorized(
        spike_times_good, go_time, T_START, T_END, BIN_WIDTH, N_BINS
    )
    neural_trials.append(fr)
```

**What this does:** Trials are taken from `nwb.trials` table; each trial gets its go-cue time from `BehavioralEvents.go_start_times`. Asserts length match. A per-trial window [-2.5, +1.5]s around go cue defines each trial.

**Rating:** match

**Note:** _(no note)_---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial filtering: Excludes only auto_water and free_water trials." (README.md:53). "For decoder task, we KEEP early lick, ignore, and stimulation trials" (CONVERSION_NOTES.md:131-133). Session selection: ">65% correct rate, >=50 correct left and right trials" (README.md:52).

**Code** (convert_data.py:392-421, 440-455):
```python
behav_valid = (auto_water == 0) & (free_water == 0)
regular_mask = behav_valid.copy()
for i in range(n_trials):
    if photostim_onset[i] != 'N/A':
        regular_mask[i] = False
    if early_licks[i] == 'early':
        regular_mask[i] = False
regular_mask &= (outcomes != 'ignore')
...
correct_rate = correct_regular / n_regular
if correct_rate < MIN_CORRECT_RATE: ... return None
if correct_left < MIN_CORRECT_LEFT or correct_right < MIN_CORRECT_RIGHT: ... return None
...
valid_mask = behav_valid.copy()
valid_mask &= ~np.isnan(tone_onset_per_trial)
for i in range(n_trials):
    trial_end_abs = go_times[i] + T_END
    if trial_end_abs > max_recording_time + 1.0:
        valid_mask[i] = False
```

**What this does:** Sessions skipped if correct rate <65% or fewer than 50 correct left/right. Trials excluded if auto_water/free_water, missing tone onset, or beyond neural recording coverage. Early lick/photostim/ignore trials are kept.

**Rating:** match

**Note:** _(no note)_---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "units.spike_times -> neural; Filter by classification=='good', align to go cue" (CONVERSION_NOTES.md:175)

**Code** (convert_data.py:424-460):
```python
units = nwb.units
classification = units['classification'][:]
good_mask_units = classification == 'good'
anno_names = units['anno_name'][:]
good_mask_units &= np.array([a != '' and a is not None for a in anno_names])
good_indices_units = np.where(good_mask_units)[0]
...
spike_times_all = units['spike_times']
spike_times_good = [spike_times_all[idx] for idx in good_indices]
```

**What this does:** Neural data derives from NWB `units.spike_times`, filtered by `units.classification=='good'` and non-empty `units.anno_name`, with go-cue times from `BehavioralEvents.go_start_times`.

**Rating:** match

**Note:** _(no note)_---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Bin into 50ms windows, compute firing rate" (CONVERSION_NOTES.md:175). "Bin size: 50ms (80 time bins per trial)" (README.md:50).

**Code** (convert_data.py:305-338):
```python
def compute_firing_rates_vectorized(spike_times_list, go_time, t_start, t_end, bin_width, n_bins):
    n_neurons = len(spike_times_list)
    fr = np.zeros((n_neurons, n_bins), dtype=np.float32)
    bin_edges_start = go_time + t_start + np.arange(n_bins) * bin_width
    ...
    for i, spk in enumerate(spike_times_list):
        if len(spk) == 0:
            continue
        mask = (spk >= go_time + t_start) & (spk < go_time + t_end)
        spk_window = spk[mask]
        if len(spk_window) == 0:
            continue
        bin_idx = np.floor((spk_window - (go_time + t_start)) / bin_width).astype(int)
        bin_idx = np.clip(bin_idx, 0, n_bins - 1)
        np.add.at(fr[i], bin_idx, 1)
    fr /= bin_width
    return fr
```

**What this does:** Per trial and per neuron: spikes are masked to the window, indexed into 50ms non-overlapping bins via floor division, accumulated with `np.add.at`, then divided by bin width to get Hz.

**Rating:** match

**Note:** _(no note)_---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neuron QC: classification == 'good' (QC classifier-based)" (README.md:51); "QC classifier: classification == 'good' in NWB. Must have both ephys and histology (CCF coordinates). anno_name must not be empty" (CONVERSION_NOTES.md:124-127).

**Code** (convert_data.py:425-434):
```python
units = nwb.units
classification = units['classification'][:]
good_mask_units = classification == 'good'
anno_names = units['anno_name'][:]
good_mask_units &= np.array([a != '' and a is not None for a in anno_names])
good_indices_units = np.where(good_mask_units)[0]
if len(good_indices_units) == 0:
    print(f'  SKIP: no good neurons')
    io.close()
    return None
```

**What this does:** Keeps only units with `classification == 'good'` and non-empty `anno_name`; sessions with no surviving neurons are skipped.

**Rating:** match

**Note:** _(no note)_---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Bin size: 50ms (80 time bins per trial)" (README.md:50); "Time window: [-2.5, +1.5]s relative to go cue" (README.md:49).

**Code** (convert_data.py:25-29, 321-337):
```python
BIN_WIDTH = 0.05  # 50 ms bins (decoder task spec)
T_START = -2.5
T_END = 1.5
N_BINS = int((T_END - T_START) / BIN_WIDTH)  # 80 bins
...
bin_edges_start = go_time + t_start + np.arange(n_bins) * bin_width
...
bin_idx = np.floor((spk_window - (go_time + t_start)) / bin_width).astype(int)
bin_idx = np.clip(bin_idx, 0, n_bins - 1)
np.add.at(fr[i], bin_idx, 1)
fr /= bin_width
```

**What this does:** Non-overlapping 50ms bins over [-2.5, +1.5]s relative to go cue (80 bins); spike counts per bin are divided by bin width to give Hz.

**Rating:** match

**Note:** _(no note)_---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: Go cue onset" (convert_data.py:769); "Spike times already aligned to go cue in source data... In NWB: spike times in absolute time, need to subtract go_start_time per trial" (CONVERSION_NOTES.md:117-118).

**Code** (convert_data.py:373-376, 498-505):
```python
be = nwb.acquisition['BehavioralEvents']
go_times = be.time_series['go_start_times'].timestamps[:]
assert len(go_times) == n_trials, f"Go times ({len(go_times)}) != trials ({n_trials})"
...
for trial_idx in valid_indices:
    go_time = go_times[trial_idx]
    fr = compute_firing_rates_vectorized(
        spike_times_good, go_time, T_START, T_END, BIN_WIDTH, N_BINS
    )
```

**What this does:** Per trial, `go_time` is read from `go_start_times` and used as t=0; firing rates are binned over absolute spike times within `[go_time + T_START, go_time + T_END]`.

**Rating:** match

**Note:** _(no note)_---

## Q 3-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "trial_instruction + outcome -> output[0]: choice; left=0, right=1; hit: choice=instruction; miss: choice=opposite; ignore: choice=instruction" (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:364-365, 540-547):
```python
instructions = trials['trial_instruction'][:]  # 'left' or 'right'
outcomes = trials['outcome'][:]  # 'hit', 'miss', 'ignore'
...
instr = instructions[trial_idx]
outcome = outcomes[trial_idx]
if outcome == 'hit':
    choice = 0 if instr == 'left' else 1
elif outcome == 'miss':
    choice = 1 if instr == 'left' else 0
else:  # ignore
    choice = 0 if instr == 'left' else 1
```

**What this does:** Choice is derived from `trials.trial_instruction` combined with `trials.outcome` (hit/miss/ignore).

**Rating:** match

**Note:** _(no note)_---

## Q 3-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Choice for ignore trials: Set to instruction direction (the 'correct' choice), since there's no actual lick" (CONVERSION_NOTES.md:194).

**Code** (convert_data.py:540-547, 575-580):
```python
if outcome == 'hit':
    choice = 0 if instr == 'left' else 1
elif outcome == 'miss':
    choice = 1 if instr == 'left' else 0
else:  # ignore
    choice = 0 if instr == 'left' else 1
...
output_data = np.array([
    np.full(N_BINS, choice, dtype=np.int64),
    ...
])
```

**What this does:** Maps left/right to 0/1; on miss flips to opposite of instruction; on ignore assigns instruction direction. The scalar choice is broadcast to all 80 bins of the trial.

**Rating:** concerning

**Note:** _(no note)_---

## Q 3-c. How is `output` *choice* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:575-581):
```python
output_data = np.array([
    np.full(N_BINS, choice, dtype=np.int64),
    np.full(N_BINS, outcome_val, dtype=np.int64),
    np.full(N_BINS, early_val, dtype=np.int64),
    tongue_y_trial.astype(np.int64),
], dtype=np.int64)  # (4, n_bins)
output_trials.append(output_data)
```

**What this does:** Choice is assigned per trial and replicated across all N_BINS=80 bins, matching the neural array's time-bin axis (sharing the same go-cue-aligned trial window).

**Rating:** _(to be filled by evaluator)_

**Note:** _(no note)_---

## Q 4-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "outcome -> output[1]: outcome; ignore=0, miss=1, hit=2; Direct mapping from NWB" (CONVERSION_NOTES.md:179)

**Code** (convert_data.py:365, 549-550):
```python
outcomes = trials['outcome'][:]  # 'hit', 'miss', 'ignore'
...
outcome_val = {'ignore': 0, 'miss': 1, 'hit': 2}[outcome]
```

**What this does:** Derived directly from `trials.outcome`.

**Rating:** match

**Note:** _(no note)_---

## Q 4-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Direct mapping from NWB" (CONVERSION_NOTES.md:179).

**Code** (convert_data.py:549-550, 577):
```python
outcome_val = {'ignore': 0, 'miss': 1, 'hit': 2}[outcome]
...
np.full(N_BINS, outcome_val, dtype=np.int64),
```

**What this does:** Categorical string mapped to integer 0/1/2 and broadcast to all bins.

**Rating:** match

**Note:** _(no note)_---

## Q 4-c. How is `output` *outcome* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:577):
```python
np.full(N_BINS, outcome_val, dtype=np.int64),
```

**What this does:** Per-trial scalar broadcast to all 80 time bins, matching the neural array's bin axis on the same per-trial go-cue-aligned window.

**Rating:** _(to be filled by evaluator)_

**Note:** _(no note)_---

## Q 5-a. What variables in the raw data is `output` *early_lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "early_lick -> output[2]: early_lick; no=0, yes=1; Direct mapping from NWB" (CONVERSION_NOTES.md:180)

**Code** (convert_data.py:366, 552-553):
```python
early_licks = trials['early_lick'][:]  # 'early' or 'no early'
...
early_val = 0 if early_licks[trial_idx] == 'no early' else 1
```

**What this does:** Derived directly from `trials.early_lick`.

**Rating:** match

**Note:** _(no note)_---

## Q 5-b. What processing is involved in computing `output` *early_lick*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Direct mapping from NWB" (CONVERSION_NOTES.md:180).

**Code** (convert_data.py:552-553, 578):
```python
early_val = 0 if early_licks[trial_idx] == 'no early' else 1
...
np.full(N_BINS, early_val, dtype=np.int64),
```

**What this does:** String 'no early' -> 0, otherwise 1; broadcast across all bins.

**Rating:** match

**Note:** _(no note)_---

## Q 5-c. How is `output` *early_lick* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:578):
```python
np.full(N_BINS, early_val, dtype=np.int64),
```

**What this does:** Per-trial scalar replicated across all 80 bins of the go-cue-aligned trial window.

**Rating:** _(to be filled by evaluator)_

**Note:** _(no note)_---

## Q 6-a. What variables in the raw data is `output` *tongue_y* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "TongueTracking y -> output[3]: tongue_y; Discretized per-session (0/1/2); 40th/60th percentile thresholds" (CONVERSION_NOTES.md:181)

**Code** (convert_data.py:474-480):
```python
bts = nwb.acquisition['BehavioralTimeSeries']
has_tongue = 'Camera0_side_TongueTracking' in bts.time_series
if has_tongue:
    tongue_data = bts.time_series['Camera0_side_TongueTracking'].data[:]  # (n_frames, 3): x, y, likelihood
    tongue_ts = bts.time_series['Camera0_side_TongueTracking'].timestamps[:]
    tongue_y = tongue_data[:, 1]
    tongue_likelihood = tongue_data[:, 2]
```

**What this does:** Derived from `BehavioralTimeSeries['Camera0_side_TongueTracking']` y-coordinate (channel 1) plus likelihood (channel 2) and its timestamps.

**Rating:** match

**Note:** _(no note)_---

## Q 6-b. What processing is involved in computing `output` *tongue_y*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Discretize per session using 40th/60th percentile thresholds over ALL valid tongue positions in the session" (CONVERSION_NOTES.md:195).

**Code** (convert_data.py:484-493, 556-571):
```python
if has_tongue:
    tongue_visible = tongue_likelihood > 0.5
    if np.sum(tongue_visible) > 100:
        visible_y = tongue_y[tongue_visible]
        p40 = np.percentile(visible_y, 40)
        p60 = np.percentile(visible_y, 60)
    else:
        p40 = np.percentile(tongue_y, 40)
        p60 = np.percentile(tongue_y, 60)
...
for b in range(N_BINS):
    bc_abs = go_time + bin_centers[b]
    t_idx = np.searchsorted(tongue_ts, bc_abs)
    t_idx = min(t_idx, len(tongue_ts) - 1)
    ty = tongue_y[t_idx]
    if ty < p40: tongue_y_trial[b] = 0
    elif ty < p60: tongue_y_trial[b] = 1
    else: tongue_y_trial[b] = 2
```

**What this does:** Computes 40th/60th percentiles of tongue y over all visible (likelihood>0.5) frames in the session; per bin samples the nearest tongue frame and assigns 0/1/2 by thresholds.

**Rating:** concerning

**Note:** _(no note)_---

## Q 6-c. How is `output` *tongue_y* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:495-496, 558-562, 579):
```python
bin_centers = T_START + np.arange(N_BINS) * BIN_WIDTH + BIN_WIDTH / 2
...
for b in range(N_BINS):
    bc_abs = go_time + bin_centers[b]
    t_idx = np.searchsorted(tongue_ts, bc_abs)
    t_idx = min(t_idx, len(tongue_ts) - 1)
    ty = tongue_y[t_idx]
...
tongue_y_trial.astype(np.int64),
```

**What this does:** For each go-cue-aligned bin center, finds the tongue tracking frame at the matching absolute time via `searchsorted`, producing a length-80 sequence aligned to the same bins as `neural`.

**Rating:** match

**Note:** _(no note)_---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Zero-neural-data trials: 126/74894 (0.17%) - negligible edge cases from recording coverage boundaries" (CONVERSION_NOTES.md:298). "All unmapped annotations fall back to OtherCortex (reasonable default)" (CONVERSION_NOTES.md:299).

**Code** (convert_data.py:282-284, 382-388, 442-448, 475-571, 833-846):
```python
# unmapped CCF annotation fallback
print(f'  WARNING: Unmapped annotation: "{anno_name}"')
return 'OtherCortex'
...
# missing tone onset -> NaN; trial later excluded
tone_onset_per_trial = np.full(n_trials, np.nan)
for i in range(n_trials):
    in_trial = sample_starts[(sample_starts >= trial_starts[i]) & (sample_starts <= go_times[i])]
    if len(in_trial) > 0:
        tone_onset_per_trial[i] = in_trial[-1]
...
valid_mask &= ~np.isnan(tone_onset_per_trial)
for i in range(n_trials):
    trial_end_abs = go_times[i] + T_END
    if trial_end_abs > max_recording_time + 1.0:
        valid_mask[i] = False
...
# missing tongue tracking
if has_tongue: ...
else:
    tongue_y_trial = np.ones(N_BINS, dtype=np.float32)  # default to middle
...
# session-level errors
try:
    result = process_session(nwb_path, ...)
except Exception as e:
    print(f'  ERROR: {e}')
    n_skipped += 1
    continue
```

**What this does:** Trials with missing tone onset or beyond recording coverage are dropped; sessions without good neurons are skipped; unmapped CCF annotations default to 'OtherCortex'; sessions without tongue tracking default tongue_y to mid (1); session-level exceptions are caught and that session skipped.

**Rating:** match

**Note:** _(no note)_---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "~5-10s per session, ~30 min total for full conversion" (CONVERSION_NOTES.md:239).

**Code** (convert_data.py:457-505, 555-569):
```python
spike_times_all = units['spike_times']
spike_times_good = [spike_times_all[idx] for idx in good_indices]
...
for trial_idx in valid_indices:
    fr = compute_firing_rates_vectorized(
        spike_times_good, go_time, T_START, T_END, BIN_WIDTH, N_BINS
    )
...
for b in range(N_BINS):
    bc_abs = go_time + bin_centers[b]
    t_idx = np.searchsorted(tongue_ts, bc_abs)
```

**What this does:** Per-trial firing rate computation (loops over trials and within over neurons) and per-bin tongue lookups dominate; reading all `spike_times` from HDF5 also has I/O cost. Final pickle write of ~10 GB is also significant.

**Rating:** ok

**Note:** _(no note)_---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:382-388, 396-401, 444-448, 498-505, 531-534, 558-569):
```python
for i in range(n_trials):
    in_trial = sample_starts[(sample_starts >= trial_starts[i]) & (sample_starts <= go_times[i])]
...
for i in range(n_trials):
    if photostim_onset[i] != 'N/A': regular_mask[i] = False
    if early_licks[i] == 'early': regular_mask[i] = False
...
for trial_idx in valid_indices:
    fr = compute_firing_rates_vectorized(
        spike_times_good, go_time, T_START, T_END, BIN_WIDTH, N_BINS
    )
...
for b in range(N_BINS):
    bc = bin_centers[b]
    if ps_onset_rel <= bc < ps_end_rel:
        photostim[b] = 1.0
...
for b in range(N_BINS):
    t_idx = np.searchsorted(tongue_ts, bc_abs)
```

**What this does:** Several Python-level loops iterate per trial or per bin (tone-onset search, regular_mask construction, firing rates per trial, photostim window, tongue lookup) where vectorized numpy operations across trials/bins would be possible.

**Rating:** ok

**Note:** _(no note)_---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:495-505):
```python
bin_centers = T_START + np.arange(N_BINS) * BIN_WIDTH + BIN_WIDTH / 2
for trial_idx in valid_indices:
    go_time = go_times[trial_idx]
    fr = compute_firing_rates_vectorized(
        spike_times_good, go_time, T_START, T_END, BIN_WIDTH, N_BINS
    )
```

**What this does:** `compute_firing_rates_vectorized` re-masks all spikes per neuron per trial (so each spike is examined many times across trials). `bin_centers` arithmetic and per-bin tongue searches recur every trial.

**Rating:** ok

**Note:** _(no note)_---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:362-363, 601-711):
```python
trial_stops = trials['stop_time'][:]
...
def make_processing_plots(session_data, session_idx, nwb_path):
    ...
```

**What this does:** `trial_stops` is read but not used. Plot generation runs only when `--show-processing` is set; otherwise no plots. `tone_relative` array is built per trial but only used as input[0]. Some computed stats (e.g., per-session correct rates) are not stored in the final pickle.

**Rating:** match

**Note:** _(no note)_---

## Q 8-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "converted_data.pkl (9977.5 MB)" (CONVERSION_NOTES.md:262).

**Code** (convert_data.py:320, 513, 583, 911-912):
```python
fr = np.zeros((n_neurons, n_bins), dtype=np.float32)
...
photostim = np.zeros(N_BINS, dtype=np.float32)
...
io.close()
...
with open(args.outfile, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** Firing rates use float32; NWB IO is closed after each session; sessions are processed one at a time. No explicit caching of large intermediates; the final pickle is ~10 GB and written in one pass with pickle protocol 4.

**Rating:** match

**Note:** _(no note)_---
