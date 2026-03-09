"""
Test file for sosa2024 neural decoder data conversion task.
Validates that all expected output files exist.
"""

import json
import os
import pickle
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment
import torch
import pytest
from decoder import (
    get_trial_indices,
    verify_data_format,
    print_data_summary,
    train_validate_decoder,
    accuracy_all_sessions
    )

WORKDIR = Path(os.environ.get("WORKDIR", "/app"))
METRICS_PATH = Path(os.environ.get("METRICS_PATH", "/logs/verifier/metrics.json"))
# path to this file's directory
TESTDIR = Path(__file__).parent

# Canary strings embedded in the reference solution.
# If any of these appear in agent-produced code, the solution was likely
# memorised from training data rather than independently derived.
CANARY_STRINGS = [
    "x5cidj2hy87s",
]

# Files that must exist for the test to pass
REQUIRED_FILES = [
    "CONVERSION_NOTES.md",
    "convert_data.py",
    "converted_data.pkl",
    "sample_data.pkl",
    "README.md",
]

# Files that are expected but we will not fail if they are missing
EXPECTED_FILES = [
    "train_decoder_full_out.txt",
    "conversion_sample_out.txt",
    "verification_sample_out.txt",
    "train_decoder_sample_out.txt",
    "conversion_full_out.txt",
    "verification_full_out.txt",
]


@pytest.fixture(scope="module")
def metrics():
    """Shared metrics dict, written to file after all tests complete."""
    data = {}
    yield data
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(data, f, indent=2)


@pytest.fixture(scope="module")
def submitted_data_sample():
    """Load the agent's sample converted data."""
    path = WORKDIR / "sample_data.pkl"
    if not path.exists():
        pytest.skip("sample_data.pkl not found")
    with open(path, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def submitted_data_full():
    """Load the agent's full converted data."""
    path = WORKDIR / "converted_data.pkl"
    if not path.exists():
        pytest.skip("converted_data.pkl not found")
    with open(path, "rb") as f:
        return pickle.load(f)

@pytest.fixture(scope="module")
def reference_data_stats():
    # load in the reference data stats for comparison
    path = TESTDIR / "reference_stats_full.json"
    if not path.exists():
        pytest.skip("reference_stats_full.json not found")
    with open(path, "r") as f:
        stats = json.load(f)
    stats['data_summary']['nneurons_total'] = stats['data_summary']['nsessions'] * stats['data_summary']['nneurons_mean']
    return stats

@pytest.fixture(scope="module")
def submitted_data_stats(submitted_data_full):
    stats = print_data_summary(submitted_data_full)
    stats['nneurons_total'] = stats['nsessions'] * stats['nneurons_mean']
    return stats

def test_required_files_exist(metrics):
    """Test that all required output files exist and are non-empty."""
    missing = []
    empty = []
    for f in REQUIRED_FILES:
        path = WORKDIR / f
        if not path.exists():
            missing.append(f)
        elif path.stat().st_size == 0:
            empty.append(f)

    metrics["required_files_missing"] = missing
    metrics["required_files_empty"] = empty

    assert not missing, f"Missing required files: {missing}"
    assert not empty, f"Required files exist but are empty: {empty}"


def test_no_contamination(metrics):
    """Check that agent-produced code does not contain reference solution canary strings."""
    contaminated_files = {}
    for pyfile in WORKDIR.glob("*.py"):
        try:
            content = pyfile.read_text()
        except Exception:
            continue
        found = [c for c in CANARY_STRINGS if c in content]
        if found:
            contaminated_files[pyfile.name] = found

    metrics["contamination_detected"] = bool(contaminated_files)
    metrics["contaminated_files"] = {k: v for k, v in contaminated_files.items()}

    assert not contaminated_files, (
        f"Possible benchmark contamination: canary strings from the reference solution "
        f"were found in agent-produced files: {contaminated_files}"
    )


def test_expected_files_exist(metrics):
    """Test that all expected output files exist and are non-empty."""
    missing = []
    empty = []
    for f in EXPECTED_FILES:
        path = WORKDIR / f
        if not path.exists():
            missing.append(f)
        elif path.stat().st_size == 0:
            empty.append(f)

    metrics["expected_files_missing"] = missing
    metrics["expected_files_empty"] = empty
    metrics["expected_files_found"] = len(EXPECTED_FILES) - len(missing)
    metrics["expected_files_total"] = len(EXPECTED_FILES)

    if missing:
        print(f"WARNING: Missing expected files: {missing}")
    if empty:
        print(f"WARNING: Expected files exist but are empty: {empty}")

def test_verify_data_format(metrics, submitted_data_sample, submitted_data_full):
    """Helper function to test data format and record metrics."""
    valid, errors, warnings = verify_data_format(submitted_data_sample)
    metrics["sample_data_format_valid"] = valid
    metrics["sample_data_format_errors"] = errors
    metrics["sample_data_format_warnings"] = warnings

    assert valid, f"Sample data format is invalid. Errors: {errors}"
    if warnings:
        print(f"Sample data format warnings: {warnings}")
        
    valid, errors, warnings = verify_data_format(submitted_data_full)
    metrics["full_data_format_valid"] = valid
    metrics["full_data_format_errors"] = errors
    metrics["full_data_format_warnings"] = warnings
    assert valid, f"Full data format is invalid. Errors: {errors}"
    if warnings:
        print(f"Full data format warnings: {warnings}")


def match_ranges_by_hungarian(submitted_ranges, reference_ranges):
    """Find 1-1 matching between input/output variables based on range similarity.

    Args:
        submitted_ranges: dict of {name: [min, max]}
        reference_ranges: dict of {name: [min, max]}

    Returns:
        matches: list of (ref_name, sub_name, cost) tuples
        cost_matrix: the full cost matrix
    """
    ref_names = list(reference_ranges.keys())
    sub_names = list(submitted_ranges.keys())
    n = len(ref_names)

    cost = np.zeros((n, n))
    for i, rn in enumerate(ref_names):
        for j, sn in enumerate(sub_names):
            ref_lo, ref_hi = reference_ranges[rn]
            sub_lo, sub_hi = submitted_ranges[sn]
            scale = max(abs(ref_hi - ref_lo), 1e-6)
            cost[i, j] = np.maximum(abs(ref_lo - sub_lo)/scale, abs(ref_hi - sub_hi)/scale)

    row_ind, col_ind = linear_sum_assignment(cost)
    matches = []
    for i, j in zip(row_ind, col_ind):
        matches.append((ref_names[i], sub_names[j], float(cost[i, j])))
    return matches, cost


def match_outputs_by_range_and_fractions(submitted_ranges, reference_ranges,
                                          submitted_fractions, reference_fractions):
    """Find 1-1 matching between outputs: ranges must match exactly, then minimize fraction error.

    Cost is inf if ranges don't match, otherwise mean absolute difference of sorted fractions.

    Args:
        submitted_ranges: dict of {name: [min, max]}
        reference_ranges: dict of {name: [min, max]}
        submitted_fractions: dict of {name: {val: frac, ...}}
        reference_fractions: dict of {name: {val: frac, ...}}

    Returns:
        matches: list of (ref_name, sub_name, cost) tuples
        cost_matrix: the full cost matrix
    """
    ref_names = list(reference_ranges.keys())
    sub_names = list(submitted_ranges.keys())
    n = len(ref_names)

    cost = np.full((n, n), np.inf)
    for i, rn in enumerate(ref_names):
        for j, sn in enumerate(sub_names):
            ref_lo, ref_hi = reference_ranges[rn]
            sub_lo, sub_hi = submitted_ranges[sn]
            # ranges must match exactly
            if ref_lo != sub_lo or ref_hi != sub_hi:
                continue
            # compare fraction distributions using sorted values
            ref_fracs = sorted(reference_fractions[rn].values())
            sub_fracs = sorted(submitted_fractions[sn].values())
            if len(ref_fracs) != len(sub_fracs):
                continue
            cost[i, j] = np.sum(np.abs(np.array(ref_fracs) - np.array(sub_fracs)))

    row_ind, col_ind = linear_sum_assignment(cost)
    matches = []
    for i, j in zip(row_ind, col_ind):
        matches.append((ref_names[i], sub_names[j], float(cost[i, j])))
    return matches, cost


STATLIMITS = {
    'nsessions_ratio': .1, # must be within 10% of reference
    'ntrials_total_ratio': .1, # must be within 10% of reference
    'T_median_ratio': .1, # must be within 10% of reference
    'nsubjects_ratio': 0, # must match reference
    'nneurons_total_ratio': .1, # must be within 10% of reference
    'input_range': .1, # mean matching cost must be below this
    'output_fractions': .1, # output fractions mean cost must be below this
}
MIN_ACCURACY_FRAC = 0.95 # submitted accuracy must be at least this fraction of reference accuracy for each output dimension

def test_data_stats(metrics, submitted_data_stats, reference_data_stats):

    fields_check = [
        'nsessions',
        'ntrials_total',
        'T_median',
        'nsubjects',
        'nneurons_total',
    ]
    
    for field in fields_check:
        metrics[field+'_ratio'] = submitted_data_stats[field] / reference_data_stats['data_summary'][field]

    for field in fields_check:
        assert 1-STATLIMITS[field+'_ratio'] <= metrics[field+'_ratio'] <= 1+STATLIMITS[field+'_ratio'], f"{field} in submitted data ({submitted_data_stats[field]}) is not within {STATLIMITS[field+'_ratio']*100}% of reference ({reference_data_stats['data_summary'][field]})"

    # check that the number of inputs and outputs matches the reference
    assert submitted_data_stats['dinput'] == reference_data_stats['data_summary']['dinput'], f"dinput in submitted data ({submitted_data_stats['dinput']}) does not match reference ({reference_data_stats['data_summary']['dinput']})"
    assert submitted_data_stats['doutput'] == reference_data_stats['data_summary']['doutput'], f"doutput in submitted data ({submitted_data_stats['doutput']}) does not match reference ({reference_data_stats['data_summary']['doutput']})"

    # check that input ranges match via 1-1 matching
    input_matches, input_costs = match_ranges_by_hungarian(
        submitted_data_stats['input_range'],
        reference_data_stats['data_summary']['input_range'],
    )

    mean_input_cost = np.mean([c for _, _, c in input_matches])
    metrics['input_range_mean_cost'] = float(mean_input_cost)
    assert mean_input_cost < STATLIMITS['input_range'], (
        f"Input range mean matching cost too high ({mean_input_cost:.3f} >= {STATLIMITS['input_range']}). "
        f"Matches: {[(r, s, f'{c:.3f}') for r, s, c in input_matches]}"
    )

    # check that output ranges match exactly, then use fraction error to match
    output_matches, output_costs = match_outputs_by_range_and_fractions(
        submitted_data_stats['output_range'],
        reference_data_stats['data_summary']['output_range'],
        submitted_data_stats['output_fractions'],
        reference_data_stats['data_summary']['output_fractions'],
    )
    metrics['output_matches'] = [
        {'reference': ref, 'submitted': sub, 'cost': cost}
        for ref, sub, cost in output_matches
    ]
    # check that all outputs had an exact range match (no inf costs)
    inf_matches = [(r, s) for r, s, c in output_matches if np.isinf(c)]
    assert not inf_matches, (
        f"Output ranges do not match exactly for: {inf_matches}. "
        f"All matches: {[(r, s, f'{c:.3f}') for r, s, c in output_matches]}"
    )
    mean_output_fraction_cost = np.mean([c for _, _, c in output_matches])
    metrics['output_fraction_mean_cost'] = float(mean_output_fraction_cost)
    assert mean_output_fraction_cost < STATLIMITS['output_fractions'], (
        f"Output fractions mean matching cost too high ({mean_output_fraction_cost:.3f} >= {STATLIMITS['output_fractions']}). "
        f"Matches: {[(r, s, f'{c:.3f}') for r, s, c in output_matches]}"
    )

def test_decoder_accuracy(metrics, submitted_data_full, submitted_data_stats, reference_data_stats):
    """Run the provided train_decoder.py script on the sample data and check that it runs without error."""

    train_params = {
        'npcs': 10,
        'num_epochs': 10,
        'lr': 1e-3,
        'l1_weight': 1e-4,
        'balanced_loss': True,
    }

    # train the decoder on the submitted data
    rng_state = reference_data_stats.get('rng_state', None)
    try:
        scores, predictions, pcs, confidences, train_idx, test_idx, model, output, _ = \
            train_validate_decoder(submitted_data_full['neural'], submitted_data_full['input'],
                                submitted_data_full['output'], state=rng_state, **train_params)
    except torch.cuda.OutOfMemoryError:
        print("CUDA out of memory error during decoder training. Retrying on CPU...")
        train_params['device'] = torch.device('cpu')
        scores, predictions, pcs, confidences, train_idx, test_idx, model, output, _ = \
            train_validate_decoder(submitted_data_full['neural'], submitted_data_full['input'],
                                submitted_data_full['output'], state=rng_state, **train_params)

    # evaluate accuracy on test set    
    test_predictions_only = get_trial_indices(predictions, test_idx)
    test_output_only = get_trial_indices(output, test_idx)
    balanced_accuracy = accuracy_all_sessions(test_predictions_only, test_output_only, balanced=True)

    ref_accuracy = reference_data_stats['validation_balanced_accuracy']
    sub_accuracy = {
        submitted_data_full['output_names'][i]: float(balanced_accuracy[i])
        for i in range(len(balanced_accuracy))
    }
    metrics['validation_balanced_accuracy'] = sub_accuracy
    metrics['validation_balanced_accuracy_reference'] = ref_accuracy
    
    # find a match between output dimensions
    output_matches, output_costs = match_outputs_by_range_and_fractions(
        submitted_data_stats['output_range'],
        reference_data_stats['data_summary']['output_range'],
        submitted_data_stats['output_fractions'],
        reference_data_stats['data_summary']['output_fractions'],
    )

    metrics['validation_balanced_accuracy_ratio'] = {
        ref_name: sub_accuracy[sub_name] / ref_accuracy[ref_name]
        for ref_name, sub_name, _ in output_matches
    }
    
    for ref_name, sub_name, _ in output_matches:
        ref_acc = ref_accuracy[ref_name]
        sub_acc = sub_accuracy[sub_name]
        assert sub_acc >= MIN_ACCURACY_FRAC * ref_acc, f'Accuracy for output {sub_name} ({sub_acc:.3f}) is below {MIN_ACCURACY_FRAC*100:.1f}% of reference accuracy ({ref_acc:.3f})'


    
