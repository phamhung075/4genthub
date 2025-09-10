#!/bin/bash

# Completely disable all required actions that block login

# Configuration - Use environment variables or command-line arguments
KEYCLOAK_URL="${KEYCLOAK_URL:-https://keycloak.92.5.226.7.nip.io}"
REALM="${KEYCLOAK_REALM:-mcp}"

# Check if admin password is provided
if [ -z "$1" ] && [ -z "$KEYCLOAK_ADMIN_PASSWORD" ]; then
    echo "Error: Admin password required!"
    echo "Usage: $0 <admin_password>"
    echo "Or set KEYCLOAK_ADMIN_PASSWORD environment variable"
    exit 1
fi

ADMIN_PASSWORD="${1:-$KEYCLOAK_ADMIN_PASSWORD}"

echo "Disabling ALL required actions to fix login..."

# Get admin token
TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

# Disable ALL required actions
ACTIONS=(
  "VERIFY_EMAIL"
  "UPDATE_PASSWORD"
  "UPDATE_PROFILE"
  "CONFIGURE_TOTP"
  "VERIFY_PROFILE"
)

for ACTION in "${ACTIONS[@]}"; do
  echo "Disabling $ACTION..."
  curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions/$ACTION" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"alias\":\"$ACTION\",\"enabled\":false,\"defaultAction\":false}" > /dev/null
done

echo "✅ All required actions disabled!"