# Ratings

How the agent-produced conversion code gets rated — by the human evaluators and
by the LLM judges — where those ratings live, and how to analyze them.

Everything is in the `ratings` package. Two entry points:

```bash
python3 -m ratings <command>     # rating workflow

```
```python
from ratings import load_ratings, summary_table, agreement, binary   # rating analysis
```

See `ratings_analysis.ipynb` for the notebook on analysis of the ratings. 
- Inter-evaluator variability
- Evaluating agent-as-judge (supervised vs. unsupervised)

## TL;DR

A rating pass, from `evaluation/eval/`, per dataset:

```bash
python3 -m ratings rate <dataset> --rater KB     # rate, one question at a time
python3 -m ratings merge <dataset> --apply       # fold into eval_summary.md
python3 -m ratings report <dataset>              # regenerate report.md
```

Ctrl-C is safe — re-run to resume. To redo, add `--overwrite` (with
`--question 3-a` for just one). Then open `ratings_analysis.ipynb` for the
figures and tables.

---

## The interface

### Commands

| command | what it does |
|---|---|
| `python3 -m ratings` | registered evaluators and the datasets with dossiers |
| `rate <dataset>` | rate one question at a time against the reference. `--rater`, `--question`, `--overwrite`, `--blind` |
| `check [dataset]` | verify reference, dossiers and summaries still agree on what each question number means |
| `merge [dataset]` | rebuild `eval_summary.md`'s evaluator columns from the dossiers. `--apply` to write |
| `report <dataset>` | render `<dataset>/report.md`. `--rater`, `--out` |
| `compare <dataset>` | walk human-vs-judge mismatches (primary evaluator only) |
| `import-judges` | copy a `data-format-experiments/` run into `<dataset>/judge_<mode>/`. `--mode`, `--apply`, `--verify` |

`python3 -m ratings <command> --help` for a command's own options.

### Library

```python
from ratings import load_ratings, summary_table, agreement, binary, display, plots

r = load_ratings()                    # every rater, all 8 datasets
r.tidy                                # one row per (dataset, question, agent, trial)
r.correctness                         # the same, minus the Code Efficiency questions

summary_table(r, rater="LZ")          # the per-question rating grid
agreement.pairwise(r.correctness)     # Pearson + weighted kappa per rater pair
binary.table(r.tidy, "LZ", ("KB", "claude", "codex"))   # who catches the mistakes
plots.format_scatter(r)               # per-trial correctness by source format
```

**rater** is who gave the rating: the humans `LZ` and `KB`, and the judges
`claude` / `codex` (which saw the reference solution) and `claude_unsup` /
`codex_unsup` (which did not). **agent** is the system being evaluated,
`claude-code` or `codex`. The old notebooks used one word for both; this one
does not.

Two more raters are derived rather than loaded, and are added to a frame on
demand: `add_null(df)` gives `LZ_null`, LZ's own ratings shuffled — the floor
any real rater should beat — and `add_combined(df)` gives `combined`, the two
supervised judges required to agree before a row counts as a mistake.

Ratings are numbers: `incorrect=-2, concerning=-1, ok=0, match=1, better=2`,
and a rating nobody gave is `NaN` — never 0.

`ratings_analysis.ipynb` is the worked version of all of this: coverage, the
rating grid per rater, inter-rater agreement, mistake-catching accuracy, and
the per-agent figures.

---

## Where the ratings live

```
eval/<dataset>/
  claude-code_trial1.md …      masters: dossier content, ratings blank
  LZ/
    claude-code_trial1.md …    LZ's copies, carrying LZ's ratings
    summary.md                 LZ's per-question tables + comments
  KB/                          same shape, KB's ratings
  judge_supervised/            <agent>_trial<N>_<judge>-judge.json
  judge_unsupervised/          the same judges, run without the reference
  eval_summary.md              combined: one column per evaluator + both judges
  report.md                    rendered report
```

**The dossier copies are the source of truth.** Each question in
`<dataset>/KB/<agent>_trial<N>.md` ends with the two lines the tools write:

```markdown
**Rating:** ok

**Note:** relies on an assumption that happens to hold here
```

`summary.md` rolls those up per question; `eval_summary.md` is regenerated from
the dossiers by `merge`; `report.md` is rendered from both. If any of them ever
disagree, the dossier wins. The analysis reads the dossiers directly, so it
cannot go stale behind them.

Both evaluators' folders are copies of the same masters, so a given question
number means the same thing in `LZ/` and in `KB/`.

---

## Details

### Rating a dataset

`rate` shows one question at a time and, for each, the six trials (3
claude-code + 3 codex) in shuffled order under anonymous labels:

- Left panel the reference answer, right panel `SAMPLE A (1/6)` — that trial's
  notes excerpt, code excerpt and a neutral description. The agent's identity is
  hidden.
- `Rating [better | match | ok | concerning | incorrect | missing]`, shortcuts
  `b` / `m` / `o` / `c` / `i` (or `x`) / `n`, then a free-text note.
- After all six the `A–F → agent / trial` mapping is revealed, then one overall
  comment for the question.

`--blind` is for a dataset with no reference solution at all: one panel per
trial, agent and trial number shown, scale reduced to
`match | ok | concerning | incorrect`. The judge panels are shown only to the
primary evaluator, so a second evaluator's ratings stay independent of the LLMs.

On the first run for a dataset the tool creates `eval/<dataset>/<CODE>/` by
copying the master dossiers — same questions, same numbering as every other
evaluator, ratings blank. Evaluators never see each other's ratings and never
write the same file.

Without `--rater` the tool asks for a code; `export DATAFORMAT_RATER=KB` sets it
for a session. An unregistered code is rejected rather than silently creating a
folder. The registry is `ratings/raters.json`.

### Stopping and resuming

Every rating is written as it is entered, so Ctrl-C is safe and re-running picks
up where it stopped — questions already rated are skipped silently.

```bash
python3 -m ratings rate allen2p --rater KB --question 3-a   # just one question
python3 -m ratings rate allen2p --rater KB --overwrite      # re-rate everything
```

### The alignment check

Before showing anything, a rating session verifies that the reference, the
dossiers and the summary files still agree on what each question number means.
Question numbering has drifted twice in this project, and a silent mismatch
would attach one question's rating to another question's content.

Drift the tools can resolve prints a note and continues (`pairing them by
content (3-a→5-a, …)`). Drift they cannot resolve aborts with the command that
repairs it. Do not work around it — a rating on the wrong question is worse than
a missing one. Run it any time with `python3 -m ratings check`.

The same principle runs through the analysis: judge results are matched to our
questions by a **fingerprint of the question text**, never by number, because
the judges ask their own list and the two numberings have drifted apart.

### Judge results

`import-judges` mirrors a run out of `data-format-experiments/` into
`<dataset>/judge_supervised/` or `judge_unsupervised/`, one flat file per
`<agent>_trial<N>_<judge>-judge.json`. `--verify` checksums what is already
there without copying. Only `claude-code` and `codex` are kept, and only the
first three trials.

### `report.md`

Hand-written parts are carried across regenerations: the `## Comments` section,
the **Difference categories** column, and the two comment columns
(**Solution comment**, **LLM judge comment**) — those start out generated from
the summary files, but whatever the last report said wins, so a comment
polished in place is never reverted to its draft. All four are matched to each
question by its *text*, so a value follows its question through a renumbering.
The rating columns are rebuilt every time and edits to them will not survive.

The two judge columns come from `<dataset>/judge_supervised/`, the same source
`load_ratings()` reads, mapped onto our question numbering by content — not
from `eval_summary.md`, which is only a snapshot of whichever judge run existed
the last time `compare` was used.

---

## Map

```
eval/
  ratings/               everything about ratings
    __main__.py          the CLI above
    __init__.py          the library interface above
    paths.py             every filesystem location, derived once
    raters.py            evaluator registry, rater folders, rating I/O,
                         alignment check, eval_summary.md merge
    session.py           the interactive rating session (rate)
    session_blind.py     … for a dataset with no reference (rate --blind)
    compare.py           judge-comparison pass; question fingerprinting
    report.py            report.md renderer
    judge_import.py      import-judges
    questions.py         the question taxonomy — what a question is about
    figure.py            the rating-square figure toolkit
    raters.json          the evaluator registry
    analysis/            loading, judges, agreement, binary, categories,
                         render, plots, display — see its docstring
    README.md            this file
  ratings_analysis.ipynb the analysis, worked through
  case_studies/          the paper's worked examples -> examples.tex
  archive/               one-off migrations and the superseded notebooks
```

`case_studies/` is the third world in this directory and the smallest: seven
hand-written failure cases and the converter that turns them into LaTeX
(`python3 -m case_studies`). It reads no data and imports nothing from here —
only section 6 of the analysis notebook, which counts the *categories* those
examples illustrate, connects them.

The other half of the evaluation — what the **verifier** measured, rather than
what a human thought of the code — is a separate world and deliberately shares
nothing with this one:

| file | role |
|---|---|
| `utils.py` | trial metrics loading + the arm / agent vocabulary |
| `metrics.py`, `metrics.ipynb` | per-trial decoder accuracy and dataset-scale tables |
| `lesion_analysis.py` | verifier categories scored per trial |
| `outcome_summary.ipynb` | the outcome summary table |
| `trial_metrics.py`, `diff_trial_metrics.py` | pulling and diffing `trial_metrics.json` |

(The doc that used to be `eval/RATINGS.md` is this file.)

### If something looks wrong

- **A rating session refuses to start** — question numbering drifted; the error
  names the file, the question and the repair command.
- **An evaluator's column is missing from `eval_summary.md`** — run
  `python3 -m ratings merge <dataset> --apply`; if it is still missing, that
  evaluator has no ratings recorded for the dataset yet.
- **A master dossier was regenerated** — the next rating session re-syncs each
  evaluator's copy and re-applies their existing ratings by question; a question
  that disappeared from the master reports its dropped rating as a warning.
- **A reference `DECISIONS.md` was renumbered** — `archive/rebuild_dossiers.py`
  is the recovery path; see [archive/README.md](archive/README.md).
