# mouseland — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/mouseland/codex/2026-03-23__15-40-42_trial1/verifier/snapshot/`

Outputs identified (K=4): visual_stimulus, licking, position_bin, running_speed_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use 89 unique recording bases as sessions: This matches the paper's '89 recordings in 19 mice'..." (CONVERSION_NOTES.md:217-218)

**Code** (convert_data.py:104-141, 469-480):
```python
def select_representative_sessions(root: Path) -> list[SessionSpec]:
    beh_dir = root / "data" / "beh"
    base_to_experiments = load_experiment_type_map(root)
    selected: dict[str, SessionSpec] = {}

    for beh_path in sorted(beh_dir.glob("Beh_*.npy")):
        exp_type = beh_path.stem.replace("Beh_", "")
        beh_dict = np.load(beh_path, allow_pickle=True).item()
        for key, record in beh_dict.items():
            base = "_".join(key.split("_")[:5])
            ...
    for session_idx, spec in enumerate(specs, start=1):
        spk = load_spike_matrix(root, spec.base)
        ...
        region_idx = load_region_index(root, spec.base, nneurons)
```

**What this does:** Iterates `data/beh/Beh_*.npy` to enumerate behavior dictionaries, deduplicates to unique recording bases `<mouse>_<date>_<blk>`, then for each session loads neural spikes from `data/spk/<base>_neural_data.npy` and retinotopy from `data/retinotopy/`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Session mouse name parsed from base id -> subjects, subject_idx; Unique mouse ids in deterministic sorted order; 19 subjects expected after deduplication." (CONVERSION_NOTES.md:214)

**Code** (convert_data.py:76-83, 460-462):
```python
def parse_base(base: str) -> tuple[str, datetime, str]:
    parts = base.split("_")
    if len(parts) != 5:
        raise ValueError(f"Unexpected recording base format: {base}")
    subject = parts[0]
    date = datetime.strptime("_".join(parts[1:4]), "%Y_%m_%d")
    blk = parts[4]
    return subject, date, blk
...
    subject_names = sorted({spec.subject for spec in specs})
    subject_to_idx = {name: idx for idx, name in enumerate(subject_names)}
```

**What this does:** Subject identity is parsed as the first underscore-separated token of each recording base. Unique subject names are sorted and assigned integer indices, attached per session via `subject_idx`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use 89 unique recording bases as sessions ... avoids leakage from duplicated experiment labels and `swap1`/`swap2` aliases that share the same raw trials." (CONVERSION_NOTES.md:217)

**Code** (convert_data.py:86-141):
```python
def session_key_score(key: str, record: dict) -> tuple[int, int, int, str]:
    stim_id = np.asarray(record.get("stim_id", []), dtype=float)
    non_nan_stim = int(np.isfinite(stim_id).sum()) if stim_id.size else 0
    unique_walls = int(len(np.unique(record.get("WallName", []))))
    swap_penalty = 1 if "swap" in key else 0
    return (swap_penalty, -non_nan_stim, -unique_walls, key)
...
    for beh_path in sorted(beh_dir.glob("Beh_*.npy")):
        ...
        for key, record in beh_dict.items():
            base = "_".join(key.split("_")[:5])
            if base not in selected:
                selected[base] = SessionSpec(base=base, key=key, record=record, ...)
            else:
                current = selected[base]
                if session_key_score(key, record) < session_key_score(current.key, current.record):
                    current.key = key
```

**What this does:** Each behavior key is reduced to a recording base `<mouse>_<date>_<blk>`. When multiple keys share a base, a scoring function picks the canonical record (penalizing `swap`, preferring more finite `stim_id` and more unique walls). Sessions are sorted by subject, date, block.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Align trials using frame-level `ft_trInd` rather than `StartFr`/`EndFr`: This matches the reference code and avoids boundary ambiguities." (CONVERSION_NOTES.md:220)

**Code** (convert_data.py:169-182):
```python
def build_trial_frame_indices(record: dict, nfr: int) -> list[np.ndarray]:
    ft_tr = np.asarray(record["ft_trInd"][:nfr], dtype=float)
    valid = np.isfinite(ft_tr)
    valid_idx = np.flatnonzero(valid)
    trial_ids = ft_tr[valid].astype(int)
    keep = np.asarray(record["ft_CorrSpc"][:nfr], dtype=bool)[valid]
    keep &= np.asarray(record["ft_move"][:nfr], dtype=float)[valid] > 0

    ntrials = int(record["ntrials"])
    frame_indices: list[np.ndarray] = []
    for trial in range(ntrials):
        trial_frames = valid_idx[keep & (trial_ids == trial)]
        frame_indices.append(trial_frames.astype(np.int32, copy=False))
    return frame_indices
```

**What this does:** Trial frame membership is derived from the frame-level `ft_trInd` array (truncated to neural frame count `nfr`). Per trial, only frames inside the textured corridor (`ft_CorrSpc`) and during running (`ft_move > 0`) are kept.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "drops decoder-pathological trials with retained duration > 60 s or retained inter-frame gaps > 10 s" (CONVERSION_NOTES.md:256); "trials with fewer than 5 retained neural timepoints will be excluded; sessions with fewer than 2 remaining trials will be excluded." (CONVERSION_NOTES.md:222)

**Code** (convert_data.py:25-27, 351-372, 519-522):
```python
MIN_TRIAL_TIMEPOINTS = 5
MAX_RETAINED_TRIAL_DURATION_S = 60.0
MAX_RETAINED_INTERFRAME_GAP_S = 10.0
...
def trial_passes_quality_filters(record, trial_idx, frame_idx, nfr):
    frame_idx = frame_idx[frame_idx < nfr]
    if frame_idx.size < MIN_TRIAL_TIMEPOINTS:
        return False, "too_few_timepoints"
    frame_times = np.asarray(record["ft"][:nfr], dtype=float)[frame_idx]
    retained_duration_s = float((frame_times[-1] - float(record["Trial_start_time"][trial_idx])) * SEC_PER_DAY)
    if retained_duration_s > MAX_RETAINED_TRIAL_DURATION_S:
        return False, "retained_duration_gt_60s"
    if frame_idx.size > 1:
        max_gap_s = float(np.max(np.diff(frame_times)) * SEC_PER_DAY)
        if max_gap_s > MAX_RETAINED_INTERFRAME_GAP_S:
            return False, "interframe_gap_gt_10s"
    return True, None
...
        if len(session_neural) < 2:
            removed_sessions.append((spec.base, len(session_neural), "fewer_than_two_valid_trials"))
```

**What this does:** Trials are dropped if they have fewer than 5 retained frames, retained duration > 60 s, or any inter-frame gap > 10 s. Sessions with fewer than 2 surviving trials are dropped.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`spk/*.npy -> spks` -> `neural` ... Concatenate plane arrays along neurons; keep deconvolved values as float32" (CONVERSION_NOTES.md:203); "stored `spks` traces loaded directly from the raw files; no dF/F recomputation." (README.md:19)

**Code** (convert_data.py:217-221, 224-238):
```python
def load_spike_matrix(root: Path, base: str) -> np.ndarray:
    path = root / "data" / "spk" / f"{base}_neural_data.npy"
    spk_item = np.load(path, allow_pickle=True).item()
    spk = np.concatenate([plane for plane in spk_item["spks"]], axis=0)
    return spk.astype(np.float32, copy=False)

def load_region_index(root: Path, base: str, nneurons: int) -> np.ndarray:
    ...
    ret = np.load(ret_path, allow_pickle=True)
    iarea = np.asarray(ret["iarea"], dtype=float)
    ...
```

**What this does:** Neural data is the concatenation along neuron axis of the per-plane `spks` arrays from `data/spk/<base>_neural_data.npy`. Retinotopy `iarea` is loaded for region labels and neuron selection.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Keep the stored `spks` arrays directly, but export only a selective decoder subset" (CONVERSION_NOTES.md:219); "paper-style top 5% positive and top 5% negative stimulus-selective neurons per visual area." (README.md:21)

**Code** (convert_data.py:265-316, 495):
```python
def select_decoder_neurons(spk, record, region_idx):
    ...
    dp = dprime(spk[:, stim1_mask], spk[:, stim2_mask])
    corr_neu = (
        (np.mean(spk[:, stim1_mask], axis=1) > np.mean(spk[:, gray_mask], axis=1))
        | (np.mean(spk[:, stim2_mask], axis=1) > np.mean(spk[:, gray_mask], axis=1))
    )
    selected = np.zeros(spk.shape[0], dtype=bool)
    for area in range(4):
        candidates = corr_neu & (region_idx == area) & np.isfinite(dp)
        ...
        hi, lo = np.nanpercentile(dp[candidates], [95, 5])
        selected |= candidates & ((dp >= hi) | (dp <= lo))
    ...
    neural_trial = spk[:, frame_idx].astype(np.float32, copy=False)
```

**What this does:** No dF/F or rescaling: deconvolved `spks` values are kept as float32. Per session, neurons are subselected to corridor-responsive top/bottom 5% d' (per visual area V1/mHV/lHV/aHV) using a chosen reference stimulus pair.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "There is no electrophysiology-style unit quality curation in the reference code." (CONVERSION_NOTES.md:52); region selection limits to V1/mHV/lHV/aHV (CONVERSION_NOTES.md:227).

**Code** (convert_data.py:224-238, 265-316):
```python
    region_idx = np.full(nneurons, 4, dtype=np.int16)
    region_idx[iarea == 8] = 0
    region_idx[np.isin(iarea, [0, 1, 2, 9])] = 1
    region_idx[np.isin(iarea, [5, 6])] = 2
    region_idx[np.isin(iarea, [3, 4])] = 3
...
    for area in range(4):
        candidates = corr_neu & (region_idx == area) & np.isfinite(dp)
```

**What this does:** No spike-quality filter is applied. Neurons are restricted to those mapped to one of four visual areas (region_idx < 4) and that pass the corridor-responsiveness + d' selectivity criterion in `select_decoder_neurons`.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: corridor entry / trial start" (convert_data.py:568); "Align trials using frame-level `ft_trInd` rather than `StartFr`/`EndFr`" (CONVERSION_NOTES.md:220)

**Code** (convert_data.py:169-182, 344-348, 567-571):
```python
def build_trial_frame_indices(record: dict, nfr: int) -> list[np.ndarray]:
    ft_tr = np.asarray(record["ft_trInd"][:nfr], dtype=float)
    ...
    for trial in range(ntrials):
        trial_frames = valid_idx[keep & (trial_ids == trial)]
...
def session_trial_info(record, trial, frame_idx):
    frame_times = np.asarray(record["ft"], dtype=float)[frame_idx]
    time_to_cue = (float(record["SoundTime"][trial]) - frame_times) * SEC_PER_DAY
    time_since_start = (frame_times - float(record["Trial_start_time"][trial])) * SEC_PER_DAY
```

**What this does:** Trials are segmented by `ft_trInd`. The `time_since_trial_start_s` input encodes alignment to the trial-start event (`Trial_start_time`); `off_start=0.0, off_end=None` is recorded in metadata.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use raw frame timestamps instead of resampling to a new clock: Median imaging frame spacing is very consistent across sessions (~314.7 ms), so keeping native frame bins is more faithful." (CONVERSION_NOTES.md:225)

**Code** (convert_data.py:495, 567-571):
```python
    neural_trial = spk[:, frame_idx].astype(np.float32, copy=False)
...
        "time_bin_size": float(np.median(frame_dt_medians)),
        "temporal_alignment_event": "corridor entry / trial start",
        "off_start": 0.0,
        "off_end": None,
        "frame_bin_source": "native imaging frame timestamps; no temporal resampling",
```

**What this does:** No resampling or rebinning is performed. Each trial's neural matrix is the raw deconvolved spk columns at retained frame indices; the metadata records the median native frame interval as the time bin size.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| `beh['SoundTime']` and retained frame times from `beh['ft']` | `input[0]` = `time_to_sound_cue_s` | For each retained frame, compute `SoundTime - frame_time` in seconds; positive before cue, negative after cue |" (CONVERSION_NOTES.md:205); "Trial-level arrays: `WallName`, `isRew`, `SoundPos`, `SoundFr`, `RewPos`, `RewTime`, `SoundTime`, ..." (CONVERSION_NOTES.md:89)

**Code** (convert_data.py:28-33, 344-348):
```python
INPUT_NAMES = [
    "time_to_sound_cue_s",
    "training_day",
    "time_since_trial_start_s",
    "reward_available",
]
...
def session_trial_info(record: dict, trial: int, frame_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    frame_times = np.asarray(record["ft"], dtype=float)[frame_idx]
    time_to_cue = (float(record["SoundTime"][trial]) - frame_times) * SEC_PER_DAY
    time_since_start = (frame_times - float(record["Trial_start_time"][trial])) * SEC_PER_DAY
    return time_to_cue.astype(np.float32), time_since_start.astype(np.float32)
```

**What this does:** The trial produces this input as `time_to_sound_cue_s` (`input[0]`). It is derived from the trial-level `SoundTime` array in the behavior record and the per-frame imaging timestamps `ft`, indexed at the retained frame indices for that trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "For each retained frame, compute `SoundTime - frame_time` in seconds; positive before cue, negative after cue ... Time-varying continuous input." (CONVERSION_NOTES.md:205); "Input timing check: For sampled trials, verify `time_to_sound_cue_s` equals raw `SoundTime - ft[mask]`" (CONVERSION_NOTES.md:233); "`time_to_sound_cue_s` range | [-49.1, 45.7]" (CONVERSION_NOTES.md:357)

**Code** (convert_data.py:23, 344-348, 496-501):
```python
SEC_PER_DAY = 24.0 * 3600.0
...
    frame_times = np.asarray(record["ft"], dtype=float)[frame_idx]
    time_to_cue = (float(record["SoundTime"][trial]) - frame_times) * SEC_PER_DAY
...
            time_to_cue, time_since_start = session_trial_info(spec.record, trial_idx, frame_idx)
            input_trial = np.vstack(
                [time_to_cue, training_day, time_since_start, reward_available]
            ).astype(np.float32, copy=False)
```

**What this does:** Subtracts each retained frame's timestamp from the trial's `SoundTime`, multiplies by `SEC_PER_DAY` (86400) to convert the day-unit raw timestamps into seconds, and casts to float32. The result is signed (positive before the cue, negative after) and is stacked as row 0 of the per-trial `(4, T)` input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "frame_bin_source: native imaging frame timestamps; no temporal resampling" (convert_data.py:571); "Use raw frame timestamps to build a trial-start-aligned time grid later; this preserves the reference streams while satisfying the decoder format requirement." (CONVERSION_NOTES.md:192)

**Code** (convert_data.py:487-501):
```python
        for trial_idx, frame_idx in enumerate(spec.trial_frame_indices):
            frame_idx = frame_idx[frame_idx < nfr]
            keep_trial, remove_reason = trial_passes_quality_filters(spec.record, trial_idx, frame_idx, nfr)
            if not keep_trial:
                ...
                continue

            neural_trial = spk[:, frame_idx].astype(np.float32, copy=False)
            time_to_cue, time_since_start = session_trial_info(spec.record, trial_idx, frame_idx)
            ...
            input_trial = np.vstack(
                [time_to_cue, training_day, time_since_start, reward_available]
            ).astype(np.float32, copy=False)
```

**What this does:** The same `frame_idx` array selects the spike columns and the `ft` timestamps, so each input column corresponds one-to-one with a neural column at the native imaging frame. No interpolation or resampling is applied on either side.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Session date parsed from recording base, relative to first recording date for that mouse | `input[1]` = `training_day` | ... | No direct paper function; required by decoder task | Decoder-task-required addition; derived from raw session dates to remain objective and reproducible. |" (CONVERSION_NOTES.md:206)

**Code** (convert_data.py:76-83, 136-141):
```python
def parse_base(base: str) -> tuple[str, datetime, str]:
    parts = base.split("_")
    subject = parts[0]
    date = datetime.strptime("_".join(parts[1:4]), "%Y_%m_%d")
    blk = parts[4]
    return subject, date, blk
...
    specs = sorted(selected.values(), key=lambda s: (s.subject, s.date, int(s.blk)))
    first_date_by_subject: dict[str, datetime] = {}
    for spec in specs:
        first_date_by_subject.setdefault(spec.subject, spec.date)
        spec.training_day = float((spec.date - first_date_by_subject[spec.subject]).days)
```

**What this does:** The trial produces this input as `training_day` (`input[1]`). It is derived from the session/recording identifier string (e.g. `DR10_2022_07_12_1`), from which the mouse name and calendar date are parsed; no dedicated training-day field is read from the raw behavior files.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Continuous per-trial scalar = elapsed days since the mouse's first retained imaging session; repeated across timepoints in the saved 2D input array" (CONVERSION_NOTES.md:206); "Represent `training_day` as elapsed days since the mouse's first retained imaging session" (CONVERSION_NOTES.md:228); "training_day_definition: elapsed days since the subject's first retained imaging session" (convert_data.py:576)

**Code** (convert_data.py:136-141, 498-501):
```python
    specs = sorted(selected.values(), key=lambda s: (s.subject, s.date, int(s.blk)))
    first_date_by_subject: dict[str, datetime] = {}
    for spec in specs:
        first_date_by_subject.setdefault(spec.subject, spec.date)
        spec.training_day = float((spec.date - first_date_by_subject[spec.subject]).days)
...
            training_day = np.full(frame_idx.size, spec.training_day, dtype=np.float32)
            input_trial = np.vstack(
                [time_to_cue, training_day, time_since_start, reward_available]
            ).astype(np.float32, copy=False)
```

**What this does:** Sessions are sorted per subject; the earliest date for each subject becomes day 0 and every other session gets the integer day difference from it as a float. That single session-level scalar is broadcast with `np.full` across all retained timepoints of every trial in the session, giving row 1 of the input array. Reported range is `[0.0, 92.0]` (CONVERSION_NOTES.md:358).

**Rating:** concerning

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Retained frame times from `beh['ft']` and `beh['Trial_start_time']` | `input[2]` = `time_since_trial_start_s` | `frame_time - Trial_start_time` in seconds for each retained frame | Raw timestamps; consistent with paper frame-time analyses | Time-varying continuous input. |" (CONVERSION_NOTES.md:207)

**Code** (convert_data.py:28-33, 344-348):
```python
INPUT_NAMES = [
    "time_to_sound_cue_s",
    "training_day",
    "time_since_trial_start_s",
    "reward_available",
]
...
def session_trial_info(record: dict, trial: int, frame_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    frame_times = np.asarray(record["ft"], dtype=float)[frame_idx]
    ...
    time_since_start = (frame_times - float(record["Trial_start_time"][trial])) * SEC_PER_DAY
```

**What this does:** The trial produces this input as `time_since_trial_start_s` (`input[2]`). It is derived from the per-frame imaging timestamps `ft` and the trial-level `Trial_start_time` array in the behavior record.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "verify ... `time_since_trial_start_s` equals raw `ft[mask] - Trial_start_time`" (CONVERSION_NOTES.md:233); "`time_since_trial_start_s` range | Should be nonnegative | Derived from raw timestamps | ... | [0.0, 54.3]" (CONVERSION_NOTES.md:359); "Extreme ... ranges: Caused by raw trials with sparse late running segments long after nominal trial start. Resolved by excluding those trials" (CONVERSION_NOTES.md:392)

**Code** (convert_data.py:344-348, 362-370):
```python
    frame_times = np.asarray(record["ft"], dtype=float)[frame_idx]
    time_since_start = (frame_times - float(record["Trial_start_time"][trial])) * SEC_PER_DAY
...
    retained_duration_s = float((frame_times[-1] - float(record["Trial_start_time"][trial_idx])) * SEC_PER_DAY)
    if retained_duration_s > MAX_RETAINED_TRIAL_DURATION_S:
        return False, "retained_duration_gt_60s"
    if frame_idx.size > 1:
        max_gap_s = float(np.max(np.diff(frame_times)) * SEC_PER_DAY)
        if max_gap_s > MAX_RETAINED_INTERFRAME_GAP_S:
            return False, "interframe_gap_gt_10s"
```

**What this does:** Subtracts the trial's `Trial_start_time` from each retained frame timestamp and scales by 86400 to get seconds, cast to float32, stored as row 2 of the input array. The same quantity also drives two trial-rejection filters: trials whose retained duration exceeds 60 s or whose inter-frame gap exceeds 10 s are dropped.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: corridor entry / trial start", "off_start: 0.0", "off_end: None", "frame_bin_source: native imaging frame timestamps; no temporal resampling", "frame_mask: ft_CorrSpc & (ft_move > 0)" (convert_data.py:568-572)

**Code** (convert_data.py:169-182, 495-501):
```python
def build_trial_frame_indices(record: dict, nfr: int) -> list[np.ndarray]:
    ft_tr = np.asarray(record["ft_trInd"][:nfr], dtype=float)
    ...
    for trial in range(ntrials):
        trial_frames = valid_idx[keep & (trial_ids == trial)]
...
            neural_trial = spk[:, frame_idx].astype(np.float32, copy=False)
            time_to_cue, time_since_start = session_trial_info(spec.record, trial_idx, frame_idx)
            input_trial = np.vstack(
                [time_to_cue, training_day, time_since_start, reward_available]
            ).astype(np.float32, copy=False)
```

**What this does:** Both the neural matrix and this input are indexed by the identical per-trial `frame_idx` (frames assigned to the trial by `ft_trInd` and passing the corridor/running mask), so column t of the input matches column t of `neural_trial`. Because retained frames start at corridor entry rather than at the raw `Trial_start_time`, the first value per trial is not forced to zero.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| `beh['isRew']` | `input[3]` = `reward_available` | Trial-level binary repeated across timepoints; 1 only for rewarded-corridor task trials, 0 otherwise | `get_cat_id`, behavior code, paper methods | In unsupervised / naive / grating sessions this is expected to be all 0. |" (CONVERSION_NOTES.md:208)

**Code** (convert_data.py:28-33, 497):
```python
INPUT_NAMES = [
    "time_to_sound_cue_s",
    "training_day",
    "time_since_trial_start_s",
    "reward_available",
]
...
            reward_available = np.full(frame_idx.size, float(bool(spec.record["isRew"][trial_idx])), dtype=np.float32)
```

**What this does:** The trial produces this input as `reward_available` (`input[3]`). It is taken from the trial-level `isRew` array in the behavior record, indexed by the raw trial index.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Store all four decoder inputs in a 2D time-varying array: Even the per-trial variables (`training_day`, `reward_available`) will be repeated across timepoints so every trial has a uniform `(4, T)` input shape." (CONVERSION_NOTES.md:223); "`reward_available` range | Task rewarded corridor only; unsupervised none | Uses `isRew` / corridor identity | Mixed 0 and 1 across sessions | [0.0, 1.0] | Yes" (CONVERSION_NOTES.md:360)

**Code** (convert_data.py:497-501):
```python
            reward_available = np.full(frame_idx.size, float(bool(spec.record["isRew"][trial_idx])), dtype=np.float32)
            training_day = np.full(frame_idx.size, spec.training_day, dtype=np.float32)
            input_trial = np.vstack(
                [time_to_cue, training_day, time_since_start, reward_available]
            ).astype(np.float32, copy=False)
```

**What this does:** The per-trial `isRew` value is coerced to a Python bool then to float (0.0 or 1.0) and broadcast with `np.full` across all retained timepoints of the trial, forming row 3 of the `(4, T)` input array. No thresholding, timing, or reward-window logic is applied; it is a constant binary flag for the whole trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`beh['WallName']` -> `output[0]` = `visual_stimulus`; Global categorical mapping over all unique stimulus names" (CONVERSION_NOTES.md:209)

**Code** (convert_data.py:212-214, 507-511):
```python
def collect_visual_categories(specs: list[SessionSpec]) -> list[str]:
    categories = sorted({str(wall) for spec in specs for wall in spec.record["UniqWalls"]})
    return categories
...
            stim_idx = np.full(
                frame_idx.size,
                visual_to_idx[str(spec.record["WallName"][trial_idx])],
                dtype=np.int16,
            )
```

**What this does:** Derived from per-trial `WallName` strings, mapped via a global category list assembled from `UniqWalls` across all retained sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Global categorical mapping over all unique stimulus names across retained sessions; repeated across timepoints" (CONVERSION_NOTES.md:209)

**Code** (convert_data.py:212-214, 454, 507-512):
```python
    visual_to_idx = {name: idx for idx, name in enumerate(visual_categories)}
...
            stim_idx = np.full(frame_idx.size,
                visual_to_idx[str(spec.record["WallName"][trial_idx])],
                dtype=np.int16)
            output_trial = np.vstack([stim_idx, licking, position_bin, speed_bin])
```

**What this does:** Builds a sorted global category vocabulary, looks up the trial's wall name, broadcasts that scalar index to the trial's retained frame count, and stacks it as row 0 of `output`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`beh['LickFr']`, `beh['LickTrind']` -> `output[1]` = `licking`; Build a binary imaging-frame vector (1 if any lick occurs on that retained frame, else 0)" (CONVERSION_NOTES.md:210)

**Code** (convert_data.py:319-331, 503-504):
```python
def build_lick_frame_lookup(record: dict, nfr: int) -> dict[int, np.ndarray]:
    lick_frames = np.asarray(record["LickFr"], dtype=float)
    lick_trial = np.asarray(record["LickTrind"], dtype=float)
    valid = np.isfinite(lick_frames) & np.isfinite(lick_trial)
    lick_frames = lick_frames[valid].astype(int)
    lick_trial = lick_trial[valid].astype(int)
    ...
    for trial in np.unique(lick_trial):
        lookup[int(trial)] = np.unique(lick_frames[lick_trial == trial]).astype(np.int32)
...
            lick_frames = lick_lookup.get(trial_idx, np.empty(0, dtype=np.int32))
            licking = np.isin(frame_idx, lick_frames, assume_unique=False).astype(np.int16)
```

**What this does:** Derived from raw `LickFr` (lick imaging-frame indices) and `LickTrind` (per-lick trial id).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *licking*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Build a binary imaging-frame vector (1 if any lick occurs on that retained frame, else 0)" (CONVERSION_NOTES.md:210)

**Code** (convert_data.py:319-331, 503-504):
```python
    lookup: dict[int, np.ndarray] = {}
    for trial in np.unique(lick_trial):
        lookup[int(trial)] = np.unique(lick_frames[lick_trial == trial]).astype(np.int32)
...
            lick_frames = lick_lookup.get(trial_idx, np.empty(0, dtype=np.int32))
            licking = np.isin(frame_idx, lick_frames, assume_unique=False).astype(np.int16)
```

**What this does:** Per session, builds a trial -> unique lick frame index lookup. Per trial, `licking[i]=1` iff retained frame i is in the trial's lick frame set (binary, no smoothing or counts).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying binary output aligned to neural frames." (CONVERSION_NOTES.md:210)

**Code** (convert_data.py:503-504):
```python
            lick_frames = lick_lookup.get(trial_idx, np.empty(0, dtype=np.int32))
            licking = np.isin(frame_idx, lick_frames, assume_unique=False).astype(np.int16)
```

**What this does:** `licking` is computed via `np.isin` against the trial's retained `frame_idx`, so it has exactly the same length and ordering as the neural columns of that trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`beh['ft_Pos']` on retained frames -> `output[2]` = `position_bin`" (CONVERSION_NOTES.md:211)

**Code** (convert_data.py:339-341, 505):
```python
def digitize_position(pos_decimeters: np.ndarray) -> np.ndarray:
    pos = np.clip(pos_decimeters, 0.0, 39.999)
    return np.clip((pos // 10.0).astype(np.int16), 0, 3)
...
            position_bin = digitize_position(np.asarray(spec.record["ft_Pos"], dtype=np.float32)[frame_idx])
```

**What this does:** Derived from frame-level `ft_Pos` (in decimeters) at retained frame indices.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Convert decimeter positions in the 0-40 textured corridor to four 1 m bins via edges `[0,10,20,30,40]`" (CONVERSION_NOTES.md:211)

**Code** (convert_data.py:339-341):
```python
def digitize_position(pos_decimeters: np.ndarray) -> np.ndarray:
    pos = np.clip(pos_decimeters, 0.0, 39.999)
    return np.clip((pos // 10.0).astype(np.int16), 0, 3)
```

**What this does:** Clips position to [0, 39.999) decimeters and integer-divides by 10 to assign one of 4 bins (0-1m, 1-2m, 2-3m, 3-4m).

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying categorical output with values `0-1m`, `1-2m`, `2-3m`, `3-4m`." (CONVERSION_NOTES.md:211)

**Code** (convert_data.py:505, 512):
```python
            position_bin = digitize_position(np.asarray(spec.record["ft_Pos"], dtype=np.float32)[frame_idx])
            ...
            output_trial = np.vstack([stim_idx, licking, position_bin, speed_bin]).astype(np.int16, copy=False)
```

**What this does:** `ft_Pos` is sampled at the same retained `frame_idx` used for the neural matrix, giving one position bin per neural frame.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`beh['ft_RunSpeed']` on retained frames -> `output[3]` = `running_speed_bin`; Discretize into global quartiles" (CONVERSION_NOTES.md:212)

**Code** (convert_data.py:200-208, 506):
```python
        run_speed = np.asarray(record["ft_RunSpeed"][:spec.estimated_nfr], dtype=np.float32)
        for trial_idx, (keep_trial, frame_idx) in enumerate(zip(spec.kept_trial_mask, spec.trial_frame_indices)):
            if keep_trial and trial_passes_quality_filters(...)[0]:
                all_speeds.append(run_speed[frame_idx])
    ...
    speed_edges = np.quantile(speed_values, [0.25, 0.5, 0.75]).astype(np.float32)
    ...
            speed_bin = digitize_speed(np.asarray(spec.record["ft_RunSpeed"], dtype=np.float32)[frame_idx], speed_edges)
```

**What this does:** Derived from frame-level `ft_RunSpeed` at retained frames; quartile edges are computed across the full retained dataset.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use global quartiles for running-speed bins: The decoder task specifies 25% bins, so edges must be computed from the full retained dataset, not per session." (CONVERSION_NOTES.md:229)

**Code** (convert_data.py:207-208, 334-336):
```python
    speed_values = np.concatenate(all_speeds).astype(np.float32, copy=False)
    speed_edges = np.quantile(speed_values, [0.25, 0.5, 0.75]).astype(np.float32)
...
def digitize_speed(speed: np.ndarray, edges: np.ndarray) -> np.ndarray:
    bins = np.searchsorted(edges, speed, side="right")
    return np.clip(bins, 0, 3).astype(np.int16)
```

**What this does:** Pre-pass concatenates all retained-frame speeds across kept trials/sessions, computes the 25/50/75 quantile edges, then `np.searchsorted` digitizes each retained frame's speed into 4 quartile bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. How is `output` *running_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying categorical output" (CONVERSION_NOTES.md:212)

**Code** (convert_data.py:506, 512):
```python
            speed_bin = digitize_speed(np.asarray(spec.record["ft_RunSpeed"], dtype=np.float32)[frame_idx], speed_edges)
            ...
            output_trial = np.vstack([stim_idx, licking, position_bin, speed_bin]).astype(np.int16, copy=False)
```

**What this does:** `ft_RunSpeed` is sampled at the same retained `frame_idx` used for neural columns, producing one speed bin per neural frame.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use the reference-code convention: truncate behavior frame arrays to neural frame count." (CONVERSION_NOTES.md:190); "Filter bad/unusable trials only when required by decoder format" (CONVERSION_NOTES.md:222)

**Code** (convert_data.py:164-166, 169-175, 319-327, 487-488):
```python
def estimate_behavior_frame_count(record: dict) -> int:
    frame_keys = ["ft", "ft_trInd", "ft_move", "ft_CorrSpc", "ft_Pos", "ft_RunSpeed"]
    return min(int(np.asarray(record[key]).shape[0]) for key in frame_keys)
...
    ft_tr = np.asarray(record["ft_trInd"][:nfr], dtype=float)
    valid = np.isfinite(ft_tr)
    valid_idx = np.flatnonzero(valid)
...
    valid = np.isfinite(lick_frames) & np.isfinite(lick_trial)
    ...
    valid = (lick_frames >= 0) & (lick_frames < nfr)
...
        for trial_idx, frame_idx in enumerate(spec.trial_frame_indices):
            frame_idx = frame_idx[frame_idx < nfr]
```

**What this does:** Behavior arrays are truncated to the minimum common frame count and clipped to neural `nfr`. NaNs in `ft_trInd`, `LickFr`, `LickTrind` are filtered out. Out-of-range lick frames are dropped. Sessions/trials below thresholds are removed (see Q 1-e), and `removed_sessions`/`removed_trials` are saved in metadata.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "The current implementation still has to load each neural recording file in full before selecting the compact neuron subset, so full conversion will still be I/O-heavy." (CONVERSION_NOTES.md:269); "Sample conversion: ~10.4 s / session" (CONVERSION_NOTES.md:320)

**Code** (convert_data.py:217-221, 473, 656):
```python
def load_spike_matrix(root: Path, base: str) -> np.ndarray:
    path = root / "data" / "spk" / f"{base}_neural_data.npy"
    spk_item = np.load(path, allow_pickle=True).item()
    spk = np.concatenate([plane for plane in spk_item["spks"]], axis=0)
    return spk.astype(np.float32, copy=False)
...
        spk = load_spike_matrix(root, spec.base)
...
    write_pickle(out_path, data)
```

**What this does:** Loading and concatenating each session's full `spks` planes is the dominant per-session cost (I/O bound), followed by per-session selectivity computation and final pickling of ~9.7 GiB output.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:178-182, 201-203, 487-517):
```python
    for trial in range(ntrials):
        trial_frames = valid_idx[keep & (trial_ids == trial)]
        frame_indices.append(trial_frames.astype(np.int32, copy=False))
...
        for trial_idx, (keep_trial, frame_idx) in enumerate(zip(spec.kept_trial_mask, spec.trial_frame_indices)):
            if keep_trial and trial_passes_quality_filters(record, trial_idx, frame_idx, spec.estimated_nfr)[0]:
                all_speeds.append(run_speed[frame_idx])
...
        for trial_idx, frame_idx in enumerate(spec.trial_frame_indices):
            ...
            neural_trial = spk[:, frame_idx].astype(np.float32, copy=False)
            time_to_cue, time_since_start = session_trial_info(spec.record, trial_idx, frame_idx)
            ...
```

**What this does:** Per-trial loops in `build_trial_frame_indices`, `prepare_session_specs`, and the main per-trial assembly loop iterate Python-side; trial assignment in particular re-scans `keep & (trial_ids == trial)` for each trial id.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Session preparation currently uses behavior-derived frame counts before the exact neural frame count is known; the second pass clips frame indices to the true neural frame count." (CONVERSION_NOTES.md:270-271)

**Code** (convert_data.py:185-203, 487-489):
```python
def prepare_session_specs(specs: list[SessionSpec]) -> tuple[np.ndarray, np.ndarray]:
    ...
    for spec in specs:
        record = spec.record
        spec.estimated_nfr = estimate_behavior_frame_count(record)
        spec.trial_frame_indices = build_trial_frame_indices(record, spec.estimated_nfr)
        ...
        for trial_idx, (keep_trial, frame_idx) in enumerate(zip(spec.kept_trial_mask, spec.trial_frame_indices)):
            if keep_trial and trial_passes_quality_filters(record, trial_idx, frame_idx, spec.estimated_nfr)[0]:
...
        for trial_idx, frame_idx in enumerate(spec.trial_frame_indices):
            frame_idx = frame_idx[frame_idx < nfr]
            keep_trial, remove_reason = trial_passes_quality_filters(spec.record, trial_idx, frame_idx, nfr)
```

**What this does:** Trial frame indices and quality filtering are computed once in `prepare_session_specs` (against estimated nfr) and again in `process_sessions` (against true neural nfr). Behavior arrays like `ft_RunSpeed` and `ft_Pos` are also re-read per trial inside the main loop.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "The current implementation still has to load each neural recording file in full before selecting the compact neuron subset" (CONVERSION_NOTES.md:269)

**Code** (convert_data.py:473-478):
```python
        spk = load_spike_matrix(root, spec.base)
        nneurons, nfr = spk.shape
        region_idx = load_region_index(root, spec.base, nneurons)
        selected_neurons = select_decoder_neurons(spk, spec.record, region_idx)
        spk = spk[selected_neurons]
        region_idx = region_idx[selected_neurons]
```

**What this does:** The entire `spks` matrix (e.g. tens of thousands of neurons x frames) is loaded and concatenated even though only ~3,400 neurons per session are exported. Speed quartile pre-pass also iterates trials before the final filter is finalized.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural recordings are loaded one session at a time in the main conversion pass." (CONVERSION_NOTES.md:275)

**Code** (convert_data.py:217-221, 473-478, 521, 551):
```python
    return spk.astype(np.float32, copy=False)
...
        spk = load_spike_matrix(root, spec.base)
        ...
        spk = spk[selected_neurons]
        ...
        if len(session_neural) < 2:
            ...
            del spk
            continue
        ...
        del spk
```

**What this does:** Spikes are kept as float32; the large `spk` matrix is downselected to chosen neurons immediately and explicitly `del`'d at end of each session iteration. Outputs use int16 dtype. Sessions are processed sequentially rather than all in memory at once.

**Rating:** match

**Note:** _(no note)_---

---
