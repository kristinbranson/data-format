"""Verify that a `rerun_verifier.sh --reuse-accuracy` run really reused the recorded accuracy.

Run from outside the container after `test.sh` exits, as well as being checked inside it by
`reuse_accuracy_conftest.py`. A run that trained a decoder instead of reusing the recorded
accuracy produces a plausible-looking number that rests on a different decoder version from
the reference statistics it is compared against, and the difference is otherwise visible only
to someone reading test-stdout.txt.

Usage:
    python3 check_reuse_accuracy.py <base metrics.json> <new metrics.json>

Exits 0 when the contract holds, 1 with a message on stderr when it does not.
"""

import json
import sys


def load_metrics(path):
    """Read one metrics.json.

    Args:
        path: str, path to a metrics.json written by a verifier run.

    Returns:
        dict of the parsed contents.

    Raises:
        SystemExit: if the file cannot be read or is not valid JSON.
    """
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        sys.exit(f"--reuse-accuracy: cannot verify the run: {error!r}")


def check_reuse(base, new):
    """Compare a rerun's metrics against the metrics its accuracy was taken from.

    Args:
        base: dict, the metrics.json the accuracy was supplied from.
        new: dict, the metrics.json the rerun produced.

    Returns:
        str, a one-line message describing what was verified. Returned rather than printed
        so the check is testable without capturing stdout.

    Raises:
        SystemExit: with an explanatory message when the contract is broken.
    """
    new_accuracy = new.get("validation_balanced_accuracy")
    if not new_accuracy:
        # Legitimate: the test can fail before the accuracy step, which is the right score
        # for a conversion that could not be loaded. Nothing to verify, and nothing wrong.
        return ("reuse check: no accuracy recorded, so the test failed before that step; "
                "nothing to verify")

    if not new.get("validation_balanced_accuracy_reused"):
        sys.exit("reuse check FAILED: the new metrics.json has no "
                 "validation_balanced_accuracy_reused, so this run trained a decoder instead "
                 "of reusing the recorded accuracy. Its numbers rest on a different decoder "
                 "version than the reference statistics; do not merge this rerun.")

    # Exact equality, not a tolerance: the accuracy is fed straight back in, so any
    # difference at all means the patch did not apply.
    base_accuracy = base.get("validation_balanced_accuracy") or {}
    disagree = {name: (base_accuracy.get(name), value)
                for name, value in new_accuracy.items() if base_accuracy.get(name) != value}
    if disagree:
        sys.exit(f"reuse check FAILED: the accuracy recorded differs from the accuracy "
                 f"supplied, (base, new) per variable: {disagree}. Do not merge this rerun.")

    return (f"reuse check: passed -- {len(new_accuracy)} output variable(s) carried over "
            f"unchanged")


def main(argv):
    """Entry point.

    Args:
        argv: list of str, the two metrics.json paths (base, new).

    Returns:
        int, 0 when the contract holds. Failures leave via SystemExit.
    """
    if len(argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <base metrics.json> <new metrics.json>")
    print(check_reuse(load_metrics(argv[0]), load_metrics(argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
