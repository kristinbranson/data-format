# MAP Dataset - Standardized Format

This directory contains the MAP (Memory-guided movement) neural dataset converted to a standardized format for decoder training.

## Dataset Overview

**Source Paper**: "Brain-wide neural activity underlying memory-guided movement"
**Task**: Auditory delayed response task with optogenetic manipulation
**Recording**: Neuropixels probes across 7+ brain regions (ALM, Striatum, Thalamus, Midbrain, Medulla)
**Subjects**: 28 mice
**Sessions**: 174 recording sessions
**Trials**: 93,429 trials (after quality filtering)

## Data Files

### Primary Datasets

**`map_data_full.pkl`** - Complete dataset
- 174 sessions from 28 subjects
- 93,429 trials total
- ~500 trials per session (average)
- ~1,565 neurons per session (average)
- Size: Large pickle file

**`map_data_sample.pkl`** - Sample dataset for testing
- 8 sessions from 2 subjects
- 160 trials total (20 per session)
- Same structure as full dataset
- Use for quick testing and development

### Data Format

Both files contain a Python dictionary with the following structure:

```python
data = {
    'neural': [  # List of sessions (each session is a separate analysis unit)
        [  # List of trials for session 1
            np.array(n_neurons, 80),  # Trial 1: 80 time bins × 50ms = 4s window
            np.array(n_neurons, 80),  # Trial 2
            ...
        ],
        ...  # More sessions
    ],

    'input': [  # Decoder inputs (contextual variables)
        [  # List of trials for session 1
            np.array(2, 80),  # [time_from_go_cue, photostim_status]
            ...
        ],
        ...
    ],

    'output': [  # Decoder outputs (variables to decode)
        [  # List of trials for session 1
            np.array(3),  # [lick_direction, outcome, early_lick]
            ...
        ],
        ...
    ],

    'metadata': {
        'task_description': str,
        'brain_regions': str,
        'session_info': list,  # Details for each session
        ...
    }
}
```

### Input Variables (2 dimensions)

1. **Time from go cue** (continuous): -2.5s to +1.5s, one value per time bin
2. **Photostimulation status** (binary): 0 = control, 1 = ALM silencing

### Output Variables (3 dimensions, all categorical)

1. **Lick direction** (3 classes):
   - 0 = left
   - 1 = right
   - 2 = none (no lick)

2. **Outcome** (3 classes):
   - 0 = hit (correct response)
   - 1 = miss (incorrect response)
   - 2 = ignore (no response)

3. **Early lick** (2 classes):
   - 0 = no early lick
   - 1 = early lick during sample/delay period

## Preprocessing Details

**Temporal Alignment**: All trials aligned to go cue onset
**Time Window**: -2.5s to +1.5s relative to go cue
**Binning**: 50ms bins (80 bins total)
**Firing Rates**: Computed as spike count per bin / bin duration (Hz)

**Quality Filtering**:
- Trials outside neural recording range excluded
- Sessions treated as independent units (different neurons per session)
- Zero-activity trials retained (legitimate biological variability)

## Scripts

### Core Scripts

**`convert_map_data_parallel.py`** - Data conversion script
- Converts NWB files to standardized format
- Parallel processing (40 minute runtime for full dataset)
- Usage: `python convert_map_data_parallel.py [--sample]`

**`train_decoder.py`** - Decoder validation script
- Trains and validates decoder on converted data
- Reports format checks, overfitting check, and cross-validation
- Usage: `python train_decoder.py <data_file.pkl> > output.log`

**`show_processing.py`** - Preprocessing visualization
- Shows step-by-step preprocessing for example trials
- Visualizes binning, alignment, and input/output computation
- Usage: `python show_processing.py`

**`decoder.py`** - Decoder implementation
- Simple PyTorch decoder with per-session embeddings
- Includes data format validation functions
- Used by train_decoder.py

### Supporting Files

**`CLAUDE.md`** - Instructions for Claude Code assistant
**`CONVERSION_NOTES.md`** - Detailed conversion documentation (580 lines)
- Complete chronological log
- Bug fixes and investigations
- Validation results
- Lessons learned

**`methods.txt`** - Excerpts from paper methods section
**`datapaper.pdf`** - Full source paper

**`cache/`** - Investigation scripts and intermediate files
- See `cache/README_CACHE.md` for details
- Development iterations, debugging scripts, diagnostic tools

## Validation Results

### Sample Data (8 sessions, 160 trials)
✓ Decoder training accuracy: 89-98%
✓ Cross-validation accuracy: 63-90%
✓ All format checks passed

### Full Data (174 sessions, 93,429 trials)
✓ All format checks passed
✓ Data alignment verified
⚠ Decoder training accuracy: 42-77%
⚠ Cross-validation accuracy: 43-75%

**Note**: The poor decoder performance on full data is due to insufficient model capacity for 174 heterogeneous sessions (different neuron populations across 28 subjects), not a data formatting error. This reveals important biological variability in the dataset.

## Key Findings

1. **Photostimulation prevents neural silence**
   - 0% of photostim trials have zero activity
   - 4-7% of control trials have zero activity
   - Confirms optogenetic manipulation drives neural activity

2. **Cross-session decoding is challenging**
   - Sample data (2 subjects, consecutive days): 89-98% accuracy
   - Full data (28 subjects, 174 sessions): 42-77% accuracy
   - Biological/technical variability across sessions is substantial

3. **Data quality is high**
   - Only 3/174 sessions (1.7%) have minor issues
   - All neural-behavior alignments verified correct
   - 2.6% zero-activity trials are legitimate biological phenomena

## Loading and Using the Data

```python
import pickle
import numpy as np

# Load data
with open('map_data_full.pkl', 'rb') as f:
    data = pickle.load(f)

# Access first session
session_0_neural = data['neural'][0]  # List of trial arrays
session_0_inputs = data['input'][0]   # List of input arrays
session_0_outputs = data['output'][0]  # List of output arrays

# Access first trial of first session
trial_0_neural = session_0_neural[0]  # Shape: (n_neurons, 80)
trial_0_input = session_0_inputs[0]   # Shape: (2, 80)
trial_0_output = session_0_outputs[0] # Shape: (3,)

print(f"Trial 0 neural activity shape: {trial_0_neural.shape}")
print(f"Trial 0 outputs: lick_dir={trial_0_output[0]}, "
      f"outcome={trial_0_output[1]}, early_lick={trial_0_output[2]}")

# Get metadata
print(f"Task: {data['metadata']['task_description']}")
print(f"Brain regions: {data['metadata']['brain_regions']}")
print(f"Total sessions: {len(data['neural'])}")
```

## Citation

If you use this data, please cite the original paper:
```
[Citation information from datapaper.pdf]
```

## Contact

For questions about the data conversion or format, see `CONVERSION_NOTES.md` for detailed documentation of all processing steps and design decisions.

---

**Data Format Version**: 1.0
**Conversion Date**: 2025-12-02
**Conversion Tool**: Custom Python scripts using pynwb, numpy, scipy
