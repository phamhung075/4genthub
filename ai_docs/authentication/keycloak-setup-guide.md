# Keycloak Authentication Setup Guide

## Overview
The agenthub system uses Keycloak for authentication when `AUTH_ENABLED=true` in `.env.dev`.

## Current Issue
You're seeing "401 Unauthorized" errors because:
1. Authentication is enabled (`AUTH_ENABLED=true`)
2. No valid users exist in Keycloak
3. The frontend is trying to access protected endpoints without valid credentials

## Solutions

### Option 1: Disable Authentication (Development Only)
For quick development without authentication:

```bash
# Run the toggle script
python toggle_auth.py off

# Or manually edit .env.dev
# Change: AUTH_ENABLED=true
# To: AUTH_ENABLED=false

# Restart the backend
pkill -f 'python.*mcp_entry_point'
python agenthub_main/src/fastmcp/server/mcp_entry_point.py
```

### Option 2: Create a User in Keycloak (Recommended)

#### Access Keycloak Admin Console
1. Open: https://keycloak.92.5.226.7.nip.io or https://keycloak.4genthub.com
2. Login with admin credentials

#### Create a User
1. Navigate to the `mcp` realm
2. Go to Users → Add User
3. Fill in:
   - Username: `testuser` (or your email)
   - Email: `test@example.com`
   - Email Verified: ON
4. Click Save

#### Set User Password
1. Go to Credentials tab
2. Set Password: `your-password`
3. Temporary: OFF (important!)
4. Click Set Password

#### Test Login via API
```bash
# Test with curl
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "your-password"
  }'
```

### Option 3: Use the Registration Flow

If registration is enabled in Keycloak:

```bash
# Register a new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123!",
    "username": "newuser"
  }'
```

## Authentication Flow

### Login Request
```javascript
// Frontend sends:
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

// Backend returns:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 300,
  "user_id": "uuid",
  "email": "user@example.com"
}
```

### Using the Token
The frontend automatically:
1. Stores tokens in cookies
2. Adds `Authorization: Bearer {token}` header to API requests
3. Refreshes tokens when they expire

### Protected Endpoints
All `/api/v2/` endpoints require authentication:
- `/api/v2/projects/` - User's projects
- `/api/v2/tasks/` - User's tasks
- `/api/v2/agents/` - User's agents
- `/api/v2/contexts/` - User's contexts

## Troubleshooting

### 401 Unauthorized on Login
- **Cause**: Invalid credentials
- **Solution**: Create a user in Keycloak or use correct credentials

### 401 Unauthorized on API Calls
- **Cause**: No token or expired token
- **Solution**: Login first or refresh token

### CORS Issues
- **Cause**: Frontend and backend on different ports
- **Solution**: Backend should already have CORS configured for localhost:3800

### Token Not Being Set
- **Cause**: Login failing silently
- **Solution**: Check browser console and network tab for errors

## Environment Variables

### Required for Keycloak (.env.dev)
```bash
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://keycloak.92.5.226.7.nip.io
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-api
KEYCLOAK_CLIENT_SECRET=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P
```

### Frontend Configuration
The frontend expects tokens in cookies:
- `access_token` - JWT access token
- `refresh_token` - JWT refresh token

## Quick Commands

### Check Authentication Status
```bash
curl http://localhost:8000/health | jq '.auth_enabled'
```

### Test Login
```bash
python test_keycloak_auth.py
```

### Toggle Authentication
```bash
# Disable
python toggle_auth.py off

# Enable
python toggle_auth.py on
```

## Security Notes
- **Never disable authentication in production**
- **Always use HTTPS in production**
- **Keep client secrets secure**
- **Rotate tokens regularly**
- **Use strong passwords**