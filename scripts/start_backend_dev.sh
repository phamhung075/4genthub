#!/bin/bash

# Backend Startup Script with Proper Environment Loading

echo "🚀 Starting 4genthub Backend Server"
echo "======================================"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment from .env.dev
if [[ -f "${PROJECT_ROOT}/.env.dev" ]]; then
    echo "📄 Loading environment from .env.dev..."
    export $(grep -v '^#' "${PROJECT_ROOT}/.env.dev" | xargs)
    echo "✅ Environment loaded from .env.dev"

    # Display loaded database config
    echo ""
    echo "📊 Database Configuration:"
    echo "  DATABASE_TYPE: ${DATABASE_TYPE:-NOT SET}"
    echo "  DATABASE_HOST: ${DATABASE_HOST:-NOT SET}"
    echo "  DATABASE_PORT: ${DATABASE_PORT:-NOT SET}"
    echo "  DATABASE_NAME: ${DATABASE_NAME:-NOT SET}"
    echo "  DATABASE_USER: ${DATABASE_USER:-NOT SET}"
    echo "  DATABASE_PASSWORD: $(if [[ -n "$DATABASE_PASSWORD" ]]; then echo "SET"; else echo "NOT SET"; fi)"
    echo ""
else
    echo "⚠️ Warning: .env.dev not found at ${PROJECT_ROOT}/.env.dev"
fi

# Change to the backend directory
cd "${PROJECT_ROOT}/4genthub_main"

# Ensure we're in production mode
export ENV=development
export PYTHONPATH="${PROJECT_ROOT}/4genthub_main/src:${PYTHONPATH:-}"

# Start the backend
echo "🔄 Starting MCP server..."
if [[ -f ".venv/bin/python" ]]; then
    echo "Using virtual environment Python"
    cd src && ../.venv/bin/python -m fastmcp.server.mcp_entry_point
else
    echo "Using system Python"
    cd src && python -m fastmcp.server.mcp_entry_point
fi