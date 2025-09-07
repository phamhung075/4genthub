# MCP Tools Connection Solution

## Issue Resolution
The MCP tools disconnection issue has been resolved. The tools are available through the Docker HTTP server using a bridge script.

## Date: 2025-08-25

## Root Cause
The MCP tools were previously configured in Claude Code to connect to the HTTP server, but that configuration was lost when the session reset. The Docker container runs with `FASTMCP_TRANSPORT=streamable-http` which exposes HTTP API endpoints but requires a bridge to work with Claude Code's STDIO transport.

## Solution Implemented

### 1. MCP Bridge Script
The existing `src/mcp_bridge.py` script bridges Claude Code's STDIO transport to the HTTP MCP server running in Docker. This script:
- Connects to `http://localhost:8000/mcp/` endpoint
- Translates STDIO JSON-RPC to HTTP requests
- Handles authentication transparently
- Logs all activity to `/tmp/mcp_bridge.log`

### 2. Configuration Script
Created `configure_claude_code.sh` that automatically configures Claude Code to use the bridge:
- Detects OS (Windows/WSL, Mac, Linux)
- Creates proper configuration in Claude Code config directory
- Sets up MCP server connection through the bridge

## How to Restore MCP Tools

### Step 1: Ensure Docker Container is Running
```bash
# Check if container is running
docker ps | grep dhafnck-mcp-server

# If not running, start it
cd dhafnck_mcp_main
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

### Step 2: Configure Claude Code
```bash
# Run the configuration script
cd dhafnck_mcp_main
./configure_claude_code.sh
```

This will create/update the Claude Code configuration file:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/claude/claude_desktop_config.json`

### Step 3: Restart Claude Code
1. Completely close Claude Code
2. Restart Claude Code
3. Test MCP tools are available:
```
mcp__dhafnck_mcp_http__health_check
```

## Configuration Details

The configuration connects Claude Code to the MCP bridge which forwards requests to the Docker HTTP server:

```json
{
  "mcpServers": {
    "dhafnck_mcp_http": {
      "command": "python3",
      "args": [
        "/path/to/dhafnck_mcp_main/src/mcp_bridge.py"
      ],
      "transport": "stdio"
    }
  }
}
```

For Windows/WSL:
```json
{
  "mcpServers": {
    "dhafnck_mcp_http": {
      "command": "wsl.exe",
      "args": [
        "--cd",
        "/path/to/dhafnck_mcp_main",
        "--exec",
        "python3",
        "src/mcp_bridge.py"
      ],
      "transport": "stdio"
    }
  }
}
```

## Available MCP Tools
Once connected, the following tools are available with `mcp__dhafnck_mcp_http__` prefix:
- `manage_project` - Project management
- `manage_task` - Task management
- `manage_subtask` - Subtask management
- `manage_context` - Context management
- `manage_git_branch` - Git branch management
- `manage_connection` - Connection management
- `manage_agent` - Agent management
- `manage_compliance` - Compliance management
- `manage_rule` - Rule management
- `call_agent` - Call specialized agents
- `complete_task_with_update` - Complete tasks with updates
- `quick_task_update` - Quick task updates
- `report_progress` - Report progress
- `get_workflow_hints` - Get workflow hints
- `get_vision_alignment` - Get vision alignment
- `complete_task_with_context` - Complete with context
- `get_task_with_reminders` - Get task reminders
- `manage_hierarchical_context` - Hierarchical context
- `manage_delegation_queue` - Delegation queue
- `validate_context_inheritance` - Validate inheritance
- `validate_rules` - Validate rules
- `health_check` - Check server health
- `get_server_capabilities` - Get capabilities

## Troubleshooting

### MCP Tools Not Available
1. Check Docker container is running: `docker ps`
2. Check server health: `curl http://localhost:8000/health`
3. Check bridge logs: `tail -f /tmp/mcp_bridge.log`
4. Test bridge manually:
```bash
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | \
  python3 src/mcp_bridge.py
```

### Authentication Errors
The bridge handles authentication automatically. If you see authentication errors:
1. Check JWT secrets are configured in `.env`
2. Restart Docker container to reload environment
3. Check server logs: `docker logs dhafnck-mcp-server`

### Connection Refused
1. Ensure Docker container is running
2. Check port 8000 is not blocked
3. Verify no other service is using port 8000

## Architecture Overview

```
Claude Code (STDIO) 
    ↓
mcp_bridge.py (STDIO → HTTP)
    ↓
Docker Container (HTTP Server on :8000)
    ↓
FastMCP Server with DDD Tools
```

## Status: RESOLVED
The MCP tools connection has been restored using the bridge approach. The tools are now accessible through the `mcp__dhafnck_mcp_http__` prefix after configuring Claude Code with the provided script.