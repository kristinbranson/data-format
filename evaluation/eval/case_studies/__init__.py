"""The paper's case-study appendix: seven worked examples of agent mistakes.

`examples.ipynb` holds them as markdown cells, one per example, written by hand;
`examples.tex` is what LaTeX gets. Nothing here is analysis — the notebook has
no code cells, and regenerating the LaTeX reads the notebook's JSON and nothing
else: no kernel, no eval data, no import from `ratings`.

    python3 -m case_studies              # rewrite examples.tex
    python3 -m case_studies --check      # is the committed .tex current?

To add or edit an example, edit the notebook and regenerate. The heading of a
case-study cell is what makes it one:

    #### Example N: <Dataset> - <CATEGORY>

Any other markdown cell is ignored, so notes and section headers can live in the
notebook without reaching the paper.
"""

from .to_latex import NB_PATH, TEX_PATH, convert

__all__ = ["convert", "NB_PATH", "TEX_PATH"]
