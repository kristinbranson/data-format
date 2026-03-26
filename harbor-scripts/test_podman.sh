#!/bin/bash
# Test podman-compose the way harbor runs it, without waiting for a full trial.
#
# Usage:
#   ./harbor-scripts/test_podman.sh <task_name> [gpu_device]
#
# Examples:
#   ./harbor-scripts/test_podman.sh mouseland
#   ./harbor-scripts/test_podman.sh mouseland nvidia.com/gpu=0

set -euo pipefail

TASK="${1:?Usage: $0 <task_name> [gpu_device]}"
GPU_DEVICE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HARBOR_COMPOSE="$HOME/codepacks/harbor-kai/src/harbor/environments/docker"
TASK_DIR="$REPO_DIR/harbor-tasks/$TASK/environment"

mkdir -p /tmp/test-verifier /tmp/test-agent /tmp/test-artifacts

COMPOSE_FILES=(
  -f "$HARBOR_COMPOSE/docker-compose-base.yaml"
  -f "$HARBOR_COMPOSE/docker-compose-build.yaml"
  -f "$TASK_DIR/docker-compose.yaml"
)

if [ -n "$GPU_DEVICE" ]; then
  GPU_OVERRIDE=$(mktemp /tmp/harbor-gpu-override-XXXX.yaml)
  cat > "$GPU_OVERRIDE" <<EOF
services:
  main:
    devices:
      - $GPU_DEVICE
EOF
  COMPOSE_FILES+=(-f "$GPU_OVERRIDE")
  trap "rm -f '$GPU_OVERRIDE'" EXIT
fi

echo "Testing podman-compose up -d for task: $TASK"
echo "Compose files: ${COMPOSE_FILES[*]}"
echo ""

MAIN_IMAGE_NAME="hb__${TASK}" \
CONTEXT_DIR="$TASK_DIR" \
CPUS=16 \
MEMORY=65536m \
HOST_VERIFIER_LOGS_PATH=/tmp/test-verifier \
HOST_AGENT_LOGS_PATH=/tmp/test-agent \
HOST_ARTIFACTS_PATH=/tmp/test-artifacts \
ENV_VERIFIER_LOGS_PATH=/logs/verifier \
ENV_AGENT_LOGS_PATH=/logs/agent \
ENV_ARTIFACTS_PATH=/logs/artifacts \
podman-compose "${COMPOSE_FILES[@]}" up -d

echo ""
echo "Container started. To clean up:"
echo "  podman-compose ${COMPOSE_FILES[*]} down"
