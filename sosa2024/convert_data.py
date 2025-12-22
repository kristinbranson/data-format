"""
Convert Sosa et al. 2024 dataset to standardized format.

This script converts NWB files from the hippocampal reward-relative remapping
study into the standardized decoder format.
"""

import numpy as np
import pynwb
import os
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing


# Reward zone definitions (cm)
REWARD_ZONES = {
    'A': (80, 130),
    'B': (200, 250),
    'C': (320, 370)
}

# Track parameters
TRACK_LENGTH = 450  # cm

# All available subjects in the dataset
ALL_SUBJECTS = ['sub-m11', 'sub-m12', 'sub-m13', 'sub-m14', 'sub-m15',
                'sub-m17', 'sub-m18', 'sub-m19', 'sub-m3', 'sub-m4', 'sub-m7']


def get_reward_zone_from_identifier(identifier: str) -> str:
    """Extract reward zone (A, B, or C) from session identifier."""
    identifier_upper = identifier.upper()
    if 'LOCATIONA' in identifier_upper or 'LOCATION_A' in identifier_upper:
        return 'A'
    elif 'LOCATIONB' in identifier_upper or 'LOCATION_B' in identifier_upper:
        return 'B'
    elif 'LOCATIONC' in identifier_upper or 'LOCATION_C' in identifier_upper:
        return 'C'
    else:
        # Try to infer from median reward zone position
        return None


def calculate_distance_to_reward_zone(position: np.ndarray, zone: str) -> np.ndarray:
    """
    Calculate minimum distance to reward zone.

    Returns:
        - Negative if before zone (position - zone_start)
        - Zero if in zone
        - Positive if after zone (position - zone_end)
    """
    zone_start, zone_end = REWARD_ZONES[zone]

    distance = np.zeros_like(position)

    # Before zone
    before_mask = position < zone_start
    distance[before_mask] = position[before_mask] - zone_start

    # In zone
    in_mask = (position >= zone_start) & (position <= zone_end)
    distance[in_mask] = 0

    # After zone
    after_mask = position > zone_end
    distance[after_mask] = position[after_mask] - zone_end

    return distance


def discretize_distance_to_reward(distance: np.ndarray) -> np.ndarray:
    """
    Discretize distance to reward zone into 7 bins.

    Bins:
        0: distance < -50 cm (far before)
        1: -50 <= distance < -10 cm (approaching)
        2: -10 <= distance < 0 cm (near before)
        3: distance = 0 cm (in reward zone)
        4: 0 < distance <= 10 cm (near after)
        5: 10 < distance <= 50 cm (past reward)
        6: distance > 50 cm (far after)
    """
    bins = np.zeros_like(distance, dtype=int)

    bins[distance < -50] = 0
    bins[(distance >= -50) & (distance < -10)] = 1
    bins[(distance >= -10) & (distance < 0)] = 2
    bins[distance == 0] = 3
    bins[(distance > 0) & (distance <= 10)] = 4
    bins[(distance > 10) & (distance <= 50)] = 5
    bins[distance > 50] = 6

    return bins


def discretize_absolute_position(position: np.ndarray) -> np.ndarray:
    """
    Discretize absolute position into 5 bins of 90 cm each.

    Bins:
        0: 0-90 cm
        1: 90-180 cm
        2: 180-270 cm
        3: 270-360 cm
        4: 360-450 cm
    """
    bins = np.floor(position / 90).astype(int)
    bins = np.clip(bins, 0, 4)  # Ensure bins are in [0, 4]
    return bins


def discretize_speed(speed: np.ndarray) -> np.ndarray:
    """
    Discretize running speed into 5 bins.

    Bins:
        0: < 2 cm/s (stationary)
        1: 2-10 cm/s (slow)
        2: 10-20 cm/s (medium)
        3: 20-40 cm/s (fast)
        4: > 40 cm/s (very fast)
    """
    bins = np.zeros_like(speed, dtype=int)

    bins[speed < 2] = 0
    bins[(speed >= 2) & (speed < 10)] = 1
    bins[(speed >= 10) & (speed < 20)] = 2
    bins[(speed >= 20) & (speed < 40)] = 3
    bins[speed >= 40] = 4

    return bins


def get_reward_zone_label(zone: str) -> int:
    """Convert reward zone letter to integer label."""
    return {'A': 0, 'B': 1, 'C': 2}[zone]


def load_session_data(nwb_file_path: str) -> Dict:
    """Load data from a single NWB file."""
    io = pynwb.NWBHDF5IO(nwb_file_path, 'r')
    nwb = io.read()

    # Get session metadata
    session_id = nwb.identifier

    # Get behavioral time series
    behavioral_ts = nwb.processing['behavior']['BehavioralTimeSeries']
    position = np.array(behavioral_ts.time_series['position'].data[:])
    speed = np.array(behavioral_ts.time_series['speed'].data[:])
    lick = np.array(behavioral_ts.time_series['lick'].data[:])
    trial_num = np.array(behavioral_ts.time_series['trial number'].data[:])
    scanning = np.array(behavioral_ts.time_series['scanning'].data[:])
    reward_zone_binary = np.array(behavioral_ts.time_series['reward_zone'].data[:])
    environment = np.array(behavioral_ts.time_series['environment'].data[:])

    # Get neural data (deconvolved calcium activity)
    deconv = nwb.processing['ophys']['Deconvolved']
    neural_data = np.array(deconv.roi_response_series['plane0'].data[:])  # Shape: (n_timepoints, n_neurons)

    # Get reward delivery info
    reward_ts = nwb.processing['behavior']['BehavioralTimeSeries'].time_series['Reward']
    reward_timestamps = np.array(reward_ts.timestamps[:]) if hasattr(reward_ts, 'timestamps') else None

    io.close()

    return {
        'session_id': session_id,
        'position': position,
        'speed': speed,
        'lick': lick,
        'trial_num': trial_num,
        'scanning': scanning,
        'reward_zone_binary': reward_zone_binary,
        'environment': environment,
        'neural_data': neural_data,
        'reward_timestamps': reward_timestamps
    }


def extract_trial_data(session_data: Dict, trial_id: int, reward_zone: str) -> Optional[Dict]:
    """
    Extract data for a single trial.

    Returns dict with:
        - neural: (n_neurons, n_timepoints)
        - input: dict of input variables
        - output: dict of output variables
        - metadata: trial-level metadata
    """
    # Get trial mask (valid scanning period, on track)
    trial_mask = (
        (session_data['trial_num'] == trial_id) &
        (session_data['scanning'] > 0) &
        (session_data['position'] >= 0) &
        (session_data['position'] <= TRACK_LENGTH)
    )

    if not np.any(trial_mask):
        return None

    # Extract trial data
    position = session_data['position'][trial_mask]
    speed = session_data['speed'][trial_mask]
    lick = session_data['lick'][trial_mask]
    environment = session_data['environment'][trial_mask]
    neural = session_data['neural_data'][trial_mask, :]  # (n_timepoints, n_neurons)

    # Check if trial has valid data
    if len(position) == 0:
        return None

    # Transpose neural data to (n_neurons, n_timepoints)
    neural = neural.T

    # Calculate time within trial (in seconds, assuming ~15.5 Hz)
    sampling_rate = 15.5  # Hz
    time_within_trial = np.arange(len(position)) / sampling_rate

    # Get environment (take mode)
    # Environment encoding in NWB: 0=ENV1, 1=ENV2, -1=invalid
    # Convert to 1=ENV1, 2=ENV2 for decoder format
    valid_env = environment[environment >= 0]  # Exclude -1 values
    if len(valid_env) > 0:
        env_mode = np.median(valid_env)
        environment_label = int(env_mode) + 1  # Convert 0->1, 1->2
    else:
        environment_label = 1  # Default to ENV1

    # Calculate distance to reward zone
    distance_to_reward = calculate_distance_to_reward_zone(position, reward_zone)

    # Check if trial was rewarded (simplified: check if any position was in reward zone)
    # More accurate: check if reward was delivered during this trial
    in_reward_zone = np.any(distance_to_reward == 0)

    # Compute outputs (all categorical/discrete)
    output = {
        'distance_to_reward_bin': discretize_distance_to_reward(distance_to_reward),  # (n_timepoints,)
        'absolute_position_bin': discretize_absolute_position(position),  # (n_timepoints,)
        'speed_bin': discretize_speed(speed),  # (n_timepoints,)
        'lick_binary': (lick > 0).astype(int),  # (n_timepoints,)
        'reward_zone_location': get_reward_zone_label(reward_zone),  # scalar
        'reward_outcome': -1  # To be filled later when we know trial outcomes
    }

    # Compute inputs
    input_data = {
        'time_within_trial': time_within_trial,  # (n_timepoints,)
        'environment': environment_label,  # scalar
        'trial_number': trial_id,  # scalar
        'previous_trial_outcome': -1  # To be filled later
    }

    return {
        'neural': neural,
        'input': input_data,
        'output': output,
        'metadata': {
            'trial_id': trial_id,
            'reward_zone': reward_zone,
            'n_timepoints': len(position)
        }
    }


def infer_reward_zone(session_data: Dict, session_id: str) -> str:
    """Infer reward zone from session identifier or data."""
    # Try to extract from identifier
    zone = get_reward_zone_from_identifier(session_id)

    if zone is not None:
        return zone

    # Fallback: infer from median position where reward_zone_binary is active
    valid_idx = session_data['scanning'] > 0
    reward_positions = session_data['position'][valid_idx & (session_data['reward_zone_binary'] > 0)]

    if len(reward_positions) > 0:
        median_pos = np.median(reward_positions)

        # Determine which zone
        for zone_name, (zone_start, zone_end) in REWARD_ZONES.items():
            if zone_start <= median_pos <= zone_end:
                return zone_name

    # Default to B if can't determine
    print(f"Warning: Could not determine reward zone for session {session_id}, defaulting to B")
    return 'B'


def convert_session(subject_id: str, session_file: str, data_dir: str = 'data',
                   n_trials_to_select: Optional[int] = None) -> Optional[Dict]:
    """
    Convert data for one session.

    Args:
        subject_id: Subject ID (e.g., 'sub-m11')
        session_file: NWB filename for this session
        data_dir: Directory containing NWB files
        n_trials_to_select: Number of trials to select from session (None = all trials)

    Returns:
        Dict with 'trials' list and 'session_metadata', or None if failed
    """
    subject_dir = os.path.join(data_dir, subject_id)
    file_path = os.path.join(subject_dir, session_file)

    print(f"  Loading {session_file}...")

    # Load session
    session_data = load_session_data(file_path)

    # Extract session number from filename (e.g., 'sub-m11_ses-03_behavior+ophys.nwb' -> '03')
    import re
    session_match = re.search(r'ses-(\d+)', session_file)
    session_num = session_match.group(1) if session_match else 'unknown'

    # Infer reward zone
    reward_zone = infer_reward_zone(session_data, session_data['session_id'])
    print(f"    Reward zone: {reward_zone}")

    # Get unique trials
    valid_idx = session_data['scanning'] > 0
    unique_trials = np.unique(session_data['trial_num'][valid_idx])
    unique_trials = unique_trials[unique_trials >= 0]  # Remove -1 values

    if len(unique_trials) == 0:
        print(f"    Warning: No valid trials found")
        return None

    # Select trials (all if n_trials_to_select is None, otherwise evenly spaced subset)
    if n_trials_to_select is None:
        selected_trials = unique_trials
    else:
        n_trials = min(n_trials_to_select, len(unique_trials))
        trial_indices = np.linspace(0, len(unique_trials) - 1, n_trials, dtype=int)
        selected_trials = unique_trials[trial_indices]

    print(f"    Processing {len(selected_trials)} trials (out of {len(unique_trials)})...")

    # Extract trial data
    session_trials = []
    for trial_id in selected_trials:
        trial_data = extract_trial_data(session_data, trial_id, reward_zone)
        if trial_data is not None:
            session_trials.append(trial_data)

    if len(session_trials) == 0:
        print(f"    Warning: No valid trial data extracted")
        return None

    # Determine reward outcomes for each trial
    for i, trial_data in enumerate(session_trials):
        trial_id = trial_data['metadata']['trial_id']
        trial_mask = (
            (session_data['trial_num'] == trial_id) &
            (session_data['scanning'] > 0)
        )

        # Check if reward zone was entered
        reward_zone_active = np.any(session_data['reward_zone_binary'][trial_mask] > 0)
        trial_data['output']['reward_outcome'] = int(reward_zone_active)

        # Set previous trial outcome
        if i > 0:
            trial_data['input']['previous_trial_outcome'] = session_trials[i-1]['output']['reward_outcome']
        else:
            trial_data['input']['previous_trial_outcome'] = 0  # Unknown for first trial

    print(f"    Added {len(session_trials)} valid trials")

    # Get number of neurons for this session (should be consistent across trials)
    n_neurons = session_trials[0]['neural'].shape[0] if len(session_trials) > 0 else 0

    return {
        'trials': session_trials,
        'session_metadata': {
            'mouse_id': subject_id,
            'session_id': session_data['session_id'],
            'session_number': session_num,
            'n_neurons': n_neurons,
            'reward_zone': reward_zone
        }
    }


def convert_subject(subject_id: str, data_dir: str = 'data',
                    session_indices: Optional[List[int]] = None,
                    n_trials_to_select: Optional[int] = None) -> List[Dict]:
    """
    Convert data for one subject, returning sessions separately.

    Args:
        subject_id: Subject ID (e.g., 'sub-m11')
        data_dir: Directory containing NWB files
        session_indices: Which sessions to include (None = all)
        n_trials_to_select: Number of trials to select per session (None = all)

    Returns:
        List of session dicts, each with 'trials' and 'session_metadata'
    """
    subject_dir = os.path.join(data_dir, subject_id)
    nwb_files = sorted([f for f in os.listdir(subject_dir) if f.endswith('.nwb')])

    if session_indices is not None:
        nwb_files = [nwb_files[i] for i in session_indices if i < len(nwb_files)]

    print(f"\nProcessing {subject_id}: {len(nwb_files)} sessions")

    all_sessions = []

    for nwb_file in nwb_files:
        session_data = convert_session(subject_id, nwb_file, data_dir, n_trials_to_select=n_trials_to_select)
        if session_data is not None:
            all_sessions.append(session_data)

    print(f"  Total sessions with valid data: {len(all_sessions)}")
    return all_sessions


def format_for_decoder(all_sessions: List[Dict]) -> Dict:
    """
    Format data into the standardized decoder format.
    Each session is treated as a separate "subject" in the decoder format.

    Args:
        all_sessions: List of session dicts, each with 'trials' and 'session_metadata'

    Returns:
        Dictionary with 'neural', 'input', 'output', 'metadata' keys
    """
    data = {
        'neural': [],
        'input': [],
        'output': [],
        'metadata': {
            'task_description': 'Virtual reality navigation task with hidden reward zones. '
                               'Mice navigate a 450 cm linear track with reward zones at different locations '
                               '(A: 80-130cm, B: 200-250cm, C: 320-370cm) that switch across sessions.',
            'brain_regions': 'Hippocampus CA1',
            'sampling_rate': 15.5,  # Hz
            'n_subjects': len(all_sessions),
            'track_length': TRACK_LENGTH,
            'reward_zones': REWARD_ZONES,
            'subject_info': [],  # Will store mouse_id, session_id, etc. for each "subject"
            'input_variables': {
                'time_within_trial': 'Time from trial start (seconds)',
                'environment': 'Virtual environment (1=ENV1, 2=ENV2)',
                'trial_number': 'Trial number in session',
                'previous_trial_outcome': 'Whether previous trial was rewarded (0=no, 1=yes)'
            },
            'output_variables': {
                'distance_to_reward_bin': '7 bins of distance to reward zone (0=far before, 3=in zone, 6=far after)',
                'absolute_position_bin': '5 bins of absolute position (0-4, 90cm bins)',
                'speed_bin': '5 bins of running speed (0=stationary, 4=very fast)',
                'lick_binary': 'Binary licking indicator (0=no lick, 1=lick)',
                'reward_zone_location': 'Reward zone location (0=A, 1=B, 2=C)',
                'reward_outcome': 'Whether trial was rewarded (0=no, 1=yes)'
            },
            'note': 'Each "subject" in this dataset is actually one recording session. '
                   'Multiple sessions may come from the same mouse (see subject_info).'
        }
    }

    for session_dict in all_sessions:
        subject_trials = session_dict['trials']
        session_meta = session_dict['session_metadata']

        # Store session metadata
        data['metadata']['subject_info'].append(session_meta)
        # Extract neural data for this subject
        subject_neural = [trial['neural'] for trial in subject_trials]
        data['neural'].append(subject_neural)

        # Extract input data for this subject
        subject_input = []
        for trial in subject_trials:
            # Stack all input variables
            # Each input variable should be either scalar or (n_timepoints,)
            # We'll create a 2D array: (n_input_vars, n_timepoints)
            # For scalar inputs, we'll broadcast to all timepoints

            n_timepoints = trial['input']['time_within_trial'].shape[0]

            input_array = np.stack([
                trial['input']['time_within_trial'],  # (n_timepoints,)
                np.full(n_timepoints, trial['input']['environment']),  # scalar -> (n_timepoints,)
                np.full(n_timepoints, trial['input']['trial_number']),  # scalar -> (n_timepoints,)
                np.full(n_timepoints, trial['input']['previous_trial_outcome'])  # scalar -> (n_timepoints,)
            ], axis=0)  # Shape: (4, n_timepoints)

            subject_input.append(input_array)

        data['input'].append(subject_input)

        # Extract output data for this subject
        subject_output = []
        for trial in subject_trials:
            # Stack all output variables
            # Each output variable should be either scalar or (n_timepoints,)

            n_timepoints = trial['output']['distance_to_reward_bin'].shape[0]

            output_array = np.stack([
                trial['output']['distance_to_reward_bin'],  # (n_timepoints,)
                trial['output']['absolute_position_bin'],  # (n_timepoints,)
                trial['output']['speed_bin'],  # (n_timepoints,)
                trial['output']['lick_binary'],  # (n_timepoints,)
                np.full(n_timepoints, trial['output']['reward_zone_location']),  # scalar -> (n_timepoints,)
                np.full(n_timepoints, trial['output']['reward_outcome'])  # scalar -> (n_timepoints,)
            ], axis=0)  # Shape: (6, n_timepoints)

            subject_output.append(output_array)

        data['output'].append(subject_output)

    return data


def load_data(filepath: str) -> Dict:
    """
    Load converted data from pickle file.
    This function will be imported by train_decoder.py
    """
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


def _convert_session_wrapper(args):
    """Wrapper for parallel session conversion."""
    subject_id, session_file, data_dir, n_trials_to_select = args
    try:
        result = convert_session(subject_id, session_file, data_dir, n_trials_to_select)
        return result
    except Exception as e:
        print(f"Error processing {subject_id}/{session_file}: {e}")
        return None


def convert_all_sessions_parallel(subjects: List[str], data_dir: str = 'data',
                                   session_indices: Optional[List[int]] = None,
                                   n_trials_to_select: Optional[int] = None,
                                   n_workers: int = 4) -> List[Dict]:
    """
    Convert all sessions in parallel.

    Args:
        subjects: List of subject IDs
        data_dir: Directory containing NWB files
        session_indices: Which sessions to include (None = all)
        n_trials_to_select: Number of trials per session (None = all)
        n_workers: Number of parallel workers

    Returns:
        List of session dicts
    """
    # Build list of all (subject, session_file) pairs
    tasks = []
    for subject_id in subjects:
        subject_dir = os.path.join(data_dir, subject_id)
        nwb_files = sorted([f for f in os.listdir(subject_dir) if f.endswith('.nwb')])

        if session_indices is not None:
            nwb_files = [nwb_files[i] for i in session_indices if i < len(nwb_files)]

        for nwb_file in nwb_files:
            tasks.append((subject_id, nwb_file, data_dir, n_trials_to_select))

    print(f"\nProcessing {len(tasks)} sessions with {n_workers} workers...")

    all_sessions = []

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_convert_session_wrapper, task): task for task in tasks}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result is not None:
                all_sessions.append(result)

            # Progress update every 10 sessions
            if completed % 10 == 0 or completed == len(tasks):
                print(f"  Progress: {completed}/{len(tasks)} sessions")

    print(f"  Completed: {len(all_sessions)} sessions with valid data")
    return all_sessions


def main():
    """Main conversion script."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert Sosa et al. 2024 dataset to standardized format')
    parser.add_argument('--mode', type=str, choices=['sample', 'full'], default='sample',
                       help='Conversion mode: "sample" for subset of data, "full" for all data (all mice, all trials)')
    parser.add_argument('--subjects', type=str, nargs='+', default=None,
                       help='Subject IDs to convert (default: sub-m11 sub-m12 for sample mode, all 11 mice for full mode)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output filename (default: auto-generated based on mode)')
    parser.add_argument('--n-trials', type=int, default=None,
                       help='Number of trials to select per session (default: 10 for sample mode, all for full mode)')
    parser.add_argument('--parallel', type=int, default=0, metavar='N',
                       help='Number of parallel workers (default: 0 = sequential, recommended: 4-8 for full mode)')

    args = parser.parse_args()

    print("="*60)
    print("Sosa et al. 2024 Dataset Conversion")
    print("="*60)
    print(f"Mode: {args.mode}")

    # Determine subjects based on mode (unless explicitly specified)
    if args.subjects is not None:
        subjects = args.subjects
    elif args.mode == 'full':
        subjects = ALL_SUBJECTS  # All 11 mice
    else:  # sample
        subjects = ['sub-m11', 'sub-m12']  # Default 2 mice for sample

    # Determine n_trials based on mode (unless explicitly specified)
    if args.n_trials is not None:
        n_trials = args.n_trials
    elif args.mode == 'full':
        n_trials = None  # All trials
    else:  # sample
        n_trials = 10

    print(f"Subjects: {', '.join(subjects)}")

    # Determine session selection based on mode
    if args.mode == 'sample':
        # Select subset of sessions (evenly spaced)
        session_indices = [0, 2, 4, 6, 8]  # Select 5 sessions per mouse
        print(f"Session indices: {session_indices}")
    else:  # full
        # Process all sessions
        session_indices = None
        print("Processing all sessions")

    if n_trials is None:
        print("Trials per session: all")
    else:
        print(f"Trials per session: {n_trials}")

    if args.parallel > 0:
        print(f"Parallel workers: {args.parallel}")

    # Collect all sessions (each session will be a "subject" in the decoder format)
    import time
    start_time = time.time()

    if args.parallel > 0:
        # Parallel processing
        all_sessions = convert_all_sessions_parallel(
            subjects, session_indices=session_indices,
            n_trials_to_select=n_trials, n_workers=args.parallel
        )
    else:
        # Sequential processing
        all_sessions = []
        for subject_id in subjects:
            subject_sessions = convert_subject(subject_id, session_indices=session_indices, n_trials_to_select=n_trials)
            all_sessions.extend(subject_sessions)

    elapsed = time.time() - start_time
    print(f"\nTotal sessions collected: {len(all_sessions)} (took {elapsed:.1f}s)")

    # Format for decoder
    print("\nFormatting data for decoder...")
    data = format_for_decoder(all_sessions)

    # Print summary
    print("\n" + "="*60)
    print("Conversion Summary")
    print("="*60)
    print(f"Number of 'subjects' (sessions): {len(data['neural'])}")

    # Count by mouse
    mouse_counts = {}
    for session_info in data['metadata']['subject_info']:
        mouse_id = session_info['mouse_id']
        mouse_counts[mouse_id] = mouse_counts.get(mouse_id, 0) + 1

    print(f"Sessions per mouse:")
    for mouse_id, count in sorted(mouse_counts.items()):
        print(f"  {mouse_id}: {count} sessions")

    # Print first and last few sessions
    n_show = min(3, len(data['neural']))
    for i in list(range(n_show)) + (list(range(len(data['neural']) - n_show, len(data['neural']))) if len(data['neural']) > n_show * 2 else []):
        if i == n_show and len(data['neural']) > n_show * 2:
            print(f"\n  ... ({len(data['neural']) - n_show * 2} more sessions) ...")
            continue
        subject_neural = data['neural'][i]
        session_info = data['metadata']['subject_info'][i]
        print(f"\nSubject {i+1} ({session_info['mouse_id']} session {session_info['session_number']}):")
        print(f"  Reward zone: {session_info['reward_zone']}")
        print(f"  Number of trials: {len(subject_neural)}")
        if len(subject_neural) > 0:
            print(f"  Neurons: {subject_neural[0].shape[0]}")
            print(f"  Timepoints per trial (range): {min(t.shape[1] for t in subject_neural)} - {max(t.shape[1] for t in subject_neural)}")

    # Determine output filename
    if args.output is None:
        if args.mode == 'sample':
            output_file = 'sosa2024_sample_data.pkl'
        else:
            output_file = 'sosa2024_full_data.pkl'
    else:
        output_file = args.output

    # Save data
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    print("\n✓ Conversion complete!")
    print(f"Data saved to: {output_file}")
    print(f"Total trials: {sum(len(s) for s in data['neural'])}")

    return data


if __name__ == '__main__':
    data = main()
