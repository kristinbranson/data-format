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
  REORG_DIRS=()
  for trial_dir in "$LATEST_JOB"/*__*/; do
    [ -d "$trial_dir" ] || continue
    task_name=$(basename "$trial_dir" | sed 's/__[^_]*$//')
    task_trial_num[$task_name]=$(( ${task_trial_num[$task_name]:-0} + 1 ))
    dest="$REORG_BASE/$task_name/$AGENT/${TIMESTAMP}_trial${task_trial_num[$task_name]}"
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
