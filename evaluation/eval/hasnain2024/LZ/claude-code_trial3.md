# hasnain2024 — claude-code / trial3

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/hasnain2024/claude/2026-03-20__17-31-10_trial3/verifier/snapshot/`

Outputs identified (K=6): lick_direction, behavioral_context, outcome, tongue_velocity, paw_velocity, motion_energy

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Data files are a mix of HDF5 (v7.3) and MATLAB v5 format" (line 76); "Each session: `data_structure_ANM_DATE.mat` + `motionEnergy_ANM_DATE.mat`" (line 74)

**Code** (convert_data.py:42-89, 146-153, 941-961):
```python
EPHYS_SESSIONS = [
    ('data/Ephys_Behavior', 'JEB6', '2021-04-18', [2]),
    ...
    ('data/RandomizedDelay_Ephys_Behavior', 'JEB24', '2023-11-03', [1]),
]

def load_mat_file(filepath):
    try:
        f = h5py.File(filepath, 'r')
        return f, 'h5'
    except Exception:
        mat = scipy.io.loadmat(filepath, squeeze_me=False)
        return mat, 'v5'

for sess_idx, (dirpath, animal, date, probes) in enumerate(sessions):
    result = process_session(dirpath, animal, date, probes, ...)
```

**What this does:** A hardcoded `EPHYS_SESSIONS` list of 44 (directory, animal, date, probe_numbers) tuples is iterated by `main()`. Each session's `.mat` is loaded by `load_mat_file`, which tries HDF5 v7.3 first then falls back to scipy v5 loader.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Subjects | 14 (EKH1, EKH3, JEB6, JEB7, JEB11, JEB12, JEB13, JEB14, JEB15, JEB19, JEB23, JEB24, JGR2, JGR3)" (line 90)

**Code** (convert_data.py:970-972, 986-987):
```python
unique_subjects = sorted(set(all_animals))
subject_idx = np.array([unique_subjects.index(a) for a in all_animals])
...
'subjects': unique_subjects,
'subject_idx': subject_idx,
```

**What this does:** Each session contributes its `animal` name (second element of the session tuple). `unique_subjects` is the sorted set of animal names; `subject_idx` maps each session to its subject index.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Sessions (total) | 44 (25 standard + 19 randomized)" (line 92)

**Code** (convert_data.py:941-961):
```python
for sess_idx, (dirpath, animal, date, probes) in enumerate(sessions):
    result = process_session(dirpath, animal, date, probes, time_axis, edges, ...)
    if result is None:
        continue
    all_neural.append(result['neural'])
    all_input.append(result['input'])
    all_output.append(result['output'])
    all_animals.append(animal)
    session_info.append({'animal': animal, 'date': date, ...})
```

**What this does:** Each entry of `EPHYS_SESSIONS` (animal+date+directory) defines one session. Per-session results are appended into the top-level lists; `session_info` records animal/date/directory for each.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> "(n_neurons, n_timepoints) per trial" (line 192)

**Code** (convert_data.py:646, 664, 720-727):
```python
ntrials = get_ntrials(data, fmt)
...
align_times = get_event_times(data, fmt, ALIGN_EVENT)
...
trialdat_valid = trialdat[:, :, valid_trial_indices]
neural_trials = []
for t_idx in range(len(valid_trial_indices)):
    neural_trials.append(trialdat_valid[:, :, t_idx].T.astype(np.float32))
```

**What this does:** Trial count comes from `obj.bp.Ntrials`; `get_event_times` returns one go-cue time per trial; spikes are tagged with their trial number (`clu['trial']`) which is used to bin per-trial. Each retained trial yields a `(n_neurons, n_timepoints)` matrix appended to `neural_trials`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Trial filter: exclude stim.enable, early lick trials" (line 133); "Sessions need >= 10 units after filtering" (line 148)

**Code** (convert_data.py:666-690):
```python
valid_trials = ~stim_enable & ~early
valid_trials &= ~np.isnan(align_times) & (align_times > 0)
valid_trial_indices = np.where(valid_trials)[0]
...
if all_clusters:
    max_spike_trial = max(int(np.max(c['trial'])) for c in all_clusters if len(c['trial']) > 0)
    beyond = np.sum(valid_trial_indices >= max_spike_trial)
    if beyond > 0:
        valid_trial_indices = valid_trial_indices[valid_trial_indices < max_spike_trial]
```

**What this does:** Trials with optogenetic stim, early licks, missing/non-positive go-cue times, or trial number beyond the last recorded spike are dropped. Sessions with <2 valid trials or <10 units are skipped entirely (lines 692-702).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "obj.clu spike times | neural | Bin, smooth, filter by quality+lowFR" (line 192)

**Code** (convert_data.py:187-225, 663-664, 706):
```python
def get_clusters(data, fmt, probe_idx):
    ...
    quality = h5_deref_string(f, q_ref).strip().lower()
    if quality in EXCLUDE_QUALITIES: continue
    trialtm = f[trialtm_ref][:].flatten()
    trial = f[trial_ref][:].flatten().astype(int)
    clusters.append({'trialtm': trialtm, 'trial': trial, 'quality': quality})
...
align_times = get_event_times(data, fmt, ALIGN_EVENT)
trialdat = bin_and_smooth_spikes(all_clusters, ntrials, align_times, time_axis, edges)
```

**What this does:** Neural data is derived from `obj.clu[probe].trialtm` (per-spike within-trial times), `obj.clu[probe].trial` (trial indices), `obj.clu[probe].quality` (string label), and `obj.bp.ev.goCue` (alignment event times).

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Bin spikes into time bins, divide by dt for rate, smooth with causal Gaussian kernel (N=15, reflect boundary)" (line 130)

**Code** (convert_data.py:392-424):
```python
def bin_and_smooth_spikes(clusters, ntrials, align_times, time_axis, edges):
    trialdat = np.zeros((n_time, n_neurons, ntrials), dtype=np.float32)
    for i, clu in enumerate(clusters):
        for j in range(ntrials):
            spike_mask = trial == (j + 1)
            aligned_times = trialtm[spike_mask] - align_times[j]
            counts = np.histogram(aligned_times, bins=edges)[0]
            rate = counts.astype(np.float64) / DT
            smoothed = causal_gaussian_smooth(rate, SMOOTH_N, SMOOTH_BC)
            trialdat[:, i, j] = smoothed.astype(np.float32)
    return trialdat
```

**What this does:** Per neuron, per trial: spikes are aligned to the trial's go cue, histogrammed into 10 ms bins on the [-2.5, 2.5] s axis, divided by `DT` to get firing rate, then smoothed with a causal Gaussian (N=15, reflect boundary).

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Quality filter: exclude 'garbage', 'noisy', 'real?', 'gabrga'" (line 141); "Low FR filter: exclude neurons with mean FR <= 1 Hz" (line 142)

**Code** (convert_data.py:38, 211-212, 427-439, 698-702):
```python
EXCLUDE_QUALITIES = {'garbage', 'gabrga', 'noisy', 'real?'}
...
if quality in EXCLUDE_QUALITIES:
    continue
...
def remove_low_fr_neurons(trialdat, clusters):
    mean_frs = np.nanmean(np.nanmean(trialdat, axis=2), axis=0)
    keep = mean_frs > LOW_FR_THRESHOLD
    trialdat_filtered = trialdat[:, keep, :]
    clusters_filtered = [c for c, k in zip(clusters, keep) if k]
    return trialdat_filtered, clusters_filtered, keep
...
if len(all_clusters) < MIN_UNITS: ... return None
```

**What this does:** Two-stage neuron filter: (1) exclude clusters whose `quality` string is in the excluded set; (2) drop neurons with mean firing rate <=1 Hz across trials/time. Sessions with fewer than 10 surviving units are dropped.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Align to goCue event" (line 128)

**Code** (convert_data.py:28, 663-664, 414-417):
```python
ALIGN_EVENT = 'goCue'
...
align_times = get_event_times(data, fmt, ALIGN_EVENT)
...
aligned_times = trialtm[spike_mask] - align_times[j]
counts = np.histogram(aligned_times, bins=edges)[0]
```

**What this does:** Per-trial go-cue times are read from `obj.bp.ev.goCue` and subtracted from each spike's within-trial time before histogramming, placing t=0 at the go cue.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Time bin: dt = 1/100 = 10ms" (line 202); "Time range: -2.5 to 2.5 s from goCue" (line 203)

**Code** (convert_data.py:29-31, 129-133, 416-422):
```python
TMIN = -2.5
TMAX = 2.5
DT = 1.0 / 100  # 10 ms time bins
...
def compute_time_axis():
    edges = np.arange(TMIN, TMAX + DT/2, DT)
    time_axis = edges[:-1] + DT / 2
    return time_axis, edges
...
counts = np.histogram(aligned_times, bins=edges)[0]
rate = counts.astype(np.float64) / DT
```

**What this does:** A fixed 10 ms-bin edges array spans -2.5 to 2.5 s; bin centers form the time axis (500 bins). Spike counts per bin are converted to a rate (counts/DT).

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_go_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:193 — `| time from goCue | input[0] | Continuous time axis | N/A | Same time axis for all trials: tmin:dt:tmax centered |`
> CONVERSION_NOTES.md:58 — `- **Time range**: tmin=-2.5, tmax=2.5 (from goCue)`
> README.md:27 — `` - `input`: List of 44 sessions, each a list of trials, each (1, 500) array of time from go cue ``
> README.md:33 — `` - `input_names`: `['time_from_go_cue']` ``

**Code** (convert_data.py:28-31, 129-133):
```python
ALIGN_EVENT = 'goCue'
TMIN = -2.5  # seconds
TMAX = 2.5   # seconds
DT = 1.0 / 100  # 10 ms time bins

def compute_time_axis():
    """Compute time axis matching getSeq.m: edges + dt/2, drop last."""
    edges = np.arange(TMIN, TMAX + DT/2, DT)
    time_axis = edges[:-1] + DT / 2
    return time_axis, edges
```

**What this does:** The trial produces a single input named `time_from_go_cue`. It is not read from any raw data field directly; it is a constructed time axis defined by the constants `TMIN`, `TMAX`, and `DT`. The raw variable it corresponds to is the go-cue event time `obj.bp.ev.goCue` (read elsewhere as `align_times` via `get_event_times(data, fmt, ALIGN_EVENT)`, convert_data.py:182-184, 665), which defines t=0 for the axis.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_go_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:193 — `| time from goCue | input[0] | Continuous time axis | N/A | Same time axis for all trials: tmin:dt:tmax centered |`
> CONVERSION_NOTES.md:278 — `| time_from_go_cue range | [-2.5, 2.5] |`
> CONVERSION_NOTES.md:367 — `4. **Input time axis**: All sessions have identical correct time axis [-2.495, 2.495] s, 500 bins.`
> README.md:20 — `| Time bins | 500 (10ms bins, -2.5 to 2.5s from go cue) |`

**Code** (convert_data.py:129-133, 792-799):
```python
def compute_time_axis():
    """Compute time axis matching getSeq.m: edges + dt/2, drop last."""
    edges = np.arange(TMIN, TMAX + DT/2, DT)
    time_axis = edges[:-1] + DT / 2
    return time_axis, edges

    # Build input and output lists
    input_trials = []
    output_trials = []

    for t_idx in range(len(valid_trial_indices)):
        # Input: time from go cue (continuous, same for all trials)
        input_data = time_axis.astype(np.float32).reshape(1, -1)
        input_trials.append(input_data)
```

**What this does:** Bin edges are built as `np.arange(-2.5, 2.5 + DT/2, DT)` and the axis is taken as the bin centers (`edges[:-1] + DT/2`), giving 500 values from -2.495 to 2.495 s. The identical `time_axis` is cast to float32, reshaped to `(1, 500)`, and appended once per valid trial, so every trial in every session carries the same input array.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_go_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:128-129 — `- Align to goCue event` / `- Time window: -2.5 to 2.5 s from goCue`
> CONVERSION_NOTES.md:40 — `| alignSpikes | DataLoadingScripts/alignSpikes.m | PROCESSING | Align spike times to event (goCue): trialtm_aligned = trialtm - event_time |`
> CONVERSION_NOTES.md:365 — `2. **Data shapes**: All sessions have correct shapes (n_neurons x 500 neural, 1x500 input, 6x500 output).`
> README.md:58 — `10. Align all data to go cue onset`

**Code** (convert_data.py:406-421, 796-799):
```python
    for i, clu in enumerate(clusters):
        trialtm = clu['trialtm']
        trial = clu['trial']

        # Align spike times: trialtm_aligned = trialtm - align_event_time
        for j in range(ntrials):
            trial_num = j + 1  # 1-indexed
            spike_mask = trial == trial_num
            if not np.any(spike_mask):
                continue

            aligned_times = trialtm[spike_mask] - align_times[j]

            # Bin spikes
            counts = np.histogram(aligned_times, bins=edges)[0]
```

**What this does:** The same `edges` array that defines `time_axis` is used as the histogram bins for the go-cue-subtracted spike times, so neural bin *k* and input sample *k* refer to the same offset relative to the go cue. Both arrays have 500 timepoints per trial, and the input is emitted once per valid trial alongside the neural array (convert_data.py:796-799).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *lick_direction* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "obj.bp.R/L | output[0]: lick_direction | L=0, R=1" (line 194); "lick_direction = instruction direction" (line 229)

**Code** (convert_data.py:652-653, 729-737, 805):
```python
R = get_bp_field(data, fmt, 'R').astype(bool)
L = get_bp_field(data, fmt, 'L').astype(bool)
...
R_valid = R[valid_trial_indices]
...
lick_direction = R_valid.astype(np.float32)
...
out[0, :] = int(lick_direction[t_idx])
```

**What this does:** `obj.bp.R` (1 = right-trial) is taken as the per-trial lick direction (L=0, R=1) and broadcast across all timepoints in the output.

**Rating:** incorrect

**Note:** _(no note)_---

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "['left', 'right']" (line 994); class distribution "left: 49.6% | right: 50.4%" (line 346)

**Code** (convert_data.py:737, 802-805, 994):
```python
lick_direction = R_valid.astype(np.float32)
...
out = np.zeros((6, len(time_axis)), dtype=np.int64)
out[0, :] = int(lick_direction[t_idx])
...
['left', 'right'],           # lick_direction: 0=left, 1=right
```

**What this does:** Already a 0/1 boolean (R vs not-R); cast to int and tiled along the time axis. No further discretization.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-a. What variables in the raw data is `output` *context* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "obj.bp.autowater | output[1]: behavioral_context | WC(aw=1)=0, DR(aw=0)=1" (line 195)

**Code** (convert_data.py:654, 733, 740, 806):
```python
autowater = get_bp_field(data, fmt, 'autowater').astype(bool)
...
autowater_valid = autowater[valid_trial_indices]
...
behavioral_context = (~autowater_valid).astype(np.float32)
...
out[1, :] = int(behavioral_context[t_idx])
```

**What this does:** Read `obj.bp.autowater`; invert it so that DR (autowater=0) maps to 1 and WC (autowater=1) maps to 0.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *context*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "['WC', 'DR']" (line 995)

**Code** (convert_data.py:740, 806):
```python
behavioral_context = (~autowater_valid).astype(np.float32)
...
out[1, :] = int(behavioral_context[t_idx])
```

**What this does:** Boolean inversion of `autowater`; one value per trial broadcast across the time axis.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "obj.bp.hit | output[2]: outcome | incorrect(miss/no)=0, correct(hit)=1" (line 196)

**Code** (convert_data.py:650, 729, 743, 807):
```python
hit = get_bp_field(data, fmt, 'hit').astype(bool)
...
hit_valid = hit[valid_trial_indices]
...
outcome = hit_valid.astype(np.float32)
...
out[2, :] = int(outcome[t_idx])
```

**What this does:** `obj.bp.hit` is read directly as the per-trial correctness signal (1 = correct, 0 = miss/no).

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "['incorrect', 'correct']" (line 996)

**Code** (convert_data.py:743, 807):
```python
outcome = hit_valid.astype(np.float32)
...
out[2, :] = int(outcome[t_idx])
```

**What this does:** Already binary; cast to int and tiled across time bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "DLC tongue velocity | output[3]: tongue_velocity ... Speed = sqrt(xvel^2+yvel^2) from jaw side cam" (line 197)

**Code** (convert_data.py:752-757, 442-521):
```python
tongue_speed = extract_velocity_from_traj(
    data, fmt, view=0, feat_name='tongue',
    ntrials=ntrials, align_times=align_times,
    time_axis=time_axis, vidshift=vidshift,
)
...
xpos = ts[feat_idx, 0, :]
ypos = ts[feat_idx, 1, :]
...
xvel = np.gradient(xpos_smooth)
yvel = np.gradient(ypos_smooth)
...
spd = np.sqrt(xvel**2 + yvel**2)
```

**What this does:** Reads the `tongue` DLC feature from the side-camera (`view=0`) `obj.traj` data, takes x/y trajectories, computes per-frame velocity via `np.gradient`, then speed = sqrt(xvel^2+yvel^2). NaN frames (tongue not visible) get velocity 0.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize by session 50th pctile" (line 197)

**Code** (convert_data.py:531-535, 616-623, 784-788, 808):
```python
interpolated = np.interp(time_axis, aligned_ft, spd)
speed[:, trial_idx] = interpolated.astype(np.float32)
...
def discretize_time_series(values, threshold):
    if threshold < 1e-10:
        threshold = 1e-10
    return (values >= threshold).astype(np.float32)
...
tongue_thresh = np.nanpercentile(tongue_speed_valid, 50)
...
tongue_disc = discretize_time_series(tongue_speed_valid, tongue_thresh)
...
out[3, :] = tongue_disc[:, t_idx].astype(np.int64)
```

**What this does:** Velocity time series is interpolated onto the neural 10 ms time axis, then thresholded by the session-wide 50th percentile (>= median => 1, else 0).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 7-d. How is `output` *tongue_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Video offset: 0.5 sec subtracted from frame times for synchronization (or computed via bitcode)" (line 63); "DLC kinematics: interpolated from video time to neural time axis, video offset subtracted (0.5s or computed via bitcode)" (line 135)

**Code** (convert_data.py:350-385, 442-474, 531-535, 747-755):
```python
def find_video_offset(data, fmt):
    # vidshift = mode(sglx.bitcode.bitstart) / sglx.fs - mode(bp.ev.bitStart)
    ...
    sglx_bitstart = bitcode['bitstart'][:].flatten()
    fs = float(sglx['fs'][0, 0])
    vid_offset = np.nanmedian(sglx_bitstart) / fs
    bp_offset = np.nanmedian(bp_bitstart[bp_bitstart > 0])
    return vid_offset - bp_offset
...
def extract_velocity_from_traj(data, fmt, view, feat_name, ntrials, align_times, time_axis, vidshift):
    ...
    ft_offset = vidshift  # (or 0.5 fallback if frame_times missing)
    aligned_ft = frame_times - ft_offset - align_times[trial_idx]
    ...
    interpolated = np.interp(time_axis, aligned_ft, spd)
    speed[:, trial_idx] = interpolated.astype(np.float32)
...
vidshift = find_video_offset(data, fmt)
tongue_speed = extract_velocity_from_traj(
    data, fmt, view=0, feat_name='tongue',
    ntrials=ntrials, align_times=align_times,
    time_axis=time_axis, vidshift=vidshift,
)
```

**What this does:** A session-wide `vidshift` is computed from `obj.sglx.bitcode.bitstart/fs` minus `obj.bp.ev.bitStart` (fallback 0.5 s). For each trial, the side-cam `frameTimes` are corrected by `vidshift` and the trial's `goCue` time, then the per-frame speed is `np.interp`-ed onto the neural `time_axis` (10 ms bins, [-2.5, 2.5] s).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "DLC paw velocity ... From bottom cam top_paw" (line 198)

**Code** (convert_data.py:761-767):
```python
paw_speed = extract_velocity_from_traj(
    data, fmt, view=1, feat_name='top_paw',
    ntrials=ntrials, align_times=align_times,
    time_axis=time_axis, vidshift=vidshift,
)
paw_speed_valid = paw_speed[:, valid_trial_indices]
```

**What this does:** Same `extract_velocity_from_traj` pipeline as tongue, but using the bottom-camera (`view=1`) `top_paw` DLC feature; positions are smoothed (N=21 reflect), velocity = gradient, baseline (median velocity) subtracted, speed = sqrt(xvel^2 + yvel^2).

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize by session 50th pctile" (line 198); paw_velocity dist "low=0.500, high=0.500" (line 283)

**Code** (convert_data.py:498-513, 785, 789, 809):
```python
xpos_smooth = causal_gaussian_smooth(xpos, 21, 'reflect')
ypos_smooth = causal_gaussian_smooth(ypos, 21, 'reflect')
xvel = np.gradient(xpos_smooth)
yvel = np.gradient(ypos_smooth)
xvel = xvel - np.nanmedian(xvel)
yvel = yvel - np.nanmedian(yvel)
...
paw_thresh = np.nanpercentile(paw_speed_valid, 50)
paw_disc = discretize_time_series(paw_speed_valid, paw_thresh)
...
out[4, :] = paw_disc[:, t_idx].astype(np.int64)
```

**What this does:** Position is smoothed (causal Gaussian N=21), gradient gives velocity, baseline (median) subtracted; speed interpolated to neural axis; binarized at session 50th percentile.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-d. How is `output` *paw_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "DLC kinematics: interpolated from video time to neural time axis, video offset subtracted (0.5s or computed via bitcode)" (line 135)

**Code** (convert_data.py:442-474, 531-535, 747, 761-766):
```python
def extract_velocity_from_traj(data, fmt, view, feat_name, ntrials, align_times, time_axis, vidshift):
    ...
    ts, frame_times, feat_names = get_traj_data(data, fmt, view, trial_idx)
    ...
    ft_offset = vidshift  # (or 0.5 fallback if frame_times missing)
    # Align frame times to goCue
    aligned_ft = frame_times - ft_offset - align_times[trial_idx]
    ...
    interpolated = np.interp(time_axis, aligned_ft, spd)
    speed[:, trial_idx] = interpolated.astype(np.float32)
...
vidshift = find_video_offset(data, fmt)
...
paw_speed = extract_velocity_from_traj(
    data, fmt, view=1, feat_name='top_paw',
    ntrials=ntrials, align_times=align_times,
    time_axis=time_axis, vidshift=vidshift,
)
```

**What this does:** Bottom-cam (`view=1`) `frameTimes` for each trial are shifted by the session `vidshift` (computed from `bitcode.bitstart/fs` minus `bp.ev.bitStart`) and the trial's `goCue` time, then the per-frame paw speed is linearly interpolated (`np.interp`) onto the neural `time_axis` (10 ms bins, [-2.5, 2.5] s).

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Motion energy: Loaded from separate files, interpolated to neural time axis at 400Hz original rate" (line 64)

**Code** (convert_data.py:301-344, 772):
```python
def load_motion_energy(dirpath, animal, date):
    me_file = os.path.join(dirpath, f'motionEnergy_{animal}_{date}.mat')
    if not os.path.exists(me_file):
        return None, None
    me_mat = scipy.io.loadmat(me_file, squeeze_me=False)
    me_raw = me_mat['me']
    ...
    trial_me = []
    for i in range(me_data.shape[0]):
        elem = me_data[i, 0] if me_data.ndim == 2 else me_data[i]
        trial_me.append(elem.flatten().astype(np.float64))
    return trial_me, me_thresh
...
me_data, me_thresh = load_motion_energy(dirpath, animal, date)
```

**What this does:** Reads a separate `motionEnergy_<animal>_<date>.mat`, robust to several struct/cell layouts, returning a per-trial list of 1D ME time series.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Discretize by session 50th pctile" (line 199)

**Code** (convert_data.py:557-598, 786, 790, 810):
```python
def interpolate_motion_energy(me_data, ntrials, data, fmt, align_times, time_axis, vidshift):
    ...
    aligned_ft = frame_times - ft_offset - align_times[trial_idx]
    n_frames = min(len(me_trial), len(aligned_ft))
    me_interp[:, trial_idx] = np.interp(
        time_axis, aligned_ft[:n_frames], me_trial[:n_frames]
    ).astype(np.float32)
...
me_thresh_50 = np.nanpercentile(me_valid, 50)
me_disc = discretize_time_series(me_valid, me_thresh_50)
...
out[5, :] = me_disc[:, t_idx].astype(np.int64)
```

**What this does:** ME is aligned to go cue using video frame times (offset `vidshift`), interpolated onto the neural time axis, then binarized at the session 50th percentile.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Motion energy: Loaded from separate files, interpolated to neural time axis at 400Hz original rate" (line 64); "Motion energy: loaded from separate files, interpolated to neural time axis, aligned to goCue" (line 134)

**Code** (convert_data.py:557-598, 747, 774-776):
```python
def interpolate_motion_energy(me_data, ntrials, data, fmt, align_times, time_axis, vidshift):
    ...
    for trial_idx in range(ntrials):
        ...
        ts, frame_times, _ = get_traj_data(data, fmt, 0, trial_idx)  # side cam
        if len(frame_times) == 0 or np.all(np.isnan(frame_times)):
            frame_times = np.arange(len(me_trial)) / 400.0
            ft_offset = 0.5
        else:
            ft_offset = vidshift
        # Align to goCue
        aligned_ft = frame_times - ft_offset - align_times[trial_idx]
        n_frames = min(len(me_trial), len(aligned_ft))
        me_interp[:, trial_idx] = np.interp(
            time_axis, aligned_ft[:n_frames], me_trial[:n_frames]
        ).astype(np.float32)
...
vidshift = find_video_offset(data, fmt)
...
me_interp = interpolate_motion_energy(
    me_data, ntrials, data, fmt, align_times, time_axis, vidshift
)
```

**What this does:** Motion energy is paired with side-cam (`view=0`) `frameTimes`; those are shifted by the session `vidshift` (or 0.5 s fallback) and the per-trial `goCue` time, then `np.interp` resamples the ME signal onto the neural `time_axis` (10 ms bins, [-2.5, 2.5] s). If `frameTimes` are missing, synthetic times at 400 Hz are used.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Session 36 ... 28 trials with zero neural data. Recording likely ended before these trials." (line 354); "Session 43 ... 33 trials" (line 355)

**Code** (convert_data.py:638-640, 658-661, 683-690, 778-779, 540-552):
```python
if not os.path.exists(filepath):
    print(f"  WARNING: File not found: {filepath}")
    return None
...
try:
    stim_enable = get_bp_field(data, fmt, 'stim.enable').astype(bool)
except Exception:
    stim_enable = np.zeros(ntrials, dtype=bool)
...
max_spike_trial = max(int(np.max(c['trial'])) for c in all_clusters if len(c['trial']) > 0)
beyond = np.sum(valid_trial_indices >= max_spike_trial)
if beyond > 0:
    valid_trial_indices = valid_trial_indices[valid_trial_indices < max_spike_trial]
...
else:
    me_valid = np.zeros((len(time_axis), len(valid_trial_indices)), dtype=np.float32)
```

**What this does:** Missing files / fields raise warnings or fall back to defaults (zeros). Trials beyond the last recorded spike are dropped. Missing ME files yield zero arrays. NaN velocities/ME are nearest-filled; all-NaN columns -> zero.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Total: 269 seconds (~6.1s/session average)" (line 332); per-session prints "Spike binning", "Tongue velocity", "Paw velocity", "Motion energy" (lines 705-780)

**Code** (convert_data.py:705, 752-780):
```python
t1 = time.time()
trialdat = bin_and_smooth_spikes(...)
print(f"    Spike binning: {time.time()-t1:.1f}s")
...
t2 = time.time(); tongue_speed = extract_velocity_from_traj(...)
print(f"    Tongue velocity: {time.time()-t2:.1f}s")
t3 = time.time(); paw_speed = extract_velocity_from_traj(...)
print(f"    Paw velocity: {time.time()-t3:.1f}s")
t4 = time.time(); me_data, me_thresh = load_motion_energy(...)
...
print(f"    Motion energy: {time.time()-t4:.1f}s")
```

**What this does:** Code times four blocks per session: spike binning + smoothing, tongue velocity extraction, paw velocity extraction, and motion energy loading/interpolation.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Spike binning loops over neurons and trials (vectorized with np.histogram)" (line 257); "DLC extraction loops over trials (necessary due to variable frame times)" (line 258)

**Code** (convert_data.py:403-422, 450-493, 544-552):
```python
for i, clu in enumerate(clusters):
    for j in range(ntrials):
        ...
        counts = np.histogram(aligned_times, bins=edges)[0]
        rate = counts.astype(np.float64) / DT
        smoothed = causal_gaussian_smooth(rate, SMOOTH_N, SMOOTH_BC)
        trialdat[:, i, j] = smoothed.astype(np.float32)
...
for trial_idx in range(ntrials):
    try:
        ts, frame_times, feat_names = get_traj_data(data, fmt, view, trial_idx)
    ...
for t in range(ntrials):
    col = speed[:, t]
    nan_mask = np.isnan(col)
    if np.any(nan_mask) and not np.all(nan_mask):
        valid = np.where(~nan_mask)[0]
        for idx in np.where(nan_mask)[0]:
            nearest = valid[np.argmin(np.abs(valid - idx))]
            col[idx] = col[nearest]
```

**What this does:** Nested per-neuron x per-trial loops in spike binning; per-trial loops in velocity/ME extraction; explicit per-NaN inner loops for nearest-neighbor fill.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 11-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:557-598, 442-554, 752-766):
```python
def interpolate_motion_energy(me_data, ntrials, data, fmt, align_times, time_axis, vidshift):
    ...
    ts, frame_times, _ = get_traj_data(data, fmt, 0, trial_idx)  # side cam
...
tongue_speed = extract_velocity_from_traj(data, fmt, view=0, feat_name='tongue', ...)
paw_speed = extract_velocity_from_traj(data, fmt, view=1, feat_name='top_paw', ...)
```

**What this does:** `get_traj_data` is called once per trial inside the tongue extractor (view=0), again inside the paw extractor (view=1), and again inside the ME interpolator (view=0) — re-parsing feature names and HDF5 references each time. `causal_gaussian_smooth` rebuilds its kernel on every call.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:782-790, 838-909):
```python
tongue_thresh = np.nanpercentile(tongue_speed_valid, 50)
paw_thresh = np.nanpercentile(paw_speed_valid, 50)
me_thresh_50 = np.nanpercentile(me_valid, 50)
tongue_disc = discretize_time_series(tongue_speed_valid, tongue_thresh)
...
def generate_processing_plots(...):
    ...
    fig.savefig(f'processing_{session_id}.png', dpi=150)
```

**What this does:** Continuous tongue/paw/ME speeds are computed in full but only their median-binarized versions are kept. `generate_processing_plots` (when `--show-processing`) creates per-session figures unrelated to the saved pickle.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> "Float32 for arrays to reduce memory" (line 262)

**Code** (convert_data.py:401, 422, 448, 535, 563, 591, 813-814, 1033-1034):
```python
trialdat = np.zeros((n_time, n_neurons, ntrials), dtype=np.float32)
...
trialdat[:, i, j] = smoothed.astype(np.float32)
...
speed = np.full((n_time, ntrials), np.nan, dtype=np.float32)
...
me_interp = np.full((n_time, ntrials), np.nan, dtype=np.float32)
...
if fmt == 'h5':
    data.close()
...
with open(args.outfile, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** Per-trial neural/velocity/ME arrays are allocated as float32; HDF5 file handles are closed after each session; output pickled with protocol 4. Discretized outputs are stored as int64.

**Rating:** match

**Note:** _(no note)_---

---
