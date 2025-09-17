#!/bin/bash

# Script to run the 4genthub server for testing with MCP Inspector
# This script sets up the proper environment and runs the server

# Set working directory to project root
cd /home/daihungpham/agentic-project

# Set environment variables
export PYTHONPATH="4genthub_main/src"
export TASKS_JSON_PATH=".cursor/rules/tasks/tasks.json"
export TASK_JSON_BACKUP_PATH=".cursor/rules/tasks/backup"
export MCP_TOOL_CONFIG=".cursor/tool_config.json"
export AGENTS_OUTPUT_DIR=".cursor/rules/agents"
export AUTO_RULE_PATH=".cursor/rules/auto_rule.mdc"
export BRAIN_DIR_PATH=".cursor/rules/brain"
export PROJECTS_FILE_PATH=".cursor/rules/brain/projects.json"
export PROJECT_ROOT_PATH="."
export AGENT_LIBRARY_DIR_PATH="4genthub_main/agent-library"
export AGENT_LIBRARY_DIR_PATH="4genthub_main/agent-library"

# Run the MCP server
exec 4genthub_main/.venv/bin/python -m fastmcp.server.mcp_entry_point 