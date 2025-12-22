"""
Convert Hasnain et al. 2024 data to standardized format

This script converts the two-context task data into the format required for
decoder analysis.

Data format:
{
    'neural': [subject][trial] -> (n_neurons, n_timebins)
    'input': [subject][trial] -> (n_input_features, n_timebins)
    'output': [subject][trial] -> (n_output_features, n_timebins) or (n_output_features,)
    'metadata': {...}
}
"""

import h5py
import numpy as np
import os
import pickle
from scipy import interpolate

# =============================================================================
# Configuration
# =============================================================================

CONFIG = {
    # Temporal parameters
    'bin_size_ms': 75,  # From original paper
    'align_event': 'goCue',  # Align to go cue
    'time_window': [-2.0, 1.5],  # Seconds relative to go cue

    # Neuron filtering (from paper: "All units with firing rates exceeding 1 Hz were included")
    'min_firing_rate_hz': 1.0,  # Minimum firing rate threshold

    # Trial selection
    'include_trial_types': ['hit', 'miss', 'early'],  # Exclude 'no' response trials
    'min_trials_per_condition': 5,  # Minimum trials needed

    # Data paths
    'data_dir': 'data/Ephys_Behavior',
    'output_file_sample': 'hasnain2024_sample_data.pkl',
    'output_file_full': 'hasnain2024_full_data.pkl',
}

# =============================================================================
# Helper Functions
# =============================================================================

def decode_matlab_string(data, f):
    """Decode a MATLAB string from HDF5 reference"""
    if isinstance(data, h5py.h5r.Reference):
        data = f[data][()]

    if isinstance(data, np.ndarray):
        if data.dtype in [np.uint16, np.uint8]:
            return ''.join([chr(int(x)) for x in data.flatten()])
    return str(data)

def get_trial_info(bp, trial_idx):
    """Extract trial information"""
    info = {
        'is_left': bool(bp['L'][0, trial_idx]),
        'is_right': bool(bp['R'][0, trial_idx]),
        'is_hit': bool(bp['hit'][0, trial_idx]),
        'is_miss': bool(bp['miss'][0, trial_idx]),
        'is_early': bool(bp['early'][0, trial_idx]),
        'is_no': bool(bp['no'][0, trial_idx]),
        'is_autowater': bool(bp['autowater'][0, trial_idx]),
    }
    return info

def get_event_times(bp_ev, trial_idx):
    """Extract event times for a trial"""
    events = {
        'sample': bp_ev['sample'][0, trial_idx],
        'delay': bp_ev['delay'][0, trial_idx],
        'goCue': bp_ev['goCue'][0, trial_idx],
        'reward': bp_ev['reward'][0, trial_idx],
    }
    return events

def bin_spikes(spike_times, time_bins):
    """
    Bin spike times into firing rates

    Parameters:
    -----------
    spike_times : array
        Spike times in seconds
    time_bins : array
        Bin edges in seconds

    Returns:
    --------
    firing_rates : array
        Firing rate in each bin (Hz)
    """
    counts, _ = np.histogram(spike_times, bins=time_bins)
    bin_width = np.diff(time_bins)[0]
    firing_rates = counts / bin_width
    return firing_rates

def compute_session_firing_rates(f, obj):
    """
    Compute session-wide firing rate for each neuron.

    Returns:
    --------
    firing_rates : list of float
        Firing rate in Hz for each neuron
    neuron_info : list of dict
        Info about each neuron (probe_idx, unit_idx)
    """
    clu = obj['clu']
    clu_data = clu[()]

    firing_rates = []
    neuron_info = []

    for probe_idx, clu_ref in enumerate(clu_data.flatten()):
        probe = f[clu_ref]
        n_units = probe['tm'].shape[0]

        for unit_idx in range(n_units):
            # Get all spike times for this neuron
            tm_ref = probe['tm'][unit_idx, 0]
            spike_times = f[tm_ref][()].flatten()
            n_spikes = len(spike_times)

            # Calculate firing rate
            if n_spikes > 1:
                duration = spike_times[-1] - spike_times[0]
                if duration > 0:
                    fr = n_spikes / duration
                else:
                    fr = 0.0
            else:
                fr = 0.0

            firing_rates.append(fr)
            neuron_info.append({'probe_idx': probe_idx, 'unit_idx': unit_idx})

    return firing_rates, neuron_info


def extract_neural_data(f, obj, trial_idx, time_bins, neuron_mask=None):
    """
    Extract and bin neural data for one trial

    Parameters:
    -----------
    f : h5py.File
        Open HDF5 file handle
    obj : h5py.Group
        The 'obj' group from the file
    trial_idx : int
        Trial index (0-based)
    time_bins : array
        Time bin edges
    neuron_mask : array of bool, optional
        Which neurons to include (True = include). If None, include all.

    Returns:
    --------
    neural_matrix : array (n_neurons, n_timebins)
    """
    clu = obj['clu']
    clu_data = clu[()]

    all_rates = []
    neuron_idx = 0

    # Process both probes
    for probe_idx, clu_ref in enumerate(clu_data.flatten()):
        probe = f[clu_ref]
        n_units = probe['tm'].shape[0]

        for unit_idx in range(n_units):
            # Check if this neuron should be included
            if neuron_mask is not None and not neuron_mask[neuron_idx]:
                neuron_idx += 1
                continue

            # Get spike times for this trial
            trialtm_ref = probe['trialtm'][unit_idx, 0]
            trial_nums_ref = probe['trial'][unit_idx, 0]

            trialtm_data = f[trialtm_ref][()].flatten()
            trial_nums = f[trial_nums_ref][()].flatten()

            # Get spikes for this trial (trial numbers are 1-indexed)
            trial_mask = trial_nums == (trial_idx + 1)
            trial_spikes = trialtm_data[trial_mask]

            # Bin the spikes
            firing_rate = bin_spikes(trial_spikes, time_bins)
            all_rates.append(firing_rate)
            neuron_idx += 1

    # Stack into matrix
    neural_matrix = np.array(all_rates)  # (n_neurons, n_timebins)
    return neural_matrix

def extract_kinematic_data(f, obj, trial_idx, time_bins):
    """
    Extract and resample kinematic data for one trial

    Returns:
    --------
    kinematic_matrix : array (n_features, n_timebins)
    """
    traj = obj['traj']
    traj_data = traj[()]

    all_features = []
    feature_names = []

    # Process both camera views
    for cam_idx, traj_ref in enumerate(traj_data.flatten()):
        cam = f[traj_ref]

        # Get kinematic time series for this trial
        ts_ref = cam['ts'][trial_idx, 0]
        frameTimes_ref = cam['frameTimes'][trial_idx, 0]

        ts_data = f[ts_ref][()]  # Shape: (n_features, 3, n_frames)
        frameTimes = f[frameTimes_ref][()].flatten()

        # Get feature names
        featNames_ref = cam['featNames'][trial_idx, 0]
        featNames_data = f[featNames_ref]

        n_feat = featNames_data.shape[0]
        for feat_idx in range(n_feat):
            name_ref = featNames_data[feat_idx, 0]
            name = decode_matlab_string(f[name_ref][()], f)

            # Extract all components of this feature (x, y, velocity, etc.)
            for comp_idx in range(ts_data.shape[1]):
                feat_timeseries = ts_data[feat_idx, comp_idx, :]

                # Remove NaNs for interpolation
                valid_mask = ~np.isnan(feat_timeseries)
                if np.sum(valid_mask) == 0:
                    # All NaNs, fill with zeros
                    feat_timeseries = np.zeros_like(feat_timeseries)
                    valid_mask = np.ones_like(valid_mask, dtype=bool)

                valid_times = frameTimes[valid_mask]
                valid_values = feat_timeseries[valid_mask]

                # Interpolate to bin centers
                bin_centers = (time_bins[:-1] + time_bins[1:]) / 2

                if len(valid_times) > 1:
                    # Interpolate
                    f_interp = interpolate.interp1d(
                        valid_times, valid_values,
                        kind='linear',
                        bounds_error=False,
                        fill_value=0.0
                    )
                    resampled = f_interp(bin_centers)
                else:
                    # Not enough data, use zeros
                    resampled = np.zeros_like(bin_centers)

                # Ensure no NaNs remain
                resampled = np.nan_to_num(resampled, nan=0.0, posinf=0.0, neginf=0.0)

                all_features.append(resampled)
                feature_names.append(f"cam{cam_idx+1}_{name}_comp{comp_idx}")

    kinematic_matrix = np.array(all_features)  # (n_features, n_timebins)
    return kinematic_matrix, feature_names

def create_input_matrix(events, align_time, time_bins, kinematic_matrix):
    """
    Create input feature matrix

    Inputs:
    1. Time from go cue
    2. Kinematic features
    3. Time to sample onset
    4. Time to reward

    Returns:
    --------
    input_matrix : array (n_input_features, n_timebins)
    """
    bin_centers = (time_bins[:-1] + time_bins[1:]) / 2

    # 1. Time from go cue (relative to alignment point)
    time_from_gocue = bin_centers.reshape(1, -1)

    # 2. Time to sample onset (negative before, positive after)
    time_to_sample = (events['sample'] - align_time - bin_centers).reshape(1, -1)

    # 3. Time to reward (use large negative value if no reward)
    if not np.isnan(events['reward']):
        time_to_reward = (events['reward'] - align_time - bin_centers).reshape(1, -1)
    else:
        # Use -999 as sentinel value for "no reward"
        time_to_reward = np.full((1, len(bin_centers)), -999.0)

    # Combine all inputs
    input_matrix = np.vstack([
        time_from_gocue,
        time_to_sample,
        time_to_reward,
        kinematic_matrix
    ])

    return input_matrix

def create_output_matrix(trial_info, n_timebins):
    """
    Create output feature matrix

    Outputs (all time-invariant, repeated for each timebin):
    1. Lick direction (0=Left, 1=Right)
    2. Behavioral context (0=DR, 1=WC)
    3. Trial outcome (0=Incorrect, 1=Correct)

    Returns:
    --------
    output_matrix : array (n_output_features,) - scalar per trial
    """
    # Lick direction (which side was cued/rewarded)
    lick_dir = 1 if trial_info['is_right'] else 0

    # Behavioral context (DR=0, WC=1)
    context = 1 if trial_info['is_autowater'] else 0

    # Trial outcome (Correct=1, Incorrect=0)
    outcome = 1 if trial_info['is_hit'] else 0

    # Return as scalar array (decoder.py will handle per-trial outputs)
    output_matrix = np.array([lick_dir, context, outcome])

    return output_matrix

# =============================================================================
# Main Conversion Function
# =============================================================================

def convert_session(file_path, config, max_trials=None):
    """
    Convert one session file

    Parameters:
    -----------
    file_path : str
        Path to .mat file
    config : dict
        Configuration parameters
    max_trials : int or None
        Maximum number of trials to process (for sampling)

    Returns:
    --------
    session_data : dict
        Converted data for this session
    """
    print(f"Converting: {os.path.basename(file_path)}")

    bin_size_sec = config['bin_size_ms'] / 1000.0
    time_window = config['time_window']
    min_firing_rate = config.get('min_firing_rate_hz', 1.0)  # Default: 1 Hz threshold

    # Create time bins
    time_bins = np.arange(time_window[0], time_window[1] + bin_size_sec, bin_size_sec)
    bin_centers = (time_bins[:-1] + time_bins[1:]) / 2
    n_timebins = len(bin_centers)

    neural_trials = []
    input_trials = []
    output_trials = []
    trial_metadata = []

    with h5py.File(file_path, 'r') as f:
        obj = f['obj']
        bp = obj['bp']
        bp_ev = bp['ev']

        # Compute session-wide firing rates and filter neurons
        firing_rates, neuron_info = compute_session_firing_rates(f, obj)
        neuron_mask = np.array([fr >= min_firing_rate for fr in firing_rates])
        n_total_neurons = len(firing_rates)
        n_kept_neurons = np.sum(neuron_mask)
        print(f"  Neurons: {n_kept_neurons}/{n_total_neurons} with firing rate >= {min_firing_rate} Hz")

        n_trials_total = int(bp['Ntrials'][0, 0])
        if max_trials is not None:
            n_trials_total = min(n_trials_total, max_trials)

        print(f"  Processing {n_trials_total} trials...")

        for trial_idx in range(n_trials_total):
            # Get trial info
            trial_info = get_trial_info(bp, trial_idx)
            events = get_event_times(bp_ev, trial_idx)

            # Check if we should include this trial
            include = False
            for trial_type in config['include_trial_types']:
                if trial_info[f'is_{trial_type}']:
                    include = True
                    break

            if not include:
                continue

            # Get alignment time
            align_time = events[config['align_event']]

            # Create time bins relative to alignment
            trial_time_bins = time_bins + align_time

            # Extract neural data (with firing rate filter)
            try:
                neural_matrix = extract_neural_data(f, obj, trial_idx, trial_time_bins, neuron_mask)

                # Extract kinematic data
                kinematic_matrix, feat_names = extract_kinematic_data(
                    f, obj, trial_idx, trial_time_bins
                )

                # Create input matrix
                input_matrix = create_input_matrix(
                    events, align_time, trial_time_bins, kinematic_matrix
                )

                # Create output matrix
                output_matrix = create_output_matrix(trial_info, n_timebins)

                # Store trial data
                neural_trials.append(neural_matrix)
                input_trials.append(input_matrix)
                output_trials.append(output_matrix)
                trial_metadata.append({
                    'trial_idx': trial_idx,
                    'trial_info': trial_info,
                    'events': events,
                })

            except Exception as e:
                print(f"  Warning: Skipping trial {trial_idx} due to error: {e}")
                continue

        print(f"  Successfully processed {len(neural_trials)} trials")

    session_data = {
        'neural': neural_trials,
        'input': input_trials,
        'output': output_trials,
        'metadata': {
            'trial_metadata': trial_metadata,
            'feature_names': feat_names,
            'time_bins': bin_centers,
            'config': config,
            'source_file': os.path.basename(file_path),
        }
    }

    return session_data

def load_data(filepath):
    """
    Main data loading function to be imported by train_decoder.py

    Parameters:
    -----------
    filepath : str
        Path to the pickled data file

    Returns:
    --------
    data : dict with keys 'neural', 'input', 'output', 'metadata'
    """
    print(f"Loading data from: {filepath}")
    with open(filepath, 'rb') as f:
        data = pickle.load(f)

    return data

# =============================================================================
# Main Execution
# =============================================================================

def convert_session_worker(args):
    """
    Worker function for parallel processing

    Parameters:
    -----------
    args : tuple
        (session_info_dict, config_dict)

    Returns:
    --------
    tuple : (session_info, session_data or None, error_msg or None)
    """
    info, config = args

    try:
        session_data = convert_session(info['file_path'], config, max_trials=None)
        return (info, session_data, None)
    except Exception as e:
        return (info, None, str(e))


if __name__ == '__main__':
    import glob
    import sys
    import multiprocessing as mp
    import time

    # Get all data files
    data_dir = CONFIG['data_dir']
    data_files = sorted(glob.glob(os.path.join(data_dir, 'data_structure_*.mat')))

    print(f"Found {len(data_files)} data files")

    # Check if user wants sample or full conversion
    convert_full = '--full' in sys.argv

    if not convert_full:
        # Convert sample (first file, limited trials)
        print("\n" + "="*80)
        print("Converting SAMPLE data (first file, max 150 trials)...")
        print("="*80)
        print("(Use --full flag to convert entire dataset)")
        print("="*80)

        sample_session = convert_session(data_files[0], CONFIG, max_trials=150)

        # Organize as [subject][trial] format
        data_sample = {
            'neural': [sample_session['neural']],  # One subject
            'input': [sample_session['input']],
            'output': [sample_session['output']],
            'metadata': {
                'task_description': 'Two-context task (DR and WC) with directional licking',
                'brain_regions': 'ALM (anterior lateral motor cortex)',
                'n_subjects': 1,
                'bin_size_ms': CONFIG['bin_size_ms'],
                'time_window': CONFIG['time_window'],
                'align_event': CONFIG['align_event'],
                'sessions': [sample_session['metadata']],
            }
        }

        # Save sample data
        with open(CONFIG['output_file_sample'], 'wb') as f:
            pickle.dump(data_sample, f)
        print(f"\nSaved sample data to: {CONFIG['output_file_sample']}")

        # Print summary
        print("\n" + "="*80)
        print("SAMPLE DATA SUMMARY:")
        print("="*80)
        print(f"Number of subjects: {len(data_sample['neural'])}")
        print(f"Number of trials (subject 1): {len(data_sample['neural'][0])}")
        if len(data_sample['neural'][0]) > 0:
            print(f"Neural data shape (trial 1): {data_sample['neural'][0][0].shape}")
            print(f"Input data shape (trial 1): {data_sample['input'][0][0].shape}")
            print(f"Output data shape (trial 1): {data_sample['output'][0][0].shape}")

        print("\nSample conversion complete!")

    else:
        # Convert FULL dataset - EACH SESSION AS SEPARATE SUBJECT
        print("\n" + "="*80)
        print("Converting FULL dataset (all files, all trials)...")
        print("Each session will be treated as a separate subject")
        print("="*80)

        # Extract subject IDs and dates from filenames for metadata
        # Filename format: data_structure_SUBJECTID_DATE.mat
        session_info = []
        for file_path in data_files:
            filename = os.path.basename(file_path)
            parts = filename.split('_')
            if len(parts) >= 4:
                subject_id = parts[2]  # e.g., "EKH1"
                date = parts[3].replace('.mat', '')  # e.g., "2021-08-07"
                session_info.append({
                    'file_path': file_path,
                    'subject_id': subject_id,
                    'date': date,
                    'session_name': f"{subject_id}_{date}"
                })

        print(f"\nFound {len(session_info)} sessions (each will be one 'subject'):")

        # Group by biological subject for display
        bio_subjects = {}
        for info in session_info:
            sid = info['subject_id']
            if sid not in bio_subjects:
                bio_subjects[sid] = []
            bio_subjects[sid].append(info['session_name'])

        for subject_id, sessions in sorted(bio_subjects.items()):
            print(f"  {subject_id}: {len(sessions)} session(s)")

        # Convert all sessions in parallel - each as a separate subject
        print(f"\n{'='*80}")
        print("PARALLEL PROCESSING")
        print('='*80)

        # Determine number of processes
        n_cpus = mp.cpu_count()
        n_processes = min(n_cpus - 1, len(session_info))  # Leave 1 CPU free
        n_processes = max(1, n_processes)  # At least 1

        print(f"Using {n_processes} parallel processes (CPUs available: {n_cpus})")
        print(f"Processing {len(session_info)} sessions...")
        print('='*80)

        # Prepare arguments for worker function
        worker_args = [(info, CONFIG) for info in session_info]

        # Process sessions in parallel
        all_subjects_neural = []
        all_subjects_input = []
        all_subjects_output = []
        all_metadata = []

        start_time = time.time()

        with mp.Pool(processes=n_processes) as pool:
            # Use imap to get progress updates
            results = []
            for sess_idx, result in enumerate(pool.imap(convert_session_worker, worker_args)):
                info, session_data, error = result

                if error is None:
                    # Success
                    all_subjects_neural.append(session_data['neural'])
                    all_subjects_input.append(session_data['input'])
                    all_subjects_output.append(session_data['output'])
                    all_metadata.append({
                        'session_name': info['session_name'],
                        'biological_subject_id': info['subject_id'],
                        'date': info['date'],
                        'n_trials': len(session_data['neural']),
                        'session_metadata': session_data['metadata'],
                    })
                    print(f"[{sess_idx+1}/{len(session_info)}] ✓ {info['session_name']}: {len(session_data['neural'])} trials")

                else:
                    # Error
                    all_subjects_neural.append([])
                    all_subjects_input.append([])
                    all_subjects_output.append([])
                    all_metadata.append({
                        'session_name': info['session_name'],
                        'biological_subject_id': info['subject_id'],
                        'date': info['date'],
                        'n_trials': 0,
                        'error': error,
                    })
                    print(f"[{sess_idx+1}/{len(session_info)}] ✗ {info['session_name']}: ERROR - {error}")

                results.append(result)

        elapsed_time = time.time() - start_time

        print(f"\n{'='*80}")
        print(f"Parallel processing complete!")
        print(f"Time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        print(f"Average: {elapsed_time/len(session_info):.1f} seconds per session")
        print('='*80)

        # Filter out empty subjects (sessions that failed completely)
        print(f"\nFiltering out empty subjects...")
        filtered_neural = []
        filtered_input = []
        filtered_output = []
        filtered_metadata = []

        for i, (neural, inp, out, meta) in enumerate(zip(
            all_subjects_neural, all_subjects_input, all_subjects_output, all_metadata
        )):
            if len(neural) > 0:  # Only include subjects with trials
                filtered_neural.append(neural)
                filtered_input.append(inp)
                filtered_output.append(out)
                filtered_metadata.append(meta)
            else:
                print(f"  Excluded {meta['session_name']} (0 trials)")

        print(f"Kept {len(filtered_neural)} of {len(all_subjects_neural)} subjects")

        # Organize final data structure
        data_full = {
            'neural': filtered_neural,
            'input': filtered_input,
            'output': filtered_output,
            'metadata': {
                'task_description': 'Two-context task (DR and WC) with directional licking',
                'brain_regions': 'ALM (anterior lateral motor cortex)',
                'n_subjects': len(filtered_neural),
                'bin_size_ms': CONFIG['bin_size_ms'],
                'time_window': CONFIG['time_window'],
                'align_event': CONFIG['align_event'],
                'subjects': filtered_metadata,
            }
        }

        # Save full data
        with open(CONFIG['output_file_full'], 'wb') as f:
            pickle.dump(data_full, f)
        print(f"\n{'='*80}")
        print(f"Saved full data to: {CONFIG['output_file_full']}")

        # Print summary
        print("\n" + "="*80)
        print("FULL DATA SUMMARY:")
        print("="*80)
        print(f"Number of subjects (sessions): {len(data_full['neural'])}")
        print(f"Number of biological subjects: {len(bio_subjects)}")

        # Group by biological subject for summary
        for bio_subj, session_names in sorted(bio_subjects.items()):
            print(f"\n  {bio_subj}: {len(session_names)} session(s)")
            for sess_name in session_names:
                # Find this session in metadata
                sess_meta = [m for m in filtered_metadata if m['session_name'] == sess_name]
                if sess_meta:
                    n_trials = sess_meta[0]['n_trials']
                    print(f"    {sess_name}: {n_trials} trials")
                else:
                    print(f"    {sess_name}: 0 trials (excluded)")

        total_trials = sum(len(trials) for trials in data_full['neural'])
        print(f"\nTotal trials across all sessions: {total_trials}")

        if len(data_full['neural']) > 0 and len(data_full['neural'][0]) > 0:
            print(f"\nExample trial shapes (first session):")
            print(f"  Neural: {data_full['neural'][0][0].shape}")
            print(f"  Input: {data_full['input'][0][0].shape}")
            print(f"  Output: {data_full['output'][0][0].shape}")

        print("\nFull conversion complete!")
