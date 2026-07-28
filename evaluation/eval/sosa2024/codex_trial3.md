# sosa2024 — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/sosa2024/codex/2026-03-11__11-30-50_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> `data/` contains one NWB file per subject-session plus `dandiset.yaml`. File layout is `data/sub-<mouse>/sub-<mouse>_ses-<NN>_behavior+ophys.nwb`. There are 152 NWB files total across 11 subjects. (lines 88-90)

**Code** (convert_data.py:62-66, 273):
```python
def list_nwb_files(sample: bool) -> list[Path]:
    files = sorted(DATA_ROOT.glob("sub-*/sub-*_behavior+ophys.nwb"))
    if sample:
        return files[:2]
    return files
...
    with h5py.File(path, "r") as f:
```

**What this does:** Globs all `sub-*/sub-*_behavior+ophys.nwb` files under `data/` and reads each via `h5py` directly (rather than `pynwb`). In sample mode, processes the first 2 files; otherwise all 152.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> Subject IDs: `m3, m4, m7, m11, m12, m13, m14, m15, m17, m18, m19` (line 134)

**Code** (convert_data.py:278, 473-474):
```python
subject = path.parent.name.replace("sub-", "")
...
subjects = sorted({sess["subject"] for sess in processed_sessions})
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
```

**What this does:** Subject ID is parsed from the `sub-<id>` parent directory name of each NWB file. The unique sorted set defines the `subjects` list and per-session `subject_idx`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> Session counts by subject: `m11`: 12; all others: 14 (lines 135-137)

**Code** (convert_data.py:62-63, 272, 279):
```python
files = sorted(DATA_ROOT.glob("sub-*/sub-*_behavior+ophys.nwb"))
...
session_id = path.stem.replace("_behavior+ophys", "")
...
session_name = path.stem
```

**What this does:** Each NWB file is treated as one session. The session name is derived from the file stem (e.g., `sub-m11_ses-03`).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> Use `trial_start > 0` and `teleport > 0` to define trial epochs; these match one-for-one in all files. (line 229)

**Code** (convert_data.py:131-147):
```python
def find_complete_trial_bounds(trial_start, teleport):
    starts = np.flatnonzero(trial_start > 0)
    teleports = np.flatnonzero(teleport > 0)
    bounds = []
    teleport_idx = 0
    for start in starts:
        while teleport_idx < len(teleports) and teleports[teleport_idx] <= start:
            teleport_idx += 1
        if teleport_idx >= len(teleports):
            break
        stop = teleports[teleport_idx]
        if stop > start:
            bounds.append((int(start), int(stop)))
        teleport_idx += 1
    return bounds
```

**What this does:** Identifies trial intervals as `[start, stop)` pairs where `start` is a `trial_start>0` frame and `stop` is the next `teleport>0` frame strictly after it. Incomplete trials (start without subsequent teleport) are dropped.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> Drops lick-artifact trials using the reference-code-style `>35%` rule. (line 305)

**Code** (convert_data.py:163-166, 339-342, 374-376, 383-386):
```python
def has_lick_sensor_error(lick_segment):
    if lick_segment.size == 0:
        return True
    return bool(np.mean(lick_segment > 2) > LICK_ERROR_FRACTION)  # 0.35
...
if stop - start < MIN_TRIAL_FRAMES:  # 5
    dropped_missing += 1
    continue
...
if meta["lick_error"]:
    dropped_lick += 1
    continue
...
frame_mask = valid_behavior_frames[start:stop] & valid_neural_frames[start:stop]
if np.count_nonzero(frame_mask) < MIN_TRIAL_FRAMES:
    dropped_missing += 1
    continue
```

**What this does:** Drops trials with fewer than 5 frames, drops trials where >35% of lick samples exceed cumulative count 2 (lick-sensor artifact), and drops trials whose valid (finite, position>-100) neural+behavior frame count is below 5.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> Use NWB deconvolved traces directly: The paper's RR decoder uses deconvolved calcium events, and the NWB `Deconvolved` data are the released equivalent of reference `sess.timeseries['events']`. (line 269)

**Code** (convert_data.py:303-308):
```python
planes = sorted(int(x) for x in np.unique(plane_idx_all))
for plane in planes:
    plane_roi_idx = np.flatnonzero(plane_idx_all == plane)
    accepted_total_idx = plane_roi_idx[accepted_mask[plane_roi_idx]]
    accepted_local_idx = np.flatnonzero(accepted_mask[plane_roi_idx])
    plane_data = ophys_group[f"Deconvolved/plane{plane}/data"][:, accepted_local_idx]
```

**What this does:** Reads `processing/ophys/Deconvolved/plane{N}/data` for each imaging plane.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> Do not recompute dF/F from fluorescence: The release already provides frame-aligned deconvolved traces. (line 271)

**Code** (convert_data.py:301-316, 393):
```python
deconv_shape_t = None
deconv = None
planes = sorted(int(x) for x in np.unique(plane_idx_all))
for plane in planes:
    plane_roi_idx = np.flatnonzero(plane_idx_all == plane)
    accepted_total_idx = plane_roi_idx[accepted_mask[plane_roi_idx]]
    accepted_local_idx = np.flatnonzero(accepted_mask[plane_roi_idx])
    plane_data = ophys_group[f"Deconvolved/plane{plane}/data"][:, accepted_local_idx]
    plane_data = plane_data.astype(np.float32, copy=False)
    if deconv_shape_t is None:
        deconv_shape_t = plane_data.shape[0]
        deconv = np.empty((deconv_shape_t, accepted_idx.size), dtype=np.float32)
    dest_cols = np.searchsorted(accepted_idx, accepted_total_idx)
    deconv[:, dest_cols] = plane_data
...
neural_trial = deconv[trial_slice][frame_mask].T.astype(np.float32, copy=False)
```

**What this does:** For multi-plane sessions, concatenates per-plane deconvolved traces into the pooled accepted-ROI ordering. Per-trial neural data is sliced and transposed to `(n_neurons, n_timepoints)`. No further numerical processing is applied.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> Filter neurons with `iscell[:,0] == 1` only: This is the shared, explicit curated-cell mask available in NWB. (line 270)

**Code** (convert_data.py:295-299):
```python
iscell = ophys_group["ImageSegmentation/PlaneSegmentation/iscell"][()]
accepted_mask = np.asarray(iscell[:, 0]) == 1
accepted_idx = np.flatnonzero(accepted_mask)
plane_idx_all = ophys_group["ImageSegmentation/PlaneSegmentation/planeIdx"][()].astype(np.int16)
plane_idx = plane_idx_all[accepted_idx]
```

**What this does:** Uses suite2p's `iscell[:,0] == 1` flag to keep only curated accepted cells. No additional interneuron exclusion is performed.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> Behavior timestamps have spacing about `0.0645 s` (~15.5 Hz). (line 120) ... Use behavior timestamps / shared sample length as the aligned time base (~15.5 Hz effective). (line 234)

**Code** (convert_data.py:454, 476-478):
```python
"time_bin_size_ms": float(np.median(np.diff(timestamps)) * 1000.0),
...
median_bin_ms = float(
    np.median([sess["summary"]["time_bin_size_ms"] for sess in processed_sessions])
)
```

**What this does:** Neural data is kept at its native frame-aligned rate (no resampling). The time-bin size in metadata is the median of behavior-timestamp diffs across sessions.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> Segment trials from `trial_start` to `teleport`. (line 272) ... `temporal_alignment_event": "trial_start"` (line 519)

**Code** (convert_data.py:388-393):
```python
trial_slice = slice(start, stop)
position_trial = position[trial_slice][frame_mask]
...
time_trial = timestamps[trial_slice][frame_mask] - timestamps[start]
neural_trial = deconv[trial_slice][frame_mask].T.astype(np.float32, copy=False)
```

**What this does:** Per-trial neural data is sliced from the trial start frame; `time_from_trial_start_sec` starts at 0 at the trial-start frame. No offset beyond the slice.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> behavior timestamps within each trial -> `input[0]` (`time_from_trial_start_sec`) (line 257)

**Code** (convert_data.py:292, 392):
```python
timestamps = behavior_group["position/timestamps"][()].astype(np.float64)
...
time_trial = timestamps[trial_slice][frame_mask] - timestamps[start]
```

**What this does:** Derived from the `position` time series timestamps in the BehavioralTimeSeries group.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

**Notes excerpt** (CONVERSION_NOTES.md):
> `timestamps[start:stop] - timestamps[start]` (line 257)

**Code** (convert_data.py:392, 400):
```python
time_trial = timestamps[trial_slice][frame_mask] - timestamps[start]
...
time_trial.astype(np.float32),
```

**What this does:** Subtracts the trial-start timestamp from each in-trial timestamp to produce seconds since trial start; cast to float32.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> the released NWB files are processed, frame-aligned session-level data ... Conversion should therefore avoid re-deriving alignment from raw files. (lines 238-239)

**Code** (convert_data.py:331, 383, 392-393):
```python
valid_neural_frames = np.all(np.isfinite(deconv), axis=1)
...
frame_mask = valid_behavior_frames[start:stop] & valid_neural_frames[start:stop]
...
time_trial = timestamps[trial_slice][frame_mask] - timestamps[start]
neural_trial = deconv[trial_slice][frame_mask].T.astype(np.float32, copy=False)
```

**What this does:** Both behavior timestamps and neural deconv traces share the same NWB sample grid; the same `frame_mask` is applied to both, so they are inherently co-indexed.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> `processing/behavior/BehavioralTimeSeries/environment/data` -> `input[1]` (`environment`) (line 258)

**Code** (convert_data.py:287, 345):
```python
environment = behavior_group["environment/data"][()].astype(np.float32)
...
env_bin = env_to_binary(environment[start:stop])
```

**What this does:** Derived from the `environment` behavioral time series.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

**Notes excerpt** (CONVERSION_NOTES.md):
> Take per-trial modal value in `{0,1}` and repeat across timepoints (line 258)

**Code** (convert_data.py:111-117, 401):
```python
def env_to_binary(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    values = values[values >= 0]
    if values.size == 0:
        raise ValueError("No valid environment values in trial.")
    return int(np.round(np.median(values)) > 0.5)
...
np.full(time_trial.shape, meta["environment"], dtype=np.float32),
```

**What this does:** Filters out non-finite and sentinel `-1` values, takes the median rounded to 0/1, and repeats this scalar across all timepoints in the trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> `processing/behavior/BehavioralTimeSeries/trial number/data` or trial index -> `input[2]` (`trial_number`); Use per-trial integer index (0-based within session). (line 259)

**Code** (convert_data.py:289, 344):
```python
trial_number = behavior_group["trial number/data"][()].astype(np.float32)
...
trial_num = modal_trial_number(trial_number[start:stop])
```

**What this does:** Derived from the NWB `trial number` behavioral time series (taking the per-trial mode), not from a pure loop counter.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

**Notes excerpt** (CONVERSION_NOTES.md):
> Use per-trial integer index (0-based within session), repeated across timepoints (line 259)

**Code** (convert_data.py:120-128, 402):
```python
def modal_trial_number(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    values = np.rint(values).astype(np.int64)
    values = values[values >= 0]
    if values.size == 0:
        raise ValueError("No valid trial numbers in trial.")
    counts = np.bincount(values)
    return int(np.argmax(counts))
...
np.full(time_trial.shape, trial_num, dtype=np.float32),
```

**What this does:** Takes the modal (most common, integer-rounded) value of the `trial number` time series within the trial epoch, then broadcasts the scalar across all timepoints.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> prior trial reward outcome -> `input[3]` (`previous_trial_rewarded`); Compute from previous complete trial. (line 260)

**Code** (convert_data.py:150-160, 348-354):
```python
def reward_outcome_for_trial(reward_timestamps, t_start, t_stop, reward_zone_segment):
    left = np.searchsorted(reward_timestamps, t_start, side="left")
    right = np.searchsorted(reward_timestamps, t_stop, side="left")
    has_reward = right > left
    has_rzone_entry = np.any(reward_zone_segment > 0)
    return int(has_reward and has_rzone_entry)
...
reward_outcome = reward_outcome_for_trial(
    reward_timestamps=reward_timestamps,
    t_start=float(timestamps[start]),
    t_stop=float(timestamps[stop]),
    reward_zone_segment=reward_zone[start:stop],
)
reward_by_trial_number[trial_num] = reward_outcome
```

**What this does:** Derived from the `Reward/timestamps` events combined with the `reward_zone` time series. A trial is rewarded if any reward event falls in `[t_start, t_stop)` AND `reward_zone > 0` somewhere in the trial. Each trial's outcome is stored keyed by trial number.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> Set first-trial previous outcome to 0. (line 279)

**Code** (convert_data.py:381, 403):
```python
prev_outcome = reward_by_trial_number.get(trial_num - 1, 0)
...
np.full(time_trial.shape, prev_outcome, dtype=np.float32),
```

**What this does:** Looks up the reward outcome for `trial_num - 1`; defaults to 0 if no such trial exists (e.g., first trial). Broadcast across all timepoints.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> Use paper/code reward-zone semantics rather than inferring from sparse `reward_zone` events alone: ... zone A/B/C must come from session condition metadata. (line 276)

**Code** (convert_data.py:22-27, 274-276, 346-347):
```python
ZONE_TO_COORDS_CM = {
    "A": (80.0, 130.0),
    "B": (200.0, 250.0),
    "C": (320.0, 370.0),
}
...
identifier = decode_bytes(f["identifier"][()])
scene = identifier.split("/")[-1]
scene_info = parse_scene(scene)
...
zone_label = zone_for_trial(scene_info, trial_num)
zone_coords = ZONE_TO_COORDS_CM[zone_label]
```

**What this does:** Reward zone identity comes from parsing the NWB `identifier` scene name (e.g. `Env1_LocationA_to_C`) and applying a 30-trial switch rule. Zone coordinates are hardcoded constants A/B/C. The signed distance is computed from the `position` time series.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

**Notes excerpt** (CONVERSION_NOTES.md):
> Signed nearest distance to zone: `<start => pos-start`, `inside => 0`, `>end => pos-end`, then discretize to 7 bins (line 261)

**Code** (convert_data.py:169-175):
```python
def signed_distance_to_zone(position_cm, zone_start, zone_end):
    distance = np.zeros_like(position_cm, dtype=np.float32)
    before = position_cm < zone_start
    after = position_cm > zone_end
    distance[before] = position_cm[before] - zone_start
    distance[after] = position_cm[after] - zone_end
    return distance
```

**What this does:** Returns negative distance before the zone, 0 inside the zone, and positive distance past the zone end.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md):
> Bins: `<-50`, `[-50,-10]`, `[-10,0)`, `0`, `(0,10]`, `(10,50]`, `>50` cm. (line 261)

**Code** (convert_data.py:178-189):
```python
def discretize_distance(distance_cm):
    out = np.full(distance_cm.shape, -1, dtype=np.int16)
    out[distance_cm < -50] = 0
    out[(distance_cm >= -50) & (distance_cm < -10)] = 1
    out[(distance_cm >= -10) & (distance_cm < 0)] = 2
    out[distance_cm == 0] = 3
    out[(distance_cm > 0) & (distance_cm <= 10)] = 4
    out[(distance_cm > 10) & (distance_cm <= 50)] = 5
    out[distance_cm > 50] = 6
    if np.any(out < 0):
        raise ValueError("Failed to discretize reward-zone distance.")
    return out
```

**What this does:** Hand-coded boolean masks assigning each sample to one of 7 bins (0-6) by signed distance; zero distance gets its own bin (3).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none specific; general alignment via shared frame grid)

**Code** (convert_data.py:388-396):
```python
trial_slice = slice(start, stop)
position_trial = position[trial_slice][frame_mask]
...
neural_trial = deconv[trial_slice][frame_mask].T.astype(np.float32, copy=False)
zone_start, zone_end = meta["zone_coords"]
distance_trial = signed_distance_to_zone(position_trial, zone_start, zone_end)
```

**What this does:** Position and neural arrays are sliced and masked with the same `frame_mask`, so distance-to-zone (computed from masked position) shares the same time index as the neural data.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> `position` -> `output[1]` (`absolute_position_bin`) (line 262)

**Code** (convert_data.py:284, 389):
```python
position = behavior_group["position/data"][()].astype(np.float32)
...
position_trial = position[trial_slice][frame_mask]
```

**What this does:** Derived directly from the `position` behavioral time series.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> Discretize absolute track position on `[0,450]` into 5 equal bins (line 262)

**Code** (convert_data.py:192-196):
```python
def discretize_absolute_position(position_cm):
    clipped = np.clip(position_cm, 0.0, np.nextafter(450.0, 0.0))
    bins = np.floor(clipped / 90.0).astype(np.int16)
    bins[bins > 4] = 4
    return bins
```

**What this does:** Clips position to `[0, 450)` cm, then floor-divides by 90 to get 5 equal-width bins (0-4).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md):
> 5 equal bins on `[0,450]`. (line 262)

**Code** (convert_data.py:192-196):
```python
def discretize_absolute_position(position_cm):
    clipped = np.clip(position_cm, 0.0, np.nextafter(450.0, 0.0))
    bins = np.floor(clipped / 90.0).astype(np.int16)
    bins[bins > 4] = 4
    return bins
```

**What this does:** 5 bins of width 90 cm: `[0,90), [90,180), [180,270), [270,360), [360,450)`. Negative positions are clipped to 0; values >=450 to bin 4.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none specific; via shared `frame_mask`)

**Code** (convert_data.py:388-393):
```python
trial_slice = slice(start, stop)
position_trial = position[trial_slice][frame_mask]
...
neural_trial = deconv[trial_slice][frame_mask].T.astype(np.float32, copy=False)
```

**What this does:** Same `frame_mask` indexing used for both, ensuring co-alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> `lick` -> `output[3]` (`lick`); Convert cumulative lick count per frame to binary (`>0 => 1`) (line 264)

**Code** (convert_data.py:286, 391):
```python
lick = behavior_group["lick/data"][()].astype(np.float32)
...
lick_trial = lick[trial_slice][frame_mask]
```

**What this does:** Derived from the `lick` behavioral time series (cumulative lick count per frame).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

**Notes excerpt** (CONVERSION_NOTES.md):
> binary (`>0 => 1`), after trial-level lick-error filtering (line 264)

**Code** (convert_data.py:412):
```python
(lick_trial > 0).astype(np.int16),
```

**What this does:** Thresholds the lick count at >0 to produce a binary (0/1) per-frame output. Trials previously identified as lick-sensor errors (>35% of frames have cumulative count >2) are entirely dropped before this point.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none specific; via shared `frame_mask`)

**Code** (convert_data.py:391, 393):
```python
lick_trial = lick[trial_slice][frame_mask]
...
neural_trial = deconv[trial_slice][frame_mask].T
```

**What this does:** Lick and neural are sliced/masked with identical indices.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> session scene / switch structure -> `output[4]` (`reward_zone_location`); Map trial to zone label `A/B/C`. For switch sessions, use pre-switch zone for trials `<30`, post-switch zone for trials `>=30`. (line 265)

**Code** (convert_data.py:29-31, 75-108, 274-276, 346):
```python
SCENE_SINGLE_RE = re.compile(r"^(Env[12])_Location([ABC])$")
SCENE_SWITCH_RE = re.compile(r"^(Env[12])_Location([ABC])_to_([ABC])$")
SCENE_CROSS_ENV_RE = re.compile(r"^(Env[12])_([ABC])_to_(Env[12])_([ABC])$")
...
def parse_scene(scene): ...  # returns SceneInfo with before/after env+zone
def zone_for_trial(scene_info, trial_number):
    if scene_info.has_switch and trial_number >= SWITCH_TRIAL:  # 30
        return scene_info.after_zone
    return scene_info.before_zone
...
identifier = decode_bytes(f["identifier"][()])
scene = identifier.split("/")[-1]
scene_info = parse_scene(scene)
...
zone_label = zone_for_trial(scene_info, trial_num)
```

**What this does:** Parses the NWB `identifier` scene name with three regexes to extract before/after zone labels, then assigns A/B/C per trial based on the trial number (switch at trial 30).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

**Notes excerpt** (CONVERSION_NOTES.md):
> encode as `0/1/2`, repeat across timepoints (line 265)

**Code** (convert_data.py:22, 413):
```python
ZONE_TO_CODE = {"A": 0, "B": 1, "C": 2}
...
np.full(time_trial.shape, ZONE_TO_CODE[meta["zone_label"]], dtype=np.int16),
```

**What this does:** Maps the zone label to integer code 0/1/2 and broadcasts across all in-trial frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> reward delivery within trial -> `output[5]` (`reward_outcome`); Trial is rewarded if any reward delivery occurs within the trial and the trial has an `rzone` entry event. (line 266)

**Code** (convert_data.py:293, 150-160):
```python
reward_timestamps = behavior_group["Reward/timestamps"][()].astype(np.float64)
...
def reward_outcome_for_trial(reward_timestamps, t_start, t_stop, reward_zone_segment):
    left = np.searchsorted(reward_timestamps, t_start, side="left")
    right = np.searchsorted(reward_timestamps, t_stop, side="left")
    has_reward = right > left
    has_rzone_entry = np.any(reward_zone_segment > 0)
    return int(has_reward and has_rzone_entry)
```

**What this does:** Derived from the `Reward/timestamps` events combined with the in-trial `reward_zone` time series (requires both reward delivery and a reward-zone entry event).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> encode `0/1`, repeat across timepoints (line 266)

**Code** (convert_data.py:348-354, 414):
```python
reward_outcome = reward_outcome_for_trial(
    reward_timestamps=reward_timestamps,
    t_start=float(timestamps[start]),
    t_stop=float(timestamps[stop]),
    reward_zone_segment=reward_zone[start:stop],
)
reward_by_trial_number[trial_num] = reward_outcome
...
np.full(time_trial.shape, meta["reward_outcome"], dtype=np.int16),
```

**What this does:** `searchsorted` finds reward events whose timestamps fall in `[t_start, t_stop)`; combined with `reward_zone>0` check yields a binary 0/1 broadcast across the trial's frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> Drops lick-artifact trials entirely rather than leaving NaNs. The validator forbids NaNs. (line 278)

**Code** (convert_data.py:163-166, 322-331, 339-342, 374-376, 384-386, 552-557):
```python
def has_lick_sensor_error(lick_segment):
    if lick_segment.size == 0: return True
    return bool(np.mean(lick_segment > 2) > LICK_ERROR_FRACTION)
...
trial_bounds = find_complete_trial_bounds(trial_start, teleport)
valid_behavior_frames = (
    np.isfinite(position) & np.isfinite(speed) & np.isfinite(lick)
    & np.isfinite(environment) & np.isfinite(timestamps)
    & (position > -100.0)
)
valid_neural_frames = np.all(np.isfinite(deconv), axis=1)
...
if stop - start < MIN_TRIAL_FRAMES: dropped_missing += 1; continue
...
if meta["lick_error"]: dropped_lick += 1; continue
...
if np.count_nonzero(frame_mask) < MIN_TRIAL_FRAMES:
    dropped_missing += 1; continue
...
if len(session["neural"]) < 2:
    print(... "Skipping ... only ... valid trials after filtering.")
    continue
```

**What this does:** Per-frame validity mask drops non-finite or sentinel-valued (`position <= -100`) frames. Incomplete trials (no matching teleport), too-short trials, lick-error trials, and sessions with fewer than 2 valid trials are dropped silently/with a print.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> Full conversion runtime: `3.36 min` for all 152 sessions. (line 421) ... Reads NWB directly with `h5py` for speed. (line 302)

**Code** (convert_data.py:308, 593-594):
```python
plane_data = ophys_group[f"Deconvolved/plane{plane}/data"][:, accepted_local_idx]
...
with args.outpicklefile.open("wb") as f:
    pickle.dump(dataset, f, protocol=pickle.HIGHEST_PROTOCOL)
```

**What this does:** No explicit profiling; based on the notes, the dominant costs are loading per-session deconvolved arrays from HDF5 and writing the final 9 GB pickle.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> Filters trials before building output arrays to avoid wasted allocations for dropped trials. (line 318)

**Code** (convert_data.py:339, 373, 549):
```python
for start, stop in trial_bounds: ...
...
for meta in trial_meta: ...
...
for idx, path in enumerate(nwb_files, start=1): ...
```

**What this does:** Per-trial loops compute meta, then per-trial loop builds neural/input/output arrays trial by trial. The discretizers themselves are vectorized within a trial. The notes do not call out specific loop targets for vectorization.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> Processes sessions sequentially and writes only the final pickle, avoiding intermediate I/O. (line 317)

**Code** (no explicit redundant computation found):
```python
# (no relevant code found)
```

**What this does:** (none called out) The conversion is one pass per session; no separate survey pass exists in this script.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:211-268, 422-441):
```python
def build_trial_plot(...):
    ...
if len(kept_examples) < 3:
    ...
    kept_examples.append({...})
```

**What this does:** Diagnostic example trials and processing plots are constructed only when `--show-processing` is passed; otherwise no clearly unused processing was identified in the script.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
