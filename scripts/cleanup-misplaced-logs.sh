#!/bin/bash
# Cleanup script to remove misplaced logs directories created before the fix
# These were created when hooks used Path.cwd() instead of project root

echo "Cleaning up misplaced logs directories..."

# List of directories to clean (excluding root logs and git logs)
DIRS_TO_CLEAN=(
    "agenthub-frontend/logs"
    "agenthub_main/agent-library/logs"
    "agenthub_main/src/tests/unit/mcp_controllers/logs"
    "agenthub_main/src/logs"
    "agenthub_main/logs"
    "docker-system/logs"
    "ai_docs/core-architecture/logs"
)

PROJECT_ROOT="/home/daihungpham/__projects__/agentic-project"
ROOT_LOGS="$PROJECT_ROOT/logs"

for dir in "${DIRS_TO_CLEAN[@]}"; do
    FULL_PATH="$PROJECT_ROOT/$dir"
    if [ -d "$FULL_PATH" ]; then
        echo "Found misplaced logs: $dir"
        
        # Check if it contains any .json files
        if ls "$FULL_PATH"/*.json 1> /dev/null 2>&1; then
            echo "  Moving .json files to root logs directory..."
            mv "$FULL_PATH"/*.json "$ROOT_LOGS/" 2>/dev/null
        fi
        
        # Remove the empty directory
        if rmdir "$FULL_PATH" 2>/dev/null; then
            echo "  Removed empty directory: $dir"
        else
            echo "  Directory not empty, keeping: $dir"
        fi
    fi
done

echo "Cleanup complete!"
echo ""
echo "Note: .claude/data/sessions directories are created by Claude Code itself"
echo "for session management and are not related to our hooks."