#!/bin/bash

# Script to run the agenthub server for testing with MCP Inspector
# This script sets up the proper environment and runs the server

# Set working directory to project root, derived from this script's own location
# (agenthub_main/scripts/ -> repo root), never a hard-coded path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$ROOT_DIR"

# Set environment variables
export PYTHONPATH="agenthub_main/src"
export TASKS_JSON_PATH=".cursor/rules/tasks/tasks.json"
export TASK_JSON_BACKUP_PATH=".cursor/rules/tasks/backup"
export MCP_TOOL_CONFIG=".cursor/tool_config.json"
export AUTO_RULE_PATH=".cursor/rules/auto_rule.mdc"
export BRAIN_DIR_PATH=".cursor/rules/brain"
export PROJECTS_FILE_PATH=".cursor/rules/brain/projects.json"
export PROJECT_ROOT_PATH="."

# Run the MCP server
exec agenthub_main/.venv/bin/python -m fastmcp.server.mcp_entry_point
