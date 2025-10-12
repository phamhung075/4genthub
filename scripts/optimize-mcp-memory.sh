#!/bin/bash
# MCP Memory Optimization Script
# Reduces memory usage for Claude Code MCP servers

echo "🔧 Optimizing MCP Server Memory Usage..."

# 1. Kill extra Claude sessions
echo "1. Checking for multiple Claude sessions..."
CLAUDE_PIDS=$(pgrep -f "^claude$" | wc -l)
if [ $CLAUDE_PIDS -gt 1 ]; then
    echo "  ⚠️  Found $CLAUDE_PIDS Claude sessions running"
    echo "  💡 Run: pkill -9 -o claude  # to keep only newest session"
fi

# 2. Clean old session data
echo "2. Cleaning old session data..."
CLEANED=$(find ~/.claude/projects -name "timeline.json" -mtime +7 -delete -print | wc -l)
echo "  ✅ Cleaned $CLEANED old timeline files"

# 3. Set optimal Node memory
echo "3. Setting Node.js memory limits..."
if ! grep -q "NODE_OPTIONS=.*max-old-space-size" ~/.bashrc; then
    echo 'export NODE_OPTIONS="--max-old-space-size=8192"' >> ~/.bashrc
    echo "  ✅ Added NODE_OPTIONS to ~/.bashrc"
else
    echo "  ℹ️  NODE_OPTIONS already configured"
fi

# 4. Show current memory usage
echo "4. Current memory usage:"
ps aux | grep -E "(claude|node)" | grep -v grep | awk '{sum+=$6} END {print "  📊 Total Memory: " sum/1024 " MB"}'

echo ""
echo "✅ Optimization complete!"
echo ""
echo "💡 Recommended actions:"
echo "  1. Restart your Claude session to apply changes"
echo "  2. Run this script weekly to maintain performance"
echo "  3. Keep only 1 Claude session active at a time"
