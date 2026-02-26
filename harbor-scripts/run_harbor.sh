#!/bin/bash

AGENT="${1:-claude}"
NTRIALS="${2:-1}"
JOBS_DIR="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/${AGENT}"

source /home/bransonk@hhmi.org/miniforge3/etc/profile.d/conda.sh
conda activate eval-data-format

case "$AGENT" in
  claude)
    export CLAUDE_CODE_OAUTH_TOKEN=$(python3 -c "import json; d=json.load(open('/home/bransonk@hhmi.org/.claude/.credentials.json')); print(d['claudeAiOauth']['accessToken'])")
    harbor run -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks -a "claude-code" -m "claude-opus-4-6" -o "$JOBS_DIR" -k "$NTRIALS" -n 1
    ;;
  codex)
    export CODEX_AUTH_JSON_B64=$(base64 -w0 /home/bransonk@hhmi.org/.codex/auth.json)
    harbor run -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks -a "codex" -m "gpt-5.2-codex" -o "$JOBS_DIR" -k "$NTRIALS" -n 1
    ;;
  oracle)
    harbor run -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks -a "oracle" -o "$JOBS_DIR" -k 1 -n 1
    ;;
  *)
    echo "Unknown agent: $AGENT"
    echo "Usage: $0 [claude|oracle|codex] [ntrials]"
    exit 1
    ;;
esac
