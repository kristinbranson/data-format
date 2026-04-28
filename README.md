# Data Organization with Coding Agents

## Overview

This project explores the use of Coding Agents to help reorganize and reformat different neuroscience datasets into a desired format. 
The goal is to test how well Coding Agents can help with the process of working with heterogeneous datasets by converting them into a common structure suitable for downstream analysis.

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
- **output**: Behavioral readouts that serve as the response variable (e.g., choice, reaction time)
- **metadata**: Descriptive information about the dataset, task, and recording parameters

## Datasets

We cover 8 neuroscience datasets spanning calcium imaging and electrophysiology across a range of behavioral tasks.

1. **`allen2p`** — 2-photon calcium imaging of mouse visual cortex during a natural-scene change-detection task ([Allen Brain Observatory: Visual Behavior 2P](https://portal.brain-map.org/circuits-behavior/visual-behavior-2p)).
2. **`hasnain2024`** — Mouse ALM/tjM1 recordings during a two-context directional-licking task that alternates between auditory-cued and water-cued blocks ([Hasnain et al., 2024](https://doi.org/10.1038/s41593-024-01859-1)).
3. **`lee2025`** — Miniscope calcium imaging of mouse hippocampal CA1 during free exploration of geometrically distinct environments ([Lee et al., 2025](https://doi.org/10.1016/j.neuron.2024.10.027)).
4. **`majnik2025`** — Longitudinal 2-photon imaging of developing mouse barrel cortex (P8–P14), with the same neurons tracked across days via Track2P ([Majnik et al., 2025](https://doi.org/10.7554/eLife.107540)).
5. **`map`** — Multi-region Neuropixels recordings during a memory-guided directional-licking task with auditory cue and delay period ([Chen et al., 2024](https://www.cell.com/cell/fulltext/S0092-8674(23)01445-9)).
6. **`mouseland`** — 2-photon mesoscope recordings across mouse visual areas during a two-corridor visual-discrimination task in virtual reality ([Zhong et al., 2025](https://doi.org/10.1038/s41586-025-09180-y)).
7. **`sosa2024`** — 2-photon calcium imaging of mouse CA1 during a virtual linear-track task with hidden reward zones that switch across days ([Sosa et al., 2025](https://doi.org/10.1038/s41593-025-01985-4)).
8. **`zhang2025`** — IBL Neuropixels sessions used to decode choice, prior, wheel speed, and whisker motion energy ([Zhang et al., 2025](https://doi.org/10.1016/j.neuron.2025.10.026)).
