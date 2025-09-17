#!/bin/bash
echo "🔄 Restarting 4genthub server..."

# Kill any existing processes
pkill -f "mcp_server.py" 2>/dev/null || true
pkill -f "4genthub" 2>/dev/null || true

# Wait a moment
sleep 2

# Set environment
cd /home/daihungpham/agentic-project
export PYTHONPATH=/home/daihungpham/agentic-project/4genthub_main/src

# Activate virtual environment and start server
source 4genthub_main/.venv/bin/activate

echo "✅ Starting MCP server with 10 tools..."
python 4genthub_main/src/fastmcp/task_management/interface/consolidated_mcp_server.py 