- Sym linked to downloaded code and data
- Read README.md
  - README.md seems to reference a different data organization structure than the downloaded nwb files
- Just going to try to load in the nwb files to try to find relationships between nwb and code
- Created convert_data.py
- Looked at tutorial about reading in calcium imaging data https://pynwb.readthedocs.io/en/stable/tutorials/domain/ophys.html
- Loaded in in nwbfile and printed with the following code
```python
with pynwb.NWBHDF5IO(datafile, 'r') as io:
    nwbfile = io.read()
    print(nwbfile)
```
- See the following fields that may be important
  - `'acquision'`
  - `'processing'` which has `'ophys'` and `'behavior'`
- Look at `'acquisition'`: `print(nwbfile.acquisition)`
- Look at `.processing['ophys']['Fluorescence']` and `.processing['ophys']['Deconvolved']`
- Based on information in Methods section of papaer, decided to use `'Deconvolved'` for the neural decoder
- Found activity data in `nwbfile.processing["ophys"]["Deconvolved"].roi_response_series['plane0'].data[:]`, shape `(T,nneurons)`
- Found metadata about corresponding in `nwbfile.processing["ophys"]["Deconvolved"].rois[:]`, including `iscell`, which I used for filtering. 
- Has no timestamps stored, will use stored `roi.rate`
- Two mice had multi-plane recording, added handling of that
- Neural rate was halved when there were two planes recorded, had to multiply

- Behavior data processing
- Went through each behavior feature and looked at its shape and unique values across the entire dataset, found
    Summary across all sessions:
    range_T: 14164 to 51520
    range_nneurons: 155 to 2341
    max_spike_rate_range: 3512.35400390625 to 28291.951171875
    range_neural_time_bin_size: 32.241813602015114 to 64.48362720403023
    unique_reward_amounts: [0.004]
    range_nrewards: 37 to 93
    unique_autoreward: [0.]
    unique_vr_environment: [0. 1.]
    unique_licks: [0. 1. 2. 3. 4. 5. 6. 7. 8.]
    position_range: -50.000000000000014 to 452.4721399656936
    unique_reward_zone: [0. 1. 2. 3. 4. 5. 6. 7. 8.]
    unique_scanning: [1.]
    speed_range: -6.44720191781 to 144.52173215683072
- After plotting reward zone data, I have realized it is not telling me where the reward zone location is, but whether the mouse is in the reward zone. I don't know why it is a value between 0 and 8, it does say binary, so can possibly threshold and estimate based on the mouse's position at these time points... 
- It looks to me like the reward zone location is **not** explicitly stored in the nwb data files! 
- Wrote some complicated code to use the reward zone binary info to localize the reward location using the position of the mouse when reward_zone > 0 and continuity across trials to smooth out the results (not sure how necessary viterbi part is, there are certainly trials with no info, so maybe it is just filling in gaps). 
- Dealt with some corner cases: number of timepoints in a trial < 50, number of timepoints in behavior and neural data do not match (off by 1ish)
- trial_number does not match trial_start data --- decided that trial_start and teleport were more reliable info than trial_number and used those (more conservative, matched text in paper, range of trial lengths was smaller), matched reference code


Steps
Found data files
Loaded in data files
Parsed subjects and sessions and trials

Loaded in neural activity data
Parsed time and cells
Found filtering information
Performed necessary preprocessing
Found neural activity timestamps/rate, offsets

Loaded in behavior data
Find each feature from the decoder input and output tasks
Process each behavior/task feature 
Categorize these as no processing needed, minor processing (e.g. thresholding), major processing (need to combined different features, or with other information)

Handle missing data as well as possible
Handle slight mistakes in data, e.g. number of data points in neural and behavioral data mismatch

Temporal alignment of all time series, categorize as no processing needed, minor, major

Correctly format the output for all of the above, output shapes correct


Consider efficiency
  - Only do time-consuming processing on data that will be used
  - Avoid loops/vectorize
  - Parallelize
  - Avoid repeating the same calculation multiple times