#!/bin/bash

# Use this file to install test dependencies and run the tests.
# It will be copied to /tests/test.sh and run from the working directory.

pip install pytest==8.4.1 pytest-json-ctrf==0.3.5

mkdir -p /logs/verifier

# Snapshot agent-created files (excluding large binaries)
cd /app && comm -23 <(find . -not -path './data/*' -type f | sort) <(sort .manifest | sed 's|^/app|.|') | while read f; do
  mkdir -p "/logs/verifier/snapshot/$(dirname "$f")" && cp "$f" "/logs/verifier/snapshot/$f"
done
cd /

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

# Step 1: Document agent decisions
cd "$JUDGE_DIR"
claude -p "$(cat /tests/decisions_instructions.md)" \
  --model sonnet \
  --permission-mode bypassPermissions \
  --output-format stream-json \
  --no-session-persistence \
  --verbose \
  2>&1 | tee judge_step1_log.txt || true

# Step 2: Evaluate decisions
claude -p "$(cat /tests/eval_instructions.md)" \
  --model sonnet \
  --permission-mode bypassPermissions \
  --output-format stream-json \
  --no-session-persistence \
  --verbose \
  2>&1 | tee judge_step2_log.txt || true
cd /

# Compute reward from llm_judge_eval.json
python3 /tests/compute_reward.py \
  --eval-json "$JUDGE_DIR/llm_judge_eval.json" \
  --pytest-reward /logs/verifier/reward.txt \
  --output /logs/verifier/reward.json 2>&1 || true

# Fix ownership of all log files to match host user
HOST_UID=$(stat -c '%u' /logs/verifier)
HOST_GID=$(stat -c '%g' /logs/verifier)
chown -R "$HOST_UID:$HOST_GID" /logs/verifier/ /logs/agent/ 2>/dev/null || true
