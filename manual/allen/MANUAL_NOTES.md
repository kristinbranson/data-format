Relatively straightforward to reorganize, especially with access to the example code using the AllenSDK

### Step 2: Dataset Exploration
- Use the notebooks provided by AllenSDK to load data and explore data structure
- Find recording `session` using data table
- Each `session` have many `experiment` associated with different imaging plane
- dF/F avialible as `ds.dff_traces.dff.values`
- Behavioral recording (image identity, running speed, pupil size) is sampled at different frequency
- Timestamp is available for each datastream, needs to interpolate

### Step 5: Mapping Planning
- Neural data: dF/F
- Input variable: running speed and pupil size, interpolated to the same time axis
- Output (decode) variable: image identity