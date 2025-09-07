#!/bin/bash

# DhafnckMCP Server Startup Script
# Ensures Docker container is running before Claude Desktop connects

set -e

echo "🚀 Starting DhafnckMCP Server..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if container exists
CONTAINER_NAME="dhafnck-mcp-server"
if ! docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container '${CONTAINER_NAME}' not found."
    echo "Please run: docker run -d --name ${CONTAINER_NAME} -p 8000-8001:8000-8001 dhafnck/mcp-server:latest"
    exit 1
fi

# Check if container is running
if ! docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "🔄 Starting container '${CONTAINER_NAME}'..."
    docker start ${CONTAINER_NAME}
    sleep 3
fi

# Wait for server to be ready
echo "⏳ Waiting for MCP server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ MCP server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ MCP server failed to start within 30 seconds"
        echo "Check container logs: docker logs ${CONTAINER_NAME}"
        exit 1
    fi
    sleep 1
done

# Show server status
echo "📊 Server Status:"
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "🎯 MCP Tools Available:"
echo "  • manage_project - Project lifecycle management"
echo "  • manage_task - Task management and tracking"
echo "  • manage_agent - Multi-agent coordination"
echo "  • manage_context - Context and knowledge management"
echo "  • manage_document - Document tracking and organization"
echo "  • call_agent - Load specialized agent configurations"
echo "  • And more..."

echo ""
echo "🔗 Connection Details:"
echo "  • HTTP Server: http://localhost:8000"
echo "  • Health Check: http://localhost:8000/health"
echo "  • MCP Endpoint: http://localhost:8000/mcp/"
echo "  • Bridge Script: src/mcp_bridge.py"

echo ""
echo "✨ Ready for Claude Desktop connection!"
echo "Use the configuration in claude_desktop_config.json" 