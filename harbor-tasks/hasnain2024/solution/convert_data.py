#!/usr/bin/env python3
"""
Convert Hasnain et al. 2024 data to decoder-compatible format.

This script converts the neural and behavioral data from the paper
"Separating cognitive and motor processes in the behaving mouse"
to the standardized decoder format.

Usage:
    python -u convert_data.py <output_file.pkl> [--sample] [--show-processing]
"""

import argparse
import pickle
import time
from pathlib import Path
import numpy as np
import h5py
from scipy import io as sio
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import warnings

# Parameters matching the paper's processing
PARAMS = {
    'align_event': 'goCue',
    'tmin': -2.5,  # seconds before alignment
    'tmax': 2.5,   # seconds after alignment
    'dt': 0.01,    # 10 ms bins
    'smooth_sigma_ms': 15,  # smoothing kernel in ms
    'low_fr_threshold': 1.0,  # Hz
    'video_offset': 0.5,  # seconds to subtract from video timestamps
    'video_fps': 400,  # Hz
    'exclude_quality': {'garbage', 'gabrga', 'noisy', 'real?', ''},
}


def normalize_quality(q):
    """Normalize quality string to handle case variations and typos."""
    q = q.strip().lower()
    if q == 'gabrga' or q == 'gabrag':
        return 'garbage'
    if q == 'ood':
        return 'good'
    return q


def causal_gaussian_smooth(data, sigma_bins):
    """
    Apply causal Gaussian smoothing (only uses past data).

    Args:
        data: array of shape (n_neurons, n_timepoints) or (n_timepoints,)
        sigma_bins: sigma in bins (not ms)

    Returns:
        Smoothed data of same shape
    """
    if sigma_bins <= 0:
        return data

    # Create causal kernel (only past values)
    kernel_size = int(4 * sigma_bins) + 1
    x = np.arange(kernel_size)
    kernel = np.exp(-x**2 / (2 * sigma_bins**2))
    kernel = kernel / kernel.sum()

    # Reverse kernel for causal convolution (past -> present)
    kernel = kernel[::-1]

    if data.ndim == 1:
        return np.convolve(data, kernel, mode='same')
    else:
        result = np.zeros_like(data)
        for i in range(data.shape[0]):
            result[i] = np.convolve(data[i], kernel, mode='same')
        return result


def load_session_data(session_file, motion_energy_file=None):
    """Load data from a single session."""

    session_data = {}

    with h5py.File(session_file, 'r') as hf:
        obj = hf['obj']
        bp = obj['bp']

        # Basic trial info
        session_data['n_trials'] = int(bp['Ntrials'][0, 0])
        session_data['hit'] = bp['hit'][:].flatten().astype(bool)
        session_data['miss'] = bp['miss'][:].flatten().astype(bool)
        session_data['L'] = bp['L'][:].flatten().astype(bool)
        session_data['R'] = bp['R'][:].flatten().astype(bool)
        session_data['autowater'] = bp['autowater'][:].flatten().astype(bool)
        session_data['early'] = bp['early'][:].flatten().astype(bool)

        # Event timing
        ev = bp['ev']
        session_data['goCue'] = ev['goCue'][:].flatten()
        session_data['sample'] = ev['sample'][:].flatten()
        session_data['delay'] = ev['delay'][:].flatten()

        # Load spike data - properly handle HDF5 references
        clu = obj['clu']
        neurons = []

        for i in range(clu.shape[0]):
            for j in range(clu.shape[1]):
                ref = clu[i, j]
                try:
                    probe_obj = hf[ref]
                    if not hasattr(probe_obj, 'keys') or 'quality' not in probe_obj.keys():
                        continue

                    n_neurons_probe = probe_obj['quality'].shape[0]
                    tm_refs = probe_obj['tm'][:]
                    trial_refs = probe_obj['trial'][:]
                    trialtm_refs = probe_obj['trialtm'][:]
                    quality_refs = probe_obj['quality'][:]

                    for neuron_idx in range(n_neurons_probe):
                        # Get quality string
                        qref = quality_refs[neuron_idx, 0]
                        q = hf[qref]
                        qual_str = ''.join([chr(int(c)) for c in q[:].flatten()])
                        qual_str = normalize_quality(qual_str)

                        # Skip excluded quality labels
                        if qual_str in PARAMS['exclude_quality']:
                            continue

                        # Dereference spike data for this neuron
                        tm_data = hf[tm_refs[neuron_idx, 0]][:].flatten()
                        trial_data = hf[trial_refs[neuron_idx, 0]][:].flatten().astype(int)
                        trialtm_data = hf[trialtm_refs[neuron_idx, 0]][:].flatten()

                        neuron = {
                            'trialtm': trialtm_data,  # within-trial times
                            'trial': trial_data,       # trial indices (1-indexed)
                            'quality': qual_str,
                            'n_spikes': len(tm_data),
                        }
                        neurons.append(neuron)
                except Exception as e:
                    pass

        session_data['neurons'] = neurons

        # Load trajectory data
        # Structure: traj[view, 0] -> Group with keys ts, frameTimes, featNames
        # Each key is (n_trials, 1) array of references
        traj = obj['traj']
        session_data['traj'] = []

        for view_idx in range(traj.shape[0]):
            view_ref = traj[view_idx, 0]
            view_obj = hf[view_ref]

            trials_data = []
            feat_names = []

            # Get feature names from first trial
            try:
                fn_refs = view_obj['featNames']
                if fn_refs.shape[0] > 0:
                    # Dereference first trial's featNames
                    first_fn = hf[fn_refs[0, 0]]
                    for i in range(first_fn.shape[1]):
                        name_ref = first_fn[0, i]
                        name_obj = hf[name_ref]
                        name_str = ''.join([chr(int(c)) for c in name_obj[:].flatten()])
                        feat_names.append(name_str)
            except:
                feat_names = []

            # Get ts and frameTimes arrays
            ts_refs = view_obj['ts']
            ft_refs = view_obj['frameTimes']
            n_trials_traj = ts_refs.shape[0]

            # Load per-trial data
            for trial_idx in range(n_trials_traj):
                try:
                    ts = hf[ts_refs[trial_idx, 0]][:]  # (n_feat, 3, n_frames)
                    frame_times = hf[ft_refs[trial_idx, 0]][:].flatten()

                    trials_data.append({
                        'ts': ts,
                        'frameTimes': frame_times,
                    })
                except:
                    trials_data.append(None)

            session_data['traj'].append({
                'featNames': feat_names,
                'trials': trials_data
            })

    # Load motion energy from separate file
    if motion_energy_file and motion_energy_file.exists():
        try:
            me_data = sio.loadmat(motion_energy_file)
            if 'me' in me_data:
                me = me_data['me']
                if hasattr(me, 'dtype') and 'data' in me.dtype.names:
                    # me.data is a cell array of per-trial motion energy
                    # Shape is (n_trials, 1), each element is (1, n_frames)
                    me_trials = me['data'][0, 0]

                    # Handle nested struct format (some sessions have extra nesting)
                    if hasattr(me_trials, 'dtype') and me_trials.dtype.names and 'data' in me_trials.dtype.names:
                        # Nested structure: me['data'][0,0]['data'][0,0]
                        me_trials = me_trials['data'][0, 0]

                    session_data['motion_energy'] = []
                    for t in range(me_trials.shape[0]):
                        trial_me = me_trials[t, 0].flatten()
                        session_data['motion_energy'].append(trial_me)
                else:
                    session_data['motion_energy'] = None
            else:
                session_data['motion_energy'] = None
        except Exception as e:
            print(f"  Warning: Could not load motion energy: {e}")
            session_data['motion_energy'] = None
    else:
        session_data['motion_energy'] = None

    return session_data


def bin_spikes_for_session(session_data):
    """
    Bin spike times into firing rates aligned to goCue.

    Returns:
        neural_data: list of (n_neurons, n_timepoints) arrays for each trial
        time_axis: time axis relative to goCue
        neuron_mean_fr: mean firing rate for each neuron
    """
    tmin = PARAMS['tmin']
    tmax = PARAMS['tmax']
    dt = PARAMS['dt']
    n_bins = int((tmax - tmin) / dt)
    time_axis = np.linspace(tmin + dt/2, tmax - dt/2, n_bins)
    bin_edges = np.linspace(tmin, tmax, n_bins + 1)

    n_trials = session_data['n_trials']
    neurons = session_data['neurons']
    goCue = session_data['goCue']

    if len(neurons) == 0:
        return [np.zeros((0, n_bins)) for _ in range(n_trials)], time_axis, np.array([])

    n_neurons = len(neurons)

    # Initialize spike counts per trial
    trial_spike_counts = np.zeros((n_trials, n_neurons, n_bins))

    for neuron_idx, neuron in enumerate(neurons):
        trialtm = neuron['trialtm']  # spike times relative to trial start
        trial_nums = neuron['trial']  # 1-indexed trial numbers

        for spike_idx in range(len(trialtm)):
            trial_idx = trial_nums[spike_idx] - 1  # Convert to 0-indexed

            if trial_idx < 0 or trial_idx >= n_trials:
                continue

            # Get spike time relative to goCue
            go_cue_time = goCue[trial_idx]
            spike_time_rel_gocue = trialtm[spike_idx] - go_cue_time

            # Find bin
            if spike_time_rel_gocue < tmin or spike_time_rel_gocue >= tmax:
                continue

            bin_idx = int((spike_time_rel_gocue - tmin) / dt)
            if 0 <= bin_idx < n_bins:
                trial_spike_counts[trial_idx, neuron_idx, bin_idx] += 1

    # Convert to firing rates (spikes/s)
    firing_rates = trial_spike_counts / dt

    # Apply causal Gaussian smoothing
    sigma_bins = PARAMS['smooth_sigma_ms'] / (dt * 1000)  # Convert ms to bins
    for trial_idx in range(n_trials):
        firing_rates[trial_idx] = causal_gaussian_smooth(firing_rates[trial_idx], sigma_bins)

    # Calculate mean firing rate per neuron (across all trials and time)
    neuron_mean_fr = np.mean(np.mean(firing_rates, axis=0), axis=1)

    # Convert to list of (n_neurons, n_bins) arrays
    neural_data = [firing_rates[t] for t in range(n_trials)]

    return neural_data, time_axis, neuron_mean_fr


def compute_velocity(x, y, dt):
    """Compute velocity magnitude from x, y positions."""
    # Handle NaN values
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    # Compute derivatives
    vx = np.gradient(x) / dt
    vy = np.gradient(y) / dt

    # Compute magnitude
    v_mag = np.sqrt(vx**2 + vy**2)

    return v_mag


def extract_kinematics(session_data, time_axis, trial_idx):
    """
    Extract tongue and paw velocity for a single trial.

    Returns:
        tongue_velocity: array of shape (n_timepoints,)
        paw_velocity: array of shape (n_timepoints,)
    """
    n_bins = len(time_axis)
    dt = PARAMS['dt']
    video_dt = 1.0 / PARAMS['video_fps']

    # Initialize with NaN
    tongue_velocity = np.full(n_bins, np.nan)
    paw_velocity = np.full(n_bins, np.nan)

    goCue = session_data['goCue'][trial_idx]

    # Get trajectory data
    if len(session_data['traj']) < 2:
        return tongue_velocity, paw_velocity

    # View 0 = side cam (has tongue, jaw, nose)
    # View 1 = bottom cam (has tongue, paw)
    side_cam = session_data['traj'][0]
    bottom_cam = session_data['traj'][1]

    # Get tongue from side cam (view 0)
    if trial_idx < len(side_cam['trials']) and side_cam['trials'][trial_idx] is not None:
        trial_data = side_cam['trials'][trial_idx]
        ts = trial_data['ts']  # (n_feat, 3, n_frames)
        frame_times = trial_data['frameTimes'] - PARAMS['video_offset']

        # Find tongue feature
        feat_names = side_cam['featNames']
        tongue_idx = None
        for i, name in enumerate(feat_names):
            if 'tongue' in name.lower() and 'left' not in name.lower() and 'right' not in name.lower():
                tongue_idx = i
                break

        if tongue_idx is not None and ts.shape[2] > 0:
            x = ts[tongue_idx, 0, :]  # x positions
            y = ts[tongue_idx, 1, :]  # y positions

            # Compute velocity
            v_tongue = compute_velocity(x, y, video_dt)

            # Align to goCue and resample to time_axis
            aligned_times = frame_times - goCue

            # Interpolate to time_axis
            valid = ~np.isnan(v_tongue)
            if np.sum(valid) > 2:
                try:
                    interp_func = interp1d(aligned_times[valid], v_tongue[valid],
                                          kind='linear', fill_value=np.nan, bounds_error=False)
                    tongue_velocity = interp_func(time_axis)
                except:
                    pass

    # Get paw from bottom cam (view 1)
    if trial_idx < len(bottom_cam['trials']) and bottom_cam['trials'][trial_idx] is not None:
        trial_data = bottom_cam['trials'][trial_idx]
        ts = trial_data['ts']
        frame_times = trial_data['frameTimes'] - PARAMS['video_offset']

        # Find paw feature (top_paw or bottom_paw)
        feat_names = bottom_cam['featNames']
        paw_idx = None
        for i, name in enumerate(feat_names):
            if 'paw' in name.lower():
                paw_idx = i
                break

        if paw_idx is not None and ts.shape[2] > 0:
            x = ts[paw_idx, 0, :]
            y = ts[paw_idx, 1, :]

            v_paw = compute_velocity(x, y, video_dt)

            aligned_times = frame_times - goCue

            valid = ~np.isnan(v_paw)
            if np.sum(valid) > 2:
                try:
                    interp_func = interp1d(aligned_times[valid], v_paw[valid],
                                          kind='linear', fill_value=np.nan, bounds_error=False)
                    paw_velocity = interp_func(time_axis)
                except:
                    pass

    return tongue_velocity, paw_velocity


def extract_motion_energy(session_data, time_axis, trial_idx):
    """
    Extract motion energy for a single trial.

    Returns:
        motion_energy: array of shape (n_timepoints,)
    """
    n_bins = len(time_axis)
    motion_energy = np.full(n_bins, np.nan)

    if session_data['motion_energy'] is None:
        return motion_energy

    if trial_idx >= len(session_data['motion_energy']):
        return motion_energy

    me_trial = session_data['motion_energy'][trial_idx]
    if len(me_trial) == 0:
        return motion_energy

    # Motion energy is at 400 Hz, need to align to goCue and resample
    video_dt = 1.0 / PARAMS['video_fps']
    goCue = session_data['goCue'][trial_idx]

    # Get trajectory frame times to align motion energy
    # Motion energy uses same timing as video
    if len(session_data['traj']) > 0:
        side_cam = session_data['traj'][0]
        if trial_idx < len(side_cam['trials']) and side_cam['trials'][trial_idx] is not None:
            frame_times = side_cam['trials'][trial_idx]['frameTimes'] - PARAMS['video_offset']

            # Motion energy should have same length as frames
            if len(me_trial) == len(frame_times):
                aligned_times = frame_times - goCue

                valid = ~np.isnan(me_trial)
                if np.sum(valid) > 2:
                    try:
                        interp_func = interp1d(aligned_times[valid], me_trial[valid],
                                              kind='linear', fill_value=np.nan, bounds_error=False)
                        motion_energy = interp_func(time_axis)
                    except:
                        pass
            else:
                # Assume motion energy starts at same time as trial
                # Create time axis for motion energy
                me_times = np.arange(len(me_trial)) * video_dt
                me_times_aligned = me_times - goCue

                try:
                    interp_func = interp1d(me_times_aligned, me_trial,
                                          kind='linear', fill_value=np.nan, bounds_error=False)
                    motion_energy = interp_func(time_axis)
                except:
                    pass

    return motion_energy


def process_session(session_info, show_processing=False, session_idx=0):
    """Process a single session and return converted data."""

    print(f"Processing {session_info['subject']}_{session_info['date']}...")
    t0 = time.time()

    # Load raw data
    session_data = load_session_data(
        session_info['file'],
        session_info['motion_energy_file']
    )
    print(f"  Loaded in {time.time() - t0:.1f}s")
    print(f"  Trials: {session_data['n_trials']}, Neurons (quality-filtered): {len(session_data['neurons'])}")

    if len(session_data['neurons']) == 0:
        print("  Skipping session - no neurons after quality filtering")
        return None

    # Bin spikes
    t1 = time.time()
    neural_data, time_axis, neuron_mean_fr = bin_spikes_for_session(session_data)
    print(f"  Binned spikes in {time.time() - t1:.1f}s")

    # Apply low firing rate threshold
    low_fr_mask = neuron_mean_fr >= PARAMS['low_fr_threshold']
    n_kept = np.sum(low_fr_mask)
    print(f"  Neurons after FR filter: {n_kept}/{len(neuron_mean_fr)}")

    if n_kept == 0:
        print("  Skipping session - no neurons after FR filtering")
        return None

    # Filter neural data
    for trial_idx in range(len(neural_data)):
        neural_data[trial_idx] = neural_data[trial_idx][low_fr_mask]

    # Extract behavioral variables
    n_trials = session_data['n_trials']
    n_bins = len(time_axis)

    # Per-trial variables
    lick_direction = np.zeros(n_trials, dtype=int)  # L=0, R=1
    lick_direction[session_data['R']] = 1

    behavioral_context = np.ones(n_trials, dtype=int)  # DR=1
    behavioral_context[session_data['autowater']] = 0  # WC=0

    outcome = np.zeros(n_trials, dtype=int)  # miss=0
    outcome[session_data['hit']] = 1  # hit=1

    # Time-varying variables
    tongue_velocities = []
    paw_velocities = []
    motion_energies = []

    for trial_idx in range(n_trials):
        tongue_v, paw_v = extract_kinematics(session_data, time_axis, trial_idx)
        me = extract_motion_energy(session_data, time_axis, trial_idx)

        tongue_velocities.append(tongue_v)
        paw_velocities.append(paw_v)
        motion_energies.append(me)

    # Compute per-session thresholds (50th percentile) for discretization
    tongue_valid = [v[~np.isnan(v)] for v in tongue_velocities if np.any(~np.isnan(v))]
    paw_valid = [v[~np.isnan(v)] for v in paw_velocities if np.any(~np.isnan(v))]
    me_valid = [v[~np.isnan(v)] for v in motion_energies if np.any(~np.isnan(v))]

    all_tongue_v = np.concatenate(tongue_valid) if len(tongue_valid) > 0 else np.array([])
    all_paw_v = np.concatenate(paw_valid) if len(paw_valid) > 0 else np.array([])
    all_me = np.concatenate(me_valid) if len(me_valid) > 0 else np.array([])

    tongue_threshold = np.percentile(all_tongue_v, 50) if len(all_tongue_v) > 0 else 0
    paw_threshold = np.percentile(all_paw_v, 50) if len(all_paw_v) > 0 else 0
    me_threshold = np.percentile(all_me, 50) if len(all_me) > 0 else 0

    print(f"  Thresholds - tongue: {tongue_threshold:.2f}, paw: {paw_threshold:.2f}, ME: {me_threshold:.2f}")

    # Discretize
    tongue_velocity_discrete = []
    paw_velocity_discrete = []
    motion_energy_discrete = []

    for trial_idx in range(n_trials):
        tv = tongue_velocities[trial_idx]
        pv = paw_velocities[trial_idx]
        me = motion_energies[trial_idx]

        # Discretize: 0 if < threshold, 1 if >= threshold
        # Handle NaN by setting to 0 (below threshold)
        tv_d = np.zeros(n_bins, dtype=int)
        tv_d[~np.isnan(tv) & (tv >= tongue_threshold)] = 1

        pv_d = np.zeros(n_bins, dtype=int)
        pv_d[~np.isnan(pv) & (pv >= paw_threshold)] = 1

        me_d = np.zeros(n_bins, dtype=int)
        me_d[~np.isnan(me) & (me >= me_threshold)] = 1

        tongue_velocity_discrete.append(tv_d)
        paw_velocity_discrete.append(pv_d)
        motion_energy_discrete.append(me_d)

    # Filter trials - exclude early licks
    valid_trials = ~session_data['early']
    n_valid = np.sum(valid_trials)
    print(f"  Valid trials (excluding early): {n_valid}/{n_trials}")

    if n_valid == 0:
        print("  Skipping session - no valid trials")
        return None

    # Apply trial filtering
    valid_indices = np.where(valid_trials)[0]

    neural_filtered = [neural_data[i] for i in valid_indices]
    lick_direction_filtered = lick_direction[valid_indices]
    behavioral_context_filtered = behavioral_context[valid_indices]
    outcome_filtered = outcome[valid_indices]
    tongue_velocity_filtered = [tongue_velocity_discrete[i] for i in valid_indices]
    paw_velocity_filtered = [paw_velocity_discrete[i] for i in valid_indices]
    motion_energy_filtered = [motion_energy_discrete[i] for i in valid_indices]

    # Create input (time axis) - same for all trials
    input_time = time_axis.reshape(1, -1)

    # Assemble trial-level data
    trial_neural = neural_filtered
    trial_input = [input_time.copy() for _ in range(n_valid)]
    trial_output = []

    for trial_idx in range(n_valid):
        # Stack outputs: (n_outputs, n_timepoints) for time-varying, (n_outputs,) for per-trial
        # Per-trial: lick_direction, behavioral_context, outcome
        # Time-varying: tongue_velocity, paw_velocity, motion_energy

        # Create output array - mix of per-trial and time-varying
        # Per spec: output can be (n_output, n_timepoints) or (n_output,)
        # We'll use (n_output, n_timepoints) and repeat per-trial values

        output = np.zeros((6, n_bins), dtype=int)
        output[0, :] = lick_direction_filtered[trial_idx]  # Constant across time
        output[1, :] = behavioral_context_filtered[trial_idx]
        output[2, :] = outcome_filtered[trial_idx]
        output[3, :] = tongue_velocity_filtered[trial_idx]
        output[4, :] = paw_velocity_filtered[trial_idx]
        output[5, :] = motion_energy_filtered[trial_idx]

        trial_output.append(output)

    # Plot processing visualization if requested
    if show_processing and session_idx < 2:
        plot_processing(session_info, session_data, time_axis, neural_filtered,
                       tongue_velocities, paw_velocities, motion_energies,
                       valid_indices, tongue_threshold, paw_threshold, me_threshold)

    # Create brain region index (all ALM)
    n_neurons_final = neural_filtered[0].shape[0]
    brain_region_idx = np.zeros(n_neurons_final, dtype=int)  # All point to index 0 (ALM)

    result = {
        'neural': trial_neural,
        'input': trial_input,
        'output': trial_output,
        'brain_region_idx': brain_region_idx,
        'n_neurons': n_neurons_final,
        'n_trials': n_valid,
    }

    return result


def plot_processing(session_info, session_data, time_axis, neural_filtered,
                   tongue_velocities, paw_velocities, motion_energies,
                   valid_indices, tongue_threshold, paw_threshold, me_threshold):
    """Plot processing visualization for verification."""

    fig, axes = plt.subplots(3, 2, figsize=(14, 10))

    # Plot 1: Example neural PSTH
    ax = axes[0, 0]
    if len(neural_filtered) > 0 and neural_filtered[0].shape[0] > 0:
        # Average across first 10 trials
        n_trials_plot = min(10, len(neural_filtered))
        mean_fr = np.mean([neural_filtered[i] for i in range(n_trials_plot)], axis=0)
        # Plot first 5 neurons
        n_neurons_plot = min(5, mean_fr.shape[0])
        for i in range(n_neurons_plot):
            ax.plot(time_axis, mean_fr[i], label=f'Neuron {i}')
        ax.axvline(0, color='k', linestyle='--', label='Go cue')
        ax.set_xlabel('Time from go cue (s)')
        ax.set_ylabel('Firing rate (Hz)')
        ax.set_title('Example PSTHs')
        ax.legend(fontsize=8)

    # Plot 2: Event timing
    ax = axes[0, 1]
    sample_times = session_data['sample'] - session_data['goCue']
    delay_times = session_data['delay'] - session_data['goCue']
    ax.hist(sample_times, bins=30, alpha=0.5, label='Sample')
    ax.hist(delay_times, bins=30, alpha=0.5, label='Delay')
    ax.axvline(0, color='k', linestyle='--', label='Go cue')
    ax.set_xlabel('Time from go cue (s)')
    ax.set_ylabel('Count')
    ax.set_title('Event timing distribution')
    ax.legend()

    # Plot 3: Tongue velocity distribution
    ax = axes[1, 0]
    all_tv = np.concatenate([v[~np.isnan(v)] for v in tongue_velocities if np.any(~np.isnan(v))])
    if len(all_tv) > 0:
        ax.hist(all_tv, bins=50, alpha=0.7)
        ax.axvline(tongue_threshold, color='r', linestyle='--', label=f'Threshold: {tongue_threshold:.1f}')
        ax.set_xlabel('Tongue velocity')
        ax.set_ylabel('Count')
        ax.set_title('Tongue velocity distribution')
        ax.legend()

    # Plot 4: Paw velocity distribution
    ax = axes[1, 1]
    all_pv = np.concatenate([v[~np.isnan(v)] for v in paw_velocities if np.any(~np.isnan(v))])
    if len(all_pv) > 0:
        ax.hist(all_pv, bins=50, alpha=0.7)
        ax.axvline(paw_threshold, color='r', linestyle='--', label=f'Threshold: {paw_threshold:.1f}')
        ax.set_xlabel('Paw velocity')
        ax.set_ylabel('Count')
        ax.set_title('Paw velocity distribution')
        ax.legend()

    # Plot 5: Motion energy distribution
    ax = axes[2, 0]
    all_me = np.concatenate([v[~np.isnan(v)] for v in motion_energies if np.any(~np.isnan(v))])
    if len(all_me) > 0:
        ax.hist(all_me, bins=50, alpha=0.7)
        ax.axvline(me_threshold, color='r', linestyle='--', label=f'Threshold: {me_threshold:.1f}')
        ax.set_xlabel('Motion energy')
        ax.set_ylabel('Count')
        ax.set_title('Motion energy distribution')
        ax.legend()

    # Plot 6: Trial type breakdown
    ax = axes[2, 1]
    hit = session_data['hit']
    miss = session_data['miss']
    early = session_data['early']
    wc = session_data['autowater']

    labels = ['Hit', 'Miss', 'Early', 'WC']
    counts = [np.sum(hit), np.sum(miss), np.sum(early), np.sum(wc)]
    ax.bar(labels, counts)
    ax.set_ylabel('Count')
    ax.set_title('Trial type breakdown')

    plt.suptitle(f"{session_info['subject']}_{session_info['date']}")
    plt.tight_layout()

    # Save figure
    fig_path = f"preprocessing_demo_{session_info['subject']}_{session_info['date']}.png"
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"  Saved processing plot to {fig_path}")


def get_session_files(data_dir):
    """Get list of session files to process."""
    ephys_dir = data_dir / 'Ephys_Behavior'
    session_files = sorted(ephys_dir.glob('data_structure_*.mat'))

    sessions = []
    for sf in session_files:
        # Parse filename: data_structure_SUBJECT_DATE.mat
        parts = sf.stem.split('_')
        subject = parts[2]
        date = parts[3]

        # Find corresponding motion energy file
        me_file = ephys_dir / f'motionEnergy_{subject}_{date}.mat'

        sessions.append({
            'file': sf,
            'motion_energy_file': me_file if me_file.exists() else None,
            'subject': subject,
            'date': date,
        })

    return sessions


def convert_data(output_file, sample_mode=False, show_processing=False, data_dir=None):
    """Main conversion function."""

    t_start = time.time()
    if data_dir is None:
        data_dir = Path('data')
    sessions = get_session_files(data_dir)

    print(f"Found {len(sessions)} sessions")

    if sample_mode:
        sessions = sessions[:2]
        print(f"Sample mode: processing {len(sessions)} sessions")

    # Process each session
    all_neural = []
    all_input = []
    all_output = []
    all_subject_idx = []
    all_brain_region_idx = []

    subjects = sorted(set(s['subject'] for s in sessions))
    subject_to_idx = {s: i for i, s in enumerate(subjects)}

    total_trials = 0
    total_neurons = 0

    for session_idx, session_info in enumerate(sessions):
        result = process_session(session_info, show_processing, session_idx)

        if result is not None:
            all_neural.append(result['neural'])
            all_input.append(result['input'])
            all_output.append(result['output'])
            all_subject_idx.append(subject_to_idx[session_info['subject']])
            all_brain_region_idx.append(result['brain_region_idx'])

            total_trials += result['n_trials']
            total_neurons += result['n_neurons']

    print(f"\n{'='*60}")
    print(f"Conversion Summary")
    print(f"{'='*60}")
    print(f"Sessions processed: {len(all_neural)}")
    print(f"Total trials: {total_trials}")
    print(f"Total neurons: {total_neurons}")
    print(f"Total time: {time.time() - t_start:.1f}s")

    # Assemble output structure
    data = {
        'neural': all_neural,
        'input': all_input,
        'output': all_output,
        'subjects': subjects,
        'subject_idx': np.array(all_subject_idx),
        'brain_regions': ['ALM'],
        'brain_region_idx': all_brain_region_idx,
        'input_names': ['time'],
        'output_names': ['lick_direction', 'behavioral_context', 'outcome',
                        'tongue_velocity', 'paw_velocity', 'motion_energy'],
        'output_values': [
            ['left', 'right'],
            ['WC', 'DR'],
            ['incorrect', 'correct'],
            ['low', 'high'],
            ['low', 'high'],
            ['low', 'high'],
        ],
        'metadata': {
            'time_bin_size': PARAMS['dt'] * 1000,  # Convert to ms
            'temporal_alignment_event': 'go cue onset',
            'off_start': PARAMS['tmin'],
            'off_end': PARAMS['tmax'],
            'task_description': 'Delayed-response and water-cued licking task',
            'smoothing_kernel_ms': PARAMS['smooth_sigma_ms'],
            'low_fr_threshold_hz': PARAMS['low_fr_threshold'],
        }
    }

    # Save
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    print(f"\nSaved to {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert Hasnain 2024 data')
    parser.add_argument('output_file', type=str, help='Output pickle file')
    parser.add_argument('--sample', action='store_true', help='Process only 2 sessions')
    parser.add_argument('--show-processing', action='store_true', help='Show processing plots')
    parser.add_argument('--datadir', type=str, default='data', help='Directory containing the data')

    args = parser.parse_args()

    convert_data(
        args.output_file,
        sample_mode=args.sample,
        show_processing=args.show_processing,
        data_dir=Path(args.datadir),
    )
