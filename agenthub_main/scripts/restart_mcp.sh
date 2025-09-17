#!/bin/bash
echo "🔄 Restarting agenthub server..."

# Kill any existing processes
pkill -f "mcp_server.py" 2>/dev/null || true
pkill -f "agenthub" 2>/dev/null || true

# Wait a moment
sleep 2

# Set environment
cd /home/daihungpham/agentic-project
export PYTHONPATH=/home/daihungpham/agentic-project/agenthub_main/src

# Activate virtual environment and start server
source agenthub_main/.venv/bin/activate

echo "✅ Starting MCP server with 10 tools..."
python agenthub_main/src/fastmcp/task_management/interface/consolidated_mcp_server.py 