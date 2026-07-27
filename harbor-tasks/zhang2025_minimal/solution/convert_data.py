#!/usr/bin/env python
"""
Convert IBL Brain-Wide Map data to decoder-compatible format.

Usage:
    python -u convert_data.py <output_pickle> [options]

Options:
    --full            Process all sessions (default)
    --sample          Process only 2 sessions for testing
    --show-processing Plot visualizations of processing steps
"""

import os
import sys
import argparse
import pickle
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d
import warnings
warnings.filterwarnings('ignore')

# Import IBL libraries (only use what's available)
from iblatlas.regions import BrainRegions

# Matplotlib for plotting
import matplotlib
matplotlib.use('Agg')


def bincount2D(x, y, xbin=0, xlim=None):
    """
    Compute a 2D histogram of spike counts (vectorized version).

    Parameters
    ----------
    x : array-like
        Spike times
    y : array-like
        Cluster IDs
    xbin : float
        Bin size
    xlim : tuple
        (xmin, xmax)

    Returns
    -------
    binned : ndarray
        2D array of shape (n_clusters, n_bins)
    xscale : ndarray
        Time bin edges
    yscale : ndarray
        Cluster IDs
    """
    if xlim is None:
        xlim = [np.min(x), np.max(x)]

    xmin, xmax = xlim
    n_bins = int(np.ceil((xmax - xmin) / xbin))
    xscale = np.linspace(xmin, xmax, n_bins + 1)

    yscale = np.unique(y)
    n_clusters = len(yscale)

    # Vectorized binning
    # Filter spikes within window
    mask = (x >= xmin) & (x < xmax)
    x_masked = x[mask]
    y_masked = y[mask]

    if len(x_masked) == 0:
        return np.zeros((n_clusters, n_bins)), xscale, yscale

    # Compute bin indices
    bin_idx = np.floor((x_masked - xmin) / xbin).astype(int)
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)

    # Create cluster index mapping
    cluster_to_idx = {c: i for i, c in enumerate(yscale)}
    cluster_idx = np.array([cluster_to_idx.get(c, -1) for c in y_masked])

    # Use numpy bincount for efficient counting
    valid = cluster_idx >= 0
    flat_idx = cluster_idx[valid] * n_bins + bin_idx[valid]
    counts = np.bincount(flat_idx, minlength=n_clusters * n_bins)
    binned = counts.reshape(n_clusters, n_bins)

    return binned, xscale, yscale
import matplotlib.pyplot as plt

# ============================================================================
# Configuration
# ============================================================================

# Processing parameters matching Zhang2025 paper
PARAMS = {
    'align_time': 'stimOn_times',
    'time_window': (-0.5, 1.5),  # 2 seconds, aligned to stimulus onset
    'binsize': 0.02,             # 20 ms bins
    'n_bins': 100,               # 2.0 / 0.02 = 100 bins
}

# Trial filtering parameters
TRIAL_PARAMS = {
    'min_rt': 0.08,        # Minimum reaction time (s)
    'max_rt': 2.0,         # Maximum reaction time (s)
    'max_trial_len': 10.0, # Maximum trial length (s)
    'exclude_nochoice': True,
}

# Data paths
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / 'data' / 'one_cache'

# ============================================================================
# Helper Functions
# ============================================================================

def timer(func):
    """Decorator to time function execution."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"  [{func.__name__}] took {elapsed:.2f}s")
        return result
    return wrapper


def get_session_paths(data_path, max_sessions=None):
    """Find all session paths in the ONE cache."""
    session_paths = []
    bwm_sessions_path = data_path / 'Brainwidemap' / 'sessions.pqt'

    if bwm_sessions_path.exists():
        bwm_df = pd.read_parquet(bwm_sessions_path)
        print(f"Found {len(bwm_df)} sessions in Brainwidemap sessions.pqt")

        # Walk through labs to find actual session directories
        for lab_dir in data_path.iterdir():
            if not lab_dir.is_dir() or lab_dir.name.startswith('.') or lab_dir.name.endswith('.pqt'):
                continue
            if lab_dir.name in ['Brainwidemap', '2022_Q4_IBL_et_al_BWM', '2025_Q3_IBL_et_al_BWM']:
                continue
            subjects_dir = lab_dir / 'Subjects'
            if not subjects_dir.exists():
                continue
            for subject_dir in subjects_dir.iterdir():
                if not subject_dir.is_dir():
                    continue
                for date_dir in subject_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    for num_dir in date_dir.iterdir():
                        if not num_dir.is_dir():
                            continue
                        alf_dir = num_dir / 'alf'
                        if alf_dir.exists():
                            session_paths.append({
                                'path': num_dir,
                                'lab': lab_dir.name,
                                'subject': subject_dir.name,
                                'date': date_dir.name,
                                'number': num_dir.name
                            })
                            if max_sessions and len(session_paths) >= max_sessions:
                                return session_paths

    return session_paths


def load_trials(session_path):
    """Load and filter trials for a session."""
    alf_path = session_path / 'alf'

    # Find trials table
    trials_path = None
    for version_dir in alf_path.iterdir():
        if version_dir.name.startswith('#') and version_dir.is_dir():
            candidate = version_dir / '_ibl_trials.table.pqt'
            if candidate.exists():
                trials_path = candidate
                break

    if trials_path is None:
        return None, None

    trials = pd.read_parquet(trials_path)

    # Create mask for valid trials
    mask = pd.Series(True, index=trials.index)

    # Check required columns exist
    required_cols = ['stimOn_times', 'choice', 'feedback_times', 'probabilityLeft',
                     'firstMovement_times', 'feedbackType']
    for col in required_cols:
        if col not in trials.columns:
            return None, None
        mask &= ~trials[col].isna()

    # Filter by reaction time
    rt = trials['firstMovement_times'] - trials['stimOn_times']
    mask &= (rt >= TRIAL_PARAMS['min_rt']) & (rt <= TRIAL_PARAMS['max_rt'])

    # Filter by trial length
    if 'goCue_times' in trials.columns:
        trial_len = trials['feedback_times'] - trials['goCue_times']
        mask &= trial_len <= TRIAL_PARAMS['max_trial_len']

    # Exclude no-choice trials
    if TRIAL_PARAMS['exclude_nochoice']:
        mask &= trials['choice'] != 0

    return trials, mask


def load_spikes(session_path):
    """Load spike data from all probes in a session."""
    alf_path = session_path / 'alf'

    all_spike_times = []
    all_spike_clusters = []
    all_cluster_regions = []
    cluster_offset = 0

    # Find all probe directories
    for probe_dir in sorted(alf_path.iterdir()):
        if not probe_dir.name.startswith('probe'):
            continue

        pks_dir = probe_dir / 'pykilosort'
        if not pks_dir.exists():
            continue

        # Find latest version
        version_dir = None
        for v in sorted(pks_dir.iterdir(), reverse=True):
            if v.name.startswith('#') and v.is_dir():
                version_dir = v
                break

        if version_dir is None:
            continue

        # Load spike data
        spike_times_path = version_dir / 'spikes.times.npy'
        spike_clusters_path = version_dir / 'spikes.clusters.npy'

        if not spike_times_path.exists() or not spike_clusters_path.exists():
            continue

        spike_times = np.load(spike_times_path)
        spike_clusters = np.load(spike_clusters_path)

        # Load cluster info
        metrics_path = version_dir / 'clusters.metrics.pqt'
        if metrics_path.exists():
            metrics = pd.read_parquet(metrics_path)
            n_clusters = len(metrics)
        else:
            n_clusters = len(np.unique(spike_clusters))

        # Get brain regions
        # Try to load from channels.brainLocationIds or use Beryl mapping
        regions = ['unknown'] * n_clusters

        # Check for acronym file or brain location IDs
        channels_path = version_dir / 'channels.brainLocationIds_ccf_2017.npy'
        cluster_channels_path = version_dir / 'clusters.channels.npy'

        if channels_path.exists() and cluster_channels_path.exists():
            try:
                brain_loc_ids = np.load(channels_path)
                cluster_channels = np.load(cluster_channels_path)

                # Map cluster to brain region using BrainRegions
                br = BrainRegions()
                for i, ch in enumerate(cluster_channels):
                    if i < len(regions) and ch < len(brain_loc_ids):
                        region_id = brain_loc_ids[int(ch)]
                        try:
                            acronym = br.id2acronym(region_id, mapping='Beryl')
                            if isinstance(acronym, np.ndarray):
                                acronym = acronym[0] if len(acronym) > 0 else 'unknown'
                            regions[i] = str(acronym)
                        except:
                            regions[i] = 'unknown'
            except Exception as e:
                print(f"    Warning: Could not load brain regions: {e}")

        # Offset cluster IDs for merging
        spike_clusters_offset = spike_clusters + cluster_offset
        cluster_offset += n_clusters

        all_spike_times.append(spike_times)
        all_spike_clusters.append(spike_clusters_offset)
        all_cluster_regions.extend(regions)

    if len(all_spike_times) == 0:
        return None, None, None

    # Merge all probes
    merged_times = np.concatenate(all_spike_times)
    merged_clusters = np.concatenate(all_spike_clusters)

    # Sort by time
    sort_idx = np.argsort(merged_times)
    merged_times = merged_times[sort_idx]
    merged_clusters = merged_clusters[sort_idx]

    return merged_times, merged_clusters, np.array(all_cluster_regions)


def bin_spikes_for_trial(spike_times, spike_clusters, trial_start, trial_end,
                         binsize, n_clusters):
    """Bin spikes for a single trial."""
    n_bins = int(np.round((trial_end - trial_start) / binsize))

    # Select spikes in trial window
    mask = (spike_times >= trial_start) & (spike_times < trial_end)
    trial_times = spike_times[mask]
    trial_clusters = spike_clusters[mask]

    if len(trial_times) == 0:
        return np.zeros((n_clusters, n_bins))

    # Bin using bincount2D
    binned, t_bins, cluster_ids = bincount2D(
        trial_times, trial_clusters,
        xbin=binsize,
        xlim=[trial_start, trial_end]
    )

    # Create full matrix for all clusters
    result = np.zeros((n_clusters, n_bins))
    for i, cid in enumerate(cluster_ids):
        if cid < n_clusters:
            result[int(cid), :binned.shape[1]] = binned[i, :n_bins]

    return result[:, :n_bins]


def load_wheel_data(session_path):
    """Load wheel data for a session."""
    alf_path = session_path / 'alf'

    times_path = alf_path / '_ibl_wheel.timestamps.npy'
    position_path = alf_path / '_ibl_wheel.position.npy'

    if not times_path.exists() or not position_path.exists():
        return None, None

    times = np.load(times_path)
    position = np.load(position_path)

    # Compute velocity using gradient
    dt = np.gradient(times)
    dt[dt == 0] = 1e-10  # Avoid division by zero
    velocity = np.gradient(position) / dt

    # Compute speed (absolute velocity)
    speed = np.abs(velocity)

    # Smooth with Gaussian filter (sigma=5 samples ~ 30ms at 158Hz)
    speed = gaussian_filter1d(speed, sigma=5)

    return times, speed


def load_motion_energy(session_path):
    """Load whisker motion energy for a session."""
    alf_path = session_path / 'alf'

    # Try different version directories for motion energy
    me_data = None
    me_times = None

    for version_dir in sorted(alf_path.iterdir(), reverse=True):
        if version_dir.name.startswith('#') and version_dir.is_dir():
            # Try left camera first, then right
            for camera in ['leftCamera', 'rightCamera']:
                me_path = version_dir / f'{camera}.ROIMotionEnergy.npy'
                times_path = version_dir / f'{camera}.times.npy'

                if me_path.exists():
                    me_data = np.load(me_path)
                    # Try to find times file
                    if times_path.exists():
                        me_times = np.load(times_path)
                    else:
                        # Estimate times from video frame rate (60 Hz for left)
                        # Look for camera times in parent alf dir
                        parent_times = alf_path / f'_ibl_{camera}.times.npy'
                        if parent_times.exists():
                            me_times = np.load(parent_times)
                        else:
                            # Estimate from length and assumed frame rate
                            frame_rate = 60 if 'left' in camera else 150
                            me_times = np.arange(len(me_data)) / frame_rate
                    break
            if me_data is not None:
                break

    return me_times, me_data


def interpolate_to_bins(times, values, bin_centers, allow_nans=True):
    """Interpolate time series to bin centers."""
    if times is None or values is None or len(times) == 0:
        return np.full(len(bin_centers), np.nan)

    # Handle NaN values
    valid = ~np.isnan(values)
    if not np.any(valid):
        return np.full(len(bin_centers), np.nan)

    times_valid = times[valid]
    values_valid = values[valid]

    # Check if bin centers are within data range
    if bin_centers[0] < times_valid[0] - 0.1 or bin_centers[-1] > times_valid[-1] + 0.1:
        if not allow_nans:
            return None

    # Interpolate
    interp_func = interp1d(times_valid, values_valid, kind='linear',
                           bounds_error=False, fill_value='extrapolate')
    return interp_func(bin_centers)


def discretize_to_bins(values, n_bins=3, quantiles=None):
    """Discretize continuous values into n_bins categories using quantiles."""
    if quantiles is None:
        # Compute quantile thresholds
        valid_values = values[~np.isnan(values)]
        if len(valid_values) == 0:
            return np.zeros_like(values, dtype=int), [0, 1, 2]
        quantiles = np.percentile(valid_values, np.linspace(0, 100, n_bins + 1))

    # Discretize
    result = np.digitize(values, quantiles[1:-1])
    result = np.clip(result, 0, n_bins - 1)

    return result, quantiles


def compute_trial_in_block(prob_left):
    """Compute trial number within each block."""
    trial_in_block = np.zeros(len(prob_left), dtype=int)
    block_start = 0
    current_block = prob_left.iloc[0] if isinstance(prob_left, pd.Series) else prob_left[0]

    for i in range(len(prob_left)):
        p = prob_left.iloc[i] if isinstance(prob_left, pd.Series) else prob_left[i]
        if p != current_block:
            block_start = i
            current_block = p
        trial_in_block[i] = i - block_start + 1

    return trial_in_block


@timer
def process_session(session_info, show_processing=False):
    """Process a single session and return formatted data."""
    session_path = session_info['path']
    print(f"  Processing {session_info['subject']}/{session_info['date']}")

    # Load trials
    trials, mask = load_trials(session_path)
    if trials is None or mask is None or mask.sum() < 50:
        print(f"    Skipping: insufficient trials")
        return None

    valid_trials = trials[mask].reset_index(drop=True)
    n_trials = len(valid_trials)
    print(f"    Valid trials: {n_trials}")

    # Load spikes
    spike_times, spike_clusters, cluster_regions = load_spikes(session_path)
    if spike_times is None:
        print(f"    Skipping: no spike data")
        return None

    n_clusters = len(cluster_regions)
    print(f"    Clusters: {n_clusters}")

    # Load behavioral data
    wheel_times, wheel_speed = load_wheel_data(session_path)
    me_times, me_data = load_motion_energy(session_path)

    # Check behavioral data availability
    has_wheel = wheel_times is not None and wheel_speed is not None
    has_me = me_times is not None and me_data is not None

    if not has_wheel or not has_me:
        print(f"    Skipping: missing behavioral data (wheel={has_wheel}, ME={has_me})")
        return None

    # Process each trial
    neural_data = []
    input_data = []
    output_data = []

    # Compute global discretization thresholds from all wheel/ME data
    all_wheel = []
    all_me = []

    # First pass: collect all behavioral data for quantile computation
    for i in range(n_trials):
        stim_time = valid_trials['stimOn_times'].iloc[i]
        t_start = stim_time + PARAMS['time_window'][0]
        t_end = stim_time + PARAMS['time_window'][1]
        bin_centers = np.linspace(t_start + PARAMS['binsize']/2,
                                  t_end - PARAMS['binsize']/2,
                                  PARAMS['n_bins'])

        if has_wheel:
            ws = interpolate_to_bins(wheel_times, wheel_speed, bin_centers)
            all_wheel.append(ws)
        if has_me:
            me = interpolate_to_bins(me_times, me_data, bin_centers)
            all_me.append(me)

    # Compute quantiles for discretization
    wheel_quantiles = None
    me_quantiles = None
    if has_wheel and len(all_wheel) > 0:
        all_wheel_flat = np.concatenate(all_wheel)
        valid_wheel = all_wheel_flat[~np.isnan(all_wheel_flat)]
        if len(valid_wheel) > 0:
            wheel_quantiles = np.percentile(valid_wheel, [0, 33.33, 66.67, 100])
    if has_me and len(all_me) > 0:
        all_me_flat = np.concatenate(all_me)
        valid_me = all_me_flat[~np.isnan(all_me_flat)]
        if len(valid_me) > 0:
            me_quantiles = np.percentile(valid_me, [0, 33.33, 66.67, 100])

    # Compute trial-in-block
    trial_in_block = compute_trial_in_block(valid_trials['probabilityLeft'])

    # Create time array (same for all trials)
    time_array = np.linspace(PARAMS['time_window'][0],
                             PARAMS['time_window'][1],
                             PARAMS['n_bins'])

    # Second pass: process each trial
    valid_trial_indices = []
    for i in range(n_trials):
        stim_time = valid_trials['stimOn_times'].iloc[i]
        t_start = stim_time + PARAMS['time_window'][0]
        t_end = stim_time + PARAMS['time_window'][1]

        # Bin spikes
        binned_spikes = bin_spikes_for_trial(
            spike_times, spike_clusters, t_start, t_end,
            PARAMS['binsize'], n_clusters
        )

        if binned_spikes.shape[1] != PARAMS['n_bins']:
            # Adjust if needed
            if binned_spikes.shape[1] < PARAMS['n_bins']:
                pad = np.zeros((n_clusters, PARAMS['n_bins'] - binned_spikes.shape[1]))
                binned_spikes = np.hstack([binned_spikes, pad])
            else:
                binned_spikes = binned_spikes[:, :PARAMS['n_bins']]

        # Inputs
        # Input 0: Time since stimulus onset
        trial_time = time_array.copy()

        # Input 1: Trial number in block (broadcast to time)
        trial_num = np.full(PARAMS['n_bins'], trial_in_block[i], dtype=float)

        trial_input = np.stack([trial_time, trial_num], axis=0)  # Shape: (2, n_bins)

        # Outputs
        # Output 0: Choice (left=0, right=1)
        choice = valid_trials['choice'].iloc[i]
        choice_out = 0 if choice == 1 else 1  # IBL: 1=left, -1=right -> our: 0=left, 1=right

        # Output 1: Prior (0.2->0, 0.5->1, 0.8->2)
        prob_left = valid_trials['probabilityLeft'].iloc[i]
        if abs(prob_left - 0.2) < 0.1:
            prior_out = 0
        elif abs(prob_left - 0.5) < 0.1:
            prior_out = 1
        else:  # ~0.8
            prior_out = 2

        # Output 2: Wheel speed (discretized, time-varying)
        bin_centers = np.linspace(t_start + PARAMS['binsize']/2,
                                  t_end - PARAMS['binsize']/2,
                                  PARAMS['n_bins'])
        wheel_interp = interpolate_to_bins(wheel_times, wheel_speed, bin_centers)
        wheel_disc, _ = discretize_to_bins(wheel_interp, n_bins=3, quantiles=wheel_quantiles)

        # Output 3: Whisker ME (discretized, time-varying)
        me_interp = interpolate_to_bins(me_times, me_data, bin_centers)
        me_disc, _ = discretize_to_bins(me_interp, n_bins=3, quantiles=me_quantiles)

        # Check for valid data
        if np.any(np.isnan(wheel_interp)) or np.any(np.isnan(me_interp)):
            continue

        # Stack outputs: choice and prior are per-trial (scalar), wheel and ME are time-varying
        trial_output = np.stack([
            np.full(PARAMS['n_bins'], choice_out),
            np.full(PARAMS['n_bins'], prior_out),
            wheel_disc,
            me_disc
        ], axis=0)  # Shape: (4, n_bins)

        neural_data.append(binned_spikes)
        input_data.append(trial_input)
        output_data.append(trial_output)
        valid_trial_indices.append(i)

    if len(neural_data) < 50:
        print(f"    Skipping: only {len(neural_data)} valid trials after processing")
        return None

    print(f"    Processed trials: {len(neural_data)}")

    # Plotting for show-processing mode
    if show_processing and len(neural_data) > 0:
        plot_processing(session_info, neural_data, input_data, output_data,
                       valid_trials.iloc[valid_trial_indices], time_array)

    return {
        'neural': neural_data,
        'input': input_data,
        'output': output_data,
        'subject': session_info['subject'],
        'cluster_regions': cluster_regions,
        'n_trials': len(neural_data),
        'n_neurons': n_clusters,
    }


def plot_processing(session_info, neural_data, input_data, output_data, trials, time_array):
    """Plot processing visualizations for a session."""
    fig, axes = plt.subplots(4, 3, figsize=(15, 12))

    # Sample trials to plot
    n_plot = min(3, len(neural_data))

    for i in range(n_plot):
        # Neural activity (mean across neurons)
        ax = axes[0, i]
        mean_activity = np.mean(neural_data[i], axis=0)
        ax.plot(time_array, mean_activity, 'k-')
        ax.axvline(0, color='r', linestyle='--', alpha=0.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Mean spike count')
        ax.set_title(f'Trial {i+1}: Neural Activity')

        # Inputs
        ax = axes[1, i]
        ax.plot(time_array, input_data[i][0], 'b-', label='Time')
        ax.plot(time_array, input_data[i][1] / input_data[i][1].max() if input_data[i][1].max() > 0 else input_data[i][1],
                'g-', label='Trial in block (norm)')
        ax.axvline(0, color='r', linestyle='--', alpha=0.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Value')
        ax.set_title(f'Trial {i+1}: Inputs')
        ax.legend(fontsize=8)

        # Outputs (per-trial)
        ax = axes[2, i]
        ax.bar([0, 1], [output_data[i][0, 0], output_data[i][1, 0]],
               tick_label=['Choice', 'Prior'])
        ax.set_ylabel('Value')
        ax.set_title(f'Trial {i+1}: Per-trial Outputs')

        # Outputs (time-varying)
        ax = axes[3, i]
        ax.plot(time_array, output_data[i][2], 'b-', label='Wheel speed')
        ax.plot(time_array, output_data[i][3], 'g-', label='Whisker ME')
        ax.axvline(0, color='r', linestyle='--', alpha=0.5)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Discretized value')
        ax.set_title(f'Trial {i+1}: Time-varying Outputs')
        ax.legend(fontsize=8)

    plt.suptitle(f"Session: {session_info['subject']}/{session_info['date']}")
    plt.tight_layout()
    plt.savefig(BASE_PATH / f"processing_{session_info['subject']}_{session_info['date']}.png", dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Convert IBL data to decoder format')
    parser.add_argument('output_file', type=str, help='Output pickle file path')
    parser.add_argument('--full', action='store_true', default=True,
                        help='Process all sessions (default)')
    parser.add_argument('--sample', action='store_true',
                        help='Process only 2 sessions for testing')
    parser.add_argument('--show-processing', action='store_true',
                        help='Plot processing visualizations')
    parser.add_argument('--datadir', type=str, default=None,
                        help='Path to data directory (default: data/one_cache next to script)')
    args = parser.parse_args()

    global DATA_PATH
    if args.datadir is not None:
        DATA_PATH = Path(args.datadir) / 'one_cache'

    if args.sample:
        args.full = False

    print("=" * 60)
    print("IBL Data Conversion")
    print("=" * 60)
    print(f"Output file: {args.output_file}")
    print(f"Mode: {'sample (2 sessions)' if args.sample else 'full'}")
    print(f"Show processing: {args.show_processing}")
    print()

    # Find sessions
    max_sessions = 2 if args.sample else None
    session_paths = get_session_paths(DATA_PATH, max_sessions=max_sessions)
    print(f"Found {len(session_paths)} sessions to process")

    # Process sessions
    all_neural = []
    all_input = []
    all_output = []
    all_subjects = []
    subject_idx = []
    all_brain_regions = set()
    brain_region_idx = []

    subject_to_idx = {}

    total_start = time.time()
    for i, session_info in enumerate(session_paths):
        print(f"\n[{i+1}/{len(session_paths)}] {session_info['lab']}/{session_info['subject']}")

        result = process_session(session_info, show_processing=args.show_processing)

        if result is None:
            continue

        # Add to lists
        all_neural.append(result['neural'])
        all_input.append(result['input'])
        all_output.append(result['output'])

        # Handle subject indexing
        subject = result['subject']
        if subject not in subject_to_idx:
            subject_to_idx[subject] = len(all_subjects)
            all_subjects.append(subject)
        subject_idx.append(subject_to_idx[subject])

        # Handle brain regions - store raw regions for now
        regions = result['cluster_regions']
        all_brain_regions.update(regions)
        brain_region_idx.append(regions)  # Store raw regions, convert to idx later

    total_elapsed = time.time() - total_start
    print(f"\nTotal processing time: {total_elapsed:.1f}s")

    if len(all_neural) == 0:
        print("ERROR: No valid sessions processed!")
        sys.exit(1)

    # Build final data structure
    brain_region_list = sorted(list(all_brain_regions))
    region_to_idx = {r: i for i, r in enumerate(brain_region_list)}

    # Convert region names to indices
    brain_region_idx_final = []
    for regions in brain_region_idx:
        brain_region_idx_final.append(np.array([region_to_idx[r] for r in regions]))

    data = {
        'neural': all_neural,
        'input': all_input,
        'output': all_output,
        'subjects': all_subjects,
        'subject_idx': np.array(subject_idx),
        'brain_regions': brain_region_list,
        'brain_region_idx': brain_region_idx_final,
        'input_names': ['time_since_stim', 'trial_in_block'],
        'output_names': ['choice', 'prior', 'wheel_speed', 'whisker_me'],
        'output_values': [
            ['left', 'right'],
            ['0.2', '0.5', '0.8'],
            ['slow', 'medium', 'fast'],
            ['low', 'medium', 'high']
        ],
        'metadata': {
            'time_bin_size': PARAMS['binsize'] * 1000,  # Convert to ms
            'temporal_alignment_event': 'stimulus onset (stimOn_times)',
            'off_start': PARAMS['time_window'][0],
            'off_end': PARAMS['time_window'][1],
            'task_description': 'IBL visual decision-making task',
            'n_sessions': len(all_neural),
            'total_trials': sum(len(s) for s in all_neural),
        }
    }

    # Print summary
    print("\n" + "=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"Sessions: {len(all_neural)}")
    print(f"Subjects: {len(all_subjects)}")
    print(f"Total trials: {sum(len(s) for s in all_neural)}")
    print(f"Brain regions: {len(brain_region_list)}")
    print(f"Input dimensions: {len(data['input_names'])}")
    print(f"Output dimensions: {len(data['output_names'])}")

    # Save
    print(f"\nSaving to {args.output_file}...")
    with open(args.output_file, 'wb') as f:
        pickle.dump(data, f)

    file_size = os.path.getsize(args.output_file) / (1024 * 1024)
    print(f"Saved! File size: {file_size:.1f} MB")


if __name__ == '__main__':
    main()
