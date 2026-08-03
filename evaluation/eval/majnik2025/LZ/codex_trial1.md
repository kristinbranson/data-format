# majnik2025 — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/majnik2025/codex/2026-03-11__11-30-50_trial1/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Subject folders present: `jm031`, `jm032`, `jm038`, `jm039`, `jm040`, `jm046`. Each subject contains daily session folders named like `YYYY-MM-DD_a`. Each session has: `suite2p/plane0/` with `F.npy`, `Fneu.npy`, `spks.npy`, `iscell.npy`, `stat.npy`, `ops.npy`; `move_deve/` with `motion_energy_glob.npy`, `tstamps.npy`, `interframe_int.npy`." [lines 64-72]

**Code** (convert_data.py:50-57, 128-203):
```python
def discover_sessions(data_root: Path) -> list[SessionInfo]:
    sessions: list[SessionInfo] = []
    for subject_dir in sorted(p for p in data_root.iterdir() if p.is_dir() and p.name.startswith("jm")):
        for session_dir in sorted(p for p in subject_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()):
            sessions.append(SessionInfo(subject=subject_dir.name, session=session_dir.name, path=session_dir))
    if not sessions:
        raise RuntimeError("No sessions found under data/.")
    return sessions
# ...
F = np.load(s2p_dir / "F.npy", mmap_mode="r")
Fneu = np.load(s2p_dir / "Fneu.npy", mmap_mode="r")
motion_raw = np.load(move_dir / "motion_energy_glob.npy")
timestamps = np.load(move_dir / "tstamps.npy")
interframe_int = np.load(move_dir / "interframe_int.npy")
```

**What this does:** Subjects are discovered as directories starting with `jm` under `data/`. Sessions are subdirectories whose name starts with 4 digits. Each session loads suite2p `F.npy`, `Fneu.npy`, `ops.npy` and move_deve `motion_energy_glob.npy`, `tstamps.npy`, `interframe_int.npy`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Subject folders present: `jm031`, `jm032`, `jm038`, `jm039`, `jm040`, `jm046`." [line 65]

**Code** (convert_data.py:52, 347-348):
```python
for subject_dir in sorted(p for p in data_root.iterdir() if p.is_dir() and p.name.startswith("jm")):
# ...
subjects = sorted({session["info"].subject for session in processed_sessions})
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
```

**What this does:** Subjects are the sorted set of `jm*` directory names under `data/`. A `subject_idx` is assigned per session via this sorted ordering and saved into the output dictionary.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Each subject contains daily session folders named like `YYYY-MM-DD_a`." [line 66]

**Code** (convert_data.py:53-54):
```python
for session_dir in sorted(p for p in subject_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()):
    sessions.append(SessionInfo(subject=subject_dir.name, session=session_dir.name, path=session_dir))
```

**What this does:** Session directories are subfolders of each subject whose name begins with 4 digits (the year), iterated in sorted order. Each yields one `SessionInfo` record processed independently.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Convert each continuous session into consecutive 2-minute pseudo-trials after 10-frame averaging. This exactly matches the paper's decoder split granularity and gives 10 trials for 20-minute sessions and 15 trials for 30-minute sessions." [line 193]

**Code** (convert_data.py:17-20, 165-189, 314, 345):
```python
RAW_FS_HZ = 30.0
BIN_FRAMES = 10
TRIAL_DURATION_SEC = 120.0
# ...
trial_bins = int(TRIAL_DURATION_SEC * RAW_FS_HZ / BIN_FRAMES)  # = 360
# ...
n_total_bins = neural_binned.shape[1]
n_trials = n_total_bins // trial_bins
for trial_idx in range(n_trials):
    start = trial_idx * trial_bins
    stop = start + trial_bins
    neural_trial = neural_binned[:, start:stop]
```

**What this does:** Continuous sessions are segmented into consecutive 2-minute (120 s) pseudo-trials after 10-frame binning, yielding 360 bins per trial. Remainder bins are dropped. A safeguard requires at least 2 trials per session (lines 391-392).

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Keep all 41 sessions. No session fails the core reference criteria, and all sessions yield at least 10 pseudo-trials after processing." [line 198]

**Code** (convert_data.py:391-392):
```python
if len(neural_trials) < 2:
    raise ValueError(f"Session {session['info'].session_id} has fewer than 2 trials after segmentation.")
```

**What this does:** No per-trial quality filtering. The only check is that each session must produce at least 2 pseudo-trials, otherwise an error is raised.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Use paper-consistent Suite2p-style preprocessing from `F` and `Fneu`" [line 165]; "Use per-session `ops.npy` values: `neucoeff=0.7`, `baseline=maximin`, `win_baseline=60`, `sig_baseline=10`, `prctile_baseline=8`, `fs=30`" [line 185]

**Code** (convert_data.py:128-134):
```python
def compute_baseline_corrected_fluorescence(s2p_dir: Path) -> tuple[np.ndarray, dict, dict]:
    ops = np.load(s2p_dir / "ops.npy", allow_pickle=True).item()
    F = np.load(s2p_dir / "F.npy", mmap_mode="r")
    Fneu = np.load(s2p_dir / "Fneu.npy", mmap_mode="r")

    corrected = np.array(F, dtype=np.float32, copy=True)
    corrected -= np.float32(ops["neucoeff"]) * np.asarray(Fneu, dtype=np.float32)
```

**What this does:** Neural data is derived from `suite2p/plane0/F.npy` (raw fluorescence), `Fneu.npy` (neuropil), with parameters loaded from `ops.npy`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Compute Suite2p-style baseline-corrected fluorescence: `Fc = F - neucoeff * Fneu`, then `suite2p.extraction.dcnv.preprocess(...)`; average non-overlapping 10-frame bins" [line 185]

**Code** (convert_data.py:133-144, 158-162):
```python
corrected = np.array(F, dtype=np.float32, copy=True)
corrected -= np.float32(ops["neucoeff"]) * np.asarray(Fneu, dtype=np.float32)
processed = dcnv.preprocess(
    corrected,
    baseline=ops["baseline"],
    win_baseline=float(ops["win_baseline"]),
    sig_baseline=float(ops["sig_baseline"]),
    fs=float(ops["fs"]),
    prctile_baseline=float(ops["prctile_baseline"]),
    batch_size=int(ops.get("batch_size", 2000)),
    device=torch.device("cpu"),
).astype(np.float32, copy=False)
# ...
def bin_array_mean(x: np.ndarray, bin_frames: int) -> np.ndarray:
    n_bins = x.shape[-1] // bin_frames
    trimmed = x[..., : n_bins * bin_frames]
    new_shape = trimmed.shape[:-1] + (n_bins, bin_frames)
    return trimmed.reshape(new_shape).mean(axis=-1, dtype=np.float32)
```

**What this does:** Neuropil subtraction with the per-session `ops['neucoeff']` (typically 0.7), then suite2p `dcnv.preprocess` baseline correction using saved ops parameters (maximin baseline, 60s window, etc.) on CPU. The resulting trace is averaged over non-overlapping 10-frame bins (~333 ms) before trial segmentation.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Keep all neurons present in the released matched Suite2p arrays for each subject. These already represent the Track2p all-days matched population analyzed in the paper." [line 199]

**Code** (no relevant code found; `iscell.npy` is not loaded in convert_data.py)

**What this does:** No additional cell filtering is applied. All neurons present in `F.npy` are kept, relying on the released suite2p/Track2p arrays to be already curated to the across-day matched cells.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Each pseudo-trial keeps its absolute position within the original recording" [line 197]

**Code** (convert_data.py:178-184, 364-366):
```python
for trial_idx in range(n_trials):
    start = trial_idx * trial_bins
    stop = start + trial_bins
    neural_trial = neural_binned[:, start:stop]
# ...
"temporal_alignment_event": "Start of each consecutive 2-minute block cut from a continuous recording session",
"off_start": 0.0,
"off_end": TRIAL_DURATION_SEC,
```

**What this does:** Each pseudo-trial begins at the start of its 2-minute block; alignment is to the start of the block. `off_start=0.0`, `off_end=120.0` are recorded in metadata.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Average non-overlapping 10-frame windows for neural and behavior streams before segmentation, matching the paper's decoder denoising (`10 consecutive timestamps`). This yields `333.33 ms` bins." [line 194]

**Code** (convert_data.py:17-20, 158-162, 206):
```python
RAW_FS_HZ = 30.0
BIN_FRAMES = 10
TIME_BIN_SIZE_MS = 1000.0 * BIN_FRAMES / RAW_FS_HZ  # 333.33 ms
# ...
neural_binned = bin_array_mean(neural_processed, BIN_FRAMES)
```

**What this does:** The 30 Hz processed neural trace is averaged in non-overlapping 10-frame windows, producing one sample every 333.33 ms (3 Hz). `time_bin_size` is recorded in metadata as `333.33`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Encode elapsed session time as one continuous, time-varying input in seconds." [line 197]

**Code** (convert_data.py:205, 208):
```python
time_full_sec = (np.arange(n_frames, dtype=np.float32) + 0.5) / np.float32(ops["fs"])
# ...
time_binned = bin_array_mean(time_full_sec[np.newaxis, :], BIN_FRAMES)[0]
```

**What this does:** Time is computed from frame index using `ops['fs']` (30 Hz), with a +0.5 frame-center offset, then 10-frame averaged. It is not loaded from any timing file.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Time*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "after 10-frame averaging, use bin-center time for each sample inside each 2-minute block" [line 186]

**Code** (convert_data.py:205, 208, 182):
```python
time_full_sec = (np.arange(n_frames, dtype=np.float32) + 0.5) / np.float32(ops["fs"])
time_binned = bin_array_mean(time_full_sec[np.newaxis, :], BIN_FRAMES)[0]
# ...
input_trial = time_binned[np.newaxis, start:stop].astype(np.float32, copy=False)
```

**What this does:** A frame-centered time vector (in seconds from session start) is built, averaged over 10-frame windows to produce bin-center times, then sliced per trial. The time values reflect elapsed session time (not reset per trial).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:206-208):
```python
neural_binned = bin_array_mean(neural_processed, BIN_FRAMES)
motion_binned = bin_array_mean(motion_full[np.newaxis, :], BIN_FRAMES)[0]
time_binned = bin_array_mean(time_full_sec[np.newaxis, :], BIN_FRAMES)[0]
```

**What this does:** Time and neural are derived from the same frame index space (length `n_frames`) and binned identically with the same 10-frame averaging, so they are frame-for-frame aligned by construction.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "`move_deve/motion_energy_glob.npy`, `tstamps.npy`, `interframe_int.npy` -> `output[0]`" [line 187]

**Code** (convert_data.py:200-203):
```python
motion_raw = np.load(move_dir / "motion_energy_glob.npy")
timestamps = np.load(move_dir / "tstamps.npy")
interframe_int = np.load(move_dir / "interframe_int.npy")
motion_full, missing_idx = reconstruct_motion_trace(motion_raw, interframe_int, n_frames)
```

**What this does:** Motion energy is loaded from `move_deve/motion_energy_glob.npy`. `tstamps.npy` and `interframe_int.npy` provide camera timing used to reconstruct missing-frame positions.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Reconstruct missing frames from doubled timing gaps so behavior length matches imaging; average non-overlapping 10-frame bins; global min-max normalize valid values; discretize all valid binned samples into 5 equal-percentile bins" [line 187]

**Code** (convert_data.py:102-125, 207, 335-343, 183):
```python
def reconstruct_motion_trace(motion, interframe_int, target_len):
    median_interval = float(np.median(interframe_int))
    steps = np.rint(interframe_int / median_interval).astype(np.int64)
    steps[steps < 1] = 1
    observed_idx = np.empty(motion.shape[0], dtype=np.int64)
    observed_idx[0] = 0
    observed_idx[1:] = np.cumsum(steps)
    full = np.full(target_len, np.nan, dtype=np.float32)
    full[observed_idx] = motion
    full = interpolate_nans(full)
# ...
motion_binned = bin_array_mean(motion_full[np.newaxis, :], BIN_FRAMES)[0]
# ...
motion_min = float(np.min(motion_all))
motion_max = float(np.max(motion_all))
motion_norm_all = (motion_all - motion_min) / (motion_max - motion_min)
motion_edges = np.quantile(motion_norm_all, [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).astype(np.float32)
# ...
output_trial = np.digitize(motion_norm_binned[start:stop], motion_edges[1:-1], right=False).astype(np.int64)
```

**What this does:** (1) Missing camera frames are inferred from interframe-interval timing-step accumulation and filled by linear interpolation. (2) Reconstructed motion is averaged in 10-frame bins. (3) All sessions' binned motion are pooled, min-max normalized globally, then discretized into 5 equal-percentile bins (Q1-Q5) using `np.digitize`.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-d. How is `output` *Motion energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Treat imaging frames as the master clock and reconstruct missing behavior frames from doubled timing gaps before alignment." [line 167]

**Code** (convert_data.py:102-125, 198-208):
```python
n_frames = int(ops["nframes"])
# ...
motion_full, missing_idx = reconstruct_motion_trace(motion_raw, interframe_int, n_frames)
# (rounds interframe gaps to integer frame steps; inserts NaNs at missing positions; interpolates)
neural_binned = bin_array_mean(neural_processed, BIN_FRAMES)
motion_binned = bin_array_mean(motion_full[np.newaxis, :], BIN_FRAMES)[0]
```

**What this does:** Imaging is the master clock at length `ops['nframes']`. Behavior is re-indexed onto this clock by inferring missed frames from `interframe_int.npy` (gap rounded to integer multiples of the median interval). After interpolation, motion has the same length as the neural trace and is binned identically.

**Rating:** match

**Note:** _(no note)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavioral frames can be missing in some sessions; the data README says missing frames should be identified from `tstamps.npy` / `interframe_int.npy` and treated as missing values or interpolated." [line 150]; "Sessions with missing behavior frames (`9` total) convert to the correct final length after reconstruction." [line 358]

**Code** (convert_data.py:90-99, 116-119):
```python
def interpolate_nans(x: np.ndarray) -> np.ndarray:
    if not np.isnan(x).any():
        return x
    idx = np.arange(x.shape[0])
    valid = ~np.isnan(x)
    out = x.copy()
    out[~valid] = np.interp(idx[~valid], idx[valid], x[valid]).astype(np.float32)
    return out
# ...
if observed_idx[-1] != target_len - 1:
    raise ValueError(
        f"Timing reconstruction failed: last observed index {observed_idx[-1]} does not match target {target_len - 1}"
    )
```

**What this does:** Missing motion frames are detected by accumulating rounded interframe-interval steps; gap positions are filled with NaN and linearly interpolated. A sanity check raises if reconstructed length does not match imaging frame count. Remainder bins not filling a full trial are silently dropped during segmentation.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "the main cost is Suite2p-style fluorescence preprocessing." [line 229]; "Sample conversion (`--sample`) | 2.48 s / session mean ... Estimated full conversion ... ~85.6 s (~1.43 min) for all 41 sessions" [lines 273-275]

**Code** (convert_data.py:135-144):
```python
processed = dcnv.preprocess(
    corrected,
    baseline=ops["baseline"],
    win_baseline=float(ops["win_baseline"]),
    sig_baseline=float(ops["sig_baseline"]),
    fs=float(ops["fs"]),
    prctile_baseline=float(ops["prctile_baseline"]),
    batch_size=int(ops.get("batch_size", 2000)),
    device=torch.device("cpu"),
)
```

**What this does:** The dominant cost is suite2p's `dcnv.preprocess` baseline correction, run on CPU. Notes report a per-session mean of ~2.5 s and ~85 s total for 41 sessions.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Behavior reconstruction is vectorized via timing-step accumulation. Binning uses reshape-and-mean rather than Python loops." [lines 233-234]

**Code** (convert_data.py:178-187):
```python
for trial_idx in range(n_trials):
    start = trial_idx * trial_bins
    stop = start + trial_bins
    neural_trial = neural_binned[:, start:stop].astype(np.float32, copy=False)
    input_trial = time_binned[np.newaxis, start:stop].astype(np.float32, copy=False)
    output_trial = np.digitize(motion_norm_binned[start:stop], motion_edges[1:-1], right=False).astype(np.int64)
    output_trial = output_trial[np.newaxis, :]
    neural_trials.append(neural_trial)
```

**What this does:** Trial segmentation uses a per-trial Python loop that slices the binned arrays. Within the loop, all expensive ops (binning, normalization, digitization) are already vectorized; the loop itself just slices.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:429-442):
```python
for session in sessions:
    processed_sessions.append(process_session(session))

data, motion_min, motion_max, motion_edges = build_dataset(processed_sessions)
# ...
if args.show_processing:
    for session in processed_sessions[:2]:
        plot_path = Path(f"processing_{session['info'].session_id}.png")
        plot_processing(session, motion_min, motion_max, motion_edges, plot_path)
```

**What this does:** Each session is processed once in a loop. When `--show-processing` is enabled, the plotting function recomputes per-session normalized motion and class assignments using `motion_min`/`motion_max` already known at the dataset level.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(none)"

**Code** (convert_data.py:146-155, 200-217):
```python
sample_neuron = min(2, processed.shape[0] - 1)
preview_len = min(3000, processed.shape[1])
preview = {
    "sample_neuron": sample_neuron,
    "F": np.asarray(F[sample_neuron, :preview_len], dtype=np.float32),
    "Fneu": np.asarray(Fneu[sample_neuron, :preview_len], dtype=np.float32),
    "corrected": corrected[sample_neuron, :preview_len].copy(),
    "processed": processed[sample_neuron, :preview_len].copy(),
}
# ...
timestamps = np.load(move_dir / "tstamps.npy")
# ...
motion_preview = { ... "timestamps": ..., "interframe_int": ... }
```

**What this does:** Per-session preview slices for `F`, `Fneu`, `corrected`, `processed`, raw timestamps, and interframe intervals are loaded/copied to support optional plotting. `tstamps.npy` is loaded but not used in the actual data computation. These are not written into the final pickle.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:266-268
> ```
> | Speed-ups Implemented | Time Savings |
> | Session-wise processing after per-session loading | Keeps memory bounded; avoids storing raw arrays |
> ```

**Code** (convert_data.py:64-68, 128-144):
```python
    def has_missing_behavior_frames(session: SessionInfo) -> bool:
        move_dir = session.path / "move_deve"
        motion_len = int(np.load(move_dir / "motion_energy_glob.npy", mmap_mode="r").shape[0])
        nframes = session_nframes(session)
        return motion_len != nframes

def compute_baseline_corrected_fluorescence(s2p_dir: Path) -> tuple[np.ndarray, dict, dict]:
    ops = np.load(s2p_dir / "ops.npy", allow_pickle=True).item()
    F = np.load(s2p_dir / "F.npy", mmap_mode="r")
    Fneu = np.load(s2p_dir / "Fneu.npy", mmap_mode="r")

    corrected = np.array(F, dtype=np.float32, copy=True)
    corrected -= np.float32(ops["neucoeff"]) * np.asarray(Fneu, dtype=np.float32)
    processed = dcnv.preprocess(
        corrected, baseline=ops["baseline"], ...,
        batch_size=int(ops.get("batch_size", 2000)), device=torch.device("cpu"),
    ).astype(np.float32, copy=False)
```

**What this does:** `F.npy`/`Fneu.npy` are opened with `mmap_mode="r"` (lines 66, 130-131) so shape checks during sample selection never read the array, and neuropil subtraction is done in place on a single `float32` buffer (`corrected -= ...`, line 134). Downstream casts use `copy=False` and `mean(..., dtype=np.float32)` (lines 144, 162, 181-182), Suite2p `preprocess` runs with an explicit `batch_size`, and sessions are processed one at a time with only binned arrays retained in the returned dict (lines 226-236). Full-resolution previews are truncated to 3000 frames before being kept for plotting (lines 146-154). No explicit `del`/`gc` calls; the per-session binned arrays for all sessions are held in memory before `build_dataset` (line 335).

**Rating:** match

**Note:** _(no note)_

---
