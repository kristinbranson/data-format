# Neurodata Without Boredom: Benchmarking Agentic AI for Data Reuse

Ling-Qi Zhang and Kristin Branson

## Overview

This project explores the use of coding agents (Claude Code and Codex) to reorganize and reformat diverse neuroscience datasets into a standardized format. The goal is to evaluate how effectively coding agents can handle heterogeneous and messy biological research data by converting them into a common structure suitable for downstream analysis.

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

1. **`allen2p`** — 2-photon calcium imaging of mouse visual cortex during a natural-scene change-detection task ([Allen Brain Observatory: Visual Behavior 2P](https://portal.brain-map.org/circuits-behavior/visual-behavior-2p)). *Format:* NWB files distributed via the AllenSDK.
2. **`hasnain2024`** — Mouse ALM/tjM1 recordings during a two-context directional-licking task that alternates between auditory-cued and water-cued blocks ([Hasnain et al., 2024](https://doi.org/10.1038/s41593-024-01859-1)). *Format:* custom MATLAB `.mat` data structures.
3. **`lee2025`** — Miniscope calcium imaging of mouse hippocampal CA1 during free exploration of geometrically distinct environments ([Lee et al., 2025](https://doi.org/10.1016/j.neuron.2024.10.027)). *Format:* custom MATLAB `.mat` files (per-subject neural + behavior).
4. **`majnik2025`** — Longitudinal 2-photon imaging of developing mouse barrel cortex (P8–P14), with the same neurons tracked across days via Track2P ([Majnik et al., 2025](https://doi.org/10.7554/eLife.107540)). *Format:* raw 2-photon TIFFs plus `suite2p` outputs (`.npy`).
5. **`chen2024`** — Multi-region Neuropixels recordings during a memory-guided directional-licking task with auditory cue and delay period ([Chen et al., 2024](https://www.cell.com/cell/fulltext/S0092-8674(23)01445-9)). *Format:* NWB files distributed via DANDI. In some of the code, this is referred to as **MAP**.
6. **`zhong2025`** — 2-photon mesoscope recordings across mouse visual areas during a two-corridor visual-discrimination task in virtual reality ([Zhong et al., 2025](https://doi.org/10.1038/s41586-025-09180-y)). *Format:* custom per-session `.npy` files (separate neural and behavior arrays). In some of the code, this is referred to as **mouseland**. 
7. **`sosa2024`** — 2-photon calcium imaging of mouse CA1 during a virtual linear-track task with hidden reward zones that switch across days ([Sosa et al., 2025](https://doi.org/10.1038/s41593-025-01985-4)). *Format:* NWB files distributed via DANDI.
8. **`zhang2025`** — IBL Neuropixels sessions used to decode choice, prior, wheel speed, and whisker motion energy ([Zhang et al., 2025](https://doi.org/10.1016/j.neuron.2025.10.026)). *Format:* IBL ONE SDK (cached Parquet / NumPy artifacts).

## Organization

```
data-format/
├── environments/                  # Conda environments for running all code (see environments/README.md)
├── template-harbor-task/          # Template from which all harbor tasks are created
│                                  # (use harbor-scripts/sync_template.py to keep tasks synced)
├── prompt_v4/                     # Final version of the prompt for each task
├── prompts/                       # Older versions of prompts for each task
│   └── harbor_instructions_v4.md  # Template for all v4 prompts
├── manual/                        # Manual solutions to tasks we manually solved
│   └── {task_name}/               # task_name = ['allen2p','lee2025','majnik2025','sosa2024']
│       ├── convert_data.py        # Code for conversion
│       ├── DECISIONS.md           # Manual annotation of our decisions
│       ├── MANUAL_NOTES.md        # Manual notes while coding
│       └── *_out.txt              # stdout captures from code
├── harbor-tasks/                  # Tasks set up for harbor (one subdir per task):
│   └── {task_name}/               # task_name = ['allen2p','hasnain2024','lee2025','majnik2025',
|                                  #              'map', 'mouseland', 'sosa2024', 'zhang2025']
|                                  # Reference code, paper, and data provided to agents
│                                  # Code/paper sources documented below TODO
│                                  # Dataset download setup documented below TODO
├── harbor-scripts/                # Scripts for running harbor, checking status, compiling results
│                                  # (see harbor-scripts/README.md for descriptions)
└── evaluation/                    # Code for and results of manual ranking of agents' decisions
```

## Task reference sources

Each task is based on code, paper, and data from original sources. We have downloaded and included the **papers** and **code** from these sources in `harbor-tasks/{task-name}environment/`. Sources of these are:
```
harbor-tasks/
├── allen2p/
|   └── environment/
|       ├── code/                   # AllenSDK cloned from https://github.com/AllenInstitute/AllenSDK
|       ├── paper.pdf               # "Behavioral strategy shapes activation of the Vip-Sst
|       |                           #  disinhibitory circuit in visual cortex" by Piet, et al., Neuron 2024
|       |                           # https://doi.org/10.1016/j.neuron.2024.02.008
|       ├── whitepaper.pdf          # "Allen Brain Observatory: Visual Behavior 2P - Technical Whitepaper"
|       |                           # https://brain-map.org/our-research/circuits-behavior/visual-behavior
|       ├── methods.txt             # Text copied from papers above
├── hasnain2024/
|   └── environment/
|       ├── code/                   # Cloned from https://github.com/economolab/HasnainBirnbaum2024.git
|       ├── paper.pdf               # "Separating cognitive and motor processes in the behaving mouse"
|       |                           # by Hasnain, et al., Nature Neuroscience 2024
|       |                           # https://doi.org/10.1038/s41593-024-01859-1
|       ├── methods.txt             # Text copied from paper above
├── lee2025/
|   └── environment/
|       ├── code/                   # Cloned from https://github.com/jquinnlee/georepca1.git
|       ├── paper.pdf               # "Identifying representational structure in CA1 to benchmark
|       |                           #  theoretical models of cognitive mapping"
|       |                           # by Lee, et al., Neuron 2025
|       |                           # https://doi.org/10.1016/j.neuron.2024.10.027
|       ├── methods.txt             # Text copied from paper above
├── majnik2025/
|   └── environment/
|       ├── code/                   # Cloned from https://github.com/juremaj/track2p.git
|       ├── paper.pdf               # "Longitudinal tracking of neuronal activity from the same cells
|       |                           #  in the developing brain using Track2p"
|       |                           # by Majnik et al., eLife 2025
|       |                           # https://doi.org/10.7554/eLife.107540
|       ├── methods.txt             # Text copied from paper above
├── map/
|   └── environment/
|       ├── code/                   # Cloned from https://github.com/druckmann-lab/MapVideoAnalysis.git
|       ├── datapaper.pdf           # "Brain-wide neural activity underlying memory-guided movement"
|       |                           # by Chen, et al., Cell 2024
|       |                           # https://doi.org/10.1016/j.cell.2023.12.035
|       ├── methodpaper.pdf         # "Brain-wide analysis reveals movement encoding structured across
|       |                           #  and within brain areas"
|       |                           # by Wang, et al., Nature Neuroscience 2025
|       |                           # https://doi.org/10.1038/s41593-025-02114-x
|       ├── ChenLiuEtAl2023_SpikeSortingQC.pdf # "Spike sorting and quality control for the 
|       |                           # mesoscale activity map project" by Chen, et al., 2023
|       |                           # https://doi.org/10.25378/janelia.24066108
|       ├── methods.txt             # Text copied from papers above
├── mouseland/
|   └── environment/
|       ├── code/                   # Cloned from https://github.com/MouseLand/zhong-et-al-2025
|       ├── paper.pdf               # "Unsupervised pretraining in biological neural networks"
|       |                           # by Zhong, et al., Nature 2025
|       |                           # https://doi.org/10.1038/s41586-025-09180-y
|       ├── methods.txt             # Text copied from paper above
├── sosa2024/
|   └── environment/
|       ├── code/                   # cloned from https://github.com/GiocomoLab/Sosa_et_al_2024.git
|       ├── paper.pdf               # "A flexible hippocampal population code for experience relative
|       |                           #  to reward" by Sosa, et al., Nature Neuroscience 2025
|       |                           # https://doi.org/10.1038/s41593-025-01985-4
|       ├── methods.txt             # Text copied from paper above
├── zhang2025/
|   └── environment/
|       ├── code/
|       |   ├── code_zhang2025/     # Cloned from https://github.com/yzhang511/neural_decoding.git
|       |   └── ibllib/             # Cloned from https://github.com/int-brain-lab/ibllib.git
|       ├── datapaper.pdf           # "A brain-wide map of neural activity during complex behaviour"
|       |                           # by International Brain Laboratory, Nature 2025
|       |                           # https://doi.org/10.1038/s41586-025-09235-0
|       ├── methodpaper.pdf         # "Exploiting correlations across trials and behavioral sessions
|       |                           #  to improve neural decoding"
|       |                           # https://doi.org/10.1016/j.neuron.2025.10.026
|       |                           # by Zhang, Lyu, Hurwitz et al., 2025
|       ├── dataarchitecture.pdf    # "Data architecture for a large-scale neuro-behavioral
|       |                           # experiment" — International Brain Lab, bioRxiv 2020
|       |                           # https://www.biorxiv.org/content/10.1101/827873v3
|       ├── methods.txt             # Text copied from papers above

```
## Data sources and downloading

Data are not included in this repository because of their size. Data are expected to be organized as follows:
```
data-format
└── data/
    ├── allen2p/
    |   └── visual-behavior-ophys-1.1.0
    ├── hasnain2024/
    ├── lee2025/
    ├── majnik2025/
    ├── map/
    ├── mouseland/
    ├── sosa2024/
    ├── zhang2025/
```

```bash
  # single task
  python download/download.py allen2p

  # multiple tasks
  python download/download.py hasnain2024 lee2025 majnik2025

  # everything
  python download/download.py --all

  # single task with custom output dir
  python download/download.py allen2p -o /scratch/allen2p
```

If any one task fails, the rest still run; failures are listed at the end and the exit code is non-zero. 
If you don't pass -o flag, data is downloaded to `data/<task>/` relative to the repo root.

Data sources:
- **allen2p**: [Allen Brain Observatory: Visual Behavior 2P](https://portal.brain-map.org/circuits-behavior/visual-behavior-2p) (via AllenSDK S3 cache).
- **hasnain2024**: https://zenodo.org/records/13941415
- **lee2025**: https://zenodo.org/records/13993254
- **majnik2025**: https://zenodo.org/records/17091226
- **map**: https://dandiarchive.org/dandiset/000363
- **mouseland**: https://figshare.com/articles/dataset/Unsupervised_pretraining_in_biological_neural_network/28811129
- **sosa2024**: https://dandiarchive.org/dandiset/001361
- **zhang2025**: IBL Neuropixels (reproducible-ephys release), via the public openalyx IBL server.
