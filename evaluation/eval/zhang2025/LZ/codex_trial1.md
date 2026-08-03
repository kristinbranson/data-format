# zhang2025 — codex / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/zhang2025/codex/2026-03-24__17-20-29_trial1/verifier/snapshot/`

Outputs identified (K=4): choice, prior_probability_of_left, wheel_speed_bin, whisker_motion_energy_bin

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "The script now targets the canonical local `2025_Q3_IBL_et_al_BWM/sessions.pqt` release manifest, which contains 459 sessions from 139 subjects and matches the data paper counts." (CONVERSION_NOTES.md:273)

**Code** (convert_data.py:100-133):
```python
def load_session_manifest() -> pd.DataFrame:
    for manifest in MANIFEST_FILES:
        if manifest.exists():
            return pd.read_parquet(manifest)
    raise FileNotFoundError("No session manifests found in data cache")


def resolve_session_specs() -> tuple[list[SessionSpec], list[str]]:
    manifest = load_session_manifest()
    specs: list[SessionSpec] = []
    missing: list[str] = []
    for eid, row in manifest.iterrows():
        session_path = (
            DATA_ROOT
            / row["lab"]
            / "Subjects"
            / row["subject"]
            / str(row["date"])
            / f"{int(row['number']):03d}"
        )
        if not session_path.exists():
            missing.append(eid)
            continue
        specs.append(SessionSpec(eid=eid, lab=str(row["lab"]), subject=str(row["subject"]),
                                 date=str(row["date"]), session_number=int(row["number"]),
                                 session_path=session_path))
    return specs, missing
```

**What this does:** Reads the BWM session manifest parquet (preferring `2025_Q3_IBL_et_al_BWM/sessions.pqt`), iterates rows to construct local session paths under `data/one_cache/<lab>/Subjects/<subject>/<date>/<NNN>`, and returns the subset that exists locally. Each session is then processed via `process_session` (optionally in a thread pool).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "session subject metadata | `subjects`, `subject_idx` | Build unique subject list from kept sessions and index each session into it" (CONVERSION_NOTES.md:240)

**Code** (convert_data.py:617-628):
```python
subjects = sorted({s.subject for s in sessions})
subject_to_idx = {s: i for i, s in enumerate(subjects)}
...
"subjects": subjects,
"subject_idx": np.array([subject_to_idx[s.subject] for s in sessions], dtype=np.int16),
```

**What this does:** Builds a sorted list of unique subject IDs across processed sessions, and stores per-session subject index. Subject identity comes from the manifest row's `subject` field carried in `SessionSpec`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "session-level units of analysis ... merged probes per session" (CONVERSION_NOTES.md:217-218)

**Code** (convert_data.py:111-132, 666):
```python
for eid, row in manifest.iterrows():
    session_path = (DATA_ROOT / row["lab"] / "Subjects" / row["subject"]
                    / str(row["date"]) / f"{int(row['number']):03d}")
    ...
    specs.append(SessionSpec(eid=eid, ..., session_path=session_path))
...
"session_eids": [s.eid for s in sessions],
```

**What this does:** Each manifest row (a unique `eid`) defines a session. Probes within a session are merged (see `load_session_spikes`), and the per-session lists in `data["neural"]`, `data["input"]`, `data["output"]` are aligned to the order of processed sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "create 2 s trial windows aligned to `stimOn_times`" (CONVERSION_NOTES.md:215)

**Code** (convert_data.py:474-485):
```python
masked_trials = trials.loc[trial_mask].reset_index(drop=False)
if len(masked_trials) < 2:
    print(f"[skip] {spec.eid}: fewer than 2 trials after trial mask")
    return None

align_times = masked_trials["stimOn_times"].to_numpy(dtype=np.float64)
neural_trials = bin_spikes_for_trials(
    spike_times, spike_clusters,
    n_clusters=n_clusters_good,
    align_times=align_times,
)
```

**What this does:** Trials come from the IBL `_ibl_trials.table.pqt`. After masking, each kept trial gets a 2 s neural window centered on `stimOn_times` ([-0.5, 1.5] s) and matching behavior interpolation windows.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "required events present; `0.08 <= firstMovement_times - stimOn_times <= 2.0`; `choice != 0`; `feedback_times - goCue_times <= 10.0`" (CONVERSION_NOTES.md:281-283)

**Code** (convert_data.py:160-177, 488-489):
```python
def compute_trial_mask(trials: pd.DataFrame) -> np.ndarray:
    required = ["stimOn_times", "choice", "feedback_times",
                "probabilityLeft", "firstMovement_times", "feedbackType"]
    mask = np.ones(len(trials), dtype=bool)
    rt = trials["firstMovement_times"] - trials["stimOn_times"]
    mask &= rt >= TRIAL_MASK_RT[0]
    mask &= rt <= TRIAL_MASK_RT[1]
    mask &= (trials["feedback_times"] - trials["goCue_times"]) <= MAX_TRIAL_LEN
    mask &= trials["choice"] != 0
    for col in required:
        mask &= trials[col].notna().to_numpy()
    return mask
...
neural_mask = np.array([np.any(trial) for trial in neural_trials], dtype=bool)
combined_mask = wheel_mask & whisk_mask & neural_mask
```

**What this does:** Applies trial mask (RT in [0.08, 2.0] s, trial length <=10 s, no-choice removed, required event columns non-NaN), then further requires successful behavior interpolation (wheel/whisker) and a non-empty neural window.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "`spikes.times`, `spikes.clusters` from all probes in one session | `neural` | Merge probes, keep clusters with `clusters.metrics.label >= 1`, bin counts into 20 ms bins over `[-0.5, 1.5]` s relative to `stimOn_times`" (CONVERSION_NOTES.md:233)

**Code** (convert_data.py:200-245):
```python
spikes_times_file = pick_one_file(pykilo_path, "spikes.times.npy")
spikes_clusters_file = pick_one_file(pykilo_path, "spikes.clusters.npy")
metrics_file = pick_one_file(pykilo_path, "clusters.metrics.pqt")
clusters_channels_file = pick_one_file(pykilo_path, "clusters.channels.npy")
channels_ids_file = pick_one_file(pykilo_path, "channels.brainLocationIds_ccf_2017.npy")
...
metrics = pd.read_parquet(metrics_file, columns=["label"])
cluster_labels = metrics["label"].to_numpy()
good_mask = cluster_labels >= label_threshold
...
spikes_times = np.load(spikes_times_file, mmap_mode="r")
spikes_clusters = np.load(spikes_clusters_file, mmap_mode="r")
```

**What this does:** Per-probe `spikes.times.npy` and `spikes.clusters.npy` (Pykilosort) provide raw spike events; `clusters.metrics.pqt` provides QC labels; `clusters.channels.npy` and `channels.brainLocationIds_ccf_2017.npy` map clusters to brain regions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "merge probes ... keep clusters with `clusters.metrics.label >= 1` ... bin spike counts into 20 ms bins over `[-0.5, 1.5]` s around `stimOn_times`" (CONVERSION_NOTES.md:276-278)

**Code** (convert_data.py:305-333):
```python
def bin_spikes_for_trials(spike_times, spike_clusters, n_clusters,
                          align_times, window=TIME_WINDOW, binsize=BINSIZE_S):
    interval_len = window[1] - window[0]
    n_bins = int(np.ceil(interval_len / binsize))
    intervals = np.c_[align_times + window[0], align_times + window[1]]
    results: list[np.ndarray] = []
    idx_starts = np.searchsorted(spike_times, intervals[:, 0], side="left")
    idx_ends = np.searchsorted(spike_times, intervals[:, 1], side="left")
    for idx0, idx1, (start, end) in zip(idx_starts, idx_ends, intervals):
        trial_counts = np.zeros((n_clusters, n_bins), dtype=np.float16)
        if idx1 > idx0:
            counts, _, cluster_idx = bincount2D(
                spike_times[idx0:idx1], spike_clusters[idx0:idx1],
                xbin=binsize, xlim=[start, end])
            if counts.size:
                counts = counts[:, :n_bins]
                trial_counts[cluster_idx, : counts.shape[1]] = counts.astype(np.float16)
        results.append(trial_counts)
    return results
```

**What this does:** Probes are merged with cluster-id offsets and spike times sorted; per-trial spike counts are binned with `bincount2D` over [-0.5, 1.5] s in 20 ms bins (100 bins). Counts are stored as float16; no smoothing or z-scoring.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Neurons are filtered using `clusters.metrics.label >= 1`, matching the 75,708 well-isolated neurons" (README.md:81)

**Code** (convert_data.py:217-220, 488):
```python
metrics = pd.read_parquet(metrics_file, columns=["label"])
cluster_labels = metrics["label"].to_numpy()
good_mask = cluster_labels >= label_threshold  # GOOD_CLUSTER_LABEL = 1
selected_cluster_ids = np.flatnonzero(good_mask)
...
neural_mask = np.array([np.any(trial) for trial in neural_trials], dtype=bool)
```

**What this does:** Clusters with `label >= 1` are kept (well-isolated IBL units). All-zero neural-trial windows are subsequently excluded by `neural_mask`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "20 ms bins over `[-0.5, 1.5]` s relative to stimulus onset" (README.md:13-14); `BINSIZE_S = 0.02`, `N_BINS = 100`.

**Code** (convert_data.py:44-46, 313-322):
```python
TIME_WINDOW = (-0.5, 1.5)
BINSIZE_S = 0.02
N_BINS = int(round((TIME_WINDOW[1] - TIME_WINDOW[0]) / BINSIZE_S))
...
n_bins = int(np.ceil(interval_len / binsize))
...
counts, _, cluster_idx = bincount2D(
    spike_times[idx0:idx1], spike_clusters[idx0:idx1],
    xbin=binsize, xlim=[start, end])
```

**What this does:** Fixed 20 ms bins via `bincount2D` produce 100 bins per 2 s trial window.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Alignment event: stimulus onset" (README.md:12); "Temporal alignment: `TIME_WINDOW = (-0.5, 1.5)`, `BINSIZE_S = 0.02`, and `stimOn_times` alignment" (CONVERSION_NOTES.md:429)

**Code** (convert_data.py:479-485):
```python
align_times = masked_trials["stimOn_times"].to_numpy(dtype=np.float64)
neural_trials = bin_spikes_for_trials(
    spike_times,
    spike_clusters,
    n_clusters=n_clusters_good,
    align_times=align_times,
)
```

**What this does:** Each trial uses `stimOn_times` as t=0 with the [-0.5, 1.5] s window passed to spike binning.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_stimulus_onset* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:234 — `| common trial time grid | input[0] | Signed time since stimulus onset at each bin, repeated for every trial as a length-100 vector | Code uses binsize=0.02, time_window=(-0.5, 1.5); behavior interpolation uses right-edge sample times | Planned values: [-0.48, -0.46, ..., 1.50] s to match behavior interpolation grid |`

**Code** (convert_data.py:44-46, 421-422, 631):
```python
TIME_WINDOW = (-0.5, 1.5)
BINSIZE_S = 0.02
N_BINS = int(round((TIME_WINDOW[1] - TIME_WINDOW[0]) / BINSIZE_S))

def make_time_input() -> np.ndarray:
    return np.linspace(TIME_WINDOW[0] + BINSIZE_S, TIME_WINDOW[1], N_BINS, dtype=np.float32)

        "input_names": ["time_since_stimulus_onset", "trial_number_in_block"],
```

**What this does:** The trial produces this input under the name `time_since_stimulus_onset` (`input[0]`). It is not read from any raw data field; it is constructed from the script constants `TIME_WINDOW = (-0.5, 1.5)` and `BINSIZE_S = 0.02`, which are the same window/bin size used to bin spikes relative to the raw `stimOn_times` alignment.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_stimulus_onset*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:419 — `exported time_since_stimulus_onset matched the directly reconstructed np.linspace(-0.48, 1.5, 100) grid (np.allclose == True)`
> CONVERSION_NOTES.md:245 — `Use 2D time-varying arrays for both input and output: Static trial variables (choice, prior, trial_number_in_block) will be repeated across the 100-bin time axis so every trial has consistent (d, T) tensors.`

**Code** (convert_data.py:421-422, 500-515):
```python
def make_time_input() -> np.ndarray:
    return np.linspace(TIME_WINDOW[0] + BINSIZE_S, TIME_WINDOW[1], N_BINS, dtype=np.float32)
...
    time_input = make_time_input()
    inputs = []
    ...
    for block_num, choice_val, prior_val in zip(block_vals, choice_vals, prior_vals, strict=True):
        input_trial = np.vstack(
            [
                time_input,
                np.full(N_BINS, block_num, dtype=np.float32),
            ]
        ).astype(np.float32)
        inputs.append(input_trial)
```

**What this does:** A single 100-element vector is built once per session with `np.linspace(-0.5 + 0.02, 1.5, 100)`, i.e. the right edge of each 20 ms bin, giving values `[-0.48, ..., 1.50]` s. The same vector is stacked as row 0 of every trial's input array, so all trials share an identical time axis.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_stimulus_onset* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:234 — `Signed time since stimulus onset at each bin, repeated for every trial as a length-100 vector | Code uses binsize=0.02, time_window=(-0.5, 1.5); behavior interpolation uses right-edge sample times`

**Code** (convert_data.py:305-320, 479-485):
```python
def bin_spikes_for_trials(..., align_times, window=TIME_WINDOW, binsize=BINSIZE_S):
    interval_len = window[1] - window[0]
    n_bins = int(np.ceil(interval_len / binsize))
    intervals = np.c_[align_times + window[0], align_times + window[1]]
...
align_times = masked_trials["stimOn_times"].to_numpy(dtype=np.float64)
neural_trials = bin_spikes_for_trials(
    spike_times,
    spike_clusters,
    n_clusters=n_clusters_good,
    align_times=align_times,
)
```

**What this does:** Neural bins are cut from `stimOn_times + [-0.5, 1.5]` s in 20 ms steps, and the time input is the `np.linspace(-0.48, 1.5, 100)` grid of right bin edges over that same window. Both arrays carry `N_BINS = 100` columns, so column *i* of the time input corresponds to column *i* of the neural array by construction; no separate re-alignment step is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `input` *trial_number_in_block* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:235 — `| raw probabilityLeft block sequence | input[1] | Trial number within current probability block, computed on the original trial sequence, then repeated across all 100 bins in the kept trial | Derived from trial table; no direct helper in repo | Block counter resets whenever probabilityLeft changes |`

**Code** (convert_data.py:458, 506, 631):
```python
block_trial_number = compute_trial_number_in_block(trials["probabilityLeft"].to_numpy())
...
block_vals = block_trial_number[masked_keep["index"].to_numpy()]
...
        "input_names": ["time_since_stimulus_onset", "trial_number_in_block"],
```

**What this does:** The trial produces this input as `input[1]`, named `trial_number_in_block`. It is derived from the `probabilityLeft` column of the raw trials table (`_ibl_trials.probabilityLeft`), read over the full unmasked trial sequence, plus the original trial index (`masked_keep["index"]`) used to select kept trials.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `input` *trial_number_in_block*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:235 — `Trial number within current probability block, computed on the original trial sequence, then repeated across all 100 bins in the kept trial ... Block counter resets whenever probabilityLeft changes`
> CONVERSION_NOTES.md:420 — `exported trial_number_in_block matched a direct block counter computed from the raw probabilityLeft sequence (np.allclose == True)`

**Code** (convert_data.py:180-192, 506-515):
```python
def compute_trial_number_in_block(prob_left: np.ndarray) -> np.ndarray:
    counters = np.zeros(len(prob_left), dtype=np.float32)
    if len(prob_left) == 0:
        return counters
    count = 1
    counters[0] = count
    for i in range(1, len(prob_left)):
        if prob_left[i] == prob_left[i - 1]:
            count += 1
        else:
            count = 1
        counters[i] = count
    return counters
...
    block_vals = block_trial_number[masked_keep["index"].to_numpy()]
    for block_num, choice_val, prior_val in zip(block_vals, choice_vals, prior_vals, strict=True):
        input_trial = np.vstack([time_input, np.full(N_BINS, block_num, dtype=np.float32)])
```

**What this does:** A running counter walks the full raw trial sequence, incrementing while `probabilityLeft` is unchanged and resetting to 1 whenever it changes, so counting is 1-based and done before trial masking. Kept trials index into this per-session counter by their original trial index, and the resulting scalar is broadcast across all 100 time bins as row 1 of the input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *choice* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "raw `choice` | `output[0]` | Map raw IBL code to categorical side: `choice == 1 -> left -> 0`, `choice == -1 -> right -> 1`" (CONVERSION_NOTES.md:236)

**Code** (convert_data.py:401-407, 504):
```python
def map_choice_to_binary(choice_values: np.ndarray) -> np.ndarray:
    mapped = np.full(choice_values.shape, -1, dtype=np.int16)
    mapped[choice_values == 1] = 0   # left
    mapped[choice_values == -1] = 1  # right
    if np.any(mapped < 0):
        raise ValueError("Unexpected choice values after masking")
    return mapped
...
choice_vals = map_choice_to_binary(masked_keep["choice"].to_numpy(dtype=np.float64))
```

**What this does:** Derived from the `choice` column of the IBL trial table.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *choice*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "After applying the no-choice mask, map the two remaining raw values to `{0, 1}` in the target export." (CONVERSION_NOTES.md:202)

**Code** (convert_data.py:401-407, 516):
```python
mapped[choice_values == 1] = 0   # left
mapped[choice_values == -1] = 1  # right
...
choice.append(np.full(N_BINS, choice_val, dtype=np.int16))
```

**What this does:** After trial mask drops `choice == 0`, raw {+1, -1} are remapped to {0 (left), 1 (right)} and broadcast across all 100 bins of the trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *prior_probability_left* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "raw `probabilityLeft` | `output[1]` | Map `{0.2, 0.5, 0.8}` to `{0, 1, 2}`" (CONVERSION_NOTES.md:237)

**Code** (convert_data.py:410-418, 505):
```python
def map_prior_to_categorical(prob_left: np.ndarray) -> np.ndarray:
    mapped = np.full(prob_left.shape, -1, dtype=np.int16)
    mapped[np.isclose(prob_left, 0.2)] = 0
    mapped[np.isclose(prob_left, 0.5)] = 1
    mapped[np.isclose(prob_left, 0.8)] = 2
    ...
prior_vals = map_prior_to_categorical(masked_keep["probabilityLeft"].to_numpy(dtype=np.float64))
```

**What this does:** Derived from the `probabilityLeft` column of the trial table.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *prior_probability_left*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Export prior as the user-required categorical mapping `0.2 -> 0`, `0.5 -> 1`, `0.8 -> 2`." (CONVERSION_NOTES.md:203)

**Code** (convert_data.py:410-417, 517):
```python
mapped[np.isclose(prob_left, 0.2)] = 0
mapped[np.isclose(prob_left, 0.5)] = 1
mapped[np.isclose(prob_left, 0.8)] = 2
...
prior.append(np.full(N_BINS, prior_val, dtype=np.int16))
```

**What this does:** Three discrete probability levels are mapped to integer classes and broadcast across the 100-bin trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *wheel_speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "wheel speed from `_ibl_wheel.position.npy` and `_ibl_wheel.timestamps.npy` using bundled `brainbox.behavior.wheel`" (CONVERSION_NOTES.md:285)

**Code** (convert_data.py:336-347):
```python
def load_wheel_speed(session_path: Path) -> tuple[np.ndarray, np.ndarray]:
    wheel_pos_file = pick_one_file(session_path / "alf", "_ibl_wheel.position.npy")
    wheel_ts_file = pick_one_file(session_path / "alf", "_ibl_wheel.timestamps.npy")
    ...
    pos = np.asarray(np.load(wheel_pos_file), dtype=np.float64)
    ts = np.asarray(np.load(wheel_ts_file), dtype=np.float64)
    if ts.ndim == 2 and ts.shape[1] == 2:
        ts = ts.mean(axis=1)
    pos_interp, ts_interp = interpolate_position(ts, pos, freq=1000)
    vel, _ = velocity_filtered(pos_interp, 1000)
    return ts_interp, np.abs(vel)
```

**What this does:** Derived from raw wheel position and timestamp arrays (`_ibl_wheel.position.npy`, `_ibl_wheel.timestamps.npy`).

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *wheel_speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Load wheel velocity, take absolute value to obtain speed, interpolate onto stimulus-onset grid, then discretize into 3 global bins" (CONVERSION_NOTES.md:238)

**Code** (convert_data.py:345-347, 425-443, 685):
```python
pos_interp, ts_interp = interpolate_position(ts, pos, freq=1000)
vel, _ = velocity_filtered(pos_interp, 1000)
return ts_interp, np.abs(vel)
...
def compute_tertile_edges(values):
    ...
    q1, q2 = np.quantile(concat, [1 / 3, 2 / 3])
    ...
def discretize_three_bins(values, edges):
    return np.digitize(values, bins=np.array(edges, dtype=np.float32), right=False).astype(np.int16)
...
discretize_three_bins(wheel_cont, wheel_edges),
```

**What this does:** Wheel position is interpolated to 1 kHz, velocity filtered, |velocity| taken as speed; per-trial values are interpolated onto the [-0.5, 1.5] s 20 ms grid; finally discretized into 3 global tertile bins computed across all sessions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-c. How is `output` *wheel_speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "both interpolated onto the shared stimulus-onset-aligned 20 ms grid" (CONVERSION_NOTES.md:287)

**Code** (convert_data.py:366-398, 486-489):
```python
def interpolate_behavior_trials(target_times, target_values, align_times,
                                window=TIME_WINDOW, binsize=BINSIZE_S):
    ...
    x_rel = np.linspace(window[0] + binsize, window[1], n_bins)
    ...
    interp = interp1d(ts, vals, kind="linear", fill_value="extrapolate")
    outputs.append(interp(align_time + x_rel).astype(np.float32))
    mask[i] = True
...
wheel_trials, wheel_mask = interpolate_behavior_trials(wheel_times, wheel_speed, align_times)
```

**What this does:** Wheel speed is linearly interpolated onto the same per-trial bin centers used for neural binning (relative to `stimOn_times`). Trials with insufficient surrounding samples are dropped via `wheel_mask`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *whisker_motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "whisker motion energy from left camera first, right fallback" (CONVERSION_NOTES.md:286)

**Code** (convert_data.py:350-363):
```python
def load_whisker_motion_energy(session_path: Path) -> tuple[np.ndarray, np.ndarray, str]:
    for camera in ("left", "right"):
        me_file = pick_one_file(session_path / "alf", f"{camera}Camera.ROIMotionEnergy.npy")
        times_file = pick_one_file(session_path / "alf", f"*{camera}Camera.times.npy")
        if me_file is None or times_file is None:
            continue
        values = np.asarray(np.load(me_file), dtype=np.float64)
        times = np.asarray(np.load(times_file), dtype=np.float64)
        ...
        return times, values, camera
    raise FileNotFoundError(...)
```

**What this does:** Derived from `leftCamera.ROIMotionEnergy.npy` (or right-camera fallback) and the matching camera `times.npy`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *whisker_motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Load left whisker motion energy; if unavailable, fall back to right; interpolate onto stimulus-onset grid; discretize into 3 global bins" (CONVERSION_NOTES.md:239)

**Code** (convert_data.py:487, 686):
```python
whisk_trials, whisk_mask = interpolate_behavior_trials(whisk_times, whisk_values, align_times)
...
discretize_three_bins(whisk_cont, whisker_edges),
```

**What this does:** Raw motion energy values (loaded from camera) are linearly interpolated to per-trial 20 ms bins, then discretized into three global tertile classes derived from all aligned values across sessions.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 8-c. How is `output` *whisker_motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "interpolated onto the shared stimulus-onset-aligned 20 ms grid" (CONVERSION_NOTES.md:287)

**Code** (convert_data.py:382-397):
```python
idx_beg = np.searchsorted(target_times, align_times + window[0], side="right")
idx_end = np.searchsorted(target_times, align_times + window[1], side="left")
for i, align_time in enumerate(align_times):
    ...
    interp = interp1d(ts, vals, kind="linear", fill_value="extrapolate")
    outputs.append(interp(align_time + x_rel).astype(np.float32))
    mask[i] = True
```

**What this does:** Same interpolation routine as wheel: per-trial whisker values are sampled at bin centers relative to `stimOn_times`. Trials where source samples don't bracket the window are dropped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "21 unusable sessions: 6 with missing wheel files; 14 with missing whisker motion energy; 1 with fewer than 2 trials surviving behavior alignment" (CONVERSION_NOTES.md:399-401)

**Code** (convert_data.py:467-493):
```python
try:
    wheel_times, wheel_speed = load_wheel_speed(spec.session_path)
    whisk_times, whisk_values, whisk_source = load_whisker_motion_energy(spec.session_path)
except FileNotFoundError as exc:
    print(f"[skip] {spec.eid}: {exc}")
    return None
...
masked_trials = trials.loc[trial_mask].reset_index(drop=False)
if len(masked_trials) < 2:
    print(f"[skip] {spec.eid}: fewer than 2 trials after trial mask")
    return None
...
neural_mask = np.array([np.any(trial) for trial in neural_trials], dtype=bool)
combined_mask = wheel_mask & whisk_mask & neural_mask

if combined_mask.sum() < 2:
    print(f"[skip] {spec.eid}: fewer than 2 trials after behavior/neural alignment")
    return None
```

**What this does:** Sessions missing wheel/whisker files raise `FileNotFoundError` and are skipped. Trial-level NaNs in required columns are masked out. Behavior interpolation returns `None` for trials whose source samples don't span the window, and all-zero neural windows are dropped. Sessions with <2 valid trials are skipped entirely.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Trial-by-trial spike binning is the main hot path." (CONVERSION_NOTES.md:301)

**Code** (convert_data.py:317-332):
```python
results: list[np.ndarray] = []
idx_starts = np.searchsorted(spike_times, intervals[:, 0], side="left")
idx_ends = np.searchsorted(spike_times, intervals[:, 1], side="left")
for idx0, idx1, (start, end) in zip(idx_starts, idx_ends, intervals):
    trial_counts = np.zeros((n_clusters, n_bins), dtype=np.float16)
    if idx1 > idx0:
        counts, _, cluster_idx = bincount2D(
            spike_times[idx0:idx1], spike_clusters[idx0:idx1],
            xbin=binsize, xlim=[start, end])
        ...
    results.append(trial_counts)
```

**What this does:** Per-trial spike binning via `bincount2D` over hundreds of trials per session is the dominant cost; behavior interpolation (per-trial `interp1d`) is also looped per trial.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:180-192, 384-397):
```python
def compute_trial_number_in_block(prob_left: np.ndarray) -> np.ndarray:
    counters = np.zeros(len(prob_left), dtype=np.float32)
    ...
    for i in range(1, len(prob_left)):
        if prob_left[i] == prob_left[i - 1]:
            count += 1
        else:
            count = 1
        counters[i] = count
    return counters
...
for i, align_time in enumerate(align_times):
    ...
    interp = interp1d(ts, vals, kind="linear", fill_value="extrapolate")
    outputs.append(interp(align_time + x_rel).astype(np.float32))
```

**What this does:** Python-level per-trial loops appear in spike binning, behavior interpolation, output construction (508-517), and the block-counter (`compute_trial_number_in_block` could use a vectorized run-length approach).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:543-544, 670-693):
```python
def process_session_worker(spec: SessionSpec) -> ProcessedSession | None:
    return process_session(spec, BrainRegions())
...
for session in sessions:
    data["neural"].append([trial.astype(np.float16) for trial in session.neural])
    data["input"].append([trial.astype(np.float32) for trial in session.inputs])
    session_output = []
    for choice, prior, wheel_cont, whisk_cont in zip(...):
        output_trial = np.vstack([
            choice, prior,
            discretize_three_bins(wheel_cont, wheel_edges),
            discretize_three_bins(whisk_cont, whisker_edges),
        ]).astype(np.int16)
```

**What this does:** `BrainRegions()` is reinstantiated per worker call (per session). Per-trial `discretize_three_bins` is invoked twice per trial during dict assembly, after the same continuous arrays were already computed in `process_session`. Trial array dtype recasts (float16/float32) repeat through the pipeline.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "(none)"

**Code** (convert_data.py:531-532, 574-579):
```python
wheel_cont=[np.asarray(x, dtype=np.float32) for x in wheel_keep],
whisker_cont=[np.asarray(x, dtype=np.float32) for x in whisk_keep],
...
ax[1].plot(t, input_trial[0], label="time since stim")
ax[1].plot(t, input_trial[1], label="trial number in block")
```

**What this does:** Continuous wheel/whisker arrays are stored on `ProcessedSession` but only the discretized versions reach the exported pickle (continuous values are used only for tertile-edge computation and optional plotting). Processing-summary plotting (executed only with `--show-processing`) does extra work not used downstream.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> "Spike arrays are memory-mapped and only QC-passing spikes are materialized." (CONVERSION_NOTES.md:305)

**Code** (convert_data.py:230-237, 321, 671):
```python
spikes_times = np.load(spikes_times_file, mmap_mode="r")
spikes_clusters = np.load(spikes_clusters_file, mmap_mode="r")
spike_keep = good_mask[spikes_clusters]
...
selected_times = np.asarray(spikes_times[spike_keep], dtype=np.float64)
selected_clusters = remap[np.asarray(spikes_clusters[spike_keep], dtype=np.int64)]
...
trial_counts = np.zeros((n_clusters, n_bins), dtype=np.float16)
...
data["neural"].append([trial.astype(np.float16) for trial in session.neural])
```

**What this does:** Spike arrays are memory-mapped on read and filtered to QC-passing clusters before materialization. Per-trial spike count matrices are stored as `float16` to halve memory; outputs are `int16`.

**Rating:** ok

**Note:** _(no note)_---

---
