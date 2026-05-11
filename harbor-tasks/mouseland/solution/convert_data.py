#!/usr/bin/env python3
"""
Convert Mouseland (Zhong et al. 2025) data to decoder-compatible format.

Usage:
    python -u convert_data.py <output_pickle_file> [--sample] [--full] [--show-processing]

Based on methods from: "Unsupervised pretraining in biological neural networks"
Reference code: code/utils.py, code/data_process_script.ipynb
"""

import argparse
import os
import sys
import time
import pickle
import numpy as np
from scipy import interpolate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

###############################################################################
# Utility functions adapted from reference code (code/utils.py)
###############################################################################

def load_spk(db, root=''):
    """Load neural data, concatenating across planes as in utils.py load_spk()"""
    fn = '%s_%s_%s_neural_data.npy' % (db['mname'], db['datexp'], db['blk'])
    spk_path = os.path.join(root, fn)
    spk = np.concatenate([nspk for nspk in np.load(spk_path, allow_pickle=True).item()['spks']], 0)
    return spk


def load_retino(db, root=''):
    """Load retinotopy/brain area data as in utils.py load_retino()"""
    fn = '%s_%s_trans.npz' % (db['mname'], db['datexp'])
    ret_path = os.path.join(root, fn)
    dtrans = np.load(ret_path, allow_pickle=True)
    return dtrans


def neu_area_ID(iarea):
    """Map iarea values to brain region indices as in utils.py neu_area_ID()

    Returns indices into brain_regions list: ['V1', 'mHV', 'lHV', 'aHV', 'Other']
    """
    # Brain regions: V1, mHV, lHV, aHV, Other
    # iarea codes from reference code:
    # V1: 8
    # mHV: 0, 1, 2, 9
    # lHV: 5, 6
    # aHV: 3, 4
    # Outside visual cortex: -1, 7 -> mapped to 'Other' (index 4)

    idx = np.full(len(iarea), 4, dtype=int)  # Default to 'Other' (index 4)

    # V1
    idx[iarea == 8] = 0
    # mHV (medial higher visual)
    idx[(iarea == 0) | (iarea == 1) | (iarea == 2) | (iarea == 9)] = 1
    # lHV (lateral higher visual)
    idx[(iarea == 5) | (iarea == 6)] = 2
    # aHV (anterior higher visual)
    idx[(iarea == 3) | (iarea == 4)] = 3
    # Outside visual cortex (iarea == -1 or iarea == 7) stays as 4 ('Other')

    return idx


def interp_value(v, vind, tind):
    """Interpolate values as in utils.py interp_value()"""
    Model_ = interpolate.interp1d(vind, v, fill_value='extrapolate')
    return Model_(tind)


def spk_pos_interp(raw_spk, accum_pos, corridorLen, new_shape):
    """Interpolate spike activity by position as in utils.py spk_pos_interp()

    Args:
        raw_spk: neurons x frames
        accum_pos: accumulated position, should be increasing
        corridorLen: length of corridor
        new_shape: [ntrials, bins_per_corridor] if [1]==0 then bins=corridorLen
    """
    if len(new_shape) == 2:
        if new_shape[1] == 0:
            new_shape[1] = int(corridorLen)
    linPos = np.arange(0, new_shape[0], 1/new_shape[1])
    spk_resh = []
    for s in range(raw_spk.shape[0]):  # loop through neurons
        spk_resh.append(np.reshape(
            interp_value(raw_spk[s, :], accum_pos/corridorLen, linPos),
            (int(new_shape[0]), int(new_shape[1]))
        ))
    return np.array(spk_resh)


def get_interpPos_spk(spk, spk_culm_pos, ntrial, n_bins=60, lengths=60):
    """Get position-interpolated neural activity as in utils.py get_interpPos_spk()"""
    interp_spk = np.zeros((spk.shape[0], ntrial, n_bins))
    step_size = 10000  # Process in chunks for memory efficiency
    i = 0
    while i < spk.shape[0]:
        end_idx = min(i + step_size, spk.shape[0])
        interp_spk[i:end_idx, :] = spk_pos_interp(
            raw_spk=spk[i:end_idx, :],
            accum_pos=spk_culm_pos,
            corridorLen=lengths,
            new_shape=[ntrial, n_bins]
        )
        i = end_idx
    return interp_spk


###############################################################################
# Data conversion functions
###############################################################################

def find_session_behavior(session_key, data_dir):
    """Find which behavior file contains this session and return the behavior data."""
    beh_dir = os.path.join(data_dir, 'beh')
    beh_files = [f for f in os.listdir(beh_dir) if f.startswith('Beh_') and f.endswith('.npy')]

    for beh_file in beh_files:
        beh_path = os.path.join(beh_dir, beh_file)
        beh_data = np.load(beh_path, allow_pickle=True).item()
        if session_key in beh_data:
            return beh_data[session_key], beh_file.replace('Beh_', '').replace('.npy', '')

    return None, None


def get_all_sessions(data_dir, prioritize_supervised=True, supervised_only=False):
    """Get all unique sessions from neural data files.

    If prioritize_supervised=True, return supervised sessions first (they have lick data).
    If supervised_only=True, return only supervised sessions.
    """
    spk_dir = os.path.join(data_dir, 'spk')
    spk_files = [f for f in os.listdir(spk_dir) if f.endswith('_neural_data.npy')]

    sessions = []
    for f in spk_files:
        # Parse filename: <mouse>_<date>_<blk>_neural_data.npy
        parts = f.replace('_neural_data.npy', '').split('_')
        mname = parts[0]
        datexp = '_'.join(parts[1:4])  # YYYY_MM_DD
        blk = parts[4]
        session_key = f"{mname}_{datexp}_{blk}"
        sessions.append({
            'mname': mname,
            'datexp': datexp,
            'blk': blk,
            'session_key': session_key
        })

    if prioritize_supervised or supervised_only:
        # Check which sessions are in supervised behavior files (have lick data)
        beh_dir = os.path.join(data_dir, 'beh')
        sup_sessions = set()

        for beh_file in os.listdir(beh_dir):
            if beh_file.startswith('Beh_sup') and beh_file.endswith('.npy'):
                beh_data = np.load(os.path.join(beh_dir, beh_file), allow_pickle=True).item()
                sup_sessions.update(beh_data.keys())

        # Sort: supervised sessions first
        sessions_sup = [s for s in sessions if s['session_key'] in sup_sessions]
        sessions_other = [s for s in sessions if s['session_key'] not in sup_sessions]

        print(f"  Found {len(sessions_sup)} supervised sessions (have lick data)")
        print(f"  Found {len(sessions_other)} other sessions")

        if supervised_only:
            sessions = sessions_sup
        else:
            sessions = sessions_sup + sessions_other

    return sessions


def create_lick_timeseries(beh, ntrials, n_bins=60):
    """Create binary licking time series for each trial.

    Returns:
        lick_ts: (ntrials, n_bins) binary array, 1 if lick in that position bin
    """
    lick_ts = np.zeros((ntrials, n_bins), dtype=int)

    lick_pos = beh['LickPos']
    lick_triind = beh['LickTrind'].astype(int)

    for i in range(len(lick_pos)):
        tr = lick_triind[i]
        pos = lick_pos[i]
        if tr < ntrials and 0 <= pos < n_bins:
            pos_bin = int(pos)
            lick_ts[tr, pos_bin] = 1

    return lick_ts


def create_speed_timeseries(beh, ntrials, n_bins=60, speed_quartiles=None):
    """Create discretized running speed time series.

    The reference code uses ft_move for frame-to-frame movement.
    We'll interpolate this to position bins and discretize into 4 quartiles.

    Returns:
        speed_ts: (ntrials, n_bins) array with values 0-3 for quartile bins
        speed_quartiles: computed quartile thresholds if not provided
    """
    n_frames = len(beh['ft_move'])
    ft_move = beh['ft_move'][:n_frames]
    ft_pos_cum = beh['ft_PosCum'][:n_frames]
    ft_trind = beh['ft_trInd'][:n_frames]
    corridor_len = beh['Corridor_Length']

    # Collect all valid (moving) speed values to compute quartiles
    if speed_quartiles is None:
        valid_speeds = ft_move[ft_move > 0]
        if len(valid_speeds) > 0:
            speed_quartiles = np.percentile(valid_speeds, [25, 50, 75])
        else:
            speed_quartiles = np.array([0.1, 0.2, 0.3])

    speed_ts = np.zeros((ntrials, n_bins), dtype=int)

    # For each trial, interpolate speed to position bins
    for tr in range(ntrials):
        tr_mask = ft_trind == tr
        if tr_mask.sum() < 2:
            continue

        tr_pos = ft_pos_cum[tr_mask]
        tr_speed = ft_move[tr_mask]

        # Normalize position within trial (0 to corridor_len)
        tr_pos_normalized = tr_pos - tr_pos[0]

        # Only use moving frames for interpolation
        valid_mask = tr_speed > 0
        if valid_mask.sum() < 2:
            continue

        # Interpolate to position bins
        pos_bins = np.arange(n_bins) + 0.5  # Center of each bin
        try:
            interp_speed = np.interp(pos_bins, tr_pos_normalized[valid_mask], tr_speed[valid_mask])
        except:
            continue

        # Discretize into quartiles (0-3)
        speed_ts[tr] = np.digitize(interp_speed, speed_quartiles)

    return speed_ts, speed_quartiles


def create_position_timeseries(n_bins=60, n_position_bins=4):
    """Create discretized position time series.

    Position bins are 4 equal-length bins covering the full corridor (0-60 dm).
    Each bin is 15 dm = 1.5 m.

    Returns:
        pos_ts: (n_bins,) array with values 0-3 for position bins
    """
    bin_width = n_bins / n_position_bins  # 15 dm per bin
    pos_ts = np.floor(np.arange(n_bins) / bin_width).astype(int)
    pos_ts = np.clip(pos_ts, 0, n_position_bins - 1)
    return pos_ts


def create_time_to_sound(beh, ntrials, n_bins=60):
    """Create time-to-sound-cue input variable.

    This is the distance from current position to sound cue position.
    Negative before cue, positive after cue.

    Returns:
        time_to_sound: (ntrials, n_bins) array
    """
    time_to_sound = np.zeros((ntrials, n_bins))
    sound_pos = beh['SoundPos']  # Sound position for each trial

    pos_bins = np.arange(n_bins)  # Position 0-59

    for tr in range(ntrials):
        # Distance from current position to sound position
        # Positive = haven't reached sound yet, Negative = passed sound
        time_to_sound[tr] = sound_pos[tr] - pos_bins

    return time_to_sound


def create_time_since_start(n_bins=60):
    """Create time-since-trial-start input variable.

    This is simply the position bin index (0-59), which represents
    time since entering the corridor (at constant VR speed).

    Returns:
        time_since_start: (n_bins,) array
    """
    return np.arange(n_bins, dtype=float)


def convert_session(session_info, data_dir, show_processing=False):
    """Convert a single session to the target format.

    Returns:
        dict with keys: neural, input, output, session_key, subject, brain_region_idx, n_neurons
    """
    session_key = session_info['session_key']

    # Load behavior data
    beh, exp_type = find_session_behavior(session_key, data_dir)
    if beh is None:
        print(f"  WARNING: No behavior found for {session_key}")
        return None

    ntrials = beh['ntrials']
    corridor_len = beh['Corridor_Length']
    n_bins = int(corridor_len)  # 60 bins

    # Load neural data
    db = {'mname': session_info['mname'], 'datexp': session_info['datexp'], 'blk': session_info['blk']}
    spk = load_spk(db, root=os.path.join(data_dir, 'spk'))
    n_neurons, n_frames = spk.shape

    print(f"  Session {session_key}: {n_neurons} neurons, {n_frames} frames, {ntrials} trials")

    # Load brain region data
    try:
        ret = load_retino(db, root=os.path.join(data_dir, 'retinotopy'))
        iarea = ret['iarea']
        brain_region_idx = neu_area_ID(iarea)
    except:
        print(f"  WARNING: No retinotopy data for {session_key}, using default")
        brain_region_idx = np.zeros(n_neurons, dtype=int)

    # Get frame-aligned behavior data
    ft_pos_cum = beh['ft_PosCum'][:n_frames]
    ft_move = beh['ft_move'][:n_frames]

    # Only use moving frames for interpolation (as in reference code)
    VRmove = ft_move > 0

    if VRmove.sum() < 100:
        print(f"  WARNING: Too few moving frames ({VRmove.sum()}) for {session_key}")
        return None

    # Interpolate neural activity to position bins
    t0 = time.time()
    interp_spk = get_interpPos_spk(spk[:, VRmove], ft_pos_cum[VRmove], ntrials,
                                    n_bins=n_bins, lengths=corridor_len)
    t1 = time.time()
    print(f"    Interpolation: {t1-t0:.1f}s")

    # Create output variables

    # 1. Visual stimulus category (per-trial)
    wall_names = beh['WallName']
    unique_walls = list(beh['UniqWalls'])
    stimulus_idx = np.array([unique_walls.index(w) for w in wall_names])

    # 2. Licking (time-varying binary)
    lick_ts = create_lick_timeseries(beh, ntrials, n_bins)

    # 3. Position (time-varying, 4 bins)
    position_ts = create_position_timeseries(n_bins, n_position_bins=4)

    # 4. Running speed (time-varying, 4 bins)
    speed_ts, speed_quartiles = create_speed_timeseries(beh, ntrials, n_bins)

    # Create input variables

    # 1. Time to sound cue
    time_to_sound = create_time_to_sound(beh, ntrials, n_bins)

    # 2. Day of training (use 0 since test sessions don't have meaningful training day)
    day_of_training = np.zeros(ntrials)

    # 3. Time since trial start
    time_since_start = create_time_since_start(n_bins)

    # 4. Reward availability (per-trial binary)
    reward_avail = beh['isRew'].astype(int)

    # Organize data by trial
    neural_trials = []
    input_trials = []
    output_trials = []

    for tr in range(ntrials):
        # Neural: (n_neurons, n_bins) - use float32 to reduce file size
        neural_trials.append(interp_spk[:, tr, :].astype(np.float32))

        # Input: (4, n_bins) - time_to_sound, day_of_training, time_since_start, reward_avail
        # Expand per-trial values to time-varying
        inp = np.zeros((4, n_bins), dtype=np.float32)
        inp[0, :] = time_to_sound[tr]
        inp[1, :] = day_of_training[tr]
        inp[2, :] = time_since_start
        inp[3, :] = reward_avail[tr]
        input_trials.append(inp)

        # Output: (4, n_bins) - stimulus, licking, position, speed
        # Stimulus is per-trial but we expand to time dimension
        out = np.zeros((4, n_bins), dtype=np.int32)
        out[0, :] = stimulus_idx[tr]
        out[1, :] = lick_ts[tr]
        out[2, :] = position_ts
        out[3, :] = speed_ts[tr]
        output_trials.append(out)

    # Visualization for --show-processing mode
    if show_processing:
        fig, axes = plt.subplots(4, 3, figsize=(15, 12))
        fig.suptitle(f'Session: {session_key}', fontsize=14)

        # Plot neural activity (mean across neurons for a few trials)
        ax = axes[0, 0]
        for tr in [0, 10, 20]:
            if tr < ntrials:
                ax.plot(neural_trials[tr].mean(axis=0), alpha=0.7, label=f'Trial {tr}')
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Mean neural activity')
        ax.set_title('Neural activity (mean across neurons)')
        ax.legend()

        # Plot time to sound
        ax = axes[0, 1]
        for tr in [0, 10, 20]:
            if tr < ntrials:
                ax.plot(input_trials[tr][0], alpha=0.7, label=f'Trial {tr}')
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Distance to sound (dm)')
        ax.set_title('Time to sound cue')
        ax.legend()

        # Plot reward availability
        ax = axes[0, 2]
        ax.bar(range(min(50, ntrials)), reward_avail[:min(50, ntrials)])
        ax.set_xlabel('Trial')
        ax.set_ylabel('Reward available')
        ax.set_title('Reward availability (first 50 trials)')

        # Plot stimulus distribution
        ax = axes[1, 0]
        stim_counts = np.bincount(stimulus_idx, minlength=len(unique_walls))
        ax.bar(range(len(unique_walls)), stim_counts)
        ax.set_xticks(range(len(unique_walls)))
        ax.set_xticklabels(unique_walls, rotation=45)
        ax.set_ylabel('Count')
        ax.set_title('Stimulus distribution')

        # Plot licking
        ax = axes[1, 1]
        lick_sum = lick_ts.sum(axis=0)
        ax.bar(range(n_bins), lick_sum)
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Lick count')
        ax.set_title('Licking across position (all trials)')

        # Plot position binning
        ax = axes[1, 2]
        ax.plot(position_ts, 'o-')
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Position category (0-3)')
        ax.set_title('Position discretization')

        # Plot speed distribution
        ax = axes[2, 0]
        speed_flat = speed_ts.flatten()
        ax.hist(speed_flat, bins=4, range=(-0.5, 3.5), edgecolor='black')
        ax.set_xlabel('Speed category')
        ax.set_ylabel('Count')
        ax.set_title('Speed distribution')

        # Plot speed vs position
        ax = axes[2, 1]
        mean_speed = speed_ts.mean(axis=0)
        ax.plot(mean_speed, 'o-')
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Mean speed category')
        ax.set_title('Speed vs position')

        # Plot brain region distribution
        ax = axes[2, 2]
        region_names = ['V1', 'mHV', 'lHV', 'aHV', 'Other']
        region_counts = np.zeros(5)
        for i in range(4):
            region_counts[i] = np.sum(brain_region_idx == i)
        region_counts[4] = np.sum(brain_region_idx == -1)
        ax.bar(range(5), region_counts)
        ax.set_xticks(range(5))
        ax.set_xticklabels(region_names)
        ax.set_ylabel('Neuron count')
        ax.set_title('Brain region distribution')

        # Plot neural activity heatmap
        ax = axes[3, 0]
        # Average across trials for each neuron
        mean_activity = np.mean(interp_spk, axis=1)  # (n_neurons, n_bins)
        # Show first 100 neurons
        im = ax.imshow(mean_activity[:min(100, n_neurons)], aspect='auto', cmap='viridis')
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Neuron')
        ax.set_title('Neural activity (first 100 neurons)')
        plt.colorbar(im, ax=ax)

        # Plot lick raster
        ax = axes[3, 1]
        for tr in range(min(50, ntrials)):
            lick_positions = np.where(lick_ts[tr] > 0)[0]
            ax.scatter(lick_positions, np.full_like(lick_positions, tr), s=1, c='black')
        ax.set_xlabel('Position bin')
        ax.set_ylabel('Trial')
        ax.set_title('Lick raster (first 50 trials)')

        # Leave last subplot empty or add additional info
        ax = axes[3, 2]
        info_text = f"""
Session: {session_key}
Experiment type: {exp_type}
Neurons: {n_neurons}
Trials: {ntrials}
Frames: {n_frames}
Moving frames: {VRmove.sum()}
Corridor length: {corridor_len} dm
Stimuli: {unique_walls}
Reward trials: {reward_avail.sum()} ({100*reward_avail.sum()/ntrials:.1f}%)
"""
        ax.text(0.1, 0.5, info_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='center', family='monospace')
        ax.axis('off')
        ax.set_title('Session info')

        plt.tight_layout()
        plt.savefig(f'processing_{session_key}.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    Saved processing_{session_key}.png")

    return {
        'neural': neural_trials,
        'input': input_trials,
        'output': output_trials,
        'session_key': session_key,
        'subject': session_info['mname'],
        'brain_region_idx': brain_region_idx,
        'n_neurons': n_neurons,
        'stimulus_names': unique_walls,
    }


def convert_data(output_file, sample=False, show_processing=False, supervised_only=False):
    """Main conversion function."""

    print("=" * 60)
    print("Mouseland Data Conversion")
    print("=" * 60)

    t_start = time.time()

    # Get all sessions
    sessions = get_all_sessions(DATA_DIR, supervised_only=supervised_only)
    print(f"\nFound {len(sessions)} sessions")

    if sample:
        # Just process first 2 sessions for testing
        sessions = sessions[:2]
        print(f"Sample mode: processing {len(sessions)} sessions")

    # Process each session
    all_neural = []
    all_input = []
    all_output = []
    all_subject_idx = []
    all_brain_region_idx = []

    subjects = []
    subject_to_idx = {}

    all_stimulus_names = set()

    speed_quartiles = None  # Will be computed from first session and reused

    for i, session_info in enumerate(sessions):
        print(f"\nProcessing session {i+1}/{len(sessions)}: {session_info['session_key']}")
        t0 = time.time()

        result = convert_session(session_info, DATA_DIR,
                                 show_processing=show_processing and i < 2)

        if result is None:
            print(f"  Skipping session {session_info['session_key']}")
            continue

        # Track subjects
        subject = result['subject']
        if subject not in subject_to_idx:
            subject_to_idx[subject] = len(subjects)
            subjects.append(subject)

        subject_idx = subject_to_idx[subject]

        # Store data
        all_neural.append(result['neural'])
        all_input.append(result['input'])
        all_output.append(result['output'])
        all_subject_idx.append(subject_idx)
        all_brain_region_idx.append(result['brain_region_idx'])
        all_stimulus_names.update(result['stimulus_names'])

        t1 = time.time()
        print(f"  Session completed in {t1-t0:.1f}s")

    print(f"\n{'='*60}")
    print(f"Conversion complete: {len(all_neural)} sessions")

    # Build stimulus mapping (consistent across all sessions)
    all_stimulus_names = sorted(list(all_stimulus_names))

    # Build output data structure
    data = {
        'neural': all_neural,
        'input': all_input,
        'output': all_output,

        'subjects': subjects,
        'subject_idx': np.array(all_subject_idx),

        'brain_regions': ['V1', 'mHV', 'lHV', 'aHV', 'Other'],
        'brain_region_idx': all_brain_region_idx,

        'input_names': ['time_to_sound', 'day_of_training', 'time_since_start', 'reward_availability'],

        'output_names': ['visual_stimulus', 'licking', 'position', 'running_speed'],
        'output_values': [
            all_stimulus_names,  # visual_stimulus categories
            ['no_lick', 'lick'],  # licking: binary
            ['0-1.5m', '1.5-3m', '3-4.5m', '4.5-6m'],  # position: 4 bins
            ['Q1', 'Q2', 'Q3', 'Q4'],  # running_speed: 4 quartiles
        ],

        'metadata': {
            'time_bin_size': 100.0,  # ms (approximately, based on VR speed of 60 cm/s)
            'temporal_alignment_event': 'corridor_entry',
            'off_start': 0.0,  # Trial starts at corridor entry
            'off_end': None,  # Variable trial duration
            'task_description': 'Visual discrimination task in head-fixed mice running through VR corridors',
            'dataset_source': 'Zhong et al. 2025 - Unsupervised pretraining in biological neural networks',
            'frame_rate_hz': 3.17,
            'corridor_length_m': 6.0,
            'texture_length_m': 4.0,
            'gray_space_length_m': 2.0,
            'vr_speed_cm_s': 60.0,
        }
    }

    # Save to pickle
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"Saved: {output_file} ({file_size:.1f} MB)")

    # Print summary statistics
    print(f"\n{'='*60}")
    print("Summary Statistics")
    print('=' * 60)

    total_neurons = sum([br.shape[0] for br in all_brain_region_idx])
    total_trials = sum([len(n) for n in all_neural])

    print(f"Subjects: {len(subjects)}")
    print(f"Sessions: {len(all_neural)}")
    print(f"Total neurons: {total_neurons}")
    print(f"Total trials: {total_trials}")
    print(f"Mean trials/session: {total_trials/len(all_neural):.1f}")
    print(f"Mean neurons/session: {total_neurons/len(all_neural):.1f}")
    print(f"Stimuli: {all_stimulus_names}")

    # Output distribution statistics
    print(f"\nOutput distributions:")
    for out_idx, out_name in enumerate(data['output_names']):
        all_values = []
        for session_outputs in all_output:
            for trial_output in session_outputs:
                all_values.extend(trial_output[out_idx])
        all_values = np.array(all_values)
        unique, counts = np.unique(all_values, return_counts=True)
        print(f"  {out_name}:")
        for u, c in zip(unique, counts):
            val_name = data['output_values'][out_idx][int(u)] if int(u) < len(data['output_values'][out_idx]) else str(u)
            print(f"    {val_name}: {c} ({100*c/len(all_values):.1f}%)")

    t_end = time.time()
    print(f"\nTotal time: {t_end-t_start:.1f}s")

    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert Mouseland data to decoder format')
    parser.add_argument('output_file', help='Output pickle file path')
    parser.add_argument('--sample', action='store_true', help='Process only 2 sessions for testing')
    parser.add_argument('--full', action='store_true', help='Process all sessions (default)')
    parser.add_argument('--supervised-only', action='store_true',
                        help='Process only supervised sessions (have lick data)')
    parser.add_argument('--show-processing', action='store_true',
                        help='Generate visualization plots for processing steps')
    parser.add_argument('--datadir', type=str, default=None,
                        help='Path to data directory (default: data/ next to script)')

    args = parser.parse_args()

    if args.datadir is not None:
        DATA_DIR = args.datadir

    sample_mode = args.sample
    if args.full:
        sample_mode = False

    convert_data(args.output_file, sample=sample_mode, show_processing=args.show_processing,
                 supervised_only=args.supervised_only)
