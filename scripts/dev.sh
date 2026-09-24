#!/usr/bin/env bash
# Run the web app locally, with every tab working (macOS / Linux / Git Bash).
#
#   bash scripts/dev.sh
#
# Starts the Python prediction service on port 8000 (the Predict tab calls it)
# and the Next.js development server on http://localhost:3000. Ctrl+C stops both.
set -e
cd "$(dirname "$0")/.."
PY="${PYTHON:-$(command -v python3 || command -v python)}"
[ -d app/node_modules ] || (cd app && npm install)
"$PY" scripts/dev_api.py &
API=$!
trap 'kill $API 2>/dev/null' EXIT
cd app && npm run dev
