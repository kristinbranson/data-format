"""Regenerate the case-study LaTeX: ``python3 -m case_studies``."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from .to_latex import NB_PATH, TEX_PATH, convert


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m case_studies",
        description="Convert examples.ipynb's case-study cells to LaTeX.")
    ap.add_argument("--out", help=f"write here instead of {TEX_PATH.name}")
    ap.add_argument("--check", action="store_true",
                    help="do not write; report whether the committed .tex is "
                         "what the notebook says, and exit 1 if it is not")
    args = ap.parse_args(argv)

    text, n = convert()
    out = TEX_PATH if args.out is None else Path(args.out)

    if args.check:
        # The committed .tex is what the paper builds against, so drift between
        # it and the notebook is the one failure worth a non-zero exit.
        current = out.read_text() if out.exists() else ""
        if current == text:
            print(f"{out.name} is up to date ({n} examples)")
            return 0
        print(f"{out.name} is STALE — regenerate with `python3 -m case_studies`\n",
              file=sys.stderr)
        diff = difflib.unified_diff(current.splitlines(), text.splitlines(),
                                    fromfile=f"{out.name} (committed)",
                                    tofile=f"{NB_PATH.name} (would generate)",
                                    lineterm="", n=1)
        print("\n".join(list(diff)[:40]), file=sys.stderr)
        return 1

    out.write_text(text)
    print(f"Wrote {n} example(s) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
