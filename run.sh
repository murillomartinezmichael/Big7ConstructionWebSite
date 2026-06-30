#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "[ERROR] python3 needed"; exit 1; }
echo "Serving Big7Construction at http://localhost:8080"
echo "Press Ctrl+C to stop."
python3 -m http.server 8080
