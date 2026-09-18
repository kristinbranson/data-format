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

### Changing a prompt, reference solution or other per-task file

A task exists as `<task>`, `<task>_minimal` and (for five tasks) `<task>_datalimit`, and
also as a terminal-bench-science task. After editing the maximal task:

```
1. Minimal prompt (if the prompt changed)       python generate_minimal_prompt.py <task> --version 2 --force
2. Minimal task's derived files                 python generate_minimal_task.py <task> --version 2 --update
   (copy other changed files, e.g. the reference solution, to <task>_minimal by hand)
3. Datalimit task                     python generate_datalimit_task.py <task>
4. Check the variants agree                     python check_task_variants.py <task>
5. Compare with terminal-bench-science          python check_forks_match.py <task> [--worktree]
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

Options: `--nconcurrent N`, `--gpuids LIST`, `--podman`, `--apikeys`, `--versions FILE`, `--jobs-dir DIR`.

**submit_harbor_cluster.py** — Submit benchmark tasks to the Janelia cluster (by default the
maximal and minimal tasks; `--maximal`, `--minimal` or `--datalimit` for one variant),
one bsub job per (task, agent, trial). Each job takes a **whole `gpu_l4_large`
node**: 64 slots + 1 GPU is an entire `l4_larges` host (64 physical cores,
1006 GB, one L4). That is deliberate — podman here does not enforce
`--cpus`/`--memory` (measured: `/sys/fs/cgroup/memory.max` reads `max` and
`nproc` reports all 128 logical cores), so owning the node is the only way to
bound a trial. Do **not** use `gpu_l4_16`: those `emeraldrapids` hosts have 8
GPUs, so 16 slots is ⅛ of a node shared with co-tenants.
```
python submit_harbor_cluster.py --check          # validate, submit nothing
python submit_harbor_cluster.py --dry-run        # print the bsub commands
python submit_harbor_cluster.py                  # 8 tasks x 2 agents x 3 trials = 48 jobs
python submit_harbor_cluster.py --tasks sosa2024_minimal --agents claude --trials 1
python submit_harbor_cluster.py --start 0 --limit 1
ssh login1 'bash -l -c "bjobs -J \"hb_*\""'      # track
```
Logs go to `/groups/branson/home/bransonk/cluster_logs/harbor/`, results to
`/groups/branson/home/bransonk/harbor-cluster-jobs/<jobname>/` — both on
`/groups` because `$HOME` differs between workstation and cluster. Each job gets
its own `--jobs-dir`, which is required: `run_harbor.sh`'s reorganization step
picks the newest timestamped run dir, so jobs sharing one would steal each
other's trials. `-W 24:00` covers observed durations (1.25 h median, 6.06 h max)
plus the two LLM judges, which add roughly an hour on top of the trial itself.
Roughly 85 GPU-hours ≈ $282 for a full sweep.

Podman on a batch node needs a **per-job runroot** (a shared one goes stale
across reboots — "boot ID differs") and benefits from a **node-local persistent
graphroot** (`/scratch/$USER/podman-storage`), so the second job on a node skips
the ~7 minute image build. `run_harbor.sh --podman` sets both when `LSB_JOBID`
is present. `gpu_ids.py` is *not* needed on these single-GPU nodes.

**config_&lt;YYYYMMDD&gt;.json** — Pinned harness (CLI) and model versions, the single
source of truth for what a run actually executes. `run_harbor.sh` reads it and
passes the model via `-m` and the harness via `--ak version=`; the judge paths
read the same values from `tests/versions.json`, which is generated from it and
shipped into the container.
```
run_harbor.sh --agent claude --task sosa2024            # newest config_*.json
run_harbor.sh --agent claude --task sosa2024 --versions harbor-scripts/config_20260728.json
```
Dated rather than mutable, so the config that produced a set of results stays
readable alongside them; start a new `config_<YYYYMMDD>.json` when bumping.
`run_harbor.sh` echoes which file it used, and `submit_harbor_cluster.py`
resolves it once per sweep so a new config landing mid-submission cannot split
the run across two configurations.

Note that jobs before 20260728 were run without pinned harnesses, and have a variety of
values here. This matters most in the minimal prompt versions, since there was a several
month gap.

One entry per tool, not separate agent/judge entries: they share
`/root/.local/bin` inside the trial container, so whichever installs last wins.
A single field makes "agent and judge run the same CLI" true by construction.

**apply_versions.py** — Propagate a config to the two places that cannot read
one at runtime: each task's `environment/Dockerfile` (installs the judge CLIs at
image build time) and each task's `tests/versions.json` (ships into the verifier
container). 36 files; never edit them by hand.
```
python apply_versions.py                    # apply the newest config_*.json
python apply_versions.py --check            # report drift, exit 1 if any
python apply_versions.py --versions harbor-scripts/config_20260728.json
```
To bump a version: copy the config to `config_<newdate>.json`, edit the
versions, run `apply_versions.py`.

A top-level `"run_llm_judge": false` in the config makes every task's `tests/test.sh` skip
both LLM judges (faster, no API keys); the trial's reward is then the mean of `outcome_all`
and `outcome_mean_per_category`. It defaults to true.

You do not normally invoke it: `run_harbor.sh` applies the config itself when
run locally, and only *verifies* under LSF (the jobs of a sweep share one
checkout, so concurrent writers would race); `submit_harbor_cluster.py` applies
once before submitting, because task Dockerfiles are baked into images built
inside the jobs. Both abort on failure rather than warning — the failure mode is
a run where agents use the new harness and judges the old one. Covers `allen2p`/`allen2p_minimal`, which
`sync_template.py` excludes. Only layers below the CLI installs rebuild
(~1-2 min); the pip layers above them stay cached.

**check_data_mounts.py** — Verify every task's `/app/data` bind source exists and
holds a real file, *before* running anything.
```
python check_data_mounts.py                 # all tasks
python check_data_mounts.py --task map
```
The tasks' own `test_data_dir_accessible` asserts the same thing, but it runs in
the verifier — after the agent has spent its entire timeout. On 2026-07-27, 47
trials ran to completion against an empty `/app/data`, because compose resolved
the then-relative mount inside the harbor checkout and the container runtime
silently *created* the missing source. This is that check moved to the host and
to before the run, where it costs seconds instead of a sweep. It reads the mount
out of each `docker-compose.yaml` rather than hardcoding a path.

**collect_cluster_results.py** — Regroup finished cluster trials into the analysis
tree. Cluster sweeps produce one bsub job per trial, so every trial is named
`trial1` and an arm's repeats are scattered across N job directories:
`harbor-cluster-jobs/hb_<task>_<arm>_t<N>/<task>/<agent>/<timestamp>_trial1/`.
```
python collect_cluster_results.py              # dry run: report, move nothing
python collect_cluster_results.py --apply
python collect_cluster_results.py --tasks map_minimal --apply
python collect_cluster_results.py --include-failed --apply
```
Moves rather than copies (same filesystem, so a rename regardless of trial size),
and takes only trials with a `verifier/metrics.json` — a trial without one did not
produce a result, and filing wreckage where results are expected is worse than
leaving it. `run_harbor.sh` does this shape of move at the end of its own run, but
only within one job; this works across jobs and can be re-run, which also makes it
the tool for rescuing trials whose job died before reorganising.

It doubles as the status report for that tree: the dry run prints how many trials
are ready, still running, and finished without metrics.

### Checking health

**check_trial_health.py** — Which artifacts each task x arm actually has. The main
"what is finished?" report.
```
python check_trial_health.py                # per-trial rows, then the summary
python check_trial_health.py --summary-only # summary table only
python check_trial_health.py --verbose      # show error details
python check_trial_health.py --include-oracle
python check_trial_health.py --job-dirs ~/harbor-tasks/data-format/jobs
```
Per trial it checks `verifier/snapshot/convert_data.py`, `converted_data.pkl`, that
`metrics.json` parses, and that both judges wrote `llm_judge_eval.json` with no
error recorded — plus the separate unsupervised judge pass and any unmerged
verifier reruns. The summary aggregates those into one row per (task, arm).

`metrics` and `judges` are separate columns because they fail independently: an API
quota kills the judges while pytest is fine. A missing snapshot *directory* is
reported distinctly from a missing file inside it — with no snapshot there is
nothing to re-read, so no verifier rerun or metrics recompute can recover the
trial, and it has to be run again.

Scans `harbor-jobs` and `harbor-jobs-new` by default; arms are derived from what is
found rather than hardcoded. Not `harbor-cluster-jobs`, whose raw layout is one
level deeper — use `collect_cluster_results.py` for that tree.

**show_reward.py** — Print a trial's reward from its verifier directory: `reward.json`
(current tasks: `reward`, `outcome_all`, `outcome_mean_per_category`, `process`) or, for older
trials, `reward.txt`. Used by `check_status.sh`, `run_harbor.sh`, `rerun_verifier.sh` and
`merge_rerun_verifier.sh`.
```
python show_reward.py <trial>/verifier            # one-line summary
python show_reward.py --value <trial>/verifier    # the reward number only
```

**check_status.sh** — Quick status overview of all trials.
```
check_status.sh                  # all tasks
check_status.sh sosa2024 claude  # filter by task/agent
```
Both scan `<jobs_root>/<task>/<agent>/<timestamp>_trial<N>/`; cluster results have
an extra per-job level (`harbor-cluster-jobs/hb_<task>_<agent>_t<N>/...`).

**rebuild_trajectories.py** — Rebuild `agent/trajectory.json` for trials where
harbor's converter failed. Harbor converts the agent's raw session files to ATIF
after the run, and that conversion can fail while the trial itself succeeds — the
failure is printed, never raised — leaving a complete, scored trial with no
trajectory. This re-runs the converter over the session files preserved in the
trial output, so nothing has to be re-run.
```
python rebuild_trajectories.py --dry-run --jobs-root <dir>   # report only
python rebuild_trajectories.py --jobs-root <dir>
python rebuild_trajectories.py --trial <trial_dir>
```
Recovers 6 of the 2026-07-27 sweep's 10 missing trajectories; the rest are dead
runs with no session files. Oracle trials never have one (no LLM session).

> **Depends on an out-of-repo patch.** The conversion bug is in the vendored
> harbor checkout at `codepacks/harbor-kai` (`078c4db`), not here: skipped events
> still consumed a `step_id`, leaving a gap that ATIF's "sequential from 1"
> validator rejected, so an otherwise-fine trajectory was discarded. Fixed in
> `agents/installed/claude_code.py` and `codex.py` by numbering from the output
> rather than the input. Re-cloning or updating that checkout loses the fix and
> trajectories start being silently dropped again. It only triggers when the
> agent harness drifts far enough to emit events harbor cannot map, which is what
> pinning the harness now prevents.

### Re-running verification

**rerun_verifier.sh** — Rerun the full verifier (tests + judges) or just specific judges.
```
rerun_verifier.sh <trial_dir>                        # full rerun -> verifier_rerun_<timestamp>/
rerun_verifier.sh --claude-judge-only <trial_dir>    # rerun claude judge only
rerun_verifier.sh --codex-judge-only <trial_dir>     # rerun codex judge only
rerun_verifier.sh --judges-only <trial_dir>          # rerun both judges
rerun_verifier.sh --verifier-dir <dir> <trial_dir>   # target a specific verifier dir
rerun_verifier.sh --podman <trial_dir>               # required for trials on /groups
rerun_verifier.sh --decoder-stats --task <task> <oracle_trial_dir>   # 20-split decoder statistics
```
`--decoder-stats` does not grade: it runs `compute_decoder_stats.py` on an oracle trial's
snapshot (`converted_data.pkl`, `stats_full.json`) inside the task's image and writes
`<trial>/decoder_stats_<time>/reference_stats_full.json`, which becomes the task's
`tests/reference_stats_full.json`. `--n-replicates N` changes the number of splits (default 20);
`--task` names the task when the trial path does not (oracle runs from
`generate_reference_stats.sh`).

Judge-only reruns also rewrite `reward.json` (`write_reward_file.py --reuse-outcome`), keeping the
pytest outcome already recorded.
In judge-only mode, automatically targets the newest unmerged `verifier_rerun_*/`
directory if one exists, otherwise targets `verifier/`. **Judge-only mode writes
into `verifier/` in place** — it does not stage a rerun directory, so the
previous judge output is replaced and no merge step is needed. Copy `verifier/`
first if you want a before/after comparison.

`--podman` is required for trials stored under `/groups` or `/nrs`: docker runs
the container as real root and those NFS mounts are root-squashed, so every
write the verifier makes is denied. Rootless podman maps container-root to your
UID, which is how the cluster jobs write there. Judge-only runs drop the GPU
request, since only the decoder training in `test_outputs.py` needs one and a
GPU request makes the run depend on the host CDI spec being parseable.

The image is tagged with the pinned harness versions
(`hb__<task>-reverify:claude-<ver>_codex-<ver>`) and the config is applied
before building, so a version bump rebuilds automatically instead of silently
reusing an image built with the old CLI. Deleting the image by hand is only
needed after changing `test_outputs.py` or other test code, which is not in the
tag.

**merge_rerun_verifier.sh** — Merge a verifier rerun into the original verifier directory.
```
merge_rerun_verifier.sh --jobdir <trial_dir>                    # merge newest rerun
merge_rerun_verifier.sh --jobdir <trial_dir> --newdir <dir>     # merge specific rerun
merge_rerun_verifier.sh --jobdir <trial_dir> --dry-run          # preview
```
Replaces top-level files (ctrf.json, reward.json or reward.txt, test-stdout.txt) and judge dirs
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

**rerun_metrics.py** — Rerun selected `test_outputs.py` tests against a trial's
snapshot and merge new metrics into `metrics.json`. **Prefer this** over the three
single-purpose scripts below, which it consolidates: it loads each snapshot pickle
once even when several tests are requested, which on multi-GB pickles is the whole
cost.
```
conda activate test-decoder-data-format     # NOT decoder-data-format, see below
python rerun_metrics.py                                   # list candidates
python rerun_metrics.py --trial <trial> --write --force
python rerun_metrics.py --all --write --force             # cheap suite
python rerun_metrics.py --all --decoder --write --force   # + decoder training (slow)
python rerun_metrics.py --all --task map --reference-only --write --force
```
By default it runs the cheap tests (file/format/contamination checks and
`test_data_stats`, which self-skips on unsupervised tasks). `--decoder` adds
`test_decoder_accuracy`, which trains and takes minutes to hours per trial.

`--reference-only` is the mode for "the reference solution changed, refresh what
depends on it". It runs `test_data_stats` and then *derives*
`validation_balanced_accuracy_{reference,ratio}` from the agent accuracy already in
`metrics.json` rather than retraining — legitimate because everything
`test_decoder_accuracy` does after training depends only on that stored accuracy,
the reference's accuracy, and the output matching. The pickle is still loaded,
because `test_data_stats` needs the submitted `output_range`/`output_fractions` for
the Hungarian matching and those are not recorded in `metrics.json`.

Merging ADDS missing keys only; `--force` also overwrites existing keys that
differ, which is what you want after a reference or matcher change. Tests are
invoked by fresh-importing the task's own `tests/test_outputs.py`, so changes there
flow through automatically — which is also why this needs an env with
`sentence_transformers` (`test-decoder-data-format`), unlike most scripts here.

**rerun_data_stats.py**, **rerun_file_format_checks.py**, **rerun_decoder_accuracy.py**
— the single-test predecessors of `rerun_metrics.py`, each rerunning one slice
(data stats / the cheap file+format+contamination checks / decoder accuracy). Still
useful when you want exactly one of those and nothing else; otherwise reach for
`rerun_metrics.py`.

**submit_rerun_verifier.sh** — Submit verifier reruns to the cluster, one bsub job
per trial.
```
./submit_rerun_verifier.sh harbor-jobs-new/mouseland/terminus-gpt/*_trial1
./submit_rerun_verifier.sh --queue gpu_t4 --judges-only <trial_dir>
./submit_rerun_verifier.sh --dry-run <trial_dir>
```
Use it when a rerun will not fit on the workstation: the verifier holds the whole
converted dataset in memory twice over (`test_verify_data_format` and
`test_data_stats` share the module-scoped full fixture while the sample fixture
stays resident), and mouseland/terminus-gpt's 348 GB pickle OOM-killed pytest on a
503 GB host. A `gpu_l4_large` node has 960 GB.

Always passes `--apikeys`: the OAuth route reads `$HOME/.claude/.credentials.json`,
and `$HOME` on a compute node is `/groups/branson/home/<user>`, not the workstation
home that holds it. Slots come from the queue's slots-per-GPU ratio — asking for
more leaves the job PEND forever. Unknown flags are forwarded to
`rerun_verifier.sh`.

**add_output_nclasses.py** — Backfill `output_nclasses_<var>` into `metrics.json`
without running any test. Loads the pickle but touches only `output_names` /
`output_values` / `output_range` / `output`, so there is no `print_data_summary`
walk over every trial, no Hungarian matching and no decoder.
```
python add_output_nclasses.py                          # list candidates
python add_output_nclasses.py --trial <trial> --write
python add_output_nclasses.py --all --task mouseland --write
```
Downstream chance-baselined plots need the class count per output; the supervised
companion `output_nclasses_reference_<var>` is read from the task's
`reference_stats_full.json`.

**rerun_supervised_verifiers_20260406.sh** / **merge_supervised_verifiers_20260406.sh**
— A dated pair from the 2026-04-06 sweep: rerun the verifier for every supervised
(non-oracle) trial, then merge the resulting `verifier_rerun_*` directories.
Supervised means the task has `tests/reference_stats_full.json`; the rerun skips
trials that already have an unmerged rerun directory. Both take `--dry-run`. Kept
for reference — they hardcode `$HOME/harbor-tasks/data-format/jobs` and predate
`--podman`, so they do not run against the current job trees as-is.

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
  - `tests/versions.json`
  - `tests/compute_reward.py`
  - `tests/write_reward_file.py`
  - `tests/decoder.py`
  - `tests/test_outputs.py`
  - `tests/test.sh`
  - `tests/train_decoder.py`
  - `environment/decoder.py`
  - `environment/train_decoder.py`
  - `environment/Dockerfile` (only `debug` and new tasks: each benchmark task pins its own packages)

`tests/expected_files.json` is per task and is not synced: maximal tasks list the full set of
agent files, and `generate_minimal_task.py` writes the minimal list. Both require the same two
files (`convert_data.py`, `converted_data.pkl`); the rest of the maximal list is expected, so
missing notes or logs are recorded and warned about rather than failing the test.

After updating any of these files, use this to propagate changes. 

If `Dockerfile` is changed: reverify images are tagged with the pinned harness
versions, so a **version** bump rebuilds on its own. Any other Dockerfile edit is
not in the tag — delete the stale images first
(`docker image rm hb__<task>-reverify:<tag>`, or `podman` if that is what built them).
Note `tests/versions.json` and the `Dockerfile` version lines are generated: edit the
config and run `apply_versions.py`, do not hand-edit them.
Note that some tasks have specialized files and will require manual melding after a change: 
`Dockerfile`: all eight benchmark tasks (package versions match their terminal-bench-science versions)
`task.toml`: `mouseland`, and every `_minimal` / `_datalimit` task
`tests/test_outputs.py`: `debug`
`tests/train_decoder.py`: `debug`
`environment/train_decoder.py`: `debug`


**generate_reference_stats.sh** — Run the oracle solution to generate `reference_stats_full.json`
(step 1 of 2; step 2 is `rerun_verifier.sh --decoder-stats` on the resulting trial).
```
generate_reference_stats.sh              # all tasks
generate_reference_stats.sh sosa2024     # one task
```

**compute_decoder_stats.py** — Add decoder accuracy over independent train/validation splits
(mean, standard deviation and each split's value; 20 by default) to an oracle's
`stats_full.json`. The verifier's accuracy threshold is mean − 3.5 × std. Normally run through
`rerun_verifier.sh --decoder-stats`, so it uses the task image's torch and numpy.

**generate_minimal_prompt.py** — Generate `minimal_prompts/<task>_prompt_minimal_v<N>.md`
from the maximal prompt (v1 from `prompt_v4/`, v2 from `prompt_v5/`) by stripping the procedural scaffolding: the
critical-constraints preamble, `## Python environment`, the 13-step `## Conversion
Workflow`, the `## CONVERSION_NOTES.md Template`, and `## Key Considerations`, plus the
"computational neuroscientist" persona and the `**Documentation**` link bullet. The task
specification, target format, decoder reference and success criteria are kept verbatim
(~870 lines in, ~200 out). `--check` verifies the transform still reproduces the
hand-written sosa2024 minimal prompt byte-for-byte. v2 also drops the consistency paragraphs
about sanity checks and verifying every step, the "Pipe the output" line, and the long Success
Criteria list (replaced by a short list requiring only `convert_data.py` and `converted_data.pkl`).
```
python generate_minimal_prompt.py --all                 # every prompt, minimal v1
python generate_minimal_prompt.py --all --version 2     # every prompt, minimal v2
python generate_minimal_prompt.py sosa2024              # one task
python generate_minimal_prompt.py --all --check         # verify only, write nothing
python generate_minimal_prompt.py --all --force         # overwrite existing outputs
```

**generate_minimal_task.py** — Generate a minimal-prompt version of a task,
`harbor-tasks/<task>_minimal`. Copies the task and swaps the prompt from
`minimal_prompts/<task>_prompt_minimal_v<N>.md` into both `instruction.md` (what the
agent sees) and `tests/instruction_reference.md` (what the judge reads), writes the minimal
`tests/expected_files.json` (only `convert_data.py` and `converted_data.pkl`), and writes the
judge instructions with the agent-file list limited to those files. Everything else — tests,
reference solution, environment — is copied unchanged. Caches and `solution/*.pkl` leftovers
are skipped. The generated directories are committed.
```
python generate_minimal_task.py sosa2024              # highest prompt version
python generate_minimal_task.py sosa2024 --version 2  # pin to a prompt version
python generate_minimal_task.py --all --version 2     # every task with a v2 prompt
python generate_minimal_task.py sosa2024 --dry-run
python generate_minimal_task.py sosa2024 --force      # regenerate in place
python generate_minimal_task.py --all --version 2 --update   # rewrite only the derived files
python generate_minimal_task.py --all --version 2 --check    # report out-of-date derived files
```

**generate_datalimit_task.py** — Generate the datalimit version of a task,
`harbor-tasks/<task>_datalimit`: the minimal task run on `data/<task>_datalimit`. Every file is
derived and rerunning brings the directory up to date, so it is never edited by hand:
- copied unchanged from `<task>_minimal`, except
- `instruction.md` and `tests/instruction_reference.md`: the minimal prompt plus the Data subset
  section and Consistency bullet from `download/datalimit/<task>_prompt.md`;
- `environment/docker-compose.yaml`: the data mount points at `${DATA_ROOT}/<task>_datalimit`
  (allen2p also mounts `DATALIMIT_SUBSET.csv` at `/app/data/DATALIMIT_SUBSET.csv`).

`tests/reference_stats_full.json` is the one file not generated: it has to describe the reduced
data, so it is kept when present. Only tasks whose data was actually reduced get a `_datalimit`
task (allen2p, map, mouseland, sosa2024, zhang2025); the others use their `_minimal` task.
The subset itself is decided by `download/select_datalimit.py` (frozen into
`download/datalimit/<task>.csv`).
```
python generate_datalimit_task.py sosa2024
python generate_datalimit_task.py --all
python generate_datalimit_task.py --all --check        # report out-of-date files
python generate_datalimit_task.py sosa2024 --dry-run

# then, per task, generate its reference statistics on the reduced data:
harbor-scripts/generate_reference_stats.sh sosa2024_datalimit
harbor-scripts/rerun_verifier.sh --decoder-stats --task sosa2024_datalimit <oracle trial dir>
```

**check_task_variants.py** — Check that a task's variants agree: files that must be identical
across `<task>`, `<task>_minimal` and `<task>_datalimit`; the prompt and judge copies; that each
prompt names the files its `expected_files.json` requires; and that the generated minimal and
datalimit files are up to date.
```
python check_task_variants.py            # every task
python check_task_variants.py sosa2024
```

**check_forks_match.py** — Compare data-format with the terminal-bench-science versions of the
tasks (branches `neurodata-reuse-<name>`): grading code, decoder scripts, reference solution,
package versions, prompt and reference statistics, plus the files that must be identical across
all the forks. Known, deliberate differences (canary lines, the judge-related prompt sentences,
the data-reuse wording data-format did not take) are ignored and listed in the script.
```
python check_forks_match.py              # forks read from their committed branches
python check_forks_match.py --worktree   # forks read from ~/tb-science-<name> working copies
python check_forks_match.py sosa2024 --verbose
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

Per-task data dirs (mirror the docker-compose mounts, i.e. `<repo>/data/<task>`):
- `allen2p` → `<repo>/data/allen2p/visual-behavior-ophys-1.1.0`
- `hasnain2024` → `<repo>/data/hasnain2024`
- `lee2025` → `<repo>/data/lee2025`
- `majnik2025` → `<repo>/data/majnik2025`
- `map` → `<repo>/data/map`
- `mouseland` → `<repo>/data/mouseland`
- `sosa2024` → `<repo>/data/sosa2024`
- `zhang2025` → `<repo>/data/zhang2025`

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

**podman_env.sh** — Not an entry point: `source` it before running a container on a
batch node. `run_harbor.sh` and `submit_rerun_verifier.sh` both do.
```
export USE_PODMAN=true
source harbor-scripts/podman_env.sh
```
Everything in it is a workaround for a specific batch-node failure, each found the
hard way — a per-job runroot (a shared one goes stale when the node reboots), a
node-shared graphroot so a second job reuses cached layers instead of repeating a
~7 min image build, `cgroup_manager = "cgroupfs"` (crun's systemd default needs a
D-Bus session bus that batch nodes lack), an EXIT trap that reaps the `catatonit`
pause process (without it LSF holds the node in RUN until the wall clock long after
the work is done), and a health probe that repairs or fails fast, because a broken
podman otherwise becomes a per-trial exception while the job still exits 0 and LSF
hands the freed node to the next job to kill.

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
