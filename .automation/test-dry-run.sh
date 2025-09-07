#!/bin/bash
# .automation/test-dry-run.sh - Dry-run test synchronization without committing

echo "🧪 Test Synchronization DRY-RUN Mode"
echo "===================================="
echo ""
echo "This will analyze your current uncommitted changes without requiring a commit."
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SYNC_SCRIPT="$SCRIPT_DIR/claude-test-sync-wsl.sh"

if [ -f "$SYNC_SCRIPT" ]; then
    echo "🔍 Analyzing uncommitted changes..."
    "$SYNC_SCRIPT" --dry-run
else
    echo "❌ Sync script not found at: $SYNC_SCRIPT"
    exit 1
fi