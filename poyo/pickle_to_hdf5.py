#!/usr/bin/env python3
"""
Convert pickle data to HDF5 format for torch_brain.

This script converts the standard pickle format to HDF5 files that can be
loaded by torch_brain's Dataset class.

Usage:
    python pickle_to_hdf5.py <input_pickle> <output_dir> [--brainset-id NAME]
"""

import argparse
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import h5py
import numpy as np
from temporaldata import Data, RegularTimeSeries, ArrayDict, Interval
from brainsets import serialize_fn_map
from brainsets.descriptions import (
    BrainsetDescription,
    SessionDescription,
    SubjectDescription,
)
from brainsets.taxonomy import Species


def create_data_object(
    neural_trials: List[np.ndarray],
    output_trials: List[np.ndarray],
    session_id: str,
    brainset_id: str,
    subject_id: str,
    time_bin_size_ms: float,
    output_names: List[str],
) -> Data:
    """
    Create a temporaldata.Data object from trial data.

    Concatenates all trials into a single continuous recording, but preserves
    trial boundaries in the domain as a multi-valued Interval.
    """
    if len(neural_trials) == 0:
        return None

    n_neurons = neural_trials[0].shape[0]
    time_bin_size_s = time_bin_size_ms / 1000.0
    sampling_rate = 1.0 / time_bin_size_s

    # Track trial boundaries as we concatenate
    trial_starts = []
    trial_ends = []
    current_time = 0.0

    for trial_neural in neural_trials:
        trial_T = trial_neural.shape[1]
        trial_duration = trial_T * time_bin_size_s
        trial_starts.append(current_time)
        trial_ends.append(current_time + trial_duration)
        current_time += trial_duration

    trial_starts = np.array(trial_starts, dtype=np.float64)
    trial_ends = np.array(trial_ends, dtype=np.float64)

    # Concatenate all trials
    neural_concat = np.concatenate(neural_trials, axis=1)  # (n_neurons, total_T)
    output_concat = np.concatenate(output_trials, axis=1)  # (n_outputs, total_T)

    total_T = neural_concat.shape[1]
    duration = total_T * time_bin_size_s

    # Create trial-based domain (multi-valued Interval for trial boundaries)
    # This allows TrialSampler to sample complete trials
    trial_domain = Interval(start=trial_starts, end=trial_ends)

    # Create continuous domain for the timeseries data
    continuous_domain = Interval(0, duration)

    # Create calcium traces as RegularTimeSeries (T, N) format
    df_over_f = neural_concat.T.astype(np.float32)  # (T, N)

    calcium_traces = RegularTimeSeries(
        sampling_rate=sampling_rate,
        domain=continuous_domain,
        df_over_f=df_over_f,
    )

    # Create unit IDs (local to session)
    unit_ids = np.array([f"unit{i:04d}" for i in range(n_neurons)])
    units = ArrayDict(id=unit_ids)

    # Create outputs as RegularTimeSeries
    output_kwargs = {}
    for i, name in enumerate(output_names):
        output_kwargs[name] = output_concat[i, :].astype(np.int64)

    outputs = RegularTimeSeries(
        sampling_rate=sampling_rate,
        domain=continuous_domain,
        **output_kwargs
    )

    # Build the Data object with brainsets description objects
    # (required by torch_brain's Dataset and CaPOYO.tokenize)
    # Use trial_domain as the session domain to enable trial-based sampling
    data_obj = Data(
        calcium_traces=calcium_traces,
        units=units,
        outputs=outputs,
        domain=trial_domain,  # Multi-valued: one interval per trial
        session=SessionDescription(
            id=session_id,
            recording_date=datetime.now(),  # placeholder
        ),
        brainset=BrainsetDescription(
            id=brainset_id,
            origin_version="1.0.0",
            derived_version="1.0.0",
            source="converted_from_pickle",
            description="Converted from pickle format",
        ),
        subject=SubjectDescription(
            id=subject_id,
            species=Species.MUS_MUSCULUS,  # mouse
        ),
    )

    return data_obj


def convert_pickle_to_hdf5(
    input_pickle: str,
    output_dir: str,
    brainset_id: str = "dataset",
):
    """
    Convert pickle data to HDF5 format for torch_brain.

    Creates directory structure: output_dir/brainset_id/session_id.h5
    """
    print(f"Loading pickle file: {input_pickle}")
    with open(input_pickle, 'rb') as f:
        data = pickle.load(f)

    output_names = data['output_names']
    time_bin_size_ms = data['metadata']['time_bin_size']
    subjects = data['subjects']
    subject_idx = data['subject_idx']

    n_sessions = len(data['neural'])
    print(f"Found {n_sessions} sessions")
    print(f"Output names: {output_names}")
    print(f"Time bin size: {time_bin_size_ms} ms")

    # Create output directory
    brainset_dir = Path(output_dir) / brainset_id
    brainset_dir.mkdir(parents=True, exist_ok=True)

    session_ids = []
    skipped = 0

    for session in range(n_sessions):
        neural_trials = data['neural'][session]
        output_trials = data['output'][session]

        if len(neural_trials) == 0:
            print(f"  Session {session}: No trials, skipping")
            skipped += 1
            continue

        # Get subject for this session
        subject_id = subjects[subject_idx[session]]
        session_id = f"session_{session:04d}"

        # Create Data object
        data_obj = create_data_object(
            neural_trials=neural_trials,
            output_trials=output_trials,
            session_id=session_id,
            brainset_id=brainset_id,
            subject_id=subject_id,
            time_bin_size_ms=time_bin_size_ms,
            output_names=output_names,
        )

        if data_obj is None:
            skipped += 1
            continue

        # Save to HDF5 with brainsets serialization
        hdf5_path = brainset_dir / f"{session_id}.h5"
        with h5py.File(hdf5_path, 'w') as f:
            data_obj.to_hdf5(f, serialize_fn_map=serialize_fn_map)

        session_ids.append(session_id)

        if (session + 1) % 20 == 0:
            print(f"  Converted {session + 1}/{n_sessions} sessions...")

    print(f"\nConversion complete!")
    print(f"  Sessions converted: {len(session_ids)}")
    print(f"  Sessions skipped: {skipped}")
    print(f"  Output directory: {brainset_dir}")

    # Save session list for config generation
    session_list_path = brainset_dir / "session_list.txt"
    with open(session_list_path, 'w') as f:
        for sid in session_ids:
            f.write(f"{sid}\n")
    print(f"  Session list saved to: {session_list_path}")

    return session_ids, output_names


def generate_yaml_config(
    output_dir: str,
    brainset_id: str,
    session_ids: List[str],
    output_names: List[str],
    output_values: List[List[str]],
):
    """Generate YAML config file for torch_brain Dataset."""

    config_path = Path(output_dir) / f"{brainset_id}_config.yaml"

    # Build multitask_readout config
    readout_configs = []
    for name, values in zip(output_names, output_values):
        n_classes = len(values)
        modality_name = f"output_{name}"
        readout_configs.append({
            'readout_id': modality_name,
            'timestamp_key': f'outputs.timestamps',
            'value_key': f'outputs.{name}',
            'num_classes': n_classes,
        })

    # Write YAML manually to control formatting
    with open(config_path, 'w') as f:
        f.write(f"# Dataset config for {brainset_id}\n")
        f.write(f"- selection:\n")
        f.write(f"  - brainset: {brainset_id}\n")
        f.write(f"    sessions:\n")
        for sid in session_ids:
            f.write(f"    - \"{sid}\"\n")
        f.write(f"  config:\n")
        f.write(f"    multitask_readout:\n")
        for rc in readout_configs:
            f.write(f"      - readout_id: {rc['readout_id']}\n")
            f.write(f"        timestamp_key: {rc['timestamp_key']}\n")
            f.write(f"        value_key: {rc['value_key']}\n")
            f.write(f"        metrics:\n")
            f.write(f"          - metric:\n")
            f.write(f"              _target_: torchmetrics.Accuracy\n")
            f.write(f"              task: multiclass\n")
            f.write(f"              num_classes: {rc['num_classes']}\n")

    print(f"  Config saved to: {config_path}")
    return config_path


def main():
    parser = argparse.ArgumentParser(description="Convert pickle to HDF5 for torch_brain")
    parser.add_argument("input_pickle", help="Input pickle file path")
    parser.add_argument("output_dir", help="Output directory for HDF5 files")
    parser.add_argument("--brainset-id", default="dataset", help="Brainset identifier")
    args = parser.parse_args()

    # Load pickle to get output info for config
    with open(args.input_pickle, 'rb') as f:
        data = pickle.load(f)

    # Handle different pickle formats
    if 'output_values' in data:
        # Standard format with output_values list
        output_values = data['output_values']
    elif 'metadata' in data and 'output_variables' in data['metadata']:
        # Format with output info in metadata
        output_vars = data['metadata']['output_variables']
        # Extract number of classes from descriptions or infer from data
        output_values = []
        for name, desc in output_vars.items():
            # Parse description for class count, or infer from max value in data
            if '7 bins' in desc:
                output_values.append([str(i) for i in range(7)])
            elif '5 bins' in desc:
                output_values.append([str(i) for i in range(5)])
            elif 'Binary' in desc or '0=no, 1=yes' in desc:
                output_values.append(['0', '1'])
            elif '0=A, 1=B, 2=C' in desc:
                output_values.append(['A', 'B', 'C'])
            else:
                # Infer from data
                all_vals = set()
                for sess in data['output']:
                    for trial in sess:
                        idx = list(output_vars.keys()).index(name)
                        if trial.shape[0] > idx:
                            all_vals.update(trial[idx, :].flatten().tolist())
                output_values.append([str(int(v)) for v in sorted(all_vals)])
    else:
        raise ValueError("Cannot find output_values or output_variables in pickle")

    # Convert to HDF5
    session_ids, output_names = convert_pickle_to_hdf5(
        args.input_pickle,
        args.output_dir,
        args.brainset_id,
    )

    # Generate YAML config
    generate_yaml_config(
        args.output_dir,
        args.brainset_id,
        session_ids,
        output_names,
        output_values,
    )


if __name__ == "__main__":
    main()
