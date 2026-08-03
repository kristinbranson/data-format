# sosa2024 — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/sosa2024/claude/2026-03-10__11-18-23_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "NWB files organized: `data/sub-{id}/sub-{id}_ses-{ses}_behavior+ophys.nwb`" (CONVERSION_NOTES.md:62); "All 152/152 sessions processed successfully" (CONVERSION_NOTES.md:165)

**Code** (convert_data.py:36-49, 203):
```python
def find_nwb_files(data_dir='data'):
    """Find all NWB files organized by subject."""
    subjects = sorted([d for d in os.listdir(data_dir) if d.startswith('sub-')])
    sessions = []
    for subj in subjects:
        subj_dir = os.path.join(data_dir, subj)
        files = sorted(glob(os.path.join(subj_dir, '*.nwb')))
        for fpath in files:
            sessions.append({
                'subject': subj.replace('sub-', ''),
                'filepath': fpath,
                'filename': os.path.basename(fpath),
            })
    return sessions
...
    with h5py.File(filepath, 'r') as f:
```

**What this does:** Walks the `data/` directory, collecting all `sub-*` subdirectories and globbing every `.nwb` file inside each. Each NWB file is opened directly with `h5py.File` (rather than `pynwb`) for reading.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Subjects | 11 (m3, m4, m7, m11-m15, m17-m19)" (CONVERSION_NOTES.md:76)

**Code** (convert_data.py:38, 45, 614-615):
```python
subjects = sorted([d for d in os.listdir(data_dir) if d.startswith('sub-')])
...
'subject': subj.replace('sub-', ''),
...
unique_subjects = sorted(set(all_subject_ids))
subject_idx = np.array([unique_subjects.index(s) for s in all_subject_ids])
```

**What this does:** Subject identity comes from the `sub-<id>` directory name. Each session retains its subject ID, and a final `unique_subjects` list with `subject_idx` mapping is produced.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions total | 152" (CONVERSION_NOTES.md:77); files named `sub-{id}_ses-{ses}_behavior+ophys.nwb`

**Code** (convert_data.py:42-48):
```python
files = sorted(glob(os.path.join(subj_dir, '*.nwb')))
for fpath in files:
    sessions.append({
        'subject': subj.replace('sub-', ''),
        'filepath': fpath,
        'filename': os.path.basename(fpath),
    })
```

**What this does:** Each NWB file under a subject directory is treated as one session. Sessions are not numbered explicitly — they are just iterated in sorted-filename order.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial boundaries: trial_start and teleport signals in behavior timeseries" (CONVERSION_NOTES.md:42)

**Code** (convert_data.py:319-338):
```python
trial_start_inds = np.where(trial_start > 0)[0]
teleport_inds = np.where(teleport_sig > 0)[0]
n_trials = len(trial_start_inds)

if n_trials < 2:
    print(f"  WARNING: Only {n_trials} trials, skipping session")
    return None

# Match teleport to trial start (ensure same count)
if len(teleport_inds) != n_trials:
    matched_teleports = []
    for ts in trial_start_inds:
        tp_after = teleport_inds[teleport_inds > ts]
        if len(tp_after) > 0:
            matched_teleports.append(tp_after[0])
    teleport_inds = np.array(matched_teleports)
    n_trials = min(n_trials, len(teleport_inds))
    trial_start_inds = trial_start_inds[:n_trials]
```

**What this does:** Identifies trial boundaries by indices where `trial_start > 0` and `teleport > 0`. If counts mismatch, each trial start is paired with the next teleport after it; counts are then truncated to match.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit on per-trial QC filters beyond skipping sessions with <2 trials)

**Code** (convert_data.py:388-394):
```python
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    n_tp = ei - si

    if n_tp < 2:
        continue
```

**What this does:** Trials with fewer than 2 timepoints are silently skipped. No other per-trial QC filtering on length, behavior validity, etc.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "NWB `Deconvolved` data is the deconvolved events AFTER full dF/F processing pipeline" (CONVERSION_NOTES.md:39); "Used deconvolved events from NWB directly (already fully processed)" (CONVERSION_NOTES.md:267)

**Code** (convert_data.py:216-238):
```python
deconv_group = f['processing/ophys/Deconvolved']
planes = sorted(deconv_group.keys())  # e.g. ['plane0'] or ['plane0', 'plane1']

deconv_list = []
...
for plane in planes:
    ...
    d = f[f'processing/ophys/Deconvolved/{plane}/data'][:]
    ...
    deconv_list.append(d)
...
deconv = np.concatenate(deconv_list, axis=1)
```

**What this does:** Loads `processing/ophys/Deconvolved/<plane>/data` for each available plane and concatenates across planes along the ROI axis. Fluorescence and Neuropil are also loaded for downstream interneuron filtering.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Multi-plane handling: detect planes, concatenate, map iscell indices" (CONVERSION_NOTES.md:155); "Interneuron exclusion: vectorized z-scored dot product for speed-dFF correlation" (CONVERSION_NOTES.md:156)

**Code** (convert_data.py:284-316):
```python
# Step 2: Interneuron exclusion - compute dF/F correlation with speed
f_corrected = fluorescence - 0.7 * neuropil_data
f_median = np.median(f_corrected, axis=0, keepdims=True)
f_median[f_median == 0] = 1
dff_simple = (f_corrected - f_median) / np.abs(f_median)
...
            speed_z = (speed_valid - speed_valid.mean()) / (speed_valid.std() + 1e-10)
            dff_accepted = dff_simple[valid_mask][:, accepted_cols]
            ...
            corrs = (speed_z @ dff_z) / len(speed_z)
            for i, col_idx in enumerate(accepted_cols):
                if corrs[i] > 0.5:
                    interneuron_mask[col_idx] = True

final_cell_mask = cell_mask_concat & ~interneuron_mask
...
neural_all = deconv[:, final_cell_mask].T
```

**What this does:** Concatenates planes; computes a simplified dF/F (raw F minus 0.7*neuropil, normalized by median); marks ROIs whose dF/F correlates >0.5 with speed as putative interneurons and excludes them in addition to the iscell filter.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Applied iscell filter + interneuron exclusion (speed-dFF corr > 0.5)" (CONVERSION_NOTES.md:268)

**Code** (convert_data.py:212, 281-316):
```python
iscell = f['processing/ophys/ImageSegmentation/PlaneSegmentation/iscell'][:]
...
cell_mask_concat = np.array([iscell[concat_to_iscell[i], 0] == 1 for i in range(n_rois_concat)])
...
final_cell_mask = cell_mask_concat & ~interneuron_mask
```

**What this does:** Two-stage QC: (1) keep ROIs with `iscell[:,0]==1` (Suite2p curation), (2) further exclude ROIs flagged as interneurons by speed-dFF correlation > 0.5.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: 'start of trial (entry to linear track)'" (convert_data.py:670)

**Code** (convert_data.py:388-397, 670):
```python
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    n_tp = ei - si
    ...
    trial_neural = neural_all[:, si:ei].copy()
...
'temporal_alignment_event': 'start of trial (entry to linear track)',
```

**What this does:** Per-trial neural slice spans from the `trial_start` index to the `teleport` index, naturally aligning to trial start (no extra offset).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Imaging rate | ~15.5 Hz (~64.5 ms/frame)" (CONVERSION_NOTES.md:81); "Time bin | 64.48 ms" (CONVERSION_NOTES.md:181)

**Code** (convert_data.py:25, 386, 626):
```python
IMAGING_RATE_NOMINAL = 15.5078125  # Hz
...
frame_time = 1.0 / imaging_rate  # seconds per frame
...
time_bin_ms = 1000.0 / IMAGING_RATE_NOMINAL
```

**What this does:** Neural data is kept at the native imaging frame rate; no resampling. Frame period derived from per-session `imaging_rate`; reported `time_bin_size` in metadata uses the nominal 15.5078125 Hz.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time from trial start | input[0] | Frame index * time_bin_size, in seconds" (CONVERSION_NOTES.md:135)

**Code** (convert_data.py:208, 386, 403):
```python
imaging_rate = f['general/optophysiology/ImagingPlane/imaging_rate'][()]
...
frame_time = 1.0 / imaging_rate  # seconds per frame
...
time_from_start = np.arange(n_tp, dtype=np.float32) * frame_time
```

**What this does:** Computed from the integer frame index multiplied by `1/imaging_rate`, not from the NWB `timestamps` array.

**Rating:** concerning

**Note:** does not use timestamps, assumes they are evenly collected. data looks consistent, so probably ok

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none beyond above)

**Code** (convert_data.py:403):
```python
time_from_start = np.arange(n_tp, dtype=np.float32) * frame_time
```

**What this does:** Simple multiplication of `arange(n_timepoints)` by frame period. No subtraction needed since indexing already starts at 0 within the trial.

**Rating:** concerning

**Note:** does not use timestamps, assumes they are evenly collected. data looks consistent, so probably ok

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Behavior aligned to imaging: All behavior timeseries at ~15.5 Hz imaging frame rate" (CONVERSION_NOTES.md:41); length-mismatch handled by truncation (CONVERSION_NOTES.md:88)

**Code** (convert_data.py:264-278):
```python
n_behav = len(position)
if n_timepoints != n_behav:
    min_len = min(n_timepoints, n_behav)
    print(f"  NOTE: Aligned neural ({n_timepoints}) and behavior ({n_behav}) to {min_len} timepoints")
    deconv = deconv[:min_len]
    ...
    behav_timestamps = behav_timestamps[:min_len]
    n_timepoints = min_len
```

**What this does:** Neural and behavior streams are assumed sample-aligned at the imaging rate; if their lengths differ, both are truncated to the minimum. The time-from-start array indexes the trial slice.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Environment (morph) | input[1] | Binary 0/1 per trial" (CONVERSION_NOTES.md:137); "Use env_per_trial from scene parsing (more reliable for cross-env switches)" (convert_data.py:359-360)

**Code** (convert_data.py:52-58, 109-129, 340-361):
```python
def parse_scene(identifier):
    return identifier.split('/')[-1]
...
def _parse_zone_and_env(parts):
    ...
    for p in parts:
        if p.startswith('Env'):
            env_num = int(p.replace('Env', ''))
            env = env_num - 1  # 0-indexed
        ...
    return zone, env
...
rz_labels, rz_coords, env_per_trial = get_reward_zone_labels(scene, n_trials)
...
trial_env = env_per_trial.copy()
```

**What this does:** Environment is parsed from the NWB `identifier` (scene name like `Env1_LocationA` or `Env1_B_to_Env2_C`); the NWB `environment` time series is loaded but not used for the per-trial env value.

**Rating:** ok

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Scene parsing: handles all 26 unique scene name formats" (CONVERSION_NOTES.md:157)

**Code** (convert_data.py:78-105, 421):
```python
if '_to_' in scene:
    parts = scene.split('_')
    to_idx = parts.index('to')
    from_parts = parts[:to_idx]
    to_parts = parts[to_idx+1:]
    from_zone, from_env = _parse_zone_and_env(from_parts)
    to_zone, to_env = _parse_zone_and_env(to_parts)
    ...
    env_per_trial[:change_trial] = from_env
    env_per_trial[change_trial:] = to_env
else:
    parts = scene.split('_')
    zone, env = _parse_zone_and_env(parts)
    ...
    env_per_trial[:] = env
...
np.full((1, n_tp), env_type, dtype=np.float32),
```

**What this does:** A switch session uses `change_trial=30` as the boundary between "from" and "to" environments. Per-trial env is broadcast across all timepoints in the trial.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial number | input[2] | Integer per trial" (CONVERSION_NOTES.md:138)

**Code** (convert_data.py:388, 407):
```python
for t in range(n_trials):
    ...
    trial_num = np.float32(t)
```

**What this does:** Trial number is the loop index from segmenting `trial_start`/`teleport` (0-indexed within session), not the NWB `trial number` time series.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:407, 422):
```python
trial_num = np.float32(t)
...
np.full((1, n_tp), trial_num, dtype=np.float32),
```

**What this does:** No processing beyond casting and broadcasting the loop counter across the trial's timepoints.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reward determined from sparse timestamp matching to frame times" (CONVERSION_NOTES.md:270)

**Code** (convert_data.py:259, 343-356):
```python
reward_timestamps = f['processing/behavior/BehavioralTimeSeries/Reward/timestamps'][:]
...
reward_frames = np.zeros(n_timepoints, dtype=np.float32)
for rt in reward_timestamps:
    frame_idx = np.argmin(np.abs(behav_timestamps - rt))
    reward_frames[frame_idx] = 1.0

trial_rewarded = np.zeros(n_trials, dtype=np.int64)
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    if np.any(reward_frames[si:ei] > 0):
        trial_rewarded[t] = 1
```

**What this does:** Derived from `Reward/timestamps`. Each reward timestamp is mapped to its closest behavior frame via argmin distance; per-trial reward flag = any reward frame inside the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Previous trial outcome | input[3] | Binary: 0=omission, 1=rewarded" (CONVERSION_NOTES.md:139)

**Code** (convert_data.py:375-378, 408, 423):
```python
prev_outcome = np.zeros(n_trials, dtype=np.int64)
for t in range(1, n_trials):
    prev_outcome[t] = trial_rewarded[t - 1]
# Trial 0: no previous, use 0 (omission)
...
prev_out = np.float32(prev_outcome[t])
...
np.full((1, n_tp), prev_out, dtype=np.float32),
```

**What this does:** Lags the per-trial reward flag by 1; trial 0 defaults to 0. Broadcast across trial timepoints.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reward zones | A:80-130, B:200-250, C:320-370" (CONVERSION_NOTES.md:109); reward zone determined per trial from scene name

**Code** (convert_data.py:17-22, 250, 340-341, 432-434):
```python
REWARD_ZONE_DICT = {
    'A': [80, 130],
    'B': [200, 250],
    'C': [320, 370],
}
...
position = f['processing/behavior/BehavioralTimeSeries/position/data'][:]
...
rz_labels, rz_coords, env_per_trial = get_reward_zone_labels(scene, n_trials)
...
rz_start = rz_coords[t, 0]
rz_end = rz_coords[t, 1]
signed_dist = compute_distance_to_reward_zone(trial_pos, rz_start, rz_end)
```

**What this does:** Position from the NWB `position` time series; reward-zone bounds are looked up from a hard-coded dict keyed by zone letter parsed from the scene-name `identifier`. The NWB `reward_zone` time series is not used.

**Rating:** ok

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none beyond mapping table)

**Code** (convert_data.py:132-148):
```python
def compute_distance_to_reward_zone(position, rz_start, rz_end):
    dist = np.zeros_like(position)
    before = position < rz_start
    after = position > rz_end
    inside = ~before & ~after

    dist[before] = position[before] - rz_start  # negative
    dist[after] = position[after] - rz_end       # positive
    dist[inside] = 0.0
    return dist
```

**What this does:** Signed distance: negative if before the zone, positive if past it, exactly 0 inside.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "distance_to_reward_zone | 7 bins, range [0,6], well-distributed" (CONVERSION_NOTES.md:196)

**Code** (convert_data.py:151-169):
```python
def discretize_distance(distance):
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

**What this does:** Manual masking into 7 bins matching the spec edges (-inf,-50,-10,0, exact 0, 10, 50, inf). The "in zone" bin is `distance == 0`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit)

**Code** (convert_data.py:388-397, 427, 434):
```python
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    ...
    trial_neural = neural_all[:, si:ei].copy()
...
trial_pos = position[si:ei]
...
signed_dist = compute_distance_to_reward_zone(trial_pos, rz_start, rz_end)
```

**What this does:** Position and neural data are sliced with identical `[si:ei]` indices, so they share the same per-frame alignment.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Absolute position | output[1] | 5 equal bins (90cm each)" (CONVERSION_NOTES.md:140)

**Code** (convert_data.py:250, 427):
```python
position = f['processing/behavior/BehavioralTimeSeries/position/data'][:]
...
trial_pos = position[si:ei]
```

**What this does:** Directly the `position` behavior time series, sliced to the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:438):
```python
pos_bins = discretize_position(trial_pos)
```

**What this does:** No processing beyond discretization (see 8-c).

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "absolute_position | 5 bins, roughly equal (~15-23% each)" (CONVERSION_NOTES.md:197); "0-90cm', '90-180cm', ..." (convert_data.py:658)

**Code** (convert_data.py:172-175):
```python
def discretize_position(position):
    """Discretize absolute position into 5 equal bins (0-90, 90-180, 180-270, 270-360, 360-450)."""
    bins = np.clip(np.floor(position / 90.0).astype(np.int64), 0, 4)
    return bins
```

**What this does:** Floor-divides position by 90 cm and clips to [0,4], yielding 5 equal-width bins covering 0–450 cm.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit)

**Code** (convert_data.py:397, 427):
```python
trial_neural = neural_all[:, si:ei].copy()
...
trial_pos = position[si:ei]
```

**What this does:** Same `[si:ei]` slice indices used for both, after the global length-equalization truncation.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "lick is cumulative per frame, set >1 to 1" (convert_data.py:364)

**Code** (convert_data.py:252, 363-373):
```python
lick = f['processing/behavior/BehavioralTimeSeries/lick/data'][:]
...
lick_binary = lick.copy()
lick_binary[lick_binary > 0] = 1
# Lick sensor error correction per trial (>30% frames with count>2 -> NaN)
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    trial_lick = lick[si:ei]
    if len(trial_lick) > 0 and (np.sum(trial_lick > 2) / len(trial_lick)) > 0.30:
        lick_binary[si:ei] = 0
```

**What this does:** Derived from the `lick` behavior time series.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "correct_lick_sensor_error: Fix stuck lick sensor: if >30-50% frames have cumcount>2, set to NaN" (CONVERSION_NOTES.md:33)

**Code** (convert_data.py:365-373, 444):
```python
lick_binary = lick.copy()
lick_binary[lick_binary > 0] = 1
for t in range(n_trials):
    ...
    if len(trial_lick) > 0 and (np.sum(trial_lick > 2) / len(trial_lick)) > 0.30:
        lick_binary[si:ei] = 0
...
lick_out = (trial_lick > 0).astype(np.int64)
```

**What this does:** Binarize lick (>0 -> 1). Then a stuck-sensor heuristic zeroes the entire trial's licks if more than 30% of frames have cumcount>2.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit)

**Code** (convert_data.py:397, 429):
```python
trial_neural = neural_all[:, si:ei].copy()
...
trial_lick = lick_binary[si:ei]
```

**What this does:** Same per-trial index slice.

**Rating:** match

**Note:** _(no note)_

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reward zone location | output[4] | 0=A, 1=B, 2=C per trial" (CONVERSION_NOTES.md:142)

**Code** (convert_data.py:207, 340, 446-448):
```python
identifier = f['identifier'][()].decode()
scene = parse_scene(identifier)
...
rz_labels, rz_coords, env_per_trial = get_reward_zone_labels(scene, n_trials)
...
zone_map = {'A': 0, 'B': 1, 'C': 2}
rz_loc = zone_map.get(rz_labels[t], 0)
```

**What this does:** Reward-zone label is parsed from the NWB `identifier` (scene name), not from the `reward_zone` time series. Each trial gets one of {A,B,C}.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "switches after trial 30 on switch days" (convert_data.py:668); 26 unique scene formats handled (CONVERSION_NOTES.md:157)

**Code** (convert_data.py:61-105):
```python
def get_reward_zone_labels(scene, n_trials, change_trial=30):
    ...
    if '_to_' in scene:
        parts = scene.split('_')
        to_idx = parts.index('to')
        from_parts = parts[:to_idx]
        to_parts = parts[to_idx+1:]
        from_zone, from_env = _parse_zone_and_env(from_parts)
        to_zone, to_env = _parse_zone_and_env(to_parts)

        labels[:change_trial] = from_zone
        labels[change_trial:] = to_zone
        ...
    else:
        ...
        labels[:] = zone
```

**What this does:** Parses single-zone vs `_to_` switch scenes. Switch sessions use a hard-coded `change_trial=30` boundary between from-zone and to-zone labels. Mapped to integer 0/1/2 and broadcast across trial timepoints.

**Rating:** ok

**Note:** _(no note)_

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reward field: Event-based (sparse), not frame-aligned" (CONVERSION_NOTES.md:91-92)

**Code** (convert_data.py:259, 344-356):
```python
reward_timestamps = f['processing/behavior/BehavioralTimeSeries/Reward/timestamps'][:]
...
reward_frames = np.zeros(n_timepoints, dtype=np.float32)
for rt in reward_timestamps:
    frame_idx = np.argmin(np.abs(behav_timestamps - rt))
    reward_frames[frame_idx] = 1.0

trial_rewarded = np.zeros(n_trials, dtype=np.int64)
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    if np.any(reward_frames[si:ei] > 0):
        trial_rewarded[t] = 1
```

**What this does:** Derived from `Reward/timestamps`.

**Rating:** match

**Note:** _(no note)_

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none beyond above)

**Code** (convert_data.py:345-356, 451, 461):
```python
for rt in reward_timestamps:
    frame_idx = np.argmin(np.abs(behav_timestamps - rt))
    reward_frames[frame_idx] = 1.0
...
    if np.any(reward_frames[si:ei] > 0):
        trial_rewarded[t] = 1
...
rew_outcome = int(trial_rewarded[t])
...
np.full((1, n_tp), rew_outcome, dtype=np.int64),
```

**What this does:** Each reward timestamp mapped to its nearest behavior frame via argmin, then per-trial outcome = any reward in the trial window. Broadcast across timepoints.

**Rating:** match

**Note:** _(no note)_

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "10 sessions had neural/behavior length alignment (off-by-one, all multi-plane)" (CONVERSION_NOTES.md:167); "Off-by-one behavior/neural mismatches resolved by truncation" (CONVERSION_NOTES.md:271)

**Code** (convert_data.py:264-278, 324-326, 329-338, 393-394, 399):
```python
if n_timepoints != n_behav:
    min_len = min(n_timepoints, n_behav)
    ...
    deconv = deconv[:min_len]
    ...
if n_trials < 2:
    print(f"  WARNING: Only {n_trials} trials, skipping session")
    return None
...
if len(teleport_inds) != n_trials:
    matched_teleports = []
    for ts in trial_start_inds:
        tp_after = teleport_inds[teleport_inds > ts]
        if len(tp_after) > 0:
            matched_teleports.append(tp_after[0])
    teleport_inds = np.array(matched_teleports)
...
if n_tp < 2:
    continue
...
trial_neural = np.nan_to_num(trial_neural, nan=0.0)
```

**What this does:** Handles (1) neural/behavior length mismatch via truncation, (2) sessions with <2 trials skipped, (3) trial_start/teleport count mismatch via greedy matching, (4) trials with <2 timepoints skipped, (5) NaNs in neural data replaced with 0, (6) stuck lick sensor heuristic per trial.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "All 152/152 sessions processed successfully ... Total processing time: 762.5 seconds" (CONVERSION_NOTES.md:165-166); "Output: `converted_data.pkl` (9380.1 MB)" (CONVERSION_NOTES.md:166)

**Code** (convert_data.py:203, 230-232, 700-702):
```python
with h5py.File(filepath, 'r') as f:
    ...
    d = f[f'processing/ophys/Deconvolved/{plane}/data'][:]
    fl = f[f'processing/ophys/Fluorescence/{plane}/data'][:]
    ne = f[f'processing/ophys/Neuropil/{plane}/data'][:]
...
with open(args.output, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** No explicit profiling. Per-session timing is printed; main heavy operations are NWB I/O of large arrays (Deconvolved + Fluorescence + Neuropil), the simplified dF/F + speed correlation computation, and pickling the ~9.4 GB output.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Interneuron exclusion: vectorized z-scored dot product for speed-dFF correlation" (CONVERSION_NOTES.md:156)

**Code** (convert_data.py:282, 305-307, 346-348, 388):
```python
cell_mask_concat = np.array([iscell[concat_to_iscell[i], 0] == 1 for i in range(n_rois_concat)])
...
for i, col_idx in enumerate(accepted_cols):
    if corrs[i] > 0.5:
        interneuron_mask[col_idx] = True
...
for rt in reward_timestamps:
    frame_idx = np.argmin(np.abs(behav_timestamps - rt))
    reward_frames[frame_idx] = 1.0
...
for t in range(n_trials):
```

**What this does:** Several Python loops remain that could be vectorized: per-ROI iscell list-comp, per-ROI interneuron mask assignment, per-reward-event argmin (could use `np.searchsorted`), per-trial segmentation loop.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit)

**Code** (convert_data.py:382-467):
```python
for t in range(n_trials):
    si = trial_start_inds[t]
    ei = teleport_inds[t]
    ...
    # Neural slice, position slice, lick slice, distance, discretization
```

**What this does:** Per-trial slicing, discretization, and broadcasting are repeated inside the trial loop. There is no second pass over NWB files (single-pass design with no separate survey step).

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit)

**Code** (convert_data.py:231-232, 285-288, 441, 459):
```python
fl = f[f'processing/ophys/Fluorescence/{plane}/data'][:]
ne = f[f'processing/ophys/Neuropil/{plane}/data'][:]
...
f_corrected = fluorescence - 0.7 * neuropil_data
f_median = np.median(f_corrected, axis=0, keepdims=True)
...
speed_bins = discretize_speed(np.abs(trial_speed))
...
speed_bins.reshape(1, -1),
```

**What this does:** Fluorescence and Neuropil are loaded only to derive a simplified dF/F for the interneuron filter, then discarded. A `speed` output channel is also computed and included in `output_names` though the spec listed in DECISIONS does not request a separate speed output.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — CONVERSION_NOTES.md contains no mention of memory, RAM, dtype sizing, chunking, streaming or memory-mapping; there is no README.md in the snapshot)

**Code** (convert_data.py:219-240):
```python
        # Load and concatenate data from all planes
        deconv_list = []
        flu_list = []
        neu_list = []
        plane_cell_offset = 0
        plane_offsets = {}
        for plane in planes:
            plane_num = int(plane.replace('plane', ''))
            plane_mask = planeIdx == plane_num
            plane_offsets[plane_num] = np.where(plane_mask)[0]

            d = f[f'processing/ophys/Deconvolved/{plane}/data'][:]  # (n_timepoints, n_rois_plane)
            fl = f[f'processing/ophys/Fluorescence/{plane}/data'][:]
            ne = f[f'processing/ophys/Neuropil/{plane}/data'][:]
            deconv_list.append(d)
            flu_list.append(fl)
            neu_list.append(ne)

        # Concatenate across planes: (n_timepoints, n_rois_total_in_data)
        deconv = np.concatenate(deconv_list, axis=1)
        fluorescence = np.concatenate(flu_list, axis=1)
        neuropil_data = np.concatenate(neu_list, axis=1)
```

Cell filtering and the float32 cast happen after the full matrix is materialized (convert_data.py:316-317), and trial arrays carry explicit dtypes (convert_data.py:465-467):
```python
    neural_all = deconv[:, final_cell_mask].T  # (n_neurons, n_timepoints)
    neural_all = neural_all.astype(np.float32)
    ...
        neural_trials.append(trial_neural.astype(np.float32))
        input_trials.append(trial_input.astype(np.float32))
        output_trials.append(trial_output.astype(np.int64))
```

**What this does:** Each session's Deconvolved, Fluorescence and Neuropil matrices are read in full per plane with `[:]` and concatenated, so the whole session (all ROIs, including ones later discarded) is resident before filtering; there is no chunked or memory-mapped read, no `del`/`gc.collect()`, and no explicit release of `fluorescence`/`neuropil_data` after the interneuron check. Dtypes are set explicitly at storage time — float32 for neural and inputs, int64 for outputs — and per-trial arrays use `np.full`/preallocated stacks rather than repeated concatenation.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
