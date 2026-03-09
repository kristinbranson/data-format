#!/bin/bash

# Use this file to install test dependencies and run the tests.
# It will be copied to /tests/test.sh and run from the working directory.

echo "=== [1/6] Installing test dependencies ==="
pip install pytest==8.4.1 pytest-json-ctrf==0.3.5

mkdir -p /logs/verifier

# Fix permissions on agent logs — Claude Code creates session files with restrictive
# permissions (0604) that block Harbor's post-processing trajectory conversion.
chmod -R a+rX /logs/agent/ 2>/dev/null || true

echo "=== [2/6] Snapshotting agent-created files ==="
# Snapshot agent-created files (excluding large binaries)
cd /app && comm -23 <(find . -not -path './data/*' -type f | sort) <(sort .manifest | sed 's|^/app|.|') | while read f; do
  mkdir -p "/logs/verifier/snapshot/$(dirname "$f")" && cp "$f" "/logs/verifier/snapshot/$f"
done
cd /

echo "=== [3/6] Running pytest ==="
# CTRF produces a standard test report in JSON format which is useful for logging.
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

# --- LLM Judge Evaluation ---
export PATH="$HOME/.local/bin:$PATH"
JUDGE_DIR=/logs/verifier/judge
mkdir -p "$JUDGE_DIR"

echo "=== [4/6] Setting up judge user and CLI tools ==="
# Install CLIs if not already present (Harbor only pre-installs them in the agent container)
apt-get update -qq && apt-get install -y -qq curl >/dev/null 2>&1 || true
if ! command -v claude &>/dev/null; then
  echo "Installing Claude CLI..."
  curl -fsSL https://claude.ai/install.sh | bash 2>&1 || true
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v codex &>/dev/null; then
  echo "Installing Codex CLI..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash 2>&1
  export NVM_DIR="$HOME/.nvm"
  \. "$NVM_DIR/nvm.sh" || true
  nvm install 22 >/dev/null 2>&1
  npm install -g @openai/codex@latest >/dev/null 2>&1
fi
# Claude CLI refuses --permission-mode bypassPermissions as root.
# Create a non-root user for claude only; codex runs fine as root.
useradd -m -s /bin/bash judge 2>/dev/null || true
install -m 755 "$(which claude)" /usr/local/bin/claude 2>/dev/null || true
chmod -R o+rX /app /logs /tests 2>/dev/null || true

# --- Claude Opus 4.6 ---
echo "=== [5/6] Claude judge ==="
CLAUDE_DIR="$JUDGE_DIR/claude"
mkdir -p "$CLAUDE_DIR"
chown -R judge:judge "$CLAUDE_DIR"

cd "$CLAUDE_DIR"
runuser -u judge -- env \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  HOME=/home/judge \
  claude -p "$(cat /tests/judge_instructions.md)" \
    --model opus \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --no-session-persistence \
    --verbose \
  2>&1 | tee judge_log.txt || true

cd /

# --- Codex GPT 5.3 ---
echo "=== [6/6] Codex judge ==="
CODEX_DIR="$JUDGE_DIR/codex"
mkdir -p "$CODEX_DIR"

# Reconstruct codex auth.json from base64-encoded env var (codex uses OAuth, not API key)
if [ -n "${CODEX_AUTH_JSON_B64:-}" ]; then
  mkdir -p /root/.codex
  echo "$CODEX_AUTH_JSON_B64" | base64 -d > /root/.codex/auth.json
fi

cd "$CODEX_DIR"
codex exec "$(cat /tests/judge_instructions.md)" \
    -m gpt-5.3-codex \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --ephemeral \
    --skip-git-repo-check \
  2>&1 | tee judge_log.txt || true

cd /

# --- Compute rewards and merge into metrics.json ---
echo "=== Computing rewards ==="
python3 /tests/compute_reward.py \
  --eval-json "$CLAUDE_DIR/llm_judge_eval.json" \
  --model-name claude \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true

python3 /tests/compute_reward.py \
  --eval-json "$CODEX_DIR/llm_judge_eval.json" \
  --model-name codex \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true

# Fix ownership of all log files to match host user
HOST_UID=$(stat -c '%u' /logs/verifier)
HOST_GID=$(stat -c '%g' /logs/verifier)
chown -R "$HOST_UID:$HOST_GID" /logs/verifier/ /logs/agent/ 2>/dev/null || true
echo "=== Verification complete ==="
