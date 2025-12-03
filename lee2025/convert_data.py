"""
Convert Lee et al. 2025 CA1 spatial navigation data to standardized format.

This script converts data from the paper "Identifying representational structure
in CA1 to benchmark theoretical models of cognitive mapping" into the standardized
format for decoder training and validation.
"""

import h5py
import numpy as np
import pickle
import sys
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Subject IDs for all 7 mice
ALL_SUBJECTS = [
    'QLAK-CA1-08',
    'QLAK-CA1-30',
    'QLAK-CA1-50',
    'QLAK-CA1-51',
    'QLAK-CA1-56',
    'QLAK-CA1-74',
    'QLAK-CA1-75'
]

# Arena parameters
ARENA_SIZE = 75.0  # cm
N_BINS = 3  # 3x3 spatial grid
BIN_SIZE = ARENA_SIZE / N_BINS  # 25 cm per bin

# Neural data smoothing parameters
SAMPLING_RATE = 30  # Hz
SMOOTHING_SIGMA_SEC = 0.3  # seconds
SMOOTHING_SIGMA_SAMPLES = SMOOTHING_SIGMA_SEC * SAMPLING_RATE  # ~9 timepoints


def load_subject_data(subject_id, data_dir='data'):
    """
    Load data for one subject from .mat file.

    Parameters
    ----------
    subject_id : str
        Subject ID (e.g., 'QLAK-CA1-08')
    data_dir : str
        Directory containing .mat files

    Returns
    -------
    dict with keys:
        - trace: list of (n_timepoints, n_neurons) arrays
        - position: list of (n_timepoints, 2) arrays
        - blocked: list of arrays indicating blocked partitions
        - envs: list of environment names
    """
    mat_file = Path(data_dir) / f"{subject_id}.mat"

    if not mat_file.exists():
        raise FileNotFoundError(f"Data file not found: {mat_file}")

    print(f"Loading {subject_id}...")

    with h5py.File(mat_file, 'r') as f:
        # Get number of sessions
        n_sessions = f['trace'].shape[0]

        # Load traces (neural activity)
        traces = []
        trace_refs = f['trace'][:]
        for i in range(n_sessions):
            trace_ref = trace_refs[i, 0]
            trace = f[trace_ref][:]  # (n_timepoints, n_neurons)
            traces.append(trace)

        # Load positions
        positions = []
        pos_refs = f['position'][:]
        for i in range(n_sessions):
            pos_ref = pos_refs[i, 0]
            pos = f[pos_ref][:]  # (n_timepoints, 2)
            positions.append(pos)

        # Load blocked partitions
        blocked_list = []
        blocked_refs = f['blocked'][:]
        for i in range(n_sessions):
            blocked_ref = blocked_refs[0, i]
            blocked = f[blocked_ref][:].flatten()
            blocked_list.append(blocked)

        # Load environment names
        envs = []
        env_refs = f['envs'][:]
        for i in range(n_sessions):
            env_ref = env_refs[0, i]
            env_str = ''.join([chr(int(c)) for c in f[env_ref][:].flatten()])
            envs.append(env_str)

    return {
        'trace': traces,
        'position': positions,
        'blocked': blocked_list,
        'envs': envs,
        'subject_id': subject_id
    }


def position_to_spatial_bin(position):
    """
    Convert continuous (x, y) position to 3x3 spatial bin index.

    Bins are numbered 0-8 in row-major order:
    0 1 2
    3 4 5
    6 7 8

    Parameters
    ----------
    position : array (n_timepoints, 2)
        Position data with columns [x, y]

    Returns
    -------
    bins : array (n_timepoints,)
        Spatial bin index for each timepoint
    """
    x, y = position[:, 0], position[:, 1]

    # Determine bin indices (0, 1, or 2 for each dimension)
    x_bin = np.floor(x / BIN_SIZE).astype(int)
    y_bin = np.floor(y / BIN_SIZE).astype(int)

    # Clip to valid range (handle edge cases at 75.0 cm)
    x_bin = np.clip(x_bin, 0, N_BINS - 1)
    y_bin = np.clip(y_bin, 0, N_BINS - 1)

    # Convert to single bin index (row-major)
    bins = y_bin * N_BINS + x_bin

    return bins


def spatial_bins_to_categorical(bins):
    """
    Convert spatial bin indices to categorical array.

    Parameters
    ----------
    bins : array (n_timepoints,)
        Spatial bin index for each timepoint

    Returns
    -------
    categorical : array (1, n_timepoints)
        Categorical position (0-8) for each timepoint
    """
    # Reshape to (1, n_timepoints) and ensure float32
    categorical = bins.astype(np.float32).reshape(1, -1)

    return categorical


def blocked_to_geometry_vector(blocked):
    """
    Convert blocked partition indices to 9-dimensional geometry vector.

    Parameters
    ----------
    blocked : array
        Indices of blocked partitions (-1 means none blocked)

    Returns
    -------
    geometry : array (9,)
        Binary vector where 1 = walled, 0 = open
    """
    geometry = np.zeros(9, dtype=np.float32)

    # If blocked contains -1, it means no partitions are blocked (full square)
    if len(blocked) == 1 and blocked[0] == -1:
        return geometry

    # Set walled partitions to 1
    for partition_idx in blocked:
        if partition_idx >= 0:
            geometry[int(partition_idx)] = 1.0

    return geometry


def smooth_neural_traces(traces):
    """
    Apply Gaussian temporal smoothing to neural traces to convert binary events to firing rates.

    Parameters
    ----------
    traces : array (n_timepoints, n_neurons)
        Binary neural activity (0/1 for calcium transient events)

    Returns
    -------
    smoothed : array (n_timepoints, n_neurons)
        Smoothed firing rates
    """
    n_timepoints, n_neurons = traces.shape
    smoothed = np.zeros_like(traces, dtype=np.float32)

    # Apply Gaussian filter to each neuron independently
    for neuron_idx in range(n_neurons):
        smoothed[:, neuron_idx] = gaussian_filter1d(
            traces[:, neuron_idx].astype(float),
            sigma=SMOOTHING_SIGMA_SAMPLES,
            mode='constant',
            cval=0.0
        )

    return smoothed


def convert_subject(subject_data):
    """
    Convert one subject's data to standardized format.

    Parameters
    ----------
    subject_data : dict
        Data from load_subject_data()

    Returns
    -------
    neural : list of arrays (n_neurons, n_timepoints)
    input_data : list of arrays (n_input,)
    output_data : list of arrays (n_output, n_timepoints)
    """
    n_sessions = len(subject_data['trace'])

    neural = []
    input_data = []
    output_data = []

    for session_idx in range(n_sessions):
        # Neural data: transpose from (n_timepoints, n_neurons) to (n_neurons, n_timepoints)
        trace = subject_data['trace'][session_idx]

        # Replace NaN with 0
        trace = np.nan_to_num(trace, nan=0.0)

        # Apply Gaussian temporal smoothing to convert binary events to firing rates
        trace_smoothed = smooth_neural_traces(trace)

        # Transpose to (n_neurons, n_timepoints)
        neural_trial = trace_smoothed.T.astype(np.float32)

        # Input: environment geometry (constant per session)
        blocked = subject_data['blocked'][session_idx]
        geometry = blocked_to_geometry_vector(blocked)

        # Output: discretized position (time-varying, categorical)
        position = subject_data['position'][session_idx]
        bins = position_to_spatial_bin(position)
        output_trial = spatial_bins_to_categorical(bins)

        # Verify shapes match
        n_timepoints = neural_trial.shape[1]
        assert output_trial.shape[1] == n_timepoints, \
            f"Output timepoints {output_trial.shape[1]} != neural timepoints {n_timepoints}"

        neural.append(neural_trial)
        input_data.append(geometry)
        output_data.append(output_trial)

    return neural, input_data, output_data


def convert_all_subjects(subject_ids, data_dir='data'):
    """
    Convert data for multiple subjects.

    Parameters
    ----------
    subject_ids : list of str
        List of subject IDs to convert
    data_dir : str
        Directory containing .mat files

    Returns
    -------
    data : dict
        Standardized data format with keys: neural, input, output, metadata
    """
    neural_all = []
    input_all = []
    output_all = []

    for subject_id in subject_ids:
        subject_data = load_subject_data(subject_id, data_dir)
        neural, input_data, output_data = convert_subject(subject_data)

        neural_all.append(neural)
        input_all.append(input_data)
        output_all.append(output_data)

        print(f"  Converted {subject_id}: {len(neural)} sessions, "
              f"{neural[0].shape[0]} neurons, "
              f"{neural[0].shape[1]} timepoints")

    # Create metadata
    metadata = {
        'task_description': 'Spatial navigation in geometrically deformed environments (3x3 grid)',
        'brain_regions': 'CA1 (dorsal hippocampus)',
        'sampling_rate': SAMPLING_RATE,  # Hz
        'time_bin_size': 1.0 / SAMPLING_RATE,  # seconds
        'arena_size': ARENA_SIZE,  # cm
        'n_geometries': 10,
        'n_sequences': 3,
        'n_spatial_bins': 9,
        'spatial_bin_size': BIN_SIZE,  # cm
        'output_type': 'categorical',  # position bin as categorical (0-8)
        'neural_smoothing': f'Gaussian filter, sigma={SMOOTHING_SIGMA_SEC}s ({SMOOTHING_SIGMA_SAMPLES:.1f} samples)',
        'subjects': subject_ids,
        'data_source': 'Lee et al. 2025, Neuron',
        'paper_doi': '10.1016/j.neuron.2024.10.027'
    }

    data = {
        'neural': neural_all,
        'input': input_all,
        'output': output_all,
        'metadata': metadata
    }

    return data


def load_data(data_file):
    """
    Load converted data from pickle file.

    This function is imported by train_decoder.py.

    Parameters
    ----------
    data_file : str
        Path to pickle file containing converted data

    Returns
    -------
    data : dict
        Data dictionary with keys: neural, input, output, metadata
    """
    with open(data_file, 'rb') as f:
        data = pickle.load(f)
    return data


def create_sample_data(output_file='lee2025_sample_data.pkl', data_dir='data',
                      max_timepoints=None):
    """
    Create sample dataset with subset of subjects and sessions.

    Sample includes first 11 sessions (first sequence + closing square) from 2 subjects
    to cover all 10 unique environments.

    Parameters
    ----------
    output_file : str
        Output filename
    data_dir : str
        Directory containing .mat files
    max_timepoints : int, optional
        Maximum timepoints per trial (for memory-constrained testing)
    """
    print("Creating sample dataset...")

    # Use first 2 subjects
    sample_subjects = ALL_SUBJECTS[:2]

    # Load and convert
    data = convert_all_subjects(sample_subjects, data_dir)

    # Keep only first 11 sessions (covers all 10 environments once)
    for i in range(len(data['neural'])):
        data['neural'][i] = data['neural'][i][:11]
        data['input'][i] = data['input'][i][:11]
        data['output'][i] = data['output'][i][:11]

    # Optionally subsample timepoints for memory-constrained testing
    if max_timepoints is not None:
        print(f"  Subsampling to {max_timepoints} timepoints per trial...")
        for i in range(len(data['neural'])):
            for j in range(len(data['neural'][i])):
                data['neural'][i][j] = data['neural'][i][j][:, :max_timepoints]
                data['output'][i][j] = data['output'][i][j][:, :max_timepoints]

    # Update metadata
    data['metadata']['subjects'] = sample_subjects
    note = 'Sample data: 2 subjects, first 11 sessions each (all 10 environments)'
    if max_timepoints is not None:
        note += f', {max_timepoints} timepoints per session'
    data['metadata']['note'] = note

    # Save
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    print(f"Sample data saved to {output_file}")
    print(f"  Subjects: {len(data['neural'])}")
    print(f"  Sessions per subject: {len(data['neural'][0])}")
    print(f"  Neurons: {data['neural'][0][0].shape[0]}")
    print(f"  Timepoints per session: {data['neural'][0][0].shape[1]}")

    # Estimate memory usage
    total_elements = sum(trial.size for mouse in data['neural'] for trial in mouse)
    memory_mb = total_elements * 4 / (1024**2)  # float32 = 4 bytes
    print(f"  Estimated memory: {memory_mb:.1f} MB (data only, ~{memory_mb*4:.1f} MB with SVD overhead)")

    return data


def create_full_data(output_file='lee2025_full_data.pkl', data_dir='data'):
    """
    Create full dataset with all subjects and sessions.
    """
    print("Creating full dataset...")

    data = convert_all_subjects(ALL_SUBJECTS, data_dir)

    # Save
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    print(f"\nFull data saved to {output_file}")
    print(f"  Subjects: {len(data['neural'])}")
    print(f"  Sessions per subject: {len(data['neural'][0])}")
    print(f"  Neurons: {data['neural'][0][0].shape[0]}")
    print(f"  Timepoints per session: {data['neural'][0][0].shape[1]}")

    return data


# For importing into train_decoder.py
input_names = [f'partition_{i}_walled' for i in range(9)]
output_names = ['position_bin']  # Single categorical output


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Convert Lee et al. 2025 data to standardized format')
    parser.add_argument('--sample', action='store_true', help='Create sample dataset')
    parser.add_argument('--full', action='store_true', help='Create full dataset')
    parser.add_argument('--data-dir', default='data', help='Directory containing .mat files')
    parser.add_argument('--max-timepoints', type=int, default=None,
                       help='Maximum timepoints per trial (for memory-constrained testing)')

    args = parser.parse_args()

    if not args.sample and not args.full:
        print("Please specify --sample or --full")
        sys.exit(1)

    if args.sample:
        create_sample_data(data_dir=args.data_dir, max_timepoints=args.max_timepoints)

    if args.full:
        create_full_data(data_dir=args.data_dir)
