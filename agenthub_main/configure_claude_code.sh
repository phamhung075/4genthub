#!/bin/bash
# Configure Claude Code to use agenthub tools via bridge

echo "agenthub Claude Code Configuration Script"
echo "==========================================="
echo ""
echo "This script will help you configure Claude Code to connect to agenthub tools."
echo ""

# Detect OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    IS_WINDOWS=true
    CONFIG_DIR="$APPDATA/Claude"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    IS_WINDOWS=false
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
else
    IS_WINDOWS=false
    CONFIG_DIR="$HOME/.config/claude"
fi

echo "Detected configuration directory: $CONFIG_DIR"

# Check if Claude Code config exists
if [ ! -f "$CONFIG_DIR/claude_desktop_config.json" ]; then
    echo "Creating new Claude Code configuration..."
    mkdir -p "$CONFIG_DIR"
    echo '{}' > "$CONFIG_DIR/claude_desktop_config.json"
else
    echo "Found existing Claude Code configuration"
fi

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create configuration based on OS
if [ "$IS_WINDOWS" = true ]; then
    # Windows configuration using WSL
    cat > "$CONFIG_DIR/claude_desktop_config.json" << EOF
{
  "mcpServers": {
    "agenthub_http": {
      "command": "wsl.exe",
      "args": [
        "--cd",
        "$(wslpath -w "$SCRIPT_DIR" | sed 's/\\/\\\\/g')",
        "--exec",
        "python3",
        "src/mcp_bridge.py"
      ],
      "transport": "stdio"
    }
  }
}
EOF
else
    # Linux/Mac configuration
    cat > "$CONFIG_DIR/claude_desktop_config.json" << EOF
{
  "mcpServers": {
    "agenthub_http": {
      "command": "python3",
      "args": [
        "$SCRIPT_DIR/src/mcp_bridge.py"
      ],
      "transport": "stdio"
    }
  }
}
EOF
fi

echo ""
echo "Configuration written to: $CONFIG_DIR/claude_desktop_config.json"
echo ""
echo "IMPORTANT: Before restarting Claude Code, ensure:"
echo "1. Docker container is running: docker ps | grep agenthub-server"
echo "2. Server is healthy: curl http://localhost:8000/health"
echo ""
echo "To start the Docker container if not running:"
echo "cd $SCRIPT_DIR && docker-compose up -d"
echo ""
echo "After confirming the above:"
echo "1. Restart Claude Code completely"
echo "2. Check MCP tools are available with: mcp__agenthub_http__health_check"
echo ""
echo "Troubleshooting:"
echo "- Check bridge logs: tail -f /tmp/mcp_bridge.log"
echo "- Test bridge manually: echo '{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}},\"id\":1}' | python3 $SCRIPT_DIR/src/mcp_bridge.py"