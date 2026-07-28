# mouseland — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/mouseland/codex/2026-03-23__15-40-42_trial3/verifier/snapshot/`

Outputs identified (K=4): visual_stimulus_category, licking, position_bin, running_speed_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "data/beh/Imaging_Exp_info.npy: master session index for imaging experiments; 23 experiment groups referencing 142 experiment entries but only 89 unique imaging recordings." (CONVERSION_NOTES.md:67-69)
>
> "Implemented `convert_data.py` with CLI ... The script deduplicates `Imaging_Exp_info.npy` to 89 unique recordings, validates duplicate behavior references, computes global speed quartiles, and exports frame-aligned trial arrays." (CONVERSION_NOTES.md:200-202)

**Code** (convert_data.py:119-157, 474-481):
```python
def collect_sessions(sample: bool) -> list[SessionRef]:
    exp_info = load_exp_info()
    per_rec: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for exp_type, dbs in exp_info.items():
        for db in dbs:
            rec_id = f"{db['mname']}_{db['datexp']}_{db['blk']}"
            per_rec[rec_id].append((exp_type, db))
    ...
    sessions.sort(key=lambda s: (s.subject, parse_date(s.date_str), int(s.blk)))
    ...
# main loop
for sess_idx, sess in enumerate(sessions):
    beh = load_beh(sess.canonical_exp_type)[sess.canonical_beh_key]
    spk_obj = np.load(ROOT / "data" / "spk" / f"{sess.rec_id}_neural_data.npy", allow_pickle=True).item()
    spk_chunks = list(spk_obj["spks"])
    ret = np.load(ROOT / "data" / "retinotopy" / f"{sess.subject}_{sess.date_str}_trans.npz", allow_pickle=True)
```

**What this does:** Reads `Imaging_Exp_info.npy` to enumerate all (mouse, date, blk) recordings, deduplicates to unique recording IDs, then iterates sessions one by one, loading per-session behavior dict, neural `spks` chunks, and retinotopy file.

**Rating:** match

**Note:** _(no note)_---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Subjects | 19 imaging mice" (CONVERSION_NOTES.md:84)

**Code** (convert_data.py:386-394, 431):
```python
def build_global_metadata(sessions):
    subjects = []
    subject_to_idx = {}
    for sess in sessions:
        if sess.subject not in subject_to_idx:
            subject_to_idx[sess.subject] = len(subjects)
            subjects.append(sess.subject)
    ...
    "subject_idx": np.array([subject_to_idx[s.subject] for s in sessions], dtype=np.int64),
```

**What this does:** Each session's subject is taken from the `mname` field; unique mice define the subjects list and each session gets a `subject_idx` mapping it to one mouse.

**Rating:** match

**Note:** _(no note)_---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Session identity = unique recording ID: Use `<mouse>_<date>_<blk>` as the session key because this resolves the 142 experiment references down to the paper-consistent 89 unique recordings." (CONVERSION_NOTES.md:174)

**Code** (convert_data.py:119-141):
```python
def collect_sessions(sample: bool) -> list[SessionRef]:
    exp_info = load_exp_info()
    per_rec: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for exp_type, dbs in exp_info.items():
        for db in dbs:
            rec_id = f"{db['mname']}_{db['datexp']}_{db['blk']}"
            per_rec[rec_id].append((exp_type, db))

    sessions = []
    for rec_id, refs in per_rec.items():
        first_db = refs[0][1]
        exp_type, beh_key = choose_canonical_behavior(rec_id, refs)
        sessions.append(SessionRef(rec_id=rec_id, subject=first_db["mname"], ...))
```

**What this does:** Sessions are defined by unique `<mouse>_<date>_<blk>` recording IDs deduplicated from `Imaging_Exp_info.npy`; duplicate experiment-group references for the same recording are merged via `choose_canonical_behavior`.

**Rating:** match

**Note:** _(no note)_---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trial frames are filtered to `ft_CorrSpc & (ft_move > 0)` to match the paper/code running-only analysis." (CONVERSION_NOTES.md:202)

**Code** (convert_data.py:293-307):
```python
def compute_trial_masks(beh: dict) -> list[np.ndarray]:
    ft_trial = np.asarray(beh["ft_trInd"], dtype=float)
    ft_trial_int = np.full(ft_trial.shape, -1, dtype=np.int64)
    finite_trial = np.isfinite(ft_trial)
    ft_trial_int[finite_trial] = ft_trial[finite_trial].astype(np.int64)
    ft_corr = np.asarray(beh["ft_CorrSpc"]).astype(bool)
    ft_move = np.asarray(beh["ft_move"], dtype=float) > 0
    valid = finite_trial & ft_corr & ft_move
    masks = []
    for trial in range(int(beh["ntrials"])):
        frame_idx = np.flatnonzero(valid & (ft_trial_int == trial))
        if len(frame_idx) == 0:
            raise ValueError(f"Trial {trial} has no retained running corridor frames")
        masks.append(frame_idx)
    return masks
```

**What this does:** Trials are split per session by iterating `ntrials` and selecting frames where `ft_trInd` equals the trial index AND the running-corridor mask holds; raises if any trial has zero retained frames.

**Rating:** match

**Note:** _(no note)_---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use only running corridor frames: This matches the paper statement 'We only considered timepoints during running for analysis' and the reference-code masks built from `ft_CorrSpc` and `ft_move > 0`." (CONVERSION_NOTES.md:177)
>
> "Trial extent for export = corridor portion only, not gray space." (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:298-307):
```python
ft_corr = np.asarray(beh["ft_CorrSpc"]).astype(bool)
ft_move = np.asarray(beh["ft_move"], dtype=float) > 0
valid = finite_trial & ft_corr & ft_move
masks = []
for trial in range(int(beh["ntrials"])):
    frame_idx = np.flatnonzero(valid & (ft_trial_int == trial))
    if len(frame_idx) == 0:
        raise ValueError(f"Trial {trial} has no retained running corridor frames")
```

**What this does:** No trials are dropped wholesale; instead each trial's frames are filtered to running-corridor frames only. Trials with zero qualifying frames raise an error rather than being silently skipped.

**Rating:** match

**Note:** _(no note)_---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "data/spk/<mouse>_<date>_<blk>_neural_data.npy: per-session neural activity file; stores a dictionary with key `spks`, where `spks` is a list of neuron-block arrays that must be concatenated across axis 0." (CONVERSION_NOTES.md:69)
>
> "The saved `spks` arrays are the deconvolved activity traces from Suite2p, not raw fluorescence; no additional dF/F computation is needed." (CONVERSION_NOTES.md:149)

**Code** (convert_data.py:477-482):
```python
spk_obj = np.load(ROOT / "data" / "spk" / f"{sess.rec_id}_neural_data.npy", allow_pickle=True).item()
spk_chunks = list(spk_obj["spks"])
ret = np.load(ROOT / "data" / "retinotopy" / f"{sess.subject}_{sess.date_str}_trans.npz", allow_pickle=True)
iarea = np.asarray(ret["iarea"])

kept_idx, region_idx, kept_stats = compute_selected_neurons(spk_chunks, beh, iarea, sess.rec_id)
```

**What this does:** Neural data come from `spks` chunks in `<rec>_neural_data.npy` (Suite2p deconvolved traces) plus retinotopy `iarea` to select V1/mHV/lHV/aHV neurons.

**Rating:** match

**Note:** _(no note)_---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Implemented compromise uses a reference-style neuron subset: mHV familiar-stimulus selective neurons defined from odd running corridor frames using the same top/bottom 5% `d'` logic as `Get_coding_direction`. aHV reward-prediction neurons defined using the same `d'late-vs-early >= 0.3` logic as `Get_dprime_rewPred_neuron`." (CONVERSION_NOTES.md:204-206)
>
> "Neural arrays are currently stored as `float16` to control output size while preserving continuous-valued activity." (CONVERSION_NOTES.md:207)

**Code** (convert_data.py:507-513):
```python
for trial_idx, frame_idx in enumerate(trial_masks):
    trial_chunks = []
    for chunk, local_rows in zip(spk_chunks, chunk_local_rows):
        if len(local_rows) == 0:
            continue
        trial_chunks.append(chunk[local_rows][:, frame_idx])
    neural_trial = np.concatenate(trial_chunks, axis=0).astype(np.float16, copy=False)
```

**What this does:** Concatenates `spks` chunks across the axis-0 neuron dimension, selects a curated subset of neurons (mHV stimulus-selective + aHV reward-prediction), slices to retained frames per trial, and stores as float16.

**Rating:** match

**Note:** _(no note)_---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Keep only neurons assigned to grouped visual regions: Reference analyses operate on `V1`, `mHV`, `lHV`, and `aHV`; neurons outside these groups are not useful for `brain_region_idx` and are excluded." (CONVERSION_NOTES.md:179)
>
> "Paper-level curation is through Suite2p motion correction, ROI detection, cell classification, neuropil correction, and spike deconvolution." (CONVERSION_NOTES.md:123)

**Code** (convert_data.py:234-274):
```python
mhv_mask = percentile_union_mask(stim_dp, corr_neu & areas["mHV"], 95, 5)
if int(np.sum(mhv_mask)) < 128:
    mhv_candidates = np.where(corr_neu & areas["mHV"])[0]
    ...
ahv_mask = np.zeros_like(mhv_mask)
if np.any(is_rew) and np.sum(areas["aHV"]) > 0:
    ...
    reward_dp = dprime(mean_corr[:, late], mean_corr[:, early])
    local_keep = (reward_dp >= 0.3) & (stim_dp[ahv_idx] >= 0)
    ahv_mask[ahv_idx[local_keep]] = True

keep_mask = mhv_mask | ahv_mask
```

**What this does:** Restricts to mHV neurons passing the top/bottom 5% familiar-stimulus `d'` (and the corridor-vs-gray "corr_neu" criterion), unioned with aHV reward-prediction neurons (`d' >= 0.3`); has fallback to top-128 mHV neurons. Non-visual area neurons are dropped.

**Rating:** incorrect

**Note:** _(no note)_---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Neural data stay on the native imaging frame bins (median `314.69 ms`), which is consistent with the reference frame-based deconvolved traces." (CONVERSION_NOTES.md:326)
>
> README.md:11: "Time bin size: median native imaging frame interval, `314.69 ms`."

**Code** (convert_data.py:457):
```python
"time_bin_size": float(np.median([np.median(np.diff(np.asarray(load_beh(s.canonical_exp_type)[s.canonical_beh_key]['ft'], dtype=float))) * 86400.0 for s in sessions]) * 1000.0),
```

**What this does:** No explicit re-binning; neural data stays on the native imaging-frame grid. The metadata reports the median frame interval (`ft` diff in seconds * 1000) as the time bin size.

**Rating:** match

**Note:** _(no note)_---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Exported trials are aligned to corridor entry (`Trial_start_time`), while cue timing is computed from raw `SoundTime` and frame timestamps `ft`." (CONVERSION_NOTES.md:325)
>
> Code metadata: `"temporal_alignment_event": "corridor entry (trial start)"`.

**Code** (convert_data.py:293-307, 458-459):
```python
valid = finite_trial & ft_corr & ft_move
for trial in range(int(beh["ntrials"])):
    frame_idx = np.flatnonzero(valid & (ft_trial_int == trial))
...
"temporal_alignment_event": "corridor entry (trial start)",
"off_start": 0.0,
"off_end": None,
```

**What this does:** Per-trial neural slices are the running-corridor frames whose `ft_trInd == trial_idx`; alignment event is corridor entry (trial start) with `off_start=0`. Cue time is encoded as the `time_to_sound_cue` input rather than as a re-alignment of the neural slice.

**Rating:** match

**Note:** _(no note)_---

## Q 3-a. What variables in the raw data is `output` *visual_stimulus_category* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use `WallName` string labels for stimulus decoding targets: This preserves all naturalistic / grating / swap categories present in the raw trials and avoids ambiguity from NaNs in `stim_id`." (CONVERSION_NOTES.md:181)

**Code** (convert_data.py:497, 527-531):
```python
wall_name = as_str_array(beh["WallName"])
...
stim_code = np.full(
    len(frame_idx),
    category_to_idx[str(wall_name[trial_idx])],
    dtype=np.int16,
)
```

**What this does:** Derived from the per-trial behavior field `WallName`.

**Rating:** match

**Note:** _(no note)_---

## Q 3-b. What processing is involved in computing `output` *visual_stimulus_category*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Map string categories to integer class IDs; repeat per frame within trial." (CONVERSION_NOTES.md:166)

**Code** (convert_data.py:417-424, 527-531):
```python
categories = sorted({str(v) for sess in sessions for v in np.asarray(load_beh(...)[...]['WallName']).tolist()})
category_to_idx = {name: idx for idx, name in enumerate(categories)}
...
stim_code = np.full(len(frame_idx), category_to_idx[str(wall_name[trial_idx])], dtype=np.int16)
```

**What this does:** Builds a global sorted list of all unique `WallName` strings across all sessions (15 categories), maps each to an integer ID, and broadcasts the trial's category across all retained frames.

**Rating:** match

**Note:** _(no note)_---

## Q 3-c. How is `output` *visual_stimulus_category* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Repeat per-trial constants across frames: `day_of_training`, `reward_available`, and `visual_stimulus_category` will be broadcast across time so every trial has consistent `(n_features, n_timepoints)` input/output arrays." (CONVERSION_NOTES.md:184)

**Code** (convert_data.py:527-535):
```python
stim_code = np.full(len(frame_idx), category_to_idx[str(wall_name[trial_idx])], dtype=np.int16)
...
trial_output = np.vstack([stim_code, licking, pos_bin, speed_bin]).astype(np.int16, copy=False)
```

**What this does:** Output is a constant value per trial broadcast across exactly the same `frame_idx` used for the neural slice, giving identical time length to neural.

**Rating:** _(to be filled by evaluator)_

**Note:** _(no note)_---

## Q 4-a. What variables in the raw data is `output` *licking* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavior fields `LickFr`, `LickTrind` -> `output[1]`: Binary frame vector: 1 if one or more licks fall in retained frame, else 0." (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:495-496, 525-526):
```python
lick_fr = np.asarray(beh["LickFr"], dtype=float).astype(int)
lick_tr = np.asarray(beh["LickTrind"], dtype=float).astype(int)
...
lick_trial_frames = lick_fr[lick_tr == trial_idx]
licking = np.isin(frame_idx, lick_trial_frames).astype(np.int16)
```

**What this does:** Derived from raw `LickFr` (lick frame indices) and `LickTrind` (per-lick trial indices).

**Rating:** match

**Note:** _(no note)_---

## Q 4-b. What processing is involved in computing `output` *licking*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Binary frame vector: 1 if one or more licks fall in retained frame, else 0." (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:525-526):
```python
lick_trial_frames = lick_fr[lick_tr == trial_idx]
licking = np.isin(frame_idx, lick_trial_frames).astype(np.int16)
```

**What this does:** For each trial, selects lick events whose `LickTrind == trial_idx`, then marks each retained frame as 1 if it appears in those lick frame indices, else 0.

**Rating:** match

**Note:** _(no note)_---

## Q 4-c. How is `output` *licking* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:525-526, 535):
```python
licking = np.isin(frame_idx, lick_trial_frames).astype(np.int16)
...
trial_output = np.vstack([stim_code, licking, pos_bin, speed_bin]).astype(np.int16, copy=False)
```

**What this does:** Licking is computed on exactly the same `frame_idx` used for the neural slice, producing a binary vector with the same temporal length as the trial's neural data.

**Rating:** match

**Note:** _(no note)_---

## Q 5-a. What variables in the raw data is `output` *position_bin* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavior field `ft_Pos` -> `output[2]`: Discretize corridor position into four 1 m bins over the 4 m texture corridor." (CONVERSION_NOTES.md:168)

**Code** (convert_data.py:499, 532-533):
```python
ft_pos = np.asarray(beh["ft_Pos"], dtype=float)
...
pos = np.clip(ft_pos[frame_idx], 0.0, 39.999)
pos_bin = np.clip((pos // 10.0).astype(np.int16), 0, 3)
```

**What this does:** Derived from frame-level position trace `ft_Pos`.

**Rating:** match

**Note:** _(no note)_---

## Q 5-b. What processing is involved in computing `output` *position_bin*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize position with paper-consistent meter bins: Raw positions are in decimeters; use 4 bins across the 40 dm texture corridor to match the requested 4 equal 1 m bins." (CONVERSION_NOTES.md:182)

**Code** (convert_data.py:532-533):
```python
pos = np.clip(ft_pos[frame_idx], 0.0, 39.999)
pos_bin = np.clip((pos // 10.0).astype(np.int16), 0, 3)
```

**What this does:** Clips position to `[0, 39.999)` decimeters and integer-divides by 10 to give bins 0-3 corresponding to 0-1m, 1-2m, 2-3m, 3-4m.

**Rating:** match

**Note:** _(no note)_---

## Q 5-c. How is `output` *position_bin* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:532-535):
```python
pos = np.clip(ft_pos[frame_idx], 0.0, 39.999)
pos_bin = np.clip((pos // 10.0).astype(np.int16), 0, 3)
...
trial_output = np.vstack([stim_code, licking, pos_bin, speed_bin]).astype(np.int16, copy=False)
```

**What this does:** Position values are read at the same `frame_idx` indices as the neural slice, ensuring identical timepoints.

**Rating:** match

**Note:** _(no note)_---

## Q 6-a. What variables in the raw data is `output` *running_speed_bin* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavior field `ft_RunSpeed` -> `output[3]`: Compute global quartile edges across all retained frames in all sessions, then discretize each retained frame into 4 bins." (CONVERSION_NOTES.md:169)

**Code** (convert_data.py:500, 534):
```python
ft_speed = np.asarray(beh["ft_RunSpeed"], dtype=float)
...
speed_bin = speed_to_bin(ft_speed[frame_idx], speed_edges)
```

**What this does:** Derived from frame-level running-speed trace `ft_RunSpeed`.

**Rating:** match

**Note:** _(no note)_---

## Q 6-b. What processing is involved in computing `output` *running_speed_bin*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize running speed with global quartiles over retained samples: The user explicitly requests 25% data bins, so quartiles will be computed after all filtering decisions are applied." (CONVERSION_NOTES.md:183)

**Code** (convert_data.py:402-412):
```python
trial_masks = compute_trial_masks(beh)
speed_values.append(np.asarray(beh["ft_RunSpeed"], dtype=float)[np.concatenate(trial_masks)])
...
speed_values = np.concatenate(speed_values).astype(np.float32)
speed_edges = np.quantile(speed_values, [0.25, 0.5, 0.75]).astype(np.float32)
...
def speed_to_bin(values, edges):
    return np.clip(np.digitize(values, edges, right=False), 0, 3).astype(np.int16)
```

**What this does:** Pre-pass over all sessions concatenates running-speed values from all retained frames, computes global 25/50/75 quantile edges, then `np.digitize` assigns each retained frame to one of 4 bins.

**Rating:** match

**Note:** _(no note)_---

## Q 6-c. How is `output` *running_speed_bin* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:534-535):
```python
speed_bin = speed_to_bin(ft_speed[frame_idx], speed_edges)
trial_output = np.vstack([stim_code, licking, pos_bin, speed_bin]).astype(np.int16, copy=False)
```

**What this does:** Speeds are sampled at the same `frame_idx` as the neural slice; bin assignment preserves frame-by-frame alignment.

**Rating:** match

**Note:** _(no note)_---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Choose one canonical behavior entry per unique recording after validating duplicates: Repeated experiment-group entries have matching `WallName`, `isRew`, `SoundPos`, and trial counts." (CONVERSION_NOTES.md:175)

**Code** (convert_data.py:25-32, 100-113, 226-227, 304-305):
```python
def dprime(x1, x2):
    ...
    denom = s1 + s2
    denom[denom == 0] = np.nan
    out = 2 * (u1 - u2) / denom
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
...
# duplicate-reference validation in choose_canonical_behavior raises ValueError if mismatched
...
if stim_pos_fr.sum() == 0 or stim_neg_fr.sum() == 0:
    raise ValueError(f"{session_id}: familiar-pair frame masks are empty ...")
...
if len(frame_idx) == 0:
    raise ValueError(f"Trial {trial} has no retained running corridor frames")
```

**What this does:** NaNs/zeros in d' are converted to 0 via `np.nan_to_num`. Non-finite `ft_trInd` frames are excluded via `finite_trial`. Trials/masks with zero data raise errors rather than being silently dropped. Duplicate behavior references must agree on key fields or `ValueError` is raised. Position is clipped to `[0,39.999)`.

**Rating:** ok

**Note:** _(no note)_---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Full-session interpolation for reward-prediction selection can be expensive if applied to all neurons; implementation restricts this step to aHV neurons only." (CONVERSION_NOTES.md:209)
>
> "Rewarded sample sessions ... 15.2 s, 19.0 s ... Weighted full-dataset estimate ~11 to 18 s / session" (CONVERSION_NOTES.md:254-255)
>
> "Corrected full conversion completed in `1,013.7 s` (`16.9 min`)." (CONVERSION_NOTES.md:307)

**Code** (convert_data.py:202, 251-257, 477-478):
```python
spk = np.concatenate(spk_chunks, axis=0)  # full neuron x frame matrix
...
interp_spk = utils.get_interpPos_spk(
    spk[ahv_idx][:, move_idx], poscum_move,
    int(beh["ntrials"]), n_bins=60,
    lengths=float(beh["Corridor_Length"]),
)
...
spk_obj = np.load(... f"{sess.rec_id}_neural_data.npy", allow_pickle=True).item()
spk_chunks = list(spk_obj["spks"])
```

**What this does:** Loading per-session `spks` (multi-GB on full dataset), concatenating chunks into a full neuron x frame matrix in `compute_selected_neurons`, computing d' across all neurons, and `get_interpPos_spk` reward-prediction interpolation are the main cost centers.

**Rating:** match

**Note:** _(no note)_---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:301-307, 483-489, 507-513):
```python
for trial in range(int(beh["ntrials"])):
    frame_idx = np.flatnonzero(valid & (ft_trial_int == trial))
...
for chunk in spk_chunks:
    end = start + chunk.shape[0]
    in_chunk = (kept_idx >= start) & (kept_idx < end)
    chunk_local_rows.append((kept_idx[in_chunk] - start).astype(np.int64, copy=False))
...
for trial_idx, frame_idx in enumerate(trial_masks):
    trial_chunks = []
    for chunk, local_rows in zip(spk_chunks, chunk_local_rows):
        trial_chunks.append(chunk[local_rows][:, frame_idx])
    neural_trial = np.concatenate(trial_chunks, axis=0).astype(np.float16, copy=False)
```

**What this does:** Per-trial Python loops that do `np.flatnonzero(valid & (ft_trial_int == trial))` could use `np.unique`+groupby. The double-nested per-trial-per-chunk slicing loop redoes neuron-row indexing on each chunk per trial; could be done once after concatenation.

**Rating:** ok

**Note:** _(no note)_---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavior-only first pass for speed quartiles and metadata: Avoids touching neural files until conversion stage." (CONVERSION_NOTES.md:213-214)

**Code** (convert_data.py:399-404, 491, 457):
```python
# in build_global_metadata:
beh = load_beh(sess.canonical_exp_type)[sess.canonical_beh_key]
...
trial_masks = compute_trial_masks(beh)
...
# in convert_dataset main loop:
beh = load_beh(sess.canonical_exp_type)[sess.canonical_beh_key]
...
trial_masks = compute_trial_masks(beh)
# and again inside metadata expression:
"time_bin_size": float(np.median([np.median(np.diff(np.asarray(load_beh(s.canonical_exp_type)[s.canonical_beh_key]['ft'], dtype=float))) * 86400.0 for s in sessions]) * 1000.0),
```

**What this does:** `load_beh` is called multiple times per session (in `build_global_metadata`, in the main loop, and again in the metadata `time_bin_size` comprehension). `compute_trial_masks` runs twice per session. Behavior dicts are reparsed each call.

**Rating:** ok

**Note:** _(no note)_---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:202, 229, 244-266):
```python
spk = np.concatenate(spk_chunks, axis=0)
...
stim_dp = dprime(spk[:, stim_pos_fr], spk[:, stim_neg_fr])  # computed for ALL neurons
...
if np.any(is_rew) and np.sum(areas["aHV"]) > 0:
    ...  # entire reward-pred branch skipped on unrewarded sessions
```

**What this does:** `stim_dp` (d') is computed for every neuron in the recording even though only mHV-area neurons are eligible for selection. Reward-prediction interpolation is skipped on unrewarded sessions but still requires the full `spk` concatenation. The full per-trial `compute_trial_masks` work in `build_global_metadata` produces masks that are recomputed (not reused) in the main loop.

**Rating:** match

**Note:** _(no note)_---

## Q 8-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Per-session processing only loads one neural recording at a time." (CONVERSION_NOTES.md:212)
>
> "Trial construction concatenates only the selected neuron subset, not the full recording." (CONVERSION_NOTES.md:213)
>
> "Neural arrays are currently stored as `float16` to control output size." (CONVERSION_NOTES.md:207)

**Code** (convert_data.py:483-489, 513, 569-570):
```python
# slice chunks rather than concatenated full matrix
for chunk, local_rows in zip(spk_chunks, chunk_local_rows):
    trial_chunks.append(chunk[local_rows][:, frame_idx])
neural_trial = np.concatenate(trial_chunks, axis=0).astype(np.float16, copy=False)
...
del spk_obj, spk_chunks, ret
gc.collect()
```

**What this does:** Loads one session's `spks` at a time, slices chunks by selected neuron indices before concatenation, casts neural arrays to `float16`, and explicitly `del` + `gc.collect()` after each session to release memory before loading the next.

**Rating:** match

**Note:** _(no note)_---
