#!/bin/bash
#
# Rerun the verifier (test_outputs.py) against an existing trial's snapshot.
#
# Usage:
#   ./rerun_verifier.sh <trial_dir>
#
# The task name is inferred from the trial path: jobs/<task>/<agent>/<timestamp>/
#
# Example:
#   ./rerun_verifier.sh /path/to/jobs/sosa2024/oracle/2026-03-10__00-06-35_trial1/
#
# Requirements:
#   - The trial must have verifier/snapshot/ with converted_data.pkl
#   - The task's Docker image must be built (or will be built automatically)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TRIAL_DIR="${1:?Usage: $0 <trial_dir>}"

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

# Validate trial directory
SNAPSHOT_DIR="$TRIAL_DIR/verifier/snapshot"
if [ ! -d "$SNAPSHOT_DIR" ]; then
    echo "Error: No snapshot directory at $SNAPSHOT_DIR"
    exit 1
fi

if [ ! -f "$SNAPSHOT_DIR/converted_data.pkl" ]; then
    echo "Warning: No converted_data.pkl in snapshot. Tests requiring it will be skipped."
fi

# Build Docker image if it doesn't exist
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building Docker image $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME" "$TASK_DIR/environment"
else
    echo "Using existing Docker image $IMAGE_NAME"
fi

# Get Claude OAuth token for LLM judge
export CLAUDE_CODE_OAUTH_TOKEN=$(python3 -c "import json; d=json.load(open('/home/bransonk@hhmi.org/.claude/.credentials.json')); print(d['claudeAiOauth']['accessToken'])")

# Codex auth (uses OAuth tokens, not a plain API key)
if [ -z "${CODEX_AUTH_JSON_B64:-}" ]; then
    export CODEX_AUTH_JSON_B64=$(base64 -w0 /home/bransonk@hhmi.org/.codex/auth.json 2>/dev/null || true)
fi
if [ -z "${CODEX_AUTH_JSON_B64:-}" ]; then
    echo "Warning: Codex auth not available. Codex judge will be skipped."
fi

# Create a fresh verifier output directory for this re-run
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
    -v "$TASK_DIR/tests":/tests:ro \
    -v "$VERIFIER_OUT":/logs/verifier \
    -v "$TRIAL_DIR/agent":/logs/agent \
    -w /app \
    "$IMAGE_NAME" \
    bash /tests/test.sh

echo ""
echo "Verifier output written to: $VERIFIER_OUT"
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
