#!/bin/bash

# Enable debugging
set -x

# Set up logging
LOG_FILE="/tmp/mcp_server.log"
exec 2>> "$LOG_FILE"

echo "Starting MCP server at $(date)" >&2
echo "Working directory: $(pwd)" >&2
echo "Python version: $(python3 --version)" >&2
echo "Python path: $(which python3)" >&2

# Change to agenthub_main, derived from this script's own location
# (agenthub_main/scripts/ -> agenthub_main), never a hard-coded path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTHUB_DIR="$(dirname "$SCRIPT_DIR")"
cd "$AGENTHUB_DIR"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment" >&2
    source .venv/bin/activate
    echo "Virtual environment activated: $VIRTUAL_ENV" >&2
fi

# Set Python path
export PYTHONPATH="$AGENTHUB_DIR/src:$PYTHONPATH"

echo "PYTHONPATH: $PYTHONPATH" >&2
echo "Running MCP server..." >&2

# Run the MCP server
python3 src/minimal_mcp_server_for_test.py
