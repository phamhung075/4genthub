# Keycloak Email Verification Configuration Guide

## Overview
This guide explains how to configure Keycloak to work with the `EMAIL_VERIFIED_AUTO` environment variable, allowing users to register and login without email verification when enabled.

## Problem
When `EMAIL_VERIFIED_AUTO=true` is set in the backend, users can register successfully but cannot login due to Keycloak's email verification requirements conflicting with the auto-verification setting.

## Solution Steps

### Option 1: Update via Keycloak Admin Console (Recommended)

1. **Access Keycloak Admin Console**
   ```
   URL: https://keycloak.92.5.226.7.nip.io/admin
   ```

2. **Navigate to Realm Settings**
   - Select the `mcp` realm
   - Go to "Realm Settings" → "Login" tab

3. **Disable Email Verification Requirement**
   - Find "Verify email" setting
   - Toggle it to **OFF**
   - Click "Save"

4. **Update Client Configuration**
   - Go to "Clients" → "mcp-api"
   - Verify client secret is: `AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P`
   - Add redirect URI: `http://localhost:3800/*`
   - Click "Save"

5. **Configure User Profile (Optional)**
   - Go to "Realm Settings" → "User Profile"
   - Ensure email field doesn't have "Required for user creation" if you want optional emails

### Option 2: Import Updated Realm Configuration

1. **Export Current Configuration (Backup)**
   ```bash
   # If you have access to Keycloak container
   docker exec keycloak-container /opt/keycloak/bin/kc.sh export \
     --file /tmp/realm-backup.json \
     --realm mcp
   ```

2. **Import Updated Configuration**
   ```bash
   # The realm-config-keycloak.json has been updated with:
   # - "verifyEmail": false
   # - Correct client secret
   # - Added localhost:3800 redirect URI
   
   # Import via Admin Console:
   # Go to "Realm Settings" → "Action" → "Partial Import"
   # Upload the updated realm-config-keycloak.json
   ```

### Option 3: Manual API Update

```bash
# Get admin token
TOKEN=$(curl -X POST "https://keycloak.92.5.226.7.nip.io/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=YOUR_ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

# Update realm to disable email verification
curl -X PUT "https://keycloak.92.5.226.7.nip.io/admin/realms/mcp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "verifyEmail": false,
    "loginWithEmailAllowed": true,
    "registrationEmailAsUsername": false
  }'
```

## How EMAIL_VERIFIED_AUTO Works

### Backend Behavior
When `EMAIL_VERIFIED_AUTO=true`:
1. New users are created with `emailVerified: true` in Keycloak
2. Users can immediately login without verifying email
3. The backend automatically marks emails as verified during registration

### Required Keycloak Settings
For this to work properly, Keycloak must have:
- `verifyEmail: false` in realm settings
- No required actions forcing email verification
- Client configured with correct secret and redirect URIs

## Testing the Configuration

1. **Test Registration and Login**
   ```bash
   # Run the test script
   ./test_auth.sh
   ```

2. **Expected Result**
   - Registration: ✅ Success
   - Login: ✅ Returns access token
   - User can access protected resources immediately

## Environment Variables

### Backend (.env.dev)
```env
# Enable automatic email verification
EMAIL_VERIFIED_AUTO=true

# Keycloak settings
KEYCLOAK_URL=https://keycloak.92.5.226.7.nip.io
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-api
KEYCLOAK_CLIENT_SECRET=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P
```

### Docker Compose
```yaml
environment:
  EMAIL_VERIFIED_AUTO: ${EMAIL_VERIFIED_AUTO:-true}
```

## Troubleshooting

### Issue: "Account is not fully set up"
**Cause**: Keycloak realm has `verifyEmail: true` while backend sets `emailVerified: true`
**Solution**: Disable email verification in Keycloak realm settings

### Issue: "Invalid client secret"  
**Cause**: Client secret mismatch between backend and Keycloak
**Solution**: Verify client secret in Keycloak matches environment variable

### Issue: "Invalid redirect URI"
**Cause**: Frontend URL not in allowed redirect URIs
**Solution**: Add `http://localhost:3800/*` to client redirect URIs

## Summary

The `EMAIL_VERIFIED_AUTO` feature is fully implemented in the backend code. To make it work end-to-end:

1. ✅ Backend creates users with `emailVerified: true` when `EMAIL_VERIFIED_AUTO=true`
2. ✅ Environment variables configured in all necessary files
3. ⚠️ **Keycloak admin configuration must be updated** to disable email verification requirement
4. ✅ Test script available to verify functionality

Once the Keycloak admin configuration is updated, users will be able to register and immediately login without email verification when `EMAIL_VERIFIED_AUTO=true`.