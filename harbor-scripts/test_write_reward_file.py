"""Unit tests for a task's tests/write_reward_file.py.

Lives here rather than in a task's tests/ directory on purpose: anything under
tests/ ships into the grading container (and, for the terminal-bench-science copies of
these tasks, is scanned by that repo's CI checks). Nothing here runs at grading time.

The reward assembly is the one piece of the verifier that previously could only be
exercised by a full trial -- a container, a 46 GB dataset and half an hour -- which is how
three separate defects survived in it: a -1 sentinel that landed in job-level aggregation
as though it were a score, a crash formatting a None, and a category that scored a free
1.0 when its file list was empty. Each is a few lines to check here.

Run:  pytest harbor-scripts/test_write_reward_file.py
      WRITE_REWARD_MODULE=harbor-tasks/sosa2024/tests/write_reward_file.py \
        pytest harbor-scripts/test_write_reward_file.py
"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

# The template copy, which sync_template.py copies into every task's tests/.
DEFAULT_MODULE = (pathlib.Path(__file__).resolve().parent.parent
                  / "template-harbor-task" / "tests" / "write_reward_file.py")


def module_path():
    """Path to the copy under test.

    An environment variable rather than a pytest option, because pytest_addoption is only
    honoured from a conftest.py and this suite is deliberately a single file.

    Returns:
        pathlib.Path to a task's tests/write_reward_file.py.
    """
    return pathlib.Path(os.environ.get("WRITE_REWARD_MODULE", DEFAULT_MODULE))


@pytest.fixture(scope="module")
def mod():
    """Import the task's write_reward_file.py by path.

    Returns:
        the imported module object.
    """
    path = module_path()
    if not path.exists():
        pytest.skip(f"no write_reward_file.py at {path}")
    spec = importlib.util.spec_from_file_location("write_reward_file", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["write_reward_file"] = module
    spec.loader.exec_module(module)
    return module


# --- what counts as a score -------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (0.0, True), (1, True), (-1.0, True),
    (None, False), ("0.5", False), ([], False), ({}, False),
])
def test_scored_accepts_only_numbers(mod, value, expected):
    """A null category must never reach reward.json: pydantic rejects it and fails
    the trial. Strings and containers are equally not scores."""
    assert mod.scored(value) is expected


# --- reward composition -----------------------------------------------------

def test_provisional_write_has_no_process_key(mod):
    """An empty metrics dict is the provisional case, and the ABSENT process key is
    what marks it as such."""
    rewards = mod.build_rewards(1.0, {})
    assert rewards == {"reward": 1.0, "outcome_all": 1.0}


def test_reward_is_mean_of_measured_terms_only(mod):
    """Turning the judges off must rescale the mean, not score them zero."""
    metrics = {"outcome_mean_per_category": 0.5}
    assert mod.build_rewards(1.0, metrics)["reward"] == pytest.approx(0.75)

    with_judges = dict(metrics, llm_judge_claude_reward=0.0, llm_judge_codex_reward=0.0)
    assert mod.build_rewards(1.0, with_judges)["reward"] == pytest.approx(0.5)


def test_one_judge_missing_is_dropped_not_zeroed(mod):
    """An API outage must not be charged to the agent, so process is the mean over the
    judges that answered -- here 0.8, not 0.4."""
    metrics = {"llm_judge_claude_reward": 0.8, "llm_judge_codex_reward": None}
    assert mod.build_rewards(1.0, metrics)["process"] == pytest.approx(0.8)


def test_unmeasured_values_are_omitted_not_sentinelled(mod):
    """The defect that started this: a -1 sentinel is a real float downstream, so it
    lands in job-level means and in plots as though it were a score."""
    rewards = mod.build_rewards(0.0, {"outcome_mean_per_category": None})
    assert "process" not in rewards
    assert "outcome_mean_per_category" not in rewards
    assert -1 not in rewards.values()


def test_null_categories_are_dropped_but_scored_ones_ride_along(mod):
    """Every scored category becomes its own reward key; an unscorable one does not
    appear at all, so harbor never sees a key that only some trials report."""
    metrics = {
        "outcome_mean_per_category": 0.5,
        "outcome_core_files_exist": 1.0,
        "outcome_input_range_matches": None,
        "required_files_missing": [],          # not an outcome_ key
    }
    rewards = mod.build_rewards(1.0, metrics)
    assert rewards["outcome_core_files_exist"] == 1.0
    assert "outcome_input_range_matches" not in rewards
    assert "required_files_missing" not in rewards


def test_zero_is_a_score_not_a_missing_value(mod):
    """0.0 must survive every filter -- the bug class where a falsy check silently
    treats a failed category as unmeasured."""
    metrics = {"outcome_mean_per_category": 0.0, "outcome_core_files_exist": 0.0,
               "llm_judge_claude_reward": 0.0}
    rewards = mod.build_rewards(0.0, metrics)
    assert rewards["reward"] == 0.0
    assert rewards["outcome_mean_per_category"] == 0.0
    assert rewards["outcome_core_files_exist"] == 0.0
    assert rewards["process"] == 0.0


def test_every_reward_value_is_json_safe(mod):
    """harbor types rewards as dict[str, float | int]; anything else fails the trial."""
    metrics = {"outcome_mean_per_category": 0.5, "outcome_x": None, "outcome_y": 1.0,
               "llm_judge_claude_reward": 0.25}
    for value in mod.build_rewards(1.0, metrics).values():
        assert isinstance(value, (int, float)) and value is not None


# --- log line ---------------------------------------------------------------

def test_summary_does_not_crash_on_omitted_values(mod):
    """Formatting a None with %.4f raises TypeError -- it did, once, at the end of a
    successful trial."""
    line = mod.format_summary(mod.build_rewards(0.0, {}), 0)
    assert "not measured" in line and "reward=0.0000" in line


# --- end to end -------------------------------------------------------------

def test_cli_writes_both_files(mod, tmp_path):
    """Run the script as test.sh does, in both modes."""
    script = str(module_path())
    metrics = tmp_path / "metrics.json"
    reward = tmp_path / "reward.json"
    metrics.write_text(json.dumps({"outcome_mean_per_category": 0.5,
                                   "outcome_core_files_exist": 1.0}))

    subprocess.run([sys.executable, script, "--provisional", "1",
                    "--metrics", str(metrics), "--reward", str(reward)], check=True)
    assert json.loads(reward.read_text()) == {"reward": 1.0, "outcome_all": 1.0}

    subprocess.run([sys.executable, script, "1",
                    "--metrics", str(metrics), "--reward", str(reward)], check=True)
    final = json.loads(reward.read_text())
    assert final["reward"] == pytest.approx(0.75)
    assert final["outcome_core_files_exist"] == 1.0


# --- judges-only rerun ------------------------------------------------------

@pytest.mark.parametrize("existing_file, existing_text, expected_outcome", [
    ("reward.json", json.dumps({"reward": 0.5, "outcome_all": 0.0}), 0.0),
    ("reward.txt", "1\n", 1.0),   # trials graded before reward.json existed
])
def test_reuse_outcome_reads_back_the_recorded_pass_fail(
        mod, tmp_path, existing_file, existing_text, expected_outcome):
    """rerun_verifier.sh --judges-only re-scores the judges without rerunning pytest, so the
    pass/fail outcome must come from the reward file already in place, not be invented."""
    script = str(module_path())
    metrics = tmp_path / "metrics.json"
    reward = tmp_path / "reward.json"
    (tmp_path / existing_file).write_text(existing_text)
    metrics.write_text(json.dumps({"outcome_mean_per_category": 0.5,
                                   "llm_judge_claude_reward": 1.0}))

    subprocess.run([sys.executable, script, "--reuse-outcome",
                    "--metrics", str(metrics), "--reward", str(reward)], check=True)
    final = json.loads(reward.read_text())
    assert final["outcome_all"] == expected_outcome
    assert final["process"] == 1.0
    assert final["reward"] == pytest.approx((expected_outcome + 0.5 + 1.0) / 3)


def test_reuse_outcome_refuses_when_there_is_nothing_to_reuse(mod, tmp_path):
    """No earlier reward file means no known outcome; writing one anyway would misreport."""
    result = subprocess.run(
        [sys.executable, str(module_path()), "--reuse-outcome",
         "--metrics", str(tmp_path / "metrics.json"), "--reward", str(tmp_path / "reward.json")],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / "reward.json").exists()
