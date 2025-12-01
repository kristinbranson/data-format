#!/usr/bin/env python
"""
Convert MAP (Mesoscale Activity Map) dataset from NWB format to standardized format.

This script converts data from the DANDI archive dataset 000363 into the
standardized format specified in CLAUDE.md.

Author: Claude Code
Date: 2025-11-25
"""

import pynwb
import numpy as np
from pathlib import Path
import pickle
from tqdm import tqdm


def bin_spikes(spike_times, trial_start, trial_stop, time_bins):
    """
    Bin spike times into discrete time bins for a single trial.

    Args:
        spike_times: Array of spike times for one unit (in seconds, absolute time)
        trial_start: Trial start time (seconds, absolute)
        trial_stop: Trial stop time (seconds, absolute)
        time_bins: Array of bin edges relative to trial start

    Returns:
        spike_counts: Array of spike counts per bin (n_bins,)
    """
    # Get spikes in this trial
    trial_spikes = spike_times[(spike_times >= trial_start) & (spike_times < trial_stop)]

    # Convert to trial-relative times
    trial_spikes_rel = trial_spikes - trial_start

    # Bin the spikes
    spike_counts, _ = np.histogram(trial_spikes_rel, bins=time_bins)

    return spike_counts.astype(np.float32)


def compute_firing_rates(spike_counts, bin_width):
    """
    Convert spike counts to firing rates (Hz).

    Args:
        spike_counts: Spike counts per bin
        bin_width: Width of each bin in seconds

    Returns:
        firing_rates: Firing rates in Hz
    """
    return spike_counts / bin_width


def process_session(nwb_path, time_window=(-3.0, 3.5), bin_width=0.05,
                    align_event='go', min_fr_threshold=0.1, verbose=True):
    """
    Process a single NWB session file.

    Args:
        nwb_path: Path to NWB file
        time_window: Time window around alignment event (start, end) in seconds
        bin_width: Width of time bins in seconds
        align_event: Event to align to ('go', 'sample', 'delay')
        min_fr_threshold: Minimum average firing rate (Hz) to include neuron
        verbose: Print progress info

    Returns:
        session_data: Dictionary with neural, input, output data for this session
    """
    if verbose:
        print(f"\nProcessing: {Path(nwb_path).name}")

    with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
        nwbfile = io.read()

        # Get trial information
        n_trials = len(nwbfile.trials)
        n_units = len(nwbfile.units)

        if verbose:
            print(f"  Trials: {n_trials}, Units: {n_units}")

        # Create time bins
        time_bins = np.arange(time_window[0], time_window[1] + bin_width, bin_width)
        n_bins = len(time_bins) - 1

        # Get alignment times based on event
        if align_event == 'go':
            # Get go cue times from behavioral events
            go_times = nwbfile.acquisition['BehavioralEvents'].time_series['go_start_times'].timestamps[:]
        elif align_event == 'sample':
            go_times = nwbfile.acquisition['BehavioralEvents'].time_series['sample_start_times'].timestamps[:]
        elif align_event == 'delay':
            go_times = nwbfile.acquisition['BehavioralEvents'].time_series['delay_start_times'].timestamps[:]
        else:
            raise ValueError(f"Unknown align_event: {align_event}")

        # Initialize arrays
        neural_data_all_units = []  # Will be (n_units, n_trials, n_bins)

        # Process each unit
        unit_brain_regions = []
        unit_indices_to_keep = []

        for unit_idx in range(n_units):
            spike_times = nwbfile.units['spike_times'][unit_idx]
            brain_region = nwbfile.units['anno_name'][unit_idx] if 'anno_name' in nwbfile.units.colnames else ''

            # Check average firing rate
            if len(spike_times) > 0:
                recording_duration = spike_times.max() - spike_times.min()
                avg_fr = len(spike_times) / recording_duration if recording_duration > 0 else 0
            else:
                avg_fr = 0

            if avg_fr < min_fr_threshold:
                continue

            unit_brain_regions.append(brain_region)
            unit_indices_to_keep.append(unit_idx)

            # Process each trial for this unit
            unit_trial_data = []
            for trial_idx in range(n_trials):
                # Get trial times
                trial_start = nwbfile.trials['start_time'][trial_idx]
                trial_stop = nwbfile.trials['stop_time'][trial_idx]

                # Adjust trial start based on alignment event
                # Go times are absolute, need to use them as reference
                if trial_idx < len(go_times):
                    align_time = go_times[trial_idx]
                else:
                    # Use trial start if go time not available
                    align_time = trial_start

                # Create absolute time bins for this trial
                trial_time_bins = time_bins + align_time

                # Bin spikes (pass relative time_bins for histogram, not absolute trial_time_bins)
                spike_counts = bin_spikes(spike_times, trial_time_bins[0],
                                         trial_time_bins[-1], time_bins)

                # Convert to firing rates
                firing_rates = compute_firing_rates(spike_counts, bin_width)

                unit_trial_data.append(firing_rates)

            neural_data_all_units.append(unit_trial_data)

        n_good_units = len(unit_indices_to_keep)
        if verbose:
            print(f"  Good units (FR > {min_fr_threshold} Hz): {n_good_units}")

        # Convert to numpy array: (n_units, n_trials, n_bins)
        neural_data_all_units = np.array(neural_data_all_units, dtype=np.float32)

        # Transpose to (n_trials, n_bins, n_units) then to (n_trials, n_units, n_bins)
        # Actually, let's keep it as (n_units, n_trials, n_bins) and transpose per trial
        # Target format wants (n_neurons, n_timepoints) per trial

        # Reorganize to list of trials, each trial is (n_neurons, n_time)
        neural_trials = []
        for trial_idx in range(n_trials):
            # Extract this trial across all units: (n_units, n_bins)
            trial_neural = neural_data_all_units[:, trial_idx, :].T  # (n_bins, n_units) -> transpose to (n_units, n_bins)?
            # Wait, the spec says (n_neurons, n_timepoints), so we want (n_units, n_bins)
            trial_neural = neural_data_all_units[:, trial_idx, :]  # (n_units, n_bins)
            neural_trials.append(trial_neural)

        # Extract input data (task variables)
        input_trials = []
        for trial_idx in range(n_trials):
            trial_instruction = nwbfile.trials['trial_instruction'][trial_idx]
            instruction_binary = 1 if trial_instruction == 'right' else 0

            # Get photostim info
            photostim_onset = nwbfile.trials['photostim_onset'][trial_idx]
            photostim_power = nwbfile.trials['photostim_power'][trial_idx]

            # Handle NaN values
            if isinstance(photostim_onset, str) and photostim_onset == 'N/A':
                photostim_onset = 0.0
                photostim_power = 0.0

            # Create input vector
            # For now: [instruction (0/1), photostim_onset, photostim_power]
            input_vec = np.array([instruction_binary, photostim_onset, photostim_power],
                                dtype=np.float32)
            input_trials.append(input_vec)

        # Extract output data (behavioral responses)
        output_trials = []
        for trial_idx in range(n_trials):
            outcome = nwbfile.trials['outcome'][trial_idx]
            early_lick = nwbfile.trials['early_lick'][trial_idx]
            trial_instruction = nwbfile.trials['trial_instruction'][trial_idx]

            # Encode outcome as class: 0=miss, 1=ignore, 2=hit
            if outcome == 'miss':
                outcome_class = 0.0
            elif outcome == 'ignore':
                outcome_class = 1.0
            elif outcome == 'hit':
                outcome_class = 2.0
            else:
                raise ValueError(f"Unknown outcome: {outcome}")

            # Encode early lick: 0=not early, 1=early
            early_lick_code = 1.0 if early_lick == 'early' else 0.0

            # Encode action: 0=lick left, 1=ignore, 2=lick right
            # Infer action from outcome and instruction
            if outcome == 'ignore':
                action = 1.0  # Mouse didn't lick
            elif outcome == 'hit':
                # Mouse licked the correct side
                action = 0.0 if trial_instruction == 'left' else 2.0
            elif outcome == 'miss':
                # Mouse licked the wrong side
                action = 2.0 if trial_instruction == 'left' else 0.0
            else:
                raise ValueError(f"Unknown outcome: {outcome}")

            # Create output vector: [outcome_class, early_lick, action]
            output_vec = np.array([outcome_class, early_lick_code, action], dtype=np.float32)
            output_trials.append(output_vec)

        # Collect metadata (including source file for verification)
        session_metadata = {
            'source_file': str(nwb_path),  # Store source NWB path
            'subject_id': nwbfile.subject.subject_id if nwbfile.subject else 'unknown',
            'session_start_time': str(nwbfile.session_start_time),
            'session_description': nwbfile.session_description,
            'n_trials': n_trials,
            'n_trials_original': len(nwbfile.trials),  # Original trial count before filtering
            'n_units_original': n_units,  # Original unit count before filtering
            'n_units': n_good_units,
            'brain_regions': unit_brain_regions,
            'time_window': time_window,
            'bin_width': bin_width,
            'align_event': align_event,
            'unit_indices': unit_indices_to_keep,
        }

        return {
            'neural': neural_trials,
            'input': input_trials,
            'output': output_trials,
            'metadata': session_metadata,
        }


def convert_map_dataset(data_dir='data',
                       output_path='map_standardized.pkl',
                       time_window=(-3.0, 3.5),
                       bin_width=0.05,
                       align_event='go',
                       max_sessions_per_subject=None,
                       max_subjects=None,
                       min_fr_threshold=0.1):
    """
    Convert the entire MAP dataset to standardized format.

    Args:
        data_dir: Directory containing subject folders with NWB files
        output_path: Path to save the converted data
        time_window: Time window around alignment event (start, end) in seconds
        bin_width: Width of time bins in seconds
        align_event: Event to align to ('go', 'sample', 'delay')
        max_sessions_per_subject: Maximum number of sessions per subject (None = all)
        max_subjects: Maximum number of subjects to process (None = all)
        min_fr_threshold: Minimum average firing rate (Hz) to include neuron

    Returns:
        data: Dictionary in standardized format
    """
    data_path = Path(data_dir)

    # Find all subject directories
    subject_dirs = sorted([d for d in data_path.iterdir() if d.is_dir() and d.name.startswith('sub-')])

    # Limit number of subjects if requested
    if max_subjects is not None:
        subject_dirs = subject_dirs[:max_subjects]

    print(f"Found {len(subject_dirs)} subjects")

    # Initialize output structure
    neural_all_subjects = []
    input_all_subjects = []
    output_all_subjects = []
    subject_metadata = []

    # Process each subject
    for subject_dir in tqdm(subject_dirs, desc="Processing subjects"):
        # Find all NWB files for this subject
        nwb_files = sorted(list(subject_dir.glob('*.nwb')))

        if max_sessions_per_subject is not None:
            nwb_files = nwb_files[:max_sessions_per_subject]

        print(f"\nSubject: {subject_dir.name}, Sessions: {len(nwb_files)}")

        # For now, we'll treat each session separately and later can combine
        # Let's combine all sessions for a subject into one "subject"
        subject_neural_trials = []
        subject_input_trials = []
        subject_output_trials = []
        subject_brain_regions = []
        subject_sessions = []  # Store session metadata

        for nwb_file in nwb_files:
            try:
                session_data = process_session(
                    nwb_file,
                    time_window=time_window,
                    bin_width=bin_width,
                    align_event=align_event,
                    min_fr_threshold=min_fr_threshold,
                    verbose=False
                )

                # Accumulate trials from this session
                subject_neural_trials.extend(session_data['neural'])
                subject_input_trials.extend(session_data['input'])
                subject_output_trials.extend(session_data['output'])

                # Store session metadata (including source_file)
                subject_sessions.append(session_data['metadata'])

                # Collect brain regions (should be consistent across sessions)
                if len(subject_brain_regions) == 0:
                    subject_brain_regions = session_data['metadata']['brain_regions']

            except Exception as e:
                print(f"  Error processing {nwb_file.name}: {e}")
                continue

        if len(subject_neural_trials) > 0:
            neural_all_subjects.append(subject_neural_trials)
            input_all_subjects.append(subject_input_trials)
            output_all_subjects.append(subject_output_trials)

            # Include first session's source_file for verification (if only 1 session)
            source_file = subject_sessions[0].get('source_file') if len(subject_sessions) > 0 else None

            subject_metadata.append({
                'subject_id': subject_dir.name,
                'n_sessions': len(nwb_files),
                'n_trials': len(subject_neural_trials),
                'brain_regions': subject_brain_regions,
                'source_file': source_file,  # For verification
                'sessions': subject_sessions,  # Store all session metadata
            })

            print(f"  Total trials for {subject_dir.name}: {len(subject_neural_trials)}")

    # Compile metadata
    all_brain_regions = set()
    for subj_meta in subject_metadata:
        all_brain_regions.update(subj_meta['brain_regions'])

    metadata = {
        'task_description': (
            'Audio delay task: Memory-guided directional licking task. '
            'Mice hear an auditory cue (left or right), wait through a delay period, '
            'then lick in the corresponding direction after a go cue.'
        ),
        'brain_regions': ', '.join(sorted(all_brain_regions)) if all_brain_regions else 'Multiple regions',
        'dataset': 'DANDI:000363 - Mesoscale Activity Map',
        'species': 'Mus musculus',
        'n_subjects': len(neural_all_subjects),
        'time_window': time_window,
        'bin_width': bin_width,
        'align_event': align_event,
        'sampling_rate': 1.0 / bin_width,  # Hz
        'input_description': 'Trial instruction (0=left, 1=right), photostim onset (s), photostim power (mW)',
        'output_description': 'Class labels: output[0]=outcome (0=miss, 1=ignore, 2=hit), output[1]=early_lick (0=not early, 1=early), output[2]=action (0=lick left, 1=ignore, 2=lick right)',
        'subject_metadata': subject_metadata,
    }

    # Create final data structure
    data = {
        'neural': neural_all_subjects,
        'input': input_all_subjects,
        'output': output_all_subjects,
        'metadata': metadata,
    }

    # Run sanity checks before saving
    print("\nRunning sanity checks...")
    from utils import sanity_check_data
    sanity_passed = sanity_check_data(data, verbose=True)

    if not sanity_passed:
        print("\n⚠ WARNING: Sanity checks failed! Please review the issues above.")
        print("Data will still be saved, but may contain errors.")

    # Save to pickle
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'wb') as f:
        pickle.dump(data, f)

    print("Conversion complete!")
    print(f"Total subjects: {len(neural_all_subjects)}")
    print(f"Total trials: {sum(len(trials) for trials in neural_all_subjects)}")

    return data


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert MAP dataset to standardized format OR verify/validate existing data',
        epilog='Examples:\n'
               '  Convert: python %(prog)s --data-dir data --output map.pkl\n'
               '  Verify:  python %(prog)s --input map.pkl --verify-source --sanity-check\n'
               '  Visualize: python %(prog)s --input map.pkl --visualize',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Mode selection
    parser.add_argument('--input', help='Load and verify existing data file (skips conversion)')

    # Conversion arguments
    parser.add_argument('--data-dir', default='data', help='Directory containing NWB files')
    parser.add_argument('--output', default='map_standardized.pkl', help='Output pickle file')
    parser.add_argument('--time-window', nargs=2, type=float, default=[-3.0, 3.5],
                       help='Time window around alignment event (start end)')
    parser.add_argument('--bin-width', type=float, default=0.05, help='Time bin width in seconds')
    parser.add_argument('--align-event', default='go', choices=['go', 'sample', 'delay'],
                       help='Event to align neural data to')
    parser.add_argument('--max-sessions', type=int, default=None,
                       help='Maximum sessions per subject (for testing)')
    parser.add_argument('--max-subjects', type=int, default=None,
                       help='Maximum number of subjects to process (for testing)')
    parser.add_argument('--min-fr', type=float, default=0.1,
                       help='Minimum firing rate threshold (Hz)')

    # Verification arguments (work with --input)
    parser.add_argument('--validate', action='store_true', help='Validate data structure')
    parser.add_argument('--verify-source', action='store_true', help='Verify against source NWB files')
    parser.add_argument('--sanity-check', action='store_true', help='Run sanity checks')
    parser.add_argument('--visualize', action='store_true', help='Create visualizations')
    parser.add_argument('--output-dir', default='visualizations', help='Output directory for plots')
    parser.add_argument('--subject-idx', type=int, default=0, help='Subject index to analyze')

    args = parser.parse_args()

    if args.input:
        # Verification mode - load existing file
        from utils import (load_data, validate_data_structure, print_data_summary,
                          verify_against_source, sanity_check_data, visualize_sample_data)

        print(f"Loading data from {args.input}...")
        data = load_data(args.input)

        # Always validate structure
        is_valid = validate_data_structure(data)

        if is_valid:
            # Print summary
            print_data_summary(data)

            # Run source verification if requested
            if args.verify_source:
                print()
                verify_passed = verify_against_source(data)
                if not verify_passed:
                    print("\n⚠ Warning: Source verification failed. Please review the output above.")

            # Run sanity checks if requested
            if args.sanity_check:
                print()
                sanity_passed = sanity_check_data(data)
                if not sanity_passed:
                    print("\n⚠ Warning: Some sanity checks failed. Please review the output above.")

            # Create visualizations if requested
            if args.visualize:
                print()
                visualize_sample_data(data, output_dir=args.output_dir, subject_idx=args.subject_idx)
        else:
            print("\nValidation failed. Skipping other operations.")
    else:
        # Conversion mode - convert NWB files
        data = convert_map_dataset(
            data_dir=args.data_dir,
            output_path=args.output,
            time_window=tuple(args.time_window),
            bin_width=args.bin_width,
            align_event=args.align_event,
            max_sessions_per_subject=args.max_sessions,
            max_subjects=args.max_subjects,
            min_fr_threshold=args.min_fr,
        )
