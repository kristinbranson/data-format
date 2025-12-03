
# Setup
import numpy as np
import matplotlib.pyplot as plt
import sys

from decoder import (
    train_decoder,
    predict,
    cross_validate_decoder,
    accuracy_all_mice,
    print_data_summary,
    plot_trial,
    random_sample_trials,
    verify_data_format
)

# Set random seed for reproducibility
np.random.seed(0)

nneurons_sample = 50
input_names = None
output_names = None
train_params = {
    'npcs': 10,
    'lr': 1e-3,
    'l1_weight': 1e-4
}

#### ADD CODE HERE ####
# import load_data function specific to your data format
from convert_data import load_data

# Define variable names for plotting
input_names = ['Time (s)', 'Environment', 'Trial #', 'Prev Reward']
output_names = ['Dist to Reward', 'Abs Position', 'Speed', 'Lick', 'Reward Zone', 'Reward Outcome']
#######################

# path to data file is the first argument
if len(sys.argv) < 2:
    print("Usage: python train_decoder.py <data_file_path>")
    sys.exit(1)
    
data_file_path = sys.argv[1]
    
# load data
data = load_data(data_file_path)

# check that the formatting is valid
valid, errors, warnings = verify_data_format(data, verbose=False)
if not valid:
    print("Data format is invalid. Errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
if warnings:
    print("Data format warnings:")
    for warning in warnings:
        print(f"  - {warning}")
        
assert valid, "Data format is invalid. See errors above."

# print summary of data
print_data_summary(data)

# plot sample trials
nplot = 4 # maximum number of trials to plot
mouseplot,trialplot = random_sample_trials(data,nplot)
fig,ax = plt.subplots(3,nplot,figsize=(30,15),sharex='col')
for i in range(nplot):
    plot_trial(data,mouse=mouseplot[i],trial=trialplot[i],ax=ax[:,i],
                input_names=input_names,output_names=output_names,
                nneurons_sample=nneurons_sample)
    if i > 0:
        ax[1,i].set_yticklabels([])
        ax[2,i].set_yticklabels([])

fig.suptitle('Sample Trials from Dataset')
fig.tight_layout()
fig.savefig('sample_trials.png', dpi=150)

# train decoder on all the data -- overfit
model_all = train_decoder(data['neural'], data['input'], data['output'], **train_params)
predictions_all, pcs_all, confidence_all = predict(data['neural'], data['input'], model_all)

# evaluate overfit model
scores_all = accuracy_all_mice(predictions_all, data['output'])
# print accuracy scores
print("\nOverfitting Check - Accuracy on Training Data:")
for out_dim in range(len(scores_all)):
    print(f"  {out_dim}: {scores_all[out_dim]:.4f}")

# plot results for overfit model
mouseplot,trialplot = random_sample_trials(data,nplot)
fig,ax = plt.subplots(3,nplot,figsize=(30,15),sharex='col')
for i in range(nplot):
    plot_trial(data,mouse=mouseplot[i],trial=trialplot[i],ax=ax[:,i],
                input_names=input_names,output_names=output_names,
                nneurons_sample=nneurons_sample,
                predictions=predictions_all)
    if i > 0:
        ax[1,i].set_yticklabels([])
        ax[2,i].set_yticklabels([])

fig.suptitle('Training Data Predictions (Overfitting Check)')

fig.tight_layout()
fig.savefig('overfitting_check.png', dpi=150)

# train with cross validation
scores_cv, predictions_cv, pcs_cv, confidence_cv, trial_splits = \
    cross_validate_decoder(
        data['neural'],
        data['input'],
        data['output'],
        **train_params
    )

print("\nCross-Validation Accuracy Scores:")
for out_dim in range(len(scores_cv)):
    print(f"  {out_dim}: {scores_cv[out_dim]:.4f}")

# plot results for cross-validated model, same trials
fig,ax = plt.subplots(3,nplot,figsize=(30,15),sharex='col')
for i in range(nplot):
    plot_trial(data,mouse=mouseplot[i],trial=trialplot[i],ax=ax[:,i],
                input_names=input_names,output_names=output_names,
                nneurons_sample=nneurons_sample,
                predictions=predictions_cv)
    if i > 0:
        ax[1,i].set_yticklabels([])
        ax[2,i].set_yticklabels([])
fig.suptitle('Cross-Validated Predictions')
fig.tight_layout()
fig.savefig('cross_validated_predictions.png', dpi=150)

