#!/bin/bash
#
# Rerun the verifier (test_outputs.py) against an existing trial's snapshot.
#
# Usage:
#   ./rerun_verifier.sh <trial_dir>
#
# Example:
#   ./rerun_verifier.sh /home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/claude/2026-02-25__00-04-07/sosa2024__stecaxC
#
# Requirements:
#   - The trial must have verifier/snapshot/ with converted_data.pkl
#   - The task's Docker image must be built (or will be built automatically)

set -euo pipefail

TASK_DIR="/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks/sosa2024"
DATA_DIR="/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/sosa2024/data"
IMAGE_NAME="hb__sosa2024-reverify"

TRIAL_DIR="${1:?Usage: $0 <trial_dir>}"

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

# OpenAI API key for Codex judge
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Warning: OPENAI_API_KEY not set. Codex judge will be skipped."
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
# Claude CLI is installed first (same as Harbor's agent setup phase),
# then test.sh runs pytest + LLM judge.
docker run --rm \
    --gpus all \
    -e CLAUDE_CODE_OAUTH_TOKEN \
    -e OPENAI_API_KEY \
    -v "$SNAPSHOT_DIR":/app \
    -v "$DATA_DIR":/app/data:ro \
    -v "$TASK_DIR/tests":/tests:ro \
    -v "$VERIFIER_OUT":/logs/verifier \
    -v "$TRIAL_DIR/agent":/logs/agent \
    -w /app \
    "$IMAGE_NAME" \
    bash -c '
      apt-get update -qq && apt-get install -y -qq curl >/dev/null 2>&1
      # Install Claude CLI
      curl -fsSL https://claude.ai/install.sh | bash
      export PATH="$HOME/.local/bin:$PATH"
      # Install Codex CLI (requires Node.js via nvm)
      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
      export NVM_DIR="$HOME/.nvm"
      \. "$NVM_DIR/nvm.sh" || true
      nvm install 22 >/dev/null 2>&1
      npm install -g @openai/codex@latest >/dev/null 2>&1
      bash /tests/test.sh
    '

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
