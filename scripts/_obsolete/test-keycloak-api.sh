#!/bin/bash

# Test Keycloak authentication and API access
# Usage: ./test-keycloak-api.sh <username> <password>

USERNAME=${1:-q987}
PASSWORD=$2

if [ -z "$PASSWORD" ]; then
    echo "❌ Password required!"
    echo "Usage: $0 <username> <password>"
    echo "Example: $0 q987 yourpassword"
    exit 1
fi

KEYCLOAK_URL="https://keycloak.92.5.226.7.nip.io"
REALM="mcp"
CLIENT_ID="mcp-api"

echo "🔐 Authenticating with Keycloak..."
echo "Server: $KEYCLOAK_URL"
echo "User: $USERNAME"
echo ""

# Get token from Keycloak
TOKEN_RESPONSE=$(curl -s -X POST \
  "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=$CLIENT_ID" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "scope=openid profile email offline_access")

# Check if we got a token
if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
    echo "✅ Authentication successful!"
    echo ""

    echo "📊 Fetching projects from backend..."
    PROJECTS=$(curl -s -X GET \
      "http://localhost:8000/api/v2/projects/" \
      -H "Authorization: Bearer $ACCESS_TOKEN")

    echo "Projects response:"
    echo "$PROJECTS" | python3 -m json.tool

    # Check if we got the project
    if echo "$PROJECTS" | grep -q "dhafnck_mcp"; then
        echo ""
        echo "✅ SUCCESS! Your project 'dhafnck_mcp' is accessible!"
        echo ""
        echo "Next steps:"
        echo "1. Login at http://localhost:3800/login with username: $USERNAME"
        echo "2. You should see your project in the dashboard"
    else
        echo ""
        echo "⚠️  No projects found. The backend may need to be synced."
    fi
else
    echo "❌ Authentication failed"
    echo "Response:"
    echo "$TOKEN_RESPONSE" | python3 -m json.tool
    echo ""
    echo "Please check your password and try again."
fi