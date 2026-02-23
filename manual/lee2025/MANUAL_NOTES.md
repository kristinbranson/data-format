### Step 2: Dataset Exploration
- Each QLAK-CA1-* file under /data represents data from a single animal in the experiment (N=7)
- There was not enough metadata provided with the files (e.g., sampling rate, preprocessing etc.)
- The data is organized by session; the geometry of each session is defined by the `blocked` variable; the neural data defined in `trace`, and the location of the animal is defined in `position`.
- Calcium imaging but the neural data is binarized "spikes".
- .mat files with HDF5 format are the worst 💩

### Step 3: Reference Text Reading
- 40 min recording session * 30Hz sampling rate, match the length of the data
- The binary vector "was treated as the firing rate in all further analyses"

### Step 5: Mapping Planning
- `trace` contains neural activity
- `trace` contains NaN on different days,
- `input` should be neural activity (`trace`) and environment geometry (`blocked`)
- `output` should be discretized location variable (computed from `position`)

- Assume location and neural data are aligned (no other info avialible)
- Potentially bin/filter neural data

**Notes on important decisions**
- missing data in `trace`
- change environment geometry to one-hot encoding
- filter/bin "spikes" data
- cut 40-min session into shorter "trials"
