#!/bin/bash
#
# Development entrypoint with auto-reload on file changes
#

set -e

echo "🔧 Starting development mode with auto-reload..."

# Install watchdog if not present
if ! python -c "import watchdog" 2>/dev/null; then
    echo "📦 Installing watchdog for file monitoring..."
    pip install watchdog
fi

# Function to start the server
start_server() {
    echo "🚀 Starting FastMCP server..."
    exec python -m fastmcp "$@"
}

# Check if HOT_RELOAD is enabled
if [ "${HOT_RELOAD:-false}" = "true" ] && [ "${DEVELOPMENT_MODE:-false}" = "true" ]; then
    echo "🔥 Hot reload enabled - watching for file changes..."
    
    # Use watchmedo for auto-restart
    exec watchmedo auto-restart \
        --directory=/app/src \
        --pattern="*.py" \
        --recursive \
        --interval=${RELOAD_DELAY:-0.5} \
        --ignore-directories \
        --debug-force-polling \
        -- python -m fastmcp "$@"
else
    echo "💻 Running in standard mode..."
    start_server "$@"
fi