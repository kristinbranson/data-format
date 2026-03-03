"""Convert lee2025 .mat files to standardized pickle format.

Usage:
    python -u convert_data.py <output_path.pkl>

The neural trace data is binary (0/1/NaN). To save memory, it is stored as
int8 with -1 representing NaN (missing neuron).

Data structure: each .mat file is one subject with one session. Each session
contains multiple trials (individual ~40 min recordings). The outer list is
indexed by session (one per subject), the inner list by trial.
"""

import sys
import glob
import numpy as np
import h5py
import pickle


ARENA_SIZE = 75.0
N_GRID = 5
N_BLOCKED_POSITIONS = 9
TIME_BIN_SIZE = 1000.0 / 30.0  # ~33.33 ms


def discretize_position(position, n_grid=N_GRID, arena_size=ARENA_SIZE):
    """Discretize (2, n_timepoints) position into grid class labels 0..n_grid^2-1."""
    edges = np.linspace(0, arena_size, n_grid + 1)[1:-1]
    x_bin = np.clip(np.digitize(position[0], edges), 0, n_grid - 1)
    y_bin = np.clip(np.digitize(position[1], edges), 0, n_grid - 1)
    return (y_bin * n_grid + x_bin).astype(np.int8)


def encode_blocked(blk_indices, n_positions=N_BLOCKED_POSITIONS):
    """Convert blocked indices to one-hot encoding.

    Args:
        blk_indices: array of blocked position indices, or [-1] if none blocked
        n_positions: total number of possible blocked positions

    Returns:
        (n_positions,) array with 1s at blocked indices, 0s elsewhere
    """
    blocked = np.zeros(n_positions, dtype=np.int8)
    if not (len(blk_indices) == 1 and blk_indices[0] == -1):
        blocked[blk_indices.astype(int)] = 1
    return blocked


def process_mat_file(filepath):
    """Process a single .mat file into lists of trials for neural/input/output.

    Returns:
        neural_trials: list of (n_neurons, n_timepoints) int8 arrays
        input_trials: list of (n_blocked_positions,) int8 arrays
        output_trials: list of (n_timepoints,) int8 arrays
    """
    f = h5py.File(filepath, 'r')

    trace_refs = f['trace']
    pos_refs = f['position']
    blk_refs = f['blocked'][:][0]
    n_trials = trace_refs.shape[0]

    neural_trials = []
    input_trials = []
    output_trials = []

    for i in range(n_trials):
        # trace: (timepoints, neurons) -> (neurons, timepoints), int8 with -1 for NaN
        trace = f[trace_refs[i][0]][:]
        nan_mask = np.isnan(trace)
        trace[nan_mask] = -1
        trace_int8 = trace.astype(np.int8)
        neural_trials.append(trace_int8.T)

        # position -> discretized class labels (1, n_timepoints) as int8
        position = f[pos_refs[i][0]][:].T
        output_trials.append(discretize_position(position)[np.newaxis, :])

        # blocked -> one-hot (n_blocked_positions,) as int8
        blk_indices = f[blk_refs[i]][:].flatten()
        input_trials.append(encode_blocked(blk_indices))

    f.close()
    return neural_trials, input_trials, output_trials


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python -u {sys.argv[0]} <output_path.pkl>")
        sys.exit(1)

    output_path = sys.argv[1]
    mat_files = sorted(glob.glob('./data/*.mat'))
    print(f"Found {len(mat_files)} subjects")

    subjects = []
    all_neural = []
    all_input = []
    all_output = []
    all_region_idx = []

    for mat_file in mat_files:
        name = mat_file.split('/')[-1].replace('.mat', '')
        subjects.append(name)
        print(f"\nProcessing {name}...")

        neural_trials, input_trials, output_trials = process_mat_file(mat_file)
        n_trials = len(neural_trials)
        n_neurons = neural_trials[0].shape[0]
        n_timepoints = neural_trials[0].shape[1]
        print(f"  {n_trials} trials, {n_neurons} neurons, {n_timepoints} timepoints/trial")

        all_neural.append(neural_trials)
        all_input.append(input_trials)
        all_output.append(output_trials)
        all_region_idx.append(np.zeros(n_neurons, dtype=np.int8))  # all CA1

    n_classes = N_GRID ** 2
    output_values = [[f"grid_{i}" for i in range(n_classes)]]

    data = {
        'neural': all_neural,
        'input': all_input,
        'output': all_output,

        'subjects': subjects,
        'subject_idx': np.arange(len(subjects)),

        'brain_regions': ['CA1'],
        'brain_region_idx': all_region_idx,

        'input_names': [f'blocked_{i}' for i in range(N_BLOCKED_POSITIONS)],
        'output_names': ['position'],
        'output_values': output_values,

        'metadata': {
            'time_bin_size': TIME_BIN_SIZE,
            'arena_size': [75, 75],
            'n_grid': N_GRID,
            'neural_encoding': 'int8: 0=inactive, 1=active, -1=missing (NaN)',
        },
    }

    print(f"\nSaving to {output_path}...")
    with open(output_path, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    total_trials = sum(len(s) for s in all_neural)
    print(f"Done. {len(subjects)} subjects, {total_trials} total trials")


if __name__ == '__main__':
    main()
