# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Neuroscience Data Standardization Project

## Project Context

You are assisting with a project that tests how well Claude Code can help reorganize and reformat heterogeneous neuroscience datasets into a unified, standardized format. 

*Goal**: Test Claude Code's ability to work with diverse neuroscience datasets and convert them into a common structure suitable for downstream analysis. To avoid contamination, do not look at code or data in the parent or sibling directories. 

## Input Data

- The data in directory `data` is from the paper "Identifying representational structure in CA1 to benchmark theoretical models of cognitive mapping". 
- The pdf of this paper is `paper.pdf`.
- Read this paper to better understand the experiment and data. 
- Relevant parts of the paper and Methods section are in the file `methods.txt`.
- Code from this paper is in the directory `code`.
- The data are quite large. First reformat a small sample of the data. Choose subsets of the data so that all output and input values are covered. Verify that data formatting works on this data subset, including by running train_decoder.py with it. Once you have verified this, convert and test the whole dataset. 
- The output variable should be the position in the arena. Discretize the (x,y) coordinate into 3 x 3 = 9 bins.
- The input variable should be the geometry of the environment. It should be 3 x 3 = 9 dimensional, and 1 should represent that the corresponding region of the square is walled off and 0 that it is not. See the paper, methods, and code for details. Consult with the user if this is not possible. 
- Ask the user for other possible output and input variables.

## Target Data Format

All datasets must be converted into the following Python dictionary structure:

```python
data = {
    'neural': [  # list of subjects (e.g., mice, rats)
        [  # list of trials for subject 1
            neuron_by_time_matrix,  # shape: (n_neurons, n_timepoints)
            neuron_by_time_matrix,  # trial 2
            ...
        ],
        [  # list of trials for subject 2
            ...
        ],
        ...
    ],

    'input': [  # list of subjects
        [  # list of trials for subject 1
            input_data,  # stimulus/task variables, shape: (n_input, n_timepoints) or (n_input)
            ...
        ],
        ...
    ],

    'output': [  # list of subjects
        [  # list of trials for subject 1
            output_data,  # behavioral response, shape (n_output, n_timepoints) or (n_output)
            ...
        ],
        ...
    ],

    'metadata': {
        'task_description': str,  # description of the behavioral task
        'brain_regions': str,     # recorded brain regions
        # additional metadata fields as needed
    }
}
```

### Key Format Requirements

- **neural**: Neural activity data (e.g., firing rates, spike counts) organized by subject and trial
  - Consistent dimensions: (n_neurons, n_timepoints) for each trial
  - Time bins should be consistent across trials/subjects when possible

- **input**: Variables that serve as inputs **to the decoder**
  - **Important**: These are decoder inputs. They could be task inputs to the animal, but inputs to the animal can also be decoder outputs.
  - Examples: time from an aligning signal, stimulus characteristics such as:
    - visual: contrast, position, orientation
    - audio: frequency, amplitude
  - Can be time-varying (n_timepoints,) or scalar values per trial. If at all possible, make it time-varying. 
  - Should capture all relevant contextual information for the decoder
  - If an input is a time such as onset of some stimulus, consider if it can be converted into a time series. 

- **output**: Variables to be decoded/predicted from neural activity
  - **Important**: These are what we want the decoder to predict. They could be the animal's output behavior or properties of the stimulus.
  - Output variables must be **categorical**, i.e. discrete rather than continuous. If a variable of interest is not discrete, **propose sensible methods to discretize it to the user**. 
  - A behavioral response from the animal could be a decoder input (if it's not what we're decoding)
  - Examples: stimulus properties (contrast, orientation), choice (left/right), reaction time, position
  - Can be time-varying or discrete values per trial. If at all possible, make it time-varying
  - This is what we're trying to extract from the neural data
  - If an output is a time such as when a behavior occurred, consider if it can be converted into a time series.
  
- **metadata**: Descriptive information
  - At minimum: task_description (str), brain_regions (str)
  - Add other relevant fields: sampling_rate, time_bin_size, session_info, etc.

## Python environment

Use the conda environment **decoder-data-format** to run any python code. 

## Decoder Reference

- Modify the script `train_decoder.py` with code to import the load_data function in the section marked `ADD CODE HERE`.
- **Only modify code within the section marker `ADD CODE HERE`**. Do not modify other parts of this code or the `decoder.py` function.
- If you believe there is a bug, tell the user about this. But check your own formatting carefully before deciding there is a bug in `train_decoder.py` or `decoder.py`
- Run this script with `python train_decoder.py <data_file_path>` to help validate.
- Pipe the output to the file `train_decoder_out.txt` so that the user can examine it.

### Purpose
These functions will be used during the validation phase to ensure:
1. Data structure is correct
2. Dimensions are consistent
3. Decoder can successfully train and predict (overfitting check)
4. Decoder generalizes appropriately (cross-validation check)
5. Poor performance indicates data formatting issues that need investigation

## Conversion Workflow

When helping convert a new dataset, follow these steps:

### 1. Dataset Exploration
- First, understand the native data structure
- Identify how data is organized (files, formats, hierarchies)
- Determine available variables and their meanings
- Check data dimensions and data types
- Look for documentation or README files

### 2. Mapping Planning
- Map source data elements to target format components:
  - Which variables contain neural activity?
  - Identify ALL available task variables (stimuli, choices, timing, etc.)
  - **Ask the user**: Which variables should be decoder **inputs** vs **outputs**?
    - Present **all** available variables as options, do not limit to a small number.
    - Clarify: inputs are contextual info for the decoder, outputs are what we want to decode
    - Remember: a stimulus to the animal can be an output of the decoder (if decoding stimulus properties)
    - Remember: an animal's response can be an input to the decoder (if not what we're decoding)
  - **Ask user for feedback**: Describe precisely how the input and output will be represented, and ask for feedback.
  - Identify all preprocessing needed, e.g. temporal binning, alignment, and filtering.
  - Consult the paper and methods to determine **temporal binning** to compute spiking rates, if applicable. **Present choices to the user for feedback**. 
  - Consult the paper and methods to determine **temporal alignment** of trials, if applicable. **Present choices to the user for feedback**.
  - What metadata should be preserved?
  - Check for variables indicating which time periods have valid data and **exclude invalid data** from conversion. 
- Note any edge cases or data quality issues

### 3. Script Development
- Write clear, well-documented conversion functions
- Handle missing data gracefully
- Validate data shapes and types at each step
- Include sanity checks (e.g., trial counts match across arrays)
- Make code modular and reusable

### 4. Validation

#### Step 4.1: Data size and format:
-  Verify converted data structure matches specification
- Check that dimensions are consistent across trials/subjects
- Ensure no data loss during conversion
- Validate that metadata accurately describes the data
- Document validation in CONVERSION_NOTES.md

#### Step 4.2: Modify and run `train_decoder.py` to validate:
- This is a critical phase that uses the script `train_decoder.py` to verify data quality and formatting.
- Only modify `train_decoder.py` within the section labeled `ADD CODE HERE` to load in the reformated data.
- Ensure that `train_decoder.py` runs without errors and does not produce infs or nans.
- Document all output from this script to the user in CONVERSION_NOTES.md. 
- **Examine the output of the script**, document all findings in CONVERSION_NOTES.md
- Do the following first on the sample data.
- Once everything is successful, convert and run on the full dataset. 

##### Step 4.2.1
Check that all formatting checks pass (performed by decoder.py:verify_data_format()) and that **no errors** were reported . Investigate and **explain to the user any warnings**. 

##### Step 4.2.2
- Examine the ranges and unique values of input and output dimensions. Check that the **no input or output dimensions are constant for all trials**. 
- What are the expected sizes of the data, ranges and unique values of all data? **Check that printed data properties match expectations.**

##### Step 4.2.3
Check that loss decreases over epochs of training decoders. 

##### Step 4.2.4
- Check that **accuracy for each output dimension is high when overfitting** to the training data. If it is not, check for formatting bugs. If no bugs are found, consider whether the output should be represented differently. Should it be time-varying? Should discretization be done differently? Consider reasons that the training accuracy might be poor and discuss with the user. Report results for all classification tasks. 
- Check that the cross validation accuracy for each output dimension is almost as high as when overfit to the training data. If it is much worse than the training accuracy, consider reasons this might be the case and discuss with user. 

##### Step 4.2.5
Ask the user to look at the plots produced and that they match expectations

#### Step 4.3: Processing Visualization
- **Create a `show_processing()` function** that demonstrates each preprocessing step for a selected trial
- Show side-by-side plots: raw data → binned data → aligned data → final format
- This helps verify that preprocessing doesn't introduce artifacts
- Document this in CONVERSION_NOTES.md

### 5. Documentation
- **Create a CONVERSION_NOTES.md file** to track the entire conversion process
  - Use an external file to record important information throughout the session
  - Document all decisions, findings, and reasoning in real-time
  - Track bugs discovered and how they were fixed
  - Include validation results and key metrics
- Document all conversion decisions and assumptions
- Note any preprocessing steps applied
- Record any data excluded and why
- Create a comprehensive README with dataset-specific details
- Organize analysis/investigation files into a cache folder for cleanup

## CONVERSION_NOTES.md Structure

Create a `CONVERSION_NOTES.md` file at the beginning of the conversion process to maintain a detailed record. This file should include:

### Session Information
- Date and session overview
- Dataset source and version
- Goals and requirements

### Chronological Log
Document decisions and findings as you work:
- **Initial Setup**: Environment, dependencies, data access
- **Data Exploration**: Structure, dimensions, variables discovered
- **Conversion Decisions**: Time windows, binning, alignment choices
- **Bugs & Fixes**: Issues discovered and how they were resolved
- **Validation Results**: All checks performed and outcomes

### Key Decisions Section
For each major decision, document:
- **What**: The decision made (e.g., "Time window: [-0.5, +1.5]s")
- **Why**: Rationale and trade-offs considered
- **Validation**: How you verified it was correct
- **Alternative**: Other approaches considered

### Findings & Insights
- Data quality issues discovered
- Dataset-specific quirks or conventions
- Performance metrics and statistics
- Unexpected behaviors or edge cases

### Final Cleanup
At the end of the session:
- Move analysis/investigation scripts to `cache/` folder
- Create `cache/README_CACHE.md` to document cached files
- Create final `README.md` summarizing the conversion
- Ensure CONVERSION_NOTES.md captures all important decisions

The CONVERSION_NOTES.md serves as a detailed technical log, while the final README.md provides user-facing documentation for using the converted data.

## Key Considerations

### Neuroscience Data Specifics
- **Spike times vs. firing rates**: Decide on appropriate binning for spike data
- **Trial alignment**: Align trials to meaningful events (stimulus onset, movement, etc.)
- **Time windows**: Choose appropriate pre/post-event windows
- **Brain regions**: Handle multi-region recordings appropriately
- **Session merging**: Decide if/how to combine multiple recording sessions

### Data Quality
- Handle incomplete trials or missing data
- Identify and handle outlier neurons or sessions
- Deal with variable trial counts across subjects
- Address timing inconsistencies

### Computational Efficiency
- Be mindful of memory usage with large datasets
- Use appropriate data types (float32 vs. float64)
- Consider lazy loading for very large datasets
- Implement efficient array operations (vectorization)

## Working with the User

- **Ask clarifying questions** when the data structure is ambiguous
- **Propose solutions** with clear trade-offs when multiple approaches are viable
- **Validate assumptions** about what variables mean and how they should be processed
- **Show examples** of converted data to verify it matches expectations
- **Be proactive** in identifying potential issues or edge cases

## Common Dataset Types

You may encounter:
- **IBL (International Brain Laboratory)**: Neuropixels recordings with wheel-based decision tasks
- **NWB (Neurodata Without Borders)**: Standardized format, may need restructuring
- **DANDI Archive**: Various formats and tasks
- **Custom formats**: Lab-specific MATLAB, Python, or HDF5 files

## Tools and Libraries

Commonly useful:
- `numpy`: Array operations
- `scipy`: Signal processing, interpolation
- `h5py`: HDF5 file handling
- `pandas`: Tabular data manipulation
- `xarray`: Labeled multi-dimensional arrays
- Dataset-specific APIs (ONE-api for IBL, pynwb for NWB, etc.)

## Success Criteria

A successful conversion should:
1. Match the target data structure exactly
2. Preserve all relevant information from the source
3. Have consistent dimensions across trials/subjects
4. Include complete and accurate metadata
5. Be reproducible with documented code
6. **Pass all validation checks**:
   - Data summary shows correct structure
   - Visual inspection reveals no artifacts
   - Decoder achieves near-perfect training performance (overfitting check)
   - Decoder generalizes reasonably in cross-validation
   - Any validation failures are investigated and resolved
7. Include comprehensive CONVERSION_NOTES.md documenting all decisions and validation results
8. Have a clean final directory structure with cache folder
9. Provide user-friendly README.md for using the converted data

## Getting Started

When the user presents a new dataset:
1. **Create CONVERSION_NOTES.md** to start documenting the process
2. Ask for the data source and format
3. Request access to explore the data structure
4. Identify all available task variables
5. **Ask the user**: Which variables should be decoder inputs vs outputs?
   - Present the options clearly
   - Explain the distinction: inputs = context for decoder, outputs = what to decode
6. Propose a conversion approach
7. Document decisions in CONVERSION_NOTES.md as you work
8. **Perform comprehensive validation**:
   - Data summary (`print_data_summary`)
   - Visual inspection (`plot_trial` for each output value)
   - Create `show_processing()` to visualize preprocessing steps
   - Overfitting check (train and predict on all data)
   - Cross-validation check (assess generalization)
9. Investigate any validation failures before finalizing
10. Organize and clean up files at the end (cache folder, final README)

Remember: The goal is not just to convert data, but to test how effectively Claude Code can assist with this complex, domain-specific task. Be thorough, ask good questions, and document your reasoning throughout the process.
