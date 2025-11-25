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
#     display_name: data-format
#     language: python
#     name: python3
# ---

# %%
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression

# %%
nmice = 10
dinput = 2
doutput = 3
data = {'neural': [], 'input': [], 'output': []}
gt = {'decoder_neural': [], 'decoder_input': []}

for mouse in range(nmice):
    ntrials = np.random.randint(48,52)
    nneurons = np.random.randint(90,110)
    rate_per_input = np.random.randint(5,15,(nneurons,dinput))
    decoder_neural = np.random.randn(doutput,nneurons+1)
    decoder_input = np.random.randn(doutput,dinput)
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

        outputtrial = np.dot(decoder_neural[:,1:],neuraltrial) + np.dot(decoder_input,inputtrial)
        inputmouse.append(inputtrial)
        neuralmouse.append(neuraltrial)
        outputmouse.append(outputtrial)

    mu = np.mean([np.mean(outputtrial,axis=1) for outputtrial in outputmouse],axis=0)
    decoder_neural[:,0] = -mu.flatten()
    outputmouse = [outputtrial > mu[:,None] for outputtrial in outputmouse]
    data['neural'].append(neuralmouse)
    data['input'].append(inputmouse)
    data['output'].append(outputmouse)
    gt['decoder_neural'].append(decoder_neural)
    gt['decoder_input'].append(decoder_input)

# %%
import matplotlib.pyplot as plt

fig,ax = plt.subplots(3,1,figsize = (30,10),sharex=True)

mouse = 0
trial = 0
for neuron in range(data['neural'][mouse][trial].shape[0]):
    maxv = np.percentile(data['neural'][mouse][trial][neuron,:],99)
    ax[0].plot(data['neural'][mouse][trial][neuron,:]/maxv+neuron)
for outdim in range(doutput):
    ax[1].plot(data['output'][mouse][trial][outdim,:]*.9+.05+outdim)
    ax[1].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'k--')
decoded = np.dot(gt['decoder_neural'][mouse][outdim,1:],data['neural'][mouse][trial])+gt['decoder_neural'][mouse][outdim,0] + np.dot(gt['decoder_input'][mouse][outdim,:],data['input'][mouse][trial])
for outdim in range(doutput):
    maxv = np.percentile(decoded,99)
    minv = np.percentile(decoded,1)
    ax[2].plot((decoded - minv)/(maxv - minv)*.9+.05+outdim)
    ax[2].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'k--')
    
ax[0].set_xlim([0,50])


# %%
def decoder(neural: list, input: list, output: list, metadata: str | None = None, **kwargs):
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
        metadata: optional string with additional information about the experiment.

        Algorithm hyperparameters can be passed as keyword arguments:
        npcs: number of principal components to use (default: 10)

    Returns:
        models: list of length doutput, models[out_dim] is a trained sklearn LogisticRegression model to predict output dimension out_dim from the
                projected neural data and input data.

    """

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
    models = []
    for out_dim in range(y.shape[1]):
        model = LogisticRegression(max_iter=1000)
        model.fit(X, y[:, out_dim])
        models.append(model)

    return models


# %%
def cross_validate_decoder(neural: list, input: list, output: list, metadata: str | None = None, nsets: int = 5, **kwargs):
    """
    Cross-validates the decoder function. Performs nsets-fold cross-validation, training the decoder on nsets-1 sets and testing on 
    the held-out set. Each cross-validation set contains 1/nsets of the trials from each mouse.
    Finds a random split of trials for each mouse into nsets sets, then, for each set, trains the decoder on the other nsets-1 sets and 
    computes the predictions on the held out set. 
    
    """

