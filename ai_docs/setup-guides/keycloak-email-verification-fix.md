# Keycloak EMAIL_VERIFIED_AUTO Configuration Fix

## Problem Summary
When `EMAIL_VERIFIED_AUTO=true` is set, users can register successfully but cannot login. The error "Account is not fully set up" occurs even though:
- Registration completes successfully
- Email verification is marked as true in the backend
- Keycloak admin shows "Verify email: Off"

## Root Cause
The issue is a configuration mismatch between the backend and Keycloak server:
1. Backend sets `emailVerified: true` for new users when `EMAIL_VERIFIED_AUTO=true`
2. Keycloak server still expects additional account setup steps
3. The Resource Owner Password Credentials Grant flow fails with "Account is not fully set up"

## Solution

### Option 1: Update Keycloak Realm Configuration (Recommended)

#### Via Keycloak Admin Console:
1. Login to Keycloak Admin Console: https://keycloak.92.5.226.7.nip.io/admin
2. Select the `mcp` realm
3. Go to **Authentication** → **Required Actions**
4. Disable or remove the following required actions:
   - Verify Email (already disabled based on screenshot)
   - Update Password
   - Update Profile
   - Configure OTP (if present)

5. Go to **Authentication** → **Flows**
6. Select **Browser** flow
7. Ensure "Verify Email" is set to **DISABLED** or **ALTERNATIVE**

8. Go to **Clients** → **mcp-api** → **Advanced**
9. Set **Direct Access Grants Enabled** to **ON**
10. Set **Service Accounts Enabled** to **ON**
11. Set **Authorization Enabled** to **OFF** (unless specifically needed)

#### Via Keycloak REST API:
```bash
# Get admin token
TOKEN=$(curl -X POST "https://keycloak.92.5.226.7.nip.io/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=YOUR_ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

# Update authentication flow to remove email verification
curl -X PUT "https://keycloak.92.5.226.7.nip.io/admin/realms/mcp/authentication/flows/browser/executions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "browser",
    "authenticationExecutions": [
      {
        "authenticator": "auth-cookie",
        "requirement": "ALTERNATIVE"
      },
      {
        "authenticator": "auth-spnego",
        "requirement": "DISABLED"
      },
      {
        "authenticator": "identity-provider-redirector",
        "requirement": "ALTERNATIVE"
      },
      {
        "flowAlias": "forms",
        "requirement": "ALTERNATIVE"
      }
    ]
  }'

# Remove all default required actions for new users
curl -X PUT "https://keycloak.92.5.226.7.nip.io/admin/realms/mcp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "registrationFlow": "registration",
    "requiredActions": [],
    "defaultDefaultClientScopes": ["web-origins", "profile", "roles", "email"],
    "defaultOptionalClientScopes": ["address", "phone", "offline_access", "microprofile-jwt"]
  }'
```

### Option 2: Fix Backend to Complete User Setup

The backend code needs to ensure complete user setup. The current implementation at `auth_endpoints.py` should be enhanced:

```python
async def setup_user_roles(client, admin_token: str, user_id: str, user_email: str):
    """Enhanced user setup to prevent 'Account is not fully set up' errors"""
    
    # 1. Clear all required actions
    user_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}"
    
    # Get current user data
    user_response = await client.get(
        user_url,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        
        # Update user with cleared required actions
        update_data = {
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "enabled": True,
            "emailVerified": EMAIL_VERIFIED_AUTO,
            "requiredActions": [],  # Clear ALL required actions
            "attributes": {
                **user_data.get("attributes", {}),
                "account_setup_complete": ["true"],
                "email_verified_auto": [str(EMAIL_VERIFIED_AUTO).lower()]
            }
        }
        
        await client.put(
            user_url,
            json=update_data,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
        )
    
    # 2. Ensure client roles are assigned
    client_id_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients"
    clients_response = await client.get(
        client_id_url,
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"clientId": "mcp-api"}
    )
    
    if clients_response.status_code == 200:
        clients = clients_response.json()
        if clients:
            client_uuid = clients[0]["id"]
            
            # Get available client roles
            client_roles_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/clients/{client_uuid}/roles"
            roles_response = await client.get(
                client_roles_url,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if roles_response.status_code == 200:
                available_roles = roles_response.json()
                
                # Assign all available client roles
                if available_roles:
                    user_client_roles_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/clients/{client_uuid}"
                    await client.post(
                        user_client_roles_url,
                        json=available_roles,
                        headers={
                            "Authorization": f"Bearer {admin_token}",
                            "Content-Type": "application/json"
                        }
                    )
```

### Option 3: Use Different Authentication Flow

Instead of using Resource Owner Password Credentials Grant, use the Authorization Code flow which handles account setup more gracefully:

1. Update client configuration to use Authorization Code flow
2. Implement proper OAuth2 redirect handling in the frontend
3. This allows Keycloak to handle any required account setup steps transparently

## Testing

After applying the fix, test with:

```bash
# Test with EMAIL_VERIFIED_AUTO=true
./test_auth.sh

# Test with EMAIL_VERIFIED_AUTO=false
./test_email_verification.sh
```

Expected results:
- Registration: ✅ Success
- Login: ✅ Returns access token
- No "Account is not fully set up" errors

## Environment Variables

Ensure these are properly set:
```bash
EMAIL_VERIFIED_AUTO=true
KEYCLOAK_URL=https://keycloak.92.5.226.7.nip.io
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-api
KEYCLOAK_CLIENT_SECRET=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P
```

## Key Findings

1. **Keycloak Configuration**: The realm must have NO required actions for new users when EMAIL_VERIFIED_AUTO=true
2. **Authentication Flow**: The browser flow must not enforce email verification
3. **Client Settings**: Direct Access Grants must be enabled for password grant type
4. **User Attributes**: Setting custom attributes alone is not sufficient - required actions must be cleared

## Conclusion

The EMAIL_VERIFIED_AUTO feature is correctly implemented in the backend. The issue is with Keycloak server configuration requiring additional setup steps even when email verification is disabled. The solution requires either:
1. Updating Keycloak server configuration (recommended)
2. Enhancing backend to fully complete user setup
3. Switching to Authorization Code flow

The root cause is that Keycloak's "Account is not fully set up" error occurs when ANY required action remains on the user account, not just email verification.