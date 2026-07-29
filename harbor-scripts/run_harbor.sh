#!/bin/bash

AGENT="claude"
NTRIALS=1
NCONCURRENT=1
TASK=""
USE_PODMAN=false
USE_APIKEYS=false
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
GPUIDS=""
JOBS_ROOT=""
# Which conda env supplies harbor. Overridable so an alternate harbor checkout can
# be tested without touching the default -- the cluster has its own conda root and
# only has this env, so changing the default here breaks every LSF job.
CONDA_ENV="eval-data-format-podman"
# Pinned harness/model versions. Dated configs; newest wins unless --versions
# says otherwise, and the choice is echoed below so the run log records it.
VERSIONS_FILE=""

USAGE="Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--nconcurrent N] [--task name] [--versions FILE] [--conda-env NAME] [--gpuids LIST] [--jobs-dir DIR] [--podman] [--apikeys] [--env FILE]"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)    AGENT="$2"; shift 2 ;;
    --ntrials)  NTRIALS="$2"; shift 2 ;;
    --nconcurrent) NCONCURRENT="$2"; shift 2 ;;
    --task)     TASK="$2"; shift 2 ;;
    --versions) VERSIONS_FILE="$2"; shift 2 ;;
    --conda-env) CONDA_ENV="$2"; shift 2 ;;
    --gpuids)   GPUIDS="$2"; shift 2 ;;
    --jobs-dir) JOBS_ROOT="$2"; shift 2 ;;
    --podman)   USE_PODMAN=true; shift ;;
    --apikeys)  USE_APIKEYS=true; shift ;;
    --env)      ENV_FILE="$2"; shift 2 ;;
    --help|-h)
      echo "$USAGE"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "$USAGE"
      exit 1
      ;;
  esac
done

# Concurrent runs MUST NOT share a jobs dir: the reorganization step below
# selects the newest timestamped run dir, so siblings would steal each
# other's trials. Use --jobs-dir to give every cluster job its own.
JOBS_ROOT="${JOBS_ROOT:-$HOME/harbor-tasks/data-format/jobs}"
JOBS_DIR="$JOBS_ROOT/raw"
REORG_BASE="$JOBS_ROOT"

TASK_FLAG=""
if [ -n "$TASK" ]; then
  TASK_FLAG="-t $TASK"
fi

source $HOME/miniforge3/etc/profile.d/conda.sh
conda activate "$CONDA_ENV" || { echo "ERROR: no conda env '$CONDA_ENV'"; exit 1; }
echo "conda env: $CONDA_ENV"
# Rootless podman on a batch node needs a per-job runroot, cgroupfs, and a pause
# process that gets killed or LSF holds the node. All of that lives in one place
# so submit_rerun_verifier.sh gets the identical treatment.
# shellcheck source=harbor-scripts/podman_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/podman_env.sh"

# --- Auth setup ---
if [ "$USE_APIKEYS" = true ]; then
  # Use API keys from env file
  if [ ! -f "$ENV_FILE" ]; then
    echo "Error: env file not found: $ENV_FILE"
    exit 1
  fi
  source "$ENV_FILE"
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "Error: ANTHROPIC_API_KEY not set in $ENV_FILE"
    exit 1
  fi
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Error: OPENAI_API_KEY not set in $ENV_FILE"
    exit 1
  fi
else
  # Use OAuth tokens from CLI credentials
  export CLAUDE_CODE_OAUTH_TOKEN=$(jq -r '.claudeAiOauth.accessToken' "$HOME/.claude/.credentials.json")
  export CODEX_AUTH_JSON_B64=$(base64 -w0 $HOME/.codex/auth.json 2>/dev/null || true)
fi

PODMAN_FLAG=""
if [ "$USE_PODMAN" = true ]; then
  PODMAN_FLAG="--ek use_podman=true"
fi

GPU_FLAG=""
if [ -n "$GPUIDS" ]; then
  GPU_FLAG="--ek gpu_ids=$GPUIDS"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HARBOR_TASKS="$(cd "$SCRIPT_DIR/../harbor-tasks" && pwd)"

# Root of the datasets bind-mounted to /app/data. Every task's docker-compose.yaml
# builds its mount as "${DATA_ROOT:?...}/<task>", so this must be exported for
# compose to substitute it -- harbor forwards os.environ to the compose subprocess.
#
# Absolute, not relative: compose resolves a relative volume source against the
# *project directory*, which is the first -f file's directory (harbor's own compose
# dir), not the task file that declares it. Harbor's docker path compensates with
# --project-directory, but podman-compose 1.5.0 has no such flag, so every cluster
# run resolved ../../../data/<task> inside the harbor checkout instead. The runtime
# then CREATED that missing source as an empty directory and mounted it read-only,
# with no error anywhere -- the whole 2026-07-27 sweep ran against an empty
# /app/data. Hence the checks below: this must never fail quietly again.
#
# Overridable from the environment so the data can live on faster local disk:
#   DATA_ROOT=/scratch/data bash run_harbor.sh --agent claude --task sosa2024
if [ -z "${DATA_ROOT:-}" ]; then
  DATA_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)/data"
fi
if [ ! -d "$DATA_ROOT" ]; then
  echo "ERROR: DATA_ROOT=$DATA_ROOT is not a directory."
  echo "       Set DATA_ROOT to the directory holding the per-task dataset dirs."
  exit 1
fi
if [ -z "$(ls -A "$DATA_ROOT" 2>/dev/null)" ]; then
  echo "ERROR: DATA_ROOT=$DATA_ROOT is empty."
  echo "       An empty data root is what the 2026-07-27 sweep silently ran on."
  exit 1
fi
export DATA_ROOT
echo "data root: $DATA_ROOT"

# Verify the bind source each task actually mounts, not just that DATA_ROOT exists.
# The tasks' own test_data_dir_accessible checks this too, but only in the verifier
# -- after the agent has burned its full timeout. Checking here costs a second and
# is what would have stopped the 2026-07-27 sweep on its first job instead of its
# 48th. Scoped to the task being run when -t was given, so a single-task run is not
# blocked by an unrelated dataset that happens to be missing.
if ! python3 "$SCRIPT_DIR/check_data_mounts.py" $TASK; then
  echo "ERROR: data mounts are not usable -- refusing to start."
  exit 1
fi

# Resolve the versions config: explicit --versions, else the newest dated one.
# Defaulting to newest keeps existing callers working, but the file used is
# echoed so a run log always records which pins were in force.
if [ -z "$VERSIONS_FILE" ]; then
  VERSIONS_FILE=$(ls -1 "$SCRIPT_DIR"/config_*.json 2>/dev/null | sort | tail -1)
fi
if [ ! -f "$VERSIONS_FILE" ]; then
  echo "ERROR: no versions config found (looked for $SCRIPT_DIR/config_*.json)."
  echo "       Pass one with --versions FILE."
  exit 1
fi
echo "versions: $VERSIONS_FILE"

# Keep the generated files in step with the config automatically -- the task
# Dockerfiles and tests/versions.json cannot read it at runtime, so a bumped
# config would otherwise leave agents on the new harness and judges on the old.
# Under LSF only verify: the 48 jobs of a sweep share this checkout, so writers
# would race; submit_harbor_cluster.py applies once before any job starts.
# Failure is fatal either way -- a warning in a batch log is a warning nobody
# reads, and the result would be a silently split run.
if [ -n "${LSB_JOBID:-}" ]; then
  python3 "$SCRIPT_DIR/apply_versions.py" --check --versions "$VERSIONS_FILE" \
    || { echo "ERROR: generated files are out of step with $VERSIONS_FILE."; exit 1; }
else
  python3 "$SCRIPT_DIR/apply_versions.py" --versions "$VERSIONS_FILE" \
    || { echo "ERROR: could not apply $VERSIONS_FILE."; exit 1; }
fi

# Read one field of one arm. Empty output when the field is absent -- the caller
# decides whether that is fatal, because it depends on the field: an empty model
# would silently unpin the run, but harness_version is legitimately absent on
# terminus arms, which are native harbor code with no CLI to pin.
read_pin() {  # $1 = arm key, $2 = field
  jq -r --arg arm "$1" --arg f "$2" '.tools[$arm][$f] // empty' "$VERSIONS_FILE"
}

# No `harbor run -c` path: a job config would bypass the pins above, and harbor's
# -a flag wipes a config's `agents` list outright, so combining them silently
# drops the version pins. Everything goes through the flags below.
case "$AGENT" in
  oracle)
    # The oracle runs the reference solution, not an LLM: no model, no harness.
    harbor run -p "$HARBOR_TASKS" -a "oracle" -o "$JOBS_DIR" -k 1 -n "$NCONCURRENT" $TASK_FLAG $PODMAN_FLAG $GPU_FLAG
    ;;
  *)
    # Every other agent is an arm defined in the versions config, so adding one
    # (a new agent, or the same agent on a different model) needs no change here.
    HARBOR_AGENT=$(read_pin "$AGENT" harbor_agent)
    MODEL=$(read_pin "$AGENT" model)
    if [ -z "$HARBOR_AGENT" ] || [ -z "$MODEL" ]; then
      # Built separately: nesting a jq program inside a double-quoted string mangles
      # its quotes.
      KNOWN_ARMS=$(jq -r '.tools | keys | join(", ")' "$VERSIONS_FILE")
      echo "ERROR: '$AGENT' is not an arm in $VERSIONS_FILE (needs harbor_agent and model)."
      echo "       Known arms: $KNOWN_ARMS (or oracle)"
      exit 1
    fi
    # Absent on native agents like terminus-2, which have no CLI to pin.
    HARNESS=$(read_pin "$AGENT" harness_version)
    AK=""
    [ -n "$HARNESS" ] && AK="--ak version=$HARNESS"

    # An arm with no harness is a native agent reaching the provider API directly
    # through LiteLLM, which reads env vars and knows nothing about the CLI
    # credential files. Without keys it fails deep inside the container, so say so
    # here instead.
    if [ -z "$HARNESS" ] && [ "$USE_APIKEYS" != true ]; then
      if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
        echo "ERROR: arm '$AGENT' ($HARBOR_AGENT) calls the provider API directly and needs"
        echo "       ANTHROPIC_API_KEY / OPENAI_API_KEY. Pass --apikeys, or export them."
        exit 1
      fi
    fi

    echo "arm: $AGENT  agent=$HARBOR_AGENT  model=$MODEL  harness=${HARNESS:-n/a}"
    harbor run -p "$HARBOR_TASKS" -a "$HARBOR_AGENT" -m "$MODEL" $AK -o "$JOBS_DIR" -k "$NTRIALS" -n "$NCONCURRENT" $TASK_FLAG $PODMAN_FLAG $GPU_FLAG
    ;;
esac
HARBOR_RC=$?
[ "$HARBOR_RC" -ne 0 ] && echo "WARNING: harbor run exited $HARBOR_RC"

# Fix permissions on agent logs — Claude Code creates session files with restrictive
# permissions (0604) that block Harbor's post-processing trajectory conversion.
chmod -R a+rX "$JOBS_DIR" 2>/dev/null || true

# Post-process: reorganize outputs into jobs/<task>/<agent>/<timestamp>_trial<N>/
LATEST_JOB=$(ls -td "$JOBS_DIR"/20* 2>/dev/null | head -1)
# Diagnostics for a live puzzle: on 2026-07-28 every terminus job exited 0 with its
# trial left in raw/ and produced NO output from this block, while claude and codex
# jobs in the same sweep reorganised normally. Replaying these exact commands by
# hand against those directories afterwards works, so record the inputs and find out
# what differs at run time. Cheap, and it prints on every job.
echo "reorg: JOBS_DIR=$JOBS_DIR"
echo "reorg: candidates=$(ls -d "$JOBS_DIR"/20* 2>/dev/null | tr '\n' ' ')"
echo "reorg: LATEST_JOB=${LATEST_JOB:-<empty>}"
[ -n "$LATEST_JOB" ] && echo "reorg: trials=$(ls -d "$LATEST_JOB"/*__*/ 2>/dev/null | tr '\n' ' ')"
if [ -n "$LATEST_JOB" ]; then
  declare -A task_trial_num
  REORG_DIRS=()
  # EVERY run directory, not just the newest. Two bugs fixed by this:
  #   * Stranding. A run whose reorganization never happened stays in raw/ forever,
  #     because the old code only ever looked at the newest directory. Every
  #     terminus job on 2026-07-28 exited 0 with its trial left in raw/. Looping
  #     over all of them makes this self-healing: a later job in the same jobs dir
  #     picks up whatever an earlier one left.
  #   * Sibling theft. `ls -td | head -1` returns the NEWEST run in the jobs dir,
  #     which for two jobs sharing one (a duplicate --jobs-dir) is the other job's
  #     run -- confirmed on hb_sosa2024_terminus-opus_t1, where it resolved to the
  #     sibling's 22-19-22 rather than its own 22-00-04.
  for run_dir in "$JOBS_DIR"/20*/; do
    [ -d "$run_dir" ] || continue
    TIMESTAMP=$(basename "$run_dir")
    for trial_dir in "$run_dir"*__*/; do
      [ -d "$trial_dir" ] || continue
      task_name=$(basename "$trial_dir" | sed 's/__[^_]*$//')
      # Infer agent name: config.json (most reliable) > trajectory.json > $AGENT
      trial_agent=""
      if [ -f "$trial_dir/config.json" ]; then
        trial_agent=$(jq -r '.agent.name // empty' "$trial_dir/config.json" 2>/dev/null)
      fi
      if [ -z "$trial_agent" ] && [ -f "$trial_dir/agent/trajectory.json" ]; then
        trial_agent=$(jq -r '.agent.name // empty' "$trial_dir/agent/trajectory.json" 2>/dev/null)
      fi
      [ -z "$trial_agent" ] && trial_agent="$AGENT"
      # Subscript QUOTED. Unquoted, it is only safe while `declare -A` is in scope:
      # an indexed array evaluates the subscript arithmetically, so a hyphenated
      # agent name makes "sosa2024__terminus-2" mean 0 - 2 = -2 and bash aborts the
      # loop with "bad array subscript". claude-code and codex both evaluate to a
      # harmless 0, so the breakage would be terminus-only and easy to miss.
      task_trial_key="${task_name}__${trial_agent}"
      task_trial_num["$task_trial_key"]=$(( ${task_trial_num["$task_trial_key"]:-0} + 1 ))
      dest="$REORG_BASE/$task_name/$trial_agent/${TIMESTAMP}_trial${task_trial_num["$task_trial_key"]}"
      mkdir -p "$(dirname "$dest")"
      mv "$trial_dir" "$dest"
      echo "Results moved to $dest"
      REORG_DIRS+=("$dest")
    done
  done

  # Report helpers. Both read JSON the trial produced; jq rather than an embedded
  # python heredoc, so the shell is not interpolating paths into program source
  # (a path containing a quote used to be enough to break it).

  # An agent that died early -- auth failure, immediate crash -- leaves a trajectory
  # of one or two steps whose last message carries the reason. A healthy run has
  # hundreds of steps, so the length test is what separates the two.
  agent_error() {  # $1 = trajectory.json, $2 = max chars to report
    jq -r --argjson n "$2" '
      .steps as $s
      | if ($s|length) > 0 and ($s|length) <= 2 then ($s[-1].message // "") else "" end
      | if (test("401") or (ascii_downcase | test("error"))) then .[0:$n] else empty end
    ' "$1" 2>/dev/null
  }

  # One judge's cell in the summary: its score, ERR if it recorded an error, an
  # em dash if it produced neither. jq has no fixed-decimal format, so it returns
  # the raw number and printf rounds it.
  judge_cell() {  # $1 = metrics.json, $2 = claude|codex
    local reward
    reward=$(jq -r --arg m "$2" '.["llm_judge_" + $m + "_reward"] // empty' "$1" 2>/dev/null)
    if [ -n "$reward" ]; then
      printf '%.3f' "$reward"
    elif jq -e --arg m "$2" 'has("llm_judge_" + $m + "_error")' "$1" >/dev/null 2>&1; then
      echo "ERR"
    else
      echo "—"
    fi
  }

  # --- Summary table ---
  echo ""
  echo "============================== RESULTS SUMMARY =============================="
  printf "%-15s %-8s %-8s %-14s %-14s %-7s\n" "TASK" "TRIAL" "AGENT" "CLAUDE_JUDGE" "CODEX_JUDGE" "REWARD"
  printf "%-15s %-8s %-8s %-14s %-14s %-7s\n" "----" "-----" "-----" "------------" "-----------" "------"
  for dest in "${REORG_DIRS[@]}"; do
    t_task=$(basename "$(dirname "$(dirname "$dest")")")
    t_trial=$(basename "$dest" | grep -o 'trial[0-9]*')

    # Agent status
    agent_ok="ok"
    if [ -f "$dest/agent/trajectory.json" ]; then
      agent_err=$(agent_error "$dest/agent/trajectory.json" 60)
      if [ -n "$agent_err" ]; then
        agent_ok="FAIL"
      fi
    else
      agent_ok="?"
    fi

    # Claude judge
    claude_j="—"
    if [ -f "$dest/verifier/metrics.json" ]; then
      claude_j=$(judge_cell "$dest/verifier/metrics.json" claude)
    fi

    # Codex judge
    codex_j="—"
    if [ -f "$dest/verifier/metrics.json" ]; then
      codex_j=$(judge_cell "$dest/verifier/metrics.json" codex)
    fi

    # Reward
    reward="—"
    if [ -f "$dest/verifier/reward.txt" ]; then
      reward=$(cat "$dest/verifier/reward.txt")
    fi

    printf "%-15s %-8s %-8s %-14s %-14s %-7s\n" "$t_task" "$t_trial" "$agent_ok" "$claude_j" "$codex_j" "$reward"
  done

  # Print warnings and errors
  has_issues=false
  for dest in "${REORG_DIRS[@]}"; do
    t_task=$(basename "$(dirname "$(dirname "$dest")")")
    t_trial=$(basename "$dest" | grep -o 'trial[0-9]*')
    label="$t_task/$t_trial"

    # Agent error (auth failure or crash)
    if [ -f "$dest/agent/trajectory.json" ]; then
      agent_err=$(agent_error "$dest/agent/trajectory.json" 200)
      if [ -n "$agent_err" ]; then
        has_issues=true
        echo "ERROR $label agent: $agent_err"
      fi
    else
      has_issues=true
      echo "ERROR $label: no agent/trajectory.json"
    fi

    # Missing key agent outputs
    if [ ! -f "$dest/verifier/snapshot/converted_data.pkl" ] && [ ! -f "$dest/verifier/snapshot/convert_data.py" ]; then
      has_issues=true
      echo "WARN  $label: agent produced no convert_data.py or converted_data.pkl"
    fi

    # Missing metrics.json
    if [ ! -f "$dest/verifier/metrics.json" ]; then
      has_issues=true
      echo "ERROR $label: no metrics.json"
    else
      # Check for judge errors or missing rewards
      # Captured, not piped: `... | while read` runs the loop in a SUBSHELL, so
      # the has_issues=true inside it was discarded and a judge failure never
      # reached the "No errors detected." decision below.
      # NB: --arg trial_label, not --arg label -- `label` is a jq keyword
      # (label $out | break) and shadowing it is a compile error.
      judge_issues=$(jq -r --arg trial_label "$label" '
        ["claude", "codex"][] as $m
        | (.["llm_judge_" + $m + "_error"]) as $err
        | (.["llm_judge_" + $m + "_reward"]) as $reward
        | if ($err != null and $err != "") then
            "ERROR \($trial_label) \($m) judge: \($err[0:200])"
          elif $reward == null then
            "WARN  \($trial_label) \($m) judge: no reward produced"
          else empty end
      ' "$dest/verifier/metrics.json" 2>/dev/null)
      if [ -n "$judge_issues" ]; then
        has_issues=true
        echo "$judge_issues"
      fi
    fi

    # Check for permission errors in judge logs (e.g. NFS issues)
    for model in claude codex; do
      logfile="$dest/verifier/judge/$model/judge_log.txt"
      if [ -f "$logfile" ]; then
        if grep -q 'EACCES\|permission denied\|Stale file handle' "$logfile" 2>/dev/null; then
          has_issues=true
          echo "WARN  $label $model judge: permission errors reading files (NFS issue?)"
        fi
      fi
    done
  done

  if [ "$has_issues" = false ]; then
    echo ""
    echo "No errors detected."
  fi
  echo "============================================================================="
fi

# Exit with harbor's status so a batch scheduler sees a failed run as failed.
exit "${HARBOR_RC:-0}"
