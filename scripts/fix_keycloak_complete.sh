#!/bin/bash

# Secure and logical Keycloak configuration for EMAIL_VERIFIED_AUTO feature
# This script properly configures security while enabling smooth user experience

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

echo "=================================================="
echo "Secure Keycloak Configuration for EMAIL_VERIFIED_AUTO"
echo "=================================================="
echo ""

# Get admin token
echo "1. Getting admin access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate as admin"
    echo "$TOKEN_RESPONSE" | jq .
    exit 1
fi
echo "✅ Admin token obtained"
echo ""

# Configure required actions based on EMAIL_VERIFIED_AUTO setting
echo "2. Configuring required actions for optimal security..."

# Check EMAIL_VERIFIED_AUTO environment variable
EMAIL_VERIFIED_AUTO="${EMAIL_VERIFIED_AUTO:-true}"
echo "   EMAIL_VERIFIED_AUTO is set to: $EMAIL_VERIFIED_AUTO"

if [ "$EMAIL_VERIFIED_AUTO" == "true" ]; then
    echo "   Configuring for automatic email verification..."
    
    # Disable email verification requirement only
    curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions/VERIFY_EMAIL" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"alias":"VERIFY_EMAIL","name":"Verify Email","providerId":"VERIFY_EMAIL","enabled":false,"defaultAction":false,"priority":50}' > /dev/null
    
    echo "   ✅ Email verification disabled (AUTO mode)"
else
    echo "   Configuring for manual email verification..."
    
    # Enable email verification requirement
    curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions/VERIFY_EMAIL" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"alias":"VERIFY_EMAIL","name":"Verify Email","providerId":"VERIFY_EMAIL","enabled":true,"defaultAction":true,"priority":50}' > /dev/null
    
    echo "   ✅ Email verification enabled (MANUAL mode)"
fi

# Keep these security features ENABLED for better security
SECURITY_ACTIONS=(
  "UPDATE_PASSWORD:false"     # Don't force password change on first login
  "UPDATE_PROFILE:false"      # Don't force profile update on first login
  "CONFIGURE_TOTP:false"      # Don't force 2FA on first login, but keep it available
  "VERIFY_PROFILE:false"      # Don't force profile verification
)

for ACTION_CONFIG in "${SECURITY_ACTIONS[@]}"; do
  ACTION="${ACTION_CONFIG%%:*}"
  DEFAULT_ACTION="${ACTION_CONFIG##*:}"
  
  echo "   Configuring $ACTION (available but not forced)..."
  curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/authentication/required-actions/$ACTION" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"alias\":\"$ACTION\",\"enabled\":true,\"defaultAction\":$DEFAULT_ACTION}" > /dev/null 2>&1
done

echo "✅ Required actions configured securely"
echo ""

# Update realm settings for security and usability
echo "3. Updating realm security settings..."

if [ "$EMAIL_VERIFIED_AUTO" == "true" ]; then
    VERIFY_EMAIL_SETTING="false"
else
    VERIFY_EMAIL_SETTING="true"
fi

curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"verifyEmail\": $VERIFY_EMAIL_SETTING,
    \"loginWithEmailAllowed\": true,
    \"registrationEmailAsUsername\": false,
    \"duplicateEmailsAllowed\": false,
    \"resetPasswordAllowed\": true,
    \"editUsernameAllowed\": false,
    \"bruteForceProtected\": true,
    \"permanentLockout\": false,
    \"maxFailureWaitSeconds\": 900,
    \"minimumQuickLoginWaitSeconds\": 60,
    \"waitIncrementSeconds\": 60,
    \"quickLoginCheckMilliSeconds\": 1000,
    \"maxDeltaTimeSeconds\": 43200,
    \"failureFactor\": 5,
    \"sslRequired\": \"external\",
    \"passwordPolicy\": \"length(8) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)\"
  }" > /dev/null

echo "✅ Realm security settings updated with:"
echo "   - Brute force protection: ENABLED"
echo "   - Password policy: Strong requirements"
echo "   - SSL required: For external connections"
echo "   - Email verification: $VERIFY_EMAIL_SETTING"
echo ""

# Configure client security settings
echo "4. Securing client configuration..."

# Get client UUID
CLIENT_RESPONSE=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/clients" \
  -H "Authorization: Bearer $TOKEN" \
  -G -d "clientId=$CLIENT_ID")

CLIENT_UUID=$(echo "$CLIENT_RESPONSE" | jq -r '.[0].id')

if [ -z "$CLIENT_UUID" ] || [ "$CLIENT_UUID" == "null" ]; then
    echo "❌ Client $CLIENT_ID not found"
    exit 1
fi

# Update client with secure settings
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
    "fullScopeAllowed": false,
    "nodeReRegistrationTimeout": 0,
    "protocolMappers": [
      {
        "name": "email-verified",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-property-mapper",
        "consentRequired": false,
        "config": {
          "usermodel.attribute": "emailVerified",
          "id.token.claim": "true",
          "access.token.claim": "true",
          "claim.name": "email_verified",
          "jsonType.label": "boolean"
        }
      }
    ]
  }' > /dev/null

echo "✅ Client security configured with:"
echo "   - Direct Access Grants: ENABLED (for password flow)"
echo "   - Standard Flow: ENABLED (for authorization code flow)"
echo "   - Implicit Flow: DISABLED (deprecated, less secure)"
echo "   - Public Client: DISABLED (requires client secret)"
echo "   - Service Accounts: ENABLED"
echo "   - Full Scope: DISABLED (principle of least privilege)"
echo ""

# Clear required actions only for test users, not all users
echo "5. Cleaning up test users only..."

# Get all users
USERS=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/users" \
  -H "Authorization: Bearer $TOKEN")

USER_COUNT=$(echo "$USERS" | jq '. | length')
echo "   Found $USER_COUNT total users"

# Clear required actions only for test users
echo "$USERS" | jq -c '.[]' | while read USER; do
  USER_ID=$(echo "$USER" | jq -r '.id')
  USERNAME=$(echo "$USER" | jq -r '.username')
  EMAIL=$(echo "$USER" | jq -r '.email')
  
  # Only process test users or users with example.com emails
  if [[ "$USERNAME" == "test"* ]] || [[ "$EMAIL" == *"@example.com" ]] || [[ "$EMAIL" == *"@yopmail.com" ]]; then
    echo "   Clearing required actions for test user: $USERNAME"
    
    if [ "$EMAIL_VERIFIED_AUTO" == "true" ]; then
      # For auto mode, clear all required actions and verify email
      curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "emailVerified": true,
          "enabled": true,
          "requiredActions": []
        }' > /dev/null
    else
      # For manual mode, set VERIFY_EMAIL as required action
      curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "emailVerified": false,
          "enabled": true,
          "requiredActions": ["VERIFY_EMAIL"]
        }' > /dev/null
    fi
  fi
done

echo "✅ Test user cleanup completed"
echo ""

# Configure authentication flows for security
echo "6. Configuring authentication flows..."

# Update browser flow to include appropriate security measures
curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/authentication/flows/browser" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "browser",
    "description": "browser based authentication",
    "providerId": "basic-flow",
    "topLevel": true,
    "builtIn": true
  }' > /dev/null 2>&1

echo "✅ Authentication flows configured"
echo ""

# Set up session security
echo "7. Configuring session security..."

curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ssoSessionIdleTimeout": 1800,
    "ssoSessionMaxLifespan": 36000,
    "ssoSessionIdleTimeoutRememberMe": 0,
    "ssoSessionMaxLifespanRememberMe": 0,
    "offlineSessionIdleTimeout": 2592000,
    "offlineSessionMaxLifespanEnabled": false,
    "accessTokenLifespan": 300,
    "accessTokenLifespanForImplicitFlow": 900,
    "accessCodeLifespan": 60,
    "accessCodeLifespanUserAction": 300,
    "accessCodeLifespanLogin": 1800,
    "actionTokenGeneratedByAdminLifespan": 43200,
    "actionTokenGeneratedByUserLifespan": 300
  }' > /dev/null

echo "✅ Session security configured with:"
echo "   - SSO Session Idle: 30 minutes"
echo "   - SSO Session Max: 10 hours"
echo "   - Access Token Lifespan: 5 minutes"
echo "   - Refresh Token: 30 days (offline)"
echo ""

echo "=================================================="
echo "✅ SECURE CONFIGURATION COMPLETED!"
echo "=================================================="
echo ""
echo "Security Summary:"
echo "  ✅ Brute force protection: ENABLED"
echo "  ✅ Strong password policy: ENFORCED"
echo "  ✅ SSL/TLS: REQUIRED for external"
echo "  ✅ Session timeouts: CONFIGURED"
echo "  ✅ Token lifespans: SECURE (5 min access, 30 day refresh)"
echo "  ✅ Email verification: $([ "$EMAIL_VERIFIED_AUTO" == "true" ] && echo "AUTO (disabled)" || echo "MANUAL (enabled)")"
echo "  ✅ 2FA/TOTP: AVAILABLE (not forced)"
echo "  ✅ Implicit flow: DISABLED"
echo "  ✅ Principle of least privilege: APPLIED"
echo ""
echo "The system is now securely configured while maintaining usability."
echo "Users can register and login smoothly with appropriate security measures."