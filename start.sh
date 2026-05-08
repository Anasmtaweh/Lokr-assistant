#!/bin/bash
# start.sh — Always launch Streamlit using the venv Python to ensure all
# dependencies (pathspec, tree-sitter, chromadb, etc.) are available.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
VENV_STREAMLIT="$SCRIPT_DIR/venv/bin/streamlit"

# Verify venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[ERROR] venv not found at $SCRIPT_DIR/venv"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Verify pathspec is available in the venv
if ! "$VENV_PYTHON" -c "import pathspec" 2>/dev/null; then
    echo "[WARN] pathspec missing from venv. Installing requirements..."
    "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

echo "[START] Launching Lokr Assistant with venv Python: $VENV_PYTHON"
exec "$VENV_STREAMLIT" run "$SCRIPT_DIR/app.py" \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --browser.gatherUsageStats=false
