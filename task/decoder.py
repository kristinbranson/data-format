# code for training decoders from mouse neural activity data
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

import tqdm

import torch
import torch.nn as nn
import torch.optim as optim

import matplotlib.pyplot as plt

def get_dim(x: list):
    """
    Get the 0th dimension from the data.
    Inputs:
        x: list of length nmice, x[mouse] is a list of length ntrials[mouse], and x[mouse][trial] is a numpy array of shape (d, T)
    Returns:
        d: int, dimension
    """
    ntrials_per_mouse = [len(x[mouse]) for mouse in range(len(x))]
    mouse = np.nonzero(ntrials_per_mouse)[0][0]
    d = x[mouse][0].shape[0]
    return d

def get_range(x: list):
    """
    Get the range of values across all mice and trials.
    Inputs:
        x: list of length nmice, x[mouse] is a list of length ntrials[mouse], and x[mouse][trial] is a numpy array of shape (d, T)
    Returns:
        min_x: numpy array of shape (dinput,), minimum input values
        max_x: numpy array of shape (dinput,), maximum input values
    """

    d = get_dim(x)
    min_x = np.zeros(d) + np.inf
    max_x = np.zeros(d) - np.inf
    for mouse in range(len(x)):
        for trial in range(len(x[mouse])):
            input_trial = x[mouse][trial]
            if np.ndim(input_trial) == 1:
                min_x = np.minimum(min_x, input_trial)
                max_x = np.maximum(max_x, input_trial)
            else:
                min_x = np.minimum(min_x, input_trial.min(axis=1))
                max_x = np.maximum(max_x, input_trial.max(axis=1))
    return min_x, max_x

def print_data_summary(data: dict):
    """Prints a summary of the data structure."""
    
    nmice = len(data['neural'])
    print(f"Number of mice: {nmice}")
    ntrials_per_mouse = [len(data['neural'][mouse]) for mouse in range(nmice)]
    print(f"Total number of trials: {sum(ntrials_per_mouse)}")
    print(f"Number of trials per mouse: {ntrials_per_mouse}")
    
    # find first non-empty trial to get input/output dimensions
    mouse = np.nonzero(ntrials_per_mouse)[0][0]
    dinput = data['input'][mouse][0].shape[0]
    doutput = data['output'][mouse][0].shape[0]    
    print(f"Input dimension: {dinput}")
    print(f"Output dimension: {doutput}")
    
    mean_T = []
    mean_nneurons = []
    min_T = []
    max_T = []
    min_nneurons = []
    max_nneurons = []
    input_range = []
    output_range = []
    unique_outputs = [set() for _ in range(doutput)]
    for mouse in range(nmice):
        ntrials = len(data['neural'][mouse])
        Ts = [data['neural'][mouse][trial].shape[1] for trial in range(ntrials)]
        nneurons = [data['neural'][mouse][trial].shape[0] for trial in range(ntrials)]
        mean_T.append(np.mean(Ts))
        mean_nneurons.append(np.mean(nneurons))
        min_T.append(np.min(Ts))
        max_T.append(np.max(Ts))
        min_nneurons.append(np.min(nneurons))
        max_nneurons.append(np.max(nneurons))
        if np.ndim(data['input'][mouse][0]) == 1:
            input_range.append((np.min([data['input'][mouse][trial] for trial in range(ntrials)],axis=0),
                                np.max([data['input'][mouse][trial] for trial in range(ntrials)],axis=0)))
        else:
            input_range.append((np.min([data['input'][mouse][trial].min(axis=1) for trial in range(ntrials)],axis=0),
                                np.max([data['input'][mouse][trial].max(axis=1) for trial in range(ntrials)],axis=0)))
        if np.ndim(data['output'][mouse][0]) == 1:
            output_range.append((np.min([data['output'][mouse][trial] for trial in range(ntrials)],axis=0),
                                np.max([data['output'][mouse][trial] for trial in range(ntrials)],axis=0)))
        else:
            output_range.append((np.min([data['output'][mouse][trial].min(axis=1) for trial in range(ntrials)],axis=0),
                                np.max([data['output'][mouse][trial].max(axis=1) for trial in range(ntrials)],axis=0)))
            

        for trial in range(ntrials):
            for i in range(doutput):
                if np.ndim(data['output'][mouse][trial]) == 1:
                    unique_outputs[i].add(data['output'][mouse][trial][i])
                else:
                    unique_outputs[i].update(set(np.unique(data['output'][mouse][trial][i, :])))
                
    print(f"Summary statistics (across all mice):")
    print(f"  T: mean: {np.mean(mean_T):.2f}, min: {np.min(min_T)}, max: {np.max(max_T)}")
    print(f"  n_neurons: mean: {np.mean(mean_nneurons):.2f}, min: {np.min(min_nneurons)}, max: {np.max(max_nneurons)}")
    input_range_all = (np.min([r[0] for r in input_range],axis=0), np.max([r[1] for r in input_range],axis=0))
    output_range_all = (np.min([r[0] for r in output_range],axis=0), np.max([r[1] for r in output_range],axis=0))
    print(f"  Input range:")
    for i in range(dinput):
        print(f"    {i}: [{input_range_all[0][i]:.1f}, {input_range_all[1][i]:.1f}]")
    print(f"  Output range:")
    for i in range(doutput):
        print(f"    {i}: [{output_range_all[0][i]:.1f}, {output_range_all[1][i]:.1f}]")
    print(f"  Unique outputs per dimension:")
    for i in range(doutput):
        print(f"    {i}: {{{', '.join(f'{x:.1f}' for x in unique_outputs[i])}}}")
    print(f"\nPer-mouse statistics:")
    print(f"  Mean T: " + ", ".join(f"{x:.1f}" for x in mean_T))
    print(f"  Min T: " + ", ".join(f"{x}" for x in min_T))
    print(f"  Max T: " + ", ".join(f"{x}" for x in max_T))
    print(f"  Mean n_neurons: " + ", ".join(f"{x:.1f}" for x in mean_nneurons))
    print(f"  Min n_neurons: " + ", ".join(f"{x}" for x in min_nneurons))
    print(f"  Max n_neurons: " + ", ".join(f"{x}" for x in max_nneurons))
    print(f"  Input range: {input_range}")
    for i in range(dinput):
        print(f"    {i}: [" + ", ".join(f"({r[0][i]:.1f}, {r[1][i]:.1f})" for r in input_range) + "]")
    print(f"  Output range: {output_range}")
    for i in range(doutput):
        print(f"    {i}: [" + ", ".join(f"({r[0][i]:.1f}, {r[1][i]:.1f})" for r in output_range) + "]")

    return

def plot_trial(data: dict, mouse: int = 0, trial: int = 0, ax: list | None = None, 
               input_names: list | None = None, output_names: list | None = None):
    """
    Plot neural, input, and output data for a specific trial of a specific mouse.
    Inputs:
        data: dict with keys 'neural', 'input', 'output' as described in train_decoder.py
        mouse: index of the mouse to plot, default = 0
        trial: index of the trial to plot, default = 0
        ax: optional list of matplotlib axes to plot on. If None, new figure and axes will be created.
    Returns:
        fig: matplotlib figure
        ax: list of matplotlib axes
    """

    if ax is None:
        fig,ax = plt.subplots(3,1,figsize = (30,20),sharex=True)
    else:
        fig = ax[0].figure

    # neural
    for neuron in range(data['neural'][mouse][trial].shape[0]):
        maxv = np.percentile(data['neural'][mouse][trial][neuron,:],99)
        if maxv == 0:
            maxv = 1.0
        ax[0].plot(data['neural'][mouse][trial][neuron,:]/maxv+neuron)
    ax[0].set_ylim((0,10))
    ax[0].set_ylabel('Neural')

    dinput = data['input'][mouse][trial].shape[0]
    T = data['neural'][mouse][trial].shape[1]
    min_input, max_input = get_range(data['input'])
    if np.ndim(data['input'][mouse][trial]) == 1:
        input = np.tile(data['input'][mouse][trial][:, np.newaxis], (1, T))
    else:
        input = data['input'][mouse][trial]
    for indim in range(dinput):
        # Normalize to [0, 1] range for plotting
        normalized = (input[indim]-min_input[indim]) / (max_input[indim] - min_input[indim])
        ax[1].plot(normalized*.9+.05+indim)
        ax[1].plot([0,T],[indim,indim],'k--')
    ax[1].plot([0,T],[dinput,dinput],'k--')
    if input_names is None:
        input_names = [f'In {i}' for i in range(dinput)]
    ax[1].set_yticks(np.arange(dinput)+0.5)
    ax[1].set_yticklabels(input_names)

    doutput = data['output'][mouse][trial].shape[0]
    _, max_output = get_range(data['output'])
    if np.ndim(data['output'][mouse][trial]) == 1:
        output = np.tile(data['output'][mouse][trial][:, np.newaxis], (1, T))
    else:
        output = data['output'][mouse][trial]
    for outdim in range(doutput):
        # Normalize to [0, 1] range for plotting
        normalized = output[outdim] / max_output[outdim]
        ax[2].plot(normalized*.9+.05+outdim)
        ax[2].plot([0,T],[outdim,outdim],'k--')
    ax[2].plot([0,T],[doutput,doutput],'k--')
    if output_names is None:
        output_names = [f'Out {i}' for i in range(doutput)]
    ax[2].set_yticks(np.arange(doutput)+0.5)
    ax[2].set_yticklabels(output_names)
    
    ax[0].set_title(f'Mouse {mouse}, Trial {trial}')

    fig.tight_layout()
    return fig, ax

def train_decoder_pca_logistic(neural: list, input: list, output: list, metadata: dict = {}, **kwargs):
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

    # Replicate 1D inputs/outputs along time axis to match neural data (make copies to avoid modifying original)
    input_processed = []
    output_processed = []
    for mouse in range(nmice):
        input_mouse = []
        output_mouse = []
        for trial in range(len(neural[mouse])):
            T = neural[mouse][trial].shape[1]  # time dimension

            # Handle 1D input - replicate along time
            if input[mouse][trial].ndim == 1:
                input_trial = np.tile(input[mouse][trial][:, np.newaxis], (1, T))
            else:
                input_trial = input[mouse][trial]
            input_mouse.append(input_trial)

            # Handle 1D output - replicate along time
            if output[mouse][trial].ndim == 1:
                output_trial = np.tile(output[mouse][trial][:, np.newaxis], (1, T))
            else:
                output_trial = output[mouse][trial]
            output_mouse.append(output_trial)

        input_processed.append(input_mouse)
        output_processed.append(output_mouse)

    # Use processed data instead of original
    input = input_processed
    output = output_processed

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

def predict_pca_logistic(neural: list, input: list, model: dict, mouseid: list | None = None, metadata: dict = {}):
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

    # Replicate 1D inputs along time axis to match neural data (make copies to avoid modifying original)
    input_processed = []
    for mouse in range(nmice):
        input_mouse = []
        for trial in range(len(neural[mouse])):
            T = neural[mouse][trial].shape[1]  # time dimension

            # Handle 1D input - replicate along time
            if input[mouse][trial].ndim == 1:
                input_trial = np.tile(input[mouse][trial][:, np.newaxis], (1, T))
            else:
                input_trial = input[mouse][trial]
            input_mouse.append(input_trial)
        input_processed.append(input_mouse)

    # Use processed data instead of original
    input = input_processed

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

def train_decoder_linear(neural: list, input: list, output: list, metadata: dict = {}, **kwargs):
    """
    Trains a common decoder for all mice to predict output from neural and input data.
    Jointly learns projection matrices for each mouse and separate shared decoders for each output dimension.

    Inputs:
        neural: neural activity. neural is a list of length nmice, neural[mouse] is a list
                of length ntrials[mouse], and neural[mouse][trial] is a numpy array of shape (nneurons[mouse], T[mouse][trial]),
                dtype = float32, giving the neural activity for that trial
        input: variables beyond neural activity the decoder should input, e.g. the stimulis, condition. input is a list of
                length nmice, input[mouse] is a list of length ntrials[mouse], and input[mouse][trial] is a numpy array of
                shape (dinput, T[mouse][trial]), dtype = float32. with the input variable(s) for each timepoint.
                dinput is the number of inputs. For discrete inputs, use a one-hot encoding.
        output: variables we want to decode. output is a list of length nmice, output[mouse] is a list of length ntrials[mouse],
                and output[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = int with
                categorical values for each timepoint. Each output[idx, t] is an integer from 0 to ncategories[idx]-1.
        metadata: optional dict with additional information about the experiment.

        Algorithm hyperparameters can be passed as keyword arguments:
        npcs: number of projected dimensions to use (default: 10)
        num_epochs: number of training epochs (default: 100)
        lr: learning rate (default: 0.01)
        batch_size: batch size for training (default: 1024)
        ncategories: optional list of length doutput giving number of categories for each output dimension.
                     If not provided, will be inferred from data.

    Returns:
        model: dict with trained decoder parameters. dict with the keys:
            'projection': list of length nmice, projection[mouse] is a torch tensor of shape (npcs, nneurons[mouse])
            'decoder': list of length doutput, decoder[out_dim] is a torch linear layer for that output dimension
            'ncategories': list of length doutput, ncategories[out_dim] is the number of categories for that output
            'device': torch device used for training

    """

    model = {
        'projection': [],
        'decoder': [],
        'ncategories': [],
        'device': None
    }

    npcs = kwargs.get('npcs', 10)
    num_epochs = kwargs.get('num_epochs', 100)
    lr = kwargs.get('lr', 0.01)
    batch_size = kwargs.get('batch_size', 1024)

    nmice = len(neural)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model['device'] = device

    # Determine dimensions (handle both 1D and 2D inputs/outputs)
    if input[0][0].ndim == 1:
        dinput = len(input[0][0])
    else:
        dinput = input[0][0].shape[0]

    if output[0][0].ndim == 1:
        doutput = len(output[0][0])
    else:
        doutput = output[0][0].shape[0]

    # Replicate 1D inputs/outputs along time axis to match neural data (make copies to avoid modifying original)
    input_processed = []
    output_processed = []
    for mouse in range(nmice):
        input_mouse = []
        output_mouse = []
        for trial in range(len(neural[mouse])):
            T = neural[mouse][trial].shape[1]  # time dimension

            # Handle 1D input - replicate along time
            if input[mouse][trial].ndim == 1:
                input_trial = np.tile(input[mouse][trial][:, np.newaxis], (1, T))
            else:
                input_trial = input[mouse][trial]
            input_mouse.append(input_trial)

            # Handle 1D output - replicate along time
            if output[mouse][trial].ndim == 1:
                output_trial = np.tile(output[mouse][trial][:, np.newaxis], (1, T))
            else:
                output_trial = output[mouse][trial]
            output_mouse.append(output_trial)

        input_processed.append(input_mouse)
        output_processed.append(output_mouse)

    # Use processed data instead of original
    input = input_processed
    output = output_processed

    # Determine number of categories for each output dimension
    if 'ncategories' in kwargs:
        ncategories = kwargs['ncategories']
    else:
        ncategories = []
        for out_dim in range(doutput):
            max_cat = 0
            for mouse in range(nmice):
                for trial in range(len(output[mouse])):
                    max_cat = max(max_cat, int(np.max(output[mouse][trial][out_dim, :])))
            ncategories.append(max_cat + 1)

    model['ncategories'] = ncategories

    # Prepare data for each mouse
    mouse_data = []
    for mouse in range(nmice):
        # Concatenate across trials for this mouse
        neural_concat = np.concatenate([neural[mouse][trial].T.astype(np.float32) for trial in range(len(neural[mouse]))], axis=0)
        input_concat = np.concatenate([input[mouse][trial].T for trial in range(len(input[mouse]))], axis=0).astype(np.float32)
        output_concat = np.concatenate([output[mouse][trial].T for trial in range(len(output[mouse]))], axis=0).astype(np.int64)

        mouse_data.append({
            'neural': torch.from_numpy(neural_concat).to(device),
            'input': torch.from_numpy(input_concat).to(device),
            'output': torch.from_numpy(output_concat).to(device),
            'nneurons': neural_concat.shape[1]
        })

    # Initialize projection matrices for each mouse
    projection_layers = []
    for mouse in range(nmice):
        nneurons = mouse_data[mouse]['nneurons']
        proj = nn.Linear(nneurons, npcs, bias=False).to(device)
        # Initialize with SVD for stability
        U, _, _ = torch.svd(mouse_data[mouse]['neural'].T)
        proj.weight.data = U[:npcs, :].clone()
        projection_layers.append(proj)

    # Initialize separate decoders for each output dimension
    decoders = []
    for out_dim in range(doutput):
        decoder = nn.Linear(npcs + dinput, ncategories[out_dim]).to(device)
        decoders.append(decoder)

    # Collect all parameters
    all_params = []
    for proj in projection_layers:
        all_params.extend(proj.parameters())
    for decoder in decoders:
        all_params.extend(decoder.parameters())

    optimizer = optim.Adam(all_params, lr=lr)
    criterion = nn.CrossEntropyLoss()

    # Training loop
    for epoch in range(num_epochs):
        total_loss = 0

        for mouse in range(nmice):
            n_samples = mouse_data[mouse]['neural'].shape[0]
            indices = torch.randperm(n_samples)

            for i in range(0, n_samples, batch_size):
                batch_indices = indices[i:min(i+batch_size, n_samples)]

                # Get batch data
                neural_batch = mouse_data[mouse]['neural'][batch_indices]
                input_batch = mouse_data[mouse]['input'][batch_indices]
                output_batch = mouse_data[mouse]['output'][batch_indices]

                # Forward pass - shared projection
                projected = projection_layers[mouse](neural_batch)
                combined = torch.cat([projected, input_batch], dim=1)

                # Compute loss for each output dimension
                loss = 0
                for out_dim in range(doutput):
                    logits = decoders[out_dim](combined)
                    loss += criterion(logits, output_batch[:, out_dim])

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

        if (epoch + 1) % 20 == 0:
            print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {total_loss:.4f}')

    # Store trained parameters
    for mouse in range(nmice):
        model['projection'].append(projection_layers[mouse].weight.data.clone())
    model['decoder'] = decoders

    return model

def predict_linear(neural: list, input: list, model: dict, mouseid: list | None = None, metadata: dict = {}):
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
                'projection': list of length nmice, projection[mouse] is a torch tensor
                'decoder': list of length doutput, decoder[out_dim] is a torch linear layer for that output dimension
                'ncategories': list of length doutput with number of categories per output dimension
                'device': torch device
        mouseid: optional list of length nmice, giving the IDs of the mice.
        metadata: optional dict with additional information about the experiment.
    Returns:
        predictions: list of length nmice, predictions[mouse] is a list of length ntrials[mouse],
                and predictions[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = int
                with the predicted categorical output variable(s) for each timepoint.
        pcs: list of length nmice, pcs[mouse] is a list of length ntrials[mouse],
                and pcs[mouse][trial] is a numpy array of shape (npcs, T[mouse][trial]) with the projected neural data.
    """

    nmice = len(neural)
    device = model['device']
    decoders = model['decoder']
    doutput = len(decoders)

    # Replicate 1D inputs along time axis to match neural data (make copies to avoid modifying original)
    input_processed = []
    for mouse in range(nmice):
        input_mouse = []
        for trial in range(len(neural[mouse])):
            T = neural[mouse][trial].shape[1]  # time dimension

            # Handle 1D input - replicate along time
            if input[mouse][trial].ndim == 1:
                input_trial = np.tile(input[mouse][trial][:, np.newaxis], (1, T))
            else:
                input_trial = input[mouse][trial]
            input_mouse.append(input_trial)
        input_processed.append(input_mouse)

    # Use processed data instead of original
    input = input_processed

    predictions = []
    pcs = []

    with torch.no_grad():
        for mouseidx in range(nmice):
            if mouseid is not None:
                mouse = mouseid[mouseidx]
            else:
                mouse = mouseidx

            ntrials = len(neural[mouseidx])
            mouse_predictions = []
            mouse_pcs = []
            projection = model['projection'][mouse]

            for trial in range(ntrials):
                # Get trial data
                neural_trial = torch.from_numpy(neural[mouseidx][trial].T.astype(np.float32)).to(device)  # (T, nneurons)
                input_trial = torch.from_numpy(input[mouseidx][trial].T.astype(np.float32)).to(device)    # (T, dinput)

                # Project neural data
                projected = torch.matmul(neural_trial, projection.T)  # (T, npcs)

                # Decode each output dimension
                combined = torch.cat([projected, input_trial], dim=1)  # (T, npcs + dinput)
                pred = np.zeros((neural_trial.shape[0], doutput), dtype=np.int64)  # (T, doutput)

                for out_dim in range(doutput):
                    logits = decoders[out_dim](combined)  # (T, ncategories[out_dim])
                    pred[:, out_dim] = torch.argmax(logits, dim=1).cpu().numpy()

                # Store results
                mouse_predictions.append(pred.T)  # (doutput, T)
                mouse_pcs.append(projected.cpu().numpy().T)  # (npcs, T)

            predictions.append(mouse_predictions)
            pcs.append(mouse_pcs)

    return predictions, pcs

def f1scores_all_mice(all_predictions: list, output: list):
    """
    Concatenate all predictions and ground truth to compute F1 scores across all mice and trials
    Inputs:
        all_predictions: list of length nmice, all_predictions[mouse] is a list of length ntrials[mouse],
                and all_predictions[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = bool
                with the predicted output variable(s) for each timepoint.
        output: the ground truth output for each trial. output is a list of length nmice, output[mouse] is a list of
                length ntrials[mouse], and output[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial])
                OR (doutput,) (scalar per trial), dtype = float32. with the output variable(s) for each timepoint.
    Returns:
        f1scores: numpy array of shape (doutput,) with the F1 score for each output dimension
    """
    nmice = len(all_predictions)
    all_pred_concat = []
    all_output_concat = []
    doutput = output[0][0].shape[0]

    for mouse in range(nmice):
        for trial in range(len(all_predictions[mouse])):
            # Predictions are always (doutput, T)
            pred_trial = all_predictions[mouse][trial].T  # (T, doutput)
            all_pred_concat.append(pred_trial)

            # Output can be (doutput,) or (doutput, T)
            output_trial = output[mouse][trial]
            if output_trial.ndim == 1:
                # Scalar per trial: (doutput,) -> expand to (T, doutput) where all T are the same
                T = pred_trial.shape[0]
                output_trial_expanded = np.tile(output_trial[:, np.newaxis], (1, T)).T  # (T, doutput)
                all_output_concat.append(output_trial_expanded)
            else:
                # Time-varying: (doutput, T) -> (T, doutput)
                all_output_concat.append(output_trial.T)

    # Concatenate all timepoints from all trials and all mice
    all_pred_concat = np.vstack(all_pred_concat)  # (total_timepoints, doutput)
    all_output_concat = np.vstack(all_output_concat)  # (total_timepoints, doutput)

    # Compute F1 score for each output dimension
    f1scores = np.zeros(doutput)
    for out_dim in range(doutput):
        f1scores[out_dim] = f1_score(all_output_concat[:, out_dim], all_pred_concat[:, out_dim])

    return f1scores

def accuracy_all_mice(all_predictions: list, output: list):
    """
    Concatenate all predictions and ground truth to compute accuracy across all mice and trials.
    For categorical outputs.

    Inputs:
        all_predictions: list of length nmice, all_predictions[mouse] is a list of length ntrials[mouse],
                and all_predictions[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial]) of dtype = int
                with the predicted categorical output variable(s) for each timepoint.
        output: the ground truth output for each trial. output is a list of length nmice, output[mouse] is a list of
                length ntrials[mouse], and output[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial])
                OR (doutput,) (scalar per trial), dtype = int with the categorical output variable(s) for each timepoint.
    Returns:
        accuracies: numpy array of shape (doutput,) with the accuracy for each output dimension
    """
    nmice = len(all_predictions)
    all_pred_concat = []
    all_output_concat = []
    doutput = output[0][0].shape[0]

    for mouse in range(nmice):
        for trial in range(len(all_predictions[mouse])):
            # Predictions are always (doutput, T)
            pred_trial = all_predictions[mouse][trial].T  # (T, doutput)
            all_pred_concat.append(pred_trial)

            # Output can be (doutput,) or (doutput, T)
            output_trial = output[mouse][trial]
            if output_trial.ndim == 1:
                # Scalar per trial: (doutput,) -> expand to (T, doutput) where all T are the same
                T = pred_trial.shape[0]
                output_trial_expanded = np.tile(output_trial[:, np.newaxis], (1, T)).T  # (T, doutput)
                all_output_concat.append(output_trial_expanded)
            else:
                # Time-varying: (doutput, T) -> (T, doutput)
                all_output_concat.append(output_trial.T)

    # Concatenate all timepoints from all trials and all mice
    all_pred_concat = np.vstack(all_pred_concat)  # (total_timepoints, doutput)
    all_output_concat = np.vstack(all_output_concat)  # (total_timepoints, doutput)

    # Compute accuracy for each output dimension
    accuracies = np.zeros(doutput)
    for out_dim in range(doutput):
        accuracies[out_dim] = np.mean(all_pred_concat[:, out_dim] == all_output_concat[:, out_dim])

    return accuracies

def cross_validate_decoder(neural: list, input: list, output: list, metadata: str | None = None,
                           train_decoder=train_decoder_linear,
                           predict=predict_linear,
                           nsets: int = 5,
                           eval_fn=None,
                           **kwargs):
    """
    Cross-validates the decoder function. Performs nsets-fold cross-validation, training the decoder on nsets-1 sets and testing on
    the held-out set. Each cross-validation set contains 1/nsets of the trials from each mouse.
    Finds a random split of trials for each mouse into nsets sets, then, for each set, trains the decoder on the other nsets-1 sets and
    computes the predictions on the held out set.
    Then computes evaluation metric (F1 score or accuracy) for each output dimension
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
                dtype = float32 or int. with the output variable(s) for each timepoint.
        metadata: optional dict with additional information about the experiment.
        train_decoder: function to train the decoder. Should have the signature
                model = train_decoder(neural_train, input_train, output_train, metadata, **kwargs)
                Default: train_decoder_linear
        predict: function to predict using the trained decoder. Should have the signature
                predictions = predict(neural_test, input_test, model, mouseid, metadata)
                Default: predict_linear
        nsets: number of cross-validation sets (default: 5)
        eval_fn: evaluation function to compute performance metric. Should have the signature
                scores = eval_fn(predictions, output)
                Default: accuracy_all_mice (for binary outputs), can use accuracy_all_mice for categorical
    kwargs are passed to train_decoder
    Returns:
        scores: numpy array of shape (doutput,) with the evaluation metric for each output dimension
        predictions: list of length nmice, predictions[mouse] is a list of length ntrials[mouse],
                and predictions[mouse][trial] is a numpy array of shape (doutput, T[mouse][trial])
                with the predicted output variable(s) for each timepoint.
        trial_splits: list of length nmice, trial_splits[mouse] is a list of length nsets,
                trial_splits[mouse][set] is a numpy array with the trial indices for that set for that mouse.
    """

    if eval_fn is None:
        eval_fn = accuracy_all_mice

    nmice = len(neural)

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

    # Compute evaluation metric across all mice and trials
    scores = eval_fn(all_predictions, output)

    return scores, all_predictions, all_pcs, trial_splits