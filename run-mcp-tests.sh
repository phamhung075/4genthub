#!/bin/bash

# MCP Testing Script
# This script runs MCP tests with authentication bypass enabled

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

# Check backend health
curl -s http://localhost:8000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
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
echo "  docker-compose restart"
echo ""
echo "==============================================="