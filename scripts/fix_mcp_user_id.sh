#!/bin/bash

# Script to fix MCP user ID to match frontend user
# This ensures subtasks created via MCP tools have the correct user association

echo "🔧 Fixing MCP user ID configuration..."

# The user ID from the frontend (q987@yopmail.com)
FRONTEND_USER_ID="f0de4c5d-2a97-4324-abcd-9dae3922761e"

# Export for current session
export TEST_USER_ID="$FRONTEND_USER_ID"

# Add to .env.dev if not already there
if ! grep -q "TEST_USER_ID=" .env.dev 2>/dev/null; then
    echo "" >> .env.dev
    echo "# MCP Testing User ID - matches frontend user for proper subtask association" >> .env.dev
    echo "TEST_USER_ID=$FRONTEND_USER_ID" >> .env.dev
    echo "✅ Added TEST_USER_ID to .env.dev"
else
    # Update existing value
    sed -i "s/TEST_USER_ID=.*/TEST_USER_ID=$FRONTEND_USER_ID/" .env.dev
    echo "✅ Updated TEST_USER_ID in .env.dev"
fi

# Restart backend to apply changes
echo "🔄 Restarting backend to apply changes..."
cd docker-system
echo "R" | ./docker-menu.sh

echo "✅ MCP user ID fixed! Subtasks created via MCP will now be associated with user: $FRONTEND_USER_ID"
echo "📝 This matches the frontend user q987@yopmail.com"