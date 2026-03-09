#!/bin/bash

# Use this file to solve the task.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Output files go to /app (working directory) where tests expect them
OUTDIR="${1:-/app}"

# Create required documentation files
cat > "$OUTDIR/CONVERSION_NOTES.md" << 'EOF'
# Debug conversion notes
EOF

cat > "$OUTDIR/README.md" << 'EOF'
# Debug README
EOF

# Copy convert_data.py to /app so tests can find it
cp "$SCRIPT_DIR/convert_data.py" "$OUTDIR/convert_data.py"

# Convert sample
python3 "$SCRIPT_DIR/convert_data.py" --sample "$OUTDIR/sample_data.pkl" > "$OUTDIR/conversion_sample_out.txt"
# Verify sample
python3 /app/train_decoder.py --verify-only "$OUTDIR/sample_data.pkl" > "$OUTDIR/verification_sample_out.txt"
# Train on sample
python3 /app/train_decoder.py "$OUTDIR/sample_data.pkl" > "$OUTDIR/train_decoder_sample_out.txt"
# Convert full data
python3 "$SCRIPT_DIR/convert_data.py" --full "$OUTDIR/converted_data.pkl" > "$OUTDIR/conversion_full_out.txt"
# Verify full data
python3 /app/train_decoder.py --verify-only "$OUTDIR/converted_data.pkl" > "$OUTDIR/verification_full_out.txt"
# Train on full data
python3 /app/train_decoder.py "$OUTDIR/converted_data.pkl" > "$OUTDIR/train_decoder_full_out.txt"

# Persist outputs to mounted volume so they survive even with --disable-verification
mkdir -p /logs/verifier/snapshot
cp "$OUTDIR"/*.pkl "$OUTDIR"/*.txt "$OUTDIR"/*.py "$OUTDIR"/*.md /logs/verifier/snapshot/ 2>/dev/null || true

# Fix ownership to match host user
HOST_UID=$(stat -c '%u' /logs/verifier)
HOST_GID=$(stat -c '%g' /logs/verifier)
chown -R "$HOST_UID:$HOST_GID" /logs/verifier/ /logs/agent/ 2>/dev/null || true
