#!/bin/bash
# Debug OpenHarness with PyCharm via debugpy
# Usage:
#   1. PyCharm → Run → Edit Configurations → + → Python Debug Server → port 5868
#   2. Start the Debug Server in PyCharm
#   3. Run this script: ./debug_oh.sh

DEBUG_PORT=${1:-5868}
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting OpenHarness with debugpy connecting to localhost:${DEBUG_PORT}"
echo "Make sure PyCharm Python Debug Server is running on port ${DEBUG_PORT}"
echo ""

cd "$PROJECT_ROOT"
PYTHONPATH=src python -m debugpy --connect localhost:"$DEBUG_PORT" -m openharness.cli
