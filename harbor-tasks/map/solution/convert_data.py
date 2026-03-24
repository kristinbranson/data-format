#!/usr/bin/env python
"""
Convert MAP (Mesoscale Activity Project) NWB data to decoder-compatible format.

Usage:
    python -u convert_data.py <output_pickle_file> [--sample] [--show-processing]

Arguments:
    output_pickle_file: Path to save the converted data
    --full: Process all sessions (default)
    --sample: Process only 2 sessions for testing
    --show-processing: Plot visualizations of processing steps
"""

import os
import sys
import glob
import json
import time
import pickle
import argparse
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict

# Parameters from CLAUDE.md
TIME_BEFORE_GO = 2.5  # seconds before go cue
TIME_AFTER_GO = 1.5   # seconds after go cue
BIN_SIZE = 0.05       # 50 ms bins
N_BINS = int((TIME_BEFORE_GO + TIME_AFTER_GO) / BIN_SIZE)  # 80 bins

# Data directory (default; overridden by --datadir)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def get_bin_centers():
    """Get bin centers relative to go cue."""
    return np.linspace(-TIME_BEFORE_GO + BIN_SIZE/2,
                       TIME_AFTER_GO - BIN_SIZE/2,
                       N_BINS)


def bin_spike_times(spike_times, bin_edges_absolute):
    """
    Bin spike times using absolute bin edges.

    Args:
        spike_times: array of spike times (absolute)
        bin_edges_absolute: edges of bins in absolute time

    Returns:
        spike_counts: array of spike counts per bin
    """
    # Bin the spikes
    counts, _ = np.histogram(spike_times, bins=bin_edges_absolute)

    return counts


def get_all_unit_spike_times(f, unit_indices):
    """
    Get spike times for multiple units from NWB file efficiently.

    Args:
        f: h5py File object
        unit_indices: list of unit indices to extract

    Returns:
        spike_times_list: list of arrays of spike times (one per unit)
    """
    spike_times_all = f['units/spike_times'][:]
    spike_times_index = f['units/spike_times_index'][:]

    spike_times_list = []
    for unit_idx in unit_indices:
        start_idx = 0 if unit_idx == 0 else spike_times_index[unit_idx - 1]
        end_idx = spike_times_index[unit_idx]
        spike_times_list.append(spike_times_all[start_idx:end_idx])

    return spike_times_list


def get_brain_region_from_electrode(f, electrode_idx):
    """
    Get brain region from electrode location JSON.

    Args:
        f: h5py File object
        electrode_idx: index of the electrode

    Returns:
        brain_region: string name of brain region (simplified)
    """
    locations = f['general/extracellular_ephys/electrodes/location'][:]
    loc_str = locations[electrode_idx]
    if isinstance(loc_str, bytes):
        loc_str = loc_str.decode()

    try:
        loc_dict = json.loads(loc_str)
        region = loc_dict.get('brain_regions', 'unknown')
        # Simplify: remove left/right prefix
        if region.startswith('left '):
            region = region[5:]
        elif region.startswith('right '):
            region = region[6:]
        return region
    except:
        return 'unknown'


def get_trial_tongue_y(f, trial_start, trial_end, bin_centers_abs):
    """
    Get tongue y-position for a trial, interpolated to bin centers.

    Args:
        f: h5py File object
        trial_start: absolute start time of trial window
        trial_end: absolute end time of trial window
        bin_centers_abs: absolute times of bin centers

    Returns:
        tongue_y: array of tongue y-positions at bin centers
    """
    try:
        tongue_ts = f['acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking/timestamps'][:]
        tongue_data = f['acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking/data'][:]

        # Get y-position (column 1)
        tongue_y_all = tongue_data[:, 1]

        # Find indices within trial window with some padding
        mask = (tongue_ts >= trial_start - 0.1) & (tongue_ts <= trial_end + 0.1)

        if not np.any(mask):
            return np.full(len(bin_centers_abs), np.nan)

        ts_trial = tongue_ts[mask]
        y_trial = tongue_y_all[mask]

        # Interpolate to bin centers
        tongue_y = np.interp(bin_centers_abs, ts_trial, y_trial,
                            left=np.nan, right=np.nan)

        return tongue_y
    except Exception as e:
        return np.full(len(bin_centers_abs), np.nan)


def process_session(nwb_path, show_processing=False, session_idx=0):
    """
    Process a single NWB session file.

    Args:
        nwb_path: path to NWB file
        show_processing: whether to plot processing visualizations
        session_idx: index for plot naming

    Returns:
        session_data: dict with neural, input, output data for this session
    """
    session_name = os.path.basename(nwb_path).replace('.nwb', '')
    print(f"  Processing {session_name}...")
    start_time = time.time()

    with h5py.File(nwb_path, 'r') as f:
        # Get good units
        classification = f['units/classification'][:]
        good_mask = classification == b'good'
        good_indices = np.where(good_mask)[0]
        n_good_units = len(good_indices)

        if n_good_units == 0:
            print(f"    WARNING: No good units found in {session_name}")
            return None

        print(f"    Found {n_good_units} good units")

        # Get brain regions for good units
        unit_electrodes = f['units/electrodes'][:]
        brain_regions = []
        for unit_idx in good_indices:
            electrode_idx = unit_electrodes[unit_idx]
            region = get_brain_region_from_electrode(f, electrode_idx)
            brain_regions.append(region)

        # Get trial info
        trials = f['intervals/trials']
        n_trials = trials['id'].shape[0]

        # Get go cue times
        go_times = f['acquisition/BehavioralEvents/go_start_times/timestamps'][:]

        # Get sample (tone) start times
        sample_times = f['acquisition/BehavioralEvents/sample_start_times/timestamps'][:]

        # Get trial outcomes, instructions, early lick
        outcomes = trials['outcome'][:]
        instructions = trials['trial_instruction'][:]
        early_licks = trials['early_lick'][:]

        # Get photostim info
        photostim_onset = trials['photostim_onset'][:]
        photostim_power = trials['photostim_power'][:]

        # Check if we have photostim stop times
        try:
            photostim_stop = f['acquisition/BehavioralEvents/photostim_stop_times/timestamps'][:]
            photostim_start = f['acquisition/BehavioralEvents/photostim_start_times/timestamps'][:]
        except:
            photostim_stop = None
            photostim_start = None

        # Setup bin edges and centers
        bin_centers = get_bin_centers()
        bin_edges = np.concatenate([
            [bin_centers[0] - BIN_SIZE/2],
            bin_centers + BIN_SIZE/2
        ])

        # Load all spike times for good units at once (more efficient)
        print(f"    Loading spike times...")
        all_unit_spike_times = get_all_unit_spike_times(f, good_indices)

        # Get the maximum spike time to identify valid trials
        max_spike_time = max(spikes.max() if len(spikes) > 0 else 0 for spikes in all_unit_spike_times)
        print(f"    Spike recording ends at: {max_spike_time:.1f} s")

        # Collect tongue y data for percentile calculation
        all_tongue_y = []

        # Load tongue tracking data once
        try:
            tongue_ts = f['acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking/timestamps'][:]
            tongue_data = f['acquisition/BehavioralTimeSeries/Camera0_side_TongueTracking/data'][:]
            tongue_y_all = tongue_data[:, 1]
            has_tongue = True
        except:
            has_tongue = False
            tongue_ts = None
            tongue_y_all = None

        # Filter trials to only those with spike data
        # Trial is valid if go_time + TIME_AFTER_GO <= max_spike_time
        valid_trial_mask = (go_times + TIME_AFTER_GO) <= max_spike_time
        n_valid_trials = min(n_trials, len(go_times))
        valid_trial_indices = [i for i in range(n_valid_trials) if valid_trial_mask[i]]
        print(f"    Valid trials (with spike data): {len(valid_trial_indices)}/{n_valid_trials}")

        # First pass: collect tongue y for percentiles
        for trial_idx in valid_trial_indices:
            go_time = go_times[trial_idx]
            trial_start = go_time - TIME_BEFORE_GO
            trial_end = go_time + TIME_AFTER_GO
            bin_centers_abs = bin_centers + go_time

            if has_tongue:
                mask = (tongue_ts >= trial_start - 0.1) & (tongue_ts <= trial_end + 0.1)
                if np.any(mask):
                    tongue_y = np.interp(bin_centers_abs, tongue_ts[mask], tongue_y_all[mask],
                                        left=np.nan, right=np.nan)
                    valid_y = tongue_y[~np.isnan(tongue_y)]
                    if len(valid_y) > 0:
                        all_tongue_y.extend(valid_y)

        # Compute session percentiles for tongue y
        if len(all_tongue_y) > 0:
            all_tongue_y = np.array(all_tongue_y)
            p40 = np.percentile(all_tongue_y, 40)
            p60 = np.percentile(all_tongue_y, 60)
        else:
            p40, p60 = 0, 1  # Fallback

        # Process each valid trial
        neural_trials = []
        input_trials = []
        output_trials = []

        print(f"    Processing {len(valid_trial_indices)} trials...")
        for trial_idx in valid_trial_indices:
            go_time = go_times[trial_idx]

            # Get sample time for this trial
            sample_time = sample_times[trial_idx] if trial_idx < len(sample_times) else go_time - 1.85

            # Compute bin centers in absolute time
            bin_centers_abs = bin_centers + go_time

            # --- Neural data ---
            neural = np.zeros((n_good_units, N_BINS), dtype=np.float32)
            bin_edges_abs = bin_edges + go_time
            for i, unit_spikes in enumerate(all_unit_spike_times):
                spike_counts = bin_spike_times(unit_spikes, bin_edges_abs)
                # Convert to firing rate (spikes/second)
                neural[i, :] = spike_counts / BIN_SIZE

            neural_trials.append(neural)

            # --- Input 0: Time from tone onset ---
            time_from_tone = bin_centers_abs - sample_time

            # --- Input 1: Photostim on/off ---
            photostim_binary = np.zeros(N_BINS, dtype=np.float32)
            ps_onset = photostim_onset[trial_idx]
            ps_power = photostim_power[trial_idx]

            # Check if this is a stim trial
            if isinstance(ps_power, bytes):
                ps_power_str = ps_power.decode()
            else:
                ps_power_str = str(ps_power)

            if ps_power_str != 'N/A':
                # This is a stim trial
                # Photostim is during last 0.5s of delay (before go cue)
                # Default stim duration is 0.5s ending at go cue
                if isinstance(ps_onset, bytes):
                    ps_onset_str = ps_onset.decode()
                else:
                    ps_onset_str = str(ps_onset)

                if ps_onset_str != 'N/A':
                    try:
                        stim_onset_rel = float(ps_onset_str)  # relative to trial start
                        # We need to convert to relative to go cue
                        # From methods: stim is during last 0.5s of delay
                        # Delay ends at go cue, so stim is from -0.5 to 0 relative to go
                        stim_start = -0.5
                        stim_end = 0.0
                        photostim_binary[(bin_centers >= stim_start) & (bin_centers < stim_end)] = 1.0
                    except:
                        # Use default timing
                        stim_start = -0.5
                        stim_end = 0.0
                        photostim_binary[(bin_centers >= stim_start) & (bin_centers < stim_end)] = 1.0

            # Combine inputs
            input_data = np.stack([time_from_tone, photostim_binary], axis=0).astype(np.float32)
            input_trials.append(input_data)

            # --- Output 0: Choice (lick direction) ---
            instr = instructions[trial_idx]
            if isinstance(instr, bytes):
                instr = instr.decode()
            choice = 0 if instr == 'left' else 1

            # --- Output 1: Outcome ---
            out = outcomes[trial_idx]
            if isinstance(out, bytes):
                out = out.decode()
            outcome_map = {'ignore': 0, 'miss': 1, 'hit': 2}
            outcome_val = outcome_map.get(out, 0)

            # --- Output 2: Early lick ---
            el = early_licks[trial_idx]
            if isinstance(el, bytes):
                el = el.decode()
            early_lick_val = 0 if el == 'no early' else 1

            # --- Output 3: Tongue y-position (discretized, time-varying) ---
            if has_tongue:
                trial_start = go_time - TIME_BEFORE_GO
                trial_end = go_time + TIME_AFTER_GO
                mask = (tongue_ts >= trial_start - 0.1) & (tongue_ts <= trial_end + 0.1)
                if np.any(mask):
                    tongue_y = np.interp(bin_centers_abs, tongue_ts[mask], tongue_y_all[mask],
                                        left=np.nan, right=np.nan)
                else:
                    tongue_y = np.full(N_BINS, np.nan)
            else:
                tongue_y = np.full(N_BINS, np.nan)

            # Discretize tongue y
            tongue_discrete = np.zeros(N_BINS, dtype=np.float32)
            tongue_discrete[tongue_y < p40] = 0
            tongue_discrete[(tongue_y >= p40) & (tongue_y < p60)] = 1
            tongue_discrete[tongue_y >= p60] = 2
            # Handle NaN by setting to 1 (middle category)
            tongue_discrete[np.isnan(tongue_y)] = 1

            # Combine outputs - per-trial outputs are broadcast to time dimension
            output_data = np.stack([
                np.full(N_BINS, int(choice), dtype=np.int64),
                np.full(N_BINS, int(outcome_val), dtype=np.int64),
                np.full(N_BINS, int(early_lick_val), dtype=np.int64),
                tongue_discrete.astype(np.int64)
            ], axis=0).astype(np.int64)

            output_trials.append(output_data)

        # Plot processing visualization if requested
        if show_processing and len(neural_trials) > 0:
            plot_processing(session_name, neural_trials, input_trials, output_trials,
                           bin_centers, good_indices, brain_regions, session_idx)

        elapsed = time.time() - start_time
        print(f"    Processed {len(neural_trials)} trials in {elapsed:.1f}s")

        return {
            'neural': neural_trials,
            'input': input_trials,
            'output': output_trials,
            'brain_regions': brain_regions,
            'session_name': session_name
        }


def plot_processing(session_name, neural_trials, input_trials, output_trials,
                   bin_centers, good_indices, brain_regions, session_idx):
    """Plot processing visualization for a session."""
    fig, axes = plt.subplots(4, 2, figsize=(16, 12))

    # Sample trials to plot
    trial_indices = [0, min(len(neural_trials)-1, 10)]

    for col, trial_idx in enumerate(trial_indices):
        neural = neural_trials[trial_idx]
        inputs = input_trials[trial_idx]
        outputs = output_trials[trial_idx]

        # Plot neural activity (sample neurons)
        ax = axes[0, col]
        n_plot = min(20, neural.shape[0])
        im = ax.imshow(neural[:n_plot, :], aspect='auto',
                       extent=[bin_centers[0], bin_centers[-1], n_plot, 0],
                       cmap='viridis')
        ax.axvline(0, color='r', linestyle='--', label='Go cue')
        ax.set_ylabel('Neuron')
        ax.set_title(f'Trial {trial_idx}: Neural Activity')
        plt.colorbar(im, ax=ax, label='FR (Hz)')

        # Plot inputs
        ax = axes[1, col]
        ax.plot(bin_centers, inputs[0, :], label='Time from tone', color='blue')
        ax.axhline(0, color='gray', linestyle=':')
        ax.axvline(0, color='r', linestyle='--', label='Go cue')
        ax.set_ylabel('Time from tone (s)')
        ax.legend(loc='upper right')

        ax2 = ax.twinx()
        ax2.fill_between(bin_centers, inputs[1, :], alpha=0.3, color='orange', label='Photostim')
        ax2.set_ylabel('Photostim', color='orange')
        ax2.set_ylim(-0.1, 1.5)

        # Plot outputs
        ax = axes[2, col]
        ax.plot(bin_centers, outputs[0, :], label=f'Choice: {int(outputs[0, 0])}', marker='.')
        ax.plot(bin_centers, outputs[1, :], label=f'Outcome: {int(outputs[1, 0])}', marker='.')
        ax.plot(bin_centers, outputs[2, :], label=f'Early lick: {int(outputs[2, 0])}', marker='.')
        ax.axvline(0, color='r', linestyle='--')
        ax.set_ylabel('Value')
        ax.legend(loc='upper right')
        ax.set_title('Per-trial outputs')

        # Plot tongue y
        ax = axes[3, col]
        ax.plot(bin_centers, outputs[3, :], label='Tongue Y (discrete)', color='green')
        ax.axvline(0, color='r', linestyle='--')
        ax.set_xlabel('Time from go cue (s)')
        ax.set_ylabel('Tongue Y category')
        ax.set_ylim(-0.5, 2.5)
        ax.set_title('Tongue Y position (discretized)')

    fig.suptitle(f'{session_name}')
    fig.tight_layout()
    fig.savefig(f'preprocessing_demo_{session_name.split("_")[0]}_{session_name.split("_")[1][:8]}_trial{trial_indices[0]}.png', dpi=150)
    plt.close(fig)


def get_all_nwb_files():
    """Get list of all NWB files in data directory."""
    nwb_files = []
    subjects = sorted([d for d in os.listdir(DATA_DIR) if d.startswith('sub-')])

    for subject in subjects:
        subject_dir = os.path.join(DATA_DIR, subject)
        files = sorted(glob.glob(os.path.join(subject_dir, '*.nwb')))
        nwb_files.extend(files)

    return nwb_files


def main():
    parser = argparse.ArgumentParser(description='Convert MAP NWB data to decoder format.')
    parser.add_argument('output_file', type=str, help='Output pickle file path')
    parser.add_argument('--full', action='store_true', default=True,
                       help='Process all sessions (default)')
    parser.add_argument('--sample', action='store_true',
                       help='Process only 2 sessions for testing')
    parser.add_argument('--show-processing', action='store_true',
                       help='Plot visualizations of processing steps')
    parser.add_argument('--datadir', type=str, default=None,
                       help='Path to data directory (default: data/ next to script)')

    args = parser.parse_args()

    if args.datadir is not None:
        global DATA_DIR
        DATA_DIR = args.datadir

    print("=" * 60)
    print("MAP Data Conversion")
    print("=" * 60)

    # Get NWB files
    nwb_files = get_all_nwb_files()
    print(f"Found {len(nwb_files)} NWB files")

    if args.sample:
        nwb_files = nwb_files[:2]
        print(f"Sample mode: processing only {len(nwb_files)} sessions")

    # Initialize data structure
    all_neural = []
    all_input = []
    all_output = []
    all_brain_region_idx = []
    all_subjects = []
    all_subject_idx = []
    session_info = []

    # Map subject IDs to indices
    subject_to_idx = {}

    # Map brain regions to indices
    all_brain_regions_set = set()

    # First pass: collect all brain regions
    print("\nFirst pass: collecting brain regions...")
    for nwb_path in nwb_files:
        with h5py.File(nwb_path, 'r') as f:
            unit_electrodes = f['units/electrodes'][:]
            classification = f['units/classification'][:]
            good_mask = classification == b'good'
            good_indices = np.where(good_mask)[0]

            for unit_idx in good_indices:
                electrode_idx = unit_electrodes[unit_idx]
                region = get_brain_region_from_electrode(f, electrode_idx)
                all_brain_regions_set.add(region)

    brain_regions_list = sorted(list(all_brain_regions_set))
    region_to_idx = {r: i for i, r in enumerate(brain_regions_list)}
    print(f"Found {len(brain_regions_list)} brain regions: {brain_regions_list}")

    # Process each session
    print("\nProcessing sessions...")
    total_start = time.time()

    for i, nwb_path in enumerate(nwb_files):
        # Extract subject ID
        filename = os.path.basename(nwb_path)
        subject_id = filename.split('_')[0]  # e.g., 'sub-440956'

        # Add subject if new
        if subject_id not in subject_to_idx:
            subject_to_idx[subject_id] = len(all_subjects)
            all_subjects.append(subject_id)

        subject_idx = subject_to_idx[subject_id]

        # Process session
        session_data = process_session(nwb_path,
                                       show_processing=args.show_processing and i < 2,
                                       session_idx=i)

        if session_data is None:
            continue

        # Add to data structure
        all_neural.append(session_data['neural'])
        all_input.append(session_data['input'])
        all_output.append(session_data['output'])
        all_subject_idx.append(subject_idx)

        # Map brain regions to indices for this session
        brain_region_indices = np.array([region_to_idx[r] for r in session_data['brain_regions']])
        all_brain_region_idx.append(brain_region_indices)

        session_info.append(session_data['session_name'])

        # Progress
        if (i + 1) % 10 == 0:
            elapsed = time.time() - total_start
            print(f"  Processed {i+1}/{len(nwb_files)} sessions ({elapsed:.1f}s)")

    total_elapsed = time.time() - total_start
    print(f"\nTotal processing time: {total_elapsed:.1f}s")

    # Build final data structure
    data = {
        'neural': all_neural,
        'input': all_input,
        'output': all_output,
        'subjects': all_subjects,
        'subject_idx': np.array(all_subject_idx, dtype=np.int64),
        'brain_regions': brain_regions_list,
        'brain_region_idx': all_brain_region_idx,
        'input_names': ['time_from_tone', 'photostim'],
        'output_names': ['choice', 'outcome', 'early_lick', 'tongue_y'],
        'output_values': [
            ['left', 'right'],              # choice
            ['ignore', 'miss', 'hit'],      # outcome
            ['no', 'yes'],                  # early_lick
            ['low', 'mid', 'high']          # tongue_y
        ],
        'metadata': {
            'time_bin_size': BIN_SIZE * 1000,  # in ms
            'temporal_alignment_event': 'Go cue onset',
            'off_start': -TIME_BEFORE_GO,
            'off_end': TIME_AFTER_GO,
            'task_description': 'Auditory delayed response task with memory-guided licking',
            'session_info': session_info
        }
    }

    # Print summary
    print("\n" + "=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"Sessions: {len(all_neural)}")
    print(f"Subjects: {len(all_subjects)}")
    print(f"Brain regions: {len(brain_regions_list)}")

    total_trials = sum(len(s) for s in all_neural)
    total_neurons = sum(s[0].shape[0] if len(s) > 0 else 0 for s in all_neural)
    print(f"Total trials: {total_trials}")
    print(f"Total neurons (sum across sessions): {total_neurons}")

    # Save
    print(f"\nSaving to {args.output_file}...")
    with open(args.output_file, 'wb') as f:
        pickle.dump(data, f)

    file_size = os.path.getsize(args.output_file) / (1024**2)
    print(f"Saved {file_size:.1f} MB")

    print("\nDone!")


if __name__ == '__main__':
    main()
