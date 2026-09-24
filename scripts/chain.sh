#!/usr/bin/env bash
# Wait for tuning to write its completion marker, then run everything else.
cd "$(dirname "$0")/.."
echo "[chain] waiting for tuning to finish..."
until grep -q "saved development results" logs/tuning.log 2>/dev/null; do
  sleep 20
  # If the tuning process died without the marker, stop waiting.
  if ! tasklist //FI "IMAGENAME eq python.exe" 2>/dev/null | grep -qi python; then
    echo "[chain] no python process left and no completion marker -- tuning died"
    exit 1
  fi
done
echo "[chain] tuning complete, starting downstream pipeline"
python -u scripts/finish_pipeline.py
