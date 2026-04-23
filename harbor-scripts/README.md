# Harbor Scripts

Scripts for running, verifying, and analyzing benchmark trials.

## Workflows

### Running and verifying jobs

A typical sequence for running and verifying trials:

```
1. Run trials               run_harbor.sh --agent claude --task sosa2024 --ntrials 3
2. Check health             python check_trial_health.py
3. Fix failed judges        rerun_verifier.sh --codex-judge-only <trial_dir>
4. OR rerun full verifier   rerun_verifier.sh <trial_dir>
5. Merge rerun results      merge_rerun_verifier.sh --jobdir <trial_dir>
6. Run unsupervised         run_unsupervised_judges.sh <trial_dir> [<trial_dir> ...]
   judges (supervised tasks only)
7. Check health again       python check_trial_health.py
8. Sync to repo backup      sync_jobs.sh --apply
```
To do steps for many trials, there are one-off scripts like 
`rerun_supervised_verifiers_20260406.sh` and `merge_supervised_verifiers_20260406.sh`
which rerun verifiers for supervised jobs only

### Changing `template-harbor-task/tests/test_outputs.py`

```
1. Propagate changes to all tasks               python sync_template.py --apply
2. Manually propagate to debug task         
3. Rerun verifier for jobs that are affected    rerun_verifier.sh <trial_dir>
4. Check health                                 python check_trial_health.py
```

### Creating a new task

See `../setup_harbor_task.md`

## Scripts

### Running trials

**run_harbor.sh** — Run harbor trials for a task/agent combination.
```
run_harbor.sh --agent claude --task sosa2024 --ntrials 3
run_harbor.sh --agent codex --task lee2025 --ntrials 3
run_harbor.sh --agent oracle --task sosa2024
```
Results go to `~/harbor-tasks/data-format/jobs/raw/` then get reorganized into
`jobs/<task>/<agent>/<timestamp>_trial<N>/`.

Options: `--nconcurrent N`, `--gpuids LIST`, `--podman`, `--apikeys`, `--config FILE`.

### Checking health

**check_trial_health.py** — Check agent and verifier health across all trials.
```
python check_trial_health.py                # full output
python check_trial_health.py --summary-only # summary table only
python check_trial_health.py --verbose      # show error details
python check_trial_health.py --include-oracle
```
Checks: agent produced `converted_data.pkl`, metrics.json is valid, both judges
produced `llm_judge_eval.json`, unsupervised judges ran (for supervised tasks).
Shows unmerged verifier reruns.

**check_status.sh** — Quick status overview of all trials.
```
check_status.sh                  # all tasks
check_status.sh sosa2024 claude  # filter by task/agent
```

### Re-running verification

**rerun_verifier.sh** — Rerun the full verifier (tests + judges) or just specific judges.
```
rerun_verifier.sh <trial_dir>                        # full rerun -> verifier_rerun_<timestamp>/
rerun_verifier.sh --claude-judge-only <trial_dir>    # rerun claude judge only
rerun_verifier.sh --codex-judge-only <trial_dir>     # rerun codex judge only
rerun_verifier.sh --judges-only <trial_dir>          # rerun both judges
rerun_verifier.sh --verifier-dir <dir> <trial_dir>   # target a specific verifier dir
```
In judge-only mode, automatically targets the newest unmerged `verifier_rerun_*/`
directory if one exists, otherwise targets `verifier/`.

**merge_rerun_verifier.sh** — Merge a verifier rerun into the original verifier directory.
```
merge_rerun_verifier.sh --jobdir <trial_dir>                    # merge newest rerun
merge_rerun_verifier.sh --jobdir <trial_dir> --newdir <dir>     # merge specific rerun
merge_rerun_verifier.sh --jobdir <trial_dir> --dry-run          # preview
```
Replaces top-level files (metrics.json, ctrf.json, reward.txt, test-stdout.txt) and
judge dirs that have `llm_judge_eval.json`. Never touches `snapshot/`. Renames the
merged rerun dir with a `_merged` suffix so it won't be picked up again.

### Unsupervised judges

**run_unsupervised_judges.sh** — Run judges with unsupervised instructions (no reference solution).
```
run_unsupervised_judges.sh <trial_dir> [<trial_dir> ...]
run_unsupervised_judges.sh --claude-judge-only <trial_dir>
run_unsupervised_judges.sh --codex-judge-only <trial_dir>
run_unsupervised_judges.sh --dry-run <trial_dir>
```
Only for supervised tasks (those with `judge_instructions_unsupervised.md`). Writes
results under `llm_judge_{model}_unsupervised_*` keys in metrics.json and judge output
to `judge_unsupervised/`. Does not modify existing supervised judge results.

### Task setup

**sync_template.py** — Sync shared files from `template-harbor-task/` to all task directories.
```
python sync_template.py          # dry-run
python sync_template.py --apply  # copy files
python sync_template.py --diff   # show full diffs
```

Syncs the following files:
  - `task.toml`
  - `tests/compute_reward.py`
  - `tests/decoder.py`
  - `tests/test_outputs.py`
  - `tests/test.sh`
  - `tests/train_decoder.py`
  - `environment/decoder.py`
  - `environment/train_decoder.py`
  - `environment/Dockerfile`

After updating any of these files, use this to propagate changes. 

If `Dockerfile` is changed: Delete old docker images (`docker image rm hb__<task>-reverify`)
Note that some tasks have specialized files and will require manual melding after a change: 
`Dockerfile`: `allen2p`
`task.toml`: `mouseland`
`tests/test_outputs.py`: `debug`
`tests/train_decoder.py`: `debug`
`environment/train_decoder.py`: `debug`


**generate_reference_stats.sh** — Run the oracle solution to generate `reference_stats_full.json`.
```
generate_reference_stats.sh              # all tasks
generate_reference_stats.sh sosa2024     # one task
```

**generate_unsupervised_task.py** — Generate an unsupervised version of a task
**OBSOLETE, do not use**
(removes reference files from tests/).
```
python generate_unsupervised_task.py sosa2024
```

**generate_canary_string.py** — Generate a random canary string for embedding in reference solutions.

### Syncing

**sync_jobs.sh** — Sync job results to the repo's `harbor-jobs/` directory (backup).
```
sync_jobs.sh            # dry-run
sync_jobs.sh --apply    # sync
```

Prefixes:
```
  - cd+++++++++ — creating a directory (new directory that doesn't exist in destination)
  - >f+++++++++ — transferring a file (new file being sent to destination)
  - >f.st...... — File exists but size and timestamp differ. 
  - >f..t...... — File exists, same size, but timestamp differs.
```

### Utilities

**gpu_ids.py** — Utility for GPU ID selection from Kai for use with podman on the cluster. We decided not to use harbor on the cluster because we weren't properly able to control access to resources. 

**install_codex.sh** — Install the Codex CLI, used on the cluster where we didn't have npm

**test_podman.sh** — Test podman container setup.

## Directory structure

```
~/harbor-tasks/data-format/jobs/          # primary job results
  <task>/<agent>/<timestamp>_trial<N>/
    config.json
    result.json
    agent/                                # agent logs, trajectory
    verifier/                             # verification results
      snapshot/                           # agent output files
      ctrf.json                           # test report
      metrics.json                        # all metrics + judge scores
      reward.txt                          # 0 or 1
      test-stdout.txt                     # pytest output
      judge/claude/                       # supervised claude judge
      judge/codex/                        # supervised codex judge
      judge_unsupervised/claude/          # unsupervised claude judge
      judge_unsupervised/codex/           # unsupervised codex judge
    verifier_rerun_<timestamp>/           # rerun results (pre-merge)
    verifier_rerun_<timestamp>_merged/    # merged reruns (archived)
```
