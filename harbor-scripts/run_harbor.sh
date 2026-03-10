#!/bin/bash

AGENT="claude"
NTRIALS=1
TASK=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)    AGENT="$2"; shift 2 ;;
    --ntrials)  NTRIALS="$2"; shift 2 ;;
    --task)     TASK="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--task name]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--task name]"
      exit 1
      ;;
  esac
done

JOBS_DIR="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/raw"
REORG_BASE="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs"

TASK_FLAG=""
if [ -n "$TASK" ]; then
  TASK_FLAG="-t $TASK"
fi

source /home/bransonk@hhmi.org/miniforge3/etc/profile.d/conda.sh
conda activate eval-data-format

# Always export CLAUDE_CODE_OAUTH_TOKEN — required by [verifier.env] in task.toml for LLM judge
export CLAUDE_CODE_OAUTH_TOKEN=$(python3 -c "import json; d=json.load(open('/home/bransonk@hhmi.org/.claude/.credentials.json')); print(d['claudeAiOauth']['accessToken'])")

# Export codex auth for LLM judge (codex uses OAuth, not a plain API key)
export CODEX_AUTH_JSON_B64=$(base64 -w0 /home/bransonk@hhmi.org/.codex/auth.json 2>/dev/null || true)

case "$AGENT" in
  claude)
    harbor run -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks -a "claude-code" -m "claude-opus-4-6" -o "$JOBS_DIR" -k "$NTRIALS" -n 1 $TASK_FLAG
    ;;
  codex)
    harbor run -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks -a "codex" -m "gpt-5.4" -o "$JOBS_DIR" -k "$NTRIALS" -n 1 $TASK_FLAG
    ;;
  oracle)
    harbor run -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks -a "oracle" -o "$JOBS_DIR" -k 1 -n 1 $TASK_FLAG
    ;;
  *)
    echo "Unknown agent: $AGENT"
    echo "Usage: $0 [--agent claude|oracle|codex] [--ntrials N] [--task name]"
    exit 1
    ;;
esac

# Fix permissions on agent logs — Claude Code creates session files with restrictive
# permissions (0604) that block Harbor's post-processing trajectory conversion.
chmod -R a+rX "$JOBS_DIR" 2>/dev/null || true

# Post-process: reorganize outputs into jobs/<task>/<agent>/<timestamp>_trial<N>/
LATEST_JOB=$(ls -td "$JOBS_DIR"/20* 2>/dev/null | head -1)
if [ -n "$LATEST_JOB" ]; then
  TIMESTAMP=$(basename "$LATEST_JOB")
  declare -A task_trial_num
  for trial_dir in "$LATEST_JOB"/*__*/; do
    [ -d "$trial_dir" ] || continue
    task_name=$(basename "$trial_dir" | sed 's/__[^_]*$//')
    task_trial_num[$task_name]=$(( ${task_trial_num[$task_name]:-0} + 1 ))
    dest="$REORG_BASE/$task_name/$AGENT/${TIMESTAMP}_trial${task_trial_num[$task_name]}"
    mkdir -p "$(dirname "$dest")"
    mv "$trial_dir" "$dest"
    echo "Results moved to $dest"
  done
fi
