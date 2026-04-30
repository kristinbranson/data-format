# zhang2025 — codex / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/zhang2025/codex/2026-03-24__17-20-29_trial3/verifier/snapshot/`

Outputs identified (K=4): choice, prior_probability_left, wheel_speed_bin, whisker_motion_energy_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Implemented a deterministic session roster from `code/code_zhang2025/data/bwm_release.csv`." (CONVERSION_NOTES.md:266) and "Implemented local ALF/parquet/numpy readers for trials, wheel, whisker motion energy, and spike sorting outputs so conversion matches the reference variables without depending on slow remote metadata resolution." (CONVERSION_NOTES.md:267)

**Code** (convert_data.py:166-187, 872-927):
```python
def load_release_sessions() -> tuple[pd.DataFrame, pd.DataFrame]:
    bwm_df = pd.read_csv(BWM_RELEASE_CSV, index_col=0)
    sessions_df = (
        bwm_df[["eid", "lab", "subject", "date", "session_number"]]
        .drop_duplicates(subset=["eid"], keep="first")
        .reset_index(drop=True)
    )
    probe_map = (
        bwm_df[["eid", "pid", "probe_name"]]
        .astype({"pid": str, "probe_name": str})
        .groupby("eid")
        .apply(lambda frame: [(str(pid), str(probe_name))
               for pid, probe_name in zip(frame["pid"], frame["probe_name"])],
               include_groups=False)
        .to_dict()
    )
    sessions_df["probe_info"] = sessions_df["eid"].map(probe_map)
    return bwm_df, sessions_df
```

**What this does:** Loads the canonical 459-session release roster from `bwm_release.csv` and builds a per-eid probe insertion map. In `--full` mode, sessions are dispatched to a `ProcessPoolExecutor` worker pool that calls `process_one_session` per session; in `--sample` mode they are processed sequentially until 2 successes.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Build unique subject list and index sessions in converted order" (CONVERSION_NOTES.md:236)

**Code** (convert_data.py:688-689, 728):
```python
subjects = ordered_unique([session.subject for session in processed_sessions])
subject_to_idx = {subject: idx for idx, subject in enumerate(subjects)}
...
subject_idx.append(subject_to_idx[session.subject])
```

**What this does:** After processing, builds the unique-ordered subject list from per-session `subject` strings (sourced from `bwm_release.csv`), and stores a parallel `subject_idx` array mapping each session to its subject index.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Session order will be fixed and deterministic in the conversion script." (CONVERSION_NOTES.md:236) and "Sessions converted: 438" (README.md:7)

**Code** (convert_data.py:166-187, 552-558, 975):
```python
def process_one_session(row, time_axis):
    eid = row["eid"]
    t0 = time.time()
    session_path = release_session_path(row)
    trials_df, trials_mask = load_trials_and_mask_current(session_path)
    ...
processed_sessions.sort(key=lambda session: session.release_index)
```

**What this does:** Each row of the deduplicated `bwm_release.csv` represents one session (identified by `eid`); each is processed independently from its own ALF directory and stored as one entry in the `neural`/`input`/`output` lists. After parallel execution, sessions are re-sorted by their original release index for deterministic order.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "spikes are merged across probes before binning; per-trial intervals are computed from `stimOn_times + (-0.5, 1.5)`" (CONVERSION_NOTES.md:80-81)

**Code** (convert_data.py:272-290, 583-594):
```python
intervals = np.vstack([
    trials_df[PARAMS["align_time"]] + PARAMS["time_window"][0],
    trials_df[PARAMS["align_time"]] + PARAMS["time_window"][1],
]).T
...
binned_array = get_spike_data_per_interval(
    regspikes, regclu,
    interval_begs=intervals[:, 0], interval_ends=intervals[:, 1],
    interval_len=interval_len, binsize=PARAMS["binsize"],
)
...
neural_trials = [binned_spikes[i].T.astype(np.float32, copy=False) for i in keep_idx]
```

**What this does:** Per-trial intervals are constructed from each row of the trials parquet table by `stimOn_times + (-0.5, 1.5)`. Spike binning, behavior segmentation, and discretization all index by trial row, and final trial lists are produced by selecting `keep_idx` rows.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reproduce the reference code trial mask exactly, including `max_trial_len=10.0`" (CONVERSION_NOTES.md:211); "Trials are filtered to require valid stimulus onset, feedback, first movement timing, valid choice, valid block probability, and usable whisker and wheel data within the aligned window." (README.md:32)

**Code** (convert_data.py:328-362, 574-577):
```python
def load_trials_and_mask_current(session_path, min_rt=0.08, max_rt=2.0,
                                  max_trial_len=10.0, exclude_nochoice=True):
    trials = pd.read_parquet(trials_path).copy()
    query_parts = []
    if min_rt is not None: query_parts.append(f"(firstMovement_times - stimOn_times < {min_rt})")
    if max_rt is not None: query_parts.append(f"(firstMovement_times - stimOn_times > {max_rt})")
    if max_trial_len is not None: query_parts.append(f"(feedback_times - goCue_times > {max_trial_len})")
    for event in ["stimOn_times","choice","feedback_times","probabilityLeft",
                  "firstMovement_times","feedbackType"]:
        query_parts.append(f"{event}.isnull()")
    if exclude_nochoice: query_parts.append("(choice == 0)")
    mask = ~trials.eval(" | ".join(query_parts)).to_numpy()
...
keep_mask = np.asarray(trials_mask, dtype=bool) & wheel_mask & whisker_mask
```

**What this does:** Replicates the reference IBL trial mask: excludes trials with reaction time outside [0.08, 2.0] s, trial-length > 10 s, NaN events, and no-choice (`choice==0`). The final keep mask additionally requires successful wheel and whisker behavior alignment within the trial window.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neural activity is spike-count data from QC-passing clusters (`label >= 1`), merged across probes within each session." (README.md:30); raw inputs are `spikes.times.npy`, `spikes.clusters.npy`, `clusters.metrics.pqt`, `clusters.channels.npy`, `channels.brainLocationIds_ccf_2017.npy` (CONVERSION_NOTES.md:108).

**Code** (convert_data.py:298-325):
```python
spikes = {
    "times": np.load(sort_dir / "spikes.times.npy"),
    "clusters": np.load(sort_dir / "spikes.clusters.npy").astype(np.int32),
}
clusters_labeled = pd.read_parquet(sort_dir / "clusters.metrics.pqt")
cluster_channels = np.load(sort_dir / "clusters.channels.npy").astype(np.int64)
channel_region_ids = np.load(sort_dir / "channels.brainLocationIds_ccf_2017.npy").astype(np.int64)
cluster_region_ids = channel_region_ids[good_channel_idx]
clusters_labeled["acronym"] = BRAIN_REGIONS.id2acronym(cluster_region_ids)
```

**What this does:** Per-probe pykilosort outputs supply spike times/cluster IDs, cluster metrics (with QC `label`), and channel-to-brain-region mapping. Probe outputs are merged across probes via `merge_probes`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "merge spikes and clusters across probes... bin spike counts in `stimOn_times + [-0.5, 1.5]` using `0.02 s` bins, store per trial as `(n_neurons, 100)` after transposing from reference `(100, n_neurons)`" (CONVERSION_NOTES.md:229)

**Code** (convert_data.py:237-290, 538-549, 583):
```python
spikes, clusters = merge_probes(spikes_list, clusters_list)
...
def get_spike_data_per_interval(times, clusters, interval_begs, interval_ends, interval_len, binsize):
    n_bins = int(np.ceil(interval_len / binsize))
    binned_spikes = np.zeros((n_intervals, n_clusters, n_bins), dtype=np.float32)
    for interval_idx, (t_beg, t_end) in enumerate(zip(interval_begs, interval_ends)):
        idxs_t = (times >= t_beg) & (times < t_end)
        ...
        binned_tmp, _, cluster_idxs = bincount2D(times_curr, clust_curr, xbin=binsize, xlim=[t_beg, t_end])
        binned_spikes[interval_idx, target_indices, :] = binned_tmp[:, :n_bins]
...
neural_trials = [binned_spikes[i].T.astype(np.float32, copy=False) for i in keep_idx]
```

**What this does:** Spikes are merged across probes (cluster ids re-indexed), then per-trial spike counts are computed via `bincount2D` into 100 bins of 20 ms. Final per-trial array is transposed to `(n_neurons, n_bins)`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Use the code's stored QC label to filter to `label >= 1` clusters during conversion." (CONVERSION_NOTES.md:208)

**Code** (convert_data.py:316-325, 524-528):
```python
iok = clusters_labeled["label"] >= qc
selected_clusters = clusters_labeled[iok].copy()
spike_idx, ib = ismember(spikes["clusters"], selected_clusters.index.to_numpy())
selected_clusters.reset_index(drop=True, inplace=True)
selected_spikes = {k: v[spike_idx] for k, v in spikes.items()}
selected_spikes["clusters"] = selected_clusters.index.to_numpy()[ib].astype(np.int32)
...
spikes, clusters = load_spiking_data_current(session_path, probe_name=probe_name, qc=1)
```

**What this does:** Each probe's clusters are filtered to `label >= 1` (well-isolated single units) and only spikes belonging to those clusters are retained, before probe merging and binning.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`align_time='stimOn_times'`, `time_window=(-0.5, 1.5)` seconds, `binsize=0.02` seconds" (CONVERSION_NOTES.md:55-57)

**Code** (convert_data.py:43-48, 246-264):
```python
PARAMS = {
    "interval_len": 2.0, "binsize": 0.02,
    "align_time": "stimOn_times", "time_window": (-0.5, 1.5),
}
...
n_bins = int(np.ceil(interval_len / binsize))
binned_tmp, _, cluster_idxs = bincount2D(times_curr, clust_curr, xbin=binsize, xlim=[t_beg, t_end])
```

**What this does:** Spikes are histogrammed into 100 fixed 20 ms bins per trial via IBL's `bincount2D`. No resampling — counts only.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Temporal alignment: stimulus onset (`stimOn_times`)" (README.md:12)

**Code** (convert_data.py:272-277):
```python
intervals = np.vstack([
    trials_df[PARAMS["align_time"]] + PARAMS["time_window"][0],
    trials_df[PARAMS["align_time"]] + PARAMS["time_window"][1],
]).T
```

**What this does:** Each trial's interval is `stimOn_times + [-0.5, +1.5] s`. Spikes within that window are binned, putting bin 25 (approximately) at stimulus onset.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials.choice` ... raw `+1 -> left -> 0`, raw `-1 -> right -> 1`" (CONVERSION_NOTES.md:232)

**Code** (convert_data.py:198-204, 581):
```python
def choice_to_label(choice_values):
    choice_values = np.asarray(choice_values)
    if not np.all(np.isin(choice_values, [-1, 1])):
        bad = np.unique(choice_values[~np.isin(choice_values, [-1, 1])])
        raise ValueError(f"Unexpected choice values after filtering: {bad.tolist()}")
    return (choice_values == -1).astype(np.int64)
...
choice_all = trials_df["choice"].to_numpy()
```

**What this does:** Sourced from the `choice` column of the trials parquet table.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`choice` with values `left=0`, `right=1`" (README.md:23)

**Code** (convert_data.py:198-204, 601, 714):
```python
return (choice_values == -1).astype(np.int64)
...
choice_labels = choice_to_label(choice_all[keep_idx])
...
np.full(T, session.choice_labels[trial_idx], dtype=np.int64),
```

**What this does:** Maps raw IBL `+1` -> 0 (left), `-1` -> 1 (right); errors on any other value (no-go trials are already excluded by the trial mask). Each trial's scalar label is broadcast to `(T,)`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 3-c. How is `output` *choice* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "repeating per-trial variables across the 100 bins" (CONVERSION_NOTES.md:242)

**Code** (convert_data.py:709-714):
```python
for trial_idx in range(session.kept_trial_count):
    T = session.neural[trial_idx].shape[1]
    outputs_session.append(np.vstack([
        np.full(T, session.choice_labels[trial_idx], dtype=np.int64),
        ...
    ]))
```

**What this does:** Choice is a per-trial scalar replicated across all 100 time bins of the neural array, so `output[trial][0, :]` is constant.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-a. What variables in the raw data is `output` *prior_probability_left* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`trials.probabilityLeft` ... Map `0.2 -> 0`, `0.5 -> 1`, `0.8 -> 2`" (CONVERSION_NOTES.md:233)

**Code** (convert_data.py:579, 207-212):
```python
prob_left_all = trials_df["probabilityLeft"].to_numpy(dtype=float)
...
def prior_to_label(probability_left):
    rounded = np.round(np.asarray(probability_left, dtype=float), 1)
    unknown = sorted(set(rounded.tolist()) - set(PRIOR_MAP))
    if unknown:
        raise ValueError(f"Unexpected probabilityLeft values: {unknown}")
    return np.array([PRIOR_MAP[x] for x in rounded], dtype=np.int64)
```

**What this does:** Sourced from `probabilityLeft` column of the trials parquet table.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-b. What processing is involved in computing `output` *prior_probability_left*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`prior_probability_left` with values `0.2=0`, `0.5=1`, `0.8=2`" (README.md:24)

**Code** (convert_data.py:69-73, 207-212, 602):
```python
PRIOR_MAP = {0.2: 0, 0.5: 1, 0.8: 2}
...
rounded = np.round(np.asarray(probability_left, dtype=float), 1)
return np.array([PRIOR_MAP[x] for x in rounded], dtype=np.int64)
...
prior_labels = prior_to_label(prob_left_all[keep_idx])
```

**What this does:** Round `probabilityLeft` to 1 decimal place, then look up `0.2/0.5/0.8` -> `0/1/2`. Errors if unexpected values appear.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 4-c. How is `output` *prior_probability_left* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "repeating per-trial variables across the 100 bins" (CONVERSION_NOTES.md:242)

**Code** (convert_data.py:715):
```python
np.full(T, session.prior_labels[trial_idx], dtype=np.int64),
```

**What this does:** Per-trial scalar prior label is broadcast to all `T=100` neural time bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-a. What variables in the raw data is `output` *wheel_speed_bin* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Wheel trace loaded via `SessionLoader` / reference behavior loader ... `abs(velocity)`" (CONVERSION_NOTES.md:234); raw files `_ibl_wheel.timestamps.npy`, `_ibl_wheel.position.npy` (CONVERSION_NOTES.md:106).

**Code** (convert_data.py:368-378):
```python
if target == "wheel-speed":
    wheel_timestamps = np.load(find_latest_file(alf_path, "**/_ibl_wheel.timestamps.npy"))
    wheel_position = np.load(find_latest_file(alf_path, "**/_ibl_wheel.position.npy"))
    position, times = interpolate_position(wheel_timestamps, wheel_position, freq=1000)
    velocity, _ = velocity_filtered(position, fs=1000, corner_frequency=20, order=8)
    return {"times": np.asarray(times, dtype=np.float32),
            "values": np.abs(np.asarray(velocity, dtype=np.float32))}
```

**What this does:** Sourced from raw wheel `timestamps.npy` and `position.npy`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-b. What processing is involved in computing `output` *wheel_speed_bin*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Load wheel speed as `abs(velocity)`, align to stimulus onset on the same 2 s / 20 ms grid as neural data, then discretize continuous values into 3 global bins" (CONVERSION_NOTES.md:234); "Compute global tertile thresholds from all retained aligned wheel-speed samples ... apply those thresholds consistently across all sessions." (CONVERSION_NOTES.md:246)

**Code** (convert_data.py:373-378, 648-667, 716-719):
```python
position, times = interpolate_position(wheel_timestamps, wheel_position, freq=1000)
velocity, _ = velocity_filtered(position, fs=1000, corner_frequency=20, order=8)
... abs(velocity) ...
# global tertiles across all sessions
q1, q2 = np.quantile(values, [1/3, 2/3])
...
def discretize(values, thresholds):
    return np.digitize(values, bins=np.array([q1, q2]), right=False).astype(np.int64)
...
discretize(session.wheel_continuous[trial_idx], thresholds["wheel_speed"])
```

**What this does:** Wheel position is interpolated to 1 kHz, low-pass filtered, differentiated to velocity, abs taken. Aligned per-trial via interpolation onto the 100-bin grid. Global wheel-speed tertiles across all retained samples define `digitize` thresholds for 3 bins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 5-c. How is `output` *wheel_speed_bin* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "behavior traces are linearly interpolated onto `n_bins = ceil(interval_len / binsize)` samples" (CONVERSION_NOTES.md:85-86)

**Code** (convert_data.py:407-465, 568, 593):
```python
align_times = trials_df[PARAMS["align_time"]].to_numpy()
interval_begs = align_times + start
interval_ends = align_times + end
...
x_interp = np.linspace(interval_begs[idx] + binsize, interval_ends[idx], n_bins)
fn = interp1d(t_seg, v_seg, kind="linear", fill_value="extrapolate")
y_interp = fn(x_interp)
...
wheel_traces, wheel_mask = align_continuous_behavior(session_path, "wheel-speed", trials_df)
wheel_aligned = [np.asarray(wheel_traces[i], dtype=np.float32) for i in keep_idx]
```

**What this does:** Continuous wheel speed is segmented into the same `stimOn_times + [-0.5, 1.5]` window as neural data and linearly interpolated onto the 100-bin time axis matching the neural matrix.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-a. What variables in the raw data is `output` *whisker_motion_energy_bin* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Load left whisker motion energy when available, otherwise right" (CONVERSION_NOTES.md:235); raw files `_ibl_leftCamera.times.npy`, `leftCamera.ROIMotionEnergy.npy` (and right counterparts) (CONVERSION_NOTES.md:107).

**Code** (convert_data.py:379-400, 473-477):
```python
if target == "left-whisker-motion-energy":
    times = np.load(find_latest_file(alf_path, "**/_ibl_leftCamera.times.npy"))
    values = np.load(find_latest_file(alf_path, "**/leftCamera.ROIMotionEnergy.npy"))
...
if behavior_name == "whisker-motion-energy":
    target = load_target_behavior_current(session_path, "left-whisker-motion-energy")
    if target.get("skip"):
        target = load_target_behavior_current(session_path, "right-whisker-motion-energy")
```

**What this does:** Sourced from camera frame timestamps and per-frame ROI motion energy npy files; left preferred, falling back to right.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-b. What processing is involved in computing `output` *whisker_motion_energy_bin*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "discretize into 3 global bins" (CONVERSION_NOTES.md:235); thresholds from global tertiles (CONVERSION_NOTES.md:246).

**Code** (convert_data.py:382-389, 648-667, 720-723):
```python
if times.shape[0] > values.shape[0]:
    times = times[-values.shape[0]:]
return {"times": ..., "values": np.asarray(values, dtype=np.float32)}
...
q1, q2 = np.quantile(values, [1/3, 2/3])
...
discretize(session.whisker_continuous[trial_idx], thresholds["whisker_motion_energy"])
```

**What this does:** Camera time vector is trimmed to match value length when longer, then aligned (see 6-c). Continuous values are discretized into 3 bins via global tertile thresholds shared across all sessions.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 6-c. How is `output` *whisker_motion_energy_bin* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "align to stimulus onset on the same 2 s / 20 ms grid as neural data" (CONVERSION_NOTES.md:235)

**Code** (convert_data.py:407-465, 569-571, 594):
```python
whisker_traces, whisker_mask = align_continuous_behavior(session_path, "whisker-motion-energy", trials_df)
...
x_interp = np.linspace(interval_begs[idx] + binsize, interval_ends[idx], n_bins)
fn = interp1d(t_seg, v_seg, kind="linear", fill_value="extrapolate")
y_interp = fn(x_interp)
...
whisker_aligned = [np.asarray(whisker_traces[i], dtype=np.float32) for i in keep_idx]
```

**What this does:** Same `get_behavior_per_interval_current` path used for wheel: per-trial segments of the continuous trace are linearly interpolated onto the 100-bin stimulus-onset grid that matches the neural data.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 7. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "21 sessions were excluded after the sequential retry pass because they had `Only 0 valid trials after filtering`" (CONVERSION_NOTES.md:373); "16 trials with all-zero neural matrices across 3 sessions ... genuine sparse-data cases rather than a conversion bug." (CONVERSION_NOTES.md:415)

**Code** (convert_data.py:401-404, 422-449, 535-536, 574-577, 632-645):
```python
except BaseException as exc:
    return {"times": None, "values": None, "skip": True, "error": str(exc)}
...
if target_times is None or target_vals is None:
    return [None] * n_intervals, np.zeros(n_intervals, dtype=bool), ["missing"] * n_intervals
...
if len(v_seg) == 0: reasons[idx] = "target data not present"; continue
if np.sum(np.isnan(v_seg)) > 0 and not allow_nans: reasons[idx] = "nans in target data"; continue
if np.abs(interval_begs[idx] - t_seg[0]) > binsize: reasons[idx] = "target data starts too late"; continue
if np.abs(interval_ends[idx] - t_seg[-1]) > binsize: reasons[idx] = "target data ends too early"; continue
...
if not spikes_list: raise RuntimeError("No good clusters after QC filtering")
...
keep_mask = np.asarray(trials_mask, dtype=bool) & wheel_mask & whisker_mask
keep_idx = np.flatnonzero(keep_mask)
if keep_idx.size < 2:
    raise RuntimeError(f"Only {keep_idx.size} valid trials after filtering")
...
def process_one_session_worker(...):  # 3 attempts with backoff for transient errors
```

**What this does:** Behavior loaders catch errors and return `skip=True`; per-trial alignment marks trials with missing/short/late behavior segments as bad and they are dropped via `keep_mask`. Sessions with no good clusters or fewer than 2 valid trials raise and are reported as skipped. Worker-level retries with backoff handle transient ONE/network errors. Skipped sessions are recorded in `metadata["skipped_sessions"]`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Sample conversion session 1: 3.0 s ... session 2: 6.4 s" (CONVERSION_NOTES.md:329-330); per-session timing logs `trials_s`, `spikes_s`, `behavior_s` (convert_data.py:623-628). The full conversion took 2071 s (34.5 min) on 12 workers (CONVERSION_NOTES.md:372).

**Code** (convert_data.py:623-628):
```python
timing={
    "trials_s": t_trials - t0,
    "spikes_s": t_spikes - t_trials,
    "behavior_s": t_behavior - t_spikes,
    "total_s": t_behavior - t0,
},
```

**What this does:** Per-session timings indicate spike loading + binning and behavior loading + alignment dominate; pickle write of the full ~12 GB output also contributes. Pre-conversion CSV roster load is small.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:215-227, 251-263, 434-465, 705-727):
```python
for idx, value in enumerate(probability_left):
    if idx == 0 or not np.isclose(value, prev): current = 1
    else: current += 1
    out[idx] = current; prev = value
...
for interval_idx, (t_beg, t_end) in enumerate(zip(interval_begs, interval_ends)):
    idxs_t = (times >= t_beg) & (times < t_end)
    ...
for idx, (t_seg, v_seg) in enumerate(zip(target_times_list, target_vals_list)):
    fn = interp1d(t_seg, v_seg, ...); y_interp = fn(x_interp)
...
for trial_idx in range(session.kept_trial_count):
    outputs_session.append(np.vstack([np.full(T, ...), ...]))
```

**What this does:** Several Python loops iterate per trial: `trial_number_in_block`, per-interval spike binning, per-interval interpolation, and per-trial output assembly. Each could be reformulated with vectorized numpy operations or batched interp.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reused the reference-style spike binning logic but switched all session data access to direct local ALF reads, eliminating avoidable network/cache overhead." (CONVERSION_NOTES.md:282)

**Code** (convert_data.py:230-234, 369-371, 380-381, 391-392, 503-510, 568-571):
```python
def find_latest_file(base_dir, pattern):
    matches = sorted(base_dir.glob(pattern))
...
# called repeatedly per file per session
wheel_timestamps = np.load(find_latest_file(alf_path, "**/_ibl_wheel.timestamps.npy"))
...
times = np.load(find_latest_file(alf_path, "**/_ibl_leftCamera.times.npy"))
...
has_trials = any(alf.glob("**/_ibl_trials.table.pqt"))
has_wheel = any(alf.glob("**/_ibl_wheel.timestamps.npy"))
```

**What this does:** Repeated `glob` walks of each session's `alf/` to find latest revision files (one glob per file per call). Continuous wheel/whisker behaviors are loaded then segmented per trial in independent loops; `BrainRegions()` is constructed at module import (single instance, but reused across many calls). `discretize` is invoked per-trial rather than vectorized over a session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Reference helper `load_spiking_data()` also attempted to fetch raw AP stream metadata that is not needed for conversion." (CONVERSION_NOTES.md:278)

**Code** (convert_data.py:544-548, 736-755):
```python
meta = {
    "cluster_regions": list(clusters["acronym"]),
    "good_clusters": (clusters["label"] >= 1).to_numpy(dtype=np.int8),
    "cluster_qc": {k: np.asarray(v) for k, v in clusters.to_dict("list").items()},
}
...
metadata = { ... "skipped_sessions": [...] , ... }
```

**What this does:** A full `cluster_qc` dictionary of all cluster columns is assembled per session but only `cluster_regions` and `good_clusters` actually flow into the output dataset. The `wheel_continuous`/`whisker_continuous` floats are kept in memory through assembly even though only their discretized labels are stored. After QC filtering all clusters already satisfy `label >= 1`, so the `cluster_good` array is uniformly 1.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

## Q 8-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Initial GPU run hit `torch.OutOfMemoryError` during full-dataset training; reran with `--cpu`" (CONVERSION_NOTES.md:443); "First full-conversion attempt with 48 session workers caused severe local disk contention ... Set the default `--session-workers` to 12" (CONVERSION_NOTES.md:366-372).

**Code** (convert_data.py:249, 290, 583, 593-594, 1004-1006):
```python
binned_spikes = np.zeros((n_intervals, n_clusters, n_bins), dtype=np.float32)
...
return np.array([x.T for x in binned_array], dtype=np.float32)
...
neural_trials = [binned_spikes[i].T.astype(np.float32, copy=False) for i in keep_idx]
wheel_aligned = [np.asarray(wheel_traces[i], dtype=np.float32) for i in keep_idx]
...
with out_path.open("wb") as f:
    pickle.dump(dataset, f, protocol=pickle.HIGHEST_PROTOCOL)
```

**What this does:** Arrays are cast to `float32` (or `int8`/`int64`) and `copy=False` is used where possible. Process-pool worker count was tuned down to 12 to avoid disk contention. Otherwise the full dataset is held in memory before pickling, and the final pickle is ~12.49 GB.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---
