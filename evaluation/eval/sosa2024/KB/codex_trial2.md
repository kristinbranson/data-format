# sosa2024 — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/sosa2024/codex/2026-03-11__11-30-50_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:96-109):
> `data/` contains one NWB file per subject-session plus `dandiset.yaml`. File pattern: `data/sub-<mouse>/sub-<mouse>_ses-<NN>_behavior+ophys.nwb`. Total NWB files: 152.

**Code** (convert_data.py:96-100, 319-321):
```python
def list_session_files() -> list[str]:
    files = sorted(glob.glob(os.path.join("data", "sub-*", "sub-*_behavior+ophys.nwb")))
    if not files:
        raise FileNotFoundError("No NWB files found under data/sub-*/")
    return files
...
def load_session_arrays(path: str) -> SessionArrays:
    with h5py.File(path, "r") as f:
        subject = decode_if_bytes(f["general/subject/subject_id"][()])
```

**What this does:** Discovers NWB files via a glob over `data/sub-*/sub-*_behavior+ophys.nwb` and loads each via direct `h5py` reads (rather than `pynwb`). All matching files are processed in `--full` mode.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:97-104):
> Subject directories present: `sub-m3`, `sub-m4`, `sub-m7`, `sub-m11`, `sub-m12`, `sub-m13`, `sub-m14`, `sub-m15`, `sub-m17`, `sub-m18`, `sub-m19`.

**Code** (convert_data.py:321, 627-629):
```python
subject = decode_if_bytes(f["general/subject/subject_id"][()])
...
if arrays.subject not in subject_to_idx:
    subject_to_idx[arrays.subject] = len(all_subjects)
    all_subjects.append(arrays.subject)
```

**What this does:** Subject ID is read from the NWB `general/subject/subject_id` field per session. A running dictionary assigns each new subject a sequential index; `subjects` list holds unique IDs in encounter order.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:101-104):
> File pattern: `data/sub-<mouse>/sub-<mouse>_ses-<NN>_behavior+ophys.nwb`.

**Code** (convert_data.py:322-323):
```python
session_id = decode_if_bytes(f["general/session_id"][()])
session_label = f"{subject}_ses-{session_id}"
```

**What this does:** Each NWB file represents one session. Session ID is read from `general/session_id` and combined with subject ID for labeling. Each session is processed independently and contributes one entry to the per-session lists in the output dict.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:251):
> Reconstruct trial start/end indices from `trial_start` and `teleport` signals in NWB.

**Code** (convert_data.py:303-316):
```python
def build_trial_slices(trial_start_signal, teleport_signal):
    starts = np.flatnonzero(trial_start_signal > 0.5)
    teleports = np.flatnonzero(teleport_signal > 0.5)
    if starts.size == 0 or teleports.size == 0:
        raise RuntimeError("Missing trial_start or teleport markers.")
    n = min(starts.size, teleports.size)
    slices: list[tuple[int, int]] = []
    for start, stop in zip(starts[:n], teleports[:n]):
        if stop < start:
            continue
        slices.append((int(start), int(stop) + 1))
    if len(slices) < 2:
        raise RuntimeError("Need at least two trials in a session.")
    return slices
```

**What this does:** Trials are derived from the binary `trial_start` and `teleport` signals: trial begins at each `trial_start` rising edge, ends at the next `teleport` index (inclusive). Pairs are zipped up to the minimum count of starts/teleports.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:228-229):
> Licking analysis removes trials with erroneous lick detection when >30% of imaging frames in the trial have cumulative lick count `> 2`.

**Code** (convert_data.py:23, 444-446, 469-471):
```python
LICK_ARTIFACT_FRACTION = 0.35  # Matches glmUtils.get_timeseries_data in the reference code.
...
lick_trial = arrays.lick[start:stop_exclusive]
if lick_trial.size and np.mean(lick_trial > 2) > LICK_ARTIFACT_FRACTION:
    lick_artifact[trial_id] = True
...
for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
    if lick_artifact[trial_id]:
        continue
```

**What this does:** A trial is flagged as a lick artifact when more than 35% of its frames have lick count > 2; flagged trials are skipped during conversion. No minimum trial length filter is applied.

**Rating:** better

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:247):
> Use NWB `processing/ophys/Deconvolved/plane0/data` as the paper-equivalent neural signal.

**Code** (convert_data.py:326, 332):
```python
neural_group = f["processing/ophys/Deconvolved/plane0"]
...
neural = neural_group["data"][()].astype(np.float32, copy=False)
```

**What this does:** Neural data is read directly from `processing/ophys/Deconvolved/plane0/data`. Only plane-0 deconvolved activity is used (no fluorescence or neuropil streams).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:263):
> Crop to valid frame range, select ROI indices from `Deconvolved/plane0/rois`, keep curated cells by `iscell[:,0] > 0.5`, ... transpose to `(neurons, time)`, split by trials, and rebin `31.015625 Hz` sessions to the common `15.5078125 Hz` bin size.

**Code** (convert_data.py:332-340, 458-463, 473, 478-482):
```python
neural = neural_group["data"][()].astype(np.float32, copy=False)
roi_ids = neural_group["rois"][()].astype(np.int64, copy=False)
iscell = seg["iscell"][()][roi_ids, 0] > 0.5
neural = neural[:, iscell]
...
if math.isclose(arrays.rate_hz, TARGET_RATE_HZ):
    factor = 1
elif math.isclose(arrays.rate_hz, 2.0 * TARGET_RATE_HZ):
    factor = 2
...
neural_trial = arrays.neural[start:stop_exclusive].T.astype(np.float32, copy=False)
...
if factor == 2:
    neural_trial = rebin_2d_sum_time_last(neural_trial, factor)
```

**What this does:** ROI-region-aware curation (only ROIs referenced by `Deconvolved/plane0/rois` and with `iscell > 0.5`). Sliced per trial, transposed to `(neurons, time)`. 31 Hz sessions are rebinned to 15.5 Hz by summing pairs of consecutive bins.

**Rating:** incorrect

**Note:** agent is confused about multiplane data, which has twice the frame rate

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:248):
> Filter cells by `iscell[:,0] > 0.5` only on ROI indices listed in `Deconvolved/plane0/rois`. This avoids overcounting plane-1 ROIs that are not in the response matrix.

**Code** (convert_data.py:333-336):
```python
roi_ids = neural_group["rois"][()].astype(np.int64, copy=False)
iscell = seg["iscell"][()][roi_ids, 0] > 0.5
neural = neural[:, iscell]
roi_ids = roi_ids[iscell]
```

**What this does:** Filters columns of the neural matrix using suite2p `iscell[:,0] > 0.5`, restricted to ROI ids referenced by the response matrix. The dF/F-vs-speed correlation interneuron exclusion mentioned in the paper is not implemented (documented as an archive limitation).

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:574):
> `"temporal_alignment_event": "trial_start"`

**Code** (convert_data.py:469-473, 489):
```python
for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
    ...
    neural_trial = arrays.neural[start:stop_exclusive].T.astype(np.float32, copy=False)
...
time_from_start = (np.arange(t_bins, dtype=np.float32) * TARGET_DT_S)
```

**What this does:** Trials are sliced from the trial-start frame to the teleport frame; bin index 0 corresponds to trial start. No additional offset shifting is applied beyond the trial slicing.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:283):
> Standardize all sessions to a common `15.5078125 Hz` bin size.

**Code** (convert_data.py:19-20, 182-193):
```python
TARGET_RATE_HZ = 15.5078125
TARGET_DT_S = 1.0 / TARGET_RATE_HZ
...
def rebin_2d_sum_time_last(x, factor):
    if factor == 1:
        return x.astype(np.float32, copy=False)
    t = x.shape[1]
    n_full = t // factor
    parts = []
    if n_full:
        full = x[:, : n_full * factor].reshape(x.shape[0], n_full, factor).sum(axis=2)
        parts.append(full)
    if t % factor:
        parts.append(x[:, n_full * factor :].sum(axis=1, keepdims=True))
    return np.concatenate(parts, axis=1).astype(np.float32, copy=False)
```

**What this does:** Sessions at the native rate (15.5078125 Hz) are kept as-is; 31.015625 Hz sessions are rebinned by factor 2 via summing consecutive pairs in the time dimension. A trailing partial bin is summed separately if length is odd.

**Rating:** incorrect

**Note:** agent is confused about data rate when multiplane

---

## Q 3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:266):
> Reconstructed trial-relative elapsed time | `input[0]` | Seconds since trial start for each bin.

**Code** (convert_data.py:488-489):
```python
t_bins = neural_trial.shape[1]
time_from_start = (np.arange(t_bins, dtype=np.float32) * TARGET_DT_S)
```

**What this does:** Time vector is constructed from the bin index multiplied by the target bin size (1/15.5078125 s). It is not derived from any NWB timestamp series; it assumes regular sampling at the target rate.

**Rating:** concerning

**Note:** does not use timestamps, assumes they are evenly collected. data looks consistent, so probably ok

---

## Q 3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

**Notes excerpt** (CONVERSION_NOTES.md:266):
> Align all trials to the first frame of the trial.

**Code** (convert_data.py:488-489):
```python
t_bins = neural_trial.shape[1]
time_from_start = (np.arange(t_bins, dtype=np.float32) * TARGET_DT_S)
```

**What this does:** A simple `arange` scaled by `TARGET_DT_S` (≈64.46 ms). No timestamp subtraction; the trial-start origin is implicit in the slicing.

**Rating:** concerning

**Note:** does not use timestamps, assumes they are evenly collected. data looks consistent, so probably ok

---

## Q 3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:284):
> All sessions share the same decoder timebase.

**Code** (convert_data.py:488-489):
```python
t_bins = neural_trial.shape[1]
time_from_start = (np.arange(t_bins, dtype=np.float32) * TARGET_DT_S)
```

**What this does:** The time vector length equals `neural_trial.shape[1]` after rebinning, so it is element-wise aligned with the neural trial bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *Environment type* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:267):
> `processing/behavior/BehavioralTimeSeries/environment/data` | `input[1]` | Per trial, take modal valid environment value (`0` or `1`) and repeat across bins.

**Code** (convert_data.py:351, 440-442):
```python
environment=beh["environment/data"][()][:t_common].astype(np.float32, copy=False),
...
env = arrays.environment[start:stop_exclusive]
env = env[env >= 0]
trial_env[trial_id] = mode_int(env, default=0)
```

**What this does:** Reads `environment` behavior series, drops negative-valued frames (out-of-trial sentinel), takes the mode of the remaining values per trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *Environment type*?

**Notes excerpt** (CONVERSION_NOTES.md:267):
> Map `0 -> ENV1`, `1 -> ENV2`.

**Code** (convert_data.py:111-118, 490):
```python
def mode_int(values, default=0):
    if values.size == 0:
        return default
    values = values.astype(np.int64, copy=False)
    values = values[values >= 0]
    if values.size == 0:
        return default
    return int(np.bincount(values).argmax())
...
env_series = np.full((t_bins,), float(trial_env[trial_id]), dtype=np.float32)
```

**What this does:** Per-trial mode of valid environment values is computed once and broadcast across all bins of that trial via `np.full`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *Trial number* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:268):
> Per trial, use within-session trial index and repeat across bins. Keep native 0-indexing to match code conventions.

**Code** (convert_data.py:469, 491):
```python
for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
    ...
trial_series = np.full((t_bins,), float(trial_id), dtype=np.float32)
```

**What this does:** Uses the loop counter `trial_id` (0-indexed sequential within session). The NWB-stored `trial number` data is used elsewhere for reward attribution but not as the trial-number input.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *Trial number*?

**Notes excerpt** (CONVERSION_NOTES.md:268):
> Per trial, use within-session trial index and repeat across bins.

**Code** (convert_data.py:491):
```python
trial_series = np.full((t_bins,), float(trial_id), dtype=np.float32)
```

**What this does:** Constant per trial, broadcast across the trial's bins via `np.full`.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:269):
> Trial reward outcome shifted by one trial.

**Code** (convert_data.py:357, 363-367, 428-435):
```python
reward_times=beh["Reward/timestamps"][()].astype(np.float64, copy=False),
...
def reward_frames_for_session(arrays):
    if arrays.reward_times.size == 0:
        return np.empty((0,), dtype=np.int64)
    idx = np.searchsorted(arrays.timestamps, arrays.reward_times, side="left")
    return np.clip(idx, 0, arrays.timestamps.shape[0] - 1).astype(np.int64, copy=False)
...
reward_frame_idx = reward_frames_for_session(arrays)
rewarded_trial_ids = set(int(t) for t in arrays.trial_number[reward_frame_idx] if t >= 0)

trial_rewarded = np.array(
    [1 if trial_id in rewarded_trial_ids else 0 for trial_id in range(len(trial_slices))],
    dtype=np.int64,
)
trial_prev_rewarded = np.concatenate([[0], trial_rewarded[:-1]]).astype(np.float32, copy=False)
```

**What this does:** Reward event timestamps are mapped to behavior frames via `searchsorted`, then attributed to a trial via the NWB `trial number` data array. `trial_prev_rewarded` is `trial_rewarded` shifted by one (prepended with 0 for the first trial).

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *Previous trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:269):
> Previous trial rewarded (`1`) vs omitted (`0`), repeated across current-trial bins; first trial gets `0`.

**Code** (convert_data.py:435, 492):
```python
trial_prev_rewarded = np.concatenate([[0], trial_rewarded[:-1]]).astype(np.float32, copy=False)
...
prev_reward_series = np.full((t_bins,), float(trial_prev_rewarded[trial_id]), dtype=np.float32)
```

**What this does:** A single shift-by-one of the trial-rewarded vector (prepending 0); broadcast across the current trial's bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:270, 285):
> `position/data` + inferred reward-zone bounds. Infer from reward-zone-active positions / reward events and fill omission trials within stable blocks.

**Code** (convert_data.py:25-29, 240-300):
```python
ZONE_BOUNDS = {
    0: (80.0, 130.0),   # A
    1: (200.0, 250.0),  # B
    2: (320.0, 370.0),  # C
}
...
def infer_trial_zones(positions, reward_zone_signal, trial_slices, trial_rewarded,
                     reward_frame_idx, trial_by_frame, trial_env):
    ...
    for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
        mask = reward_zone_signal[start:stop_exclusive] > 0
        if np.any(mask):
            zone_pos = float(np.nanmedian(positions[start:stop_exclusive][mask]))
        elif trial_id in reward_pos_by_trial:
            zone_pos = reward_pos_by_trial[trial_id]
        ...
        if np.isfinite(zone_pos):
            observed_position[trial_id] = zone_pos
            observed[trial_id] = int(np.argmin(np.abs(ZONE_CENTERS - zone_pos)))
    ...
    split = min(SWITCH_TRIAL_INDEX, n_trials)
    pre_majority = trial_majority_zone(observed, 0, split, fallback=int(unique_observed[0]))
    post_majority = trial_majority_zone(observed, split, n_trials, fallback=post_fallback)
```

**What this does:** Per-trial reward zone is inferred by taking the median position where `reward_zone > 0`, snapped to the nearest of zones A/B/C centers. Missing trials are filled by majority vote within pre-/post-switch halves (split at trial 30).

**Rating:** ok

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Distance to reward zone*?

**Notes excerpt** (CONVERSION_NOTES.md:270):
> Signed distance to nearest point in active reward zone: negative before zone, `0` inside zone, positive after zone.

**Code** (convert_data.py:222-229):
```python
def compute_distance_to_zone(position_cm, zone_idx):
    zone_start, zone_end = ZONE_BOUNDS[zone_idx]
    distance = np.zeros(position_cm.shape, dtype=np.float32)
    before = position_cm < zone_start
    after = position_cm > zone_end
    distance[before] = position_cm[before] - zone_start
    distance[after] = position_cm[after] - zone_end
    return distance
```

**What this does:** Signed distance from current position to the nearest edge of the active reward zone: 0 inside the zone, negative before, positive after.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-c. How is `output` *Distance to reward zone* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md:50):
> `["lt_-50", "-50_to_-10", "-10_to_lt_0", "0", "gt_0_to_10", "10_to_50", "gt_50"]`

**Code** (convert_data.py:196-205):
```python
def discretize_distance(distance_cm):
    out = np.zeros(distance_cm.shape, dtype=np.int64)
    out[distance_cm < -50.0] = 0
    out[(distance_cm >= -50.0) & (distance_cm < -10.0)] = 1
    out[(distance_cm >= -10.0) & (distance_cm < 0.0)] = 2
    out[distance_cm == 0.0] = 3
    out[(distance_cm > 0.0) & (distance_cm <= 10.0)] = 4
    out[(distance_cm > 10.0) & (distance_cm <= 50.0)] = 5
    out[distance_cm > 50.0] = 6
    return out
```

**What this does:** Hand-coded boolean masks place each value into one of 7 bins with thresholds at ±50, ±10, and exactly 0. The `==0` case is a separate bin matching the "inside zone" sentinel.

**Rating:** ok

**Note:** _(no note)_

---

## Q 7-d. How is `output` *Distance to reward zone* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:570 paraphrase):
> Per-trial slice using same trial slicing as neural; rebinned with `rebin_1d_mean` for 31 Hz sessions.

**Code** (convert_data.py:474, 480, 495-496):
```python
position = np.clip(arrays.position[start:stop_exclusive], 0.0, TRACK_LENGTH_CM)
...
position = rebin_1d_mean(position, factor)
...
dist = compute_distance_to_zone(position, zone_idx)
dist_bin = discretize_distance(dist)
```

**What this does:** Uses the same `[start:stop_exclusive]` indices as the neural slice; for 31 Hz sessions position is mean-rebinned by factor 2 to align frame-by-frame with the rebinned neural data.

**Rating:** incorrect

**Note:** propagated error from misunderstanding about neural data rate, bins position

---

## Q 8-a. What variables in the raw data is `output` *Absolute position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:271):
> `processing/behavior/BehavioralTimeSeries/position/data` | `output[1]` | Discretize absolute position on the 450 cm corridor into 5 equal bins.

**Code** (convert_data.py:348, 474):
```python
position=beh["position/data"][()][:t_common].astype(np.float32, copy=False),
...
position = np.clip(arrays.position[start:stop_exclusive], 0.0, TRACK_LENGTH_CM)
```

**What this does:** Reads `position` series and clips to `[0, 450]` cm before discretization.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What processing is involved in computing `output` *Absolute position*?

**Notes excerpt** (CONVERSION_NOTES.md:271):
> Discretize absolute position on the 450 cm corridor into 5 equal bins.

**Code** (convert_data.py:21, 208-210, 474, 497):
```python
TRACK_LENGTH_CM = 450.0
...
def discretize_position(position_cm):
    clipped = np.clip(position_cm, 0.0, TRACK_LENGTH_CM - 1e-6)
    return np.minimum((clipped / (TRACK_LENGTH_CM / 5.0)).astype(np.int64), 4)
...
position = np.clip(arrays.position[start:stop_exclusive], 0.0, TRACK_LENGTH_CM)
...
pos_bin = discretize_position(position)
```

**What this does:** Position values are clipped to `[0, 450)` and divided by 90 cm bin width, capped at index 4. Negative positions (mentioned in dataset survey) are clipped to 0 rather than placed in their own bin.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-c. How is `output` *Absolute position* thresholded into categories?

**Notes excerpt** (CONVERSION_NOTES.md:271):
> 5 equal bins on the 450 cm corridor.

**Code** (convert_data.py:208-210):
```python
def discretize_position(position_cm):
    clipped = np.clip(position_cm, 0.0, TRACK_LENGTH_CM - 1e-6)
    return np.minimum((clipped / (TRACK_LENGTH_CM / 5.0)).astype(np.int64), 4)
```

**What this does:** Five equal-width bins of 90 cm spanning `[0, 450)`. Bin edges are 0, 90, 180, 270, 360, 450.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-d. How is `output` *Absolute position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:570 paraphrase):
> Same per-trial slicing and rebinning as neural.

**Code** (convert_data.py:474, 480, 497):
```python
position = np.clip(arrays.position[start:stop_exclusive], 0.0, TRACK_LENGTH_CM)
...
position = rebin_1d_mean(position, factor)
...
pos_bin = discretize_position(position)
```

**What this does:** Same trial slicing as neural; mean-rebin by factor 2 for 31 Hz sessions ensures bin-by-bin alignment with neural.

**Rating:** incorrect

**Note:** propagated error from misunderstanding about neural data rate

---

## Q 9-a. What variables in the raw data is `output` *Lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:273):
> `processing/behavior/BehavioralTimeSeries/lick/data` | `output[3]` | Convert to binary per bin (`lick > 0`).

**Code** (convert_data.py:350, 476):
```python
lick=beh["lick/data"][()][:t_common].astype(np.float32, copy=False),
...
lick_binary = (arrays.lick[start:stop_exclusive] > 0).astype(np.int64, copy=False)
```

**What this does:** Reads the `lick` behavior series; values >0 within the trial are marked as licks.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-b. What processing is involved in computing `output` *Lick*?

**Notes excerpt** (CONVERSION_NOTES.md:273):
> For rebinned 31 Hz sessions, use logical OR within each 15.5 Hz bin.

**Code** (convert_data.py:170-179, 476, 482):
```python
def rebin_1d_any(x, factor):
    if factor == 1:
        return x.astype(np.int64, copy=False)
    n_full = x.shape[0] // factor
    out = []
    if n_full:
        out.append(np.any(x[: n_full * factor].reshape(n_full, factor) > 0, axis=1))
    if x.shape[0] % factor:
        out.append(np.array([np.any(x[n_full * factor :] > 0)], dtype=bool))
    return np.concatenate(out).astype(np.int64, copy=False)
...
lick_binary = (arrays.lick[start:stop_exclusive] > 0).astype(np.int64, copy=False)
...
lick_binary = rebin_1d_any(lick_binary, factor)
```

**What this does:** Threshold at >0 to binary; for 31 Hz sessions, OR across each pair of consecutive frames so a bin is 1 if either subframe had a lick.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. How is `output` *Lick* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:273 paraphrase):
> Same trial slicing and rebinning as neural.

**Code** (convert_data.py:476, 482):
```python
lick_binary = (arrays.lick[start:stop_exclusive] > 0).astype(np.int64, copy=False)
...
lick_binary = rebin_1d_any(lick_binary, factor)
```

**What this does:** Slice indices match neural; factor-2 OR-rebin matches neural rebinning for 31 Hz sessions.

**Rating:** incorrect

**Note:** propagated error from misunderstanding about neural data rate

---

## Q 10-a. What variables in the raw data is `output` *Reward zone location* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:274):
> Inferred active reward zone per trial | `output[4]` | Map trial reward location to categorical `{A:0, B:1, C:2}` and repeat across trial bins.

**Code** (convert_data.py:25-31, 240-300):
```python
ZONE_BOUNDS = {0: (80.0, 130.0), 1: (200.0, 250.0), 2: (320.0, 370.0)}
ZONE_CENTERS = np.array([(lo + hi) / 2.0 for lo, hi in ZONE_BOUNDS.values()], dtype=np.float32)
...
def infer_trial_zones(...):
    ...
    for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
        mask = reward_zone_signal[start:stop_exclusive] > 0
        if np.any(mask):
            zone_pos = float(np.nanmedian(positions[start:stop_exclusive][mask]))
        elif trial_id in reward_pos_by_trial:
            zone_pos = reward_pos_by_trial[trial_id]
        ...
        observed[trial_id] = int(np.argmin(np.abs(ZONE_CENTERS - zone_pos)))
```

**What this does:** Derived from `reward_zone` signal, `position`, and `Reward` event timestamps. The active zone per trial is inferred by snapping the median in-zone position (or fallback reward-event position) to the closest of zones A/B/C.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-b. What processing is involved in computing `output` *Reward zone location*?

**Notes excerpt** (CONVERSION_NOTES.md:285):
> Infer from reward-zone-active positions / reward events and fill omission trials within stable blocks.

**Code** (convert_data.py:275-300, 499):
```python
filled = observed.copy()
unique_observed = np.unique(observed[observed >= 0])
...
if unique_observed.size == 1:
    filled[filled < 0] = int(unique_observed[0])
    return filled, observed_position
...
split = min(SWITCH_TRIAL_INDEX, n_trials)
pre_majority = trial_majority_zone(observed, 0, split, fallback=int(unique_observed[0]))
post_majority = trial_majority_zone(observed, split, n_trials, fallback=post_fallback)
filled[:split][filled[:split] < 0] = pre_majority
filled[split:][filled[split:] < 0] = post_majority

if unique_env.size > 1 and split < n_trials:
    filled[:split] = pre_majority
    filled[split:] = post_majority
...
zone_bin = np.full((t_bins,), zone_idx, dtype=np.int64)
```

**What this does:** Trials with no observed zone are filled with the per-half (pre-/post-switch at trial 30) majority zone. If environment changes mid-session, the entire pre/post halves are forced to their majority. Constant per trial, broadcast across bins.

**Rating:** ok

**Note:** _(no note)_

---

## Q 11-a. What variables in the raw data is `output` *Reward outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:275):
> Reward events assigned to trials | `output[5]` | Trial outcome categorical `{omitted:0, rewarded:1}`.

**Code** (convert_data.py:357, 363-367, 428-432):
```python
reward_times=beh["Reward/timestamps"][()].astype(np.float64, copy=False),
...
def reward_frames_for_session(arrays):
    ...
    idx = np.searchsorted(arrays.timestamps, arrays.reward_times, side="left")
    return np.clip(idx, 0, arrays.timestamps.shape[0] - 1).astype(np.int64, copy=False)
...
reward_frame_idx = reward_frames_for_session(arrays)
rewarded_trial_ids = set(int(t) for t in arrays.trial_number[reward_frame_idx] if t >= 0)
trial_rewarded = np.array(
    [1 if trial_id in rewarded_trial_ids else 0 for trial_id in range(len(trial_slices))],
    dtype=np.int64,
)
```

**What this does:** Reward event timestamps are mapped via `searchsorted` against position timestamps to nearest behavior frames; trial assignment uses NWB `trial number` value at that frame. A trial is rewarded if any reward event maps to its trial id.

**Rating:** match

**Note:** _(no note)_

---

## Q 11-b. What processing is involved in computing `output` *Reward outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:275):
> Rewarded if any `Reward` event timestamp falls within the trial.

**Code** (convert_data.py:500):
```python
reward_bin = np.full((t_bins,), int(trial_rewarded[trial_id]), dtype=np.int64)
```

**What this does:** Constant per trial (0 or 1), broadcast across bins. Note that trial assignment uses the NWB `trial number` value at the reward frame, which differs from the `trial_id` derived from `trial_start`/`teleport`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 12. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:142, 470):
> 10 sessions are off by exactly 1 sample (`behavior = neural - 1`). Handled 10 sessions with a 1-sample neural/behavior length mismatch by cropping to the common minimum length before trial parsing.

**Code** (convert_data.py:338-340, 234-237, 279-280, 314-315, 444-446):
```python
t_neural = neural.shape[0]
t_behavior = beh["position/data"].shape[0]
t_common = min(t_neural, t_behavior)
...
def trial_majority_zone(observed_zone, start, stop, fallback):
    subset = observed_zone[start:stop]
    subset = subset[subset >= 0]
    if subset.size == 0:
        return fallback
    return int(np.bincount(subset).argmax())
...
if unique_observed.size == 0:
    raise RuntimeError("Could not infer any reward-zone labels from the session.")
...
if len(slices) < 2:
    raise RuntimeError("Need at least two trials in a session.")
...
if lick_trial.size and np.mean(lick_trial > 2) > LICK_ARTIFACT_FRACTION:
    lick_artifact[trial_id] = True
```

**What this does:** Length mismatch between neural and behavior is silently handled by cropping to the minimum. Missing zone labels are filled by half-session majority. Lick-artifact trials skipped. Sessions with no zone labels or fewer than 2 trials raise. Negative `environment`/`trial number` sentinel values are filtered.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:359-361):
> Conversion core (observed sample sessions): `1.22-1.35 s/session`, `~3.5 min` for 152 sessions without processing plots. Sample conversion command including plot generation: `8.47 s / 2 sessions total`.

**Code** (convert_data.py:332-336, 614-625):
```python
neural = neural_group["data"][()].astype(np.float32, copy=False)
roi_ids = neural_group["rois"][()].astype(np.int64, copy=False)
iscell = seg["iscell"][()][roi_ids, 0] > 0.5
neural = neural[:, iscell]
...
for session_idx, path in enumerate(files):
    session_t0 = time.perf_counter()
    arrays = load_session_arrays(path)
```

**What this does:** Per-session timing is logged. The bulk of time is the NWB read (loading the deconvolved matrix into memory) and plotting when enabled. Per-session times reported `1.22-1.35 s` for the sample.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md:317-320):
> Used vectorized trial construction and simple factor-2 rebinning for 31 Hz sessions.

**Code** (convert_data.py:439, 469):
```python
for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
    env = arrays.environment[start:stop_exclusive]
    ...
for trial_id, (start, stop_exclusive) in enumerate(trial_slices):
    if lick_artifact[trial_id]:
        continue
    neural_trial = arrays.neural[start:stop_exclusive].T...
```

**What this does:** Two per-trial Python loops iterate over `trial_slices` (one for env/lick-artifact, one for output construction). The notes do not call out remaining vectorization targets explicitly.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md:121-145):
> `infer_sample_files` opens every NWB file to read environment/rate before sample selection.

**Code** (convert_data.py:121-128):
```python
def infer_sample_files(files):
    metadata = []
    for path in files:
        with h5py.File(path, "r") as f:
            env = f["processing/behavior/BehavioralTimeSeries/environment/data"][()]
            rate = float(f["processing/ophys/Deconvolved/plane0/starting_time"].attrs["rate"])
            env_valid = tuple(int(v) for v in np.unique(env) if v >= 0)
            metadata.append((path, rate, env_valid))
```

**What this does:** In sample mode, the code opens every NWB file once to gather rate/environment metadata before selecting two sessions; the chosen sessions are then re-opened for full loading. The conversion notes do not flag any other repeated processing.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none — no explicit discussion of computed-then-discarded variables.)

**Code** (convert_data.py:518-530):
```python
session_info = {
    ...
    "observed_zone_positions_cm": observed_zone_position.tolist(),
    ...
}
```

**What this does:** Some session-level metadata (e.g. `observed_zone_positions_cm`, `n_trials_lick_artifact_removed`, `conversion_seconds`) is computed and stored in the session_info dict but is not used by the decoder. No prominent throwaway computation noted.

**Rating:** ok

**Note:** _(no note)_

---

## Q 13-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:313-320
> ```
> Code inefficiencies identified:
> - Full-session NWB reads currently materialize the session response matrix in memory once per session.
> - Processing plots intentionally add overhead and should stay disabled for full conversion.
>
> Code speedups added:
> - Used direct `h5py` reads instead of heavier NWB object materialization.
> - Restricted neural loading to ROI indices actually referenced by the response matrix and then to curated `iscell` ROIs.
> - Used vectorized trial construction and simple factor-2 rebinning for 31 Hz sessions.
> ```
> CONVERSION_NOTES.md:356
> ```
> | ROI-region-aware cell filtering before downstream work | Avoids processing unused segmentation-table ROIs |
> ```

**Code** (convert_data.py:330-337):
```python
        rate_hz = float(neural_group["starting_time"].attrs["rate"])
        timestamps = beh["position/timestamps"][()].astype(np.float64, copy=False)

        neural = neural_group["data"][()].astype(np.float32, copy=False)
        roi_ids = neural_group["rois"][()].astype(np.int64, copy=False)
        iscell = seg["iscell"][()][roi_ids, 0] > 0.5
        neural = neural[:, iscell]
        roi_ids = roi_ids[iscell]
```

`copy=False` casting is applied consistently to behavior streams and per-trial arrays (convert_data.py:348-357, 473, 511):
```python
            position=beh["position/data"][()][:t_common].astype(np.float32, copy=False),
            speed=beh["speed/data"][()][:t_common].astype(np.float32, copy=False),
            ...
        neural_trial = arrays.neural[start:stop_exclusive].T.astype(np.float32, copy=False)
        ...
        neural_trials.append(neural_trial.astype(np.float32, copy=False))
```

**What this does:** Reads only the `Deconvolved/plane0` response matrix via `h5py` (Fluorescence and Neuropil are never loaded), materializes it in full with `[()]` and then boolean-masks curated ROI columns, so the uncurated matrix is briefly resident. Every cast uses `copy=False` to avoid gratuitous duplicates, dtypes are pinned to float32 for neural/inputs and int64 for outputs, and sessions are handled one at a time; the notes name the remaining full-session materialization as a known inefficiency. No memory-mapping, chunked reads, `del`, or `gc.collect()`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
