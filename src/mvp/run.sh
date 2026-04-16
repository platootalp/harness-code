#!/bin/bash
# Quick start script for MVP AI CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Show config
echo "=== MVP AI CLI Configuration ==="
echo "ANTHROPIC_BASE_URL: ${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
echo "ANTHROPIC_MODEL: ${ANTHROPIC_MODEL:-claude-sonnet-4-20250514}"
echo "API_TIMEOUT_MS: ${API_TIMEOUT_MS:-300000}"
echo "================================"

# Install dependencies if needed
if ! pip3 show src-mvp &> /dev/null; then
    echo "Installing dependencies..."
    pip3 install --break-system-packages -e . 2>/dev/null || pip3 install --user -e .
fi

# Run REPL
echo "Starting MVP AI CLI..."
PYTHONPATH="$PROJECT_DIR" python3 -m src_mvp.main "$@"
