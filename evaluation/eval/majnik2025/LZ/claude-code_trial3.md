# majnik2025 — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/majnik2025/claude/2026-03-10__11-18-23_trial3/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:56-67):
> Data structure per session:
> - `move_deve/` - Motion energy data (interframe_int.npy, motion_energy_glob.npy, tstamps.npy)
> - `suite2p/plane0/` - Suite2p output (F.npy, Fneu.npy, iscell.npy, ops.npy, spks.npy, stat.npy)
> ...
> 6 subjects (jm031, jm032, jm038, jm039, jm040, jm046), each with date-labeled sessions

**Code** (convert_data.py:55-65, 149-154):
```python
def get_subjects_and_sessions():
    """Discover all subjects and their sessions from the data directory."""
    subjects = sorted([d for d in os.listdir(DATA_DIR)
                       if os.path.isdir(os.path.join(DATA_DIR, d)) and d.startswith('jm')])
    all_sessions = {}
    for subj in subjects:
        subj_dir = os.path.join(DATA_DIR, subj)
        sessions = sorted([d for d in os.listdir(subj_dir)
                          if os.path.isdir(os.path.join(subj_dir, d))])
        all_sessions[subj] = sessions
    return subjects, all_sessions
# ...
F = np.load(os.path.join(sess_dir, 'suite2p', 'plane0', 'F.npy'))
Fneu = np.load(os.path.join(sess_dir, 'suite2p', 'plane0', 'Fneu.npy'))
me_raw = np.load(os.path.join(sess_dir, 'move_deve', 'motion_energy_glob.npy'))
```

**What this does:** Discovers subject directories matching `jm*` and their session subdirectories under `DATA_DIR`, sorts both alphabetically. For each session, loads suite2p `F.npy` and `Fneu.npy` from `plane0`, and motion energy from `move_deve/motion_energy_glob.npy`.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:48-52):
> SUBJECT_MAP = {
>   'jm031': 'Mouse_A', 'jm032': 'Mouse_B', 'jm038': 'Mouse_C',
>   'jm039': 'Mouse_D', 'jm040': 'Mouse_E', 'jm046': 'Mouse_F'
> }

**Code** (convert_data.py:49-58, 288):
```python
SUBJECT_MAP = {
    'jm031': 'Mouse_A', 'jm032': 'Mouse_B', 'jm038': 'Mouse_C',
    'jm039': 'Mouse_D', 'jm040': 'Mouse_E', 'jm046': 'Mouse_F'
}
# ...
subjects = sorted([d for d in os.listdir(DATA_DIR)
                   if os.path.isdir(os.path.join(DATA_DIR, d)) and d.startswith('jm')])
# ...
subject_names = list(SUBJECT_MAP.values()) if not sample_mode else [SUBJECT_MAP[subjects_to_process[0]]]
```

**What this does:** Each `jm*` directory is treated as one subject. A fixed mapping renames them to `Mouse_A` through `Mouse_F`, and these renamed labels are stored in the `subjects` field of the output.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:60-67):
> jm031/ (Mouse A, 7 sessions: 2023-10-18 to 2023-10-24)
> ... jm046/ (Mouse F, 7 sessions: 2024-09-03 to 2024-09-09)

**Code** (convert_data.py:60-65, 295-309):
```python
for subj in subjects:
    subj_dir = os.path.join(DATA_DIR, subj)
    sessions = sorted([d for d in os.listdir(subj_dir)
                      if os.path.isdir(os.path.join(subj_dir, d))])
    all_sessions[subj] = sessions
# ...
for i, session in enumerate(sessions):
    # ...
    neural_trials, input_trials, output_trials, n_neurons = process_session(
        subj, session, ...)
```

**What this does:** Each subdirectory of a subject's folder is treated as one session, sorted alphabetically (date-named). Sessions are processed independently and appended to per-session lists.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:167-172):
> No discrete trials in the original experiment (continuous spontaneous recording)
> Split continuous recording into 2-minute blocks (matching paper's CV structure)
> After 10-frame binning: 2 min = 120s * 30Hz / 10 = 360 time bins per trial

**Code** (convert_data.py:37-38, 169-190):
```python
TRIAL_DURATION_SEC = 120   # 2 minutes (paper: "consecutive 2 minute blocks")
TRIAL_BINS = int(TRIAL_DURATION_SEC * FRAME_RATE / BIN_SIZE)  # 360 bins per trial
# ...
n_total_bins = dfof_binned.shape[1]
n_trials = n_total_bins // TRIAL_BINS

for t in range(n_trials):
    start = t * TRIAL_BINS
    end = (t + 1) * TRIAL_BINS
    neural_trials.append(dfof_binned[:, start:end].astype(np.float32))
    time_sec = np.arange(start, end) * (BIN_SIZE / FRAME_RATE)
    input_trials.append(time_sec.reshape(1, -1).astype(np.float32))
    output_trials.append(me_discrete[start:end].reshape(1, -1).astype(np.int64))
```

**What this does:** Splits the continuous recording (after 10-frame binning) into non-overlapping 2-minute blocks of 360 bins each. Remainder bins not filling a full trial are dropped via integer division.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:128-130):
> Trial curation rules:
> - No explicit trial curation (continuous spontaneous recording)
> - Missing camera frames should be interpolated

**Code** (convert_data.py): (no relevant code found)

**What this does:** No trial-level quality filtering is performed; all 2-minute segments are kept.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:160-163):
> | F.npy - 0.7*Fneu.npy, baseline corrected | neural | dF/F via Suite2p preprocess, bin by 10 frames | `suite2p.extraction.dcnv.preprocess` |

**Code** (convert_data.py:148-151):
```python
# Load neural data
F = np.load(os.path.join(sess_dir, 'suite2p', 'plane0', 'F.npy'))
Fneu = np.load(os.path.join(sess_dir, 'suite2p', 'plane0', 'Fneu.npy'))
n_neurons, n_frames = F.shape
```

**What this does:** Neural data is derived from suite2p `F.npy` (raw fluorescence) and `Fneu.npy` (neuropil) from `plane0`.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:174-188):
> 2. Compute neuropil-corrected fluorescence: Fc = F - 0.7 * Fneu
> 3. Compute dF/F using Suite2p's preprocess (maximin baseline)
> 5. Bin both neural and motion energy by averaging 10 consecutive frames

**Code** (convert_data.py:68-89, 107-119, 162-163):
```python
def compute_dfof(F, Fneu, fs=FRAME_RATE):
    # Neuropil correction
    Fc = F - NEUROPIL_COEFF * Fneu

    # Suite2p baseline correction: returns Fc - F0 (baseline-subtracted)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    dfof = s2p_preprocess(
        Fc.copy().astype(np.float32), BASELINE_METHOD, WIN_BASELINE,
        SIG_BASELINE, fs, PRCTILE_BASELINE, device=device
    )
    return dfof.astype(np.float32)

def bin_timeseries(data, bin_size):
    n_frames = data.shape[-1]
    n_bins = n_frames // bin_size
    truncated = data[..., :n_bins * bin_size]
    new_shape = truncated.shape[:-1] + (n_bins, bin_size)
    return truncated.reshape(new_shape).mean(axis=-1)
# ...
dfof_binned = bin_timeseries(dfof, BIN_SIZE)  # (n_neurons, n_bins)
```

**What this does:** Subtracts 0.7×neuropil from raw fluorescence, then applies suite2p `preprocess` (maximin baseline, win=60s, sig=10, prctile=8) which returns the baseline-subtracted signal (used directly as dF/F). The result is then averaged in non-overlapping 10-frame bins.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:124-127):
> Neuron curation rules:
> - Suite2p iscell probability > 0.5 (already applied in provided data)
> - Track2p matching: only neurons tracked across ALL days (already applied)

**Code** (convert_data.py): (no relevant code found — no filtering applied in this script)

**What this does:** No additional cell filtering is applied; all rows of `F.npy` are used. The notes state the provided data is already pre-filtered by Track2p (all `iscell=1`).

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:167-170):
> No discrete trials in the original experiment (continuous spontaneous recording)
> Split continuous recording into 2-minute blocks

**Code** (convert_data.py:346-352):
```python
'metadata': {
    ...
    'temporal_alignment_event': 'start of continuous recording session',
    'off_start': 0.0,
    'off_end': None,
    ...
}
```

**What this does:** Trials are not aligned to a stimulus event; they begin at fixed 2-minute offsets from the recording start. Metadata records the alignment event as "start of continuous recording session".

**Rating:** match

**Note:** _(no note)_

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:111):
> Decoding bin size | 10 frames = 333ms

**Code** (convert_data.py:36-40, 113-119):
```python
BIN_SIZE = 10              # frames per bin (paper: "bins of 10 consecutive timestamps")
TIME_BIN_MS = BIN_SIZE / FRAME_RATE * 1000  # ~333.33 ms
# ...
n_bins = n_frames // bin_size
truncated = data[..., :n_bins * bin_size]
new_shape = truncated.shape[:-1] + (n_bins, bin_size)
return truncated.reshape(new_shape).mean(axis=-1)
```

**What this does:** Averages every 10 consecutive 30 Hz frames into a single bin (~333.33 ms bin size, i.e. ~3 Hz).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `input` *Time* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:161):
> | Time index | input[0] | time_elapsed = bin_index * (10/30) seconds | N/A | Decoder input: time from start |

**Code** (convert_data.py:184-187):
```python
# Input: time elapsed from start of recording in seconds
# Each bin covers BIN_SIZE/FRAME_RATE seconds
time_sec = np.arange(start, end) * (BIN_SIZE / FRAME_RATE)
input_trials.append(time_sec.reshape(1, -1).astype(np.float32))
```

**What this does:** Time is computed from bin indices times the bin width (10/30 s); not derived from any raw data variable.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *Time*?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:184-187):
```python
time_sec = np.arange(start, end) * (BIN_SIZE / FRAME_RATE)
input_trials.append(time_sec.reshape(1, -1).astype(np.float32))
```

**What this does:** Builds a per-trial time vector as `np.arange(start, end) * (BIN_SIZE/FRAME_RATE)`; values are seconds from the start of the recording (continuing across trial boundaries, not per-trial reset).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *Time* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:177-187):
```python
for t in range(n_trials):
    start = t * TRIAL_BINS
    end = (t + 1) * TRIAL_BINS
    neural_trials.append(dfof_binned[:, start:end].astype(np.float32))
    time_sec = np.arange(start, end) * (BIN_SIZE / FRAME_RATE)
    input_trials.append(time_sec.reshape(1, -1).astype(np.float32))
```

**What this does:** Time and neural data share the same `start:end` bin indices, so they are aligned bin-for-bin.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Motion energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:165):
> | motion_energy_glob.npy | output[0] | Bin by 10 frames, normalize per session, discretize to 5 quintile bins |

**Code** (convert_data.py:153-154):
```python
# Load motion energy
me_raw = np.load(os.path.join(sess_dir, 'move_deve', 'motion_energy_glob.npy'))
```

**What this does:** Motion energy is loaded from `move_deve/motion_energy_glob.npy`. (Note: `interframe_int.npy` is mentioned in notes but not loaded here.)

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Motion energy*?

**Notes excerpt** (CONVERSION_NOTES.md:178-181):
> 5. Bin both neural and motion energy by averaging 10 consecutive frames
> 6. Normalize motion energy per session
> 7. Discretize motion energy into 5 equal-percentile bins (per session)

**Code** (convert_data.py:92-104, 122-133, 162-167):
```python
def interpolate_motion_energy(me, n_frames):
    if len(me) == n_frames:
        return me.astype(np.float64)
    # Linear interpolation to match neural frame count
    x_orig = np.linspace(0, 1, len(me))
    x_new = np.linspace(0, 1, n_frames)
    me_interp = np.interp(x_new, x_orig, me.astype(np.float64))
    return me_interp

def discretize_motion_energy(me_binned, n_bins=N_OUTPUT_BINS):
    percentiles = np.linspace(0, 100, n_bins + 1)[1:-1]  # e.g., [20, 40, 60, 80]
    thresholds = np.percentile(me_binned, percentiles)
    labels = np.digitize(me_binned, thresholds).astype(np.int64)
    return labels
# ...
me_binned = bin_timeseries(me.reshape(1, -1), BIN_SIZE).squeeze()
me_discrete = discretize_motion_energy(me_binned, N_OUTPUT_BINS)
```

**What this does:** Linearly interpolates motion energy to match the neural frame count, averages it in 10-frame bins, then discretizes per-session into 5 equal-percentile bins (quintiles) using `np.percentile` thresholds and `np.digitize`. Note: code does not explicitly normalize per session before discretizing (despite notes mentioning normalization).

**Rating:** concerning

**Note:** missing normalization

---

## Q 4-d. How is `output` *Motion energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:82-90):
> Some sessions have fewer motion energy frames than neural frames... Per data README: "indices of missing frames can be obtained by looking at tstamps.npy or interframe_int.npy and treated as missing values or interpolated over"

**Code** (convert_data.py:92-104, 156-157):
```python
def interpolate_motion_energy(me, n_frames):
    if len(me) == n_frames:
        return me.astype(np.float64)
    x_orig = np.linspace(0, 1, len(me))
    x_new = np.linspace(0, 1, n_frames)
    me_interp = np.interp(x_new, x_orig, me.astype(np.float64))
    return me_interp
# ...
me = interpolate_motion_energy(me_raw, n_frames)
```

**What this does:** Aligns motion energy to neural frames via global linear interpolation across the entire session length (not via interframe-interval-based gap detection). After interpolation it is binned and trial-sliced with the same indices as the neural data.

**Rating:** incorrect

**Note:** didn't find missing frames correctly

---

## Q 5. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:82-90, 130):
> Some sessions have fewer motion energy frames than neural frames
> Missing camera frames should be interpolated

**Code** (convert_data.py:97-104, 113-115):
```python
if len(me) == n_frames:
    return me.astype(np.float64)
x_orig = np.linspace(0, 1, len(me))
x_new = np.linspace(0, 1, n_frames)
me_interp = np.interp(x_new, x_orig, me.astype(np.float64))
return me_interp
# ...
n_bins = n_frames // bin_size
truncated = data[..., :n_bins * bin_size]
```

**What this does:** Missing motion energy frames are handled via global linear interpolation to the neural length. Trailing frames not filling a complete bin/trial are truncated.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 6-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:230-233):
> | Full processing | ~0.5s (36k frames), ~0.7s (54k frames) | ~25s for 41 sessions |

**Code** (convert_data.py:83-87):
```python
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
dfof = s2p_preprocess(
    Fc.copy().astype(np.float32), BASELINE_METHOD, WIN_BASELINE,
    SIG_BASELINE, fs, PRCTILE_BASELINE, device=device
)
```

**What this does:** The suite2p `preprocess` (maximin baseline) call dominates runtime; it runs on GPU when available.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:177-190):
```python
for t in range(n_trials):
    start = t * TRIAL_BINS
    end = (t + 1) * TRIAL_BINS
    neural_trials.append(dfof_binned[:, start:end].astype(np.float32))
    time_sec = np.arange(start, end) * (BIN_SIZE / FRAME_RATE)
    input_trials.append(time_sec.reshape(1, -1).astype(np.float32))
    output_trials.append(me_discrete[start:end].reshape(1, -1).astype(np.int64))
```

**What this does:** The per-trial slicing loop builds trial lists by repeated slicing; could in principle be done with reshape on the binned arrays. Per-session loop in `convert_data` is inherently sequential.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py): (no relevant code found)

**What this does:** No obvious repeated computation; each session's dF/F and motion-energy pipeline is run once.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md): (none)

**Code** (convert_data.py:199-254):
```python
def plot_processing(ax_list, subj, session, F, Fneu, dfof, me, me_binned,
                    me_discrete, dfof_binned, n_frames):
    """Plot processing steps for visual verification."""
    ...
```

**What this does:** Optional `--show-processing` plotting routine generates verification figures; not used by downstream decoder. No clearly wasted core computation otherwise.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none — no memory, dtype, memory-mapping, or streaming discussion in CONVERSION_NOTES.md or README.md; README.md:43-44 only documents the stored `float32` array dtypes)

**Code** (convert_data.py:79-89, 148-164):
```python
    # Neuropil correction
    Fc = F - NEUROPIL_COEFF * Fneu

    # Suite2p baseline correction: returns Fc - F0 (baseline-subtracted)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    dfof = s2p_preprocess(
        Fc.copy().astype(np.float32), BASELINE_METHOD, WIN_BASELINE,
        SIG_BASELINE, fs, PRCTILE_BASELINE, device=device
    )
    return dfof.astype(np.float32)

    # :148-164 (process_session)
    F = np.load(os.path.join(sess_dir, 'suite2p', 'plane0', 'F.npy'))
    Fneu = np.load(os.path.join(sess_dir, 'suite2p', 'plane0', 'Fneu.npy'))
    ...
    dfof_binned = bin_timeseries(dfof, BIN_SIZE)  # (n_neurons, n_bins)
```

**What this does:** `process_session` handles one session at a time and returns only the binned, trial-split arrays, so the raw `F`/`Fneu`/`dfof` arrays go out of scope per iteration; the neural traces are held as `float32` (line 85, 89) and stored trials re-cast to `float32` (line 182). `Fc.copy()` creates an extra full-size copy before Suite2p `preprocess`, which may run on CUDA if available (line 83). No memory-mapping, chunked reads, explicit `del`, or in-place arithmetic; motion energy is interpolated in `float64` (lines 98-103).

**Rating:** match

**Note:** _(no note)_

---
