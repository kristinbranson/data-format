# hasnain2024 — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/hasnain2024/codex/2026-03-21__11-04-17_trial2/verifier/snapshot/`

Outputs identified (K=6): lick_direction, behavioral_context, outcome, tongue_velocity, paw_velocity, motion_energy

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Implemented raw-session loading with `mat73` for MATLAB v7.3/HDF5 session files and `scipy.io.loadmat` for motion-energy files." (CONVERSION_NOTES.md:267-268)
> "Implemented the reference two-context ALM session subset directly from the figure-specific session loader list in the reference code." (CONVERSION_NOTES.md:266)

**Code** (convert_data.py:50-63, 389-393, 747-756):
```python
CONTEXT_SESSION_SPECS = [
    SessionSpec("JEB6", "2021-04-18", 1),
    SessionSpec("JEB7", "2021-04-29", 0),
    SessionSpec("JEB7", "2021-04-30", 0),
    SessionSpec("EKH1", "2021-08-07", 1),
    SessionSpec("EKH3", "2021-08-11", 1),
    SessionSpec("JGR2", "2021-11-16", 0),
    SessionSpec("JGR2", "2021-11-17", 0),
    SessionSpec("JGR3", "2021-11-18", 0),
    SessionSpec("JEB19", "2023-04-21", 0),
    SessionSpec("JEB19", "2023-04-20", 0),
    SessionSpec("JEB19", "2023-04-19", 0),
    SessionSpec("JEB19", "2023-04-18", 0),
]
...
def convert_session(spec: SessionSpec, make_plot: bool = False) -> dict:
    obj = mat73.loadmat(spec.data_path)["obj"]
    me = load_motion_energy(spec)
...
    for sess_idx, spec in enumerate(session_specs):
        converted_sessions.append(convert_session(spec, make_plot=make_plot))
```

**What this does:** A hard-coded list of 12 (animal, date, probe) specs from the paper's Figure 8 two-context ALM loader is iterated; for each, the session `.mat` is loaded with `mat73` and the matching motion-energy file with `scipy.io.loadmat`. Sessions outside this list (and the entire `RandomizedDelay`/`*Inhibition` directories) are not loaded.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Subjects: 7 (`EKH1`, `EKH3`, `JEB6`, `JEB7`, `JGR2`, `JGR3`, `JEB19`)" (README.md:10)

**Code** (convert_data.py:654-663):
```python
def build_dataset(converted_sessions: list[dict]) -> dict:
    subjects = sorted({sess["subject"] for sess in converted_sessions})
    subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}

    dataset = {
        ...
        "subjects": subjects,
        "subject_idx": np.asarray([subject_to_idx[sess["subject"]] for sess in converted_sessions], dtype=np.int64),
```

**What this does:** Each `SessionSpec.animal` (e.g. "JEB6") becomes the subject id; unique sorted subject names form `subjects`, and each session's `subject_idx` is its position in that list.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sessions: 12" (README.md:9). Per-session id is `f\"{animal}_{date}\"` from `SessionSpec`.

**Code** (convert_data.py:31-48, 658-665):
```python
@dataclass(frozen=True)
class SessionSpec:
    animal: str
    date: str
    probe_index: int  # 0-based

    @property
    def session_id(self) -> str:
        return f"{self.animal}_{self.date}"
...
"neural": [sess["neural"] for sess in converted_sessions],
"input": [sess["input"] for sess in converted_sessions],
"output": [sess["output"] for sess in converted_sessions],
```

**What this does:** Each entry of `CONTEXT_SESSION_SPECS` defines one session as `<animal>_<date>` plus a probe index; `neural`/`input`/`output` are lists indexed by session in that order, and `metadata.source_session_ids` records the ids.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "5 ms spike binning from `-2.5` s to `+2.5` s" (CONVERSION_NOTES.md:270). "Window: `[-2.5, 2.5]` s around alignment" (README.md:14).

**Code** (convert_data.py:389-423, 491-508):
```python
align_times = ensure_1d_numeric(bp["ev"][ALIGN_EVENT])
valid_trials = select_valid_trials(obj)
...
for trial_idx in valid_trials:
    lick_dir = get_first_lick_direction(obj, int(trial_idx), align_times[trial_idx])
    if lick_dir is None:
        continue
    kept_trials.append(int(trial_idx))
    trial_labels.append((lick_dir, 0 if autowater[trial_idx] != 0 else 1,
                          1 if hit[trial_idx] != 0 else 0))
...
for local_trial_idx, trial_idx in enumerate(kept_trials):
    ...
    session_neural.append(neural_trial.astype(np.float32))
    session_input.append(time_input)
    session_output.append(output_trial)
```

**What this does:** Trials are indexed by the raw `bp.ev.goCue` entries (one per trial). `select_valid_trials` applies QC masks; `get_first_lick_direction` further requires a lick post-alignment. Each surviving trial produces one element in the per-session `neural`/`input`/`output` lists, each of length `n_timepoints=1000` (5 ms bins over `[-2.5, 2.5]`).

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Keep `hit` or `miss` trials; Exclude `early` trials; Exclude `no` / ignore trials; Exclude stimulation trials; Require a valid first post-alignment lick direction" (README.md:18-22)

**Code** (convert_data.py:322-342, 405-421):
```python
def select_valid_trials(obj: dict) -> np.ndarray:
    bp = obj["bp"]
    early = ensure_1d_numeric(bp["early"]) != 0
    no = ensure_1d_numeric(bp["no"]) != 0
    hit = ensure_1d_numeric(bp["hit"]) != 0
    miss = ensure_1d_numeric(bp["miss"]) != 0
    stim_enable = ensure_1d_numeric(bp["stim"]["enable"]) != 0
    valid = (~early) & (~no) & (~stim_enable) & (hit | miss)
    return np.flatnonzero(valid)

def get_first_lick_direction(obj, trial_idx, go_time):
    lick_l = event_list_to_array(obj["bp"]["ev"]["lickL"][trial_idx])
    lick_r = event_list_to_array(obj["bp"]["ev"]["lickR"][trial_idx])
    lick_l = lick_l[lick_l >= go_time]
    lick_r = lick_r[lick_r >= go_time]
    ...
    return 0 if first_l < first_r else 1
```

**What this does:** Trials must be `hit | miss`, not `early`, not `no`, and not have `stim.enable`. They additionally must have at least one post-`goCue` `lickL` or `lickR` event; trials with no licks after the go cue are dropped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`obj.clu{probe}[*].trialtm`, `obj.clu{probe}[*].trial`, `bp.ev.goCue` -> `neural` ..." (CONVERSION_NOTES.md:228)
> "Source: electrophysiology spike times from the ALM probe selected by the paper's Figure 8 session loaders" (README.md:26)

**Code** (convert_data.py:425-453):
```python
clu = obj["clu"][spec.probe_index]
...
unit_quality = [str(q).strip() if q is not None else "" for q in clu["quality"]]
quality_keep = np.asarray([keep_quality(q) for q in unit_quality], dtype=bool)
...
for unit_idx, use_unit in enumerate(quality_keep):
    if not use_unit:
        continue
    mean_fr = mean_firing_rate_window(
        clu["trialtm"][unit_idx],
        np.asarray(clu["trial"][unit_idx], dtype=np.int64),
        align_times,
    )
    ...
    trialdat = bin_unit_spikes(
        clu["trialtm"][unit_idx],
        np.asarray(clu["trial"][unit_idx], dtype=np.int64),
        align_times, kept_trials,
    )
```

**What this does:** `neural` is built from `obj.clu[probe_index]` per-unit fields `trialtm` (per-spike trial-relative times), `trial` (per-spike 1-based trial number), and `quality` labels, using `bp.ev.goCue` (the alignment event) to compute go-cue-relative spike times.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Binning: 5 ms; Representation: single-trial firing rates; Smoothing: causal Gaussian (`smooth = 15`, `bctype = reflect`)" (README.md:27-29)

**Code** (convert_data.py:352-374, 66-104):
```python
def bin_unit_spikes(trialtm, trial_numbers_1based, align_times, kept_trials_0based):
    ...
    aligned = trialtm[valid_spikes] - align_times[trial_numbers_1based[valid_spikes] - 1]
    ...
    bin_idx = np.floor((aligned - TMIN) / DT).astype(np.int64)
    ...
    aligned_counts = np.zeros((kept_trials_0based.size, TIME_AXIS.size), dtype=np.float64)
    np.add.at(aligned_counts, (spike_local_trial[valid_bins], bin_idx[valid_bins]), 1.0)
    rates = aligned_counts / DT
    rates = my_smooth(rates.T, SMOOTH_N, BCTYPE).T
    return rates

# my_smooth: causal Gaussian (right half of kernel zeroed) with reflect boundary
kern = gaussian_window(n)
kern[: len(kern) // 2] = 0.0
kern /= np.sum(kern)
```

**What this does:** Spike times are subtracted from each trial's `goCue`, binned into 5 ms bins over `[-2.5, 2.5]` (1000 bins) using `np.add.at`, divided by `dt` to convert counts to firing rate, and smoothed with a causal Gaussian (window length 15, only the left half non-zero, reflect boundary on the leading edge). Output cast to `float32`.

**Rating:** ok

**Note:** _(no note)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "exclude quality labels `garbage`, `gabrga`, `noisy`, `real?`; keep units with mean firing rate `> 1 Hz` in the aligned window across all session trials" (README.md:31-32)

**Code** (convert_data.py:24-26, 345-349, 377-386, 429-445):
```python
LOW_FR_HZ = 1.0
QUALITY_EXCLUDE = {"garbage", "gabrga", "noisy", "real?"}
...
def keep_quality(quality: str) -> bool:
    quality = str(quality).strip()
    return quality not in QUALITY_EXCLUDE

def mean_firing_rate_window(trialtm, trial_numbers_1based, align_times):
    aligned = trialtm - align_times[trial_numbers_1based - 1]
    in_window = (aligned >= TMIN) & (aligned < TMAX)
    return float(np.sum(in_window) / (align_times.size * (TMAX - TMIN)))
...
quality_keep = np.asarray([keep_quality(q) for q in unit_quality], dtype=bool)
...
if mean_fr <= LOW_FR_HZ: continue
```

**What this does:** Two-stage unit curation: (1) drop units whose `clu.quality` string is in {`garbage`, `gabrga`, `noisy`, `real?`}; (2) compute mean firing rate over the `[-2.5, 2.5]` window across all session trials and drop units with mean FR `<= 1 Hz`.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trials are aligned to the stored `bp.ev.goCue` event. In delayed-response (DR) trials this is the auditory go cue; in water-cued (WC) trials the stored field acts as the water-presentation-equivalent event used throughout the conversion." (README.md:5)

**Code** (convert_data.py:25, 396, 366-368):
```python
ALIGN_EVENT = "goCue"
...
align_times = ensure_1d_numeric(bp["ev"][ALIGN_EVENT])
...
aligned = trialtm[valid_spikes] - align_times[trial_numbers_1based[valid_spikes] - 1]
...
bin_idx = np.floor((aligned - TMIN) / DT).astype(np.int64)
```

**What this does:** Per-trial `goCue` times are read from `bp.ev.goCue` and subtracted from each spike's `trialtm` so that t=0 corresponds to the go cue (or the goCue-equivalent event on WC trials). The same `align_times` vector is used for kinematics, motion energy, and lick events.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "5 ms spike binning from `-2.5` s to `+2.5` s" (CONVERSION_NOTES.md:270). "Time bin: 5 ms" (README.md:13)

**Code** (convert_data.py:19-28, 368-373):
```python
DT = 0.005
TMIN = -2.5
TMAX = 2.5
TIME_AXIS = np.arange(TMIN, TMAX, DT, dtype=np.float64) + DT / 2.0
EDGES = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
...
bin_idx = np.floor((aligned - TMIN) / DT).astype(np.int64)
valid_bins = (bin_idx >= 0) & (bin_idx < TIME_AXIS.size)
aligned_counts = np.zeros((kept_trials_0based.size, TIME_AXIS.size), dtype=np.float64)
np.add.at(aligned_counts, (spike_local_trial[valid_bins], bin_idx[valid_bins]), 1.0)
rates = aligned_counts / DT
```

**What this does:** A fixed 5 ms uniform grid spans `[-2.5, 2.5)` (1000 bins, bin centers stored in `TIME_AXIS`). Spike times relative to `goCue` are floored to bin index, accumulated into counts via `np.add.at`, divided by `DT` to give Hz, then smoothed.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_go_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:229 — `| Common aligned time axis | `input[0]` | Continuous time-from-go-cue vector repeated for every trial | Reference decoders train one model per time bin after alignment | Single decoder input requested by user. |`
> CONVERSION_NOTES.md:371 — "`time_from_go_cue_seconds` range | Go-cue-centered analyses throughout paper | `alignEvent = 'goCue'` | Raw `goCue` available on DR and WC trials | [-2.5, 2.5] | Yes"
> CONVERSION_NOTES.md:277 — "1 time-varying decoder input (`time_from_go_cue_seconds`)"

**Code** (convert_data.py:19-28, 396, 666):
```python
DT = 0.005
TMIN = -2.5
TMAX = 2.5
SMOOTH_N = 15
BCTYPE = "reflect"
LOW_FR_HZ = 1.0
ALIGN_EVENT = "goCue"
QUALITY_EXCLUDE = {"garbage", "gabrga", "noisy", "real?"}
TIME_AXIS = np.arange(TMIN, TMAX, DT, dtype=np.float64) + DT / 2.0
EDGES = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
...
    align_times = ensure_1d_numeric(bp["ev"][ALIGN_EVENT])
...
        "input_names": ["time_from_go_cue_seconds"],
```

**What this does:** The trial produces a single input named `time_from_go_cue_seconds`. Its values come from the module-level `TIME_AXIS` constant defined by `TMIN`/`TMAX`/`DT`, not from a per-trial raw field; the raw variable giving it its meaning is `bp.ev.goCue` (`ALIGN_EVENT`), the per-trial event time subtracted from spike times.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_go_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:306 — `| `time_from_go_cue_seconds` range | [-2.5, 2.5] |`
> CONVERSION_NOTES.md:388 — "Input check: converted `time_from_go_cue_seconds` matched the independently reconstructed 5 ms time axis exactly (`np.allclose = True`)."
> CONVERSION_NOTES.md:409-411 — "reference decoders train separate models at each aligned time bin rather than using an explicit 'time' predictor array / conversion stores the aligned time axis as the requested decoder input"

**Code** (convert_data.py:27-28, 491-507):
```python
TIME_AXIS = np.arange(TMIN, TMAX, DT, dtype=np.float64) + DT / 2.0
EDGES = np.arange(TMIN, TMAX + DT, DT, dtype=np.float64)
...
    for local_trial_idx, trial_idx in enumerate(kept_trials):
        lick_dir, context_label, outcome_label = trial_labels[local_trial_idx]
        neural_trial = neural_by_trial[:, local_trial_idx, :]
        time_input = TIME_AXIS[None, :].astype(np.float32)
        ...
        session_neural.append(neural_trial.astype(np.float32))
        session_input.append(time_input)
        session_output.append(output_trial)
```

**What this does:** `TIME_AXIS` is computed once at import as `np.arange(-2.5, 2.5, 0.005) + 0.0025`, i.e. the centers of the 1000 5 ms bins. Inside the per-trial loop it is reshaped to `(1, n_timepoints)` and cast to float32, so each kept trial receives an identical copy with no per-trial computation.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_go_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:405-408 — "reference aligns to `goCue` ... conversion aligns to `bp.ev.goCue` with `[-2.5, 2.5]` and `5 ms` bins / result: alignment matched"
> CONVERSION_NOTES.md:229 — "Common aligned time axis | `input[0]` | Continuous time-from-go-cue vector repeated for every trial"

**Code** (convert_data.py:366-372, 396, 494, 691-693):
```python
    aligned = trialtm[valid_spikes] - align_times[trial_numbers_1based[valid_spikes] - 1]
    spike_local_trial = spike_local_trial[valid_spikes]
    bin_idx = np.floor((aligned - TMIN) / DT).astype(np.int64)
    valid_bins = (bin_idx >= 0) & (bin_idx < TIME_AXIS.size)
    aligned_counts = np.zeros((kept_trials_0based.size, TIME_AXIS.size), dtype=np.float64)
    np.add.at(aligned_counts, (spike_local_trial[valid_bins], bin_idx[valid_bins]), 1.0)
    rates = aligned_counts / DT
...
    align_times = ensure_1d_numeric(bp["ev"][ALIGN_EVENT])
...
        time_input = TIME_AXIS[None, :].astype(np.float32)
...
            "temporal_alignment_event": "bp.ev.goCue",
            "off_start": TMIN,
            "off_end": TMAX,
```

**What this does:** Spike times are shifted by each trial's `bp.ev.goCue` and binned with `bin_idx = floor((aligned - TMIN)/DT)` into arrays sized `TIME_AXIS.size`, so the input vector is exactly the bin-center coordinate of each neural column and shares its length. Metadata reports the alignment event as `bp.ev.goCue` with window -2.5 to 2.5 s.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *lick_direction* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "First post-alignment lick side from `bp.ev.lickL` / `bp.ev.lickR` -> `output[0]` ... left = 0, right = 1" (CONVERSION_NOTES.md:230)

**Code** (convert_data.py:333-342):
```python
def get_first_lick_direction(obj: dict, trial_idx: int, go_time: float) -> int | None:
    lick_l = event_list_to_array(obj["bp"]["ev"]["lickL"][trial_idx])
    lick_r = event_list_to_array(obj["bp"]["ev"]["lickR"][trial_idx])
    lick_l = lick_l[lick_l >= go_time]
    lick_r = lick_r[lick_r >= go_time]
    first_l = lick_l[0] if lick_l.size else math.inf
    first_r = lick_r[0] if lick_r.size else math.inf
    if math.isinf(first_l) and math.isinf(first_r):
        return None
    return 0 if first_l < first_r else 1
```

**What this does:** Derived from `bp.ev.lickL` and `bp.ev.lickR` event-time arrays per trial, plus the trial's `goCue` to define "post-alignment". Not derived from `bp.R`/`bp.L` instructed sides.

**Rating:** match

**Note:** _(no note)_---

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`lick_direction`: `left=0`, `right=1`" (README.md:52). "constant-in-time traces for per-trial categorical variables" (CONVERSION_NOTES.md:280)

**Code** (convert_data.py:333-342, 491-499):
```python
return 0 if first_l < first_r else 1
...
output_trial = np.vstack([
    np.full(TIME_AXIS.size, lick_dir, dtype=np.int64),
    ...
])
```

**What this does:** For each kept trial, the side of the earliest post-`goCue` lick (L vs R) becomes a single int (0 or 1) which is broadcast to a constant length-1000 trace as row 0 of the per-trial `output` matrix.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *context* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`bp.autowater` -> `output[1]` ... WC = 0, DR = 1" (CONVERSION_NOTES.md:231)

**Code** (convert_data.py:401, 413-414):
```python
autowater = ensure_1d_numeric(bp["autowater"])
...
trial_labels.append((
    lick_dir,
    0 if autowater[trial_idx] != 0 else 1,
    ...
))
```

**What this does:** Derived solely from `bp.autowater` (per-trial boolean): autowater -> WC (0), not-autowater -> DR (1).

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *context*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`behavioral_context`: `WC=0`, `DR=1`" (README.md:53). "constant-in-time traces for per-trial categorical variables" (CONVERSION_NOTES.md:280)

**Code** (convert_data.py:413-414, 496-500):
```python
0 if autowater[trial_idx] != 0 else 1,
...
output_trial = np.vstack([
    np.full(TIME_AXIS.size, lick_dir, dtype=np.int64),
    np.full(TIME_AXIS.size, context_label, dtype=np.int64),
    ...
])
```

**What this does:** The per-trial context label is broadcast to a constant length-1000 trace as row 1 of the per-trial `output` matrix.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`bp.hit`, `bp.miss` -> `output[2]` ... incorrect = 0, correct = 1" (CONVERSION_NOTES.md:232)

**Code** (convert_data.py:402, 415):
```python
hit = ensure_1d_numeric(bp["hit"])
...
trial_labels.append((
    lick_dir,
    0 if autowater[trial_idx] != 0 else 1,
    1 if hit[trial_idx] != 0 else 0,
))
```

**What this does:** Derived only from `bp.hit` (with `bp.miss` used implicitly via the trial filter requiring `hit | miss`); `hit==1` -> correct (1), else incorrect (0).

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`outcome`: `incorrect=0`, `correct=1`" (README.md:54)

**Code** (convert_data.py:415, 496-501):
```python
1 if hit[trial_idx] != 0 else 0,
...
output_trial = np.vstack([
    ...,
    np.full(TIME_AXIS.size, outcome_label, dtype=np.int64),
    ...,
])
```

**What this does:** Per-trial 0/1 label broadcast to a constant length-1000 trace as row 2 of the per-trial `output` matrix.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "DLC kinematics for side-view tongue feature -> `output[3]` ... `sqrt(xvel^2 + yvel^2)` for `tongue_*_view1`" (CONVERSION_NOTES.md:233)

**Code** (convert_data.py:461-465):
```python
vidshift = compute_vidshift(obj)
tongue_x, tongue_y = align_feature_positions(obj, 0, "tongue", align_times, TIME_AXIS, vidshift)
tongue_visible = np.isfinite(tongue_x) & np.isfinite(tongue_y)
tongue_vx, tongue_vy = compute_velocity(tongue_x, tongue_y, "tongue")
tongue_speed = np.sqrt(tongue_vx**2 + tongue_vy**2)
```

**What this does:** Derived from side-view DLC tongue x/y positions (`obj.traj[0]` "tongue" feature `ts[:, 0:2, feat_index]`), per-trial `frameTimes`, plus `vidshift` (computed from `bp.ev.bitStart` and `sglx.bitcode.bitstart/sglx.fs`) and the trial's `goCue` for alignment.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying binary trace from per-timepoint tongue-speed magnitude, thresholded at session median" (CONVERSION_NOTES.md:233). Tongue threshold computed only from tongue-visible timepoints; invisible timepoints set to low bin (CONVERSION_NOTES.md:317-318).

**Code** (convert_data.py:249-275, 479-485, 495):
```python
xv = np.gradient(tsinterp[:, 0]); yv = np.gradient(tsinterp[:, 1])
... # tongue branch: NaN -> 0 instead of nearest-fill / baseline subtraction
tongue_speed = np.sqrt(tongue_vx**2 + tongue_vy**2)
...
if np.any(tongue_visible_kept):
    tongue_threshold = float(np.nanpercentile(tongue_speed[:, kept_trials][tongue_visible_kept], 50))
...
tongue_bin = ((tongue_speed[:, trial_idx] >= tongue_threshold) & tongue_visible[:, trial_idx]).astype(np.int64)
```

**What this does:** Tongue x/y positions are linearly interpolated onto the 5 ms `TIME_AXIS` (no nearest-fill across NaNs since tongue has visibility gaps). Velocity = `np.gradient` per axis; speed = sqrt(vx^2+vy^2). The session-median threshold uses only tongue-visible samples; final binary is `speed >= threshold AND visible`, so invisible periods always go to the low bin.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 7-d. How is `output` *tongue_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Motion energy is loaded from companion files and aligned to the same trial-centered time axis by interpolating DLC/video-timestamped traces onto `obj.time + params.advance_movement`, after subtracting the video offset and the chosen alignment event time." (CONVERSION_NOTES.md:60)

**Code** (convert_data.py:187-190, 222-240, 461-462):
```python
def compute_vidshift(obj: dict) -> float:
    bit_start = mode_value(obj["bp"]["ev"]["bitStart"])
    vid_file_offset = mode_value(obj["sglx"]["bitcode"]["bitstart"]) / float(obj["sglx"]["fs"])
    return float(vid_file_offset - bit_start)
...
if frame_times is None:
    frame_times = (np.arange(ts.shape[0], dtype=np.float64) + 1.0) / 400.0
else:
    frame_times = ensure_1d_numeric(frame_times)
if frame_times.size == 0 or np.all(np.isnan(frame_times)):
    frame_times = (np.arange(ts.shape[0], dtype=np.float64) + 1.0) / 400.0

xy = ts[:, 0:2, feat_index]
...
shifted_time = frame_times - vidshift - align_times[trial_idx]
valid = np.isfinite(shifted_time) & np.isfinite(xy[:, 0]) & np.isfinite(xy[:, 1])
if np.sum(valid) < 2:
    continue

xpos[:, trial_idx] = np.interp(time_axis, shifted_time[valid], xy[valid, 0], left=np.nan, right=np.nan)
ypos[:, trial_idx] = np.interp(time_axis, shifted_time[valid], xy[valid, 1], left=np.nan, right=np.nan)
...
vidshift = compute_vidshift(obj)
tongue_x, tongue_y = align_feature_positions(obj, 0, "tongue", align_times, TIME_AXIS, vidshift)
```

**What this does:** Side-view DLC tongue x/y are first re-referenced to neural time per trial via `shifted_time = frame_times - vidshift - align_times[trial_idx]`, where `vidshift = sglx.bitcode.bitstart/sglx.fs - bp.ev.bitStart` and `align_times` are `bp.ev.goCue`. Positions are then linearly interpolated with `np.interp` onto the same 5 ms `TIME_AXIS` (`[-2.5, 2.5)`, 1000 bins) used for spike binning; velocity/speed are computed on this aligned grid.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "DLC kinematics for bottom-view paw feature(s) -> `output[4]` ... mean speed magnitude across `top_paw` and `bottom_paw` in view 2." (CONVERSION_NOTES.md:234)

**Code** (convert_data.py:467-475):
```python
paw_speeds = []
for paw_feat in ("top_paw", "bottom_paw"):
    paw_x, paw_y = align_feature_positions(obj, 1, paw_feat, align_times, TIME_AXIS, vidshift)
    paw_vx, paw_vy = compute_velocity(paw_x, paw_y, paw_feat)
    paw_speeds.append(np.sqrt(paw_vx**2 + paw_vy**2))
paw_stack = np.stack(paw_speeds, axis=0)
paw_counts = np.sum(np.isfinite(paw_stack), axis=0)
paw_speed = np.full(paw_counts.shape, np.nan, dtype=np.float64)
np.divide(np.nansum(paw_stack, axis=0), paw_counts, out=paw_speed, where=paw_counts > 0)
```

**What this does:** Derived from bottom-view DLC features `top_paw` and `bottom_paw` x/y positions in `obj.traj[1]`, plus `frameTimes`, `vidshift`, and per-trial `goCue` for alignment.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying binary trace from per-timepoint paw-speed magnitude, thresholded at session median" (CONVERSION_NOTES.md:234)

**Code** (convert_data.py:249-275, 467-475, 484, 502):
```python
xv = np.gradient(tsinterp[:, 0]); yv = np.gradient(tsinterp[:, 1])
xv = xv - basederiv[0]; yv = yv - basederiv[0]   # non-tongue branch
xv = fill_nearest_1d(xv); yv = fill_nearest_1d(yv)
...
paw_speed = mean of sqrt(xvel^2 + yvel^2) across {top_paw, bottom_paw}
paw_threshold = float(np.nanpercentile(paw_speed[:, kept_trials], 50))
(paw_speed[:, trial_idx] >= paw_threshold).astype(np.int64)
```

**What this does:** Per-paw x/y positions are linearly interpolated onto `TIME_AXIS`, gap-filled by nearest-value, velocity from `np.gradient` minus per-trial median-derivative baseline; speed = sqrt(vx^2+vy^2) per paw; the two paws are averaged element-wise. Each timepoint is binarized at the session-wide 50th percentile of paw speed.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 8-d. How is `output` *paw_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Kinematics are derived from DLC trajectories, producing x/y displacement and x/y velocity for each tracked feature from both views, then concatenated into a common `(time, trials, features)` representation." (CONVERSION_NOTES.md:61)

**Code** (convert_data.py:187-190, 234-244, 461, 467-471):
```python
def compute_vidshift(obj: dict) -> float:
    bit_start = mode_value(obj["bp"]["ev"]["bitStart"])
    vid_file_offset = mode_value(obj["sglx"]["bitcode"]["bitstart"]) / float(obj["sglx"]["fs"])
    return float(vid_file_offset - bit_start)
...
shifted_time = frame_times - vidshift - align_times[trial_idx]
valid = np.isfinite(shifted_time) & np.isfinite(xy[:, 0]) & np.isfinite(xy[:, 1])
if np.sum(valid) < 2:
    continue
xpos[:, trial_idx] = np.interp(time_axis, shifted_time[valid], xy[valid, 0], left=np.nan, right=np.nan)
ypos[:, trial_idx] = np.interp(time_axis, shifted_time[valid], xy[valid, 1], left=np.nan, right=np.nan)

if "tongue" not in feat_name:
    xpos[:, trial_idx] = fill_nearest_1d(xpos[:, trial_idx])
    ypos[:, trial_idx] = fill_nearest_1d(ypos[:, trial_idx])
...
vidshift = compute_vidshift(obj)
...
for paw_feat in ("top_paw", "bottom_paw"):
    paw_x, paw_y = align_feature_positions(obj, 1, paw_feat, align_times, TIME_AXIS, vidshift)
```

**What this does:** Per-trial bottom-view DLC paw x/y are aligned with the same recipe used for tongue: per-trial `frame_times` are shifted by `-vidshift - align_times[trial_idx]` (where `align_times = bp.ev.goCue`), then linearly interpolated onto the 5 ms `TIME_AXIS`; for non-tongue features residual NaNs are nearest-filled before velocity computation. The same aligned grid is used for both `top_paw` and `bottom_paw` before averaging speeds.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Motion-energy trace -> `output[5]` ... aligned motion-energy stream after interpolation onto neural time base." (CONVERSION_NOTES.md:235)

**Code** (convert_data.py:278-296):
```python
def load_motion_energy(spec: SessionSpec) -> dict:
    me_mat = loadmat(spec.motion_energy_path, squeeze_me=True, struct_as_record=False)
    me = me_mat["me"]
    return {"data": np.atleast_1d(me.data), "moveThresh": float(me.moveThresh)}

def align_motion_energy(obj, me, align_times, time_axis):
    vidshift = compute_vidshift(obj)
    view_dict = obj["traj"][0]
    ...
    frame_times = view_dict["frameTimes"][trial_idx]
    me_trial = np.asarray(me["data"][trial_idx], dtype=np.float64).reshape(-1)
```

**What this does:** Derived from the per-trial `me.data` array in companion `motionEnergy_<animal>_<date>.mat` files, plus side-view `frameTimes` from `obj.traj[0]`, `vidshift`, and per-trial `goCue`. The raw `me.moveThresh` is loaded but unused.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Time-varying binary trace from aligned motion-energy value, thresholded at session median" (CONVERSION_NOTES.md:235)

**Code** (convert_data.py:308-319, 485, 503):
```python
n = min(frame_times.size, me_trial.size)
frame_times = frame_times[:n]; me_trial = me_trial[:n]
...
shifted_time = frame_times[valid] - vidshift - align_times[trial_idx]
aligned[:, trial_idx] = np.interp(time_axis, shifted_time, me_trial[valid], left=np.nan, right=np.nan)
aligned[:, trial_idx] = fill_nearest_1d(aligned[:, trial_idx])
...
me_threshold = float(np.nanpercentile(motion_energy[:, kept_trials], 50))
(motion_energy[:, trial_idx] >= me_threshold).astype(np.int64)
```

**What this does:** Raw `me.data` is truncated to match `frameTimes` length, then linearly interpolated onto the 5 ms `TIME_AXIS` after subtracting `vidshift` and the trial's `goCue`; gaps nearest-filled. Each timepoint is binarized at the session-wide 50th percentile of aligned ME, and stored as row 5 of `output`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "motion-energy interpolation onto the neural time axis using video timestamps and video offset" (CONVERSION_NOTES.md:274)
> "Motion-energy alignment spot-check: compare converted aligned motion-energy trace for a chosen trial against direct interpolation from the raw motion-energy file using raw frame times and `goCue`, with `np.allclose()` after matching binning." (CONVERSION_NOTES.md:255)

**Code** (convert_data.py:287-317):
```python
def align_motion_energy(obj: dict, me: dict, align_times: np.ndarray, time_axis: np.ndarray) -> np.ndarray:
    vidshift = compute_vidshift(obj)
    view_dict = obj["traj"][0]
    n_trials = int(obj["bp"]["Ntrials"])
    aligned = np.full((time_axis.size, n_trials), np.nan, dtype=np.float64)

    for trial_idx in range(n_trials):
        frame_times = view_dict["frameTimes"][trial_idx]
        ts = view_dict["ts"][trial_idx]
        me_trial = np.asarray(me["data"][trial_idx], dtype=np.float64).reshape(-1)
        ...
        n = min(frame_times.size, me_trial.size)
        frame_times = frame_times[:n]
        me_trial = me_trial[:n]
        valid = np.isfinite(frame_times) & np.isfinite(me_trial)
        if np.sum(valid) < 2:
            continue

        shifted_time = frame_times[valid] - vidshift - align_times[trial_idx]
        aligned[:, trial_idx] = np.interp(time_axis, shifted_time, me_trial[valid], left=np.nan, right=np.nan)
        aligned[:, trial_idx] = fill_nearest_1d(aligned[:, trial_idx])
```

**What this does:** Per-trial motion-energy samples are paired with side-view (`obj.traj[0]`) `frameTimes`, truncated to a common length, then re-referenced to the neural clock as `shifted_time = frame_times[valid] - vidshift - align_times[trial_idx]` (with `align_times = bp.ev.goCue` and `vidshift = sglx.bitcode.bitstart/sglx.fs - bp.ev.bitStart`). The shifted samples are linearly interpolated with `np.interp` onto the same 5 ms `TIME_AXIS` used for spikes, and remaining NaNs are nearest-filled.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`cache/step10_checks.py` found `2` raw trials with empty/all-NaN `frameTimes`; the conversion already handles this by falling back to the nominal 400 Hz frame grid... `527` raw trials in the selected sessions had the tongue completely invisible; the conversion ... treats missing tongue velocity as zero and keeps invisible periods in the low bin." (CONVERSION_NOTES.md:424-426)

**Code** (convert_data.py:138-147, 209-228, 296-307, 333-342):
```python
def fill_nearest_1d(x):
    ...
    x[~good] = np.interp(idx[~good], idx[good], x[good])

# kinematics
if frame_times is None or frame_times.size == 0 or np.all(np.isnan(frame_times)):
    frame_times = (np.arange(ts.shape[0], dtype=np.float64) + 1.0) / 400.0
if np.sum(valid) < 2: continue          # leave column NaN
xpos[:, trial_idx] = fill_nearest_1d(xpos[:, trial_idx])

# tongue
xv = np.where(np.isfinite(xv), xv, 0.0)

# lick
if math.isinf(first_l) and math.isinf(first_r):
    return None    # trial dropped
```

**What this does:** Missing video frame times -> fallback to a synthetic 400 Hz grid. Sparse NaNs in interpolated positions/ME -> nearest-neighbor fill (non-tongue) or zero (tongue velocity). Trials with no usable lick events are dropped. Trials with all-NaN `NdroppedFrames` skip kinematics for that trial. Empty quality strings are treated as kept.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Conversion (sample measurement) | ~7.4 s/session | ~1.5-2 min for 12 sessions" (CONVERSION_NOTES.md:331). "Full MATLAB session objects are loaded into memory per session via `mat73`" (CONVERSION_NOTES.md:285).

**Code** (convert_data.py:392, 207-246, 434-453):
```python
obj = mat73.loadmat(spec.data_path)["obj"]   # whole HDF5 session into RAM
...
for trial_idx in range(n_trials):            # per-trial Python loops in
    ... np.interp(time_axis, ...)            # align_feature_positions /
                                             # align_motion_energy
...
for unit_idx, use_unit in enumerate(quality_keep):
    ... bin_unit_spikes(...)                 # per-unit Python loop
```

**What this does:** Loading the v7.3/HDF5 session with `mat73` and the per-unit / per-trial Python loops for spike binning, kinematics interpolation, and motion-energy alignment dominate runtime; reported as ~7.4 s/session.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Kinematic alignment currently interpolates each requested feature trial-by-trial in Python loops." (CONVERSION_NOTES.md:286)

**Code** (convert_data.py:207-246, 253-275, 293-319, 436-453):
```python
for trial_idx in range(n_trials):
    ...
    xpos[:, trial_idx] = np.interp(time_axis, shifted_time[valid], xy[valid, 0], ...)
...
for trial_idx in range(xpos.shape[1]):
    ... np.gradient(...)
...
for trial_idx in range(n_trials):
    ... np.interp(time_axis, shifted_time, me_trial[valid], ...)
...
for unit_idx, use_unit in enumerate(quality_keep):
    bin_unit_spikes(...)
```

**What this does:** Per-trial loops in `align_feature_positions`, `compute_velocity`, and `align_motion_energy`, plus per-unit loops in `convert_session` and the per-column `np.convolve` loop in `my_smooth`, are written serially in Python and could be batched.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 11-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none explicit)

**Code** (convert_data.py:439-453, 461-475, 287-296):
```python
mean_fr = mean_firing_rate_window(clu["trialtm"][unit_idx],
                                  np.asarray(clu["trial"][unit_idx], dtype=np.int64),
                                  align_times)
...
trialdat = bin_unit_spikes(clu["trialtm"][unit_idx],
                           np.asarray(clu["trial"][unit_idx], dtype=np.int64),
                           align_times, kept_trials)
...
tongue_x, tongue_y = align_feature_positions(obj, 0, "tongue", ...)
for paw_feat in ("top_paw", "bottom_paw"):
    paw_x, paw_y = align_feature_positions(obj, 1, paw_feat, ...)
def align_motion_energy(obj, me, ...):
    vidshift = compute_vidshift(obj)         # already computed in convert_session
```

**What this does:** Per-unit alignment subtraction of `align_times` and the Trial->local-trial map is recomputed inside `mean_firing_rate_window` and again in `bin_unit_spikes`. `align_feature_positions` re-flattens `featNames` and recomputes shifted_time per feature/trial. `compute_vidshift(obj)` runs once in `convert_session` and again inside `align_motion_energy`. The `(time, trial, feature)` interpolation pipeline is repeated separately for tongue, top_paw, bottom_paw.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Only the exact kinematic features needed for the requested outputs are extracted (`tongue`, `top_paw`, `bottom_paw`) instead of the full feature set." (CONVERSION_NOTES.md:289)

**Code** (convert_data.py:278-284, 491-508):
```python
return {"data": np.atleast_1d(me.data),
        "moveThresh": float(me.moveThresh)}    # moveThresh never used downstream
...
time_input = TIME_AXIS[None, :].astype(np.float32)   # identical for every trial
session_input.append(time_input)
```

**What this does:** `me.moveThresh` is loaded per session but never referenced again (replaced by computed median). The same `TIME_AXIS` is rebuilt and stored once per trial as the `input`, which is identical for all trials. Smoothing is applied to all 1000 bins of every kept unit even though downstream decoders may window-aggregate.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Full MATLAB session objects are loaded into memory per session via `mat73`, which is simpler and reliable but not maximally lean." (CONVERSION_NOTES.md:285)

**Code** (convert_data.py:458, 506, 522, 754-756):
```python
neural_by_trial = np.stack(neural_trials_by_unit, axis=0).astype(np.float32)
...
session_neural.append(neural_trial.astype(np.float32))
...
"brain_region_idx": np.zeros((neural_by_trial.shape[0],), dtype=np.int64),
...
for sess_idx, spec in enumerate(session_specs):
    converted_sessions.append(convert_session(spec, make_plot=make_plot))
```

**What this does:** Neural arrays are downcast to `float32`; output traces use `int64`. Sessions are processed one at a time with no explicit caching across sessions, but the full session `obj` is held in memory during processing and all converted sessions are accumulated in a list before pickling. There is no streaming write of `converted_data.pkl`.

**Rating:** match

**Note:** _(no note)_---

---
