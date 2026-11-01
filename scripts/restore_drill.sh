#!/usr/bin/env bash
# ==============================================================================
# TrustFed Disaster Recovery & Database Restore Drill
# ==============================================================================
# Usage:
#   ./scripts/restore_drill.sh
#   bash scripts/restore_drill.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================================================"
echo " Starting TrustFed Disaster Recovery & Restore Verification Drill"
echo " Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "======================================================================"

if [ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null && [ "$(python3 --version 2>&1 | grep -c 'Python 3')" -gt 0 ]; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null && [ "$(python --version 2>&1 | grep -c 'Python')" -gt 0 ]; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python interpreter not found."
    exit 1
fi

"$PYTHON_CMD" "$SCRIPT_DIR/restore_drill.py"
DRILL_EXIT_CODE=$?

if [ $DRILL_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Restore drill executed with 0 discrepancies."
    exit 0
else
    echo "[FAILED] Restore drill failed with exit code $DRILL_EXIT_CODE."
    exit $DRILL_EXIT_CODE
fi
