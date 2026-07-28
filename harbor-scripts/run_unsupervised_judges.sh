#!/bin/bash
#
# Run LLM judges with unsupervised instructions against an existing trial.
#
# Runs the judges with unsupervised judge_instructions.md, writing results
# under llm_judge_{model}_unsupervised_* keys in metrics.json. Existing
# (supervised) judge keys are left untouched.
#
# Usage:
#   ./run_unsupervised_judges.sh [OPTIONS] <trial_dir> [<trial_dir> ...]
#
# Options:
#   --claude-judge-only   Only run the Claude judge
#   --codex-judge-only    Only run the Codex judge
#   --dry-run             Print what would be done without modifying anything
#   (default: run both)
#
# Example:
#   ./run_unsupervised_judges.sh /path/to/jobs/sosa2024/claude/2026-03-10__19-44-11_trial1/
#   ./run_unsupervised_judges.sh --claude-judge-only /path/to/jobs/sosa2024/claude/*trial*/
#   ./run_unsupervised_judges.sh --dry-run /path/to/jobs/sosa2024/claude/*trial*/ /path/to/jobs/lee2025/claude/*trial*/

set -euo pipefail

RUN_CLAUDE_JUDGE=true
RUN_CODEX_JUDGE=true
DRY_RUN=false
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --claude-judge-only) RUN_CODEX_JUDGE=false; shift ;;
        --codex-judge-only)  RUN_CLAUDE_JUDGE=false; shift ;;
        --dry-run|-n)        DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TRIAL_DIRS=("$@")
if [ ${#TRIAL_DIRS[@]} -eq 0 ]; then
    echo "Usage: $0 [--claude-judge-only|--codex-judge-only|--dry-run] <trial_dir> [<trial_dir> ...]"
    exit 1
fi

JUDGES=""
[ "$RUN_CLAUDE_JUDGE" = true ] && JUDGES="$JUDGES claude"
[ "$RUN_CODEX_JUDGE" = true ] && JUDGES="$JUDGES codex"

TOTAL=${#TRIAL_DIRS[@]}
CURRENT=0

for TRIAL_DIR in "${TRIAL_DIRS[@]}"; do

CURRENT=$((CURRENT + 1))
if [ "$TOTAL" -gt 1 ]; then
    echo ""
    echo "======== [$CURRENT/$TOTAL] $TRIAL_DIR ========"
fi

# Infer task name from trial directory path: .../jobs/<task>/<agent>/<timestamp>/
TASK_NAME="$(basename "$(dirname "$(dirname "$TRIAL_DIR")")")"
TASK_DIR="$REPO_DIR/harbor-tasks/$TASK_NAME"
IMAGE_NAME="hb__${TASK_NAME}-reverify"

# Keep the task Dockerfile in step with the pinned versions before building, and
# fold those versions into the image tag. Without the tag, a version bump would
# silently reuse the image built from the previous Dockerfile, because the build
# below is skipped whenever the tag already exists.
VERSIONS_FILE="${VERSIONS_FILE:-$(ls -1 "$SCRIPT_DIR"/config_*.json 2>/dev/null | sort | tail -1)}"
if [ -f "$VERSIONS_FILE" ]; then
    python3 "$SCRIPT_DIR/apply_versions.py" --versions "$VERSIONS_FILE" >/dev/null \
        || { echo "Error: could not apply $VERSIONS_FILE"; exit 1; }
    read_harness() {  # $1 = tool key
        python3 -c "
import json, sys
print(json.load(open(sys.argv[1]))['tools'][sys.argv[2]]['harness_version'])" \
            "$VERSIONS_FILE" "$1"
    }
    IMAGE_TAG="claude-$(read_harness claude)_codex-$(read_harness codex)"
    IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
    echo "versions: $VERSIONS_FILE  ->  $IMAGE_NAME"
else
    echo "Warning: no config_*.json found; image tag will not record harness versions"
fi

if [ ! -d "$TASK_DIR" ]; then
    echo "Error: Task directory not found: $TASK_DIR"
    echo "Inferred task name '$TASK_NAME' from trial path. Expected jobs/<task>/<agent>/<timestamp>/"
    exit 1
fi

# Verify unsupervised instructions exist
if [ ! -f "$TASK_DIR/tests/judge_instructions_unsupervised.md" ]; then
    echo "Error: No unsupervised judge instructions at $TASK_DIR/tests/judge_instructions_unsupervised.md"
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
VERIFIER_OUT="$TRIAL_DIR/verifier"
SNAPSHOT_DIR="$VERIFIER_OUT/snapshot"
if [ ! -d "$SNAPSHOT_DIR" ]; then
    echo "Error: No snapshot directory at $SNAPSHOT_DIR"
    exit 1
fi
if [ ! -f "$VERIFIER_OUT/metrics.json" ]; then
    echo "Error: No metrics.json at $VERIFIER_OUT/metrics.json"
    exit 1
fi

# --- Dry run: print what would happen and continue ---
if [ "$DRY_RUN" = true ]; then
    echo "[dry run] Task:     $TASK_NAME"
    echo "[dry run] Task dir: $TASK_DIR"
    echo "[dry run] Trial:    $TRIAL_DIR"
    echo "[dry run] Snapshot: $SNAPSHOT_DIR"
    echo "[dry run] Data dir: $DATA_DIR"
    echo "[dry run] Image:    $IMAGE_NAME"
    echo "[dry run] Judges:  $JUDGES"
    echo ""

    echo "[dry run] Prepare test files:"
    echo "  Copy $TASK_DIR/tests/ to tmpdir"
    echo "  Copy tests/judge_instructions_unsupervised.md -> tests/judge_instructions.md"
    echo "  Remove tests/judge_instructions_unsupervised.md"
    echo "  Remove tests/reference_DECISIONS.md"
    echo "  Remove tests/reference_convert_data.py"
    echo "  Remove tests/reference_stats_full.json"
    echo ""

    echo "[dry run] docker run $IMAGE_NAME with:"
    echo "  -v $SNAPSHOT_DIR:/app"
    echo "  -v $DATA_DIR:/app/data:ro"
    echo "  -v <tmpdir>:/tests:ro"
    echo "  -v $VERIFIER_OUT:/logs/verifier"
    echo "  -v $TRIAL_DIR/agent:/logs/agent"
    if [ "$RUN_CLAUDE_JUDGE" = true ]; then
        echo "  Run Claude judge -> /logs/verifier/judge_unsupervised/claude/"
        echo "  compute_reward.py --model-name claude_unsupervised -> metrics.json llm_judge_claude_unsupervised_*"
    fi
    if [ "$RUN_CODEX_JUDGE" = true ]; then
        echo "  Run Codex judge -> /logs/verifier/judge_unsupervised/codex/"
        echo "  compute_reward.py --model-name codex_unsupervised -> metrics.json llm_judge_codex_unsupervised_*"
    fi
    continue
fi

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

# --- Prepare test files with unsupervised instructions ---
# Copy tests to tmpdir, swapping in unsupervised judge_instructions.md
TESTS_TMPDIR=$(mktemp -d)
cp -r "$TASK_DIR/tests/." "$TESTS_TMPDIR/"
# Swap: unsupervised -> judge_instructions.md
cp "$TASK_DIR/tests/judge_instructions_unsupervised.md" "$TESTS_TMPDIR/judge_instructions.md"
# Remove supervised-only files that shouldn't be available
rm -f "$TESTS_TMPDIR/judge_instructions_unsupervised.md"
rm -f "$TESTS_TMPDIR/reference_DECISIONS.md"
rm -f "$TESTS_TMPDIR/reference_convert_data.py"
rm -f "$TESTS_TMPDIR/reference_stats_full.json"
chmod -R a+rX "$TESTS_TMPDIR"
trap 'rm -rf "$TESTS_TMPDIR"' EXIT

echo "Trial:    $TRIAL_DIR"
echo "Snapshot: $SNAPSHOT_DIR"
echo "Mode:     Unsupervised judges ($JUDGES)"
echo ""

# Build the inline script for selected judges
JUDGE_SCRIPT='
export PATH="$HOME/.local/bin:$PATH"
JUDGE_DIR=/logs/verifier/judge_unsupervised

# Judge models come from /tests/versions.json, which ships in with the tests.
# Fall back to the literals so a task whose tests predate versions.json still
# runs rather than invoking the judge with an empty model flag.
read_judge_model() {  # $1 = judge key, $2 = fallback
  python3 -c "
import json, sys
try:
    print(json.load(open('"'"'/tests/versions.json'"'"'))['"'"'tools'"'"'][sys.argv[1]]['"'"'model'"'"'])
except Exception:
    print(sys.argv[2])" "$1" "$2"
}
CLAUDE_JUDGE_MODEL=$(read_judge_model claude claude-opus-4-6)
CODEX_JUDGE_MODEL=$(read_judge_model codex gpt-5.4)
echo "judge models: claude=$CLAUDE_JUDGE_MODEL codex=$CODEX_JUDGE_MODEL"
'

if [ "$RUN_CLAUDE_JUDGE" = true ]; then
    JUDGE_SCRIPT+='
CLAUDE_DIR="$JUDGE_DIR/claude"
rm -rf "$CLAUDE_DIR"
mkdir -p "$CLAUDE_DIR"

echo "=== Running Claude judge (unsupervised) ==="
cd "$CLAUDE_DIR"
# Pin the exact model, not the bare `opus` alias, which gets repointed as new
# models ship and would silently change the grading basis. Matches test.sh.
IS_SANDBOX=1 \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  claude -p "$(cat /tests/judge_instructions.md)" \
    --model "$CLAUDE_JUDGE_MODEL" \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --no-session-persistence \
    --verbose \
  2>&1 | tee judge_log.txt || true

cd /
python3 /tests/compute_reward.py \
  --eval-json "$CLAUDE_DIR/llm_judge_eval.json" \
  --model-name claude_unsupervised \
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

echo "=== Running Codex judge (unsupervised) ==="
cd "$CODEX_DIR"
codex exec "$(cat /tests/judge_instructions.md)" \
    -m "$CODEX_JUDGE_MODEL" \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --ephemeral \
    --skip-git-repo-check \
  2>&1 | tee judge_log.txt || true

cd /
python3 /tests/compute_reward.py \
  --eval-json "$CODEX_DIR/llm_judge_eval.json" \
  --model-name codex_unsupervised \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true
'
fi

JUDGE_SCRIPT+='
HOST_UID=$(stat -c "%u" /logs/verifier)
HOST_GID=$(stat -c "%g" /logs/verifier)
chown -R "$HOST_UID:$HOST_GID" /logs/verifier/ 2>/dev/null || true
echo "=== Unsupervised judge rerun complete ==="
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

# --- Verify judges produced output ---
JUDGE_FAILED=false
if [ "$RUN_CLAUDE_JUDGE" = true ]; then
    CLAUDE_EVAL="$VERIFIER_OUT/judge_unsupervised/claude/llm_judge_eval.json"
    if [ ! -f "$CLAUDE_EVAL" ]; then
        echo "Error: Claude judge did not produce $CLAUDE_EVAL"
        echo "Check $VERIFIER_OUT/judge_unsupervised/claude/judge_log.txt for details"
        JUDGE_FAILED=true
    fi
fi
if [ "$RUN_CODEX_JUDGE" = true ]; then
    CODEX_EVAL="$VERIFIER_OUT/judge_unsupervised/codex/llm_judge_eval.json"
    if [ ! -f "$CODEX_EVAL" ]; then
        echo "Error: Codex judge did not produce $CODEX_EVAL"
        echo "Check $VERIFIER_OUT/judge_unsupervised/codex/judge_log.txt for details"
        JUDGE_FAILED=true
    fi
fi
if [ "$JUDGE_FAILED" = true ]; then
    echo "Aborting due to judge failure."
    exit 1
fi

echo ""
echo "Unsupervised judge output: $VERIFIER_OUT/judge_unsupervised/"
if [ -f "$VERIFIER_OUT/metrics.json" ]; then
    echo "Scores:"
    python3 -c "
import json
d = json.load(open('$VERIFIER_OUT/metrics.json'))
for mode in ['supervised', 'unsupervised']:
    for model in ['claude', 'codex']:
        if mode == 'supervised':
            key = f'llm_judge_{model}_reward'
        else:
            key = f'llm_judge_{model}_unsupervised_reward'
        r = d.get(key)
        err_key = key.replace('_reward', '_error')
        if r is not None:
            print(f'  {model} {mode}: {r:.3f}')
        elif err_key in d:
            print(f'  {model} {mode}: ERR')
" 2>/dev/null || true
fi

done # end loop over TRIAL_DIRS

if [ "$TOTAL" -gt 1 ]; then
    echo ""
    echo "======== Completed $TOTAL trials ========"
fi
