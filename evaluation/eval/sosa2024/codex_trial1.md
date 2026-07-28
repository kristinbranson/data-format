# sosa2024 — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/sosa2024/codex/2026-03-11__11-30-50_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> Top level of `data/`: dandiset.yaml; one folder per subject (`sub-m3`...`sub-m19`). Each subject folder contains one NWB file per session. Total files: 152. (lines 73-78)
> "Reads NWB directly with `h5py`" (line 256)

**Code** (convert_data.py:71-75, 273-275):
```python
def get_session_files(sample: bool) -> list[Path]:
    files = sorted(Path("data").glob("sub-*/sub-*_behavior+ophys.nwb"))
    if sample:
        return files[:2]
    return files
...
def load_session(path: Path, show_processing: bool):
    with h5py.File(path, "r") as handle:
        identifier = decode_h5_scalar(handle["identifier"])
```

**What this does:** Discovers NWB files via a glob pattern `sub-*/sub-*_behavior+ophys.nwb` under `data/`, sorts them, and opens each one with h5py rather than via pynwb. Each NWB file is treated as one session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "one folder per subject: `sub-m3`, `sub-m4`, ..., `sub-m19`" (line 76)

**Code** (convert_data.py:276, 471-500):
```python
subject = decode_h5_scalar(handle["general/subject/subject_id"])
...
subject_to_idx = {}
...
if subject not in subject_to_idx:
    subject_to_idx[subject] = len(data["subjects"])
    data["subjects"].append(subject)
...
subject_idx.append(subject_to_idx[subject])
```

**What this does:** Subject identity is read from each NWB file's `general/subject/subject_id` field. A `subject_to_idx` dict assigns sequential indices for each unique subject, and `subject_idx` records the subject for each session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Each subject folder contains one NWB file per session, named like `sub-m3_ses-01_behavior+ophys.nwb`." (line 77)

**Code** (convert_data.py:71-75, 277):
```python
files = sorted(Path("data").glob("sub-*/sub-*_behavior+ophys.nwb"))
...
session_id = decode_h5_scalar(handle["general/session_id"])
```

**What this does:** Each NWB file maps to a single session; the session ID is read directly from the NWB `general/session_id` attribute. Sessions are processed one at a time in sorted order.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Reconstructs trials from `trial_start` impulse to `teleport` impulse" (line 258)

**Code** (convert_data.py:137-153):
```python
def reconstruct_trials(trial_start: np.ndarray, teleport: np.ndarray) -> list[tuple[int, int]]:
    starts = np.flatnonzero(trial_start > 0.5)
    teleports = np.flatnonzero(teleport > 0.5)
    trials = []
    tp_ptr = 0
    for start in starts:
        while tp_ptr < len(teleports) and teleports[tp_ptr] <= start:
            tp_ptr += 1
        if tp_ptr >= len(teleports):
            break
        stop = teleports[tp_ptr]
        if stop > start:
            trials.append((int(start), int(stop)))
        tp_ptr += 1
    return trials
```

**What this does:** Trial boundaries are determined from the `trial_start` and `teleport` behavioral streams. For each trial-start frame the next teleport frame after it becomes the trial end; the (start, stop) pair defines the trial frame range.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Drops trials failing lick-sensor QC" (line 259)
> "Lick-analysis trials are removed when >30% of imaging-frame samples in the trial have cumulative lick count >2." (line 179)

**Code** (convert_data.py:156-159, 334-338):
```python
def is_bad_lick_trial(lick_trial: np.ndarray) -> bool:
    if lick_trial.size == 0:
        return True
    return float(np.mean(lick_trial > 2)) > LICK_ERROR_FRAC
...
if pos_trial.size < 2:
    continue
if is_bad_lick_trial(lick_trial):
    dropped_bad_lick += 1
    continue
```

**What this does:** Trials with fewer than 2 position samples are skipped. Trials are also dropped when more than 35% (`LICK_ERROR_FRAC = 0.35`) of frames have cumulative lick count >2, treated as a lick-sensor failure.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Uses NWB `Deconvolved/plane0/data` as neural activity" (line 257)
> "Neural signal = deconvolved activity" (line 227)

**Code** (convert_data.py:297-314):
```python
deconv_group = handle["processing/ophys/Deconvolved"]
plane_keys = sorted(deconv_group.keys(), key=lambda key: int(key.replace("plane", "")))
if len(plane_keys) == 1:
    deconvolved = np.asarray(deconv_group[plane_keys[0]]["data"][:, curated_idx], dtype=np.float16)
else:
    n_frames = deconv_group[plane_keys[0]]["data"].shape[0]
    n_rois = plane_idx.shape[0]
    all_deconvolved = np.empty((n_frames, n_rois), dtype=np.float16)
    for plane_key in plane_keys:
        ...
        all_deconvolved[:, cols] = plane_data
    deconvolved = all_deconvolved[:, curated_idx]
```

**What this does:** Neural activity is read from NWB `processing/ophys/Deconvolved` (deconvolved calcium events). For multi-plane sessions, the planes are reassembled into a single ROI matrix using `planeIdx`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Stores neural trials as `float16` to reduce output size; training code later casts to `float32`." (line 278)

**Code** (convert_data.py:300-314, 347):
```python
deconvolved = np.asarray(deconv_group[plane_keys[0]]["data"][:, curated_idx], dtype=np.float16)
...
all_deconvolved[:, cols] = plane_data
...
deconvolved = all_deconvolved[:, curated_idx]
...
neural_trial = deconvolved[start:stop].T
```

**What this does:** Beyond reading the deconvolved values, the only processing is curated-ROI selection, multi-plane reassembly, dtype cast to `float16`, slicing by trial frame indices, and transposing to `(neurons, time)`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Filters ROIs with `iscell[:,0] == 1`" (line 258)
> "Initial neuron filter = `iscell[:,0] == 1`: This matches Suite2p manual curation." (line 233)

**Code** (convert_data.py:291-294):
```python
segmentation = handle["processing/ophys/ImageSegmentation/PlaneSegmentation"]
iscell = segmentation["iscell"][:]
plane_idx = segmentation["planeIdx"][:].astype(np.int16)
curated_idx = np.flatnonzero(iscell[:, 0] > 0.5)
```

**What this does:** ROIs are filtered to those with `iscell[:,0] > 0.5` (Suite2p manual curation flag). No additional speed-correlation interneuron exclusion is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use native imaging-frame resolution: ... ~15.5 Hz ... No rebinning in time unless a later validation forces it." (line 229)

**Code** (convert_data.py:18-19, 451):
```python
FRAME_RATE_HZ = 15.5078125
TIME_BIN_MS = 1000.0 / FRAME_RATE_HZ
...
"time_bin_size": TIME_BIN_MS,
```

**What this does:** Neural data is kept at the native imaging frame rate (~15.5 Hz, ~64.5 ms). No rebinning or resampling is performed; the rate constant is stored in metadata.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> `"temporal_alignment_event": "trial start"` (metadata, line 452 in code)

**Code** (convert_data.py:325, 332, 347):
```python
for trial_idx, (start, stop) in enumerate(trials):
    ...
    time_trial = position_t[start:stop] - position_t[start]
    ...
    neural_trial = deconvolved[start:stop].T
```

**What this does:** Neural data is sliced from the same `start:stop` frame range as the behavior, so the first frame of each per-trial neural array corresponds to the trial-start event. No extra offset is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`processing/behavior/BehavioralTimeSeries/position` timestamps -> `input[0]` = `time_from_trial_start_s`" (line 215)

**Code** (convert_data.py:283, 332):
```python
position_t = behavior["position/timestamps"][:].astype(np.float64)
...
time_trial = position_t[start:stop] - position_t[start]
```

**What this does:** Time-from-trial-start is computed from the `position` time series' timestamp array.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`timestamps - timestamps[trial_start]` within each trial" (line 215)

**Code** (convert_data.py:332, 357):
```python
time_trial = position_t[start:stop] - position_t[start]
...
time_trial.astype(np.float32),
```

**What this does:** Per-trial timestamps are zeroed by subtracting the timestamp at the trial-start frame, producing seconds elapsed since trial start.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Neural and behavioral data are analyzed at the imaging frame rate (~15.5 Hz). Reference code aligns Unity VR data to imaging frames before any later analyses." (lines 148-149)

**Code** (convert_data.py:332, 347, 354):
```python
time_trial = position_t[start:stop] - position_t[start]
...
neural_trial = deconvolved[start:stop].T
...
n_time = neural_trial.shape[1]
```

**What this does:** Behavior and neural arrays use the same `start:stop` frame indices and the NWB stores them already aligned to the imaging frame grid, so no resampling is performed.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Scene identifier drives reward-zone identity. NWB `reward_zone` is not the A/B/C label. Active reward-zone identity will be parsed from the session identifier (for example `Env1_LocationA_to_B`...)" (line 231)

**Code** (convert_data.py:89-128, 275, 279, 340-342):
```python
identifier = decode_h5_scalar(handle["identifier"])
...
scene_info = parse_scene(identifier)
...
def parse_scene(identifier: str) -> dict:
    scene = identifier.rstrip("/").split("/")[-1]
    match = re.fullmatch(r"(Env[12])_Location([ABC])", scene)
    ...
env_name, zone_name = zone_for_trial(scene_info, trial_idx)
...
env_code = float(ENV_TO_INT[env_name])
```

**What this does:** Environment label is parsed from the NWB `identifier` scene string (e.g. `Env1_LocationA`, `Env1_B_to_Env2_C`) rather than from the `environment` time series. `Env1` -> 0, `Env2` -> 1.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "On switch days, reward zone changes after 30 trials. ENV2 introduced on day 8" (line 146)

**Code** (convert_data.py:131-134, 340, 342, 358):
```python
def zone_for_trial(scene_info: dict, trial_idx: int) -> tuple[str, str]:
    if scene_info["switch"] and trial_idx >= SWITCH_TRIAL:
        return scene_info["post_env"], scene_info["post_zone"]
    return scene_info["pre_env"], scene_info["pre_zone"]
...
env_name, zone_name = zone_for_trial(scene_info, trial_idx)
env_code = float(ENV_TO_INT[env_name])
...
np.full(n_time, env_code, dtype=np.float32),
```

**What this does:** For switch sessions, trials before index 30 use the pre-switch env, trials >=30 use the post-switch env. The resulting integer code is repeated across all timepoints in the trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Reconstructed within-session trial index -> `input[2]` = `trial_number`. Use reconstructed trial order from `trial_start` events, not raw `trial number` during teleport." (line 217)

**Code** (convert_data.py:325, 359):
```python
for trial_idx, (start, stop) in enumerate(trials):
    ...
    np.full(n_time, float(trial_idx), dtype=np.float32),
```

**What this does:** Trial number is the 0-based loop index from enumerating the reconstructed `(start, stop)` trial list, not the NWB `trial number` time series.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "0-based per-trial index repeated across frames" (line 217)

**Code** (convert_data.py:359):
```python
np.full(n_time, float(trial_idx), dtype=np.float32),
```

**What this does:** The integer trial index is broadcast to a constant float vector of length `n_time` for the trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Previous trial reward outcome -> `input[3]` ... For trial `t`, use reward outcome of trial `t-1`; first trial defaults to `0`" (line 218)

**Code** (convert_data.py:289, 317, 162-171):
```python
reward_times = behavior["Reward/timestamps"][:].astype(np.float64)
...
reward_outcomes = reward_outcomes_from_timestamps(reward_times, position_t, trials)
...
def reward_outcomes_from_timestamps(reward_times, trial_times, trials):
    outcomes = np.zeros(len(trials), dtype=np.int8)
    reward_ptr = 0
    for trial_idx, (start, stop) in enumerate(trials):
        start_t = trial_times[start]
        stop_t = trial_times[stop]
        while reward_ptr < len(reward_times) and reward_times[reward_ptr] < start_t:
            reward_ptr += 1
        outcomes[trial_idx] = int(reward_ptr < len(reward_times) and reward_times[reward_ptr] < stop_t)
    return outcomes
```

**What this does:** Derived from the `Reward` time series timestamps. For each trial, a binary outcome flag is set if any reward timestamp falls within the trial's start/stop time window. The previous trial's outcome is then used.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "first trial defaults to `0`; repeat across frames" (line 218)

**Code** (convert_data.py:344-345, 360):
```python
reward_code = int(reward_outcomes[trial_idx])
prev_reward = int(reward_outcomes[trial_idx - 1]) if trial_idx > 0 else 0
...
np.full(n_time, float(prev_reward), dtype=np.float32),
```

**What this does:** For trial `t > 0`, the previous trial's outcome (0/1) is used; trial 0 defaults to 0. The value is repeated across all frames in the trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`position` + trial reward-zone coordinates -> `output[0]` = `distance_to_reward_zone_bin`. Signed distance to nearest point in active reward zone" (line 219)
> "Reward zones A/B/C are fixed track spans: A `80-130`, B `200-250`, C `320-370` cm." (line 144)

**Code** (convert_data.py:23-27, 282, 340-341):
```python
ZONE_COORDS_CM = {
    "A": (80.0, 130.0),
    "B": (200.0, 250.0),
    "C": (320.0, 370.0),
}
...
position = behavior["position/data"][:].astype(np.float32)
...
env_name, zone_name = zone_for_trial(scene_info, trial_idx)
zone_start, zone_end = ZONE_COORDS_CM[zone_name]
```

**What this does:** Distance is derived from the `position` behavioral time series and the per-trial reward zone (A/B/C) parsed from the scene identifier. The fixed zone coordinates from the paper define the zone bounds.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Signed distance to nearest point in active reward zone: negative before zone, zero inside, positive after zone" (line 219)

**Code** (convert_data.py:174-187):
```python
def discretize_distance_to_zone(position_cm, zone_start, zone_end):
    distance = np.where(
        position_cm < zone_start,
        position_cm - zone_start,
        np.where(position_cm > zone_end, position_cm - zone_end, 0.0),
    )
    bins = np.full(distance.shape, 6, dtype=np.int16)
    bins[distance < -50.0] = 0
    bins[(distance >= -50.0) & (distance < -10.0)] = 1
    bins[(distance >= -10.0) & (distance < 0.0)] = 2
    bins[distance == 0.0] = 3
    bins[(distance > 0.0) & (distance <= 10.0)] = 4
    bins[(distance > 10.0) & (distance <= 50.0)] = 5
    return bins
```

**What this does:** Computes signed distance from current position to the nearest zone edge: negative before the zone, 0 inside, positive after. Then discretizes into the 7 bins below.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md):
> Output values: `["lt_-50", "minus50_to_minus10", "minus10_to_lt0", "in_zone", "gt0_to_10", "gt10_to_50", "gt50"]` (line 48 in code)

**Code** (convert_data.py:180-187):
```python
bins = np.full(distance.shape, 6, dtype=np.int16)
bins[distance < -50.0] = 0
bins[(distance >= -50.0) & (distance < -10.0)] = 1
bins[(distance >= -10.0) & (distance < 0.0)] = 2
bins[distance == 0.0] = 3
bins[(distance > 0.0) & (distance <= 10.0)] = 4
bins[(distance > 10.0) & (distance <= 50.0)] = 5
return bins
```

**What this does:** 7 bins are assigned by hard-coded thresholds at -50, -10, 0 (exact), 10, 50 cm. The `distance == 0.0` case is its own "in_zone" bin, and any value outside the explicit ranges falls to bin 6 (`gt50`).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use only in-trial frames; exclude teleport." (line 220)

**Code** (convert_data.py:329, 347, 349):
```python
pos_trial = position[start:stop]
...
neural_trial = deconvolved[start:stop].T
...
dist_bin = discretize_distance_to_zone(pos_trial, zone_start, zone_end)
```

**What this does:** Position and neural data share the same `start:stop` frame slice, so the discretized distance vector is automatically aligned with the neural time axis frame-by-frame.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`position` -> `output[1]` = `absolute_position_bin`. Bin position on `0-450 cm` track into 5 equal bins" (line 220)

**Code** (convert_data.py:282, 329):
```python
position = behavior["position/data"][:].astype(np.float32)
...
pos_trial = position[start:stop]
```

**What this does:** Derived from the `position` behavioral time series, sliced to the trial frame range.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Bin position on `0-450 cm` track into 5 equal bins" (line 220)

**Code** (convert_data.py:190-193, 350):
```python
def discretize_absolute_position(position_cm: np.ndarray) -> np.ndarray:
    clipped = np.clip(position_cm, TRACK_START_CM, np.nextafter(TRACK_END_CM, TRACK_START_CM))
    edges = np.linspace(TRACK_START_CM, TRACK_END_CM, 6)
    return np.digitize(clipped, edges[1:-1], right=False).astype(np.int16)
...
pos_bin = discretize_absolute_position(pos_trial)
```

**What this does:** Position is clipped to `[0, 450)` cm, then discretized into 5 equal-width bins via `np.digitize` against `linspace(0, 450, 6)`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md):
> Output values: `["bin0", "bin1", "bin2", "bin3", "bin4"]` (line 49 in code)

**Code** (convert_data.py:16-17, 190-193):
```python
TRACK_START_CM = 0.0
TRACK_END_CM = 450.0
...
clipped = np.clip(position_cm, TRACK_START_CM, np.nextafter(TRACK_END_CM, TRACK_START_CM))
edges = np.linspace(TRACK_START_CM, TRACK_END_CM, 6)
return np.digitize(clipped, edges[1:-1], right=False).astype(np.int16)
```

**What this does:** 5 equal-width bins of 90 cm each spanning 0-450 cm; positions are clipped to within the track before digitizing. Negative pre-sync (-500) values map to bin 0 after clipping.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use only in-trial frames; exclude teleport." (line 220)

**Code** (convert_data.py:329, 347, 350):
```python
pos_trial = position[start:stop]
...
neural_trial = deconvolved[start:stop].T
...
pos_bin = discretize_absolute_position(pos_trial)
```

**What this does:** Same `start:stop` slice as neural data; alignment is automatic with one bin per frame.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`lick` -> `output[3]` = `lick`. Clip cumulative lick counts to binary `0/1`" (line 222)

**Code** (convert_data.py:285, 331):
```python
lick = behavior["lick/data"][:].astype(np.float32)
...
lick_trial = lick[start:stop]
```

**What this does:** Derived from the `lick` behavioral time series, sliced to the trial range.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Clip cumulative lick counts to binary `0/1`; bad-lick trials dropped by QC rule" (line 222)

**Code** (convert_data.py:205-206, 352):
```python
def binarize_licks(lick_trial: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(lick_trial), 0, 1).astype(np.int16)
...
lick_bin = binarize_licks(lick_trial)
```

**What this does:** The lick stream is rounded to nearest int, then clipped to `[0, 1]`, producing a binary per-frame lick output.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none specifically; lines 148-149 note neural and behavior share frame grid)

**Code** (convert_data.py:331, 347, 352):
```python
lick_trial = lick[start:stop]
...
neural_trial = deconvolved[start:stop].T
...
lick_bin = binarize_licks(lick_trial)
```

**What this does:** Same `start:stop` indexing as the neural data, producing a per-frame aligned lick vector.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Scene-derived active reward zone -> `output[4]` = `reward_zone_location`. Map `A/B/C -> 0/1/2`" (line 223)
> "NWB `reward_zone` is not the A/B/C label. Active reward-zone identity will be parsed from the session identifier" (line 231)

**Code** (convert_data.py:89-128, 131-134, 275, 343):
```python
identifier = decode_h5_scalar(handle["identifier"])
...
scene_info = parse_scene(identifier)
...
def zone_for_trial(scene_info, trial_idx):
    if scene_info["switch"] and trial_idx >= SWITCH_TRIAL:
        return scene_info["post_env"], scene_info["post_zone"]
    return scene_info["pre_env"], scene_info["pre_zone"]
...
zone_code = int(ZONE_TO_INT[zone_name])
```

**What this does:** Reward zone identity is parsed from the NWB `identifier` scene string using regex over three formats (`Env1_LocationA`, `Env1_LocationA_to_B`, `Env1_A_to_Env2_C`). Zones are encoded A=0, B=1, C=2.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Map `A/B/C -> 0/1/2`; repeat across frames in the trial" (line 223)

**Code** (convert_data.py:20, 28, 131-134, 369):
```python
SWITCH_TRIAL = 30
...
ZONE_TO_INT = {"A": 0, "B": 1, "C": 2}
...
def zone_for_trial(scene_info, trial_idx):
    if scene_info["switch"] and trial_idx >= SWITCH_TRIAL:
        return scene_info["post_env"], scene_info["post_zone"]
    return scene_info["pre_env"], scene_info["pre_zone"]
...
np.full(n_time, zone_code, dtype=np.int16),
```

**What this does:** For switch sessions, trials before index 30 use the pre-switch zone; trials >=30 use the post-switch zone. The integer zone code is broadcast across all frames in the trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trial reward delivery from `BehavioralTimeSeries/Reward` -> `output[5]` = `reward_outcome`. `1` if any reward event timestamp falls within trial, else `0`" (line 224)

**Code** (convert_data.py:289, 162-171):
```python
reward_times = behavior["Reward/timestamps"][:].astype(np.float64)
...
def reward_outcomes_from_timestamps(reward_times, trial_times, trials):
    outcomes = np.zeros(len(trials), dtype=np.int8)
    reward_ptr = 0
    for trial_idx, (start, stop) in enumerate(trials):
        start_t = trial_times[start]
        stop_t = trial_times[stop]
        while reward_ptr < len(reward_times) and reward_times[reward_ptr] < start_t:
            reward_ptr += 1
        outcomes[trial_idx] = int(reward_ptr < len(reward_times) and reward_times[reward_ptr] < stop_t)
    return outcomes
```

**What this does:** Derived from the `Reward` time series' timestamps, compared against the position-time trial start/stop timestamps.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`1` if any reward event timestamp falls within trial, else `0`; repeat across frames" (line 224)

**Code** (convert_data.py:162-171, 344, 370):
```python
outcomes[trial_idx] = int(reward_ptr < len(reward_times) and reward_times[reward_ptr] < stop_t)
...
reward_code = int(reward_outcomes[trial_idx])
...
np.full(n_time, reward_code, dtype=np.int16),
```

**What this does:** A single-pointer scan over reward timestamps marks each trial as 1 if any reward time is in `[start_t, stop_t)`, else 0. The per-trial value is repeated across all frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Drops trials failing lick-sensor QC" (line 259)
> "skipping {path.name}: fewer than 2 usable trials after QC" (line 493 in code)

**Code** (convert_data.py:308-312, 326-338, 492-494):
```python
if plane_data.shape[1] != cols.size:
    raise ValueError(
        f"{path.name}: {plane_key} has {plane_data.shape[1]} ROIs but planeIdx maps {cols.size}"
    )
...
if stop <= start:
    continue
...
if pos_trial.size < 2:
    continue
if is_bad_lick_trial(lick_trial):
    dropped_bad_lick += 1
    continue
...
if len(session_data["neural_trials"]) < 2:
    print(f"  skipping {path.name}: fewer than 2 usable trials after QC")
    continue
```

**What this does:** Several defensive checks: invalid (stop <= start) trials are skipped; trials with <2 frames are skipped; bad-lick trials are dropped with a counter; sessions with fewer than 2 usable trials are skipped; multi-plane shape mismatches raise an error. No explicit handling for negative pre-sync `position` (-500) or `environment` (-1) values besides clipping in the position discretizer.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Large multi-plane benchmark (`m18 ses-03`) ~2.49 s/session; Conservative upper bound ~6.3 min for 152 sessions" (line 325)
> "Full-session deconvolved activity is currently loaded into memory per session before trial slicing." (line 272)

**Code** (convert_data.py:300-314, 477-490):
```python
deconvolved = np.asarray(deconv_group[plane_keys[0]]["data"][:, curated_idx], dtype=np.float16)
...
for plane_key in plane_keys:
    ...
    plane_data = np.asarray(deconv_group[plane_key]["data"], dtype=np.float16)
    ...
    all_deconvolved[:, cols] = plane_data
...
for session_number, path in enumerate(session_files):
    session_t0 = time.perf_counter()
    session_data, stats = load_session(...)
    elapsed = time.perf_counter() - session_t0
    print(...)
```

**What this does:** Per-session NWB I/O (especially loading the full deconvolved matrix) is the dominant cost. Multi-plane sessions read both planes; per-session timings are printed.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "No parallel file processing yet." (line 273)

**Code** (convert_data.py:325-388, 165-171):
```python
for trial_idx, (start, stop) in enumerate(trials):
    ...
    dist_bin = discretize_distance_to_zone(pos_trial, zone_start, zone_end)
    pos_bin = discretize_absolute_position(pos_trial)
    speed_bin = discretize_speed(speed_trial)
    lick_bin = binarize_licks(lick_trial)
    ...
# and:
for trial_idx, (start, stop) in enumerate(trials):
    start_t = trial_times[start]
    stop_t = trial_times[stop]
    while reward_ptr < len(reward_times) and reward_times[reward_ptr] < start_t:
        reward_ptr += 1
```

**What this does:** Per-trial loop applies discretization functions trial-by-trial, and the reward-outcome assignment uses a sequential pointer scan over trials. The per-session loop is also serial across files. The code itself does not call out vectorization opportunities.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none — no explicit "repeated processing" section)

**Code** (convert_data.py:273-320):
```python
def load_session(path: Path, show_processing: bool):
    with h5py.File(path, "r") as handle:
        ...
```

**What this does:** Each session is loaded only once; no separate "survey" pre-pass over the dataset is performed. (No relevant code found indicating intentional repeated processing.)

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:209-270):
```python
def make_processing_plot(session_label, savedir, neural_trials, input_trials, output_trials, raw_examples):
    fig, axes = plt.subplots(4, 2, figsize=(16, 14), constrained_layout=True)
    ...
    plot_path = savedir / f"processing_{session_label}.png"
    fig.savefig(plot_path, dpi=150)
```

**What this does:** Optional `--show-processing` plotting computes and renders figures that are not consumed by downstream training. Otherwise no obviously discarded computation. (No explicit notes-based discussion.)

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
