# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Training and Testing Decoders on MAP Dataset
#
# This notebook demonstrates how to:
# 1. Load the standardized MAP dataset
# 2. Prepare data for decoder training
# 3. Train decoder using joint linear projection method
# 4. Perform cross-validation and evaluate performance
# 5. Visualize results

# %% [markdown]
# ## Setup

# %%
import numpy as np
import matplotlib
# set backend to tkAgg
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
plt.ion()
import sys
from pathlib import Path

# Add the task directory to path to import decoder
sys.path.insert(0, str(Path('../task').resolve()))

from decoder import (
    train_decoder_linear,
    predict_linear,
    cross_validate_decoder,
    accuracy_all_mice,
    print_data_summary,
    plot_trial
)

from utils import load_data

# Set random seed for reproducibility
np.random.seed(42)

# %% [markdown]
# ## Load Data

# %%
# Load the standardized MAP dataset
data = load_data('single_session_formatted.pkl')
nmice = len(data['neural'])

# Print summary
print_data_summary(data)

# Plot example trials
input_names = ['Instruction (0=left, 1=right)', 'Photostim onset (s)', 'Photostim power (mW)']
output_names = ['Outcome (0=miss,1=ignore,2=hit)', 'Early lick (0=no,1=yes)', 'Action (0=lick left,1=ignore,2=lick right)']

mousesplot = []
trialsplot = []

# find a trial where outcome is miss (0)
outdim = 0
mousemiss = None
trialmiss = None
for mouse in np.random.permutation(nmice):
    ntrials = len(data['neural'][mouse])
    for trial in np.random.permutation(ntrials):
        if np.any(data['output'][mouse][trial][outdim] == 0):
            mousemiss = mouse
            trialmiss = trial
            mousesplot.append(mouse)
            trialsplot.append(trial)
            break
    if mousemiss is not None:
        break
    
# find a trial where outcome is hit (2)
mousehit = None
trialhit = None
for mouse in np.random.permutation(nmice):
    ntrials = len(data['neural'][mouse])
    for trial in np.random.permutation(ntrials):
        if np.any(data['output'][mouse][trial][outdim] == 2):
            mousehit = mouse
            trialhit = trial
            mousesplot.append(mouse)
            trialsplot.append(trial)
            break
    if mousehit is not None:
        break

nplot = len(mousesplot)
fig,ax = plt.subplots(3,nplot,figsize = (30,15),sharex='col')
for iplot in range(nplot):
    plot_trial(data, mouse=mousesplot[iplot], trial=trialsplot[iplot], input_names=input_names, output_names=output_names, ax=ax[:,iplot])

# %% [markdown]
# ## Prepare Data for Decoder
#
# The decoder functions now fully support 1D inputs/outputs:
# - Training functions handle 1D inputs/outputs internally
# - Evaluation functions also handle 1D outputs
# - No manual expansion needed!

# %%
# Use data directly - decoder handles everything!
neural = data['neural']
input_vars = data['input']
output_vars = data['output']

# Print shapes
print("\n" + "="*80)
print("DATA SHAPES (Native Format)")
print("="*80)
print(f"\nNumber of subjects: {len(neural)}")
print(f"Subject 0, Trial 0:")
print(f"  Neural shape: {neural[0][0].shape} (n_neurons, n_timepoints)")
print(f"  Input shape: {input_vars[0][0].shape} (n_input_vars,) - scalar per trial")
print(f"  Output shape: {output_vars[0][0].shape} (n_output_vars,) - scalar per trial")
print(f"\nNote: Decoder handles 1D inputs/outputs automatically during training and evaluation")
print(f"\nOutput format:")
print(f"  output[0] = outcome class (0=miss, 1=ignore, 2=hit)")
print(f"  output[1] = early lick (0=not early, 1=early)")
print(f"  output[2] = action (0=lick left, 1=ignore, 2=lick right)")
print(f"\nExample trial output: {output_vars[0][0]}")

# %% [markdown]
# ## Train and Test on All Data (Overfitting Check)
#
# First, let's train on all data and test on the same data to see the best possible performance
# (upper bound on what cross-validation should achieve).

# %%
print("\n" + "="*80)
print("TRAINING ON ALL DATA (Overfitting Check)")
print("="*80)

# Train on all data
model_all = train_decoder_linear(
    neural,
    input_vars,
    output_vars,
    metadata={},
    npcs=10,
    num_epochs=100,
    lr=0.01,
    batch_size=1024
)

# Predict on all data
predictions_all, pcs_all, confidences_all = predict_linear(neural, input_vars, model_all)

# Evaluate
scores_all = accuracy_all_mice(predictions_all, output_vars)

print("\nAccuracy on training data (overfitting upper bound):")
for out_dim in range(len(scores_all)):
    labels = ['Outcome', 'Early Lick', 'Action']
    print(f"  {labels[out_dim]}: {scores_all[out_dim]:.4f}")

print(f"\nMean accuracy: {scores_all.mean():.4f}")

fig,ax = plt.subplots(3,nplot,figsize = (30,15),sharex='col')
for iplot in range(nplot):
    plot_trial(data, mouse=mousesplot[iplot], trial=trialsplot[iplot], input_names=input_names, output_names=output_names, ax=ax[:,iplot],
               predictions=predictions_all)
fig.suptitle('Decoder Predictions (Trained and Tested on All Data)', fontsize=16, fontweight='bold')
fig.tight_layout()


# %% [markdown]
# ## Cross-Validation
#
# Now let's use 5-fold cross-validation to get a realistic estimate of generalization performance.
# This will be lower than the overfitting check above.

# %%
print("\n" + "="*80)
print("CROSS-VALIDATION (5-fold)")
print("="*80)

# Run cross-validation with accuracy evaluation
scores_cv, predictions_cv, pcs_cv, trial_splits = cross_validate_decoder(
    neural,
    input_vars,
    output_vars,
    train_decoder=train_decoder_linear,
    predict=predict_linear,
    eval_fn=accuracy_all_mice,  # Use accuracy for multi-class output
    nsets=5,           # 5-fold cross-validation
    npcs=10,           # Number of projected dimensions
    num_epochs=100,    # Training epochs
    lr=0.01,           # Learning rate
    batch_size=1024    # Batch size
)

print("\nCross-validation Accuracy Scores:")
print(f"  Output 0 (outcome class): {scores_cv[0]:.4f}")
print(f"  Output 1 (early lick):    {scores_cv[1]:.4f}")
print(f"  Output 2 (action):        {scores_cv[2]:.4f}")
print(f"\nMean Accuracy: {scores_cv.mean():.4f}")

# %% [markdown]
# ## Analyze Results

# %%
# Analyze predictions
subject_idx = 0
outputs_array = np.array(output_vars[subject_idx])  # (n_trials, doutput) - native 1D format
predictions_array = np.array(predictions_cv[subject_idx])  # (n_trials, doutput, T)

# For outputs: no time dimension (native 1D format)
# For predictions: take first timepoint (all are same for scalar outputs)
outcome_true = outputs_array[:, 0].astype(int)  # (n_trials,) outcome class
outcome_pred = predictions_array[:, 0, 0].astype(int)  # (n_trials,) predicted outcome
early_true = outputs_array[:, 1].astype(int)  # (n_trials,) early lick
early_pred = predictions_array[:, 1, 0].astype(int)  # (n_trials,) predicted early
action_true = outputs_array[:, 2].astype(int)  # (n_trials,) action
action_pred = predictions_array[:, 2, 0].astype(int)  # (n_trials,) predicted action

print("\n" + "="*80)
print("PREDICTION STATISTICS")
print("="*80)

# Outcome statistics
print("\nOutcome Classification:")
outcome_labels = ['Miss', 'Ignore', 'Hit']
for i, label in enumerate(outcome_labels):
    n_true = (outcome_true == i).sum()
    n_pred = (outcome_pred == i).sum()
    n_correct = ((outcome_true == i) & (outcome_pred == i)).sum()

    print(f"\n{label}:")
    print(f"  True count:      {n_true:4d}")
    print(f"  Predicted count: {n_pred:4d}")
    print(f"  Correct:         {n_correct:4d}")
    if n_true > 0:
        print(f"  Recall:          {n_correct/n_true:.3f}")
    if n_pred > 0:
        print(f"  Precision:       {n_correct/n_pred:.3f}")

# Overall outcome accuracy
outcome_accuracy = (outcome_true == outcome_pred).sum() / len(outcome_true)
print(f"\nOverall Outcome Accuracy: {outcome_accuracy:.3f}")

# Early lick statistics
print("\n" + "-"*80)
print("Early Lick Classification:")
n_true_early = (early_true == 1).sum()
n_pred_early = (early_pred == 1).sum()
n_correct_early = ((early_true == 1) & (early_pred == 1)).sum()
n_correct_not_early = ((early_true == 0) & (early_pred == 0)).sum()

print(f"\nEarly lick:")
print(f"  True count:      {n_true_early:4d}")
print(f"  Predicted count: {n_pred_early:4d}")
print(f"  Correct:         {n_correct_early:4d}")
if n_true_early > 0:
    print(f"  Recall:          {n_correct_early/n_true_early:.3f}")
if n_pred_early > 0:
    print(f"  Precision:       {n_correct_early/n_pred_early:.3f}")

early_accuracy = (early_true == early_pred).sum() / len(early_true)
print(f"\nOverall Early Lick Accuracy: {early_accuracy:.3f}")

# Action statistics
print("\n" + "-"*80)
print("Action Classification:")
action_labels = ['Lick Left', 'Ignore', 'Lick Right']
for i, label in enumerate(action_labels):
    n_true = (action_true == i).sum()
    n_pred = (action_pred == i).sum()
    n_correct = ((action_true == i) & (action_pred == i)).sum()

    print(f"\n{label}:")
    print(f"  True count:      {n_true:4d}")
    print(f"  Predicted count: {n_pred:4d}")
    print(f"  Correct:         {n_correct:4d}")
    if n_true > 0:
        print(f"  Recall:          {n_correct/n_true:.3f}")
    if n_pred > 0:
        print(f"  Precision:       {n_correct/n_pred:.3f}")

action_accuracy = (action_true == action_pred).sum() / len(action_true)
print(f"\nOverall Action Accuracy: {action_accuracy:.3f}")

# %% [markdown]
# ## Visualize Single Trial
#
# Let's examine a single trial in detail, showing:
# - Input variables over time
# - Neural activity (heatmap)
# - Ground truth output
# - Predicted output

# %%
# Select an example trial (pick a hit trial for clarity)
subject_idx = 0
hit_trials = np.where(outcome_true == 2)[0]  # outcome class 2 = hit
trial_idx = hit_trials[0] if len(hit_trials) > 0 else 0

# Get time axis
time_axis = np.arange(neural[subject_idx][trial_idx].shape[1]) * data['metadata']['bin_width'] + \
            data['metadata']['time_window'][0]

# Get data for this trial
trial_neural = neural[subject_idx][trial_idx]  # (n_neurons, T)
trial_input = input_vars[subject_idx][trial_idx]  # (3,) - scalar per trial
trial_output_true = output_vars[subject_idx][trial_idx]  # (3,) - scalar per trial
trial_output_pred = predictions_cv[subject_idx][trial_idx]  # (3, T) - predictions over time

# Create figure with 4 panels
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 2, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.3)

# Panel 1: Neural activity heatmap (spans both columns)
ax1 = fig.add_subplot(gs[0, :])
im = ax1.imshow(trial_neural, aspect='auto', cmap='viridis', interpolation='none',
                extent=[time_axis[0], time_axis[-1], 0, trial_neural.shape[0]])
ax1.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Go cue')
ax1.set_xlabel('Time from go cue (s)', fontsize=12)
ax1.set_ylabel('Neuron index', fontsize=12)
ax1.set_title(f'Trial {trial_idx} - Neural Activity (n_neurons={trial_neural.shape[0]})',
              fontsize=14, fontweight='bold')
cbar = plt.colorbar(im, ax=ax1, label='Firing rate (Hz)')
ax1.legend(loc='upper right')

# Panel 2: Input variables
ax2 = fig.add_subplot(gs[1, 0])
input_labels = ['Instruction\n(0=left, 1=right)', 'Photostim\nonset (s)', 'Photostim\npower (mW)']
colors_input = ['blue', 'orange', 'green']

for i, (label, color) in enumerate(zip(input_labels, colors_input)):
    # Input is scalar per trial (1D format)
    ax2.axhline(trial_input[i], color=color, linewidth=2, label=label, linestyle='-')

ax2.axvline(0, color='red', linestyle='--', linewidth=1, alpha=0.5)
ax2.set_xlabel('Time from go cue (s)', fontsize=12)
ax2.set_ylabel('Input value', fontsize=12)
ax2.set_title('Task Input Variables', fontsize=13, fontweight='bold')
ax2.legend(loc='upper right', fontsize=9)
ax2.grid(True, alpha=0.3)
ax2.set_xlim([time_axis[0], time_axis[-1]])

# Panel 3: Ground truth vs predicted output
ax3 = fig.add_subplot(gs[1, 1])

# Decode the outcome class (true is 1D, pred is 2D with time)
outcome_true_val = int(trial_output_true[0])  # Scalar
outcome_pred_val = int(trial_output_pred[0, 0])  # Take first timepoint
early_true_val = int(trial_output_true[1])  # Scalar
early_pred_val = int(trial_output_pred[1, 0])  # Take first timepoint
action_true_val = int(trial_output_true[2])  # Scalar
action_pred_val = int(trial_output_pred[2, 0])  # Take first timepoint

outcome_labels = ['Miss', 'Ignore', 'Hit']
outcome_colors = ['red', 'gray', 'green']

# Create bars for outcome
x_pos = [0, 1, 2]
true_outcome_bars = [1 if i == outcome_true_val else 0 for i in range(3)]
pred_outcome_bars = [1 if i == outcome_pred_val else 0 for i in range(3)]

width = 0.35
bars1 = ax3.bar([x - width/2 for x in x_pos], true_outcome_bars, width,
                label='True', alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax3.bar([x + width/2 for x in x_pos], pred_outcome_bars, width,
                label='Pred', alpha=0.5, edgecolor='black', linewidth=1.5)

# Color the bars
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    bar1.set_color(outcome_colors[i])
    bar2.set_color(outcome_colors[i])

ax3.axvline(3.5, color='black', linewidth=1, alpha=0.3)
ax3.text(3.5, 1.15, 'Early Lick', ha='center', fontsize=10, fontweight='bold')

# Add early lick bars
early_x = [4.5]
bars3 = ax3.bar([early_x[0] - width/2], [early_true_val], width,
                alpha=0.8, edgecolor='black', linewidth=1.5, color='orange')
bars4 = ax3.bar([early_x[0] + width/2], [early_pred_val], width,
                alpha=0.5, edgecolor='black', linewidth=1.5, color='orange')

ax3.set_xlabel('Output Variable', fontsize=12)
ax3.set_ylabel('Value', fontsize=12)
ax3.set_title('Output: Ground Truth vs Predicted', fontsize=13, fontweight='bold')
ax3.set_xticks(x_pos + early_x)
ax3.set_xticklabels(outcome_labels + ['Early'], rotation=45, ha='right')
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_ylim([0, 1.2])

# Panel 4: Output over time
ax4 = fig.add_subplot(gs[2, :])

# Plot outcome class over time
# True output is scalar (constant), pred varies over time
ax4.axhline(trial_output_true[0], color='blue', linewidth=3,
            linestyle='-', alpha=0.7, label='Outcome (true)')
ax4.plot(time_axis, trial_output_pred[0, :], color='blue', linewidth=3,
         linestyle='--', alpha=0.5, label='Outcome (pred)')

# Plot early lick over time (offset for visibility)
# True output is scalar (constant), pred varies over time
ax4.axhline(trial_output_true[1] + 3, color='orange', linewidth=3,
            linestyle='-', alpha=0.7, label='Early lick (true)')
ax4.plot(time_axis, trial_output_pred[1, :] + 3, color='orange', linewidth=3,
         linestyle='--', alpha=0.5, label='Early lick (pred)')

ax4.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax4.axhline(3, color='gray', linestyle=':', alpha=0.3)

# Add labels for outcome classes
ax4.text(time_axis[0], 0, 'Miss', fontsize=9, va='center')
ax4.text(time_axis[0], 1, 'Ignore', fontsize=9, va='center')
ax4.text(time_axis[0], 2, 'Hit', fontsize=9, va='center')
ax4.text(time_axis[0], 3, 'Not Early', fontsize=9, va='center')
ax4.text(time_axis[0], 4, 'Early', fontsize=9, va='center')

ax4.set_xlabel('Time from go cue (s)', fontsize=12)
ax4.set_ylabel('Output value', fontsize=12)
ax4.set_title('Output Variables Over Time', fontsize=13, fontweight='bold')
ax4.legend(loc='upper right', fontsize=9)
ax4.grid(True, alpha=0.3)
ax4.set_ylim([-0.5, 4.5])
ax4.set_yticks([0, 1, 2, 3, 4])
ax4.set_yticklabels(['Miss', 'Ignore', 'Hit', 'Not Early', 'Early'])

# Add summary text
outcome_str = outcome_labels[outcome_true_val]
predicted_str = outcome_labels[outcome_pred_val]
correct_str = "✓ Correct" if outcome_str == predicted_str else "✗ Incorrect"

fig.suptitle(f'Trial {trial_idx} - True: {outcome_str}, Predicted: {predicted_str} {correct_str}',
             fontsize=16, fontweight='bold', y=0.995)

plt.savefig('single_trial_visualization.png', dpi=150, bbox_inches='tight')
print("\nSaved plot: single_trial_visualization.png")
plt.show()

# %% [markdown]
# ## Visualize Results

# %%
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Accuracy scores
ax = axes[0, 0]
output_var_labels = ['Outcome\n(3-class)', 'Early Lick\n(binary)', 'Action\n(3-class)']
x = np.arange(len(output_var_labels))
bars = ax.bar(x, scores_cv, alpha=0.8, edgecolor='black')

# Color bars by performance
colors = ['green' if acc > 0.5 else 'orange' if acc > 0.3 else 'red' for acc in scores_cv]
for bar, color in zip(bars, colors):
    bar.set_color(color)

ax.set_xlabel('Output Variable')
ax.set_ylabel('Accuracy')
ax.set_title('Cross-Validation Accuracy Scores')
ax.set_xticks(x)
ax.set_xticklabels(output_var_labels, rotation=0)
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim([0, 1])
ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='0.5 threshold')
ax.legend()

# Plot 2: Confusion matrix for outcome (miss/ignore/hit)
ax = axes[0, 1]

from sklearn.metrics import confusion_matrix
cm = confusion_matrix(outcome_true, outcome_pred)

im = ax.imshow(cm, cmap='Blues')
ax.set_xlabel('Predicted')
ax.set_ylabel('True')
ax.set_title('Confusion Matrix (Outcome)')
ax.set_xticks(np.arange(3))
ax.set_yticks(np.arange(3))
ax.set_xticklabels(['Miss', 'Ignore', 'Hit'])
ax.set_yticklabels(['Miss', 'Ignore', 'Hit'])

# Add text annotations
for i in range(3):
    for j in range(3):
        text = ax.text(j, i, cm[i, j],
                      ha="center", va="center", color="black" if cm[i, j] < cm.max()/2 else "white")

plt.colorbar(im, ax=ax, label='Count')

# Plot 3: Example predictions across time for a few trials
ax = axes[1, 0]

time_axis = np.arange(neural[0][0].shape[1]) * data['metadata']['bin_width'] + \
            data['metadata']['time_window'][0]

# Show predictions for first 3 hit trials
hit_trial_indices = np.where(outcome_true == 2)[0][:3]  # outcome 2 = hit

for i, trial_idx in enumerate(hit_trial_indices):
    # Get outcome predictions over time
    pred = predictions_cv[subject_idx][trial_idx][0, :]  # outcome class predictions
    ax.plot(time_axis, pred + i*3.5, label=f'Trial {trial_idx}', alpha=0.7, linewidth=2)

ax.axvline(0, color='red', linestyle='--', alpha=0.5, linewidth=2, label='Go cue')
ax.set_xlabel('Time from go cue (s)')
ax.set_ylabel('Predicted Outcome Class (offset for visibility)')
ax.set_title('Example Predictions Across Time (Hit Trials)')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_yticks([0, 1, 2])
ax.set_yticklabels(['Miss', 'Ignore', 'Hit'])

# Plot 4: Count of outcomes by instruction direction
ax = axes[1, 1]

inputs_array = np.array(data['input'][subject_idx])  # (n_trials, 3)
instructions = inputs_array[:, 0]  # 0=left, 1=right

# Count outcomes by instruction (outcome: 0=miss, 1=ignore, 2=hit)
left_miss = ((instructions == 0) & (outcome_true == 0)).sum()
left_ignore = ((instructions == 0) & (outcome_true == 1)).sum()
left_hit = ((instructions == 0) & (outcome_true == 2)).sum()

right_miss = ((instructions == 1) & (outcome_true == 0)).sum()
right_ignore = ((instructions == 1) & (outcome_true == 1)).sum()
right_hit = ((instructions == 1) & (outcome_true == 2)).sum()

x = np.arange(2)
width = 0.25

ax.bar(x - width, [left_miss, right_miss], width, label='Miss', alpha=0.8, color='red')
ax.bar(x, [left_ignore, right_ignore], width, label='Ignore', alpha=0.8, color='gray')
ax.bar(x + width, [left_hit, right_hit], width, label='Hit', alpha=0.8, color='green')

ax.set_xlabel('Instruction Direction')
ax.set_ylabel('Number of Trials')
ax.set_title('Trial Outcomes by Instruction')
ax.set_xticks(x)
ax.set_xticklabels(['Left', 'Right'])
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('decoder_results.png', dpi=150)
print("\nSaved plot: decoder_results.png")
plt.show()

# %% [markdown]
# ## Examine Principal Components
#
# Look at the learned projections (PCs) for a few trials

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: PCs for a single trial
ax = axes[0]
trial_idx = 0
pcs_trial = pcs_cv[subject_idx][trial_idx]  # (npcs, T)

for pc_idx in range(min(5, pcs_trial.shape[0])):
    ax.plot(time_axis, pcs_trial[pc_idx, :], label=f'PC {pc_idx+1}', alpha=0.7)

ax.axvline(0, color='red', linestyle='--', alpha=0.5, label='Go cue')
ax.set_xlabel('Time from go cue (s)')
ax.set_ylabel('PC Value')
ax.set_title(f'Principal Components - Trial {trial_idx}')
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 2: Average PC across different outcome classes
ax = axes[1]

hit_trials_idx = np.where(outcome_true == 2)[0]  # outcome class 2 = hit
miss_trials_idx = np.where(outcome_true == 0)[0]  # outcome class 0 = miss
ignore_trials_idx = np.where(outcome_true == 1)[0]  # outcome class 1 = ignore

if len(hit_trials_idx) > 0 and len(miss_trials_idx) > 0:
    # Average first PC across outcome classes
    pc1_hit = np.mean([pcs_cv[subject_idx][i][0, :] for i in hit_trials_idx], axis=0)
    pc1_miss = np.mean([pcs_cv[subject_idx][i][0, :] for i in miss_trials_idx], axis=0)

    ax.plot(time_axis, pc1_hit, label='Hit trials', linewidth=2, alpha=0.8, color='green')
    ax.plot(time_axis, pc1_miss, label='Miss trials', linewidth=2, alpha=0.8, color='red')

    if len(ignore_trials_idx) > 0:
        pc1_ignore = np.mean([pcs_cv[subject_idx][i][0, :] for i in ignore_trials_idx], axis=0)
        ax.plot(time_axis, pc1_ignore, label='Ignore trials', linewidth=2, alpha=0.8, color='gray')

    ax.axvline(0, color='black', linestyle='--', alpha=0.5, linewidth=2)
    ax.text(0, ax.get_ylim()[1]*0.95, 'Go cue', ha='center', fontsize=10)
    ax.set_xlabel('Time from go cue (s)')
    ax.set_ylabel('PC1 Value')
    ax.set_title('First Principal Component by Outcome')
    ax.legend()
    ax.grid(True, alpha=0.3)
else:
    ax.text(0.5, 0.5, 'Not enough trials for comparison',
            ha='center', va='center', transform=ax.transAxes)

plt.tight_layout()
plt.savefig('decoder_pcs.png', dpi=150)
print("Saved plot: decoder_pcs.png")
plt.show()

# %% [markdown]
# ## Summary
#
# This notebook demonstrated:
# 1. Loading and preparing MAP dataset for decoder training
# 2. Using the joint linear decoder with cross-validation
# 3. Evaluating performance with F1 scores
# 4. Visualizing results including:
#    - F1 scores by output variable
#    - Confusion matrix for outcomes
#    - Example predictions over time
#    - Trial outcome distributions
#    - Learned principal components
#
# The decoder predicts trial outcomes (hit/miss/ignore/early_lick) from neural activity and task inputs.

# %% [markdown]
# ## Next Steps
#
# Potential improvements and analyses:
# - Decode from specific time windows (e.g., delay period only)
# - Try different numbers of PCs (npcs parameter)
# - Adjust training hyperparameters (epochs, learning rate, batch size)
# - Decode stimulus direction instead of outcome
# - Analyze which time periods contribute most to decoding
# - Compare performance across different brain regions
# - Use only neural data (remove task inputs) to see how much is neural-driven

# %%
