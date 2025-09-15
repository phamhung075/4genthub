#!/bin/bash

# Test MCP connection in production
API_URL="https://api.92.5.226.7.nip.io"
TOKEN="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMGRlNGM1ZC0yYTk3LTQzMjQtYWJjZC05ZGFlMzkyMjc2MWUiLCJzY29wZXMiOlsib3BlbmlkIiwicHJvZmlsZSIsImVtYWlsIiwib2ZmbGluZV9hY2Nlc3MiLCJtY3AtYXBpIiwibWNwLXJvbGVzIiwibWNwLXByb2ZpbGUiLCJwcm9qZWN0czpjcmVhdGUiLCJwcm9qZWN0czpyZWFkIiwicHJvamVjdHM6dXBkYXRlIiwicHJvamVjdHM6ZGVsZXRlIiwidGFza3M6Y3JlYXRlIiwidGFza3M6cmVhZCIsInRhc2tzOnVwZGF0ZSIsInRhc2tzOmRlbGV0ZSIsInN1YnRhc2tzOmNyZWF0ZSIsInN1YnRhc2tzOnJlYWQiLCJzdWJ0YXNrczp1cGRhdGUiLCJzdWJ0YXNrczpkZWxldGUiLCJjb250ZXh0czpjcmVhdGUiLCJjb250ZXh0czpyZWFkIiwiY29udGV4dHM6dXBkYXRlIiwiY29udGV4dHM6ZGVsZXRlIiwiYWdlbnRzOmNyZWF0ZSIsImFnZW50czpyZWFkIiwiYWdlbnRzOnVwZGF0ZSIsImFnZW50czpkZWxldGUiLCJicmFuY2hlczpjcmVhdGUiLCJicmFuY2hlczpyZWFkIiwiYnJhbmNoZXM6dXBkYXRlIiwiYnJhbmNoZXM6ZGVsZXRlIiwibWNwOmV4ZWN1dGUiLCJtY3A6ZGVsZWdhdGUiXSwidHlwZSI6ImFwaV90b2tlbiIsImF1ZCI6Im1jcC1zZXJ2ZXIiLCJpYXQiOjE3NTc5NTk0MDcsImV4cCI6MTc2MDU1MTQwNywiaXNzIjoiZGhhZm5jay1tY3AiLCJqdGkiOiJ0b2tfZWE4ZTFmMzZhZWU4MDE5NSJ9.enl2CRSzdhlxTrmtrQ5S56Vodal9f6riHgJNpc59DKQ"

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