# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project standardizes heterogeneous neuroscience datasets into a unified format and trains decoders to predict behavioral outputs from neural activity across different subjects and tasks. The codebase focuses on training cross-subject decoders that learn subject-specific neural embeddings and a shared behavioral decoder.

## Environment Setup

**Python Environment**: `decoder-data-format`

The project uses:
- PyTorch for neural network training
- scikit-learn for PCA and logistic regression
- NumPy for array operations
- tqdm for progress bars

## Standard Data Format

All datasets follow this structure:

```python
data = {
    'neural': [  # list of subjects
        [  # list of trials for subject 1
            np.ndarray,  # shape: (n_neurons, n_timepoints), dtype: float32
            ...
        ],
        ...
    ],
    'input': [  # list of subjects
        [  # list of trials for subject 1
            np.ndarray,  # shape: (n_input_dims, n_timepoints), dtype: float32
            ...
        ],
        ...
    ],
    'output': [  # list of subjects
        [  # list of trials for subject 1
            np.ndarray,  # shape: (n_output_dims, n_timepoints), dtype: bool/float32
            ...
        ],
        ...
    ],
    'metadata': {
        'task_description': str,
        'brain_regions': str,
        # additional fields as needed
    }
}
```

**Key conventions**:
- All arrays are organized as (features, time) not (time, features)
- Neural data: `(n_neurons, n_timepoints)` per trial
- Inputs/outputs: `(n_dimensions, n_timepoints)` per trial
- Use one-hot encoding for discrete/categorical variables
- Subjects can have different numbers of neurons, trials, and trial lengths

## Code Architecture

### decoder.py

Core module containing all decoder training and prediction functions. Two main decoder approaches:

**1. PCA + Logistic Regression (`train_decoder_pca_logistic`, `predict_pca_logistic`)**
- Fits separate PCA to each subject's neural data
- Projects neural data to principal components
- Trains shared logistic regression across all subjects on concatenated PCs + inputs
- Simpler, faster, but PCA is unsupervised

**2. Linear Projection + Logistic (`train_decoder_linear`, `predict_linear`)**
- Jointly learns subject-specific linear projections and shared decoder using PyTorch
- Trains end-to-end with gradient descent
- More flexible, optimizes projection for decoding task
- Uses BCEWithLogitsLoss for binary classification

**Key functions**:
- `cross_validate_decoder()`: Performs k-fold cross-validation, splitting trials within each subject
- `f1scores_all_mice()`: Computes F1 scores by concatenating all predictions across subjects/trials
- Both decoders return `(predictions, pcs)` where pcs contains the projected neural embeddings

**Important details**:
- All functions handle variable trial counts and lengths per subject
- Mouse indexing: when `mouseid` parameter is provided, use it to index into model parameters; otherwise use sequential indices
- Projections are initialized with SVD for stability in the linear decoder
- Cross-validation preserves subject structure (never mixes subjects between train/test)

### synthetic.py

Generates synthetic data for testing decoders:
- Creates synthetic neural responses as Poisson spike counts
- Ground truth: neural → PCA → linear decoder → output
- Each subject has different numbers of neurons but shares common PC-to-output mapping
- Use for validating decoder implementations and debugging

## Common Development Tasks

### Running synthetic data tests

```bash
# From task/ directory
python synthetic.py
```

Or use the Jupyter notebook:
```bash
jupyter notebook synthetic.ipynb
```

### Testing decoders

```python
from decoder import train_decoder_linear, predict_linear, cross_validate_decoder

# Train on all data
model = train_decoder_linear(neural, input, output, npcs=10, num_epochs=100, lr=0.01)
predictions, pcs = predict_linear(neural, input, model)

# Cross-validate
f1scores, predictions, pcs, splits = cross_validate_decoder(
    neural, input, output,
    train_decoder=train_decoder_linear,
    predict=predict_linear,
    nsets=5,
    npcs=10
)
```

### Key hyperparameters

- `npcs`: Number of projected dimensions (default: 10)
- `num_epochs`: Training epochs for linear decoder (default: 100)
- `lr`: Learning rate for linear decoder (default: 0.01)
- `batch_size`: Batch size for linear decoder (default: 1024)
- `nsets`: Number of cross-validation folds (default: 5)

## Dataset Conversion Guidelines

When converting new neuroscience datasets:

1. **Exploration**: Understand native structure, identify neural/input/output variables
2. **Alignment**: Decide on trial alignment (stimulus onset, response, etc.)
3. **Binning**: Convert spike times to firing rates with appropriate time bins
4. **Validation**: Ensure shapes are `(n_features, n_time)` and types match spec
5. **Metadata**: Document task description, brain regions, and preprocessing decisions

See `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/README.md` for target datasets and conversion details.

## Important Implementation Notes

- **Array orientation**: All data uses `(features, time)` convention, not `(time, features)`. This is critical when concatenating or transposing.
- **Trial concatenation**: When concatenating across trials, transpose to `(time, features)`, concatenate along time axis, then transpose back if needed
- **Cross-validation structure**: Splits preserve all subjects in both train and test; each subject contributes different trials to each fold
- **Prediction output**: Both decoder types return predictions in original trial structure: list of subjects → list of trials → arrays
- **Device handling**: Linear decoder automatically uses CUDA if available, stores device in model dict

## Related Directories

- `../IBLPrior/`: International Brain Laboratory dataset and analysis code
- `../MAP/`: Video analysis tools (separate project)
- Root `../README.md`: High-level project overview and dataset descriptions
