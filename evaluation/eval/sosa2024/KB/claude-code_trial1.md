# sosa2024 — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/sosa2024/claude/2026-03-10__19-44-11_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:90-117):
> NWB files organized as: `data/sub-{mouse}/sub-{mouse}_ses-{session}_behavior+ophys.nwb`
> Subjects: 11 (m3, m4, m7, m11-m15, m17-m19); Total sessions: 152

**Code** (convert_data.py:644-677):
```python
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
nwb_files = sorted(glob.glob(os.path.join(data_dir, 'sub-*', '*.nwb')))
...
for nwb_path in nwb_files:
    fname = os.path.basename(nwb_path)
    session_label = fname.replace('_behavior+ophys.nwb', '')
    result = process_session(
        nwb_path,
        show_processing=args.show_processing and session_count < 2,
        session_label=session_label
    )
    if result is not None:
        all_sessions.append(result)
        subjects_set.add(result['subject_id'])
```

**What this does:** Globs all `*.nwb` files inside `data/sub-*/` directories and iterates over each, calling `process_session` to load the NWB via `h5py.File`. Subjects are derived from the `subject_id` metadata inside each NWB file.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:90, 111):
> Subjects: 11 (m3, m4, m7, m11-m15, m17-m19); subject derived from NWB `general/subject/subject_id`

**Code** (convert_data.py:295, 676, 684, 697):
```python
subject_id = f['general/subject/subject_id'][()].decode()
...
subjects_set.add(result['subject_id'])
...
subjects = sorted(subjects_set)
...
subject_idx.append(subjects.index(sess['subject_id']))
```

**What this does:** Reads `subject_id` from each NWB's `general/subject/subject_id` metadata, accumulates a set of unique IDs, and assigns each session a `subject_idx` based on a sorted subjects list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:90):
> NWB files organized as: `data/sub-{mouse}/sub-{mouse}_ses-{session}_behavior+ophys.nwb`

**Code** (convert_data.py:296, 646, 665-666):
```python
session_id = f['general/session_id'][()].decode()
...
nwb_files = sorted(glob.glob(os.path.join(data_dir, 'sub-*', '*.nwb')))
...
fname = os.path.basename(nwb_path)
session_label = fname.replace('_behavior+ophys.nwb', '')
```

**What this does:** Each NWB file in a subject directory is treated as one session. The `session_id` is read from the NWB metadata; one `process_session` call per file produces one entry in the all_sessions list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:225):
> Identify trials: From trial_start and teleport indices

**Code** (convert_data.py:309-310, 380-391):
```python
trial_start_flag = bts['trial_start/data'][:]
teleport_flag = bts['teleport/data'][:]
...
trial_start_inds = np.where(trial_start_flag > 0)[0]
teleport_inds = np.where(teleport_flag > 0)[0]
n_trials = min(len(trial_start_inds), len(teleport_inds))
if n_trials < 2:
    print(f"  Skipping {session_label}: only {n_trials} trials")
    return None
trial_start_inds = trial_start_inds[:n_trials]
teleport_inds = teleport_inds[:n_trials]
```

**What this does:** Trial boundaries are derived from the `trial_start` and `teleport` behavioral timeseries flags, taking indices where each flag is positive. The minimum count of starts/ends is used to align them.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:155-164):
> Lick sensor error: trials with >35% of samples having cumulative lick count >2 get licks set to NaN; Only include frames within trial boundaries

**Code** (convert_data.py:441-447, 461-462):
```python
if e <= s or (e - s) < 2:
    # Still need to track prev_trial_rewarded
    trial_start_time = pos_timestamps[s] if s < len(pos_timestamps) else 0
    trial_end_time = pos_timestamps[min(e, len(pos_timestamps) - 1)]
    was_rewarded = detect_reward_in_trial(reward_timestamps, trial_start_time, trial_end_time)
    prev_trial_rewarded = int(was_rewarded)
    continue
...
if np.sum(trial_lick > 2) / n_t > LICK_ERROR_FRACTION_THRESHOLD:
    trial_lick[:] = 0  # set to 0 instead of NaN for decoder output
```

**What this does:** Trials shorter than 2 timepoints are skipped. Trials whose fraction of samples with cumulative lick > 2 exceeds 35% have their licks zeroed out (a lick-sensor error correction) but are otherwise retained.

**Rating:** better

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:71-72, 230):
> The reference decoder (Fig3) uses deconvolved events, NOT dF/F. Neural data = deconvolved events: NWB has them pre-computed

**Code** (convert_data.py:328-342, 400, 424):
```python
deconv_list = []
...
for pi, plane_name in enumerate(fluor_planes):
    deconv_data = ophys[f'Deconvolved/{plane_name}/data'][:]
    ...
    deconv_list.append(deconv_data)
deconv_all = np.concatenate(deconv_list, axis=1)
...
deconv_cells = deconv_all[:, cell_mask].T
...
neural_data = deconv_cells[final_cell_mask]
```

**What this does:** Neural data uses the pre-computed `Deconvolved/plane{N}/data` arrays from NWB, concatenated across planes for multi-plane recordings.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:267-270):
> dF/F computation for interneuron detection (maximin baseline, neuropil subtraction); Deconvolved events as neural data (pre-computed in NWB)

**Code** (convert_data.py:333-344, 396-409):
```python
for pi, plane_name in enumerate(fluor_planes):
    deconv_data = ophys[f'Deconvolved/{plane_name}/data'][:]
    F_data = ophys[f'Fluorescence/{plane_name}/data'][:]
    Fneu_data = ophys[f'Neuropil/{plane_name}/data'][:]
    ...
deconv_all = np.concatenate(deconv_list, axis=1)
F_all = np.concatenate(F_list, axis=1)
Fneu_all = np.concatenate(Fneu_list, axis=1)
...
F_cells = F_all[:, cell_mask].T
Fneu_cells = Fneu_all[:, cell_mask].T
deconv_cells = deconv_all[:, cell_mask].T
dff_full = np.full_like(F_cells, np.nan)
for i in range(n_trials):
    s = trial_start_inds[i]; e = teleport_inds[i]
    if e <= s: continue
    dff_full[:, s:e] = compute_dff_trial(F_cells[:, s:e], Fneu_cells[:, s:e])
```

**What this does:** Concatenates deconvolved data from multiple planes. The deconvolved values themselves are not further processed and are passed through as the final neural data; dF/F is computed only for downstream interneuron detection.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:156-159, 268):
> iscell column 0 == 1 means cell is included; Interneuron exclusion: Pearson correlation of dF/F with speed > 0.5

**Code** (convert_data.py:321, 372-377, 411-424):
```python
iscell = ophys['ImageSegmentation/PlaneSegmentation/iscell'][:]
...
cell_mask = iscell[:, 0].astype(bool)
n_cells_iscell = cell_mask.sum()
if n_cells_iscell < 2:
    print(f"  Skipping {session_label}: only {n_cells_iscell} cells after iscell filter")
    return None
...
is_interneuron = detect_interneurons(dff_full, speed)
n_interneurons = is_interneuron.sum()
final_cell_mask = ~is_interneuron
n_final_cells = final_cell_mask.sum()
...
neural_data = deconv_cells[final_cell_mask]
```

**What this does:** First filter is the suite2p `iscell` flag (column 0). Then a vectorized Pearson correlation between per-cell dF/F and speed identifies putative interneurons (corr > 0.5), which are excluded.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:741):
> 'temporal_alignment_event': 'Start of trial (entry to linear track)'

**Code** (convert_data.py:437-453):
```python
for i in range(n_trials):
    s = trial_start_inds[i]
    e = teleport_inds[i]
    ...
    trial_neural = neural_data[:, s:e]
```

**What this does:** Each trial's neural data is the slice from `trial_start_inds[i]` to `teleport_inds[i]`, so timepoint 0 corresponds to the trial start. No additional alignment offset is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:227, 232):
> Time bin = imaging frame: ~64.5 ms per frame at ~15.5 Hz. This matches the native sampling rate.

**Code** (convert_data.py:367-370):
```python
n_planes = len(fluor_planes)
effective_rate = imaging_rate if n_planes == 1 else imaging_rate / n_planes
time_bin_ms = 1000.0 / effective_rate
```

**What this does:** Neural data is kept at the native imaging frame rate; for multi-plane recordings the effective per-plane rate is `imaging_rate / n_planes`. No resampling or rebinning is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:208):
> Time from trial start | input[0] | (t - trial_start) / imaging_rate, continuous seconds

**Code** (convert_data.py:474, 502):
```python
time_from_start = (np.arange(n_t) / effective_rate).astype(np.float32)
...
input_arr[0, :] = time_from_start
```

**What this does:** Time is computed from a numerical index (0..n_t-1) divided by the effective imaging rate, rather than from any stored timestamp variable.

**Rating:** concerning

**Note:** does not use timestamps, assumes they are evenly collected. data looks consistent, so probably ok

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

**Notes excerpt** (CONVERSION_NOTES.md:208):
> (t - trial_start) / imaging_rate, continuous seconds

**Code** (convert_data.py:474):
```python
time_from_start = (np.arange(n_t) / effective_rate).astype(np.float32)
```

**What this does:** Generates an arange of length `n_t` and divides by the effective imaging rate (per-plane rate for multi-plane sessions) to produce seconds from trial start.

**Rating:** concerning

**Note:** does not use timestamps, assumes they are evenly collected. data looks consistent, so probably ok

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:152):
> all behavioral and neural data at ~15.5 Hz frame rate, already synchronized

**Code** (convert_data.py:347-363, 474):
```python
n_timepoints_neural = deconv_all.shape[0]
n_timepoints_behav = len(position)
n_timepoints_total = min(n_timepoints_neural, n_timepoints_behav)
if n_timepoints_neural != n_timepoints_behav:
    deconv_all = deconv_all[:n_timepoints_total]
    ...
time_from_start = (np.arange(n_t) / effective_rate).astype(np.float32)
```

**What this does:** Neural and behavioral timeseries are first cropped to the shorter of the two so they share indices. Time is computed from index using the same effective rate as the neural data, so they share the same time base.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:209):
> Environment (morph) | input[1] | 0=ENV1, 1=ENV2 | From `environment` behavioral TS

**Code** (convert_data.py:311, 454, 477-478):
```python
environment = bts['environment/data'][:]
...
trial_env = environment[s:e]
...
env_val = np.median(trial_env[trial_env >= 0]) if np.any(trial_env >= 0) else 0.0
env_type = np.float32(env_val)
```

**What this does:** Reads the `environment` behavioral timeseries; per trial takes the median of non-negative samples as a scalar environment label.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

**Notes excerpt** (CONVERSION_NOTES.md:209):
> 0=ENV1, 1=ENV2, per-trial scalar

**Code** (convert_data.py:477-478, 503):
```python
env_val = np.median(trial_env[trial_env >= 0]) if np.any(trial_env >= 0) else 0.0
env_type = np.float32(env_val)
...
input_arr[1, :] = env_type  # broadcast
```

**What this does:** Filters out negative samples, takes the median of remaining samples for the trial, and broadcasts the scalar across all timepoints in the trial.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:210):
> Trial number within session | input[2] | 0-indexed, per-trial scalar | From `trial number` behavioral TS

**Code** (convert_data.py:437, 481, 504):
```python
for i in range(n_trials):
    ...
    trial_number = np.float32(i)
    ...
    input_arr[2, :] = trial_number  # broadcast
```

**What this does:** Trial number is the loop index `i` (0-indexed) over detected trial boundaries, not the stored `trial number` timeseries values from NWB.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

**Notes excerpt** (CONVERSION_NOTES.md:210):
> per-trial scalar

**Code** (convert_data.py:481, 504):
```python
trial_number = np.float32(i)
...
input_arr[2, :] = trial_number  # broadcast
```

**What this does:** Casts the loop index to float32 and broadcasts it across every timepoint in the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:211):
> Previous trial outcome | input[3] | 0=omitted, 1=rewarded | From reward detection in previous trial

**Code** (convert_data.py:316, 278-282, 467-470):
```python
reward_timestamps = bts['Reward/timestamps'][:]
...
def detect_reward_in_trial(reward_timestamps, trial_start_time, trial_end_time):
    if len(reward_timestamps) == 0:
        return False
    return np.any((reward_timestamps >= trial_start_time) & (reward_timestamps <= trial_end_time))
...
trial_start_time = trial_timestamps[0]
trial_end_time = trial_timestamps[-1]
was_rewarded = detect_reward_in_trial(reward_timestamps, trial_start_time, trial_end_time)
```

**What this does:** Uses `Reward/timestamps` from the NWB BehavioralTimeSeries; checks whether any reward timestamp falls within each trial's start and end time.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:211):
> 0=omitted, 1=rewarded, per-trial scalar

**Code** (convert_data.py:435, 484, 505, 545):
```python
prev_trial_rewarded = 0  # For the first trial, assume no previous reward
...
prev_outcome = np.float32(prev_trial_rewarded)
...
input_arr[3, :] = prev_outcome  # broadcast
...
# Update previous trial reward
prev_trial_rewarded = int(was_rewarded)
```

**What this does:** A running variable tracks whether the previous trial was rewarded; first trial defaults to 0. After each trial the variable is updated to the current trial's reward outcome and the value is broadcast across all timepoints of the next trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:213-216):
> Distance to reward zone | output[0] | Discretized into 7 bins | Compute from position and reward zone coords

**Code** (convert_data.py:30-34, 297-299, 70-133, 304, 393-394, 509-510):
```python
REWARD_ZONE_DICT = {'A': [80, 130], 'B': [200, 250], 'C': [320, 370]}
...
identifier = f['identifier'][()].decode()
scene = get_scene_from_identifier(identifier)
...
def get_reward_zones(scene, n_trials, change_trial=DEFAULT_CHANGE_TRIAL):
    ...
    if 'Location' in scene and '_to' not in scene:
        loc = scene.split('Location')[-1]
        rz_coords[:] = REWARD_ZONE_DICT[loc]
    elif 'A_to' in scene and scene[-1] == 'B':
        rz_coords[:change_trial] = REWARD_ZONE_DICT['A']
        rz_coords[change_trial:] = REWARD_ZONE_DICT['B']
    ...
position = bts['position/data'][:]
...
rz_coords, rz_labels = get_reward_zones(scene, n_trials)
...
rz_start, rz_end = rz_coords[i]
dist_to_rz = compute_distance_to_reward_zone(trial_pos, rz_start, rz_end)
```

**What this does:** Reward zone coordinates come from a hardcoded dict (A/B/C from paper), with the per-trial zone determined by parsing the NWB `identifier` scene name (assuming switch occurs at trial 30). Distance is computed from the `position` timeseries against these coordinates. The `reward_zone` behavioral timeseries is not used.

**Rating:** ok

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

**Notes excerpt** (CONVERSION_NOTES.md:240):
> Distance = position - nearest_reward_zone_edge (signed, negative=before, 0=in zone)

**Code** (convert_data.py:212-223):
```python
def compute_distance_to_reward_zone(position, rz_start, rz_end):
    dist = np.zeros_like(position)
    before = position < rz_start
    inside = (position >= rz_start) & (position <= rz_end)
    after = position > rz_end
    dist[before] = position[before] - rz_start  # negative
    dist[inside] = 0.0
    dist[after] = position[after] - rz_end  # positive
    return dist
```

**What this does:** Per-timepoint signed distance to the reward zone: negative before the zone, zero inside, positive after.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md:239-240):
> 7 bins: < -50, [-50,-10], [-10,0), 0, (0,10], [10,50], > 50 cm

**Code** (convert_data.py:226-244, 511):
```python
def discretize_distance_to_rz(dist):
    out = np.zeros(len(dist), dtype=np.int64)
    out[dist < -50] = 0
    out[(dist >= -50) & (dist < -10)] = 1
    out[(dist >= -10) & (dist < 0)] = 2
    out[dist == 0] = 3
    out[(dist > 0) & (dist <= 10)] = 4
    out[(dist > 10) & (dist <= 50)] = 5
    out[dist > 50] = 6
    return out
...
dist_to_rz_binned = discretize_distance_to_rz(dist_to_rz)
```

**What this does:** Maps signed distance to one of 7 integer bins via boolean indexing, with bin 3 reserved for samples exactly inside (distance == 0).

**Rating:** ok

**Note:** _(no note)_

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:152):
> all behavioral and neural data at ~15.5 Hz frame rate, already synchronized

**Code** (convert_data.py:438-453, 510, 532):
```python
s = trial_start_inds[i]
e = teleport_inds[i]
...
trial_pos = position[s:e]
...
trial_neural = neural_data[:, s:e]
...
dist_to_rz = compute_distance_to_reward_zone(trial_pos, rz_start, rz_end)
...
output_arr[0, :] = dist_to_rz_binned
```

**What this does:** Position and neural arrays are sliced with the same `[s:e]` indices, sharing the same time base after the upstream length-equalization step.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:212):
> Absolute position | output[1] | From `position` behavioral TS

**Code** (convert_data.py:304, 450):
```python
position = bts['position/data'][:]
...
trial_pos = position[s:e]
```

**What this does:** Reads `position/data` from the NWB BehavioralTimeSeries.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

**Notes excerpt** (CONVERSION_NOTES.md:212):
> Discretized into 5 equal bins (90cm each), time-varying

**Code** (convert_data.py:514, 247-252):
```python
pos_binned = discretize_position(trial_pos)
...
def discretize_position(position, n_bins=POSITION_BINS):
    bin_edges = np.linspace(0, TRACK_LENGTH, n_bins + 1)
    binned = np.digitize(position, bin_edges) - 1
    binned = np.clip(binned, 0, n_bins - 1)
    return binned
```

**What this does:** Per-trial slice is digitized directly with no further preprocessing of the raw position values.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md:242):
> Absolute position (5 bins): [0,90), [90,180), [180,270), [270,360), [360,450] cm

**Code** (convert_data.py:42-44, 247-252):
```python
POSITION_BINS = 5  # equal-size bins over [0, 450]
POSITION_BIN_EDGES = np.linspace(0, TRACK_LENGTH, POSITION_BINS + 1)
...
def discretize_position(position, n_bins=POSITION_BINS):
    bin_edges = np.linspace(0, TRACK_LENGTH, n_bins + 1)
    binned = np.digitize(position, bin_edges) - 1
    binned = np.clip(binned, 0, n_bins - 1)
    return binned
```

**What this does:** Uses `np.linspace(0, 450, 6)` to create 5 equal-width bins over the assumed track length, with values clipped to [0, 4].

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:152):
> all behavioral and neural data at ~15.5 Hz frame rate, already synchronized

**Code** (convert_data.py:438-453, 514, 533):
```python
s = trial_start_inds[i]
e = teleport_inds[i]
trial_pos = position[s:e]
trial_neural = neural_data[:, s:e]
...
pos_binned = discretize_position(trial_pos)
...
output_arr[1, :] = pos_binned
```

**What this does:** Position and neural arrays are indexed with the same trial slice `[s:e]`, sharing time bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:213):
> Lick | output[3] | Binary 0/1, time-varying | From `lick` behavioral TS, cap at 1

**Code** (convert_data.py:306, 452):
```python
lick_raw = bts['lick/data'][:]
...
trial_lick = lick[s:e].copy()
```

**What this does:** Reads the `lick/data` behavioral timeseries.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

**Notes excerpt** (CONVERSION_NOTES.md:151, 162):
> if >35% of samples in trial have cumulative lick >2, set trial licks to NaN; then cap at 1

**Code** (convert_data.py:459-465):
```python
# Lick sensor error correction (from reference code):
# if >35% of samples have cumulative lick count > 2, set licks to NaN for this trial
if np.sum(trial_lick > 2) / n_t > LICK_ERROR_FRACTION_THRESHOLD:
    trial_lick[:] = 0  # set to 0 instead of NaN for decoder output
# Cap licks at 1 (binary)
trial_lick[trial_lick > 1] = 1
trial_lick = (trial_lick > 0).astype(np.float32)
```

**What this does:** Detects sensor-error trials (>35% samples with lick > 2) and zeros their licks; otherwise caps lick values at 1 and binarizes by `> 0`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:152):
> all behavioral and neural data at ~15.5 Hz frame rate, already synchronized

**Code** (convert_data.py:438-452, 535):
```python
s = trial_start_inds[i]; e = teleport_inds[i]
...
trial_lick = lick[s:e].copy()
trial_neural = neural_data[:, s:e]
...
output_arr[3, :] = lick_binned
```

**What this does:** Uses identical `[s:e]` slicing as for the neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:215):
> Reward zone location | output[4] | 0=A, 1=B, 2=C, per-trial | From scene name + trial number

**Code** (convert_data.py:297-299, 70-133, 393-394, 522-523):
```python
identifier = f['identifier'][()].decode()
...
scene = get_scene_from_identifier(identifier)
...
def get_reward_zones(scene, n_trials, change_trial=DEFAULT_CHANGE_TRIAL):
    ...
    elif 'A_to' in scene and scene[-1] == 'B':
        rz_coords[:change_trial] = REWARD_ZONE_DICT['A']
        rz_labels[:change_trial] = 'A'
        rz_coords[change_trial:] = REWARD_ZONE_DICT['B']
        rz_labels[change_trial:] = 'B'
    ...
rz_coords, rz_labels = get_reward_zones(scene, n_trials)
...
rz_loc = rz_label_to_idx(rz_labels[i])
```

**What this does:** Reward zone label per trial is determined by parsing the scene string from NWB `identifier` and applying a fixed change trial (30) to switch between zones; the `reward_zone` behavioral timeseries is not used. Labels A/B/C are mapped to 0/1/2.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

**Notes excerpt** (CONVERSION_NOTES.md:235):
> Change trial = 30: Default from code; determines when reward zone switches within a session

**Code** (convert_data.py:35, 70-133, 272-275, 522-523, 536):
```python
DEFAULT_CHANGE_TRIAL = 30  # 0-indexed trial where reward zone switches
...
def rz_label_to_idx(label):
    mapping = {'A': 0, 'B': 1, 'C': 2}
    return mapping.get(label, -1)
...
rz_loc = rz_label_to_idx(rz_labels[i])
...
output_arr[4, :] = rz_loc  # broadcast
```

**What this does:** A scene-name parser produces labels A/B/C per trial (with trial 30 as the change point for switch sessions). The label is mapped to 0/1/2 and broadcast across timepoints. Training scenes default to label 'T' (returns -1).

**Rating:** ok

**Note:** _(no note)_

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:216):
> Reward outcome | output[5] | 0=no, 1=yes, per-trial | From Reward timestamps within trial

**Code** (convert_data.py:316, 278-282, 467-470):
```python
reward_timestamps = bts['Reward/timestamps'][:]
...
def detect_reward_in_trial(reward_timestamps, trial_start_time, trial_end_time):
    if len(reward_timestamps) == 0:
        return False
    return np.any((reward_timestamps >= trial_start_time) & (reward_timestamps <= trial_end_time))
...
trial_start_time = trial_timestamps[0]
trial_end_time = trial_timestamps[-1]
was_rewarded = detect_reward_in_trial(reward_timestamps, trial_start_time, trial_end_time)
```

**What this does:** Reads `Reward/timestamps` from BehavioralTimeSeries and checks whether any reward fell within the trial window.

**Rating:** match

**Note:** _(no note)_

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:216):
> 0=no, 1=yes, per-trial

**Code** (convert_data.py:467-470, 526, 537):
```python
trial_start_time = trial_timestamps[0]
trial_end_time = trial_timestamps[-1]
was_rewarded = detect_reward_in_trial(reward_timestamps, trial_start_time, trial_end_time)
...
reward_outcome = int(was_rewarded)
...
output_arr[5, :] = reward_outcome  # broadcast
```

**What this does:** Per-trial scalar 0/1 from `np.any` check on reward timestamps within the trial's `pos_timestamps[0]` and `pos_timestamps[-1]`; broadcast across all timepoints.

**Rating:** ok

**Note:** _(no note)_

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:387-389):
> Cross-env scene parsing fixed; Multi-plane length mismatch: m17/m18 sessions had neural data 1 frame longer than behavioral. Fixed by truncating to min length.

**Code** (convert_data.py:347-363, 376-388, 419-420, 441-447):
```python
n_timepoints_neural = deconv_all.shape[0]
n_timepoints_behav = len(position)
n_timepoints_total = min(n_timepoints_neural, n_timepoints_behav)
if n_timepoints_neural != n_timepoints_behav:
    deconv_all = deconv_all[:n_timepoints_total]
    ...
if n_cells_iscell < 2:
    print(f"  Skipping {session_label}: only {n_cells_iscell} cells after iscell filter")
    return None
...
n_trials = min(len(trial_start_inds), len(teleport_inds))
if n_trials < 2:
    print(f"  Skipping {session_label}: only {n_trials} trials")
    return None
...
if n_final_cells < 2:
    print(f"  Skipping {session_label}: only {n_final_cells} cells after interneuron exclusion")
    return None
...
if e <= s or (e - s) < 2:
    ...
    continue
```

**What this does:** Length mismatches between neural and behavior are silently truncated to the shorter. Sessions with <2 cells (after iscell or interneuron filter) or <2 trials are skipped. Trials with <2 timepoints are skipped while still updating `prev_trial_rewarded`. Unrecognized scenes log a warning and default to zone A.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:300-304):
> Vectorized interneuron detection: 18.2s/2sess -> 7.1s/2sess; Estimated full conversion: ~9 minutes

**Code** (convert_data.py:no specific section):
```python
# (no profiling instrumentation in convert_data.py beyond per-session timing)
t0 = time.time()
...
elapsed = time.time() - t0
print(f"  {session_label}: {n_final_cells} neurons, {valid_trial_count} trials, "
      f"{n_interneurons} interneurons removed, {elapsed:.1f}s")
```

**What this does:** The script logs per-session elapsed wall time. Notes attribute the main cost to the per-session NWB read of fluorescence/neuropil/deconvolved arrays plus dF/F computation for interneuron detection.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md:300-301):
> Vectorized interneuron detection: 18.2s/2sess -> 7.1s/2sess

**Code** (convert_data.py:172-209, 437-546):
```python
def detect_interneurons(dff_all, speed_all, threshold=INTERNEURON_SPEED_CORR_THRESHOLD):
    ...
    # Vectorized Pearson correlation
    speed_mean = speed_valid.mean()
    speed_centered = speed_valid - speed_mean
    ...
    corr = dff_centered @ speed_centered / (dff_std * speed_std + 1e-10)
...
for i in range(n_trials):
    s = trial_start_inds[i]; e = teleport_inds[i]
    ...
```

**What this does:** Interneuron detection is already vectorized with matrix multiplication. The remaining per-trial loop iterates trial-by-trial to extract slices and compute per-trial inputs/outputs.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md:no explicit section):
> (none)

**Code** (convert_data.py:333-344, 396-409):
```python
for pi, plane_name in enumerate(fluor_planes):
    deconv_data = ophys[f'Deconvolved/{plane_name}/data'][:]
    F_data = ophys[f'Fluorescence/{plane_name}/data'][:]
    Fneu_data = ophys[f'Neuropil/{plane_name}/data'][:]
    ...
dff_full = np.full_like(F_cells, np.nan)
for i in range(n_trials):
    ...
    dff_full[:, s:e] = compute_dff_trial(F_cells[:, s:e], Fneu_cells[:, s:e])
```

**What this does:** Loads F, Fneu, and Deconvolved arrays for each session even though only Deconvolved enters the final output (F/Fneu are used solely to compute dF/F for interneuron detection).

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md:no explicit section):
> (none)

**Code** (convert_data.py:402-409, 396-417):
```python
dff_full = np.full_like(F_cells, np.nan)
for i in range(n_trials):
    s = trial_start_inds[i]; e = teleport_inds[i]
    if e <= s:
        continue
    dff_full[:, s:e] = compute_dff_trial(F_cells[:, s:e], Fneu_cells[:, s:e])
is_interneuron = detect_interneurons(dff_full, speed)
```

**What this does:** Computes a full-session dF/F matrix per trial that is used only to compute speed-correlations for interneuron detection; the dF/F values themselves are not propagated to the final output.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — CONVERSION_NOTES.md and README.md contain no discussion of memory, RAM, dtype sizing, chunking or streaming. The only related remark is the output size, README/CONVERSION_NOTES.md:456: `converted_data.pkl           - Full dataset (9.4 GB, 152 sessions)`)

**Code** (convert_data.py:327-344):
```python
        # Load deconvolved events (already computed in NWB)
        deconv_list = []
        F_list = []
        Fneu_list = []
        plane_assignment = []

        for pi, plane_name in enumerate(fluor_planes):
            deconv_data = ophys[f'Deconvolved/{plane_name}/data'][:]  # (n_timepoints, n_rois_plane)
            F_data = ophys[f'Fluorescence/{plane_name}/data'][:]
            Fneu_data = ophys[f'Neuropil/{plane_name}/data'][:]
            deconv_list.append(deconv_data)
            F_list.append(F_data)
            Fneu_list.append(Fneu_data)

        # Concatenate across planes: (n_timepoints, n_total_rois)
        deconv_all = np.concatenate(deconv_list, axis=1)
        F_all = np.concatenate(F_list, axis=1)
        Fneu_all = np.concatenate(Fneu_list, axis=1)
```

Per-trial arrays are preallocated and stored as float32 / int64 (convert_data.py:501, 531, 540):
```python
        input_arr = np.zeros((4, n_t), dtype=np.float32)
        ...
        output_arr = np.zeros((6, n_t), dtype=np.int64)
        ...
        neural_trials.append(trial_neural.astype(np.float32))
```

The speed-correlation interneuron check upcasts to float64 (convert_data.py:189-190):
```python
    speed_valid = speed_all[valid].astype(np.float64)
    dff_valid = dff_all[:, valid].astype(np.float64)  # (n_cells, n_valid)
```

**What this does:** For each session the script reads three full-session ROI matrices (Deconvolved, Fluorescence, Neuropil) entirely into memory per plane and concatenates the per-plane lists, with no column subsetting at read time, no chunked/streaming reads, no memory-mapping, and no `del`/`gc.collect()` of the large intermediates. Stored trial arrays are preallocated with explicit dtypes — float32 for neural and inputs, int64 for outputs — while the interneuron speed-correlation step temporarily casts to float64. All sessions accumulate into a single in-memory structure that is pickled at the end.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
