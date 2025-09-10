#!/bin/bash

# Configuration - Use environment variables or command-line arguments
KEYCLOAK_URL="${KEYCLOAK_URL:-https://keycloak.92.5.226.7.nip.io}"
REALM="${KEYCLOAK_REALM:-mcp}"
CLIENT_ID="${KEYCLOAK_CLIENT_ID:-mcp-api}"
ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"

# Check if admin password is provided
if [ -z "$1" ] && [ -z "$KEYCLOAK_ADMIN_PASSWORD" ]; then
    echo "Error: Admin password required!"
    echo "Usage: $0 <admin_password>"
    echo "Or set KEYCLOAK_ADMIN_PASSWORD environment variable"
    exit 1
fi

ADMIN_PASSWORD="${1:-$KEYCLOAK_ADMIN_PASSWORD}"

echo "Fixing client permissions..."

# Get admin token
TOKEN_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

# Get client UUID
CLIENT_RESPONSE=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients" \
  -H "Authorization: Bearer $TOKEN" \
  -G -d "clientId=$CLIENT_ID")

CLIENT_UUID=$(echo "$CLIENT_RESPONSE" | jq -r '.[0].id')

# Update client with correct permissions for user management
curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "directAccessGrantsEnabled": true,
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "publicClient": false,
    "serviceAccountsEnabled": true,
    "authorizationServicesEnabled": true,
    "frontchannelLogout": true,
    "protocol": "openid-connect",
    "fullScopeAllowed": true
  }'

echo "✅ Client permissions fixed"

# Ensure service account has manage-users role
SERVICE_ACCOUNT_USER=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/service-account-user" \
  -H "Authorization: Bearer $TOKEN")

if [ ! -z "$SERVICE_ACCOUNT_USER" ]; then
    SERVICE_USER_ID=$(echo "$SERVICE_ACCOUNT_USER" | jq -r '.id')
    
    # Get realm management client
    REALM_MGMT=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients" \
      -H "Authorization: Bearer $TOKEN" \
      -G -d "clientId=realm-management")
    
    REALM_MGMT_UUID=$(echo "$REALM_MGMT" | jq -r '.[0].id')
    
    # Get available roles
    AVAILABLE_ROLES=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients/$REALM_MGMT_UUID/roles" \
      -H "Authorization: Bearer $TOKEN")
    
    # Assign manage-users role
    MANAGE_USERS_ROLE=$(echo "$AVAILABLE_ROLES" | jq -c '.[] | select(.name=="manage-users")')
    
    if [ ! -z "$MANAGE_USERS_ROLE" ]; then
        curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users/$SERVICE_USER_ID/role-mappings/clients/$REALM_MGMT_UUID" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d "[$MANAGE_USERS_ROLE]"
        
        echo "✅ Service account granted manage-users permission"
    fi
fi

echo "Done!"
