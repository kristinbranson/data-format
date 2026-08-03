# map — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/map/codex/2026-03-23__08-25-17_trial3/verifier/snapshot/`

Outputs identified (K=4): choice, outcome, early_lick, tongue_y_position

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "NWB loading via `h5py` rather than higher-level wrappers for lower overhead and explicit access to ragged arrays." (CONVERSION_NOTES.md:253)

**Code** (convert_data.py:85-95, 578-599):
```python
def get_nwb_files(sample_only: bool) -> list[Path]:
    files = sorted(DATA_DIR.glob("sub-*/*.nwb"))
    valid = []
    for path in files:
        with h5py.File(path, "r") as f:
            good = decode_str_array(f["units/classification"]) == "good"
            if np.any(good):
                valid.append(path)
    if sample_only:
        return valid[:SAMPLE_SESSION_COUNT]
    return valid
...
    files = get_nwb_files(sample_only=sample_only)
    ...
    for i, path in enumerate(files, start=1):
        result = process_session(path)
        results.append(result)
    data = build_dataset(results)
    with open(args.outpicklefile, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
```

**What this does:** Recursively globs `data/sub-*/*.nwb`, opens each with `h5py`, keeps sessions that have at least one `good` unit, then iterates sessions sequentially calling `process_session` and aggregates via `build_dataset` before pickling.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`subject` folder / NWB subject metadata → `subjects`, `subject_idx`: Use exact subject IDs (`sub-xxxxx`) and map each session to its subject index" (CONVERSION_NOTES.md:216)

**Code** (convert_data.py:319-320, 557-561):
```python
    session_id = path.stem
    subject_id = path.parent.name
...
    for session_idx, result in enumerate(results):
        if result.subject_id not in subject_to_idx:
            subject_to_idx[result.subject_id] = len(subjects)
            subjects.append(result.subject_id)
        data["subject_idx"][session_idx] = subject_to_idx[result.subject_id]
```

**What this does:** Subject ID is taken as the parent folder name (`sub-xxxxx`) of each NWB file; `subjects` is a unique list and each session gets a `subject_idx` pointing into that list.

**Rating:** ok

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Each session is a single NWB file inside its subject folder, for a total of `174` NWB files." (CONVERSION_NOTES.md:69)

**Code** (convert_data.py:86, 317-321, 587-590):
```python
    files = sorted(DATA_DIR.glob("sub-*/*.nwb"))
...
def process_session(path: Path) -> SessionResult:
    t0 = time.perf_counter()
    session_id = path.stem
    subject_id = path.parent.name
...
    for i, path in enumerate(files, start=1):
        print(f"[progress] {i}/{len(files)} {path.name}")
        result = process_session(path)
        results.append(result)
```

**What this does:** Each NWB file in `data/sub-*/` is one session; `session_id` is the file stem. Sessions are processed in sorted order, one `SessionResult` per file.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use `go_start_times` as the unique per-trial alignment anchor." (CONVERSION_NOTES.md:191)

**Code** (convert_data.py:323-355):
```python
    with h5py.File(path, "r") as f:
        trials = f["intervals/trials"]
        n_trials_raw = len(trials["id"])
        ...
        start_times_all = trials["start_time"][()].astype(np.float64)
        stop_times_all = trials["stop_time"][()].astype(np.float64)
        go_times_all = f["acquisition/BehavioralEvents/go_start_times/timestamps"][()].astype(np.float64)
        if len(go_times_all) != n_trials_raw:
            raise ValueError(f"{session_id}: go cue count {len(go_times_all)} does not match trial count {n_trials_raw}")
        ...
        valid_trial_mask = compute_valid_trial_mask(obs_intervals=obs_intervals, go_times=go_times_all)
        ...
        start_times = start_times_all[valid_trial_mask]
        stop_times = stop_times_all[valid_trial_mask]
        go_times = go_times_all[valid_trial_mask]
        n_trials = len(go_times)
```

**What this does:** Trials are taken row-wise from `intervals/trials`; `go_start_times` is asserted to have one entry per trial and used as the per-trial anchor. A coverage mask from `units/obs_intervals` then keeps only trials whose go-aligned analysis window fits inside recording intervals.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trials are retained only when the requested neural window is available and contains nonzero spikes across the good-unit population." (README.md:89)

**Code** (convert_data.py:255-263, 413-427):
```python
def compute_valid_trial_mask(
    obs_intervals: np.ndarray,
    go_times: np.ndarray,
) -> np.ndarray:
    trial_start = go_times + REL_START_S
    trial_end = go_times + REL_END_S
    starts = obs_intervals[:, 0][None, :]
    ends = obs_intervals[:, 1][None, :]
    return np.any((trial_start[:, None] >= starts) & (trial_end[:, None] <= ends), axis=1)
...
        nonzero_trial_mask = np.any(firing_rates != 0, axis=(0, 2))
        if not np.all(nonzero_trial_mask):
            firing_rates = firing_rates[:, nonzero_trial_mask, :]
            ...
            n_trials = len(go_times)
```

**What this does:** Two-stage trial QC: (1) `obs_intervals` mask requires the full `[-2.5, 1.5)` go-aligned window be inside a recording interval of the first good unit; (2) post-binning, trials with all-zero firing across all good units and bins are dropped. No filtering on outcome, early lick, or stim status.

**Rating:** concerning

**Note:** does not filter for free_water

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`units/spike_times`, `units/classification`, `acquisition/BehavioralEvents/go_start_times` → `neural`" (CONVERSION_NOTES.md:209)

**Code** (convert_data.py:327-329, 338, 403-412):
```python
        classification = decode_str_array(f["units/classification"])
        good_mask = classification == "good"
        good_unit_indices = np.flatnonzero(good_mask)
        ...
        go_times_all = f["acquisition/BehavioralEvents/go_start_times/timestamps"][()].astype(np.float64)
        ...
        spike_times_flat = f["units/spike_times"][()]
        spike_times_index = f["units/spike_times_index"][()]
        trial_edges_abs = go_times[:, None] + REL_EDGES[None, :]
        firing_rates = bin_spikes_to_firing_rates(
            spike_times_flat=spike_times_flat,
            spike_times_index=spike_times_index,
            good_unit_indices=good_unit_indices,
            trial_edges_abs=trial_edges_abs,
        )
```

**What this does:** Neural data is derived from `units/spike_times` (+ `spike_times_index` for ragged decoding), filtered by `units/classification == "good"`, with bin edges built from `go_start_times` plus `units/obs_intervals` for trial validity.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Spike binning into `50 ms` go-aligned bins and conversion to firing rate in Hz." (CONVERSION_NOTES.md:257)

**Code** (convert_data.py:235-252):
```python
def bin_spikes_to_firing_rates(
    spike_times_flat: np.ndarray,
    spike_times_index: np.ndarray,
    good_unit_indices: np.ndarray,
    trial_edges_abs: np.ndarray,
) -> np.ndarray:
    n_trials = trial_edges_abs.shape[0]
    n_edges = trial_edges_abs.shape[1]
    flat_edges = trial_edges_abs.reshape(-1)
    start_index = np.concatenate(([0], spike_times_index[:-1]))
    firing_rates = np.empty((len(good_unit_indices), n_trials, n_edges - 1), dtype=np.float16)

    for i, unit_idx in enumerate(good_unit_indices):
        spikes = spike_times_flat[start_index[unit_idx]: spike_times_index[unit_idx]]
        edge_idx = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_edges)
        counts = np.diff(edge_idx, axis=1)
        firing_rates[i] = (counts / BIN_SIZE_S).astype(np.float16)
    return firing_rates
```

**What this does:** For each good unit, extracts its ragged spike-time slice, then uses `np.searchsorted` against flattened per-trial bin edges to count spikes per `50 ms` bin and converts to Hz (`counts / 0.05`), stored as `float16`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Good-unit filtering from `units/classification == "good"`." (CONVERSION_NOTES.md:255)

**Code** (convert_data.py:327-334):
```python
        classification = decode_str_array(f["units/classification"])
        good_mask = classification == "good"
        good_unit_indices = np.flatnonzero(good_mask)
        if len(good_unit_indices) == 0:
            raise ValueError(f"Session {session_id} has no good units")

        anno_name = decode_str_array(f["units/anno_name"])
        region_labels = anno_name[good_unit_indices]
```

**What this does:** Only units with `classification == "good"` are kept; sessions with zero good units raise (and are pre-excluded by `get_nwb_files`). No further per-unit QC metrics applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use `50 ms` bins because the decoder task explicitly requires this... Window: `-2.5 s` to `+1.5 s`" (CONVERSION_NOTES.md:232; README.md:32)

**Code** (convert_data.py:18-24, 405-407):
```python
BIN_SIZE_S = 0.05
REL_START_S = -2.5
REL_END_S = 1.5
TONE_ONSET_REL_GO_S = -1.85
N_BINS = int(round((REL_END_S - REL_START_S) / BIN_SIZE_S))
REL_EDGES = np.linspace(REL_START_S, REL_END_S, N_BINS + 1, dtype=np.float64)
REL_CENTERS = (REL_EDGES[:-1] + REL_EDGES[1:]) / 2.0
...
        trial_edges_abs = go_times[:, None] + REL_EDGES[None, :]
```

**What this does:** Fixed `50 ms` non-overlapping bins span `[-2.5, +1.5) s` relative to go cue (`N_BINS=80`). Edges are constructed once at module level and broadcast against per-trial go times.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Temporal alignment: go cue onset" (README.md:29)

**Code** (convert_data.py:338, 405-412):
```python
        go_times_all = f["acquisition/BehavioralEvents/go_start_times/timestamps"][()].astype(np.float64)
...
        trial_edges_abs = go_times[:, None] + REL_EDGES[None, :]
        firing_rates = bin_spikes_to_firing_rates(
            spike_times_flat=spike_times_flat,
            spike_times_index=spike_times_index,
            good_unit_indices=good_unit_indices,
            trial_edges_abs=trial_edges_abs,
        )
```

**What this does:** Per-trial absolute bin edges = `go_time + REL_EDGES`, so each trial's neural matrix is centered at the per-trial go cue onset.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *time_from_tone_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Task structure from papers (`sample = 0.65 s`, `delay = 1.2 s`) + go cue | `input[0]` | Compute `time_from_tone_onset_s = bin_center - (-1.85 s)` for every bin ... Raw NWB sample-event streams contain replay-related extra events and are not reliable one-to-one trial markers; using the canonical `-1.85 s` tone onset is more consistent with the task definition" (CONVERSION_NOTES.md:210)
> "**Sample/tone onset definition**: Use the canonical tone onset at `-1.85 s` relative to go cue from the task structure (`0.65 s` sample epoch + `1.2 s` delay), because raw NWB sample-event streams contain replay-related extra events." (CONVERSION_NOTES.md:225)
> "`tone_onset_definition`: Canonical sample onset at -1.85 s relative to go cue from task structure" (convert_data.py:540)

**Code** (convert_data.py:19-24, 378):
```python
REL_START_S = -2.5
REL_END_S = 1.5
TONE_ONSET_REL_GO_S = -1.85
N_BINS = int(round((REL_END_S - REL_START_S) / BIN_SIZE_S))
REL_EDGES = np.linspace(REL_START_S, REL_END_S, N_BINS + 1, dtype=np.float64)
REL_CENTERS = (REL_EDGES[:-1] + REL_EDGES[1:]) / 2.0
...
        input_time = np.tile((REL_CENTERS - TONE_ONSET_REL_GO_S).astype(np.float16), (n_trials, 1))
```

**What this does:** The variable is not read from any raw NWB dataset. It is built from the module-level bin-center grid plus a hard-coded constant `TONE_ONSET_REL_GO_S = -1.85`, which the notes derive from the published task structure (0.65 s sample + 1.2 s delay) rather than from the per-trial `acquisition/BehavioralEvents` sample/tone event stream. The only raw quantity entering indirectly is the per-trial go cue time, via the go-aligned bin grid.

**Rating:** incorrect

**Note:** hardcoded rather than using sample_start_times

---

## Q 3-b. What processing is involved in computing `input` *time_from_tone_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Compute `time_from_tone_onset_s = bin_center - (-1.85 s)` for every bin" (CONVERSION_NOTES.md:210)
> "`time_from_tone_onset_s` range | [-0.6, 3.3]" (CONVERSION_NOTES.md:289)
> "Full `time_from_tone_onset_s` vector matched the independent formula from fixed bin centers and canonical tone onset." (CONVERSION_NOTES.md:390)

**Code** (convert_data.py:378, 424, 442):
```python
        input_time = np.tile((REL_CENTERS - TONE_ONSET_REL_GO_S).astype(np.float16), (n_trials, 1))
...
            input_time = input_time[nonzero_trial_mask]
...
        input_trial = np.vstack([input_time[trial_idx], input_stim[trial_idx]]).astype(np.float16)
```

**What this does:** A single 80-element vector `REL_CENTERS - (-1.85)` is computed once (values `[-0.575, ..., 3.325]` s), cast to `float16`, and tiled identically across all trials in the session; no per-trial timing enters. It is then row-subset by the nonzero-spike trial mask and stacked as row 0 of each trial's `input` array (`input_names[0] = "time_from_tone_onset_s"`, convert_data.py:515).

**Rating:** incorrect

**Note:** does not use the real data, hardcoded

---

## Q 3-c. How is `input` *time_from_tone_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying decoder inputs for canonical time-from-tone-onset and photostimulation on/off." (CONVERSION_NOTES.md:258)
> "Temporal alignment: go cue onset" (README.md:29)

**Code** (convert_data.py:23-24, 378, 405, 424):
```python
REL_EDGES = np.linspace(REL_START_S, REL_END_S, N_BINS + 1, dtype=np.float64)
REL_CENTERS = (REL_EDGES[:-1] + REL_EDGES[1:]) / 2.0
...
        input_time = np.tile((REL_CENTERS - TONE_ONSET_REL_GO_S).astype(np.float16), (n_trials, 1))
...
        trial_edges_abs = go_times[:, None] + REL_EDGES[None, :]
...
            input_time = input_time[nonzero_trial_mask]
```

**What this does:** The input uses the same `REL_CENTERS` grid that defines the neural bins (`REL_EDGES` shifted by each trial's go time), so it is a shape-`(n_trials, 80)` array on the identical go-aligned 50 ms lattice as `neural`. Because a fixed offset is assumed rather than per-trial tone times, every trial's vector is the same; the nonzero-spike trial mask is applied to `input_time` alongside the neural array so trial indices stay in correspondence.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *photostim* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`intervals/trials/photostim_onset`, `photostim_duration`, `start_time`, `go_start_times` | `input[1]` | Convert photostim onset/duration from trial-start coordinates to go-centered coordinates; emit binary `0/1` per bin center for photostim on/off" (CONVERSION_NOTES.md:211)
> "NWB trial table stores `photostim_onset` relative to trial start; in example trials, subtracting `(go_time - trial_start)` gives about `-1.2 s`, matching late-delay stimulation" (CONVERSION_NOTES.md:192)

**Code** (convert_data.py:336-338, 360-361, 379-384):
```python
        start_times_all = trials["start_time"][()].astype(np.float64)
        stop_times_all = trials["stop_time"][()].astype(np.float64)
        go_times_all = f["acquisition/BehavioralEvents/go_start_times/timestamps"][()].astype(np.float64)
...
        photostim_onset_str = decode_str_array(trials["photostim_onset"])[valid_trial_mask]
        photostim_duration_str = decode_str_array(trials["photostim_duration"])[valid_trial_mask]
...
        input_stim = build_photostim_matrix(
            photostim_onset_str=photostim_onset_str,
            photostim_duration_str=photostim_duration_str,
            start_times=start_times,
            go_times=go_times,
        )
```

**What this does:** Derived from the trial-table string columns `intervals/trials/photostim_onset` and `photostim_duration`, plus `intervals/trials/start_time` and `acquisition/BehavioralEvents/go_start_times/timestamps` for the coordinate change. `photostim_power` and the photostimulation event time series under `acquisition/BehavioralEvents` are not used.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *photostim*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Convert photostim onset/duration from trial-start coordinates to go-centered coordinates; emit binary `0/1` per bin center for photostim on/off" (CONVERSION_NOTES.md:211)
> "`photostim_definition`: Binary per-bin input from trial-table photostim onset/duration converted to go coordinates" (convert_data.py:541)
> "Confirmed `photostim_on` handles `N/A` values as all-zero vectors." (CONVERSION_NOTES.md:427)

**Code** (convert_data.py:215-232):
```python
def build_photostim_matrix(
    photostim_onset_str: np.ndarray,
    photostim_duration_str: np.ndarray,
    start_times: np.ndarray,
    go_times: np.ndarray,
) -> np.ndarray:
    onset_trial = parse_optional_float_array(photostim_onset_str)
    duration = parse_optional_float_array(photostim_duration_str)
    go_minus_start = go_times - start_times
    onset_rel_go = onset_trial - go_minus_start
    offset_rel_go = onset_rel_go + duration

    stim = np.zeros((len(go_times), N_BINS), dtype=np.float16)
    valid = np.isfinite(onset_rel_go) & np.isfinite(offset_rel_go)
    for trial_idx in np.where(valid)[0]:
        mask = (REL_CENTERS >= onset_rel_go[trial_idx]) & (REL_CENTERS < offset_rel_go[trial_idx])
        stim[trial_idx, mask] = 1.0
    return stim
```

**What this does:** Onset and duration strings are parsed to floats with `"N/A"` becoming NaN; onset is shifted from trial-start to go-cue coordinates by subtracting `go_time - start_time`, and offset is onset plus duration. A per-trial boolean mask marks bin centers in `[onset_rel_go, offset_rel_go)` as `1.0` in a `float16` zeros matrix; NaN (non-stim) trials stay all-zero. The result becomes row 1 of `input` (`input_names[1] = "photostim_on"`, convert_data.py:515) and is subset by `nonzero_trial_mask` at line 425.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `input` *photostim* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Convert photostimulation onset/offset from trial-start coordinates into go-aligned coordinates during conversion." (CONVERSION_NOTES.md:192)
> "Conversion also centers everything on go cue and converts photostimulation timing into go-centered coordinates." (CONVERSION_NOTES.md:412)
> "Photostimulation vector for session `sub-440956_ses-20190207T120657_behavior+ecephys+ogen`, trial `44` matched direct recomputation from raw `photostim_onset`, `photostim_duration`, `start_time`, and `go_time`." (CONVERSION_NOTES.md:391)

**Code** (convert_data.py:223-231, 425, 442):
```python
    go_minus_start = go_times - start_times
    onset_rel_go = onset_trial - go_minus_start
    offset_rel_go = onset_rel_go + duration

    stim = np.zeros((len(go_times), N_BINS), dtype=np.float16)
    valid = np.isfinite(onset_rel_go) & np.isfinite(offset_rel_go)
    for trial_idx in np.where(valid)[0]:
        mask = (REL_CENTERS >= onset_rel_go[trial_idx]) & (REL_CENTERS < offset_rel_go[trial_idx])
        stim[trial_idx, mask] = 1.0
...
            input_stim = input_stim[nonzero_trial_mask]
...
        input_trial = np.vstack([input_time[trial_idx], input_stim[trial_idx]]).astype(np.float16)
```

**What this does:** Per-trial stim onset/offset are converted into the same go-cue-relative coordinate frame as the neural bins, then thresholded against `REL_CENTERS`, giving a shape-`(n_trials, 80)` binary array on the identical go-aligned 50 ms grid as `neural`. Trials dropped by the nonzero-spike mask are removed from `input_stim` too, keeping trial ordering matched.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`intervals/trials/trial_instruction`, `intervals/trials/outcome`, lick events → `output[0]` (`choice`)" (CONVERSION_NOTES.md:212)

**Code** (convert_data.py:357-376):
```python
        trial_instruction = decode_str_array(trials["trial_instruction"])[valid_trial_mask]
        outcome_str = decode_str_array(trials["outcome"])[valid_trial_mask]
        ...
        outcome_code = np.array([{"ignore": 0, "miss": 1, "hit": 2}[x] for x in outcome_str], dtype=np.int16)
        ...
        left_lick_times = f["acquisition/BehavioralEvents/left_lick_times/timestamps"][()].astype(np.float64)
        right_lick_times = f["acquisition/BehavioralEvents/right_lick_times/timestamps"][()].astype(np.float64)
        choice_code = build_choice_array(
            trial_instruction=trial_instruction,
            outcome_code=outcome_code,
            start_times=start_times,
            go_times=go_times,
            stop_times=stop_times,
            left_lick_times=left_lick_times,
            right_lick_times=right_lick_times,
        )
```

**What this does:** Choice derives from `trial_instruction`, `outcome`, trial `start_time`/`stop_time`, `go_start_times`, and `left_lick_times`/`right_lick_times`.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Encode left=`0`, right=`1`; for `hit`, use instructed side; for `miss`, use opposite side; for `ignore`, use first post-go lick side if present, else first lick side anywhere in trial if present, else fall back to instructed side" (CONVERSION_NOTES.md:212)

**Code** (convert_data.py:183-212):
```python
def build_choice_array(...):
    choice = np.zeros(len(trial_instruction), dtype=np.int16)
    instructed = np.where(trial_instruction == "left", 0, 1).astype(np.int16)

    hit_mask = outcome_code == 2
    miss_mask = outcome_code == 1
    ignore_mask = outcome_code == 0

    choice[hit_mask] = instructed[hit_mask]
    choice[miss_mask] = 1 - instructed[miss_mask]

    ignore_trials = np.where(ignore_mask)[0]
    for trial_idx in ignore_trials:
        choice[trial_idx] = lick_choice_with_fallback(
            left_times=left_lick_times,
            right_times=right_lick_times,
            start_time=float(start_times[trial_idx]),
            go_time=float(go_times[trial_idx]),
            stop_time=float(stop_times[trial_idx]),
            instructed_choice=int(instructed[trial_idx]),
        )
    return choice
```

**What this does:** Hits inherit instructed side, misses get opposite side, ignores fall back to first post-go lick side, then any in-trial lick side, then instructed side. Result is `int16` repeated across all 80 bins per trial.

**Rating:** incorrect

**Note:** returns left or right for ignore

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`intervals/trials/outcome` → `output[1]` (`outcome`): Map `ignore -> 0`, `miss -> 1`, `hit -> 2`" (CONVERSION_NOTES.md:213)

**Code** (convert_data.py:358, 363):
```python
        outcome_str = decode_str_array(trials["outcome"])[valid_trial_mask]
        ...
        outcome_code = np.array([{"ignore": 0, "miss": 1, "hit": 2}[x] for x in outcome_str], dtype=np.int16)
```

**What this does:** Outcome derives solely from the trial-table `outcome` column.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map `ignore -> 0`, `miss -> 1`, `hit -> 2`" (CONVERSION_NOTES.md:213)

**Code** (convert_data.py:363):
```python
        outcome_code = np.array([{"ignore": 0, "miss": 1, "hit": 2}[x] for x in outcome_str], dtype=np.int16)
```

**What this does:** Single dictionary lookup mapping the three string outcome categories to `int16` codes.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *early_lick* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`intervals/trials/early_lick` → `output[2]` (`early_lick`)" (CONVERSION_NOTES.md:214)

**Code** (convert_data.py:359, 364):
```python
        early_lick_str = decode_str_array(trials["early_lick"])[valid_trial_mask]
        ...
        early_code = np.array([{"no early": 0, "early": 1}[x] for x in early_lick_str], dtype=np.int16)
```

**What this does:** Derived solely from the trial-table `early_lick` column.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *early_lick*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map `no early -> 0`, `early -> 1`" (CONVERSION_NOTES.md:214)

**Code** (convert_data.py:364):
```python
        early_code = np.array([{"no early": 0, "early": 1}[x] for x in early_lick_str], dtype=np.int16)
```

**What this does:** Direct categorical-to-int mapping.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-a. What variables in the raw data is `output` *tongue_y_position* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking` `(x, y, likelihood)` + timestamps → `output[3]`" (CONVERSION_NOTES.md:215)

**Code** (convert_data.py:386-391):
```python
        tongue_ts = f["acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking"]
        tongue_data = tongue_ts["data"][()]
        tongue_x = tongue_data[:, 0]
        tongue_y = tongue_data[:, 1]
        tongue_likelihood = tongue_data[:, 2]
        tongue_timestamps = tongue_ts["timestamps"][()].astype(np.float64)
```

**What this does:** Derived from the side-camera tongue-tracking series (`x`, `y`, `likelihood`) and its timestamps; also uses go times for alignment.

**Rating:** match

**Note:** _(no note)_

---

## Q 8-b. What processing is involved in computing `output` *tongue_y_position*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "5-sigma velocity outlier interpolation, low-likelihood frames set to mean visible y, last-frame-carried-forward alignment to bin centers, per-session 40th/60th percentile discretization" (convert_data.py:545-548)

**Code** (convert_data.py:134-169, 392-401, 430-433):
```python
def clean_tongue_tracking(x, y, likelihood):
    ...
    speed[1:] = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
    speed_threshold = float(np.nanmean(speed) + 5.0 * np.nanstd(speed))
    outlier_mask = ~np.isfinite(x) | ~np.isfinite(y) | (speed > speed_threshold)
    ...
    x[outlier_mask] = np.interp(frame_idx[outlier_mask], frame_idx[keep_mask], x[keep_mask])
    y[outlier_mask] = np.interp(frame_idx[outlier_mask], frame_idx[keep_mask], y[keep_mask])
    visible_mask = np.isfinite(likelihood) & (likelihood >= TONGUE_LIKELIHOOD_THRESHOLD)
    mean_y = float(np.nanmean(y[visible_mask])) if np.any(visible_mask) else float(np.nanmean(y))
    y[occluded_mask] = mean_y
...
        cleaned_tongue_y, _ = clean_tongue_tracking(...)
        aligned_tongue_y = align_tongue_y(timestamps=tongue_timestamps, cleaned_y=cleaned_tongue_y, go_times=go_times)
...
        q40, q60 = np.percentile(aligned_tongue_y.reshape(-1), [40, 60])
        tongue_disc = np.ones(aligned_tongue_y.shape, dtype=np.int16)
        tongue_disc[aligned_tongue_y < q40] = 0
        tongue_disc[aligned_tongue_y > q60] = 2
```

**What this does:** Cleans tongue trace by interpolating 5-sigma velocity outliers and replacing low-likelihood (<0.9) frames with mean-visible-y, aligns by last-frame-carried-forward at go-centered bin centers, then discretizes per-session into 3 classes via 40/60 percentile thresholds.

**Rating:** ok

**Note:** _(no note)_

---

## Q 8-c. How is `output` *tongue_y_position* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying output over 80 bins" (CONVERSION_NOTES.md:215)

**Code** (convert_data.py:172-180):
```python
def align_tongue_y(
    timestamps: np.ndarray,
    cleaned_y: np.ndarray,
    go_times: np.ndarray,
) -> np.ndarray:
    abs_centers = go_times[:, None] + REL_CENTERS[None, :]
    idx = np.searchsorted(timestamps, abs_centers, side="right") - 1
    idx = np.clip(idx, 0, len(timestamps) - 1)
    return cleaned_y[idx]
```

**What this does:** For each trial, computes absolute bin-center times = `go_time + REL_CENTERS`, then `searchsorted` picks the most recent tracking sample (last-frame-carried-forward) at each of the 80 go-aligned bin centers, matching the neural binning grid.

**Rating:** match

**Note:** _(no note)_

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Confirmed `photostim_on` handles `N/A` values as all-zero vectors." (CONVERSION_NOTES.md:427)

**Code** (convert_data.py:76-82, 134-161, 215-232, 330-331, 339-340):
```python
def parse_optional_float_array(strings: np.ndarray) -> np.ndarray:
    out = np.full(strings.shape, np.nan, dtype=np.float64)
    for i, value in enumerate(strings):
        if value == "N/A":
            continue
        out[i] = float(value)
    return out
...
    speed_threshold = float(np.nanmean(speed) + 5.0 * np.nanstd(speed))
    outlier_mask = ~np.isfinite(x) | ~np.isfinite(y) | (speed > speed_threshold)
    ...
    if np.sum(keep_mask) >= 2:
        x[outlier_mask] = np.interp(frame_idx[outlier_mask], frame_idx[keep_mask], x[keep_mask])
    ...
    y[occluded_mask] = mean_y
...
    valid = np.isfinite(onset_rel_go) & np.isfinite(offset_rel_go)
    for trial_idx in np.where(valid)[0]:
        mask = (REL_CENTERS >= onset_rel_go[trial_idx]) & (REL_CENTERS < offset_rel_go[trial_idx])
        stim[trial_idx, mask] = 1.0
...
        if len(good_unit_indices) == 0:
            raise ValueError(f"Session {session_id} has no good units")
        ...
        if len(go_times_all) != n_trials_raw:
            raise ValueError(...)
```

**What this does:** Photostim `"N/A"` strings become NaN and skipped (zero stim vector). Tongue x/y NaNs and 5-sigma velocity outliers are linearly interpolated; low-likelihood frames replaced by mean visible y. Sessions with no good units or trial-count mismatches raise. Ignore trials missing a post-go lick fall back through any-trial-lick, then instructed side. All-zero spike trials and trials outside `obs_intervals` are dropped.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sample conversion observed `0.6-0.8 s / session`... Full conversion runtime was `7.24 min`" (CONVERSION_NOTES.md:312, 370)

**Code** (convert_data.py:235-252, 403-412, 247-251):
```python
def bin_spikes_to_firing_rates(...):
    ...
    for i, unit_idx in enumerate(good_unit_indices):
        spikes = spike_times_flat[start_index[unit_idx]: spike_times_index[unit_idx]]
        edge_idx = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_edges)
        counts = np.diff(edge_idx, axis=1)
        firing_rates[i] = (counts / BIN_SIZE_S).astype(np.float16)
```

**What this does:** Per-session timing notes attribute the bulk of cost to the per-good-unit spike-binning loop (`bin_spikes_to_firing_rates`), with NWB I/O (`spike_times[()]`, `tongue_data[()]`) and final pickle write also non-trivial.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Kept all heavy operations vectorized in NumPy... Used search-sorted spike binning on per-unit spike vectors rather than per-bin Python loops." (CONVERSION_NOTES.md:267-269)

**Code** (convert_data.py:65-73, 247-252, 229-232, 441-452):
```python
def decode_str_array(ds):
    ...
    for x in arr:
        if isinstance(x, bytes):
            out.append(x.decode("utf-8"))
        ...
...
    for i, unit_idx in enumerate(good_unit_indices):
        spikes = spike_times_flat[start_index[unit_idx]: spike_times_index[unit_idx]]
        edge_idx = np.searchsorted(spikes, flat_edges, side="left").reshape(n_trials, n_edges)
...
    for trial_idx in np.where(valid)[0]:
        mask = (REL_CENTERS >= onset_rel_go[trial_idx]) & (REL_CENTERS < offset_rel_go[trial_idx])
        stim[trial_idx, mask] = 1.0
...
    for trial_idx in range(n_trials):
        input_trial = np.vstack([input_time[trial_idx], input_stim[trial_idx]]).astype(np.float16)
        output_trial = np.vstack([...])
```

**What this does:** Remaining Python loops: per-unit binning loop, per-string `decode_str_array` and outcome/early dict comprehensions, per-trial photostim mask assignment, per-trial output_trial construction, per-ignore-trial choice fallback, and per-unit region indexing in `build_dataset`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reused aligned bin-center arrays and session-level tongue thresholds instead of recomputing them per trial." (CONVERSION_NOTES.md:271)

**Code** (convert_data.py:85-95, 215-225, 454-458):
```python
def get_nwb_files(sample_only: bool) -> list[Path]:
    files = sorted(DATA_DIR.glob("sub-*/*.nwb"))
    valid = []
    for path in files:
        with h5py.File(path, "r") as f:
            good = decode_str_array(f["units/classification"]) == "good"
            if np.any(good):
                valid.append(path)
...
def build_photostim_matrix(...):
    onset_trial = parse_optional_float_array(photostim_onset_str)
    duration = parse_optional_float_array(photostim_duration_str)
    go_minus_start = go_times - start_times
    onset_rel_go = onset_trial - go_minus_start
...
    onset_trial = parse_optional_float_array(photostim_onset_str)
    go_minus_start = go_times - start_times
    onset_rel_go = onset_trial - go_minus_start
    photostim_onsets_rel_go = onset_rel_go[np.isfinite(onset_rel_go)]
```

**What this does:** Each NWB file is opened twice (once in `get_nwb_files` to test for good units, again in `process_session`); `parse_optional_float_array(photostim_onset_str)` and `onset_rel_go` are computed inside `build_photostim_matrix` and again at the diagnostics block. `decode_str_array` is also called against `units/classification` in both passes.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none directly identifying discarded work)

**Code** (convert_data.py:266-314, 460-478, 134-145):
```python
def make_session_plot(result, out_path):
    ...
    fig, ax = plt.subplots(3, 2, figsize=(16, 12))
    ...
    fig.savefig(out_path, dpi=150)
...
    diagnostics = {
        "tracking_preview_time": tongue_timestamps[:preview_n] - go_times[0],
        "tracking_preview_raw": tongue_y[:preview_n],
        ...
    }
...
    speed = np.zeros_like(x)
    if len(x) > 1:
        speed[1:] = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
```

**What this does:** Diagnostics dict (tracking previews, photostim onsets, q40/q60, timing) is built but not stored in the pickle. `clean_tongue_tracking` cleans `x` even though only `y` is used downstream. Per-session diagnostic plots are produced under `--show-processing` but unused by the decoder.

**Rating:** ok

**Note:** _(no note)_

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "used `float16` for stored neural/input arrays and `int16` for outputs to reduce pickle size." (CONVERSION_NOTES.md:269)

**Code** (convert_data.py:3, 245-251, 378, 227, 435-437):
```python
import gc
...
    firing_rates = np.empty((len(good_unit_indices), n_trials, n_edges - 1), dtype=np.float16)
    ...
        firing_rates[i] = (counts / BIN_SIZE_S).astype(np.float16)
...
    input_time = np.tile((REL_CENTERS - TONE_ONSET_REL_GO_S).astype(np.float16), (n_trials, 1))
...
    stim = np.zeros((len(go_times), N_BINS), dtype=np.float16)
...
    neural_trials = [firing_rates[:, i, :].copy() for i in range(n_trials)]
    del firing_rates
    gc.collect()
```

**What this does:** Stores neural firing rates and input vectors as `float16` and outputs/codes as `int16`; explicit `del firing_rates` + `gc.collect()` after copying per-trial slices to release the dense session array; sessions are processed sequentially rather than all in memory at once.

**Rating:** ok

**Note:** _(no note)_

---
