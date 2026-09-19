"""Score a trial's decoder without retraining it, for a re-scoring run.

Copied to `conftest.py` inside the throwaway copy of a task's `tests/` that
`rerun_verifier.sh --reuse-accuracy` mounts at /tests. It is never installed into a task's
own tests/, so a normal harbor run cannot pick it up, and it does nothing unless
REUSE_VALIDATION_ACCURACY names a file.

Why reuse rather than retrain. Training the decoder is the only expensive part of grading --
minutes to hours per trial -- and every line of `test_decoder_accuracy` after the training
call is arithmetic on the resulting per-output accuracy. That accuracy is a property of the
agent's converted data and the reference's rng_state, both fixed, so an earlier run's value
is the value retraining would produce. It also keeps the comparison honest: the reference
mean and standard deviation a trial is graded against were produced by the decoder of the
era its own accuracy was measured in, and retraining only the agent's side would compare
two decoder versions.

How. A hookwrapper around the call phase of `test_decoder_accuracy` swaps three functions on
the `decoder` module for the duration of that one test and restores them afterwards. The test
imports those names inside its own body, so the swap is picked up when the test runs.
`train_validate_decoder` and `get_trial_indices` only have to satisfy the unpacking and the
two calls between the training and the accuracy; what they return is dead once `sub_accuracy`
has been built. Only `accuracy_all_sessions` returns anything that matters.

The accuracy is ordered by the conversion's own `output_names`, read from the fixture the test
has already been handed, rather than from the recorded file's key order: `rerun_metrics.py`
rewrites metrics.json with sorted keys, so key order there is not reliably output order.

Every mismatch raises instead of falling back to training. A run that silently trained would
be indistinguishable in its output from one that reused, while resting on a different decoder
version -- the worst of the available failures.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Set by rerun_verifier.sh --reuse-accuracy to /tests/base_metrics.json, a copy of the
# trial's existing metrics.json. Absent in every other run, which disables this file.
RECORDED_PATH = os.environ.get("REUSE_VALIDATION_ACCURACY")

# The test whose training is replaced, the fixture output_names is read from, and the three
# decoder functions it calls between training and accuracy. Named as constants and checked
# below so that a rename upstream fails at setup, rather than leaving the real training in
# place or producing a plausible wrong number.
TEST_NAME = "test_decoder_accuracy"
DATA_FIXTURE = "submitted_data_full"
METRICS_FIXTURE = "metrics"
PATCHED_NAMES = ("train_validate_decoder", "get_trial_indices", "accuracy_all_sessions")

# train_validate_decoder's caller unpacks exactly this many values.
TRAIN_RETURN_VALUES = 9


def load_recorded_accuracy(path):
    """Read the per-output decoder accuracy an earlier run recorded for this trial.

    Args:
        path: str, path to a metrics.json written by a previous verifier run.

    Returns:
        dict mapping output variable name (str) to balanced accuracy (float).

    Raises:
        RuntimeError: if the file cannot be read or holds no usable
            validation_balanced_accuracy. Raised rather than falling back to training, so a
            broken reuse cannot be mistaken for a normal run.

    Side effects: none.
    """
    try:
        recorded = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise RuntimeError(
            f"--reuse-accuracy: cannot read {path}: {error!r}") from error
    accuracy = recorded.get("validation_balanced_accuracy")
    if not accuracy:
        raise RuntimeError(
            f"--reuse-accuracy: {path} records no validation_balanced_accuracy, so this "
            "trial has no accuracy to reuse. Rerun it without --reuse-accuracy to train "
            "the decoder instead.")
    return accuracy


def import_decoder():
    """Import the task's decoder module from the directory holding this conftest.

    Returns:
        the imported `decoder` module, the same object the test's own
        `from decoder import ...` will read attributes from.

    Side effects: imports decoder into sys.modules if it is not already there. The tests
        directory is put on sys.path only for the duration of the import.
    """
    tests_dir = str(Path(__file__).resolve().parent)
    sys.path.insert(0, tests_dir)
    try:
        import decoder
    finally:
        if sys.path and sys.path[0] == tests_dir:
            sys.path.pop(0)
    return decoder


def ordered_accuracy(recorded, output_names):
    """Line the recorded accuracies up with the order the test will index them in.

    Args:
        recorded: dict {output variable name: float}, from load_recorded_accuracy.
        output_names: list of str, the conversion's own output variable names, in the order
            test_decoder_accuracy zips them against the accuracy list.

    Returns:
        list of float, one per name in output_names.

    Raises:
        RuntimeError: if any of output_names has no recorded accuracy, which means the
            recorded file describes a different conversion than this snapshot.

    Side effects: none.
    """
    missing = [name for name in output_names if name not in recorded]
    if missing:
        raise RuntimeError(
            f"--reuse-accuracy: no recorded accuracy for {', '.join(missing)}. The recorded "
            f"file describes a different conversion than this snapshot, whose outputs are "
            f"{', '.join(output_names)}.")
    return [float(recorded[name]) for name in output_names]


def pytest_collection_modifyitems(items):
    """Fail the session if the test this file patches was not collected.

    Args:
        items: the collected pytest items.

    Returns:
        None.

    Raises:
        SystemExit, via pytest.exit: when reuse is requested and no test named TEST_NAME is
            in the collected set. Without this the hookwrapper below would simply never
            fire, the decoder would train as usual, and --reuse-accuracy would be a silent
            no-op -- a run resting on a different decoder version than it claims. Aborting
            loses the other tests' results for this trial, which is the cheaper loss.

    Side effects: ends the pytest session on failure.
    """
    if RECORDED_PATH is None:
        return
    if not any(item.name == TEST_NAME for item in items):
        pytest.exit(
            f"--reuse-accuracy: no test named {TEST_NAME} was collected, so the accuracy "
            f"could not be reused and the decoder would have trained instead. Either the "
            f"test was renamed, in which case this patch needs updating, or the run "
            f"selected a subset of tests, in which case drop the flag.",
            returncode=4)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """Run test_decoder_accuracy against recorded accuracies instead of a trained decoder.

    Args:
        item: the pytest item about to be called. Only TEST_NAME is touched; every other
            test runs untouched, as does every test when RECORDED_PATH is unset.

    Yields:
        once, to let the test run with the decoder module patched.

    Raises:
        RuntimeError: if decoder.py or the test's signature no longer matches what this
            patch is written against, or if the recorded accuracy does not describe this
            snapshot's outputs.

    Side effects: replaces three attributes on the imported decoder module for the duration
        of the one test, and records validation_balanced_accuracy_reused in metrics so the
        trial's own record says the decoder was not retrained.
    """
    if RECORDED_PATH is None or item.name != TEST_NAME:
        yield
        return

    # funcargs are filled by the setup phase, which has already run. A snapshot with no
    # loadable converted_data.pkl leaves this None, and the test then fails on its own --
    # which is the intended score for a trial that produced nothing, so do not interfere.
    data = item.funcargs.get(DATA_FIXTURE)
    if data is None:
        yield
        return

    decoder = import_decoder()
    absent = [name for name in PATCHED_NAMES if not hasattr(decoder, name)]
    if absent:
        raise RuntimeError(
            f"--reuse-accuracy: decoder.py has no {', '.join(absent)}. This patch is written "
            f"against {TEST_NAME}'s call sequence and has to be updated to match it.")

    output_names = list(data["output_names"])
    recorded = load_recorded_accuracy(RECORDED_PATH)
    accuracy = ordered_accuracy(recorded, output_names)

    # Reported, not fatal: extra variables in the recorded file are the same evidence of a
    # mismatched file as missing ones, but they cost nothing here -- every name this
    # conversion actually has was found above.
    extra = [name for name in recorded if name not in output_names]
    if extra:
        print(f"=== WARNING: recorded accuracy also covers {', '.join(extra)}, which this "
              f"conversion does not produce; check it is the right file ===")

    metrics = item.funcargs.get(METRICS_FIXTURE)
    if metrics is not None:
        metrics["validation_balanced_accuracy_reused"] = True
    print(f"=== decoder accuracy reused from {RECORDED_PATH}, decoder NOT retrained ===")

    # Counted so that "the test never reached the accuracy" is distinguishable from "the
    # test trained one". Zero calls is legitimate -- the test can fail earlier, on an
    # invalid format -- but it must not be read as a successful reuse.
    calls = []

    def reused_accuracy(*args, **kwargs):
        """Stand in for decoder.accuracy_all_sessions, returning the recorded values.

        Args:
            *args, **kwargs: ignored; the real function's inputs are the predictions this
                run never computed.

        Returns:
            list of float, one per output variable in output_names order.

        Side effects: records the call, so the wrapper below can tell whether the test got
            this far.
        """
        calls.append(1)
        return accuracy

    originals = {name: getattr(decoder, name) for name in PATCHED_NAMES}
    decoder.train_validate_decoder = lambda *args, **kwargs: (None,) * TRAIN_RETURN_VALUES
    decoder.get_trial_indices = lambda *args, **kwargs: None
    decoder.accuracy_all_sessions = reused_accuracy
    try:
        yield
    finally:
        for name, original in originals.items():
            setattr(decoder, name, original)

    if not calls:
        print(f"=== {TEST_NAME} did not reach the accuracy step, so nothing was reused; "
              f"its earlier failure is the reason ===")
        return

    # The flag's contract, stated directly: what the test recorded is what was handed in.
    landed = (metrics or {}).get("validation_balanced_accuracy") or {}
    disagree = {name: (recorded[name], landed.get(name))
                for name in output_names if landed.get(name) != recorded[name]}
    if disagree:
        raise RuntimeError(
            f"--reuse-accuracy: {TEST_NAME} recorded an accuracy that is not the one "
            f"supplied, so the patch did not take effect as intended. "
            f"(recorded, landed) per variable: {disagree}")
