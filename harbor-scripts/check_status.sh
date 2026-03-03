#!/bin/bash

JOBS_ROOT="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs"

AGENT="${1:-}"

# If agent specified, only show that agent's jobs
if [ -n "$AGENT" ]; then
  AGENTS=("$AGENT")
else
  AGENTS=($(ls "$JOBS_ROOT" 2>/dev/null))
fi

for agent in "${AGENTS[@]}"; do
  agent_dir="$JOBS_ROOT/$agent"
  [ -d "$agent_dir" ] || continue

  echo "=== Agent: $agent ==="

  for job_dir in "$agent_dir"/*/; do
    [ -d "$job_dir" ] || continue
    job_name=$(basename "$job_dir")

    # Check if job is finished
    if [ -f "$job_dir/result.json" ]; then
      n_trials=$(python3 -c "import json; d=json.load(open('$job_dir/result.json')); print(d['stats']['n_trials'])" 2>/dev/null)
      n_errors=$(python3 -c "import json; d=json.load(open('$job_dir/result.json')); print(d['stats']['n_errors'])" 2>/dev/null)
      metrics=$(python3 -c "
import json
d = json.load(open('$job_dir/result.json'))
for eval_name, eval_data in d['stats']['evals'].items():
    for m in eval_data.get('metrics', []):
        for k, v in m.items():
            print(f'{k}={v:.3f}', end=' ')
" 2>/dev/null)
      echo "  Job $job_name: FINISHED  trials=$n_trials errors=$n_errors $metrics"
    else
      echo "  Job $job_name: RUNNING"
    fi

    # Show trial details
    for trial_dir in "$job_dir"/*/; do
      [ -d "$trial_dir" ] || continue
      trial_name=$(basename "$trial_dir")
      # Skip non-trial directories
      [[ "$trial_name" == *.json || "$trial_name" == *.log ]] && continue

      if [ -f "$trial_dir/result.json" ]; then
        reward=$(python3 -c "import json; d=json.load(open('$trial_dir/result.json')); print(d.get('verifier_result',{}).get('rewards',{}).get('reward','?'))" 2>/dev/null)
        started=$(python3 -c "import json; d=json.load(open('$trial_dir/result.json')); print(d.get('started_at','?')[:19])" 2>/dev/null)
        finished=$(python3 -c "import json; d=json.load(open('$trial_dir/result.json')); print(d.get('finished_at','?')[:19])" 2>/dev/null)
        duration=$(python3 -c "
from datetime import datetime
import json
d = json.load(open('$trial_dir/result.json'))
s = datetime.fromisoformat(d['started_at'].rstrip('Z'))
f = datetime.fromisoformat(d['finished_at'].rstrip('Z'))
m = int((f-s).total_seconds() / 60)
print(f'{m}m')
" 2>/dev/null)
        echo "    $trial_name: FINISHED  reward=$reward  $started  ${duration}"
      else
        # Trial still running — figure out which phase
        phase="unknown"
        if [ -d "$trial_dir/verifier" ] && docker ps --format '{{.Names}}' 2>/dev/null | grep -qi "$(echo "$trial_name" | tr '[:upper:]' '[:lower:]')"; then
          # Container is running
          container_id=$(docker ps --format '{{.ID}} {{.Names}}' 2>/dev/null | grep -i "$(echo "$trial_name" | tr '[:upper:]' '[:lower:]')" | awk '{print $1}')
          if [ -n "$container_id" ]; then
            uptime=$(docker ps --format '{{.Status}}' --filter "id=$container_id" 2>/dev/null)
            # Check what files exist in the container to determine phase
            has_agent_log=$(docker exec "$container_id" test -s /logs/agent/claude-code.txt 2>/dev/null && echo "yes" || echo "no")
            has_reward=$(docker exec "$container_id" test -f /logs/verifier/reward.txt 2>/dev/null && echo "yes" || echo "no")
            if [ "$has_reward" = "yes" ]; then
              phase="verifier"
            elif [ "$has_agent_log" = "yes" ]; then
              phase="agent"
            else
              phase="setup"
            fi
            # Check latest output files
            latest=$(docker exec "$container_id" bash -c "ls -t /app/*.txt /app/*.pkl 2>/dev/null | head -1" 2>/dev/null)
            echo "    $trial_name: RUNNING  phase=$phase  container=$uptime  latest=$latest"
          else
            echo "    $trial_name: RUNNING  (no container found)"
          fi
        else
          echo "    $trial_name: RUNNING  (no container detected)"
        fi
      fi
    done
  done
  echo
done
