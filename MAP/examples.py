#!/usr/bin/env python
"""
Example usage of the converted MAP dataset.

This script demonstrates how to load and use the standardized MAP data
for downstream analysis tasks.
"""

import pickle
import numpy as np
import matplotlib.pyplot as plt


def load_data(filepath):
    """Load the standardized MAP dataset."""
    print(f"Loading data from {filepath}...")
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


def example_1_basic_access(data):
    """Example 1: Basic data access and inspection."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Data Access")
    print("="*80)

    # Access neural data for first subject
    subject_0_neural = data['neural'][0]
    subject_0_input = data['input'][0]
    subject_0_output = data['output'][0]

    print(f"\nSubject 0:")
    print(f"  Number of trials: {len(subject_0_neural)}")
    print(f"  Neurons in trial 0: {subject_0_neural[0].shape[0]}")
    print(f"  Time bins in trial 0: {subject_0_neural[0].shape[1]}")

    # Access specific trial
    trial_10_neural = subject_0_neural[10]
    trial_10_input = subject_0_input[10]
    trial_10_output = subject_0_output[10]

    print(f"\nTrial 10:")
    print(f"  Neural activity shape: {trial_10_neural.shape}")
    print(f"  Input [instruction, photostim_onset, photostim_power]: {trial_10_input}")
    print(f"  Output [outcome_class, early_lick, action]: {trial_10_output}")


def example_2_trial_selection(data):
    """Example 2: Selecting trials by condition."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Trial Selection by Condition")
    print("="*80)

    subject_0_neural = data['neural'][0]
    subject_0_input = data['input'][0]
    subject_0_output = data['output'][0]

    # Convert to arrays for easier indexing
    inputs = np.array(subject_0_input)  # (n_trials, 3)
    outputs = np.array(subject_0_output)  # (n_trials, 3)

    # Select trials by instruction (left vs right)
    left_trials = inputs[:, 0] == 0  # instruction = 0 (left)
    right_trials = inputs[:, 0] == 1  # instruction = 1 (right)

    print(f"\nLeft trials: {left_trials.sum()}")
    print(f"Right trials: {right_trials.sum()}")

    # Select trials by outcome class (output[0]: 0=miss, 1=ignore, 2=hit)
    hit_trials = outputs[:, 0] == 2
    miss_trials = outputs[:, 0] == 0
    ignore_trials = outputs[:, 0] == 1

    print(f"\nHit trials: {hit_trials.sum()}")
    print(f"Miss trials: {miss_trials.sum()}")
    print(f"Ignore trials: {ignore_trials.sum()}")

    # Select hit trials by direction
    hit_left_trials = left_trials & hit_trials
    hit_right_trials = right_trials & hit_trials

    print(f"\nHit left trials: {hit_left_trials.sum()}")
    print(f"Hit right trials: {hit_right_trials.sum()}")

    # Get neural data for these conditions
    neural_hit_left = [subject_0_neural[i] for i in range(len(subject_0_neural))
                       if hit_left_trials[i]]
    neural_hit_right = [subject_0_neural[i] for i in range(len(subject_0_neural))
                        if hit_right_trials[i]]

    print(f"\nNeural data shapes:")
    print(f"  Hit left: {len(neural_hit_left)} trials")
    print(f"  Hit right: {len(neural_hit_right)} trials")


def example_3_population_average(data):
    """Example 3: Compute population average PSTH."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Population Average PSTH")
    print("="*80)

    subject_0_neural = data['neural'][0]
    subject_0_input = data['input'][0]
    subject_0_output = data['output'][0]

    inputs = np.array(subject_0_input)
    outputs = np.array(subject_0_output)

    # Select hit trials by direction
    left_trials = inputs[:, 0] == 0
    right_trials = inputs[:, 0] == 1
    hit_trials = outputs[:, 0] == 2  # outcome class 2 = hit

    hit_left = left_trials & hit_trials
    hit_right = right_trials & hit_trials

    # Get neural data and average across neurons
    left_neural = [subject_0_neural[i].mean(axis=0) for i in range(len(subject_0_neural))
                   if hit_left[i]]
    right_neural = [subject_0_neural[i].mean(axis=0) for i in range(len(subject_0_neural))
                    if hit_right[i]]

    # Average across trials
    left_avg = np.mean(left_neural, axis=0)
    right_avg = np.mean(right_neural, axis=0)

    # Time axis
    bin_width = data['metadata']['bin_width']
    time_window = data['metadata']['time_window']
    time_axis = np.arange(time_window[0], time_window[1], bin_width)

    print(f"\nComputed average PSTH:")
    print(f"  Left trials: {len(left_neural)} trials averaged")
    print(f"  Right trials: {len(right_neural)} trials averaged")
    print(f"  Time axis: {time_window[0]} to {time_window[1]} sec")

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(time_axis, left_avg, label='Left trials', linewidth=2)
    plt.plot(time_axis, right_avg, label='Right trials', linewidth=2)
    plt.axvline(0, color='k', linestyle='--', alpha=0.5, label='Go cue')
    plt.xlabel('Time from go cue (s)')
    plt.ylabel('Average firing rate (Hz)')
    plt.title('Population Average Activity (Hit Trials)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('example_psth.png', dpi=150)
    print(f"\nSaved plot: example_psth.png")
    plt.close()


def example_4_single_neuron_selectivity(data):
    """Example 4: Analyze single neuron selectivity."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Single Neuron Selectivity")
    print("="*80)

    subject_0_neural = data['neural'][0]
    subject_0_input = data['input'][0]
    subject_0_output = data['output'][0]

    inputs = np.array(subject_0_input)
    outputs = np.array(subject_0_output)

    # Select hit trials
    left_trials = inputs[:, 0] == 0
    right_trials = inputs[:, 0] == 1
    hit_trials = outputs[:, 0] == 2  # outcome class 2 = hit

    hit_left = left_trials & hit_trials
    hit_right = right_trials & hit_trials

    # Stack all trials to get (n_trials, n_neurons, n_time)
    all_neural = np.array(subject_0_neural)  # (n_trials, n_neurons, n_time)

    # Compute average during delay period (example: bins 40-60)
    delay_bins = slice(40, 60)
    delay_activity = all_neural[:, :, delay_bins].mean(axis=2)  # (n_trials, n_neurons)

    # Average across trials for each condition
    left_delay = delay_activity[hit_left].mean(axis=0)  # (n_neurons,)
    right_delay = delay_activity[hit_right].mean(axis=0)

    # Compute selectivity index: (right - left) / (right + left)
    selectivity = (right_delay - left_delay) / (right_delay + left_delay + 1e-10)

    print(f"\nSelectivity analysis:")
    print(f"  Neurons analyzed: {len(selectivity)}")
    print(f"  Left-selective neurons (selectivity < -0.2): {(selectivity < -0.2).sum()}")
    print(f"  Right-selective neurons (selectivity > 0.2): {(selectivity > 0.2).sum()}")
    print(f"  Non-selective neurons: {((selectivity >= -0.2) & (selectivity <= 0.2)).sum()}")

    # Plot selectivity distribution
    plt.figure(figsize=(10, 5))
    plt.hist(selectivity, bins=50, edgecolor='black', alpha=0.7)
    plt.axvline(0, color='r', linestyle='--', linewidth=2, label='No selectivity')
    plt.axvline(-0.2, color='b', linestyle='--', alpha=0.5, label='Left selective threshold')
    plt.axvline(0.2, color='b', linestyle='--', alpha=0.5, label='Right selective threshold')
    plt.xlabel('Selectivity index (right - left) / (right + left)')
    plt.ylabel('Number of neurons')
    plt.title('Direction Selectivity During Delay Period')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('example_selectivity.png', dpi=150)
    print(f"\nSaved plot: example_selectivity.png")
    plt.close()


def example_5_decoding_preparation(data):
    """Example 5: Prepare data for decoding analysis."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Prepare Data for Decoding")
    print("="*80)

    subject_0_neural = data['neural'][0]
    subject_0_input = data['input'][0]
    subject_0_output = data['output'][0]

    # Only use hit trials for decoding
    outputs = np.array(subject_0_output)
    hit_trials = outputs[:, 0] == 2  # outcome class 2 = hit

    # Get labels (trial instruction)
    inputs = np.array(subject_0_input)
    labels = inputs[:, 0].astype(int)  # 0 (left) or 1 (right)

    # Filter to hit trials
    labels_hit = labels[hit_trials]
    neural_hit = [subject_0_neural[i] for i in range(len(subject_0_neural))
                  if hit_trials[i]]

    # For decoding, we might want to average over a time window
    # Example: use delay period (bins 40-60)
    delay_bins = slice(40, 60)
    X = np.array([trial[:, delay_bins].mean(axis=1) for trial in neural_hit])  # (n_trials, n_neurons)
    y = labels_hit

    print(f"\nDecoding dataset prepared:")
    print(f"  Features (X): {X.shape} (n_trials, n_neurons)")
    print(f"  Labels (y): {y.shape}")
    print(f"  Label distribution: {np.bincount(y)}")
    print(f"\n  This can now be used with scikit-learn classifiers:")
    print(f"    from sklearn.linear_model import LogisticRegression")
    print(f"    from sklearn.model_selection import cross_val_score")
    print(f"    clf = LogisticRegression()")
    print(f"    scores = cross_val_score(clf, X, y, cv=5)")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python examples.py <data_file.pkl>")
        print("\nExample: python examples.py single_session_formatted.pkl")
        sys.exit(1)

    # Load data
    data = load_data(sys.argv[1])

    # Run examples
    example_1_basic_access(data)
    example_2_trial_selection(data)
    example_3_population_average(data)
    example_4_single_neuron_selectivity(data)
    example_5_decoding_preparation(data)

    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80)
