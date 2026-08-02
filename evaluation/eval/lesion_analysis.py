# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.2
#   kernelspec:
#     display_name: tmp-data-format
#     language: python
#     name: python3
# ---

# %%
# imports and constants/parameters

# %load_ext autoreload
# %autoreload 2

from contextlib import contextmanager
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle as _Rect
from utils import load_trial_metrics, TASK_DISPLAY_NAME, ARM_COLUMNS, ARM_AGENT, AGENT_SHORT, PROMPT_LABEL, SUPERVISED_DS, UNSUPERVISED_DS
import textwrap

try:
    # running as a script via jupytext
    EVAL_DIR = Path(__file__).resolve()
except NameError:
    # running in a notebook: use metrics.py
    # so two levels up is data-format/
    EVAL_DIR = Path("metrics.py").resolve()

ROOT = EVAL_DIR.parents[2]  # two levels up is data-format/

# import ROOT.template-harbor-task.tests.test_outputs
# add tests to sys.path so we can import test_outputs.py from template-harbor-task
import sys
sys.path.append(str(ROOT / "template-harbor-task" / "tests"))
import test_outputs as tests

# Where LaTeX table dumps land (one .tex per table for inclusion via \input).
FIGURES_DIR = ROOT / "figures"
print(f"Figures will be written to {FIGURES_DIR}")

import seaborn as sns
sns.set_theme(style="ticks", rc={"axes.spines.right": False, "axes.spines.top": False})
import matplotlib as mpl
mpl.rcParams['figure.dpi'] = 300
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['ps.fonttype'] = 42

_cmap     = plt.get_cmap("RdYlGn")
_cnorm    = mcolors.TwoSlopeNorm(vmin=0.5, vcenter=1.0, vmax=1.5)
NAN_GREY  = "#f2f2f2"
RAW_GREY  = "#cfcfcf"
PASS_GREEN = "#7fc97f"   # easier on the eye than full saturation
FAIL_RED   = "#e08585"
_cmap = mcolors.LinearSegmentedColormap.from_list(
    "LightRdYlGn", [FAIL_RED, "#f7f1b5", PASS_GREEN]
)

TRIAL_METRICS_JSON = 'trial_metrics_all.json'

data = load_trial_metrics(filename=TRIAL_METRICS_JSON)

TRIALS_PER_ARM = 3
N_CELLS = len(ARM_COLUMNS) * TRIALS_PER_ARM

# The full set, kept so set_arms() can restore it after a subset plot.
ALL_ARMS = list(ARM_COLUMNS)

SCALE_FIELDS = [
    ("Sessions",  "nsessions"),
    ("Trials",    "ntrials_total"),
    ("Subjects",  "nsubjects"),
    ("Neurons",   "nneurons_total"),
    ("T median",  "T_median"),
]


# %%
# look at the data
datasets = sorted(list(data.keys()))
# union all agents across datasets
agents = sorted(list({agent for dataset in datasets for agent in data[dataset].keys()}))
# union all prompts across datasets and agents
prompts = sorted(list({prompt for dataset in datasets for agent in data[dataset].keys() for prompt in data[dataset][agent].keys()}))
trials = sorted([str(trial+1) for trial in range(TRIALS_PER_ARM)])
print(f'datasets: {datasets}')
print(f'agents: {agents}')
print(f'prompts: {prompts}')

print(f'\ndata keys for {datasets[0]} / {agents[0]} / {prompts[0]} / {trials[0]}:')
for k,v in data[datasets[0]][agents[0]][prompts[0]][trials[0]].items():
    print(f'{k}: {v}')


# %% [markdown]
# For each dataset, i want to divide the metrics that we have into the following categories:
#
# 1. converted_data.pkl and convert_data.py exist
# 2. other required files exist
# 3. converted_data.pkl properly formatted (see test_verify_data_format)
# 4. nneurons_total matches (based on STATLIMITS, see test_data_stats)
# 5. fraction of nsubjects, nsessions, ntrials_total matches (based on STATLIMITS, see test_data_stats)
# 6. fraction of input variables that match range
# 7. fraction of output variables that match nclasses
# 8. fraction of output variables that match distribution (output_fraction)
# 9. fraction of output variables for which decoder accuracy ratio large enough

# %%
# Constants and reference statistics for the lesion categories.

import functools
import json

from trial_metrics import DATASET_ALIASES

# Thresholds come from the verifier itself so a limit is never restated here and
# the analysis cannot drift from what test_outputs.py actually asserts.
STATLIMITS = tests.STATLIMITS                # {'<field>_ratio': tolerance, ...}
MIN_ACCURACY_FRAC = tests.MIN_ACCURACY_FRAC  # 0.95

# The two files without which the conversion is worthless, and the rest.
CORE_FILES = ['converted_data.pkl', 'convert_data.py']
OTHER_FILES = [f for f in tests.REQUIRED_FILES if f not in CORE_FILES]

# Scale fields pooled into one fraction (category 6). nneurons_total is checked
# on its own as category 5, and T_median is not part of the requested split.
SCALE_FIELDS_CHECK = ['nsubjects', 'nsessions', 'ntrials_total']

# An input variable matches when its endpoint error is within this fraction of
# the reference variable's span. Relative, not absolute: reference spans differ
# by three orders of magnitude across datasets (majnik2025 'time' spans 1800,
# lee2025 'blocked_*' span 1), so no absolute cut is meaningful for all of them.
# 0.1 is the same 10% convention STATLIMITS applies to the scale ratios.
INPUT_RANGE_TOL = 0.1

# An output variable matches in distribution when the L1 distance between the
# sorted class-fraction vectors is at most this. That field ranges 0-2.
OUTPUT_FRACTION_TOL = 0.1

# trial_metrics.py renames harbor task directories into the manual/ vocabulary
# (map -> chen2024). Invert it to get back to the directory holding the stats.
TASK_DIR_NAME = {v: k for k, v in DATASET_ALIASES.items()}


@functools.lru_cache(maxsize=None)
def load_reference_stats(dataset):
    """Oracle summary statistics for one dataset, or None if it has none.

    Needed only by category 7: the recorded input_range_error_<var> is an
    absolute endpoint error, and turning it into a pass/fail needs the reference
    variable's span, which no field of metrics.json carries.

    Args:
        dataset: metrics-side dataset name, e.g. 'chen2024'. The harbor task
            directory may be named differently, e.g. 'map'.

    Returns:
        The 'data_summary' sub-dict of
        harbor-tasks/<task>/tests/reference_stats_full.json: 'input_range' and
        'output_range' as {variable_name: [lo, hi]} in the variable's own units,
        plus the scalar scale fields. None for the unsupervised tasks, which
        ship no reference stats.
    """
    task = TASK_DIR_NAME.get(dataset, dataset)
    path = ROOT / "harbor-tasks" / task / "tests" / "reference_stats_full.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())['data_summary']


# %%
# One function per lesion category, in the order test_outputs.py checks them.
# Each takes a single trial's curated metrics (data[dataset][agent][prompt][trial])
# plus that dataset's reference data_summary, and returns a float in [0, 1] --
# a boolean as 0.0/1.0, a fraction otherwise -- or nan when the verifier never
# recorded the fields it reads.
#
# Every lookup goes through .get(). A trial whose verifier died early carries
# only a handful of keys (sosa2024/terminus-gpt/full/2 has 8 of the ~50), and a
# trial whose metrics.json was never written carries none at all.
#
# The per-variable categories (7-10) iterate the *reference* variable list rather
# than the recorded keys. Two reasons: a variable the agent never produced then
# counts as a miss instead of silently shrinking the denominator, and it steps
# around the derived '<prefix>_max' keys that trial_metrics._curate injects
# alongside the real per-variable fields, which would otherwise be read as a
# variable named "max".

def _files_present(jobdata, filenames):
    """Whether all of `filenames` reached the workdir non-empty.

    Args:
        jobdata: one trial's curated metrics dict.
        filenames: names as they appear in test_outputs.REQUIRED_FILES.

    Returns:
        1.0 when no name appears in either the missing or the empty list, 0.0
        when any does, nan when test_required_files_exist recorded neither list.
    """
    missing = jobdata.get('required_files_missing')
    if missing is None:
        return np.nan
    # required_files_empty catches a file that exists at zero bytes; it is [] on
    # every trial in the current data, but a missing file and an empty one are
    # equally unusable.
    unusable = set(missing) | set(jobdata.get('required_files_empty') or [])
    return float(all(f not in unusable for f in filenames))


def _recorded_bool(jobdata, key):
    """A boolean metric as 0.0/1.0, or nan when the verifier never recorded it."""
    value = jobdata.get(key)
    return np.nan if value is None else float(bool(value))


def _ratio_within_limit(jobdata, field):
    """Whether <field>_ratio (agent/reference) sits inside its STATLIMITS band.

    Args:
        jobdata: one trial's curated metrics dict.
        field: scale field name, e.g. 'nsubjects'. STATLIMITS is keyed by
            '<field>_ratio' and holds a half-width tolerance; 0 means exact.

    Returns:
        1.0, 0.0, or nan when the ratio was not recorded (test_data_stats skipped
        or never got that far).
    """
    ratio = jobdata.get(f'{field}_ratio')
    if ratio is None:
        return np.nan
    limit = STATLIMITS[f'{field}_ratio']
    return float(1 - limit <= ratio <= 1 + limit)


def _reference_output_names(refstats):
    """Reference output variable names, or None when there is nothing to compare."""
    if refstats is None:
        return None
    return list(refstats['output_range']) or None


def core_files_exist(jobdata, refstats):
    """converted_data.pkl and convert_data.py both exist and are non-empty."""
    return _files_present(jobdata, CORE_FILES)


def other_files_exist(jobdata, refstats):
    """The remaining REQUIRED_FILES all exist and are non-empty."""
    return _files_present(jobdata, OTHER_FILES)


def full_data_format_valid(jobdata, refstats):
    """verify_data_format accepted converted_data.pkl.

    Never False anywhere in the current data -- when the test runs at all it
    passes -- so this column reads 1-or-nan. That is the data, not a bug.
    """
    return _recorded_bool(jobdata, 'full_data_format_valid')


def nneurons_total_matches(jobdata, refstats):
    """Total neuron count within STATLIMITS of the reference."""
    return _ratio_within_limit(jobdata, 'nneurons_total')


def scale_matches(jobdata, refstats):
    """Fraction of nsubjects/nsessions/ntrials_total within STATLIMITS.

    nsubjects has a tolerance of 0, so it must match the reference exactly; the
    other two allow 10%.
    """
    within = [_ratio_within_limit(jobdata, field) for field in SCALE_FIELDS_CHECK]
    if all(np.isnan(v) for v in within):
        return np.nan
    return float(np.nanmean(within))


def input_range_matches(jobdata, refstats):
    """Fraction of reference input variables whose range matches.

    A variable matches when its recorded absolute endpoint error is at most
    INPUT_RANGE_TOL of the reference variable's span. This is cost_range from
    test_outputs.match_variables_by_hungarian, including its max(span, 1e-6)
    guard, so a reference variable that is constant (lee2025 blocked_7 = [0, 0])
    matches only on an exactly zero error.

    Not reproduced: the matcher's "both submitted and reference constant -> cost
    0" special case. It needs the submitted span for a given reference variable,
    which the curated metrics cannot supply -- input_range_<var> is keyed by the
    agent's own variable names and the pairing between the two naming schemes
    (input_matches) is dropped by trial_metrics._curate.

    Returns nan when the dataset has no input variables at all (allen2p, where
    the reference input_range is empty and dinput == 0), or when test_data_stats
    never reached the input matcher.
    """
    if refstats is None:
        return np.nan
    reference_ranges = refstats['input_range']   # {name: [lo, hi]}, variable's own units
    if not reference_ranges:
        return np.nan                            # allen2p: dinput == 0
    if 'input_range_mean_cost' not in jobdata:
        return np.nan                            # matcher never ran for this trial
    n_match = 0
    for name, (low, high) in reference_ranges.items():
        error = jobdata.get(f'input_range_error_{name}')  # absolute, variable's units
        if error is None:
            continue                             # unmatched reference variable -> miss
        span = max(abs(high - low), 1e-6)
        if error / span <= INPUT_RANGE_TOL:
            n_match += 1
    return n_match / len(reference_ranges)


def output_nclasses_matches(jobdata, refstats):
    """Fraction of reference output variables with the right number of classes.

    test_data_stats records both counts keyed by the reference variable name:
    output_nclasses_<v> is the agent's and output_nclasses_reference_<v> the
    oracle's, both derived as round(hi - lo + 1) from the respective ranges.
    """
    names = _reference_output_names(refstats)
    if names is None or 'output_fraction_mean_cost' not in jobdata:
        return np.nan
    n_match = sum(
        1 for name in names
        if jobdata.get(f'output_nclasses_{name}') is not None
        and jobdata.get(f'output_nclasses_{name}') == jobdata.get(f'output_nclasses_reference_{name}')
    )
    return n_match / len(names)


def output_fraction_matches(jobdata, refstats):
    """Fraction of reference output variables matching in class distribution.

    output_fraction_error_<v> is the L1 distance between the sorted class-fraction
    vectors, so it ignores a permutation of the class labels and ranges 0-2. A
    recorded None means the agent and reference disagreed on the number of
    classes, which counts as a miss.
    """
    names = _reference_output_names(refstats)
    if names is None or 'output_fraction_mean_cost' not in jobdata:
        return np.nan
    n_match = 0
    for name in names:
        error = jobdata.get(f'output_fraction_error_{name}')
        if error is not None and error <= OUTPUT_FRACTION_TOL:
            n_match += 1
    return n_match / len(names)


def decoder_accuracy_matches(jobdata, refstats):
    """Fraction of output variables whose decoder accuracy clears the bar.

    test_decoder_accuracy asserts sub_acc >= MIN_ACCURACY_FRAC * ref_acc for each
    output and records the per-output quotient in
    validation_balanced_accuracy_ratio, keyed by reference variable name. The
    same >= is used here.

    Absent or None means the verifier never got far enough to record anything --
    the decoder itself produced no accuracy -- so the result is unknown, nan.

    An empty dict is different, and is scored 0.0: the verifier ran, but the
    output matcher produced no usable pairs because the agent's outputs did not
    correspond to the reference's, so nothing could clear the bar.
    majnik2025/codex/full/2 is the case -- it split the reference's single
    motion_energy into five quantile bins. Categories 8 and 9 score that trial 0
    for the same reason, and this keeps the three consistent.

    Individual variables may also be missing from a populated dict, where the
    verifier skipped an entry whose reference accuracy was zero; those count as
    misses.
    """
    names = _reference_output_names(refstats)
    if names is None:
        return np.nan
    ratios = jobdata.get('validation_balanced_accuracy_ratio')
    if ratios is None:
        return np.nan
    n_match = sum(1 for name in names
                  if ratios.get(name) is not None
                  and ratios[name] >= MIN_ACCURACY_FRAC)
    return n_match / len(names)



# (key, display label, scoring function), in the order test_outputs.py checks them.
CATEGORIES = [
    ('core_files_exist',         'Core files exist',      core_files_exist),
    ('other_files_exist',        'Other files exist',     other_files_exist),
    ('full_data_format_valid',   'Converted data format', full_data_format_valid),
    ('nneurons_total_matches',   'N neurons',             nneurons_total_matches),
    ('scale_matches',            'N replicates',          scale_matches),
    ('input_range_matches',      'Input ranges',          input_range_matches),
    ('output_nclasses_matches',  'Output N classes',      output_nclasses_matches),
    ('output_fraction_matches',  'Output distributions',  output_fraction_matches),
    ('decoder_accuracy_matches', 'Decoder accuracy',      decoder_accuracy_matches),
]

CATEGORY_KEYS = [key for key, _label, _fn in CATEGORIES]
CATEGORY_LABELS = {key: label for key, label, _fn in CATEGORIES}


# %%
# Score every trial.

def compute_job_categories(jobdata, refstats):
    """Score one trial against every lesion category.

    Args:
        jobdata: one trial's curated metrics, data[dataset][agent][prompt][trial].
        refstats: that dataset's reference data_summary from
            load_reference_stats, or None when it has no reference solution.

    Returns:
        {category_key: float in [0, 1] or nan}, in CATEGORIES order.
    """
    return {key: fn(jobdata, refstats) for key, _label, fn in CATEGORIES}


# Everything measured on converted_data.pkl, in verifier order. If that file is
# absent, or is not in the required format, none of these could have passed.
CATEGORIES_FROM_CONVERTED_DATA = [
    'full_data_format_valid', 'nneurons_total_matches', 'scale_matches',
    'input_range_matches', 'output_nclasses_matches', 'output_fraction_matches',
    'decoder_accuracy_matches',
]


def missing_or_empty(jobdata, filename):
    """Whether one required file was absent, or present at zero bytes.

    Args:
        jobdata: one trial's curated metrics dict.
        filename: name as it appears in test_outputs.REQUIRED_FILES.

    Returns:
        True/False, or None when test_required_files_exist recorded no lists at
        all, in which case nothing is known about the file either way.
    """
    missing = jobdata.get('required_files_missing')
    if missing is None:
        return None
    return filename in set(missing) | set(jobdata.get('required_files_empty') or [])


def undefined_categories(refstats):
    """Categories with no meaning for this dataset, whatever a trial did.

    Propagation must not reach these: allen2p has no input variables at all, so
    there is no input range for a trial to get right or wrong, and forcing it to
    0 would invent a failure the agent could not have committed.

    Args:
        refstats: the dataset's reference data_summary, or None.

    Returns:
        set of category keys to leave alone.
    """
    if refstats is None:
        # No reference solution, so nothing from the stats test onward is
        # comparable, no matter what the agent produced.
        return set(CATEGORIES_FROM_CONVERTED_DATA[1:])
    if not refstats['input_range']:
        return {'input_range_matches'}
    return set()


def propagate_failures(jobres, jobdata, refstats):
    """Score downstream categories 0 where an earlier failure guarantees it.

    A category is nan when the verifier could not measure it and 0 when it was
    measured and failed. Left alone, those two get conflated: a trial that never
    produced converted_data.pkl has no downstream metrics recorded, so it reads
    as nine unknowns when in fact every one of those checks is a certain failure
    -- there is no data for them to have passed on.

    Only failures the agent is responsible for propagate. A verifier that died
    on a GPU fault (chen2024/terminus-gpt/full/3, lee2025/terminus-gpt/full/2)
    leaves the same absent fields, but there the outcome really is unknown, so
    those stay nan. The discriminator is whether the required file is recorded
    as missing, not whether the metric is absent.

    Args:
        jobres: one trial's raw category scores from compute_job_categories().
        jobdata: that trial's curated metrics dict.
        refstats: the dataset's reference data_summary, or None.

    Returns:
        A new dict; the input is not modified.
    """
    jobres = dict(jobres)
    skip = undefined_categories(refstats)

    if missing_or_empty(jobdata, 'converted_data.pkl'):
        forced = CATEGORIES_FROM_CONVERTED_DATA
    elif jobres['full_data_format_valid'] == 0:
        # The file exists but verify_data_format rejected it, so the stats and
        # the decoder were computed on -- or refused -- malformed data.
        forced = CATEGORIES_FROM_CONVERTED_DATA[1:]
    else:
        forced = []

    for key in forced:
        if key not in skip:
            jobres[key] = 0.0
    return jobres


def lesion_scores(data, datasets=SUPERVISED_DS, *, propagate=True):
    """Score every trial of the given datasets against the lesion categories.

    Args:
        data: nested {dataset: {agent: {prompt: {trial: metrics}}}}, as returned
            by utils.load_trial_metrics.
        datasets: dataset names to include. Defaults to the five supervised
            tasks. The unsupervised ones ship no reference stats, so
            test_data_stats skips before recording anything and categories 5-10
            would be uniformly nan for them.
        propagate: score a downstream category 0 rather than nan when an earlier
            failure by the agent makes it a certain failure -- see
            propagate_failures(). Pass False to see only what the verifier
            actually measured.

    Returns:
        {(dataset, agent, prompt, trial): {category_key: float in [0, 1] or nan}}
        with trial as an int. The flat 4-tuple key is the same one
        diff_trial_metrics.flatten() uses for these trials.
    """
    scores = {}
    for dataset in datasets:
        if dataset not in data:
            print(f'  ! {dataset} not in trial metrics, skipping')
            continue
        refstats = load_reference_stats(dataset)
        if refstats is None:
            print(f'  ! no reference stats for {dataset}, categories 5-10 will be nan')
        for agent, by_prompt in data[dataset].items():
            for prompt, by_trial in by_prompt.items():
                for trial, jobdata in by_trial.items():
                    jobres = compute_job_categories(jobdata, refstats)
                    if propagate:
                        jobres = propagate_failures(jobres, jobdata, refstats)
                    scores[(dataset, agent, prompt, int(trial))] = jobres
    return scores


def dataset_of(trial_key):
    """Dataset name from a (dataset, agent, prompt, trial) score key."""
    return trial_key[0]


scores = lesion_scores(data)
n_per_dataset = {ds: sum(1 for key in scores if dataset_of(key) == ds)
                 for ds in SUPERVISED_DS}
print(f'\n{len(scores)} trials scored across {len(n_per_dataset)} datasets')
print(f'per dataset: {n_per_dataset}')


# %%
# Render: one square per (arm, trial), one row per category, one panel per dataset.

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

def resolve_arms(arms=None, *, agents=None, prompts=None):
    """Which (agent, prompt) arms a figure should show.

    The selection is returned rather than stored, so a figure restricted to a
    subset cannot leak that restriction into the next one. (metrics.py solves the
    same problem with set_arms/arms_subset mutating module globals; importing it
    here would run its whole analysis as a side effect.)

    Left-to-right order follows what the caller asked for: the order of `arms`,
    or of `agents` with `prompts` nested inside each agent. Only when neither is
    given does it fall back to ARM_COLUMNS order. Ordering is a deliberate part
    of a comparison figure -- putting the two arms you are contrasting side by
    side -- so a caller-supplied order is honoured rather than re-sorted.

    Args:
        arms: explicit (agent, prompt) tuples, drawn in this order. Mutually
            exclusive with agents/prompts.
        agents: keep only these agents, drawn in this order.
        prompts: keep only these prompts, drawn in this order within each agent.
            Combines with `agents`; both filters apply. Accepts the display name
            'maximal' as well as the metrics field's 'full', since the figures,
            PROMPT_LABEL and submit_harbor_cluster.py's flags all say maximal.

    Returns:
        list of (agent, prompt) tuples, deduplicated, keeping first occurrence.

    Raises:
        ValueError: on an unknown arm, agent or prompt name, on combining `arms`
            with `agents`/`prompts`, or when the selection matches nothing.
    """
    if arms is not None:
        if agents is not None or prompts is not None:
            raise ValueError('pass either arms, or agents/prompts, not both')
        requested = [tuple(arm) for arm in arms]
        unknown = [arm for arm in requested if arm not in ARM_COLUMNS]
        if unknown:
            raise ValueError(f'unknown arms: {unknown}; known: {ARM_COLUMNS}')
        # dict.fromkeys rather than set(): dedupes while keeping the given order.
        return list(dict.fromkeys(requested))

    if agents is not None:
        known = {agent for agent, _prompt in ARM_COLUMNS}
        unknown = [a for a in agents if a not in known]
        if unknown:
            raise ValueError(f'unknown agents: {unknown}; known: {sorted(known)}')
        agent_order = list(dict.fromkeys(agents))
    else:
        agent_order = list(dict.fromkeys(agent for agent, _prompt in ARM_COLUMNS))

    if prompts is not None:
        known = {prompt for _agent, prompt in ARM_COLUMNS}
        # PROMPT_LABEL renames 'full' to 'maximal' for display, so accept
        # whichever name the caller has in front of them.
        display_to_field = {label: field for field, label in PROMPT_LABEL.items()}
        wanted = [display_to_field.get(p, p) for p in prompts]
        unknown = [p for p in wanted if p not in known]
        if unknown:
            raise ValueError(f'unknown prompts: {unknown}; '
                             f'known: {sorted(known | set(PROMPT_LABEL.values()))}')
        prompt_order = list(dict.fromkeys(wanted))
    else:
        prompt_order = None   # per-agent, in ARM_COLUMNS order

    # Agent-major, prompt-minor -- the nesting ARM_COLUMNS itself uses, so a
    # multi-prompt selection still reads as one group per agent.
    prompts_of_agent = {}
    for agent, prompt in ARM_COLUMNS:
        prompts_of_agent.setdefault(agent, []).append(prompt)

    selected = []
    for agent in agent_order:
        for prompt in (prompt_order if prompt_order is not None
                       else prompts_of_agent[agent]):
            if (agent, prompt) in ARM_COLUMNS:
                selected.append((agent, prompt))

    if not selected:
        raise ValueError('arm selection is empty')
    return selected


def cell_index(agent, prompt, trial, arms):
    """Column for one trial within the arm x trial strip.

    Args:
        agent: agent name as it appears in the trial metrics, e.g. 'claude-code'.
        prompt: 'full' or 'minimal'.
        trial: 1-based trial number.
        arms: displayed arms, from resolve_arms().

    Returns:
        Column index into the len(arms) * TRIALS_PER_ARM strip, or None when this
        (agent, prompt) arm is not displayed, or when the trial number is beyond
        TRIALS_PER_ARM. unplaced_trials() reports whatever is dropped.
    """
    arm = (agent, prompt)
    # The trial bound is not decoration: zhang2025/codex/full has a fourth run,
    # from a separate job two weeks after the first three, and without this it
    # indexes past the end of its three-wide group.
    if arm not in arms or not 1 <= trial <= TRIALS_PER_ARM:
        return None
    return arms.index(arm) * TRIALS_PER_ARM + (trial - 1)


def category_matrix(scores, dataset, arms):
    """Scores for one dataset laid out for plotting.

    Args:
        scores: the score dict from lesion_scores().
        dataset: dataset name to extract.
        arms: displayed arms, from resolve_arms().

    Returns:
        (n_categories, len(arms) * TRIALS_PER_ARM) float array in CATEGORIES row
        order, nan wherever the category is undetermined or no trial occupies
        that cell.
    """
    grid = np.full((len(CATEGORIES), len(arms) * TRIALS_PER_ARM), np.nan)
    for (ds, agent, prompt, trial), jobres in scores.items():
        if ds != dataset:
            continue
        column = cell_index(agent, prompt, trial, arms)
        if column is None:
            continue
        for i, key in enumerate(CATEGORY_KEYS):
            grid[i, column] = jobres[key]
    return grid


def unplaced_trials(scores, arms=None):
    """Score keys whose (agent, prompt) arm is not among the displayed arms.

    With the default full set of arms a non-empty result means those trials are
    silently missing from every figure, which is worth printing rather than
    discovering later. Against a deliberate subset it just lists what was
    excluded.
    """
    arms = list(ARM_COLUMNS) if arms is None else arms
    return [key for key in scores if cell_index(key[1], key[2], key[3], arms) is None]


# Figure margins, in inches. Fixed rather than proportional so that panels keep
# their geometry as datasets and arms are added or removed: everything outside
# the grids has a constant size and only the grids themselves grow.
MARGIN_LEFT_IN = 1.75     # category labels, longest is "10. Output distributions"
MARGIN_RIGHT_IN = 1.15    # colourbar, its ticks and its axis label
MARGIN_TOP_IN = 0.75      # dataset titles, plus the suptitle above them
COLORBAR_WIDTH_IN = 0.13
COLORBAR_PAD_IN = 0.25

# The bottom margin is measured from the arm labels rather than fixed, since it
# depends on both their length and whether they end up horizontal or rotated.
ARM_LABEL_FONTSIZE = 6
ARM_LABEL_PAD_IN = 0.14   # gap between the grid and the labels below it
MARGIN_BOTTOM_MIN_IN = 0.30


def arm_labels(arms):
    """Axis label for each arm, with any part that never varies left out.

    With a single agent every group would repeat the same agent name, and
    likewise for a single prompt, so that part is dropped -- it is already in
    the title or implied by the figure. A single arm keeps the full label, since
    there is nothing else on the axis to say what it is.

    Args:
        arms: (agent, prompt) tuples, from resolve_arms().

    Returns:
        list of label strings, parallel to `arms`.
    """
    n_agents = len({agent for agent, _prompt in arms})
    n_prompts = len({prompt for _agent, prompt in arms})
    labels = []
    for arm in arms:
        agent = AGENT_SHORT[ARM_AGENT[arm]]
        prompt = PROMPT_LABEL[arm[1]]
        if n_agents > 1 and n_prompts > 1:
            labels.append(f'{agent} ({prompt})')
        elif n_agents > 1:
            labels.append(agent)
        elif n_prompts > 1:
            labels.append(prompt)
        else:
            labels.append(f'{agent} ({prompt})')
    return labels


def _text_width_points(text, fontsize):
    """Rendered width of a string in points.

    Measured with TextPath so it works before the figure exists -- the layout
    needs the width to decide the label rotation and the bottom margin, both of
    which feed the figure size.
    """
    extents = TextPath((0, 0), text, prop=FontProperties(size=fontsize)).get_extents()
    return extents.width


def render_lesion_table(scores, datasets=SUPERVISED_DS, *, arms=None,
                        agents=None, prompts=None, suptitle=None,
                        cell_size_in=0.20, dataset_gap_in=0.30):
    """Draw the lesion categories as a grid of coloured squares.

    Rows are the ten categories in verifier order; within each panel the squares
    run left to right over the selected arms, TRIALS_PER_ARM squares per arm.
    Colour is the score on a 0-1 red-to-green scale, grey for nan. Booleans and
    fractions share the scale deliberately: both mean "how much of this check
    passed".

    The axes are placed explicitly in inches rather than by subplots/tight_layout.
    That is what makes the cells actually square and the inter-dataset gap a
    fixed distance: with a shared subplot grid the panels stretch to fill the
    figure, so cell aspect and gap both drift with the number of datasets.

    Args:
        scores: the score dict from lesion_scores().
        datasets: dataset names, one panel each, left to right.
        arms: explicit (agent, prompt) tuples to show. Mutually exclusive with
            agents/prompts. Defaults to all of ARM_COLUMNS.
        agents: show only these agents, e.g. ['claude-code', 'codex'].
        prompts: show only these prompts, e.g. ['full']. Combines with `agents`.
        suptitle: optional figure title.
        cell_size_in: side of one square, in inches. The figure width follows
            from it, so with all six arms (18 squares per panel) something around
            0.14 keeps the figure manageable; a subset of two or three arms can
            afford 0.3 or more.
        dataset_gap_in: horizontal space between adjacent dataset panels, in
            inches. Constant regardless of how many datasets are drawn.

    Returns:
        The matplotlib Figure. Also draws it.

    Side effects: creates a figure; does not write any file.
    """
    arms = resolve_arms(arms, agents=agents, prompts=prompts)
    n_cells = len(arms) * TRIALS_PER_ARM
    n_rows = len(CATEGORIES)

    cmap = _cmap.copy()
    cmap.set_bad(NAN_GREY)

    # Arm labels drive the bottom margin, so they are resolved before any
    # geometry. Horizontal reads better than diagonal, so it is used whenever the
    # longest label fits inside the TRIALS_PER_ARM squares it sits under.
    labels = arm_labels(arms)
    label_width_pt = max(_text_width_points(label, ARM_LABEL_FONTSIZE)
                         for label in labels)
    group_width_pt = TRIALS_PER_ARM * cell_size_in * 72
    labels_horizontal = label_width_pt <= group_width_pt
    if labels_horizontal:
        label_rotation, label_align = 0, 'center'
        label_extent_in = ARM_LABEL_FONTSIZE / 72          # one line of text
    else:
        label_rotation, label_align = 45, 'right'
        # A 45-degree label reaches down by its own width times sin(45).
        label_extent_in = label_width_pt * np.sin(np.pi / 4) / 72
    margin_bottom_in = max(MARGIN_BOTTOM_MIN_IN,
                           label_extent_in + ARM_LABEL_PAD_IN)

    # Panel geometry, then figure size derived from it so each cell lands on
    # exactly cell_size_in by cell_size_in.
    panel_width_in = n_cells * cell_size_in
    panel_height_in = n_rows * cell_size_in
    fig_width_in = (MARGIN_LEFT_IN + MARGIN_RIGHT_IN
                    + len(datasets) * panel_width_in
                    + (len(datasets) - 1) * dataset_gap_in)
    fig_height_in = MARGIN_TOP_IN + margin_bottom_in + panel_height_in

    # Text scaled to the cell so annotations stay inside their square. A cell is
    # cell_size_in * 72 points across; ~40% of that leaves room for three
    # characters (".83") without touching the edges.
    annotation_fontsize = min(8.0, cell_size_in * 72 * 0.40)

    fig = plt.figure(figsize=(fig_width_in, fig_height_in))
    axes = []
    for panel, dataset in enumerate(datasets):
        left_in = MARGIN_LEFT_IN + panel * (panel_width_in + dataset_gap_in)
        ax = fig.add_axes([
            left_in / fig_width_in,
            margin_bottom_in / fig_height_in,
            panel_width_in / fig_width_in,
            panel_height_in / fig_height_in,
        ])
        axes.append(ax)

        grid = np.ma.masked_invalid(category_matrix(scores, dataset, arms))
        # aspect='auto' fills the axes box, and the box was sized above to make
        # that exactly square per cell. 'equal' would re-fit the box and break
        # the fixed gap.
        ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, aspect='auto',
                  interpolation='nearest')

        # Annotate fractions only. A tick or cross reads faster for the booleans,
        # and printing "1.00" in every cell of the first four rows is noise.
        for i, (key, _label, _fn) in enumerate(CATEGORIES):
            for j in range(n_cells):
                value = grid[i, j]
                if value is np.ma.masked:
                    continue
                if value in (0.0, 1.0):   # a check that wholly passed or wholly failed
                    text = '✓' if value >= 0.5 else '✗'
                else:
                    text = f'{value:.2f}'.lstrip('0')
                ax.text(j, i, text, ha='center', va='center',
                        fontsize=annotation_fontsize)

        # Solid separators between arm groups, faint ones between trials.
        for k in range(1, n_cells):
            ax.axvline(k - 0.5, color='white',
                       lw=1.6 if k % TRIALS_PER_ARM == 0 else 0.5)
        for i in range(1, n_rows):
            ax.axhline(i - 0.5, color='white', lw=0.5)

        # One arm header centred over each group of TRIALS_PER_ARM squares.
        # Rotated rather than stacked on two lines: "Terminus-Opus" is far wider
        # than three squares, so a horizontal label would collide with its
        # neighbours no matter how the figure is sized.
        centres = [a * TRIALS_PER_ARM + (TRIALS_PER_ARM - 1) / 2
                   for a in range(len(arms))]
        ax.set_xticks(centres)
        ax.set_xticklabels(
            labels, fontsize=ARM_LABEL_FONTSIZE, rotation=label_rotation,
            ha=label_align, rotation_mode='anchor',
        )
        ax.tick_params(axis='both', length=0)
        ax.set_title(TASK_DISPLAY_NAME.get(dataset, dataset), fontsize=9,
                     fontweight='bold')
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Category labels on the leftmost panel only.
        if panel == 0:
            ax.set_yticks(range(n_rows))
            ax.set_yticklabels(
                [label for _key, label, _fn in CATEGORIES],
                fontsize=7.5,
            )
        else:
            ax.set_yticks([])

    if suptitle:
        fig.suptitle(suptitle, fontsize=11, fontweight='bold',
                     y=1 - 0.12 / fig_height_in, va='top')

    # Colourbar in its own explicitly placed axes, the height of the grids, so it
    # cannot repack the panels the way an `ax=`-attached one would.
    bar_left_in = fig_width_in - MARGIN_RIGHT_IN + COLORBAR_PAD_IN
    bar_ax = fig.add_axes([
        bar_left_in / fig_width_in,
        margin_bottom_in / fig_height_in,
        COLORBAR_WIDTH_IN / fig_width_in,
        panel_height_in / fig_height_in,
    ])
    bar = fig.colorbar(
        mpl.cm.ScalarMappable(norm=mcolors.Normalize(0, 1), cmap=cmap),
        cax=bar_ax,
    )
    bar.set_label('fraction of the check that passed', fontsize=7)
    bar.ax.tick_params(labelsize=6)
    return fig


missing = unplaced_trials(scores)
if missing:
    print(f'! {len(missing)} trials have no column in ARM_COLUMNS and are not drawn:')
    for key in missing:
        print('   ', '/'.join(str(part) for part in key))


# %%
# Arm subsets. Pass `agents`, `prompts`, or explicit `arms` to restrict a figure;
# the selection applies to that call only.

# Maximal vs minimal for the two agents that ran both.
fig = render_lesion_table(
    scores, agents=['claude-code'],
    suptitle='Claude minimal vs maximal prompt',
)
fig.savefig(FIGURES_DIR / 'minimal_vs_full_prompt_claude_table.pdf', bbox_inches='tight')
fig = render_lesion_table(
    scores, agents=['codex'],
    suptitle='Codex minimal vs maximal prompt',
)
fig.savefig(FIGURES_DIR / 'minimal_vs_full_prompt_codex_table.pdf', bbox_inches='tight')
plt.show()

# %%
# Arm subsets. Pass `agents`, `prompts`, or explicit `arms` to restrict a figure;
# the selection applies to that call only.

# Maximal vs minimal for the two agents that ran both.
fig = render_lesion_table(
    scores, agents=['codex','terminus-gpt','terminus-opus'],
    prompts=['maximal'],
    suptitle='Agent vs model -- GPT',
)
fig.savefig(FIGURES_DIR / 'agent_vs_model_gpt_table.pdf', bbox_inches='tight')
fig = render_lesion_table(
    scores, agents=['claude-code','terminus-opus','terminus-gpt'],
    prompts=['maximal'],
    suptitle='Agent vs model -- Opus',
)
fig.savefig(FIGURES_DIR / 'agent_vs_model_opus_table.pdf', bbox_inches='tight')
plt.show()


# %%
# Text form of the figures above, for pasting into notes or a paper.

def lesion_score_table(scores, datasets=SUPERVISED_DS, *, arms=None, agents=None,
                       prompts=None, fmt='markdown', color=True, decimals=2,
                       missing='--', heading=True, glyphs=False, outfile=None):
    """Text form of render_lesion_table: one table per dataset.

    Rows are the categories in verifier order and columns are the selected arms
    crossed with trials, so each cell is one square of the figure. Cell contents
    follow the figure too: a tick or cross where the check wholly passed or
    wholly failed, the fraction otherwise, and `missing` where it could not be
    measured.

    Args:
        scores: the score dict from lesion_scores().
        datasets: dataset names, one table each, in this order.
        arms: explicit (agent, prompt) tuples. Mutually exclusive with
            agents/prompts. Defaults to all of ARM_COLUMNS.
        agents: show only these agents, in this order.
        prompts: show only these prompts, in this order within each agent.
        fmt: 'markdown', 'latex', or 'text'.
        color: shade cells by value on the same ramp the figure uses. 'markdown'
            switches to an HTML table when set, since pipe tables cannot carry a
            cell background.
        decimals: digits after the decimal point for fractional cells.
        missing: what to show where the category could not be measured.
        heading: print the dataset name above each table.
        glyphs: draw a wholly-passed or wholly-failed check as a tick or cross,
            the way the figure does. Off by default here: in a text table a
            number stays aligned with the fractional cells and survives being
            pasted somewhere without the font that renders the glyph.
        outfile: path to write the tables to. Printed to stdout when None.

    Returns:
        All the tables as one string, blank-line separated.

    Side effects: prints to stdout.

    All six arms give 18 columns, which is wide for a document. Pass `agents` or
    `arms` to cut it down the same way you would for the figure.
    """
    arms = resolve_arms(arms, agents=agents, prompts=prompts)
    labels = arm_labels(arms)
    headers = [f'{label} {trial}'
               for label in labels
               for trial in range(1, TRIALS_PER_ARM + 1)]

    def text_of(value):
        if np.isnan(value):
            return missing
        if glyphs and value in (0.0, 1.0):   # wholly passed or wholly failed
            return '✓' if value else '✗'
        return f'{value:.{decimals}f}'

    blocks = []
    for dataset in datasets:
        grid = category_matrix(scores, dataset, arms)
        title = TASK_DISPLAY_NAME.get(dataset, dataset)
        lines = []

        if fmt == 'latex':
            if heading:
                lines.append(f'% {title}')
            if color:
                lines.append('% needs \\usepackage[table]{xcolor}')
            lines.append('\\begin{tabular}{l' + 'c' * len(headers) + '}')
            lines.append('\\toprule')
            # One spanning header per arm rather than repeating its name three
            # times; the trial number is the only thing that varies within it.
            spans = ' & '.join(f'\\multicolumn{{{TRIALS_PER_ARM}}}{{c}}{{{label}}}'
                               for label in labels)
            lines.append(f' & {spans} \\\\')
            lines.append(' & ' + ' & '.join(str(t) for _label in labels
                                            for t in range(1, TRIALS_PER_ARM + 1)) + ' \\\\')
            lines.append('\\midrule')
            for i, (key, label, _fn) in enumerate(CATEGORIES):
                row = []
                for j in range(len(headers)):
                    body = text_of(grid[i, j])
                    if color:
                        body = f'\\cellcolor[HTML]{{{score_hex(grid[i, j])}}} {body}'
                    row.append(body)
                lines.append(f'{label} & ' + ' & '.join(row) + ' \\\\')
            lines.append('\\bottomrule')
            lines.append('\\end{tabular}')

        elif fmt == 'markdown' and color:
            if heading:
                lines.append(f'**{title}**')
                lines.append('')
            lines.append('<table>')
            lines.append('<tr><th></th>'
                         + ''.join(f'<th>{h}</th>' for h in headers) + '</tr>')
            for i, (key, label, _fn) in enumerate(CATEGORIES):
                row = ''.join(
                    f'<td style="background-color:#{score_hex(grid[i, j])};'
                    f'text-align:center">{text_of(grid[i, j])}</td>'
                    for j in range(len(headers)))
                lines.append(f'<tr><td>{label}</td>{row}</tr>')
            lines.append('</table>')

        elif fmt == 'markdown':
            if heading:
                lines.append(f'**{title}**')
                lines.append('')
            lines.append('| ' + ' | '.join([''] + headers) + ' |')
            lines.append('|:---|' + ':---:|' * len(headers))
            for i, (key, label, _fn) in enumerate(CATEGORIES):
                row = [text_of(grid[i, j]) for j in range(len(headers))]
                lines.append('| ' + ' | '.join([label] + row) + ' |')

        else:
            if heading:
                lines.append(title)
            widths = [max(len(headers[j]),
                          max(len(text_of(grid[i, j])) for i in range(len(CATEGORIES))))
                      for j in range(len(headers))]
            label_width = max(len(label) for _key, label, _fn in CATEGORIES) + 2
            lines.append(' ' * label_width
                         + ' '.join(f'{h:>{w}}' for h, w in zip(headers, widths)))
            for i, (key, label, _fn) in enumerate(CATEGORIES):
                row = []
                for j, width in enumerate(widths):
                    padded = f'{text_of(grid[i, j]):>{width}}'
                    row.append(_ansi_cell(padded, score_hex(grid[i, j]))
                               if color else padded)
                lines.append(f'{label:<{label_width}}' + ' '.join(row))

        blocks.append('\n'.join(lines))

    table = '\n\n'.join(blocks)
    if outfile is None:
        print(table)
    else:
        with open(outfile, 'w') as f:
            f.write(table)
    return table


lesion_score_table(scores, agents=['terminus-gpt', 'terminus-opus'],
                   prompts=['maximal'], fmt='markdown', color=False)
lesion_score_table(scores, agents=['terminus-gpt', 'terminus-opus'],
                   prompts=['maximal'], fmt='markdown', color=False,
                   outfile=FIGURES_DIR / 'agent_vs_model_table.md')

# %%
# compute sum across trials per dataset, arm, category

# Collect the per-trial values rather than running a sum: std needs them a second
# time, three trials per arm makes the memory irrelevant, and keeping the raw
# lists means the n behind every statistic stays inspectable.
values_per_category = {}   # (dataset, agent, prompt) -> {category: [value per trial]}
values_overall = {}        # (dataset, agent, prompt) -> [mean over categories, per trial]

for (dataset, agent, prompt, trial), jobres in scores.items():
    arm = (dataset, agent, prompt)
    if arm not in values_per_category:
        values_per_category[arm] = {k: [] for k in CATEGORY_KEYS}
        values_overall[arm] = []

    trial_values = []
    for k in CATEGORY_KEYS:
        x = jobres[k]
        if not np.isnan(x):
            values_per_category[arm][k].append(x)
            trial_values.append(x)
    # One number per trial, so the overall std below is variability between
    # trials rather than between categories.
    if trial_values:
        values_overall[arm].append(float(np.mean(trial_values)))

mean_scores_per_category, std_scores_per_category, n_trials_per_category = {}, {}, {}
mean_scores, std_scores, n_trials = {}, {}, {}

for arm, per_category in values_per_category.items():
    mean_scores_per_category[arm] = {}
    std_scores_per_category[arm] = {}
    n_trials_per_category[arm] = {}
    for cat in CATEGORY_KEYS:
        vals = per_category[cat]
        n_trials_per_category[arm][cat] = len(vals)
        mean_scores_per_category[arm][cat] = float(np.mean(vals)) if vals else np.nan
        # ddof=1: the trials are a sample of what the arm does, not the whole
        # population. Undefined for one trial, so nan rather than a misleading 0.
        std_scores_per_category[arm][cat] = (
            float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan)

    vals = values_overall[arm]
    n_trials[arm] = len(vals)
    mean_scores[arm] = float(np.mean(vals)) if vals else np.nan
    std_scores[arm] = float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan

print(next(iter(mean_scores_per_category.items())))

def score_hex(value):
    """Hex colour for a score, on the same ramp the figures use.

    Args:
        value: score in [0, 1], or nan.

    Returns:
        Six hex digits, no leading '#'. NAN_GREY when the value is missing.
    """
    if value is None or np.isnan(value):
        return NAN_GREY.lstrip('#').upper()
    return mcolors.to_hex(_cmap(float(np.clip(value, 0.0, 1.0))))[1:].upper()


def _ansi_cell(text, hex_colour):
    """Wrap text in a 24-bit ANSI background, black on the pastel ramp."""
    red, green, blue = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    return f'\033[48;2;{red};{green};{blue}m\033[30m{text}\033[0m'


def arm_dataset_table(mean_values, std_values=None, datasets=SUPERVISED_DS,
                      arms=ARM_COLUMNS, fmt='text', color=True, decimals=2,
                      missing='--', outfile=None):
    """Render {(dataset, agent, prompt): value} as an arm x dataset table.

    Args:
        mean_values: {(dataset, agent, prompt): float}, e.g. mean_scores. A nan
            or an absent key both render as `missing`.
        std_values: matching dict of standard deviations, e.g. std_scores. When
            given, each cell reads "mean +/- std". A nan std prints the mean
            alone, which is what a single-trial arm gives.
        datasets: dataset names, one column each, in this order.
        arms: (agent, prompt) tuples, one row each, in this order.
        fmt: 'text' for the terminal, 'markdown', or 'latex'.
        color: shade each cell by its value on the red-yellow-green ramp.
            'text' uses 24-bit ANSI, 'latex' needs \\usepackage[table]{xcolor},
            and 'markdown' switches to an HTML table because pipe tables cannot
            carry a cell background. Set False for a plain pipe table.
        decimals: digits after the decimal point.
        missing: what to show where there is no number.
        outfile: path to write the table to. Printed to stdout when None.

    Returns:
        The rendered table as a string.

    Side effects: prints to stdout.
    """
    row_labels = [f'{AGENT_SHORT[ARM_AGENT[arm]]} ({PROMPT_LABEL[arm[1]]})'
                  for arm in arms]
    headers = [TASK_DISPLAY_NAME.get(dataset, dataset) for dataset in datasets]

    def cell(dataset, arm):
        """(text, hex colour) for one cell."""
        mean = mean_values.get((dataset, arm[0], arm[1]))
        if mean is None or np.isnan(mean):
            return missing, score_hex(np.nan)
        text = f'{mean:.{decimals}f}'
        if std_values is not None:
            std = std_values.get((dataset, arm[0], arm[1]))
            if std is not None and not np.isnan(std):
                pm = {'latex': r' $\pm$ ', 'markdown': ' ± '}.get(fmt, ' ± ')
                text += f'{pm}{std:.{decimals}f}'
        return text, score_hex(mean)

    lines = []
    if fmt == 'latex':
        if color:
            lines.append('% needs \\usepackage[table]{xcolor}')
        lines.append('\\begin{tabular}{l' + 'c' * len(datasets) + '}')
        lines.append('\\toprule')
        lines.append(' & ' + ' & '.join(headers) + ' \\\\')
        lines.append('\\midrule')
        for arm, label in zip(arms, row_labels):
            cells = []
            for dataset in datasets:
                text, hex_colour = cell(dataset, arm)
                cells.append(f'\\cellcolor[HTML]{{{hex_colour}}} {text}' if color else text)
            lines.append(f'{label} & ' + ' & '.join(cells) + ' \\\\')
        lines.append('\\bottomrule')
        lines.append('\\end{tabular}')

    elif fmt == 'markdown' and color:
        # Pipe tables have no way to colour a cell, so emit HTML. Jupyter and most
        # markdown viewers render it; GitHub strips the style attribute and falls
        # back to an uncoloured table, which is still readable.
        lines.append('<table>')
        lines.append('<tr><th></th>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr>')
        for arm, label in zip(arms, row_labels):
            cells = []
            for dataset in datasets:
                text, hex_colour = cell(dataset, arm)
                cells.append(f'<td style="background-color:#{hex_colour};'
                             f'text-align:right">{text}</td>')
            lines.append(f'<tr><td>{label}</td>' + ''.join(cells) + '</tr>')
        lines.append('</table>')

    elif fmt == 'markdown':
        lines.append('| ' + ' | '.join([''] + headers) + ' |')
        lines.append('|' + '---|' * (len(headers) + 1))
        for arm, label in zip(arms, row_labels):
            cells = [cell(dataset, arm)[0] for dataset in datasets]
            lines.append('| ' + ' | '.join([label] + cells) + ' |')

    else:
        # Width from the rendered text, since "0.60 ± 0.05" is far wider than a
        # bare mean and the ANSI escapes must not count toward it.
        widths = [max(len(headers[i]),
                      max(len(cell(datasets[i], arm)[0]) for arm in arms))
                  for i in range(len(datasets))]
        label_width = max(len(label) for label in row_labels) + 2
        lines.append(' ' * label_width
                     + '  '.join(f'{h:>{w}}' for h, w in zip(headers, widths)))
        for arm, label in zip(arms, row_labels):
            cells = []
            for dataset, width in zip(datasets, widths):
                text, hex_colour = cell(dataset, arm)
                padded = f'{text:>{width}}'
                cells.append(_ansi_cell(padded, hex_colour) if color else padded)
            lines.append(f'{label:<{label_width}}' + '  '.join(cells))

    table = '\n'.join(lines)
    if outfile is None:
        print(table)
    else:
        with open(outfile, 'w') as f:
            f.write(table)
    return table

arm_dataset_table(mean_scores, std_scores, fmt='latex',
                  outfile=FIGURES_DIR / 'lesion_scores_table.tex')
arm_dataset_table(mean_scores, std_scores, fmt='markdown', color=False,
                  outfile=FIGURES_DIR / 'lesion_scores_table.md')

# %%
# compute difference in scores between minimal and maximal per category
minvsmax_per_category = {category: {} for category in CATEGORY_KEYS}   # category -> {agent: [minimal - maximal per dataset]}
for (dataset, agent, prompt), jobres in mean_scores_per_category.items():
    if prompt != 'minimal':
        continue
    max_key = (dataset, agent, 'full')
    assert max_key in mean_scores_per_category, f'missing maximal for {dataset}/{agent}'
    for category in CATEGORY_KEYS:
        min_score = jobres[category]
        max_score = mean_scores_per_category[max_key][category]
        diff = min_score - max_score
        minvsmax_per_category[category].setdefault(agent, []).append(diff)
        
mean_minvsmax_per_category = {category: {} for category in CATEGORY_KEYS}   # category -> {agent: mean difference}
std_minvsmax_per_category = {category: {} for category in CATEGORY_KEYS}   # category -> {agent: std difference}
for category, agent_diffs in minvsmax_per_category.items():
    for agent, diffs in agent_diffs.items():
        mean_minvsmax_per_category[category][agent] = float(np.nanmean(diffs)) if diffs else np.nan
        std_minvsmax_per_category[category][agent] = float(np.nanstd(diffs, ddof=1)) if len(diffs) > 1 else np.nan
        
        
# plot a bar plot
# bars start at 0 to emphasize sign of difference
# nagents bars per category, one bar per agent, grouped by category
# plot individual values as points on top of the bars, with jitter to avoid overlap

def plot_prompt_difference(mean_diffs, std_diffs, all_diffs,
                           categories=CATEGORY_KEYS, agents=None,
                           jitter=0.55, seed=0, ax=None, label_wrap=None):
    """Grouped bar plot of the minimal-minus-maximal score difference.

    One group per category, one bar per agent within it, with every individual
    (dataset, trial) difference scattered on top. Bars run from zero rather than
    from the data minimum so the sign reads first: above the line the minimal
    prompt did better, below it the maximal prompt did.

    Args:
        mean_diffs: {category: {agent: mean difference}}, the bar heights.
        std_diffs: {category: {agent: std difference}}, drawn as error bars.
            A nan std (one observation) draws no bar.
        all_diffs: {category: {agent: [difference per (dataset, trial)]}}, the
            scattered points. nan entries are dropped.
        categories: category keys, one group each, left to right.
        agents: agent names, one bar each within a group. Defaults to every
            agent present, in ARM_COLUMNS order.
        jitter: horizontal spread of the points, as a fraction of the bar width.
        seed: fixes the jitter so redrawing gives the same figure.
        ax: axes to draw on. A new figure is created when None.

    Returns:
        The axes drawn on.

    Side effects: creates a figure when ax is None.
    """
    if agents is None:
        present = {agent for per_agent in mean_diffs.values() for agent in per_agent}
        ordered = list(dict.fromkeys(agent for agent, _prompt in ARM_COLUMNS))
        agents = [agent for agent in ordered if agent in present]

    rng = np.random.default_rng(seed)
    bar_width = 0.8 / len(agents)
    group_x = np.arange(len(categories))

    if ax is None:
        fig, ax = plt.subplots(figsize=(1.1 * len(categories) + 2, 4))
    else:
        fig = ax.figure

    colors = plt.get_cmap('tab10').colors
    for i, agent in enumerate(agents):
        # Bars sit side by side, centred on the group tick.
        offset = (i - (len(agents) - 1) / 2) * bar_width
        heights = [mean_diffs[c].get(agent, np.nan) for c in categories]
        errors = [std_diffs[c].get(agent, np.nan) for c in categories]
        ax.bar(group_x + offset, heights, bar_width * 0.9,
               yerr=np.where(np.isnan(errors), 0.0, errors),
               color=colors[i % len(colors)], alpha=0.5,
               error_kw={'lw': 0.8, 'ecolor': '#555'},
               label=AGENT_SHORT.get(agent, agent), zorder=2)

        # Every underlying observation, jittered so ties do not hide each other.
        for j, category in enumerate(categories):
            points = [v for v in all_diffs[category].get(agent, []) if not np.isnan(v)]
            if not points:
                continue
            spread = rng.uniform(-0.5, 0.5, len(points)) * bar_width * jitter
            ax.scatter(group_x[j] + offset + spread, points,
                       s=18, color=colors[i % len(colors)],
                       edgecolor='white', linewidth=0.3, zorder=3)

    # The zero line is the reference the whole figure is read against.
    ax.axhline(0, color='black', lw=0.9, zorder=1)
    
    ax.set_xticks(group_x)
    if label_wrap is not None:
        xticklabels = ['\n'.join(textwrap.wrap(CATEGORY_LABELS[c], width=label_wrap)) for c in categories]
    else:
        xticklabels = [CATEGORY_LABELS[c] for c in categories]
    ax.set_xticklabels(xticklabels, fontsize=12)
    
    ax.set_ylabel('Minimal $-$ maximal prompt score', fontsize=12)

    ax.annotate('Minimal\nbetter', xy=(0, .25), horizontalalignment='center', verticalalignment='center')
    ax.annotate('Maximal\nbetter', xy=(0, -.25), horizontalalignment='center', verticalalignment='center')
    
    ax.tick_params(axis='y', labelsize=10)
    ax.legend(fontsize=12, frameon=False, loc='best')
    ax.margins(x=0.02)
    
    fig.tight_layout()
    return fig, ax

fig, ax = plot_prompt_difference(mean_minvsmax_per_category,
                                 std_minvsmax_per_category,
                                 minvsmax_per_category,
                                 label_wrap=14)
fig.savefig(FIGURES_DIR / 'minimal_vs_full_prompt_difference.pdf', bbox_inches='tight')
plt.show()


# %%
# print total average difference per agent, with one data point per dataset
print('Average minimal-maximal prompt difference, one point per dataset:')

# Difference the trial-averaged scores, never one trial against another: trial 1
# under the minimal prompt is an independent run from trial 1 under the maximal
# one, so matching the indices would pair runs that have nothing to do with each
# other. mean_scores_per_category has already collapsed the trials, and is what
# every other difference in this notebook subtracts.
diffs_by_dataset = {}   # agent -> {dataset: [difference per category]}
for (dataset, agent, prompt), per_category in mean_scores_per_category.items():
    if prompt != 'minimal':
        continue
    maximal = mean_scores_per_category[(dataset, agent, 'full')]
    for category in CATEGORY_KEYS:
        difference = per_category[category] - maximal[category]
        if not np.isnan(difference):
            diffs_by_dataset.setdefault(agent, {}).setdefault(dataset, []).append(difference)

for agent in sorted(diffs_by_dataset):
    # Collapse each dataset to one number first, so every dataset counts once
    # however many categories it contributed.
    per_dataset = [float(np.mean(values))
                   for values in diffs_by_dataset[agent].values() if values]
    mean_diff = float(np.mean(per_dataset)) if per_dataset else np.nan
    std_diff = float(np.std(per_dataset, ddof=1)) if len(per_dataset) > 1 else np.nan
    print(f'  {AGENT_SHORT.get(agent, agent):<16} {mean_diff:+.3f} ± {std_diff:.3f}  '
          f'(n={len(per_dataset)} datasets)')


# %%
# compute difference in scores between terminus-opus and terminus-gpt per-category
def compute_diff_per_category(arm1, arm2):
    
    diff_per_category = {category: [] for category in CATEGORY_KEYS}   # category -> [difference per dataset]
    for dataset in SUPERVISED_DS:
        key1 = (dataset,) + arm1
        key2 = (dataset,) + arm2
        for category in CATEGORY_KEYS:
            score1 = mean_scores_per_category[key1][category]
            score2 = mean_scores_per_category[key2][category]
            diff = score1 - score2
            diff_per_category[category].append(diff)
    return diff_per_category

def compute_mean_diff_per_dataset(arm1, arm2):
    diff_per_dataset = {dataset: [] for dataset in SUPERVISED_DS}   # dataset -> [difference per category]
    for dataset in SUPERVISED_DS:
        key1 = (dataset,) + arm1
        key2 = (dataset,) + arm2
        for category in CATEGORY_KEYS:
            score1 = mean_scores_per_category[key1][category]
            score2 = mean_scores_per_category[key2][category]
            diff = score1 - score2
            diff_per_dataset[dataset].append(diff)
    mean_diff_per_dataset = {dataset: float(np.nanmean(values)) for dataset, values in diff_per_dataset.items()}
    return mean_diff_per_dataset

terminus_opusvsgpt_per_category = compute_diff_per_category(( 'terminus-opus', 'full'), ('terminus-gpt', 'full'))
codex_vs_terminusgpt_per_category = compute_diff_per_category(('codex', 'full'), ('terminus-gpt', 'full'))
claude_vs_terminusopus_per_category = compute_diff_per_category(('claude-code', 'full'), ('terminus-opus', 'full'))
terminus_gptvsopus_per_category = compute_diff_per_category(('terminus-gpt', 'full'), ('terminus-opus', 'full'))

terminus_opusvsgpt_per_dataset = compute_mean_diff_per_dataset(( 'terminus-opus', 'full'), ('terminus-gpt', 'full'))
codex_vs_terminusgpt_per_dataset = compute_mean_diff_per_dataset(('codex', 'full'), ('terminus-gpt', 'full'))
claude_vs_terminusopus_per_dataset = compute_mean_diff_per_dataset(('claude-code', 'full'), ('terminus-opus', 'full'))
terminus_gptvsopus_per_dataset = compute_mean_diff_per_dataset(('terminus-gpt', 'full'), ('terminus-opus', 'full'))

x = list(terminus_opusvsgpt_per_dataset.values())
print('Effect of LLM (terminus-opus - terminus-gpt):',
      f'{np.nanmean(x):+.3f} ± {np.nanstd(x, ddof=1):.3f}  ',
      f'(n={np.count_nonzero(~np.isnan(x))} datasets)')
x = list(codex_vs_terminusgpt_per_dataset.values())
print('Effect of harness (codex -     terminus-gpt):',
      f'{np.nanmean(x):+.3f} ± {np.nanstd(x, ddof=1):.3f}  ',
      f'(n={np.count_nonzero(~np.isnan(x))} datasets)')
x = list(terminus_gptvsopus_per_dataset.values())
print('Effect of LLM (terminus-gpt -    terminus-opus):',
      f'{np.nanmean(x):+.3f} ± {np.nanstd(x, ddof=1):.3f}  ',
      f'(n={np.count_nonzero(~np.isnan(x))} datasets)')
x = list(claude_vs_terminusopus_per_dataset.values())
print('Effect of harness (claude-code - terminus-opus):',
      f'{np.nanmean(x):+.3f} ± {np.nanstd(x, ddof=1):.3f}  ',
      f'(n={np.count_nonzero(~np.isnan(x))} datasets)')

# plot a bar plot
# bars start at 0 to emphasize sign of difference
# nagents bars per category, one bar per agent, grouped by category
# plot individual values as points on top of the bars, with jitter to avoid overlap

def plot_compare_difference(label1, diffs1, label2, diffs2, categories=CATEGORY_KEYS, 
                           jitter=0.55, seed=0, ax=None, label_wrap=None):
    """Grouped bar plot of the minimal-minus-maximal score difference.

    One group per category, one bar per agent within it, with every individual
    (dataset, trial) difference scattered on top. Bars run from zero rather than
    from the data minimum so the sign reads first: above the line the minimal
    prompt did better, below it the maximal prompt did.

    Args:
        diffs1: {category: [difference per dataset]}
        diffs2: {category: [difference per dataset]}
        label1: label for the first set of differences.
        label2: label for the second set of differences.
        categories: category keys, one group each, left to right.
        jitter: horizontal spread of the points, as a fraction of the bar width.
        seed: fixes the jitter so redrawing gives the same figure.
        ax: axes to draw on. A new figure is created when None.

    Returns:
        The axes drawn on.

    Side effects: creates a figure when ax is None.
    """
    mean_diffs1 = {category: float(np.nanmean(values)) for category, values in diffs1.items()}
    mean_diffs2 = {category: float(np.nanmean(values)) for category, values in diffs2.items()}
    std_diffs1 = {category: float(np.nanstd(values, ddof=1)) if len(values) > 1 else np.nan for category, values in diffs1.items()}
    std_diffs2 = {category: float(np.nanstd(values, ddof=1)) if len(values) > 1 else np.nan for category, values in diffs2.items()}
    
    rng = np.random.default_rng(seed)
    bar_width = 0.8 / 2  # two sets of differences
    group_x = np.arange(len(categories))

    if ax is None:
        fig, ax = plt.subplots(figsize=(1.1 * len(categories) + 2, 4))
    else:
        fig = ax.figure

    colors = plt.get_cmap('tab10').colors
    for i, (label, mean_diffs, std_diffs, all_diffs) in enumerate([(label1, mean_diffs1, std_diffs1, diffs1),
                                                                (label2, mean_diffs2, std_diffs2, diffs2)]):
        # Bars sit side by side, centred on the group tick.
        offset = (i - .5) * bar_width
        heights = [mean_diffs[c] for c in categories]
        errors = [std_diffs[c] for c in categories]
        ax.bar(group_x + offset, heights, bar_width * 0.9,
               yerr=np.where(np.isnan(errors), 0.0, errors),
               color=colors[i % len(colors)], alpha=0.5,
               error_kw={'lw': 0.8, 'ecolor': '#555'},
               label=label, zorder=2)

        # Every underlying observation, jittered so ties do not hide each other.
        for j, category in enumerate(categories):
            points = [v for v in all_diffs[category] if not np.isnan(v)]
            if not points:
                continue
            spread = rng.uniform(-0.5, 0.5, len(points)) * bar_width * jitter
            ax.scatter(group_x[j] + offset + spread, points,
                       s=18, color=colors[i % len(colors)],
                       edgecolor='white', linewidth=0.3, zorder=3)

    # The zero line is the reference the whole figure is read against.
    ax.axhline(0, color='black', lw=0.9, zorder=1)
    
    ax.set_xticks(group_x)
    if label_wrap is not None:
        xticklabels = ['\n'.join(textwrap.wrap(CATEGORY_LABELS[c], width=label_wrap)) for c in categories]
    else:
        xticklabels = [CATEGORY_LABELS[c] for c in categories]
    ax.set_xticklabels(xticklabels, fontsize=12)
    
    ax.set_ylabel(f'{label1} $-$ {label2} score', fontsize=12)
    ax.set_ylim(-1,1)

    # ax.annotate(f'{label1}\nbetter', xy=(0, .5), horizontalalignment='center', verticalalignment='center')
    # ax.annotate(f'{label2}\nbetter', xy=(0, -.5), horizontalalignment='center', verticalalignment='center')
    
    ax.tick_params(axis='y', labelsize=10)
    ax.legend(fontsize=12, frameon=False, loc='best')
    ax.margins(x=0.02)
    
    fig.tight_layout()
    return fig, ax

fig, ax = plot_compare_difference('Terminus-Opus - Terminus-GPT',terminus_opusvsgpt_per_category, 
                                  'Codex - Terminus-GPT', codex_vs_terminusgpt_per_category,
                                  label_wrap=14)
fig.savefig(FIGURES_DIR / 'LLM_vs_harness_difference_gpt.pdf', bbox_inches='tight')

fig, ax = plot_compare_difference('Terminus-GPT - Terminus-Opus',terminus_gptvsopus_per_category, 
                                  'Claude - Terminus-Opus', claude_vs_terminusopus_per_category,
                                  label_wrap=14)
fig.savefig(FIGURES_DIR / 'LLM_vs_harness_difference_opus.pdf', bbox_inches='tight')

# %%
# Table form of the per-category difference figures above.

def difference_hex(value, limit=1.0):
    """Hex colour for a signed difference: red below zero, green above.

    Args:
        value: the difference, or nan.
        limit: value mapped to full saturation. Differences beyond it clip.

    Returns:
        Six hex digits, no leading '#'. NAN_GREY when the value is missing.

    The same ramp as the score tables, but re-centred: a difference of zero
    lands on the neutral middle rather than on red, since zero here means "no
    difference" and not "failed everything".
    """
    if value is None or np.isnan(value):
        return NAN_GREY.lstrip('#').upper()
    position = (float(value) + limit) / (2 * limit)
    return mcolors.to_hex(_cmap(float(np.clip(position, 0.0, 1.0))))[1:].upper()


def difference_table(series, categories=CATEGORY_KEYS, fmt='markdown', color=True,
                     decimals=2, limit=None, show_std=True, missing='--', outfile=None):
    """Render per-category differences as a category x series table.

    The table form of the per-category difference bar plot: one row per
    category, one column per comparison, each cell the mean over whatever the
    values are (datasets, or datasets and trials) with its spread.

    Args:
        series: {column label: {category: [values]}}. Each value list is the
            differences behind one bar. nan entries are dropped.
        categories: category keys, one row each, in this order.
        fmt: 'markdown', 'latex', or 'text'.
        color: shade cells by the mean on a red-neutral-green ramp centred at
            zero. 'markdown' switches to an HTML table when set, since pipe
            tables cannot carry a cell background.
        decimals: digits after the decimal point.
        limit: difference mapped to full colour saturation. Defaults to the
            largest absolute mean in the table, so the ramp always spans the
            data rather than a fixed +/-1 that would wash everything out.
        show_std: append "+/- std" to each cell.
        missing: what to show where there is no number.

    Returns:
        The rendered table as a string. Also prints it.

    Side effects: prints to stdout.
    """
    labels = list(series)

    def summarise(label, category):
        """(mean, std) over one cell's values, nan when it has none."""
        values = [v for v in series[label].get(category, []) if not np.isnan(v)]
        if not values:
            return np.nan, np.nan
        return (float(np.mean(values)),
                float(np.std(values, ddof=1)) if len(values) > 1 else np.nan)

    cells = {(label, category): summarise(label, category)
             for label in labels for category in categories}

    if limit is None:
        magnitudes = [abs(mean) for mean, _std in cells.values() if not np.isnan(mean)]
        limit = max(magnitudes) if magnitudes else 1.0
        limit = max(limit, 10.0 ** -decimals)   # never divide by zero

    def text_of(label, category):
        mean, std = cells[(label, category)]
        if np.isnan(mean):
            return missing
        # Explicit sign: the whole point of a difference table is its direction.
        out = f'{mean:+.{decimals}f}'
        if show_std and not np.isnan(std):
            out += (r' $\pm$ ' if fmt == 'latex' else ' ± ') + f'{std:.{decimals}f}'
        return out

    lines = []
    if fmt == 'latex':
        if color:
            lines.append('% needs \\usepackage[table]{xcolor}')
        lines.append('\\begin{tabular}{l' + 'c' * len(labels) + '}')
        lines.append('\\toprule')
        lines.append(' & ' + ' & '.join(labels) + ' \\\\')
        lines.append('\\midrule')
        for category in categories:
            row = []
            for label in labels:
                body = text_of(label, category)
                if color:
                    body = (f'\\cellcolor[HTML]'
                            f'{{{difference_hex(cells[(label, category)][0], limit)}}} {body}')
                row.append(body)
            lines.append(f'{CATEGORY_LABELS[category]} & ' + ' & '.join(row) + ' \\\\')
        lines.append('\\bottomrule')
        lines.append('\\end{tabular}')

    elif fmt == 'markdown' and color:
        lines.append('<table>')
        lines.append('<tr><th></th>' + ''.join(f'<th>{l}</th>' for l in labels) + '</tr>')
        for category in categories:
            row = ''.join(
                f'<td style="background-color:#'
                f'{difference_hex(cells[(label, category)][0], limit)};'
                f'text-align:right">{text_of(label, category)}</td>'
                for label in labels)
            lines.append(f'<tr><td>{CATEGORY_LABELS[category]}</td>{row}</tr>')
        lines.append('</table>')

    elif fmt == 'markdown':
        lines.append('| ' + ' | '.join([''] + labels) + ' |')
        # ---: right-aligns the numeric columns, left-aligns the category names.
        lines.append('|:---|' + '---:|' * len(labels))
        for category in categories:
            row = [text_of(label, category) for label in labels]
            lines.append('| ' + ' | '.join([CATEGORY_LABELS[category]] + row) + ' |')

    else:
        widths = [max(len(label),
                      max(len(text_of(label, c)) for c in categories))
                  for label in labels]
        label_width = max(len(CATEGORY_LABELS[c]) for c in categories) + 2
        lines.append(' ' * label_width
                     + '  '.join(f'{l:>{w}}' for l, w in zip(labels, widths)))
        for category in categories:
            row = []
            for label, width in zip(labels, widths):
                padded = f'{text_of(label, category):>{width}}'
                row.append(_ansi_cell(padded,
                                      difference_hex(cells[(label, category)][0], limit))
                           if color else padded)
            lines.append(f'{CATEGORY_LABELS[category]:<{label_width}}' + '  '.join(row))

    table = '\n'.join(lines)
    if outfile is None:
        print(table)
    else:
        with open(outfile, 'w') as f:
            f.write(table)
    return table


# The same two comparisons the figures show, as markdown.
difference_table({'Terminus-Opus − Terminus-GPT': terminus_opusvsgpt_per_category,
                  'Codex − Terminus-GPT': codex_vs_terminusgpt_per_category},
                 fmt='markdown', color=False)
print()
difference_table({'Terminus-GPT − Terminus-Opus': terminus_gptvsopus_per_category,
                  'Claude − Terminus-Opus': claude_vs_terminusopus_per_category},
                 fmt='markdown', color=False)

# The prompt comparison goes through the same function: compute_diff_per_category
# takes any two arms, and a prompt pair is just an arm pair that happens to share
# an agent. Its per-dataset unit also matches the arm tables above, so the two
# sets of numbers are directly comparable.
print()
difference_table(
    {'Claude: minimal − maximal': compute_diff_per_category(('claude-code', 'minimal'),
                                                            ('claude-code', 'full')),
     'Codex: minimal − maximal':  compute_diff_per_category(('codex', 'minimal'),
                                                            ('codex', 'full'))},
    fmt='markdown', color=False)

# The same three tables again, written out for the paper.
difference_table({'Terminus-Opus − Terminus-GPT': terminus_opusvsgpt_per_category,
                  'Codex − Terminus-GPT': codex_vs_terminusgpt_per_category},
                 fmt='markdown', color=False,
                 outfile=FIGURES_DIR / 'LLM_vs_harness_difference_gpt.md')
difference_table({'Terminus-GPT − Terminus-Opus': terminus_gptvsopus_per_category,
                  'Claude − Terminus-Opus': claude_vs_terminusopus_per_category},
                 fmt='markdown', color=False,
                 outfile=FIGURES_DIR / 'LLM_vs_harness_difference_opus.md')
difference_table(
    {'Claude: minimal − maximal': compute_diff_per_category(('claude-code', 'minimal'),
                                                            ('claude-code', 'full')),
     'Codex: minimal − maximal':  compute_diff_per_category(('codex', 'minimal'),
                                                            ('codex', 'full'))},
    fmt='markdown', color=False,
    outfile=FIGURES_DIR / 'minimal_vs_maximal_difference.md')
