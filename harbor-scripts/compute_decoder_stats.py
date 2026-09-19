#!/usr/bin/env python3
"""
Build a task's reference_stats_full.json by adding replicate decoder statistics to the
oracle's stats_full.json.

Why this exists
---------------
train_decoder.py trains on ONE random train/validation split, so the accuracy it records carries a
full draw of split noise. Grading a submission as a fixed fraction of that single number
compares one noisy draw against another, and the noise is not small: measured across the
eight neurodata-reuse tasks, a legitimate re-split moves balanced accuracy by 0.3% to 5.8%
depending on the output variable, and the worst single split lands at 0.87 of the mean.

Retraining on several independent splits gives two things that single number cannot:

  * a mean, which is a far less noisy reference than any one split, and
  * a standard deviation, which says how much THAT output moves under re-splitting.

test_outputs.py then passes a submitted accuracy when it is at least
`mean - ACCURACY_NSTD * std`, a per-output tolerance derived from the output's own
measured spread rather than one global percentage.

Protocol
--------
  1. Run the oracle: harbor-scripts/generate_reference_stats.sh <task>. Its solve.sh writes
     converted_data.pkl and stats_full.json (one split, and the rng_state the verifier
     reuses) into the trial's verifier/snapshot/.

  2. Train the replicates on that conversion, inside the task's own image so torch and numpy
     are the versions the verifier grades with. Two routes, which produce the same numbers:

     SERIAL -- every replicate in one process. The default, and what the reruns use:

       harbor-scripts/rerun_verifier.sh --decoder-stats --task <task> <oracle trial dir>

     which runs, in the container,

       python3 compute_decoder_stats.py --decoder-dir /tests --stats-json /app/stats_full.json \\
           --out <trial>/decoder_stats_<time>/reference_stats_full.json \\
               [--n-replicates N] \\
           /app/converted_data.pkl

     A run killed partway resumes from the checkpoint written beside --out after each
     replicate, so a wall clock or a node failure costs one replicate rather than all of them.

     ONE JOB PER REPLICATE -- for a task where serial would take days:

       harbor-scripts/submit_decoder_replicates.sh --task <task> --data <pkl> --stats <json>
       harbor-scripts/submit_decoder_replicates.sh --merge --task <task> --stats <json> \\
           --out-dir <dir>

     Each job runs `--replicate N` and writes replicate_N.json; `--merge` assembles them and
     refuses an incomplete set. Replicate N draws its split from a seed fixed by N, so this
     gives what the serial route would, in one replicate's wall clock rather than all of them.

  3. Copy the output to tests/reference_stats_full.json in <task> and <task>_minimal.
     check_task_variants.py requires those two to be identical.

The input stats JSON is read, never modified; every key in it is carried through.

It runs during no trial: not the agent, not the verifier, not the oracle. It is run by hand
when a task's reference statistics are built. It imports the task's own decoder.py via
--decoder-dir, so the replicates come from exactly the code the verifier grades with.
"""

import argparse
import importlib
import json
import os
import pickle
import re
import sys
import time

import numpy as np
import torch

# Fixed seed bases, so regenerating a task's reference statistics reproduces them exactly.
# The two RNGs are kept in disjoint ranges so replicate i never reuses replicate j's stream
# for the other generator.
REPLICATE_NUMPY_SEED_BASE = 700_000
REPLICATE_TORCH_SEED_BASE = 800_000

# How many independent re-splits a reference solution is trained on. This is the `n`
# behind the verifier's accuracy tolerance: tests/test_outputs.py compares a submission
# against mean - ACCURACY_NSTD * std of these, and ACCURACY_NSTD is derived from n as
# t(n - 1, alpha) * sqrt(1 + 1/n). Changing it invalidates that multiplier, so recompute
# ACCURACY_NSTD alongside it.
DEFAULT_N_REPLICATES = 20

# Must match train_decoder.py, or the replicates would not be drawn from the same process
# as the single-split accuracy already in stats_full.json.
TRAIN_PARAMS = {
    'npcs': 100,
    'lr': 1e-3,
    'l1_weight': 1e-4,
    'balanced_loss': True,
}


def load_checkpoint(path, expected):
    """Replicate accuracies already computed for this exact run.

    Inputs:
        path: checkpoint file written by save_checkpoint; missing is not an error.
        expected: dict of run properties that must match -- the data file, the
            replicate count and the output names. Note that the decoder code is NOT
            among them: whether a change to it matters is a judgement, so a run that
            should not reuse earlier replicates is restarted by deleting this file.

    Returns:
        List of per-replicate accuracy lists, in replicate order, or [] when there is
        no checkpoint or it describes a different run. Prints what it found, since a
        silently ignored checkpoint looks the same as a slow start.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            saved = json.load(f)
    except (OSError, ValueError) as error:
        print(f"ignoring unreadable checkpoint {path}: {error!r}")
        return []

    differing = [key for key, value in expected.items() if saved.get(key) != value]
    if differing:
        print(f"ignoring checkpoint {path}: {', '.join(differing)} differ(s) from this run")
        return []

    accuracies = saved.get('accuracies', [])
    print(f"resuming from {path}: {len(accuracies)} of {expected['n_replicates']} "
          f"replicates already done")
    return accuracies


def save_checkpoint(path, expected, accuracies):
    """Record the replicates finished so far, so a killed run can resume.

    Inputs:
        path: file to write.
        expected: the run properties load_checkpoint will match against.
        accuracies: list of per-replicate accuracy lists, in replicate order.

    Side effects: writes `path` by renaming a temporary file over it, so a run killed
    mid-write leaves the previous checkpoint intact rather than a truncated one.
    """
    temporary = f"{path}.tmp"
    with open(temporary, 'w') as f:
        json.dump({**expected, 'accuracies': accuracies}, f)
    os.replace(temporary, path)


def replicate_accuracies(decoder, data, n_replicates, train_params,
                         checkpoint_path=None, expected=None):
    """
    Train the decoder on n_replicates independent random train/validation splits.

    The split fraction is decoder.py's DEFAULT_FRAC_TRAIN; this function does not override
    it, so the replicates split the same way train_decoder.py does.

    Each replicate calls train_validate_decoder with a fresh random state and otherwise
    identical arguments, so the replicates are independent, identically distributed draws
    from the same process that produced the single-split accuracy in stats_full.json.

    Inputs:
        decoder: the task's imported decoder module.
        data: dict loaded from converted_data.pkl; uses 'neural', 'input', 'output' and
            'output_names'.
        n_replicates: int, number of independent splits. Must be >= 2 for a standard
            deviation to be defined.
        train_params: dict of keyword arguments forwarded to train_validate_decoder,
            including 'device'.
        checkpoint_path: file to resume from and rewrite after each replicate; None
            runs without checkpointing, which repeats every replicate after a restart.
        expected: run properties recorded in the checkpoint and required to match on
            resume; required when checkpoint_path is given.

    Returns:
        accuracy: numpy array of shape (n_replicates, doutput), dtype float64, the
            validation balanced accuracy of each replicate for each output variable.

    Side effects: prints per-replicate progress and rewrites checkpoint_path after each
    replicate. Consumes the global numpy and torch RNGs, which train_validate_decoder
    reseeds from the state it is given.
    """
    # Replicate i always draws its split from seeds REPLICATE_*_SEED_BASE + i, so a
    # replicate recomputed after a restart is the one that was interrupted, and resuming
    # gives the same result as never having stopped.
    accuracies = load_checkpoint(checkpoint_path, expected) if checkpoint_path else []

    for replicate in range(len(accuracies), n_replicates):
        accuracies.append(one_replicate(decoder, data, replicate, train_params,
                                        n_replicates)[0])
        if checkpoint_path:
            save_checkpoint(checkpoint_path, expected, accuracies)
    return np.array(accuracies)


def one_replicate(decoder, data, replicate, train_params, n_replicates=None):
    """Train and validate the decoder on the split belonging to one replicate.

    Inputs:
        decoder: the task's imported decoder module.
        data: dict loaded from converted_data.pkl.
        replicate: replicate index, counted from 0. Its split comes from
            REPLICATE_*_SEED_BASE + replicate, so the same index gives the same split
            whether it runs alone or among others.
        train_params: keyword arguments forwarded to train_validate_decoder.
        n_replicates: total being run, for the progress line only.

    Returns:
        (accuracy, device): accuracy is a list of floats, length doutput, the validation
        balanced accuracy per output; device names what actually trained, which is not
        train_params' device when the GPU ran out of memory and the CPU took over.

    Side effects: prints a line before and after. Consumes the global numpy and torch
    RNGs, which train_validate_decoder reseeds from the state it is given.
    """
    state = {'numpy': REPLICATE_NUMPY_SEED_BASE + replicate,
             'torch': REPLICATE_TORCH_SEED_BASE + replicate}
    total = f"/{n_replicates}" if n_replicates else ""
    start = time.time()
    print(f"\n=== replicate {replicate + 1}{total}  state={state} ===", flush=True)
    # A dataset whose activations do not fit the card raises torch.OutOfMemoryError partway
    # through the first epoch. Retrying on the CPU costs time but finishes, where failing
    # loses the replicate and leaves the set incomplete -- and an incomplete set is no
    # statistic at all, since the mean and standard deviation need every one. The device
    # that trained is returned so that a replicate which fell back says so.
    try:
        (_, predictions, _, _, _, test_indices,
         _, output, _) = decoder.train_validate_decoder(
            data['neural'], data['input'], data['output'], state=state, **train_params)
    except torch.OutOfMemoryError:
        print(f"replicate {replicate + 1}: CUDA out of memory, retrying on CPU", flush=True)
        train_params = {**train_params, 'device': torch.device('cpu')}
        (_, predictions, _, _, _, test_indices,
         _, output, _) = decoder.train_validate_decoder(
            data['neural'], data['input'], data['output'], state=state, **train_params)
    # (doutput,) mean per-class recall on this replicate's held-out trials
    accuracy = decoder.accuracy_all_sessions(
        decoder.get_trial_indices(predictions, test_indices),
        decoder.get_trial_indices(output, test_indices),
        balanced=True)
    device = str(train_params.get('device', 'cuda'))
    print(f"replicate {replicate + 1} done in {time.time() - start:.1f}s on {device}: "
          + "  ".join(f"{data['output_names'][i]}={accuracy[i]:.4f}"
                      for i in range(len(accuracy))), flush=True)
    return [float(value) for value in accuracy], device


def read_replicate_files(directory, n_replicates):
    """Collect the per-replicate files written by --replicate.

    Inputs:
        directory: where the jobs wrote replicate_<N>.json.
        n_replicates: how many are expected; every index from 1 to this must be present,
            since a mean over a subset would silently be a mean over fewer splits.

    Returns:
        (accuracies, devices), both ordered by replicate index: the per-replicate
        accuracy lists, and what each one trained on. Says so when they differ, since
        a spread measured across two devices carries their difference as well as the
        splits'.

    Exits with an error naming the missing indices if any file is absent, and if the
    files disagree about the output names.
    """
    found = {}
    devices = {}
    names = None
    for replicate in range(1, n_replicates + 1):
        path = os.path.join(directory, f"replicate_{replicate}.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            saved = json.load(f)
        if names is None:
            names = saved['output_names']
        elif saved['output_names'] != names:
            print(f"ERROR: {path} has output names {saved['output_names']}, expected "
                  f"{names}", file=sys.stderr)
            sys.exit(1)
        found[replicate] = saved['accuracy']
        devices[replicate] = saved.get('device', 'unrecorded')

    missing = [n for n in range(1, n_replicates + 1) if n not in found]
    if missing:
        print(f"ERROR: {len(missing)} of {n_replicates} replicates missing from "
              f"{directory}: {missing}", file=sys.stderr)
        sys.exit(1)
    ordered = [n for n in range(1, n_replicates + 1)]
    distinct = sorted(set(devices.values()))
    if len(distinct) > 1:
        print(f"note: replicates ran on more than one device: "
              + ", ".join(f"{d} x{sum(1 for v in devices.values() if v == d)}"
                          for d in distinct))
    return [found[n] for n in ordered], [devices[n] for n in ordered]


def accuracy_nstd_from(decoder_dir):
    """The verifier's pass threshold multiplier, read from the task's test_outputs.py.

    Inputs:
        decoder_dir: directory holding test_outputs.py, as passed to --decoder-dir.

    Returns:
        ACCURACY_NSTD as a float, so the summary printed here cannot disagree with how
        submissions are graded. Read as text rather than imported, because test_outputs
        imports pytest and the task image does not have it. Exits if it is absent.
    """
    with open(os.path.join(decoder_dir, 'test_outputs.py')) as f:
        found = re.search(r'^ACCURACY_NSTD\s*=\s*([0-9.]+)', f.read(), re.M)
    if found is None:
        print(f"ERROR: no ACCURACY_NSTD in {decoder_dir}/test_outputs.py", file=sys.stderr)
        sys.exit(1)
    return float(found.group(1))


def write_reference_stats(stats, accuracy, output_names, n_replicates, out, accuracy_nstd):
    """Add the replicate statistics to the oracle's stats and write them out.

    Inputs:
        stats: dict read from the oracle's stats_full.json; every key is carried through.
        accuracy: (n_replicates, doutput) array of validation balanced accuracies.
        output_names: length doutput, naming accuracy's columns.
        n_replicates: recorded as `n_replicates`, the n behind the verifier's tolerance.
        out: file to write.
        accuracy_nstd: multiplier, for the printed summary only.

    Side effects: writes `out` and prints a per-output table of mean, standard deviation
    and the resulting threshold.
    """
    stats['n_replicates'] = n_replicates
    stats['validation_balanced_accuracy_mean'] = {
        output_names[i]: float(accuracy[:, i].mean()) for i in range(len(output_names))
    }
    # ddof=1: the replicates are a sample of the possible splits, not the population.
    stats['validation_balanced_accuracy_std'] = {
        output_names[i]: float(accuracy[:, i].std(ddof=1)) for i in range(len(output_names))
    }
    # Kept so a reference can be audited, or a different threshold applied later, without
    # rerunning the replicates.
    stats['validation_balanced_accuracy_replicates'] = {
        output_names[i]: [float(v) for v in accuracy[:, i]] for i in range(len(output_names))
    }

    with open(out, 'w') as f:
        json.dump(stats, f, indent=2)

    threshold_label = f'mean-{accuracy_nstd:g}std'
    print(f"\n{'output':<26}{'mean':>10}{'std':>10}{threshold_label:>14}")
    print('-' * 60)
    for i, name in enumerate(output_names):
        mean = accuracy[:, i].mean()
        std = accuracy[:, i].std(ddof=1)
        print(f"{name:<26}{mean:>10.4f}{std:>10.4f}{mean - accuracy_nstd * std:>14.4f}")
    print(f"\nWrote {out}: the oracle's statistics plus {n_replicates}-replicate "
          f"mean and std.")


def main():
    parser = argparse.ArgumentParser(
        description="Add replicate decoder statistics to an oracle's stats_full.json.")
    parser.add_argument('data_file_path', type=str, nargs='?',
                        help='Path to the converted data file (pickle format). Not '
                             'needed with --merge, which reads finished replicates.')
    parser.add_argument('--decoder-dir', type=str, required=True,
                        help="Directory holding the task's decoder.py, normally <task>/tests.")
    parser.add_argument('--stats-json', type=str, required=True,
                        help="The oracle's stats_full.json, read but not modified.")
    parser.add_argument('--out', type=str, required=True,
                        help='Where to write the reference stats: every key from '
                             '--stats-json, plus the replicate mean and std.')
    parser.add_argument('--n-replicates', type=int, default=DEFAULT_N_REPLICATES,
                        help=f'Number of independent train/validation splits '
                             f'(default {DEFAULT_N_REPLICATES}). Min 2.')
    parser.add_argument('--replicate', type=int, default=None, metavar='N',
                        help='Run only replicate N of --n-replicates, numbered from 1, '
                             'and write its accuracy to --out. For splitting the '
                             'replicates across jobs, one per replicate; --merge then '
                             'assembles them. Replicate N draws the same split however '
                             'it is run, so the result matches a single serial run.')
    parser.add_argument('--merge', type=str, default=None, metavar='DIR',
                        help='Assemble the per-replicate files written by --replicate '
                             'into the full reference statistics. Reads every '
                             'replicate_*.json in DIR and needs no data file or decoder.')
    parser.add_argument('--cpu', action='store_true', help='Force torch to use CPU only.')
    args = parser.parse_args()

    if args.merge is None and args.data_file_path is None:
        parser.error('a data file is required unless --merge is given.')
    if args.replicate is not None and args.merge is not None:
        parser.error('--replicate computes one replicate and --merge assembles them; '
                     'pass one or the other.')
    if args.replicate is not None and not 1 <= args.replicate <= args.n_replicates:
        parser.error(f'--replicate must be between 1 and --n-replicates '
                     f'({args.n_replicates}); got {args.replicate}.')

    if args.n_replicates < 2:
        parser.error('--n-replicates must be at least 2; a standard deviation is '
                     'undefined for a single split.')

    # Python block-buffers stdout at 8 KB when it is a pipe, which is what it is when the
    # caller tees to a log. A replicate prints well under that, so progress would reach the
    # log hours late and in bursts. Line buffering applies to everything sharing this
    # stream, decoder.py's per-session and per-epoch lines included.
    sys.stdout.reconfigure(line_buffering=True)

    with open(args.stats_json) as stats_file:
        stats = json.load(stats_file)

    if args.merge is not None:
        replicates, devices = read_replicate_files(args.merge, args.n_replicates)
        accuracy = np.array(replicates)
        output_names = json.load(
            open(os.path.join(args.merge, 'replicate_1.json')))['output_names']
        # Kept so the spread can be read knowing what produced it: a replicate that fell
        # back to the CPU differs from a GPU one in the last digits, and a reference whose
        # replicates span both should say so rather than look uniform.
        stats['replicate_devices'] = devices
        write_reference_stats(stats, accuracy, output_names, args.n_replicates,
                              args.out, accuracy_nstd_from(args.decoder_dir))
        return

    sys.path.insert(0, args.decoder_dir)
    decoder = importlib.import_module('decoder')
    accuracy_nstd = accuracy_nstd_from(args.decoder_dir)

    with open(args.data_file_path, 'rb') as f:
        data = pickle.load(f)

    train_params = dict(TRAIN_PARAMS)
    if args.cpu:
        train_params['device'] = torch.device('cpu')

    output_names = data['output_names']
    # Written beside --out after every replicate, so a run killed by a wall clock or a
    # node failure resumes instead of repeating hours of training. The fields below must
    # match for it to be reused; the decoder code is deliberately not one of them, since
    # an edit that cannot change results should not discard finished replicates. Delete
    # this file to force every replicate to be recomputed.
    checkpoint_path = f"{args.out}.partial"
    expected = {'data_file_path': os.path.abspath(args.data_file_path),
                'n_replicates': args.n_replicates,
                'output_names': list(output_names)}

    if args.replicate is not None:
        accuracy, device = one_replicate(decoder, data, args.replicate - 1, train_params,
                                         args.n_replicates)
        with open(args.out, 'w') as f:
            json.dump({'replicate': args.replicate, 'accuracy': accuracy,
                       'device': device,
                       'output_names': list(output_names),
                       'data_file_path': os.path.abspath(args.data_file_path),
                       'n_replicates': args.n_replicates}, f, indent=2)
        print(f"\nWrote {args.out}: replicate {args.replicate} of {args.n_replicates}. "
              f"Assemble with --merge once every replicate has one.")
        return

    # (n_replicates, doutput)
    accuracy = replicate_accuracies(decoder, data, args.n_replicates, train_params,
                                    checkpoint_path, expected)
    if accuracy.shape[1] != len(output_names):
        print(f"ERROR: decoder returned {accuracy.shape[1]} outputs but the data declares "
              f"{len(output_names)} output names", file=sys.stderr)
        sys.exit(1)

    write_reference_stats(stats, accuracy, output_names, args.n_replicates,
                          args.out, accuracy_nstd)


if __name__ == '__main__':
    main()
