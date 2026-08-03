# mouseland — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/mouseland/claude-code/2026-03-23__15-22-50_trial1/verifier/snapshot/`

Outputs identified (K=4): visual_stimulus, licking, position, running_speed

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural (spk/): `{mouse}_{date}_{block}_neural_data.npy` - dict with 'spks' key containing list of arrays per imaging plane ... Behavior (beh/): `Beh_{exp_type}.npy` - dict with session keys mapping to full behavior dicts ... Retinotopy: `{mouse}_{date}_trans.npz`" (CONVERSION_NOTES.md:77-79)

**Code** (convert_data.py:436-471):
```python
session_map = get_unique_sessions()
print(f"Found {len(session_map)} unique sessions")
...
for sess_key, (exp_type, ndb) in sorted(session_map.items()):
    t0 = time.time()
    result = process_session(
        sess_key, exp_type, ndb,
        day_of_training=day_map[sess_key],
        speed_quartiles=speed_quartiles,
        show_processing=show_processing
    )
    session_results.append(result)
```

**What this does:** Builds a unique session list from `Imaging_Exp_info.npy`, then iterates session-by-session, calling `process_session` which loads neural spikes (`load_spk`), behavior (`load_behavior_for_session`), and retinotopy (`load_retino`) per session.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Subjects identified (19): DR10, DR15, LZ13, LZ16, TX104, ..." (CONVERSION_NOTES.md:26)

**Code** (convert_data.py:491-509):
```python
all_subjects = sorted(set(r['subject'] for r in session_results))
subject_to_idx = {s: i for i, s in enumerate(all_subjects)}
...
for result in session_results:
    neural_all.append(result['neural'])
    input_all.append(result['input'])
    output_all.append(result['output'])
    subject_idx.append(subject_to_idx[result['subject']])
    brain_region_idx.append(result['region_idx'])
```

**What this does:** Each session's `mname` (mouse name) is recorded as `subject`; subjects are assembled into a sorted list and a per-session `subject_idx` integer points each session to its subject.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Each physical session used once: For sessions in multiple exp types, use the first available behavior data" (CONVERSION_NOTES.md:171)

**Code** (convert_data.py:66-82):
```python
def get_unique_sessions():
    """Build list of unique sessions with metadata from exp_info."""
    exp_info = np.load(
        os.path.join(DATA_ROOT, 'beh', 'Imaging_Exp_info.npy'),
        allow_pickle=True
    ).item()
    session_map = {}
    for exp_type in exp_info:
        for ndb in exp_info[exp_type]:
            key = f"{ndb['mname']}_{ndb['datexp']}_{ndb['blk']}"
            if key not in session_map:
                session_map[key] = (exp_type, ndb)
    return session_map
```

**What this does:** Sessions are uniquely identified by `mname_datexp_blk`. Walks all 23 experiment-type entries; on first occurrence of a session key, records its (exp_type, db_entry); subsequent duplicates are skipped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial window: StartFr to GrayFr (corridor entry to grey space entry) - captures full textured corridor portion" (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:206-242):
```python
ntrials = beh['ntrials']
start_frs = np.round(beh['StartFr']).astype(int)
gray_frs = np.round(beh['GrayFr']).astype(int)
...
for trial_idx in range(ntrials):
    sfr = start_frs[trial_idx]
    gfr = gray_frs[trial_idx]
    if sfr < 0 or gfr > n_frames or sfr >= gfr:
        skipped += 1
        continue
    n_trial_frames = gfr - sfr
    if n_trial_frames < 2:
        skipped += 1
        continue
    trial_neural = spk[:, sfr:gfr].astype(np.float16)
```

**What this does:** Trials use `StartFr` (corridor entry) to `GrayFr` (grey-space entry) as the temporal window per trial; rounded to integer frame indices and used as slices into all per-frame arrays.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial curation rules: None mentioned. All trials used." (CONVERSION_NOTES.md:125); "1 trial skipped (TX83_2022_08_31_1: invalid frame range)" (CONVERSION_NOTES.md:280)

**Code** (convert_data.py:231-239):
```python
if sfr < 0 or gfr > n_frames or sfr >= gfr:
    skipped += 1
    continue

n_trial_frames = gfr - sfr
if n_trial_frames < 2:
    skipped += 1
    continue
```

**What this does:** No quality-based trial filtering. Trials are only skipped if their start/end frame indices are invalid (out of range, reversed, or shorter than 2 frames).

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural data is loaded via `load_spk()`: concatenates `spks` list across imaging planes ... spks are deconvolved fluorescence traces from Suite2p" (CONVERSION_NOTES.md:49-50)

**Code** (convert_data.py:49-56):
```python
def load_spk(mname, datexp, blk, root=''):
    """Load neural data, concatenating across planes. Matches reference code."""
    fn = f'{mname}_{datexp}_{blk}_neural_data.npy'
    spk_path = os.path.join(root, fn)
    spk = np.concatenate(
        [nspk for nspk in np.load(spk_path, allow_pickle=True).item()['spks']], 0
    )
    return spk
```

**What this does:** The `neural` data is the `spks` field (deconvolved Suite2p spike traces) from each session's `{mname}_{datexp}_{blk}_neural_data.npy`, concatenated across the per-plane list of arrays.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural data stored as float16 to reduce file size ... Uses reference code's `load_spk` approach (concatenate across planes)" (CONVERSION_NOTES.md:194-195)

**Code** (convert_data.py:182-242):
```python
spk = load_spk(mname, datexp, blk, root=os.path.join(DATA_ROOT, 'spk'))
n_neurons, n_frames_neural = spk.shape
...
n_frames = min(n_frames_neural, n_frames_beh)
...
trial_neural = spk[:, sfr:gfr].astype(np.float16)
```

**What this does:** Spikes from all imaging planes are concatenated along the neuron axis, truncated to the shorter of neural/behavior frame counts, sliced per trial by `[StartFr:GrayFr]`, and cast to `float16`. No additional filtering, normalization, or smoothing.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "No neuron filtering/curation in the reference code - all Suite2p-detected neurons used" (CONVERSION_NOTES.md:51); "All neurons included: No filtering, consistent with reference code" (CONVERSION_NOTES.md:169)

**Code** (convert_data.py:198-204):
```python
iarea = load_retino(mname, datexp, root=os.path.join(DATA_ROOT, 'retinotopy'))
region_idx = iarea_to_region_idx(iarea)

# Verify neuron count matches
assert len(region_idx) == n_neurons, \
    f"Retinotopy ({len(region_idx)}) != neural ({n_neurons}) for {session_key}"
```

**What this does:** No neuron-level QC filtering. All Suite2p-detected neurons are kept; only a region label (V1/mHV/lHV/aHV/other) is attached via the retinotopy `iarea` array.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "'temporal_alignment_event': 'Trial start (corridor entry)', 'off_start': 0.0" (convert_data.py:547-548); "Trial window: StartFr to GrayFr" (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:228-242, 544-549):
```python
sfr = start_frs[trial_idx]
gfr = gray_frs[trial_idx]
...
trial_neural = spk[:, sfr:gfr].astype(np.float16)
...
'temporal_alignment_event': 'Trial start (corridor entry)',
'off_start': 0.0,  # alignment is at corridor entry
'off_end': None,  # variable trial length
```

**What this does:** Each trial's neural slice begins at `StartFr` (corridor entry) and ends at `GrayFr` (grey-space entry); thus frame 0 of each trial is aligned to corridor entry. Trial lengths are variable.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Frame rate: ~3.17 Hz (dt ≈ 0.315 s per frame)" (CONVERSION_NOTES.md:80); "Time bin: 314.7 ms" (CONVERSION_NOTES.md:269)

**Code** (convert_data.py:190-193, 242):
```python
ft = beh['ft']
dt_days = np.nanmedian(np.diff(ft))
dt_sec = dt_days * 24 * 3600  # convert days to seconds
...
trial_neural = spk[:, sfr:gfr].astype(np.float16)
```

**What this does:** No resampling or rebinning is performed. Native imaging frames (~3.17 Hz, ~315 ms) are kept as-is; `dt_sec` is computed from behavior timestamps and reported in metadata.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| SoundFr - frame_idx | input[0]: time_to_sound_cue | (SoundFr - frame_idx) * dt_sec | Continuous, time-varying, positive before cue |" (CONVERSION_NOTES.md:157)
> "| Sound cue | SoundPos, SoundFr | SoundPos uniform ~5-35 | 0.5-3.5 m range | 5-35 dm = 0.5-3.5m, consistent |" (CONVERSION_NOTES.md:143)

**Code** (convert_data.py:190-193, 208-211):
```python
    # Compute actual frame duration from timestamps
    ft = beh['ft']
    dt_days = np.nanmedian(np.diff(ft))
    dt_sec = dt_days * 24 * 3600  # convert days to seconds
    ...
    # Get frame indices for each trial
    start_frs = np.round(beh['StartFr']).astype(int)
    gray_frs = np.round(beh['GrayFr']).astype(int)
    sound_frs = beh['SoundFr']  # keep as float for precise time computation
```

**What this does:** `input[0]` is named `time_to_sound_cue` and is built from the behavior field `beh['SoundFr']` (sound-cue frame index per trial), the trial's frame indices derived from `beh['StartFr']`/`beh['GrayFr']`, and the per-session frame duration `dt_sec` computed from the `beh['ft']` frame timestamps.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| SoundFr - frame_idx | input[0]: time_to_sound_cue | (SoundFr - frame_idx) * dt_sec | Continuous, time-varying, positive before cue |" (CONVERSION_NOTES.md:157)
> "**Frame alignment**: Round fractional frame indices (StartFr, GrayFr, SoundFr) to nearest integer" (CONVERSION_NOTES.md:168)

**Code** (convert_data.py:244-247, 262-267):
```python
        # === INPUTS ===
        # Time to sound cue (positive before cue, negative after)
        frame_indices = np.arange(sfr, gfr, dtype=np.float64)
        time_to_sound = (sound_frs[trial_idx] - frame_indices) * dt_sec
        ...
        trial_input = np.stack([
            time_to_sound.astype(np.float32),
            np.full(n_trial_frames, day_val, dtype=np.float32),
            time_since_start.astype(np.float32),
            np.full(n_trial_frames, rew_val, dtype=np.float32),
        ], axis=0)  # shape: (4, n_timepoints)
```

**What this does:** For each trial, the frame indices spanning `StartFr` to `GrayFr` are subtracted from that trial's (unrounded, float) `SoundFr` and multiplied by `dt_sec`, giving a continuous per-frame value in seconds that is positive before the cue and negative after. It is cast to float32 and stacked as row 0 of the `(4, n_timepoints)` input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Trial window**: StartFr to GrayFr (corridor entry to grey space entry) - captures full textured corridor portion" (CONVERSION_NOTES.md:167)

**Code** (convert_data.py:236-247):
```python
        n_trial_frames = gfr - sfr
        if n_trial_frames < 2:
            skipped += 1
            continue

        # Neural data: (n_neurons, n_timepoints)
        trial_neural = spk[:, sfr:gfr].astype(np.float16)

        # === INPUTS ===
        # Time to sound cue (positive before cue, negative after)
        frame_indices = np.arange(sfr, gfr, dtype=np.float64)
        time_to_sound = (sound_frs[trial_idx] - frame_indices) * dt_sec
```

**What this does:** The input uses the same session frame indices `sfr:gfr` used to slice the neural array `spk[:, sfr:gfr]`, so element *i* of `time_to_sound` corresponds to neural frame `sfr + i`; both have length `gfr - sfr`. No additional lag or resampling is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| date difference | input[1]: day_of_training | Days since mouse's first recording | Continuous, per-trial |" (CONVERSION_NOTES.md:158)
> "**Day of training**: Calendar day difference from mouse's first recording date" (CONVERSION_NOTES.md:176)

**Code** (convert_data.py:66-82, 108-113):
```python
def get_unique_sessions():
    """Build list of unique sessions with metadata from exp_info."""
    exp_info = np.load(
        os.path.join(DATA_ROOT, 'beh', 'Imaging_Exp_info.npy'), allow_pickle=True
    ).item()
    ...
    for sess_key, (exp_type, ndb) in session_map.items():
        mname = ndb['mname']
        datexp = ndb['datexp']
        # Parse date
        date = datetime.strptime(datexp, '%Y_%m_%d')
        mouse_sessions[mname].append((sess_key, date))
```

**What this does:** `input[1]` is named `day_of_training` and is derived from the `mname` (mouse name) and `datexp` (session date string) fields of the session entries in `beh/Imaging_Exp_info.npy`; no separate training-day field in the raw data is used.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| date difference | input[1]: day_of_training | Days since mouse's first recording | Continuous, per-trial |" (CONVERSION_NOTES.md:158)

**Code** (convert_data.py:115-123, 249-250, 264):
```python
    # Compute day offset from first session per mouse
    day_map = {}
    for mname, sessions in mouse_sessions.items():
        sessions.sort(key=lambda x: x[1])
        first_date = sessions[0][1]
        for sess_key, date in sessions:
            day_map[sess_key] = (date - first_date).days
    return day_map
    ...
        # Day of training (scalar, broadcast to per-trial)
        day_val = np.float32(day_of_training)
        ...
            np.full(n_trial_frames, day_val, dtype=np.float32),
```

**What this does:** Sessions are grouped by mouse, dates parsed from `datexp` with `'%Y_%m_%d'`, sorted, and each session gets the calendar-day difference from that mouse's earliest session (first session = 0). The day map is computed over the full session list (`all_session_map`) even in sample mode, and the resulting scalar is broadcast across all timepoints of every trial in that session as input row 1.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| frame_idx - StartFr | input[2]: time_since_trial_start | (frame_idx - StartFr) * dt_sec | Continuous, time-varying |" (CONVERSION_NOTES.md:159)

**Code** (convert_data.py:188-193, 208-210):
```python
    n_frames_beh = len(beh['ft'])

    # Compute actual frame duration from timestamps
    ft = beh['ft']
    dt_days = np.nanmedian(np.diff(ft))
    dt_sec = dt_days * 24 * 3600  # convert days to seconds
    ...
    # Get frame indices for each trial
    start_frs = np.round(beh['StartFr']).astype(int)
    gray_frs = np.round(beh['GrayFr']).astype(int)
```

**What this does:** `input[2]` is named `time_since_trial_start` and is derived from `beh['StartFr']` (trial-start frame, corridor entry), the within-trial frame index, and the per-session frame duration `dt_sec` computed from `beh['ft']` timestamps.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| frame_idx - StartFr | input[2]: time_since_trial_start | (frame_idx - StartFr) * dt_sec | Continuous, time-varying |" (CONVERSION_NOTES.md:159)

**Code** (convert_data.py:246, 252-253, 262-267):
```python
        frame_indices = np.arange(sfr, gfr, dtype=np.float64)
        ...
        # Time since trial start
        time_since_start = (frame_indices - sfr) * dt_sec
        ...
        trial_input = np.stack([
            time_to_sound.astype(np.float32),
            np.full(n_trial_frames, day_val, dtype=np.float32),
            time_since_start.astype(np.float32),
            np.full(n_trial_frames, rew_val, dtype=np.float32),
        ], axis=0)  # shape: (4, n_timepoints)
```

**What this does:** The rounded trial-start frame `sfr` is subtracted from the trial's frame indices and multiplied by the session frame duration `dt_sec`, yielding a ramp in seconds starting at 0.0 on the first frame of the trial. It is cast to float32 and placed as row 2 of the input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "**Trial window**: StartFr to GrayFr (corridor entry to grey space entry) - captures full textured corridor portion" (CONVERSION_NOTES.md:167)
> "'temporal_alignment_event': 'Trial start (corridor entry)'" (convert_data.py:547, mirrored in notes)

**Code** (convert_data.py:242-253):
```python
        # Neural data: (n_neurons, n_timepoints)
        trial_neural = spk[:, sfr:gfr].astype(np.float16)

        # === INPUTS ===
        # Time to sound cue (positive before cue, negative after)
        frame_indices = np.arange(sfr, gfr, dtype=np.float64)
        time_to_sound = (sound_frs[trial_idx] - frame_indices) * dt_sec
        ...
        # Time since trial start
        time_since_start = (frame_indices - sfr) * dt_sec
```

**What this does:** `time_since_start` is defined on the same `sfr:gfr` frame range used to slice `spk`, so its value 0.0 falls on the first neural frame of the trial and each subsequent entry advances by one neural frame (`dt_sec`). Lengths match at `gfr - sfr`.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| isRew | input[3]: reward_availability | 1 if rewarded corridor, 0 otherwise | Discrete, per-trial |" (CONVERSION_NOTES.md:160)
> "Key behavior variables: ft_trInd, ft_CorrSpc, ft_GraySpc, ft_move, ft_Pos, ft_PosCum, StartFr, GrayFr, SoundFr, LickFr, WallName, isRew" (CONVERSION_NOTES.md:55)

**Code** (convert_data.py:218-219, 255-256):
```python
    # Collect all stimulus names across sessions for consistent encoding
    wall_names = beh['WallName']
    is_rew = beh['isRew']
    ...
        # Reward availability
        rew_val = np.float32(1.0 if is_rew[trial_idx] else 0.0)
```

**What this does:** `input[3]` is named `reward_availability` and comes from the per-trial behavior field `beh['isRew']`, indexed by trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| isRew | input[3]: reward_availability | 1 if rewarded corridor, 0 otherwise | Discrete, per-trial |" (CONVERSION_NOTES.md:160)

**Code** (convert_data.py:255-267):
```python
        # Reward availability
        rew_val = np.float32(1.0 if is_rew[trial_idx] else 0.0)

        # Stack inputs: (4, n_timepoints) for time-varying, or (4,) for mixed
        # time_to_sound and time_since_start are time-varying
        # day_of_training and reward_availability are per-trial (scalar)
        # Use (4, n_timepoints) with broadcast for per-trial values
        trial_input = np.stack([
            time_to_sound.astype(np.float32),
            np.full(n_trial_frames, day_val, dtype=np.float32),
            time_since_start.astype(np.float32),
            np.full(n_trial_frames, rew_val, dtype=np.float32),
        ], axis=0)  # shape: (4, n_timepoints)
```

**What this does:** The trial's `isRew` flag is cast to a float32 1.0/0.0 scalar and broadcast with `np.full` across all `n_trial_frames` timepoints as row 3 of the input array; the value is constant within a trial (no time-varying reward-zone window).

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "WallName | output[0]: visual_stimulus | Map to category index | Per-trial categorical" (CONVERSION_NOTES.md:162)

**Code** (convert_data.py:219, 271, 345-355):
```python
wall_names = beh['WallName']
...
stim_name = wall_names[trial_idx]
...
def build_stimulus_mapping(session_results):
    all_stim_names = set()
    for result in session_results:
        for (_, stim_name) in result['output']:
            all_stim_names.add(stim_name)
    stim_names = sorted(all_stim_names)
    stim_to_idx = {name: idx for idx, name in enumerate(stim_names)}
    return stim_names, stim_to_idx
```

**What this does:** Derived from per-trial `WallName` strings in the behavior dict (e.g., `circle1`, `leaf1`, `leaf1_swap1`).

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Stimulus categories from WallName (not stim_id)" (CONVERSION_NOTES.md:298); "Stimulus categories: leaf/circle/rock/brick ... 15 unique" (CONVERSION_NOTES.md:271)

**Code** (convert_data.py:476-484):
```python
stim_names, stim_to_idx = build_stimulus_mapping(session_results)
print(f"\nStimulus categories ({len(stim_names)}): {stim_names}")

# Fill in stimulus indices in output data
for result in session_results:
    for i, (out_data, stim_name) in enumerate(result['output']):
        stim_idx = stim_to_idx[stim_name]
        out_data[0, :] = stim_idx
        result['output'][i] = out_data
```

**What this does:** Unique `WallName` values across all sessions are sorted to build a global name→index map (15 categories). Per-trial stimulus index is broadcast across all timepoints in the trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "LickFr, LickTrind | output[1]: licking | Binary per frame (any lick in frame window)" (CONVERSION_NOTES.md:163)

**Code** (convert_data.py:149-170):
```python
def build_lick_binary(beh, start_fr, end_fr):
    n_frames = end_fr - start_fr
    lick_binary = np.zeros(n_frames, dtype=np.float32)
    lick_frs = beh['LickFr']
    if len(lick_frs) == 0:
        return lick_binary
    lick_trinds = beh['LickTrind']
    lick_frs_int = np.round(lick_frs).astype(int)
    mask = (lick_frs_int >= start_fr) & (lick_frs_int < end_fr)
    if mask.any():
        frame_offsets = lick_frs_int[mask] - start_fr
        frame_offsets = np.clip(frame_offsets, 0, n_frames - 1)
        lick_binary[frame_offsets] = 1.0
    return lick_binary
```

**What this does:** Built from `beh['LickFr']` (per-lick frame indices). `LickTrind` is read but unused; trial assignment is done by frame-range filtering.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *licking*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Licking: Binary 1 at any frame that has >=1 lick (using LickFr rounded to nearest integer frame)" (CONVERSION_NOTES.md:175)

**Code** (convert_data.py:161-168, 274):
```python
lick_frs_int = np.round(lick_frs).astype(int)
mask = (lick_frs_int >= start_fr) & (lick_frs_int < end_fr)
if mask.any():
    frame_offsets = lick_frs_int[mask] - start_fr
    frame_offsets = np.clip(frame_offsets, 0, n_frames - 1)
    lick_binary[frame_offsets] = 1.0
...
lick_binary = build_lick_binary(beh, sfr, gfr)
```

**What this does:** `LickFr` (continuous lick frame timestamps) is rounded to integer frames, masked into the trial's `[StartFr, GrayFr)` window, and frames containing any lick are marked 1 (else 0).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:152, 274, 285-290):
```python
n_frames = end_fr - start_fr
lick_binary = np.zeros(n_frames, dtype=np.float32)
...
lick_binary = build_lick_binary(beh, sfr, gfr)
...
trial_output = np.stack([
    ...
    lick_binary.astype(int),
    ...
], axis=0)
```

**What this does:** `lick_binary` is built with length `gfr - sfr` (same as neural slice) and indexed by `LickFr - StartFr`, so it shares the same per-trial frame axis as the neural data.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "ft_Pos | output[2]: position | Discretize into 4 bins of 10 dm each" (CONVERSION_NOTES.md:164)

**Code** (convert_data.py:223, 277):
```python
ft_pos = beh['ft_Pos'][:n_frames]
...
trial_pos = ft_pos[sfr:gfr]
```

**What this does:** Derived from `beh['ft_Pos']`, a per-frame position-along-corridor array (decimeters).

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Position discretization: 4 equal bins of 10dm (0-40dm)" (CONVERSION_NOTES.md:293)

**Code** (convert_data.py:126-131, 277-278):
```python
def discretize_position(pos, n_bins=4):
    """Discretize position (0-40 dm) into n_bins equal 1m bins."""
    bin_edges = np.linspace(0, CORRIDOR_LENGTH_DM, n_bins + 1)
    binned = np.digitize(pos, bin_edges) - 1
    binned = np.clip(binned, 0, n_bins - 1)
    return binned.astype(int)
...
trial_pos = ft_pos[sfr:gfr]
pos_binned = discretize_position(trial_pos, POSITION_BINS).astype(np.float32)
```

**What this does:** Per-frame raw position is discretized into 4 equal-width bins spanning 0–40 dm (i.e., 0–1m, 1–2m, 2–3m, 3–4m); values outside are clipped to the end bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:223, 277-278):
```python
ft_pos = beh['ft_Pos'][:n_frames]
...
trial_pos = ft_pos[sfr:gfr]
pos_binned = discretize_position(trial_pos, POSITION_BINS).astype(np.float32)
```

**What this does:** Sliced from `ft_Pos` with the same `[sfr:gfr]` indices used for the neural data, giving identical length and frame indexing.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "ft_RunSpeed | output[3]: running_speed | Discretize into 4 quartile bins" (CONVERSION_NOTES.md:165)

**Code** (convert_data.py:224, 281, 337-338):
```python
ft_run_speed = beh['ft_RunSpeed'][:n_frames]
...
trial_speed = ft_run_speed[sfr:gfr]
...
corr_mask = beh['ft_CorrSpc'][:n_frames]
speeds = beh['ft_RunSpeed'][:n_frames]
```

**What this does:** Derived from `beh['ft_RunSpeed']` per frame; quartile edges are computed using the same variable masked by `ft_CorrSpc` (corridor frames) across all sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Running speed quartiles: Computed across ALL corridor frames in the dataset" (CONVERSION_NOTES.md:174); "Speed quartile distribution skewed (Q1=9.8%): Fixed by adding `right=True` to `np.digitize`" (CONVERSION_NOTES.md:301)

**Code** (convert_data.py:134-146, 281-282, 449-456):
```python
def compute_speed_bin_edges(all_speeds):
    valid = all_speeds[np.isfinite(all_speeds)]
    quartiles = np.percentile(valid, [25, 50, 75])
    return quartiles

def discretize_speed(speed, quartiles):
    binned = np.digitize(speed, quartiles, right=True)
    binned = np.clip(binned, 0, 3)
    return binned
...
trial_speed = ft_run_speed[sfr:gfr]
speed_binned = discretize_speed(trial_speed, speed_quartiles).astype(np.float32)
```

**What this does:** Quartile cutoffs are computed once across all corridor-frame speeds in the dataset, then per-frame speed is binned into 4 quartile categories with `right=True`.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-d. How is `output` *running_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:224, 281-282):
```python
ft_run_speed = beh['ft_RunSpeed'][:n_frames]
...
trial_speed = ft_run_speed[sfr:gfr]
speed_binned = discretize_speed(trial_speed, speed_quartiles).astype(np.float32)
```

**What this does:** Sliced from `ft_RunSpeed` with the same `[sfr:gfr]` indices used for the neural slice, sharing per-trial frame timing.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "1 trial skipped (TX83_2022_08_31_1: invalid frame range)" (CONVERSION_NOTES.md:280)

**Code** (convert_data.py:137, 188-204, 231-239):
```python
valid = all_speeds[np.isfinite(all_speeds)]
...
n_frames_beh = len(beh['ft'])
...
n_frames = min(n_frames_neural, n_frames_beh)
...
assert len(region_idx) == n_neurons, \
    f"Retinotopy ({len(region_idx)}) != neural ({n_neurons}) for {session_key}"
...
if sfr < 0 or gfr > n_frames or sfr >= gfr:
    skipped += 1
    continue
if n_trial_frames < 2:
    skipped += 1
    continue
```

**What this does:** Mismatched neural/behavior frame counts are reconciled by truncating to the minimum; non-finite speeds are dropped before quartile computation; invalid trial frame ranges are skipped with a count printed; retinotopy/neural neuron-count mismatches assert.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Process session | ~15s | ~22 min for 89 sessions ... Save pickle | 6s for 3.87 GB | ~3 min estimate ... Total estimate ~25-30 min" (CONVERSION_NOTES.md:226-230); "Total conversion time: 33.3 min" (CONVERSION_NOTES.md:260)

**Code** (convert_data.py:463-471, 587-591):
```python
for sess_key, (exp_type, ndb) in sorted(session_map.items()):
    t0 = time.time()
    result = process_session(...)
    session_results.append(result)
    gc.collect()
...
with open(output_file, 'wb') as f:
    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
file_size = os.path.getsize(output_file)
print(f"Saved {file_size / 1e9:.2f} GB in {time.time()-t0:.1f}s")
```

**What this does:** The dominant cost is the per-session loop (loading neural .npy and processing all trials), followed by pickling the ~148 GB output. A separate pass loads behavior again to compute speed quartiles.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:227-294):
```python
for trial_idx in range(ntrials):
    sfr = start_frs[trial_idx]
    gfr = gray_frs[trial_idx]
    ...
    trial_neural = spk[:, sfr:gfr].astype(np.float16)
    ...
    frame_indices = np.arange(sfr, gfr, dtype=np.float64)
    time_to_sound = (sound_frs[trial_idx] - frame_indices) * dt_sec
    ...
    lick_binary = build_lick_binary(beh, sfr, gfr)
    ...
    pos_binned = discretize_position(trial_pos, POSITION_BINS).astype(np.float32)
    ...
    speed_binned = discretize_speed(trial_speed, speed_quartiles).astype(np.float32)
```

**What this does:** Per-trial Python loop performs slicing, time-axis arithmetic, lick-binarization, and discretization one trial at a time. Position/speed discretization could have been computed once on the full session array; lick assignment could use a single histogram-style scatter.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:332-339, 446-447, 463-470):
```python
for sess_key, (exp_type, ndb) in sessions:
    beh = load_behavior_for_session(sess_key, exp_type, ndb)
    ...
    corr_mask = beh['ft_CorrSpc'][:n_frames]
    speeds = beh['ft_RunSpeed'][:n_frames]
    all_speeds.append(speeds[corr_mask])
...
all_session_map = get_unique_sessions()  # need full map for day computation
day_map = compute_day_of_training(all_session_map)
...
for sess_key, (exp_type, ndb) in sorted(session_map.items()):
    result = process_session(...)
```

**What this does:** Behavior files are loaded twice per session (once in `collect_all_corridor_speeds`, once in `process_session`). `get_unique_sessions` is also called twice. Per trial, position discretization/speed binning recompute things that could be done once per session.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:158, 285-290, 311-314):
```python
lick_trinds = beh['LickTrind']  # read but unused
...
trial_output = np.stack([
    np.full(n_trial_frames, -1, dtype=int),  # placeholder for stim, filled later
    ...
], axis=0)
...
if show_processing:
    result['beh'] = beh
    result['start_frs'] = start_frs
    result['gray_frs'] = gray_frs
```

**What this does:** `LickTrind` is loaded but never used. The visual_stimulus channel is initially filled with `-1` then overwritten in a second pass. When `show_processing` is on, the entire `beh` dict and frame arrays are kept in memory but not pickled.

**Rating:** match

**Note:** _(no note)_---

---

## Q 12-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural data stored as float16 to reduce file size" (CONVERSION_NOTES.md:194); "OOM during training ... Fixed by subsampling to 2000 neurons per session" (CONVERSION_NOTES.md:343-344)

**Code** (convert_data.py:242, 316-318, 472, 580-582):
```python
trial_neural = spk[:, sfr:gfr].astype(np.float16)
...
del spk
gc.collect()
...
gc.collect()
...
del session_results
gc.collect()
```

**What this does:** Neural arrays are downcast to `float16`; large per-session `spk` arrays are deleted after processing; explicit `gc.collect()` calls run after each session and before pickling; `session_results` is freed before pickle dump.

**Rating:** match

**Note:** _(no note)_---

---
