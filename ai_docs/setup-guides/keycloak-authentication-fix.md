# Keycloak Authentication Fix Guide

## Problem Summary
Users were experiencing 401 "Invalid credentials" errors when trying to login, even though registration appeared successful and accounts were being created in Keycloak.

## Root Cause Analysis

### Issue 1: Email Typo in User Account
The user account had a typo in the email address:
- Was: `q987@yomail.com` (missing 'p')
- Fixed to: `q987@yopmail.com`
- This caused login attempts to fail as the email didn't match

### Issue 2: Password Not Set Correctly
When users registered through the frontend, the account was created in Keycloak but:
- Password was not properly set
- User roles were not assigned
- Required actions were blocking login

### Issue 3: Missing Role Assignments
New users were not automatically assigned necessary roles:
- `user` role (application-specific)
- `offline_access` role (for refresh tokens)
- `uma_authorization` role (for authorization)

## Solution

### Fix Script: `fix_user_account.sh`
Created a script that:
1. Resets user password to a known value
2. Assigns all necessary roles
3. Clears required actions
4. Enables the account
5. Verifies login works

### Usage
```bash
# Fix a specific user account
./fix_user_account.sh <admin_password> <user_email>

# Example
./fix_user_account.sh P02tqbj016p9@@@ q987@yopmail.com
```

## Authentication Flow Verification

### 1. Registration Endpoint
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123!",
    "username": "testuser"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "user_id": "uuid",
  "email": "test@example.com",
  "username": "testuser",
  "message": "🎉 SUCCESS: Account created and you have been automatically logged in!",
  "auto_login_token": "jwt_token"
}
```

### 2. Login Endpoint
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123!"
  }'
```

**Expected Response:**
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "refresh_token": "refresh_token",
  "expires_in": 300,
  "user_id": "uuid",
  "email": "test@example.com"
}
```

## Configuration

### Environment Variables (.env.keycloak)
```bash
# Keycloak Admin Credentials
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=<admin_password>

# Keycloak URLs and Realm
KEYCLOAK_URL=https://keycloak.92.5.226.7.nip.io
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-api
KEYCLOAK_CLIENT_SECRET=<client_secret>

# Email Verification Setting
EMAIL_VERIFIED_AUTO=true
```

### Key Features
- **EMAIL_VERIFIED_AUTO=true**: Automatically marks email as verified during registration
- **Auto-login after registration**: Users receive JWT token immediately after registration
- **Role auto-assignment**: User roles assigned during registration process

## Troubleshooting

### Common Issues

#### 1. 401 Invalid Credentials
**Cause**: User password not set correctly or roles missing
**Fix**: Run `fix_user_account.sh` for the affected user

#### 2. Registration Success but Login Fails
**Cause**: Required actions blocking login
**Fix**: Script clears all required actions automatically

#### 3. Token Validation Errors
**Cause**: Client configuration mismatch
**Fix**: Ensure KEYCLOAK_CLIENT_SECRET matches Keycloak configuration

## Security Improvements Implemented

1. **Removed Hardcoded Passwords**: All scripts now use environment variables or command-line arguments
2. **Git History Cleaned**: Removed sensitive data from git history using orphan branch approach
3. **Environment File Protection**: Added .env.keycloak to .gitignore
4. **Template File**: Created .env.keycloak.example for safe sharing

## Testing Checklist

- [x] Registration creates user in Keycloak
- [x] Registration returns auto-login token
- [x] Login with registered user succeeds
- [x] Refresh token works correctly
- [x] User roles properly assigned
- [x] Email verification handled correctly

## Related Files
- `/fix_user_account.sh` - User account fix script
- `/fix_keycloak_complete.sh` - Complete Keycloak setup
- `agenthub_main/src/fastmcp/auth/interface/auth_endpoints.py` - Auth implementation
- `.env.keycloak` - Environment configuration (not in git)
- `.env.keycloak.example` - Configuration template