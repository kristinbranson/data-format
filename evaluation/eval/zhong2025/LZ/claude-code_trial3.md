# mouseland — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/mouseland/claude-code/2026-03-23__15-22-50_trial3/verifier/snapshot/`

Outputs identified (K=4): visual_stimulus, licking, position, running_speed

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:64-92):
> Neural: `{mouse}_{date}_{blk}_neural_data.npy` -> dict with 'spks' key -> list of arrays (one per imaging plane), concatenated = (n_neurons, n_frames). Behavior: `Beh_{exp_type}.npy` -> dict keyed by `{mouse}_{date}_{blk}` -> session behavior dict. Retinotopy: `{mouse}_{date}_trans.npz` -> contains iarea, xy_t. Experiment info: `Imaging_Exp_info.npy` -> dict keyed by experiment type -> list of session dicts.

**Code** (convert_data.py:414-478):
```python
sessions = build_session_list()
# ...
beh_cache = {}
exp_types_needed = set(s['exp_type'] for s in sessions)
for et in exp_types_needed:
    beh_cache[et] = load_beh(et)
# ...
for i, session in enumerate(sessions):
    beh = beh_cache[session['exp_type']][session['beh_key']]
    neural_trials, input_trials, output_trials, brain_reg_idx, elapsed = \
        process_session(session, beh, day, speed_quartiles, stim_to_idx, frame_period)
```

**What this does:** Builds a list of unique sessions from `Imaging_Exp_info.npy`, preloads all needed behavior `.npy` files into a cache, then iterates per session loading the per-session `_neural_data.npy` (spks list concatenated across imaging planes) and `_trans.npz` (retinotopy) inside `process_session`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:73-76):
> Unique subjects: 19 mice. Sessions / subject: 1-8 (mean ~4.7).

**Code** (convert_data.py:467-468, 517-518):
```python
subjects = sorted(set(s['mname'] for s in sessions))
subject_to_idx = {s: i for i, s in enumerate(subjects)}
# ...
'subjects': subjects,
'subject_idx': np.array(subject_idx_list, dtype=np.int64),
```

**What this does:** Subjects are derived from the unique `mname` field in the session list and stored as a sorted list; each session in the output is tagged with its subject index via `subject_idx`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:150-154):
> The same physical recording session appears in multiple experiment types (e.g., TX60_2021_06_07_1 appears in both sup_test1 and sup_train2_before_learning). For the decoder, each physical session should be included ONCE. I will pick the first experiment type that contains each session.

**Code** (convert_data.py:84-116):
```python
def build_session_list():
    exp_info = np.load(
        os.path.join(DATA_ROOT, 'beh', 'Imaging_Exp_info.npy'), allow_pickle=True
    ).item()
    seen = set()
    sessions = []
    for exp_type in exp_info:
        for db in exp_info[exp_type]:
            key = (db['mname'], db['datexp'], db['blk'])
            if key in seen:
                continue
            seen.add(key)
            sessions.append({...'exp_type': exp_type, ...})
    sessions.sort(key=lambda s: (s['mname'], s['datexp']))
```

**What this does:** Sessions are keyed by `(mname, datexp, blk)`. The script iterates all experiment types in `Imaging_Exp_info.npy`, deduplicates so each physical recording appears once (using whichever exp_type is encountered first), then sorts by mouse and date.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:184-185):
> Trial window: StartFr to EndFr (corridor + gray space).

**Code** (convert_data.py:237-269):
```python
ntrials = beh['ntrials']
StartFr = beh['StartFr'].astype(int)
EndFr = beh['EndFr'].astype(int)
# ...
for t in range(ntrials):
    start = StartFr[t]
    end = EndFr[t]
    if start < 0 or end > n_total_frames or end <= start:
        skipped += 1
        continue
    end = min(end, len(ft_Pos), len(ft_RunSpeed))
    if end <= start:
        skipped += 1
        continue
    n_tp = end - start
    if n_tp < 2:
        skipped += 1
        continue
```

**What this does:** Trials are split using per-trial `StartFr` and `EndFr` from the behavior dict, including both corridor and gray space frames. Trial windows are clipped to the available frames in spk and behavior arrays.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:126-130):
> Reference code uses all trials in a session. Some analyses only use first 200 trials. Odd/even trial splitting for cross-validation in some analyses.

**Code** (convert_data.py:255-269, 480-482):
```python
if start < 0 or end > n_total_frames or end <= start:
    skipped += 1
    continue
end = min(end, len(ft_Pos), len(ft_RunSpeed))
if end <= start:
    skipped += 1
    continue
n_tp = end - start
if n_tp < 2:
    skipped += 1
    continue
# ...
if len(neural_trials) < 2:
    print(f"    WARNING: Only {len(neural_trials)} trials, skipping session")
    continue
```

**What this does:** Only structural QC: trials with out-of-bounds frame indices, non-positive duration, or fewer than 2 timepoints are skipped. Sessions yielding fewer than 2 valid trials are dropped entirely. No content-based trial filtering applied.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:42-47, 162-164):
> Neural data: Loaded via `load_spk()` -> concatenates multiple planes of Suite2p output -> shape (n_neurons, n_frames). DeltaF/F: NOT needed - data is already Suite2p deconvolved traces. spks (concatenated planes) -> neural; Raw deconvolved spikes, extract per-trial segments StartFr:EndFr.

**Code** (convert_data.py:50-57, 226-272):
```python
def load_spk(db):
    fn = '%s_%s_%s_neural_data.npy' % (db['mname'], db['datexp'], db['blk'])
    spk_path = os.path.join(DATA_ROOT, 'spk', fn)
    spk = np.concatenate(
        [nspk for nspk in np.load(spk_path, allow_pickle=True).item()['spks']], 0
    )
    return spk
# ...
spk = load_spk(session['db_entry'])
# ...
neural = spk[:, start:end].astype(np.float16)
```

**What this does:** Derived from the `spks` field of `{mouse}_{date}_{blk}_neural_data.npy` (Suite2p deconvolved traces, list of arrays per imaging plane), concatenated along the neuron axis.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:42-47):
> Suite2p deconvolved spikes; no additional DeltaF/F needed. Stored as float32 (notes say). Final converted file uses float16 neural per Step 9.

**Code** (convert_data.py:50-57, 271-273):
```python
spk = np.concatenate(
    [nspk for nspk in np.load(spk_path, allow_pickle=True).item()['spks']], 0
)
# ...
# --- Neural ---
neural = spk[:, start:end].astype(np.float16)
# Using float16 to reduce memory (decoder uses PCA, so precision is fine)
```

**What this does:** The list of per-plane spike arrays is concatenated along axis 0 (neurons). Per trial, the corresponding frame slice is extracted and cast to float16. No deconvolution, normalization, or smoothing applied.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:121-124, 188-189):
> Neurons outside visual cortex (iarea == -1) and area 7 (iarea == 7) are excluded in some analyses. For our decoder: include ALL neurons (no filtering by area). All neurons included: No area filtering; let decoder learn.

**Code** (convert_data.py:200-235):
```python
def get_brain_region_idx(iarea):
    region_to_idx = {r: i for i, r in enumerate(BRAIN_REGIONS)}
    idx = np.full(len(iarea), region_to_idx['other'], dtype=np.int64)
    for area_val, region_name in AREA_MAP.items():
        mask = iarea == area_val
        idx[mask] = region_to_idx[region_name]
    return idx
# ...
iarea = load_retino(session['db_entry'])
brain_reg_idx = get_brain_region_idx(iarea)
assert len(iarea) == n_neurons, ...
```

**What this does:** No neurons are dropped. iarea==-1 and iarea==7 are mapped to the 'other' brain-region label rather than excluded. Only an assert is used to verify neuron-count consistency between spk and retinotopy.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:186-187):
> Time bin = frame rate: ~315ms, no additional binning.

**Code** (convert_data.py:271-272, 450-456):
```python
neural = spk[:, start:end].astype(np.float16)
# ...
sample_beh = beh_cache[sessions[0]['exp_type']][sessions[0]['beh_key']]
ft = sample_beh['ft']
dt = np.diff(ft) * 24 * 3600  # datenum to seconds
frame_period = float(np.nanmedian(dt))
```

**What this does:** No resampling is performed. Neural data uses the raw Suite2p frame rate (~3.17 Hz, ~315 ms/frame). The `frame_period` is computed once from the median diff of `ft` (MATLAB datenum) of the first session and stored in metadata.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:184; convert_data.py:538):
> Trial window: StartFr to EndFr. Metadata: `'temporal_alignment_event': 'Trial start (corridor entry)'`, `'off_start': 0.0`, `'off_end': None`.

**Code** (convert_data.py:251-272, 538-540):
```python
for t in range(ntrials):
    start = StartFr[t]
    end = EndFr[t]
    # ...
    neural = spk[:, start:end].astype(np.float16)
# ...
'temporal_alignment_event': 'Trial start (corridor entry)',
'off_start': 0.0,
'off_end': None,   # variable trial length
```

**What this does:** Each trial's neural slice begins at `StartFr` (corridor entry) and ends at `EndFr`. Alignment event documented as trial start; trial length is variable.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| SoundFr - current_frame | input[0]: time_to_sound_cue | (SoundFr - frame_idx) * frame_period_sec, continuous | Negative before, positive = time since |" (CONVERSION_NOTES.md:165)
> "`SoundFr`: Correctly used as per-trial scalar frame index" (CONVERSION_NOTES.md:294)

**Code** (convert_data.py:237-244, 450-455):
```python
    ntrials = beh['ntrials']
    StartFr = beh['StartFr'].astype(int)
    EndFr = beh['EndFr'].astype(int)
    SoundFr = beh['SoundFr']
    ...
    # Compute mean frame period
    sample_beh = beh_cache[sessions[0]['exp_type']][sessions[0]['beh_key']]
    ft = sample_beh['ft']
    dt = np.diff(ft) * 24 * 3600  # datenum to seconds
    frame_period = float(np.nanmedian(dt))
```

**What this does:** `input[0]` is named `time_to_sound_cue` and is built from the behavior field `beh['SoundFr']` (per-trial sound-cue frame index), the trial frame indices set by `beh['StartFr']`/`beh['EndFr']`, and a single global `frame_period` computed from the `ft` timestamps of the first session only.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| SoundFr - current_frame | input[0]: time_to_sound_cue | (SoundFr - frame_idx) * frame_period_sec, continuous | Negative before, positive = time since |" (CONVERSION_NOTES.md:165)
> "**Frame period consistency**: std=0.0003s across 99 sessions — using single session value is fine" (CONVERSION_NOTES.md:296)

**Code** (convert_data.py:275-290):
```python
        # --- Inputs ---
        # 1. Time to sound cue (seconds): positive = time until cue, negative = time since cue
        sound_fr = SoundFr[t]
        frame_indices = np.arange(start, end, dtype=np.float64)
        time_to_sound = (sound_fr - frame_indices) * frame_period  # positive before, negative after

        # 2. Day of training (constant for trial)
        day = np.full(n_tp, training_day, dtype=np.float32)

        # 3. Time since trial start (seconds)
        time_since_start = (frame_indices - start) * frame_period

        # 4. Reward availability
        rew = np.full(n_tp, float(isRew[t]), dtype=np.float32)

        inp = np.stack([time_to_sound, day, time_since_start, rew], axis=0).astype(np.float32)
```

**What this does:** Per trial, the frame indices from `StartFr` to `EndFr` are subtracted from that trial's `SoundFr` and multiplied by the constant `frame_period`, giving seconds relative to the cue that are positive before the cue and negative after. No NaN handling is applied to `SoundFr`. The result is cast to float32 as row 0 of the `(4, n_timepoints)` input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Trial window**: StartFr to EndFr (corridor + gray space)" (CONVERSION_NOTES.md:185)
> "'temporal_alignment_event': 'Trial start (corridor entry)', 'off_start': 0.0" (convert_data.py:538-539)

**Code** (convert_data.py:251-253, 266-279):
```python
    for t in range(ntrials):
        start = StartFr[t]
        end = EndFr[t]
        ...
        n_tp = end - start
        ...
        # --- Neural ---
        neural = spk[:, start:end].astype(np.float16)
        ...
        sound_fr = SoundFr[t]
        frame_indices = np.arange(start, end, dtype=np.float64)
        time_to_sound = (sound_fr - frame_indices) * frame_period
```

**What this does:** `frame_indices` covers the same `start:end` session frames used to slice `spk`, so element *i* of the input matches neural frame `start + i`, and both arrays have length `n_tp = end - start`. `end` is additionally clipped to `min(end, len(ft_Pos), len(ft_RunSpeed))` before the slice.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Session date order | input[1]: day_of_training | Chronological session index within mouse | Per-trial (broadcast) |" (CONVERSION_NOTES.md:166)
> "**Day of training**: Ordinal session index (by date) within each mouse" (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:89-92, 104-112):
```python
    exp_info = np.load(
        os.path.join(DATA_ROOT, 'beh', 'Imaging_Exp_info.npy'), allow_pickle=True
    ).item()
    ...
            sessions.append({
                'mname': db['mname'],
                'datexp': db['datexp'],
                'blk': db['blk'],
                ...
            })
```

**What this does:** `input[1]` is named `day_of_training` and is derived from the `mname` (mouse) and `datexp` (session date string) fields of the session entries in `beh/Imaging_Exp_info.npy`; no dedicated training-day field in the raw data is used.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Day of training**: Ordinal session index (by date) within each mouse" (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:119-131, 282):
```python
def compute_training_days(sessions):
    """Compute ordinal training day for each session within each mouse."""
    mouse_sessions = defaultdict(list)
    for i, s in enumerate(sessions):
        mouse_sessions[s['mname']].append((s['datexp'], i))

    days = np.zeros(len(sessions), dtype=np.float32)
    for mname, sess_list in mouse_sessions.items():
        sess_list.sort(key=lambda x: x[0])  # sort by date
        for day_idx, (datexp, global_idx) in enumerate(sess_list):
            days[global_idx] = float(day_idx)
    return days
    ...
        day = np.full(n_tp, training_day, dtype=np.float32)
```

**What this does:** Sessions are grouped by mouse and sorted by the `datexp` string, then each session receives its 0-based rank in that ordering (an ordinal session index rather than a calendar-day difference). The per-session scalar is broadcast with `np.full` over all timepoints of every trial as input row 1. In `--sample` mode the ranks are computed over only the sampled sessions.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| frame_idx - StartFr | input[2]: time_since_trial_start | (frame_idx - StartFr) * frame_period_sec | Time-varying |" (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:238-239, 452-455):
```python
    StartFr = beh['StartFr'].astype(int)
    EndFr = beh['EndFr'].astype(int)
    ...
    sample_beh = beh_cache[sessions[0]['exp_type']][sessions[0]['beh_key']]
    ft = sample_beh['ft']
    dt = np.diff(ft) * 24 * 3600  # datenum to seconds
    frame_period = float(np.nanmedian(dt))
```

**What this does:** `input[2]` is named `time_since_trial_start` and is derived from `beh['StartFr']` (trial-start frame) plus the within-trial frame index, scaled by the global `frame_period` computed from the `ft` frame timestamps of the first session.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| frame_idx - StartFr | input[2]: time_since_trial_start | (frame_idx - StartFr) * frame_period_sec | Time-varying |" (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:278, 284-290):
```python
        frame_indices = np.arange(start, end, dtype=np.float64)
        ...
        # 3. Time since trial start (seconds)
        time_since_start = (frame_indices - start) * frame_period

        # 4. Reward availability
        rew = np.full(n_tp, float(isRew[t]), dtype=np.float32)

        inp = np.stack([time_to_sound, day, time_since_start, rew], axis=0).astype(np.float32)
```

**What this does:** The trial's start frame `start` (`StartFr[t]`, cast to int) is subtracted from the trial frame indices and multiplied by the constant `frame_period`, producing a ramp in seconds beginning at 0.0. It becomes row 2 of the input array after the float32 cast. Since the window runs to `EndFr`, the ramp spans corridor plus grey-space frames.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Trial window**: StartFr to EndFr (corridor + gray space)" (CONVERSION_NOTES.md:185)
> "'temporal_alignment_event': 'Trial start (corridor entry)', 'off_start': 0.0, 'off_end': None" (convert_data.py:538-540)

**Code** (convert_data.py:252-285):
```python
        start = StartFr[t]
        end = EndFr[t]
        ...
        # Also clip end to available frames in beh arrays
        end = min(end, len(ft_Pos), len(ft_RunSpeed))
        ...
        n_tp = end - start
        ...
        neural = spk[:, start:end].astype(np.float16)
        ...
        frame_indices = np.arange(start, end, dtype=np.float64)
        ...
        time_since_start = (frame_indices - start) * frame_period
```

**What this does:** The ramp is defined on the same `start:end` frame range used to slice `spk`, so its 0.0 value falls on the first neural frame of the trial (corridor entry) and each subsequent sample advances one neural frame; both arrays have length `n_tp`.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| isRew | input[3]: reward_availability | 1 if rewarded corridor, 0 if not | Per-trial (broadcast) |" (CONVERSION_NOTES.md:168)
> "| Reward zone | After sound cue in rewarded corridor | Methods |" (CONVERSION_NOTES.md:108)

**Code** (convert_data.py:237-244):
```python
    ntrials = beh['ntrials']
    StartFr = beh['StartFr'].astype(int)
    EndFr = beh['EndFr'].astype(int)
    SoundFr = beh['SoundFr']
    WallName = beh['WallName']
    isRew = beh['isRew']
    ft_Pos = beh['ft_Pos']
    ft_RunSpeed = beh['ft_RunSpeed']
```

**What this does:** `input[3]` is named `reward_availability` and comes from the per-trial behavior field `beh['isRew']`, indexed by trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| isRew | input[3]: reward_availability | 1 if rewarded corridor, 0 if not | Per-trial (broadcast) |" (CONVERSION_NOTES.md:168)

**Code** (convert_data.py:287-290):
```python
        # 4. Reward availability
        rew = np.full(n_tp, float(isRew[t]), dtype=np.float32)

        inp = np.stack([time_to_sound, day, time_since_start, rew], axis=0).astype(np.float32)
```

**What this does:** The trial's `isRew` entry is cast with `float()` and broadcast by `np.full` across all `n_tp` timepoints as row 3 of the input array, so it is constant within each trial; no reward-zone timing (e.g. onset after the sound cue) modulates it.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> WallName -> output[0]: visual_stimulus; Map to category index; Per-trial, 15 unique stimuli.

**Code** (convert_data.py:154-161, 293-296):
```python
def get_all_stimuli(sessions, beh_cache):
    all_stim = set()
    for s in sessions:
        beh = beh_cache[s['exp_type']][s['beh_key']]
        for wn in beh['UniqWalls']:
            all_stim.add(str(wn))
    return sorted(all_stim)
# ...
stim_name = str(WallName[t])
stim_idx = stim_to_idx[stim_name]
```

**What this does:** Derived from per-trial `WallName` from each session's behavior dict; the global vocabulary is built from `UniqWalls` across all sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

**Notes excerpt** (CONVERSION_NOTES.md:170, 226):
> Per-trial, 15 unique stimuli. Output_values lists `all_stimuli` for visual_stimulus.

**Code** (convert_data.py:443-445, 293-296):
```python
all_stimuli = get_all_stimuli(sessions, beh_cache)
stim_to_idx = {s: i for i, s in enumerate(all_stimuli)}
# ...
stim_name = str(WallName[t])
stim_idx = stim_to_idx[stim_name]
stim_out = np.full(n_tp, stim_idx, dtype=np.int64)
```

**What this does:** Wall names are stringified and mapped to a global integer index using a sorted vocabulary built across all sessions. The per-trial scalar index is broadcast across all timepoints in the trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> LickFr, LickTrind -> output[1]: licking; Binary per frame, 1 if lick in frame.

**Code** (convert_data.py:178-197):
```python
def make_lick_vector(beh, start_fr, end_fr):
    n_frames = end_fr - start_fr
    lick_vec = np.zeros(n_frames, dtype=np.int64)
    lick_frs = beh['LickFr']
    lick_frs_int = np.round(lick_frs).astype(int)
    mask = (lick_frs_int >= start_fr) & (lick_frs_int < end_fr)
    if mask.any():
        trial_lick_frs = lick_frs_int[mask] - start_fr
        trial_lick_frs = np.clip(trial_lick_frs, 0, n_frames - 1)
        lick_vec[trial_lick_frs] = 1
    return lick_vec
```

**What this does:** Derived from `LickFr` (fractional frame indices of lick events) in the behavior dict. `LickTrind` is mentioned in notes but not actually used; lick events are filtered into trial windows by frame index.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *licking*?

**Notes excerpt** (CONVERSION_NOTES.md:191):
> Licking: Round LickFr to nearest int frame, create binary vector per trial.

**Code** (convert_data.py:184-196):
```python
lick_vec = np.zeros(n_frames, dtype=np.int64)
lick_frs = beh['LickFr']
lick_frs_int = np.round(lick_frs).astype(int)
mask = (lick_frs_int >= start_fr) & (lick_frs_int < end_fr)
if mask.any():
    trial_lick_frs = lick_frs_int[mask] - start_fr
    trial_lick_frs = np.clip(trial_lick_frs, 0, n_frames - 1)
    lick_vec[trial_lick_frs] = 1
```

**What this does:** Lick frame times are rounded to integer frames, masked to the trial window, offset relative to trial start, clipped to bounds, and used as indices to set entries of a zero vector to 1 (binary per-frame).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> Time-varying.

**Code** (convert_data.py:178-184, 297-299):
```python
def make_lick_vector(beh, start_fr, end_fr):
    n_frames = end_fr - start_fr
    lick_vec = np.zeros(n_frames, dtype=np.int64)
# ...
lick = make_lick_vector(beh, start, end)
```

**What this does:** Lick vector length equals `end - start`, matching the trial's neural frame range; lick frame indices are converted to be relative to `start_fr`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> ft_Pos -> output[2]: position; 4 bins of 1m: [0,10), [10,20), [20,30), [30,60) dm; Time-varying.

**Code** (convert_data.py:243, 301-303):
```python
ft_Pos = beh['ft_Pos']
# ...
pos = ft_Pos[start:end]
pos_bin = digitize_position(pos)
```

**What this does:** Derived from `ft_Pos` (per-frame VR position in dm) in the behavior dict.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *position*?

**Notes excerpt** (CONVERSION_NOTES.md:187):
> Position bin 3 includes gray space: [30,60) dm covers 3-4m texture + 2m gray.

**Code** (convert_data.py:43-44, 164-169, 301-303):
```python
POS_BIN_EDGES = [0, 10, 20, 30, 60.01]
POS_BIN_LABELS = ['0-1m', '1-2m', '2-3m', '3m+']
# ...
def digitize_position(pos):
    bins = np.digitize(pos, [10, 20, 30])
    return bins.astype(np.int64)
# ...
pos = ft_Pos[start:end]
pos_bin = digitize_position(pos)
```

**What this does:** Per-frame position values are discretized via `np.digitize` into 4 bins (1 m each, last bin captures 3 m through 6 m corridor including gray space).

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 9-c. How is `output` *position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> Time-varying.

**Code** (convert_data.py:301-303, 309):
```python
pos = ft_Pos[start:end]
pos_bin = digitize_position(pos)
# ...
out = np.stack([stim_out, lick, pos_bin, speed_bin], axis=0).astype(np.int64)
```

**What this does:** Position is sliced from the same `start:end` frame range as the neural data, giving one position bin per neural frame.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> ft_RunSpeed -> output[3]: running_speed; Quartile bins across all data; Time-varying.

**Code** (convert_data.py:244, 305-307):
```python
ft_RunSpeed = beh['ft_RunSpeed']
# ...
speed = ft_RunSpeed[start:end]
speed_bin = digitize_speed(speed, speed_quartiles)
```

**What this does:** Derived from `ft_RunSpeed` (per-frame running speed in cm/s) in the behavior dict.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

**Notes excerpt** (CONVERSION_NOTES.md:189):
> Speed quartiles: Computed globally across all frames in all sessions.

**Code** (convert_data.py:138-151, 172-175, 305-307):
```python
def compute_speed_quartiles(sessions, beh_cache):
    all_speeds = []
    for s in sessions:
        beh = beh_cache[s['exp_type']][s['beh_key']]
        speeds = beh['ft_RunSpeed']
        all_speeds.append(speeds)
    all_speeds = np.concatenate(all_speeds)
    quartiles = np.percentile(all_speeds, [25, 50, 75])
    return quartiles
# ...
def digitize_speed(speed, quartiles):
    bins = np.digitize(speed, quartiles)
    return bins.astype(np.int64)
```

**What this does:** Global 25/50/75 percentiles are computed across all `ft_RunSpeed` frames in all sessions, then per-frame speeds are discretized via `np.digitize` into 4 quartile bins.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 10-c. How is `output` *running_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:170):
> Time-varying.

**Code** (convert_data.py:305-307, 309):
```python
speed = ft_RunSpeed[start:end]
speed_bin = digitize_speed(speed, speed_quartiles)
# ...
out = np.stack([stim_out, lick, pos_bin, speed_bin], axis=0).astype(np.int64)
```

**What this does:** Speed is sliced from the same `start:end` frame range as the neural data, giving one quartile bin per neural frame.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:233-269, 449-456, 480-482):
```python
assert len(iarea) == n_neurons, \
    f"Neuron count mismatch: spk={n_neurons}, retinotopy={len(iarea)}"
# ...
if start < 0 or end > n_total_frames or end <= start:
    skipped += 1
    continue
end = min(end, len(ft_Pos), len(ft_RunSpeed))
if end <= start:
    skipped += 1
    continue
n_tp = end - start
if n_tp < 2:
    skipped += 1
    continue
# ...
frame_period = float(np.nanmedian(dt))
# ...
if len(neural_trials) < 2:
    print(f"    WARNING: Only {len(neural_trials)} trials, skipping session")
    continue
```

**What this does:** Out-of-range/empty/short trials are skipped with a counted warning. End frames are clipped to behavior-array length. `np.nanmedian` is used to ignore NaNs in frame-period computation. Sessions with <2 valid trials are dropped. Lick frame indices outside trial bounds are filtered; in-bound indices are clipped before assignment. Hard `assert` on neuron-count mismatch.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:233-237):
> Processing: ~15s/session; Estimated total ~22 min. File size ~7 GB/session, ~217 GB float32. Step 9: 33.4 min total.

**Code** (convert_data.py:50-57, 470-505, 577-579):
```python
spk = np.concatenate(
    [nspk for nspk in np.load(spk_path, allow_pickle=True).item()['spks']], 0
)
# ...
for i, session in enumerate(sessions):
    # load + process per session
    ...
# ...
with open(args.outfile, 'wb') as f:
    pickle.dump(data, f, protocol=5)
```

**What this does:** Per-session loading of the large `_neural_data.npy` file and the final pickle dump (≈202 GB) are the dominant costs; the per-session loop processes 89 sessions sequentially.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:251-313, 200-211):
```python
for t in range(ntrials):
    start = StartFr[t]
    end = EndFr[t]
    # ... per-trial neural slice, input stack, lick vector, digitize, stack
    neural_trials.append(neural)
    input_trials.append(inp)
    output_trials.append(out)
# ...
def get_brain_region_idx(iarea):
    idx = np.full(len(iarea), region_to_idx['other'], dtype=np.int64)
    for area_val, region_name in AREA_MAP.items():
        mask = iarea == area_val
        idx[mask] = region_to_idx[region_name]
    return idx
```

**What this does:** The per-trial loop in `process_session` does Python-level slicing and stacking that could partially be precomputed once per session (e.g., `digitize_position(ft_Pos)`, `digitize_speed(ft_RunSpeed, ...)` over the whole session, then sliced). The brain-region map is looped per-area_val instead of using a single lookup array.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:138-151, 154-161, 178-197, 205):
```python
def compute_speed_quartiles(sessions, beh_cache):
    for s in sessions:
        beh = beh_cache[s['exp_type']][s['beh_key']]
        speeds = beh['ft_RunSpeed']
        all_speeds.append(speeds)
# ...
def get_all_stimuli(sessions, beh_cache):
    for s in sessions:
        beh = beh_cache[s['exp_type']][s['beh_key']]
        for wn in beh['UniqWalls']:
            all_stim.add(str(wn))
# ...
def make_lick_vector(beh, start_fr, end_fr):
    lick_frs = beh['LickFr']
    lick_frs_int = np.round(lick_frs).astype(int)
# ...
region_to_idx = {r: i for i, r in enumerate(BRAIN_REGIONS)}
```

**What this does:** `compute_speed_quartiles` and `get_all_stimuli` both iterate over all sessions/behavior dicts separately. `make_lick_vector` re-rounds and re-indexes `LickFr` for each trial of each session (could be done once per session). `region_to_idx` is rebuilt every call to `get_brain_region_idx`.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:60-64, 200-211, 326-390):
```python
def load_retino(db):
    fn = '%s_%s_trans.npz' % (db['mname'], db['datexp'])
    dtrans = np.load(os.path.join(DATA_ROOT, 'retinotopy', fn), allow_pickle=True)
    return dtrans['iarea']
# ...
def plot_processing(...):
    # produces processing_*.png plots, only invoked when --show-processing
```

**What this does:** Retinotopy `.npz` is loaded but only `iarea` is used (other arrays like `xy_t` are ignored). `brain_region_idx` is computed and stored but not consumed by the trial-level neural data. Optional `plot_processing` is only emitted under a flag, so not unconditionally wasted.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md:264, 314-316):
> converted_data.pkl: 202 GB (pickle protocol 5, float16 neural data). Neurons subsampled to 3000/session ... in decoder.

**Code** (convert_data.py:271-273, 500-504, 572-574):
```python
neural = spk[:, start:end].astype(np.float16)
# Using float16 to reduce memory
# ...
if (i + 1) % 10 == 0:
    gc.collect()
    total_neural_mb = sum(sum(t.nbytes for t in s) for s in neural_all) / 1e6
    print(f"    [Memory] Total neural so far: {total_neural_mb/1000:.1f} GB")
# ...
del beh_cache
gc.collect()
```

**What this does:** Neural data stored as float16 to roughly halve memory. Periodic `gc.collect()` every 10 sessions and a behavior-cache deletion before pickle save. Pickle protocol 5 used. All 89 sessions are still held in memory simultaneously before saving.

**Rating:** match

**Note:** _(no note)_---

---
