#!/bin/bash
set -e

# MCP Testing Script
# This script runs MCP tests with authentication bypass enabled
#
# IT REFUSES BEFORE IT WRITES. The script replaces TWO files in the repository root: `.env` is
# copied to `.env.backup`, then `.env.testing` is copied over `.env`. `.env.testing` is gitignored
# and absent unless somebody creates it, and before this precondition existed that state read as
# success: the second copy failed, nothing stopped the script, the success lines printed anyway,
# and the stack was restarted for a switch that never happened - with `.env.backup` ALREADY
# REPLACED, and that backup is a single slot rather than a history. So the precondition stands
# before the FIRST write, and `set -e` stops the run at any later failure instead of stepping over
# it, which is what makes each success line below conditional on the step it describes.
if [ ! -f .env.testing ]; then
    echo "❌ refusing: .env.testing does not exist, so there is nothing to switch to"
    echo "   .env and .env.backup are untouched. Create .env.testing (it is gitignored), or run"
    echo "   the tests without this script."
    exit 1
fi

echo "==============================================="
echo "🧪 MCP TESTING MODE INITIALIZATION"
echo "==============================================="

# Save current .env if it exists
if [ -f .env ]; then
    cp .env .env.backup
    echo "✅ Backed up current .env to .env.backup"
fi

# Switch to testing configuration
cp .env.testing .env
echo "✅ Switched to testing configuration"

# Restart backend with testing configuration
echo "🔄 Restarting backend with testing mode..."
cd docker-system
docker-compose down
docker-compose up -d
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 10

# Check backend health. Written as the condition itself rather than a following `$?`, because under
# `set -e` a failing curl would end the script before the branch that reports it.
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running in testing mode"
else
    echo "❌ Backend failed to start"
    exit 1
fi

echo ""
echo "==============================================="
echo "🚀 TESTING MODE READY"
echo "==============================================="
echo ""
echo "Testing configuration enabled:"
echo "  - AUTH_ENABLED=false"
echo "  - MCP_AUTH_MODE=testing"
echo "  - TEST_USER_ID=test-user-001"
echo ""
echo "You can now run MCP tests without authentication!"
echo ""
echo "To restore production configuration, run:"
echo "  cp .env.backup .env"
echo "  (that backup is one slot, not a history: each run of this script replaces it)"
echo "  docker-compose restart"
echo ""
echo "==============================================="
