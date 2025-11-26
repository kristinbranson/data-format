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
import matplotlib.pyplot as plt

from decoder import train_decoder_linear as train_decoder
from decoder import predict_linear as predict
from decoder import cross_validate_decoder, f1scores_all_mice


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
# plot a sample trial
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
fig.tight_layout()
#ax[0].set_xlim([0,50])

# %%
# train on all the data, should be close to perfect
model_all = train_decoder(data['neural'], data['input'], data['output'], npcs=npcs)
predicted_outputs, predicted_pcs = predict(data['neural'], data['input'], model_all)


# %%
# plot learned vs ground truth
# note that embedding does not need to match, e.g. not defined up to an affine transform
def debug_plot(data,gt,predicted_outputs,predicted_pcs,mouse,trial):

    fig,ax = plt.subplots(2,1,figsize = (30,20),sharex=True)
    for pcidx in range(npcs):
        maxv = np.percentile(data['pc'][mouse][trial][pcidx],99)
        minv = np.percentile(data['pc'][mouse][trial][pcidx],1)
        ax[0].plot([0,data['pc'][mouse][trial].shape[1]],[.5+pcidx,.5+pcidx],'--',color=[.7,.7,.7])
        ax[0].plot((predicted_pcs[mouse][trial][pcidx] - minv)/(maxv - minv)*.9+.05+pcidx, label='Learned embedding')
        ax[0].plot((data['pc'][mouse][trial][pcidx] - minv)/(maxv - minv)*.9+.05+pcidx,'k--', label='GT embedding')
    ax[0].set_ylabel('PCs')

    for outdim in range(doutput):
        ax[1].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'--',color = [.7,.7,.7])
        ax[1].plot(predicted_outputs[mouse][trial][outdim,:]*.9+.05+outdim,'o-')
        ax[1].plot(data['output'][mouse][trial][outdim,:]*.9+.05+outdim,'k.--')
    ax[1].set_ylabel('Output')
    
    return fig, ax

mouse = 0
trial = 0
fig,ax = debug_plot(data,gt,predicted_outputs,predicted_pcs,mouse,trial)
fig.tight_layout()
f1scores = f1scores_all_mice(data['output'], predicted_outputs)
print("Training F1 scores per output dimension:", f1scores)
#ax[0].set_xlim([0,200])

# %%
f1scores, cv_predictions, cv_pcs, trial_splits = cross_validate_decoder(data['neural'], data['input'], data['output'], nsets=5, npcs=npcs)

# %%
fig, ax = debug_plot(data,gt,cv_predictions,cv_pcs,0,0)
fig.tight_layout()
#ax[0].set_xlim([0,200])
print("CV F1 scores:", f1scores)

