# What is left to do

---

## 1. Moving jobs from staging area to git repo
Migrate from `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-jobs-new`
to `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-jobs`

## Record of terminus job failures:

Killed the following jobs on 2026-09-20 because they were stuck. All eight are
`terminus-opus`, and all eight failed the same way:

| trial | LSF job | host | harbor run | turns | terminal died | dead for | largest paste | cost |
|---|---|---|---|---|---|---|---|---|
| `allen2p` t2 | 154375874 | `h06u23` | 05:10:54 - 12:54:41 | 144 | 06:05:45 | 6h49m | 25,057 | $59.19 |
| `map` t2 | 154375898 | `h06u31` | 09:55:17 - 13:09:23 | 126 | 11:02:47 | 2h07m | 26,692 | $16.38 |
| `map` t3 | 154375899 | `h06u06` | 10:31:29 - 13:09:23 | 126 | 11:31:10 | 1h38m | 30,430 | $25.17 |
| `mouseland` t2 | 154375904 | `h06u27` | 12:12:07 - 13:19:17 | 69 | 13:04:54 | 14m | 25,823 | $8.48 |
| `mouseland` t3 | 154375905 | `h06u22` | 12:27:46 - 14:11:32 | 89 | 13:26:47 | 45m | 27,015 | $13.02 |
| `sosa2024` t1 | 154375909 | `h06u27` | 13:19:35 - 14:33:05 | 418 | 13:59:57 | 33m | 25,511 | $46.77 |
| `sosa2024` t2 | 154375910 | `h06u23` | 13:45:21 - 15:15:25 | 102 | 14:41:25 | 34m | 26,166 | $12.67 |
| `zhang2025` t1 | 154375916 | `h06u06` | 15:00:35 - 16:36:13 | 99 | 15:58:52 | 37m | 25,483 | $10.42 |

$192.10 between them, and none of it bought anything: every turn after the "terminal died"
column is a poll of a pane that never changed again. None produced a `convert_data.py` or a
`converted_data.pkl`, and none has a `metrics.json`, so none carries a score.

How long each took to catch is the case for the detection. `allen2p` t2 was noticed by hand
after 7h44m, for $59.19. The two `map` ones were found by running `check_stuck_trials.py`
while they ran, and killed within two hours. `mouseland` t2 was killed 14 minutes after its
terminal died, for $8.48, caught by its own turns reporting a frozen pane before it even
crossed the checker's 30-minute threshold. The last four -- `mouseland` t3, `sosa2024` t1 and
t2, and `zhang2025` t1 -- were killed by `watch_stuck_trials.sh` with nobody watching, 33 to
45 minutes after each got stuck.

All eight ran on the paste delivery as it was before the fix below. `zhang2025` t1 was the
last of them, started at 15:00:35, twenty minutes before the fix was merged at 15:20:23.

**All twelve affected trials were resubmitted** at 17:59 as LSF 154382140-154382151, with
`--jobs` so the set is exact and nothing still running is disturbed. Twelve rather than eight
because four more ran to the 800-turn cap on a stuck terminal and were scored on nothing:
`allen2p` t3, `hasnain2024` t1, `lee2025` t1 and `map` t1. `map` needed all three of its
trials, having produced nothing usable at all.

Each landed a new `raw/<timestamp>/` beside the old one and recorded `f6f9ded3` in its
`lock.json`, distinguishing it from the pre-fix failures at `4f5222ad`. With the
`mouseland_minimal` trial killed by mistake (below), thirteen went in. They took three
attempts to start -- a relative config path, then a Launchpad outage, both under "Confirmed
in live trials" -- and ran on 2026-09-21. Every one produced its outputs:

| trial | first run | rerun, fixed harbor |
|---|---|---|
| `map` t1 / t2 / t3 | stuck: 0.18, killed, killed | **0.97 / 0.97 / 0.53** |
| `sosa2024` t1 / t2 | both killed | **0.99 / 0.97** |
| `allen2p` t2 / t3 | killed, stuck 0.25 | **0.42 / 0.43** |
| `mouseland` t2 / t3 | both killed | **0.53 / 0.49** |
| `hasnain2024` t1 | stuck 0.27 | **0.55** |
| `lee2025` t1 | stuck 0.22 | **0.55** |
| `zhang2025` t1 | killed | **0.52** |
| `mouseland_minimal` gpt t1 | healthy, killed by mistake | **0.45** |

So `map` terminus-opus went from no usable trial to three.

**One healthy trial was killed by mistake.** `mouseland_minimal` / `terminus-gpt` t1, LSF
154377223, killed 21:03 on 2026-09-20 by `watch_stuck_trials.sh`. It was not stuck: its pane
read `[82/89] TX108_2023_04_01_1`, a conversion 92% of the way through its sessions, and its
last turns say so -- "the large session completed successfully", "session 82 is still
processing normally". It needs resubmitting, and it is an infrastructure failure rather than
an agent one.

The detector was reading the wrong file. It measured staleness from `agent/recording.cast`,
which is written by a separate `asciinema rec` process; that process had stopped 35 minutes
earlier while the terminal carried on. `agent/terminus_2.pane` is the direct measurement --
terminus rewrites it from `capture-pane` every turn -- and it was current to within three
minutes. On a genuinely stuck trial the two stop together within a second, which is why one
example made them look interchangeable. `check_stuck_trials.py` now reads the pane.
Backtested over 81 finished trials: the pane signal catches 11 of the 12 known failures with
no false alarms, where the recording signal caught the same 11 and raised this one false
alarm. The twelfth, `mouseland` opus t2, sat 14 minutes below the 30-minute threshold and was
caught by hand.

**The failure.** terminus writes a file by pasting it into the tmux pane in one piece. Past
roughly 24,000 characters the pty input buffer stops draining mid-paste, the shell never
returns from the heredoc, and the pane freezes at the `>` continuation prompt. The boundary
is sharp: ranking the 2026-09-20 `terminus-opus` runs by their largest single paste, all
eight above 24,133 characters got stuck and none of the eleven below 23,109 did. For `allen2p`
t2 the mechanism is visible in `agent/recording.cast`, which ends at t=2820.6 s with a run of
input events and not one output event after it. The agent cannot distinguish that from a slow
command, so it polls: `job.log` fills with `Sending keys: ['']` at 60-180 s a time, and the
trajectory becomes one repeated turn. Ctrl-C, Ctrl-D, Ctrl-Q, Ctrl-\, `reset`, `stty sane`,
the heredoc delimiter and `exit` were all tried across the eight trials; none reached the
shell, because nothing was draining the buffer.

**Fixed in the harbor fork.** `_paste_key` in `terminus_2/tmux_session.py` staged an
oversized key to a file in chunks and then handed the whole thing to the pane in one
`paste-buffer`; it now delivers it in 4 KB line-aligned pieces with a pause between, so the
shell drains as it goes. The bytes reaching the pane and their order are unchanged.

Reproducing it needs a container, which is why it never showed up in development: replaying
the 34,827-character heredoc from `map` t1 on a workstation running tmux 3.5a and asciinema
2.4.0 completes in a second, while the same payload in a task image running tmux 3.2a and
asciinema 2.1.0 gets stuck every time. `scripts/reproduce_terminus_paste_problem.sh` in the
fork replays it either way: unchunked wrote 0 of 722 lines and left the pane at `>`, chunked
wrote all 722 and came back to a prompt.

The fix is upstream's code, from harbor PR #1873/#1904, so it is a candidate to offer back
alongside the compose-detection fix above.

**Confirmed in live trials** on 2026-09-21, once the reruns ran. Four of them pasted past
the old threshold -- `sosa2024` t2 at 32,284 characters, `mouseland` t2 at 31,150, `map` t1
at 30,898, `sosa2024` t1 at 29,297 -- and all four kept a live pane. On the old delivery
every `terminus-opus` run above about 24,000 characters got stuck, eight of eight, and these
are the same trials that did, most of them now pasting more than they did then.

The reruns took two attempts to start, for reasons unrelated to the fix. The first batch
passed `--versions` as a relative path; jobs run from the home directory, so every one
failed to find the config and exited in under a second. `submit_harbor_cluster.py` passes
the path through unresolved, and `run_harbor.sh`'s error names the fallback directory it
would search rather than the path it actually checked, which points away from the cause. The
second batch hit a Launchpad outage, roughly 09:10-09:37: the task Dockerfiles add the
`deadsnakes` PPA for Python 3.13, and Launchpad's signing-key lookup
(`getSigningKeyData`) returned 500 `GPGKeyTemporarilyNotFoundError`, so no image could build.
It took out every build in that window, the September reruns and 28 of the 30 July-sweep
terminus jobs alike. Because each job rebuilds its image from scratch, every job depends on
Launchpad at the moment it starts -- a second argument for the shared image store in
section 3.

**Why they were killed rather than left to finish.** Neither `map` trial would have reached
the 800-turn cap that ends the other stuck trials: at 126 turns, advancing 14 to 16 an hour,
both were on course for the 24-hour agent timeout roughly 21 hours out. A trial that times
out is not scored, so letting them run would have bought about $100 more and still produced
no result -- the outcome that killing them produces immediately.

**What each one left on disk.** `run_harbor.sh`'s cleanup runs on the interrupt, so all three
are collected like ordinary trials, under
`/groups/branson/home/bransonk/harbor-cluster-jobs/hb_<task>_terminus-opus_t<N>/<task>/terminus-2/<timestamp>_trial1`:
a `result.json` carrying `exception_type: CancelledError`, an `exception.txt` whose traceback
ends inside `terminus_2/tmux_session.py` at the poll it was sleeping in, and the full
trajectory and recording. None has a `metrics.json`, because the verifier never ran, so none
carries a score. All three would have scored 0 -- harbor reports `agent produced no
convert_data.py or converted_data.pkl` for each, and their trajectories show the agent
finishing steps 0-5 of the conversion notes and never executing the script. Anything
downstream that reads `metrics.json` skips these trials rather than seeing a zero, which is
worth remembering when the terminus arms are tabulated.

**The same issue hit four more trials in the same sweep, and those were scored.** Found by
`check_stuck_trials.py --all` over all 45 terminus trials. Each one pasted a file into the
pane, got the pty stuck, and then spent every remaining turn polling a dead terminal until it
hit the 800-turn cap -- so it ended by running out of turns rather than by hanging, and was
verified and scored like an ordinary run:

| trial | turns | terminal dead for | reward | rerun |
|---|---|---|---|---|
| `allen2p` terminus-opus t3 | 801 | 4h08m | 0.2474 | 0.43 |
| `lee2025` terminus-opus t1 | 801 | 1h40m | 0.2236 | 0.55 |
| `map` terminus-opus t1 | 801 | 1h16m | 0.1835 | 0.97 |
| `hasnain2024` terminus-opus t1 | 801 | 1h11m | 0.2688 | 0.55 |

**All four are superseded and set aside, not collected.** The collect script takes anything
with a `verifier/metrics.json`, and these have one, so left in place they would have been
collected next to the reruns that replaced them, giving each arm a fourth trial scored on
nothing. They were moved to `/groups/branson/home/bransonk/harbor-cluster-jobs-superseded/`,
each keeping its sub-path -- for example
`hb_allen2p_terminus-opus_t3/allen2p/terminus-2/2026-09-20__05-17-38_trial1` -- and the reruns
were collected in their place. They are kept for the record of the failure, and are not a
measurement.

Their closing turns read `Wedged pty, no in-pane action available` and `Terminal unchanged
for roughly 726 consecutive polls`. **None of them produced any output at all** -- every
verifier reports `Required files missing: ['convert_data.py', 'converted_data.pkl']` and
skips every outcome test. The reward is entirely the judge component, partial credit for the
`CONVERSION_NOTES.md` written before it got stuck. So a trial that produced nothing scores
around 0.25, which is worth knowing independently of this bug: the process score stands on
its own even when there is no artifact behind it.

Two July trials carry the same signature, `zhang2025` terminus-gpt t3 and `hasnain2024`
terminus-gpt t1.

The 800-turn cap is what makes this quiet. Without it these would have hung for a day and
been noticed; with it they look like finished trials with middling scores.

**It is an arm, not the scaffold.** Of the 2026-09-20 trials, all 15 finished `terminus-gpt`
produced their outputs and none got stuck, while 8 of the 19 `terminus-opus` runs did. Both
arms run the same terminus-2 against the same pty, and the difference is only how much they
paste at once: the largest single keystroke payload per run has median 23,109 characters for
opus against 13,137 for gpt. Every opus run above the ~24,000 threshold got stuck; gpt never
exceeded 20,054 and so never reached it. So the
`terminus-opus` numbers are depressed by a mechanical limit that `terminus-gpt` stays under
by writing in smaller pieces, which is worth saying explicitly wherever the two arms are
compared.

## 2. Podman image builds on the cluster

Every cluster job rebuilds the task image, five to seven minutes on these tasks, because
`PODMAN_PRIVATE_STORAGE=true` gives each job its own graphroot. That is deliberate: a shared
store outlives the job that filled it, and a job killed partway leaves it unusable.
`podman_env.sh` then refuses to reset a shared store -- correctly, since it cannot prove no
sibling is using it -- so a poisoned node fails every job it is handed in under a second,
frees itself, and takes the next. Three such hosts destroyed 63 jobs on 2026-09-19. A few
minutes of build per job is cheap against that.

**The GPU is named, not requested.** Every task's `environment/docker-compose.yaml` reserves
its card as `device_ids: ["${HARBOR_GPU_ID:-0}"]`, which `run_harbor.sh` fills from
`harbor-scripts/gpu_ids.py`. Do not put `count:` back: on a multi-GPU node it yields physical
index 0, a card the job does not own, and the decoder falls back to CPU while holding an idle
one. `gpu_ids.py`'s docstring has the reasoning. This is what makes the dense queues usable --
`gpu_l4` is 8 slots against `gpu_l4_large`'s 64, and 88 GPUs against 32.

Recovering a poisoned host: `podman unshare rm -rf /scratch/$USER/podman-storage` on that
node while nothing of yours is running there. A plain `rm -rf` fails -- rootless podman's
overlay directories are owned by subuid-mapped UIDs -- which `podman_env.sh` already
documents at its own reset path.

**A build that overruns is not cleaned up.** `harbor`'s environment start has a
`build_timeout_sec`, and `compose up -d` builds the image when the store is cold, so the
timeout covers the build. On expiry harbor cancels the await but does not kill the
process, leaving `podman build` running: `cleanup_podman_job` removes containers and the
pause process, and a build is neither, so it survives and LSF holds the job in RUN until
someone kills it. The timeout is now 1800 s, which makes the overrun unlikely rather than impossible. The cleanup could also kill processes whose root or cwd is under
`$PODMAN_JOB_DIR` before removing it -- scoped to the job's own directory, so a sibling
is never touched, and by pid rather than by name.

**Both go away with an additional image store.** Podman can read images from a read-only
store listed in `storage.conf` as `additionalimagestores`, layering a private writable
graphroot on top. Build each task's image once into a shared location, and jobs find it
present, never write to it, and cannot corrupt each other: no per-job build, no
corruption risk, and nothing for a timeout to interrupt.

## Known gaps, not yet scheduled

- **Two small fixes so a relative `--versions` path cannot silently sink a batch.** On
  2026-09-21 thirteen resubmitted jobs each exited in under a second because the config was
  given as `harbor-scripts/config_20260919.json`, and jobs start in the home directory, not
  the repo. Nothing flagged it until the whole batch had waited in the queue and died.
  - `submit_harbor_cluster.py:510` passes `--versions` through as typed. Resolving it --
    `(args.versions or newest_versions_config()).resolve()` -- makes a relative path mean the
    directory it was typed in. Another session edits and submits through this file too, so
    tell it before changing.
  - `run_harbor.sh:72-74` prints `looked for $SCRIPT_DIR/config_*.json` whichever check
    failed, so when an explicit `--versions` is missing it names the fallback directory -- the
    correct one -- and points away from the cause. It should name the path it tested.
- **Push the fork commits?** Each `~/tb-science-*` clone now has three unpushed commits on
  `neurodata-reuse-<name>`, and those branches have open pull requests. The third carries the
  threaded conversion, the CPU fallback and the two session-handling fixes, which brings
  `decoder.py` and `train_decoder.py` back into step with this repository -- each fork keeps
  only its own harbor-canary line in `tests/train_decoder.py`.
- **Does a re-collected July trial keep its bare name?** `collect_cluster_results.py` now
  appends the config it was given, so collecting with `--versions config_20260728.json` files
  trials under `claude-code-config_20260728`. The trials already in `harbor-jobs/` are bare
  `claude-code`, which is what `utils.AGENT_KEYS` maps to the 4.6/5.4 display names, and they
  parse unchanged -- all 146 of them. The two spellings only diverge if July trials are ever
  re-collected out of `harbor-cluster-jobs/`. Either add the four `-config_20260728` keys
  pointing at the same display names, or decide that already-collected trials are never
  collected again.
- **`harbor-scripts/data_roots.sh` is unclaimed** -- in neither session's work, referenced by
  nothing, left out of every commit.
- **A loud failure for zhang2025's index loading.** If the session index is not found, the
  search returns nothing without raising. The index is present in both datasets, so it should
  not fire, but a check would fail at the point of the mistake. It would have to go into the
  terminal-bench-science copy too, to keep that one file shared.
- **Offer the compose-detection fix upstream?** Harbor has to work out which "compose" program
  it is driving, because the two differ: Docker Compose V2 has `cp` and `ls` subcommands and a
  `--project-directory` flag, while podman-compose -- a separate Python program -- has none of
  them. Harbor decided by running `podman compose up --help` and looking for `--detach`, which
  both advertise. So on a host where `podman compose` is only a thin wrapper that hands off to
  podman-compose, harbor concluded it had Compose V2 and then broke on the first subcommand
  podman-compose does not have, reporting it as a missing Podman API socket -- which sent us
  looking in the wrong place entirely. `21e76a50` asks `podman compose version` instead, where
  the program names itself. The bug is upstream's, not ours, so it is worth offering to
  harbor-framework; if they take it, we stop carrying the patch.
- **Should `rerun_verifier.sh` call `harbor trials regrade`?** Re-scoring trials that have
  already run is needed whenever the grading code changes, and there is nothing left to port:
  harbor now ships its own command for it. Kai wrote `harbor trials reverify` for the fork in
  `d7ac3b21` (2026-03-10), which re-ran the verifier on a finished trial and overwrote that
  trial's `result.json`. Upstream reached the same capability independently four months later
  -- Kobe Chen's `b3d5f5af`, 2026-07-21, PR #2358 -- and that one is in 0.23.0, so `harbor
  trials regrade` is already on the branch we just pushed. It differs in never touching the
  source trial: it writes a new one, and it also accepts a Hub trial UUID.

  It would replace only half of what we do. `rerun_verifier.sh` builds its own
  `hb__<task>-reverify` image and runs the verifier container directly, which is what lets it
  do a judges-only rerun and hand rootless podman the CDI device name that trials stored on
  `/groups` need. `merge_rerun_verifier.sh` then folds the result back into the original
  trial, merging `metrics.json` key by key rather than replacing it. `regrade` covers the
  first script's container work and not the second's merge, so the question is whether harbor
  should own launching the verifier -- not whether it can take over the workflow.
- **Every upload makes one call it knows will fail.** Copying files into a container has two
  routes, `compose cp` and a tar stream for programs that lack it, and harbor records which
  one the program supports in `supports_compose_cp`. Downloads check that flag before
  choosing; uploads do not, so they always try `compose cp` first and fall back after it
  fails. Under podman-compose, which has no `cp` at all, that failure is guaranteed on every
  upload. It costs nothing but noise in the logs. A small fix, and a candidate for the same
  pull request as the one above.

- **The forks are behind on grading code.** `check_forks_match.py --worktree` reports
  `tests/test_outputs.py`, `write_reward_file.py` and `train_decoder.py` as differing: the
  forks do not have the per-task `expected_files.json` or the required-files change, and some
  of it cannot be shared anyway, because the forks have no LLM judges.
- **Version pins are patched into each Dockerfile rather than read from a file.**
  `apply_versions.py` rewrites two `RUN` lines in all 24 `environment/Dockerfile` copies by
  regular expression. The forks solved this properly in `fadfa9d`: `tests/Dockerfile` does
  `COPY versions.json` and reads it at build time with `jq -er`, so one file decides what
  grades a run and a malformed pin fails the build rather than installing `null`. It does not
  transfer as written, because that needs the verifier in its own container: data-format
  grades in the agent's container -- there is no `tests/Dockerfile` at all -- and a Dockerfile
  cannot COPY from outside its own build context, which is `environment/`. Doing it here means
  generating `environment/versions.json` too, and the Dockerfile ends `WORKDIR /app` with
  `COPY . .`, so that file would land in `/app` and tell the agent which models judge it.
  Copying it to `/opt` early and deleting `/app/versions.json` as the last line works, and
  `jq` is already installed. Worth doing; not worth doing mid-sweep, and the delete step is
  the kind of thing that stops working quietly.
- **The same knowledge lives in two places.** `evaluation/eval/ratings/experiments.py` and
  `evaluation/eval/{utils.py,trial_metrics.py}` each hold the dataset aliases and parse task
  folder names into a dataset and a prompt variant. They agree today only because `3d91595`
  made them agree. One of them should own it.
- **The analysis code is not described** in `changes_since_preprint.md`. `lesion_analysis.py`
  changed substantially: the accuracy criterion and the threshold-sensitivity figure now work
  in standard deviations rather than the old 0.95 fraction, which changes a figure in the
  paper.
- **The decoder's SVD initialisation does not recover the subspace it claims to.** It projects
  onto `svd_max_neurons` random directions, takes the SVD there and maps back through the
  projection. Against the exact top-`npcs` subspace of a power-law spectrum, that reaches a
  mean principal-angle cosine of 0.46, where the standard formulation -- orthonormalise the
  projected range, then project the data onto it -- reaches 0.998 at the same cost, and
  0.9999 with two power iterations at half the cost. Changing it moves every reference
  number, so it is a decision for after this round of statistics, not part of it.
- **One conversion per epoch, not per run.** `SessionData` converts a session's per-trial
  arrays into the contiguous layout training reads, and the training loop reads every session
  on each of the `num_epochs` passes. Threads hide most of the cost, but the work is still
  repeated. Holding the converted sessions removes it entirely and was measured and rejected:
  the converted copy is the size of the source, and the two together do not fit the memory a
  task is given. Converting once and releasing the source as it goes would fit, but the
  release has to happen on the caller's dict, and both callers keep it -- the verifier for a
  CPU retry after a CUDA out-of-memory, `compute_decoder_stats.py` for its other replicates.

## Running the checks

```bash
source /home/bransonk@hhmi.org/miniforge3/etc/profile.d/conda.sh
conda activate test-decoder-data-format
cd /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format

python harbor-scripts/check_task_variants.py           # a task's variants, and manual/
python harbor-scripts/check_forks_match.py --worktree  # this repo vs the tb-science clones
python harbor-scripts/sync_template.py                 # files shared by every task
python harbor-scripts/check_stuck_trials.py            # terminus trials on a stuck terminal
```

While a sweep is running, leave the watchdog up instead of checking by hand. It scans every
ten minutes and **reports, never kills**: each newly stuck trial writes one line to its log,
and a person confirms from the trial's last turns that the pane is frozen -- not a long
silent command still running -- before any `bkill`. It was made notify-only after the
auto-killing version destroyed a healthy trial, below.

```bash
ROOTS="/groups/branson/home/bransonk/harbor-cluster-jobs \
       /groups/branson/home/bransonk/harbor-cluster-jobs-config_20260728-prompt_v5" \
nohup bash harbor-scripts/watch_stuck_trials.sh \
    >> /groups/branson/home/bransonk/cluster_logs/harbor/watch_stuck_trials.log 2>&1 &
```

`ROOTS` lists the job trees to scan, so one watcher can cover several sweeps at once; left
unset it scans `harbor-cluster-jobs` only. `INTERVAL_MIN` and `FROZEN_MIN` override the
cadence and the threshold.

**Read a report before acting on it.** A pane that has stopped changing looks the same from
outside whatever the cause, and the cause decides whether a kill is right. Running
`check_stuck_trials.py` on a flagged trial prints which of three it is, from the most recent
prompt on the pane:

- **continuation prompt** -- the shell is inside a heredoc or quote that never closed, the
  paste problem. Infrastructure: it will not recover. Kill it, and rerun it.
- **idle prompt** -- the shell sits at an ordinary prompt while the agent issues nothing.
  Agent behaviour, and part of the measurement. gpt-5.4 did this on harbor 0.1.45, with no
  turn cap, and the v4 arm kept and scored those trials. A bare LSF kill leaves no verifier
  and no reward, so it drops a result the arm is meant to record -- but see "Stop a trial and
  still score it" below.
- **busy** -- a command is running and has printed nothing new, or the prompt has scrolled
  out of view. It covers three quite different things, and the label cannot tell them apart:
  - *a long silent command* -- leave it;
  - *a command holding the terminal while the agent believes the shell is broken*, because
    it sent its interrupt as `'C-c\n'`. terminus 0.1.45 turns a bare `'C-c'` into Ctrl-C but
    types `'C-c\n'` literally, so the interrupt never lands; the agent's later commands are
    type-ahead that runs once the command exits. Agent behaviour. gpt-5.4 did this on both
    v5-sweep `map` trials, and both times it read as "shell only echoing input";
  - *a command blocked on I/O* -- infrastructure. `mouseland` terminus-gpt t2 stalled reading
    `/nrs` on `h06u24`, under 1 MB/s against ~650 MB/s from the workstation.

  To tell them apart, check whether the command started before or after the last bare
  `'C-c'` in `job.log`, then take two LSF CPU readings a minute apart with `bjobs -l`. CPU and
  memory climbing means it is computing; both flat, alongside an ignored bare Ctrl-C, means
  blocked. The checker does not yet flag the `'C-c\n'` case itself: a `'C-c'` followed by
  text, sent after the pane stopped changing, is the signature to add.

Checked against 14 known cases: all 10 stuck trials, the 2 idle v4 trials, and 2 healthy
long-runners, one of them the trial killed by mistake.

**Stop a trial and still score it.** For a trial worth stopping that should still be scored --
an idle-prompt loop running up the bill, say -- snapshot the verifier first, then kill:

1. pipe step [2/6] of `tests/test.sh` into the live container,
   `podman exec -i <task>__<id>_main_1 bash -s`, on the job's host, with
   `CONTAINERS_STORAGE_CONF`, `CONTAINERS_CONF` and `XDG_RUNTIME_DIR` pointed at
   `/scratch/bransonk/podman-<lsfid>/`. `/logs/verifier` is bind-mounted, so this writes
   `<trial>/verifier/snapshot/`;
2. `bkill` the job;
3. `submit_rerun_verifier.sh --apikeys <trial>`, from the checkout that ran the sweep;
4. `merge_rerun_verifier.sh --jobdir <trial>`.

The trial then records `CancelledError`, with its cost and time cut off at the kill. Two
v5-sweep gpt trials were stopped this way, for cost: `hasnain2024` t2, idle for 9 h after
writing its output ($199.78), and `map` t2, whose own `--sample` conversion ran 3 h on one
session ($147.46).

Stop it by pid. `pgrep -u $USER -f check_stuck_trials` also matches the shell running the
pgrep, so confirm the pid with `ps -p <pid>` before `kill <pid>`, and after it. Never edit
`watch_stuck_trials.sh` while it runs: stop it first.

`check_stuck_trials.py --kill` still exists for a one-off, deliberate kill once a trial has
been checked by hand.

Add a task name to either checker to run just that one. Without `--worktree` the fork checker
reads the committed branches rather than the working files.
