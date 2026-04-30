# sosa2024 — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/sosa2024/claude/2026-03-10__11-18-23_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:62-69):
> NWB files: `data/sub-{id}/sub-{id}_ses-{nn}_behavior+ophys.nwb`. Each file contains one session for one mouse. 11 subjects, 152 total sessions. Loaded via `h5py`.

**Code** (convert_data.py:57-84):
```python
def get_all_nwb_files(data_dir, sample=False):
    """Get all NWB files organized by subject."""
    subjects = sorted([d for d in os.listdir(data_dir)
                       if d.startswith('sub-') and os.path.isdir(os.path.join(data_dir, d))])

    all_files = []
    for subj in subjects:
        subj_dir = os.path.join(data_dir, subj)
        nwb_files = sorted([f for f in os.listdir(subj_dir) if f.endswith('.nwb')])
        for nwb_file in nwb_files:
            all_files.append({
                'subject': subj.replace('sub-', ''),
                'filepath': os.path.join(subj_dir, nwb_file),
                'filename': nwb_file,
            })
    ...
    return all_files
```

Loading via h5py (convert_data.py:309):
```python
with h5py.File(filepath, 'r') as f:
```

**What this does:** Enumerates all `sub-*` subdirectories under `data/`, then collects every `.nwb` file within each as a session. NWB files are opened directly with `h5py` (rather than `pynwb`).

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:22):
> 11 subjects (all switch-condition mice), 152 total sessions.

**Code** (convert_data.py:59-71):
```python
subjects = sorted([d for d in os.listdir(data_dir)
                   if d.startswith('sub-') and os.path.isdir(os.path.join(data_dir, d))])
...
all_files.append({
    'subject': subj.replace('sub-', ''),
    ...
})
```

Subjects list assembled (convert_data.py:791-794):
```python
subj = session_info['subject']
if subj not in subjects_list:
    subjects_list.append(subj)
subject_idx_list.append(subjects_list.index(subj))
```

**What this does:** Subject identifiers are derived from each `sub-*` directory name (the `sub-` prefix stripped). A `subjects` list and per-session `subject_idx` array are built during the conversion loop.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:64-65):
> NWB files: `data/sub-{id}/sub-{id}_ses-{nn}_behavior+ophys.nwb`. Each file contains one session for one mouse.

**Code** (convert_data.py:65-71):
```python
nwb_files = sorted([f for f in os.listdir(subj_dir) if f.endswith('.nwb')])
for nwb_file in nwb_files:
    all_files.append({
        'subject': subj.replace('sub-', ''),
        'filepath': os.path.join(subj_dir, nwb_file),
        'filename': nwb_file,
    })
```

Session id pulled from NWB metadata (convert_data.py:313-314):
```python
session_id = f['general']['session_id'][()].decode() if isinstance(
    f['general']['session_id'][()], bytes) else str(f['general']['session_id'][()])
```

**What this does:** Each `.nwb` file under a subject directory becomes one session; the session identifier is read from the NWB `general/session_id` field rather than parsed from the filename.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:131):
> Trials defined by trial_start to teleport indices. Teleport periods excluded from analysis

**Code** (convert_data.py:387-399):
```python
# ---- Find trial boundaries ----
trial_starts = np.where(trial_start_signal > 0)[0]
teleports = np.where(teleport_signal > 0)[0]

# Ensure matching number of starts and teleports
n_trials = min(len(trial_starts), len(teleports))
trial_starts = trial_starts[:n_trials]
teleports = teleports[:n_trials]

# Ensure each teleport comes after its corresponding trial start
valid = teleports > trial_starts
trial_starts = trial_starts[valid]
teleports = teleports[valid]
n_trials = len(trial_starts)
```

**What this does:** Trial boundaries are extracted as the indices where `trial_start_signal > 0` and `teleport_signal > 0`. The arrays are truncated to equal length and pairs where the teleport does not come after its corresponding start are dropped.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:140-142):
> Lick sensor error: if >35% of samples have cumulative lick count >2, set licks to NaN for that trial. Samples with speed < 2 cm/s excluded from decoder.

**Code** (convert_data.py:509-521):
```python
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    n_timepoints = end - start

    if n_timepoints < 5:
        continue  # Skip very short trials

    # Neural: (n_neurons, n_timepoints)
    trial_neural = neural_all[start:end, :].T.copy()
```

Lick-error trials per-trial NaN'ing (convert_data.py:474-483):
```python
for t in range(n_trials):
    ...
    trial_lick = lick[start:end]
    if len(trial_lick) > 0:
        frac_bad = np.sum(trial_lick > 2) / len(trial_lick)
        if frac_bad > LICK_ERROR_FRACTION:
            lick_binary[start:end] = np.nan
            lick_error_trials.append(t)
```

**What this does:** Trials with fewer than 5 timepoints are skipped. For trials where >35% of samples have cumulative lick > 2, the lick output is set to NaN (trial otherwise retained).

**Rating:** better

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:54-56):
> The NWB `processing/ophys/Deconvolved/plane0/data` contains pre-computed deconvolved events. We do NOT need to compute dF/F from scratch.

**Code** (convert_data.py:341-360):
```python
planes = sorted(ophys['Deconvolved'].keys())

if len(planes) == 1:
    deconv_data = ophys['Deconvolved']['plane0']['data'][:]  # (n_samples, n_rois)
    fluor_data = ophys['Fluorescence']['plane0']['data'][:]
    neuropil_data = ophys['Neuropil']['plane0']['data'][:]
    n_planes = 1
else:
    # Multi-plane: concatenate ROIs across planes
    deconv_parts = []
    ...
    for plane in planes:
        deconv_parts.append(ophys['Deconvolved'][plane]['data'][:])
        ...
    deconv_data = np.concatenate(deconv_parts, axis=1)
```

**What this does:** Final neural data is taken from the NWB `processing/ophys/Deconvolved` group. Fluorescence and Neuropil are also loaded but only used for an interneuron-detection step.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:227-228):
> Multi-plane handling (m17, m18): Neurons from plane0 and plane1 concatenated. iscell filtering applied. Interneuron detection via Pearson correlation of dF/F with speed (threshold > 0.5).

**Code** (convert_data.py:411-421):
```python
# Create final neuron mask: iscell AND not interneuron
iscell_indices = np.where(iscell)[0]
non_interneuron = ~is_interneuron
final_neuron_mask = np.zeros(n_total_rois, dtype=bool)
final_neuron_mask[iscell_indices[non_interneuron]] = True

n_neurons = final_neuron_mask.sum()
n_interneurons = is_interneuron.sum()

# ---- Get deconvolved data for selected neurons ----
neural_all = deconv_data[:, final_neuron_mask]  # (n_samples, n_neurons)
```

NaN replacement after slicing (convert_data.py:518-521):
```python
trial_neural = neural_all[start:end, :].T.copy()
trial_neural[np.isnan(trial_neural)] = 0
```

**What this does:** Multi-plane ROIs are concatenated. Deconvolved data is filtered to iscell-positive ROIs that are not flagged as interneurons. NaN entries in the per-trial slice are zeroed.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:136-138):
> Neuron curation rules: 1. iscell from Suite2p manual curation. 2. Interneuron exclusion: Pearson correlation of dF/F with speed > 0.5

**Code** (convert_data.py:139-189):
```python
def identify_interneurons(dff, speed, iscell_mask):
    ...
    dff_cells = dff[:, iscell_mask]
    ...
    # Vectorized Pearson correlation
    X = dff_cells[valid, :]
    Y = speed[valid]
    ...
    cov_XY = (X_centered * Y_centered[:, np.newaxis]).sum(axis=0) / (n - 1)
    std_X = np.sqrt((X_centered ** 2).sum(axis=0) / (n - 1))
    std_Y = np.sqrt((Y_centered ** 2).sum() / (n - 1))
    ...
    r = cov_XY / (std_X * std_Y)
    is_interneuron = r > INTERNEURON_CORR_THRESHOLD
    return is_interneuron
```

Final mask combining both (convert_data.py:411-415):
```python
iscell_indices = np.where(iscell)[0]
non_interneuron = ~is_interneuron
final_neuron_mask = np.zeros(n_total_rois, dtype=bool)
final_neuron_mask[iscell_indices[non_interneuron]] = True
```

**What this does:** Two filters are applied: (1) the NWB `iscell` mask, and (2) interneuron exclusion based on Pearson correlation of dF/F (computed locally) with speed greater than 0.5.

**Rating:** better

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:195):
> Time bin = 1 imaging frame: ~64.5 ms (1/15.5078125 Hz). This matches the native temporal resolution.

**Code** (convert_data.py:25-26, 838-839):
```python
IMAGING_RATE = 15.5078125  # Hz
FRAME_PERIOD = 1.0 / IMAGING_RATE  # seconds
...
'time_bin_size': 1000.0 / IMAGING_RATE,  # ms per frame
```

**What this does:** No resampling; the data is kept at the native imaging frame rate of ~15.51 Hz, with `time_bin_size` recorded in metadata.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:840):
> 'temporal_alignment_event': 'start of each trial (first imaging frame on track after teleport)'

**Code** (convert_data.py:509-518):
```python
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    n_timepoints = end - start
    ...
    trial_neural = neural_all[start:end, :].T.copy()
```

**What this does:** Each trial's neural data is sliced from the trial-start frame index to the teleport index. No additional time-shift alignment is performed; alignment to the trial start is implicit in the slicing.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:184):
> Time from trial start | input[0] | seconds, time-varying | Computed from frame timestamps relative to trial start

**Code** (convert_data.py:524-525, 546):
```python
# [0] Time from trial start in seconds (time-varying)
time_from_start = np.arange(n_timepoints) * FRAME_PERIOD
...
trial_input[0, :] = time_from_start
```

**What this does:** Time within trial is derived from the per-trial timepoint count multiplied by the constant frame period (1 / 15.5078125 s); behavior timestamps are not used.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

**Notes excerpt** (CONVERSION_NOTES.md:184):
> Computed from frame timestamps relative to trial start

**Code** (convert_data.py:524-525):
```python
time_from_start = np.arange(n_timepoints) * FRAME_PERIOD
```

**What this does:** A numerical range `[0, 1, ..., n_timepoints-1]` is multiplied by the frame period to produce per-frame elapsed time within each trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:196):
> Temporal alignment: Align to trial start (first frame of each trial)

**Code** (convert_data.py:509-525):
```python
start = trial_starts[t]
end = teleports[t]
n_timepoints = end - start
...
trial_neural = neural_all[start:end, :].T.copy()
...
time_from_start = np.arange(n_timepoints) * FRAME_PERIOD
```

**What this does:** Both arrays use `n_timepoints = end - start` derived from the same trial boundaries, so input time and neural data share the same length and frame indexing by construction.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:91):
> environment: -1 pre-TTL, 0=ENV1, 1=ENV2

**Code** (convert_data.py:326, 487-495):
```python
environment = behav['environment']['data'][:]
...
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    env_vals = environment[start:end]
    valid_env = env_vals[env_vals >= 0]
    if len(valid_env) > 0:
        trial_env[t] = int(np.median(valid_env))
    else:
        trial_env[t] = 0
```

**What this does:** Pulled from the `environment` behavioral time series; per-trial value is the median of the (non-negative) samples within the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

**Notes excerpt** (CONVERSION_NOTES.md:182):
> Environment (0/1) | input[1] | binary per trial | environment in NWB | ENV1=0, ENV2=1

**Code** (convert_data.py:485-495, 547):
```python
trial_env = np.zeros(n_trials, dtype=np.int64)
for t in range(n_trials):
    ...
    env_vals = environment[start:end]
    valid_env = env_vals[env_vals >= 0]
    if len(valid_env) > 0:
        trial_env[t] = int(np.median(valid_env))
    else:
        trial_env[t] = 0
...
trial_input[1, :] = env_val  # broadcast per-trial
```

**What this does:** For each trial, takes the median of valid (non-negative) environment samples and broadcasts the per-trial scalar across all timepoints in the input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:183):
> Trial number | input[2] | continuous per trial | trial number in NWB | 0-indexed trial within session

**Code** (convert_data.py:530-531, 548):
```python
# [2] Trial number (per trial)
trial_num = float(t)
...
trial_input[2, :] = trial_num
```

**What this does:** Trial number is the loop index `t` over within-session trials (0-indexed), not the NWB `trial number` variable.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

**Notes excerpt** (none directly; CONVERSION_NOTES.md:183 lists it as "0-indexed trial within session").

**Code** (convert_data.py:530-548):
```python
trial_num = float(t)
...
trial_input[2, :] = trial_num
```

**What this does:** No processing other than casting the loop index to float and broadcasting it across all timepoints in the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:185):
> Previous trial outcome | input[3] | binary per trial (0=omitted, 1=rewarded) | Custom from Reward events | Check if previous trial had reward

**Code** (convert_data.py:330-331, 425-434):
```python
reward_data = behav['Reward']['data'][:]
reward_timestamps = behav['Reward']['timestamps'][:]
behav_timestamps = behav['position']['timestamps'][:]
...
reward_frame_indices = np.searchsorted(behav_timestamps, reward_timestamps)
reward_frame_indices = np.clip(reward_frame_indices, 0, n_samples - 1)

trial_rewarded = np.zeros(n_trials, dtype=bool)
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    trial_rewards = np.any((reward_frame_indices >= start) & (reward_frame_indices < end))
    trial_rewarded[t] = trial_rewards
```

**What this does:** Derived from the NWB `Reward` event timestamps (mapped to frame indices via `searchsorted` against position timestamps), then a per-trial boolean array of whether any reward fell in each trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:185):
> Check if previous trial had reward

**Code** (convert_data.py:497-501, 549):
```python
prev_trial_outcome = np.zeros(n_trials, dtype=np.int64)
for t in range(1, n_trials):
    prev_trial_outcome[t] = int(trial_rewarded[t - 1])
# First trial: no previous, default to 0 (unknown/omitted)
...
trial_input[3, :] = prev_outcome
```

**What this does:** For each trial, looks up the previous trial's `trial_rewarded` boolean and casts to int; the first trial gets 0. Value broadcast across all timepoints.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:189, 198):
> Distance to reward zone | output[0] | from position + reward zone. Reward zone identification: Infer from position where reward_zone>0 in NWB data. Map to A (80-130), B (200-250), C (320-370) based on position range.

**Code** (convert_data.py:192-218):
```python
def identify_reward_zone(position, reward_zone_signal, trial_start, trial_end):
    pos_trial = position[trial_start:trial_end]
    rz_trial = reward_zone_signal[trial_start:trial_end]
    in_rz = rz_trial > 0
    if not np.any(in_rz):
        return None
    rz_pos = pos_trial[in_rz]
    mean_rz_pos = np.mean(rz_pos)
    best_zone = None
    best_dist = np.inf
    for zone_name, (zone_start, zone_end) in REWARD_ZONES.items():
        zone_center = (zone_start + zone_end) / 2
        dist = abs(mean_rz_pos - zone_center)
        if dist < best_dist:
            best_dist = dist
            best_zone = zone_name
    return best_zone
```

Distance computation (convert_data.py:221-239):
```python
def compute_distance_to_reward_zone(position, rz_start, rz_end):
    distance = np.zeros_like(position)
    before = position < rz_start
    inside = (position >= rz_start) & (position <= rz_end)
    after = position > rz_end
    distance[before] = position[before] - rz_start
    distance[inside] = 0.0
    distance[after] = position[after] - rz_end
    return distance
```

**What this does:** Reward zone label per trial is inferred from the mean `position` value when `reward_zone > 0`, mapped by nearest zone center to A/B/C. Distance is then signed (negative before, 0 inside, positive after) relative to the chosen zone bounds.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

**Notes excerpt** (CONVERSION_NOTES.md:199):
> Distance to reward zone: Signed distance from animal position to nearest edge of reward zone. Negative = before zone, positive = past zone, 0 = within zone

**Code** (convert_data.py:221-239, 556-558):
```python
def compute_distance_to_reward_zone(position, rz_start, rz_end):
    distance = np.zeros_like(position)
    before = position < rz_start
    inside = (position >= rz_start) & (position <= rz_end)
    after = position > rz_end
    distance[before] = position[before] - rz_start
    distance[inside] = 0.0
    distance[after] = position[after] - rz_end
    return distance
...
dist_to_rz = compute_distance_to_reward_zone(trial_pos, trial_rz_start[t], trial_rz_end[t])
dist_bins = discretize_distance(dist_to_rz)
```

**What this does:** For each timepoint computes signed distance to the trial's identified reward zone (negative before, 0 inside, positive after), then discretizes into bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md:185):
> Bins: <-50, -50 to -10, -10 to 0, 0, >0 to +10, +10 to +50, >+50

**Code** (convert_data.py:242-263):
```python
def discretize_distance(distance):
    """
    Discretize distance to reward zone into 7 bins:
    0: < -50 cm
    1: -50 to -10 cm
    2: -10 cm to < 0 cm
    3: 0 cm (in reward zone)
    4: >0 cm to +10 cm
    5: +10 to +50 cm
    6: > +50 cm
    """
    bins = np.zeros(len(distance), dtype=np.int64)
    bins[distance < -50] = 0
    bins[(distance >= -50) & (distance < -10)] = 1
    bins[(distance >= -10) & (distance < 0)] = 2
    bins[distance == 0] = 3
    bins[(distance > 0) & (distance <= 10)] = 4
    bins[(distance > 10) & (distance <= 50)] = 5
    bins[distance > 50] = 6
    return bins
```

**What this does:** Custom branching assigns one of 7 integer bins, with bin 3 reserved for distance exactly equal to 0 (i.e., samples inside the reward zone).

**Rating:** match

**Note:** _(no note)_

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

**Notes excerpt** (none directly).

**Code** (convert_data.py:510-557):
```python
start = trial_starts[t]
end = teleports[t]
...
trial_neural = neural_all[start:end, :].T.copy()
...
trial_pos = position[start:end]
...
dist_to_rz = compute_distance_to_reward_zone(trial_pos, trial_rz_start[t], trial_rz_end[t])
```

**What this does:** Position and neural slices use the same `start:end` indices from the same trial boundaries, so timepoints are aligned by construction.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:186):
> Absolute position | output[1] | position in NWB

**Code** (convert_data.py:319, 552):
```python
position = behav['position']['data'][:]
...
trial_pos = position[start:end]
```

**What this does:** Taken directly from the `position` behavioral time series.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

**Notes excerpt** (CONVERSION_NOTES.md:186):
> Discretized to 5 equal bins (90 cm each)

**Code** (convert_data.py:286-296, 561):
```python
def discretize_position(position):
    """
    Discretize position into 5 equal bins of 90 cm each.
    0: 0-90 cm
    1: 90-180 cm
    2: 180-270 cm
    3: 270-360 cm
    4: 360-450 cm
    """
    bins = np.clip(np.floor(position / 90.0).astype(np.int64), 0, 4)
    return bins
...
pos_bins = discretize_position(trial_pos)
```

**What this does:** Position values are divided by 90 and floored, with the result clipped to [0, 4]; no other transformation.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md:186):
> Bins: 0-90, 90-180, 180-270, 270-360, 360-450

**Code** (convert_data.py:286-296):
```python
bins = np.clip(np.floor(position / 90.0).astype(np.int64), 0, 4)
```

**What this does:** Floor-divides the position by 90 cm and clips to a 5-bin range. Negative pre-trial values (e.g., -500 placeholder) and values >450 collapse into the end bins via clipping.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

**Notes excerpt** (none directly).

**Code** (convert_data.py:510-561):
```python
start = trial_starts[t]
end = teleports[t]
...
trial_pos = position[start:end]
...
pos_bins = discretize_position(trial_pos)
```

**What this does:** Same `start:end` slicing as the neural data; alignment is by shared indexing.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:188):
> Lick | output[3] | Binary, time-varying | lick in NWB binarized

**Code** (convert_data.py:321, 471):
```python
lick = behav['lick']['data'][:]
...
lick_binary = np.clip(lick, 0, 1).astype(np.float64)
```

**What this does:** Taken from the NWB `lick` behavioral time series (cumulative lick count).

**Rating:** match

**Note:** _(no note)_

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

**Notes excerpt** (CONVERSION_NOTES.md:48-49, 142):
> Lick binarization: After correction, licks > 1 set to 1 (binary). Lick error correction: If >35% of samples in a trial have cumulative lick count >2, lick data for that trial set to NaN.

**Code** (convert_data.py:469-483, 554, 567):
```python
lick_binary = np.clip(lick, 0, 1).astype(np.float64)

lick_error_trials = []
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    trial_lick = lick[start:end]
    if len(trial_lick) > 0:
        frac_bad = np.sum(trial_lick > 2) / len(trial_lick)
        if frac_bad > LICK_ERROR_FRACTION:
            lick_binary[start:end] = np.nan
            lick_error_trials.append(t)
...
trial_lick = lick_binary[start:end]
...
lick_vals = np.where(np.isnan(trial_lick), 0, trial_lick).astype(np.int64)
```

**What this does:** Clips `lick` to [0, 1] for binarization, NaN-masks trials with >35% bad samples, then for output replaces NaN with 0 and casts to int.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

**Notes excerpt** (none directly).

**Code** (convert_data.py:510-554):
```python
start = trial_starts[t]
end = teleports[t]
...
trial_lick = lick_binary[start:end]
```

**What this does:** Same `start:end` slicing as neural; alignment by shared trial indexing.

**Rating:** match

**Note:** _(no note)_

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:189):
> Reward zone location | output[4] | Categorical per trial (0=A,1=B,2=C) | Inferred from position where rz>0

**Code** (convert_data.py:436-467):
```python
trial_rz_label = []
trial_rz_start = np.zeros(n_trials)
trial_rz_end = np.zeros(n_trials)

last_known_zone = None
for t in range(n_trials):
    zone = identify_reward_zone(position, reward_zone_signal, trial_starts[t], teleports[t])
    if zone is not None:
        last_known_zone = zone
    trial_rz_label.append(zone if zone is not None else last_known_zone)

# Fill backward for any leading None values
if trial_rz_label[0] is None:
    for t in range(n_trials):
        if trial_rz_label[t] is not None:
            for tt in range(t):
                trial_rz_label[tt] = trial_rz_label[t]
            break
...
rz_label_to_idx = {'A': 0, 'B': 1, 'C': 2}
trial_rz_idx = np.array([rz_label_to_idx.get(lbl, 0) for lbl in trial_rz_label])
```

**What this does:** Derived from the `reward_zone` and `position` behavioral time series. Per trial, the mean position when `reward_zone > 0` is used to pick the closest zone center (A/B/C). Trials with no reward-zone entry inherit the previous trial's label (with backfill for leading missing).

**Rating:** match

**Note:** _(no note)_

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

**Notes excerpt** (CONVERSION_NOTES.md:198):
> Reward zone identification: Infer from position where reward_zone>0 in NWB data. Map to A (80-130), B (200-250), C (320-370) based on position range.

**Code** (convert_data.py:36-40, 192-218, 569-583):
```python
REWARD_ZONES = {
    'A': (80, 130),
    'B': (200, 250),
    'C': (320, 370),
}
...
def identify_reward_zone(position, reward_zone_signal, trial_start, trial_end):
    ...
    rz_pos = pos_trial[in_rz]
    mean_rz_pos = np.mean(rz_pos)
    best_zone = None
    best_dist = np.inf
    for zone_name, (zone_start, zone_end) in REWARD_ZONES.items():
        zone_center = (zone_start + zone_end) / 2
        dist = abs(mean_rz_pos - zone_center)
        if dist < best_dist:
            best_dist = dist
            best_zone = zone_name
    return best_zone
...
rz_loc = trial_rz_idx[t]
...
trial_output[4, :] = rz_loc  # broadcast per-trial
```

**What this does:** Mean position during reward-zone-active samples is mapped to the nearest of three hardcoded zone centers; zones are mapped to integers (A=0, B=1, C=2) and broadcast across all timepoints in the output.

**Rating:** match

**Note:** _(no note)_

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:190):
> Reward outcome | output[5] | Binary per trial | From Reward events | 0=no reward, 1=rewarded

**Code** (convert_data.py:330-332, 425-434):
```python
reward_data = behav['Reward']['data'][:]
reward_timestamps = behav['Reward']['timestamps'][:]
behav_timestamps = behav['position']['timestamps'][:]
...
reward_frame_indices = np.searchsorted(behav_timestamps, reward_timestamps)
reward_frame_indices = np.clip(reward_frame_indices, 0, n_samples - 1)

trial_rewarded = np.zeros(n_trials, dtype=bool)
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    trial_rewards = np.any((reward_frame_indices >= start) & (reward_frame_indices < end))
    trial_rewarded[t] = trial_rewards
```

**What this does:** Derived from the NWB `Reward` event group; reward event timestamps are converted to frame indices via `searchsorted` against position timestamps.

**Rating:** match

**Note:** _(no note)_

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:190):
> Binary per trial. From Reward events.

**Code** (convert_data.py:425-434, 572-584):
```python
reward_frame_indices = np.searchsorted(behav_timestamps, reward_timestamps)
reward_frame_indices = np.clip(reward_frame_indices, 0, n_samples - 1)

trial_rewarded = np.zeros(n_trials, dtype=bool)
for t in range(n_trials):
    ...
    trial_rewards = np.any((reward_frame_indices >= start) & (reward_frame_indices < end))
    trial_rewarded[t] = trial_rewards
...
reward_out = int(trial_rewarded[t])
...
trial_output[5, :] = reward_out  # broadcast per-trial
```

**What this does:** A trial is marked rewarded if any reward event's frame index falls within its `[start, end)`; the per-trial 0/1 is broadcast across all timepoints.

**Rating:** match

**Note:** _(no note)_

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:236-237):
> Shape mismatch fix: For multi-plane animals, behavioral and neural data can differ by 1 frame; truncated to common length.

**Code** (convert_data.py:364-382, 396-399, 449-455, 514, 521):
```python
n_behav_samples = len(position)
n_neural_samples = deconv_data.shape[0]
n_samples = min(n_behav_samples, n_neural_samples)
if n_behav_samples != n_neural_samples:
    position = position[:n_samples]
    speed = speed[:n_samples]
    ...
    deconv_data = deconv_data[:n_samples, :]
    ...

# Trial-pair sanity
valid = teleports > trial_starts
trial_starts = trial_starts[valid]
teleports = teleports[valid]

# Missing reward zone inherits previous trial label
last_known_zone = None
for t in range(n_trials):
    zone = identify_reward_zone(...)
    if zone is not None:
        last_known_zone = zone
    trial_rz_label.append(zone if zone is not None else last_known_zone)

# Short trial skip
if n_timepoints < 5:
    continue

# Replace NaN in neural data
trial_neural[np.isnan(trial_neural)] = 0
```

**What this does:** Length mismatch between behavior and neural is resolved by truncating to the minimum. Trial-start/teleport pairs where teleport precedes start are dropped. Trials with no reward-zone entry inherit the previous trial's zone label. Trials shorter than 5 frames are skipped. NaN entries in neural and lick data are replaced by 0.

**Rating:** match

**Note:** _(no note)_

---

## Q 13-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:239-240):
> Vectorized interneuron detection (matrix correlation instead of per-neuron loop): 4.3s -> 0.4s per session. Full conversion: ~879s (~14.6 min) for 152 sessions.

**Code** (convert_data.py:362, 402-408):
```python
t_load = time.time() - t0
...
t1 = time.time()
dff = compute_dff(fluor_data, neuropil_data, trial_starts, teleports)
t_dff = time.time() - t1

t1 = time.time()
is_interneuron = identify_interneurons(dff, speed, iscell)
t_int = time.time() - t1
```

Per-session timing logged (convert_data.py:907-910):
```python
for info in data['metadata']['session_info']:
    print(f"  {info['subject']} ses-{info['session']}: "
          f"load={info['load_time']:.1f}s, dff={info['dff_time']:.1f}s, "
          f"int={info['interneuron_time']:.1f}s, total={info['total_time']:.1f}s")
```

**What this does:** Code instruments load time, dF/F computation time, and interneuron-detection time per session, printed at the end. Notes report ~14.6 min for full 152-session conversion.

**Rating:** match

**Note:** _(no note)_

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md:239):
> Vectorized interneuron detection (matrix correlation instead of per-neuron loop): 4.3s -> 0.4s per session.

**Code** (convert_data.py:139-189):
```python
def identify_interneurons(dff, speed, iscell_mask):
    ...
    X = dff_cells[valid, :]
    Y = speed[valid]
    X_centered = X - X_mean
    Y_centered = Y - Y_mean
    cov_XY = (X_centered * Y_centered[:, np.newaxis]).sum(axis=0) / (n - 1)
    std_X = np.sqrt((X_centered ** 2).sum(axis=0) / (n - 1))
    ...
    r = cov_XY / (std_X * std_Y)
```

Remaining per-trial loops (convert_data.py:115, 430, 442-447, 475, 487, 499, 509):
```python
for i, (start, stop) in enumerate(zip(trial_starts, teleports)):  # in compute_dff
for t in range(n_trials):  # multiple per-trial loops
```

**What this does:** Notes mention vectorization of interneuron-detection. Multiple per-trial loops remain (dF/F baseline, reward-event-in-trial check, lick-error check, environment median, reward-zone identification, trial-data assembly).

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-c. What processing does the code repeat multiple times?

**Notes excerpt** (none directly).

**Code** (convert_data.py:475, 487, 499, 509-512):
```python
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    trial_lick = lick[start:end]
    ...
for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    env_vals = environment[start:end]
    ...
for t in range(1, n_trials):
    prev_trial_outcome[t] = int(trial_rewarded[t - 1])

for t in range(n_trials):
    start = trial_starts[t]
    end = teleports[t]
    n_timepoints = end - start
```

**What this does:** Several separate per-trial loops each re-iterate over `range(n_trials)` and re-extract `trial_starts[t]`/`teleports[t]` slices, rather than accumulating all per-trial outputs in a single pass.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (none directly).

**Code** (convert_data.py:330, 619-625):
```python
reward_data = behav['Reward']['data'][:]   # loaded but only timestamps used
...
if show_processing and session_idx < 2:
    plot_processing(filepath, subject_id, session_id,
                    position, speed, lick_binary, trial_starts, teleports,
                    neural_all, trial_rz_start, trial_rz_end,
                    trial_rewarded, trial_env, valid_trials,
                    neural_trials, input_trials, output_trials,
                    session_idx)
```

Also `scanning` is loaded (convert_data.py:327) but not used in output construction:
```python
scanning = behav['scanning']['data'][:]
```

**What this does:** Loads `Reward['data']` (amounts) and `scanning` arrays that are not used in any output computation; also generates optional diagnostic plots when `--show-processing` is set. dF/F is computed from raw fluorescence solely for interneuron detection and otherwise discarded.

**Rating:** match

**Note:** _(no note)_

---
