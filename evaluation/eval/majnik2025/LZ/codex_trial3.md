# majnik2025 — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/majnik2025/codex/2026-03-11__11-30-50_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "There are 6 subject folders: `jm031`, `jm032`, ... Each subject contains daily session folders named as dates (e.g. `2023-04-30_a`). Each session contains: `suite2p/plane0/F.npy`, `Fneu.npy`, `ops.npy`, `move_deve/motion_energy_glob.npy`, `tstamps.npy`, `interframe_int.npy`" (CONVERSION_NOTES.md:71-82)

**Code** (convert_data.py:46-77, 272-294, 348-352):
```python
def discover_sessions(sample: bool) -> list[SessionInfo]:
    sessions: list[SessionInfo] = []
    for subject_dir in sorted(p for p in DATA_ROOT.iterdir() if p.is_dir() and p.name.startswith("jm")):
        session_dirs = sorted(
            p for p in subject_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()
        )
        for session_dir in session_dirs:
            sessions.append(
                SessionInfo(
                    subject=subject_dir.name,
                    session_id=f"{subject_dir.name}_{session_dir.name}",
                    path=session_dir,
                )
            )
    ...
# Per-session loading:
F = np.load(session.path / "suite2p" / "plane0" / "F.npy", allow_pickle=True)
Fneu = np.load(session.path / "suite2p" / "plane0" / "Fneu.npy", allow_pickle=True)
motion = np.load(session.path / "move_deve" / "motion_energy_glob.npy", allow_pickle=True)
tstamps = np.load(session.path / "move_deve" / "tstamps.npy", allow_pickle=True)
```

**What this does:** Subjects are discovered as directories under `data/` starting with `jm`; sessions are subdirectories whose first four characters are digits (a date prefix). For each session, the code loads suite2p outputs (`F`, `Fneu`, `ops`) and behavior arrays (`motion_energy_glob`, `tstamps`) from `move_deve`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sorted unique subject IDs; each session points to its subject index" (CONVERSION_NOTES.md:234)

**Code** (convert_data.py:48, 304-312):
```python
for subject_dir in sorted(p for p in DATA_ROOT.iterdir() if p.is_dir() and p.name.startswith("jm")):
    ...
subjects = sorted({session.subject for session in sessions})
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
converted = {
    ...
    "subjects": subjects,
    "subject_idx": np.array([subject_to_idx[session.subject] for session in sessions], dtype=np.int64),
```

**What this does:** Subjects are taken as sorted unique subject directory names matching the `jm*` prefix; each session is assigned the index of its parent subject in that sorted list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions: 41 ... `jm031`: 7, `jm032`: 7, `jm038`: 7, `jm039`: 7, `jm040`: 6, `jm046`: 7" (CONVERSION_NOTES.md:97-99)

**Code** (convert_data.py:49-59):
```python
session_dirs = sorted(
    p for p in subject_dir.iterdir() if p.is_dir() and p.name[:4].isdigit()
)
for session_dir in session_dirs:
    sessions.append(
        SessionInfo(
            subject=subject_dir.name,
            session_id=f"{subject_dir.name}_{session_dir.name}",
            path=session_dir,
        )
    )
```

**What this does:** Each daily recording subdirectory under a subject (whose name begins with four digits, i.e. a date) is treated as a session. Sessions are sorted alphabetically and given an ID combining subject and session-folder name.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Construct pseudo-trials as consecutive 2-minute blocks. The native data have no trials, and the paper's decoder splits recordings into consecutive 2-minute blocks. After 10-frame averaging, each block contains `120 s * 3 Hz = 360` time bins." (CONVERSION_NOTES.md:241)

**Code** (convert_data.py:17-20, 166-177, 372-374):
```python
MOTION_BIN_SIZE_FRAMES = 10
IMAGING_FS = 30.0
BLOCK_DURATION_SEC = 120.0
BLOCK_BINS = int(BLOCK_DURATION_SEC * IMAGING_FS / MOTION_BIN_SIZE_FRAMES)
...
def split_into_blocks_2d(x: np.ndarray, block_bins: int) -> list[np.ndarray]:
    nblocks = x.shape[1] // block_bins
    usable = nblocks * block_bins
    x = x[:, :usable]
    return [x[:, i * block_bins : (i + 1) * block_bins] for i in range(nblocks)]
...
neural_trials = split_into_blocks_2d(neural_binned, BLOCK_BINS)
input_trials = [x[None, :].astype(np.float32) for x in split_into_blocks_1d(time_binned, BLOCK_BINS)]
output_trials = [x[None, :].astype(np.int64) for x in split_into_blocks_1d(motion_disc, BLOCK_BINS)]
```

**What this does:** Trials are defined as consecutive non-overlapping 2-minute blocks of the continuous recording. After 10-frame averaging (3 Hz), each trial contains 360 bins. Any leftover bins not filling a complete block are discarded.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — no explicit per-trial quality filtering described)

**Code** (convert_data.py:376-379):
```python
if not (len(neural_trials) == len(input_trials) == len(output_trials)):
    raise ValueError(f"{session.session_id}: trial count mismatch after block splitting")
if len(neural_trials) < 2:
    raise ValueError(f"{session.session_id}: needs at least two trials, got {len(neural_trials)}")
```

**What this does:** No quality-based filtering is applied to trials. The only checks raise errors if neural/input/output trial counts disagree or if a session yields fewer than two trials.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reconstruct Suite2p-style baseline-corrected fluorescence from `F.npy` and `Fneu.npy`" (CONVERSION_NOTES.md:268)

**Code** (convert_data.py:347-349):
```python
ops = load_ops(session)
F = np.load(session.path / "suite2p" / "plane0" / "F.npy", allow_pickle=True)
Fneu = np.load(session.path / "suite2p" / "plane0" / "Fneu.npy", allow_pickle=True)
```

**What this does:** Neural data is derived from suite2p `F.npy` (raw fluorescence), `Fneu.npy` (neuropil), and `ops.npy` (parameters) from `plane0`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use baseline-corrected fluorescence as neural data: The paper explicitly states that subsequent analyses used baseline-corrected fluorescence traces (\"our dF/F\") with default Suite2p parameters." (CONVERSION_NOTES.md:239)

**Code** (convert_data.py:150-163):
```python
def compute_suite2p_baseline_corrected(F: np.ndarray, Fneu: np.ndarray, ops: dict) -> np.ndarray:
    fc = F.astype(np.float32, copy=False) - float(ops.get("neucoeff", 0.7)) * Fneu.astype(
        np.float32, copy=False
    )
    return dcnv.preprocess(
        fc.copy(),
        baseline=ops.get("baseline", "maximin"),
        win_baseline=float(ops.get("win_baseline", 60.0)),
        sig_baseline=float(ops.get("sig_baseline", 10.0)),
        fs=float(ops.get("fs", IMAGING_FS)),
        prctile_baseline=float(ops.get("prctile_baseline", 8.0)),
        batch_size=int(ops.get("batch_size", 100)),
        device=torch.device("cpu"),
    ).astype(np.float32, copy=False)
```

**What this does:** Neuropil subtraction (`F - neucoeff*Fneu`) using each session's `ops` neucoeff (default 0.7), followed by suite2p `dcnv.preprocess` with the session's baseline parameters (`maximin`, 60 s window). Then bin-averaged in 10-frame bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "The release data already reflect this filtering [iscell > 0.5 + Track2p across-day matching], so the conversion does not apply a second filtering pass." (CONVERSION_NOTES.md:396)

**Code** (convert_data.py): (no relevant code found)

**What this does:** No additional neuron-level QC filter is applied; all neurons present in the provided suite2p `F.npy` (already pre-filtered to cells matched across days) are kept.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use 10-frame temporal averaging before segmentation: This exactly matches the paper's decoding preprocessing and converts 30 Hz traces into 3 Hz traces" (CONVERSION_NOTES.md:240)

**Code** (convert_data.py:137-147, 360-362):
```python
def bin_average_1d(x: np.ndarray, bin_size: int) -> np.ndarray:
    usable = (len(x) // bin_size) * bin_size
    x = x[:usable]
    return x.reshape(-1, bin_size).mean(axis=1, dtype=np.float64).astype(np.float32)


def bin_average_2d(x: np.ndarray, bin_size: int) -> np.ndarray:
    usable = (x.shape[1] // bin_size) * bin_size
    x = x[:, :usable]
    nbins = usable // bin_size
    return x.reshape(x.shape[0], nbins, bin_size).mean(axis=2, dtype=np.float64).astype(np.float32)
...
neural_binned = bin_average_2d(neural, MOTION_BIN_SIZE_FRAMES)
```

**What this does:** Neural data is averaged in non-overlapping 10-frame bins, downsampling from 30 Hz to 3 Hz (resulting in `time_bin_size = 1000.0 * 10 / 30 ≈ 333.33` ms).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "temporal_alignment_event: start of each consecutive 2-minute block; input stores absolute elapsed time from session start" (convert_data.py:327)

**Code** (convert_data.py:327-329):
```python
"temporal_alignment_event": "start of each consecutive 2-minute block; input stores absolute elapsed time from session start",
"off_start": 0.0,
"off_end": BLOCK_DURATION_SEC,
```

**What this does:** Each trial's neural data starts at the beginning of a 2-minute block; there is no stimulus event-based alignment. Metadata records the alignment event as the start of each block, with `off_start=0.0` and `off_end=120.0`.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use absolute elapsed time from session start as the sole decoder input" (CONVERSION_NOTES.md:243)

**Code** (convert_data.py:180-182, 362):
```python
def make_time_input(nbins: int, fs: float, bin_size_frames: int) -> np.ndarray:
    step = bin_size_frames / fs
    return (np.arange(nbins, dtype=np.float32) * step)[None, :]
...
time_binned = make_time_input(neural_binned.shape[1], float(ops["fs"]), MOTION_BIN_SIZE_FRAMES)[0]
```

**What this does:** Time is computed from bin indices using `ops['fs']` (30 Hz) and the 10-frame bin size; not derived from any timestamp variable in the raw data.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Time*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — direct computation from frame indices)

**Code** (convert_data.py:180-182, 373):
```python
def make_time_input(nbins: int, fs: float, bin_size_frames: int) -> np.ndarray:
    step = bin_size_frames / fs
    return (np.arange(nbins, dtype=np.float32) * step)[None, :]
...
input_trials = [x[None, :].astype(np.float32) for x in split_into_blocks_1d(time_binned, BLOCK_BINS)]
```

**What this does:** Builds a per-bin elapsed-time vector starting at 0 with step `bin_size_frames/fs` (≈0.333 s), spanning all binned timepoints in the session, then splits into 360-bin blocks. Time values are absolute elapsed seconds from the session start, not reset per trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit; alignment by construction)

**Code** (convert_data.py:361-374):
```python
neural_binned = bin_average_2d(neural, MOTION_BIN_SIZE_FRAMES)
time_binned = make_time_input(neural_binned.shape[1], float(ops["fs"]), MOTION_BIN_SIZE_FRAMES)[0]
...
neural_trials = split_into_blocks_2d(neural_binned, BLOCK_BINS)
input_trials = [x[None, :].astype(np.float32) for x in split_into_blocks_1d(time_binned, BLOCK_BINS)]
```

**What this does:** The time vector is constructed with the same number of bins as the binned neural array, then split into the same 360-bin blocks, ensuring index-for-index alignment with neural trials.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Map behavior samples onto imaging frame indices using normalized timestamps; fill missing frames by linear interpolation on the imaging grid; average over 10-frame bins" (CONVERSION_NOTES.md:232)

**Code** (convert_data.py:275-276, 350-351):
```python
motion = np.load(session.path / "move_deve" / "motion_energy_glob.npy", allow_pickle=True)
tstamps = np.load(session.path / "move_deve" / "tstamps.npy", allow_pickle=True)
```

**What this does:** Motion energy is derived from `move_deve/motion_energy_glob.npy`; `move_deve/tstamps.npy` is used to map behavior samples onto the imaging frame grid when lengths differ.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Normalize globally to `[0,1]` across included sessions after 10-frame averaging; discretize into 5 equal-percentile bins using global quintiles" (CONVERSION_NOTES.md:233)

**Code** (convert_data.py:185-186, 296-300, 354-358):
```python
def motion_to_bins(x: np.ndarray, quantile_edges: np.ndarray) -> np.ndarray:
    return np.digitize(x, quantile_edges, right=False).astype(np.int64)
...
all_motion = np.concatenate(all_motion_binned)
motion_min = float(all_motion.min())
motion_max = float(all_motion.max())
motion_norm_all = (all_motion - motion_min) / max(motion_max - motion_min, 1e-12)
quantile_edges = np.quantile(motion_norm_all, [0.2, 0.4, 0.6, 0.8]).astype(np.float32)
...
motion_binned_norm = ((motion_binned - motion_min) / max(motion_max - motion_min, 1e-12)).astype(np.float32)
motion_disc = motion_to_bins(motion_binned_norm, quantile_edges)
```

**What this does:** (1) Behavior is aligned to imaging frame grid (via timestamp mapping with linear interpolation over missing frames). (2) 10-frame bin averaging. (3) Global min-max normalization across all included sessions. (4) Discretization into 5 quintile-based bins (`np.digitize` against [0.2, 0.4, 0.6, 0.8] quantile edges).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Motion energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Treat imaging frames as the reference clock... motion energy will be aligned to the imaging grid using `tstamps.npy`, then interpolated over missing positions" (CONVERSION_NOTES.md:242)

**Code** (convert_data.py:86-134):
```python
def align_motion_to_imaging(motion, tstamps, nframes):
    if len(motion) == nframes:
        aligned = motion.astype(np.float32, copy=False)
        ...
        return aligned, stats
    ...
    denom = tstamps[-1] - tstamps[0]
    frame_idx = np.round((tstamps - tstamps[0]) / denom * (nframes - 1)).astype(np.int64)
    frame_idx = np.clip(frame_idx, 0, nframes - 1)
    summed = np.zeros(nframes, dtype=np.float64)
    counts = np.zeros(nframes, dtype=np.int64)
    np.add.at(summed, frame_idx, motion.astype(np.float64))
    np.add.at(counts, frame_idx, 1)
    aligned = np.full(nframes, np.nan, dtype=np.float64)
    good = counts > 0
    aligned[good] = summed[good] / counts[good]
    ...
    missing = np.flatnonzero(~good)
    if missing.size:
        aligned[missing] = np.interp(missing, known_idx, aligned[known_idx])
```

**What this does:** If motion length equals neural frame count, no remap is needed. Otherwise, behavior timestamps are linearly mapped onto the `[0, nframes-1]` index range, samples falling on the same imaging frame are averaged, and missing-frame slots are filled by `np.interp` against the known-index/value pairs.

**Rating:** match

**Note:** _(no note)_

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions with missing camera frames were converted without NaNs or length mismatches." (CONVERSION_NOTES.md:408)

**Code** (convert_data.py:114-126, 167-170, 364-370):
```python
aligned = np.full(nframes, np.nan, dtype=np.float64)
good = counts > 0
aligned[good] = summed[good] / counts[good]
...
missing = np.flatnonzero(~good)
if missing.size:
    aligned[missing] = np.interp(missing, known_idx, aligned[known_idx])
...
nblocks = x.shape[1] // block_bins
usable = nblocks * block_bins
x = x[:, :usable]
...
if neural_binned.shape[1] != len(motion_disc):
    raise ValueError(...)
if neural_binned.shape[1] % BLOCK_BINS != 0:
    raise ValueError(...)
```

**What this does:** Missing camera frames are detected (frames where no behavior timestamp maps) and filled by linear interpolation. Bins not filling a complete 2-minute block are truncated. Length mismatches between neural and motion arrays raise an error.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Suite2p baseline correction requires loading full `F.npy` and `Fneu.npy` arrays for each session. Full conversion may still be moderately expensive because baseline correction is performed per session on CPU." (CONVERSION_NOTES.md:274-275)

**Code** (convert_data.py:154-163):
```python
return dcnv.preprocess(
    fc.copy(),
    baseline=ops.get("baseline", "maximin"),
    win_baseline=float(ops.get("win_baseline", 60.0)),
    ...
    device=torch.device("cpu"),
).astype(np.float32, copy=False)
```

**What this does:** The dominant cost is per-session suite2p `dcnv.preprocess` baseline correction, performed on CPU. Loading large `F.npy`/`Fneu.npy` arrays per session is a secondary cost.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — no loops explicitly flagged for vectorization)

**Code** (convert_data.py:345-405):
```python
for idx, session in enumerate(sessions):
    ...
    neural = compute_suite2p_baseline_corrected(F, Fneu, ops)
    neural_binned = bin_average_2d(neural, MOTION_BIN_SIZE_FRAMES)
    ...
```

**What this does:** The main per-session loop could not be readily vectorized since each session must be loaded and preprocessed separately by suite2p; smaller helper operations (binning, alignment) already use vectorized numpy.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Two-pass design avoids loading all neural sessions simultaneously." (CONVERSION_NOTES.md:279)

**Code** (convert_data.py:272-294, 345-353):
```python
# Pass 1
for session in sessions:
    ops = load_ops(session)
    motion = np.load(session.path / "move_deve" / "motion_energy_glob.npy", ...)
    tstamps = np.load(session.path / "move_deve" / "tstamps.npy", ...)
    motion_aligned, align_stats = align_motion_to_imaging(motion, tstamps, nframes)
    motion_binned = bin_average_1d(motion_aligned, MOTION_BIN_SIZE_FRAMES)
    ...

# Pass 2
for idx, session in enumerate(sessions):
    ops = load_ops(session)
    ...
    motion = np.load(session.path / "move_deve" / "motion_energy_glob.npy", ...)
    tstamps = np.load(session.path / "move_deve" / "tstamps.npy", ...)
    motion_aligned, _ = align_motion_to_imaging(motion, tstamps, F.shape[1])
```

**What this does:** Each session's `ops`, `motion_energy_glob.npy`, `tstamps.npy` are loaded twice (once in pass 1 to compute global quantile edges, once in pass 2 for full conversion); `align_motion_to_imaging` is also recomputed in pass 2 even though `motion_binned_by_session` is already cached.

**Rating:** ok

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — no flagged unnecessary processing)

**Code** (convert_data.py:353):
```python
motion_aligned, _ = align_motion_to_imaging(motion, tstamps, F.shape[1])
```

**What this does:** In pass 2, `motion_aligned` is recomputed but only used when generating optional processing plots (`--show-processing`); the actual output relies on the cached `motion_binned_by_session` from pass 1. When plotting is not requested, this recomputation is unused.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:273-281
> ```
> Code inefficiencies identified:
> - Suite2p baseline correction requires loading full `F.npy` and `Fneu.npy` arrays for each session.
> Code speedups added:
> - Two-pass design avoids loading all neural sessions simultaneously.
> - Motion quantile computation stores only 10-frame-averaged behavior values, which are small.
> - Neural data are processed one session at a time and written to in-memory output lists only after temporal binning and block splitting.
> - Used `mmap_mode='r'` when only shape inspection was needed.
> ```
> CONVERSION_NOTES.md:310-313
> ```
> | Two-pass streaming conversion | Avoids holding the full neural dataset in memory |
> | Session-by-session neural preprocessing | Keeps peak memory bounded by one session |
> ```

**Code** (convert_data.py:272-280, 288, 345-361):
```python
    for session in sessions:                       # pass 1: behavior only
        ops = load_ops(session)
        motion = np.load(session.path / "move_deve" / "motion_energy_glob.npy", allow_pickle=True)
        tstamps = np.load(session.path / "move_deve" / "tstamps.npy", allow_pickle=True)
        motion_aligned, align_stats = align_motion_to_imaging(motion, tstamps, nframes)
        motion_binned = bin_average_1d(motion_aligned, MOTION_BIN_SIZE_FRAMES)
        all_motion_binned.append(motion_binned)
        # :288
        "nneurons": int(np.load(... / "F.npy", mmap_mode="r").shape[0]),

    for idx, session in enumerate(sessions):       # pass 2: neural, one session at a time
        F = np.load(session.path / "suite2p" / "plane0" / "F.npy", allow_pickle=True)
        Fneu = np.load(session.path / "suite2p" / "plane0" / "Fneu.npy", allow_pickle=True)
        neural = compute_suite2p_baseline_corrected(F, Fneu, ops)
        neural_binned = bin_average_2d(neural, MOTION_BIN_SIZE_FRAMES)
```

**What this does:** The pipeline is split into two passes: pass 1 touches only the small behavior arrays (plus `mmap_mode="r"` for a neuron-count shape lookup, line 288) to compute global quantile edges, and pass 2 loads `F`/`Fneu` for one session at a time, so at most one session's full-resolution neural data is resident. Neural arrays are held as `float32` with `copy=False` casts (lines 151-163, 381) while bin means accumulate in `float64` (lines 140, 147). `fc.copy()` makes one extra full-size copy before `dcnv.preprocess`, which uses an explicit `batch_size` (lines 155, 161). No `del`/`gc` calls; with `--show-processing` the raw `F`/`Fneu` and full-resolution `dff` are passed to the plotting function (lines 386-399).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
