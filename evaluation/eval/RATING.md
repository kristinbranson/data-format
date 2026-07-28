# Human rating workflow

How a second evaluator (KB) rates the agent-produced conversion code, where
those ratings are stored, and how they are combined with the existing ratings
(LZ) and the LLM judges into the tables the analysis reads.

## TL;DR

All commands run from `evaluation/eval/`. Substitute the evaluator code and the
dataset; `<dataset>` is one of `allen2p`, `chen2024`, `hasnain2024`, `lee2025`,
`majnik2025`, `sosa2024`, `zhang2025`, `zhong2025`.

```bash
cd /groups/zhang/home/zhangl5/Data-Format/evaluation/eval

# 1. Rate. With a reference (allen2p, lee2025, majnik2025, sosa2024):
python3 rate.py <dataset> --rater KB
#    Without one (chen2024, hasnain2024, zhang2025, zhong2025):
python3 rate_blind.py <dataset> --rater KB
#    Stop any time with Ctrl-C; re-run the same command to resume.

# 2. Fold the new ratings into the combined table.
python3 raters.py merge <dataset> --apply      # omit <dataset> for all of them

# 3. Regenerate the report.
python3 report.py <dataset>                    # --rater KB for KB's version

# 4. Sanity check (optional — step 1 runs this check itself).
python3 raters.py check
```

Repeat 1–3 per dataset.

### Stopping, resuming, re-rating

```bash
# Resume after Ctrl-C — just run the same command again. Already-rated
# questions are skipped silently; nothing is lost.
python3 rate.py <dataset> --rater KB

# Redo ONE question (re-prompts all 6 trials). Without --overwrite the
# question is treated as done and skipped without a prompt.
python3 rate.py <dataset> --rater KB --question 3-a --overwrite

# Redo the WHOLE dataset.
python3 rate.py <dataset> --rater KB --overwrite

# Start that evaluator's dataset from scratch — deletes their ratings *and*
# their summary.md for it, then reseeds blank copies from the masters.
rm -rf <dataset>/KB
python3 rate.py <dataset> --rater KB
```

The same flags work for `rate_blind.py`; there, pressing Enter at a rating
prompt skips that trial without writing anything.

After any re-rating, re-run steps 2 and 3 so the combined table and the report
pick up the change:

```bash
python3 raters.py merge <dataset> --apply && python3 report.py <dataset>
```

Two things to know:

- Ratings are written the moment they are entered, so Ctrl-C never loses more
  than the question you were on.
- Deleting an evaluator's folder removes their ratings for that dataset (they
  survive in git history). Until they rate something again, the next merge
  drops their column from `eval_summary.md` — `raters.py merge` prints the
  column list on every run, so watch that line.

Everything else below is detail.

Evaluators are registered in [`raters.json`](raters.json):

| code | role |
|---|---|
| `LZ` | primary — also owns the judge-comparison pass (`compare.py`) |
| `KB` | second evaluator — solution ratings only |

Add an evaluator by appending an entry there; nothing else needs changing.

---

## 1. How KB does the rating

Everything runs from `evaluation/eval/`. Which script to use depends on whether
the dataset has a hand-written reference solution
(`manual/<dataset>/DECISIONS.md`):

| script | datasets |
|---|---|
| `rate.py` | `allen2p`, `lee2025`, `majnik2025`, `sosa2024` |
| `rate_blind.py` | `chen2024`, `hasnain2024`, `zhang2025`, `zhong2025` |

```bash
cd /groups/zhang/home/zhangl5/Data-Format/evaluation/eval

python3 rate.py allen2p --rater KB          # reference available
python3 rate_blind.py chen2024 --rater KB   # no reference
```

Without `--rater` the script asks for the code; `export DATAFORMAT_RATER=KB`
sets it for a whole session. An unregistered code is rejected rather than
silently creating a new folder.

On the first run for a dataset the script creates `eval/<dataset>/KB/` by
copying the master dossiers from the dataset root — same questions, same
numbering as every other evaluator, with the ratings blank. **KB never sees
LZ's ratings**, and the two never write the same file.

### What a session looks like

**`rate.py`** — one question at a time, and for each question the six trials
(3 claude-code + 3 codex) in shuffled order under anonymous labels:

- Left panel: the reference answer. Right panel: `SAMPLE A (1/6)` — that
  trial's notes excerpt, code excerpt and neutral description. The agent's
  identity is hidden.
- Prompt: `Rating [better | match | ok | concerning | incorrect | missing]`,
  shortcuts `b` / `m` / `o` / `c` / `i` (or `x`) / `n`.
- Prompt: a free-text `Note` (blank is fine).
- After all six: the `A–F → agent / trial` mapping is revealed, then one
  free-text **overall comment** for the question.

**`rate_blind.py`** — no reference to compare against, so each trial is shown
on its own:

- One `SOLUTION` panel per trial, in an order shuffled per question. The agent
  and trial number *are* shown in the header here — only `rate.py` blinds them.
- The Claude/Codex judge panels are shown **only to the primary evaluator**, so
  KB's ratings stay independent of the LLM judges.
- Scale is `match | ok | concerning | incorrect` (`m` / `o` / `c` / `i`); no
  `better` / `missing`, since there is no reference to be better than. Enter
  skips a trial without writing anything.
- After the six trials: a recap table and one **solution note** for the
  question. KB is not asked for a judge note.

### Stopping and resuming

Each rating is written to disk as soon as it is entered, so Ctrl-C or Ctrl-D is
safe. Re-running the same command picks up where it stopped — questions already
rated are skipped silently. Useful flags:

```bash
python3 rate.py allen2p --rater KB --question 3-a   # just one question
python3 rate.py allen2p --rater KB --overwrite      # re-rate everything
```

### The startup check

Both scripts verify, before showing anything, that the reference, the dossiers
and the summary files still agree on what each question number means. Question
numbering has drifted twice in this project, and a silent mismatch would pair
one question's rating with another question's content.

- Drift the tools resolve themselves prints a note and continues:
  `Note: 12 question(s) numbered differently in the dossiers; pairing them by content (3-a→5-a, …)`
  (`allen2p`'s reference was reordered after its dossiers were generated;
  `rate.py` pairs the two by what the question is *about*, not by its number.)
- Drift that cannot be resolved aborts the session with the command that
  repairs it. Do not work around it — a rating entered against the wrong
  question is worse than a missing one.

Run it by hand any time with `python3 raters.py check [dataset]`.

---

## 2. Where the ratings are recorded

```
eval/<dataset>/
  claude-code_trial1.md …      masters: dossier content, ratings blank
  LZ/
    claude-code_trial1.md …    LZ's copies, carrying LZ's ratings
    summary.md                 LZ's per-question tables + solution comments
  KB/
    claude-code_trial1.md …    KB's copies, carrying KB's ratings
    summary.md
  eval_summary.md              combined: one column per evaluator + both judges
  report.md                    rendered report
```

**The dossier copies are the source of truth.** Each question in
`<dataset>/KB/<agent>_trial<N>.md` ends with the two lines the tools write:

```markdown
**Rating:** ok

**Note:** relies on an assumption that happens to hold here
```

`summary.md` is a per-question roll-up of the same ratings plus the overall
comment, and `eval_summary.md` is regenerated from the dossiers — so if the two
ever disagree, the dossier wins.

Both evaluators' folders are copies of the same masters, so a given question
number means the same thing in `LZ/` and in `KB/`, and their `summary.md` files
line up row for row.

---

## 3. Combining into the final data format

Fold KB's ratings into the combined table once they exist (any time — it is
idempotent and safe to re-run):

```bash
python3 raters.py merge                  # dry run, all datasets
python3 raters.py merge chen2024 --apply
```

This rewrites each `eval_summary.md` with one rating column per evaluator, read
straight from the dossiers. Judge columns, the `Best` / `Why` adjudication and
the per-question overall comments are preserved untouched:

```markdown
| Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
|---|---|---|---|---|---|---|
| claude-code / trial1 | ok | concerning | ok | incorrect | LZ |  |
```

An evaluator's column appears only once they have at least one rating for that
dataset, so tables stay clean while a pass is in progress.

`eval_summary.md` is the only file the analysis layer reads:

```python
import utils
data = utils.load_all()
q = data["allen2p"]["1"]["c"]

q["human"]            # primary evaluator's scores, 6 trials (unchanged API)
q["humans"]["LZ"]     # per-evaluator scores …
q["humans"]["KB"]     # … for inter-rater agreement
q["claude"], q["codex"], q["best_rating"], q["overall"]
```

Scores are `incorrect=-2, concerning=-1, ok=0, match=1, better=2`; a missing
rating is `NaN`. `metrics.ipynb` / `analysis.ipynb` keep working off
`q["human"]`, so adding KB changes nothing until you deliberately use
`q["humans"]`.

Then render the report — one per evaluator, built from `eval_summary.md` plus
that evaluator's `summary.md` (the primary's, unless `--rater` says otherwise):

```bash
python3 report.py chen2024                # writes chen2024/report.md
python3 report.py chen2024 --rater KB     # same report from KB's ratings/notes
```

The report carries one ratings column per evaluator
(`| Q | Question | LZ | KB | Claude judge | …`), with the evaluator it was built
from first and named in the header — the solution comments and the
judge-was-better markers are theirs. Which questions get a row is still decided
by the summary files, so questions the workflow leaves out of the roll-up (the
alignment questions `rate_blind.py` skips for scalar variables) stay out.

Two parts of `report.md` are hand-curated, not generated, and are carried
across regenerations: the `## Comments` section and the **`Difference
categories`** column (matched to each question by its text, so the values follow
a question even if it is renumbered). Everything else is rebuilt from the
summary files, so edits to other columns will not survive.

---

## Reference

| script | role |
|---|---|
| `rate.py` | rate against a reference `DECISIONS.md` |
| `rate_blind.py` | rate a dataset with no reference |
| `compare.py` | judge-comparison pass — primary evaluator only |
| `report.py` | render `report.md` |
| `raters.py` | shared library, plus `list` / `check` / `merge` subcommands |
| `utils.py`, `metrics.py`, `trial_metrics.py` | notebook analysis |

One-off migration and repair scripts live in [`archive/`](archive/README.md).

### If something looks wrong

- **A rating session refuses to start** — question numbering drifted; the error
  names the file, the question and the repair command.
- **KB's column is missing from `eval_summary.md`** — run
  `python3 raters.py merge <dataset> --apply`; if it is still missing, KB has no
  ratings recorded for that dataset yet.
- **A master dossier was regenerated** — the next rating session re-syncs each
  evaluator's copy to the new content and re-applies their existing ratings by
  question; a question that disappeared from the master reports its dropped
  rating as a warning.
