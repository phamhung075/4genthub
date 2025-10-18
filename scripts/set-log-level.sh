#!/bin/bash
# Temporary log level override for debugging WebSocket issues
# Usage: ./scripts/set-log-level.sh [debug|info|warn|error]

LOG_LEVEL=${1:-warn}

echo "🔧 Setting log level to: $LOG_LEVEL"

# Update .env.dev file
if [ -f .env.dev ]; then
    # Backup original
    cp .env.dev .env.dev.backup

    # Update or add VITE_LOG_LEVEL
    if grep -q "VITE_LOG_LEVEL" .env.dev; then
        sed -i "s/^VITE_LOG_LEVEL=.*/VITE_LOG_LEVEL=$LOG_LEVEL/" .env.dev
    else
        echo "VITE_LOG_LEVEL=$LOG_LEVEL" >> .env.dev
    fi

    echo "✅ Updated .env.dev: VITE_LOG_LEVEL=$LOG_LEVEL"
    echo "🔄 Restart frontend to apply: echo 'R' | ./docker-system/docker-menu.sh"
else
    echo "❌ .env.dev not found"
    exit 1
fi
