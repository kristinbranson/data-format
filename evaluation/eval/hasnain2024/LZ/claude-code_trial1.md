# hasnain2024 — claude-code / trial1

Trial path: `/groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/hasnain2024/claude/2026-03-20__13-50-53_trial1/verifier/snapshot/`

Outputs identified (K=6): lick_direction, context, outcome, tongue_velocity, paw_velocity, motion_energy

---

## Q 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

**Notes excerpt** (CONVERSION_NOTES.md:85-104):
> Sessions to Include (from loading scripts) — Ephys_Behavior (25 sessions, 10 mice) + RandomizedDelay_Ephys_Behavior (19 sessions, 4 mice). Excluded: MAH (behavior-only), JEB4/JEB5, JEB23_2023-10-20, JEB24_2023-10-03/04.

**Code** (convert_data.py:32-85, 949-957):
```python
EPHYS_SESSIONS = [
    ('EKH1', '2021-08-07', [2], 'Ephys_Behavior'),
    ...
]
RANDOMIZED_DELAY_SESSIONS = [
    ('JEB11', '2022-05-10', [1], 'RandomizedDelay_Ephys_Behavior'),
    ...
]
ALL_SESSIONS = EPHYS_SESSIONS + RANDOMIZED_DELAY_SESSIONS

for i, (anm, date, probes, data_dir) in enumerate(sessions):
    result = process_session(anm, date, probes, data_dir, ...)
```

**What this does:** Hardcoded registries of (animal, date, probes, data_dir) tuples for 25 ephys + 19 randomized-delay sessions are iterated; each session's `data_structure_<anm>_<date>.mat` is loaded via `mat73.loadmat` (or scipy.io for v5 files).

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-b. How are the data split into subjects?

**Notes excerpt** (CONVERSION_NOTES.md:271-274):
> 14 subjects: EKH1, EKH3, JEB6, JEB7, JEB11, JEB12, JEB13, JEB14, JEB15, JEB19, JEB23, JEB24, JGR2, JGR3

**Code** (convert_data.py:947, 964-965, 984-985, 993-994):
```python
subjects_set = set()
...
all_animals.append(anm)
subjects_set.add(anm)
...
subjects = sorted(subjects_set)
subject_idx = np.array([subjects.index(anm) for anm in all_animals], dtype=np.int64)
...
'subjects': subjects,
'subject_idx': subject_idx,
```

**What this does:** Subject identity is the animal string from each session tuple. Unique animals are sorted into `subjects`, and `subject_idx` provides one index per session into that list.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-c. How are the data split into sessions?

**Notes excerpt** (CONVERSION_NOTES.md:201):
> Include all 44 ephys sessions: Both Ephys_Behavior (25) and RandomizedDelay (19).

**Code** (convert_data.py:951-977):
```python
for i, (anm, date, probes, data_dir) in enumerate(sessions):
    result = process_session(anm, date, probes, data_dir, ...)
    if result is None:
        continue
    all_neural.append(result['neural'])
    all_input.append(result['input'])
    all_output.append(result['output'])
    all_animals.append(anm)
    ...
    session_info.append({'animal': anm, 'date': date, 'data_dir': data_dir,
                         'probes': probes, 'n_neurons': ..., 'n_trials': ...})
```

**What this does:** Each (animal, date) pair from `ALL_SESSIONS` is one session; trial lists are appended to per-session lists in `all_neural`, `all_input`, `all_output`, with parallel `session_info` metadata.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-d. Are the data correctly split into trials?

**Notes excerpt** (CONVERSION_NOTES.md:204):
> Trial exclusion: Exclude early, stim.enable, and no-response trials. Keep hit and miss.

**Code** (convert_data.py:633, 779-795):
```python
ntrials_total = int(bp['Ntrials'])
...
for t_idx in range(n_valid):
    neural_trials.append(trialdat_valid[:, :, t_idx].T.astype(np.float32))
    input_trials.append(time_axis.reshape(1, -1).astype(np.float32))
    out = np.zeros((6, n_time), dtype=np.int32)
    out[0, :] = lick_direction[t_idx]
    ...
    output_trials.append(out)
```

**What this does:** `bp.Ntrials` defines per-session total trial count; spike data is binned per-trial via `trial_arr == trial_num` (1-indexed). After valid-trial selection, each trial is a separate entry in `neural_trials`/`input_trials`/`output_trials`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 1-e. How are trials filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:155):
> Trial curation: Exclude early lick trials (early=1), stim trials (stim.enable=1), ignore/no-response trials (no=1).

**Code** (convert_data.py:640-661):
```python
R = np.array(bp['R']).flatten().astype(bool)
L = np.array(bp['L']).flatten().astype(bool)
hit = np.array(bp['hit']).flatten().astype(bool)
miss = np.array(bp['miss']).flatten().astype(bool)
no = np.array(bp['no']).flatten().astype(bool)
autowater = np.array(bp['autowater']).flatten().astype(bool)
early = np.array(bp['early']).flatten().astype(bool)
...
valid_mask = ~early & ~stim_enable & ~no
valid_mask = valid_mask & (hit | miss)
valid_trials = np.where(valid_mask)[0]
```

**What this does:** Trials are excluded if `early`, `stim.enable`, or `no` flags are set, and required to be either `hit` or `miss`. Sessions with fewer than 2 valid trials or fewer than 10 neurons after filtering are skipped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-a. What variables in the raw data is the final `neural` data derived from?

**Notes excerpt** (CONVERSION_NOTES.md:191):
> obj.clu (spike times) -> neural; Align to goCue, bin at 10ms, smooth, convert to firing rate.

**Code** (convert_data.py:707-720):
```python
for i, clu_idx in enumerate(valid_clu):
    trial_arr = np.array(clu_probe['trial'][clu_idx]).flatten()
    trialtm_arr = np.array(clu_probe['trialtm'][clu_idx]).flatten()
    for j in range(ntrials_total):
        trial_num = j + 1
        spk_mask = trial_arr == trial_num
        if not np.any(spk_mask): continue
        aligned = trialtm_arr[spk_mask] - align_times_all[j]
        counts, _ = np.histogram(aligned, bins=edges)
        fr = counts.astype(np.float32) / DT
        trialdat[:, neuron_offset + i, j] = causal_gaussian_smooth(fr, SMOOTH_WINDOW, BC_TYPE)
```

**What this does:** Neural data derives from `obj.clu[probe].trial` and `obj.clu[probe].trialtm` (per-cluster spike trial indices and within-trial spike times) and `obj.bp.ev.goCue` for alignment.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 2-b. How is the `neural` data processed?

**Notes excerpt** (CONVERSION_NOTES.md:52-59):
> 1. Load obj. 2. Find trial indices. 3. Find valid clusters. 4. Align spikes to goCue. 5. Bin spikes histc. 6. Smooth with Gaussian. 7. Remove low FR clusters.

**Code** (convert_data.py:91-141, 715-720):
```python
ALIGN_EVENT = 'goCue'; TMIN = -2.5; TMAX = 2.5; DT = 1.0/100
SMOOTH_WINDOW = 15; BC_TYPE = 'reflect'; LOW_FR = 1.0

def causal_gaussian_smooth(x, N, bctype='reflect'):
    kern = np.array(scipy_windows.gaussian(N, std=N/6.0))
    kern[:N//2] = 0  # causal: zero out first half
    kern = kern / kern.sum()
    ...
    out[:, j] = np.convolve(x_filt[:, j], kern, mode='same')
```

**What this does:** Spike times are aligned to goCue, histogrammed into 10 ms bins over [-2.5, 2.5]s, divided by `DT` to get firing rate (spk/s), then smoothed with a 15-bin causal Gaussian kernel using reflect boundary conditions.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-c. How is the `neural` data filtered based on quality controls?

**Notes excerpt** (CONVERSION_NOTES.md:154):
> Neuron curation: Exclude quality labels: garbage, gabrga, noisy, real?. Then remove neurons with mean FR < 1 Hz.

**Code** (convert_data.py:98, 351-362, 406-412, 728-734):
```python
EXCLUDED_QUALITIES = {'garbage', 'gabrga', 'noisy', 'real?'}

def get_valid_cluster_indices(clu_probe, excluded_qualities=EXCLUDED_QUALITIES):
    qualities = clu_probe['quality']
    valid = []
    for i, q in enumerate(qualities):
        ...
        if q_stripped.lower() not in {e.lower() for e in excluded_qualities}:
            valid.append(i)
    return valid

def remove_low_fr_neurons(trialdat, low_fr):
    mean_fr = np.nanmean(np.nanmean(trialdat, axis=2), axis=0)
    keep = mean_fr > low_fr
    return trialdat[:, keep, :], keep
```

**What this does:** Clusters with quality labels in `{garbage, gabrga, noisy, real?}` are excluded; remaining clusters with mean firing rate <= 1 Hz (averaged across trials and time) are removed. Sessions with <10 surviving neurons are skipped.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`?

**Notes excerpt** (CONVERSION_NOTES.md:1013-1016 — metadata):
> 'temporal_alignment_event': 'Go cue onset', 'align_event': 'goCue'

**Code** (convert_data.py:91, 636-637, 673, 715-718):
```python
ALIGN_EVENT = 'goCue'
...
ev = bp['ev']
goCue = np.array(ev['goCue']).flatten()
...
align_times_all = goCue
...
aligned = trialtm_arr[spk_mask] - align_times_all[j]
counts, _ = np.histogram(aligned, bins=edges)
```

**What this does:** Per-trial spike times (`trialtm`) have the trial's `goCue` time subtracted, so t=0 in `time_axis` corresponds to go-cue onset. The same `goCue` is used as `align_times` for behavioral signal alignment too.

**Rating:** match

**Note:** _(no note)_---

---

## Q 2-e. How is the `neural` data temporally binned/resampled?

**Notes excerpt** (CONVERSION_NOTES.md:202):
> Bin size 10 ms (dt=1/100): As in WorkingWithDataObjs.m, gives time axis from -2.5 to 2.5 s = 500 time bins.

**Code** (convert_data.py:92-95, 374-376, 693-695, 718-720):
```python
TMIN = -2.5; TMAX = 2.5; DT = 1.0/100; SMOOTH_WINDOW = 15
...
edges = np.arange(TMIN, TMAX + DT, DT)
time_axis = edges[:-1] + DT / 2
n_time = len(time_axis)
...
counts, _ = np.histogram(aligned, bins=edges)
fr = counts.astype(np.float32) / DT
trialdat[:, neuron_offset + i, j] = causal_gaussian_smooth(fr, SMOOTH_WINDOW, BC_TYPE)
```

**What this does:** Spikes are histogrammed into fixed 10 ms bins over [-2.5, 2.5]s (500 bins; bin centers used as time axis), giving firing rate per bin, then smoothed with the causal Gaussian.

**Rating:** match

**Note:** _(no note)_---

---

## Q 3-a. What variables in the raw data is `input` *time_from_go_cue* derived from?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:192 — `| time from goCue (s) | input[0] | Continuous time axis | N/A | Ranges from -2.5 to 2.5 s |`
> CONVERSION_NOTES.md:44-45 — `- \`alignEvent = 'goCue'\`` / `- \`tmin = -2.5\`, \`tmax = 2.5\` (seconds from goCue)`
> README.md:38 — `| \`input\` | list of 44 arrays, each: (n_trials, 500, 1) | Time from go cue (seconds) |`
> README.md:44 — `| \`input_names\` | \`['time_from_gocue']\` | Input variable names |`

**Code** (convert_data.py:91-94, 636-637, 673, 693-695):
```python
ALIGN_EVENT = 'goCue'
TMIN = -2.5  # seconds
TMAX = 2.5   # seconds
DT = 1.0 / 100  # 10 ms bins
...
    ev = bp['ev']
    goCue = np.array(ev['goCue']).flatten()
...
    align_times_all = goCue  # for all trials
...
    edges = np.arange(TMIN, TMAX + DT, DT)
    time_axis = edges[:-1] + DT / 2
    n_time = len(time_axis)
```

**What this does:** The trial produces a single input variable, `input_names = ['time_from_gocue']`. It is not read from a raw data field directly; it is the bin-center time axis constructed from the constants `TMIN`, `TMAX`, `DT`, which is the same axis the spikes are binned on after subtracting the raw per-trial `obj.bp.ev.goCue` time.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-b. What processing is involved in computing `input` *time_from_go_cue*?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:192 — `| time from goCue (s) | input[0] | Continuous time axis | N/A | Ranges from -2.5 to 2.5 s |`
> CONVERSION_NOTES.md:275 — `- **500 time bins** per trial (-2.5 to 2.5 s from goCue at 10ms resolution)`
> README.md:19 — `| Time bins per trial | 500 (-2.5 to +2.5 s from go cue, 10 ms bins) |`

**Code** (convert_data.py:693-695, 774-784):
```python
    edges = np.arange(TMIN, TMAX + DT, DT)
    time_axis = edges[:-1] + DT / 2
    n_time = len(time_axis)
...
    # Build trial-level data structures
    neural_trials = []
    input_trials = []
    output_trials = []

    for t_idx in range(n_valid):
        # Neural: (n_neurons, n_time)
        neural_trials.append(trialdat_valid[:, :, t_idx].T.astype(np.float32))

        # Input: time from goCue in seconds (1, n_time)
        input_trials.append(time_axis.reshape(1, -1).astype(np.float32))
```

**What this does:** `edges` spans TMIN=-2.5 to TMAX=2.5 s in DT=0.01 s steps and `time_axis` takes the bin centers (edges shifted by DT/2), giving 500 values from -2.495 to 2.495 s. The identical `time_axis` vector is reshaped to (1, n_time), cast to float32, and appended once per valid trial, so every trial in a session carries the same input row.

**Rating:** match

**Note:** _(no note)_

---

## Q 3-c. How is `input` *time_from_go_cue* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> CONVERSION_NOTES.md:56 — `4. Align spikes to goCue: \`trialtm_aligned = trialtm - goCue_time\``
> CONVERSION_NOTES.md:142-143 — `- Align to goCue` / `- Time window: -2.5 to 2.5 s from goCue`
> README.md:64 — `3. Align spike times to go cue onset`

**Code** (convert_data.py:711-720, 781-784):
```python
            for j in range(ntrials_total):
                trial_num = j + 1
                spk_mask = trial_arr == trial_num
                if not np.any(spk_mask):
                    continue

                aligned = trialtm_arr[spk_mask] - align_times_all[j]
                counts, _ = np.histogram(aligned, bins=edges)
                fr = counts.astype(np.float32) / DT
                trialdat[:, neuron_offset + i, j] = causal_gaussian_smooth(fr, SMOOTH_WINDOW, BC_TYPE)
...
        # Neural: (n_neurons, n_time)
        neural_trials.append(trialdat_valid[:, :, t_idx].T.astype(np.float32))

        # Input: time from goCue in seconds (1, n_time)
        input_trials.append(time_axis.reshape(1, -1).astype(np.float32))
```

**What this does:** Alignment is by construction: spikes are histogrammed into `edges` after subtracting each trial's `goCue` time, and the input is the bin-center vector of those same `edges`. Neural arrays are (n_neurons, 500) and the input is (1, 500) over the identical bin grid, so index k of the input is the time offset from go cue of bin k of the neural data. `metadata['temporal_alignment_event'] = 'Go cue onset'` (convert_data.py:1013).

**Rating:** match

**Note:** _(no note)_

---

## Q 4-a. What variables in the raw data is `output` *lick_direction* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:193):
> obj.bp.R/L + hit/miss -> output[0]: lick_direction; R&hit or L&miss -> right(1); L&hit or R&miss -> left(0)

**Code** (convert_data.py:640-643, 741-742):
```python
R = np.array(bp['R']).flatten().astype(bool)
L = np.array(bp['L']).flatten().astype(bool)
hit = np.array(bp['hit']).flatten().astype(bool)
miss = np.array(bp['miss']).flatten().astype(bool)
...
lick_right = (R & hit) | (L & miss)
lick_direction = lick_right[valid_trials].astype(np.int32)
```

**What this does:** Derived from `bp.R`, `bp.L`, `bp.hit`, `bp.miss`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 4-b. What processing is involved in computing `output` *lick_direction*?

**Notes excerpt** (CONVERSION_NOTES.md:193):
> R&hit or L&miss -> right(1); L&hit or R&miss -> left(0)

**Code** (convert_data.py:741-742, 788-789):
```python
lick_right = (R & hit) | (L & miss)
lick_direction = lick_right[valid_trials].astype(np.int32)
...
out[0, :] = lick_direction[t_idx]  # broadcast per-trial to time
```

**What this does:** A boolean per trial: True (=1, "right") if (right-cue, correct) or (left-cue, error); else 0 ("left"). Per-trial scalar broadcast across all time bins.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-a. What variables in the raw data is `output` *context* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:194):
> obj.bp.autowater -> output[1]: context; autowater=1 -> WC(0); autowater=0 -> DR(1)

**Code** (convert_data.py:645, 745):
```python
autowater = np.array(bp['autowater']).flatten().astype(bool)
...
context = (~autowater[valid_trials]).astype(np.int32)
```

**What this does:** Derived solely from `bp.autowater`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 5-b. What processing is involved in computing `output` *context*?

**Notes excerpt** (CONVERSION_NOTES.md:194):
> autowater=1 -> WC(0); autowater=0 -> DR(1)

**Code** (convert_data.py:745, 790):
```python
context = (~autowater[valid_trials]).astype(np.int32)
...
out[1, :] = context[t_idx]
```

**What this does:** Logical NOT of `autowater`: 1 = DR (delayed-response), 0 = WC (water-cued). Output values list is `['WC', 'DR']`.

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-a. What variables in the raw data is `output` *outcome* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:195):
> obj.bp.hit/miss -> output[2]: outcome; hit -> correct(1); miss -> incorrect(0)

**Code** (convert_data.py:642, 748):
```python
hit = np.array(bp['hit']).flatten().astype(bool)
...
outcome = hit[valid_trials].astype(np.int32)
```

**What this does:** Derived from `bp.hit` (with `bp.miss` used implicitly via the hit|miss filter).

**Rating:** match

**Note:** _(no note)_---

---

## Q 6-b. What processing is involved in computing `output` *outcome*?

**Notes excerpt** (CONVERSION_NOTES.md:195):
> hit -> correct(1); miss -> incorrect(0)

**Code** (convert_data.py:748, 791):
```python
outcome = hit[valid_trials].astype(np.int32)
...
out[2, :] = outcome[t_idx]
```

**What this does:** `hit` boolean cast to int32 (1=correct, 0=incorrect). Per-trial scalar.

**Rating:** match

**Note:** _(no note)_---

---

## Q 7-a. What variables in the raw data is `output` *tongue_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:196):
> tongue velocity from DLC -> output[3]: tongue_velocity; Compute from DLC, discretize at 50th percentile per session

**Code** (convert_data.py:457-484):
```python
traj_bottom = obj['traj'][1]  # bottom cam
feat_names_raw = traj_bottom['featNames'][0]
...
for i, name in enumerate(feat_names):
    if name == 'top_tongue':
        tongue_idx = i; break
...
ts = np.array(traj_bottom['ts'][trix])
...
x = ts[:, 0, tongue_idx].copy(); y = ts[:, 1, tongue_idx].copy()
```

**What this does:** Derived from the bottom-camera DLC trajectories (`obj.traj[1].ts`), specifically the `top_tongue` feature's x,y coordinates per frame, plus `frameTimes` and `sglx.bitcode`/`fs` for video offset.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 7-b. What processing is involved in computing `output` *tongue_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md:235):
> Tongue NaN values NOT filled (per paper methods), velocity computed only where visible

**Code** (convert_data.py:489-522):
```python
valid = ~np.isnan(x) & ~np.isnan(y)
if np.sum(valid) >= 2:
    vx_all = np.gradient(x) * VIDEO_FR
    vy_all = np.gradient(y) * VIDEO_FR
    speed = np.sqrt(vx_all**2 + vy_all**2)
    speed[~valid] = np.nan
...
f_interp = interp1d(old_time, speed, kind='linear', bounds_error=False, fill_value=np.nan)
tongue_vel[:, trix] = f_interp(time_axis)
...
tongue_vel = np.nan_to_num(tongue_vel, nan=0.0)
# discretize at 50th percentile per session
```

**What this does:** Compute frame-rate-scaled gradient of x and y to get vx, vy; magnitude = speed; NaN preserved where tongue not visible. Linearly interpolated to neural time axis, NaNs set to 0, then `discretize_per_session` thresholds at the 50th percentile -> 0/1.

**Rating:** ok

**Note:** _(no note)_---

---

## Q 7-d. How is `output` *tongue_velocity* aligned with the neural data?

**Notes excerpt** (none beyond above).

**Code** (convert_data.py:508-519, 754-756, 792):
```python
ft = np.array(traj_bottom['frameTimes'][trix]).flatten()
old_time = ft - vidshift - align_times[trix]
...
f_interp = interp1d(old_time, speed, kind='linear', bounds_error=False, fill_value=np.nan)
tongue_vel[:, trix] = f_interp(time_axis)
...
tongue_vel = compute_tongue_velocity(obj, align_times_all, time_axis, vidshift, ntrials_total)
tongue_vel_valid = tongue_vel[:, valid_trials]
tongue_vel_disc = discretize_per_session(tongue_vel_valid)
...
out[3, :] = tongue_vel_disc[:, t_idx]
```

**What this does:** Frame times are corrected by `vidshift = bitcode/fs - bp.ev.bitStart` and the trial's `goCue`, then linearly interpolated onto the neural `time_axis` (10 ms bins, [-2.5, 2.5]s).

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-a. What variables in the raw data is `output` *paw_velocity* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:197):
> paw velocity from DLC -> output[4]: paw_velocity; Compute from DLC, discretize at 50th percentile per session

**Code** (convert_data.py:529-556):
```python
traj_bottom = obj['traj'][1]  # bottom cam
feat_names_raw = traj_bottom['featNames'][0]
...
paw_indices = []
for i, name in enumerate(feat_names):
    if 'paw' in name.lower():
        paw_indices.append(i)
...
ts = np.array(traj_bottom['ts'][trix])
```

**What this does:** Derived from bottom-cam DLC trajectories (`obj.traj[1].ts`) for any feature whose name contains "paw" (typically `top_paw`, `bottom_paw`), plus `frameTimes` and video offset variables.

**Rating:** match

**Note:** _(no note)_---

---

## Q 8-b. What processing is involved in computing `output` *paw_velocity*?

**Notes excerpt** (CONVERSION_NOTES.md:236):
> Paw NaN values filled with nearest neighbor before velocity computation

**Code** (convert_data.py:556-595):
```python
for arr in [x, y]:
    nans = np.isnan(arr)
    if nans.any() and not nans.all():
        valid = np.where(~nans)[0]
        nan_pos = np.where(nans)[0]
        nearest = np.searchsorted(valid, nan_pos).clip(0, len(valid)-1)
        arr[nans] = arr[valid[nearest]]
vx = np.gradient(x) * VIDEO_FR
vy = np.gradient(y) * VIDEO_FR
speeds.append(np.sqrt(vx**2 + vy**2))
...
avg_speed = np.mean(speeds, axis=0)
...
# interp to time_axis, discretize at 50th percentile per session
```

**What this does:** NaNs in paw x/y filled with nearest neighbor; gradient * video_fr gives vx,vy, magnitude is speed. Speeds across paw features averaged. Result interpolated to neural time axis, NaNs filled, then discretized at session 50th percentile.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 8-d. How is `output` *paw_velocity* aligned with the neural data?

**Notes excerpt** (none).

**Code** (convert_data.py:574-585, 759-761, 793):
```python
ft = np.array(traj_bottom['frameTimes'][trix]).flatten()
old_time = ft - vidshift - align_times[trix]
...
f_interp = interp1d(old_time, avg_speed, kind='linear', bounds_error=False, fill_value=np.nan)
paw_vel[:, trix] = f_interp(time_axis)
...
paw_vel = compute_paw_velocity(obj, align_times_all, time_axis, vidshift, ntrials_total)
paw_vel_disc = discretize_per_session(paw_vel_valid)
...
out[4, :] = paw_vel_disc[:, t_idx]
```

**What this does:** Same alignment as tongue velocity: frame times shifted by `vidshift` and per-trial `goCue`, then linearly interpolated to the neural 10 ms time axis.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-a. What variables in the raw data is `output` *motion_energy* derived from?

**Notes excerpt** (CONVERSION_NOTES.md:198):
> motion energy -> output[5]: motion_energy; Load from motionEnergy file, discretize at 50th percentile per session

**Code** (convert_data.py:314-338, 415-422):
```python
me_path = os.path.join(DATA_ROOT, data_dir, f'motionEnergy_{anm}_{date}.mat')
me_file = scipy.io.loadmat(me_path)
me_var = me_file['me']
...
me_data = me_struct['data']
if me_data.dtype.names and 'data' in me_data.dtype.names:
    inner = me_data[0, 0]
    me_raw = inner['data']
...
for trix in range(ntrials):
    me_trial = np.array(me_raw[trix, 0]).flatten()
```

**What this does:** Derived from a separate file `motionEnergy_<anm>_<date>.mat` (`me.data`, a per-trial cell array of (1, nFrames) at 400 Hz), plus `obj.traj[0].frameTimes` and video offset for alignment.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-b. What processing is involved in computing `output` *motion_energy*?

**Notes excerpt** (CONVERSION_NOTES.md:207):
> Motion energy discretization: Per-session 50th percentile threshold on the time-varying signal.

**Code** (convert_data.py:600-616, 764-767):
```python
def discretize_per_session(data_2d, percentile=50):
    all_vals = data_2d[~np.isnan(data_2d)]
    threshold = np.percentile(all_vals, percentile)
    if threshold == 0:
        threshold = np.finfo(np.float32).eps
    result = (data_2d >= threshold).astype(np.int32)
    result[np.isnan(data_2d)] = 0
    return result

if me_raw is not None:
    me_aligned = get_motion_energy_aligned(me_raw, obj, align_times_all, time_axis, vidshift, ntrials_total)
    me_valid = me_aligned[:, valid_trials]
    me_disc = discretize_per_session(me_valid)
```

**What this does:** Raw per-trial motion-energy frames are aligned to the neural time axis via interpolation, NaN gaps filled with nearest values, then thresholded at the per-session 50th percentile to give binary 0/1.

**Rating:** match

**Note:** _(no note)_---

---

## Q 9-d. How is `output` *motion_energy* aligned with the neural data?

**Notes excerpt** (CONVERSION_NOTES.md:64):
> Motion energy aligned: interp1(frameTimes - vidshift - alignTime, me.data, taxis)

**Code** (convert_data.py:421-450, 794):
```python
for trix in range(ntrials):
    me_trial = np.array(me_raw[trix, 0]).flatten()
    ft = np.array(traj_view0['frameTimes'][trix]).flatten()
    old_time = ft - vidshift - align_times[trix]
    if len(old_time) > 1 and len(me_trial) > 1:
        f_interp = interp1d(old_time, me_trial, kind='linear',
                           bounds_error=False, fill_value=np.nan)
        me_aligned[:, trix] = f_interp(time_axis)
# Fill NaN with nearest
...
out[5, :] = me_disc[:, t_idx]
```

**What this does:** Per-trial side-cam frame times shifted by `vidshift` and `goCue` per trial, linearly interpolated to the neural `time_axis`; NaNs filled by nearest valid value, then discretized.

**Rating:** match

**Note:** _(no note)_---

---

## Q 10. How are minor mistakes in the data, e.g. missing data, handled?

**Notes excerpt** (CONVERSION_NOTES.md:292-295):
> Session 36 (JEB24_2023-10-23, 17 neurons): 19 trials with all-zero neural data at end of session ... These are likely recording artifacts; trials retained for completeness.

**Code** (convert_data.py:316-338, 440-449, 558-565, 663-665, 732-734):
```python
if os.path.exists(me_path):
    me_file = scipy.io.loadmat(me_path)
    ...
elif me_var.dtype == object:
    me_raw = me_var
    me_thresh = None
...
# fill NaN with nearest for motion energy
nans = np.isnan(col)
if nans.any() and not nans.all():
    valid_idx = np.where(~nans)[0]; nan_idx = np.where(nans)[0]
    nearest = np.searchsorted(valid_idx, nan_idx).clip(0, len(valid_idx)-1)
    col[nans] = col[valid_idx[nearest]]
...
if n_valid < 2: return None
if n_neurons_final < 10: return None
```

**What this does:** Missing motion-energy file -> output filled with zeros. NaN frames in motion energy/paw filled with nearest neighbor; tongue NaNs intentionally set to 0 (not visible). v5 mat fallback handles non-v7.3 sessions. Try/except guards float conversion of irregular bp fields. Sessions failing the >=2 valid-trial or >=10 neuron threshold are skipped entirely.

**Rating:** match

**Note:** _(no note)_---

---

## Q 11-a. What are the most time-consuming steps of the code?

**Notes excerpt** (CONVERSION_NOTES.md:271):
> 44 sessions processed in 300s

**Code** (convert_data.py:692-725, 751-772):
```python
t_bin_start = time.time()
...
for probe_idx, valid_clu in all_cluster_indices:
    for i, clu_idx in enumerate(valid_clu):
        ...
        for j in range(ntrials_total):
            ...
            counts, _ = np.histogram(aligned, bins=edges)
            ...
            trialdat[:, neuron_offset + i, j] = causal_gaussian_smooth(...)
t_bin = time.time() - t_bin_start
print(f"  Spike binning: {t_bin:.1f}s for {total_neurons} neurons")
...
t_behav = time.time() - t_behav_start
print(f"  Behavioral processing: {t_behav:.1f}s")
```

**What this does:** Internal timers track session loading (`t_load`), spike binning/smoothing (`t_bin`, the largest reported per-session step), and behavioral processing (`t_behav`).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-b. What loops in the code could have been vectorized to improve efficiency?

**Notes excerpt** (none).

**Code** (convert_data.py:707-722, 134-136):
```python
for i, clu_idx in enumerate(valid_clu):
    trial_arr = np.array(clu_probe['trial'][clu_idx]).flatten()
    trialtm_arr = np.array(clu_probe['trialtm'][clu_idx]).flatten()
    for j in range(ntrials_total):
        trial_num = j + 1
        spk_mask = trial_arr == trial_num
        ...
        counts, _ = np.histogram(aligned, bins=edges)
        fr = counts.astype(np.float32) / DT
        trialdat[:, neuron_offset + i, j] = causal_gaussian_smooth(fr, SMOOTH_WINDOW, BC_TYPE)
...
for j in range(x_filt.shape[1]):
    out[:, j] = np.convolve(x_filt[:, j], kern, mode='same')
```

**What this does:** Nested neuron x trial loop in `process_session` calls histogram and smoothing per (neuron, trial). The inner per-channel `np.convolve` loop in `causal_gaussian_smooth` and per-trial loops in tongue/paw/ME computation are also Python-level loops.

**Rating:** concerning

**Note:** _(no note)_---

---

## Q 11-c. What processing does the code repeat multiple times?

**Notes excerpt** (none).

**Code** (convert_data.py:421-449, 508-519, 574-585, 587-596):
```python
# Same alignment/interpolation pattern repeated for ME, tongue, and paw:
ft = np.array(traj_view['frameTimes'][trix]).flatten()
old_time = ft - vidshift - align_times[trix]
f_interp = interp1d(old_time, signal, kind='linear', bounds_error=False, fill_value=np.nan)
output[:, trix] = f_interp(time_axis)
# Then per-trial NaN-fill via searchsorted nearest, repeated in ME and paw
```

**What this does:** Frame-time shifting + interp1d construction + nearest-NaN filling logic is duplicated in `get_motion_energy_aligned`, `compute_tongue_velocity`, `compute_paw_velocity`. There is also a dead helper `align_and_bin_spikes` that is not used (logic is duplicated inline in `process_session`).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-d. What unnecessary processing does the code do that is discarded in downstream analyses?

**Notes excerpt** (none).

**Code** (convert_data.py:701-720, 727-737, 798-803, 827-914):
```python
trialdat = np.zeros((n_time, total_neurons, ntrials_total), dtype=np.float32)
# computes spikes for ALL trials, then:
trialdat_valid = trialdat[:, :, valid_trials]
...
if show_processing and n_valid > 0:
    plot_processing(...)  # only if --show-processing flag
```

**What this does:** Spike binning + smoothing is done across all `ntrials_total` (including early/stim/no-response trials), then only `valid_trials` are kept. The `plot_processing` and per-session matplotlib figure-creation work is only used when the optional flag is set (no downstream effect on `.pkl`).

**Rating:** ok

**Note:** _(no note)_---

---

## Q 11-e. How is memory usage optimized?

**Notes excerpt** (none).

**Code** (convert_data.py:380, 417, 481, 547, 701, 1037-1038):
```python
trialdat = np.zeros((n_time, n_neurons, ntrials), dtype=np.float32)
me_aligned = np.zeros((len(time_axis), ntrials), dtype=np.float32)
tongue_vel = np.full(..., np.nan, dtype=np.float32)
paw_vel = np.zeros((len(time_axis), ntrials), dtype=np.float32)
...
with open(args.output, 'wb') as f:
    pickle.dump(data, f, protocol=4)
```

**What this does:** Arrays use float32 (and int32 for outputs) rather than float64; pickle protocol=4 is used to support large objects. No streaming/chunking — the full dataset (1,461 MB) is held in memory before pickling.

**Rating:** match

**Note:** _(no note)_---

---
