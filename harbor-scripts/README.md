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

**job_config.yaml** — Harbor batch-config for running all tasks across both
agents (claude-code and codex) in one `harbor run -c` invocation. Useful for
the full eval sweep; for one-off task/agent runs use `run_harbor.sh` directly.
```
harbor run -c harbor-scripts/job_config.yaml                         # all tasks, both agents
harbor run -c harbor-scripts/job_config.yaml -t hasnain2024          # one task
harbor run -c harbor-scripts/job_config.yaml --ek use_podman=true    # podman instead of docker
```
Edit the `task_names:` list in the yaml to control which tasks are included.
Auth env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.) must be set in the
shell before running, or use `run_harbor.sh --apikeys` instead.

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
Replaces top-level files (ctrf.json, reward.txt, test-stdout.txt) and judge dirs
that have `llm_judge_eval.json`. **Merges** `metrics.json` (preserves base keys
not in rerun) so that judge-only reruns don't wipe out pytest-produced ratios /
matches / decoder accuracy. Never touches `snapshot/`. Renames the merged rerun
dir with a `_merged` suffix so it won't be picked up again.

**rerun_decoder_accuracy.py** — Recompute `validation_balanced_accuracy` (and
the data-stats metrics that go with it) for trials where those fields are
missing or stale. Loads `verifier/snapshot/converted_data.pkl` and calls
`test_outputs.test_data_stats` + `test_outputs.test_decoder_accuracy` directly
as Python functions, then merges the new keys into the trial's metrics.json
without touching judge keys.

```
# dry-run (lists missing trials, no work):
python rerun_decoder_accuracy.py
python rerun_decoder_accuracy.py --harbor-jobs ~/harbor-tasks/data-format/jobs

# rerun one trial locally (slow + RAM-heavy on big pkls):
python rerun_decoder_accuracy.py --trial allen2p/claude-code/<ts>_trial1 --write

# rerun all missing trials locally:
python rerun_decoder_accuracy.py --all --write

# submit each missing trial as a separate bsub job to gpu_a100 (recommended
# for the bigger pkls — automatically picks slot/GPU count from pkl size):
python rerun_decoder_accuracy.py --all --cluster        # preview bsub commands
python rerun_decoder_accuracy.py --all --cluster --write  # actually submit
```

Cluster mode requires the `test-decoder-data-format` conda env on the cluster
(see `data-format/test-decoder-data-format.yml`); slot count scales with pkl
size via `PKL_RAM_FACTOR * pkl_gb + BASE_OVERHEAD_GB`, and GPU count scales
with slots so `gpu_a100`'s 12-slots/GPU ratio is never exceeded (extra GPUs
are reserved-but-unused). Logs are written to
`/groups/branson/home/bransonk/cluster_logs/rerun_decoder/`.

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
python sync_template.py                     # dry-run
python sync_template.py --apply             # do it
python sync_template.py --update --apply    # update new files
python sync_template.py --diff              # show full diffs
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

**sync_jobs.sh** — Sync job results between `~/harbor-tasks/data-format/jobs/`
(HOME) and the repo's `harbor-jobs/` directory.
```
sync_jobs.sh                                         # dry-run, HOME -> REPO, new files only
sync_jobs.sh --apply                                 # actually sync
sync_jobs.sh --update                                # also include files newer in source
sync_jobs.sh --reverse                               # REPO -> HOME instead
sync_jobs.sh --metrics-only                          # only sync metrics.json files
sync_jobs.sh --reverse --update --metrics-only --apply   # one-liner: pull metrics.json
                                                          # updates from REPO into HOME
```

Itemize-changes prefixes (rsync's `YXcstpoguax` format):
```
  - cd+++++++++ — creating a directory in destination
  - >f+++++++++ — new file being transferred
  - >f.st...... — file exists but size + timestamp differ (real content change)
  - >f..t...... — file exists, content same, but timestamp differs (cosmetic)
  - >f..tp..... — timestamp + permissions differ, content same
```

### Conversion timing (cluster)

End-to-end timing of `convert_data.py` for supervised tasks (`allen2p`,
`lee2025`, `majnik2025`, `sosa2024`) and unsupervised tasks (`hasnain2024`,
`mouseland`, `zhang2025`, `map`). Supervised tasks have a hand-written
reference at `manual/<task>/convert_data.py` that gets timed alongside every
agent trial under `harbor-jobs/<task>/<agent>/<trial>/verifier/snapshot/`;
unsupervised tasks have no manual baseline, so only agent trials are timed.
Runs as bsub jobs on `gpu_a100` with 8 cores; outputs go to
`<repo>/timing_results/`.

Per-task data dirs (mirror the docker-compose mounts):
- `allen2p` → `<repo>/allen2p/data`
- `lee2025` → `<repo>/lee2025/data`
- `majnik2025` → `<repo>/track2p/data`
- `sosa2024` → `<repo>/sosa2024/data`
- `hasnain2024` → `<repo>/hasnain2024/data`
- `mouseland` → `<repo>/mouseland/data`
- `zhang2025` → `<repo>/zhang2025/data`
- `map` → `<repo>/MAP/data`

Workflow:
```
1. Verify prereqs       python submit_conversion_timing.py --check
2. Submit one job       python submit_conversion_timing.py --start 0 --limit 1
3. Submit everything    python submit_conversion_timing.py
4. Watch failures       python scan_conversion_failures.py --only-fail
5. Aggregate to CSV     python summarize_conversion_timing.py
```

Cluster env: `decoder-data-format`. Note that `$HOME` differs between
workstation and cluster, so the env must be installed on the cluster
separately. Known extra deps to install in the cluster env:
`pip install "allensdk@git+https://github.com/AllenInstitute/AllenSDK.git" suite2p`.

**run_one_conversion.py** — Run one `convert_data.py` with `/usr/bin/time -v`
+ `train_decoder.py --verify-only`. Working files (data symlink, output pkls,
copied scripts) live in `/scratch/$USER/`; only `timing.txt`, `stdout.txt`,
`verify.txt` get written to the permanent result dir. Patches `/app/data` to
the local data symlink in the copied script and only passes `--datadir` if
the script's argparse accepts it.
```
python run_one_conversion.py <task> <convert_data.py> <result_dir>
```

**submit_conversion_timing.py** — Discover and submit jobs. Auto-wraps `bsub`
through `ssh login1` when run from the workstation.
```
python submit_conversion_timing.py --check                   # validate, don't submit
python submit_conversion_timing.py --dry-run                 # print commands
python submit_conversion_timing.py                           # supervised tasks (29 jobs)
python submit_conversion_timing.py --unsupervised            # unsupervised tasks (30 jobs)
python submit_conversion_timing.py --all-tasks               # both
python submit_conversion_timing.py --tasks sosa2024          # filter
python submit_conversion_timing.py --manual-only             # skip agent trials
python submit_conversion_timing.py --trials-only             # skip manual
python submit_conversion_timing.py --start N --limit M       # paginate
python submit_conversion_timing.py --minutes 360             # bsub -W
```
Each job gets `-n 8 -q gpu_a100 -gpu "num=1:aff=yes" -W 240`.

**scan_conversion_failures.py** — Walk `timing_results/` and report
per-job status (OK / BAD-CONV / BAD-VRFY / NO-VRFY / PENDING / NO-TIMING),
with conv/verify wall time, output pkl size, and a rough throughput metric
`(n_neurons + n_inputs + n_outputs) × n_trials × T_mean / wall_seconds`
parsed out of `verify.txt`.
```
python scan_conversion_failures.py
python scan_conversion_failures.py --only-fail --show-tail 30
python scan_conversion_failures.py --only-pending
```

**summarize_conversion_timing.py** — Aggregate every `timing.txt` (plus
shape fields scraped from `verify.txt`) into a CSV with throughput and
work-unit columns.
```
python summarize_conversion_timing.py
python summarize_conversion_timing.py --out /path/to/summary.csv
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
