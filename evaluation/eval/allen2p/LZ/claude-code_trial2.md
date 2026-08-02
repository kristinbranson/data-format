# allen2p — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/allen2p/claude-code/2026-03-26__07-49-34_trial2/verifier/snapshot/`

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:22-24, 80-82: "284 NWB files in `behavior_ophys_experiments/`"; "Each NWB file = one imaging plane from one session." CONVERSION_NOTES.md:243-245: "Pass 1: Collect running speed and pupil statistics... Pass 2: Full conversion."

**Code** (convert_data.py:32-57, 480-488):
```python
NWB_DIR = 'data/visual-behavior-ophys-1.1.0/behavior_ophys_experiments/'
METADATA_DIR = 'data/visual-behavior-ophys-1.1.0/project_metadata/'
...
def get_experiment_metadata():
    exp_table = pd.read_csv(os.path.join(METADATA_DIR, 'ophys_experiment_table.csv'))
    nwb_files = glob.glob(os.path.join(NWB_DIR, '*.nwb'))
    nwb_map = {}
    for f in nwb_files:
        eid = int(os.path.basename(f).replace('behavior_ophys_experiment_', '').replace('.nwb', ''))
        nwb_map[eid] = f
    our_exps = exp_table[exp_table['ophys_experiment_id'].isin(nwb_map.keys())].copy()
    active_exps = our_exps[our_exps['passive'] == False].copy()
    active_exps = active_exps.sort_values('ophys_experiment_id').reset_index(drop=True)
    return active_exps, nwb_map
...
for idx, (_, row) in enumerate(active_exps.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = nwb_map[eid]
    stats = process_experiment(nwb_path, row, collect_stats_only=True)
```

**What this does:** Reads NWB files directly via `h5py` from a local data directory, joining them to the `ophys_experiment_table.csv` metadata. Filters to `passive == False` (active behavior) experiments. Each experiment is processed in a per-experiment loop (two passes: stats collection and full conversion).

**Rating:** ok

**Note:** _(no note)_

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:312: "Subjects | 38" derived from `mouse_id` of active experiments.

**Code** (convert_data.py:517, 579):
```python
subjects_list = sorted(active_exps['mouse_id'].unique().astype(str).tolist())
...
subject_idx = subjects_list.index(result['mouse_id'])
all_subject_idx.append(subject_idx)
```

**What this does:** Derives the subject list from unique `mouse_id` values across active experiments and assigns each session a subject index by lookup in this sorted list.

**Rating:** match

**Note:** _(no note)_

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:81: "Each NWB file = one imaging plane from one session." Code treats each NWB file (each `ophys_experiment_id`) as a session unit; no aggregation by `ophys_session_id`.

**Code** (convert_data.py:55-57, 523-527):
```python
active_exps = our_exps[our_exps['passive'] == False].copy()
active_exps = active_exps.sort_values('ophys_experiment_id').reset_index(drop=True)
...
for idx, (_, row) in enumerate(active_exps.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = nwb_map[eid]
    result = process_experiment(nwb_path, row, collect_stats_only=False)
```

**What this does:** Treats each `ophys_experiment_id` (a single imaging plane / NWB file) as one "session" entry in the output. Sessions/experiments are processed independently and not grouped by `ophys_session_id`.

**Rating:** incorrect

**Note:** _(no note)_

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:172: "Per task instructions: Include Go and Catch trials, exclude Aborted and Auto-rewarded." CONVERSION_NOTES.md:218: "Time bin = 750ms (1 per stimulus flash)... Each bin = 250ms image + 500ms grey."

**Code** (convert_data.py:128-145, 216-232):
```python
trials = f['intervals']['trials']
trial_ids = trials['id'][:]
trial_go = trials['go'][:].astype(bool)
trial_catch = trials['catch'][:].astype(bool)
trial_aborted = trials['aborted'][:].astype(bool)
trial_auto = trials['auto_rewarded'][:].astype(bool)
...
trial_mask = (trial_go | trial_catch) & ~trial_aborted & ~trial_auto
valid_trial_ids = trial_ids[trial_mask]
...
for trial_idx in np.where(trial_mask)[0]:
    tid = trial_ids[trial_idx]
    trial_stim_indices = np.where(stim_trials_id == tid)[0]
    if len(trial_stim_indices) == 0:
        continue
    n_bins = len(trial_stim_indices)
    neural_matrix = np.zeros((n_neurons, n_bins), dtype=np.float32)
    for bi, si in enumerate(trial_stim_indices):
        s, e = ophys_bin_starts[si], ophys_bin_ends[si]
        n_frames = e - s
        if n_frames > 0:
            neural_matrix[:, bi] = (dff_cumsum[e] - dff_cumsum[s]) / n_frames
```

**What this does:** Trials come from the NWB `intervals/trials` table. Each trial's bins are defined by the stimulus presentations belonging to that trial (`stim_trials_id == tid`); `n_bins` = the number of 750ms stimulus presentations in that trial.

**Rating:** concerning

**Note:** did not use start_time and stop_time explicitly, but using side information that could be inconsistent

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:172-174: "Per task instructions: Include Go and Catch trials, exclude Aborted and Auto-rewarded. Paper excludes images where licking bout already ongoing." CONVERSION_NOTES.md:529: "if result is None or result['n_trials'] < 2: skipped"

**Code** (convert_data.py:144-145, 219-223, 529-533):
```python
trial_mask = (trial_go | trial_catch) & ~trial_aborted & ~trial_auto
valid_trial_ids = trial_ids[trial_mask]
...
trial_stim_indices = np.where(stim_trials_id == tid)[0]
if len(trial_stim_indices) == 0:
    continue
...
if result is None or result['n_trials'] < 2:
    skipped += 1
    reason = 'no result' if result is None else f'only {result["n_trials"]} trials'
    print(f"  Skipped experiment {eid}: {reason}")
    continue
```

**What this does:** Filters trials to Go or Catch trials, excluding aborted and auto-rewarded. Trials with no associated stimulus presentations are skipped. Sessions yielding fewer than 2 valid trials are dropped. No further per-trial QC (e.g., ongoing licking bout) is applied.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:51: "dF/F is pre-computed in NWB files." CONVERSION_NOTES.md:209: "dF/F traces | neural | Average within 750ms stimulus bins."

**Code** (convert_data.py:99-108):
```python
dff_data = f['processing']['ophys']['dff']['traces']['data'][:]  # (timepoints, neurons)
ophys_ts = f['processing']['ophys']['dff']['traces']['timestamps'][:]

cell_table = f['processing']['ophys']['image_segmentation']['cell_specimen_table']
valid_roi = cell_table['valid_roi'][:].astype(bool)
n_total_rois = dff_data.shape[1]

dff_valid = dff_data[:, valid_roi]  # (timepoints, n_valid_neurons)
n_neurons = dff_valid.shape[1]
```

**What this does:** Reads the pre-computed dF/F traces from `processing/ophys/dff/traces/data` in the NWB file, along with their timestamps and the `cell_specimen_table` for `valid_roi` filtering.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:218-219: "Time bin = 750ms (1 per stimulus flash)." CONVERSION_NOTES.md:247-248: "Cumulative sum-based bin averaging."

**Code** (convert_data.py:171-185, 226-232):
```python
bin_duration = TIME_BIN_MS / 1000.0  # 0.75s
all_stim_starts = stim_start
all_stim_ends = all_stim_starts + bin_duration
ophys_bin_starts = np.searchsorted(ophys_ts, all_stim_starts, side='left')
ophys_bin_ends = np.searchsorted(ophys_ts, all_stim_ends, side='left')

dff_cumsum = np.cumsum(dff_valid, axis=0)
dff_cumsum = np.vstack([np.zeros((1, n_neurons), dtype=dff_cumsum.dtype), dff_cumsum])
...
neural_matrix = np.zeros((n_neurons, n_bins), dtype=np.float32)
for bi, si in enumerate(trial_stim_indices):
    s, e = ophys_bin_starts[si], ophys_bin_ends[si]
    n_frames = e - s
    if n_frames > 0:
        neural_matrix[:, bi] = (dff_cumsum[e] - dff_cumsum[s]) / n_frames
```

**What this does:** Averages dF/F frames falling within each 750ms stimulus presentation window (start to start+0.75s) into a single value per bin per neuron, using a cumulative-sum trick for efficiency. No additional filtering or normalization beyond that already in the NWB dF/F.

**Rating:** incorrect

**Note:** averge all the neural data within the same stim presentation bin (750 ms), very wrong choice...

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:159-160: "valid_roi filter: excludes unions of cells, duplicates, edge ROIs, apical dendrites, too small/narrow/dim, ghost cells, negative/zero traces." CONVERSION_NOTES.md:221: "valid_roi filter: Use only cells marked valid_roi=True."

**Code** (convert_data.py:103-112):
```python
cell_table = f['processing']['ophys']['image_segmentation']['cell_specimen_table']
valid_roi = cell_table['valid_roi'][:].astype(bool)
n_total_rois = dff_data.shape[1]

dff_valid = dff_data[:, valid_roi]  # (timepoints, n_valid_neurons)
n_neurons = dff_valid.shape[1]

if n_neurons == 0:
    print(f"  WARNING: Experiment {experiment_id} has 0 valid neurons, skipping")
    return None
```

**What this does:** Subsets neurons to those with `valid_roi == True` in the NWB cell specimen table. Experiments with zero valid neurons are skipped entirely.

**Rating:** match

**Note:** _(no note)_

---

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:34: `TIME_BIN_MS = 750.0  # One bin per stimulus presentation (250ms image + 500ms grey)`. CONVERSION_NOTES.md:218: "Natural task unit, consistent across all equipment types (MESO/CAM2P)."

**Code** (convert_data.py:34, 173-185):
```python
TIME_BIN_MS = 750.0  # One bin per stimulus presentation (250ms image + 500ms grey)
...
bin_duration = TIME_BIN_MS / 1000.0  # 0.75s
all_stim_starts = stim_start
all_stim_ends = all_stim_starts + bin_duration
ophys_bin_starts = np.searchsorted(ophys_ts, all_stim_starts, side='left')
ophys_bin_ends = np.searchsorted(ophys_ts, all_stim_ends, side='left')
dff_cumsum = np.cumsum(dff_valid, axis=0)
dff_cumsum = np.vstack([np.zeros((1, n_neurons), dtype=dff_cumsum.dtype), dff_cumsum])
```

**What this does:** Bins neural data into fixed 750ms windows aligned to each stimulus presentation onset. Each ophys frame falling within `[stim_start, stim_start+0.75)` contributes to that bin's mean. This downsamples the native ~11/31 Hz dF/F to one value per stimulus flash.

**Rating:** incorrect

**Note:** 750 ms is completely wrong

---

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:641: `'temporal_alignment_event': 'Stimulus presentation onset (each 750ms image flash)'`.

**Code** (convert_data.py:216-232):
```python
for trial_idx in np.where(trial_mask)[0]:
    tid = trial_ids[trial_idx]
    trial_stim_indices = np.where(stim_trials_id == tid)[0]
    if len(trial_stim_indices) == 0:
        continue
    n_bins = len(trial_stim_indices)
    neural_matrix = np.zeros((n_neurons, n_bins), dtype=np.float32)
    for bi, si in enumerate(trial_stim_indices):
        s, e = ophys_bin_starts[si], ophys_bin_ends[si]
        n_frames = e - s
        if n_frames > 0:
            neural_matrix[:, bi] = (dff_cumsum[e] - dff_cumsum[s]) / n_frames
```

**What this does:** Each trial's neural matrix uses bins aligned to the onset of every stimulus presentation belonging to that trial (looked up via `stim_trials_id`). The trial spans the stimulus presentations associated with the trial in the NWB; alignment is at stimulus onset, not at `change_time` specifically.

**Rating:** ok

**Note:** _(no note)_

---

## Q 3-a. What variables in the raw data is `output` *Image identity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:211: "image_name | output[0] | Categorical encoding (8 images) | stimulus_presentations | Forward-fill for omitted."

**Code** (convert_data.py:120-126, 320-336):
```python
stim = f['intervals'][stim_key]
stim_start = stim['start_time'][:]
stim_stop = stim['stop_time'][:]
stim_image_name = np.array([x.decode() if isinstance(x, bytes) else str(x) for x in stim['image_name'][:]])
stim_is_change = stim['is_change'][:]
stim_omitted = stim['omitted'][:]
stim_trials_id = stim['trials_id'][:]
...
def collect_all_image_names(active_exps, nwb_map):
    all_images = set()
    sample_exps = active_exps.head(min(10, len(active_exps)))
    for _, row in sample_exps.iterrows():
        nwb_path = nwb_map[row['ophys_experiment_id']]
        with h5py.File(nwb_path, 'r') as f:
            stim_key = find_stim_key(f)
            ...
            names = f['intervals'][stim_key]['image_name'][:]
            for n in names:
                name = n.decode() if isinstance(n, bytes) else str(n)
                if name != 'omitted':
                    all_images.add(name)
    return sorted(all_images)
```

**What this does:** Image identity is derived from the `image_name` column of the stimulus presentations table in NWB intervals. The global vocabulary is built from up to 10 sampled experiments (excluding `'omitted'`).

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `output` *Image identity*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:222: "Omitted stimuli: Forward-fill image identity from previous presentation."

**Code** (convert_data.py:206-247):
```python
img_to_idx = {name: i for i, name in enumerate(IMAGE_NAMES_GLOBAL)}
...
images = stim_image_name[trial_stim_indices].copy()
# Forward-fill omitted presentations
for bi in range(len(images)):
    if images[bi] == 'omitted':
        if bi > 0:
            images[bi] = images[bi - 1]
        else:
            for bj in range(bi + 1, len(images)):
                if images[bj] != 'omitted':
                    images[bi] = images[bj]
                    break

image_indices = np.array([img_to_idx.get(img, 0) for img in images], dtype=np.int64)
```

**What this does:** Forward-fills omitted-stimulus bins with the previous image (or backfills if the trial starts with `'omitted'`), then maps strings to integer codes via the global sorted image-name vocabulary; missing names fall back to 0.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `output` *Image identity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Per-presentation index `trial_stim_indices` is shared between neural and image_identity bins.

**Code** (convert_data.py:220-247):
```python
trial_stim_indices = np.where(stim_trials_id == tid)[0]
...
n_bins = len(trial_stim_indices)
neural_matrix = np.zeros((n_neurons, n_bins), dtype=np.float32)
...
images = stim_image_name[trial_stim_indices].copy()
...
image_indices = np.array([img_to_idx.get(img, 0) for img in images], dtype=np.int64)
```

**What this does:** Image name is indexed by the same `trial_stim_indices` used to build the neural matrix, so bin `bi` of the image-identity row corresponds to bin `bi` of the neural matrix.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *Image change* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:212: "is_change | output[1] | Binary (0/1) | stimulus_presentations | 1 at change flash only."

**Code** (convert_data.py:124, 249-250):
```python
stim_is_change = stim['is_change'][:]
...
change_flags = np.nan_to_num(stim_is_change[trial_stim_indices], nan=0).astype(np.int64)
```

**What this does:** Image change is derived directly from the `is_change` column of the stimulus presentations table, indexed per stimulus bin within each trial; NaNs are mapped to 0.

**Rating:** ok

**Note:** _(no note)_

---

## Q 4-b. What processing is involved in computing `output` *Image change*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:329: "Image change rate | ~7.5% of presentations | 7.5% | Match." Marked at the change flash only (the bin equal to one stimulus presentation).

**Code** (convert_data.py:249-250, 559-563):
```python
change_flags = np.nan_to_num(stim_is_change[trial_stim_indices], nan=0).astype(np.int64)
...
output_arr = np.stack([
    ot['image_identity'].astype(np.int64),
    ot['image_change'].astype(np.int64),
    ...
], axis=0)
```

**What this does:** Casts the boolean `is_change` per stimulus to int (0/1) with NaN→0; no smoothing or windowing — only the single change-flash bin is set to 1.

**Rating:** match

**Note:** _(no note)_

---

## Q 4-c. How is `output` *Image change* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Same per-presentation alignment as image identity / neural.

**Code** (convert_data.py:249-250):
```python
change_flags = np.nan_to_num(stim_is_change[trial_stim_indices], nan=0).astype(np.int64)
```

**What this does:** Image change uses the same `trial_stim_indices` per-stimulus indexing as the neural matrix bins, so bin `bi` matches.

**Rating:** ok

**Note:** _(no note)_

---

## Q 5-a. What variables in the raw data is `output` *Running speed* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:213: "running speed | output[2] | Average in 750ms bins, discretize to 5 percentile bins | running/speed in NWB | 10 Hz Butterworth filtered."

**Code** (convert_data.py:147-149):
```python
running_speed = f['processing']['running']['speed']['data'][:]
running_ts = f['processing']['running']['speed']['timestamps'][:]
```

**What this does:** Reads the (already filtered) running speed and timestamps from `processing/running/speed` in the NWB file.

**Rating:** match

**Note:** _(no note)_

---

## Q 5-b. What processing is involved in computing `output` *Running speed*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:224: "Discretization: Compute percentile bin edges across ALL valid time points in dataset (2-pass), then assign bins."

**Code** (convert_data.py:188-191, 252-258, 339-357, 540-541):
```python
run_bin_starts = np.searchsorted(running_ts, all_stim_starts, side='left')
run_bin_ends = np.searchsorted(running_ts, all_stim_ends, side='left')
run_cumsum = np.cumsum(running_speed)
run_cumsum = np.concatenate([[0], run_cumsum])
...
running_binned = np.zeros(n_bins, dtype=np.float32)
for bi, si in enumerate(trial_stim_indices):
    s, e = run_bin_starts[si], run_bin_ends[si]
    n_pts = e - s
    if n_pts > 0:
        running_binned[bi] = (run_cumsum[e] - run_cumsum[s]) / n_pts
...
def discretize_values(values, n_bins, bin_edges=None):
    if bin_edges is None:
        valid = values[~np.isnan(values)]
        percentiles = np.linspace(0, 100, n_bins + 1)
        bin_edges = np.percentile(valid, percentiles)
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf
    binned = np.digitize(values, bin_edges[1:-1]).astype(np.int64)
    binned = np.clip(binned, 0, n_bins - 1)
    return binned, bin_edges
...
running_disc, _ = discretize_values(ot['running_speed_raw'], N_PERCENTILE_BINS, running_bin_edges)
```

**What this does:** Averages running speed samples falling in each 750ms stimulus window (cumsum-based mean), then discretizes into 5 percentile bins computed globally across all sessions in pass 1.

**Rating:** incorrect

**Note:** same binning error cascade to all the variables

---

## Q 5-c. How is `output` *Running speed* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:218-219: All outputs are computed per stimulus presentation bin, sharing the same bin index space as `neural`.

**Code** (convert_data.py:179-181, 188-189, 254-258):
```python
ophys_bin_starts = np.searchsorted(ophys_ts, all_stim_starts, side='left')
ophys_bin_ends = np.searchsorted(ophys_ts, all_stim_ends, side='left')
...
run_bin_starts = np.searchsorted(running_ts, all_stim_starts, side='left')
run_bin_ends = np.searchsorted(running_ts, all_stim_ends, side='left')
...
for bi, si in enumerate(trial_stim_indices):
    s, e = run_bin_starts[si], run_bin_ends[si]
    n_pts = e - s
    if n_pts > 0:
        running_binned[bi] = (run_cumsum[e] - run_cumsum[s]) / n_pts
```

**What this does:** Both neural and running speed bins use the same `all_stim_starts`/`all_stim_ends` window list, indexed by `trial_stim_indices`, so each running bin corresponds to the matching neural bin in the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-a. What variables in the raw data is `output` *Pupil diameter* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:214: "pupil area → diameter | output[3] | 2*sqrt(area/pi), interpolate NaN... | pupil_tracking/area." CONVERSION_NOTES.md:199: "Use area → compute diameter, interpolate NaNs."

**Code** (convert_data.py:152-166):
```python
has_eye_tracking = 'EyeTracking' in f['acquisition']
if has_eye_tracking:
    pupil_area_raw = f['acquisition']['EyeTracking']['pupil_tracking']['area'][:]
    pupil_ts = f['acquisition']['EyeTracking']['pupil_tracking']['timestamps'][:]
    likely_blink = f['acquisition']['EyeTracking']['likely_blink']['data'][:].astype(bool)

    pupil_area = pupil_area_raw.copy().astype(float)
    pupil_area[likely_blink] = np.nan
    pupil_area[pupil_area <= 0] = np.nan
    pupil_diameter = 2.0 * np.sqrt(pupil_area / np.pi)
    pupil_diameter = interpolate_nans(pupil_diameter)
```

**What this does:** Loads pupil area, eye-tracking timestamps, and the `likely_blink` mask. Sets blink frames and non-positive areas to NaN, converts area to diameter via `2*sqrt(area/pi)`, then linearly interpolates NaNs.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 6-b. What processing is involved in computing `output` *Pupil diameter*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:223: "Pupil NaN handling: Linear interpolation for blink frames before computing diameter and averaging."

**Code** (convert_data.py:194-204, 263-269, 543-552):
```python
if has_eye_tracking and pupil_diameter is not None:
    pup_bin_starts = np.searchsorted(pupil_ts, all_stim_starts, side='left')
    pup_bin_ends = np.searchsorted(pupil_ts, all_stim_ends, side='left')
    pup_valid = ~np.isnan(pupil_diameter)
    pup_filled = np.where(pup_valid, pupil_diameter, 0.0)
    pup_cumsum = np.cumsum(pup_filled)
    pup_cumsum = np.concatenate([[0], pup_cumsum])
    pup_count_cumsum = np.cumsum(pup_valid.astype(np.float64))
    pup_count_cumsum = np.concatenate([[0], pup_count_cumsum])
...
pupil_binned = np.full(n_bins, np.nan, dtype=np.float32)
if has_eye_tracking and pupil_diameter is not None:
    for bi, si in enumerate(trial_stim_indices):
        s, e = pup_bin_starts[si], pup_bin_ends[si]
        n_valid = pup_count_cumsum[e] - pup_count_cumsum[s]
        if n_valid > 0:
            pupil_binned[bi] = (pup_cumsum[e] - pup_cumsum[s]) / n_valid
...
pupil_raw = ot['pupil_diameter_raw']
nan_mask = np.isnan(pupil_raw)
if nan_mask.all():
    pupil_disc = np.full(n_bins, N_PERCENTILE_BINS // 2, dtype=np.int64)  # middle bin
else:
    if nan_mask.any():
        pupil_raw = interpolate_nans(pupil_raw)
    pupil_disc, _ = discretize_values(pupil_raw, N_PERCENTILE_BINS, pupil_bin_edges)
```

**What this does:** After blink-aware NaN interpolation and area→diameter conversion, averages diameter samples per 750ms stimulus bin (skipping NaNs in the average). Any remaining NaN bins are interpolated, then discretized into 5 percentile bins using global edges from pass 1; all-NaN trials default to the middle bin.

**Rating:** match

**Note:** _(no note)_

---

## Q 6-c. How is `output` *Pupil diameter* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> Pupil bins use the same `all_stim_starts/ends` index as neural bins (same code structure as running speed).

**Code** (convert_data.py:194-196, 263-269):
```python
pup_bin_starts = np.searchsorted(pupil_ts, all_stim_starts, side='left')
pup_bin_ends = np.searchsorted(pupil_ts, all_stim_ends, side='left')
...
for bi, si in enumerate(trial_stim_indices):
    s, e = pup_bin_starts[si], pup_bin_ends[si]
    n_valid = pup_count_cumsum[e] - pup_count_cumsum[s]
    if n_valid > 0:
        pupil_binned[bi] = (pup_cumsum[e] - pup_cumsum[s]) / n_valid
```

**What this does:** Pupil bins are computed against the same per-stimulus-presentation windows as neural bins, indexed by the same `trial_stim_indices`. This aligns pupil bin `bi` to neural bin `bi` within each trial.

**Rating:** incorrect

**Note:** same error due to time bin definition

---

## Q 7-a. What variables in the raw data is `output` *Trial outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:215: "hit/miss/fa/cr | output[4] | Categorical (4 classes) | trials table | Static per trial."

**Code** (convert_data.py:135-138, 273-283):
```python
trial_hit = trials['hit'][:].astype(bool)
trial_miss = trials['miss'][:].astype(bool)
trial_fa = trials['false_alarm'][:].astype(bool)
trial_cr = trials['correct_reject'][:].astype(bool)
...
if trial_hit[trial_idx]:
    outcome = 0  # Hit
elif trial_miss[trial_idx]:
    outcome = 1  # Miss
elif trial_fa[trial_idx]:
    outcome = 2  # False Alarm
elif trial_cr[trial_idx]:
    outcome = 3  # Correct Rejection
else:
    outcome = 1  # Default to Miss
```

**What this does:** Pulls the four boolean outcome columns (`hit`, `miss`, `false_alarm`, `correct_reject`) from the NWB trials table.

**Rating:** match

**Note:** _(no note)_

---

## Q 7-b. What processing is involved in computing `output` *Trial outcome*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:613: `outcome_value_names = ['hit', 'miss', 'false_alarm', 'correct_rejection']`. Static per-trial value, replicated across time bins.

**Code** (convert_data.py:273-283, 557-563):
```python
if trial_hit[trial_idx]:
    outcome = 0  # Hit
elif trial_miss[trial_idx]:
    outcome = 1  # Miss
elif trial_fa[trial_idx]:
    outcome = 2  # False Alarm
elif trial_cr[trial_idx]:
    outcome = 3  # Correct Rejection
else:
    outcome = 1  # Default to Miss
...
output_arr = np.stack([
    ot['image_identity'].astype(np.int64),
    ot['image_change'].astype(np.int64),
    running_disc.astype(np.int64),
    pupil_disc.astype(np.int64),
    np.full(n_bins, ot['trial_outcome'], dtype=np.int64),
], axis=0)  # (5, n_bins)
```

**What this does:** Picks the first true outcome flag (with a fallback to Miss=1 if none is true), maps to integer code 0-3, and replicates the constant value across all `n_bins` time bins of the trial.

**Rating:** match

**Note:** _(no note)_

---

## Q 8. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:222-223: "Omitted stimuli: Forward-fill image identity from previous presentation"; "Pupil NaN handling: Linear interpolation for blink frames." CONVERSION_NOTES.md:529: sessions with `< 2 trials` skipped.

**Code** (convert_data.py:60-70, 110-118, 159-166, 236-247, 282-283, 545-552):
```python
def interpolate_nans(values):
    valid = ~np.isnan(values)
    if valid.sum() == 0:
        return values
    if valid.sum() == len(values):
        return values
    result = values.copy()
    x = np.arange(len(values))
    result[~valid] = np.interp(x[~valid], x[valid], values[valid])
    return result
...
if n_neurons == 0:
    print(f"  WARNING: Experiment {experiment_id} has 0 valid neurons, skipping")
    return None
...
stim_key = find_stim_key(f)
if stim_key is None:
    print(f"  WARNING: No stimulus presentations found for {experiment_id}, skipping")
    return None
...
pupil_area[likely_blink] = np.nan
pupil_area[pupil_area <= 0] = np.nan
pupil_diameter = 2.0 * np.sqrt(pupil_area / np.pi)
pupil_diameter = interpolate_nans(pupil_diameter)
...
# Forward-fill omitted images
for bi in range(len(images)):
    if images[bi] == 'omitted':
        ...
...
else:
    outcome = 1  # Default to Miss
...
nan_mask = np.isnan(pupil_raw)
if nan_mask.all():
    pupil_disc = np.full(n_bins, N_PERCENTILE_BINS // 2, dtype=np.int64)  # middle bin
else:
    if nan_mask.any():
        pupil_raw = interpolate_nans(pupil_raw)
```

**What this does:** Skips experiments with 0 valid ROIs or no stimulus presentations key, and trials with no associated stimuli. Sessions with < 2 valid trials are dropped. Pupil blinks/non-positive areas → NaN → linear interpolation; remaining NaN bins fall back to interpolation or the median bin. Omitted stimulus images are forward-filled (or backfilled). Missing/unknown image names map to code 0. Trials with none of the four outcome flags default to Miss.

**Rating:** match

**Note:** _(no note)_

---

## Q 9-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md / README.md, conversion_full_out.txt):
> conversion_full_out.txt: "Pass 1 completed in 261.6s ... Pass 2 completed in 246.6s ... Total elapsed time: 510.4s." Pass 1 (NWB load + running/pupil stats) and Pass 2 (full processing) are roughly equal and dominate runtime; saving the pickle takes 1.1s.

**Code** (convert_data.py:95-149, 480-505, 523-527):
```python
with h5py.File(nwb_path, 'r') as f:
    ...
    dff_data = f['processing']['ophys']['dff']['traces']['data'][:]
    ophys_ts = f['processing']['ophys']['dff']['traces']['timestamps'][:]
    ...
    running_speed = f['processing']['running']['speed']['data'][:]
    running_ts = f['processing']['running']['speed']['timestamps'][:]
    ...
    pupil_area_raw = f['acquisition']['EyeTracking']['pupil_tracking']['area'][:]
...
for idx, (_, row) in enumerate(active_exps.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = nwb_map[eid]
    stats = process_experiment(nwb_path, row, collect_stats_only=True)
...
for idx, (_, row) in enumerate(active_exps.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = nwb_map[eid]
    result = process_experiment(nwb_path, row, collect_stats_only=False)
```

**What this does:** The bottleneck is opening each NWB file and reading its dF/F, eye tracking, running speed, and trials arrays. Because the code does this twice (Pass 1 for stats, Pass 2 for full conversion), every file is opened and read fully twice; the per-trial processing inside Python is comparatively cheap.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:247-249: "Optimizations: Cumulative sum-based bin averaging... np.searchsorted for efficient bin boundary finding... Sample 10 experiments for image name collection."

**Code** (convert_data.py:216-247):
```python
for trial_idx in np.where(trial_mask)[0]:
    ...
    for bi, si in enumerate(trial_stim_indices):
        s, e = ophys_bin_starts[si], ophys_bin_ends[si]
        n_frames = e - s
        if n_frames > 0:
            neural_matrix[:, bi] = (dff_cumsum[e] - dff_cumsum[s]) / n_frames
    ...
    for bi in range(len(images)):
        if images[bi] == 'omitted':
            ...
    image_indices = np.array([img_to_idx.get(img, 0) for img in images], dtype=np.int64)
```

**What this does:** Per-trial Python loops remain over each bin to fill the neural, running, and pupil per-bin means and to forward-fill omitted images and map image strings. These could be expressed as fully vectorized indexing/gather operations across all bins at once.

**Rating:** ok

**Note:** _(no note)_

---

## Q 9-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:243-245: Two-pass approach: "Pass 1: Collect running speed and pupil statistics... Pass 2: Full conversion."

**Code** (convert_data.py:480-488, 523-527):
```python
for idx, (_, row) in enumerate(active_exps.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = nwb_map[eid]
    stats = process_experiment(nwb_path, row, collect_stats_only=True)
    ...
for idx, (_, row) in enumerate(active_exps.iterrows()):
    eid = row['ophys_experiment_id']
    nwb_path = nwb_map[eid]
    result = process_experiment(nwb_path, row, collect_stats_only=False)
```

**What this does:** Each NWB file is fully opened and parsed (including dF/F load) twice — once in Pass 1 to compute global percentile bin edges for running and pupil, and again in Pass 2 to produce the per-trial output. Pass 1 even computes neural means it doesn't use, since `collect_stats_only` only short-circuits the storage step.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> (none)

**Code** (convert_data.py:226-232, 285-286):
```python
neural_matrix = np.zeros((n_neurons, n_bins), dtype=np.float32)
for bi, si in enumerate(trial_stim_indices):
    s, e = ophys_bin_starts[si], ophys_bin_ends[si]
    n_frames = e - s
    if n_frames > 0:
        neural_matrix[:, bi] = (dff_cumsum[e] - dff_cumsum[s]) / n_frames
...
if collect_stats_only:
    continue
```

**What this does:** During Pass 1 (`collect_stats_only=True`), the code still computes `neural_matrix`, image indices, change flags, pupil binning, and outcome — only the per-trial append is skipped. These computations are discarded each Pass 1 trial.

**Rating:** concerning

**Note:** _(no note)_

---

## Q 9-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:247-248: "Cumulative sum-based bin averaging (avoids per-bin boolean masking)... Sample 10 experiments for image name collection (not all 202)."

**Code** (convert_data.py:95, 183-185, 320-336):
```python
with h5py.File(nwb_path, 'r') as f:
    ...
    dff_cumsum = np.cumsum(dff_valid, axis=0)
    dff_cumsum = np.vstack([np.zeros((1, n_neurons), dtype=dff_cumsum.dtype), dff_cumsum])
...
def collect_all_image_names(active_exps, nwb_map):
    all_images = set()
    sample_exps = active_exps.head(min(10, len(active_exps)))
    for _, row in sample_exps.iterrows():
        ...
```

**What this does:** Each NWB file is opened inside a `with` block so its full-session arrays are released after the experiment is processed. Only per-trial slices (small) are kept in `all_sessions_neural`. Cumulative-sum buffers replace per-bin boolean masks. The image vocabulary is built from at most 10 sampled NWBs to avoid scanning the whole dataset.

**Rating:** match

**Note:** _(no note)_

---
