"""The experiment tree: where a run lives on disk, and what condition it was.

`data-format-experiments/` is organized for *running* trials, not for reading
them back:

    <task>/<agent>/<timestamp>_trial<N>/verifier/
        judge/<judge>/llm_judge_eval.json               supervised
        judge_unsupervised/<judge>/llm_judge_eval.json

Everything awkward about that layout is handled here, once:

* the task folder is sometimes named differently from the dataset (`map`,
  `mouseland`), and the Claude agent is filed as `claude` under half the tasks
  and `claude-code` under the other half;
* the minimal-prompt runs are a *sibling task folder* (`allen2p_minimal/`), not
  a subfolder, so the prompt variant has to be parsed out of the task name;
* `<judge>` is the judge model and has nothing to do with which agent produced
  the trial — `terminus-gpt/.../judge/codex/` is a terminus run graded by the
  codex judge;
* timestamps repeat across trial numbers and do not sort in trial order, so the
  trial number can only come from the `_trial<N>` suffix.

A **condition** is what a run varied: `(agent, prompt)`. Six of them exist —
claude-code and codex ran both prompts, terminus-gpt and terminus-opus only the
full one. The evaluation with human ratings covers exactly the two full-prompt
`EVAL_AGENTS` conditions; everything else is judge-rated only.

This module holds no pandas and reads nothing at import. `judge_import` uses it
to mirror the two evaluated conditions into `eval/`; `analysis.conditions`
uses it to read every one of them directly.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .paths import EXPERIMENTS_DIR

# Experiment task name -> our dataset name. Verified by trial timestamps:
# map/claude/2026-03-22__21-13-57_trial1 is chen2024's trial 1, and
# mouseland/... is zhong2025's. `zhang2025` has its own folder under both names.
# The same two entries are in `eval/utils.py` as DATASET_ALIASES, for the
# outcome half of the evaluation; the two halves share no code by design.
DATASET_ALIAS = {"map": "chen2024", "mouseland": "zhong2025"}

# The Claude agent is filed as `claude` for some tasks and `claude-code` for
# others; everything downstream calls it claude-code.
AGENT_ALIAS = {"claude": "claude-code"}

# The two agents the human evaluation covers, and the only ones `import-judges`
# mirrors into eval/. The tree also holds terminus-gpt and terminus-opus.
EVAL_AGENTS = {"claude-code", "codex"}

MODES = {"supervised": "judge", "unsupervised": "judge_unsupervised"}

# `debug` is a throwaway task; `oracle` runs the reference solution itself, so a
# supervised judge rates it `match` almost by construction and it has only one
# trial. Neither belongs beside a real condition.
SKIP_DIRS = {"debug", "oracle"}

TRIAL_RE = re.compile(r"_trial(\d+)$")

# The evaluation is three trials per condition. zhang2025/codex has a stray
# fourth run; it is reported and skipped rather than changing that condition's n.
MAX_TRIAL = 3

MINIMAL_SUFFIX = "_minimal"
PROMPTS = ("full", "minimal")

JUDGE_FILE = "llm_judge_eval.json"


# ---------- conditions ----------

# Ordered so an agent's two prompt variants sit next to each other — that
# adjacency is the comparison the minimal runs exist to make — and so the two
# conditions the human evaluation covers come first.
CONDITIONS = (
    ("claude-code", "full"), ("claude-code", "minimal"),
    ("codex", "full"), ("codex", "minimal"),
    ("terminus-opus", "full"), ("terminus-gpt", "full"),
)

AGENT_LABEL = {
    "claude-code": "Claude Code",
    "codex": "Codex",
    "terminus-opus": "Terminus/Opus",
    "terminus-gpt": "Terminus/GPT",
}

# "maximal" is what the harbor flag and the metrics figures call the full
# prompt; the metrics field itself says "full". Same convention as
# eval/utils.py's PROMPT_LABEL.
PROMPT_LABEL = {"full": "maximal", "minimal": "minimal"}

# Claude Code orange and Codex blue are fixed across the whole project (see
# plots.AGENT_COLOR); the minimal variant of each gets the lighter shade of the
# same hue so an agent reads as one color and the prompt as its shade.
CONDITION_COLOR = {
    "claude-code/full": "#D55E00", "claude-code/minimal": "#E69F00",
    "codex/full": "#0072B2", "codex/minimal": "#56B4E9",
    "terminus-opus/full": "#009E73", "terminus-gpt/full": "#CC79A7",
}


def condition_key(agent: str, prompt: str) -> str:
    """The condition's name in a frame: `"claude-code/full"`."""
    return f"{agent}/{prompt}"


CONDITION_ORDER = tuple(condition_key(a, p) for a, p in CONDITIONS)

CONDITION_LABEL = {condition_key(a, p): f"{AGENT_LABEL.get(a, a)} ({PROMPT_LABEL[p]})"
                   for a, p in CONDITIONS}


def split_task(task: str) -> tuple[str, str]:
    """Task folder name -> (our dataset name, prompt variant)."""
    if task.endswith(MINIMAL_SUFFIX):
        base, prompt = task[:-len(MINIMAL_SUFFIX)], "minimal"
    else:
        base, prompt = task, "full"
    return DATASET_ALIAS.get(base, base), prompt


# ---------- what is on disk ----------

@dataclass(frozen=True)
class JudgeRun:
    """One judge's verdicts on one trial: the smallest unit the tree holds."""

    dataset: str
    prompt: str
    agent: str
    trial: int
    mode: str
    judge: str
    path: Path          # .../verifier/judge[_unsupervised]/<judge>/

    @property
    def json(self) -> Path:
        return self.path / JUDGE_FILE

    @property
    def condition(self) -> str:
        return condition_key(self.agent, self.prompt)

    @property
    def trial_dir(self) -> Path:
        return self.path.parents[2]


def discover_runs(*, datasets: list[str] | None = None,
                  agents: set[str] | None = None,
                  prompts: tuple[str, ...] = PROMPTS,
                  modes: tuple[str, ...] = ("supervised",),
                  max_trial: int | None = MAX_TRIAL,
                  root: Path = EXPERIMENTS_DIR) -> tuple[list[JudgeRun], dict]:
    """Walk the experiment tree -> (runs, skipped).

    Every filter is an argument, because the two callers want different slices
    of the same walk: `import-judges` mirrors the full-prompt `EVAL_AGENTS`
    runs, while the condition analysis wants all of them. `None` = no filter.

    `skipped` reports what was deliberately left out — `{"agents": [...],
    "trials": [...]}` — so a caller can say so rather than quietly dropping
    runs.

    Order is `sorted()` at every level, so the result is deterministic and
    matches the order the tree has always been walked in.
    """
    if not root.is_dir():
        sys.exit(f"Experiment tree not found: {root}")

    runs: list[JudgeRun] = []
    skipped_agents: set[str] = set()
    skipped_trials: list[str] = []

    for task_dir in sorted(root.iterdir()):
        if not task_dir.is_dir():
            continue
        task = task_dir.name
        # `.git` and friends are not tasks; without this their internals get
        # walked as if they were agent folders.
        if task.startswith(".") or task in SKIP_DIRS:
            continue
        dataset, prompt = split_task(task)
        if datasets is not None and dataset not in datasets:
            continue
        if prompt not in prompts:
            continue

        for agent_dir in sorted(task_dir.iterdir()):
            if (not agent_dir.is_dir() or agent_dir.name.startswith(".")
                    or agent_dir.name in SKIP_DIRS):
                continue
            agent = AGENT_ALIAS.get(agent_dir.name, agent_dir.name)
            if agents is not None and agent not in agents:
                skipped_agents.add(agent)
                continue

            for trial_dir in sorted(agent_dir.iterdir()):
                m = TRIAL_RE.search(trial_dir.name)
                if not trial_dir.is_dir() or not m or "badtrial" in trial_dir.name:
                    continue
                trial = int(m.group(1))
                if max_trial is not None and trial > max_trial:
                    skipped_trials.append(f"{dataset}/{agent}/trial{trial}")
                    continue
                for mode in modes:
                    judge_root = trial_dir / "verifier" / MODES[mode]
                    if not judge_root.is_dir():
                        continue
                    for judge_dir in sorted(judge_root.iterdir()):
                        if not judge_dir.is_dir():
                            continue
                        if not (judge_dir / JUDGE_FILE).exists():
                            continue
                        runs.append(JudgeRun(
                            dataset=dataset, prompt=prompt, agent=agent,
                            trial=trial, mode=mode, judge=judge_dir.name,
                            path=judge_dir))

    return runs, {"agents": sorted(skipped_agents),
                  "trials": sorted(set(skipped_trials))}


def skip_notes(skipped: dict, max_trial: int | None = MAX_TRIAL) -> list[str]:
    """`skipped` -> the lines a CLI should print about what it left out."""
    notes = []
    if skipped.get("agents"):
        notes.append("agents not in the evaluation: "
                     + ", ".join(skipped["agents"]))
    if skipped.get("trials"):
        notes.append(f"{len(skipped['trials'])} run(s) beyond trial {max_trial} "
                     f"({', '.join(skipped['trials'])})")
    return notes
