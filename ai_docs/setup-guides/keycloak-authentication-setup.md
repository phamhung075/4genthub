# Keycloak Authentication Setup Guide

## Overview

This guide provides step-by-step instructions for setting up Keycloak authentication with the 4genthub platform.

## Prerequisites

- Keycloak instance (cloud or self-hosted)
- PostgreSQL database configured
- Docker environment set up
- Admin access to Keycloak

## Step 1: Keycloak Configuration

### 1.1 Create Realm

1. Log in to Keycloak Admin Console
2. Create a new realm named `mcp` (or use your preferred name)
3. Configure realm settings:
   - Display name: "4genthub"
   - Enable user registration if needed
   - Set token lifespans:
     - Access Token: 30 minutes
     - Refresh Token: 7 days

### 1.2 Create Client

1. Navigate to Clients → Create
2. Create client with:
   - Client ID: `mcp-backend`
   - Client Protocol: `openid-connect`
   - Root URL: `http://localhost:8000` (adjust for production)

3. Configure client settings:
   - Access Type: `confidential`
   - Standard Flow Enabled: `ON`
   - Direct Access Grants Enabled: `ON`
   - Service Accounts Enabled: `ON`
   - Valid Redirect URIs: 
     - `http://localhost:8000/*`
     - `http://localhost:3800/*` (frontend)

4. Save and go to Credentials tab
5. Copy the Secret value for `KEYCLOAK_CLIENT_SECRET`

### 1.3 Create Roles

Create the following realm roles:

1. **mcp-admin**
   - Description: Full system administrator access
   - Composite: No

2. **mcp-developer**
   - Description: Developer with project management access
   - Composite: No

3. **mcp-tools**
   - Description: Can execute MCP tools
   - Composite: No

4. **mcp-user**
   - Description: Basic user with read-only access
   - Composite: No

### 1.4 Create Groups (Optional)

For easier role management, create groups:

1. **Administrators**
   - Assign role: `mcp-admin`

2. **Developers**
   - Assign roles: `mcp-developer`, `mcp-tools`

3. **Users**
   - Assign role: `mcp-user`

### 1.5 Configure Mappers

Add protocol mappers for the client:

1. **Roles Mapper**
   - Name: `realm-roles`
   - Mapper Type: `User Realm Role`
   - Token Claim Name: `realm_access.roles`
   - Add to ID token: `ON`
   - Add to access token: `ON`

2. **Email Mapper**
   - Name: `email`
   - Mapper Type: `User Property`
   - Property: `email`
   - Token Claim Name: `email`

## Step 2: 4genthub Configuration

### 2.1 Update .env File

```bash
# Authentication Configuration
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak

# Keycloak Settings (replace with your values)
KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here

# Keycloak Options
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
KEYCLOAK_SSL_VERIFY=true

# JWT Configuration
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 2.2 Verify Configuration

Run the configuration test script:

```bash
cd 4genthub_main
python scripts/test/test-keycloak-mcp-clean.py
```

Expected output:
```
✅ Keycloak is accessible
✅ Realm configuration valid
✅ Client configured correctly
✅ Authentication test passed
```

## Step 3: User Setup

### 3.1 Create Test Users

1. In Keycloak, go to Users → Add User
2. Create users with different roles:

**Admin User:**
- Username: `admin`
- Email: `admin@example.com`
- Role: `mcp-admin`

**Developer User:**
- Username: `developer`
- Email: `dev@example.com`
- Roles: `mcp-developer`, `mcp-tools`

**Regular User:**
- Username: `user`
- Email: `user@example.com`
- Role: `mcp-user`

### 3.2 Set Passwords

1. Go to each user's Credentials tab
2. Set a temporary password
3. Set "Temporary" to OFF if you don't want forced password change

## Step 4: Start Services

### 4.1 Start Backend with Authentication

```bash
# Using Docker
docker-compose up -d

# Or using quick start script
./4genthub_main/scripts/quick_start_postgres_keycloak.sh
```

### 4.2 Verify Authentication

Test authentication endpoint:

```bash
# Get access token
curl -X POST https://your-keycloak/realms/mcp/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=mcp-backend" \
  -d "client_secret=your-secret" \
  -d "grant_type=password" \
  -d "username=developer" \
  -d "password=your-password"

# Use token with MCP
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8001/health
```

## Step 5: Frontend Configuration

### 5.1 Update Frontend Environment

Create/update `4genthub-frontend/.env`:

```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_KEYCLOAK_URL=https://your-keycloak-instance.com
REACT_APP_KEYCLOAK_REALM=mcp
REACT_APP_KEYCLOAK_CLIENT_ID=mcp-frontend
```

### 5.2 Create Frontend Client in Keycloak

1. Create another client for frontend:
   - Client ID: `mcp-frontend`
   - Access Type: `public`
   - Root URL: `http://localhost:3800`
   - Valid Redirect URIs: `http://localhost:3800/*`
   - Web Origins: `*`

## Step 6: Testing Authentication Flow

### 6.1 Test Login Flow

```python
import httpx
import asyncio

async def test_login():
    # Login
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/auth/login",
            json={
                "username": "developer",
                "password": "your-password"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful")
            print(f"Access Token: {data['access_token'][:50]}...")
            print(f"Roles: {data['roles']}")
            print(f"MCP Permissions: {data['mcp_permissions']}")
        else:
            print(f"❌ Login failed: {response.status_code}")

asyncio.run(test_login())
```

### 6.2 Test MCP Tool Access

```python
async def test_mcp_access(token):
    async with httpx.AsyncClient() as client:
        # Test task management
        response = await client.post(
            "http://localhost:8001/mcp/tools/manage_task",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "list",
                "git_branch_id": "test-branch"
            }
        )
        
        if response.status_code == 200:
            print("✅ MCP tool access granted")
        elif response.status_code == 403:
            print("❌ Access denied - insufficient permissions")
        else:
            print(f"❌ Error: {response.status_code}")
```

## Step 7: Production Deployment

### 7.1 Security Checklist

- [ ] Use HTTPS for all endpoints
- [ ] Enable SSL verification (`KEYCLOAK_SSL_VERIFY=true`)
- [ ] Use strong client secrets (min 32 characters)
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Set up monitoring and alerts
- [ ] Regular security updates

### 7.2 Performance Optimization

- [ ] Enable token caching
- [ ] Configure connection pooling
- [ ] Set appropriate cache TTLs
- [ ] Use Redis for session storage
- [ ] Enable GZIP compression

### 7.3 High Availability

- [ ] Multiple Keycloak instances
- [ ] Database replication
- [ ] Load balancing
- [ ] Session affinity
- [ ] Health checks

## Troubleshooting

### Common Issues and Solutions

#### 1. "Invalid token" errors
- Check token expiry
- Verify Keycloak URL is correct
- Ensure client secret matches
- Check realm configuration

#### 2. "Insufficient permissions" errors
- Verify user has correct roles
- Check role mappings in Keycloak
- Ensure token includes roles claim
- Review MCP permission mappings

#### 3. Connection errors
- Verify Keycloak is accessible
- Check firewall rules
- Ensure SSL certificates are valid
- Test with curl first

#### 4. CORS errors
- Add frontend URL to Valid Redirect URIs
- Configure Web Origins in Keycloak client
- Update CORS_ORIGINS in backend .env

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG
KEYCLOAK_DEBUG=true
```

Check logs:
```bash
docker-compose logs -f backend
```

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Specification](https://openid.net/connect/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [4genthub Authentication Architecture](../CORE%20ARCHITECTURE/authentication-system-current.md)