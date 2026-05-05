# Differences between humans and agents

**`SDK`**: Using domain-specific SDKs or Python modules
  - Allen2p general: did not use AllenSDK . Used h5py to load the files, despite pynwb and allensdk being installed in their environment, having access to notebook examples showing how to access data. Human code used allensdk, agent used h5py
**`VARNAME`**: Agent made mistakes when the variable name was misleading (confusing / unconventional variable names)
  - Allen2p, splitting data into sessions, confused by variable named `ophys_experiment_id`. Example of how to do this correctly is in the example notebooks, agent ignored. TODO: check CONVERSION_NOTES.md to see if, in the code summary, agent noted this.
**`TIMERES`**: Strange choices on time resolution
**`RESAMP`**: Strange choices on resampling
**`IMAGINGVAR`**: Using event data vs dF/F vs F -- when multiple versions of the neural imaging data are available, agents may choose the wrong version of the data, bias toward the more processed events than rawer forms
**`EXTRAFILTER`**: Added extra filtering of neural, trial data
**`UNDERFILTER`**: Missed some filtering
**`FILTER`**: Filtering
**`OUTLIERFILTER`**: Handling missing or bad data 
**`SEMANTIC`**: Semantic misunderstanding, common knowledge
**`INEFFICIENT`**: Compare running time of human vs machine code
**`COMPLEX`**: Requires complex processing
**`INCOMPLETE`**: Did not load the full dataset
**`LITERAL`**: Took paper too literally
**`DETAIL`**: Followed details in the resources better than human
