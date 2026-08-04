# Case studies

The paper's appendix of worked examples: seven individual failures from the
trials, each one a mistake the agents made when reformatting a dataset.

    python3 -m case_studies              # rewrite examples.tex from the notebook
    python3 -m case_studies --check      # is the committed .tex current? (exit 1 if not)
    python3 -m case_studies --out P      # write somewhere else

Run from `evaluation/eval/`. The conversion reads the notebook's JSON and
nothing else — no kernel, no eval data, no import from `ratings` — so the LaTeX
regenerates anywhere the two files are.

| file | |
|---|---|
| `examples.ipynb` | the case studies, hand-written, markdown only |
| `examples.tex` | generated; what the paper `\input`s |
| `to_latex.py` | the converter |

## Writing an example

A markdown cell becomes an example when its first line is

    #### Example N: <Dataset> - <CATEGORY>

Any other markdown cell is ignored, so section headers and notes can live in the
notebook without reaching the paper. `<CATEGORY>` is one of the difference
categories (`FILTER`, `TIME_RES`, `PROCESS`, `ASSUME`, `VARNAME`, `MISC`) —
defined, and counted across all 8 datasets, in section 6 of
`../ratings_analysis.ipynb`.

The seven existing examples all follow the same shape, and a new one should
too:

- **Task:** what the agent was asked to deliver, the dataset context needed to
  understand the question, and what the nominally correct decision is. Don't
  repeat the verbatim question text from `DECISIONS.md`.
- **Summary:** a short paragraph on what went wrong and why it matters across
  the six trials.
- **Trial summary table** — one row per trial (3 Claude Code × 3 Codex),
  labeled "Claude Code, Trial *N*" and "Codex, Trial *N*", summarizing what
  each agent chose so the spread is visible at a glance.
- **Code Snippets:** a bold mini-heading, then two or three labeled snippets of
  10–15 lines from the actual `convert_data.py` files, line numbers and paths
  stripped, each followed by a sentence or two on what it does.

Two conventions the converter depends on:

- A table row whose **last column** reads `incorrect` is shaded red in the
  LaTeX, `concerning` yellow. Keep the rating last.
- Fenced code blocks become `minted` environments; the language after the
  opening fence is passed through.

`Example N:` is dropped on conversion — `amsthm` assigns the number, so
renumbering the notebook cells cannot desynchronise the paper.

## Preamble the output needs

```latex
\usepackage{amsthm}
\usepackage{booktabs}
\usepackage[table]{xcolor}   % row shading in the trial tables
\usepackage{minted}          % needs shell-escape; Overleaf has it on
\theoremstyle{definition}
\newtheorem{agentexample}{Example}
```

`examples.tex` also defines `codebg` (the gray behind code blocks) with
`\providecolor`, so it will not fight a definition already in your preamble.

## The examples

| N | Dataset | Category |
|---|---|---|
| 1 | Allen2P | `TIME_RES` |
| 2 | Hasnain2024 | `VARNAME` |
| 3 | Zhong2025 | `FILTER` |
| 4 | Majnik2025 | `PROCESS` |
| 5 | Chen2024 | `PROCESS` |
| 6 | Zhang2025 | `ASSUME` |
| 7 | Allen2P | `ASSUME/VARNAME` |

These are prose, not generated output: nothing regenerates them, and the
converter never rewrites the notebook. Edit the cell, re-run
`python3 -m case_studies`, commit both.
