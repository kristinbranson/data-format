# mouseland — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/mouseland/codex/2026-03-23__15-40-42_trial2/verifier/snapshot/`

Outputs identified (K=4): visual_stimulus_category, licking, position_bin, running_speed_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Implemented deduplication from 142 analysis entries to 89 unique neural recordings." (CONVERSION_NOTES.md:281)
> "The script reuses reference loaders from `code/utils.py` for neural data loading and broad area definitions." (CONVERSION_NOTES.md:280)

**Code** (convert_data.py:121-143, 484-487):
```python
def build_session_catalog() -> list[SessionCandidate]:
    exp_info = np.load(BEH_ROOT / "Imaging_Exp_info.npy", allow_pickle=True).item()
    grouped: dict[str, list[SessionCandidate]] = defaultdict(list)
    for exp_type, db_list in exp_info.items():
        for db in db_list:
            session_id = f"{db['mname']}_{db['datexp']}_{db['blk']}"
            ...
    return [choose_canonical(grouped[sid]) for sid in sorted(grouped, key=session_sort_key)]

def load_behavior(exp_type, beh_key):
    beh = np.load(BEH_ROOT / f"Beh_{exp_type}.npy", allow_pickle=True).item()
    return beh[beh_key]
# In process_session:
beh = load_behavior(candidate.exp_type, candidate.beh_key)
spk = utils.load_spk(candidate.db, root=str(SPK_ROOT))
ret = np.load(RET_ROOT / f"{candidate.db['mname']}_{candidate.db['datexp']}_trans.npz", ...)
```

**What this does:** Builds a session catalog from `Imaging_Exp_info.npy` deduplicating to 89 canonical sessions. For each session, loads behavior dict from `Beh_<exp_type>.npy`, neural spikes via `utils.load_spk`, and retinotopy from `*_trans.npz`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sessions are deduplicated to the `89` unique imaging recordings in `Imaging_Exp_info.npy`." (README.md:28)
> "`subjects = sorted(unique mname)`; `subject_idx` indexes subject per session" (CONVERSION_NOTES.md:239)

**Code** (convert_data.py:622-624, 658-661):
```python
subjects_all = sorted({cand.db["mname"] for cand in catalog})
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects_all)}
...
"subjects": subjects_all,
"subject_idx": np.asarray(
    [subject_to_idx[s.subject] for s in processed_sessions], dtype=np.int64
),
```

**What this does:** Subjects are taken from the `mname` field of session metadata; subjects list is sorted unique mnames, and per-session `subject_idx` maps each session to its subject index.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Deduplicate 142 behavior entries down to 89 unique neural sessions: The same recording appears under multiple analysis labels in `Imaging_Exp_info.npy`. Conversion will use one canonical copy per base session ID `<mouse>_<date>_<blk>`, preferring a non-`stimtype` entry when present." (CONVERSION_NOTES.md:250)

**Code** (convert_data.py:113-138):
```python
def choose_canonical(candidates):
    def key_fn(c):
        has_stimtype = 1 if "stimtype" in c.db else 0
        return has_stimtype, c.exp_type, c.beh_key
    return sorted(candidates, key=key_fn)[0]

def build_session_catalog():
    exp_info = np.load(BEH_ROOT / "Imaging_Exp_info.npy", ...).item()
    grouped = defaultdict(list)
    for exp_type, db_list in exp_info.items():
        for db in db_list:
            session_id = f"{db['mname']}_{db['datexp']}_{db['blk']}"
            beh_key = session_id
            if "stimtype" in db:
                beh_key = f"{beh_key}_{db['stimtype']}"
            grouped[session_id].append(SessionCandidate(...))
    return [choose_canonical(grouped[sid]) for sid in sorted(grouped, key=session_sort_key)]
```

**What this does:** Sessions are uniquely identified by `<mname>_<datexp>_<blk>`. Multiple experiment-type entries for the same recording are grouped and one canonical entry chosen, yielding 89 sessions sorted by subject/date/block.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Implemented trial slicing on running-only texture frames (`StartFr:GrayFr`, `ft_move > 0`)." (CONVERSION_NOTES.md:283)
> "Use the texture segment only (`StartFr:GrayFr`): The decoder output requires exactly four 1 m position bins. Ending trials at grey-space entry also matches the paper's `0–4 m` texture-area analyses." (CONVERSION_NOTES.md:251)

**Code** (convert_data.py:307-313):
```python
for trial_idx in range(int(beh["ntrials"])):
    frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
    frames = frames[ft_move[frames] > 0]
    if frames.size == 0:
        continue
    neural = spk_sel[:, frames].astype(np.float32, copy=False)
```

**What this does:** Trials are iterated using `beh["ntrials"]`. For each trial, the frame index range is `StartFr[trial_idx]:GrayFr[trial_idx]` (corridor-entry to gray-space entry, the texture segment).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Keep running frames only inside the texture segment: This matches the reference paper/code rule that analyses use running timepoints and removes extremely long paused trials." (CONVERSION_NOTES.md:252)
> "Trials keep only running frames between corridor entry and gray-space entry." (README.md:29)

**Code** (convert_data.py:307-311):
```python
for trial_idx in range(int(beh["ntrials"])):
    frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
    frames = frames[ft_move[frames] > 0]
    if frames.size == 0:
        continue
```

**What this does:** Trials with zero retained running frames are skipped (`continue`). No other quality-control filters at the trial level; running-only frame filtering implicitly drops trials with no movement.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`spk/*_neural_data.npy` -> `['spks']` via `utils.load_spk()` -> `neural`" (CONVERSION_NOTES.md:237)
> "Neural data use the paper's deconvolved imaging traces from `data/spk`." (README.md:27)

**Code** (convert_data.py:485, 489-491):
```python
spk = utils.load_spk(candidate.db, root=str(SPK_ROOT))
...
selected_mask, selection_info = compute_neuron_selection(spk, beh, region_idx_all)
spk_sel = spk[selected_mask]
region_sel = region_idx_all[selected_mask]
```

**What this does:** Neural data come from the per-session `*_neural_data.npy` files (deconvolved fluorescence) loaded via `utils.load_spk`, with neuron rows curated by `compute_neuron_selection`. Brain region from retinotopy `iarea`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "The reference code does **not** compute delta-F-over-F inside this repository. `load_spk()` directly loads `*_neural_data.npy` and concatenates `['spks']`, so the saved neural signal is already the processed neural activity used downstream." (CONVERSION_NOTES.md:50)

**Code** (convert_data.py:489-491, 312-313):
```python
selected_mask, selection_info = compute_neuron_selection(spk, beh, region_idx_all)
spk_sel = spk[selected_mask]
...
neural = spk_sel[:, frames].astype(np.float32, copy=False)
```

**What this does:** No further transform of the deconvolved traces; processing consists of subselecting curated neurons (rows) and slicing per-trial running texture frames (columns), cast to `float32`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Curate neurons using paper-defined task relevance: Keep neurons in retinotopically assigned visual regions that are either: corridor-responsive and stimulus-selective with `|d′| >= 0.3` ... or reward-prediction neurons with `d′late_vs_early >= 0.3` on the rewarded exemplar-1 corridor." (CONVERSION_NOTES.md:253-256)

**Code** (convert_data.py:206-254):
```python
visual_mask = region_idx_all != 4
rew_primary, nonrew_primary = get_reference_pair(beh)
stim1_fr = (ft_wall == rew_primary) & corr & running
stim2_fr = (ft_wall == nonrew_primary) & corr & running
dp = safe_dprime(spk[:, stim1_fr], spk[:, stim2_fr])
stim_selective = visual_mask & np.isfinite(dp) & (np.abs(dp) >= DP_THRESHOLD)
...
reward_pred = (
    ahv_mask
    & np.isfinite(reward_dp)
    & np.isfinite(dp_sound)
    & (dp_sound > DP_THRESHOLD)
    & (reward_dp >= reward_dp_thr)  # session 95th percentile in aHV
)
selected = stim_selective | reward_pred
```

**What this does:** Restricts to visual cortex (V1/mHV/lHV/aHV); selects neurons with `|d'|>=0.3` on the primary rewarded vs non-rewarded corridor (running texture frames), unioned with aHV reward-prediction neurons (cue d'>0.3 and late-vs-early d' >= 95th percentile within aHV). Fallback top-|d'| if too few survive.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "calcium imaging frame rate is `3.17 Hz`" (CONVERSION_NOTES.md:48)
> "Use actual frame times in seconds, not just frame index: Because non-running frames are dropped, elapsed time inputs must come from `ft` timestamps rather than assuming contiguous native-frame spacing." (CONVERSION_NOTES.md:259)

**Code** (convert_data.py:285-288, 312-313):
```python
ft = np.asarray(beh["ft"][:nfr], dtype=float)
dft = np.diff(ft)
dft = dft[np.isfinite(dft) & (dft > 0)]
frame_dt = float(np.median(dft) * SECONDS_PER_DAY)
...
neural = spk_sel[:, frames].astype(np.float32, copy=False)
```

**What this does:** No resampling; the deconvolved imaging frames are kept at native frame rate. Non-running frames within texture segment are removed, but no rebinning is applied. `frame_dt` (median sampling interval) is used only to derive time inputs.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Temporal alignment: corridor entry (`StartFr`)" (README.md:21)
> "temporal_alignment_event: corridor entry (trial start / StartFr)" (convert_data.py:688)

**Code** (convert_data.py:307-316):
```python
for trial_idx in range(int(beh["ntrials"])):
    frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
    frames = frames[ft_move[frames] > 0]
    if frames.size == 0:
        continue
    neural = spk_sel[:, frames].astype(np.float32, copy=False)
    retained_idx = np.arange(frames.size, dtype=np.float32)
    cue_idx = float(np.searchsorted(frames, sound_fr[trial_idx], side="left"))
    t_since = (retained_idx * frame_dt).astype(np.float32)
```

**What this does:** Each trial begins at `StartFr` (corridor entry), ending at `GrayFr` (gray-space entry). `t=0` corresponds to corridor entry; `time_since_trial_start_sec` and `time_to_sound_cue_sec` provide alignment relative to event(s).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `input` *time_to_sound_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| `beh['SoundTime']`, `beh['ft']`, `StartFr:GrayFr` running frames | `input[0]` = `time_to_sound_cue_sec` | For each retained frame, `(SoundTime[trial] - ft[frame]) * 86400` ... |" (CONVERSION_NOTES.md:240); "- `time_to_sound_cue_sec`" (README.md:36)

**Code** (convert_data.py:285-295, 315-317):
```python
    ft = np.asarray(beh["ft"][:nfr], dtype=float)
    dft = np.diff(ft)
    dft = dft[np.isfinite(dft) & (dft > 0)]
    frame_dt = float(np.median(dft) * SECONDS_PER_DAY)
    ...
    start_fr = np.asarray(beh["StartFr"], dtype=int)
    gray_fr = np.asarray(beh["GrayFr"], dtype=int)
    sound_fr = np.asarray(beh["SoundFr"], dtype=int)
...
        cue_idx = float(np.searchsorted(frames, sound_fr[trial_idx], side="left"))
        t_since = (retained_idx * frame_dt).astype(np.float32)
        t_to_cue = ((cue_idx - retained_idx) * frame_dt).astype(np.float32)
```

**What this does:** The trial produces this input as `time_to_sound_cue_sec` (`input[0]`). In code it is derived from the trial-level cue frame index `SoundFr`, the retained running-frame list (built from `StartFr`, `GrayFr`, `ft_move`), and a session-level median frame interval computed from `ft`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `input` *time_to_sound_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use actual frame times in seconds, not just frame index: Because non-running frames are dropped, elapsed time inputs must come from `ft` timestamps rather than assuming contiguous native-frame spacing." (CONVERSION_NOTES.md:259); "verify `time_since_trial_start_sec + time_to_sound_cue_sec` equals the trial's cue time-from-start at every retained frame" (CONVERSION_NOTES.md:264); "`time_to_sound_cue_sec` range | ... | Derived from running texture-frame axis in raw behavior files | `[-51.3, 23.3]`" (CONVERSION_NOTES.md:386)

**Code** (convert_data.py:307-317, 376-383):
```python
    for trial_idx in range(int(beh["ntrials"])):
        frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
        frames = frames[ft_move[frames] > 0]
        ...
        retained_idx = np.arange(frames.size, dtype=np.float32)
        cue_idx = float(np.searchsorted(frames, sound_fr[trial_idx], side="left"))
        t_to_cue = ((cue_idx - retained_idx) * frame_dt).astype(np.float32)
...
            input_arr = np.vstack(
                [
                    input_raw["time_to_sound_cue_sec"],
                    ...
```

**What this does:** The cue frame `SoundFr` is located within the retained running-frame list via `searchsorted` to give a cue index on the retained axis; the signed difference between that index and each retained frame's ordinal position is multiplied by the session median frame interval `frame_dt` (seconds). Values are positive before the cue and negative after; the array becomes row 0 of the `(4, T)` float32 input.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `input` *time_to_sound_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: corridor entry (trial start / StartFr)", "off_start: 0.0", "off_end: None", "frame_selection: running-only frames within texture area" (convert_data.py:688-692); "Temporal alignment: corridor entry (`StartFr`)" (README.md:21)

**Code** (convert_data.py:308-317, 374-394):
```python
        frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
        frames = frames[ft_move[frames] > 0]
        neural = spk_sel[:, frames].astype(np.float32, copy=False)
        retained_idx = np.arange(frames.size, dtype=np.float32)
        cue_idx = float(np.searchsorted(frames, sound_fr[trial_idx], side="left"))
        t_to_cue = ((cue_idx - retained_idx) * frame_dt).astype(np.float32)
...
            T = neural_trial.shape[1]
            input_arr = np.vstack([...]).astype(np.float32)
            if input_arr.shape[1] != T or output_arr.shape[1] != T:
                raise ValueError(f"Time dimension mismatch in session {session.session_id}.")
```

**What this does:** The same `frames` array selects the neural columns and defines the retained-frame axis on which the cue time is computed, so column t of the input corresponds to column t of the neural matrix. `finalize_io` explicitly asserts the input and neural time dimensions match.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `input` *day_of_training* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| Session recording date / optional `db['days']` | `input[1]` = `day_of_training` | Use elapsed calendar days since the mouse's first recording date; repeat across retained frames in the trial | `Imaging_Exp_info.npy` | Chosen because a complete per-session training-day label is not available for all sessions. |" (CONVERSION_NOTES.md:241)

**Code** (convert_data.py:156-167):
```python
def compute_day_offsets(catalog: list[SessionCandidate]) -> dict[str, float]:
    by_subject: dict[str, list[datetime]] = defaultdict(list)
    session_dates: dict[str, datetime] = {}
    for cand in catalog:
        date = datetime.strptime(cand.db["datexp"], "%Y_%m_%d")
        by_subject[cand.db["mname"]].append(date)
        session_dates[cand.session_id] = date
    first_dates = {subject: min(dates) for subject, dates in by_subject.items()}
    return {
        cand.session_id: float((session_dates[cand.session_id] - first_dates[cand.db["mname"]]).days)
        for cand in catalog
    }
```

**What this does:** The trial produces this input as `day_of_training` (`input[1]`). It is derived from the `datexp` (experiment date) and `mname` (mouse name) fields of the session records in `data/beh/Imaging_Exp_info.npy`; no explicit training-day field from the raw data is used.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `input` *day_of_training*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Represent all decoder inputs as time-varying arrays: Even trial-constant variables (`day_of_training`, `reward_available`) will be repeated across timepoints..." (CONVERSION_NOTES.md:258); "`day_of_training` range | ... | `0` to `92` from canonical session order per mouse | `[0.0, 92.0]` | Yes" (CONVERSION_NOTES.md:387)

**Code** (convert_data.py:163-167, 319, 495-500):
```python
    first_dates = {subject: min(dates) for subject, dates in by_subject.items()}
    return {
        cand.session_id: float((session_dates[cand.session_id] - first_dates[cand.db["mname"]]).days)
        for cand in catalog
    }
...
        day = np.full(frames.shape, session_day, dtype=np.float32)
...
    neural_trials, input_trials, output_trials, speed_values, trial_summary = build_trial_arrays(
        spk_sel,
        beh,
        session_day=day_offsets[candidate.session_id],
```

**What this does:** Session date strings are parsed to `datetime`; for each mouse the earliest date across the whole catalog is day 0, and each session's offset is the integer day difference as a float. That per-session scalar is broadcast with `np.full` across all retained timepoints of every trial, forming row 1 of the input array.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `input` *time_since_trial_start* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| `beh['ft']`, `StartFr` | `input[2]` = `time_since_trial_start_sec` | `(ft[frame] - ft[StartFr[trial]]) * 86400` for each retained frame | Behavior frame timing fields | Continuous time-varying input in seconds. |" (CONVERSION_NOTES.md:242); "- `time_since_trial_start_sec`" (README.md:38)

**Code** (convert_data.py:285-294, 308-316):
```python
    ft = np.asarray(beh["ft"][:nfr], dtype=float)
    dft = np.diff(ft)
    dft = dft[np.isfinite(dft) & (dft > 0)]
    frame_dt = float(np.median(dft) * SECONDS_PER_DAY)
    ft_move = np.asarray(beh["ft_move"][:nfr], dtype=float)
    ...
    start_fr = np.asarray(beh["StartFr"], dtype=int)
    gray_fr = np.asarray(beh["GrayFr"], dtype=int)
...
        frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
        frames = frames[ft_move[frames] > 0]
        retained_idx = np.arange(frames.size, dtype=np.float32)
        t_since = (retained_idx * frame_dt).astype(np.float32)
```

**What this does:** The trial produces this input as `time_since_trial_start_sec` (`input[2]`). In code it is derived from the count of retained running frames in the trial (defined by `StartFr`, `GrayFr`, `ft_move`) together with the session median frame interval computed from `ft`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `input` *time_since_trial_start*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Keep running frames only inside the texture segment ... Actual elapsed time is still preserved through the continuous time inputs." (CONVERSION_NOTES.md:252); "Use actual frame times in seconds, not just frame index: Because non-running frames are dropped, elapsed time inputs must come from `ft` timestamps rather than assuming contiguous native-frame spacing." (CONVERSION_NOTES.md:259); "`time_since_trial_start_sec` range | ... | Derived from retained running-frame intervals in raw behavior files | `[0.0, 56.0]`" (CONVERSION_NOTES.md:388)

**Code** (convert_data.py:286-288, 308-316):
```python
    dft = np.diff(ft)
    dft = dft[np.isfinite(dft) & (dft > 0)]
    frame_dt = float(np.median(dft) * SECONDS_PER_DAY)
...
        frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
        frames = frames[ft_move[frames] > 0]
        if frames.size == 0:
            continue
        neural = spk_sel[:, frames].astype(np.float32, copy=False)
        retained_idx = np.arange(frames.size, dtype=np.float32)
        t_since = (retained_idx * frame_dt).astype(np.float32)
```

**What this does:** A session-level `frame_dt` is computed as the median positive `ft` difference converted to seconds. Per trial, the retained running frames are numbered 0, 1, 2, ... and multiplied by `frame_dt`, so the value starts at exactly 0 at the first retained frame and increments uniformly, without re-reading the per-frame timestamps of the dropped non-running frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-c. How is `input` *time_since_trial_start* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: corridor entry (trial start / StartFr)", "off_start: 0.0", "off_end: None", "trial_end_event: entry into gray space (GrayFr)" (convert_data.py:688-691); "Use the texture segment only (`StartFr:GrayFr`)" (CONVERSION_NOTES.md:251)

**Code** (convert_data.py:308-316, 374-397):
```python
        frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
        frames = frames[ft_move[frames] > 0]
        neural = spk_sel[:, frames].astype(np.float32, copy=False)
        retained_idx = np.arange(frames.size, dtype=np.float32)
        t_since = (retained_idx * frame_dt).astype(np.float32)
...
        for neural_trial, input_raw, output_raw in zip(session.neural, session.input_raw, session.output_raw):
            T = neural_trial.shape[1]
            ...
            if input_arr.shape[1] != T or output_arr.shape[1] != T:
                raise ValueError(f"Time dimension mismatch in session {session.session_id}.")
```

**What this does:** The input is defined on the same retained-frame index axis used to slice the neural matrix, so it is column-for-column aligned with the neural data. Its value is 0 at the first retained (running) frame of the trial, which is the corridor-entry alignment event recorded in metadata.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `input` *reward_availability* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "| `beh['isRew']` | `input[3]` = `reward_available` | Trialwise 0/1 repeated across retained frames | Behavior session dict | Uses rewarded-corridor identity even in unsupervised sessions, matching reference use of `isRew`. |" (CONVERSION_NOTES.md:243); "- `reward_available`" (README.md:39)

**Code** (convert_data.py:297, 318, 664-669):
```python
    is_rew = np.asarray(beh["isRew"]).astype(np.float32)
...
        reward = np.full(frames.shape, is_rew[trial_idx], dtype=np.float32)
...
        "input_names": [
            "time_to_sound_cue_sec",
            "day_of_training",
            "time_since_trial_start_sec",
            "reward_available",
        ],
```

**What this does:** The trial produces this input as `reward_available` (`input[3]`). It is read directly from the trial-level `isRew` array in the per-session behavior dict, indexed by trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `input` *reward_availability*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Represent all decoder inputs as time-varying arrays: Even trial-constant variables (`day_of_training`, `reward_available`) will be repeated across timepoints so the dataset is uniform..." (CONVERSION_NOTES.md:258); "`reward_available` range | Binary rewarded vs unrewarded corridors | ... | `[0.0, 1.0]` | Yes" (CONVERSION_NOTES.md:389)

**Code** (convert_data.py:297, 318, 331-338):
```python
    is_rew = np.asarray(beh["isRew"]).astype(np.float32)
...
        reward = np.full(frames.shape, is_rew[trial_idx], dtype=np.float32)
...
        input_trials.append(
            {
                "time_to_sound_cue_sec": t_to_cue,
                "day_of_training": day,
                "time_since_trial_start_sec": t_since,
                "reward_available": reward,
            }
        )
```

**What this does:** `isRew` is cast to float32 and the per-trial scalar is broadcast with `np.full` over all retained running frames of that trial, becoming row 3 of the `(4, T)` input array. No time-windowing or reward-delivery timing is applied; the flag is constant for the whole trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-a. What variables in the raw data is `output` *visual_stimulus* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`beh['WallName']` -> `output[0]` = `visual_stimulus_category` ... Use `WallName` directly so swap sessions and non-leaf/circle stimuli are preserved correctly." (CONVERSION_NOTES.md:244)

**Code** (convert_data.py:296, 328):
```python
wall_name = np.asarray(beh["WallName"]).astype(str)
...
stim_val = np.full(frames.shape, stimulus_to_idx[wall_name[trial_idx]], dtype=np.int64)
```

**What this does:** Derived from per-trial `WallName` strings.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7-b. What processing is involved in computing `output` *visual_stimulus*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use exact `WallName` strings as stimulus labels: This avoids ambiguity from `stim_id` NaNs in swap sessions and preserves non-leaf/circle texture pairs (`rock*`, `wood*`)." (CONVERSION_NOTES.md:257)

**Code** (convert_data.py:547-552, 618, 676-678):
```python
def collect_stimulus_values(catalog):
    names = set()
    for cand in catalog:
        beh = load_behavior(cand.exp_type, cand.beh_key)
        names.update(map(str, np.asarray(beh["WallName"]).tolist()))
    return sorted(names)
...
stimulus_to_idx = {name: idx for idx, name in enumerate(stimulus_values)}
...
"output_values": [stimulus_values, ...]
```

**What this does:** All unique `WallName` strings across all sessions are collected and sorted to define the integer vocabulary. Each trial's wall name is mapped to its index, then broadcast across the trial's retained frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What variables in the raw data is `output` *licking* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`beh['LickFr']`, `beh['LickTrind']` -> `output[1]` = `licking` ... Binary per retained frame: 1 if one or more licks occur on that imaging frame, else 0" (CONVERSION_NOTES.md:245)

**Code** (convert_data.py:298-299, 321-323):
```python
lick_fr = np.asarray(beh["LickFr"], dtype=float)
lick_tr = np.asarray(beh["LickTrind"], dtype=float)
...
lick_frames_trial = lick_fr[(lick_tr == trial_idx) & np.isfinite(lick_fr)]
lick_frames_trial = lick_frames_trial.astype(int)
licking = np.isin(frames, lick_frames_trial).astype(np.int64)
```

**What this does:** Derived from `LickFr` (frame index of each lick) and `LickTrind` (trial index of each lick).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What processing is involved in computing `output` *licking*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Binary per retained frame: 1 if one or more licks occur on that imaging frame, else 0" (CONVERSION_NOTES.md:245)

**Code** (convert_data.py:321-323, 678):
```python
lick_frames_trial = lick_fr[(lick_tr == trial_idx) & np.isfinite(lick_fr)]
lick_frames_trial = lick_frames_trial.astype(int)
licking = np.isin(frames, lick_frames_trial).astype(np.int64)
...
["no_lick", "lick"]
```

**What this does:** For each trial, lick frame indices belonging to that trial are filtered, then `np.isin` produces a binary vector marking retained frames where at least one lick occurred. Two-class vocabulary `[no_lick, lick]`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. How is `output` *licking* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none — alignment is implicit via shared `frames` index)"

**Code** (convert_data.py:323):
```python
licking = np.isin(frames, lick_frames_trial).astype(np.int64)
```

**What this does:** `np.isin(frames, ...)` is computed against the same retained-frames array used for the neural slice, giving direct per-frame alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-a. What variables in the raw data is `output` *position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`beh['ft_Pos']` on retained frames -> `output[2]` = `position_bin` ... Discretize `0–40 dm` into 4 equal bins" (CONVERSION_NOTES.md:246)

**Code** (convert_data.py:290, 325-326):
```python
ft_pos = np.asarray(beh["ft_Pos"][:nfr], dtype=float)
...
pos = ft_pos[frames]
pos_bin = np.clip(np.floor(pos / 10.0).astype(np.int64), 0, 3)
```

**What this does:** Derived from framewise `ft_Pos` (corridor position in decimeters).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-b. What processing is involved in computing `output` *position*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize `0–40 dm` into 4 equal bins: `[0,10), [10,20), [20,30), [30,40]`" (CONVERSION_NOTES.md:246)

**Code** (convert_data.py:325-326, 679):
```python
pos = ft_pos[frames]
pos_bin = np.clip(np.floor(pos / 10.0).astype(np.int64), 0, 3)
...
["0-1m", "1-2m", "2-3m", "3-4m"]
```

**What this does:** Position in dm divided by 10 (to meters) and floored to integer bins, clipped to [0, 3], yielding four 1-m bins covering the texture corridor.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 9-c. How is `output` *position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none — alignment is implicit via shared `frames` index)"

**Code** (convert_data.py:325-326):
```python
pos = ft_pos[frames]
pos_bin = np.clip(np.floor(pos / 10.0).astype(np.int64), 0, 3)
```

**What this does:** `ft_Pos` is indexed by the same `frames` array that defines neural columns, giving direct per-frame alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-a. What variables in the raw data is `output` *running_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`beh['ft_RunSpeed']` on retained frames -> `output[3]` = `running_speed_bin` ... Compute global quartile edges over all retained running frames in all sessions; assign bin 0–3" (CONVERSION_NOTES.md:247)

**Code** (convert_data.py:291, 327):
```python
ft_speed = np.asarray(beh["ft_RunSpeed"][:nfr], dtype=float)
...
raw_speed = ft_speed[frames].astype(np.float32)
```

**What this does:** Derived from framewise `ft_RunSpeed`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-b. What processing is involved in computing `output` *running_speed*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Compute global quartile edges over all retained running frames in all sessions; assign bin 0–3" (CONVERSION_NOTES.md:247)

**Code** (convert_data.py:641-646, 384):
```python
all_speed_concat = np.concatenate(all_speed_values).astype(np.float32)
speed_edges = np.quantile(all_speed_concat, [0.0, 0.25, 0.5, 0.75, 1.0]).astype(np.float32)
for i in range(1, len(speed_edges)):
    if speed_edges[i] <= speed_edges[i - 1]:
        speed_edges[i] = np.nextafter(speed_edges[i - 1], np.float32(np.inf))
...
speed_bin = np.searchsorted(thresholds, output_raw["running_speed_raw"], side="right").astype(np.int64)
```

**What this does:** All retained-frame raw speeds across sessions are concatenated; global quartile edges are computed; per-frame raw speeds are assigned to bin 0–3 using `np.searchsorted` against the inner thresholds.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 10-c. How is `output` *running_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none — alignment is implicit via shared `frames` index)"

**Code** (convert_data.py:327, 384):
```python
raw_speed = ft_speed[frames].astype(np.float32)
...
speed_bin = np.searchsorted(thresholds, output_raw["running_speed_raw"], side="right").astype(np.int64)
```

**What this does:** Raw speed is sampled at the same `frames` indices used for neural data, then binned; alignment is direct, per frame.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 11. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sessions with no finite aHV reward `d′` values are now handled explicitly by assigning an infinite reward threshold, preventing accidental over-selection." (CONVERSION_NOTES.md:419)
> "fallback top-|d′| selection if too few neurons pass" (CONVERSION_NOTES.md:289)

**Code** (convert_data.py:93-102, 242-244, 256-265):
```python
def safe_dprime(x1, x2):
    if x1.size == 0 or x2.size == 0:
        return np.full(..., np.nan, dtype=np.float32)
    ...
    denom[denom == 0] = np.nan
    return (2.0 * (u1 - u2) / denom).astype(np.float32)

reward_dp_thr = np.inf
ahv_mask = region_idx_all == 3
if np.isfinite(reward_dp[ahv_mask]).any():
    reward_dp_thr = float(np.nanpercentile(reward_dp[ahv_mask], 95))
...
if selected.sum() < MIN_NEURONS_FALLBACK:
    candidate = visual_mask & np.isfinite(dp)
    if candidate.sum() == 0:
        candidate = visual_mask
    abs_dp = np.abs(np.nan_to_num(dp, nan=0.0))
    ...
```

**What this does:** Empty/zero-denominator d-prime computations return NaN. Sessions lacking finite aHV reward d' set the threshold to infinity (no reward neurons selected). If fewer than 64 neurons survive, a fallback top-|d'| selection is used. `get_reference_pair` has multi-tier fallbacks for stim_id NaNs and missing reward labels. Lick frames filtered with `np.isfinite`. Trials with no retained frames skipped.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Full conversion estimate (size-weighted over 404.36 GB raw spike files) | ~2.10 s / GB | ~870 s (~14.5 min) plus modest validation overhead" (CONVERSION_NOTES.md:347)
> "corrected full conversion completed in `501.4 s`" (CONVERSION_NOTES.md:375)
> "Sample conversion session 1 (`TX109_2023_03_27_1`) | 3.7 s ... session 2 (`TX60_2021_06_22_1`) | 5.3 s" (CONVERSION_NOTES.md:345-346)

**Code** (convert_data.py:483-500, 524-529):
```python
t0 = time.perf_counter()
beh = load_behavior(candidate.exp_type, candidate.beh_key)
spk = utils.load_spk(candidate.db, root=str(SPK_ROOT))
ret = np.load(RET_ROOT / f"{candidate.db['mname']}_{candidate.db['datexp']}_trans.npz", allow_pickle=True)
_, region_idx_all = area_labels_from_iarea(ret["iarea"])

selected_mask, selection_info = compute_neuron_selection(spk, beh, region_idx_all)
spk_sel = spk[selected_mask]
...
neural_trials, input_trials, output_trials, speed_values, trial_summary = build_trial_arrays(
    spk_sel,
    beh,
    session_day=day_offsets[candidate.session_id],
    stimulus_to_idx=stimulus_to_idx,
)
...
elapsed = time.perf_counter() - t0
print(f"[session] {candidate.session_id} ... time={elapsed:.1f}s")
```

**What this does:** Per-session processing dominates total runtime (~5–13 s/session, total ~501 s for 89 sessions). The largest per-session costs are loading the multi-GB spike `.npy` via `utils.load_spk`, `compute_neuron_selection` (d-prime computations across all frames/neurons), and the per-trial loop in `build_trial_arrays`. Final `pickle.dump` of ~12.5 GiB at end.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:236-241, 307-348, 560-580):
```python
for trial_idx in np.flatnonzero(valid_reward_trials):
    frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
    frames = frames[running[frames] & (ft_pos[frames] >= 5.0) & (ft_pos[frames] <= TEXTURE_LENGTH_DM)]
    if frames.size:
        trial_means[:, trial_idx] = np.nanmean(spk[:, frames], axis=1)
...
for trial_idx in range(int(beh["ntrials"])):
    frames = np.arange(start_fr[trial_idx], gray_fr[trial_idx], dtype=int)
    frames = frames[ft_move[frames] > 0]
    ...
    lick_frames_trial = lick_fr[(lick_tr == trial_idx) & np.isfinite(lick_fr)]
    licking = np.isin(frames, lick_frames_trial).astype(np.int64)
...
for trial_idx, (s, g) in enumerate(zip(start, gray)):
    frames = np.arange(s, g, dtype=int)
    frames = frames[move[frames]]
    ...
    if np.isin(frames, lfr).any():
        lick_trials += 1
```

**What this does:** Several Python-level per-trial loops perform per-frame indexing, lick `np.isin`, and per-trial nanmean over neuron x frame slices. The reward-trial mean loop and the main `build_trial_arrays` loop iterate per trial sequentially. `sample_candidate_score` also loops over trials when ranking sample sessions.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Full-mode metadata currently recomputes frame-interval medians by reloading behavior files." (CONVERSION_NOTES.md:298)
> "Stimulus vocabulary collection reloads behavior dictionaries once more after catalog creation." (CONVERSION_NOTES.md:299)

**Code** (convert_data.py:547-552, 583-593, 601-604):
```python
def collect_stimulus_values(catalog):
    names = set()
    for cand in catalog:
        beh = load_behavior(cand.exp_type, cand.beh_key)
        names.update(map(str, np.asarray(beh["WallName"]).tolist()))
    return sorted(names)

def compute_time_bin_ms(catalog):
    medians = []
    for cand in catalog:
        ft = np.asarray(load_behavior(cand.exp_type, cand.beh_key)["ft"], dtype=float)
        ...
...
full_catalog = build_session_catalog()
day_offsets = compute_day_offsets(full_catalog)
stimulus_values = collect_stimulus_values(full_catalog)
time_bin_ms = compute_time_bin_ms(full_catalog)
```

**What this does:** Behavior `.npy` files are loaded multiple times per session: once in `collect_stimulus_values`, once in `compute_time_bin_ms`, and once again inside `process_session`. `load_behavior` itself reloads the entire `Beh_<exp_type>.npy` dict per call without caching. In `--sample` mode, `sample_candidate_score` and `session_spk_size` also reload behavior for ranking.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:232-241, 502-513, 414-474):
```python
start_fr = np.asarray(beh["StartFr"], dtype=int)
gray_fr_trial = np.asarray(beh["GrayFr"], dtype=int)
ft_pos = np.asarray(beh["ft_Pos"][:nfr], dtype=float)
trial_means = np.full((spk.shape[0], int(beh["ntrials"])), np.nan, dtype=np.float32)
for trial_idx in np.flatnonzero(valid_reward_trials):
    ...
    trial_means[:, trial_idx] = np.nanmean(spk[:, frames], axis=1)
...
example_trial = None
if show_processing and neural_trials:
    idx = 0
    sample_neurons = min(100, neural_trials[idx].shape[0])
    example_trial = {
        "neural": neural_trials[idx][:sample_neurons],
        ...
    }
...
def plot_processing(session, speed_edges):
    ...
    fig.savefig(ROOT / f"processing_{session.session_id}.png", dpi=150)
```

**What this does:** Reward-prediction `trial_means` are computed across all neurons but only used for selecting aHV reward neurons (then discarded). `processing_info` accumulates `cue_positions_dm` and `example_trial` arrays which are only used by `plot_processing` (gated by `--show-processing`). Per-session `time=elapsed:.1f` and selection summary prints are computed but not saved into the pickle.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 12-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Session processing loads each large spike file only once, computes the neuron mask, then immediately drops the full matrix after subsetting." (CONVERSION_NOTES.md:302)
> "Speed quantiles are computed from concatenated retained running frames only, not all raw frames." (CONVERSION_NOTES.md:303)

**Code** (convert_data.py:489-493, 313, 395):
```python
selected_mask, selection_info = compute_neuron_selection(spk, beh, region_idx_all)
spk_sel = spk[selected_mask]
region_sel = region_idx_all[selected_mask]
raw_neurons = int(spk.shape[0])
del spk
...
neural = spk_sel[:, frames].astype(np.float32, copy=False)
...
neural_session.append(neural_trial.astype(np.float32, copy=False))
```

**What this does:** The full neuron x frame spike matrix is freed (`del spk`) immediately after the curated subset is taken, keeping peak per-session memory limited to the curated subset. `astype(..., copy=False)` avoids extra allocations when dtype already matches. Only retained running speeds are concatenated for global quantile computation, not all raw frames.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
