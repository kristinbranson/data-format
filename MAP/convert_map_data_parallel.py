"""
Parallel MAP dataset converter using multiprocessing.

Key optimizations:
- Parallel processing of sessions (embarrassingly parallel)
- Pre-load spike times at session level
- Vectorized spike counting

Author: Claude Code
Date: 2025-12-02
"""

import numpy as np
import pickle
import glob
from pynwb import NWBHDF5IO
from pathlib import Path
import json
from collections import defaultdict
import time
from multiprocessing import Pool, cpu_count
import sys


class MAPConverterParallel:
    """Parallel MAP NWB data converter."""

    def __init__(self, time_window=(-2.5, 1.5), bin_size=0.05, align_to='go_cue'):
        self.time_window = time_window
        self.bin_size = bin_size
        self.align_to = align_to

        # Compute time bins and edges
        self.time_bins = np.arange(time_window[0], time_window[1], bin_size)
        self.n_time_bins = len(self.time_bins)

        # Pre-compute bin edges for vectorized binning
        self.bin_edges = np.arange(time_window[0], time_window[1] + bin_size, bin_size)

        print(f"Parallel Converter initialized:")
        print(f"  Alignment: {align_to}")
        print(f"  Time window: {time_window[0]:.2f}s to {time_window[1]:.2f}s")
        print(f"  Bin size: {bin_size*1000:.0f}ms")
        print(f"  Number of time bins: {self.n_time_bins}")

    def compute_firing_rates_vectorized(self, spike_times, align_time):
        """Vectorized firing rate computation using np.histogram."""
        spikes_rel = spike_times - align_time
        spike_counts, _ = np.histogram(spikes_rel, bins=self.bin_edges)
        firing_rates = spike_counts / self.bin_size
        return firing_rates

    def convert_session(self, nwb_path, max_trials=None):
        """Convert a single session."""

        session_start = time.time()

        io = NWBHDF5IO(nwb_path, 'r')
        nwbfile = io.read()

        try:
            n_trials = len(nwbfile.trials)
            n_units = len(nwbfile.units)

            if max_trials is not None:
                n_trials = min(n_trials, max_trials)

            # Pre-load all data at once
            go_times = nwbfile.acquisition['BehavioralEvents'].time_series['go_start_times'].timestamps[:]

            # Load all trial metadata at once
            trials = nwbfile.trials
            instructions = trials['trial_instruction'][:n_trials]
            outcomes = trials['outcome'][:n_trials]
            early_licks = trials['early_lick'][:n_trials]
            photostim_onsets = trials['photostim_onset'][:n_trials]

            # Pre-load ALL spike times for all units
            all_spike_times = []
            for unit_idx in range(n_units):
                all_spike_times.append(nwbfile.units['spike_times'][unit_idx])

            # Determine valid neural recording range
            # (earliest spike start to latest spike end across all units)
            spike_mins = [spikes.min() if len(spikes) > 0 else np.inf for spikes in all_spike_times]
            spike_maxs = [spikes.max() if len(spikes) > 0 else -np.inf for spikes in all_spike_times]
            neural_start = np.min(spike_mins)
            neural_end = np.max(spike_maxs)

            print(f"  Neural recording range: [{neural_start:.1f}s, {neural_end:.1f}s]")

            # Pre-load brain regions
            brain_regions = []
            for unit_idx in range(n_units):
                eg = nwbfile.units['electrode_group'][unit_idx]
                if hasattr(eg, 'location'):
                    try:
                        loc_dict = json.loads(eg.location)
                        region = loc_dict.get('brain_regions', 'unknown')
                    except:
                        region = 'unknown'
                else:
                    region = 'unknown'
                brain_regions.append(region)

            # Process trials
            trial_infos = []
            valid_trial_indices = []

            for trial_idx in range(n_trials):
                try:
                    # Check if trial's analysis window falls within neural recording range
                    align_time = go_times[trial_idx]
                    window_start = align_time + self.time_window[0]
                    window_end = align_time + self.time_window[1]

                    # Skip trials outside neural recording range
                    if window_start < neural_start or window_end > neural_end:
                        continue

                    instruction = instructions[trial_idx]
                    outcome = outcomes[trial_idx]
                    early_lick = early_licks[trial_idx]
                    photostim_onset = photostim_onsets[trial_idx]

                    if outcome == 'hit':
                        lick_direction = instruction
                    elif outcome == 'miss':
                        lick_direction = 'right' if instruction == 'left' else 'left'
                    else:
                        lick_direction = 'none'

                    trial_info = {
                        'instruction': instruction,
                        'outcome': outcome,
                        'early_lick': early_lick,
                        'photostim': 0 if photostim_onset == 'N/A' else 1,
                        'lick_direction': lick_direction,
                        'align_time': align_time,
                    }

                    trial_infos.append(trial_info)
                    valid_trial_indices.append(trial_idx)

                except Exception as e:
                    continue

            # Pre-allocate arrays for all trials
            neural_data = []
            input_data = []
            output_data = []

            # Process all trials
            for idx, trial_idx in enumerate(valid_trial_indices):
                trial_info = trial_infos[idx]
                align_time = trial_info['align_time']

                # Pre-allocate firing rate matrix for this trial
                trial_firing_rates = np.zeros((n_units, self.n_time_bins), dtype=np.float32)

                # Process all units (using pre-loaded spike times)
                for unit_idx in range(n_units):
                    spike_times = all_spike_times[unit_idx]
                    trial_firing_rates[unit_idx, :] = self.compute_firing_rates_vectorized(
                        spike_times, align_time
                    )

                # Prepare input variables
                time_input = self.time_bins.reshape(1, -1).astype(np.float32)
                photostim_input = np.full((1, self.n_time_bins), trial_info['photostim'], dtype=np.float32)
                trial_input = np.vstack([time_input, photostim_input])

                # Prepare output variables
                lick_mapping = {'left': 0, 'right': 1, 'none': 2}
                outcome_mapping = {'hit': 0, 'miss': 1, 'ignore': 2}
                early_lick_mapping = {'no early': 0, 'early': 1}

                trial_output = np.array([
                    lick_mapping[trial_info['lick_direction']],
                    outcome_mapping[trial_info['outcome']],
                    early_lick_mapping[trial_info['early_lick']]
                ], dtype=np.int64)

                neural_data.append(trial_firing_rates)
                input_data.append(trial_input)
                output_data.append(trial_output)

            session_data = {
                'neural': neural_data,
                'input': input_data,
                'output': output_data,
                'brain_regions': brain_regions,
                'subject_id': nwbfile.subject.subject_id if nwbfile.subject else 'unknown',
                'session_id': Path(nwb_path).stem,
                'n_trials': len(valid_trial_indices),
                'n_units': n_units,
            }

            session_time = time.time() - session_start

            return session_data, session_time

        finally:
            io.close()


def convert_session_wrapper(args):
    """Wrapper function for parallel processing."""
    nwb_path, max_trials, time_window, bin_size, align_to = args

    converter = MAPConverterParallel(
        time_window=time_window,
        bin_size=bin_size,
        align_to=align_to
    )

    session_data, session_time = converter.convert_session(nwb_path, max_trials=max_trials)

    # Return minimal info for progress tracking
    session_name = Path(nwb_path).name
    return {
        'session_data': session_data,
        'session_time': session_time,
        'session_name': session_name,
    }


def convert_dataset_parallel(data_dir, output_path, subjects=None, max_trials_per_session=None,
                            time_window=(-2.5, 1.5), bin_size=0.05, align_to='go_cue',
                            n_workers=None):
    """Convert entire MAP dataset using parallel processing."""

    total_start = time.time()

    print("="*80)
    print("PARALLEL MAP DATA CONVERSION")
    print("="*80)

    # Determine number of workers
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)  # Leave one CPU free

    print(f"\nUsing {n_workers} parallel workers")

    # Find all NWB files
    data_path = Path(data_dir)

    if subjects is None:
        nwb_files = sorted(glob.glob(str(data_path / 'sub-*' / '*.nwb')))
    else:
        nwb_files = []
        for subject in subjects:
            nwb_files.extend(sorted(glob.glob(str(data_path / subject / '*.nwb'))))

    print(f"Found {len(nwb_files)} NWB files")

    # Prepare arguments for parallel processing
    args_list = [(nwb_path, max_trials_per_session, time_window, bin_size, align_to)
                 for nwb_path in nwb_files]

    # Process sessions in parallel
    print(f"\nProcessing sessions in parallel...")

    results = []
    with Pool(processes=n_workers) as pool:
        for i, result in enumerate(pool.imap(convert_session_wrapper, args_list)):
            results.append(result)

            # Progress update
            elapsed = time.time() - total_start
            rate = (i + 1) / elapsed
            remaining = (len(nwb_files) - (i + 1)) / rate

            print(f"  Completed: {i+1}/{len(nwb_files)} sessions "
                  f"({100*(i+1)/len(nwb_files):.1f}%) | "
                  f"Last: {result['session_name']} ({result['session_time']:.1f}s) | "
                  f"Est. remaining: {remaining/60:.1f} min")

    # Organize results
    neural_all = []
    input_all = []
    output_all = []
    session_ids = []
    session_info = []

    for result in results:
        session_data = result['session_data']

        neural_all.append(session_data['neural'])
        input_all.append(session_data['input'])
        output_all.append(session_data['output'])

        # Extract subject and session IDs
        subject_id = Path(session_data['session_id']).stem.split('_ses-')[0]
        session_id_str = f"{subject_id}_{session_data['session_id'].split('_ses-')[1]}"
        session_ids.append(session_id_str)

        session_info.append({
            'subject_id': session_data['subject_id'],
            'session_id': session_data['session_id'],
            'n_trials': session_data['n_trials'],
            'n_units': session_data['n_units'],
            'brain_regions': session_data['brain_regions'],
        })

    # Create final data dictionary
    data = {
        'neural': neural_all,
        'input': input_all,
        'output': output_all,
        'metadata': {
            'task_description': 'Auditory delayed response task: Memory-guided movement',
            'brain_regions': 'ALM, Striatum, Thalamus, Midbrain, Medulla (bilateral)',
            'alignment': align_to,
            'time_window': time_window,
            'bin_size': bin_size,
            'n_time_bins': len(np.arange(time_window[0], time_window[1], bin_size)),
            'time_bins': np.arange(time_window[0], time_window[1], bin_size).tolist(),
            'sampling_rate': 1.0 / bin_size,
            'session_ids': session_ids,
            'session_info': session_info,
            'input_descriptions': [
                'Time from go cue (seconds)',
                'Photostimulation status (0=control, 1=ALM silencing)'
            ],
            'output_descriptions': [
                'Lick direction (0=left, 1=right, 2=none/ignore)',
                'Outcome (0=hit, 1=miss, 2=ignore)',
                'Early lick (0=no early, 1=early)'
            ],
        }
    }

    # Save to pickle
    print(f"\n{'='*80}")
    print(f"SAVING DATA")
    print(f"{'='*80}")
    print(f"Output: {output_path}")
    print(f"Sessions: {len(neural_all)}")

    total_trials = sum(len(s) for s in neural_all)
    print(f"Total trials: {total_trials}")

    with open(output_path, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    total_time = time.time() - total_start
    print(f"\nTotal conversion time: {total_time/60:.1f} minutes")
    print(f"Average: {total_time/len(neural_all):.1f}s per session")
    print(f"Conversion complete!")

    return data


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert MAP data (parallel)')
    parser.add_argument('--data-dir', type=str, default='data')
    parser.add_argument('--output', type=str, default='map_data_full.pkl')
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--subjects', nargs='+')
    parser.add_argument('--max-trials', type=int)
    parser.add_argument('--workers', type=int, help='Number of parallel workers (default: CPU count - 1)')

    args = parser.parse_args()

    if args.sample:
        subjects = ['sub-440956', 'sub-440957']
        max_trials = 20
        output = 'map_data_sample.pkl'
    else:
        subjects = args.subjects
        max_trials = args.max_trials
        output = args.output

    data = convert_dataset_parallel(
        data_dir=args.data_dir,
        output_path=output,
        subjects=subjects,
        max_trials_per_session=max_trials,
        time_window=(-2.5, 1.5),
        bin_size=0.05,
        align_to='go_cue',
        n_workers=args.workers
    )


if __name__ == '__main__':
    main()
