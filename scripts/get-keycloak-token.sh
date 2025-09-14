#!/bin/bash

# Keycloak token request script
# Usage: ./get-keycloak-token.sh <username> <password>

USERNAME=${1:-q987}
PASSWORD=$2

if [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <username> <password>"
    echo "Example: $0 q987 yourpassword"
    exit 1
fi

KEYCLOAK_URL="https://keycloak.92.5.226.7.nip.io"
REALM="mcp"
CLIENT_ID="mcp-api"
CLIENT_SECRET="your-client-secret"  # Update this if you have the client secret

echo "🔐 Requesting token from Keycloak..."
echo "Server: $KEYCLOAK_URL"
echo "Realm: $REALM"
echo "User: $USERNAME"

RESPONSE=$(curl -s -X POST \
  "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=$CLIENT_ID" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "scope=openid profile email offline_access mcp-api mcp-roles mcp-profile mcp-crud-create mcp-crud-read mcp-crud-update mcp-crud-delete")

# Check if we got a token
if echo "$RESPONSE" | grep -q "access_token"; then
    echo "✅ Token obtained successfully!"
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | python3 -m json.tool

    # Extract and display the access token
    ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
    echo ""
    echo "📋 Access Token (copy this for API testing):"
    echo "$ACCESS_TOKEN"

    # Test the token against the backend
    echo ""
    echo "🧪 Testing token against backend API..."
    curl -s -X GET \
      "http://localhost:8000/api/v2/projects" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -m json.tool
else
    echo "❌ Failed to obtain token"
    echo "Response:"
    echo "$RESPONSE" | python3 -m json.tool
fi