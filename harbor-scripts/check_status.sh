#!/bin/bash
#
# Show status of all trials in the reorganized jobs directory.
#
# Usage:
#   ./check_status.sh [task] [agent]
#
# Examples:
#   ./check_status.sh                  # all tasks, all agents
#   ./check_status.sh sosa2024         # one task, all agents
#   ./check_status.sh sosa2024 claude  # one task, one agent

JOBS_ROOT="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs"

FILTER_TASK="${1:-}"
FILTER_AGENT="${2:-}"

# Header
printf "%-12s %-8s %-28s %-6s %-6s %-7s %-8s %-14s %-14s %s\n" \
  "TASK" "AGENT" "TRIAL" "AGENT" "VERIF" "REWARD" "FILES" "CLAUDE_JUDGE" "CODEX_JUDGE" "ISSUES"
printf "%-12s %-8s %-28s %-6s %-6s %-7s %-8s %-14s %-14s %s\n" \
  "----" "-----" "-----" "-----" "-----" "------" "-----" "------------" "-----------" "------"

ISSUES_LIST=()

for task_dir in "$JOBS_ROOT"/*/; do
  [ -d "$task_dir" ] || continue
  task=$(basename "$task_dir")
  [[ "$task" == "raw" ]] && continue
  [ -n "$FILTER_TASK" ] && [ "$task" != "$FILTER_TASK" ] && continue

  for agent_dir in "$task_dir"/*/; do
    [ -d "$agent_dir" ] || continue
    agent=$(basename "$agent_dir")
    [ -n "$FILTER_AGENT" ] && [ "$agent" != "$FILTER_AGENT" ] && continue

    for trial_dir in "$agent_dir"/*/; do
      [ -d "$trial_dir" ] || continue
      trial=$(basename "$trial_dir")
      issues=""

      # --- Agent status ---
      agent_status="?"
      if [ "$agent" = "oracle" ]; then
        # Oracle agent doesn't produce trajectory.json
        agent_status="ok"
      elif [ -f "$trial_dir/agent/trajectory.json" ]; then
        agent_status=$(python3 -c "
import json
d = json.load(open('$trial_dir/agent/trajectory.json'))
steps = d.get('steps', [])
if len(steps) <= 2 and len(steps) > 0:
    msg = steps[-1].get('message', '')
    if '401' in msg or 'error' in msg.lower():
        print('FAIL')
    else:
        print('ok')
else:
    print('ok')
" 2>/dev/null || echo "?")
        if [ "$agent_status" = "FAIL" ]; then
          err_msg=$(python3 -c "
import json
d = json.load(open('$trial_dir/agent/trajectory.json'))
steps = d.get('steps', [])
if steps: print(steps[-1].get('message', '')[:120])
" 2>/dev/null)
          issues="${issues}agent_err: ${err_msg}; "
        fi
      elif [ -d "$trial_dir/agent" ]; then
        # Agent dir exists but no trajectory — might still be running
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -qi "$(echo "$trial" | head -c 20)"; then
          agent_status="RUN"
        else
          agent_status="FAIL"
          issues="${issues}no trajectory.json; "
        fi
      else
        agent_status="NONE"
        issues="${issues}no agent dir; "
      fi

      # --- Verifier status ---
      verif_status="?"
      if [ -f "$trial_dir/verifier/reward.txt" ]; then
        verif_status="ok"
      elif [ -d "$trial_dir/verifier" ]; then
        verif_status="PART"
        issues="${issues}no reward.txt; "
      else
        verif_status="NONE"
        issues="${issues}no verifier dir; "
      fi

      # --- Reward ---
      reward="—"
      [ -f "$trial_dir/verifier/reward.txt" ] && reward=$(cat "$trial_dir/verifier/reward.txt")

      # --- Files status (from metrics.json) ---
      files_status="—"
      if [ -f "$trial_dir/verifier/metrics.json" ]; then
        files_info=$(python3 -c "
import json
d = json.load(open('$trial_dir/verifier/metrics.json'))
req_missing = d.get('required_files_missing', [])
req_empty = d.get('required_files_empty', [])
all_missing = req_missing + req_empty
status = f'MISS:{len(all_missing)}' if all_missing else 'ok'
missing_str = ', '.join(all_missing)
print(f'{status};;{missing_str}')
" 2>/dev/null)
        files_status="${files_info%%;;*}"
        missing_files="${files_info#*;;}"
        if [ -n "$missing_files" ]; then
          issues="${issues}missing: ${missing_files}; "
        fi
      fi

      # --- Claude judge ---
      claude_j="—"
      if [ -f "$trial_dir/verifier/metrics.json" ]; then
        claude_j=$(python3 -c "
import json
d = json.load(open('$trial_dir/verifier/metrics.json'))
r = d.get('llm_judge_claude_reward')
e = d.get('llm_judge_claude_error', '')
if e:
    print('ERR')
elif r is not None:
    print(f'{r:.3f}')
else:
    print('NONE')
" 2>/dev/null || echo "?")
        if [ "$claude_j" = "ERR" ]; then
          err=$(python3 -c "
import json
d = json.load(open('$trial_dir/verifier/metrics.json'))
print(d.get('llm_judge_claude_error', '')[:100])
" 2>/dev/null)
          issues="${issues}claude_judge: ${err}; "
        elif [ "$claude_j" = "NONE" ]; then
          issues="${issues}claude_judge: not run; "
        fi
      fi

      # --- Codex judge ---
      codex_j="—"
      if [ -f "$trial_dir/verifier/metrics.json" ]; then
        codex_j=$(python3 -c "
import json
d = json.load(open('$trial_dir/verifier/metrics.json'))
r = d.get('llm_judge_codex_reward')
e = d.get('llm_judge_codex_error', '')
if e:
    print('ERR')
elif r is not None:
    print(f'{r:.3f}')
else:
    print('NONE')
" 2>/dev/null || echo "?")
        if [ "$codex_j" = "ERR" ]; then
          err=$(python3 -c "
import json
d = json.load(open('$trial_dir/verifier/metrics.json'))
print(d.get('llm_judge_codex_error', '')[:100])
" 2>/dev/null)
          issues="${issues}codex_judge: ${err}; "
        elif [ "$codex_j" = "NONE" ]; then
          issues="${issues}codex_judge: not run; "
        fi
      fi

      # --- Print row ---
      flag=""
      [ -n "$issues" ] && flag="*"
      printf "%-12s %-8s %-28s %-6s %-6s %-7s %-8s %-14s %-14s %s\n" \
        "$task" "$agent" "$trial" "$agent_status" "$verif_status" "$reward" "$files_status" "$claude_j" "$codex_j" "$flag"

      if [ -n "$issues" ]; then
        ISSUES_LIST+=("$task/$agent/$trial: $issues")
      fi
    done
  done
done

# Print issues
if [ ${#ISSUES_LIST[@]} -gt 0 ]; then
  echo ""
  echo "============================== ISSUES =============================="
  for issue in "${ISSUES_LIST[@]}"; do
    echo "  $issue"
  done
fi
