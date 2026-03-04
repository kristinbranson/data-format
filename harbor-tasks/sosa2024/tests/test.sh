#!/bin/bash

# Use this file to install test dependencies and run the tests.
# It will be copied to /tests/test.sh and run from the working directory.

echo "=== [1/7] Installing test dependencies ==="
pip install pytest==8.4.1 pytest-json-ctrf==0.3.5

mkdir -p /logs/verifier

echo "=== [2/7] Snapshotting agent-created files ==="
# Snapshot agent-created files (excluding large binaries)
cd /app && comm -23 <(find . -not -path './data/*' -type f | sort) <(sort .manifest | sed 's|^/app|.|') | while read f; do
  mkdir -p "/logs/verifier/snapshot/$(dirname "$f")" && cp "$f" "/logs/verifier/snapshot/$f"
done
cd /

echo "=== [3/7] Running pytest ==="
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

echo "=== [4/7] Setting up judge user and CLI tools ==="
# Claude CLI refuses --permission-mode bypassPermissions as root.
useradd -m -s /bin/bash judge 2>/dev/null || true
install -m 755 "$(which claude)" /usr/local/bin/claude 2>/dev/null || true
install -m 755 "$(which codex)" /usr/local/bin/codex 2>/dev/null || true
chmod -R o+rX /app /logs /tests 2>/dev/null || true

# --- Claude Opus 4.6 ---
echo "=== [5/7] Claude judge: documenting decisions (step 1/2) ==="
CLAUDE_DIR="$JUDGE_DIR/claude"
mkdir -p "$CLAUDE_DIR"
chown -R judge:judge "$CLAUDE_DIR"

cd "$CLAUDE_DIR"
runuser -u judge -- env \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  HOME=/home/judge \
  claude -p "$(cat /tests/decisions_instructions.md)" \
    --model opus \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --no-session-persistence \
    --verbose \
  2>&1 | tee judge_step1_log.txt || true

echo "=== [5/7] Claude judge: evaluating decisions (step 2/2) ==="
EVAL_PROMPT="$(sed 's|/logs/verifier/judge/DECISIONS.md|/logs/verifier/judge/claude/DECISIONS.md|g' /tests/eval_instructions.md)"
runuser -u judge -- env \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  HOME=/home/judge \
  claude -p "$EVAL_PROMPT" \
    --model opus \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --no-session-persistence \
    --verbose \
  2>&1 | tee judge_step2_log.txt || true

cd /

# --- Codex GPT 5.3 ---
echo "=== [6/7] Codex judge: documenting decisions (step 1/2) ==="
CODEX_DIR="$JUDGE_DIR/codex"
mkdir -p "$CODEX_DIR"
chown -R judge:judge "$CODEX_DIR"

cd "$CODEX_DIR"
runuser -u judge -- env \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  HOME=/home/judge \
  codex exec "$(cat /tests/decisions_instructions.md)" \
    -m gpt-5.3-codex \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --ephemeral \
    --skip-git-repo-check \
  2>&1 | tee judge_step1_log.txt || true

echo "=== [6/7] Codex judge: evaluating decisions (step 2/2) ==="
EVAL_PROMPT="$(sed 's|/logs/verifier/judge/DECISIONS.md|/logs/verifier/judge/codex/DECISIONS.md|g' /tests/eval_instructions.md)"
runuser -u judge -- env \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  HOME=/home/judge \
  codex exec "$EVAL_PROMPT" \
    -m gpt-5.3-codex \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --ephemeral \
    --skip-git-repo-check \
  2>&1 | tee judge_step2_log.txt || true

cd /

# --- Compute rewards and merge into metrics.json ---
echo "=== [7/7] Computing rewards ==="
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
