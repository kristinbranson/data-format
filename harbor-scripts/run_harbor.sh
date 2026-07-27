#!/bin/bash

AGENT="claude"
NTRIALS=1
NCONCURRENT=1
TASK=""
USE_PODMAN=false
USE_APIKEYS=false
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
CONFIG_FILE=""
GPUIDS=""
JOBS_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)    AGENT="$2"; shift 2 ;;
    --ntrials)  NTRIALS="$2"; shift 2 ;;
    --nconcurrent) NCONCURRENT="$2"; shift 2 ;;
    --task)     TASK="$2"; shift 2 ;;
    --config)   CONFIG_FILE="$2"; shift 2 ;;
    --gpuids)   GPUIDS="$2"; shift 2 ;;
    --jobs-dir) JOBS_ROOT="$2"; shift 2 ;;
    --podman)   USE_PODMAN=true; shift ;;
    --apikeys)  USE_APIKEYS=true; shift ;;
    --env)      ENV_FILE="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--nconcurrent N] [--task name] [--config FILE] [--gpuids LIST] [--jobs-dir DIR] [--podman] [--apikeys] [--env FILE]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--nconcurrent N] [--task name] [--config FILE] [--gpuids LIST] [--jobs-dir DIR] [--podman] [--apikeys] [--env FILE]"
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
conda activate eval-data-format-podman
if [ "$USE_PODMAN" = true ]; then
  export REGISTRY_AUTH_FILE="$HOME/.config/containers/auth.json"
  # On a batch node there is no systemd user session, so podman has nowhere to
  # put its runtime state. The runroot must be per-job: a shared one goes stale
  # across reboots ("boot ID differs"). The graphroot holds image layers and is
  # deliberately shared per node so a second job skips the ~7 min image build.
  if [ -n "${LSB_JOBID:-}" ]; then
    export XDG_RUNTIME_DIR="/scratch/$USER/podman-run-$LSB_JOBID"
    export TMPDIR="/scratch/$USER/podman-tmp-$LSB_JOBID"
    mkdir -p "$XDG_RUNTIME_DIR" "$TMPDIR" "/scratch/$USER/podman-storage"
    export CONTAINERS_RUNROOT="$XDG_RUNTIME_DIR"
    export CONTAINERS_GRAPHROOT="/scratch/$USER/podman-storage"
    trap 'rm -rf "$XDG_RUNTIME_DIR" "$TMPDIR"' EXIT
  fi
fi

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
  export CLAUDE_CODE_OAUTH_TOKEN=$(python3 -c "import json; d=json.load(open('$HOME/.claude/.credentials.json')); print(d['claudeAiOauth']['accessToken'])")
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

if [ -n "$CONFIG_FILE" ]; then
  harbor run -c "$CONFIG_FILE" -o "$JOBS_DIR" $TASK_FLAG $PODMAN_FLAG $GPU_FLAG
else
  case "$AGENT" in
    claude)
      harbor run -p "$HARBOR_TASKS" -a "claude-code" -m "claude-opus-4-6" -o "$JOBS_DIR" -k "$NTRIALS" -n "$NCONCURRENT" $TASK_FLAG $PODMAN_FLAG $GPU_FLAG
      ;;
    codex)
      harbor run -p "$HARBOR_TASKS" -a "codex" -m "gpt-5.4" -o "$JOBS_DIR" -k "$NTRIALS" -n "$NCONCURRENT" $TASK_FLAG $PODMAN_FLAG $GPU_FLAG
      ;;
    oracle)
      harbor run -p "$HARBOR_TASKS" -a "oracle" -o "$JOBS_DIR" -k 1 -n "$NCONCURRENT" $TASK_FLAG $PODMAN_FLAG $GPU_FLAG
      ;;
    *)
      echo "Unknown agent: $AGENT"
      echo "Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--task name] [--podman]"
      exit 1
      ;;
  esac
fi
HARBOR_RC=$?
[ "$HARBOR_RC" -ne 0 ] && echo "WARNING: harbor run exited $HARBOR_RC"

# Fix permissions on agent logs — Claude Code creates session files with restrictive
# permissions (0604) that block Harbor's post-processing trajectory conversion.
chmod -R a+rX "$JOBS_DIR" 2>/dev/null || true

# Post-process: reorganize outputs into jobs/<task>/<agent>/<timestamp>_trial<N>/
LATEST_JOB=$(ls -td "$JOBS_DIR"/20* 2>/dev/null | head -1)
if [ -n "$LATEST_JOB" ]; then
  TIMESTAMP=$(basename "$LATEST_JOB")
  declare -A task_trial_num
  REORG_DIRS=()
  for trial_dir in "$LATEST_JOB"/*__*/; do
    [ -d "$trial_dir" ] || continue
    task_name=$(basename "$trial_dir" | sed 's/__[^_]*$//')
    # Infer agent name: config.json (most reliable) > trajectory.json > $AGENT
    trial_agent=""
    if [ -f "$trial_dir/config.json" ]; then
      trial_agent=$(python3 -c "import json; d=json.load(open('$trial_dir/config.json')); print(d.get('agent',{}).get('name',''))" 2>/dev/null)
    fi
    if [ -z "$trial_agent" ] && [ -f "$trial_dir/agent/trajectory.json" ]; then
      trial_agent=$(python3 -c "import json; d=json.load(open('$trial_dir/agent/trajectory.json')); print(d.get('agent',{}).get('name',''))" 2>/dev/null)
    fi
    [ -z "$trial_agent" ] && trial_agent="$AGENT"
    task_trial_key="${task_name}__${trial_agent}"
    task_trial_num[$task_trial_key]=$(( ${task_trial_num[$task_trial_key]:-0} + 1 ))
    dest="$REORG_BASE/$task_name/$trial_agent/${TIMESTAMP}_trial${task_trial_num[$task_trial_key]}"
    mkdir -p "$(dirname "$dest")"
    mv "$trial_dir" "$dest"
    echo "Results moved to $dest"
    REORG_DIRS+=("$dest")
  done

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
      agent_err=$(python3 -c "
import json
d = json.load(open('$dest/agent/trajectory.json'))
steps = d.get('steps', [])
if len(steps) <= 2 and len(steps) > 0:
    msg = steps[-1].get('message','')
    if '401' in msg or 'error' in msg.lower():
        print(msg[:60])
" 2>/dev/null)
      if [ -n "$agent_err" ]; then
        agent_ok="FAIL"
      fi
    else
      agent_ok="?"
    fi

    # Claude judge
    claude_j="—"
    if [ -f "$dest/verifier/metrics.json" ]; then
      claude_j=$(python3 -c "
import json
d = json.load(open('$dest/verifier/metrics.json'))
r = d.get('llm_judge_claude_reward')
if r is not None:
    print(f'{r:.3f}')
elif 'llm_judge_claude_error' in d:
    print('ERR')
else:
    print('—')
" 2>/dev/null || echo "?")
    fi

    # Codex judge
    codex_j="—"
    if [ -f "$dest/verifier/metrics.json" ]; then
      codex_j=$(python3 -c "
import json
d = json.load(open('$dest/verifier/metrics.json'))
r = d.get('llm_judge_codex_reward')
if r is not None:
    print(f'{r:.3f}')
elif 'llm_judge_codex_error' in d:
    print('ERR')
else:
    print('—')
" 2>/dev/null || echo "?")
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
      agent_err=$(python3 -c "
import json
d = json.load(open('$dest/agent/trajectory.json'))
steps = d.get('steps', [])
if len(steps) <= 2 and len(steps) > 0:
    msg = steps[-1].get('message','')
    if '401' in msg or 'error' in msg.lower():
        print(msg[:200])
" 2>/dev/null)
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
      python3 -c "
import json
d = json.load(open('$dest/verifier/metrics.json'))
label = '$label'
for model in ['claude', 'codex']:
    e = d.get(f'llm_judge_{model}_error')
    r = d.get(f'llm_judge_{model}_reward')
    if e:
        print(f'ERROR {label} {model} judge: {e[:200]}')
    elif r is None:
        print(f'WARN  {label} {model} judge: no reward produced')
" 2>/dev/null | while read line; do
        has_issues=true
        echo "$line"
      done
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
