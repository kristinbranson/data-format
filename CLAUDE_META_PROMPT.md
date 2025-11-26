# Meta Prompt for Claude Code: Neuroscience Data Standardization Project

## Project Context

You are assisting with a project that tests how well Claude Code can help reorganize and reformat heterogeneous neuroscience datasets into a unified, standardized format. The project has two main goals:

**Primary Goal**: Test Claude Code's ability to work with diverse neuroscience datasets and convert them into a common structure suitable for downstream analysis.

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
            input_data,  # stimulus/task variables (with or without time dimension)
            ...
        ],
        ...
    ],

    'output': [  # list of subjects
        [  # list of trials for subject 1
            output_data,  # behavioral response (with or without time dimension)
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

- **input**: Task/stimulus variables that serve as inputs
  - Examples: stimulus contrast, position, orientation, timing
  - Can be time-varying (n_timepoints,) or scalar values per trial
  - Should capture all relevant task information

- **output**: Behavioral or task outputs to be decoded
  - Examples: choice (left/right), reaction time, lick times
  - Can be time-varying or discrete values per trial
  - This is typically what we want to predict from neural data

- **metadata**: Descriptive information
  - At minimum: task_description (str), brain_regions (str)
  - Add other relevant fields: sampling_rate, time_bin_size, session_info, etc.

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
  - What represents task inputs/stimuli?
  - What represents behavioral outputs/responses?
  - What metadata should be preserved?
- Identify any preprocessing needed (binning, alignment, filtering)
- Note any edge cases or data quality issues

### 3. Script Development
- Write clear, well-documented conversion functions
- Handle missing data gracefully
- Validate data shapes and types at each step
- Include sanity checks (e.g., trial counts match across arrays)
- Make code modular and reusable

### 4. Validation
- Verify converted data structure matches specification
- Check that dimensions are consistent across trials/subjects
- Ensure no data loss during conversion
- Validate that metadata accurately describes the data
- Create visualizations to spot-check conversions

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
6. Pass validation checks
7. Include comprehensive CONVERSION_NOTES.md documenting all decisions
8. Have a clean final directory structure with cache folder
9. Provide user-friendly README.md for using the converted data

## Getting Started

When the user presents a new dataset:
1. **Create CONVERSION_NOTES.md** to start documenting the process
2. Ask for the data source and format
3. Request access to explore the data structure
4. Clarify the task: What is input? What is output?
5. Propose a conversion approach
6. Document decisions in CONVERSION_NOTES.md as you work
7. Iterate based on feedback
8. Organize and clean up files at the end (cache folder, final README)

Remember: The goal is not just to convert data, but to test how effectively Claude Code can assist with this complex, domain-specific task. Be thorough, ask good questions, and document your reasoning throughout the process.
