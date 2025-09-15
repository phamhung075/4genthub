#!/bin/bash

echo "Verifying MCP backend configuration..."
echo "======================================"

# Check if MCP endpoint is properly configured in backend
echo -e "\n1. Checking backend MCP route configuration:"
grep -r "mcp" dhafnck_mcp_main/src --include="*.py" | grep -E "(route|endpoint|path)" | head -10

echo -e "\n2. Checking FastMCP server configuration:"
grep -r "FastMCP\|MCP\|mcp_server" dhafnck_mcp_main/src --include="*.py" | grep -E "(Server|server|init)" | head -10

echo -e "\n3. Checking CORS configuration for MCP:"
grep -r "CORS\|cors" dhafnck_mcp_main/src --include="*.py" | grep -E "(origins|allow|credentials)" | head -10

echo -e "\n4. Environment variables for MCP:"
grep -E "MCP|FASTMCP" .env 2>/dev/null || echo "No .env file found"

echo -e "\nDone!"