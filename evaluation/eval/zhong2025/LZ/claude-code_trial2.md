# mouseland — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/mouseland/claude-code/2026-03-23__15-22-50_trial2/verifier/snapshot/`

Outputs identified (K=4): visual_stimulus, licking, position, running_speed

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Session map building from Imaging_Exp_info.npy" / "Neural data loading with per-plane filtering" (lines 211-212). Data sources: `data/spk/{mname}_{datexp}_{blk}_neural_data.npy`, `data/retinotopy/{mname}_{datexp}_trans.npz`, `data/beh/Beh_{exp_type}.npy`, `data/beh/Imaging_Exp_info.npy` (lines 64-67).

**Code** (convert_data.py:92-115, 279-322):
```python
def build_session_map():
    exp_info = np.load(os.path.join(DATA_ROOT, 'beh', 'Imaging_Exp_info.npy'),
                       allow_pickle=True).item()
    session_map = {}
    for exp_type, db_list in exp_info.items():
        for ndb in db_list:
            spk_key = f"{ndb['mname']}_{ndb['datexp']}_{ndb['blk']}"
            beh_key = f"{spk_key}_{ndb['stimtype']}" if 'stimtype' in ndb else spk_key
            if spk_key not in session_map or 'stimtype' not in ndb:
                session_map[spk_key] = {
                    'exp_type': exp_type, 'beh_key': beh_key, 'db': dict(ndb)
                }
    return session_map
# main loop:
for idx, spk_key in enumerate(keys):
    info = session_map[spk_key]
    result = process_session(spk_key, info, speed_quartiles)
```

**What this does:** Builds a session map from `Imaging_Exp_info.npy` keyed by `{mname}_{datexp}_{blk}`, deduplicating across stim variants. Iterates sorted session keys, calling `process_session` for each, which loads retinotopy, neural spikes, and behavior files on demand.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "mouse name → subjects, subject_idx" (line 184). 19 subjects total (line 71).

**Code** (convert_data.py:298, 311-317, 332, 339):
```python
subjects_seen = {}
...
mname = info['db']['mname']
...
if mname not in subjects_seen:
    subjects_seen[mname] = len(subjects_seen)
subject_idx_list.append(subjects_seen[mname])
...
subjects = sorted(subjects_seen.keys(), key=lambda x: subjects_seen[x])
'subject_idx': np.array(subject_idx_list, dtype=np.int64),
```

**What this does:** `mname` (mouse name) parsed from session metadata identifies each subject. A dictionary assigns a sequential integer index per first-encountered subject; `subject_idx[s]` gives subject identity for session `s`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sessions can appear in multiple experiment types (142 total entries for 89 unique sessions). For the decoder, each physical recording (neural data file) is used once." (line 165)

**Code** (convert_data.py:97-106, 281):
```python
for exp_type, db_list in exp_info.items():
    for ndb in db_list:
        spk_key = f"{ndb['mname']}_{ndb['datexp']}_{ndb['blk']}"
        ...
        if spk_key not in session_map or 'stimtype' not in ndb:
            session_map[spk_key] = {...}
...
keys = sample_keys if sample_keys else sorted(session_map.keys())
```

**What this does:** Each session is uniquely identified by `(mname, datexp, blk)` matching neural data filenames. Duplicate exp_info entries (different stimtypes for same recording) are deduplicated via `session_map`. Result: 89 sessions iterated in sorted order.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trial length: Use frames from StartFr to start of next trial (or end of session). This captures corridor + gray space." (lines 188-189)

**Code** (convert_data.py:166-167, 176, 216-224):
```python
ntrials = beh['ntrials']
nfr_use = min(nfr, len(beh['ft']))
...
StartFr = beh['StartFr'].astype(int)
...
for i in range(ntrials):
    start = StartFr[i]
    end = StartFr[i + 1] if i < ntrials - 1 else nfr_use
    start = max(0, start)
    end = min(nfr_use, end)
    n_frames = end - start
    if n_frames < 2:
        continue
```

**What this does:** Iterates `ntrials` trials per session. Each trial spans `[StartFr[i], StartFr[i+1])` (or to end of session for last trial), clamped to valid frame range. Trials with <2 frames are skipped.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "No explicit trial filtering in reference code for basic loading... For decoder: use all trials (no filtering)" (lines 141-143)

**Code** (convert_data.py:222-224, 258-260):
```python
n_frames = end - start
if n_frames < 2:
    continue
...
if len(neural_trials) < 2:
    print(f"WARNING: <2 valid trials for {spk_key}")
    return None
```

**What this does:** Only filters trials shorter than 2 frames. Sessions with fewer than 2 valid trials are skipped entirely. No other quality-based trial filtering.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "spk (concatenated planes) → neural" (line 175). "Neural data: Suite2p deconvolved calcium traces (NOT raw fluorescence). Deconvolution with tau=0.75s." (line 45)

**Code** (convert_data.py:55-70):
```python
def load_spk_filtered(mname, datexp, blk, valid_mask):
    fn = f'{mname}_{datexp}_{blk}_neural_data.npy'
    spk_data = np.load(os.path.join(DATA_ROOT, 'spk', fn), allow_pickle=True).item()
    planes = spk_data['spks']
    filtered = []
    offset = 0
    for plane in planes:
        n = plane.shape[0]
        plane_mask = valid_mask[offset:offset+n]
        filtered.append(plane[plane_mask].astype(np.float16))
        offset += n
    return np.concatenate(filtered, 0)
```

**What this does:** Neural data derives from `spks` (list of per-plane deconvolved calcium trace arrays) in `data/spk/{mname}_{datexp}_{blk}_neural_data.npy`. Brain area assignments come from `iarea` in `data/retinotopy/{mname}_{datexp}_trans.npz`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Filter neurons per-plane before concatenation (saves memory and time); Store neural data as float16 (halves file size)" (lines 222-223). "No additional delta F/F computation needed" (line 129).

**Code** (convert_data.py:62-70, 161-162, 168, 227):
```python
for plane in planes:
    n = plane.shape[0]
    plane_mask = valid_mask[offset:offset+n]
    filtered.append(plane[plane_mask].astype(np.float16))
    offset += n
return np.concatenate(filtered, 0)
...
spk = load_spk_filtered(mname, datexp, blk, valid_mask)
nneu, nfr = spk.shape
...
spk = spk[:, :nfr_use]
...
trial_spk = spk[:, start:end].copy()
```

**What this does:** Per-plane neuron filtering by `valid_mask`, cast to float16, then concatenated across planes into `(n_neurons, n_frames)`. Truncated to length of behavior arrays. Sliced into per-trial windows.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Exclude neurons outside visual cortex: iarea==-1 or iarea==7" (line 138). "Brain region assignment from retinotopy data" (line 132).

**Code** (convert_data.py:30, 80-89):
```python
EXCLUDED_AREAS = {-1, 7}  # Outside visual cortex
...
def get_brain_region_idx(iarea):
    valid_mask = np.array([int(ia) not in EXCLUDED_AREAS for ia in iarea])
    region_idx = np.array([
        BRAIN_REGIONS.index(AREA_MAP.get(int(ia), 'V1'))
        for ia in iarea[valid_mask]
    ], dtype=np.int64)
    return valid_mask, region_idx
```

**What this does:** Neurons with `iarea == -1` or `iarea == 7` (outside visual cortex) are excluded via boolean mask. Remaining neurons assigned to V1, mHV, lHV, or aHV regions. No further activity-based QC.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trial length: Use frames from StartFr to start of next trial (or end of session)" (line 188). `'temporal_alignment_event': 'corridor entry (trial start)'` (line 355).

**Code** (convert_data.py:218-227, 355):
```python
start = StartFr[i]
end = StartFr[i + 1] if i < ntrials - 1 else nfr_use
start = max(0, start)
end = min(nfr_use, end)
n_frames = end - start
if n_frames < 2:
    continue
trial_spk = spk[:, start:end].copy()
...
'temporal_alignment_event': 'corridor entry (trial start)',
```

**What this does:** Each trial's neural slice begins at frame `StartFr[i]` (corridor entry) and ends at the next trial's start. Frame index 0 of the trial corresponds to the corridor entry event.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Time bin size: Use native frame rate (~315 ms). No resampling needed." (line 188). `time_bin_size = 1000.0/3.17 ≈ 315.5 ms`.

**Code** (convert_data.py:33-34, 202-205, 354):
```python
FRAME_RATE = 3.17  # Hz
TIME_BIN_MS = 1000.0 / FRAME_RATE  # ~315.5 ms
...
ft = beh['ft']
dt = np.median(np.diff(ft[:min(1000, len(ft))])) * 86400  # days->seconds
fs = 1.0 / dt if dt > 0 else FRAME_RATE
...
'time_bin_size': TIME_BIN_MS,
```

**What this does:** No resampling. Native imaging frame rate (~3.17 Hz, ~315 ms per frame) is preserved. Per-session sampling rate `fs` is derived from median frame timestamp difference for input scaling.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Time to SoundFr | input[0]: time_to_sound_cue | (SoundFr - current_frame) / fs | Negative before cue, 0 at cue, positive after |" (CONVERSION_NOTES.md:176)
> "`SoundFr`: frame index of sound cue delivery" (CONVERSION_NOTES.md:98)

**Code** (convert_data.py:176-177, 202-205):
```python
    # Per-trial arrays
    StartFr = beh['StartFr'].astype(int)
    SoundFr = beh['SoundFr']
    ...
    # Frame rate for this session
    ft = beh['ft']
    dt = np.median(np.diff(ft[:min(1000, len(ft))])) * 86400  # days->seconds
    fs = 1.0 / dt if dt > 0 else FRAME_RATE
```

**What this does:** `input[0]` is named `time_to_sound_cue` and is built from the behavior field `beh['SoundFr']` (per-trial sound-cue frame), the trial's frame indices anchored at `beh['StartFr']`, and a per-session sampling rate `fs` derived from the `beh['ft']` frame timestamps (falling back to the 3.17 Hz constant if `dt <= 0`).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Time to SoundFr | input[0]: time_to_sound_cue | (SoundFr - current_frame) / fs | Negative before cue, 0 at cue, positive after |" (CONVERSION_NOTES.md:176)

**Code** (convert_data.py:229-242):
```python
        # Inputs: (4, n_timepoints)
        frame_idx = np.arange(start, end)
        sound_fr = SoundFr[i]
        if np.isnan(sound_fr):
            time_to_sound = np.zeros(n_frames, dtype=np.float32)
        else:
            time_to_sound = ((sound_fr - frame_idx) / fs).astype(np.float32)

        inp = np.stack([
            time_to_sound,
            np.full(n_frames, day, dtype=np.float32),
            (np.arange(n_frames) / fs).astype(np.float32),
            np.full(n_frames, float(isRew[i]), dtype=np.float32),
        ], axis=0)
```

**What this does:** Per trial, session frame indices are subtracted from that trial's `SoundFr` and divided by the sampling rate `fs`, yielding seconds relative to the cue that are positive before the cue and negative after; trials with `SoundFr == NaN` get an all-zero row. The float32 result is row 0 of the `(4, n_timepoints)` input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Trial length**: Use frames from StartFr to start of next trial (or end of session). This captures corridor + gray space." (CONVERSION_NOTES.md:189)
> "'temporal_alignment_event': 'corridor entry (trial start)'" (convert_data.py:355)

**Code** (convert_data.py:216-235):
```python
    for i in range(ntrials):
        # Trial frames: StartFr[i] to StartFr[i+1] or end
        start = StartFr[i]
        end = StartFr[i + 1] if i < ntrials - 1 else nfr_use
        ...
        # Neural: (n_neurons, n_timepoints), already float16
        trial_spk = spk[:, start:end].copy()

        # Inputs: (4, n_timepoints)
        frame_idx = np.arange(start, end)
        sound_fr = SoundFr[i]
        ...
            time_to_sound = ((sound_fr - frame_idx) / fs).astype(np.float32)
```

**What this does:** `frame_idx` spans the same `start:end` range used to slice `spk`, so element *i* of the input corresponds to neural frame `start + i` and both have length `end - start`. Neural and behavior frames are first truncated to a common length `nfr_use = min(nfr, len(beh['ft']))`.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Session day info | input[1]: day_of_training | Session index within mouse or sess# field | Per-trial scalar |" (CONVERSION_NOTES.md:177)
> "**Day of training**: Use sess# or days field from exp_info if available; otherwise use session chronological order within subject." (CONVERSION_NOTES.md:195)

**Code** (convert_data.py:92-106, 118-123):
```python
def build_session_map():
    """Build mapping: spk_key -> {exp_type, beh_key, db}"""
    exp_info = np.load(os.path.join(DATA_ROOT, 'beh', 'Imaging_Exp_info.npy'),
                       allow_pickle=True).item()
    ...
def get_session_day(db):
    """Extract day of training from session metadata."""
    for key in ['days', 'sess#']:
        if key in db:
            return int(db[key])
    return 0
```

**What this does:** `input[1]` is named `day_of_training` and is read from the `days` or `sess#` field of each session's db entry in `beh/Imaging_Exp_info.npy`; if neither key is present the value is 0. Session dates (`datexp`) are not used. Verification reports the resulting range as `day_of_training: [0.0, 15.0]` with most sessions at 0 or 1 (verification_full_out.txt:34, input dim 1 per-session ranges).

**Rating:** incorrect

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Day of training**: Use sess# or days field from exp_info if available; otherwise use session chronological order within subject." (CONVERSION_NOTES.md:195)

**Code** (convert_data.py:118-123, 207-208, 237-242):
```python
def get_session_day(db):
    for key in ['days', 'sess#']:
        if key in db:
            return int(db[key])
    return 0
    ...
    # Day of training
    day = np.float32(get_session_day(db))
    ...
        inp = np.stack([
            time_to_sound,
            np.full(n_frames, day, dtype=np.float32),
            ...
        ], axis=0)
```

**What this does:** The metadata field is cast to `int` then `np.float32` once per session and broadcast with `np.full` across all timepoints of every trial in that session as input row 1. No date arithmetic or per-mouse ordering is performed; the documented chronological-order fallback is not implemented in code (missing keys return 0).

**Rating:** incorrect

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Time since StartFr | input[2]: time_since_trial_start | (current_frame - StartFr) / fs | Continuous, starts at 0 |" (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:176, 202-205, 216-222):
```python
    StartFr = beh['StartFr'].astype(int)
    ...
    ft = beh['ft']
    dt = np.median(np.diff(ft[:min(1000, len(ft))])) * 86400  # days->seconds
    fs = 1.0 / dt if dt > 0 else FRAME_RATE
    ...
    for i in range(ntrials):
        # Trial frames: StartFr[i] to StartFr[i+1] or end
        start = StartFr[i]
        end = StartFr[i + 1] if i < ntrials - 1 else nfr_use
```

**What this does:** `input[2]` is named `time_since_trial_start` and is derived from `beh['StartFr']` (which sets the trial window start) together with the per-session sampling rate `fs` computed from the `beh['ft']` timestamps.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Time since StartFr | input[2]: time_since_trial_start | (current_frame - StartFr) / fs | Continuous, starts at 0 |" (CONVERSION_NOTES.md:178)

**Code** (convert_data.py:237-242):
```python
        inp = np.stack([
            time_to_sound,
            np.full(n_frames, day, dtype=np.float32),
            (np.arange(n_frames) / fs).astype(np.float32),
            np.full(n_frames, float(isRew[i]), dtype=np.float32),
        ], axis=0)
```

**What this does:** A within-trial counter `np.arange(n_frames)` is divided by the session sampling rate `fs`, giving a float32 ramp in seconds that starts at 0.0 on the trial's first frame and increases by `1/fs` per frame. It is placed as row 2 of the input array. Because the trial window runs to the next `StartFr`, the ramp covers corridor plus grey-space frames (verification reports a max of 1768.1 s for one session; verification_full_out.txt:35).

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "'temporal_alignment_event': 'corridor entry (trial start)', 'off_start': 0.0, 'off_end': None" (convert_data.py:355-357)

**Code** (convert_data.py:167-168, 218-227, 240):
```python
    nfr_use = min(nfr, len(beh['ft']))
    spk = spk[:, :nfr_use]
    ...
        start = StartFr[i]
        end = StartFr[i + 1] if i < ntrials - 1 else nfr_use
        start = max(0, start)
        end = min(nfr_use, end)
        n_frames = end - start
        if n_frames < 2:
            continue

        # Neural: (n_neurons, n_timepoints), already float16
        trial_spk = spk[:, start:end].copy()
        ...
            (np.arange(n_frames) / fs).astype(np.float32),
```

**What this does:** The ramp has the same length `n_frames = end - start` as the neural slice `spk[:, start:end]`, so its 0.0 value coincides with the first neural frame of the trial (`StartFr[i]`) and each step corresponds to one neural frame.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| isRew | input[3]: reward_availability | Binary 0/1 | Per-trial scalar |" (CONVERSION_NOTES.md:179)
> "`isRew`: boolean reward trial indicator" (CONVERSION_NOTES.md:101)
> "`RewardFr`: frame of reward delivery (NaN if no reward)" (CONVERSION_NOTES.md:99)

**Code** (convert_data.py:175-179):
```python
    # Per-trial arrays
    StartFr = beh['StartFr'].astype(int)
    SoundFr = beh['SoundFr']
    WallName = beh['WallName']
    isRew = beh['isRew']
```

**What this does:** `input[3]` is named `reward_availability` and comes from the per-trial behavior field `beh['isRew']`, indexed by trial. `RewardFr` is described in the notes but is not read by the conversion code.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| isRew | input[3]: reward_availability | Binary 0/1 | Per-trial scalar |" (CONVERSION_NOTES.md:179)
> "| Reward fraction | Session 0: ~36% rewarded, Session 1: 0% (unsupervised) |" (CONVERSION_NOTES.md:240)

**Code** (convert_data.py:237-242):
```python
        inp = np.stack([
            time_to_sound,
            np.full(n_frames, day, dtype=np.float32),
            (np.arange(n_frames) / fs).astype(np.float32),
            np.full(n_frames, float(isRew[i]), dtype=np.float32),
        ], axis=0)
```

**What this does:** The trial's `isRew` entry is cast with `float()` and broadcast by `np.full` across all `n_trial_frames` timepoints as row 3 of the input array, so the value is constant within a trial. Verification reports the range as `reward_availability: [0.0, 1.0]`, with entire sessions constant at 0 (verification_full_out.txt:36).

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "WallName → output[0]: visual_stimulus, Categorical encoding, Per-trial" (line 180). 8 categories (line 290).

**Code** (convert_data.py:178, 245):
```python
WallName = beh['WallName']
...
stim = standardize_stim_name(str(WallName[i]))
```

**What this does:** Derived from the per-trial `WallName` array in behavior data, which gives the stimulus identifier shown in that trial's corridor.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Stimulus name standardization (rock→circle, wood→leaf, brick→circle/leaf3)" (line 215). 8 final categories (line 306).

**Code** (convert_data.py:37-48, 126-128, 245-251, 324-329):
```python
STIM_CATEGORY_MAP = {
    'circle1': 'circle1', ...
    'rock1': 'circle1', 'rock2': 'circle2',
    'wood1': 'leaf1', ...
}
def standardize_stim_name(name):
    return STIM_CATEGORY_MAP.get(name, name)
...
stim = standardize_stim_name(str(WallName[i]))
out = np.stack([np.full(n_frames, 0, dtype=np.int64), ...])
...
all_stim_sorted = sorted(all_stim_names)
stim_to_idx = {s: i for i, s in enumerate(all_stim_sorted)}
for si in range(len(output_all)):
    for ti in range(len(output_all[si])):
        output_all[si][ti][0, :] = stim_to_idx[all_stim_per_session[si][ti]]
```

**What this does:** Wall names are normalized via `STIM_CATEGORY_MAP` (e.g. rock→circle, wood→leaf). Standardized names are sorted globally and assigned integer indices. Each trial's stim index is broadcast to all frames in that trial.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "LickFr/LickTrind → output[1]: licking, Binary per frame, Time-varying" (line 181).

**Code** (convert_data.py:184-187):
```python
if 'LickFr' in beh and len(beh['LickFr']) > 0:
    lick_fr = beh['LickFr'].astype(int)
    valid_lick = (lick_fr >= 0) & (lick_fr < nfr_use)
    lick_binary[lick_fr[valid_lick]] = 1
```

**What this does:** Derived from `beh['LickFr']` — the array of frame indices at which licks occurred.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *licking*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Licking: Binary per frame - check if any lick occurred in that frame's time window." (line 193)

**Code** (convert_data.py:182-187, 248):
```python
lick_binary = np.zeros(nfr_use, dtype=np.int64)
if 'LickFr' in beh and len(beh['LickFr']) > 0:
    lick_fr = beh['LickFr'].astype(int)
    valid_lick = (lick_fr >= 0) & (lick_fr < nfr_use)
    lick_binary[lick_fr[valid_lick]] = 1
...
lick_binary[start:end],
```

**What this does:** Builds a length-`nfr_use` binary vector with 1 at each frame containing a lick event. Frames out of range filtered out. No smoothing or counting (multiple licks → still 1).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Time-varying" per frame (line 181).

**Code** (convert_data.py:248):
```python
out = np.stack([
    np.full(n_frames, 0, dtype=np.int64),
    lick_binary[start:end],
    ...
], axis=0)
```

**What this does:** The session-wide `lick_binary` is sliced to `[start:end]` matching each trial's neural slice. Frame i of `output[1]` corresponds to frame i of `neural`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "ft_Pos → output[2]: position_bin, Discretize 0-4m into 4 bins... Time-varying, use 4+1 bins (add gray space bin)" (line 182).

**Code** (convert_data.py:171-172):
```python
ft_Pos = beh['ft_Pos'][:nfr_use]
ft_CorrSpc = beh['ft_CorrSpc'][:nfr_use].astype(bool)
```

**What this does:** Derived from `beh['ft_Pos']` (per-frame corridor position 0–60 dm) and `beh['ft_CorrSpc']` (boolean: in texture corridor vs gray space).

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Position binning: 4 bins in texture area (0-10dm,...,30-40dm) + 1 bin for gray space" (line 191).

**Code** (convert_data.py:189-194):
```python
pos_bins = np.full(nfr_use, 4, dtype=np.int64)  # default: gray
for b in range(4):
    mask = ft_CorrSpc & (ft_Pos >= b * 10) & (ft_Pos < (b + 1) * 10)
    pos_bins[mask] = b
pos_bins[ft_CorrSpc & (ft_Pos >= 40)] = 3  # edge case
```

**What this does:** All frames default to bin 4 (gray). For frames in the corridor, position is bucketed into 4 equal bins covering 0–40 dm (1 m each). Edge case: frames in corridor with position ≥ 40 dm assigned to last texture bin.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Time-varying" per frame (line 182).

**Code** (convert_data.py:249):
```python
out = np.stack([
    ...
    pos_bins[start:end],
    ...
], axis=0)
```

**What this does:** Per-frame `pos_bins` is sliced `[start:end]` per trial; same frame indexing as neural.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "ft_RunSpeed → output[3]: running_speed_bin, Quartile discretization across all frames, Time-varying" (line 183).

**Code** (convert_data.py:142, 173):
```python
speeds = beh['ft_RunSpeed']
...
ft_RunSpeed = beh['ft_RunSpeed'][:nfr_use]
```

**What this does:** Derived from `beh['ft_RunSpeed']` — per-frame VR running speed values.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Running speed: Discretize into 4 quartile bins computed across ALL running frames in the dataset." (line 192). "Speed quartile Q1 contains 47.1% of frames... since quartiles computed on positive speeds only." (line 308)

**Code** (convert_data.py:135-147, 196-200):
```python
def collect_speed_quartiles(session_map, keys):
    all_speeds = []
    for spk_key in keys:
        info = session_map[spk_key]
        beh = load_beh(info)
        speeds = beh['ft_RunSpeed']
        all_speeds.append(speeds)
    all_speeds = np.concatenate(all_speeds)
    valid = all_speeds > 0
    ...
    return np.percentile(all_speeds[valid], [25, 50, 75])
...
speed_bins = np.zeros(nfr_use, dtype=np.int64)
speed_bins[ft_RunSpeed >= speed_quartiles[0]] = 1
speed_bins[ft_RunSpeed >= speed_quartiles[1]] = 2
speed_bins[ft_RunSpeed >= speed_quartiles[2]] = 3
```

**What this does:** Speed thresholds are 25/50/75 percentiles of positive speeds aggregated across all sessions. Each frame's speed is bucketed via cumulative threshold comparison into 4 bins (Q1..Q4).

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 10-d. How is `output` *running_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Time-varying" per frame (line 183).

**Code** (convert_data.py:250):
```python
out = np.stack([
    ...
    speed_bins[start:end],
], axis=0)
```

**What this does:** Per-frame `speed_bins` sliced to `[start:end]` for each trial; identical frame indexing as neural.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "RewardFr: frame of reward delivery (NaN if no reward)" (line 99). Sample sanity checks include trial count and position range (lines 198-203).

**Code** (convert_data.py:118-123, 167, 184-187, 220-224, 232-235, 258-260):
```python
def get_session_day(db):
    for key in ['days', 'sess#']:
        if key in db:
            return int(db[key])
    return 0
...
nfr_use = min(nfr, len(beh['ft']))
...
if 'LickFr' in beh and len(beh['LickFr']) > 0:
    lick_fr = beh['LickFr'].astype(int)
    valid_lick = (lick_fr >= 0) & (lick_fr < nfr_use)
...
start = max(0, start); end = min(nfr_use, end)
if n_frames < 2: continue
...
if np.isnan(sound_fr):
    time_to_sound = np.zeros(n_frames, dtype=np.float32)
...
if len(neural_trials) < 2:
    print(f"WARNING: <2 valid trials for {spk_key}")
    return None
```

**What this does:** Truncates to `min(nfr, len(ft))` to handle length mismatches. Clamps trial bounds. Filters out lick frames out of range. NaN `SoundFr` zeros out time-to-sound. Missing `days`/`sess#` defaults to 0. Empty stim map returns name unchanged. Sessions with <2 trials are skipped with warning.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Neural loading+filtering ~15-25s/session, ~1600s total; Processing ~5s/session, ~450s; Total ~21 minutes" (lines 251-256).

**Code** (convert_data.py:55-70, 161, 300-322, 376-380):
```python
def load_spk_filtered(...):
    spk_data = np.load(..., allow_pickle=True).item()
    ...
spk = load_spk_filtered(mname, datexp, blk, valid_mask)
...
for idx, spk_key in enumerate(keys):
    result = process_session(spk_key, info, speed_quartiles)
...
with open(output_file, 'wb') as f:
    pickle.dump(data, f, protocol=4)
    f.flush(); os.fsync(f.fileno())
```

**What this does:** Per-session neural file `.npy` loading (multi-GB) dominates per CONVERSION_NOTES; pickling the ~177 GB output file is also large. Per-trial slicing/copying inside the trial loop adds overhead.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none specific to vectorization)

**Code** (convert_data.py:84-88, 191-194, 216-256, 327-329):
```python
valid_mask = np.array([int(ia) not in EXCLUDED_AREAS for ia in iarea])
region_idx = np.array([
    BRAIN_REGIONS.index(AREA_MAP.get(int(ia), 'V1'))
    for ia in iarea[valid_mask]
], dtype=np.int64)
...
for b in range(4):
    mask = ft_CorrSpc & (ft_Pos >= b * 10) & (ft_Pos < (b + 1) * 10)
    pos_bins[mask] = b
...
for i in range(ntrials):
    ...
for si in range(len(output_all)):
    for ti in range(len(output_all[si])):
        output_all[si][ti][0, :] = stim_to_idx[...]
```

**What this does:** Python list comprehensions over `iarea` could be replaced with numpy `np.isin`. Position binning loop could use `np.digitize`. Per-trial slicing loop could be partially vectorized via `np.split` on `StartFr`. Stim index assignment loop could batch-fill arrays.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Speed quartile collection from behavior only (no neural data loading)" (line 224) — done as a separate first pass.

**Code** (convert_data.py:135-147, 165):
```python
def collect_speed_quartiles(session_map, keys):
    for spk_key in keys:
        info = session_map[spk_key]
        beh = load_beh(info)
        speeds = beh['ft_RunSpeed']
        ...
...
beh = load_beh(session_info)  # in process_session, called again per session
```

**What this does:** Behavior file (`Beh_{exp_type}.npy`) is loaded twice per session — once to gather speeds for quartile thresholds, once again inside `process_session`. No caching between passes.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> "processing visualization plots" produced (line 218); decoder uses random projection to 2000 dims → SVD to 100 PCs (line 321).

**Code** (convert_data.py:118-123, 384-385, 390-468):
```python
def get_session_day(db):
    for key in ['days', 'sess#']:
        if key in db:
            return int(db[key])
    return 0
...
if show_processing:
    plot_processing(data)
...
def plot_processing(data):
    ...  # generates per-session matplotlib figures
```

**What this does:** `plot_processing` generates verification PNGs not consumed downstream. Computing per-session `fs` from frame times (and the full `time_to_sound`/`time_since_trial_start` float32 arrays) yields fields not used by the decoder. Day-of-training is per-trial broadcast even though it is constant per session.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Filter neurons per-plane before concatenation (saves memory and time)" / "Store neural data as float16 (halves file size)" (lines 222-223). Subsampling for decoder (line 321).

**Code** (convert_data.py:55-70, 156-162, 227, 376-380):
```python
def load_spk_filtered(mname, datexp, blk, valid_mask):
    ...
    for plane in planes:
        ...
        filtered.append(plane[plane_mask].astype(np.float16))
    return np.concatenate(filtered, 0)
...
iarea = load_retino(mname, datexp)
valid_mask, region_idx = get_brain_region_idx(iarea)
spk = load_spk_filtered(mname, datexp, blk, valid_mask)
...
trial_spk = spk[:, start:end].copy()  # copy to avoid referencing large array
...
pickle.dump(data, f, protocol=4)
```

**What this does:** Retinotopy is loaded first to build a valid mask before loading the large neural array. Per-plane filtering happens before concatenation to avoid a large intermediate array. Neural data stored as float16. Per-trial copies break references to the full session array allowing GC.

**Rating:** match

**Note:** _(no note)_---

---
