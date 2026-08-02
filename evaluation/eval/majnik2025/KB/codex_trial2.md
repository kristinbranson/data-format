# majnik2025 — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/majnik2025/codex/2026-03-11__11-30-50_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md lines 63-78):
> Top level contains 6 subject folders: `jm031`, `jm032`, `jm038`, `jm039`, `jm040`, `jm046`. Each subject folder contains 6 or 7 daily session folders named `YYYY-MM-DD_a`. Each session has: `suite2p/plane0/` with `F.npy`, `Fneu.npy`, ... `move_deve/` with `motion_energy_glob.npy`, `tstamps.npy`, `interframe_int.npy`.

**Code** (convert_data.py:54-63, 282-287):
```python
def discover_sessions(data_root: Path) -> list[SessionRef]:
    sessions: list[SessionRef] = []
    for subject_dir in sorted(p for p in data_root.iterdir() if p.is_dir() and p.name.startswith("jm")):
        for session_dir in sorted(
            p for p in subject_dir.iterdir() if p.is_dir() and len(p.name) >= 10 and p.name[:4].isdigit()
        ):
            sessions.append(
                SessionRef(subject=subject_dir.name, session_id=session_dir.name, path=session_dir)
            )
    return sessions
...
F = np.load(suite2p_dir / "F.npy", allow_pickle=True)
Fneu = np.load(suite2p_dir / "Fneu.npy", allow_pickle=True)
ops = np.load(suite2p_dir / "ops.npy", allow_pickle=True).item()
motion_raw = np.load(move_dir / "motion_energy_glob.npy", allow_pickle=True)
tstamps = np.load(move_dir / "tstamps.npy", allow_pickle=True)
```

**What this does:** Subjects are detected as directories under `data/` whose names start with `jm`. Sessions are subdirectories named with a date-like prefix (first 4 chars digits, length ≥ 10). For each session, `F.npy`, `Fneu.npy`, `ops.npy`, `motion_energy_glob.npy`, and `tstamps.npy` are loaded from `suite2p/plane0/` and `move_deve/`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md lines 96-102):
> Subject-level tracked neuron counts: jm031:221, jm032:370, jm038:685, jm039:746, jm040:541, jm046:435.

**Code** (convert_data.py:56, 377-386):
```python
for subject_dir in sorted(p for p in data_root.iterdir() if p.is_dir() and p.name.startswith("jm")):
...
def build_dataset(converted_sessions, session_refs):
    subjects = sorted({session.subject for session in session_refs})
    subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
    ...
    "subjects": subjects,
    "subject_idx": np.array([subject_to_idx[session.subject] for session in session_refs], dtype=np.int64),
```

**What this does:** Subjects are identified as `jm*` directories sorted alphabetically. A unique subject list and a per-session `subject_idx` array are exported.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md line 67):
> Each subject folder contains 6 or 7 daily session folders named `YYYY-MM-DD_a`.

**Code** (convert_data.py:57-62):
```python
for session_dir in sorted(
    p for p in subject_dir.iterdir() if p.is_dir() and len(p.name) >= 10 and p.name[:4].isdigit()
):
    sessions.append(
        SessionRef(subject=subject_dir.name, session_id=session_dir.name, path=session_dir)
    )
```

**What this does:** Sessions are subdirectories of each subject whose names are at least 10 characters long and begin with 4 digits (matching the `YYYY-MM-DD_a` pattern), enumerated in sorted order.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md lines 187-196):
> Trial definition: Define each trial as one consecutive 2-minute block from a continuous session, matching the paper's decoding split unit exactly. ... Use 360 time bins per trial for every session because 2 minutes / 333.3 ms = 360; 20-minute sessions contribute 10 trials, 30-minute sessions contribute 15 trials.

**Code** (convert_data.py:160-183):
```python
def split_trials(neural_binned, time_binned_s, output_one_hot, fs, bin_frames):
    bins_per_trial = int(round(TRIAL_SECONDS * fs / bin_frames))
    usable_bins = (neural_binned.shape[1] // bins_per_trial) * bins_per_trial
    if usable_bins < bins_per_trial:
        raise ValueError("Session is too short to form even one 2-minute trial.")
    neural_binned = neural_binned[:, :usable_bins]
    ...
    for start in range(0, usable_bins, bins_per_trial):
        stop = start + bins_per_trial
        neural_trials.append(neural_binned[:, start:stop].astype(np.float32, copy=False))
        input_trials.append(time_binned_s[np.newaxis, start:stop].astype(np.float32, copy=False))
        output_trials.append(output_one_hot[:, start:stop].astype(np.int64, copy=False))
```

**What this does:** Continuous recordings are split into consecutive non-overlapping 2-minute (`TRIAL_SECONDS=120.0`) blocks computed in binned units (`bins_per_trial = round(120 * fs / 10) = 360`). Any leftover bins not filling a complete trial are dropped.

**Rating:** better

**Note:** 2 min is listed in the methods, manual uses 1 min

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt:**
> (none — no explicit per-trial QC filter described)

**Code** (no relevant code found):
```python
# No trial-level QC filtering performed; all complete 2-minute blocks are kept.
```

**What this does:** No trial-level quality-control filter is applied. Every contiguous 360-bin block is exported; only the trailing partial block is discarded.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md line 181):
> `suite2p/plane0/F.npy`, `Fneu.npy`, `ops.npy` → `neural` | Neuropil subtraction using `ops['neucoeff']`, then Suite2p-style baseline correction ...

**Code** (convert_data.py:282-289):
```python
F = np.load(suite2p_dir / "F.npy", allow_pickle=True)
Fneu = np.load(suite2p_dir / "Fneu.npy", allow_pickle=True)
ops = np.load(suite2p_dir / "ops.npy", allow_pickle=True).item()
...
fs = float(ops["fs"])
neural_processed = compute_fluorescence_signal(F, Fneu, ops)
```

**What this does:** Neural data is derived from suite2p `F.npy` and `Fneu.npy` from `plane0`, with parameters (`neucoeff`, `baseline`, `win_baseline`, `sig_baseline`, `fs`, `prctile_baseline`) read from `ops.npy`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md line 188):
> Neural signal: Use neuropil-subtracted, baseline-corrected fluorescence derived from `F` and `Fneu` with Suite2p defaults from `ops.npy`, because the paper states downstream analyses used baseline-corrected fluorescence as dF/F.

**Code** (convert_data.py:76-89, 290):
```python
def compute_fluorescence_signal(F, Fneu, ops):
    """Approximate the paper's Suite2p-based dF/F signal."""
    Fc = F.astype(np.float32, copy=False) - float(ops["neucoeff"]) * Fneu.astype(np.float32, copy=False)
    processed = suite2p_preprocess(
        Fc.copy(),
        baseline=ops["baseline"],
        win_baseline=float(ops["win_baseline"]),
        sig_baseline=float(ops["sig_baseline"]),
        fs=float(ops["fs"]),
        prctile_baseline=float(ops["prctile_baseline"]),
        batch_size=min(512, max(32, Fc.shape[0])),
        device=torch.device("cpu"),
    )
    return processed.astype(np.float32, copy=False)
...
neural_binned = average_nonoverlapping(neural_processed, BIN_FRAMES).astype(np.float32, copy=False)
```

**What this does:** Neuropil subtraction is performed using `ops["neucoeff"]`, then suite2p's `dcnv.preprocess` baseline correction is applied with parameters loaded from `ops.npy`. The processed traces are then averaged in non-overlapping 10-frame bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md lines 158-160):
> Provided `suite2p` exports already have all rows passing `iscell` and the same row count across all days within a mouse... Treat provided rows as already curated tracked cells.

**Code** (no relevant code found):
```python
# No iscell filtering applied; all rows from F.npy are kept.
```

**What this does:** No additional cell filtering is applied in `convert_data.py`. The script relies on the provided suite2p exports being already curated (Track2p all-day matched and `iscell`-filtered).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md line 190):
> Apply non-overlapping 10-frame averaging before trialization for both neural and behavioral streams, matching the paper's decoding preprocessing and giving a final bin size of 333.3 ms.

**Code** (convert_data.py:22, 66-73, 290, 398):
```python
BIN_FRAMES = 10
...
def average_nonoverlapping(x, bin_frames):
    n_frames = x.shape[-1]
    usable = (n_frames // bin_frames) * bin_frames
    if usable == 0:
        raise ValueError(f"Not enough frames to bin: got {n_frames}, need at least {bin_frames}")
    x = x[..., :usable]
    new_shape = x.shape[:-1] + (usable // bin_frames, bin_frames)
    return x.reshape(new_shape).mean(axis=-1)
...
neural_binned = average_nonoverlapping(neural_processed, BIN_FRAMES)
...
"time_bin_size": float(1000.0 * BIN_FRAMES / 30.0),
```

**What this does:** Neural traces are averaged in non-overlapping 10-frame windows, reducing the 30 Hz rate to ~3 Hz (333.3 ms bin size). Frames not filling a complete 10-frame bin are truncated.

**Rating:** ok

**Note:** agent is closer to the paper which says it averages 10 timepoints

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md line 192):
> Time input meaning: Interpret "time elapsed from the beginning of the experiment" as time from the beginning of the recording session, carried through each 2-minute trial as an absolute-within-session time vector.

**Code** (convert_data.py:399-401):
```python
"temporal_alignment_event": "start of each consecutive 2-minute recording block",
"off_start": 0.0,
"off_end": float(TRIAL_SECONDS),
```

**What this does:** Trials are contiguous 2-minute blocks of the continuous recording; per-trial neural data is aligned to the start of each consecutive block. No event-based alignment is performed because the recordings are spontaneous.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

**Notes excerpt** (CONVERSION_NOTES.md line 182):
> Session frame index after 10-frame binning → `input[0]` | Convert to elapsed time from session start in seconds for each averaged bin.

**Code** (convert_data.py:156-157, 299):
```python
def make_time_input(n_bins, fs, bin_frames):
    return (np.arange(n_bins, dtype=np.float32) * (bin_frames / fs)).astype(np.float32)
...
time_binned_s = make_time_input(neural_binned.shape[1], fs=fs, bin_frames=BIN_FRAMES)
```

**What this does:** Time is computed from the binned frame index multiplied by `bin_frames / fs`, producing seconds elapsed from session start. It is not derived from any stored timestamps for the imaging stream.

**Rating:** ok

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Time*?

**Notes excerpt:**
> (none beyond construction described in 3-a)

**Code** (convert_data.py:156-157, 182):
```python
def make_time_input(n_bins, fs, bin_frames):
    return (np.arange(n_bins, dtype=np.float32) * (bin_frames / fs)).astype(np.float32)
...
input_trials.append(time_binned_s[np.newaxis, start:stop].astype(np.float32, copy=False))
```

**What this does:** A 1D vector `np.arange(n_bins) * (BIN_FRAMES/fs)` is generated once per session, then sliced per trial (each slice retains absolute within-session time, not reset to zero per trial).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md line 192):
> ... carried through each 2-minute trial as an absolute-within-session time vector.

**Code** (convert_data.py:179-183):
```python
for start in range(0, usable_bins, bins_per_trial):
    stop = start + bins_per_trial
    neural_trials.append(neural_binned[:, start:stop].astype(np.float32, copy=False))
    input_trials.append(time_binned_s[np.newaxis, start:stop].astype(np.float32, copy=False))
    output_trials.append(output_one_hot[:, start:stop].astype(np.int64, copy=False))
```

**What this does:** The same `[start:stop]` index range is used to slice neural, input time, and output arrays, so the time vector is index-aligned bin-for-bin with the neural data.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md line 183):
> `move_deve/motion_energy_glob.npy`, `tstamps.npy` → `output[0:5]` | Reconstruct motion on full imaging-frame grid using timestamps...

**Code** (convert_data.py:285-286, 292):
```python
motion_raw = np.load(move_dir / "motion_energy_glob.npy", allow_pickle=True)
tstamps = np.load(move_dir / "tstamps.npy", allow_pickle=True)
...
motion_aligned, motion_info = reconstruct_motion_trace(motion_raw, tstamps, F.shape[1])
```

**What this does:** Motion energy is derived from `motion_energy_glob.npy` plus per-sample timestamps `tstamps.npy` from the `move_deve/` subdirectory. (`interframe_int.npy` is not used.)

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

**Notes excerpt** (CONVERSION_NOTES.md line 193):
> Output discretization: Normalize motion energy within session after 10-frame averaging, then discretize into five equal-percentile bins within that session and export them as one-hot binary channels.

**Code** (convert_data.py:141-153, 293-297):
```python
def normalize_motion(x):
    xmin = float(np.min(x)); xmax = float(np.max(x))
    if xmax <= xmin:
        return np.zeros_like(x, dtype=np.float32)
    return ((x - xmin) / (xmax - xmin)).astype(np.float32)

def quintile_one_hot(x):
    edges = np.quantile(x, [0.2, 0.4, 0.6, 0.8]).astype(np.float32)
    classes = np.searchsorted(edges, x, side="right").astype(np.int64)
    one_hot = np.eye(N_OUTPUT_BINS, dtype=np.int64)[classes].T
    return one_hot, classes, edges
...
motion_binned = average_nonoverlapping(motion_aligned[np.newaxis, :], BIN_FRAMES)[0]
motion_binned_norm = normalize_motion(motion_binned)
output_one_hot, motion_classes, motion_edges = quintile_one_hot(motion_binned_norm)
```

**What this does:** Aligned motion energy is averaged in 10-frame bins, min-max normalized to [0,1] within session, then discretized into 5 equal-percentile (quintile) bins computed per session, and one-hot encoded into 5 binary channels.

**Rating:** ok

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Motion energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md line 191):
> Behavior alignment: Use `tstamps.npy` to map behavior samples onto the imaging-frame grid of length `n_imaging_frames`; missing camera frames become NaNs that are then interpolated.

**Code** (convert_data.py:92-138):
```python
def reconstruct_motion_trace(motion_energy, tstamps, n_imaging_frames):
    ...
    frame_dt = (tstamps[-1] - tstamps[0]) / (n_imaging_frames - 1)
    frame_idx = np.round((tstamps - tstamps[0]) / frame_dt).astype(np.int64)
    frame_idx = np.clip(frame_idx, 0, n_imaging_frames - 1)
    full = np.full(n_imaging_frames, np.nan, dtype=np.float32)
    counts = np.zeros(n_imaging_frames, dtype=np.int64)
    sums = np.zeros(n_imaging_frames, dtype=np.float64)
    np.add.at(sums, frame_idx, motion_energy.astype(np.float64, copy=False))
    np.add.at(counts, frame_idx, 1)
    valid = counts > 0
    full[valid] = (sums[valid] / counts[valid]).astype(np.float32)
    ...
    missing = np.flatnonzero(~valid)
    if len(missing):
        full[missing] = np.interp(missing, valid_idx, full[valid_idx]).astype(np.float32)
```

**What this does:** Each motion sample's timestamp is mapped to a target imaging frame index using the inferred mean frame interval. Multiple samples landing on the same frame are averaged. Missing frames are linearly interpolated from neighboring valid frames so that the motion array length matches the imaging frame count.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md lines 92-94):
> Sessions with motion-energy length mismatch vs imaging: 9 / 41. Mismatch sizes (n_imaging_frames - n_motion_frames): 1, 2, 3, 116, 148.

**Code** (convert_data.py:113-130, 168-170, 352-374):
```python
full = np.full(n_imaging_frames, np.nan, dtype=np.float32)
...
if not np.any(valid):
    raise ValueError("No valid motion frames after alignment.")
valid_idx = np.flatnonzero(valid)
if len(valid_idx) == 1:
    full[:] = full[valid_idx[0]]
else:
    missing = np.flatnonzero(~valid)
    if len(missing):
        full[missing] = np.interp(missing, valid_idx, full[valid_idx]).astype(np.float32)
...
if usable_bins < bins_per_trial:
    raise ValueError("Session is too short to form even one 2-minute trial.")
...
def validate_converted_session(converted):
    ...
    if np.isnan(neural[trial_idx]).any() or np.isnan(input_[trial_idx]).any() or np.isnan(output[trial_idx]).any():
        raise ValueError("Converted arrays must not contain NaN values.")
    if not np.all(output[trial_idx].sum(axis=0) == 1):
        raise ValueError("Each output timepoint must belong to exactly one motion quintile.")
```

**What this does:** Missing motion frames are linearly interpolated from neighbors. Trailing frames not filling a complete 10-frame bin or 2-minute trial are dropped. A `validate_converted_session` routine asserts no NaNs, consistent shapes across trials, exactly-one-hot outputs, and at least 2 trials per session.

**Rating:** incorrect

**Note:** doesn't detect missing video frames

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md lines 256-267):
> Sample conversion: 2.26 s/session; full conversion estimated at 1.54 min for 41 sessions. (conversion_full_out.txt: Total conversion time 57.35s; mean 1.38s/session.)

**Code** (convert_data.py:79-89):
```python
processed = suite2p_preprocess(
    Fc.copy(),
    baseline=ops["baseline"],
    win_baseline=float(ops["win_baseline"]),
    sig_baseline=float(ops["sig_baseline"]),
    fs=float(ops["fs"]),
    prctile_baseline=float(ops["prctile_baseline"]),
    batch_size=min(512, max(32, Fc.shape[0])),
    device=torch.device("cpu"),
)
```

**What this does:** The suite2p `dcnv.preprocess` baseline-correction step is identified as the dominant per-session cost; it is run on CPU. Per-session times reported in the full log range from ~1.3 s to ~2.3 s.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md lines 225-226):
> Vectorized motion-frame reconstruction using `np.add.at` and `np.interp`. Vectorized non-overlapping bin averaging via reshape/mean.

**Code** (convert_data.py:66-73, 116-117, 130):
```python
def average_nonoverlapping(x, bin_frames):
    ...
    new_shape = x.shape[:-1] + (usable // bin_frames, bin_frames)
    return x.reshape(new_shape).mean(axis=-1)
...
np.add.at(sums, frame_idx, motion_energy.astype(np.float64, copy=False))
np.add.at(counts, frame_idx, 1)
...
full[missing] = np.interp(missing, valid_idx, full[valid_idx]).astype(np.float32)
```

**What this does:** The principal numerical loops (binning and motion-frame reconstruction/interpolation) are already vectorized via reshape/mean, `np.add.at`, and `np.interp`. The remaining per-session and per-trial Python loops perform little numerical work.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt:**
> (none)

**Code** (no relevant code found):
```python
# No explicit re-computation pattern; each session is processed once.
```

**What this does:** Each session is loaded and processed once; no obvious repeated computation across sessions. Diagnostic plots are produced for at most 2 sessions when `--show-processing` is set.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt:**
> (none)

**Code** (convert_data.py:328-341):
```python
summary = {
    "subject": session.subject,
    "session_id": session.session_id,
    "n_neurons": int(F.shape[0]),
    "n_frames_raw": int(F.shape[1]),
    "n_bins": int(neural_binned.shape[1]),
    "n_trials": int(trial_info["n_trials"]),
    "fs": fs,
    "duration_s_raw": float(F.shape[1] / fs),
    "duration_s_used": float(trial_info["usable_seconds"]),
    "missing_motion_frames": int(motion_info["n_missing_motion_frames"]),
    "motion_quintile_edges": motion_edges.tolist(),
    "processing_seconds": float(elapsed),
}
```

**What this does:** Per-session summary dicts and optional diagnostic PNG plots are produced; these are stored alongside the dataset metadata but are not consumed by `train_decoder.py`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none about memory — the speedup notes cover CPU time only) CONVERSION_NOTES.md:225-227
> ```
> Code speedups added:
> - Vectorized motion-frame reconstruction using `np.add.at` and `np.interp`.
> - Vectorized non-overlapping bin averaging via reshape/mean.
> ```

**Code** (convert_data.py:76-89, 282-295):
```python
def compute_fluorescence_signal(F: np.ndarray, Fneu: np.ndarray, ops: dict) -> np.ndarray:
    Fc = F.astype(np.float32, copy=False) - float(ops["neucoeff"]) * Fneu.astype(np.float32, copy=False)
    processed = suite2p_preprocess(
        Fc.copy(), baseline=ops["baseline"], ...,
        batch_size=min(512, max(32, Fc.shape[0])), device=torch.device("cpu"),
    )
    return processed.astype(np.float32, copy=False)

    # :282-295 (process_session)
    F = np.load(suite2p_dir / "F.npy", allow_pickle=True)
    Fneu = np.load(suite2p_dir / "Fneu.npy", allow_pickle=True)
    ...
    neural_processed = compute_fluorescence_signal(F, Fneu, ops)
    neural_binned = average_nonoverlapping(neural_processed, BIN_FRAMES).astype(np.float32, copy=False)
```

**What this does:** All neural arrays are kept in `float32` and every cast uses `copy=False` so no redundant copies are made (lines 78, 89, 181-183, 290-296); Suite2p `preprocess` is called with a capped `batch_size` of at most 512 neurons (line 86). Sessions are loaded and processed one at a time and only binned trial arrays are retained. `np.load` reads each array fully (no `mmap_mode`), `Fc.copy()` makes one extra full-size copy (line 80), the motion-alignment accumulators are `float64` (lines 115-116), and there is no `del`/`gc` call. When `--show-processing` is on, the raw `F`/`Fneu` arrays are passed through to the plotting function (lines 312-313).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
