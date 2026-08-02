# hasnain2024 — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/hasnain2024/codex/2026-03-21__11-04-17_trial3/verifier/snapshot/`

Outputs identified (K=6): lick_direction, behavioral_context, outcome, tongue_velocity_bin, paw_velocity_bin, motion_energy_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Parses the reference MATLAB loader files to recover the analyzed session lists and selected probes." (CONVERSION_NOTES.md:257-258)
> "Uses `pymatreader` to load both v7.3/HDF5 and older MATLAB files into a consistent Python representation." (CONVERSION_NOTES.md:260)

**Code** (convert_data.py:165-171, 1054-1062):
```python
def get_reference_sessions() -> List[SessionSpec]:
    sessions: List[SessionSpec] = []
    for loader in FIXED_DELAY_LOADERS:
        sessions.extend(parse_loader_file(loader, folder="Ephys_Behavior", task="fixed_delay"))
    for loader in RANDOMIZED_DELAY_LOADERS:
        sessions.extend(parse_loader_file(loader, folder="RandomizedDelay_Ephys_Behavior", task="randomized_delay"))
    return sessions
...
session_specs = get_reference_sessions()
...
data = build_dataset(session_specs, show_processing=args.show_processing)
```
And per-session loading (convert_data.py:804-806):
```python
obj = read_mat(spec.data_path)["obj"]
probes = normalize_probe_container(obj.get("clu"))
align_times = to_vector(obj["bp"]["ev"]["goCue"], float)
```

**What this does:** Parses the MATLAB loader scripts (`load<SUBJ>_ALMVideo.m`) for fixed-delay and randomized-delay subjects to enumerate session+probe specs, then for each session loads `data_structure_<subject>_<date>.mat` via `pymatreader.read_mat` and extracts the `obj` struct.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:218-220):
> "Session inclusion: Include only neural sessions represented in the reference ephys loaders. Fixed-delay set: all 25 sessions in `Ephys_Behavior`. Randomized-delay set: the 19-session subset encoded by `loadJEB11_ALMVideo`, ..."

**Code** (convert_data.py:62-71, 989-991, 1004-1005):
```python
@dataclass(frozen=True)
class SessionSpec:
    subject: str
    date: str
    probe: Tuple[int, ...]
    folder: str
    task: str

    @property
    def session_id(self) -> str:
        return f"{self.subject}_{self.date}"
...
if spec.subject not in subject_order:
    subject_order.append(spec.subject)
subject_idx.append(subject_order.index(spec.subject))
...
"subjects": subject_order,
"subject_idx": np.asarray(subject_idx, dtype=np.int64),
```

**What this does:** Subject identifier is parsed from the loader filename and stored on each SessionSpec; in `build_dataset`, each session's subject is mapped to an index into `subject_order` (a stable list of unique subjects encountered).

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:218-221):
> "Session inclusion: Include only neural sessions represented in the reference ephys loaders. Fixed-delay set: all 25 sessions in `Ephys_Behavior`. Randomized-delay set: the 19-session subset encoded by `loadJEB11_ALMVideo`, `loadJEB12_ALMVideo`, `loadJEB23_ALMVideo`, and `loadJEB24_ALMVideo`."

**Code** (convert_data.py:120-162):
```python
def parse_loader_file(loader_name: str, folder: str, task: str) -> List[SessionSpec]:
    ...
    date_re = re.compile(r"meta\(end\)\.date = '([^']+)'")
    probe_re = re.compile(r"meta\(end\)\.probe = (\[[^\]]+\]|[0-9]+)")
    ...
    if "datapth = fullfile" in line and current_date is not None and current_probe is not None:
        sessions.append(SessionSpec(subject=subject, date=current_date,
                                    probe=current_probe, folder=folder, task=task))
```

**What this does:** Each session is identified by a (subject, date, probe(s)) tuple parsed from the MATLAB loader file. Sessions are processed independently in `build_dataset`, producing one entry per session in `neural`/`input`/`output` lists.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:208):
> "Align each spike to go cue, bin at 5 ms from `-2.5` to `+2.5` s, ... arrange as `(neurons, time)` per trial"

**Code** (convert_data.py:856-866, 881-896):
```python
n_trials = keep_trials.size
n_neurons = len(selected_neurons)
neural_trials = [np.zeros((n_neurons, time_centers.size), dtype=np.float32) for _ in range(n_trials)]
...
for out_idx, selected in enumerate(selected_neurons):
    probe = probes[selected.probe_num - 1]
    rates = binned_neuron_trials(probe, selected.neuron_index, align_times, keep_trials, time_edges)
    ...
    for tr in range(n_trials):
        neural_trials[tr][out_idx, :] = rates[:, tr]
...
for tr in range(n_trials):
    input_trials.append(time_centers[None, :].astype(np.float32))
    output_trials.append(np.vstack([...]))
```

**What this does:** Trials are derived from `obj.bp` per-trial fields (with `keep_trials` indexing); per-trial neural matrices are built by binning spikes whose `obj.clu.trial` index matches kept trials, then per-trial input/output arrays are appended.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:222-223):
> "Trial inclusion: Use only control/non-stimulation trials with valid behavioral labels. Exclude `stim.enable`, `early`, and `no` trials to match the reference analyses..."
> Plus late-trial neural-coverage trim (CONVERSION_NOTES.md:368-369): "`JEB24_2023-10-23` and `JEB24_2023-11-03` contained behavior-valid trials after the last trial with neural spikes; those late trials were excluded..."

**Code** (convert_data.py:570-576, 818-828):
```python
def build_trial_mask(obj: dict) -> np.ndarray:
    bp = obj["bp"]
    stim_enable = to_vector(bp["stim"]["enable"], float).astype(bool)
    early = to_vector(bp["early"], float).astype(bool)
    no = to_vector(bp["no"], float).astype(bool)
    valid = (~stim_enable) & (~early) & (~no)
    return valid
...
max_trial_with_spikes = max_supported_trial(selected_neurons, probes)
if max_trial_with_spikes > 0:
    neural_coverage_mask = (np.arange(trial_mask.size, dtype=np.int32) + 1) <= max_trial_with_spikes
    refined_trial_mask = trial_mask & neural_coverage_mask
```

**What this does:** Trials are excluded if they have stim enabled, are early-lick, or are no-response; additionally, behavior-valid trials beyond the last trial with neural spikes are dropped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:208):
> "`obj.clu{probe}.trialtm`, `obj.clu{probe}.trial`, `obj.bp.ev.goCue` -> `neural` ..."

**Code** (convert_data.py:611-619, 805-807):
```python
def binned_neuron_trials(...):
    trials = to_vector(probe["trial"][neuron_index], int)
    trialtm = to_vector(probe["trialtm"][neuron_index], float)
    ...
    aligned = trialtm[mask] - align_times[trials[mask] - 1]
...
obj = read_mat(spec.data_path)["obj"]
probes = normalize_probe_container(obj.get("clu"))
align_times = to_vector(obj["bp"]["ev"]["goCue"], float)
```

**What this does:** `neural` is derived from per-cluster spike data `obj.clu[probe].trial` and `obj.clu[probe].trialtm`, aligned to `obj.bp.ev.goCue`. Cluster `quality` and `obj.ex.probe.loc` are also used for selection/labeling.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:225-226):
> "Temporal representation: Use go-cue alignment and a common 5 ms bin width over `[-2.5 s, +2.5 s)`. ... preserving the baseline window used in the methods and the code."

**Code** (convert_data.py:604-626):
```python
def binned_neuron_trials(probe, neuron_index, align_times, keep_trials_0based, edges):
    trials = to_vector(probe["trial"][neuron_index], int)
    trialtm = to_vector(probe["trialtm"][neuron_index], float)
    trial_to_keep = np.full(align_times.size + 1, -1, dtype=np.int32)
    trial_to_keep[keep_trials_0based + 1] = np.arange(keep_trials_0based.size, dtype=np.int32)
    keep_index = trial_to_keep[trials]
    mask = keep_index >= 0
    keep_index = keep_index[mask]
    aligned = trialtm[mask] - align_times[trials[mask] - 1]
    bin_index = np.floor((aligned - TMIN) / DT).astype(np.int64)
    valid = (bin_index >= 0) & (bin_index < edges.size - 1)
    counts = np.zeros((edges.size - 1, keep_trials_0based.size), dtype=np.float32)
    np.add.at(counts, (bin_index[valid], keep_index[valid]), 1.0)
    rates = counts / DT
    return causal_gaussian_smooth(rates, SMOOTH, BCTYPE)
```

**What this does:** Spikes are aligned to go-cue, binned into 5 ms bins on `[-2.5, 2.5)`, divided by bin width to get firing rate (Hz), then smoothed with a causal Gaussian kernel of width 15 bins with reflect boundary handling.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:224):
> "Neural curation: Apply the released-code quality filter (`all` except garbage/noisy-like labels), then remove units with firing rate `<= 1 Hz`, and exclude sessions with fewer than 10 remaining units."

**Code** (convert_data.py:288-291, 645-662, 835-837):
```python
def quality_keep_mask(qualities: Sequence[str]) -> np.ndarray:
    cleaned = [normalize_string(q).lower() for q in qualities]
    bad = {"garbage", "gabrga", "noisy", "real?"}
    return np.array([q not in bad for q in cleaned], dtype=bool)
...
qualities = [normalize_string(q) for q in probe["quality"]]
quality_mask = quality_keep_mask(qualities)
...
for neuron_index in np.flatnonzero(quality_mask):
    mean_fr = neuron_mean_fr(probe, int(neuron_index), align_times, trial_mask)
    if mean_fr > LOW_FR:
        kept_indices.append(int(neuron_index))
...
if len(selected_neurons) < MIN_UNITS_PER_SESSION:
    log(f"Skipping {spec.session_id}: only {len(selected_neurons)} units after filtering")
    return None
```

**What this does:** Neurons whose `quality` is in {garbage, gabrga, noisy, real?} are dropped, then mean firing rate is computed over kept trials and units with mean FR <= 1 Hz removed; sessions with fewer than 10 surviving units are skipped entirely.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:225):
> "Use go-cue alignment and a common 5 ms bin width over `[-2.5 s, +2.5 s)`."

**Code** (convert_data.py:24-28, 216-221, 619-626):
```python
DT = 0.005
TMIN = -2.5
TMAX = 2.5
SMOOTH = 15
BCTYPE = "reflect"
...
def make_time_edges() -> np.ndarray:
    return np.arange(TMIN, TMAX + DT * 0.5, DT, dtype=np.float64)

def make_time_centers(edges: np.ndarray) -> np.ndarray:
    return edges[:-1] + DT / 2.0
...
bin_index = np.floor((aligned - TMIN) / DT).astype(np.int64)
...
counts = np.zeros((edges.size - 1, keep_trials_0based.size), dtype=np.float32)
np.add.at(counts, (bin_index[valid], keep_index[valid]), 1.0)
rates = counts / DT
return causal_gaussian_smooth(rates, SMOOTH, BCTYPE)
```

**What this does:** A regular grid of 5 ms bin edges from -2.5 to 2.5 s (1000 bins) is built; spike-aligned times are floored into bin indices, counts are summed, divided by DT to firing rate, then convolved with a causal Gaussian (width 15, reflect boundary).

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:226):
> "go-cue alignment ... matching the main neural alignment used in the code and paper."

**Code** (convert_data.py:807, 619):
```python
align_times = to_vector(obj["bp"]["ev"]["goCue"], float)
...
aligned = trialtm[mask] - align_times[trials[mask] - 1]
```
Metadata (convert_data.py:1033):
```python
"temporal_alignment_event": "Auditory go cue onset",
```

**What this does:** Per-trial go cue times come from `obj.bp.ev.goCue`; each spike's `trialtm` is subtracted by the trial's go-cue time so t=0 = go cue onset.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_go_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:209 — `| Common aligned time axis | `input[0]` | Continuous time-from-go-cue series, same for every trial, shape `(1, time)` | `getSeq` / paper decoding methods | Input name: `time_from_go_cue`. |`
> CONVERSION_NOTES.md:360 — "`time_from_go_cue` range | `[-2.5, 2.5]` implied by chosen decoding window | `tmin=-2.5`, `tmax=2.5` in reference scripts | Raw event times support this range | `[-2.4975, 2.4975]`"

**Code** (convert_data.py:23-27, 216-221, 807, 1008):
```python
DT = 0.005
TMIN = -2.5
TMAX = 2.5
SMOOTH = 15
BCTYPE = "reflect"
...
def make_time_edges() -> np.ndarray:
    return np.arange(TMIN, TMAX + DT * 0.5, DT, dtype=np.float64)

def make_time_centers(edges: np.ndarray) -> np.ndarray:
    return edges[:-1] + DT / 2.0
...
    align_times = to_vector(obj["bp"]["ev"]["goCue"], float)
...
        "input_names": ["time_from_go_cue"],
```

**What this does:** The trial produces one input, `time_from_go_cue`. Its numeric values come from the fixed window constants `TMIN`/`TMAX`/`DT` via `make_time_edges`/`make_time_centers`, not from a raw per-trial array; the raw field that defines the zero point is `obj.bp.ev.goCue`, used as `align_times` when binning spikes.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_go_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:291 — `| `time_from_go_cue` range | [-2.4975, 2.4975] |`
> CONVERSION_NOTES.md:380 — "Input: independently rebuilt the 1000-bin time axis `(-2.4975 ... 2.4975)` and matched `input[0]` for the same session/trial (`np.allclose=True`, max abs diff `3.58e-07`)."

**Code** (convert_data.py:216-221, 808-809, 881-884):
```python
def make_time_edges() -> np.ndarray:
    return np.arange(TMIN, TMAX + DT * 0.5, DT, dtype=np.float64)

def make_time_centers(edges: np.ndarray) -> np.ndarray:
    return edges[:-1] + DT / 2.0
...
    time_edges = make_time_edges()
    time_centers = make_time_centers(time_edges)
...
    input_trials: List[np.ndarray] = []
    output_trials: List[np.ndarray] = []
    for tr in range(n_trials):
        input_trials.append(time_centers[None, :].astype(np.float32))
```

**What this does:** Edges are `np.arange(-2.5, 2.5 + DT/2, 0.005)` and centers are `edges[:-1] + DT/2`, yielding 1000 values spanning -2.4975 to 2.4975 s. The center vector is reshaped to `(1, n_timepoints)` and cast to float32, and the same array is appended for every kept trial in the session.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_go_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:386 — "Input construction: decoder input is the common aligned time axis, derived from the same bin centers as the neural data."
> CONVERSION_NOTES.md:237 — "[ ] Input check: verify `input[0]` exactly matches the converted time axis for every session/trial."

**Code** (convert_data.py:619-626, 857-862, 884, 1033-1035):
```python
    aligned = trialtm[mask] - align_times[trials[mask] - 1]
    bin_index = np.floor((aligned - TMIN) / DT).astype(np.int64)
    valid = (bin_index >= 0) & (bin_index < edges.size - 1)
    counts = np.zeros((edges.size - 1, keep_trials_0based.size), dtype=np.float32)
    np.add.at(counts, (bin_index[valid], keep_index[valid]), 1.0)
    rates = counts / DT
    return causal_gaussian_smooth(rates, SMOOTH, BCTYPE)
...
    neural_trials = [np.zeros((n_neurons, time_centers.size), dtype=np.float32) for _ in range(n_trials)]
        rates = binned_neuron_trials(probe, selected.neuron_index, align_times, keep_trials, time_edges)
...
        input_trials.append(time_centers[None, :].astype(np.float32))
...
            "temporal_alignment_event": "Auditory go cue onset",
            "off_start": TMIN,
            "off_end": TMAX,
```

**What this does:** Spikes are shifted by each trial's `goCue` time and binned into `time_edges`; the neural arrays are allocated with width `time_centers.size`, so the input row holds the center coordinate of each neural bin and matches column-for-column. Metadata lists the alignment event as "Auditory go cue onset" over -2.5 to 2.5 s.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *lick_direction* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:210):
> "`obj.bp.R` / `obj.bp.L` -> `output[0]` Per-trial categorical label: left=`0`, right=`1`"

**Code** (convert_data.py:868, 873):
```python
R = to_vector(bp["R"], float).astype(int)
...
lick_direction = R[keep_trials]
```

**What this does:** Lick direction equals `obj.bp.R` (1 = right lick) restricted to kept trials.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?

**Notes excerpt** (CONVERSION_NOTES.md:210, 1018):
> "Per-trial categorical label: left=`0`, right=`1`"

**Code** (convert_data.py:884-895, 1017-1019):
```python
output_trials.append(
    np.vstack([
        np.full(time_centers.size, lick_direction[tr], dtype=np.int64),
        ...
    ])
)
...
"output_values": [
    ["left", "right"],
```

**What this does:** Per-trial scalar value (0/1) is broadcast across the 1000-bin time axis as the first row of each trial's output matrix.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-a. What variables in the raw data is `output` *context* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:211):
> "`obj.bp.autowater` -> `output[1]` Per-trial categorical label remapped to WC=`0`, DR=`1`"

**Code** (convert_data.py:869, 874):
```python
autowater = to_vector(bp["autowater"], float).astype(int)
...
context = 1 - autowater[keep_trials]
```

**What this does:** Behavioral context comes from `obj.bp.autowater`, with polarity flipped via `1 - autowater`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *context*?

**Notes excerpt** (CONVERSION_NOTES.md:227):
> "Context encoding: Represent behavioral context as WC=`0`, DR=`1`, even though raw `autowater` uses the opposite polarity."

**Code** (convert_data.py:874, 1019):
```python
context = 1 - autowater[keep_trials]
...
["WC", "DR"],
```

**What this does:** Polarity inverted (`1 - autowater`) so WC=0, DR=1, then broadcast across time as row 1 of output.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:212):
> "`obj.bp.hit` / `obj.bp.miss` -> `output[2]` Per-trial categorical label: miss=`0`, hit=`1`"

**Code** (convert_data.py:870-871, 875):
```python
hit = to_vector(bp["hit"], float).astype(int)
miss = to_vector(bp["miss"], float).astype(int)
...
outcome = hit[keep_trials]
```

**What this does:** Outcome is derived from `obj.bp.hit` (1 = correct) on kept trials.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Code** (convert_data.py:875-879):
```python
outcome = hit[keep_trials]
if not np.all((outcome == 0) | (outcome == 1)):
    raise ValueError(f"{spec.session_id}: outcome contains values outside hit/miss after filtering")
if not np.all((hit[keep_trials] + miss[keep_trials]) == 1):
    raise ValueError(f"{spec.session_id}: hit/miss are not mutually exclusive on kept trials")
```

**What this does:** Asserts each kept trial is binary hit/miss (mutually exclusive); broadcast across time as row 2.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:213):
> "DLC trajectories for tongue-related features -> `output[3]` Reference kinematic interpolation and velocity computation, then aggregate to a single tongue-speed trace and bin by per-session median"

**Code** (convert_data.py:33-36, 840):
```python
TONGUE_FEATURES = {
    1: ["tongue", "left_tongue", "right_tongue"],
    2: ["top_tongue", "topleft_tongue", "bottom_tongue", "bottomleft_tongue"],
}
...
tongue_speed_all, tongue_feats = aggregate_speed(obj, TONGUE_FEATURES, time_centers, align_times, vidshift)
```

**What this does:** Tongue features from `obj.traj` views 1 and 2 (DLC trajectories) form the source.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?

**Code** (convert_data.py:415-437, 440-468, 562-567, 848, 852):
```python
def feature_velocity(xpos, ypos, feat_name):
    ...
    xv = np.gradient(tsinterp[:, 0]).astype(np.float32)
    yv = np.gradient(tsinterp[:, 1]).astype(np.float32)
    ...
    else:  # tongue
        xv = np.nan_to_num(xv, nan=0.0)
        yv = np.nan_to_num(yv, nan=0.0)

def aggregate_speed(...):
    ...
    speed = np.sqrt(np.square(xvel) + np.square(yvel))
    ...
    agg = np.divide(summed, np.maximum(count, 1), dtype=np.float32)
...
def discretize_trace(traces, threshold):
    flat = traces.reshape(-1)
    order = np.argsort(flat, kind="mergesort")
    out = np.zeros(flat.size, dtype=np.int64)
    out[order[flat.size // 2 :]] = 1
    return out.reshape(traces.shape)
...
tongue_thr = percentile_threshold(tongue_speed, 50.0)
tongue_bin = discretize_trace(tongue_speed, tongue_thr)
```

**What this does:** Per-feature x/y positions are interpolated to the aligned time axis, gradient -> velocity, magnitude per feature, then averaged across the tongue feature group; the resulting per-session matrix is binarized by an exact 50/50 split (sorted indices) instead of strict threshold.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 7-c. How is `output` *tongue_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:60-61):
> "DLC trajectories also use frame times corrected by a 0.5 s or computed video offset depending on loader/helper path. This is important for later consistency checks on temporal alignment."

**Code** (convert_data.py:302-310, 375, 388-404, 839-840):
```python
def compute_video_offset(obj: dict) -> float:
    try:
        bit_start = robust_mode(obj["bp"]["ev"]["bitStart"])
        vid_file_offset = robust_mode(obj["sglx"]["bitcode"]["bitstart"]) / float(obj["sglx"]["fs"])
        if np.isfinite(bit_start) and np.isfinite(vid_file_offset):
            return float(vid_file_offset - bit_start)
    except Exception:
        pass
    return 0.5
...
taxis = time_centers + ADVANCE_MOVEMENT
...
frame_times = get_frame_times(trial_view, ts.shape[0])
...
old_time = frame_times - vidshift - float(align_times[trial])
interp = interp1d(old_time, xy, axis=0, kind="linear",
                  bounds_error=False, fill_value=np.nan, assume_sorted=True)
xy_aligned = interp(taxis)
...
vidshift = compute_video_offset(obj)
tongue_speed_all, tongue_feats = aggregate_speed(obj, TONGUE_FEATURES, time_centers, align_times, vidshift)
```

**What this does:** Per-session `vidshift` is computed as `obj.sglx.bitcode.bitstart / obj.sglx.fs - obj.bp.ev.bitStart` (defaulting to 0.5 s on failure). For each trial, DLC frame times are shifted by `frame_times - vidshift - align_times[trial]` (where `align_times` is `obj.bp.ev.goCue`) and the x/y trajectories are linearly interpolated onto the neural `time_centers + ADVANCE_MOVEMENT` (1000 5-ms bins on `[-2.5, 2.5)`).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:214):
> "DLC trajectories for paw-related features -> `output[4]` ... Paws are tracked in the bottom view only."

**Code** (convert_data.py:37-39, 841):
```python
PAW_FEATURES = {
    2: ["top_paw", "bottom_paw"],
}
...
paw_speed_all, paw_feats = aggregate_speed(obj, PAW_FEATURES, time_centers, align_times, vidshift)
```

**What this does:** Paw features from `obj.traj[1]` (bottom-view DLC).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?

**Code** (convert_data.py:415-437, 849, 853):
```python
def feature_velocity(xpos, ypos, feat_name):
    ...
    if "tongue" not in feat_name:  # paw branch
        xv = xv - base[0]
        yv = yv - base[1]
        xv = fill_nearest_1d(xv)
        yv = fill_nearest_1d(yv)
...
paw_thr = percentile_threshold(paw_speed, 50.0)
paw_bin = discretize_trace(paw_speed, paw_thr)
```

**What this does:** Same interpolation/velocity pipeline as tongue but with per-trial baseline subtraction (median diff) and NaN nearest-fill. Aggregated across paw features then binarized via 50/50 split.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *paw_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:60-61):
> "DLC trajectories also use frame times corrected by a 0.5 s or computed video offset depending on loader/helper path. This is important for later consistency checks on temporal alignment."

**Code** (convert_data.py:375, 388-410, 841):
```python
taxis = time_centers + ADVANCE_MOVEMENT

for trial in range(n_trials):
    ...
    frame_times = get_frame_times(trial_view, ts.shape[0])
    if not np.isfinite(frame_times).any():
        continue

    xy = ts[:, :2, feat_index]
    old_time = frame_times - vidshift - float(align_times[trial])

    interp = interp1d(old_time, xy, axis=0, kind="linear",
                      bounds_error=False, fill_value=np.nan, assume_sorted=True)
    xy_aligned = interp(taxis)
    xpos[:, trial] = xy_aligned[:, 0]
    ypos[:, trial] = xy_aligned[:, 1]

    if "tongue" not in feat_name:
        xpos[:, trial] = fill_nearest_1d(xpos[:, trial])
        ypos[:, trial] = fill_nearest_1d(ypos[:, trial])
...
paw_speed_all, paw_feats = aggregate_speed(obj, PAW_FEATURES, time_centers, align_times, vidshift)
```

**What this does:** Paw features go through the same `aligned_position` path as tongue: per-trial DLC `frameTimes` are corrected by the session-level `vidshift` (`bitcode.bitstart/fs - bp.ev.bitStart`) and the trial's `goCue`, then linearly interpolated onto the neural `time_centers + ADVANCE_MOVEMENT` axis. Non-tongue (paw) channels additionally receive nearest-neighbor NaN fill on the aligned x/y traces.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:215):
> "Motion energy traces (`motionEnergy_*.mat` or embedded `obj.me`) -> `output[5]` Align/interpolate to neural time axis using reference logic, then bin by per-session median"

**Code** (convert_data.py:489-510):
```python
def load_motion_energy_raw(obj, spec):
    if spec.motion_energy_path.exists():
        raw_me = read_mat(spec.motion_energy_path).get("me")
        ...
    if "me" in obj:
        raw_me = obj["me"]
        ...
```

**What this does:** Source is the external `motionEnergy_<subject>_<date>.mat` file when present, otherwise the embedded `obj.me`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *motion_energy*?

**Code** (convert_data.py:513-551, 850, 854):
```python
def aligned_motion_energy(obj, raw_me, time_centers, align_times, vidshift):
    ...
    for trial in range(min(len(me_data), n_trials)):
        me_trial = np.asarray(me_data[trial], dtype=np.float32).reshape(-1)
        ...
        old_time = frame_times - vidshift - float(align_times[trial])
        interp = interp1d(old_time, me_trial, kind="linear", bounds_error=False, fill_value=np.nan, assume_sorted=True)
        aligned[:, trial] = interp(taxis).astype(np.float32)
        aligned[:, trial] = fill_nearest_1d(aligned[:, trial])
    return np.nan_to_num(aligned, ...)
...
me_thr = percentile_threshold(motion_energy, 50.0)
me_bin = discretize_trace(motion_energy, me_thr)
```

**What this does:** Per-trial ME trace is interpolated onto the go-cue-aligned 5 ms axis using video frame times (corrected by `vidshift`), edge NaNs filled, then binarized by 50/50 sort split.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-c. How is `output` *motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:60):
> "Motion energy alignment is explicit: `interp1(frameTimes - video_offset - align_event_time, me.data{trial}, obj.time + advance_movement)`, then edge NaNs are filled with nearest values."

**Code** (convert_data.py:526-551, 842):
```python
view = obj["traj"][0]
taxis = time_centers + ADVANCE_MOVEMENT

for trial in range(min(len(me_data), n_trials)):
    me_trial = np.asarray(me_data[trial], dtype=np.float32).reshape(-1)
    trial_view = get_view_trial(view, trial)
    ts = np.asarray(trial_view["ts"])
    frame_times = get_frame_times(trial_view, ts.shape[0])
    if frame_times.size != me_trial.size:
        frame_times = (np.arange(me_trial.size, dtype=np.float32) + 1.0) / 400.0
        old_time = frame_times - 0.5 - float(align_times[trial])
    else:
        old_time = frame_times - vidshift - float(align_times[trial])

    interp = interp1d(old_time, me_trial, kind="linear",
                      bounds_error=False, fill_value=np.nan, assume_sorted=True)
    aligned[:, trial] = interp(taxis).astype(np.float32)
    aligned[:, trial] = fill_nearest_1d(aligned[:, trial])
...
motion_energy_all = aligned_motion_energy(obj, load_motion_energy_raw(obj, spec), time_centers, align_times, vidshift)
```

**What this does:** Per-trial motion-energy frame times are taken from `obj.traj[0]` (side-cam) `frameTimes`, shifted by `vidshift` (computed from `sglx.bitcode.bitstart/fs - bp.ev.bitStart`) and the trial's `goCue`, then linearly interpolated onto the neural `time_centers + ADVANCE_MOVEMENT` axis (1000 5-ms bins on `[-2.5, 2.5)`); when frame-times are missing, a synthetic 400 Hz axis with a fixed 0.5 s offset is used. Edge NaNs are then filled with the nearest valid value.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:367-370, 397-400):
> "`JEB15` motion-energy files required recursive unwrapping of nested `me.data` structs."
> "`JEB24_2023-10-23` and `JEB24_2023-11-03` contained behavior-valid trials after the last trial with neural spikes; those late trials were excluded..."
> "Spurious `np.nanmean` runtime warning during kinematic aggregation: replaced with an explicit finite-value average..."

**Code** (convert_data.py:266-281, 471-486, 818-834):
```python
def fill_nearest_1d(x):
    ...
    valid = np.flatnonzero(~mask)
    ...
    nearest = np.where(choose_left, left, right)
    x[mask] = x[nearest[mask]]
    return x
...
def unwrap_embedded_motion_energy(raw_me):
    data = raw_me
    seen = set()
    while isinstance(data, dict) and "data" in data and id(data) not in seen:
        seen.add(id(data))
        ...
...
max_trial_with_spikes = max_supported_trial(selected_neurons, probes)
if max_trial_with_spikes > 0:
    neural_coverage_mask = (np.arange(trial_mask.size, dtype=np.int32) + 1) <= max_trial_with_spikes
    refined_trial_mask = trial_mask & neural_coverage_mask
```

**What this does:** Missing kinematic samples filled by nearest valid value (tongue: zeroed instead); nested `me` structs recursively unwrapped; trials beyond last neural-spike trial dropped; sessions with <2 trials or <10 units skipped; finite-value averaging replaces nanmean to suppress warnings.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:267-269):
> "Code inefficiencies identified: Session loading from large MATLAB files is the main cost. Kinematic interpolation and per-neuron spike binning dominate runtime."

**Code** (convert_data.py:805, 862, 395-403):
```python
obj = read_mat(spec.data_path)["obj"]
...
rates = binned_neuron_trials(probe, selected.neuron_index, align_times, keep_trials, time_edges)
...
interp = interp1d(old_time, xy, axis=0, kind="linear", bounds_error=False, fill_value=np.nan, assume_sorted=True)
xy_aligned = interp(taxis)
```

**What this does:** Largest runtime contributors are MATLAB v7.3 file reads, scipy `interp1d` per (trial, feature), and per-neuron spike binning. Reported full runtime ~480 s for 44 sessions.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-b. What loops in the code could have been vectorized to improve efficiency?

**Code** (convert_data.py:619-624, 257-258):
```python
bin_index = np.floor((aligned - TMIN) / DT).astype(np.int64)
valid = (bin_index >= 0) & (bin_index < edges.size - 1)
counts = np.zeros((edges.size - 1, keep_trials_0based.size), dtype=np.float32)
np.add.at(counts, (bin_index[valid], keep_index[valid]), 1.0)
...
for col in range(x_filt.shape[1]):
    out[:, col] = np.convolve(x_filt[:, col], kern, mode="same")
```

**What this does:** Spike binning is vectorized with `np.add.at`; smoothing convolves each column in a Python loop; per-neuron loop in `binned_neuron_trials` is called once per kept neuron; per-trial `interp1d` calls in kinematics are inside Python loops.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md:271-275):
> "Avoided full-session temporary 3D neural arrays before low-FR filtering by using a two-pass approach: pass 1: estimate firing rate and select neurons; pass 2: build only kept neurons' trial matrices"

**Code** (convert_data.py:589-602, 833):
```python
def neuron_mean_fr(probe, neuron_index, align_times, trial_mask):
    trials = to_vector(probe["trial"][neuron_index], int)
    trialtm = to_vector(probe["trialtm"][neuron_index], float)
    n_spikes = count_window_spikes(trials, trialtm, align_times, trial_mask)
    ...
    return n_spikes / (n_trials * (TMAX - TMIN))
...
selected_neurons, probe_summaries = select_neurons(obj, spec, trial_mask)  # called again after refining trial mask
```

**What this does:** Two-pass design (FR estimate then bin only kept neurons). However, `select_neurons` and `binned_neuron_trials` both re-extract `trial`/`trialtm` per neuron; if the late-trial trim fires, `select_neurons` is invoked a second time, recomputing FR per neuron.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md:275-276):
> "Aggregated output traces only for the feature groups needed by the decoder task (tongue, paw, motion energy) instead of reconstructing the full video feature matrix."

**Code** (convert_data.py:840-846):
```python
tongue_speed_all, tongue_feats = aggregate_speed(obj, TONGUE_FEATURES, time_centers, align_times, vidshift)
paw_speed_all, paw_feats = aggregate_speed(obj, PAW_FEATURES, time_centers, align_times, vidshift)
motion_energy_all = aligned_motion_energy(obj, load_motion_energy_raw(obj, spec), time_centers, align_times, vidshift)

tongue_speed = tongue_speed_all[:, keep_trials]
paw_speed = paw_speed_all[:, keep_trials]
motion_energy = motion_energy_all[:, keep_trials]
```

**What this does:** Movement traces are computed for all trials of the session, then sliced by `keep_trials` after the fact (work spent on excluded trials), but only the needed feature groups are processed.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md:271-273, 348):
> "Avoided full-session temporary 3D neural arrays before low-FR filtering by using a two-pass approach"
> "`converted_data.pkl`: `3.2G`"

**Code** (convert_data.py:856-865):
```python
n_trials = keep_trials.size
n_neurons = len(selected_neurons)
neural_trials = [np.zeros((n_neurons, time_centers.size), dtype=np.float32) for _ in range(n_trials)]
...
for out_idx, selected in enumerate(selected_neurons):
    probe = probes[selected.probe_num - 1]
    rates = binned_neuron_trials(probe, selected.neuron_index, align_times, keep_trials, time_edges)
    ...
    for tr in range(n_trials):
        neural_trials[tr][out_idx, :] = rates[:, tr]
```

**What this does:** Per-session storage is a list of (n_neurons, 1000) float32 trial matrices; intermediate `rates` (1000, n_trials) is built per neuron. Output pickle ~3.2 GB. Two-pass design avoids holding full 3D neural arrays for rejected neurons.

**Rating:** match

**Note:** _(no note)_---

---
