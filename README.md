# Neurodata Without Boredom: Benchmarking Agentic AI for Data Reuse

Ling-Qi Zhang (zhangl5@janelia.hhmi.org)
Kristin Branson (kristinbranson@gmail.com)

## Overview

This project explores the use of coding agents (Claude Code and Codex) to reorganize and reformat diverse neuroscience datasets into a standardized format. The goal is to evaluate how effectively coding agents can handle heterogeneous and messy biological research data by converting them into a common structure suitable for downstream analysis.

 The benchmark bundles **8 published neuroscience datasets** (calcium imaging and electrophysiology, across mice doing visual, navigation, and decision tasks) together with a single standardized target format, a neural-decoder verifier that scores the converted data quantitatively, and a pair of LLM-as-judge agents that score the agent's *choices and code* qualitatively. Four datasets have hand-written human reference solutions (the *supervised* tasks); the other four have only the paper and code as ground truth (the *unsupervised* tasks). Tasks run in isolated docker containers via [Harbor](https://github.com/harbor-framework/harbor), so any new agent can be plugged in and scored end-to-end.

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

 ## Prerequisites

- **OS**: Developed for Linux. (The verifier pipeline assumes Linux paths; macOS may work for the Python parts but `docker compose` mounts and `dandi`'s NFS-aware caching have not been tested elsewhere.)
- **GPU**: Developed with a single CUDA-capable GPU with ≥ 24 GB VRAM for the verifier's decoder training. The environment pins `torch 2.9.1+cu128`; if your driver doesn't support CUDA 12.8, you'll need to swap the torch wheel index in `environment/minimal_environment.yaml`. CPU-only runs work with `--cpu` on `train_decoder.py`, will need to change `test.sh` scripts accordingly.
- **RAM**: Code requires loading entire dataset into RAM.
- **Container runtime**: either Docker (default) with `nvidia-container-toolkit` for GPU passthrough, or Podman with `podman-compose` (the env yaml installs `podman-compose`; pass `--podman` to `run_harbor.sh`).
- **Conda / mamba** for the Python environment (Miniforge / Miniconda / mambaforge all work).
- **Disk space**: ≥ 50 GB free per task you download; ~1.4 TB free if downloading everything.
- **API access** for running real LLM agents:
  - `ANTHROPIC_API_KEY` (or a Claude Code OAuth token in `~/.claude/.credentials.json`) for the Claude agent and Claude judge. 
  - `OPENAI_API_KEY` (or a Codex auth.json in `~/.codex/`) for the Codex agent and Codex judge.
  - Not needed for `--agent oracle`.

 ## Quickstart

Run the oracle (reference solution) on one task to verify your setup, then point any LLM agent at the same task.

1. Setup your environment. Check which version of pytorch you want to setup, and modify the `environment.yaml` file
```bash
conda env create -f environment/minimal_environment.yaml
conda activate data-format
```
2. Download one dataset (~16 GB for hasnain2024)
```bash
mkdir -p data
python download/download.py hasnain2024
```
3. Run the oracle agent — runs the reference `convert_data.py` + verifier
```bash 
harbor-scripts/run_harbor.sh --agent oracle --task hasnain2024
```

4. Check the result
```bash
python harbor-scripts/check_trial_health.py
```

Results land in `~/harbor-tasks/data-format/jobs/<task>/<agent>/<timestamp>_trial<N>/`, with:
- `verifier/snapshot/` — the agent's convert_data.py + the converted *.pkl files + captured stdout
- `verifier/metrics.json` — quantitative scores (decoder accuracy, dataset-stat match, judge rewards)
- `verifier/judge/{claude,codex}/` — the LLM judges' decisions

To run a real LLM agent instead of the oracle, swap --agent oracle for --agent claude or --agent codex (requires ANTHROPIC_API_KEY / OPENAI_API_KEY in env, or --apikeys pointing at a .env file). To sweep multiple tasks × agents, see harbor-scripts/job_config.yaml.

The smallest tasks for first-run testing are lee2025 (15 GB) and hasnain2024 (16 GB); the largest is zhang2025 (566 GB). Full benchmark download is ~1.4 TB — see Data sources and downloading below.

## Organization

```
data-format/
├── data/                          # Root directory of data
├── download/                      # Code for downloading data
├── environment/                   # Conda environment for running all code
├── evaluation/                    # Code for and results of manual ranking of agents' decisions
├── harbor-tasks/                  # Tasks set up for harbor (one subdir per task):
│   └── {task_name}/               # task_name = ['allen2p','hasnain2024','lee2025','majnik2025',
|                                  #              'map', 'mouseland', 'sosa2024', 'zhang2025']
|                                  # Reference code, paper, and data provided to agents
│                                  # Code/paper sources documented below TODO
│                                  # Dataset download setup documented below TODO
├── harbor-scripts/                # Scripts for running harbor, checking status, compiling results
│                                  # (see harbor-scripts/README.md for descriptions)
├── template-harbor-task/          # Template from which all harbor tasks are created
│                                  # (use harbor-scripts/sync_template.py to keep tasks synced)
├── manual/                        # Manual solutions to tasks we manually solved
│   └── {task_name}/               # task_name = ['allen2p','lee2025','majnik2025','sosa2024']
│       ├── convert_data.py        # Code for conversion
│       ├── DECISIONS.md           # Manual annotation of our decisions
│       ├── MANUAL_NOTES.md        # Manual notes while coding
│       └── *_out.txt              # stdout captures from code
├── prompt_v4/                     # Final version of the prompt for each task
└── prompts/                       # Older versions of prompts for each task
    └── harbor_instructions_v4.md  # Template for all v4 prompts
```

## Task reference paper and code sources

Each task is based on code, paper, and data from original sources. We have downloaded and included the **papers** and **code** from these sources in `harbor-tasks/{task-name}/environment/`. Sources of these are:
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

 ## Conda environments

Three conda environment YAMLs live in `environment/` (see `environment/README.md` for the file-level
summary):

| File | Resulting env name | Purpose |
|---|---|---|
| `minimal_environment.yaml` | `data-format` | **Recommended.** A minimal, post-hoc env that pins every  dependency this repo's own code (download scripts, decoder, verifier, harbor harness) needs. Use this unless it doesn't work... |
| `decoder-data-format_freeze_full_environment.yaml` | `decoder-data-format` | Full `pip freeze` of the env used while developing and testing `decoder.py`. Kept for reproducibility; superseded by `minimal_environment.yaml`. |
| `eval-data-format_freeze_full_environment.yaml` | `eval-data-format-podman` | Full `pip freeze` of the env used while running the harbor harness (oracle/agent/judge trials) against the eight tasks. Kept for reproducibility. |

All environments have PyTorch (CUDA 12.8): torch==2.9.1+cu128, torchvision==0.24.1+cu128, pulled from the PyTorch CUDA-12.8 wheel index. On a CPU-only or machine with an older version of CUDA, you may need to swap the index URL and the +cu128 suffix accordingly.

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

**Disk-space required**: roughly **1.4 TB total** to download all 8 datasets. Per-task sizes:

| Task | Source | Approx. on-disk size |
|---|---|---:|
| `allen2p` | [Allen Brain Observatory: Visual Behavior 2P](https://portal.brain-map.org/circuits-behavior/visual-behavior-2p) (via AllenSDK S3 cache) | 247 GB |
| `hasnain2024` | https://zenodo.org/records/13941415 | 16 GB |
| `lee2025` | https://zenodo.org/records/13993254 | 15 GB |
| `majnik2025` | https://zenodo.org/records/17091226 | 16 GB |
| `map` | https://dandiarchive.org/dandiset/000363 | 50 GB |
| `mouseland` | https://figshare.com/articles/dataset/Unsupervised_pretraining_in_biological_neural_network/28811129 | 412 GB |
| `sosa2024` | https://dandiarchive.org/dandiset/001361 | 87 GB |
| `zhang2025` | IBL Neuropixels (reproducible-ephys release, public openalyx server) | 566 GB |
| **Total** | | **~1.4 TB** |

## Task

### Target Data Format

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

**Output format specifications**:
- **neural**: Neural activity data organized by subject and trial, with consistent dimensions (neurons × time)
- **input**: Task/stimulus variables that serve as inputs to the system (e.g., stimulus properties)
- **output**: Behavioral readouts that serve as the response variable (e.g., choice, reaction time)
- **metadata**: Descriptive information about the dataset, task, and recording parameters

### Downstream task

Each converted dataset is evaluated by training a neural decoder that maps the standardized `data['neural']` to `data['output']`. The decoder code and runner are bundled into every harbor task and are identical across tasks; the canonical copies live at:
- **`template-harbor-task/environment/decoder.py`** — the decoder library. Exposes `verify_data_format`, `print_data_summary`, `train_decoder`, `predict`, `cross_validate_decoder`, `train_validate_decoder`, `accuracy_all_sessions`, `f1scores_all_sessions`, and plotting helpers. The default model (`_train_decoder_pca_logistic`) projects the per-session neural matrix to a fixed number of PCs and fits an L1-regularized logistic regression per output dimension; outputs are assumed categorical and chance is computed from the training-set class fractions.

- **`template-harbor-task/environment/train_decoder.py`** — the entry point. Loads a `data.pkl` (the conversion artifact the agent produces), verifies the dict structure with `verify_data_format`, prints a summary, runs `train_validate_decoder` on a 70/30 train/test split, and reports balanced accuracy per output dimension against chance.

The same decoder.py and train_decoder.py are also propagated into each harbor task at harbor-tasks/<task>/environment/ (use `harbor-scripts/sync_template.py` to keep them in sync with the template).

Usage (run inside each task's container against the agent's converted data):
```bash
python train_decoder.py /app/converted_data.pkl
# inspect the data format / sample plots without training:
python train_decoder.py /app/converted_data.pkl --verify-only --plot-samples
# write all stats to JSON for the verifier to consume:
python train_decoder.py /app/converted_data.pkl --stats-json stats.json
# force CPU (some tasks build a CUDA-less image):
python train_decoder.py /app/converted_data.pkl --cpu
```

## Prompts

Final (v4) versions of the prompts are in `prompt_v4`. Earlier drafts are in `prompts`. All prompts follow the same structure:
1. **Task definition.** What `data['input']` and `data['output']` of the trained decoder should be for *this* task (per-task list of variables to derive from the raw data, e.g. *running speed*, *trial outcome*, *image change*, *reward zone position*).
2. **Target format.** The exact `data` dict layout (`neural`, `input`, `output`, `metadata`) and dimension conventions.
3. **Reference inputs** the agent is given:
  - `paper.pdf` — the original paper (or two papers, for `map` and `zhang2025`)
  - `methods.txt` — relevant methods excerpts copied out of the paper
  - `code/` — the upstream paper's code repository
  - `data/` — the raw data
4. **Conversion workflow** — an 11-step procedure the agent must follow in order:
    | Step | What it does |
    |---|---|
    | 0 | Setup; create `CONVERSION_NOTES.md` immediately to document every decision |
    | 1 | Read the reference code |
    | 2 | Explore the dataset |
    | 3 | Read the reference paper / methods text |
    | 4 | Check consistency between code, paper, and data |
    | 5 | Plan the mapping from raw fields → target format |
    | 6 | Write `convert_data.py` |
    | 7 | Run on a sample (`--sample`); validate format and time it |
    | 8 | Train the decoder on the sample; verify above-chance accuracy |
    | 9 | Run full conversion; check dataset statistics against the reference text |
    | 10 | Critical review (self-audit pass) |
    | 11 | Full decoder training run on the converted data |

## Harbor tasks

- Each dataset is exposed to the agent as a harbor task in `harbor-tasks/<task>/`. All tasks share a common layout (based on `template-harbor-task/`). 
- Steps to construct the task from the template are in `harbor-tasks/setup_harbor_task.md`. 
- The agent's job for each task is to:
  - Read the paper and reference code, understand the data. 
  - Write a `convert_data.py`, and produce `converted_data.pkl` in the standardized format. 
  - `converted_data.pkl` wil be input to `train_decoder.py` to train a neural decoder. 
- After the agent finishes:
  - A snapshot of the agent's /app working tree is stored
  - Verifier runs pytest test_outputs.py to validate:
    - The output format
    - Compute decoder accuracy
    - Supervised-only:
      - Whether the dataset properties match the manual solution's
      - Whether the decoder accuracies match the manual solution's 
  - Run claude-code and codex agent judge with `judge_instructions.md`

`harbor-tasks/debug` is a nothing task used to debug the harbor setup.

### Harbor task layout

```
{task}/
├── task.toml                              # Harbor manifest: timeouts, CPU/memory/storage,
│                                          # internet access, MCP servers, env-var passthrough.
├── instruction.md                         # The prompt given to the agent at run time.
├── environment/                           # Built into the docker image for both agent and verifier.
│   ├── Dockerfile
│   ├── docker-compose.yaml                # Mounts data/{task} at /app/data.
│   ├── paper.pdf, methods.txt             # Reference paper + extracted methods section
│   │                                      # (or datapaper.pdf + methodpaper.pdf for map/zhang2025).
│   ├── code/                              # Upstream paper code (see "Task reference sources").
│   ├── decoder.py                         # Decoder library copied from template.
│   └── train_decoder.py                   # Decoder runner copied from template.
├── solution/                              # Reference solution used by the oracle agent.
│   ├── solve.sh                           # Driver: runs convert_data.py (sample + full)
│   │                                      # and train_decoder.py, captures stdout.
│   └── convert_data.py                    # Supervised tasks: hand-written reference conversion
|                                          # Unsupervised tasks: dummy solution for debugging
└── tests/                                 # The verifier (does not run during the agent phase).
    ├── test.sh                            # Verifier entry point: pytest + LLM judges + reward.
    ├── test_outputs.py                    # Pytest: format validation + decoder accuracy
    ├── decoder.py                         # Decoder library copied from template.
    ├── train_decoder.py                   # Decoder runner copied from template.
    ├── compute_reward.py                  # Maps an LLM judge's decision labels to a numeric reward.
    ├── judge_instructions.md              # Prompt given to the claude-code/codex judges. 
    |                                      # Supervised for supervised tasks, unsupervised for unsupervised tasks
    ├── judge_instructions_unsupervised.md # Supervised only: Additional judge instructions for an unsupervised judge
    ├── reference_convert_data.py          # Supervised only: Gold-standard solution written by human
    ├── reference_DECISIONS.md             # Supervised only: Decisions by the human
    ├── reference_stats_full.json          # Supervised only: Statistics of gold-standard reference dataset solution
    └── instruction_reference.md           # The agent's instruction.md, copied here for the judge.
```

### Automatic task scoring

Task verification is run by `tests/test.sh` which:
- Runs `pytest test_outputs.py` to quantitatively assess solutions
- Runs LLM-agents as judges

The eight tasks split into two scoring regimes:

| Regime | Tasks | 
|---|---|
| **Supervised**: gold-standard reference solution exists | `allen2p`, `lee2025`, `majnik2025`, `sosa2024` |
| **Unsupervised**: no reference solution | `hasnain2024`, `map`, `mouseland`, `zhang2025` | 

#### Quantitative scoring

For all tasks, the verifier runs `pytest test_outputs.py`, which runs:
- `decoder.py:verify_data_format()`: to verify that the data is properly formatted
- `decoder.py:train_validate_decoder()`: to train the neural decoder

For all tasks, `test_outputs.py` scores the following:
| Test | What it asserts | 
|---|---|
| `test_required_files_exist` | These five files exist in `/app` and are non-empty: `CONVERSION_NOTES.md`, `convert_data.py`, `converted_data.pkl`, `sample_data.pkl`, `README.md`. |
| `test_no_contamination` | None of the agent's `*.py` files contain any of the planted "canary strings". A hit means the agent likely copied/memorized a reference. |
| `test_expected_files_exist` | These six log files exist and are non-empty: `conversion_{sample,full}_out.txt`, `verification_{sample,full}_out.txt`, `train_decoder_{sample,full}_out.txt`. | 
| `test_verify_data_format` | Both `sample_data.pkl` and `converted_data.pkl` pass `decoder.verify_data_format` (correct dict shape, types, dimensions). |

For supervised tasks only, the verifier also scores:
| Test | What it asserts | 
|---|---|
| `test_data_stats` | Dataset *summary statistics* match (see below) |
| `test_decoder_accuracy` | Decoder accuracy >= 95% of reference accuracy for each output variable |

Dataset *summary statistics* tested:
The following statistics must match exactly:
- `nsubjects`: Number of subjects (mice)
- `dinput`: Number of input variables
- `doutput`: Number of output variables
- The following statistics must be within 10% of the reference dataset's statistics:
  - `nsessions`: Total number of sessions 
  - `ntrials_total`: Total number of trials
  - `nneurons_total`: Total number of neurons across sessions
  - `T_median`: Median trial length
- Input and output variables are matched between the agent and reference solutions based on a combination of:
  - Semantic similarity between their names
  - Range of values
  - Distribution of values (output variables only)
- Output ranges for corresponding variables must match exactly

**Tunable thresholds** defined at the top of `test_outputs.py`:
| Constant | Default | Meaning |
|---|---|---|
| `STATLIMITS['nsessions_ratio']` etc. | 0.1 | Allowed fractional deviation from reference (10%). `nsubjects_ratio: 0` = exact match. |
| `STATLIMITS['input_match_cost']` | 1 | Max mean Hungarian-match cost for input variables. |
| `STATLIMITS['output_match_cost']` | 1 | Max mean Hungarian-match cost for output variables. |
| `MIN_ACCURACY_FRAC` | 0.95 | Required ratio of submitted to reference balanced accuracy per output dimension. |

#### LLM-agent as a judge

For all tasks, the verifier asks **two LLM agents** to judge the agent's work — one claude code + Opus 4.6 and one codex + GPT-5.4. Each judge gets the prompt (`tests/judge_instructions.md`) and runs as a full agentic sandbox inside the verifier container (`claude -p` / `codex exec` with bypass-permissions), with read access to the original instruction, the agent's code and outputs, the agent's trajectory, and the reference materials.

Each judge runs a two-step task:
1. **Document.** Read the agent's `convert_data.py`, `CONVERSION_NOTES.md`, and (optionally) the trajectory in `/logs/agent/trajectory.json`, then fill in a `DECISIONS.md` that answers ~30–40 numbered questions about the conversion. The questions span:
  - **Data loading and partitioning**: how data is loaded; how it is split into subjects / sessions / trials.
  - **Neural processing**: how neural activity is computed and aligned.
  - **Per-input and per-output variables**: which raw fields each is derived from, what processing is applied, how it's discretized into categories (for categorical variables), and how it's aligned to the neural data.
  - **Robustness**: how missing/malformed data is handled.
  - **Code efficiency**: time-consuming steps, vectorizable loops, repeated work, unused computation.
2. **Evaluate.** For each question, write to `llm_judge_eval.json` two ratings with brief justifications:
  - `decision_correctness` — was the agent's choice the right one?
  - `code_correctness` — `CORRECT` / `INCORRECT`: does the code actually implement that choice?

Supervised judges are given access to the reference code and decisions and asked to score decision correctness with the following key:
- `"MATCH"`: AI's decision **matches** the human decision
- `"BETTER"`: AI's decision is **better** than the human decision
- `"OK"`: AI's decision does not match the human decision, but it is **equally as justified**
- `"CONCERNING"`: AI's decision is not technically wrong given ambiguity in the instructions, but it is a concerning choice that should be checked by a human
- `"INCORRECT"`: AI's decision is **incorrect**

Unsupervised judges are **not** given access to the reference, and are asked to score decision correctness with the following key:
- `"MATCH"`: AI's decision **matches** the instructions, reference paper, and code
- `"CONCERNING"`: AI's decision is not technically wrong given ambiguity in the instructions, but it is a concerning choice that should be checked by a human
- `"INCORRECT"`: AI's decision is **incorrect**

After judges run, `compute_reward.py` then maps each label to a scalar reward and merges everything into `metrics.json`:

| Label | Decision reward |
|---|---:|
| MATCH | 1.0 |
| BETTER | 1.0 |
| OK | 0.75 |
| CONCERNING | 0.25 |
| INCORRECT | 0.0 |

| Label | Code reward |
|---|---:|
| CORRECT | 1.0 |
| INCORRECT | 0.0 |

Each judge produces an independent reward, recorded as `llm_judge_claude_reward` and `llm_judge_codex_reward` in `metrics.json`.

For *supervised* tasks, the *unsupervised* judge is run post-hoc with `harbor-scripts/run_unsupervised_judges.sh`. This ensures that reference solutions are **not** provided to the unsupervised judge.

### Template (`template-harbor-task/`)

`template-harbor-task/` is the seed every task is cloned from. It contains the same layout as a real task, minus task-specific reference material (no
`paper.pdf`, no upstream `code/`, no `reference_*` files). Notable extras:

- `environment/synthetic.py` — generates a synthetic toy dataset in the target format. Useful for sanity-checking the decoder/verifier loop
end-to-end without any real data.
- `tests/template_judge_instructions_unsupervised.md` — the starting-point template for unsupervised judge prompts. Per-task `judge_instructions.md`
files are customizations of this.

To propagate template changes (e.g., updates to `decoder.py` or `test_outputs.py`) into every task at once, use:
```bash
python harbor-scripts/sync_template.py --apply
```

## Manual (gold-standard) solutions

For the four **supervised** tasks (`allen2p`, `lee2025`, `majnik2025`, `sosa2024`), Ling-Qi Zhang and Kristin Branson hand-wrote a complete reference conversion before any agent saw the task. These manual solutions are the ground truth that the supervised LLM judges compare each agent's output against, and they provide the reference statistics that `test_outputs.py`'s quantitative checks use.

```
manual/                                # Only the 4 supervised tasks live here
├── allen2p/
├── lee2025/
├── majnik2025/
└── sosa2024/
    ├── convert_data.py                # Hand-written reference conversion
    ├── DECISIONS.md                   # Q-by-Q answers to the same ~30–40
    │                                  # numbered questions the LLM judge asks
    │                                  # (data loading, neural processing,
    │                                  # per-variable derivation, missing-data
    │                                  # handling, code efficiency)
    ├── MANUAL_NOTES.md                # Chronological dev notes from the
    │                                  # human while writing the conversion
    │                                  # (false starts, lookups, gotchas)
    ├── conversion_full_out.txt        # Captured stdout from convert_data.py
    ├── verification_full_out.txt      # Captured stdout from
    │                                  # train_decoder.py --verify-only
    └── train_decoder_full_out.txt     # Captured stdout from train_decoder.py
                                        # (per-output balanced accuracy = the
                                        # numbers the verifier asserts agents
                                        # must reach ≥95% of)
```

## Harbor scripts

The `harbor-scripts/` directory holds the operational tooling — shell and Python scripts for running trials, post-processing them, and propagating template changes. The full per-script reference lives in `harbor-scripts/README.md`; this section is a tour of the most common workflows.

- `harbor-scripts/run_harbor.sh` is used for running the agents and verification through Harbor, e.g.:
```bash
bash harbor-scripts/run_harbor.sh --agent claude --task sosa2024 --ntrials 3
```
- `harbor-scripts/run_unsupervised_judges.sh` runs the unsupervised judges for the supervised tasks.

Other scripts check status, rerun parts that failed for various reasons, sync templates, sync job outputs, generate reference statistics, time code.

See harbor-scripts/README.md for full per-script flag listings and the recommended end-to-end workflows.

## Manual evaluation: Human ratings of agent output

The `evaluation/` directory contains the **human-rater** side of the benchmark — the ground-truth dataset of expert ratings against which we compare the automated LLM-judge scores from `harbor-tasks/<task>/tests/test.sh`. Both supervised and unsupervised tasks are rated by hand using the same `DECISIONS.md` Q&A template that the LLM judges use, so per-question ratings are directly comparable.

```
evaluation/
├── EVAL_RUNBOOK.md                     # Playbook for running the human evaluation
├── DECISIONS.md                        # Reference question list (~30–40 numbered Qs:
│                                       # data loading, neural processing, per-variable
│                                       # derivation, missing-data handling, efficiency)
├── eval/
│   ├── /{task}                         # Per-dataset rating folder, one per task
│   │   ├── claude-code_trial{1,2,3}.md # Human ratings of each claude-code trial
│   │   ├── codex_trial{1,2,3}.md       # Human ratings of each codex trial
│   │   ├── summary.md                  # Per-Q solution-quality summary (rate.py output)
│   │   ├── eval_summary.md             # Human + Claude judge + Codex judge side-by-side
│   │   │                               # (compare.py output, used to score the judges)
│   │   └── report.md                   # Final markdown writeup (report.py output)
│   │
│   ├── rate.py                         # Interactive Q-by-Q rater for supervised tasks
│   │                                   #   (compares trial against manual//DECISIONS.md)
│   ├── rate_blind.py                   # Interactive rater for unsupervised tasks
│   │                                   #   (no reference; rate against paper + code)
│   ├── compare.py                      # Interactive arbitration: for each Q×trial disagreement
│   │                                   # between human / Claude judge / Codex judge, prompt the
│   │                                   # rater to pick the best answer and record it in
│   │                                   # eval_summary.md
│   ├── trial_metrics.py                # Pull verifier metrics.json fields per trial
│   ├── trial_metrics.json              # Aggregated quantitative metrics across all trials
│   ├── report.py                       # Generate per-dataset summary report
│   ├── analysis.ipynb                  # Cross-task aggregate / summary plots for the paper
│   ├── examples.ipynb                  # Scratch notebook: case studies of agent failure modes
│   ├── metrics.ipynb                   # Trial-level verifier metrics (decoder accuracy +
│   │                                   # dataset-scale stats from per-trial metrics.json)
│   └── utils.py                        # Shared helpers
```

See `EVAL_RUNBOOK.md` for a step-by-step procedure to reproduce the evaluation. The short version:

**Manual ratings**. For each task and each of the 3 trials per agent (claude-code and codex), an expert human:

1. Reads the agent's `convert_data.py` and `CONVERSION_NOTES.md` from `harbor-jobs/<task>/<agent>/<timestamp>_trial<N>/verifier/snapshot/`.
2. For every numbered question in `DECISIONS.md` (e.g. *"1-a. How are all the data loaded?"*), records:
  - A rating (`MATCH` / `BETTER` / `OK` / `CONCERNING` / `INCORRECT` for supervised; `MATCH` / `CONCERNING` / `INCORRECT` for unsupervised) — the same labels the LLM judges use.
  - A short note explaining the rating.
3. Writes a per-Q overall comment summarizing how well the agent handled that decision across the three trials.

`rate.py` (supervised) and `rate_blind.py` (unsupervised) drive this loop interactively.

**Expert vs LLM as a judge comparison**:
For every trial, `compare.py` shows the human ratings (from `eval/<task>/*_trial*.md`) alongside the two LLM judges' ratings (from
`harbor-jobs/<task>/<agent>/<trial>/verifier/judge/{claude,codex}/llm_judge_eval.json`) when they disagree. The human expert scores whether they agree more with the human expert (themselves) or the LLM judge. Output is written to `eval_summary.md`.
This allows us to both measure the accuracy of the LLM-agent judges, and to revise the human expert's rating if they notice something while reviewing disagreements. 

## License

The code original to this project is released under the MIT License. See [LICENSE.txt](LICENSE.txt).

The repository also bundles third-party code and paper PDFs from the upstream sources of each benchmark dataset. Those materials remain under their original licenses; in particular:

- **`harbor-tasks/allen2p/environment/code/`** — Allen Institute Software License (BSD-2-clause + non-commercial-redistribution clause).
- **`harbor-tasks/majnik2025/environment/code/`** and **`harbor-tasks/mouseland/environment/code/`** — GPL v3 (copyleft).
- All other vendored code trees are MIT-licensed.
- Paper PDFs and the extracted `methods.txt` excerpts are publisher copyright (Nature, Cell, eLife, bioRxiv, etc.) and are included for benchmark use only.

See `LICENSE.txt` for the full list and the canonical license file shipped inside each vendored subtree.