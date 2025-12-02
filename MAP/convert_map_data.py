#!/usr/bin/env python
"""
Convert MAP dataset to standardized format for decoder training.

This script converts NWB files from the MAP dataset into the standardized
format with 'neural', 'input', 'output', and 'metadata' keys.
"""

import numpy as np
from pynwb import NWBHDF5IO
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
import warnings


# Conversion parameters
BIN_SIZE = 0.050  # 50ms bins
TIME_BEFORE_GO = 2.0  # seconds before go cue (capture late delay + photostim)
TIME_AFTER_GO = 2.0  # seconds after go cue (capture movement/response)
TOTAL_TIME = TIME_BEFORE_GO + TIME_AFTER_GO
N_TIME_BINS = int(TOTAL_TIME / BIN_SIZE)


def get_trial_choice(trial_instruction: str, outcome: str) -> str:
    """
    Infer which direction the mouse licked based on instruction and outcome.

    Args:
        trial_instruction: 'left' or 'right' (which tone was played)
        outcome: 'hit' or 'miss'

    Returns:
        'left' or 'right' (which direction mouse licked)
    """
    if outcome == 'hit':
        # Correct trial: licked in instructed direction
        return trial_instruction
    elif outcome == 'miss':
        # Incorrect trial: licked opposite direction
        return 'right' if trial_instruction == 'left' else 'left'
    else:
        raise ValueError(f"Unexpected outcome: {outcome}")


def is_valid_trial(trial_data: Dict) -> bool:
    """Check if trial should be included in dataset."""
    # Exclude early lick trials
    if trial_data['early_lick'] == 'early':
        return False

    # Exclude trials with no response
    if trial_data['outcome'] == 'ignore':
        return False

    # Include only hit and miss trials
    if trial_data['outcome'] not in ['hit', 'miss']:
        return False

    return True


def check_trial_coverage(nwbfile, time_window: Tuple[float, float],
                         min_coverage: float = 0.9) -> Tuple[bool, float]:
    """
    Check if a trial's time window has sufficient obs_intervals coverage.

    Args:
        nwbfile: NWB file object
        time_window: (start_time, end_time) tuple for the trial
        min_coverage: Minimum required coverage fraction (default 0.9 = 90%)

    Returns:
        Tuple of (is_valid, coverage)
            is_valid: True if coverage >= min_coverage
            coverage: Coverage fraction (0.0 to 1.0)
    """
    # Check if obs_intervals column exists
    if 'obs_intervals' not in nwbfile.units.colnames:
        # If no obs_intervals, assume full coverage
        return True, 1.0

    # Check first unit only (obs_intervals are session-wide, same for all units)
    obs_intervals = nwbfile.units['obs_intervals'][0]
    window_duration = time_window[1] - time_window[0]

    # Calculate overlap between time_window and obs_intervals
    total_overlap = 0.0
    for interval in obs_intervals:
        overlap_start = max(time_window[0], interval[0])
        overlap_end = min(time_window[1], interval[1])
        if overlap_end > overlap_start:
            total_overlap += (overlap_end - overlap_start)

    coverage = total_overlap / window_duration
    is_valid = coverage >= min_coverage

    return is_valid, coverage


def bin_spikes(spike_times: np.ndarray, time_window: Tuple[float, float],
               bin_size: float, n_bins: int) -> np.ndarray:
    """
    Bin spike times into firing rate using fast searchsorted approach.

    Args:
        spike_times: Array of spike times (in seconds, must be sorted)
        time_window: (start_time, end_time) for the window of interest
        bin_size: Size of bins in seconds
        n_bins: Expected number of bins

    Returns:
        Array of firing rates (spikes per second)
    """
    start_time, end_time = time_window

    # Create bin edges
    bin_edges = np.linspace(start_time, end_time, n_bins + 1)

    # Use searchsorted for faster binning (O(log n) per edge vs O(n) for histogram)
    # spike_times are already sorted in NWB files
    indices = np.searchsorted(spike_times, bin_edges)

    # Calculate spike counts per bin
    spike_counts = np.diff(indices)

    # Convert to firing rate (spikes per second)
    firing_rate = spike_counts / bin_size

    return firing_rate


def bin_all_spikes_cached(spike_times_list: list, time_window: Tuple[float, float],
                          bin_size: float, n_bins: int) -> np.ndarray:
    """
    Bin spikes for all units using cached spike times.

    Args:
        spike_times_list: List of spike time arrays (one per unit)
        time_window: (start_time, end_time) for the window of interest
        bin_size: Size of bins in seconds
        n_bins: Expected number of bins

    Returns:
        Array of shape (n_units, n_bins) with firing rates
    """
    n_units = len(spike_times_list)
    neural_activity = np.zeros((n_units, n_bins), dtype=np.float32)

    # Create bin edges once
    start_time, end_time = time_window
    bin_edges = np.linspace(start_time, end_time, n_bins + 1)

    # Process each unit (can't vectorize fully due to variable-length spike trains)
    for i, spike_times in enumerate(spike_times_list):
        # Pre-filter spikes to window (reduces searchsorted work)
        mask = (spike_times >= start_time - 0.1) & (spike_times <= end_time + 0.1)
        spikes_windowed = spike_times[mask]

        # Fast binning using searchsorted
        indices = np.searchsorted(spikes_windowed, bin_edges)
        spike_counts = np.diff(indices)
        neural_activity[i, :] = spike_counts / bin_size

    return neural_activity


def process_session(nwb_path: str, max_trials: int = None) -> Tuple[List, List, List]:
    """
    Process a single NWB session file.

    Args:
        nwb_path: Path to NWB file
        max_trials: Maximum number of trials to include (for debugging)

    Returns:
        Tuple of (neural_data, input_data, output_data) lists
    """
    print(f"  Loading {Path(nwb_path).name}...")

    with NWBHDF5IO(nwb_path, 'r') as io:
        nwbfile = io.read()

        # Get trial information
        n_trials = len(nwbfile.trials)
        n_units = len(nwbfile.units)

        print(f"    Found {n_trials} trials, {n_units} units")

        # Get behavioral events
        behav_events = nwbfile.acquisition['BehavioralEvents']
        go_start_times = behav_events.time_series['go_start_times'].timestamps[:]

        # Get photostim times
        photostim_start_times = behav_events.time_series['photostim_start_times'].timestamps[:]
        photostim_stop_times = behav_events.time_series['photostim_stop_times'].timestamps[:]

        # Cache spike times for all units (avoid repeated NWB access)
        print(f"    Caching spike times for {n_units} units...")
        spike_times_cache = []
        for unit_idx in range(n_units):
            spike_times_cache.append(nwbfile.units['spike_times'][unit_idx])

        # Prepare lists for this session
        neural_trials = []
        input_trials = []
        output_trials = []

        trial_count = 0
        skipped_coverage = 0

        for trial_idx in range(n_trials):
            # Check if we've reached max trials
            if max_trials is not None and trial_count >= max_trials:
                break

            # Get trial data
            trial_data = {col: nwbfile.trials[col][trial_idx]
                         for col in nwbfile.trials.colnames}

            # Check if trial is valid
            if not is_valid_trial(trial_data):
                continue

            # Get go cue time for this trial
            go_time = go_start_times[trial_idx]

            # Define time window relative to go cue
            time_window = (go_time - TIME_BEFORE_GO, go_time + TIME_AFTER_GO)

            # Check if trial has sufficient obs_intervals coverage
            has_coverage, coverage = check_trial_coverage(nwbfile, time_window, min_coverage=0.9)
            if not has_coverage:
                skipped_coverage += 1
                continue

            # Bin spikes for all units using cached spike times
            neural_activity = bin_all_spikes_cached(
                spike_times_cache, time_window, BIN_SIZE, N_TIME_BINS
            )

            # Create input variables (n_input x n_timepoints)
            # Input 0: Time from go cue (same for all time bins)
            time_from_go = np.linspace(-TIME_BEFORE_GO, TIME_AFTER_GO, N_TIME_BINS)

            # Input 1: Trial instruction (0=left, 1=right)
            instruction = 1.0 if trial_data['trial_instruction'] == 'right' else 0.0
            instruction_array = np.full(N_TIME_BINS, instruction)

            # Input 2: Photostim amplitude (power in mW when active, 0 when off)
            photostim_array = np.zeros(N_TIME_BINS)
            if trial_data['photostim_onset'] != 'N/A':
                # Get photostim power for this trial
                photostim_power = float(trial_data['photostim_power'])

                # Find which photostim event corresponds to this trial
                # Match by finding photostim start closest to trial go cue
                trial_time = go_time
                time_diffs = np.abs(photostim_start_times - trial_time)
                if len(time_diffs) > 0 and np.min(time_diffs) < 5.0:  # within 5s
                    photostim_idx = np.argmin(time_diffs)
                    photostim_start = photostim_start_times[photostim_idx]
                    photostim_stop = photostim_stop_times[photostim_idx]

                    # For each time bin, check if photostim is active
                    bin_centers = np.linspace(-TIME_BEFORE_GO + BIN_SIZE/2,
                                             TIME_AFTER_GO - BIN_SIZE/2,
                                             N_TIME_BINS)
                    bin_times = go_time + bin_centers

                    # Set power when photostim is active
                    active_mask = (bin_times >= photostim_start) & (bin_times <= photostim_stop)
                    photostim_array[active_mask] = photostim_power

            # Stack inputs: (3, n_timepoints)
            input_data = np.vstack([time_from_go, instruction_array, photostim_array])

            # Create output variables (n_output,)
            # Output 0: Choice direction (0=left, 1=right)
            choice = get_trial_choice(trial_data['trial_instruction'],
                                     trial_data['outcome'])
            choice_value = 1.0 if choice == 'right' else 0.0

            # Output 1: Outcome (0=miss, 1=hit)
            outcome_value = 1.0 if trial_data['outcome'] == 'hit' else 0.0

            # Outputs are scalar per trial: (2,)
            output_data = np.array([choice_value, outcome_value])

            # Add to lists
            neural_trials.append(neural_activity)
            input_trials.append(input_data)
            output_trials.append(output_data)
            trial_count += 1

        print(f"    Processed {trial_count} valid trials")
        if skipped_coverage > 0:
            print(f"    Skipped {skipped_coverage} trials due to insufficient obs_intervals coverage (<90%)")

    return neural_trials, input_trials, output_trials


def convert_map_dataset(data_dir: str, output_path: str,
                       max_subjects: int = None, max_trials: int = None):
    """
    Convert MAP dataset to standardized format.

    Args:
        data_dir: Path to directory containing subject folders
        output_path: Path to save converted data
        max_subjects: Maximum number of subjects to include (for debugging)
        max_trials: Maximum number of trials per session (for debugging)
    """
    data_path = Path(data_dir)

    # Get all subject directories
    subject_dirs = sorted([d for d in data_path.iterdir() if d.is_dir()
                          and d.name.startswith('sub-')])

    if max_subjects is not None:
        subject_dirs = subject_dirs[:max_subjects]

    print(f"Converting {len(subject_dirs)} subjects...")

    # Initialize data structure
    neural_data = []
    input_data = []
    output_data = []

    for subject_dir in subject_dirs:
        print(f"\nProcessing {subject_dir.name}...")

        # Get all NWB files for this subject
        nwb_files = sorted(subject_dir.glob('*.nwb'))

        # Treat each SESSION as a separate "subject" since neuron populations differ
        for nwb_file in nwb_files:
            session_neural, session_input, session_output = process_session(
                str(nwb_file), max_trials=max_trials
            )

            if len(session_neural) > 0:
                # Add this session as a "subject" to dataset
                neural_data.append(session_neural)
                input_data.append(session_input)
                output_data.append(session_output)

    # Create metadata
    metadata = {
        'task_description': (
            'Auditory delayed response task. Mice hear a tone (3kHz or 12kHz) '
            'indicating which direction to lick (left or right). After a 1.2s '
            'delay and go cue, mice lick the appropriate port for reward. '
            'Data aligned to go cue onset.'
        ),
        'brain_regions': (
            'Multi-region recordings including ALM (anterior lateral motor cortex), '
            'striatum, thalamus, midbrain, and medulla using Neuropixels probes.'
        ),
        'bin_size_s': BIN_SIZE,
        'sampling_rate_hz': 1.0 / BIN_SIZE,
        'time_before_go_s': TIME_BEFORE_GO,
        'time_after_go_s': TIME_AFTER_GO,
        'n_time_bins': N_TIME_BINS,
        'alignment': 'go_cue',
        'input_variables': [
            'time_from_go_cue (s)',
            'trial_instruction (0=left, 1=right)',
            'photostimulation_power (mW, 0 when inactive)'
        ],
        'output_variables': [
            'choice_direction (0=left, 1=right)',
            'outcome (0=miss, 1=hit)'
        ],
        'trial_selection': (
            'Excluded early lick and ignore trials. Only hit and miss trials included. '
            'Trials where the time window had <90% obs_intervals coverage were excluded '
            'to avoid recording gaps.'
        ),
        'obs_intervals_threshold': 0.9,
        'dataset': 'MAP - Brain-wide neural activity underlying memory-guided movement',
        'source': 'DANDI Archive',
        'note': 'Each recording session is treated as a separate subject since neuron populations differ across sessions.',
    }

    # Package data
    data = {
        'neural': neural_data,
        'input': input_data,
        'output': output_data,
        'metadata': metadata
    }

    # Save data
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'wb') as f:
        pickle.dump(data, f)

    print(f"Done! Converted {len(neural_data)} sessions (treated as subjects)")
    print(f"Total trials: {sum(len(subj) for subj in neural_data)}")

    return data


def load_data(data_path: str):
    """Load converted data from pickle file."""
    with open(data_path, 'rb') as f:
        data = pickle.load(f)
    return data


if __name__ == '__main__':
    import sys

    # Default: convert small sample for debugging
    data_dir = 'data'
    output_path = 'map_data_sample.pkl'
    max_subjects = 2
    max_trials = 60  # Need enough samples for PCA, including during cross-validation splits

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--full':
            print("Converting FULL dataset...")
            output_path = 'map_data_full.pkl'
            max_subjects = None
            max_trials = None
        else:
            print("Usage: python convert_map_data.py [--full]")
            print("  (no args): Convert sample (2 subjects, 20 trials each)")
            print("  --full: Convert full dataset")
            sys.exit(1)

    # Run conversion
    data = convert_map_dataset(
        data_dir=data_dir,
        output_path=output_path,
        max_subjects=max_subjects,
        max_trials=max_trials
    )

    # Print summary
    print("\n" + "="*80)
    print("CONVERSION SUMMARY")
    print("="*80)
    print(f"Subjects: {len(data['neural'])}")
    print(f"Total trials: {sum(len(subj) for subj in data['neural'])}")
    print(f"\nExample trial:")
    print(f"  Neural shape: {data['neural'][0][0].shape}")
    print(f"  Input shape: {data['input'][0][0].shape}")
    print(f"  Output shape: {data['output'][0][0].shape}")
