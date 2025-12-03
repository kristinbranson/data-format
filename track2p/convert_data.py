"""
Convert Track2p dataset to standardized decoder format

User Decisions (2025-12-02):
- Trial definition: 2-minute blocks (10 trials per 20-min session)
- Neural data: Deconvolved spikes (spks.npy)
- Decoder inputs: Time within trial (continuous)
- Decoder outputs: Motion energy (tertiles), Postnatal age (Early/Mid/Late), Session number
"""
import numpy as np
import pickle
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
from scipy.ndimage import uniform_filter1d

# Parameters
SAMPLING_RATE = 30  # Hz
TRIAL_DURATION = 120  # seconds (2 minutes)
TRIAL_TIMEPOINTS = int(TRIAL_DURATION * SAMPLING_RATE)  # 3600 timepoints
MOTION_SMOOTHING_WINDOW = 30  # timepoints (1 second at 30 Hz)

def load_subject_data(subject_dir: Path) -> Tuple[List, List, List, List]:
    """
    Load all session data for a single subject

    Returns:
        sessions_spks: List of spike arrays (n_neurons, n_timepoints) for each session
        sessions_motion: List of motion energy arrays (n_timepoints,) for each session
        session_names: List of session directory names
        n_neurons: Number of tracked neurons (consistent across sessions)
    """
    # Get all session directories, sorted by date
    session_dirs = sorted([d for d in subject_dir.iterdir() if d.is_dir()])

    sessions_spks = []
    sessions_motion = []
    session_names = []

    for session_dir in session_dirs:
        # Load neural data
        suite2p_dir = session_dir / 'suite2p' / 'plane0'
        spks = np.load(suite2p_dir / 'spks.npy')

        # Load behavioral data
        move_dir = session_dir / 'move_deve'
        motion_energy = np.load(move_dir / 'motion_energy_glob.npy')

        # Check alignment
        if len(motion_energy) != spks.shape[1]:
            warnings.warn(
                f"Motion energy length ({len(motion_energy)}) != "
                f"spike data length ({spks.shape[1]}) for {session_dir.name}"
            )
            # Interpolate or pad motion energy to match spikes
            if len(motion_energy) < spks.shape[1]:
                # Pad with median value
                pad_length = spks.shape[1] - len(motion_energy)
                motion_energy = np.pad(
                    motion_energy,
                    (0, pad_length),
                    'constant',
                    constant_values=np.median(motion_energy)
                )
            else:
                # Truncate
                motion_energy = motion_energy[:spks.shape[1]]

        sessions_spks.append(spks)
        sessions_motion.append(motion_energy)
        session_names.append(session_dir.name)

    n_neurons = sessions_spks[0].shape[0]

    # Verify consistent neuron count across sessions
    for i, spks in enumerate(sessions_spks):
        if spks.shape[0] != n_neurons:
            raise ValueError(
                f"Inconsistent neuron count in session {session_names[i]}: "
                f"expected {n_neurons}, got {spks.shape[0]}"
            )

    return sessions_spks, sessions_motion, session_names, n_neurons

def segment_into_trials(data: np.ndarray, trial_length: int) -> List[np.ndarray]:
    """
    Segment continuous data into fixed-length trials

    Args:
        data: Array to segment (can be 1D or 2D)
        trial_length: Number of timepoints per trial

    Returns:
        List of trial arrays
    """
    if data.ndim == 1:
        n_timepoints = len(data)
    else:
        n_timepoints = data.shape[-1]  # Assume time is last dimension

    n_trials = n_timepoints // trial_length
    trials = []

    for i in range(n_trials):
        start_idx = i * trial_length
        end_idx = start_idx + trial_length

        if data.ndim == 1:
            trial_data = data[start_idx:end_idx]
        else:
            trial_data = data[:, start_idx:end_idx]

        trials.append(trial_data)

    return trials

def discretize_motion_energy(motion_trials: List[np.ndarray], method='binary', smoothing_window=None) -> List[np.ndarray]:
    """
    Discretize motion energy into categorical states (per timepoint)

    Args:
        motion_trials: List of motion energy arrays for all trials (each shape: (n_timepoints,))
        method: 'binary' for 2 categories (low/high)
        smoothing_window: Window size for smoothing (in timepoints). If None, no smoothing applied.

    Returns:
        List of categorical label arrays (each shape: (n_timepoints,))
    """
    # Apply smoothing if requested
    if smoothing_window is not None and smoothing_window > 1:
        smoothed_trials = []
        for trial in motion_trials:
            # Use uniform filter (moving average) for smoothing
            smoothed = uniform_filter1d(trial, size=smoothing_window, mode='nearest')
            smoothed_trials.append(smoothed)
        motion_trials_to_discretize = smoothed_trials
    else:
        motion_trials_to_discretize = motion_trials

    # Collect all motion energy values across all trials
    all_values = np.concatenate(motion_trials_to_discretize)

    if method == 'binary':
        # Use 90th percentile to separate low from high activity
        threshold = np.percentile(all_values, 90)

        print(f"    Motion energy threshold (90th percentile):")
        print(f"      Low-High boundary: {threshold:,.0f}")
        print(f"      Low activity:  {np.mean(all_values < threshold):.1%} of timepoints")
        print(f"      High activity: {np.mean(all_values >= threshold):.1%} of timepoints")

        # Discretize each trial's timepoints
        categorized_trials = []
        for trial in motion_trials_to_discretize:
            categories = np.zeros(len(trial), dtype=int)
            categories[trial >= threshold] = 1
            categorized_trials.append(categories)

    else:
        raise ValueError(f"Unknown discretization method: {method}")

    return categorized_trials

def map_session_to_age_category(session_idx: int, n_sessions: int) -> int:
    """
    Map session number to developmental age category

    Categories:
        0: Early (first ~1/3 of sessions)
        1: Mid (middle ~1/3 of sessions)
        2: Late (last ~1/3 of sessions)

    Args:
        session_idx: 0-indexed session number
        n_sessions: Total number of sessions

    Returns:
        Age category (0, 1, or 2)
    """
    # Divide sessions into thirds
    third = n_sessions / 3

    if session_idx < third:
        return 0  # Early
    elif session_idx < 2 * third:
        return 1  # Mid
    else:
        return 2  # Late

def create_time_input(trial_length: int, sampling_rate: float) -> np.ndarray:
    """
    Create time within trial input variable

    Args:
        trial_length: Number of timepoints per trial
        sampling_rate: Sampling rate in Hz

    Returns:
        Time array of shape (1, trial_length) in seconds
    """
    time = np.arange(trial_length) / sampling_rate
    return time.reshape(1, -1)

def convert_subject(subject_dir: Path, sample_mode: bool = False) -> Tuple[List, List, List]:
    """
    Convert one subject's data to standardized format

    Returns:
        neural_trials: List of (n_neurons, n_timepoints) arrays
        input_trials: List of (1, n_timepoints) arrays
        output_trials: List of (3,) arrays [motion_cat, age_cat, session_num]
    """
    print(f"\nProcessing {subject_dir.name}...")

    # Load all sessions
    sessions_spks, sessions_motion, session_names, n_neurons = load_subject_data(subject_dir)
    n_sessions = len(sessions_spks)

    print(f"  Sessions: {n_sessions}, Neurons: {n_neurons}")

    # Sample mode: use only first 2 sessions
    if sample_mode:
        sessions_spks = sessions_spks[:2]
        sessions_motion = sessions_motion[:2]
        session_names = session_names[:2]
        n_sessions = 2
        print(f"  [SAMPLE MODE] Using only first 2 sessions")

    # Storage for all trials
    neural_trials = []
    input_trials = []
    output_trials = []

    # First pass: segment all sessions into trials and collect all motion data
    all_spks_trials = []
    all_motion_trials = []
    session_trial_counts = []

    for session_idx, (spks, motion, session_name) in enumerate(
        zip(sessions_spks, sessions_motion, session_names)
    ):
        print(f"    Session {session_idx + 1}/{n_sessions}: {session_name}")

        # Segment into trials
        spks_trials = segment_into_trials(spks, TRIAL_TIMEPOINTS)
        motion_trials = segment_into_trials(motion, TRIAL_TIMEPOINTS)

        n_trials = len(spks_trials)
        print(f"      Trials: {n_trials}")

        all_spks_trials.append(spks_trials)
        all_motion_trials.append(motion_trials)
        session_trial_counts.append(n_trials)

    # Discretize motion energy across ALL sessions (per-subject thresholds)
    print(f"  Computing per-subject motion energy thresholds across all {sum(session_trial_counts)} trials...")
    all_motion_flat = [trial for session_trials in all_motion_trials for trial in session_trials]
    all_motion_categories_flat = discretize_motion_energy(
        all_motion_flat,
        method='binary',
        smoothing_window=MOTION_SMOOTHING_WINDOW
    )

    # Distribute categorized trials back to sessions
    trial_offset = 0
    all_motion_categories = []
    for n_trials in session_trial_counts:
        session_categories = all_motion_categories_flat[trial_offset:trial_offset + n_trials]
        all_motion_categories.append(session_categories)
        trial_offset += n_trials

    # Create time input (same for all trials)
    time_input = create_time_input(TRIAL_TIMEPOINTS, SAMPLING_RATE)

    # Second pass: build output structure
    for session_idx, (spks_trials, motion_categories) in enumerate(
        zip(all_spks_trials, all_motion_categories)
    ):
        # Determine age category for this session
        age_category = map_session_to_age_category(session_idx, len(sessions_spks))

        # Session number (0-indexed for consistency)
        session_number = session_idx

        # Add each trial
        for trial_idx, (spks_trial, motion_cat_timeseries) in enumerate(
            zip(spks_trials, motion_categories)
        ):
            # Neural data: (n_neurons, n_timepoints)
            neural_trials.append(spks_trial.astype(np.float32))

            # Input: time within trial (1, n_timepoints)
            input_trials.append(time_input.astype(np.float32))

            # Output: (3, n_timepoints) - motion is time-varying, age and session are constant per trial
            n_timepoints = len(motion_cat_timeseries)
            age_timeseries = np.full(n_timepoints, age_category, dtype=int)
            session_timeseries = np.full(n_timepoints, session_number, dtype=int)

            output_trial = np.stack([motion_cat_timeseries, age_timeseries, session_timeseries], axis=0)
            output_trials.append(output_trial)

    print(f"  Total trials: {len(neural_trials)}")

    return neural_trials, input_trials, output_trials

def convert_dataset(data_dir: Path, sample_mode: bool = False) -> Dict:
    """
    Convert entire dataset to standardized format

    Args:
        data_dir: Path to data directory containing subject folders
        sample_mode: If True, only process first 2 subjects and 2 sessions each

    Returns:
        data: Dictionary with 'neural', 'input', 'output', 'metadata' keys
    """
    # Get all subject directories
    subject_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir() and d.name.startswith('jm')])

    if sample_mode:
        subject_dirs = subject_dirs[:2]
        print(f"[SAMPLE MODE] Processing only first {len(subject_dirs)} subjects")

    print(f"\nFound {len(subject_dirs)} subjects to process")

    # Storage for all subjects
    neural_all = []
    input_all = []
    output_all = []

    # Process each subject
    for subject_dir in subject_dirs:
        neural_subj, input_subj, output_subj = convert_subject(subject_dir, sample_mode)

        neural_all.append(neural_subj)
        input_all.append(input_subj)
        output_all.append(output_subj)

    # Create metadata
    metadata = {
        'task_description': (
            'Spontaneous neural activity during postnatal development (P7-P14). '
            'Longitudinal 2-photon calcium imaging of developing mouse barrel cortex. '
            'Daily recordings with same neurons tracked across days. '
            'No task - sensory-minimized conditions with free movement on treadmill.'
        ),
        'brain_regions': 'Primary somatosensory cortex (barrel cortex), Layer 2/3',
        'sampling_rate': SAMPLING_RATE,
        'trial_duration_sec': TRIAL_DURATION,
        'trial_timepoints': TRIAL_TIMEPOINTS,
        'preprocessing': (
            'Suite2p pipeline: motion correction, ROI detection, signal extraction, '
            'spike deconvolution. Track2p for longitudinal cell tracking.'
        ),
        'neural_data_type': 'Deconvolved spikes from GCaMP8m calcium imaging',
        'input_variables': {
            'time_within_trial': 'Elapsed time in seconds (0-120s) within each 2-minute trial'
        },
        'output_variables': {
            'motion_energy': f'Behavioral state binary categorization (time-varying): 0=low activity, 1=high activity. Smoothed with {MOTION_SMOOTHING_WINDOW}-timepoint window ({MOTION_SMOOTHING_WINDOW/SAMPLING_RATE:.1f}s). Threshold is 90th percentile computed per-subject across all sessions (~90% low, ~10% high). Shape: (n_timepoints,)',
            'age_category': 'Developmental stage (constant per trial): 0=Early, 1=Mid, 2=Late. Shape: (n_timepoints,) with constant value',
            'session_number': 'Recording session number (constant per trial, 0-indexed: 0-6 for most subjects, 0-5 for jm040). Shape: (n_timepoints,) with constant value'
        },
        'subjects': {
            'count': len(subject_dirs),
            'ids': [d.name for d in subject_dirs],
            'tracked_neurons': [len(neural_all[i][0]) for i in range(len(neural_all))]
        },
        'paper': 'Majnik et al. 2025, eLife 14:RP107540',
        'doi': 'https://doi.org/10.7554/eLife.107540.1'
    }

    # Assemble final data structure
    data = {
        'neural': neural_all,
        'input': input_all,
        'output': output_all,
        'metadata': metadata
    }

    return data

def save_data(data: Dict, output_path: Path):
    """Save converted data to pickle file"""
    print(f"\nSaving data to {output_path}...")
    with open(output_path, 'wb') as f:
        pickle.dump(data, f)
    print(f"Saved successfully. File size: {output_path.stat().st_size / 1e6:.1f} MB")

def load_data(data_path: Path) -> Dict:
    """Load converted data from pickle file"""
    print(f"Loading data from {data_path}...")
    with open(data_path, 'rb') as f:
        data = pickle.load(f)
    print(f"Loaded successfully.")
    return data

if __name__ == '__main__':
    import sys

    # Determine mode
    sample_mode = '--sample' in sys.argv
    full_mode = '--full' in sys.argv

    if not sample_mode and not full_mode:
        print("Usage:")
        print("  python convert_data.py --sample  # Convert sample data (2 subjects, 2 sessions each)")
        print("  python convert_data.py --full    # Convert full dataset (all subjects, all sessions)")
        sys.exit(1)

    # Set paths
    data_dir = Path('data')

    if sample_mode:
        output_path = Path('track2p_sample_data.pkl')
        print("\n" + "=" * 80)
        print("CONVERTING SAMPLE DATA")
        print("=" * 80)
        data = convert_dataset(data_dir, sample_mode=True)
    else:
        output_path = Path('track2p_full_data.pkl')
        print("\n" + "=" * 80)
        print("CONVERTING FULL DATASET")
        print("=" * 80)
        data = convert_dataset(data_dir, sample_mode=False)

    # Save
    save_data(data, output_path)

    # Print summary
    print("\n" + "=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Subjects: {len(data['neural'])}")
    for i, (neural_subj, output_subj) in enumerate(zip(data['neural'], data['output'])):
        subject_id = data['metadata']['subjects']['ids'][i]
        n_neurons = neural_subj[0].shape[0]
        n_trials = len(neural_subj)
        # Unique session numbers (output[2] is now time-varying, so take first value)
        n_sessions = len(set([out[2, 0] for out in output_subj]))
        print(f"  {subject_id}: {n_trials} trials, {n_sessions} sessions, {n_neurons} neurons")

    print("\nOutput file:", output_path)
    print("=" * 80)
