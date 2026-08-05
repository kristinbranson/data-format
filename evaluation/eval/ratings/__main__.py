"""The rating workflow's command line: ``python3 -m ratings <command>``.

Each command forwards everything after it to the module that implements it, so
the flags are defined in exactly one place and ``-m ratings rate --help`` shows
that module's own help rather than a copy that can drift out of date.

    python3 -m ratings                        list evaluators and datasets
    python3 -m ratings rate <ds> --rater KB   rate, one question at a time
    python3 -m ratings check                  question numbering still aligned?
    python3 -m ratings merge <ds> --apply     fold ratings into eval_summary.md
    python3 -m ratings report <ds>            render report.md
    python3 -m ratings compare <ds>           judge-comparison pass (primary only)
    python3 -m ratings import-judges --apply  mirror a judge run into the tree
    python3 -m ratings validate-conditions    direct loader vs the mirror
"""

from __future__ import annotations

import sys

USAGE = """usage: python3 -m ratings <command> [options]

  list                     registered evaluators and the datasets with dossiers
  rate <dataset>           rate one question at a time against the reference
                           (--blind for a dataset with no reference solution)
  check [dataset]          verify reference, dossiers and summaries still agree
                           on what each question number means
  merge [dataset]          rebuild eval_summary.md's evaluator columns (--apply)
  report <dataset>         render <dataset>/report.md
  compare <dataset>        walk human vs LLM-judge mismatches (primary rater)
  import-judges            copy a data-format-experiments run into
                           <dataset>/judge_<mode>/ (--apply, --verify)
  validate-conditions            check the direct-from-experiments loader against
                           the mirrored judge files, cell for cell

Run `python3 -m ratings <command> --help` for a command's own options.
"""


def _named(prog: str):
    """Make a delegated parser print the command the user actually typed.

    Each module builds its own ArgumentParser, which takes its program name
    from `sys.argv[0]` — otherwise `-m ratings rate --help` announces itself as
    `__main__.py`. `basename` of a string without slashes is the whole string,
    so this is enough. `raters` has subparsers of its own and appends the
    subcommand itself, so it is named without one.
    """
    sys.argv[0] = prog


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        from . import raters
        return raters.main(["list"]) or 0

    command, rest = argv[0], argv[1:]
    _named(f"python3 -m ratings {command}")

    if command in ("-h", "--help", "help"):
        print(USAGE, end="")
        return 0

    if command == "rate":
        # The one place two former entry points merge: same six trials, same
        # scale minus better/missing, but no reference panel to compare against.
        if "--blind" in rest:
            from . import session_blind
            return session_blind.main([a for a in rest if a != "--blind"]) or 0
        from . import session
        return session.main(rest) or 0

    if command in ("list", "check", "merge"):
        from . import raters
        _named("python3 -m ratings")
        return raters.main([command, *rest]) or 0

    if command == "report":
        from . import report
        return report.main(rest) or 0

    if command == "compare":
        from . import compare
        return compare.main(rest) or 0

    if command == "import-judges":
        from . import judge_import
        return judge_import.main(rest) or 0

    if command == "validate-conditions":
        from .analysis import conditions
        return conditions.main(rest) or 0

    print(f"unknown command: {command}\n", file=sys.stderr)
    print(USAGE, end="", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
