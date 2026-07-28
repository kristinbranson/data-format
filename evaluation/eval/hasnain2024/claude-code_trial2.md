# hasnain2024 — claude-code / trial2

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/hasnain2024/claude/2026-03-20__13-50-53_trial2/verifier/snapshot/`

Outputs identified (K=6): lick_direction, behavioral_context, outcome, tongue_velocity, paw_velocity, motion_energy

---

## Q 1-a. How are all the data for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:53-65: "Data structure: Each session .mat file loads struct `obj` with fields: bp (bpod/trial), clu (spike data), traj (DLC trajectories), ex (session metadata), me (motion energy for behavior-only)"; "Neural processing pipeline: loadObjs -> findTrials -> findClusters -> alignSpikes -> getSeq -> removeLowFRClusters"

**Code** (convert_data.py:856-873):
```python
def convert_all(session_defs, outfile, show_processing=False):
    """Convert all sessions to the target format."""
    total_t0 = time.time()

    all_sessions = []
    for i, (anm, date, probes, ddir) in enumerate(session_defs):
        print(f"[{i+1}/{len(session_defs)}] Loading {anm}_{date}...")
        result = load_session(anm, date, probes, ddir, PARAMS)
        if result is not None:
            all_sessions.append(result)
```

**What this does:** Iterates over a hard-coded `SESSION_DEFS` list (44 entries, each a tuple of `(animal, date, probes, data_dir_key)`) and calls `load_session` on each. `load_session` opens the per-session `data_structure_<anm>_<date>.mat` (HDF5 v7.3 or v5) plus the matching `motionEnergy_*.mat`, runs the full processing pipeline, and returns a per-session dict that is appended.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:74-76: "Ephys_Behavior: 25 sessions (EKH1, EKH3, JEB6, JEB7, JGR2, JGR3, JEB13, JEB14, JEB15, JEB19) - 10 animals; RandomizedDelay_Ephys_Behavior: 22 sessions (JEB11, JEB12, JEB23, JEB24) - 4 animals"

**Code** (convert_data.py:876-878, 926, 936):
```python
all_animals = sorted(set(s['animal'] for s in all_sessions))
animal_to_idx = {a: i for i, a in enumerate(all_animals)}
...
subject_idx.append(animal_to_idx[sess['animal']])
...
'subject_idx': np.array(subject_idx, dtype=np.int64),
```

**What this does:** Subject identity is the `animal` string parsed from each session tuple. After loading, unique animal codes are sorted and given integer indices; each session's `subject_idx` points into that list. Output stores `subjects` (list of names) and `subject_idx` (one int per session).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:71-72: "Each session: `data_structure_<Animal>_<Date>.mat` (HDF5 format, MATLAB v7.3); Each ephys session paired with `motionEnergy_<Animal>_<Date>.mat`"

**Code** (convert_data.py:30-77, 396-407):
```python
SESSION_DEFS = [
    ('EKH1', '2021-08-07', [2], 'ephys'),
    ...
    ('JEB24', '2023-11-03', [1], 'random'),
]
...
def load_session(anm, date, probes, data_dir_key, params):
    data_dir = DATA_DIRS[data_dir_key]
    data_fn = os.path.join(data_dir, f'data_structure_{anm}_{date}.mat')
    me_fn = os.path.join(data_dir, f'motionEnergy_{anm}_{date}.mat')
    session_id = f'{anm}_{date}'
```

**What this does:** Each entry in the manually curated `SESSION_DEFS` list (44 entries) is treated as one session, identified by `<animal>_<date>`. Sessions are kept as separate elements in the top-level `neural`/`input`/`output` lists, one list per session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:144-149: "Trial curation rules: 1. Exclude early lick trials (~early); 2. Exclude stim/photoinactivation trials (~stim.enable); 3. For hit analyses: use hit trials only; 4. For DR: ~autowater (autowater=0); 5. For WC: autowater=1"

**Code** (convert_data.py:444-449, 460-473):
```python
trial_mask = (bp['early'] == 0) & (bp['stim_enable'] == 0)
valid_trials = np.where(trial_mask)[0] + 1  # 1-indexed
...
for neuron_idx, clu_idx in enumerate(good_indices):
    spike_tm = all_spike_times[clu_idx]
    spike_trial = all_spike_trials[clu_idx]
    for t_idx, trial_num in enumerate(valid_trials):
        spk_mask = spike_trial == trial_num
        ...
        spk_times = spike_tm[spk_mask] - align_times[trial_num - 1]
        counts, _ = np.histogram(spk_times, bins=edges)
```

**What this does:** Trials are taken from `obj.bp` (Ntrials), filtered by `early==0 & stim_enable==0`, and indexed via the `trial` field on each unit's spike list. Each kept trial becomes its own entry in the `trialdat` array (n_neurons, n_timebins, n_trials) and ultimately one element in the per-session `neural`/`input`/`output` lists.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:201: "Exclude early lick and stim trials: Per reference code conditions (~early, ~stim.enable)"; CONVERSION_NOTES.md:200: "Trial filtering for decoder: Include ALL trial types (hit, miss, no-response) per session. The decoder should predict outcome, so needs all types."

**Code** (convert_data.py:444-449):
```python
# --- Trial filtering ---
trial_mask = (bp['early'] == 0) & (bp['stim_enable'] == 0)
valid_trials = np.where(trial_mask)[0] + 1  # 1-indexed
if len(valid_trials) < 2:
    print(f"  WARNING: {session_id} has < 2 valid trials, skipping")
    return None
```

**What this does:** Two QC filters applied at the trial level: drop trials with `bp.early==1` (early lick) and trials with `bp.stim.enable==1` (photostimulation). Hit/miss/no-response and DR/WC trials are all kept (so outcome and context can be decoded). Sessions with fewer than 2 surviving trials are skipped entirely.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:81-82: "obj.clu: Cell array (1 x nProbes), each probe has struct array of units with: tm, trialtm, trial, quality, site, spkWavs"; CONVERSION_NOTES.md:199: "Dual probe sessions: Concatenate neurons from both probes (both are ALM)"

**Code** (convert_data.py:343-357):
```python
clu_refs = obj['clu'][()].flatten()
all_spike_times = []
all_spike_trials = []
all_qualities = []
for probe_num in probes:
    probe_idx = probe_num - 1
    probe_ref = clu_refs[probe_idx]
    probe_group = f[probe_ref]
    quality_refs = probe_group['quality'][()].flatten()
    trialtm_refs = probe_group['trialtm'][()].flatten()
    trial_refs = probe_group['trial'][()].flatten()
    for i in range(len(quality_refs)):
        quality = h5_read_string(f, quality_refs[i]).strip().lower()
        trialtm = f[trialtm_refs[i]][()].flatten().astype(np.float64)
        trial = f[trial_refs[i]][()].flatten().astype(np.float64)
```

**What this does:** Neural source is the per-unit spike-time stream from `obj.clu` for each ALM probe listed in the session tuple. Per unit, the script reads `trialtm` (spike time within trial), `trial` (trial index), and `quality`. Units from multiple probes (e.g., JEB13/JEB15 dual-probe sessions) are concatenated into one neuron pool.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:128-132: "Time window: -2.5 to 2.5 s from goCue; Spike binning: 10ms bins, histc with edges tmin:dt:tmax; Smoothing: Causal Gaussian kernel, window=15 (via mySmooth); Firing rates: spks/sec (spike count / dt)"

**Code** (convert_data.py:451-473):
```python
align_times = ev[params['align_event']]
edges = np.arange(params['tmin'], params['tmax'] + params['dt'], params['dt'])
time_axis = edges[:-1] + params['dt'] / 2
n_timebins = len(time_axis)
...
trialdat = np.zeros((len(good_indices), n_timebins, n_valid_trials), dtype=np.float32)
for neuron_idx, clu_idx in enumerate(good_indices):
    ...
    for t_idx, trial_num in enumerate(valid_trials):
        spk_mask = spike_trial == trial_num
        if not np.any(spk_mask):
            continue
        spk_times = spike_tm[spk_mask] - align_times[trial_num - 1]
        counts, _ = np.histogram(spk_times, bins=edges)
        fr = causal_gaussian_smooth(counts.astype(np.float64) / params['dt'],
                                   params['smooth_window'],
                                   params['smooth_bctype'])
        trialdat[neuron_idx, :, t_idx] = fr.astype(np.float32)
```

**What this does:** For each (neuron, trial), spike times are re-referenced to the trial's go-cue, histogrammed into 10 ms bins over [-2.5, 2.5] s, divided by `dt` to get spikes/s, then smoothed with a causal Gaussian (window=15, reflect padding) implemented in `causal_gaussian_smooth`.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:139-142: "Quality filter: Exclude 'garbage', 'noisy', 'gabrga', 'real?' (quality='all' mode); Low firing rate: Remove neurons with mean FR < 1 Hz across all trials; Min units: Sessions with < 10 units excluded"

**Code** (convert_data.py:434-442, 475-483):
```python
quality_exclude = params['quality_exclude']
keep_mask = np.array([q not in quality_exclude and q != '' and q != 'nan'
                      for q in all_qualities])
good_indices = np.where(keep_mask)[0]
if len(good_indices) == 0:
    print(f"  WARNING: {session_id} has no units after quality filter, skipping")
    return None
...
mean_fr = np.mean(trialdat, axis=(1, 2))
fr_mask = mean_fr > params['low_fr']
trialdat = trialdat[fr_mask, :, :]
n_neurons = trialdat.shape[0]
if n_neurons < params['min_units']:
    print(f"  WARNING: {session_id} has {n_neurons} units (< {params['min_units']}), skipping")
    return None
```

**What this does:** Two-stage neuron QC: (1) drop units whose `quality` string is in `{garbage, noisy, gabrga, real?, '', nan}`; (2) after binning, drop units with mean FR <= 1 Hz across all timepoints/trials. Sessions with < 10 surviving units are skipped.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 2-d. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:115: "Neural data time bin | 10ms (dt=1/100) | WorkingWithDataObjs.m params"; CONVERSION_NOTES.md:131: "Smoothing: Causal Gaussian kernel, window=15 (via mySmooth)"

**Code** (convert_data.py:86-96, 155-194):
```python
PARAMS = {
    'align_event': 'goCue',
    'tmin': -2.5,
    'tmax': 2.5,
    'dt': 1.0 / 100,  # 10 ms bins
    'smooth_window': 15,
    'smooth_bctype': 'reflect',
    ...
}
...
def causal_gaussian_smooth(x, N, bctype='reflect'):
    ...
    kern = np.array(sig_windows.gaussian(N, std=(N - 1) / (2 * 2.5)))
    # Make causal: zero out first half
    kern[:N // 2] = 0
    kern = kern / kern.sum()
```

**What this does:** Bin edges are `np.arange(-2.5, 2.5+dt, dt)` giving 500 10-ms bins; the time axis uses bin centers. Smoothing kernel is a Gaussian with the first half zeroed out (causal), normalized to sum 1, applied via 1D convolution along time with reflect padding.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:128: "Temporal alignment: Align to goCue onset"

**Code** (convert_data.py:451-468):
```python
align_times = ev[params['align_event']]
edges = np.arange(params['tmin'], params['tmax'] + params['dt'], params['dt'])
time_axis = edges[:-1] + params['dt'] / 2
...
for t_idx, trial_num in enumerate(valid_trials):
    spk_mask = spike_trial == trial_num
    if not np.any(spk_mask):
        continue
    spk_times = spike_tm[spk_mask] - align_times[trial_num - 1]
    counts, _ = np.histogram(spk_times, bins=edges)
```

**What this does:** Each trial's spikes are subtracted by that trial's `obj.bp.ev.goCue` time, then histogrammed in the fixed [-2.5, 2.5] s window. All trials therefore share an identical 500-bin time axis centered on go-cue.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 3-a. What variables in the raw data is `output` *lick_direction* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:185: "obj.bp.R/L | output[0]: lick_direction | L=0, R=1, per-trial"

**Code** (convert_data.py:485-487):
```python
# --- Extract trial-level variables ---
valid_trial_indices = valid_trials - 1
lick_direction = bp['R'][valid_trial_indices].copy()
```

**What this does:** Derived directly from `obj.bp.R` (1 if the trial's correct/instructed lick direction was right, 0 if left), one value per kept trial.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 3-b. What processing is involved in computing `output` *lick_direction*?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:185: "L=0, R=1, per-trial"

**Code** (convert_data.py:487, 913, 940-944):
```python
lick_direction = bp['R'][valid_trial_indices].copy()
...
lick_dir = np.full((1, n_timebins), int(sess['lick_direction'][t]), dtype=np.int64)
...
'output_names': ['lick_direction', ...
'output_values': [
    ['left', 'right'],        # lick_direction
```

**What this does:** No transformation beyond cast to int and broadcast across the 500 timebins so the output array shape matches neural. Class 0 = left, 1 = right.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 3-c. How is `output` *lick_direction* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:911-921):
```python
lick_dir = np.full((1, n_timebins), int(sess['lick_direction'][t]), dtype=np.int64)
context = np.full((1, n_timebins), int(sess['behavioral_context'][t]), dtype=np.int64)
outc = np.full((1, n_timebins), int(sess['outcome'][t]), dtype=np.int64)
tongue_v = sess['tongue_vel_disc'][:, t].astype(np.int64).reshape(1, -1)
paw_v = sess['paw_vel_disc'][:, t].astype(np.int64).reshape(1, -1)
me_v = sess['me_disc'][:, t].astype(np.int64).reshape(1, -1)
trial_output = np.concatenate([lick_dir, context, outc, tongue_v, paw_v, me_v], axis=0).astype(np.int64)
```

**What this does:** The scalar lick direction is `np.full`-broadcast across the same 500-bin time axis used for neural data, then concatenated with the other outputs into a (6, n_timebins) per-trial array.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 4-a. What variables in the raw data is `output` *behavioral_context* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:186: "obj.bp.autowater | output[1]: behavioral_context | ... autowater=1 -> WC=0, autowater=0 -> DR=1"

**Code** (convert_data.py:488):
```python
behavioral_context = 1.0 - bp['autowater'][valid_trial_indices]
```

**What this does:** Derived from `obj.bp.autowater`. Autowater trials (=1) are mapped to context 0 (WC, water-cued), non-autowater (=0) to context 1 (DR, delayed-response).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 4-b. What processing is involved in computing `output` *behavioral_context*?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:186: "WC=0, DR=1"

**Code** (convert_data.py:488, 945):
```python
behavioral_context = 1.0 - bp['autowater'][valid_trial_indices]
...
['WC', 'DR'],             # behavioral_context
```

**What this does:** Single arithmetic flip (`1 - autowater`) then int cast. No per-block grouping or smoothing.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 4-c. How is `output` *behavioral_context* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:914):
```python
context = np.full((1, n_timebins), int(sess['behavioral_context'][t]), dtype=np.int64)
```

**What this does:** Per-trial scalar broadcast across all 500 timebins so it matches the neural shape.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 5-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:187: "obj.bp.hit | output[2]: outcome | incorrect=0, correct=1, per-trial"

**Code** (convert_data.py:489):
```python
outcome = bp['hit'][valid_trial_indices].copy()
```

**What this does:** Direct copy of `obj.bp.hit` (1=correct/rewarded, 0=miss/no-response) at the kept-trial indices.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 5-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:489, 946):
```python
outcome = bp['hit'][valid_trial_indices].copy()
...
['incorrect', 'correct'], # outcome
```

**What this does:** No transformation beyond integer cast; `miss` and `no` (no-response) are both lumped into class 0.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 5-c. How is `output` *outcome* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:915):
```python
outc = np.full((1, n_timebins), int(sess['outcome'][t]), dtype=np.int64)
```

**What this does:** Per-trial scalar broadcast across all 500 timebins.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 6-a. What variables in the raw data is `output` *tongue_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:188: "DLC tongue velocity | output[3]: tongue_velocity | Discretize 50th percentile per session ... Time-varying, from bottom cam"

**Code** (convert_data.py:501-505):
```python
tongue_vel = _compute_feature_velocity_generic(
    traj_data, ntrials, view=2, feat_name='top_tongue',
    vidshift=vidshift, align_times=align_times,
    time_axis=time_axis, is_tongue=True)
```

**What this does:** Derived from `obj.traj` view 2 (bottom cam), DLC feature `top_tongue` x/y coordinates, plus `frameTimes`, `obj.sglx.bitcode/bitstart` and `obj.bp.ev.bitStart` for the video-to-neural offset, and `obj.bp.ev.goCue` for trial alignment.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 6-b. What processing is involved in computing `output` *tongue_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:202: "Tongue velocity: Compute from bottom cam DLC features (top_tongue or similar). Use Euclidean velocity = sqrt(vx^2 + vy^2)"; CONVERSION_NOTES.md:205: "Per-session discretization: 50th percentile threshold computed on all timepoints across all trials in session"

**Code** (convert_data.py:664-687, 708-722):
```python
xpos = interp1d(ft_a[valid], x_r[valid], kind='linear',
                bounds_error=False, fill_value=np.nan)(time_axis)
ypos = interp1d(ft_a[valid], y_r[valid], kind='linear',
                bounds_error=False, fill_value=np.nan)(time_axis)
...
xvel = np.gradient(xpos)
yvel = np.gradient(ypos)
if is_tongue:
    xvel[np.isnan(xvel)] = 0
    yvel[np.isnan(yvel)] = 0
...
speed[:, trix] = np.sqrt(xvel**2 + yvel**2).astype(np.float32)
...
threshold = np.percentile(valid_vals, 50)
disc = (data >= threshold).astype(np.int64)
```

**What this does:** x,y of `top_tongue` are linearly interpolated onto the neural time axis, NaN-filled with zero (tongue retracted), differenced via `np.gradient`, combined as Euclidean speed, then thresholded at the per-session 50th percentile to a binary low/high label.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 6-c. How is `output` *tongue_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:133: "Video offset: subtract 0.5s from frameTimes (or use findVideoOffset via bitcode)"

**Code** (convert_data.py:240-251, 656-665):
```python
bit_start_arr = ev_raw['bitStart'][0, 0].flatten().astype(np.float64)
bit_start = np.nanmedian(bit_start_arr)
...
bitcode_bitstart = np.nanmedian(bitcode_raw['bitstart'][0, 0].flatten().astype(np.float64))
vid_file_offset = bitcode_bitstart / fs
vidshift = vid_file_offset - bit_start
...
ft_aligned = ft - vidshift - align_times[trix]
...
xpos = interp1d(ft_a[valid], x_r[valid], kind='linear',
                bounds_error=False, fill_value=np.nan)(time_axis)
```

**What this does:** Per-session `vidshift` is computed from the bitcode (falls back to 0.5 s). Each trial's `frameTimes` are corrected by `vidshift` and re-referenced to that trial's go-cue, then x/y positions are interpolated onto the same 500-bin neural time axis before differentiation.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 7-a. What variables in the raw data is `output` *paw_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:189: "DLC paw velocity | output[4]: paw_velocity | Discretize 50th percentile per session ... Time-varying, from bottom cam"

**Code** (convert_data.py:506-509):
```python
paw_vel = _compute_feature_velocity_generic(
    traj_data, ntrials, view=2, feat_name='top_paw',
    vidshift=vidshift, align_times=align_times,
    time_axis=time_axis, is_tongue=False)
```

**What this does:** Same source pipeline as tongue but uses DLC feature `top_paw` from `obj.traj` view 2 (bottom cam).

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 7-b. What processing is involved in computing `output` *paw_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:204: "Per-session discretization: 50th percentile threshold computed on all timepoints across all trials in session"

**Code** (convert_data.py:669-687):
```python
if not is_tongue:
    xpos = _fill_nearest(xpos)
    ypos = _fill_nearest(ypos)
xvel = np.gradient(xpos)
yvel = np.gradient(ypos)
...
else:
    base_xvel = np.nanmedian(np.diff(xpos))
    base_yvel = np.nanmedian(np.diff(ypos))
    xvel -= (base_xvel if not np.isnan(base_xvel) else 0)
    yvel -= (base_yvel if not np.isnan(base_yvel) else 0)
    xvel = _fill_nearest(xvel)
    yvel = _fill_nearest(yvel)
speed[:, trix] = np.sqrt(xvel**2 + yvel**2).astype(np.float32)
```

**What this does:** Like tongue, but NaNs are filled with the nearest valid value (paw is usually visible) and the median per-trial drift is subtracted from x/y velocity before computing Euclidean speed; speed is then 50th-percentile-thresholded per session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 7-c. How is `output` *paw_velocity* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:656-667):
```python
ft_aligned = ft - vidshift - align_times[trix]
min_len = min(len(ft_aligned), len(x_raw))
ft_a, x_r, y_r = ft_aligned[:min_len], x_raw[:min_len], y_raw[:min_len]
valid = ~np.isnan(ft_a) & ~np.isnan(x_r) & ~np.isnan(y_r)
if valid.sum() < 2:
    continue
xpos = interp1d(ft_a[valid], x_r[valid], kind='linear',
                bounds_error=False, fill_value=np.nan)(time_axis)
```

**What this does:** Same alignment path as tongue: bitcode-derived `vidshift` plus per-trial go-cue subtraction, then linear interpolation of paw x,y onto the neural 500-bin axis.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 8-a. What variables in the raw data is `output` *motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:190: "Motion energy | output[5]: motion_energy | Discretize 50th percentile per session ... Time-varying, from motionEnergy file"

**Code** (convert_data.py:404-405, 555-564):
```python
me_fn = os.path.join(data_dir, f'motionEnergy_{anm}_{date}.mat')
...
me_file = sio.loadmat(me_fn, squeeze_me=True)
me_struct = me_file['me']
me_cell = me_struct['data'].item()
...
me_cell = [me_h5[ref][()].flatten().astype(np.float64) for ref in me_data_refs]
```

**What this does:** Derived from the per-session `motionEnergy_<anm>_<date>.mat` file: `me.data` is a cell array of per-trial 1-D motion-energy traces sampled at ~400 Hz.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 8-b. What processing is involved in computing `output` *motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:134: "Motion energy alignment: Interpolate to neural time axis using interp1, align to goCue"

**Code** (convert_data.py:582-602):
```python
ft_aligned = ft - vidshift - align_times[trix]
min_len = min(len(ft_aligned), len(me_trial))
ft_aligned, me_trial = ft_aligned[:min_len], me_trial[:min_len]
valid = ~np.isnan(ft_aligned) & ~np.isnan(me_trial)
if valid.sum() < 2:
    continue
me_aligned[:, trix] = interp1d(ft_aligned[valid], me_trial[valid],
                               kind='linear', bounds_error=False,
                               fill_value=np.nan)(time_axis).astype(np.float32)
...
for trix in range(ntrials):
    col = me_aligned[:, trix]
    if not np.isnan(col).all() and np.isnan(col).any():
        me_aligned[:, trix] = _fill_nearest(col)
```

**What this does:** Per trial, the raw ME trace is paired with the side-cam `frameTimes`, shifted by `vidshift` and the trial go-cue, linearly interpolated to the neural time axis, NaNs filled by nearest-neighbour, and finally 50th-percentile-thresholded into a binary low/high label per session.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 8-c. How is `output` *motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:134: "Motion energy alignment: Interpolate to neural time axis using interp1, align to goCue"

**Code** (convert_data.py:567-595):
```python
side_cam = traj_data['views'][0] if traj_data is not None else None
n_time = len(time_axis)
me_aligned = np.full((n_time, ntrials), np.nan, dtype=np.float32)
for trix in range(ntrials):
    ...
    ft = None
    if side_cam is not None and trix < len(side_cam['trials']) and side_cam['trials'][trix] is not None:
        ft = side_cam['trials'][trix]['frameTimes']
    if ft is None or ft.size == 0 or np.all(np.isnan(ft)):
        ft = np.arange(1, me_trial.size + 1) / 400.0
    ft_aligned = ft - vidshift - align_times[trix]
    ...
    me_aligned[:, trix] = interp1d(ft_aligned[valid], me_trial[valid],
                                   kind='linear', bounds_error=False,
                                   fill_value=np.nan)(time_axis).astype(np.float32)
```

**What this does:** Uses the side-cam `frameTimes` (or a synthetic 400 Hz axis if missing), subtracts `vidshift + goCue`, and interpolates onto the neural 500-bin time axis.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 9. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:331-336 "Known Issues": "All-zero neural data: Sessions 36 ... and 43 ... have ~28-33 late trials with all-zero neural data ..."; "Motion energy loading failures: 4 JEB23 sessions ... have ME .mat files that can't be opened ... These get all-zero ME"; "Behavioral context always DR: ~14 sessions have no WC trials"

**Code** (convert_data.py:409-422, 492-498, 694-705, 715-721):
```python
if not os.path.exists(data_fn):
    print(f"  WARNING: {data_fn} not found, skipping")
    return None
fmt = _detect_file_format(data_fn)
try:
    if fmt == 'hdf5':
        raw = _load_raw_data_hdf5(data_fn, probes)
    else:
        raw = _load_raw_data_v5(data_fn, probes)
except Exception as e:
    print(f"  WARNING: Could not load {session_id}: {e}")
    return None
...
me_data = None
if os.path.exists(me_fn):
    try:
        me_data = _load_motion_energy_generic(...)
    except Exception as e:
        print(f"  WARNING: Could not load motion energy for {session_id}: {e}")
...
def _fill_nearest(arr):
    nans = np.isnan(arr)
    if not nans.any():
        return arr
    if nans.all():
        return arr
    valid_idx = np.where(~nans)[0]
    nan_idx = np.where(nans)[0]
    nearest = np.searchsorted(valid_idx, nan_idx).clip(0, len(valid_idx) - 1)
    arr[nans] = arr[valid_idx[nearest]]
    return arr
...
if valid_vals.size == 0:
    return np.zeros((n_timebins, n_trials), dtype=np.int64)
threshold = np.percentile(valid_vals, 50)
disc = (data >= threshold).astype(np.int64)
disc[np.isnan(data)] = 0
```

**What this does:** Multi-layer fallbacks: missing `.mat` files / load failures print a WARNING and skip; ME load failures default to None which becomes an all-zero discretized output; per-trial NaNs in ME and paw kinematics are filled by nearest valid neighbour; tongue NaN velocities are zeroed (treated as "tongue retracted"); empty velocity arrays default to all-zero discretization; sessions with too few trials/units are skipped.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 10-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:253-256: "Full loading | ~5s | ~220s (~3.7 min)"; CONVERSION_NOTES.md:284 "conversion_full_out.txt: created (162.8s processing, 166.2s total)"

**Code** (convert_data.py:460-473):
```python
for neuron_idx, clu_idx in enumerate(good_indices):
    spike_tm = all_spike_times[clu_idx]
    spike_trial = all_spike_trials[clu_idx]
    for t_idx, trial_num in enumerate(valid_trials):
        spk_mask = spike_trial == trial_num
        if not np.any(spk_mask):
            continue
        spk_times = spike_tm[spk_mask] - align_times[trial_num - 1]
        counts, _ = np.histogram(spk_times, bins=edges)
        fr = causal_gaussian_smooth(counts.astype(np.float64) / params['dt'],
                                   params['smooth_window'],
                                   params['smooth_bctype'])
        trialdat[neuron_idx, :, t_idx] = fr.astype(np.float32)
```

**What this does:** The dominant cost is the nested neuron x trial loop that performs `np.histogram` and a single-trial 1-D Gaussian convolution per (neuron, trial) pair. HDF5 dereferencing per spike-cluster and the per-trial DLC interpolation also contribute. Total full-conversion runtime reported: ~163 s.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 10-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:186-194, 460-473, 901-921):
```python
out = np.zeros_like(x_filt)
for j in range(x_filt.shape[1]):
    out[:, j] = np.convolve(x_filt[:, j], kern, mode='same')
...
for neuron_idx, clu_idx in enumerate(good_indices):
    for t_idx, trial_num in enumerate(valid_trials):
        spk_mask = spike_trial == trial_num
        ...
        counts, _ = np.histogram(spk_times, bins=edges)
        fr = causal_gaussian_smooth(...)
        trialdat[neuron_idx, :, t_idx] = fr.astype(np.float32)
...
for t in range(n_trials):
    sess_neural.append(trialdat[:, :, t].astype(np.float32))
    time_input = time_axis.astype(np.float32).reshape(1, -1)
    sess_input.append(time_input)
    lick_dir = np.full((1, n_timebins), int(sess['lick_direction'][t]), dtype=np.int64)
```

**What this does:** Three vectorizable loops: (1) per-column `np.convolve` in `causal_gaussian_smooth` could be a single `scipy.signal.fftconvolve` over an axis; (2) the (neuron, trial) histogram + smoothing could be replaced by a single `np.histogram2d`/`searchsorted`-based binning followed by one batched smoothing call; (3) the per-trial output assembly in `convert_all` builds time-broadcast arrays one trial at a time.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 10-c. What processing does the code repeat multiple times?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:606-687, 551-603):
```python
def _compute_feature_velocity_generic(traj_data, ntrials, view, feat_name, ...):
    ...
    for trix in range(min(ntrials, len(view_data['trials']))):
        ...
        ft_aligned = ft - vidshift - align_times[trix]
        ...
        xpos = interp1d(ft_a[valid], x_r[valid], ...)(time_axis)
        ypos = interp1d(ft_a[valid], y_r[valid], ...)(time_axis)
```

**What this does:** Per session, `_compute_feature_velocity_generic` is called twice (tongue, paw) and traverses the same `traj_data['views'][1]` cell, recomputing `ft - vidshift - align_times[trix]` each time. The motion-energy loader independently re-iterates the same per-trial frame-time pipeline. Causal-Gaussian smoothing rebuilds the kernel on every call. HDF5 string decoding is also performed per cluster even though many qualities repeat.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 10-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (CONVERSION_NOTES.md):
> (none)

**Code** (convert_data.py:540-547, 906-908):
```python
'tongue_vel_raw': tongue_vel,
'paw_vel_raw': paw_vel,
'me_raw': me_data,
...
time_input = time_axis.astype(np.float32).reshape(1, -1)
sess_input.append(time_input)
```

**What this does:** Raw (continuous) tongue/paw/ME arrays are computed and stored on the session dict for plotting but only the discretized versions are used in the saved pickle. A copy of `time_axis` is also re-built per trial as `input` even though it is identical for every trial across the dataset. Plotting code (`plot_processing`) is also gated on `--show-processing` but its precursors (raw velocities) are still produced.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

## Q 10-e. How is memory usage optimized?

**Notes excerpt** (CONVERSION_NOTES.md):
> CONVERSION_NOTES.md:284: "converted_data.pkl: 1843.5 MB"

**Code** (convert_data.py:458, 473, 569, 609, 969-970):
```python
trialdat = np.zeros((len(good_indices), n_timebins, n_valid_trials), dtype=np.float32)
...
trialdat[neuron_idx, :, t_idx] = fr.astype(np.float32)
...
me_aligned = np.full((n_time, ntrials), np.nan, dtype=np.float32)
...
speed = np.full((n_time, ntrials), np.nan, dtype=np.float32)
...
with open(outfile, 'wb') as pkl:
    pickle.dump(data, pkl, protocol=4)
```

**What this does:** Neural and behavioural arrays are stored as `float32` (and outputs as `int64`); the per-session HDF5 file is closed after raw extraction; sessions are processed serially so only one session's intermediate buffers live at a time. The final aggregated lists are pickled with protocol 4. No explicit `del` of raw spike arrays or chunked writing is used.

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_
