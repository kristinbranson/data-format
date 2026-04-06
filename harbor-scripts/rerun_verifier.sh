#!/bin/bash
#
# Rerun the verifier (test_outputs.py) against an existing trial's snapshot.
#
# Usage:
#   ./rerun_verifier.sh [OPTIONS] <trial_dir>
#
# Options:
#   --claude-judge-only   Only rerun the Claude judge and update metrics.json
#   --codex-judge-only    Only rerun the Codex judge and update metrics.json
#   --judges-only         Rerun both judges and update metrics.json
#   --verifier-dir DIR    Use DIR as the verifier directory (default: newest
#                         verifier_rerun_* if one exists, otherwise verifier/)
#
# The task name is inferred from the trial path: jobs/<task>/<agent>/<timestamp>/
#
# Example:
#   ./rerun_verifier.sh /path/to/jobs/sosa2024/oracle/2026-03-10__00-06-35_trial1/
#   ./rerun_verifier.sh --claude-judge-only /path/to/jobs/lee2025/claude/2026-03-10__11-18-23_trial3/
#   ./rerun_verifier.sh --codex-judge-only /path/to/jobs/sosa2024/claude/2026-03-10__19-44-11_trial1/
#
# Requirements:
#   - The trial must have verifier/snapshot/ with converted_data.pkl
#   - The task's Docker image must be built (or will be built automatically)

set -euo pipefail

RUN_CLAUDE_JUDGE=false
RUN_CODEX_JUDGE=false
JUDGE_ONLY=false
VERIFIER_DIR_OVERRIDE=""
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --claude-judge-only) RUN_CLAUDE_JUDGE=true; JUDGE_ONLY=true; shift ;;
        --codex-judge-only)  RUN_CODEX_JUDGE=true;  JUDGE_ONLY=true; shift ;;
        --judges-only)       RUN_CLAUDE_JUDGE=true; RUN_CODEX_JUDGE=true; JUDGE_ONLY=true; shift ;;
        --verifier-dir)      VERIFIER_DIR_OVERRIDE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TRIAL_DIR="${1:?Usage: $0 [--claude-judge-only|--codex-judge-only|--judges-only] <trial_dir>}"

# Infer task name from trial directory path: .../jobs/<task>/<agent>/<timestamp>/
TASK_NAME="$(basename "$(dirname "$(dirname "$TRIAL_DIR")")")"
TASK_DIR="$REPO_DIR/harbor-tasks/$TASK_NAME"
IMAGE_NAME="hb__${TASK_NAME}-reverify"

if [ ! -d "$TASK_DIR" ]; then
    echo "Error: Task directory not found: $TASK_DIR"
    echo "Inferred task name '$TASK_NAME' from trial path. Expected jobs/<task>/<agent>/<timestamp>/"
    exit 1
fi

# Read data directory from docker-compose.yaml (the host path mounted to /app/data)
COMPOSE="$TASK_DIR/environment/docker-compose.yaml"
DATA_DIR=$(grep ':/app/data' "$COMPOSE" | sed 's|.*- ||; s|:/app/data.*||; s|^ *||')
if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Data directory not found: $DATA_DIR (from $COMPOSE)"
    exit 1
fi

# Snapshot dir is resolved after we know which verifier dir to use (see below).
# Default to verifier/snapshot; overridden for judge-only mode targeting a rerun dir.

# Build Docker image if it doesn't exist
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building Docker image $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME" "$TASK_DIR/environment"
else
    echo "Using existing Docker image $IMAGE_NAME"
fi

# Get Claude OAuth token for LLM judge
export CLAUDE_CODE_OAUTH_TOKEN=$(python3 -c "import json; d=json.load(open('$HOME/.claude/.credentials.json')); print(d['claudeAiOauth']['accessToken'])")

# Codex auth (uses OAuth tokens, not a plain API key)
if [ -z "${CODEX_AUTH_JSON_B64:-}" ]; then
    export CODEX_AUTH_JSON_B64=$(base64 -w0 $HOME/.codex/auth.json 2>/dev/null || true)
fi
if [ -z "${CODEX_AUTH_JSON_B64:-}" ]; then
    echo "Warning: Codex auth not available. Codex judge will be skipped."
fi

# Harbor copies test files into the container (upload_dir) rather than bind-mounting.
# NFS-mounted paths lose permissions when accessed by non-host users inside Docker.
# Replicate Harbor's behavior by copying tests to a local tmpdir before mounting.
TESTS_TMPDIR=$(mktemp -d)
cp -r "$TASK_DIR/tests/." "$TESTS_TMPDIR/"
chmod -R a+rX "$TESTS_TMPDIR"
trap 'rm -rf "$TESTS_TMPDIR"' EXIT

if [ "$JUDGE_ONLY" = true ]; then
    if [ -n "$VERIFIER_DIR_OVERRIDE" ]; then
        VERIFIER_OUT="$VERIFIER_DIR_OVERRIDE"
    else
        # Default: newest verifier_rerun_* if one exists, otherwise verifier/
        NEWEST_RERUN=$(ls -dt "$TRIAL_DIR"/verifier_rerun_*/ 2>/dev/null | head -1)
        if [ -n "$NEWEST_RERUN" ]; then
            VERIFIER_OUT="${NEWEST_RERUN%/}"
            echo "Found unmerged rerun: $VERIFIER_OUT"
        else
            VERIFIER_OUT="$TRIAL_DIR/verifier"
        fi
    fi
    if [ ! -d "$VERIFIER_OUT" ]; then
        echo "Error: No verifier directory at $VERIFIER_OUT"
        exit 1
    fi

    # Resolve snapshot dir: use the target verifier's snapshot, fall back to verifier/snapshot
    SNAPSHOT_DIR="$VERIFIER_OUT/snapshot"
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        SNAPSHOT_DIR="$TRIAL_DIR/verifier/snapshot"
    fi
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        echo "Error: No snapshot directory found"
        exit 1
    fi

    JUDGES=""
    [ "$RUN_CLAUDE_JUDGE" = true ] && JUDGES="$JUDGES claude"
    [ "$RUN_CODEX_JUDGE" = true ] && JUDGES="$JUDGES codex"

    echo "Trial:    $TRIAL_DIR"
    echo "Snapshot: $SNAPSHOT_DIR"
    echo "Mode:     Judge only ($JUDGES) — updating existing verifier/"
    echo ""

    # Build the inline script for selected judges
    JUDGE_SCRIPT='
export PATH="$HOME/.local/bin:$PATH"
JUDGE_DIR=/logs/verifier/judge
'

    if [ "$RUN_CLAUDE_JUDGE" = true ]; then
        JUDGE_SCRIPT+='
CLAUDE_DIR="$JUDGE_DIR/claude"
rm -rf "$CLAUDE_DIR"
mkdir -p "$CLAUDE_DIR"

echo "=== Running Claude judge ==="
cd "$CLAUDE_DIR"
# IS_SANDBOX=1 allows claude to run --permission-mode bypassPermissions as root,
# matching how Harbor runs the claude agent.
IS_SANDBOX=1 \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  claude -p "$(cat /tests/judge_instructions.md)" \
    --model opus \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --no-session-persistence \
    --verbose \
  2>&1 | tee judge_log.txt || true

cd /
python3 /tests/compute_reward.py \
  --eval-json "$CLAUDE_DIR/llm_judge_eval.json" \
  --model-name claude \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true
'
    fi

    if [ "$RUN_CODEX_JUDGE" = true ]; then
        JUDGE_SCRIPT+='
CODEX_DIR="$JUDGE_DIR/codex"
rm -rf "$CODEX_DIR"
mkdir -p "$CODEX_DIR"

if [ -n "${CODEX_AUTH_JSON_B64:-}" ]; then
  mkdir -p /root/.codex
  echo "$CODEX_AUTH_JSON_B64" | base64 -d > /root/.codex/auth.json
fi

echo "=== Running Codex judge ==="
cd "$CODEX_DIR"
codex exec "$(cat /tests/judge_instructions.md)" \
    -m gpt-5.4 \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --ephemeral \
    --skip-git-repo-check \
  2>&1 | tee judge_log.txt || true

cd /
python3 /tests/compute_reward.py \
  --eval-json "$CODEX_DIR/llm_judge_eval.json" \
  --model-name codex \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true
'
    fi

    JUDGE_SCRIPT+='
HOST_UID=$(stat -c "%u" /logs/verifier)
HOST_GID=$(stat -c "%g" /logs/verifier)
chown -R "$HOST_UID:$HOST_GID" /logs/verifier/ 2>/dev/null || true
echo "=== Judge rerun complete ==="
'

    docker run --rm \
        --gpus all \
        -e CLAUDE_CODE_OAUTH_TOKEN \
        -e CODEX_AUTH_JSON_B64 \
        -v "$SNAPSHOT_DIR":/app \
        -v "$DATA_DIR":/app/data:ro \
        -v "$TESTS_TMPDIR":/tests:ro \
        -v "$VERIFIER_OUT":/logs/verifier \
        -v "$TRIAL_DIR/agent":/logs/agent \
        -w /app \
        "$IMAGE_NAME" \
        bash -c "$JUDGE_SCRIPT"
else
    # Full verifier rerun
    SNAPSHOT_DIR="$TRIAL_DIR/verifier/snapshot"
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        echo "Error: No snapshot directory at $SNAPSHOT_DIR"
        exit 1
    fi
    if [ ! -f "$SNAPSHOT_DIR/converted_data.pkl" ]; then
        echo "Warning: No converted_data.pkl in snapshot. Tests requiring it will be skipped."
    fi
    VERIFIER_OUT="$TRIAL_DIR/verifier_rerun_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$VERIFIER_OUT"

    echo "Trial:    $TRIAL_DIR"
    echo "Snapshot: $SNAPSHOT_DIR"
    echo "Output:   $VERIFIER_OUT"
    echo ""

    # Run test.sh inside the container
    # Mount layout matches Harbor:
    #   - snapshot -> /app (the agent's working directory)
    #   - data -> /app/data (the source data)
    #   - tests -> /tests
    #   - verifier output -> /logs/verifier
    #   - agent logs -> /logs/agent (for chown)
    # Claude and Codex CLIs are pre-installed in the Docker image.
    docker run --rm \
        --gpus all \
        -e CLAUDE_CODE_OAUTH_TOKEN \
        -e CODEX_AUTH_JSON_B64 \
        -v "$SNAPSHOT_DIR":/app \
        -v "$DATA_DIR":/app/data:ro \
        -v "$TESTS_TMPDIR":/tests:ro \
        -v "$VERIFIER_OUT":/logs/verifier \
        -v "$TRIAL_DIR/agent":/logs/agent \
        -w /app \
        "$IMAGE_NAME" \
        bash /tests/test.sh
fi

echo ""
echo "Verifier output: $VERIFIER_OUT"
echo "Reward: $(cat "$VERIFIER_OUT/reward.txt" 2>/dev/null || echo 'N/A')"
if [ -f "$VERIFIER_OUT/metrics.json" ]; then
    echo "Judge:  $(python3 -c "
import json
d = json.load(open('$VERIFIER_OUT/metrics.json'))
parts = []
for model in ['claude', 'codex']:
    r = d.get(f'llm_judge_{model}_reward')
    if r is not None:
        parts.append(f'{model}={r:.3f}')
    elif f'llm_judge_{model}_error' in d:
        parts.append(f'{model}=ERR')
print(', '.join(parts) if parts else 'N/A')
" 2>/dev/null || echo 'N/A')"
fi
