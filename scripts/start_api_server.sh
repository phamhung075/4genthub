#!/bin/bash

echo "🌐 Starting agenthub API Server (with WebSocket support)"
echo "========================================"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment from .env.dev
if [[ -f "${PROJECT_ROOT}/.env.dev" ]]; then
    echo "📄 Loading environment from .env.dev..."
    set -a
    source "${PROJECT_ROOT}/.env.dev"
    set +a
    echo "✅ Environment loaded"
else
    echo "⚠️ Warning: .env.dev not found at ${PROJECT_ROOT}/.env.dev"
fi

# Set defaults for missing Supabase vars (using dummy values since we're not using Supabase)
export SUPABASE_URL="${SUPABASE_URL:-https://dummy.supabase.co}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-dummy-key}"

# Change to the backend directory
cd "${PROJECT_ROOT}/agenthub_main"

# Ensure we're in development mode
export ENV=development
export AUTH_API_HOST="0.0.0.0"
export AUTH_API_PORT="8001"

# Start the API server with WebSocket support
echo "🔄 Starting API server on port 8001..."
if [[ -f ".venv/bin/python" ]]; then
    echo "Using virtual environment Python"
    cd src && ../.venv/bin/python -m fastmcp.auth.api_server
else
    echo "Using system Python"
    cd src && python -m fastmcp.auth.api_server
fi