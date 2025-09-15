#!/bin/bash

# Test production MCP connection
API_URL="https://api.92.5.226.7.nip.io"
TOKEN="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmMGRlNGM1ZC0yYTk3LTQzMjQtYWJjZC05ZGFlMzkyMjc2MWUiLCJzY29wZXMiOlsib3BlbmlkIiwicHJvZmlsZSIsImVtYWlsIiwib2ZmbGluZV9hY2Nlc3MiLCJtY3AtYXBpIiwibWNwLXJvbGVzIiwibWNwLXByb2ZpbGUiLCJwcm9qZWN0czpjcmVhdGUiLCJwcm9qZWN0czpyZWFkIiwicHJvamVjdHM6dXBkYXRlIiwicHJvamVjdHM6ZGVsZXRlIiwidGFza3M6Y3JlYXRlIiwidGFza3M6cmVhZCIsInRhc2tzOnVwZGF0ZSIsInRhc2tzOmRlbGV0ZSIsInN1YnRhc2tzOmNyZWF0ZSIsInN1YnRhc2tzOnJlYWQiLCJzdWJ0YXNrczp1cGRhdGUiLCJzdWJ0YXNrczpkZWxldGUiLCJjb250ZXh0czpjcmVhdGUiLCJjb250ZXh0czpyZWFkIiwiY29udGV4dHM6dXBkYXRlIiwiY29udGV4dHM6ZGVsZXRlIiwiYWdlbnRzOmNyZWF0ZSIsImFnZW50czpyZWFkIiwiYWdlbnRzOnVwZGF0ZSIsImFnZW50czpkZWxldGUiLCJicmFuY2hlczpjcmVhdGUiLCJicmFuY2hlczpyZWFkIiwiYnJhbmNoZXM6dXBkYXRlIiwiYnJhbmNoZXM6ZGVsZXRlIiwibWNwOmV4ZWN1dGUiLCJtY3A6ZGVsZWdhdGUiXSwidHlwZSI6ImFwaV90b2tlbiIsImF1ZCI6Im1jcC1zZXJ2ZXIiLCJpYXQiOjE3NTc5NTk0MDcsImV4cCI6MTc2MDU1MTQwNywiaXNzIjoiZGhhZm5jay1tY3AiLCJqdGkiOiJ0b2tfZWE4ZTFmMzZhZWU4MDE5NSJ9.enl2CRSzdhlxTrmtrQ5S56Vodal9f6riHgJNpc59DKQ"

echo "Testing MCP production deployment..."
echo "====================================="

# Test 1: Check health endpoint
echo -e "\n1. Health Check:"
curl -s "$API_URL/health" | jq .

# Test 2: Check MCP endpoint exists
echo -e "\n2. MCP Endpoint Check (should return 405 for GET without SSE):"
curl -I "$API_URL/mcp/" 2>/dev/null | head -n 5

# Test 3: Test MCP initialization
echo -e "\n3. MCP Initialize:"
curl -s -X POST "$API_URL/mcp/initialize" \
  -H "Content-Type: application/json" \
  -H "Authorization: $TOKEN" \
  -H "Accept: application/json" \
  -d '{"protocolVersion":"1.0.0","capabilities":{"tools":{}}}' | jq .

# Test 4: Test MCP tools listing via messages endpoint
echo -e "\n4. MCP Tools List:"
curl -s -X POST "$API_URL/mcp/messages/" \
  -H "Content-Type: application/json" \
  -H "Authorization: $TOKEN" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | jq .

# Test 5: Test SSE connection (will timeout after 3 seconds - that's expected)
echo -e "\n5. SSE Connection Test (3 second timeout is normal):"
timeout 3 curl -N \
  -H "Accept: text/event-stream" \
  -H "Authorization: $TOKEN" \
  "$API_URL/mcp/" 2>&1 | head -20

echo -e "\n====================================="
echo "Tests complete!"
echo ""
echo "If you see:"
echo "  - Health check: OK"
echo "  - MCP endpoint: Returns headers (not 404)"
echo "  - Initialize: Returns session info"
echo "  - Tools list: Returns tool array"
echo "  - SSE: Connects without immediate error"
echo ""
echo "Then MCP is working correctly!"