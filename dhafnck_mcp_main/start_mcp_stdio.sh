#!/bin/bash
# Start MCP server in STDIO mode for Claude Code integration
# This runs alongside the Docker HTTP server

echo "Starting MCP STDIO server for Claude Code..."

# Change to script directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Set STDIO transport mode
export FASTMCP_TRANSPORT=stdio
export FASTMCP_LOG_LEVEL=WARNING

# Use Python from virtual environment if available
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

# Run the MCP server in STDIO mode
exec $PYTHON -m fastmcp