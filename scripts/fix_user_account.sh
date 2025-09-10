#!/bin/bash

# Fix specific user account in Keycloak

# Configuration - Use environment variables or command-line arguments
KEYCLOAK_URL="${KEYCLOAK_URL:-https://keycloak.92.5.226.7.nip.io}"
REALM="${KEYCLOAK_REALM:-mcp}"

# Check if admin password and user email are provided
if [ $# -lt 2 ] && ([ -z "$KEYCLOAK_ADMIN_PASSWORD" ] || [ -z "$USER_EMAIL" ]); then
    echo "Error: Admin password and user email required!"
    echo "Usage: $0 <admin_password> <user_email>"
    echo "Or set KEYCLOAK_ADMIN_PASSWORD and USER_EMAIL environment variables"
    exit 1
fi

ADMIN_PASSWORD="${1:-$KEYCLOAK_ADMIN_PASSWORD}"
USER_EMAIL="${2:-$USER_EMAIL}"

echo "=================================================="
echo "Fixing user account: $USER_EMAIL"
echo "=================================================="
echo ""

# Get admin token
echo "1. Getting admin access token..."
TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate as admin"
    exit 1
fi
echo "✅ Admin token obtained"
echo ""

# Search for user by email
echo "2. Searching for user..."
USER_SEARCH=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/users" \
  -H "Authorization: Bearer $TOKEN" \
  -G -d "email=$USER_EMAIL")

USER_COUNT=$(echo "$USER_SEARCH" | jq '. | length')

if [ "$USER_COUNT" -eq 0 ]; then
    echo "❌ User not found: $USER_EMAIL"
    echo ""
    echo "Creating new user with provided credentials..."
    
    # Create the user
    USER_DATA='{
      "username": "q987",
      "email": "'$USER_EMAIL'",
      "enabled": true,
      "emailVerified": true,
      "credentials": [{
        "type": "password",
        "value": "qP987987@",
        "temporary": false
      }],
      "requiredActions": []
    }'
    
    CREATE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$USER_DATA")
    
    if [ "$CREATE_RESPONSE" -eq 201 ]; then
        echo "✅ User created successfully"
        
        # Get the newly created user
        USER_SEARCH=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/users" \
          -H "Authorization: Bearer $TOKEN" \
          -G -d "email=$USER_EMAIL")
    else
        echo "❌ Failed to create user"
        exit 1
    fi
fi

# Get user details
USER_ID=$(echo "$USER_SEARCH" | jq -r '.[0].id')
USERNAME=$(echo "$USER_SEARCH" | jq -r '.[0].username')
ENABLED=$(echo "$USER_SEARCH" | jq -r '.[0].enabled')
EMAIL_VERIFIED=$(echo "$USER_SEARCH" | jq -r '.[0].emailVerified')

echo "✅ User found:"
echo "   - ID: $USER_ID"
echo "   - Username: $USERNAME"
echo "   - Enabled: $ENABLED"
echo "   - Email Verified: $EMAIL_VERIFIED"
echo ""

# Fix user account
echo "3. Fixing user account settings..."

# Update user to ensure proper settings
curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "emailVerified": true,
    "requiredActions": []
  }' > /dev/null

echo "✅ User settings updated"
echo ""

# Reset password to ensure it's correct
echo "4. Resetting password..."
curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/reset-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "password",
    "value": "qP987987@",
    "temporary": false
  }' > /dev/null

echo "✅ Password reset to: qP987987@"
echo ""

# Assign necessary roles
echo "5. Assigning roles..."

# Get available realm roles
REALM_ROLES=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/roles" \
  -H "Authorization: Bearer $TOKEN")

# Find and assign user role
USER_ROLE=$(echo "$REALM_ROLES" | jq -c '.[] | select(.name=="user")')
if [ ! -z "$USER_ROLE" ]; then
    curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/role-mappings/realm" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "[$USER_ROLE]" > /dev/null 2>&1
    echo "✅ User role assigned"
fi

# Assign offline_access role
OFFLINE_ROLE=$(echo "$REALM_ROLES" | jq -c '.[] | select(.name=="offline_access")')
if [ ! -z "$OFFLINE_ROLE" ]; then
    curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/role-mappings/realm" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "[$OFFLINE_ROLE]" > /dev/null 2>&1
    echo "✅ Offline access role assigned"
fi

# Assign uma_authorization role
UMA_ROLE=$(echo "$REALM_ROLES" | jq -c '.[] | select(.name=="uma_authorization")')
if [ ! -z "$UMA_ROLE" ]; then
    curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/role-mappings/realm" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "[$UMA_ROLE]" > /dev/null 2>&1
    echo "✅ UMA authorization role assigned"
fi

echo ""
echo "=================================================="
echo "✅ USER ACCOUNT FIXED!"
echo "=================================================="
echo ""
echo "User can now login with:"
echo "  Email: $USER_EMAIL"
echo "  Password: qP987987@"
echo ""
echo "Testing login..."

# Test login
LOGIN_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=mcp-api" \
  -d "client_secret=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P" \
  -d "username=$USER_EMAIL" \
  -d "password=qP987987@" \
  -d "scope=openid")

if echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    echo "✅ Login test successful!"
else
    echo "❌ Login test failed:"
    echo "$LOGIN_RESPONSE" | jq .
fi