import numpy as np
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use('tkAgg')
import matplotlib.pyplot as plt
plt.ioff()

from decoder import train_decoder
from decoder import predict
from decoder import cross_validate_decoder, accuracy_all_mice


def linear(coeff,x):
    if coeff.shape[1] == x.shape[0]:
        return np.dot(coeff,x)
    assert coeff.shape[1] == x.shape[0] + 1
    return np.dot(coeff[:,1:],x) + coeff[:,0][:,None]

def softmax(x, axis=0):
    """Compute softmax values for each set of scores along specified axis."""
    exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

def generate_synthetic_data(nmice = 10,dinput = 2,doutput = 3,npcs = 10,
                            ncategories = [2, 3, 4],  # different number of categories for each output dimension
                            sigma_neural = .1,
                            nneuron_range = (1900,2100),
                            T_range = (100,200),
                            ntrials_range = (48,52),
                            rate_range = (5,15)):

    data = {'neural': [], 'input': [], 'output': [], 'pc': []}
    gt = {'decoder_neural': [], 'decoder_pca': [], 'decoder_input': []}

    # Create separate decoder for each output dimension with appropriate number of categories
    decoder_pca_list = []
    for out_dim in range(doutput):
        decoder_pca = np.random.randn(ncategories[out_dim], npcs)
        decoder_pca_list.append(decoder_pca)
    gt['decoder_pca'] = decoder_pca_list

    for mouse in range(nmice):
        ntrials = np.random.randint(ntrials_range[0],ntrials_range[1])
        nneurons = np.random.randint(nneuron_range[0],nneuron_range[1])
        rate_per_input = np.random.randint(rate_range[0],rate_range[1],(nneurons,dinput))

        # Create separate decoder_input for each output dimension
        decoder_input_list = []
        for out_dim in range(doutput):
            decoder_input = np.random.randn(ncategories[out_dim], dinput+1)
            decoder_input_list.append(decoder_input)

        neuralmouse = []
        outputmouse = []
        inputmouse = []
        for trial in range(ntrials):
            T = np.random.randint(T_range[0],T_range[1])

            inputidx = np.random.randint(0,dinput)
            # to one-hot encoding of input
            inputtrial = np.zeros((dinput,T),dtype=np.float32)
            inputtrial[inputidx,:] = 1.0

            neuraltrial = np.zeros((nneurons,T),dtype=np.float32)
            for neuron in range(nneurons):
                rate = rate_per_input[neuron,inputidx]
                spikes = np.random.poisson(rate,(T,))
                neuraltrial[neuron,:] = spikes.astype(np.float32)

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
            outputtrial = np.zeros((doutput, inputtrial.shape[1]), dtype=np.int64)

            # Generate categorical output for each dimension
            for out_dim in range(doutput):
                # Compute logits from PCA and input
                logits = linear(decoder_pca_list[out_dim], pcsmouse[trial]) + linear(decoder_input_list[out_dim], inputtrial)
                # Apply softmax and sample categories
                probs = softmax(logits, axis=0)
                # Take argmax to get deterministic categories
                outputtrial[out_dim, :] = np.argmax(probs, axis=0)

            outputmouse.append(outputtrial)

        data['neural'].append(neuralmouse)
        data['input'].append(inputmouse)
        data['output'].append(outputmouse)
        data['pc'].append(pcsmouse)
        gt['decoder_input'].append(decoder_input_list)
        
    return data, gt

def main():
    

    nmice = 10
    dinput = 2
    doutput = 3
    npcs = 10
    ncategories = [2, 3, 4]  # different number of categories for each output dimension
    sigma_neural = .1
    nneuron_range = (1900,2100)
    #nneuron_range = (90,110)
    T_range = (100,200)
    ntrials_range = (48,52)
    rate_range = (5,15)
    
    data,gt = generate_synthetic_data(nmice=nmice, dinput=dinput, doutput=doutput, npcs=npcs,
                                    ncategories=ncategories,
                                    sigma_neural=sigma_neural,
                                    nneuron_range=nneuron_range,
                                    T_range=T_range,
                                    ntrials_range=ntrials_range,
                                    rate_range=rate_range)

    # %%
    # plot a sample trial
    fig,ax = plt.subplots(4,1,figsize = (30,20),sharex=True)

    mouse = 0
    trial = 0

    # neural
    for neuron in range(min(50,data['neural'][mouse][trial].shape[0])):
        maxv = np.percentile(data['neural'][mouse][trial][neuron,:],99)
        ax[0].plot(data['neural'][mouse][trial][neuron,:]/maxv+neuron)
    #ax[0].set_ylim((0,10))
    ax[0].set_ylabel('Neural')

    # from neural to pc
    pc = gt['decoder_neural'][mouse].transform(data['neural'][mouse][trial].T).T
    for pcidx in range(npcs):
        maxv = np.percentile(pc[pcidx],99)
        ax[1].plot(pc[pcidx]/maxv+pcidx)
    ax[1].set_ylabel('PCs')

    for outdim in range(doutput):
        # Normalize to [0, 1] range for plotting
        normalized = data['output'][mouse][trial][outdim,:] / (ncategories[outdim] - 1)
        ax[2].plot(normalized*.9+.05+outdim)
        ax[2].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'k--')
    ax[2].set_ylabel('Output (categorical)')

    # Compute decoded logits for each output dimension
    for outdim in range(doutput):
        logits = linear(gt['decoder_pca'][outdim], pc) + linear(gt['decoder_input'][mouse][outdim], data['input'][mouse][trial])
        probs = softmax(logits, axis=0)
        predicted_cat = np.argmax(probs, axis=0)
        # Normalize to [0, 1] range for plotting
        normalized = predicted_cat / (ncategories[outdim] - 1)
        ax[3].plot(normalized*.9+.05+outdim)
        ax[3].plot([0,data['neural'][mouse][trial].shape[1]],[.5+outdim,.5+outdim],'k--')
    ax[3].set_ylabel('Decoded (categorical)')
    fig.tight_layout()
    plt.show()
    #ax[0].set_xlim([0,50])

    # %%
    # train on all the data, should be close to perfect
    model_all = train_decoder(data['neural'], data['input'], data['output'], npcs=npcs, lr=1e-3)
    predicted_outputs, predicted_pcs, confidence = predict(data['neural'], data['input'], model_all)


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
            # Normalize categorical values to [0, 1] for plotting
            pred_normalized = predicted_outputs[mouse][trial][outdim,:] / (ncategories[outdim] - 1)
            gt_normalized = data['output'][mouse][trial][outdim,:] / (ncategories[outdim] - 1)
            ax[1].plot(pred_normalized*.9+.05+outdim,'o-', label='Predicted')
            ax[1].plot(gt_normalized*.9+.05+outdim,'k.--', label='Ground truth')
        ax[1].set_ylabel('Output (categorical)')
        
        return fig, ax

    mouse = 0
    trial = 0
    fig,ax = debug_plot(data,gt,predicted_outputs,predicted_pcs,mouse,trial)
    fig.tight_layout()
    accuracies = accuracy_all_mice(predicted_outputs, data['output'])
    print("Training accuracies per output dimension:", accuracies)
    #ax[0].set_xlim([0,200])

    # %%
    accuracies, cv_predictions, cv_pcs, cv_confidences, trial_splits = cross_validate_decoder(data['neural'], data['input'], data['output'], nsets=5, npcs=npcs, ncategories=ncategories, eval_fn=accuracy_all_mice)

    # %%
    fig, ax = debug_plot(data,gt,cv_predictions,cv_pcs,0,0)
    fig.tight_layout()
    plt.show()
    #ax[0].set_xlim([0,200])
    print("CV accuracies:", accuracies)

if __name__ == "__main__":
    main()
