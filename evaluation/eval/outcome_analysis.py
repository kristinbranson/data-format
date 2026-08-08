"""The paper's four outcome tables, rebuilt across all eight datasets.

The outcome-based half of the evaluation asks what the agent's conversion *is*,
not how its code reads: did it write the files, does the data have the right
shape and scale, and does a decoder trained on it recover the behavior as well
as one trained on the manual reference. `verifier/metrics.json` records all of
that per trial; `trial_metrics.py` collects it and `utils.trial_metrics_df`
flattens it. This module turns that frame into the four tables the paper shows:

    summary_table   the main table -- passes / measured per (dataset, agent)
    checks_table    the pass/fail checks, one mark per trial
    scale_table     agent / reference ratios for the five scale statistics
    decoder_table   agent / reference decoder accuracy, per output variable

The main table is a pure aggregation of the other three, and
`outcome_analysis.ipynb` asserts that rather than trusting it.

Every threshold is imported from the verifier's own `test_outputs.py`, never
restated here, so a limit cannot drift from what the tests assert. Three named
constants deviate from it deliberately, each with a comment saying why:
`COUNT_TOLERANCE`, `MAJNIK_STAT_EXCLUDE` and `INPUT_MATCH_OVERRIDE`.

All eight datasets now have a reference solution, so the supervised /
unsupervised split the published tables carried is gone -- every table is one
uniform block.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utils import (AGENT_SHORT, ARM_AGENT, ARM_COLUMNS, DECODER_VAR_ALIASES,
                   TASK_DISPLAY_NAME, load_reference_stats,
                   load_trial_metrics, trial_metrics_df)

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]

# Thresholds come from the verifier itself. Same import that
# `lesion_analysis.py` uses, and for the same reason: a limit restated here
# could silently disagree with the test that produced the numbers.
sys.path.append(str(ROOT / "template-harbor-task" / "tests"))
import test_outputs as tests  # noqa: E402

STATLIMITS = tests.STATLIMITS
MIN_ACCURACY_FRAC = tests.MIN_ACCURACY_FRAC     # 0.95

# What counts as matching the reference decoder in the summary table. Not
# `MIN_ACCURACY_FRAC`: the decoder table marks every ratio below 0.90 in orange
# or red and leaves the rest black, so scoring at 0.95 would count uncolored
# cells as failures and the two tables would disagree on the page. 0.90 is also
# what the published summary used. `ratio_color` is the single definition of
# that boundary -- change it there and this follows.
DECODER_MIN = 0.90


# ---------- what the tables cover ----------

# The two conditions the paper compares, in column order. The other four
# conditions in the tree (both minimal-prompt arms, terminus-opus, terminus-gpt)
# are the subject of `lesion_analysis.py` and `ratings_experiment.ipynb`.
ARMS = (("claude-code", "full"), ("codex", "full"))

TRIALS = (1, 2, 3)

# `debug` is a throwaway task that `trial_metrics.py` does not filter (its
# SKIP_AGENTS only drops `oracle`, which is an agent name, not a task).
SKIP_DATASETS = {"debug"}

# The project's display order for datasets, in every table and figure. Same
# list as `ratings.analysis.loading.DATASET_ORDER`; the two halves of the
# evaluation share no code by design, so it is restated rather than imported.
DATASET_ORDER = ("allen2p", "lee2025", "majnik2025", "sosa2024",
                 "chen2024", "hasnain2024", "zhang2025", "zhong2025")


# The paper's tables are tight on width, so the qualifier `TASK_DISPLAY_NAME`
# carries for reading on screen is dropped there.
LATEX_DISPLAY_NAME = {"zhang2025": "Zhang2025"}


def display_name(ds: str, *, latex: bool = False) -> str:
    if latex and ds in LATEX_DISPLAY_NAME:
        return LATEX_DISPLAY_NAME[ds]
    return TASK_DISPLAY_NAME.get(ds, ds[:1].upper() + ds[1:])


def arm_label(arm) -> str:
    return ARM_AGENT[tuple(arm)]


def load(*, arms=ARMS, trials=TRIALS, eval_dir: Path = EVAL_DIR) -> pd.DataFrame:
    """The trial metrics, filtered to what the tables cover.

    One row per (dataset, agent, trial): 8 x 2 x 3 = 48. `trials` caps at 3,
    which drops zhang2025/codex's stray fourth run -- a resubmitted trial that
    would otherwise make one cell n=4 while every other cell is n=3.
    """
    df = trial_metrics_df(load_trial_metrics(eval_dir))
    keep = {tuple(a) for a in arms}
    in_arm = pd.Series([(a, p) in keep for a, p in zip(df["agent"], df["prompt"])],
                       index=df.index)
    df = df[~df["dataset"].isin(SKIP_DATASETS) & df["trial"].isin(trials) & in_arm]
    return df.sort_values(["dataset", "agent", "trial"]).reset_index(drop=True)


def _cells(df: pd.DataFrame, dataset: str, fn, *, arms=ARMS, trials=TRIALS):
    """`fn(row)` for every (arm, trial) cell of one dataset, in column order.

    A cell with no trial behind it is None, so a missing run leaves a gap where
    it belongs instead of shifting its neighbors left.
    """
    out = []
    for agent, prompt in arms:
        for trial in trials:
            sub = df[(df.dataset == dataset) & (df.agent == agent)
                     & (df.prompt == prompt) & (df.trial == trial)]
            out.append(None if sub.empty else fn(sub.iloc[0]))
    return out


# ---------- the pass/fail checks ----------

def _has(row, key) -> bool:
    """Whether `key` was recorded for this trial (NaN and None both count as not)."""
    v = row.get(key)
    if v is None:
        return False
    return not (isinstance(v, float) and np.isnan(v))


def _empty_list(row, key) -> bool:
    v = row.get(key)
    return isinstance(v, list) and len(v) == 0


# Datasets whose input-match failure is naming alone, corrected by hand.
#
# lee2025's nine inputs are one-hot indicators the reference calls `blocked_0..8`
# and the agents call `env_partition_*`, `partition_*`, `open_partition_*` or
# `geometry_bin_*` -- no shared vocabulary, so the 0.95-weighted name term puts
# every trial at 0.705-0.893, above the 0.5 limit. The data is right:
# `mean_input_range_error` is 0.000 in all six trials, and the reference's one
# constant variable (`blocked_7`, range [0,0]) is correctly paired with the
# agent's one constant variable every time -- the range term forces that, since
# pairing a constant against a non-constant costs ~1e6. Scored as a pass, marked
# in the table, and explained in the caption.
INPUT_MATCH_OVERRIDE = {"lee2025"}


def _input_variables_match(row):
    """Whether the agent's input variables paired up with the reference's.

    `input_match_mean_cost` is the mean Hungarian assignment cost, and the
    matcher weights name similarity at 0.95 against 0.05 for range agreement --
    so this is a check on naming, not on the data. `mean_input_range_error` is
    the field that tests the values, and it is deliberately not folded in here:
    lee2025 has the corpus's highest matching costs with zero range error, and
    zhong2025 the reverse.

    A task with no decoder inputs cannot fail this. allen2p has `dinput == 0`,
    for which the verifier records a cost of 0.0 by definition; counting that as
    three passes would credit the agent for work it was never asked to do.
    """
    if _has(row, "dinput") and row["dinput"] == 0:
        return None
    if not _has(row, "input_match_mean_cost"):
        return None
    if row["dataset"] in INPUT_MATCH_OVERRIDE:
        return True
    return bool(row["input_match_mean_cost"] < STATLIMITS["input_match_cost"])


def _output_variables_match(row):
    """Whether a one-to-one output matching was found. Inf when the counts differ."""
    if not _has(row, "output_match_mean_cost"):
        return None
    return bool(row["output_match_mean_cost"] < STATLIMITS["output_match_cost"])


def _outputs_unmatched(row) -> bool:
    """The agent's outputs could not be paired with the reference's, at all.

    The Hungarian matcher only pairs equal-sized sets, so producing a different
    *number* of outputs makes every assignment `inf`. That happens once in the
    corpus: majnik2025/codex trial 2 split the reference's one 5-class
    `motion_energy` into five binary `motion_energy_q0..q4`.
    """
    return _output_variables_match(row) is False


def _output_nclasses_match(row):
    """Whether every matched output was discretised into the right class count.

    `output_range_error_<var>` is `|sub_hi - ref_hi|` on integer-coded outputs,
    so zero error is exactly "same number of classes" -- what the verifier's own
    limit of 0.9 tests.

    When the outputs could not be paired at all the field is never written, but
    that is a **failure, not a gap**: an agent that did not produce the
    reference's variables certainly did not give them the right class counts.
    Recording it as unmeasured would shrink the denominator and flatter the
    score -- 12/14 rather than 12/15 for the one trial it affects. Same rule as
    `lesion_analysis.propagate_failures`, and deliberately unlike allen2p's
    input row, which is NA because the check is *undefined* (no inputs exist)
    rather than unmeasurable after an earlier failure.
    """
    if _outputs_unmatched(row):
        return False
    if _output_variables_match(row) is None or not _has(row, "output_range_error_max"):
        return None
    return bool(row["output_range_error_max"] <= STATLIMITS["output_range_error"])


CHECKS = (
    ("Required files", lambda r: (_empty_list(r, "required_files_missing")
                                  and _empty_list(r, "required_files_empty"))),
    ("Data format", lambda r: bool(r.get("full_data_format_valid"))),
    ("Input match", _input_variables_match),
    ("Output match", _output_variables_match),
    ("N output classes", _output_nclasses_match),
)


def check_flags(row) -> dict:
    """The five checks for one trial: True (pass), False (fail) or None (NA)."""
    return {label: fn(row) for label, fn in CHECKS}


# ---------- the scale statistics ----------

SCALE_FIELDS = (
    ("Sessions", "nsessions"),
    ("Trials", "ntrials_total"),
    ("Subjects", "nsubjects"),
    ("Neurons", "nneurons_total"),
    ("T median", "T_median"),
)

# Fields whose agreement is judged as an absolute count difference rather than a
# ratio, and how far off they may be. Subjects are the only one: the verifier
# sets their tolerance to 0 because a conversion should neither drop nor invent
# a subject, but the corpus splits sharply between +/-1 -- an edge case such as a
# subject with no usable trials -- and losses of 7 or 18. A ratio band cannot
# express that, since one subject is 2.7% of allen2p's 37 and 0.7% of
# zhang2025's 136. This is ours, not the verifier's, and the caption says so.
COUNT_TOLERANCE = {"nsubjects": 1}


def stat_passes(field: str, ratio: float, reference=None) -> bool:
    """Whether one scale ratio agrees with the reference.

    `tests.ratio_within_limits` and `STATLIMITS` are the verifier's own, so the
    ratio limits are not a restatement: +/-10% for sessions, trials, neurons and
    median bin count, 0 for subjects. `COUNT_TOLERANCE` then widens subjects to
    one whole subject, which needs `reference` to convert the ratio back into a
    count; without it the verifier's exact rule applies.
    """
    if field in COUNT_TOLERANCE and reference:
        return abs(ratio * reference - reference) <= COUNT_TOLERANCE[field] + 1e-9
    return bool(tests.ratio_within_limits(ratio, STATLIMITS[field + "_ratio"]))

# majnik2025's source experiment has no trial structure -- it is organized only
# at the session level -- so every agent picked its own trial length and bin
# size, all of them defensible and none of them the reference's. Counting the
# two fields that follow from that choice would score a documented ambiguity as
# six failures. The rows still appear in the scale table, starred.
MAJNIK_STAT_EXCLUDE = ("ntrials_total", "T_median")


def scale_fields(dataset: str):
    """(label, field, starred) per scale row, with this dataset's exclusions."""
    return [(label, field, dataset == "majnik2025" and field in MAJNIK_STAT_EXCLUDE)
            for label, field in SCALE_FIELDS]


def scale_rows(df: pd.DataFrame, dataset: str):
    """[(label, starred, [cell ratios], reference absolute), ...]."""
    ref = load_reference_stats(dataset) or {}
    out = []
    for label, field, starred in scale_fields(dataset):
        vals = _cells(df, dataset,
                      lambda r, f=field: r[f + "_ratio"] if _has(r, f + "_ratio") else None)
        out.append((label, starred, vals, ref.get(field)))
    return out


# ---------- the decoder ----------

RATIO_PREFIX = "validation_balanced_accuracy_ratio."
REF_PREFIX = "validation_balanced_accuracy_reference."

# Per-dataset row order, carried over from `metrics.ROW_ORDER` (metrics.py is a
# jupytext notebook and cannot be imported). Roughly most to least decodable,
# which is how the paper reads them. Anything unlisted keeps the alphabetical
# default -- zhong2025 by choice, lee2025 and majnik2025 have one variable each.
ROW_ORDER = {
    "allen2p": ["trial_outcome", "running_speed", "pupil_diameter",
                "image_name", "image_change"],
    "chen2024": ["choice", "outcome", "early_lick", "tongue_y"],
    "hasnain2024": ["context", "outcome", "lick_direction",
                    "tongue_velocity", "paw_velocity", "motion_energy"],
    "sosa2024": ["position", "speed", "lick", "distance_to_reward_zone",
                 "reward_location", "reward_outcome"],
    "zhang2025": ["prior", "choice", "wheel_speed", "whisker_motion_energy"],
}

# Shortened for the table only, where the full name is wider than its column.
VAR_LABEL = {"distance_to_reward_zone": "distance_to_reward"}


def decoder_variables(df: pd.DataFrame, dataset: str) -> list[str]:
    """The dataset's reference output variables, in display order.

    Driven by which `_ratio` columns exist, so a variable the agent invented
    with no reference counterpart is not a row: there is nothing to compare it
    against. Agents produce more outputs than the reference on four datasets.
    """
    sub = df[df.dataset == dataset]
    found = {c[len(RATIO_PREFIX):] for c in sub.columns
             if c.startswith(RATIO_PREFIX) and not sub[c].isna().all()}
    ordered = [v for v in ROW_ORDER.get(dataset, []) if v in found]
    return ordered + sorted(found - set(ordered))


def _reference_scalar(df: pd.DataFrame, dataset: str, column: str):
    """A reference-side value, which every trial of a dataset records identically."""
    sub = df[df.dataset == dataset]
    if column not in sub.columns:
        return None
    vals = sub[column].dropna().unique()
    return float(vals[0]) if len(vals) else None


def _canonical(name) -> str:
    """A variable name with the project's renaming applied, or "" if absent."""
    return DECODER_VAR_ALIASES.get(name, name) if name else ""


def mispaired_outputs(row) -> set[str]:
    """Reference variables the matcher assigned to an implausible partner.

    `test_data_stats` asserts `output_match_mean_cost < 1`, i.e. on the **mean**
    over pairings. One catastrophic assignment averaged with three good ones
    passes: zhong2025/codex trials 2 and 3 come to 0.600. Applying the verifier's
    own limit to each pairing instead separates the corpus cleanly -- 190 of 192
    pairings cost at most 0.422, and the two that exceed 1 are exactly the known
    swap, where reference `visual_stimulus` took the agent's `position_bin` and
    reference `position` took its `visual_stimulus_category` (cost 1.649).

    Trial 1 of the same agent pairs correctly only because it happened to name
    the variable `visual_stimulus`, which forces the assignment at cost 0; naming
    it `visual_stimulus_category` in the other two trials removed that shortcut
    and the range term, half the total weight, preferred the swap.

    Whatever those cells measure, it is not the agent against its counterpart, so
    they are dropped rather than scored -- a failure of our matching, not of the
    conversion.
    """
    pairs = row.get("output_matches")
    # When nothing could be paired at all every cost is inf; that is the whole
    # trial failing, handled by `_outputs_unmatched`, not a per-variable slip.
    if not isinstance(pairs, list) or _outputs_unmatched(row):
        return set()
    over = {p["reference"] for p in pairs
            if p.get("cost") is not None
            and not (p["cost"] < STATLIMITS["output_match_cost"])}
    if not over:
        return set()

    # A swap has two halves and only one is expensive: reference `position` took
    # `visual_stimulus_category` at 1.649, but reference `visual_stimulus` took
    # `position_bin` at 0.422 -- cheap, and just as wrong. The assignment is
    # solved jointly, so once one pairing is over the limit, any pairing in the
    # same trial whose partner canonically belongs to a *different* reference
    # variable is compromised too. Gated on `over` so the alias comparison,
    # which fires on ~30 legitimate renamings corpus-wide, cannot act alone.
    return over | {p["reference"] for p in pairs
                   if _canonical(p["submitted"]) != _canonical(p["reference"])}


class _Sentinel:
    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name


# The agent produced no counterpart for this reference variable. Not an empty
# cell: there is no ratio to print, but the trial did not merely go unmeasured --
# it failed to produce the variable, so it cannot have decoded it as well as the
# reference. Printed as a fail mark and counted as one.
UNMATCHED = _Sentinel("UNMATCHED")

# The matcher paired this reference variable with something implausible AND the
# raw accuracies were not enough to repair it. Dropped from the count entirely --
# our measurement failed, which is not evidence either way about the conversion.
MISPAIRED = _Sentinel("MISPAIRED")

ACC_PREFIX = "validation_balanced_accuracy."


class _RepairedRatio(float):
    """A ratio recomputed from the raw accuracies after a matching error.

    A float everywhere it matters -- compared, formatted and counted like any
    other ratio -- but distinguishable so the table can mark it.
    """


def repaired_ratio(row, var):
    """Recompute a decoder ratio from the raw accuracies, ignoring the matcher.

    `metrics.json` records `validation_balanced_accuracy` keyed by the *agent's*
    variable names and `validation_balanced_accuracy_reference` keyed by the
    *reference's*, and `trial_metrics_df` canonicalizes the former through
    `DECODER_VAR_ALIASES`. So where the alias table knows the agent's name --
    `position_bin` -> `position`, `visual_stimulus_category` -> `visual_stimulus`
    -- the correct partner can be found by name alone and the ratio recomputed
    as `agent / reference`, which is exactly how the verifier forms it.

    Only used to repair `mispaired_outputs`. Elsewhere the matcher's own pairing
    stands, because the alias table does not cover every renaming an agent
    invented (`image_identity`, `absolute_position`, `motion_energy_quintile`),
    and for those this would find no partner where the matcher found a good one.

    Returns None when either side is missing.
    """
    agent, reference = ACC_PREFIX + var, REF_PREFIX + var
    if not (_has(row, agent) and _has(row, reference)) or row[reference] == 0:
        return None
    return float(row[agent]) / float(row[reference])


def _ratio_cell(row, col, var):
    """One decoder cell: the ratio, a sentinel, or None if never measured."""
    if _outputs_unmatched(row):
        return UNMATCHED
    if var in mispaired_outputs(row):
        repaired = repaired_ratio(row, var)
        return MISPAIRED if repaired is None else _RepairedRatio(repaired)
    return float(row[col]) if _has(row, col) else None


def decoder_rows(df: pd.DataFrame, dataset: str):
    """[(variable, [cell ratios], reference accuracy, chance), ...].

    Chance is `1 / output_nclasses_reference_<var>` -- the reference's own class
    count, so it describes the task rather than whatever binning the agent
    chose. That reproduces every chance level the paper quotes.
    """
    out = []
    for var in decoder_variables(df, dataset):
        col = RATIO_PREFIX + var
        vals = _cells(df, dataset, lambda r, c=col, v=var: _ratio_cell(r, c, v))
        n_classes = _reference_scalar(df, dataset, f"output_nclasses_reference_{var}")
        out.append((var, vals,
                    _reference_scalar(df, dataset, REF_PREFIX + var),
                    1.0 / n_classes if n_classes else None))
    return out


def _decoder_flags(row, df: pd.DataFrame, dataset: str) -> list[bool]:
    """Pass/fail per reference output variable, skipping the unmeasured.

    A variable the agent produced no counterpart for counts as a failure rather
    than a gap, for the reason `_output_nclasses_match` gives.
    """
    out = []
    for var in decoder_variables(df, dataset):
        cell = _ratio_cell(row, RATIO_PREFIX + var, var)
        if cell is UNMATCHED:
            out.append(False)
        elif cell is MISPAIRED or cell is None:
            continue
        else:
            out.append(bool(cell >= DECODER_MIN))
    return out


# ---------- the summary ----------

CATEGORIES = ("Checks", "Statistics", "Decoder")

# What a trial has to pass to count as end-to-end clean. The checks are about
# whether the conversion is *defined* the way the reference defines it -- files
# present, variables pairable, class counts equal -- and most of what they catch
# is a naming or convention difference rather than a wrong number. Statistics and
# Decoder are the two that speak to whether the data itself is right, so the
# end-to-end column is built from those.
E2E_CATEGORIES = ("Statistics", "Decoder")

# The rate the published table prints in green.
GREEN = 2 / 3


def trial_flags(row, df: pd.DataFrame, dataset: str) -> dict[str, list[bool]]:
    """Every pass/fail one trial contributes, grouped by category.

    A measurement the verifier never recorded is absent from the list, so it
    neither passes nor fails and shrinks the denominator instead.
    """
    checks = [v for v in check_flags(row).values() if v is not None]
    reference = load_reference_stats(dataset) or {}
    stats = [stat_passes(f, row[f + "_ratio"], reference.get(f))
             for _label, f, starred in scale_fields(dataset)
             if not starred and _has(row, f + "_ratio")]
    return {"Checks": checks, "Statistics": stats,
            "Decoder": _decoder_flags(row, df, dataset)}


def pass_counts(df: pd.DataFrame, *, arms=ARMS) -> pd.DataFrame:
    """Per (dataset, arm): passed / measured in each category, plus end-to-end.

    End-to-end is per trial, not per metric: a trial counts only when every
    metric measured for it passed, across `E2E_CATEGORIES`. That reproduces the
    published column, which also excluded the Checks category -- Sosa2024/Claude
    reads 2/3 there despite its own Checks cell recording a missing README in
    two of the three trials.
    """
    rows = []
    for dataset in [d for d in DATASET_ORDER if d in set(df.dataset)]:
        for agent, prompt in arms:
            totals = {c: [] for c in CATEGORIES}
            per_trial = []
            sub = df[(df.dataset == dataset) & (df.agent == agent)
                     & (df.prompt == prompt)]
            for _, row in sub.iterrows():
                flags = trial_flags(row, df, dataset)
                for c in CATEGORIES:
                    totals[c] += flags[c]
                measured = [f for c in E2E_CATEGORIES for f in flags[c]]
                if measured:
                    per_trial.append(all(measured))
            rows.append({
                "dataset": dataset, "agent": agent, "prompt": prompt,
                **{c: (sum(totals[c]), len(totals[c])) for c in CATEGORIES},
                "End-to-end": (sum(per_trial), len(per_trial)),
            })
    return pd.DataFrame(rows)


# ---------- formatting ----------

def _is_symbol(v) -> bool:
    """Whether a cell holds a mark rather than a number."""
    return v is UNMATCHED or v is MISPAIRED or v is None or (
        isinstance(v, float) and np.isnan(v))


def _numeric_cell(v, *, latex: bool = True) -> str:
    """One cell of a numeric column: formatted, colored, and centered if a mark.

    The numeric columns are right-aligned so the decimal points line up, which
    leaves a short mark ($\\times$, --) pinned to the right edge instead of
    under its header. `\\multicolumn{1}{c}` re-centers just those cells.
    """
    text, color = _fmt_ratio(v, latex=latex), ratio_color(v)
    if color:
        text = rf"\textcolor{{{color}}}{{{text}}}" if latex else text
    return rf"\multicolumn{{1}}{{c}}{{{text}}}" if latex and _is_symbol(v) else text


def _fmt_ratio(v, *, latex: bool = True) -> str:
    if v is UNMATCHED:
        return r"$\times$" if latex else "✗"
    if v is MISPAIRED:
        return r"$\ddag$" if latex else "‡"
    return "--" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.3f}"


def ratio_color(v) -> str | None:
    """The published caption's color rule for an agent / reference ratio."""
    if v is UNMATCHED:
        return "red"
    if v is MISPAIRED:
        return None
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v > 1.10:
        return "blue"
    if v < 0.70:
        return "red"
    if v < 0.90:
        return "orange"
    return None


def _fmt_reference(v, field: str) -> str:
    """An absolute reference value. Neuron counts run to millions, so they are
    kept in K rather than switching units between rows."""
    if v is None:
        return "--"
    if field == "T_median":
        return f"{v:.1f}"
    if field == "nneurons_total" and v >= 100_000:
        return f"{v / 1_000:,.0f}K"
    return f"{v:,.0f}"


def _frac(passed: int, measured: int) -> str:
    return "--" if not measured else f"{passed}/{measured}"


def _escape(s: str) -> str:
    return s.replace("_", r"\_")


# ---------- the tables ----------
#
# Each renderer emits `fmt="latex"` for the paper and `fmt="markdown"` for
# reading in the notebook. The two share their cell values, so what the notebook
# shows is what the .tex file holds.

# Each mark sits in a fixed-width box, so the three trials in a cell line up as
# vertical sub-columns down the whole table. Without it \checkmark, $\times$ and
# -- have different widths and trial 2's mark shifts depending on trial 1's.
# Emitted as macros: it keeps the generated source readable enough to hand-edit,
# and the width is one number to change.
CHECK_MACROS = [
    r"\newcommand{\markbox}[1]{\makebox[1.15em][c]{#1}}",
    r"\newcommand{\ckpass}{\markbox{\textcolor{green!55!black}{\checkmark}}}",
    r"\newcommand{\ckfail}{\markbox{\textcolor{red!70!black}{$\times$}}}",
    r"\newcommand{\ckna}{\markbox{--}}",
]
CHECK_PASS = r"\ckpass"
CHECK_FAIL = r"\ckfail"
CHECK_NA = r"\ckna"


def _arm_header(trailing: str = "") -> list[str]:
    """The two-row `Claude Code | Codex` header shared by the three supplements."""
    spans = " & ".join(rf"\multicolumn{{{len(TRIALS)}}}{{c}}{{{arm_label(a)}}}"
                       for a in ARMS)
    rules, at = [], 3
    for _arm in ARMS:
        rules.append(rf"\cmidrule(lr){{{at}-{at + len(TRIALS) - 1}}}")
        at += len(TRIALS)
    trials = " & ".join(f"T{t}" for _arm in ARMS for t in TRIALS)
    return [f" & & {spans}" + (f" & {trailing}" if trailing else "") + r" \\",
            " ".join(rules)]


def _latex_table(colspec, header, body, *, caption, label, placement="!ht",
                 preamble=None, setup=None) -> str:
    lines = list(preamble or [])
    lines += [rf"\begin{{table}}[{placement}]", r"\centering",
              r"\setlength{\tabcolsep}{4pt}", *(setup or []),
              rf"\begin{{tabular}}{{{colspec}}}", r"\toprule",
              *header, r"\midrule", *body, r"\bottomrule", r"\end{tabular}"]
    if caption:
        lines += [r"\vspace{5pt}", r"\caption{" + caption + "}"]
    if label:
        lines.append(r"\label{" + label + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def _markdown_table(header: list[str], body: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def _blocks(df, row_fn):
    """[(dataset, [(row label, [cells]), ...]), ...] over the datasets present."""
    return [(ds, row_fn(ds)) for ds in DATASET_ORDER if ds in set(df.dataset)]


# (dataset, check) -> the footnote marker its row label carries. Both notes
# describe a convention difference between the reference and the agents rather
# than something an agent got wrong, so the row is marked and explained instead
# of being read at face value.
CHECK_NOTES = {
    ("lee2025", "Input match"): "*",
    ("chen2024", "N output classes"): r"\dag",
    ("hasnain2024", "N output classes"): r"\dag",
}

# Column headers for the paper table. The full names are too wide for five
# columns side by side; the caption spells each one out.
CHECK_HEADER = {
    "Required files": "Files",
    "Data format": "Format",
    "Input match": "Inputs",
    "Output match": "Outputs",
    "N output classes": "N classes",
}

CHECKS_CAPTION = (
    "Verifier checks for each dataset. Each cell holds one mark per trial, "
    "\\checkmark\\ (pass), $\\times$\\ (fail), or -- where the check does not "
    "apply. \\emph{Files} indicates whether all required output files were "
    "present. \\emph{Format} checks whether the converted dataset matches the "
    "prescribed output structure. \\emph{Inputs} and \\emph{Outputs} indicate "
    "whether a one-to-one correspondence could be established between the agent "
    "and reference variables, at the matching costs the verifier enforces; "
    "Allen2P has no decoder inputs, so its \\emph{Inputs} cells do not apply. "
    "\\emph{N classes} checks whether the number of output classes matched the "
    "reference for every output variable; where the variables could not be "
    "matched at all it is marked as failing, since an agent that did not "
    "produce the reference's variables cannot have given them the right class "
    "counts. \\vspace{5pt} \\\\\n"
    "\\footnotesize{*For Lee2025 the matching cost exceeds the verifier's limit "
    "on all six trials, but only because of naming: the reference calls its "
    "nine one-hot environment indicators \\texttt{blocked\\_0..8} while the "
    "agents call them \\texttt{env\\_partition\\_*}, \\texttt{partition\\_*}, "
    "\\texttt{open\\_partition\\_*} or \\texttt{geometry\\_bin\\_*}. The cost is "
    "dominated by name similarity; the values agree exactly (mean input range "
    "error 0.000 in every trial), so these are scored as passing. \\\\\n"
    "$\\dag$For Chen2024 and Hasnain2024 the class counts differ by exactly one "
    "on every mismatched variable, in every trial and for both agents. The "
    "manual reference reserves an additional category for samples where the "
    "behavior is undefined -- no-response trials in Chen2024 (14.9\\% of "
    "trials, the same fraction the \\emph{outcome} variable marks as such) and "
    "in Hasnain2024 (13.1\\%) -- whereas the agents excluded those samples "
    "instead. This is a "
    "difference in convention rather than an error in the conversion.}")


def checks_table(df: pd.DataFrame, *, fmt: str = "latex",
                 caption: str | None = CHECKS_CAPTION,
                 label: str = "tab:checks-supervised") -> str:
    """One row per (dataset, check), one mark per (agent, trial)."""
    def rows(ds):
        return [(lbl, _cells(df, ds, lambda r, f=fn: f(r))) for lbl, fn in CHECKS]

    def note(ds, lbl, *, latex=True):
        """The dataset's name, carrying any footnote marker for this check."""
        name = display_name(ds, latex=latex)
        marker = CHECK_NOTES.get((ds, lbl), "")
        if not marker:
            return name
        if not latex:
            return name + marker.replace("\\dag", "†")
        return name + (marker if marker == "*" else f"$^{{{marker}}}$")

    if fmt == "markdown":
        blocks = _blocks(df, rows)
        body = [[display_name(ds) if i == 0 else "", lbl,
                 *["✓" if v else "✗" if v is False else "--" for v in cells]]
                for ds, rs in blocks for i, (lbl, cells) in enumerate(rs)]
        return _markdown_table(
            ["Dataset", "Check",
             *[f"{AGENT_SHORT[arm_label(a)]} T{t}" for a in ARMS for t in TRIALS]],
            body)

    # Datasets down the page, checks across it, and one cell per (dataset,
    # agent) holding that arm's three trial marks. Dataset-major with a row per
    # check ran to 40 rows; splitting it into two panels of four datasets fixed
    # the height but came to 15 columns and overflowed the page. This is 16 rows
    # by 7. Column headers are shortened -- the caption names each check in full.
    present = [d for d in DATASET_ORDER if d in set(df.dataset)]
    marks = {(ds, lbl): [CHECK_PASS if v else CHECK_FAIL if v is False else CHECK_NA
                         for v in cells]
             for ds in present for lbl, cells in rows(ds)}

    body = []
    for ds in present:
        for a, arm in enumerate(ARMS):
            head = (rf"\multirow{{{len(ARMS)}}}{{*}}{{{display_name(ds, latex=True)}}}"
                    if a == 0 else "")
            cells = [head, AGENT_SHORT[arm_label(arm)]]
            for lbl, _fn in CHECKS:
                trials = marks[(ds, lbl)][a * len(TRIALS):(a + 1) * len(TRIALS)]
                marker = CHECK_NOTES.get((ds, lbl), "")
                cells.append("".join(trials)
                             + (f"$^{{{marker}}}$" if marker else ""))
            body.append(" & ".join(cells) + r" \\")
        if ds != present[-1]:
            body.append(r"\midrule")

    return _latex_table(
        "l l " + "c" * len(CHECKS),
        [" & ".join(["Dataset", "Agent",
                     *[CHECK_HEADER[lbl] for lbl, _fn in CHECKS]]) + r" \\"],
        body, caption=caption, label=label, placement="htb",
        # A rule between datasets and a little air in every row: eight blocks of
        # dense glyphs read as one block otherwise.
        setup=[r"\renewcommand{\arraystretch}{1.25}"],
        preamble=[r"% requires \usepackage{booktabs, multirow, xcolor, amssymb}",
                  *CHECK_MACROS, ""])


SCALE_CAPTION = (
    "Dataset statistics. Each cell reports the ratio between the agent solution "
    "and the manual reference for the corresponding metric (three trials per "
    "agent). Metrics include the total number of sessions, trials, subjects, "
    "and neurons, as well as the median number of time bins per trial. Colors "
    "indicate agreement with the reference: black denotes close agreement, "
    "\\textcolor{blue}{blue} indicates ratio $> 1.10$, \\textcolor{orange}"
    "{orange} indicates $0.70 \\leq$ ratio $< 0.90$, and \\textcolor{red}{red} "
    "indicates ratio $< 0.70$. \\vspace{5pt} \\\\\n"
    "\\footnotesize{*For Majnik2025, the original experiment does not define an "
    "explicit trial structure and is organized only at the session level. To "
    "construct trials, all agents selected trial lengths and temporal bin sizes "
    "that were consistent with the decoding analysis described in the original "
    "paper, but differed from the manual reference solution. These two metrics "
    "are excluded from that dataset's Statistics count in "
    "Table~\\ref{outcome_summary}.}")


def scale_table(df: pd.DataFrame, *, fmt: str = "latex",
                caption: str | None = SCALE_CAPTION,
                label: str = "scale-supervised") -> str:
    """One row per (dataset, scale metric): six ratios and the reference value."""
    blocks = _blocks(df, lambda ds: scale_rows(df, ds))
    fields = {label_: field for label_, field in SCALE_FIELDS}

    if fmt == "markdown":
        body = [[display_name(ds) if i == 0 else "", lbl + ("*" if star else ""),
                 *[_fmt_ratio(v, latex=False) for v in cells],
                 _fmt_reference(ref, fields[lbl])]
                for ds, rs in blocks
                for i, (lbl, star, cells, ref) in enumerate(rs)]
        return _markdown_table(
            ["Dataset", "Metric",
             *[f"{AGENT_SHORT[arm_label(a)]} T{t}" for a in ARMS for t in TRIALS],
             "Reference"], body)

    body = []
    for ds, rs in blocks:
        for i, (lbl, star, cells, ref) in enumerate(rs):
            head = (rf"\multirow{{{len(rs)}}}{{*}}{{{display_name(ds, latex=True)}}}"
                    if i == 0 else "")
            nums = [_numeric_cell(v) for v in cells]
            body.append(" & ".join([head, lbl + ("*" if star else ""), *nums,
                                    _fmt_reference(ref, fields[lbl])]) + r" \\")
        if ds != blocks[-1][0]:
            body.append(r"\midrule")

    return _latex_table(
        "l l " + " ".join("r" * len(TRIALS) for _a in ARMS) + " c",
        [*_arm_header("Reference"),
         " & ".join(["Dataset", "Metric",
                     *[f"T{t}" for _a in ARMS for t in TRIALS], ""]) + r" \\"],
        body, caption=caption, label=label)


DECODER_CAPTION = (
    "Per-trial decoder performance. The numeric columns report the ratio of "
    "validation balanced accuracy for decoders trained on each agent solution "
    "relative to the manual reference (three trials per agent). Colors indicate "
    "accuracy relative to the reference: black denotes similar performance, "
    "\\textcolor{blue}{blue} for ratio $> 1.10$, \\textcolor{orange}{orange} "
    "for $0.70 \\leq$ ratio $< 0.90$, and \\textcolor{red}{red} for ratio $< "
    "0.70$. The ``reference'' column shows the absolute validation balanced "
    "accuracy of the manual reference solution, with chance level indicated in "
    "parentheses. Rows are the reference solution's output variables; a "
    "variable an agent produced with no reference counterpart has nothing to be "
    "compared against and is not shown. $\\times$ marks a reference variable the "
    "agent produced no counterpart for, which counts as a failure.")


def decoder_table(df: pd.DataFrame, *, fmt: str = "latex",
                  caption: str | None = DECODER_CAPTION,
                  label: str = "decoder-supervised") -> str:
    """One row per (dataset, output variable): six ratios, reference and chance."""
    blocks = _blocks(df, lambda ds: decoder_rows(df, ds))

    def ref_cell(ref, chance):
        if ref is None:
            return "--"
        return f"{ref:.3f}" + (f" ({chance:.3f})" if chance else "")

    if fmt == "markdown":
        body = [[display_name(ds) if i == 0 else "", VAR_LABEL.get(var, var),
                 *[_fmt_ratio(v, latex=False) for v in cells], ref_cell(ref, chance)]
                for ds, rs in blocks
                for i, (var, cells, ref, chance) in enumerate(rs)]
        return _markdown_table(
            ["Dataset", "Variable",
             *[f"{AGENT_SHORT[arm_label(a)]} T{t}" for a in ARMS for t in TRIALS],
             "Reference (chance)"], body)

    body = []
    for ds, rs in blocks:
        for i, (var, cells, ref, chance) in enumerate(rs):
            head = (rf"\multirow{{{len(rs)}}}{{*}}{{{display_name(ds, latex=True)}}}"
                    if i == 0 else "")
            nums = [_numeric_cell(v) for v in cells]
            body.append(" & ".join([head, _escape(VAR_LABEL.get(var, var)), *nums,
                                    ref_cell(ref, chance)]) + r" \\")
        if ds != blocks[-1][0]:
            body.append(r"\midrule")

    return _latex_table(
        "l l " + " ".join("r" * len(TRIALS) for _a in ARMS) + " c",
        [*_arm_header("Reference"),
         " & ".join(["Dataset", "Variable",
                     *[f"T{t}" for _a in ARMS for t in TRIALS], "(Chance)"]) + r" \\"],
        body, caption=caption, label=label)


SUMMARY_CAPTION = (
    "Summary of outcome-based evaluation of agent performance. In each cell, "
    "the top value corresponds to Claude Code and the bottom value corresponds "
    "to Codex. Values aggregate across all trials and metrics within each "
    "category. \\emph{Checks} reports the fraction of pass/fail validation "
    "checks passed (Table~\\ref{tab:checks-supervised}). \\emph{Statistics} is "
    "the fraction of dataset summary statistics that agree with the manual "
    "reference, within 10\\% for sessions, trials, neurons and median bin "
    "count and to within one subject, since a conversion should neither drop "
    "nor invent them (Table~\\ref{scale-supervised}). \\emph{Decoder} is the "
    "fraction of decoder metrics for which validation accuracy reached at "
    "least 90\\% of the reference, the threshold below which "
    "Table~\\ref{decoder-supervised} colors a cell. \\emph{End-to-end} counts "
    "trials in which every statistic and decoder metric measured for that "
    "trial passed simultaneously; the checks are excluded, since they test "
    "whether the conversion is defined as the reference defines it rather than "
    "whether its values are right. A measurement the verifier did not record "
    "is excluded from both the numerator and the denominator, so denominators "
    "differ between datasets; the exception is a measurement that could not be "
    "taken because of an earlier failure by the agent, which counts as a "
    "failure rather than a gap. Green text highlights high agreement rates.")


def summary_table(df: pd.DataFrame, *, fmt: str = "latex",
                  caption: str | None = SUMMARY_CAPTION,
                  label: str = "outcome_summary") -> str:
    """The main table: one row per dataset, one line per agent inside each cell.

    Every number is a count over the other three tables, so this cannot say
    anything they do not; `outcome_analysis.ipynb` asserts that rather than
    trusting it.
    """
    counts = pass_counts(df)
    columns = (*CATEGORIES, "End-to-end")
    datasets = [d for d in DATASET_ORDER if d in set(counts.dataset)]

    if fmt == "markdown":
        body = []
        for ds in datasets:
            for i, (agent, prompt) in enumerate(ARMS):
                r = counts[(counts.dataset == ds) & (counts.agent == agent)
                           & (counts.prompt == prompt)].iloc[0]
                body.append([display_name(ds) if i == 0 else "",
                             AGENT_SHORT[arm_label((agent, prompt))],
                             *[_frac(*r[c]) for c in columns]])
        return _markdown_table(["Dataset", "Agent", *columns], body)

    def cell(dataset, column):
        """Both agents' fractions stacked, each green when it clears the rate."""
        parts = []
        for agent, prompt in ARMS:
            r = counts[(counts.dataset == dataset) & (counts.agent == agent)
                       & (counts.prompt == prompt)].iloc[0]
            passed, measured = r[column]
            text = _frac(passed, measured)
            if measured and passed / measured >= GREEN:
                text = rf"\textcolor{{highGreen}}{{{text}}}"
            parts.append(text)
        return r"\makecell{" + r"\\".join(parts) + "}"

    body = []
    for ds in datasets:
        body.append(display_name(ds, latex=True))
        body += [f"& {cell(ds, c)}" for c in columns]
        body.append(r"\\")

    lines = [r"\begin{table}[b]", r"\centering", r"\small",
             r"\begin{NiceTabular}{l c c c c}[",
             r"  cell-space-top-limit = 1pt,",
             r"  cell-space-bottom-limit = 1pt,",
             r"  colortbl-like", r"]",
             r"\CodeBefore",
             # One header row now that the supervised/unsupervised split is gone,
             # so the shading starts a row earlier than it used to.
             r"  \rowcolors{2}{}{rowgray}",
             r"\Body", r"\toprule",
             " & ".join(["Dataset", *columns]) + r" \\",
             r"\midrule", *body, r"\bottomrule", r"\end{NiceTabular}"]
    if caption:
        lines += [r"\vspace{6pt}", r"\caption{" + caption + "}"]
    if label:
        lines.append(r"\label{" + label + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


TABLES = {
    "table_summary": summary_table,
    "checks_supervised": checks_table,
    "sup_datasize": scale_table,
    "sup_decoder": decoder_table,
}


# ---------- comparing conditions ----------
#
# The figures `ratings_experiment` uses for the judge ratings, applied to the
# verifier metrics: harness (agent vs Terminus on the same model) and prompt
# (maximal vs minimal for the same agent). One point per trial, a bar at the
# condition's mean within the dataset, a dashed line joining the two means, and
# a pooled box panel.
#
# A point is a **share of metrics passed**, not a mean of the ratios. Averaging
# ratios does not work here: they are two-sided and unbounded above, so
# zhang2025/claude's 7-8x neuron count would score better than a perfect 1.0.
# `lesion_analysis` reaches the same conclusion -- every one of its nine
# categories is a fraction of pass/fail indicators, never a ratio magnitude --
# and this reuses the pass rules the three tables above already apply, so a point
# is the summary table's cell broken out by trial.
#
# The figure itself is `ratings.analysis.conditions.condition_scatter`. The two
# halves of the evaluation deliberately share no data vocabulary, but this is
# layout, and the requirement is that the two sets of figures look identical --
# which a copy cannot guarantee. Importing costs one module and reads nothing.
from ratings.analysis import conditions as _conditions  # noqa: E402
from ratings.experiments import condition_key  # noqa: E402

# Every condition the run tree holds, not just the two the paper's tables show.
# The comparisons below need the minimal-prompt and Terminus arms.
ALL_ARMS = tuple(tuple(a) for a in ARM_COLUMNS)

# What one point measures. Statistics and Decoder are the two categories that
# speak to whether the data is right; the checks mostly catch naming and
# convention differences, which is why `E2E_CATEGORIES` excludes them too.
SCORE_CATEGORIES = E2E_CATEGORIES

SCORE_LABEL = "verifier metrics passed"

# The four contrasts, in the order `ratings_experiment` makes them: the harness
# held against the same underlying model, then the prompt held against the same
# agent.
HARNESS_PAIRS = (
    ("Opus 4.6: Claude Code vs Terminus",
     ("claude-code/full", "terminus-opus/full")),
    ("GPT: Codex vs Terminus", ("codex/full", "terminus-gpt/full")),
)
PROMPT_PAIRS = tuple(
    (f"{ARM_AGENT[(agent, 'full')]}: full vs minimal prompt",
     (condition_key(agent, "full"), condition_key(agent, "minimal")))
    for agent in ("claude-code", "codex"))


def trial_scores(df: pd.DataFrame, *, arms=ALL_ARMS) -> pd.DataFrame:
    """One row per (dataset, condition, trial, category): the share that passed.

    Rows for each of `CATEGORIES` plus `"Outcome"`, which pools
    `SCORE_CATEGORIES` and is what the comparison figures plot.

    `n` is how many metrics the share rests on, which varies -- a dataset has
    between one and six decoded variables, and majnik2025 contributes three
    scale metrics rather than five. A category with nothing measured for a trial
    is omitted rather than scored 0.
    """
    rows = []
    for dataset in [d for d in DATASET_ORDER if d in set(df.dataset)]:
        for agent, prompt in arms:
            sub = df[(df.dataset == dataset) & (df.agent == agent)
                     & (df.prompt == prompt)]
            for _, row in sub.iterrows():
                flags = trial_flags(row, df, dataset)
                flags["Outcome"] = [f for c in SCORE_CATEGORIES for f in flags[c]]
                for category, got in flags.items():
                    if not got:
                        continue
                    rows.append({
                        "dataset": dataset, "agent": agent, "prompt": prompt,
                        "condition": condition_key(agent, prompt),
                        "trial": int(row["trial"]), "category": category,
                        "n": len(got), "passed": sum(got),
                        "score": sum(got) / len(got),
                    })
    return pd.DataFrame(rows)


def condition_scatter(scores: pd.DataFrame, pair, *, category: str = "Outcome",
                      **kw):
    """One comparison figure. Returns `(fig, (ax, ax_box))`.

    `pair` is the two conditions to contrast; `condition_labels` drops whichever
    half they share, so a harness pair is labelled by agent and a prompt pair by
    prompt.
    """
    kw.setdefault("ylabel", SCORE_LABEL)
    kw.setdefault("labels", _conditions.condition_labels(pair))
    # Axis ticks use the same short names the paper's tables do, so Zhang2025
    # keeps its qualifier on screen but not under a figure.
    kw.setdefault("xlabels", lambda ds: display_name(ds, latex=True))
    return _conditions.condition_scatter(
        scores[scores.category == category], conditions=tuple(pair),
        value="score", **kw)
