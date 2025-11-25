# Data Organization with Claude Code

## Overview

This project explores the use of Claude Code to help reorganize and reformat different neuroscience datasets into a desired format. The goals are:
1. Test how well Claude Code can help with the process of working with heterogeneous datasets by converting them into a common structure suitable for downstream analysis.
2. (More ambitious) See how well we can train a decoder that generalizes across tasks and brain regions to decode behavioral output (decision) from neural recordings.

## Target Data Format

All datasets are converted into a consistent Python dictionary structure:

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

### Format Specifications

- **neural**: Neural activity data organized by subject and trial, with consistent dimensions (neurons × time)
- **input**: Task/stimulus variables that serve as inputs to the system (e.g., stimulus properties)
- **output**: Behavioral or neural readouts that serve as the response variable (e.g., choice, reaction time)
- **metadata**: Descriptive information about the dataset, task, and recording parameters

## Datasets

### 1. International Brain Laboratory (IBL) Dataset

**Reference**: [Nature, 2025](https://www.nature.com/articles/s41586-025-09235-0)

**Status**: Planned

**Source**: IBL brain-wide Neuropixels recordings

**Conversion Details**:
- **Input**: Stimulus contrast and position
- **Output**: Subject choice (left/right wheel turn)
- **Neural data**: Spike times from multiple brain regions (mice)
- **Metadata**:
  - Task description: "Visual discrimination task with wheel turn response"
  - Brain regions: [To be determined from data]

**Files**:
- `IBLPrior/Imbizo_2023.py`: Original IBL analysis notebook
- `IBLPrior/environment.yml`: Environment specification with IBL dependencies

### 2. Zhong et al., 2025 Dataset

**Reference**: [Nature, 2025](https://www.nature.com/articles/s41586-025-09180-y)

**Status**: Planned

**Source**: [To be added]

**Conversion Details**:
- **Input**: [To be determined]
- **Output**: [To be determined]
- **Neural data**: [To be determined]
- **Metadata**:
  - Task description: [To be determined]
  - Brain regions: [To be determined]