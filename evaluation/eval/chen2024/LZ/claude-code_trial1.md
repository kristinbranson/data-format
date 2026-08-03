# map — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/map/claude/2026-03-22__21-13-57_trial1/verifier/snapshot/`

Outputs identified (K=4): choice, outcome, early_lick, tongue_y_position

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "28 subject directories (`sub-XXXXXX/`) / 174 NWB files total (`*_behavior+ecephys+ogen.nwb`) / 3-10 sessions per subject" (lines 58-61)

**Code** (convert_data.py:286-288, 950-972):
```python
def get_nwb_files():
    """Get list of all NWB files sorted by subject then session."""
    return sorted(glob.glob(os.path.join(DATA_DIR, 'sub-*', 'sub-*_ses-*.nwb')))
...
nwb_files = get_nwb_files()
print(f'Found {len(nwb_files)} NWB files')
...
for i, nwb_path in enumerate(nwb_files):
    print(f'\n[{i+1}/{len(nwb_files)}] Processing {os.path.basename(nwb_path)}')
    result = process_session(nwb_path, ...)
```

**What this does:** Globs all `sub-*/sub-*_ses-*.nwb` under `/app/data`, sorts them, and iterates session-by-session calling `process_session` on each NWB file.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`subject.subject_id` → `subjects` Unique subject IDs" (line 184)

**Code** (convert_data.py:346-348, 962, 977-980, 1013, 1019-1021):
```python
subject_id = nwb.subject.subject_id
subject_desc = nwb.subject.description  # e.g., "SC015"
...
subjects_set = OrderedDict()
...
sid = result['subject_id']
if sid not in subjects_set:
    subjects_set[sid] = len(subjects_set)
...
subject_idx = np.array(subject_idx, dtype=np.int64)
...
'subjects': subjects,
'subject_idx': subject_idx,
```

**What this does:** Reads `subject_id` per NWB file; builds an OrderedDict mapping unique subject IDs to integer indices; emits `subjects` list and a per-session `subject_idx` array.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "174 NWB files total (`*_behavior+ecephys+ogen.nwb`) ... 3-10 sessions per subject" (lines 59-61); "144 pass selection criteria" (line 302)

**Code** (convert_data.py:286-288, 658-744):
```python
def get_nwb_files():
    return sorted(glob.glob(os.path.join(DATA_DIR, 'sub-*', 'sub-*_ses-*.nwb')))
...
def process_session(nwb_path, show_processing=False, session_idx=0):
    """Process a single NWB session into decoder format."""
    ...
    data = load_nwb_session(nwb_path)
    ...
    return {... 'nwb_path': nwb_path, ...}
```

**What this does:** Each NWB file is treated as one session. `process_session` returns a per-session dict containing neural/input/output lists; sessions are appended to `all_sessions` in `convert_all`.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trials table (14 columns): trial_instruction (left/right), outcome (hit/miss/ignore), early_lick, auto_water, free_water, photostim info" (line 65)

**Code** (convert_data.py:377-391, 685-698):
```python
trials = nwb.trials
n_trials = len(trials)
trials_data = {
    'start_time': trials['start_time'][:],
    'stop_time': trials['stop_time'][:],
    'trial_instruction': trials['trial_instruction'][:],
    'outcome': trials['outcome'][:],
    'early_lick': trials['early_lick'][:],
    'auto_water': trials['auto_water'][:],
    'free_water': trials['free_water'][:],
    ...
}
...
trial_mask = np.ones(data['n_trials'], dtype=bool)
trial_mask[td['auto_water'] == 1] = False
trial_mask[td['free_water'] == 1] = False
trial_indices = np.where(trial_mask)[0]
...
go_times = data['go_times'][trial_indices]
```

**What this does:** Pulls per-trial fields from the NWB `trials` table; trial alignment uses `go_times` (from BehavioralEvents `go_start_times`) indexed by `trial_indices`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "For our decoder, we keep most of these since they are outputs/inputs ... Exclude: auto_water, free_water trials / Keep: all other trials (including early lick, ignore, stim - these are decoder I/O)" (lines 126, 136-137)

**Code** (convert_data.py:684-697, 719-742):
```python
# === Trial filtering: exclude auto_water and free_water ===
trial_mask = np.ones(data['n_trials'], dtype=bool)
trial_mask[td['auto_water'] == 1] = False
trial_mask[td['free_water'] == 1] = False
trial_indices = np.where(trial_mask)[0]
n_valid_trials = len(trial_indices)
if n_valid_trials < 2:
    print(f'    SKIP: only {n_valid_trials} valid trials')
    return None
...
# === Exclude trials beyond recording range ===
recording_mask = (go_times + ALIGN_START <= max_spike_time) & \
                 (go_times + ALIGN_END >= min_spike_time)
```

**What this does:** Excludes auto_water and free_water trials, plus trials whose [-2.5s,+1.5s] window around go cue falls outside recorded spike time range. Session-level filter (perf>65%, ≥50 correct L/R) applied earlier.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`units.spike_times` (good units) → `neural` Bin into 50ms non-overlapping bins around go cue (-2.5 to +1.5s)" (line 176)

**Code** (convert_data.py:350-373):
```python
units = nwb.units
classifications = units['classification'][:]
good_mask = classifications == 'good'
anno_names = units['anno_name'][:]

spike_times_vi = units['spike_times']  # VectorIndex
all_spike_times = np.array(spike_times_vi.target.data[:])
all_st_idx = np.array(spike_times_vi.data[:])

good_indices = np.where(good_mask)[0]
good_spike_times = []
for ui in good_indices:
    start_idx = 0 if ui == 0 else int(all_st_idx[ui - 1])
    end_idx = int(all_st_idx[ui])
    good_spike_times.append(all_spike_times[start_idx:end_idx])
```

**What this does:** Derived from NWB `units` table: `spike_times` (via VectorIndex `.target.data`), `classification` (filter == 'good'), and `anno_name` (brain region).

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Bin into 50ms non-overlapping bins around go cue (-2.5 to +1.5s) = 80 timepoints" (line 176); "Spike alignment ... Align using go_start_times" (line 154)

**Code** (convert_data.py:456-502):
```python
def bin_spikes(spike_times_list, go_times, align_start, align_end, bin_width, n_bins):
    n_neurons = len(spike_times_list)
    n_trials = len(go_times)
    bin_edges = np.linspace(align_start, align_end, n_bins + 1)
    all_matrices = np.zeros((n_trials, n_neurons, n_bins), dtype=np.float32)
    for n in range(n_neurons):
        st = spike_times_list[n]
        if len(st) == 0:
            continue
        for t in range(n_trials):
            go_t = go_times[t]
            abs_start = go_t + align_start
            abs_end = go_t + align_end
            idx_lo = np.searchsorted(st, abs_start, side='left')
            idx_hi = np.searchsorted(st, abs_end, side='left')
            if idx_hi > idx_lo:
                rel_spikes = st[idx_lo:idx_hi] - go_t
                counts, _ = np.histogram(rel_spikes, bins=bin_edges)
                all_matrices[t, n, :] = counts / bin_width
    return [all_matrices[t] for t in range(n_trials)]
```

**What this does:** Spike times converted to firing rates by histogram binning into 80 non-overlapping 50ms bins from -2.5s to +1.5s relative to go cue, divided by bin width to give Hz.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "In NWB: `classification == 'good'` corresponds to the classifier QC output" (line 48); "Classifier-based QC: 5 region-specific logistic regression classifiers" (line 130)

**Code** (convert_data.py:354-355, 700-717):
```python
classifications = units['classification'][:]
good_mask = classifications == 'good'
...
# === Neuron filtering: only good units with valid brain region ===
good_anno = data['good_anno_names']
region_labels = []
neuron_mask = []
for i, anno in enumerate(good_anno):
    region = map_anno_to_region(anno)
    if region is not None:
        region_labels.append(region)
        neuron_mask.append(i)
neuron_mask = np.array(neuron_mask)
n_neurons = len(neuron_mask)
```

**What this does:** Two filters: (1) `classification == 'good'` (NWB-encoded classifier QC), and (2) units must map to one of 14 major brain regions via `anno_name` keyword matching, else dropped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Alignment: go cue onset (`go_start_times`)" (line 191); "temporal_alignment_event: 'Go cue onset'" (in metadata)

**Code** (convert_data.py:394-395, 488-499):
```python
be = nwb.acquisition['BehavioralEvents']
go_times = be.time_series['go_start_times'].timestamps[:]
...
for t in range(n_trials):
    go_t = go_times[t]
    abs_start = go_t + align_start
    abs_end = go_t + align_end
    idx_lo = np.searchsorted(st, abs_start, side='left')
    idx_hi = np.searchsorted(st, abs_end, side='left')
    if idx_hi > idx_lo:
        rel_spikes = st[idx_lo:idx_hi] - go_t
```

**What this does:** Each trial's go cue time (from `BehavioralEvents.go_start_times`) defines time 0; spike times are subtracted by `go_t` and binned in [-2.5, +1.5]s.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Bin width: 50ms (non-overlapping) / N timepoints: 80 bins" (lines 192-193); "50ms bins: Task specification overrides reference code's 40ms/3.4ms sliding histogram" (line 200)

**Code** (convert_data.py:30-33, 476, 498-499):
```python
BIN_WIDTH = 0.050  # 50 ms bins (decoder task spec)
ALIGN_START = -2.5  # seconds before go cue
ALIGN_END = 1.5     # seconds after go cue
N_BINS = int((ALIGN_END - ALIGN_START) / BIN_WIDTH)  # 80 bins
...
bin_edges = np.linspace(align_start, align_end, n_bins + 1)
...
counts, _ = np.histogram(rel_spikes, bins=bin_edges)
all_matrices[t, n, :] = counts / bin_width
```

**What this does:** 80 non-overlapping 50ms bins from -2.5s to +1.5s. Spikes counted with np.histogram, divided by bin_width → Hz.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_tone_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sample start time relative to go cue | `input[0]`: time_from_tone_onset | Continuous, `t - tone_onset` for each time bin | Use last sample_start before go cue for each trial" (line 177); "**Behavioral events**: go_start_times, sample_start/stop_times, ..." (line 66)

**Code** (convert_data.py:393-398, 437-453):
```python
be = nwb.acquisition['BehavioralEvents']
go_times = be.time_series['go_start_times'].timestamps[:]

# Sample start times (may have more entries than trials due to early lick replays)
sample_start_ts = be.time_series['sample_start_times'].timestamps[:]
...
def get_tone_onset_for_trials(go_times, sample_start_ts, trial_starts, trial_stops):
    """Get the last sample start time before go cue for each trial. ..."""
    n_trials = len(go_times)
    tone_onsets = np.full(n_trials, np.nan)
    for i in range(n_trials):
        mask = (sample_start_ts >= trial_starts[i]) & (sample_start_ts <= go_times[i])
        matching = sample_start_ts[mask]
        if len(matching) > 0:
            tone_onsets[i] = matching[-1]  # last sample start
```

**What this does:** Derived from NWB `BehavioralEvents.sample_start_times` timestamps (tone/sample epoch onset), bounded by the `trials` table `start_time`/`stop_time` and `BehavioralEvents.go_start_times`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_tone_onset*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Continuous, `t - tone_onset` for each time bin | Use last sample_start before go cue for each trial" (line 177); "time_from_tone_onset range | [-1.5, 9.4]" (line 244)

**Code** (convert_data.py:629-655, 752-758):
```python
def compute_tone_onset_input(go_times, tone_onsets, align_start, align_end, bin_width, n_bins):
    """Compute time from tone onset for each trial and time bin. ..."""
    bin_centers = np.linspace(align_start + bin_width/2, align_end - bin_width/2, n_bins)
    tone_onset_input = []
    for t in range(n_trials):
        go_t = go_times[t]
        tone_t = tone_onsets[t]
        if np.isnan(tone_t):
            tone_input = np.zeros(n_bins, dtype=np.float32)
        else:
            tone_rel = tone_t - go_t  # tone onset relative to go cue (negative)
            tone_input = (bin_centers - tone_rel).astype(np.float32)
        tone_onset_input.append(tone_input)
    return tone_onset_input
...
tone_onsets = get_tone_onset_for_trials(
    go_times, data['sample_start_ts'],
    td['start_time'][trial_indices], td['stop_time'][trial_indices])
tone_onset_input = compute_tone_onset_input(go_times, tone_onsets, ALIGN_START, ALIGN_END, BIN_WIDTH, N_BINS)
```

**What this does:** Per trial, the last `sample_start_times` event between trial start and go cue is taken as tone onset; then a continuous elapsed-time value `bin_center - (tone_t - go_t)` is computed at each of the 80 bin centers. Trials with no tone onset found get an all-zeros vector.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_tone_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Alignment: go cue onset (`go_start_times`) / Window: -2.5s to +1.5s / Bin width: 50ms (non-overlapping) / N timepoints: 80 bins" (lines 191-193); "Sample start time relative to go cue" (line 177)

**Code** (convert_data.py:636, 640, 650-651, 765-769, 817):
```python
bin_centers = np.linspace(align_start + bin_width/2, align_end - bin_width/2, n_bins)
...
go_t = go_times[t]
...
tone_rel = tone_t - go_t  # tone onset relative to go cue (negative)
tone_input = (bin_centers - tone_rel).astype(np.float32)
...
# Combine inputs: (2, n_bins)
input_trials = []
for t in range(n_valid_trials):
    inp = np.stack([tone_onset_input[t], photostim_input[t]], axis=0).astype(np.float32)
    input_trials.append(inp)
...
'input': input_trials,            # list of (2, n_bins)
```

**What this does:** Uses the same go-cue-referenced grid as `neural`: the same `ALIGN_START=-2.5`/`ALIGN_END=1.5`, `BIN_WIDTH=0.050`, `N_BINS=80` constants, evaluated at bin centers with the trial's `go_times[t]` as time 0. Stored as row 0 of a per-trial `(2, 80)` input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *photostim* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Photostim start/stop times | `input[1]`: photostim_on | Binary time-varying, 1 when photostim active | From photostim_start/stop_times" (line 178); "**Behavioral events**: ... photostim_start/stop_times" (line 66)

**Code** (convert_data.py:394-402, 428-429):
```python
be = nwb.acquisition['BehavioralEvents']
go_times = be.time_series['go_start_times'].timestamps[:]
...
# Photostim events
photostim_start_ts = be.time_series['photostim_start_times'].timestamps[:]
photostim_stop_ts = be.time_series['photostim_stop_times'].timestamps[:]
...
'photostim_start_ts': photostim_start_ts,
'photostim_stop_ts': photostim_stop_ts,
```

**What this does:** Derived from NWB `BehavioralEvents.photostim_start_times` and `photostim_stop_times` timestamps, plus `go_start_times` for referencing. (The `trials` table columns `photostim_onset`/`photostim_power`/`photostim_duration` are loaded at lines 388-390 but are used only for session-level control-trial performance, not for this input.)

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *photostim*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Binary time-varying, 1 when photostim active" (line 178); "photostim_on range | [0.0, 1.0]" (line 245); "Photostim input is binary with small fraction of stim trials" (line 252)

**Code** (convert_data.py:596-626, 760-763):
```python
def compute_photostim_input(go_times, photostim_start_ts, photostim_stop_ts,
                            align_start, align_end, bin_width, n_bins):
    """Compute binary photostimulation time series for each trial. 1 when photostim is active, 0 otherwise."""
    bin_centers = np.linspace(align_start + bin_width/2, align_end - bin_width/2, n_bins)
    photostim_trials = []
    for t in range(n_trials):
        go_t = go_times[t]
        ps = np.zeros(n_bins, dtype=np.float32)
        for si in range(len(photostim_start_ts)):
            ps_start = photostim_start_ts[si] - go_t
            ps_stop = photostim_stop_ts[si] - go_t
            if ps_stop < align_start or ps_start > align_end:
                continue
            for b in range(n_bins):
                bc = bin_centers[b]
                if bc >= ps_start and bc < ps_stop:
                    ps[b] = 1.0
        photostim_trials.append(ps)
    return photostim_trials
```

**What this does:** For each trial, every photostim start/stop interval in the session is shifted into go-cue-relative time; intervals overlapping the [-2.5, +1.5]s window set the bins whose centers fall inside `[ps_start, ps_stop)` to 1.0, others remain 0.0 (float32 binary vector).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `input` *photostim* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Alignment: go cue onset (`go_start_times`) / Window: -2.5s to +1.5s / Bin width: 50ms (non-overlapping) / N timepoints: 80 bins" (lines 191-193); "Binary time-varying" (line 178)

**Code** (convert_data.py:603, 607, 611-612, 761-769, 1024):
```python
bin_centers = np.linspace(align_start + bin_width/2, align_end - bin_width/2, n_bins)
...
go_t = go_times[t]
...
ps_start = photostim_start_ts[si] - go_t
ps_stop = photostim_stop_ts[si] - go_t
...
photostim_input = compute_photostim_input(go_times, data['photostim_start_ts'],
                                           data['photostim_stop_ts'],
                                           ALIGN_START, ALIGN_END, BIN_WIDTH, N_BINS)
input_trials = []
for t in range(n_valid_trials):
    inp = np.stack([tone_onset_input[t], photostim_input[t]], axis=0).astype(np.float32)
...
'input_names': ['time_from_tone_onset', 'photostim_on'],
```

**What this does:** Photostim times are converted to go-cue-relative time using each trial's `go_times[t]` and evaluated on the same 80-bin [-2.5, +1.5]s grid as `neural`. Stored as row 1 of the per-trial `(2, 80)` input array, named `photostim_on`.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`trial_instruction` → `output[0]`: choice / left=0, right=1 (per-trial)" (line 179)

**Code** (convert_data.py:773-774):
```python
# 1. Choice: left=0, right=1
instructions = td['trial_instruction'][trial_indices]
choices = np.array([0 if ins == 'left' else 1 for ins in instructions], dtype=np.int64)
```

**What this does:** Derived from NWB `trials.trial_instruction` ('left'/'right') string column.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "left=0, right=1 (per-trial)" (line 179)

**Code** (convert_data.py:773-774, 798-799):
```python
instructions = td['trial_instruction'][trial_indices]
choices = np.array([0 if ins == 'left' else 1 for ins in instructions], dtype=np.int64)
...
out = np.array([
    np.full(N_BINS, choices[t], dtype=np.int64),         # choice (per-trial, broadcast)
```

**What this does:** Strings mapped to integers (left→0, right→1); per-trial scalar broadcast to length-80 vector across time bins.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`outcome` → `output[1]`: outcome / ignore=0, miss=1, hit=2 (per-trial)" (line 180)

**Code** (convert_data.py:776-779):
```python
# 2. Outcome: ignore=0, miss=1, hit=2
outcomes_raw = td['outcome'][trial_indices]
outcome_map = {'ignore': 0, 'miss': 1, 'hit': 2}
outcomes = np.array([outcome_map.get(o, 0) for o in outcomes_raw], dtype=np.int64)
```

**What this does:** Derived from NWB `trials.outcome` string column.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "ignore=0, miss=1, hit=2 (per-trial)" (line 180)

**Code** (convert_data.py:776-779, 800):
```python
outcomes_raw = td['outcome'][trial_indices]
outcome_map = {'ignore': 0, 'miss': 1, 'hit': 2}
outcomes = np.array([outcome_map.get(o, 0) for o in outcomes_raw], dtype=np.int64)
...
np.full(N_BINS, outcomes[t], dtype=np.int64),        # outcome (per-trial, broadcast)
```

**What this does:** String labels mapped to integers via dict (unknowns default to 0/'ignore'); broadcast across time bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *early_lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`early_lick` → `output[2]`: early_lick / no=0, yes=1 (per-trial)" (line 181)

**Code** (convert_data.py:781-783):
```python
# 3. Early lick: no=0, yes=1
early_lick_raw = td['early_lick'][trial_indices]
early_licks = np.array([1 if el == 'early' else 0 for el in early_lick_raw], dtype=np.int64)
```

**What this does:** Derived from NWB `trials.early_lick` string column.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *early_lick*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "no=0, yes=1 (per-trial)" (line 181)

**Code** (convert_data.py:781-783, 801):
```python
early_lick_raw = td['early_lick'][trial_indices]
early_licks = np.array([1 if el == 'early' else 0 for el in early_lick_raw], dtype=np.int64)
...
np.full(N_BINS, early_licks[t], dtype=np.int64),     # early lick (per-trial, broadcast)
```

**What this does:** Strings mapped: 'early'→1 else 0; broadcast across time bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *tongue_y_position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "TongueTracking y-position → `output[3]`: tongue_y_position / Discretized per session: 0(<40th), 1(40-60th), 2(>60th); time-varying / Handle occlusion (set to mean when confidence low)" (line 182)

**Code** (convert_data.py:408-412):
```python
bts = nwb.acquisition['BehavioralTimeSeries']
tongue_ts_obj = bts.time_series['Camera0_side_TongueTracking']
tongue_data = tongue_ts_obj.data[:]  # (n_frames, 3): x, y, confidence
tongue_timestamps = tongue_ts_obj.timestamps[:]
```

**What this does:** Derived from NWB `BehavioralTimeSeries.Camera0_side_TongueTracking` data column 1 (y) and column 2 (confidence) plus its timestamps.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *tongue_y_position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Tongue occlusion handling: Set tongue position to session mean when confidence < 0.9 ... 0(<40th), 1(40-60th), 2(>60th)" (lines 203, 182); "Optimized tongue processing: vectorized using np.digitize" (line 224)

**Code** (convert_data.py:515-560, 563-593):
```python
tongue_y = tongue_data[:, 1].astype(np.float64)
tongue_conf = tongue_data[:, 2].astype(np.float64)
visible_mask = tongue_conf >= confidence_threshold
session_mean_y = np.mean(tongue_y[visible_mask])
tongue_y_imputed = tongue_y.copy()
tongue_y_imputed[~visible_mask] = session_mean_y
...
for t in range(n_trials):
    ...
    bin_indices = np.digitize(trial_ts, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    trial_tongue_y = np.full(n_bins, session_mean_y, dtype=np.float64)
    for b in range(n_bins):
        in_bin = trial_y[bin_indices == b]
        if len(in_bin) > 0:
            trial_tongue_y[b] = np.mean(in_bin)
...
p40 = np.percentile(all_values, 40)
p60 = np.percentile(all_values, 60)
...
d = np.zeros(len(trial_y), dtype=np.int64)
d[trial_y >= p40] = 1
d[trial_y >= p60] = 2
```

**What this does:** Imputes occluded frames (confidence<0.9) with session mean y; bins frames per trial into 80 bins via `np.digitize` (mean within bin); discretizes against session 40th/60th percentiles into {0,1,2}.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 8-d. How is `output` *tongue_y_position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "time-varying" (line 182)

**Code** (convert_data.py:529-549, 802):
```python
n_trials = len(go_times)
bin_edges = np.linspace(align_start, align_end, n_bins + 1)
...
for t in range(n_trials):
    go_t = go_times[t]
    window_start = go_t + align_start
    window_end = go_t + align_end
    mask = (tongue_timestamps >= window_start) & (tongue_timestamps < window_end)
    trial_ts = tongue_timestamps[mask] - go_t
    trial_y = tongue_y_imputed[mask]
    ...
    bin_indices = np.digitize(trial_ts, bin_edges) - 1
...
tongue_y_discrete[t].astype(np.int64),                # tongue y (time-varying)
```

**What this does:** Tongue timestamps are aligned to each trial's `go_times` and binned into the same 80-bin [-2.5,+1.5]s window as `neural`; output stored as a length-80 vector per trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trials beyond recording range (FIXED): Some sessions had behavioral trials continuing after neural recording ended ... Fixed by checking spike time range" (line 326); "Several unmapped annotations (FIXED)" (line 330)

**Code** (convert_data.py:275-283, 444-452, 519-527, 644-651, 719-742):
```python
def map_anno_to_region(anno_name):
    if not anno_name or anno_name.strip() == '':
        return None
    for region, keywords in REGION_MAPPING.items():
        for kw in keywords:
            if kw.lower() in anno_name.lower():
                return region
    return None  # unmapped
...
for i in range(n_trials):
    mask = (sample_start_ts >= trial_starts[i]) & (sample_start_ts <= go_times[i])
    matching = sample_start_ts[mask]
    if len(matching) > 0:
        tone_onsets[i] = matching[-1]
...
visible_mask = tongue_conf >= confidence_threshold
if np.sum(visible_mask) > 0:
    session_mean_y = np.mean(tongue_y[visible_mask])
else:
    session_mean_y = np.mean(tongue_y)
tongue_y_imputed[~visible_mask] = session_mean_y
...
if np.isnan(tone_t):
    tone_input = np.zeros(n_bins, dtype=np.float32)
...
recording_mask = (go_times + ALIGN_START <= max_spike_time) & \
                 (go_times + ALIGN_END >= min_spike_time)
if not np.all(recording_mask):
    n_dropped = np.sum(~recording_mask)
    ...
```

**What this does:** Empty/unmapped CCF annotations → neuron dropped; missing tone onset → zeros; occluded tongue frames → session mean; trials outside recording window → dropped. Sessions failing performance/L-R thresholds skipped. p40==p60 edge case patched with epsilon.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "NWB loading ~1.5s | Spike binning ~3.3s | Tongue processing ~1.5s | Total ~7.5s" per session (lines 254-260); "Optimized tongue processing: vectorized using np.digitize (142s -> 1.5s); Optimized spike binning: use np.searchsorted (14s -> 3s)" (lines 224-225)

**Code** (convert_data.py:481-502, 533-558):
```python
for n in range(n_neurons):
    st = spike_times_list[n]
    if len(st) == 0:
        continue
    for t in range(n_trials):
        go_t = go_times[t]
        abs_start = go_t + align_start
        abs_end = go_t + align_end
        idx_lo = np.searchsorted(st, abs_start, side='left')
        idx_hi = np.searchsorted(st, abs_end, side='left')
        if idx_hi > idx_lo:
            rel_spikes = st[idx_lo:idx_hi] - go_t
            counts, _ = np.histogram(rel_spikes, bins=bin_edges)
            all_matrices[t, n, :] = counts / bin_width
```

**What this does:** Per session: spike binning (~3.3s, dominant), NWB I/O (~1.5s), tongue processing (~1.5s). Spike binning loops O(n_neurons × n_trials).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Optimized spike binning: use np.searchsorted ... Optimized tongue processing: vectorized using np.digitize" (lines 224-225)

**Code** (convert_data.py:481-502, 553-556, 596-624):
```python
for n in range(n_neurons):
    ...
    for t in range(n_trials):
        ...
        counts, _ = np.histogram(rel_spikes, bins=bin_edges)
...
for b in range(n_bins):
    in_bin = trial_y[bin_indices == b]
    if len(in_bin) > 0:
        trial_tongue_y[b] = np.mean(in_bin)
...
for si in range(len(photostim_start_ts)):
    ...
    for b in range(n_bins):
        bc = bin_centers[b]
        if bc >= ps_start and bc < ps_stop:
            ps[b] = 1.0
```

**What this does:** Triple nested loops in `bin_spikes` (neuron × trial × histogram); per-bin loop in `compute_tongue_y_per_trial` (could use np.bincount); per-bin scan in `compute_photostim_input` (could use vectorized comparisons).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none specific)

**Code** (convert_data.py:476, 530, 603, 636):
```python
bin_edges = np.linspace(align_start, align_end, n_bins + 1)
...
bin_edges = np.linspace(align_start, align_end, n_bins + 1)
...
bin_centers = np.linspace(align_start + bin_width/2, align_end - bin_width/2, n_bins)
...
bin_centers = np.linspace(align_start + bin_width/2, align_end - bin_width/2, n_bins)
```

**What this does:** `bin_edges`/`bin_centers` recomputed in each helper (bin_spikes, tongue, photostim, tone_onset). `compute_session_performance` iterates trials in Python loop with multiple per-trial scans (lines 306-336). Region mapping loop scans keyword list per neuron.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:380-406, 564-573):
```python
trials_data = {
    'start_time': trials['start_time'][:],
    'stop_time': trials['stop_time'][:],
    ...
    'photostim_power': trials['photostim_power'][:],
    'photostim_duration': trials['photostim_duration'][:],
}
...
left_lick_ts = be.time_series['left_lick_times'].timestamps[:]
right_lick_ts = be.time_series['right_lick_times'].timestamps[:]
...
all_values = np.concatenate([t for t in tongue_y_trials])
```

**What this does:** Loads `photostim_power`, `photostim_duration`, `left_lick_ts`, `right_lick_ts` (used only minimally / not in output). Also loads tongue x-coordinate. Computes `tongue_y_trials` continuous values that are then discarded after discretization. `subject_desc` loaded but only used in metadata.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "converted_data.pkl: 9.3 GB" (line 287)

**Code** (convert_data.py:413, 479, 499, 1072-1073):
```python
io.close()
...
all_matrices = np.zeros((n_trials, n_neurons, n_bins), dtype=np.float32)
...
all_matrices[t, n, :] = counts / bin_width
...
with open(outfile, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** NWB file handle closed after extraction; neural arrays use float32 instead of float64; pickle protocol 4 used for large objects. No streaming/chunked processing — full per-session matrices held in memory and then accumulated across all sessions before pickling.

**Rating:** match

**Note:** _(no note)_---

---
