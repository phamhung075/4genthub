#!/bin/bash

# Test MCP connection in production
API_URL="https://api.92.5.226.7.nip.io"
TOKEN="Bearer [REDACTED-JWT-TOKEN]"

echo "Testing MCP connection to production..."
echo "================================"

# Test 1: Basic health check
echo -e "\n1. Testing basic API health:"
curl -s -X GET "$API_URL/health" \
  -H "Authorization: $TOKEN" | jq .

# Test 2: MCP endpoint with SSE headers
echo -e "\n2. Testing MCP endpoint with SSE:"
curl -i -N \
  -H "Accept: text/event-stream" \
  -H "Authorization: $TOKEN" \
  -H "Cache-Control: no-cache" \
  "$API_URL/mcp" \
  --max-time 5

# Test 3: Test MCP tools listing
echo -e "\n3. Testing MCP tools listing:"
curl -s -X POST "$API_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Authorization: $TOKEN" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | jq .

# Test 4: Check response headers
echo -e "\n4. Checking response headers:"
curl -I "$API_URL/mcp" \
  -H "Authorization: $TOKEN" \
  -H "Accept: text/event-stream"

echo -e "\nTests complete!"