### Step 2: Dataset Exploration
- 6 subjects, organized as folders, with each session a seperate folder
- `F.npy` - raw data (n_neurons, n_samples); `Fneu.npy` - neuropil
- Use suite2p.extraction.dcnv to preprocess the data
https://suite2p.readthedocs.io/en/latest/deconvolution/

- Imaging and video at 30Hz, with microscope acquisition acting as a trigger for camera frame acquisition
(Should be synced except for frame drop)
- move_deve contains information on motion energy
- Use `interframe_int.npy` to deal with missing frames (dt >> 1/30 sec)
- Motion energy data needs to be normalized

### Step 5: Mapping Planning
- Use `F` and `Fneu` to compute preprocessed data
- Use motion engery as the output variable (discretized)
- Fix alignment (interpolation) when there are frames missing

**Note on important decisions**
- Use Suite2P for data preprocessing (or at least some version of it)
- How to deal with 40 min session (chunk into smaller trials?)
- Handle missing frame issue
The dropped frames need to be extracted by looking at dt = interframe_int * 1000 > 0.04 (sec)
Don't quite understand the unit of this variable but *1000 seems to work
