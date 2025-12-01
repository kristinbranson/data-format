#!/usr/bin/env python
"""
Utility functions for MAP dataset conversion and validation.

This module provides functions for:
- Validating converted data structure
- Loading and saving data
- Basic data inspection and statistics
- Visualization of converted data
"""

import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_data(filepath):
    """
    Load the standardized MAP dataset.

    Args:
        filepath: Path to pickle file

    Returns:
        data: Dictionary with 'neural', 'input', 'output', 'metadata' keys
    """
    print(f"Loading data from {filepath}...")
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


def save_data(data, filepath):
    """
    Save the standardized MAP dataset.

    Args:
        data: Dictionary with 'neural', 'input', 'output', 'metadata' keys
        filepath: Path to save pickle file
    """
    print(f"Saving data to {filepath}...")
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)
    print("Done!")


def validate_data_structure(data):
    """
    Validate that data matches the required format specification.

    Args:
        data: Dictionary with 'neural', 'input', 'output', 'metadata' keys

    Returns:
        bool: True if valid, False otherwise
    """
    print("="*80)
    print("VALIDATING DATA STRUCTURE")
    print("="*80)

    all_valid = True

    # Check top-level keys
    required_keys = ['neural', 'input', 'output', 'metadata']
    for key in required_keys:
        if key not in data:
            print(f"✗ Missing required key: {key}")
            all_valid = False
        else:
            print(f"✓ Found key: {key}")

    if not all_valid:
        return False

    # Validate neural data structure
    print("\n--- Neural Data ---")
    neural = data['neural']

    if isinstance(neural, list):
        print(f"✓ Neural is a list (subjects)")
        print(f"  Number of subjects: {len(neural)}")

        for subj_idx, subject_trials in enumerate(neural[:3]):
            if not isinstance(subject_trials, list):
                print(f"  ✗ Subject {subj_idx} is not a list of trials")
                all_valid = False
                continue

            print(f"\n  Subject {subj_idx}:")
            print(f"    Number of trials: {len(subject_trials)}")

            if len(subject_trials) > 0:
                trial0 = subject_trials[0]
                if isinstance(trial0, np.ndarray):
                    print(f"    ✓ Trial 0 is numpy array")
                    print(f"      Shape: {trial0.shape} (n_neurons={trial0.shape[0]}, n_timepoints={trial0.shape[1]})")
                    print(f"      Dtype: {trial0.dtype}")

                    # Check consistency across trials
                    shapes = [t.shape for t in subject_trials[:min(10, len(subject_trials))]]
                    if len(set(shapes)) == 1:
                        print(f"    ✓ All trials have consistent shape (checked first {min(10, len(subject_trials))} trials)")
                    else:
                        print(f"    ✗ Inconsistent trial shapes: {set(shapes)}")
                        all_valid = False
                else:
                    print(f"    ✗ Trial 0 is not numpy array: {type(trial0)}")
                    all_valid = False
    else:
        print(f"✗ Neural is not a list: {type(neural)}")
        all_valid = False

    # Validate input data structure
    print("\n--- Input Data ---")
    input_data = data['input']

    if isinstance(input_data, list):
        print(f"✓ Input is a list (subjects)")
        print(f"  Number of subjects: {len(input_data)}")

        if len(input_data) > 0 and len(input_data[0]) > 0:
            print(f"  First subject, first trial shape: {input_data[0][0].shape}")
            print(f"  First subject, first trial values: {input_data[0][0]}")
    else:
        print(f"✗ Input is not a list: {type(input_data)}")
        all_valid = False

    # Validate output data structure
    print("\n--- Output Data ---")
    output_data = data['output']

    if isinstance(output_data, list):
        print(f"✓ Output is a list (subjects)")
        print(f"  Number of subjects: {len(output_data)}")

        if len(output_data) > 0 and len(output_data[0]) > 0:
            print(f"  First subject, first trial shape: {output_data[0][0].shape}")
            print(f"  First subject, first trial values: {output_data[0][0]}")

            # Validate class label encoding for output
            all_outputs = np.array(output_data[0])
            if all_outputs.shape[1] == 3:
                # Check outcome classes are valid (0, 1, or 2)
                outcome_classes = all_outputs[:, 0]
                if np.all(np.isin(outcome_classes, [0.0, 1.0, 2.0])):
                    print(f"  ✓ Outcome classes valid (0=miss, 1=ignore, 2=hit)")
                else:
                    print(f"  ✗ Invalid outcome classes found: {np.unique(outcome_classes)}")
                    all_valid = False

                # Check early lick codes are valid (0 or 1)
                early_lick_codes = all_outputs[:, 1]
                if np.all(np.isin(early_lick_codes, [0.0, 1.0])):
                    print(f"  ✓ Early lick codes valid (0=not early, 1=early)")
                else:
                    print(f"  ✗ Invalid early lick codes found: {np.unique(early_lick_codes)}")
                    all_valid = False

                # Check action codes are valid (0, 1, or 2)
                action_codes = all_outputs[:, 2]
                if np.all(np.isin(action_codes, [0.0, 1.0, 2.0])):
                    print(f"  ✓ Action codes valid (0=lick left, 1=ignore, 2=lick right)")
                else:
                    print(f"  ✗ Invalid action codes found: {np.unique(action_codes)}")
                    all_valid = False
            else:
                print(f"  ✗ Expected output shape (n_trials, 3), got {all_outputs.shape}")
                all_valid = False
    else:
        print(f"✗ Output is not a list: {type(output_data)}")
        all_valid = False

    # Validate metadata
    print("\n--- Metadata ---")
    metadata = data['metadata']

    required_metadata = ['task_description', 'brain_regions']
    for key in required_metadata:
        if key in metadata:
            val_str = str(metadata[key])
            print(f"✓ Has {key}: {val_str[:100]}..." if len(val_str) > 100 else f"✓ Has {key}: {val_str}")
        else:
            print(f"  Note: Missing optional metadata key: {key}")

    # Check dimension consistency
    print("\n--- Dimension Consistency ---")
    n_subjects = len(neural)
    if len(input_data) == n_subjects and len(output_data) == n_subjects:
        print(f"✓ All data structures have {n_subjects} subjects")
    else:
        print(f"✗ Inconsistent number of subjects: neural={len(neural)}, input={len(input_data)}, output={len(output_data)}")
        all_valid = False

    # Check trial counts match
    for subj_idx in range(min(3, n_subjects)):
        n_neural_trials = len(neural[subj_idx])
        n_input_trials = len(input_data[subj_idx])
        n_output_trials = len(output_data[subj_idx])

        if n_neural_trials == n_input_trials == n_output_trials:
            print(f"✓ Subject {subj_idx}: {n_neural_trials} trials (consistent)")
        else:
            print(f"✗ Subject {subj_idx}: neural={n_neural_trials}, input={n_input_trials}, output={n_output_trials}")
            all_valid = False

    print("\n" + "="*80)
    if all_valid:
        print("✓✓✓ DATA STRUCTURE IS VALID ✓✓✓")
    else:
        print("✗✗✗ DATA STRUCTURE HAS ERRORS ✗✗✗")
    print("="*80)

    return all_valid


def print_data_summary(data):
    """
    Print a summary of the converted data.

    Args:
        data: Converted data dictionary
    """
    print("\n" + "="*80)
    print("DATA SUMMARY")
    print("="*80)

    neural = data['neural']
    input_data = data['input']
    output_data = data['output']
    metadata = data['metadata']

    print(f"\nDataset: {metadata.get('dataset', 'N/A')}")
    print(f"Task: {metadata.get('task_description', 'N/A')}")
    print(f"\nNumber of subjects: {len(neural)}")

    total_trials = sum(len(subj) for subj in neural)
    print(f"Total trials across all subjects: {total_trials}")

    if len(neural) > 0 and len(neural[0]) > 0:
        n_neurons = neural[0][0].shape[0]
        n_time = neural[0][0].shape[1]
        print(f"\nExample trial dimensions:")
        print(f"  Neurons: {n_neurons}")
        print(f"  Time bins: {n_time}")
        print(f"  Bin width: {metadata.get('bin_width', 'N/A')} seconds")
        print(f"  Sampling rate: {metadata.get('sampling_rate', 'N/A')} Hz")
        print(f"  Time window: {metadata.get('time_window', 'N/A')}")

    brain_regions_str = str(metadata.get('brain_regions', 'N/A'))
    print(f"\nBrain regions: {brain_regions_str[:200]}...")

    # Print input/output descriptions
    print(f"\nInput description: {metadata.get('input_description', 'N/A')}")
    print(f"Output description: {metadata.get('output_description', 'N/A')}")

    print("\n" + "="*80)


def compute_statistics(data, subject_idx=0):
    """
    Compute basic statistics for the dataset.

    Args:
        data: Converted data dictionary
        subject_idx: Index of subject to analyze

    Returns:
        dict: Dictionary of statistics
    """
    neural = data['neural'][subject_idx]
    input_data = data['input'][subject_idx]
    output_data = data['output'][subject_idx]

    # Concatenate all neural data
    all_neural = np.concatenate([t for t in neural], axis=1)

    # Compute statistics
    stats = {
        'n_trials': len(neural),
        'n_neurons': neural[0].shape[0],
        'n_timebins': neural[0].shape[1],
        'avg_fr_per_neuron': all_neural.mean(axis=1),
        'std_fr_per_neuron': all_neural.std(axis=1),
        'sparsity_per_neuron': (all_neural == 0).mean(axis=1),
        'trial_counts': {
            'total': len(output_data),
            'hit': sum(1 for out in output_data if out[0] == 1),
            'miss': sum(1 for out in output_data if out[1] == 1),
            'ignore': sum(1 for out in output_data if out[2] == 1),
            'early_lick': sum(1 for out in output_data if out[3] == 1),
        }
    }

    return stats


def visualize_sample_data(data, output_dir='visualizations', subject_idx=0):
    """
    Create visualizations of the converted data.

    Args:
        data: Converted data dictionary
        output_dir: Directory to save plots
        subject_idx: Index of subject to visualize
    """
    Path(output_dir).mkdir(exist_ok=True)

    print(f"\nCreating visualizations in {output_dir}/...")

    # Get subject's data
    neural = data['neural'][subject_idx]
    input_data = data['input'][subject_idx]
    output_data = data['output'][subject_idx]

    # Plot 1: Neural activity raster for sample trials
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    for trial_idx in range(min(3, len(neural))):
        ax = axes[trial_idx]
        trial_neural = neural[trial_idx]

        im = ax.imshow(trial_neural, aspect='auto', cmap='viridis', interpolation='none')
        ax.set_ylabel('Neuron')
        ax.set_title(f'Trial {trial_idx} (Input: {input_data[trial_idx]}, Output: {output_data[trial_idx]})')

        if trial_idx == 2:
            ax.set_xlabel('Time bin')

    plt.colorbar(im, ax=axes, label='Firing rate (Hz)')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/neural_activity_raster.png', dpi=150)
    print(f"  Saved: neural_activity_raster.png")
    plt.close()

    # Plot 2: Population average firing rate
    fig, ax = plt.subplots(figsize=(12, 6))

    for trial_idx in range(min(20, len(neural))):
        trial_neural = neural[trial_idx]
        avg_fr = trial_neural.mean(axis=0)
        ax.plot(avg_fr, alpha=0.3, color='blue')

    all_trials_avg = np.mean([t.mean(axis=0) for t in neural[:20]], axis=0)
    ax.plot(all_trials_avg, color='red', linewidth=2, label='Mean across trials')

    ax.set_xlabel('Time bin')
    ax.set_ylabel('Average firing rate (Hz)')
    ax.set_title('Population Average Firing Rate')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/population_average_fr.png', dpi=150)
    print(f"  Saved: population_average_fr.png")
    plt.close()

    # Plot 3: Input/Output distributions
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    inputs = np.array(input_data)
    outputs = np.array(output_data)

    # Input distribution
    ax = axes[0]
    ax.hist(inputs[:, 0], bins=2, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Instruction')
    ax.set_ylabel('Count')
    ax.set_title('Trial Instructions (0=left, 1=right)')
    ax.set_xticks([0, 1])

    # Output distribution
    ax = axes[1]
    outcome_counts = [outputs[:, i].sum() for i in range(4)]
    ax.bar(['Hit', 'Miss', 'Ignore', 'Early Lick'], outcome_counts, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Count')
    ax.set_title('Trial Outcomes')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/input_output_distributions.png', dpi=150)
    print(f"  Saved: input_output_distributions.png")
    plt.close()

    # Plot 4: Statistics summary
    stats = compute_statistics(data, subject_idx)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Firing rate distribution
    ax = axes[0, 0]
    ax.hist(stats['avg_fr_per_neuron'], bins=50, edgecolor='black', alpha=0.7)
    ax.set_xlabel('Average firing rate (Hz)')
    ax.set_ylabel('Number of neurons')
    ax.set_title(f'Neuron Firing Rates (mean={stats["avg_fr_per_neuron"].mean():.2f} Hz)')
    ax.set_xlim([0, max(10, np.percentile(stats['avg_fr_per_neuron'], 95))])

    # Sparsity distribution
    ax = axes[0, 1]
    ax.hist(stats['sparsity_per_neuron'], bins=50, edgecolor='black', alpha=0.7)
    ax.set_xlabel('Sparsity (fraction of zero bins)')
    ax.set_ylabel('Number of neurons')
    ax.set_title('Neuron Sparsity')

    # Trial outcome counts
    ax = axes[1, 0]
    counts = stats['trial_counts']
    ax.bar(['Hit', 'Miss', 'Ignore', 'Early\nLick'],
           [counts['hit'], counts['miss'], counts['ignore'], counts['early_lick']],
           alpha=0.7, edgecolor='black')
    ax.set_ylabel('Number of trials')
    ax.set_title(f'Trial Outcomes (n={counts["total"]} trials)')
    ax.grid(True, alpha=0.3, axis='y')

    # Summary text
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
Dataset Summary
{'='*40}

Trials: {stats['n_trials']}
Neurons: {stats['n_neurons']}
Time bins: {stats['n_timebins']}

Average FR: {stats['avg_fr_per_neuron'].mean():.2f} Hz
Median FR: {np.median(stats['avg_fr_per_neuron']):.2f} Hz
Sparsity: {stats['sparsity_per_neuron'].mean():.2%}

Hit rate: {100*counts['hit']/counts['total']:.1f}%
Miss rate: {100*counts['miss']/counts['total']:.1f}%
Ignore rate: {100*counts['ignore']/counts['total']:.1f}%
Early lick rate: {100*counts['early_lick']/counts['total']:.1f}%
    """
    ax.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
            verticalalignment='center')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/data_statistics.png', dpi=150)
    print(f"  Saved: data_statistics.png")
    plt.close()

    print("\nVisualization complete!")


def verify_against_source(data, verbose=True):
    """
    Verify that converted data matches the source NWB files.

    Args:
        data: Converted data dictionary
        verbose: Print detailed information

    Returns:
        bool: True if verification passes, False otherwise
    """
    if verbose:
        print("\n" + "="*80)
        print("SOURCE FILE VERIFICATION")
        print("="*80)

    try:
        from pynwb import NWBHDF5IO
    except ImportError:
        print("  ⚠ pynwb not available, skipping source verification")
        return True

    all_passed = True

    # Check each subject
    for subj_idx, subj_metadata in enumerate(data['metadata'].get('subject_metadata', [])):
        source_file = subj_metadata.get('source_file')

        if not source_file:
            print(f"  ⚠ Subject {subj_idx}: No source_file in metadata")
            continue

        if verbose:
            print(f"\nSubject {subj_idx}: {source_file}")

        # Check if file exists
        from pathlib import Path
        source_path = Path(source_file)
        if not source_path.exists():
            print(f"  ✗ Source file not found: {source_file}")
            all_passed = False
            continue

        # Load NWB file and verify
        try:
            with NWBHDF5IO(str(source_path), 'r') as io:
                nwbfile = io.read()

                # Check 1: Trial counts
                n_trials_original = len(nwbfile.trials)
                n_trials_converted = len(data['neural'][subj_idx])
                n_trials_metadata = subj_metadata.get('n_trials', n_trials_converted)

                if n_trials_converted != n_trials_metadata:
                    print(f"  ✗ Trial count mismatch: converted={n_trials_converted}, metadata={n_trials_metadata}")
                    all_passed = False
                elif verbose:
                    print(f"  ✓ Trial count: {n_trials_converted} (original: {n_trials_original})")

                # Check 2: Unit counts
                n_units_original = subj_metadata.get('n_units_original', 0)
                n_units_converted = data['neural'][subj_idx][0].shape[0] if n_trials_converted > 0 else 0
                n_units_metadata = subj_metadata.get('n_units', n_units_converted)

                if n_units_converted != n_units_metadata:
                    print(f"  ✗ Unit count mismatch: converted={n_units_converted}, metadata={n_units_metadata}")
                    all_passed = False
                elif verbose:
                    print(f"  ✓ Unit count: {n_units_converted} (original: {n_units_original})")

                # Check 3: Spot check a few trials
                if n_trials_converted > 0:
                    # Check first trial
                    trial_idx = 0
                    outcome_converted = data['output'][subj_idx][trial_idx][0]
                    outcome_nwb = nwbfile.trials['outcome'][trial_idx]

                    # Map outcome to class
                    outcome_map = {'miss': 0.0, 'ignore': 1.0, 'hit': 2.0}
                    outcome_expected = outcome_map.get(outcome_nwb, -1)

                    if outcome_converted != outcome_expected:
                        print(f"  ✗ Trial 0 outcome mismatch: converted={outcome_converted}, NWB={outcome_nwb}")
                        all_passed = False
                    elif verbose:
                        print(f"  ✓ Trial 0 outcome matches: {outcome_nwb}")

                    # Check instruction
                    instruction_converted = data['input'][subj_idx][trial_idx][0]
                    instruction_nwb = nwbfile.trials['trial_instruction'][trial_idx]
                    instruction_expected = 1.0 if instruction_nwb == 'right' else 0.0

                    if instruction_converted != instruction_expected:
                        print(f"  ✗ Trial 0 instruction mismatch: converted={instruction_converted}, NWB={instruction_nwb}")
                        all_passed = False
                    elif verbose:
                        print(f"  ✓ Trial 0 instruction matches: {instruction_nwb}")

        except Exception as e:
            print(f"  ✗ Error reading NWB file: {e}")
            all_passed = False

    if verbose:
        print("\n" + "="*80)
        if all_passed:
            print("✓✓✓ SOURCE VERIFICATION PASSED ✓✓✓")
        else:
            print("✗✗✗ SOURCE VERIFICATION FAILED ✗✗✗")
        print("="*80)

    return all_passed


def sanity_check_data(data, verbose=True):
    """
    Perform comprehensive sanity checks on converted data to catch common bugs.

    Args:
        data: Converted data dictionary
        verbose: Print detailed information

    Returns:
        bool: True if all checks pass, False otherwise
    """
    if verbose:
        print("\n" + "="*80)
        print("SANITY CHECKS")
        print("="*80)

    all_passed = True

    # Check 1: Neural data is not all zeros
    if verbose:
        print("\n1. Checking neural data is not all zeros...")

    for subj_idx, subject_trials in enumerate(data['neural']):
        n_zero_trials = 0
        n_low_activity_trials = 0

        for trial_idx, trial_neural in enumerate(subject_trials):
            max_val = trial_neural.max()
            mean_val = trial_neural.mean()

            if max_val == 0:
                n_zero_trials += 1
                if verbose and trial_idx < 5:  # Show first few
                    print(f"  ✗ Subject {subj_idx}, Trial {trial_idx}: All zeros!")
                all_passed = False
            elif mean_val < 0.1:  # Very low average firing rate
                n_low_activity_trials += 1

        if n_zero_trials > 0:
            print(f"  ✗ Subject {subj_idx}: {n_zero_trials}/{len(subject_trials)} trials have all zeros")
            all_passed = False
        else:
            if verbose:
                print(f"  ✓ Subject {subj_idx}: No all-zero trials")

        if n_low_activity_trials > 0.5 * len(subject_trials):
            print(f"  ⚠ Subject {subj_idx}: {n_low_activity_trials}/{len(subject_trials)} trials have very low activity (<0.1 Hz mean)")

    # Check 2: Neural data has reasonable firing rates
    if verbose:
        print("\n2. Checking firing rates are reasonable...")

    for subj_idx, subject_trials in enumerate(data['neural']):
        all_neural = np.concatenate([t for t in subject_trials], axis=1)
        max_fr = all_neural.max()
        mean_fr = all_neural.mean()

        if max_fr > 1000:
            print(f"  ⚠ Subject {subj_idx}: Very high max firing rate: {max_fr:.1f} Hz (possible bug?)")
        elif max_fr < 1:
            print(f"  ⚠ Subject {subj_idx}: Very low max firing rate: {max_fr:.1f} Hz")
        else:
            if verbose:
                print(f"  ✓ Subject {subj_idx}: Max FR = {max_fr:.1f} Hz, Mean FR = {mean_fr:.2f} Hz")

    # Check 3: Check for NaN or Inf values
    if verbose:
        print("\n3. Checking for NaN/Inf values...")

    has_nan_inf = False
    for subj_idx in range(len(data['neural'])):
        # Check neural
        for trial_idx, trial in enumerate(data['neural'][subj_idx]):
            if np.any(np.isnan(trial)) or np.any(np.isinf(trial)):
                print(f"  ✗ Subject {subj_idx}, Trial {trial_idx}: Neural data has NaN/Inf")
                has_nan_inf = True
                all_passed = False

        # Check input
        inputs = np.array(data['input'][subj_idx])
        if np.any(np.isnan(inputs)) or np.any(np.isinf(inputs)):
            print(f"  ✗ Subject {subj_idx}: Input data has NaN/Inf")
            has_nan_inf = True
            all_passed = False

        # Check output
        outputs = np.array(data['output'][subj_idx])
        if np.any(np.isnan(outputs)) or np.any(np.isinf(outputs)):
            print(f"  ✗ Subject {subj_idx}: Output data has NaN/Inf")
            has_nan_inf = True
            all_passed = False

    if not has_nan_inf and verbose:
        print("  ✓ No NaN/Inf values found")

    # Check 4: Verify output consistency (outcome, early_lick, action)
    if verbose:
        print("\n4. Checking output variable consistency...")

    for subj_idx in range(len(data['output'])):
        inputs = np.array(data['input'][subj_idx])
        outputs = np.array(data['output'][subj_idx])

        if outputs.shape[1] >= 3:  # Has action variable
            n_inconsistent = 0
            for trial_idx in range(len(outputs)):
                outcome = outputs[trial_idx, 0]
                early_lick = outputs[trial_idx, 1]
                action = outputs[trial_idx, 2]
                instruction = inputs[trial_idx, 0]

                # Check action consistency with outcome and instruction
                if outcome == 1:  # ignore
                    if action != 1:
                        n_inconsistent += 1
                        if verbose and n_inconsistent <= 3:
                            print(f"  ✗ Subject {subj_idx}, Trial {trial_idx}: outcome=ignore but action={action}")
                elif outcome == 2:  # hit
                    expected_action = 0 if instruction == 0 else 2
                    if action != expected_action:
                        n_inconsistent += 1
                        if verbose and n_inconsistent <= 3:
                            print(f"  ✗ Subject {subj_idx}, Trial {trial_idx}: outcome=hit, instruction={instruction}, but action={action}")
                elif outcome == 0:  # miss
                    expected_action = 2 if instruction == 0 else 0
                    if action != expected_action:
                        n_inconsistent += 1
                        if verbose and n_inconsistent <= 3:
                            print(f"  ✗ Subject {subj_idx}, Trial {trial_idx}: outcome=miss, instruction={instruction}, but action={action}")

            if n_inconsistent > 0:
                print(f"  ✗ Subject {subj_idx}: {n_inconsistent} trials have inconsistent action")
                all_passed = False
            else:
                if verbose:
                    print(f"  ✓ Subject {subj_idx}: All actions consistent with outcome/instruction")

    # Check 5: Trial counts match across neural/input/output
    if verbose:
        print("\n5. Checking trial counts match...")

    for subj_idx in range(len(data['neural'])):
        n_neural = len(data['neural'][subj_idx])
        n_input = len(data['input'][subj_idx])
        n_output = len(data['output'][subj_idx])

        if n_neural != n_input or n_neural != n_output:
            print(f"  ✗ Subject {subj_idx}: Mismatch! neural={n_neural}, input={n_input}, output={n_output}")
            all_passed = False
        else:
            if verbose:
                print(f"  ✓ Subject {subj_idx}: {n_neural} trials (consistent)")

    # Check 6: All trials have same dimensions
    if verbose:
        print("\n6. Checking trial dimensions are consistent...")

    for subj_idx in range(len(data['neural'])):
        shapes = [t.shape for t in data['neural'][subj_idx]]
        unique_shapes = set(shapes)

        if len(unique_shapes) > 1:
            print(f"  ✗ Subject {subj_idx}: Inconsistent shapes: {unique_shapes}")
            all_passed = False
        else:
            if verbose:
                print(f"  ✓ Subject {subj_idx}: All trials have shape {shapes[0]}")

    # Final summary
    if verbose:
        print("\n" + "="*80)
        if all_passed:
            print("✓✓✓ ALL SANITY CHECKS PASSED ✓✓✓")
        else:
            print("✗✗✗ SOME SANITY CHECKS FAILED ✗✗✗")
        print("="*80)

    return all_passed
