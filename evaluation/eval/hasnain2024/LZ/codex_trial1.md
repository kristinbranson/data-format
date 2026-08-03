# hasnain2024 — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/hasnain2024/codex/2026-03-21__11-04-17_trial1/verifier/snapshot/`

Outputs identified (K=6): lick_direction, behavioral_context, outcome, tongue_velocity_bin, paw_velocity_bin, motion_energy_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Parses the reference ALM session loader scripts to recover the analyzed session list and probe selections." (Step 6, lines 248-250)
> "Retain only the 44 code-selected ALM sessions present in `data/`" (line 220)

**Code** (convert_data.py:167-204, 929-944):
```python
def parse_reference_session_specs(code_dir: Path, data_dir: Path) -> list[SessionSpec]:
    data_files = find_data_files(data_dir)
    specs: list[SessionSpec] = []
    loader_dir = code_dir / "DataLoadingScripts" / "Recording and video"
    for loader in sorted(loader_dir.glob("load*_ALMVideo.m")):
        loader_subject = loader.name.split("_")[0].replace("load", "")
        ...
            if {"subject", "date", "probes"} <= current.keys():
                key = (current["subject"], current["date"])
                if key in data_files:
                    path = data_files[key]
                    specs.append(SessionSpec(...))
    return specs
...
specs = parse_reference_session_specs(code_dir, data_dir)
log(f"Found {len(specs)} reference-selected sessions available in data/")
...
data = build_dataset(specs, show_processing=args.show_processing, outdir=root)
```

**What this does:** Parses the reference MATLAB loader scripts (`load*_ALMVideo.m`) to extract the analyzed session list with subject/date/probe assignments, intersects it with available `data_structure_*.mat` files, and iterates `build_dataset` over each spec (one session at a time).

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Animal IDs from filenames / loader scripts → `subjects`, `subject_idx`. Build unique subject list across retained sessions" (line 216)

**Code** (convert_data.py:843-845, 862-863):
```python
if session["subject"] not in subject_names:
    subject_names.append(session["subject"])
subject_index.append(subject_names.index(session["subject"]))
...
"subjects": subject_names,
"subject_idx": np.asarray(subject_index, dtype=np.int64),
```

**What this does:** Subjects are extracted from each `SessionSpec.subject` (parsed from the loader script filename). A unique subject name list is accumulated and per-session integer indices into that list are stored in `subject_idx`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use only the 44 sessions in the intersection of reference loader lists and available data files" (line 208)

**Code** (convert_data.py:826-856):
```python
def build_dataset(session_specs: list[SessionSpec], show_processing: bool, outdir: Path) -> dict:
    neural = []
    inputs = []
    outputs = []
    ...
    for spec in session_specs:
        session = convert_one_session(spec, show_processing=show_processing, outdir=outdir)
        if session is None:
            continue
        neural.append(session["neural"])
        inputs.append(session["input"])
        outputs.append(session["output"])
        ...
        session_info.append({
            "session_id": session["session_id"],
            "subject": session["subject"], ...
        })
```

**What this does:** Each session is processed independently in `convert_one_session` and the per-session lists of `neural`, `input`, `output` arrays are appended to the top-level dataset lists (one entry per retained session). Session metadata is also recorded in `metadata.session_info`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "output one `(n_neurons, n_timepoints)` matrix per trial" (line 208)
> "Represent trial-level categorical outputs as constant time series" (line 226)

**Code** (convert_data.py:768-794):
```python
input_trials = []
output_trials = []
final_neural = []
for local_idx, trial_idx in enumerate(selected_trials):
    neural_arr = np.stack(neural_trials[local_idx], axis=0).astype(np.float32)
    final_neural.append(neural_arr)
    input_trials.append(time_vec[None, :].astype(np.float32))
    lick_direction = np.int64(1 if raw["R"][trial_idx] == 1 else 0)
    context = np.int64(1 if raw["autowater"][trial_idx] == 0 else 0)
    outcome = np.int64(1 if raw["hit"][trial_idx] == 1 else 0)
    output_arr = np.vstack([...])
    output_trials.append(output_arr)
```

**What this does:** Iterates over `selected_trials` (raw trial indices that pass the valid-trial mask) and produces one neural matrix, one input matrix, and one output matrix per trial. Trial alignment uses raw trial index `trial_idx` to read R/autowater/hit fields and converts them to per-trial output arrays.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Filters to non-stim, non-early hit/miss trials" (Step 6, line 253)
> "Exclude stimulation, early-lick, and ignore/no-response trials" (line 222)

**Code** (convert_data.py:629-635, 702-712):
```python
def session_valid_trial_mask(raw: dict) -> np.ndarray:
    return (
        (raw["stim_enable"] == 0)
        & (raw["early"] == 0)
        & ((raw["hit"] == 1) | (raw["miss"] == 1))
        & ((raw["R"] == 1) | (raw["L"] == 1))
    )
...
valid = session_valid_trial_mask(raw)
selected_trials = np.flatnonzero(valid)
covered_trial_max = [int(np.nanmax(unit["trial"])) for unit in raw["units"]
    if good_quality(unit["quality"]) and np.asarray(unit["trial"]).size]
if covered_trial_max:
    max_neural_trial = min(raw["R"].size, max(covered_trial_max))
    selected_trials = selected_trials[selected_trials + 1 <= max_neural_trial]
if selected_trials.size < 2:
    log(f"SKIP {spec.session_id}: only ...")
    return None
```

**What this does:** Trials are kept if `stim_enable==0`, `early==0`, hit-or-miss, and R-or-L. Additionally trials whose raw index exceeds the max neural unit trial coverage are dropped. Sessions with <2 valid trials are skipped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Code-selected ALM probe from `load*_ALMVideo.m` + `obj.clu{probe}` spike times" (line 208)
> "Use the ALM-designated probe only for each retained session" (line 221)

**Code** (convert_data.py:316-334, 388-403):
```python
clu = obj.clu
...
units = []
for probe_idx in spec.probes:
    probe = probes[probe_idx - 1]
    for unit in np.asarray(probe).reshape(-1):
        units.append({
            "quality": mat_to_str(getattr(unit, "quality", "")),
            "trialtm": np.asarray(getattr(unit, "trialtm"), dtype=np.float64).reshape(-1),
            "trial": np.asarray(getattr(unit, "trial"), dtype=np.int64).reshape(-1),
        })
```

**What this does:** Neural data are derived from `obj.clu{probe}` per-spike fields `trialtm` (within-trial time) and `trial` (trial index), plus `quality` strings, restricted to the ALM-designated probe per session.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Selected ALM probe, bad-label exclusion, goCue alignment, 5 ms binning, causal Gaussian smoothing, FR > 1 Hz" (line 892, metadata.neural_processing)

**Code** (convert_data.py:604-618):
```python
def compute_unit_trial_matrix(unit, go_cue, trial_to_pos, n_sel, time_edges):
    aligned = unit["trialtm"] - go_cue[unit["trial"] - 1]
    trial_pos = trial_to_pos[unit["trial"] - 1]
    keep = ((trial_pos >= 0) & np.isfinite(aligned)
            & (aligned >= time_edges[0]) & (aligned < time_edges[-1]))
    mat = np.zeros((n_sel, time_edges.size - 1), dtype=np.float64)
    if np.any(keep):
        bins = np.floor((aligned[keep] - time_edges[0]) / DT).astype(np.int64)
        np.add.at(mat, (trial_pos[keep], bins), 1.0 / DT)
    mat = my_smooth(mat.T, SMOOTH, BCTYPE).T
    return mat
```

**What this does:** Per-unit spike times are aligned to `goCue`, vector-binned with 5 ms bins (DT=1/200) over [-2.5, 2.5] s into a (trials × bins) matrix scaled to Hz, then smoothed with a causal Gaussian kernel (SMOOTH=15, reflect padding) reimplementing the reference `mySmooth`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "use all non-garbage manually curated units on the selected ALM probe, then apply a 1 Hz FR threshold" (line 225)

**Code** (convert_data.py:497-499, 724-739):
```python
def good_quality(label: str) -> bool:
    label = label.strip().lower()
    return label not in {"garbage", "gabrga", "noisy", "real?"}
...
for unit in raw["units"]:
    if not good_quality(unit["quality"]):
        continue
    unit_mat = compute_unit_trial_matrix(...)
    if float(unit_mat.mean()) <= LOW_FR_HZ:
        continue
    kept_units += 1
    ...
if kept_units < 10:
    log(f"SKIP {spec.session_id}: only {kept_units} units after quality/FR filtering")
    return None
```

**What this does:** Two-stage filter: (1) drop units whose `quality` label is in {garbage, gabrga, noisy, real?}; (2) drop units whose mean firing rate over the binned/smoothed matrix is ≤ 1 Hz. Sessions retaining <10 units are skipped.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use `goCue` as the universal alignment event" (line 223)
> "go cue onset (stored bp.ev.goCue for every trial)" (line 889, metadata.temporal_alignment_event)

**Code** (convert_data.py:23, 604-606, 729):
```python
ALIGN_EVENT = "goCue"
...
def compute_unit_trial_matrix(unit, go_cue, trial_to_pos, n_sel, time_edges):
    aligned = unit["trialtm"] - go_cue[unit["trial"] - 1]
    trial_pos = trial_to_pos[unit["trial"] - 1]
...
unit_mat = compute_unit_trial_matrix(unit, raw["events"]["goCue"], trial_to_pos, selected_trials.size, time_edges)
```

**What this does:** Each spike's within-trial time `trialtm` is shifted by subtracting that trial's `bp.ev.goCue` value, producing times relative to go-cue onset before binning over [-2.5, 2.5] s.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "tentatively prefer the paper/code-aligned 5 ms default" (line 195)
> "fixed window of `[-2.5, 2.5] s` around `goCue` with a 5 ms bin (`dt = 1/200`)" (line 224)

**Code** (convert_data.py:18-21, 718-719, 615-617):
```python
TMIN = -2.5
TMAX = 2.5
DT = 1.0 / 200.0
SMOOTH = 15
...
time_edges = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
time_vec = time_edges[:-1] + DT / 2.0
...
bins = np.floor((aligned[keep] - time_edges[0]) / DT).astype(np.int64)
np.add.at(mat, (trial_pos[keep], bins), 1.0 / DT)
```

**What this does:** Spike times are binned into 5 ms bins (DT = 1/200 s) over the window [-2.5, 2.5] s relative to goCue, yielding 1000 timepoints. Counts are divided by DT to get Hz, then convolved with a causal Gaussian kernel (length 15).

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_go_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:209 — `| `obj.time` / aligned bin centers relative to `goCue` | `input[0]` | Continuous time-from-go-cue vector repeated for every trial: shape `(1, n_timepoints)` | `getSeq` | Decoder input requested by user |`
> CONVERSION_NOTES.md:198 — "`obj.bp.ev.goCue` exists for all inspected sessions... Use the stored `bp.ev.goCue` field for all trials as the universal alignment event in the converted dataset."
> CONVERSION_NOTES.md:406-408 — "Reference trial time base is `obj.time` relative to the align event. / Converter stores that same time base as `time_from_go_cue_s`."

**Code** (convert_data.py:18-23, 371-374, 718-719):
```python
TMIN = -2.5
TMAX = 2.5
DT = 1.0 / 200.0
SMOOTH = 15
LOW_FR_HZ = 1.0
ALIGN_EVENT = "goCue"
...
            "goCue": np.asarray(bp.ev.goCue, dtype=np.float64).reshape(-1),
...
    time_edges = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
    time_vec = time_edges[:-1] + DT / 2.0
```

**What this does:** The input is a time axis built from the module constants `TMIN`/`TMAX`/`DT` (-2.5 to 2.5 s, 5 ms bins) rather than read per trial from a raw field; the raw variable that anchors it is `obj.bp.ev.goCue`, which is the event subtracted from spike times so that bin centers mean "time from go cue". It is named `time_from_go_cue_s` in `input_names`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_go_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:279 — `| `time_from_go_cue_s` range | [-2.5, 2.5] |`
> CONVERSION_NOTES.md:354 — "`params.tmin = -2.5`, `params.tmax = 2.5` in default pipeline | [-2.5, 2.5]"
> CONVERSION_NOTES.md:387-389 — "Independently constructed the go-cue-centered time axis `[-2.4975, ..., 2.4975]` from the reference window/bin definition and compared against `input[0]`. Result: `np.allclose = True`, max absolute difference `0.0`."

**Code** (convert_data.py:718-719, 768-774, 866):
```python
    time_edges = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
    time_vec = time_edges[:-1] + DT / 2.0
...
    input_trials = []
    output_trials = []
    final_neural = []
    for local_idx, trial_idx in enumerate(selected_trials):
        neural_arr = np.stack(neural_trials[local_idx], axis=0).astype(np.float32)
        final_neural.append(neural_arr)
        input_trials.append(time_vec[None, :].astype(np.float32))
...
        "input_names": ["time_from_go_cue_s"],
```

**What this does:** Bin edges are created with `np.arange(TMIN, TMAX + DT, DT)` and the time vector is the bin centers (`edges[:-1] + DT/2`), giving 1000 values from -2.4975 to 2.4975 s. The same `time_vec` is cast to float32, reshaped to `(1, n_timepoints)`, and appended once per selected trial, so every trial in every session carries an identical single-row input.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_go_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:239 — "[ ] Check that all trials in the converted dataset share the same time vector and that `input[0]` matches the neural bin centers exactly."
> CONVERSION_NOTES.md:198 — "Use the stored `bp.ev.goCue` field for all trials as the universal alignment event in the converted dataset."

**Code** (convert_data.py:604-615, 718-719, 729, 774):
```python
def compute_unit_trial_matrix(unit, go_cue, trial_to_pos, n_sel, time_edges):
    aligned = unit["trialtm"] - go_cue[unit["trial"] - 1]
    ...
        & (aligned >= time_edges[0])
        & (aligned < time_edges[-1])
    mat = np.zeros((n_sel, time_edges.size - 1), dtype=np.float64)
        bins = np.floor((aligned[keep] - time_edges[0]) / DT).astype(np.int64)
...
    time_edges = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
    time_vec = time_edges[:-1] + DT / 2.0
...
        unit_mat = compute_unit_trial_matrix(unit, raw["events"]["goCue"], trial_to_pos, selected_trials.size, time_edges)
...
        input_trials.append(time_vec[None, :].astype(np.float32))
```

**What this does:** The neural matrix is built by histogramming go-cue-subtracted spike times into the same `time_edges` used to derive `time_vec`, so the input row is by construction the bin centers of the neural array and has the same length (`time_edges.size - 1`). Metadata records `temporal_alignment_event = "go cue onset (stored bp.ev.goCue for every trial)"` with `off_start`/`off_end` of -2.5/2.5 s.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *lick_direction* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`bp.R`, `bp.L` → `output[0]`. Lick direction: left `0`, right `1`" (line 210)

**Code** (convert_data.py:776):
```python
lick_direction = np.int64(1 if raw["R"][trial_idx] == 1 else 0)
```

**What this does:** Derived from `obj.bp.R` (right-lick trial flag); 1 if R==1 else 0.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "encode as a constant time series over the trial window" (line 210)

**Code** (convert_data.py:776, 779-782):
```python
lick_direction = np.int64(1 if raw["R"][trial_idx] == 1 else 0)
output_arr = np.vstack([
    np.full(time_vec.size, lick_direction, dtype=np.int64),
    ...
])
```

**What this does:** Scalar per-trial label (0/1) is broadcast into a constant time series over all 1000 timepoints and stacked as the first row of the output array.

**Rating:** incorrect

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *context* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`bp.autowater` → `output[1]`. Behavioral context: WC `0`, DR `1` via `1 - autowater`" (line 211)

**Code** (convert_data.py:777):
```python
context = np.int64(1 if raw["autowater"][trial_idx] == 0 else 0)
```

**What this does:** Derived from `obj.bp.autowater`. Context is 1 (DR) when autowater==0, else 0 (WC).

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *context*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "constant time series over the trial window" (line 211)

**Code** (convert_data.py:777, 779-783):
```python
context = np.int64(1 if raw["autowater"][trial_idx] == 0 else 0)
output_arr = np.vstack([
    ...,
    np.full(time_vec.size, context, dtype=np.int64),
    ...
])
```

**What this does:** Per-trial 0/1 scalar broadcast to all timepoints as the second output row.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`bp.hit`, `bp.miss` → `output[2]`. Outcome: miss `0`, hit `1`" (line 212)

**Code** (convert_data.py:778):
```python
outcome = np.int64(1 if raw["hit"][trial_idx] == 1 else 0)
```

**What this does:** Derived from `obj.bp.hit`. 1 if hit==1, else 0.

**Rating:** incorrect

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "constant time series over the trial window" (line 212)

**Code** (convert_data.py:778, 779-784):
```python
outcome = np.int64(1 if raw["hit"][trial_idx] == 1 else 0)
output_arr = np.vstack([
    ...,
    np.full(time_vec.size, outcome, dtype=np.int64),
    ...
])
```

**What this does:** Scalar 0/1 broadcast to all timepoints as the third output row.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Compute tongue speed as `sqrt(tongue_xvel_view1^2 + tongue_yvel_view1^2)` after reference interpolation/fill rules" (line 213)

**Code** (convert_data.py:741-746):
```python
tongue_pos = feature_xy(raw, 0, "tongue", raw["events"]["goCue"], time_vec)
tongue_speed = feature_speed(*tongue_pos, "tongue")
tongue_valid = np.isfinite(tongue_pos[0]) & np.isfinite(tongue_pos[1])
tongue_speed = tongue_speed.astype(np.float64, copy=False)
tongue_speed[~tongue_valid] = np.nan
```

**What this does:** Derived from side-view (`obj.traj[0]`) `tongue` DLC marker x/y trajectories (`ts`), `frameTimes`, and bitcode-derived video offset (from `obj.sglx.bitcode.bitstart` and `bp.ev.bitStart`).

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "binarize by session median over all kept samples" (line 213)
> "computing the tongue percentile on visible frames only and assigning non-visible frames to bin `0`" (line 295)

**Code** (convert_data.py:760-790):
```python
tongue_sel = tongue_speed[:, selected_trials]
...
tongue_thr = summarize_threshold(tongue_sel)
...
np.where(
    np.isfinite(tongue_sel[:, local_idx]),
    tongue_sel[:, local_idx] >= tongue_thr,
    0,
).astype(np.int64),
```

**What this does:** x/y position aligned to goCue via interpolation and video-offset correction, speed = sqrt(dx^2 + dy^2) via `np.gradient`. NaNs preserved on invalid tongue frames. Then binarized at the session 50th-percentile (computed only on finite samples), with non-visible frames assigned bin 0.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 7-d. How is `output` *tongue_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "DLC/video alignment uses `frameTimes - vidshift - alignTimes(trial)`, where `vidshift` is computed from bitcode synchronization metadata" (line 56)
> "Reference-style interpolation to neural time base with video offset correction" (line 895, metadata.video_processing)

**Code** (convert_data.py:511-516, 519-540, 741-742):
```python
def find_video_offset(raw: dict) -> float:
    bitstart = np.asarray(raw["bitcode_bitstart"], dtype=np.float64).reshape(-1)
    fs = float(raw["fs"])
    if bitstart.size == 0 or not np.isfinite(fs) or fs <= 0:
        return 0.5
    return robust_mode(bitstart) / fs - robust_mode(raw["events"]["bitStart"])
...
def feature_xy(raw, view_idx, feature_name, align_times, time_vec):
    trials = raw["traj"][view_idx]
    taxis = time_vec.copy()
    vidshift = find_video_offset(raw)
    ...
    for trix, trial in enumerate(trials):
        ...
        frame_times = trial["frame_times"]
        if frame_times is None or frame_times.size == 0 or np.all(~np.isfinite(frame_times)):
            frame_times = (np.arange(ts.shape[0], dtype=np.float64) + 1.0) / 400.0
        old_t = frame_times - vidshift - align_times[trix]
        xpos[:, trix] = interp_to_taxis(old_t, ts[:, 0], taxis)
        ypos[:, trix] = interp_to_taxis(old_t, ts[:, 1], taxis)
...
tongue_pos = feature_xy(raw, 0, "tongue", raw["events"]["goCue"], time_vec)
```

**What this does:** Side-view DLC `frameTimes` are corrected by `vidshift = robust_mode(sglx.bitcode.bitstart)/fs - robust_mode(bp.ev.bitStart)` and then re-referenced to each trial's `bp.ev.goCue`; the resulting `old_t` is linearly interpolated onto the neural 5 ms time axis (`time_vec`, [-2.5, 2.5] s) via `np.interp`, sharing the same alignment as the spike binning.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Compute top- and bottom-paw speed magnitudes from x/y velocity pairs, average them per timepoint" (line 214)

**Code** (convert_data.py:747-755):
```python
paw_speeds = []
for paw_name in ("top_paw", "bottom_paw"):
    paw_pos = feature_xy(raw, 1, paw_name, raw["events"]["goCue"], time_vec)
    paw_speeds.append(feature_speed(*paw_pos, paw_name))
paw_stack = np.stack(paw_speeds, axis=0)
paw_count = np.sum(np.isfinite(paw_stack), axis=0)
paw_sum = np.nansum(paw_stack, axis=0)
paw_speed = np.divide(paw_sum, np.maximum(paw_count, 1), where=np.maximum(paw_count, 1) > 0)
paw_speed = np.nan_to_num(paw_speed, nan=0.0)
```

**What this does:** Derived from bottom-view (`obj.traj[1]`) `top_paw` and `bottom_paw` DLC markers' x/y positions, `frameTimes`, and bitcode video offset.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "binarize by session median over all kept samples" (line 214)

**Code** (convert_data.py:761-790):
```python
paw_sel = paw_speed[:, selected_trials]
...
paw_thr = summarize_threshold(paw_sel)
...
(paw_sel[:, local_idx] >= paw_thr).astype(np.int64),
```

**What this does:** Each paw's x/y position interpolated to neural time axis with video-offset correction; speed via gradient; non-tongue NaNs filled by nearest neighbor; mean over the two paws (per finite sample); session 50th percentile threshold; binary >= threshold per timepoint.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 8-d. How is `output` *paw_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "DLC/video alignment uses `frameTimes - vidshift - alignTimes(trial)`, where `vidshift` is computed from bitcode synchronization metadata" (line 56)
> "Reference-style interpolation to neural time base with video offset correction" (line 895, metadata.video_processing)

**Code** (convert_data.py:519-540, 747-750):
```python
def feature_xy(raw, view_idx, feature_name, align_times, time_vec):
    trials = raw["traj"][view_idx]
    taxis = time_vec.copy()
    vidshift = find_video_offset(raw)
    ...
    for trix, trial in enumerate(trials):
        ...
        frame_times = trial["frame_times"]
        if frame_times is None or frame_times.size == 0 or np.all(~np.isfinite(frame_times)):
            frame_times = (np.arange(ts.shape[0], dtype=np.float64) + 1.0) / 400.0
        old_t = frame_times - vidshift - align_times[trix]
        xpos[:, trix] = interp_to_taxis(old_t, ts[:, 0], taxis)
        ypos[:, trix] = interp_to_taxis(old_t, ts[:, 1], taxis)
...
for paw_name in ("top_paw", "bottom_paw"):
    paw_pos = feature_xy(raw, 1, paw_name, raw["events"]["goCue"], time_vec)
    paw_speeds.append(feature_speed(*paw_pos, paw_name))
```

**What this does:** For each paw marker, bottom-view DLC `frameTimes` are shifted by `vidshift` (derived from `sglx.bitcode.bitstart/fs` minus `bp.ev.bitStart`) and the per-trial `bp.ev.goCue`, then x/y positions are linearly interpolated onto the neural 5 ms time axis (`time_vec`, [-2.5, 2.5] s) before computing speed and averaging across the two paws.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Aligned motion-energy trace `me.data` → `output[5]`" (line 215)

**Code** (convert_data.py:288-309, 350-351):
```python
def load_motion_energy(path: Path) -> tuple[list[np.ndarray], float]:
    me = sio.loadmat(path, squeeze_me=True, struct_as_record=False)["me"]
    ...
    return data, thresh
...
me_path = spec.session_path.parent / f"motionEnergy_{spec.subject}_{spec.date}.mat"
motion_energy, motion_thresh = load_motion_energy(me_path)
```

**What this does:** Derived from per-session `motionEnergy_<subject>_<date>.mat` (`me.data` per-trial traces). Frame timing from the side-view `frameTimes`, video offset from bitcode metadata.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use aligned continuous motion energy and binarize by session median over all kept samples" (line 215)

**Code** (convert_data.py:585-601, 757-790):
```python
def aligned_motion_energy(raw, align_times, time_vec):
    me_trials = raw["motion_energy"]
    side_trials = raw["traj"][0]
    vidshift = find_video_offset(raw)
    out = np.full((time_vec.size, len(me_trials)), np.nan, dtype=np.float64)
    for trix, me in enumerate(me_trials):
        ...
        old_t = frame_times - vidshift - align_times[trix]
        out[:, trix] = interp_to_taxis(old_t, me, time_vec)
        out[:, trix] = nearest_fill_1d(out[:, trix])
    return out
...
motion = aligned_motion_energy(raw, raw["events"]["goCue"], time_vec)
motion = np.nan_to_num(motion, nan=0.0)
...
motion_thr = summarize_threshold(motion_sel)
...
(motion_sel[:, local_idx] >= motion_thr).astype(np.int64),
```

**What this does:** Per-trial `me` trace interpolated onto goCue-aligned 5 ms time axis via `np.interp` with bitcode video offset, NaNs nearest-filled then zero-filled, then binarized at session 50th-percentile.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Motion energy and DLC trajectories are not used at their native frame rate directly. They are interpolated onto the same `obj.time` axis as neural activity after correcting for video offset." (line 55)
> "Motion energy loader expects one motion-energy file per ephys session and converts it to `me.data(time, trial)` on the neural time base." (line 57)

**Code** (convert_data.py:585-601, 757):
```python
def aligned_motion_energy(raw, align_times, time_vec):
    me_trials = raw["motion_energy"]
    side_trials = raw["traj"][0]
    vidshift = find_video_offset(raw)
    out = np.full((time_vec.size, len(me_trials)), np.nan, dtype=np.float64)
    for trix, me in enumerate(me_trials):
        me = np.asarray(me, dtype=np.float64).reshape(-1)
        if me.size == 0:
            continue
        frame_times = side_trials[trix]["frame_times"] if trix < len(side_trials) else None
        if frame_times is None or frame_times.size == 0 or np.all(~np.isfinite(frame_times)):
            old_t = (np.arange(me.size, dtype=np.float64) + 1.0) / 400.0 - 0.5 - align_times[trix]
        else:
            old_t = frame_times - vidshift - align_times[trix]
        out[:, trix] = interp_to_taxis(old_t, me, time_vec)
        out[:, trix] = nearest_fill_1d(out[:, trix])
    return out
...
motion = aligned_motion_energy(raw, raw["events"]["goCue"], time_vec)
```

**What this does:** Per-trial motion-energy traces are timestamped using the side-view DLC `frameTimes` shifted by `vidshift` (`sglx.bitcode.bitstart/fs - bp.ev.bitStart`) and the trial's `bp.ev.goCue`; those `old_t` are linearly interpolated (`np.interp`) onto the same neural 5 ms time axis (`time_vec`, [-2.5, 2.5] s). When `frameTimes` is missing, the loader falls back to a synthetic 400 Hz axis offset by 0.5 s.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Nested `motionEnergy` MATLAB structs in `JEB15` sessions required recursive unwrapping" (line 371)
> "Randomized-delay `motionEnergy` files store only the per-trial traces in `me` and omit `moveThresh`" (line 372)
> "`JEB6_2021-04-18` contains an empty HDF5 probe slot before the actual ALM probe" (line 373)
> "`JEB24_...` include trailing behavioral trials with no neural coverage; conversion now drops valid behavioral trials whose raw trial index exceeds the last neural `unit.trial` index" (line 374)

**Code** (convert_data.py:99-117, 275-309, 391-395, 705-712):
```python
def nearest_fill_1d(x):
    ...
    idx = np.arange(x.size)
    x[~mask] = np.interp(idx[~mask], idx[mask], x[mask])
    return x
...
def unwrap_motion_energy_container(x):
    while hasattr(current, "data") and not isinstance(current, np.ndarray):
        current = current.data
    ...
...
if probe_idx < 1 or probe_idx > probe_refs.size:
    raise IndexError(...)
probe = f[probe_refs[probe_idx - 1]]
if not isinstance(probe, h5py.Group):
    raise IndexError(f"{spec.session_id}: probe slot {probe_idx} is empty in HDF5 file")
...
covered_trial_max = [int(np.nanmax(unit["trial"])) for unit in raw["units"]
    if good_quality(unit["quality"]) and np.asarray(unit["trial"]).size]
if covered_trial_max:
    max_neural_trial = min(raw["R"].size, max(covered_trial_max))
    selected_trials = selected_trials[selected_trials + 1 <= max_neural_trial]
```

**What this does:** Missing-position frames are nearest-neighbor-filled (non-tongue) or zeroed (tongue); motion-energy nested struct variants are recursively unwrapped; missing `moveThresh` becomes NaN; empty HDF5 probe slots raise informative errors; trailing behavioral trials without neural coverage are dropped; sessions with too few trials/units are skipped with a SKIP log.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Full recursive HDF5-to-Python loading was too slow and memory-heavy" (line 257)
> "Per-spike/per-trial histogram loops would likely be a bottleneck if implemented naively" (line 258)
> "Sample conversion (`convert_data.py --sample --show-processing`) | 4.06 s / session average ... ~3.5-5 minutes" (line 308)
> "Runtime: `135.23 s` for all 44 sessions" (line 363)

**Code** (convert_data.py:826-836):
```python
for spec in session_specs:
    session = convert_one_session(spec, show_processing=show_processing, outdir=outdir)
```

**What this does:** Sessions are processed sequentially; reported full-run time is ~135 s for 44 sessions. Per-session loading and HDF5 reads are the largest steps.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Implemented vectorized per-unit spike accumulation with `np.add.at` instead of calling a histogram inside nested trial loops" (line 262)

**Code** (convert_data.py:613-617, 90-93):
```python
mat = np.zeros((n_sel, time_edges.size - 1), dtype=np.float64)
if np.any(keep):
    bins = np.floor((aligned[keep] - time_edges[0]) / DT).astype(np.int64)
    np.add.at(mat, (trial_pos[keep], bins), 1.0 / DT)
mat = my_smooth(mat.T, SMOOTH, BCTYPE).T
...
for j in range(x_filt.shape[1]):
    out[:, j] = np.convolve(x_filt[:, j], kern, mode="same")
```

**What this does:** Spike accumulation uses `np.add.at` over all spikes vectorized; per-unit binning is single-pass. `feature_speed` and `feature_xy` loop over trials rather than fully vectorizing across trials. `my_smooth` loops over columns calling `np.convolve`.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:519-547, 585-601):
```python
def feature_xy(raw, view_idx, feature_name, align_times, time_vec):
    ...
    vidshift = find_video_offset(raw)
    ...
def aligned_motion_energy(raw, align_times, time_vec):
    ...
    vidshift = find_video_offset(raw)
```

**What this does:** `find_video_offset(raw)` is recomputed inside `feature_xy`, `feature_speed` callers, and `aligned_motion_energy`; called four times per session (tongue, two paws, motion). `feature_xy` rebuilds `taxis = time_vec.copy()` though `time_vec` is unchanged. Otherwise per-trial loops in kinematics process each trial once.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:638-696, 795-814):
```python
def plot_processing(session_id, time_vec, session_out, outdir):
    ...
    fig.savefig(outdir / f"processing_{session_id}.png", dpi=150)
...
"continuous": {
    "tongue": tongue_sel.astype(np.float32),
    "paw": paw_sel.astype(np.float32),
    "motion": motion_sel.astype(np.float32),
    "tongue_thr": tongue_thr,
    "paw_thr": paw_thr,
    "motion_thr": motion_thr,
},
```

**What this does:** When `--show-processing` is set, processing PNGs are generated per session (optional). The `session_out["continuous"]` dict carries pre-binarized continuous traces and thresholds used by the plot but not used in the final pickled top-level dataset.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Processes one session at a time to keep memory bounded" (line 263)
> "`converted_data.pkl`: 3.2 GB" (line 342)

**Code** (convert_data.py:725-735, 826-846):
```python
neural_trials = [[] for _ in range(selected_trials.size)]
for unit in raw["units"]:
    ...
    unit_mat = unit_mat.astype(np.float32)
    for trix in range(selected_trials.size):
        neural_trials[trix].append(unit_mat[trix])
...
for spec in session_specs:
    session = convert_one_session(...)
    if session is None:
        continue
    neural.append(session["neural"])
```

**What this does:** Sessions are processed serially and per-trial neural matrices are cast to float32. Final dict accumulates all session data in memory before pickling, producing a 3.2 GB output file. No streaming write path.

**Rating:** match

**Note:** _(no note)_---

---
