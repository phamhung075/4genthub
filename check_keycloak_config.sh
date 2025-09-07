#!/bin/bash

# Script to check and fix Keycloak configuration for EMAIL_VERIFIED_AUTO feature
# This script uses the Keycloak Admin REST API to verify and update settings

KEYCLOAK_URL="https://keycloak.92.5.226.7.nip.io"
REALM="mcp"
CLIENT_ID="mcp-api"
ADMIN_USER="admin"

echo "=================================================="
echo "Keycloak Configuration Check for EMAIL_VERIFIED_AUTO"
echo "=================================================="
echo ""

# Check if admin password is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <admin_password>"
    echo "Example: $0 your-admin-password"
    exit 1
fi

ADMIN_PASSWORD="$1"

echo "1. Getting admin access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli")

if echo "$TOKEN_RESPONSE" | grep -q "error"; then
    echo "❌ Failed to authenticate as admin"
    echo "$TOKEN_RESPONSE" | jq .
    exit 1
fi

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
echo "✅ Admin token obtained"
echo ""

echo "2. Checking realm configuration..."
REALM_CONFIG=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM" \
  -H "Authorization: Bearer $TOKEN")

VERIFY_EMAIL=$(echo "$REALM_CONFIG" | jq -r '.verifyEmail')
REGISTRATION_EMAIL_AS_USERNAME=$(echo "$REALM_CONFIG" | jq -r '.registrationEmailAsUsername')
LOGIN_WITH_EMAIL=$(echo "$REALM_CONFIG" | jq -r '.loginWithEmailAllowed')

echo "Current Realm Settings:"
echo "  - Verify Email: $VERIFY_EMAIL"
echo "  - Registration Email as Username: $REGISTRATION_EMAIL_AS_USERNAME"
echo "  - Login with Email Allowed: $LOGIN_WITH_EMAIL"
echo ""

echo "3. Checking required actions..."
REQUIRED_ACTIONS=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions" \
  -H "Authorization: Bearer $TOKEN")

echo "Required Actions Status:"
echo "$REQUIRED_ACTIONS" | jq -r '.[] | "  - \(.alias): enabled=\(.enabled), defaultAction=\(.defaultAction)"'
echo ""

echo "4. Checking client configuration..."
CLIENT_CONFIG=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients" \
  -H "Authorization: Bearer $TOKEN" \
  -G -d "clientId=$CLIENT_ID")

if [ "$(echo "$CLIENT_CONFIG" | jq '. | length')" -eq 0 ]; then
    echo "❌ Client $CLIENT_ID not found"
else
    CLIENT_UUID=$(echo "$CLIENT_CONFIG" | jq -r '.[0].id')
    DIRECT_ACCESS=$(echo "$CLIENT_CONFIG" | jq -r '.[0].directAccessGrantsEnabled')
    SERVICE_ACCOUNTS=$(echo "$CLIENT_CONFIG" | jq -r '.[0].serviceAccountsEnabled')
    AUTHORIZATION=$(echo "$CLIENT_CONFIG" | jq -r '.[0].authorizationServicesEnabled')
    
    echo "Client Settings for $CLIENT_ID:"
    echo "  - Client UUID: $CLIENT_UUID"
    echo "  - Direct Access Grants: $DIRECT_ACCESS"
    echo "  - Service Accounts: $SERVICE_ACCOUNTS"
    echo "  - Authorization Services: $AUTHORIZATION"
    echo ""
    
    # Check client roles
    echo "5. Checking client roles..."
    CLIENT_ROLES=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/roles" \
      -H "Authorization: Bearer $TOKEN")
    
    ROLE_COUNT=$(echo "$CLIENT_ROLES" | jq '. | length')
    echo "  - Client has $ROLE_COUNT roles defined"
    if [ "$ROLE_COUNT" -gt 0 ]; then
        echo "$CLIENT_ROLES" | jq -r '.[] | "    - \(.name)"'
    fi
fi

echo ""
echo "=================================================="
echo "RECOMMENDED FIXES"
echo "=================================================="
echo ""

if [ "$VERIFY_EMAIL" = "true" ]; then
    echo "⚠️  ISSUE: Realm has 'Verify Email' enabled"
    echo "   FIX: Disable email verification at realm level"
    echo "   Command to fix:"
    echo "   curl -X PUT \"$KEYCLOAK_URL/admin/realms/$REALM\" \\"
    echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"verifyEmail\": false}'"
    echo ""
fi

echo "⚠️  CRITICAL: Check and disable VERIFY_EMAIL required action"
echo "   Command to disable:"
echo "   curl -X PUT \"$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions/VERIFY_EMAIL\" \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"alias\":\"VERIFY_EMAIL\",\"name\":\"Verify Email\",\"providerId\":\"VERIFY_EMAIL\",\"enabled\":false,\"defaultAction\":false,\"priority\":50}'"
echo ""

if [ "$DIRECT_ACCESS" = "false" ]; then
    echo "⚠️  ISSUE: Direct Access Grants disabled for client"
    echo "   FIX: Enable Direct Access Grants"
    echo "   Command to fix:"
    echo "   curl -X PUT \"$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID\" \\"
    echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"directAccessGrantsEnabled\": true}'"
    echo ""
fi

echo "=================================================="
echo "APPLY ALL FIXES AUTOMATICALLY?"
echo "=================================================="
echo ""
echo "To apply all recommended fixes, run:"
echo "$0 $ADMIN_PASSWORD --apply-fixes"
echo ""

if [ "$2" = "--apply-fixes" ]; then
    echo "Applying fixes..."
    echo ""
    
    # Disable realm email verification
    echo "1. Disabling realm email verification..."
    curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"verifyEmail": false}' > /dev/null
    echo "✅ Done"
    
    # Disable VERIFY_EMAIL required action
    echo "2. Disabling VERIFY_EMAIL required action..."
    curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions/VERIFY_EMAIL" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"alias":"VERIFY_EMAIL","name":"Verify Email","providerId":"VERIFY_EMAIL","enabled":false,"defaultAction":false,"priority":50}' > /dev/null
    echo "✅ Done"
    
    # Enable Direct Access Grants if needed
    if [ "$DIRECT_ACCESS" = "false" ]; then
        echo "3. Enabling Direct Access Grants..."
        curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d '{"directAccessGrantsEnabled": true}' > /dev/null
        echo "✅ Done"
    fi
    
    echo ""
    echo "✅ All fixes applied successfully!"
    echo "Please test registration and login again."
fi