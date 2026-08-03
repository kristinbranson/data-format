# zhang2025 — codex / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/zhang2025/codex/2026-03-24__17-20-29_trial2/verifier/snapshot/`

Outputs identified (K=4): choice, prior_probability_of_left, wheel_speed_bin, whisker_motion_energy_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Start from the frozen 459-session / 699-insertion BWM release, not from all locally visible session folders." (CONVERSION_NOTES.md:231)
> "Implemented `/app/convert_data.py` as a two-pass converter: pass 1 loads trials + wheel + whisker, applies the reference trial mask plus behavior-coverage mask, and computes global dynamic-output tertile thresholds; pass 2 reloads good units (`label >= 1`), bins stimulus-aligned spikes into 20 ms bins..." (CONVERSION_NOTES.md:285-287)

**Code** (convert_data.py:114-131, 695-712):
```python
def load_release_sessions() -> list[SessionSpec]:
    bwm = pd.read_csv(RELEASE_CSV, index_col=0)
    grouped = bwm.groupby("eid", sort=False)
    sessions: list[SessionSpec] = []
    for eid, df in grouped:
        row = df.iloc[0]
        probe_names = tuple(df["probe_name"].tolist())
        sessions.append(SessionSpec(eid=eid, subject=str(row["subject"]),
            lab=str(row["lab"]), date=str(row["date"]),
            session_number=int(row["session_number"]), probe_names=probe_names))
    return sessions
# main:
sessions = load_release_sessions()
target_sessions = sessions
with ThreadPoolExecutor(max_workers=n_workers) as pool:
    results_iter = pool.map(build_session_behavior_safe, target_sessions)
```

**What this does:** Reads the frozen BWM release CSV (`bwm_release.csv`) to enumerate 459 session specs (eid, subject, lab, date, session number, probe names) and dispatches each spec to `build_session_behavior_safe` via a thread pool. Direct ALF file loads (not ONE/SessionLoader) are used inside.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "subject IDs from frozen release metadata | `subjects`, `subject_idx` | unique sorted subject list and per-session index" (CONVERSION_NOTES.md:252)

**Code** (convert_data.py:561-563, 631):
```python
subject_names = sorted({ps.spec.subject for ps in prepared_sessions})
subject_to_idx = {subject: i for i, subject in enumerate(subject_names)}
subject_idx_list: list[int] = []
...
"subject_idx": np.array(subject_idx_list, dtype=np.int64),
```

**What this does:** Subject identity is taken from the `subject` column of `bwm_release.csv` per session. Unique subjects are sorted alphabetically into `subjects`, and each session is assigned a `subject_idx` mapping into that list.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "sessions are organized as: `data/one_cache/<lab>/Subjects/<subject>/<date>/<number>/`" (CONVERSION_NOTES.md:90)

**Code** (convert_data.py:59-70, 116-118):
```python
@dataclass(frozen=True)
class SessionSpec:
    eid: str
    subject: str
    lab: str
    date: str
    session_number: int
    probe_names: tuple[str, ...]
    @property
    def session_path(self) -> Path:
        return DATA_ROOT / self.lab / "Subjects" / self.subject / self.date / f"{self.session_number:03d}"
# load_release_sessions groups bwm CSV rows by 'eid'
grouped = bwm.groupby("eid", sort=False)
```

**What this does:** Sessions are defined by unique `eid` rows in `bwm_release.csv`; each maps to an ALF folder via `lab/Subjects/subject/date/session_number`. Each prepared session contributes a separate list entry in `neural`/`input`/`output`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "common trial window: `[-0.5, 1.5]` s; bin size: `20 ms`" (README.md:9-10)
> "Alignment: stimulus onset (`stimOn_times`)" (README.md:8)

**Code** (convert_data.py:35-39, 269, 398-402):
```python
ALIGN_EVENT = "stimOn_times"
TIME_WINDOW = (-0.5, 1.5)
BINSIZE = 0.02
NBINS = int(round((TIME_WINDOW[1] - TIME_WINDOW[0]) / BINSIZE))
# build_session_behavior:
align_times = trials[ALIGN_EVENT].to_numpy(dtype=np.float64)
# bin_spikes_by_trial:
interval_begs = align_times + time_window[0]
interval_ends = align_times + time_window[1]
n_bins = int(np.ceil((time_window[1] - time_window[0]) / binsize))
```

**What this does:** Each trial corresponds to a row of the trials parquet table; trial windows are constructed by adding `[-0.5, 1.5]` s to each `stimOn_times` value, producing 100-bin trial segments.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "required non-null `stimOn_times`, `choice`, `feedback_times`, `probabilityLeft`, `firstMovement_times`, `feedbackType`; reaction time `0.08` to `2.0` s; no-choice trials removed; maximum trial length `10.0` s" (README.md:78-81)

**Code** (convert_data.py:139-153, 273-275):
```python
def compute_trial_mask(trials: pd.DataFrame) -> np.ndarray:
    rt = trials["firstMovement_times"] - trials["stimOn_times"]
    mask = (
        ~trials["stimOn_times"].isnull()
        & ~trials["choice"].isnull()
        & ~trials["feedback_times"].isnull()
        & ~trials["probabilityLeft"].isnull()
        & ~trials["firstMovement_times"].isnull()
        & ~trials["feedbackType"].isnull()
        & (rt >= 0.08) & (rt <= 2.0)
        & ((trials["feedback_times"] - trials["goCue_times"]) <= 10.0)
        & (trials["choice"] != 0))
    return mask.to_numpy(dtype=bool)
# in build_session_behavior:
keep_mask = trial_mask & wheel_mask & whisker_mask
if keep_mask.sum() < 2: return None
```

**What this does:** Applies the reference paper trial mask (non-null key events, RT in [0.08, 2.0] s, trial length <= 10 s, no-choice excluded), then ANDs with per-trial wheel and whisker interpolation coverage masks. Sessions with fewer than 2 valid trials are dropped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`spikes.times`, `spikes.clusters`, `clusters.metrics.label` from all probes in a frozen-release session | `neural` | merge probes by session after filtering to clusters with `label >= 1`..." (CONVERSION_NOTES.md:245)

**Code** (convert_data.py:333-348):
```python
def load_good_spikes_and_regions(spec, brain_regions):
    for probe_name in spec.probe_names:
        probe_dir = spec.session_path / "alf" / probe_name / "pykilosort"
        metrics_path = resolve_latest(probe_dir, "**/clusters.metrics.pqt")
        clusters_channels_path = resolve_latest(probe_dir, "**/clusters.channels.npy")
        channels_region_ids_path = resolve_latest(probe_dir, "**/channels.brainLocationIds_ccf_2017.npy")
        spikes_times_path = resolve_latest(probe_dir, "**/spikes.times.npy")
        spikes_clusters_path = resolve_latest(probe_dir, "**/spikes.clusters.npy")
        metrics = pd.read_parquet(metrics_path, columns=["label"])
        good_rows = metrics["label"].to_numpy(copy=False) >= 1
```

**What this does:** Neural data derives from per-probe `spikes.times.npy`, `spikes.clusters.npy`, with cluster-level filtering via `clusters.metrics.pqt` (`label`) and brain-region tagging via `clusters.channels.npy` + `channels.brainLocationIds_ccf_2017.npy`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Vectorized per-trial spike binning via `np.searchsorted` + flattened `np.bincount`. Low-precision storage for neural arrays (`float16`)..." (CONVERSION_NOTES.md:300-301)

**Code** (convert_data.py:381-387, 405-422):
```python
merged_spike_times = np.concatenate(spike_times_all)
merged_spike_clusters = np.concatenate(spike_clusters_all)
order = np.argsort(merged_spike_times)
merged_spike_times = merged_spike_times[order]
merged_spike_clusters = merged_spike_clusters[order]
# bin_spikes_by_trial inner loop:
for i in range(len(align_times)):
    i0 = start_idx[i]; i1 = end_idx[i]
    rel = spike_times[i0:i1] - interval_begs[i]
    bin_idx = np.floor(rel / binsize).astype(np.int64)
    valid = (bin_idx >= 0) & (bin_idx < n_bins)
    flat = spike_clusters[i0:i1][valid] * n_bins + bin_idx[valid]
    counts = np.bincount(flat, minlength=n_units * n_bins).reshape(n_units, n_bins)
    out.append(counts.astype(np.float16))
```

**What this does:** Spikes are merged across probes (concatenate + argsort by time, with cluster IDs offset between probes). Per-trial spike counts are computed by `searchsorted` window + `floor((t-tbeg)/binsize)` + `bincount` on a flat `(cluster*nbins + bin)` index. Output is `(n_units, 100)` per trial in float16.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neurons are filtered to `clusters.metrics.label >= 1`, reproducing the paper's 75,708 well-isolated-unit count..." (README.md:76)

**Code** (convert_data.py:171-178, 347-364):
```python
def count_good_units(spec):
    total = 0
    for probe_name in spec.probe_names:
        ...
        metrics = pd.read_parquet(metrics_path, columns=["label"])
        total += int((metrics["label"].to_numpy() >= 1).sum())
    return total
# load_good_spikes_and_regions:
good_rows = metrics["label"].to_numpy(copy=False) >= 1
spike_mask = good_rows[spikes_clusters]
remap = np.full(n_clusters, -1, dtype=np.int32)
remap[good_rows] = np.arange(int(good_rows.sum()), dtype=np.int32)
good_spike_times = np.asarray(spikes_times[spike_mask], dtype=np.float64)
```

**What this does:** Clusters whose IBL-bundled `clusters.metrics.label >= 1` are kept ("well-isolated"); spikes from other clusters are dropped via a boolean mask indexed by cluster ID, then cluster IDs are remapped to a contiguous range.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Bin size: `20 ms`; Trial shape: neural: `(n_neurons, 100)`" (README.md:10-13)

**Code** (convert_data.py:35-39, 412-421):
```python
TIME_WINDOW = (-0.5, 1.5)
BINSIZE = 0.02
NBINS = int(round((TIME_WINDOW[1] - TIME_WINDOW[0]) / BINSIZE))
# bin_spikes_by_trial:
rel = spike_times[i0:i1] - interval_begs[i]
bin_idx = np.floor(rel / binsize).astype(np.int64)
valid = (bin_idx >= 0) & (bin_idx < n_bins)
flat = spike_clusters[i0:i1][valid] * n_bins + bin_idx[valid]
counts = np.bincount(flat, minlength=n_units * n_bins).reshape(n_units, n_bins)
```

**What this does:** Spike counts are accumulated into 100 non-overlapping 20 ms bins covering `[-0.5, 1.5]` s relative to alignment. No smoothing or rate normalization is applied; values are raw spike counts cast to float16.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Alignment: stimulus onset (`stimOn_times`)" (README.md:8)

**Code** (convert_data.py:35, 452, 398-402):
```python
ALIGN_EVENT = "stimOn_times"
# build_session_payload:
kept_align_times = prepared.trials.loc[prepared.keep_mask, ALIGN_EVENT].to_numpy(dtype=np.float64)
# bin_spikes_by_trial:
interval_begs = align_times + time_window[0]
interval_ends = align_times + time_window[1]
start_idx = np.searchsorted(spike_times, interval_begs, side="left")
end_idx = np.searchsorted(spike_times, interval_ends, side="left")
```

**What this does:** Alignment uses each trial's `stimOn_times`; per-trial intervals are `[stimOn-0.5, stimOn+1.5]`, located by `np.searchsorted` on the merged sorted spike-time array.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_stimulus_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:246 — `| common trial grid relative to stimOn_times | input[0] = time_since_stimulus_onset_s | 100-length vector of relative times on the same grid as aligned behavior/neural bins; use a common vector for every trial | reference code uses time_window and binsize; behavior interpolation grid from get_behavior_per_interval | represent as time-varying continuous input |`

**Code** (convert_data.py:35-43):
```python
ALIGN_EVENT = "stimOn_times"
TIME_WINDOW = (-0.5, 1.5)
BINSIZE = 0.02
NBINS = int(round((TIME_WINDOW[1] - TIME_WINDOW[0]) / BINSIZE))
COMMON_RELATIVE_TIMES = np.linspace(TIME_WINDOW[0] + BINSIZE, TIME_WINDOW[1], NBINS, dtype=np.float32)

INPUT_NAMES = [
    "time_since_stimulus_onset_s",
    "trial_number_in_block",
]
```

**What this does:** The trial produces this input under the name `time_since_stimulus_onset_s` (`input[0]`). It is not taken from any raw data column; it is a module-level constant built from `TIME_WINDOW = (-0.5, 1.5)` and `BINSIZE = 0.02`, the same window and bin size used to align neural and behavioral data to the raw `stimOn_times` event.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_stimulus_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:260 — `Represent both inputs as 2D arrays of shape (2, 100): time_since_stimulus_onset_s varies over time; trial_number_in_block is repeated across time for each trial.`
> CONVERSION_NOTES.md:416 — `| time_since_stimulus_onset_s range | 20 ms bins over [-0.5, 1.5] s around stimulus onset | time_window=(-0.5, 1.5), binsize=0.02, 100 bins | derived from aligned-bin construction | [-0.48, 1.50] | Yes |`

**Code** (convert_data.py:39, 466-476):
```python
COMMON_RELATIVE_TIMES = np.linspace(TIME_WINDOW[0] + BINSIZE, TIME_WINDOW[1], NBINS, dtype=np.float32)
...
    session_input: list[np.ndarray] = []
    for trial_idx in range(len(neural_trials)):
        inp = np.vstack(
            [
                COMMON_RELATIVE_TIMES,
                np.full(NBINS, prepared.trial_number_in_block[trial_idx], dtype=np.float32),
            ]
        ).astype(np.float32)
        ...
        session_input.append(inp)
```

**What this does:** `np.linspace(-0.5 + 0.02, 1.5, 100)` yields the right edge of each 20 ms bin, i.e. `[-0.48, ..., 1.50]` s, computed once at module load. The same vector is stacked as row 0 of every trial's `(2, 100)` input array, identical across trials and sessions.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_stimulus_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:246 — `100-length vector of relative times on the same grid as aligned behavior/neural bins; use a common vector for every trial`
> CONVERSION_NOTES.md:468 — `conversion constructs decoder-specific inputs (time_since_stimulus_onset_s, trial_number_in_block) and outputs (choice, prior_probability_of_left, wheel_speed_bin, whisker_motion_energy_bin) on that same grid`

**Code** (convert_data.py:390-413, 452-459):
```python
def bin_spikes_by_trial(spike_times, spike_clusters, align_times, n_units,
                        binsize=BINSIZE, time_window=TIME_WINDOW):
    interval_begs = align_times + time_window[0]
    interval_ends = align_times + time_window[1]
    n_bins = int(np.ceil((time_window[1] - time_window[0]) / binsize))
    ...
        rel = spike_times[i0:i1] - interval_begs[i]
        bin_idx = np.floor(rel / binsize).astype(np.int64)
...
kept_align_times = prepared.trials.loc[prepared.keep_mask, ALIGN_EVENT].to_numpy(dtype=np.float64)
neural_trials = bin_spikes_by_trial(
    spike_times=spike_times,
    spike_clusters=spike_clusters,
    align_times=kept_align_times,
    n_units=cluster_regions.shape[0],
)
```

**What this does:** Spikes are binned into 100 bins of 20 ms spanning `stimOn_times + [-0.5, 1.5]` s, and the time input holds the right edges of those same bins. Column *i* of the time row therefore corresponds to column *i* of the neural array by shared construction (`NBINS`), with no separate alignment or interpolation step.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *trial_number_in_block* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:247 — `| probabilityLeft block structure in raw trial table | input[1] = trial_number_in_block | compute block index from original unfiltered session trial sequence; reset to 1 whenever probabilityLeft changes; then repeat the scalar across all 100 bins for each kept trial | custom logic consistent with raw trial table semantics | unbiased 0.5 block counts as its own block |`

**Code** (convert_data.py:41-43, 261, 284):
```python
INPUT_NAMES = [
    "time_since_stimulus_onset_s",
    "trial_number_in_block",
]
...
    trial_number_in_block = compute_trial_number_in_block(trials["probabilityLeft"].to_numpy())
...
        trial_number_in_block=trial_number_in_block[keep_mask],
```

**What this does:** The trial produces this input as `input[1]`, named `trial_number_in_block`. It is derived from the `probabilityLeft` column of the raw trials table read over the full unfiltered trial sequence, subset afterwards by the kept-trial mask.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *trial_number_in_block*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:263 — `Compute trial_number_in_block on the original trial table before filtering: This preserves the actual behavioural position within a block rather than renumbering after trial exclusion.`
> CONVERSION_NOTES.md:417 — `| trial_number_in_block range | first block 90 trials; later biased blocks 20-100 trials | block counter derived from probabilityLeft changes | [1, 99] over included sessions | [1, 99] | Yes |`

**Code** (convert_data.py:156-173, 466-476):
```python
def compute_trial_number_in_block(prob_left: np.ndarray) -> np.ndarray:
    out = np.zeros(len(prob_left), dtype=np.int16)
    prev = None
    counter = 0
    for i, val in enumerate(prob_left):
        current = None if pd.isna(val) else float(val)
        if i == 0 or current != prev:
            counter = 1
        else:
            counter += 1
        out[i] = counter
        prev = current
    return out
...
        inp = np.vstack(
            [
                COMMON_RELATIVE_TIMES,
                np.full(NBINS, prepared.trial_number_in_block[trial_idx], dtype=np.float32),
            ]
        ).astype(np.float32)
```

**What this does:** A sequential counter over the unfiltered trial table starts at 1 and increments while `probabilityLeft` is unchanged, resetting to 1 at every change (NaN handled as `None`). The counter is computed before trial exclusion, then indexed by `keep_mask`, and each kept trial's scalar is broadcast across all 100 time bins as row 1 of the input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`choice` (`left=0`, `right=1`)" (README.md:71)
> "raw `choice` in trial table (`-1`, `1`) after filtering | `output[0]` = `choice`" (CONVERSION_NOTES.md:248)

**Code** (convert_data.py:285, 425-431):
```python
choice_raw=trials.loc[keep_mask, "choice"].to_numpy(),
...
def map_choice(raw_choice):
    mapped = np.empty(raw_choice.shape[0], dtype=np.int8)
    mapped[raw_choice == 1] = 0
    mapped[raw_choice == -1] = 1
    if not np.all(np.isin(raw_choice, [-1, 1])):
        raise ValueError("Unexpected choice values encountered after filtering.")
    return mapped
```

**What this does:** Derived from the `choice` column of the `_ibl_trials.table.pqt` trials table (after the trial mask drops no-choice rows).

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "map left `1 -> 0`, right `-1 -> 1`; repeat across all 100 bins for a common 2D output shape" (CONVERSION_NOTES.md:248)

**Code** (convert_data.py:425-431, 475-477):
```python
def map_choice(raw_choice):
    mapped = np.empty(raw_choice.shape[0], dtype=np.int8)
    mapped[raw_choice == 1] = 0
    mapped[raw_choice == -1] = 1
...
out = np.vstack([
    np.full(NBINS, choice[trial_idx], dtype=np.int8),
    ...
```

**What this does:** Raw `choice` (-1/1) is remapped to (1/0) for left=0, right=1, then broadcast as a constant across all 100 time bins of the output array.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *prior_probability_left* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "raw `probabilityLeft` in trial table (`0.2`, `0.5`, `0.8`) | `output[1]` = `prior_probability_of_left`" (CONVERSION_NOTES.md:249)

**Code** (convert_data.py:286, 434-442):
```python
prior_raw=trials.loc[keep_mask, "probabilityLeft"].to_numpy(),
...
def map_prior(raw_prior):
    out = np.empty(raw_prior.shape[0], dtype=np.int8)
    mapper = {0.2: 0, 0.5: 1, 0.8: 2}
    for i, val in enumerate(raw_prior):
        key = round(float(val), 1)
        if key not in mapper:
            raise ValueError(f"Unexpected probabilityLeft value {val}")
        out[i] = mapper[key]
    return out
```

**What this does:** Derived from the `probabilityLeft` column of the trials table.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *prior_probability_left*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "map `0.2 -> 0`, `0.5 -> 1`, `0.8 -> 2`; repeat across all 100 bins" (CONVERSION_NOTES.md:249)

**Code** (convert_data.py:434-442, 478):
```python
def map_prior(raw_prior):
    out = np.empty(raw_prior.shape[0], dtype=np.int8)
    mapper = {0.2: 0, 0.5: 1, 0.8: 2}
    for i, val in enumerate(raw_prior):
        key = round(float(val), 1)
        ...
        out[i] = mapper[key]
    return out
# in build_session_payload:
np.full(NBINS, prior[trial_idx], dtype=np.int8),
```

**What this does:** `probabilityLeft` is rounded to one decimal and mapped via `{0.2:0, 0.5:1, 0.8:2}` to a categorical index, then broadcast across all 100 bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *wheel_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Wheel speed is absolute wheel velocity." (README.md:82)
> "wheel trace from `_ibl_wheel.*` ... compute wheel speed as absolute velocity" (CONVERSION_NOTES.md:250)

**Code** (convert_data.py:181-189):
```python
def load_wheel_speed(session_path):
    alf_path = session_path / "alf"
    timestamps = np.load(resolve_latest(alf_path, "**/_ibl_wheel.timestamps.npy"))
    position = np.load(resolve_latest(alf_path, "**/_ibl_wheel.position.npy"))
    if timestamps.shape[0] != position.shape[0]:
        raise ValueError(...)
    interp_pos, interp_times = interpolate_position(timestamps, position, freq=1000)
    velocity, _ = velocity_filtered(interp_pos, fs=1000, corner_frequency=20, order=8)
    return interp_times.astype(np.float64), np.abs(velocity).astype(np.float32)
```

**What this does:** Derived from `_ibl_wheel.timestamps.npy` and `_ibl_wheel.position.npy`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *wheel_speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "compute wheel speed as absolute velocity; align/interpolate to the common stimulus-onset grid; discretize using global 3-bin thresholds" (CONVERSION_NOTES.md:250)
> "Wheel and whisker outputs are discretized with global tertile thresholds" (README.md:84)

**Code** (convert_data.py:187-189, 306-330, 463, 736):
```python
interp_pos, interp_times = interpolate_position(timestamps, position, freq=1000)
velocity, _ = velocity_filtered(interp_pos, fs=1000, corner_frequency=20, order=8)
return interp_times.astype(np.float64), np.abs(velocity).astype(np.float32)
# tertile edges:
def robust_tertile_edges(values):
    finite = finite[np.isfinite(finite)]
    q1, q2 = np.quantile(finite, [1/3, 2/3])
    ...
def digitize_three_bins(values, edges):
    return np.digitize(values, bins=np.array([low, high]), right=False).astype(np.int8)
# in main:
all_wheel = np.concatenate([ps.wheel_cont.reshape(-1) for ps in prepared_sessions])
wheel_edges = robust_tertile_edges(all_wheel)
# in build_session_payload:
wheel_bins = digitize_three_bins(prepared.wheel_cont, wheel_edges)
```

**What this does:** Position is interpolated to 1 kHz, low-pass filtered (8th-order, 20 Hz corner) to obtain velocity, absolute-valued for speed. Per-trial linear interpolation onto the 20 ms grid, then global tertile thresholds (1/3, 2/3 quantiles across all kept timepoints from all sessions) digitize into {0, 1, 2}.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-c. How is `output` *wheel_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "align/interpolate to the common stimulus-onset grid" (CONVERSION_NOTES.md:250)

**Code** (convert_data.py:216-255, 270, 479):
```python
def interpolate_behavior_per_trial(target_times, target_vals, align_times, ...):
    interval_begs = align_times + time_window[0]
    interval_ends = align_times + time_window[1]
    n_bins = int(np.ceil((time_window[1] - time_window[0]) / binsize))
    ...
    x_interp = np.linspace(t_beg + binsize, t_end, n_bins)
    y_interp = np.interp(x_interp, curr_times, curr_vals)
# build_session_behavior:
wheel_interp, wheel_mask = interpolate_behavior_per_trial(wheel_times, wheel_speed, align_times)
# build_session_payload row:
wheel_bins[trial_idx],
```

**What this does:** Per-trial wheel speed is linearly interpolated to the same 100-bin stimulus-aligned `[-0.5, 1.5]` s grid as the neural matrix; trials lacking full coverage are dropped via `wheel_mask` so neural and wheel rows refer to identical trials.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Whisker motion energy uses the left camera when available, otherwise the right camera." (README.md:83)

**Code** (convert_data.py:202-213):
```python
def load_whisker_motion_energy(session_path):
    alf_path = session_path / "alf"
    for view in ("left", "right"):
        me_candidates = sorted(alf_path.glob(f"**/{view}Camera.ROIMotionEnergy.npy"))
        ts_candidates = sorted(alf_path.glob(f"**/_ibl_{view}Camera.times.npy"))
        if not me_candidates or not ts_candidates:
            continue
        motion_energy = np.load(me_candidates[-1])
        timestamps = np.load(ts_candidates[-1])
        timestamps, motion_energy = check_video_timestamps(view, timestamps, motion_energy)
        return timestamps.astype(np.float64), motion_energy.astype(np.float32), view
    raise FileNotFoundError(...)
```

**What this does:** Derived from `leftCamera.ROIMotionEnergy.npy` + `_ibl_leftCamera.times.npy` (preferred) or right-camera equivalents.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *whisker_motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "load left whisker motion energy if available, else right; align/interpolate to common stimulus-onset grid; discretize with global 3-bin thresholds; store `0/1/2`" (CONVERSION_NOTES.md:251)
> "reference-style video timestamp repair where camera timestamps longer than motion-energy arrays are trimmed from the front" (CONVERSION_NOTES.md:289)

**Code** (convert_data.py:192-199, 271, 464, 737):
```python
def check_video_timestamps(view, video_timestamps, video_data):
    if video_timestamps.shape[0] > video_data.shape[0]:
        video_timestamps = video_timestamps[-video_data.shape[0]:]
    return video_timestamps, video_data
# build_session_behavior:
whisker_interp, whisker_mask = interpolate_behavior_per_trial(whisker_times, whisker_motion, align_times)
# build_session_payload:
whisker_bins = digitize_three_bins(prepared.whisker_cont, whisker_edges)
# main:
whisker_edges = robust_tertile_edges(all_whisker)
```

**What this does:** Camera timestamps are trimmed from the front to match motion-energy length, per-trial linearly interpolated to the 20 ms grid, then globally tertile-discretized into {0, 1, 2} using thresholds computed across all kept timepoints from all sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *whisker_motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "align/interpolate to common stimulus-onset grid" (CONVERSION_NOTES.md:251)

**Code** (convert_data.py:216-255, 271, 480):
```python
def interpolate_behavior_per_trial(target_times, target_vals, align_times, ...):
    interval_begs = align_times + time_window[0]
    interval_ends = align_times + time_window[1]
    ...
    x_interp = np.linspace(t_beg + binsize, t_end, n_bins)
    y_interp = np.interp(x_interp, curr_times, curr_vals)
# build_session_behavior:
whisker_interp, whisker_mask = interpolate_behavior_per_trial(whisker_times, whisker_motion, align_times)
# row in output matrix:
whisker_bins[trial_idx],
```

**What this does:** Per-trial whisker motion energy is linearly interpolated onto the same `stimOn_times`-aligned 100-bin grid; trials lacking coverage are removed via `whisker_mask`, ensuring 1:1 alignment with neural rows.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Drop any trial lacking full valid coverage of neural, wheel, or whisker data on the common window: no padding or fabricated values." (CONVERSION_NOTES.md:266)
> "Excluded-session reasons from converted metadata: `missing_required_stream`: 20 sessions; `no_good_units_or_too_few_valid_trials`: 1 session" (CONVERSION_NOTES.md:425-426)

**Code** (convert_data.py:236-248, 262-264, 273-275, 294-303):
```python
# interpolate_behavior_per_trial drops trials with NaN or insufficient coverage:
if np.isnan(t_beg) or np.isnan(t_end): continue
if curr_vals.shape[0] == 0: continue
if np.isnan(curr_vals).any(): continue
if abs(t_beg - curr_times[0]) > binsize: continue
if abs(t_end - curr_times[-1]) > binsize: continue
# build_session_behavior:
if n_good_units == 0: return None
keep_mask = trial_mask & wheel_mask & whisker_mask
if keep_mask.sum() < 2: return None
# safe wrapper:
def build_session_behavior_safe(spec):
    try:
        prepared = build_session_behavior(spec)
        if prepared is None:
            return spec.eid, None, "no_good_units_or_too_few_valid_trials"
        return spec.eid, prepared, None
    except FileNotFoundError:
        return spec.eid, None, "missing_required_stream"
    except Exception as exc:
        return spec.eid, None, f"{type(exc).__name__}: {exc}"
```

**What this does:** Trials with NaN or partial coverage are dropped (no imputation). Sessions that lack required streams (`FileNotFoundError`) or end up with no good units / fewer than 2 valid trials are excluded with categorized reason strings recorded in `metadata.excluded_sessions`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Initial full-run profiling showed the real bottleneck was spike-stream reload and dtype copying in pass 2, not the trial-binning code." (CONVERSION_NOTES.md:298)
> "pass 1: 144.12 s; pass 2 build: 455.65 s" (CONVERSION_NOTES.md:402-403)

**Code** (convert_data.py:333-387, 390-422):
```python
def load_good_spikes_and_regions(spec, brain_regions):
    # per-probe load of spikes.times.npy, spikes.clusters.npy with mmap_mode="r"
    spikes_times = np.load(spikes_times_path, mmap_mode="r")
    spikes_clusters = np.load(spikes_clusters_path, mmap_mode="r")
    ...
    merged_spike_times = np.concatenate(spike_times_all)
    order = np.argsort(merged_spike_times)
def bin_spikes_by_trial(...):
    # iterate per trial, np.bincount on flat (cluster*nbins+bin)
```

**What this does:** Pass 2's spike loading + concatenate + argsort across probes and per-trial spike binning dominate runtime; pass 1 trial/wheel/whisker prep is secondary.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Vectorized per-trial spike binning via `np.searchsorted` + flattened `np.bincount`." (CONVERSION_NOTES.md:300)

**Code** (convert_data.py:156-168, 233-253, 405-422, 437-442):
```python
def compute_trial_number_in_block(prob_left):
    out = np.zeros(len(prob_left), dtype=np.int16)
    prev = None; counter = 0
    for i, val in enumerate(prob_left):
        ...
        out[i] = counter
        prev = current
def interpolate_behavior_per_trial(...):
    for i in range(len(align_times)):
        ...
        x_interp = np.linspace(t_beg + binsize, t_end, n_bins)
        y_interp = np.interp(x_interp, curr_times, curr_vals)
def map_prior(raw_prior):
    for i, val in enumerate(raw_prior):
        key = round(float(val), 1)
        out[i] = mapper[key]
def bin_spikes_by_trial(...):
    for i in range(len(align_times)):  # per-trial bincount loop
```

**What this does:** Several Python-level per-trial loops remain (`compute_trial_number_in_block`, `interpolate_behavior_per_trial`, `bin_spikes_by_trial`, `map_prior`) that could be replaced with array-wide numpy ops.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "two-pass converter: pass 1 loads trials + wheel + whisker ... pass 2 reloads good units (`label >= 1`)" (CONVERSION_NOTES.md:285-287)

**Code** (convert_data.py:171-178, 333-348, 451):
```python
def count_good_units(spec):  # called in pass 1
    metrics = pd.read_parquet(metrics_path, columns=["label"])
    total += int((metrics["label"].to_numpy() >= 1).sum())
# load_good_spikes_and_regions  (pass 2)
metrics = pd.read_parquet(metrics_path, columns=["label"])
good_rows = metrics["label"].to_numpy(copy=False) >= 1
# build_session_payload re-instantiates BrainRegions per session:
brain_regions = BrainRegions()
```

**What this does:** `clusters.metrics.pqt` is read once in pass 1 (count) and again in pass 2 (filter). `BrainRegions()` is re-constructed for every session inside the worker. The trials parquet is also reread implicitly via `prepared.trials` being kept around.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none directly)

**Code** (convert_data.py:362, 366-371, 39, 471):
```python
remap = np.full(n_clusters, -1, dtype=np.int32)
remap[good_rows] = np.arange(int(good_rows.sum()), dtype=np.int32)
cluster_channels = np.load(clusters_channels_path, mmap_mode="r")[good_rows]
channel_region_ids = np.load(channels_region_ids_path, mmap_mode="r")
region_ids = np.zeros(cluster_channels.shape[0], dtype=np.int64)
valid_channel = (cluster_channels >= 0) & (cluster_channels < channel_region_ids.shape[0])
region_ids[valid_channel] = channel_region_ids[cluster_channels[valid_channel]]
cluster_regions = brain_regions.id2acronym(region_ids, mapping="Beryl").astype(str)
# COMMON_RELATIVE_TIMES is computed once but full-replicated per trial:
inp = np.vstack([COMMON_RELATIVE_TIMES, np.full(NBINS, ...)])
```

**What this does:** Brain-region mapping and per-trial repetition of the constant `time_since_stimulus_onset_s` row create duplicate data; the constant time vector is identical for every trial across the dataset.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Low-precision storage for neural arrays (`float16`)..." (CONVERSION_NOTES.md:301)
> "Pass-2 spike loading now uses ALF-native cluster indexing, memory-mapped spike arrays, and no-copy dtype handling..." (CONVERSION_NOTES.md:305)

**Code** (convert_data.py:16-19, 352-353, 366-367, 409, 421, 426, 435):
```python
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
...
spikes_times = np.load(spikes_times_path, mmap_mode="r")
spikes_clusters = np.load(spikes_clusters_path, mmap_mode="r")
cluster_channels = np.load(clusters_channels_path, mmap_mode="r")[good_rows]
channel_region_ids = np.load(channels_region_ids_path, mmap_mode="r")
out.append(np.zeros((n_units, n_bins), dtype=np.float16))
counts = np.bincount(flat, minlength=n_units * n_bins).reshape(n_units, n_bins)
out.append(counts.astype(np.float16))
mapped = np.empty(raw_choice.shape[0], dtype=np.int8)
out = np.empty(raw_prior.shape[0], dtype=np.int8)
```

**What this does:** Spike arrays are loaded with `mmap_mode="r"` to avoid full copies. Neural matrices are stored as float16; categorical outputs as int8. BLAS thread counts are pinned to 1 to avoid oversubscription with the thread pool.

**Rating:** ok

**Note:** _(no note)_---

---
