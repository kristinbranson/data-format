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
def decoder(neural: list, input: list, output: list):
    """
    Train a common decoder for all mice to predict output from neural and input data.
    Inputs:
        neural: neural activity. neural is a list of length nmice, neural[mouse] is a list of length ntrials[mouse], and
                neural[mouse][trial] is a numpy array of shape (nneurons[mouse], T[mouse][trial]) giving the neural activity
                for that trial
        input: input data. input is a list of length nmice, input[mouse] is a list of length ntrials[mouse], and
                input[mouse][trial] is a numpy array of shape (dinput, T[mouse][trial]) or with the
                stimulus and condition information for each timepoint. dinput is the number of inputs. For continuous inputs, 
                this should the dimensionality of the input. For discrete inputs, use a one-hot encoding. 
        output: output data. output is a list of length nmice, output[mouse] is a list of length ntrials[mouse], and

                
    """
    
    return
