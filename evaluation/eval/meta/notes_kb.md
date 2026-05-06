# Differences between humans and agents

**`SDK`**: Using domain-specific SDKs or Python modules
  - Allen2p general: did not use AllenSDK . Used h5py to load the files, despite pynwb and allensdk being installed in their environment, having access to notebook examples showing how to access data. Human code used allensdk, agent used h5py
**`VARNAME`**: Agent made mistakes when the variable name was misleading (confusing / unconventional variable names)
  - Allen2p, splitting data into sessions, confused by variable named `ophys_experiment_id`. Example of how to do this correctly is in the example notebooks, agent ignored. TODO: check CONVERSION_NOTES.md to see if, in the code summary, agent noted this.
**`TIMERES`**: Strange choices on time resolution
**`RESAMP`**: Strange choices on resampling
**`FILTER`**: Filtering parameters choice
**`PROCESS`**: Requires extra (complex) processing from raw data
  - Tracking data: filter by conf, interpolation
  - Combine recording for dual probe
  - e.g., data stream from multiple camera, additional data analysis
**`ASSUME`**: Assume certain information without checking against data
  - Lee2025: 40 minute session length (exact)

**`OUTLIER`**: Handling missing or bad data 
**`SEMANTIC`**: Semantic misunderstanding, common knowledge
**`INCOMPLETE`**: Did not load the full dataset
**`LITERAL`**: Took paper too literally
**`DETAIL`**: Followed details in the resources better than human
**`INEFFICIENT`**: Compare running time of human vs machine code
**`IMAGINGVAR`**: Using event data vs dF/F vs F -- when multiple versions of the neural imaging data are available, agents may choose the wrong version of the data, bias toward the more processed events than rawer forms