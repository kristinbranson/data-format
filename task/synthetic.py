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
#     display_name: decoder-data-format
#     language: python
#     name: python3
# ---

# %%
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

import tqdm

# %%
nmice = 10
dinput = 2
doutput = 3
npcs = 10
data = {'neural': [], 'input': [], 'output': [], 'pc': []}
gt = {'decoder_neural': [], 'decoder_pca': [], 'decoder_input': []}
sigma_neural = .1

decoder_pca = np.random.randn(doutput,npcs)
gt['decoder_pca'] = decoder_pca

def linear(coeff,x):
    if coeff.shape[1] == x.shape[0]:
        return np.dot(coeff,x)
    assert coeff.shape[1] == x.shape[0] + 1
    return np.dot(coeff[:,1:],x) + coeff[:,0][:,None]

for mouse in range(nmice):
    ntrials = np.random.randint(48,52)
    nneurons = np.random.randint(90,110)
    rate_per_input = np.random.randint(5,15,(nneurons,dinput))
    decoder_input = np.random.randn(doutput,dinput+1)
    neuralmouse = []
    outputmouse = []
    inputmouse = []
    for trial in range(ntrials):
        T = np.random.randint(900,1100)

        inputidx = np.random.randint(0,dinput-1)
        inputtrial = np.zeros((dinput,T),dtype=bool)
        inputtrial[inputidx,:] = True

        neuraltrial = np.zeros((nneurons,T),dtype=object)
        for neuron in range(nneurons):
            rate = rate_per_input[neuron,inputidx]
            spikes = np.random.poisson(rate,(T,))
            neuraltrial[neuron,:] = spikes

        inputmouse.append(inputtrial)
        neuralmouse.append(neuraltrial)
        
    # do pca on all data from this mouse
    allneural = np.hstack(neuralmouse)
    pca = PCA(n_components=npcs)
    pca.fit(allneural.T)
    pcsmouse = [pca.transform(neuraltrial.T).T for neuraltrial in neuralmouse]
    gt['decoder_neural'].append(pca)
        
    for trial in range(ntrials):
        inputtrial = inputmouse[trial]
        outputtrial = linear(decoder_pca,pcsmouse[trial]) + linear(decoder_input[:,1:],inputtrial)
        outputmouse.append(outputtrial)

    mu = np.mean([np.mean(outputtrial,axis=1) for outputtrial in outputmouse],axis=0)
    decoder_input[:,0] = -mu.flatten()
    outputmouse = [outputtrial > mu[:,None] for outputtrial in outputmouse]
    data['neural'].append(neuralmouse)
    data['input'].append(inputmouse)
    data['output'].append(outputmouse)
    data['pc'].append(pcsmouse)
    gt['decoder_input'].append(decoder_input)

# %%
import matplotlib.pyplot as plt

fig,ax = plt.subplots(4,1,figsize = (30,20),sharex=True)

mouse = 0
trial = 0

# neural
for neuron in range(data['neural'][mouse][trial].shape[0]):
    maxv = np.percentile(data['neural'][mouse][trial][neuron,:],99)
    ax[0].plot(data['neural'][mouse][trial][neuron,:]/maxv+neuron)
ax[0].set_ylim((0,10))
ax[0].set_ylabel('Neural')

# from neural to pc
pc = gt['decoder_neural'][mouse].transform(data['neural'][mouse][trial].T).T
for pcidx in range(npcs):
    maxv = np.percentile(pc[pcidx],99)
    ax[1].plot(pc[pcidx]/maxv+pcidx)
ax[1].set_ylabel('PCs')

for outdim in range(doutput):
    ax[2].plot(data['output'][mouse][trial][outdim,:]*.9+.05+outdim)
    ax[2].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'k--')
ax[2].set_ylabel('Output')
    
decoded = linear(gt['decoder_pca'],pc) + linear(gt['decoder_input'][mouse],data['input'][mouse][trial])
for outdim in range(doutput):
    maxv = np.percentile(decoded[outdim],99)
    minv = np.percentile(decoded[outdim],1)
    ax[3].plot((decoded[outdim] - minv)/(maxv - minv)*.9+.05+outdim)
    ax[3].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'k--')
ax[3].set_ylabel('Decoded')
    
ax[0].set_xlim([0,50])


# %%
def train_decoder(neural: list, input: list, output: list, metadata: dict = {}, **kwargs):
    """
    Trains a common decoder for all mice to predict output from neural and input data.
    Concatenates data across trials for each mouse, then projects the neural data for each mouse onto its first npcs principal components.
    Then, concatenates data across all mice and trains a common decoder across all mice using logistic regression to predict output from the
    projected neural data and input data.

    Inputs:
        neural: neural activity. neural is a list of length nmice, neural[mouse] is a list
                of length ntrials[mouse], and neural[mouse][trial] is a numpy array of shape (nneurons[mouse], T[mouse][trial]),
                dtype = float32, giving the neural activity for that trial
        input: variables beyond neural activity the decoder should input, e.g. the stimulis, condition. input is a list of
                length nmice, input[mouse] is a list of length ntrials[mouse], and input[mouse][trial] is a numpy array of
                shape (dinput, T[mouse][trial]), dtype = float32. with the input variable(s) for each timepoint.
                dinput is the number of inputs. For discrete inputs, use a one-hot encoding.
        output: variables we want to decode. output is a list of length nmice, output[mouse] is a list of length ntrials[mouse],
                and output[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = bool with the
                binary output variable(s) for each timepoint. Use a one-hot encoding for multi-class outputs.
        metadata: optional dict with additional information about the experiment.

        Algorithm hyperparameters can be passed as keyword arguments:
        npcs: number of principal components to use (default: 10)

    Returns:
        model: dict with trained decoder parameters. dict with the keys:
            'pca': list of length nmice, pca[mouse] is a PCA object fitted to the neural data of that mouse
            'logisticregression': list of length doutput, logisticregression[out_dim] is a sklearn LogisticRegression model

    """

    model = {
        'pca': [],
        'logisticregression': []
    }

    npcs = kwargs.get('npcs', 10)
    nmice = len(neural)

    # Store projected neural data and inputs/outputs for all mice
    all_projected_neural = []
    all_input = []
    all_output = []

    # Process each mouse separately
    for mouse in range(nmice):
        # Concatenate across trials for this mouse
        # neural[mouse][trial] is (nneurons, T), we want (T_total, nneurons)
        neural_concat = np.concatenate([neural[mouse][trial].T for trial in range(len(neural[mouse]))], axis=0).astype(np.float32)
        input_concat = np.concatenate([input[mouse][trial].T for trial in range(len(input[mouse]))], axis=0).astype(np.float32)
        output_concat = np.concatenate([output[mouse][trial].T for trial in range(len(output[mouse]))], axis=0).astype(bool)

        # Project neural data onto first npcs principal components
        pca = PCA(n_components=min(npcs, neural_concat.shape[1]))
        model['pca'].append(pca)
        
        neural_projected = pca.fit_transform(neural_concat)

        # Store for later concatenation
        all_projected_neural.append(neural_projected)
        all_input.append(input_concat)
        all_output.append(output_concat)

    # Concatenate across all mice
    X_neural = np.vstack(all_projected_neural)
    X_input = np.vstack(all_input)
    X = np.hstack([X_neural, X_input])
    y = np.vstack(all_output)

    # Train logistic regression for each output dimension
    for out_dim in range(y.shape[1]):
        lr = LogisticRegression(max_iter=1000)
        lr.fit(X, y[:, out_dim])
        model['logisticregression'].append(lr)

    return model

def predict(neural: list, input: list, model: dict, mouseid: list | None = None, metadata: dict = {}):
    """
    Uses a trained decoder model to predict output from neural and input data.

    Inputs:
        neural: neural activity. neural is a list of length nmice, neural[mouse] is a list
                of length ntrials[mouse], and neural[mouse][trial] is a numpy array of shape (nneurons[mouse], T[mouse][trial]),
                dtype = float32, giving the neural activity for that trial
        input: variables beyond neural activity the decoder should input, e.g. the stimulis, condition. input is a list of
                length nmice, input[mouse] is a list of length ntrials[mouse], and input[mouse][trial] is a numpy array of
                shape (dinput, T[mouse][trial]), dtype = float32. with the input variable(s) for each timepoint.
                dinput is the number of inputs. For discrete inputs, use a one-hot encoding.
        model: dict with trained decoder parameters. dict with the keys:
                'pca': list of length nmice, pca[mouse] is a PCA object fitted to the neural data of that mouse
                'logisticregression': list of length doutput, logisticregression[out_dim] is a sklearn LogisticRegression model
        mouseid: optional list of length nmice, giving the IDs of the mice. 
        metadata: optional dict with additional information about the experiment.
    Returns:
        predictions: list of length nmice, predictions[mouse] is a list of length ntrials[mouse],
                and predictions[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = bool
                with the predicted output variable(s) for each timepoint.
    """

    nmice = len(neural)
    doutput = len(model['logisticregression'])

    # Store projected neural data and inputs for all mice, and trial lengths
    all_projected_neural = []
    all_input = []
    trial_lengths = []  # To track where each mouse's trials are in the concatenated data

    # Process each mouse separately
    for mouseidx in range(nmice):
        if mouseid is not None:
            mouse = mouseid[mouseidx]
        else:
            mouse = mouseidx
        ntrials = len(neural[mouse])
        mouse_trial_lengths = []

        # Concatenate across trials for this mouse
        neural_concat = np.concatenate([neural[mouseidx][trial].T for trial in range(ntrials)], axis=0).astype(np.float32)
        input_concat = np.concatenate([input[mouseidx][trial].T for trial in range(ntrials)], axis=0).astype(np.float32)

        # Store trial lengths for this mouse
        for trial in range(ntrials):
            mouse_trial_lengths.append(neural[mouseidx][trial].shape[1])
        trial_lengths.append(mouse_trial_lengths)

        # Project neural data using the fitted PCA for this mouse
        pca = model['pca'][mouse]
        neural_projected = pca.transform(neural_concat)

        # Store for later concatenation
        all_projected_neural.append(neural_projected)
        all_input.append(input_concat)

    # store mouse pcs
    pcs = []
    for mouseidx in range(nmice):
        mousepcs = []
        idx = 0
        for trial in range(len(neural[mouseidx])):
            mousepcs.append(all_projected_neural[mouseidx][idx:idx+trial_lengths[mouseidx][trial], :].T)
            idx += trial_lengths[mouseidx][trial]
        pcs.append(mousepcs)

    # Concatenate across all mice
    X_neural = np.vstack(all_projected_neural)
    X_input = np.vstack(all_input)
    X = np.hstack([X_neural, X_input])

    # Predict for each output dimension
    y_pred = np.zeros((X.shape[0], doutput), dtype=bool)
    for out_dim in range(doutput):
        lr = model['logisticregression'][out_dim]
        y_pred[:, out_dim] = lr.predict(X)

    # Reshape predictions back to the original structure (per mouse, per trial)
    predictions = []
    idx = 0
    for mouseidx in range(nmice):
        mouse_predictions = []
        for trial_length in trial_lengths[mouseidx]:
            # Extract predictions for this trial and transpose to (doutput, T)
            trial_pred = y_pred[idx:idx+trial_length, :].T
            mouse_predictions.append(trial_pred)
            idx += trial_length
        predictions.append(mouse_predictions)
    return predictions, pcs


# %%
model_all = train_decoder(data['neural'], data['input'], data['output'], npcs=npcs)
predicted_outputs, predicted_pcs = predict(data['neural'], data['input'], model_all)

# %%
mouse = 0
trial = 0

def debug_plot(data,gt,predicted_outputs,predicted_pcs,mouse,trial):

    fig,ax = plt.subplots(2,1,figsize = (30,20),sharex=True)
    for pcidx in range(npcs):
        maxv = np.percentile(data['pc'][mouse][trial][pcidx],99)
        minv = np.percentile(data['pc'][mouse][trial][pcidx],1)
        ax[0].plot([0,data['pc'][mouse][trial].shape[1]],[.5+pcidx,.5+pcidx],'--',color=[.7,.7,.7])
        ax[0].plot((predicted_pcs[mouse][trial][pcidx] - minv)/(maxv - minv)*.9+.05+pcidx)
        ax[0].plot((data['pc'][mouse][trial][pcidx] - minv)/(maxv - minv)*.9+.05+pcidx,'k--')
    ax[0].set_ylabel('PCs')

    for outdim in range(doutput):
        ax[1].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'--',color = [.7,.7,.7])
        ax[1].plot(predicted_outputs[mouse][trial][outdim,:]*.9+.05+outdim,'o-')
        ax[1].plot(data['output'][mouse][trial][outdim,:]*.9+.05+outdim,'k.--')
    ax[1].set_ylabel('Output')
    
    return fig, ax

fig,ax = debug_plot(data,gt,predicted_outputs,predicted_pcs,mouse,trial)
ax[0].set_xlim([0,200])


# %%
def cross_validate_decoder(neural: list, input: list, output: list, metadata: str | None = None, nsets: int = 5, **kwargs):
    """
    Cross-validates the decoder function. Performs nsets-fold cross-validation, training the decoder on nsets-1 sets and testing on
    the held-out set. Each cross-validation set contains 1/nsets of the trials from each mouse.
    Finds a random split of trials for each mouse into nsets sets, then, for each set, trains the decoder on the other nsets-1 sets and
    computes the predictions on the held out set.
    Then computes the F1 score for each output dimension
    Inputs:
        neural: neural activity. neural is a list of length nmice, neural[mouse] is a list
                of length ntrials[mouse], and neural[mouse][trial] is a numpy array of shape (nneurons[mouse], T[mouse][trial]),
                dtype = float32, giving the neural activity for that trial
        input: variables beyond neural activity the decoder should input, e.g. the stimulis, condition. input is a list of
                length nmice, input[mouse] is a list of length ntrials[mouse], and input[mouse][trial] is a numpy array of
                shape (dinput, T[mouse][trial]), dtype = float32. with the input variable(s) for each timepoint.
                dinput is the number of inputs. For discrete inputs, use a one-hot encoding.
        output: the ground truth output for each trial. output is a list of length nmice, output[mouse] is a list of
                length ntrials[mouse], and output[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]),
                dtype = float32. with the output variable(s) for each timepoint.
        metadata: optional dict with additional information about the experiment.
        nsets: number of cross-validation sets (default: 5)
    kwargs are passed to train_decoder
    Returns:
        f1scores: numpy array of shape (doutput,) with the F1 score for each output dimension
        predictions: list of length nmice, predictions[mouse] is a list of length ntrials[mouse],
                and predictions[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = bool
                with the predicted output variable(s) for each timepoint.
        trial_splits: list of length nmice, trial_splits[mouse] is a list of length nsets,
                trial_splits[mouse][set] is a numpy array with the trial indices for that set for that mouse.
    """

    nmice = len(neural)

    # Determine doutput from the first mouse's first trial
    doutput = output[0][0].shape[0]

    # Create random splits of trials for each mouse
    trial_splits = []
    for mouse in range(nmice):
        ntrials = len(neural[mouse])
        trial_indices = np.random.permutation(ntrials)

        # Split trial indices into nsets
        split_indices = np.array_split(trial_indices, nsets)
        trial_splits.append(split_indices)

    # Initialize storage for all predictions (will be filled in during cross-validation)
    all_predictions = [[None for _ in range(len(neural[mouse]))] for mouse in range(nmice)]
    all_pcs = [[None for _ in range(len(neural[mouse]))] for mouse in range(nmice)]

    # Perform cross-validation
    for test_set in tqdm.trange(nsets):
        # Create training and test data for this fold
        train_neural = [[] for _ in range(nmice)]
        train_input = [[] for _ in range(nmice)]
        train_output = [[] for _ in range(nmice)]

        test_neural = [[] for _ in range(nmice)]
        test_input = [[] for _ in range(nmice)]
        test_output = [[] for _ in range(nmice)]

        test_trial_indices = [[] for _ in range(nmice)]

        for mouse in range(nmice):
            for set_idx in range(nsets):
                trials_in_set = trial_splits[mouse][set_idx]

                if set_idx == test_set:
                    # These trials go to test set
                    for trial_idx in trials_in_set:
                        test_neural[mouse].append(neural[mouse][trial_idx])
                        test_input[mouse].append(input[mouse][trial_idx])
                        test_output[mouse].append(output[mouse][trial_idx])
                        test_trial_indices[mouse].append(trial_idx)
                else:
                    # These trials go to training set
                    for trial_idx in trials_in_set:
                        train_neural[mouse].append(neural[mouse][trial_idx])
                        train_input[mouse].append(input[mouse][trial_idx])
                        train_output[mouse].append(output[mouse][trial_idx])

        # Train decoder on training data
        model = train_decoder(train_neural, train_input, train_output, metadata={}, **kwargs)

        # Predict on test data
        test_predictions, test_pc = predict(test_neural, test_input, model)

        # Store predictions in the correct positions
        for mouse in range(nmice):
            for idx, trial_idx in enumerate(test_trial_indices[mouse]):
                all_predictions[mouse][trial_idx] = test_predictions[mouse][idx]
                all_pcs[mouse][trial_idx] = test_pc[mouse][idx]
                
    # Concatenate all predictions and ground truth to compute F1 scores
    all_pred_concat = []
    all_output_concat = []

    for mouse in range(nmice):
        for trial in range(len(neural[mouse])):
            # Flatten predictions and outputs across time: (doutput, T) -> (T, doutput)
            all_pred_concat.append(all_predictions[mouse][trial].T)
            all_output_concat.append(output[mouse][trial].T)

    # Concatenate all timepoints from all trials and all mice
    all_pred_concat = np.vstack(all_pred_concat)  # (total_timepoints, doutput)
    all_output_concat = np.vstack(all_output_concat)  # (total_timepoints, doutput)

    # Compute F1 score for each output dimension
    f1scores = np.zeros(doutput)
    for out_dim in range(doutput):
        f1scores[out_dim] = f1_score(all_output_concat[:, out_dim], all_pred_concat[:, out_dim])

    return f1scores, all_predictions, all_pcs, trial_splits


# %%
f1scores, cv_predictions, cv_pcs, trial_splits = cross_validate_decoder(data['neural'], data['input'], data['output'], nsets=5, npcs=npcs, debug=True)

# %%
fig, ax = debug_plot(data,gt,cv_predictions,cv_pcs,0,0)
ax[0].set_xlim([0,200])
print("F1 scores:", f1scores)

