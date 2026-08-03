# map — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/map/claude/2026-03-22__21-13-57_trial2/verifier/snapshot/`

Outputs identified (K=4): choice, outcome, early_lick, tongue_y_position

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "NWB files organized by subject (sub-XXXXXX directories) / Each NWB file = one session" (CONVERSION_NOTES.md:62-64)

**Code** (convert_data.py:150-159, 608-632):
```python
def get_nwb_files(data_dir):
    """Get list of all NWB files organized by subject."""
    subjects = sorted([d for d in os.listdir(data_dir) if d.startswith('sub-')])
    nwb_files = []
    for subj in subjects:
        subj_dir = os.path.join(data_dir, subj)
        files = sorted([f for f in os.listdir(subj_dir) if f.endswith('.nwb')])
        for fname in files:
            nwb_files.append((subj, os.path.join(subj_dir, fname)))
    return nwb_files
...
nwb_files = get_nwb_files(DATA_DIR)
...
for i, (subject_id, nwb_path) in enumerate(nwb_files):
    result = process_session(nwb_path, subject_id)
```

**What this does:** Walks `/app/data` for `sub-*` directories, collects all `.nwb` files, then iterates serially calling `process_session` on each via `NWBHDF5IO`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "subject_id | subjects/subject_idx | Subject names | N/A | From NWB metadata" (CONVERSION_NOTES.md:181)

**Code** (convert_data.py:622, 638-645, 671-672):
```python
subjects_seen = {}
...
if subject_id not in subjects_seen:
    subjects_seen[subject_id] = len(subjects_seen)
    subjects_list.append(subject_id)
subj_idx = subjects_seen[subject_id]
...
subject_idx_list.append(subj_idx)
...
'subjects': subjects_list,
'subject_idx': np.array(subject_idx_list, dtype=np.int64),
```

**What this does:** Subject identity is taken from the parent directory name (`sub-XXXXXX`) returned by `get_nwb_files`. A dict assigns a unique integer to each new subject; `subject_idx` is recorded per session.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Each NWB file = one session" (CONVERSION_NOTES.md:64)

**Code** (convert_data.py:617, 644, 666-669):
```python
all_sessions = []
...
all_sessions.append(result)
...
data = {
    'neural': [s['neural'] for s in all_sessions],
    'input': [s['input'] for s in all_sessions],
    'output': [s['output'] for s in all_sessions],
```

**What this does:** Each NWB file is treated as a separate session. `all_sessions` is a list parallel across `neural`, `input`, `output`; the outer list dimension corresponds to sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "trials: start_time, stop_time, trial_instruction (left/right), early_lick, outcome..." (CONVERSION_NOTES.md:65)

**Code** (convert_data.py:374-381, 416-421):
```python
trials = nwb.trials
outcomes = trials['outcome'][:]
instructions = trials['trial_instruction'][:]
early_lick = trials['early_lick'][:]
auto_water = trials['auto_water'][:]
free_water = trials['free_water'][:]
...
for ti in trial_indices:
    go_cue = go_start_times[ti]
    fr = compute_firing_rates(spike_times_per_unit, go_cue, T_START, T_END, BIN_SIZE_S)
    neural_trials.append(fr)
```

**What this does:** Trials come from the NWB `trials` table. Each trial is processed by indexing per-trial arrays with `ti` and using its `go_start_time` to extract a -2.5..1.5 s window for neural and behavioral signals.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "EXCLUDE: auto_water, free_water (confound behavior, not decoder variables)" (CONVERSION_NOTES.md:140); "obs_intervals filtering: Properly excludes trials outside recording periods" (CONVERSION_NOTES.md:328)

**Code** (convert_data.py:287-317, 398-408):
```python
def get_valid_trial_indices(nwb, good_unit_indices, n_trials):
    trial_starts = nwb.trials['start_time'][:]
    obs_sets = {}
    for idx in good_unit_indices:
        obs = nwb.units['obs_intervals'][idx]
        ...
    valid_trials = np.ones(n_trials, dtype=bool)
    for n_obs, obs in obs_sets.items():
        obs_starts = obs[:, 0]
        diffs = np.abs(trial_starts[:, None] - obs_starts[None, :])
        min_diffs = diffs.min(axis=1)
        covered = min_diffs < 1.0
        valid_trials &= covered
    return np.where(valid_trials)[0]
...
trial_mask = (auto_water == 0) & (free_water == 0)
recording_mask = np.zeros(n_trials_total, dtype=bool)
recording_mask[valid_trial_idx] = True
trial_mask = trial_mask & recording_mask
trial_indices = np.where(trial_mask)[0]
if len(trial_indices) < 2:
    return None
```

**What this does:** Excludes trials with `auto_water` or `free_water` set, and trials whose start_time is not within 1 s of any unit's `obs_intervals` start (i.e., outside the recording period). Sessions with fewer than 2 trials remaining are skipped.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "units.spike_times (good) | neural | Align to go cue, bin at 50ms, -2.5 to 1.5s" (CONVERSION_NOTES.md:173)

**Code** (convert_data.py:331-340, 368-372, 384):
```python
classification = nwb.units['classification'][:]
good_mask = np.array([c == 'good' for c in classification])
...
anno_names = nwb.units['anno_name'][:][good_mask]
...
spike_times_per_unit = []
for idx in good_unit_indices:
    st = nwb.units['spike_times'][idx]
    spike_times_per_unit.append(st)
...
go_start_times = events.time_series['go_start_times'].timestamps[:]
```

**What this does:** Neural data derives from `nwb.units['spike_times']` for units with `classification == 'good'` and a mappable `anno_name`, aligned by `go_start_times` from `BehavioralEvents`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Spike binning: 50ms non-overlapping bins (per task spec)" (CONVERSION_NOTES.md:203)

**Code** (convert_data.py:162-197):
```python
def compute_firing_rates(spike_times_list, go_cue_time, t_start, t_end, bin_size):
    n_neurons = len(spike_times_list)
    n_bins = int((t_end - t_start) / bin_size)
    fr = np.zeros((n_neurons, n_bins), dtype=np.float32)
    abs_start = go_cue_time + t_start
    abs_end = go_cue_time + t_end
    for i, st in enumerate(spike_times_list):
        if len(st) == 0:
            continue
        mask = (st >= abs_start) & (st < abs_end)
        spikes_in_window = st[mask]
        if len(spikes_in_window) == 0:
            continue
        bin_indices = ((spikes_in_window - abs_start) / bin_size).astype(int)
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)
        np.add.at(fr[i], bin_indices, 1.0)
    fr /= bin_size
    return fr
```

**What this does:** Per trial, spikes within [go_cue-2.5, go_cue+1.5) are histogrammed into 50 ms bins for each unit and divided by bin width to get firing rate (Hz). Result shape per trial is (n_neurons, 80).

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Neurons: classification=='good' only (all have anno_name). No firing rate threshold (2 Hz was analysis-specific)." (CONVERSION_NOTES.md:201)

**Code** (convert_data.py:331-362):
```python
classification = nwb.units['classification'][:]
good_mask = np.array([c == 'good' for c in classification])
n_good = good_mask.sum()
if n_good == 0:
    io.close()
    return None
anno_names = nwb.units['anno_name'][:][good_mask]
region_indices = []
valid_neuron_mask = np.ones(n_good, dtype=bool)
for i, anno in enumerate(anno_names):
    region = map_anno_to_region(str(anno))
    if region is None:
        valid_neuron_mask[i] = False
        region_indices.append(-1)
    else:
        region_indices.append(COARSE_REGIONS.index(region))
...
good_unit_indices = good_unit_indices[valid_neuron_mask]
```

**What this does:** Keeps units where `classification == 'good'` and whose `anno_name` maps to one of 14 coarse brain regions. No firing-rate threshold is applied. Sessions with zero good units are skipped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "temporal_alignment_event: 'Go cue onset'" (convert_data.py:689); "Spike times are ABSOLUTE (not aligned to go cue)" (CONVERSION_NOTES.md:69)

**Code** (convert_data.py:179-187, 416-421):
```python
abs_start = go_cue_time + t_start
abs_end = go_cue_time + t_end
for i, st in enumerate(spike_times_list):
    ...
    mask = (st >= abs_start) & (st < abs_end)
    spikes_in_window = st[mask]
...
for ti in trial_indices:
    go_cue = go_start_times[ti]
    fr = compute_firing_rates(spike_times_per_unit, go_cue, T_START, T_END, BIN_SIZE_S)
```

**What this does:** Absolute spike times are filtered into the window [go_cue + T_START, go_cue + T_END), with bin index 0 corresponding to go_cue + T_START. Alignment event is the per-trial `go_start_times` value.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Spike binning: 50ms non-overlapping bins (per task spec), NOT 40ms/3.4ms stride from reference." (CONVERSION_NOTES.md:203)

**Code** (convert_data.py:27-30, 191-197):
```python
BIN_SIZE_S = 0.05  # 50 ms bins
T_START = -2.5     # seconds before go cue
T_END = 1.5        # seconds after go cue
N_TIMEBINS = int((T_END - T_START) / BIN_SIZE_S)  # 80
...
bin_indices = ((spikes_in_window - abs_start) / bin_size).astype(int)
bin_indices = np.clip(bin_indices, 0, n_bins - 1)
np.add.at(fr[i], bin_indices, 1.0)
fr /= bin_size
```

**What this does:** Non-overlapping 50 ms bins from -2.5 s to +1.5 s relative to go cue → 80 bins. Counts converted to rates by dividing by bin width.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_tone_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "sample_start_times | input[0]: time_from_tone | Continuous time from last sample onset before go cue | N/A | Time-varying" (CONVERSION_NOTES.md:174); "Tone onset: Last sample_start_time before each trial's go cue (accounting for early lick replays)." (CONVERSION_NOTES.md:206)

**Code** (convert_data.py:383-385, 417, 423-427):
```python
events = nwb.acquisition['BehavioralEvents']
go_start_times = events.time_series['go_start_times'].timestamps[:]
sample_start_times = events.time_series['sample_start_times'].timestamps[:]
...
go_cue = go_start_times[ti]
...
# Input 0: time from tone onset
tone_onset = find_last_sample_before_go(sample_start_times, go_cue)
if tone_onset is None:
    tone_onset = go_cue - 1.85
time_from_tone = compute_time_from_tone(go_cue, tone_onset, T_START, T_END, BIN_SIZE_S)
```

**What this does:** Derived from the timestamps of `BehavioralEvents/sample_start_times` (tone/sample epoch onsets) together with `BehavioralEvents/go_start_times` (per-trial go cue). No trials table field is used for this input.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_tone_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time from tone onset computation (finds last sample_start before go cue)" (CONVERSION_NOTES.md:230); "time_from_tone_onset max=7.94: Some trials have very early or misdetected tone onsets. Not critical for decoder." (CONVERSION_NOTES.md:325)

**Code** (convert_data.py:200-221):
```python
def find_last_sample_before_go(sample_start_times, go_cue_time):
    """Find the last sample onset time before a given go cue time."""
    valid = sample_start_times[sample_start_times < go_cue_time]
    if len(valid) == 0:
        return None
    return valid[-1]  # Last one before go cue

def compute_time_from_tone(go_cue_time, tone_onset_time, t_start, t_end, bin_size):
    n_bins = int((t_end - t_start) / bin_size)
    bin_centers = np.arange(n_bins) * bin_size + t_start + bin_size / 2
    tone_rel = tone_onset_time - go_cue_time  # tone onset relative to go cue
    time_from_tone = bin_centers - tone_rel  # time since tone onset
    return time_from_tone.astype(np.float32)
```

**What this does:** For each trial, the tone onset is the last `sample_start_times` value strictly before that trial's go cue (fallback `go_cue - 1.85` if none exists). The value at each of the 80 bin centers is the bin-center time minus the tone onset expressed relative to the go cue, giving a float32 elapsed-seconds ramp. Values are not clipped at zero, so pre-tone bins are negative.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_tone_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "input[0]: time_from_tone ... Time-varying" (CONVERSION_NOTES.md:174); "Data shapes: Neural (n_neurons, 80), input (2, 80), output (4, 80) — all correct." (CONVERSION_NOTES.md:320)

**Code** (convert_data.py:215-221, 416-420, 438-439):
```python
n_bins = int((t_end - t_start) / bin_size)
bin_centers = np.arange(n_bins) * bin_size + t_start + bin_size / 2
tone_rel = tone_onset_time - go_cue_time
time_from_tone = bin_centers - tone_rel
...
for ti in trial_indices:
    go_cue = go_start_times[ti]
    fr = compute_firing_rates(spike_times_per_unit, go_cue, T_START, T_END, BIN_SIZE_S)
...
input_data = np.stack([time_from_tone, photostim_ts], axis=0)
input_trials.append(input_data)
```

**What this does:** The signal is evaluated at the centers of the same 80 go-cue-aligned 50 ms bins (T_START=-2.5 to T_END=1.5) used for firing rates, computed from the same per-trial `go_cue`. It is stored as row 0 of a (2, 80) float32 array, one per trial, parallel to the (n_neurons, 80) neural array.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *photostim* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "photostim_start/stop_times | input[1]: photostim_on | Binary: 1 if photostim active, 0 otherwise | N/A | Time-varying" (CONVERSION_NOTES.md:175); "Photostim input: Binary time series - 1 during photostim, 0 otherwise. Use absolute photostim_start/stop_times aligned to go cue." (CONVERSION_NOTES.md:207)

**Code** (convert_data.py:383-389):
```python
events = nwb.acquisition['BehavioralEvents']
go_start_times = events.time_series['go_start_times'].timestamps[:]
sample_start_times = events.time_series['sample_start_times'].timestamps[:]

# Photostim event times (absolute)
photostim_start_abs = events.time_series['photostim_start_times'].timestamps[:]
photostim_stop_abs = events.time_series['photostim_stop_times'].timestamps[:]
```

**What this does:** Derived from the absolute timestamps of `BehavioralEvents/photostim_start_times` and `photostim_stop_times`, combined with the per-trial `go_start_times`. The trials-table fields `photostim_onset/power/duration` are not used.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *photostim*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Photostim binary time series from absolute event times" (CONVERSION_NOTES.md:231); "Photostim trials | ~25% (VGAT mice) | — | 20.0% | Reasonable" (CONVERSION_NOTES.md:305)

**Code** (convert_data.py:224-240, 429-436):
```python
def compute_photostim_timeseries(go_cue_time, photostim_starts, photostim_stops,
                                  t_start, t_end, bin_size):
    n_bins = int((t_end - t_start) / bin_size)
    bin_centers = np.arange(n_bins) * bin_size + t_start + bin_size / 2
    abs_centers = bin_centers + go_cue_time
    stim = np.zeros(n_bins, dtype=np.float32)
    for start, stop in zip(photostim_starts, photostim_stops):
        mask = (abs_centers >= start) & (abs_centers <= stop)
        stim[mask] = 1.0
    return stim
...
trial_abs_start = go_cue + T_START
trial_abs_end = go_cue + T_END
stim_mask = (photostim_stop_abs > trial_abs_start) & (photostim_start_abs < trial_abs_end)
ps_starts = photostim_start_abs[stim_mask]
ps_stops = photostim_stop_abs[stim_mask]
photostim_ts = compute_photostim_timeseries(go_cue, ps_starts, ps_stops, ...)
```

**What this does:** Photostim pulses overlapping the trial's absolute window are selected, then each bin center falling inside a [start, stop] interval is set to 1.0 (else 0.0), producing a binary float32 vector of length 80. Stimulation power/duration are not encoded — only on/off.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `input` *photostim* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use absolute photostim_start/stop_times aligned to go cue." (CONVERSION_NOTES.md:207); "input_names: ['time_from_tone_onset', 'photostim_on']" (convert_data.py:677)

**Code** (convert_data.py:231-239, 438-439, 677):
```python
n_bins = int((t_end - t_start) / bin_size)
bin_centers = np.arange(n_bins) * bin_size + t_start + bin_size / 2
# bin_centers are relative to go cue; convert to absolute
abs_centers = bin_centers + go_cue_time
stim = np.zeros(n_bins, dtype=np.float32)
for start, stop in zip(photostim_starts, photostim_stops):
    mask = (abs_centers >= start) & (abs_centers <= stop)
    stim[mask] = 1.0
...
input_data = np.stack([time_from_tone, photostim_ts], axis=0)
input_trials.append(input_data)
```

**What this does:** Bin centers relative to the trial's go cue are converted to absolute time and tested against the absolute pulse intervals, so the 80 photostim bins share the same go-cue-aligned 50 ms grid as the neural array. It is stored as row 1 of the per-trial (2, 80) input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "trial_instruction | output[0]: choice | left=0, right=1" (CONVERSION_NOTES.md:176)

**Code** (convert_data.py:377, 442):
```python
instructions = trials['trial_instruction'][:]
...
choice = 0 if instructions[ti] == 'left' else 1
```

**What this does:** Choice is derived from `nwb.trials['trial_instruction']`, mapped to 0 (left) or 1 (right).

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "left=0, right=1" (CONVERSION_NOTES.md:176)

**Code** (convert_data.py:442, 489-490):
```python
choice = 0 if instructions[ti] == 'left' else 1
...
full_output = np.zeros((4, N_TIMEBINS), dtype=np.int64)
full_output[0, :] = out_dict['choice']
```

**What this does:** A simple string-to-int mapping is applied per trial; the scalar value is then broadcast across all 80 time bins as row 0 of the (4, 80) int64 output array.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "outcome | output[1]: outcome | ignore=0, miss=1, hit=2" (CONVERSION_NOTES.md:177)

**Code** (convert_data.py:376, 445-446):
```python
outcomes = trials['outcome'][:]
...
outcome_str = outcomes[ti]
outcome_val = {'ignore': 0, 'miss': 1, 'hit': 2}.get(outcome_str, 0)
```

**What this does:** Outcome is derived from `nwb.trials['outcome']` (string values 'hit'/'miss'/'ignore').

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "ignore=0, miss=1, hit=2" (CONVERSION_NOTES.md:177)

**Code** (convert_data.py:444-446, 491):
```python
outcome_str = outcomes[ti]
outcome_val = {'ignore': 0, 'miss': 1, 'hit': 2}.get(outcome_str, 0)
...
full_output[1, :] = out_dict['outcome']
```

**What this does:** String label mapped via dict to int (default 0 if unknown), then broadcast across 80 time bins as row 1 of the output.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *early_lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "early_lick | output[2]: early_lick | no=0, yes=1" (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:378, 449):
```python
early_lick = trials['early_lick'][:]
...
early_val = 0 if early_lick[ti] == 'no early' else 1
```

**What this does:** Derived from `nwb.trials['early_lick']` string values.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *early_lick*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "no=0, yes=1" (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:449, 492):
```python
early_val = 0 if early_lick[ti] == 'no early' else 1
...
full_output[2, :] = out_dict['early_lick']
```

**What this does:** Binarized: 0 if 'no early', else 1; then broadcast across all 80 bins as row 2.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *tongue_y_position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "TongueTracking y | output[3]: tongue_y | Discretize per-session: 0(<40th), 1(40-60th), 2(>60th)" (CONVERSION_NOTES.md:179)

**Code** (convert_data.py:392-396):
```python
tongue_ts = nwb.acquisition['BehavioralTimeSeries'].time_series['Camera0_side_TongueTracking']
tongue_data_all = tongue_ts.data[:]  # (n_frames, 3): x, y, likelihood
tongue_timestamps = tongue_ts.timestamps[:]
tongue_y_all = tongue_data_all[:, 1].astype(np.float32)
tongue_likelihood = tongue_data_all[:, 2].astype(np.float32)
```

**What this does:** Derived from column 1 (y) of `Camera0_side_TongueTracking` data, with column 2 (likelihood) used to mask low-confidence samples.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *tongue_y_position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize per-session: 0(<40th), 1(40-60th), 2(>60th)" (CONVERSION_NOTES.md:179)

**Code** (convert_data.py:243-284, 469-485):
```python
def get_tongue_y_for_trial(...):
    ...
    y_in_window[like_in_window < 0.9] = np.nan
    ...
    bin_indices = np.digitize(t_in_window, bin_edges) - 1
    ...
    sums = np.bincount(valid_bins, weights=valid_vals, minlength=n_bins)
    counts = np.bincount(valid_bins, minlength=n_bins)
    tongue_y_binned[has_data] = (sums[has_data] / counts[has_data]).astype(np.float32)
...
if len(tongue_y_session) > 0:
    p40 = np.percentile(tongue_y_arr, 40)
    p60 = np.percentile(tongue_y_arr, 60)
...
tongue_y_disc[valid & (tongue_y_raw < p40)] = 0
tongue_y_disc[valid & (tongue_y_raw >= p40) & (tongue_y_raw <= p60)] = 1
tongue_y_disc[valid & (tongue_y_raw > p60)] = 2
```

**What this does:** Per-trial: low-likelihood (<0.9) samples → NaN; remaining y values are mean-binned into 50 ms bins. Per-session: compute 40th/60th percentiles over all valid binned values, then discretize into {0, 1, 2}. NaN bins map to 0 (zero-init).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 8-d. How is `output` *tongue_y_position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> Tongue is "Time-varying" output (CONVERSION_NOTES.md:179)

**Code** (convert_data.py:250-256, 493):
```python
n_bins = int((t_end - t_start) / bin_size)
bin_edges = np.arange(n_bins + 1) * bin_size + t_start + go_cue_time
abs_start = go_cue_time + t_start
abs_end = go_cue_time + t_end
mask = (tongue_timestamps >= abs_start) & (tongue_timestamps < abs_end)
...
full_output[3, :] = tongue_y_disc.astype(np.int64)
```

**What this does:** Tongue y samples are binned with edges shifted by the per-trial `go_cue_time`, giving the same 80 go-cue-aligned 50 ms bins as the neural data; placed in row 3 of output.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "1 session has 0 good units (sub-440958_ses-20190216T162508) - will be excluded" (CONVERSION_NOTES.md:73)

**Code** (convert_data.py:335-337, 360-362, 406-408, 424-426, 258-259, 470-475):
```python
if n_good == 0:
    io.close()
    return None
...
if n_neurons == 0:
    io.close()
    return None
...
if len(trial_indices) < 2:
    io.close()
    return None
...
tone_onset = find_last_sample_before_go(sample_start_times, go_cue)
if tone_onset is None:
    tone_onset = go_cue - 1.85
...
if mask.sum() == 0:
    return np.full(n_bins, np.nan, dtype=np.float32)
...
if len(tongue_y_session) > 0:
    p40 = np.percentile(tongue_y_arr, 40)
    p60 = np.percentile(tongue_y_arr, 60)
else:
    p40, p60 = 0, 0
```

**What this does:** Sessions with no good units, no mappable neurons, or fewer than 2 valid trials are skipped (return None). Missing tone onset defaults to `go_cue - 1.85`. Missing/low-likelihood tongue values become NaN; NaN tongue bins are written as 0 in the discretized output. Sessions with no valid tongue samples use percentiles of 0.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Load + process | ~6.5s | ~19 min for 174 sessions"; "Processing time: 2300.8s (~38 min)" (CONVERSION_NOTES.md:256, 287)

**Code** (convert_data.py:368-372, 416-466):
```python
spike_times_per_unit = []
for idx in good_unit_indices:
    st = nwb.units['spike_times'][idx]
    spike_times_per_unit.append(st)
...
for ti in trial_indices:
    go_cue = go_start_times[ti]
    fr = compute_firing_rates(spike_times_per_unit, go_cue, T_START, T_END, BIN_SIZE_S)
    neural_trials.append(fr)
    ...
    tongue_y_trial = get_tongue_y_for_trial(...)
```

**What this does:** Loading spike_times for all good units from disk, then the nested per-trial × per-neuron loop in `compute_firing_rates`, plus per-trial tongue binning, dominate runtime (~13 s/session × 173 sessions ≈ 38 min total).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:182-193, 416-421, 237-240, 478-495):
```python
for i, st in enumerate(spike_times_list):
    if len(st) == 0:
        continue
    mask = (st >= abs_start) & (st < abs_end)
    ...
    np.add.at(fr[i], bin_indices, 1.0)
...
for ti in trial_indices:
    go_cue = go_start_times[ti]
    fr = compute_firing_rates(spike_times_per_unit, go_cue, T_START, T_END, BIN_SIZE_S)
...
for start, stop in zip(photostim_starts, photostim_stops):
    mask = (abs_centers >= start) & (abs_centers <= stop)
    stim[mask] = 1.0
...
for out_dict in output_trials_raw:
    ...
    full_output = np.zeros((4, N_TIMEBINS), dtype=np.int64)
    full_output[0, :] = out_dict['choice']
```

**What this does:** Per-neuron loop in `compute_firing_rates`, the per-trial outer loop in `process_session` calling firing-rate/tongue/photostim helpers, and the per-pulse photostim loop are written as Python loops. The final per-trial output assembly also runs in a loop.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:175-177, 215-216, 231-232, 250-251, 416-432):
```python
n_bins = int((t_end - t_start) / bin_size)
fr = np.zeros((n_neurons, n_bins), dtype=np.float32)
...
n_bins = int((t_end - t_start) / bin_size)
bin_centers = np.arange(n_bins) * bin_size + t_start + bin_size / 2
...
n_bins = int((t_end - t_start) / bin_size)
bin_centers = np.arange(n_bins) * bin_size + t_start + bin_size / 2
...
n_bins = int((t_end - t_start) / bin_size)
bin_edges = np.arange(n_bins + 1) * bin_size + t_start + go_cue_time
...
for ti in trial_indices:
    go_cue = go_start_times[ti]
    ...
    stim_mask = (photostim_stop_abs > trial_abs_start) & (photostim_start_abs < trial_abs_end)
```

**What this does:** `n_bins`/`bin_centers` recomputed in each helper for every trial. The photostim window-mask intersection is recomputed per trial. Spike times list is iterated per neuron each trial rather than once per session.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:344-352, 513-581, 719-741):
```python
region_indices = []
valid_neuron_mask = np.ones(n_good, dtype=bool)
for i, anno in enumerate(anno_names):
    region = map_anno_to_region(str(anno))
    if region is None:
        valid_neuron_mask[i] = False
        region_indices.append(-1)
    else:
        region_indices.append(COARSE_REGIONS.index(region))
...
def plot_processing(session_data, session_idx, nwb_path):
    ...
...
all_choices = []
all_outcomes = []
all_early = []
for session_outputs in data['output']:
    for trial_out in session_outputs:
        all_choices.append(int(trial_out[0, 0]))
```

**What this does:** Per-session region mapping loop runs even though region info is only stored as int indices; the `plot_processing` path runs full image rendering when `--show-processing` is set; the post-conversion summary loops over every trial to print Counters that aren't saved.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "converted_data.pkl — 11,339 MB (11.3 GB)" (CONVERSION_NOTES.md:286)

**Code** (convert_data.py:177, 236, 270, 395-396, 467, 705):
```python
fr = np.zeros((n_neurons, n_bins), dtype=np.float32)
...
stim = np.zeros(n_bins, dtype=np.float32)
...
tongue_y_binned = np.full(n_bins, np.nan, dtype=np.float32)
...
tongue_y_all = tongue_data_all[:, 1].astype(np.float32)
tongue_likelihood = tongue_data_all[:, 2].astype(np.float32)
...
io.close()
...
pickle.dump(data, f, protocol=4)
```

**What this does:** Uses float32 for firing rates / inputs / tongue arrays (int64 for outputs as required), explicitly closes each NWB IO handle after processing, and writes pickle protocol 4 for large objects. No streaming — all sessions are kept in memory before pickling.

**Rating:** match

**Note:** _(no note)_---

---
