# Keycloak Authentication Setup for DhafnckMCP

## Overview

DhafnckMCP now uses Keycloak as the primary authentication provider, integrated with PostgreSQL Docker for local development. This guide explains the setup and configuration.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  MCP Server  │────▶│  PostgreSQL │
│   (API)     │     │   (Port 8001) │     │   (Docker)  │
└─────────────┘     └──────────────┘     └─────────────┘
        │                  │
        │                  │
        ▼                  ▼
┌─────────────────────────────┐
│     Keycloak Server         │
│   (Local: localhost:8080)   │
└─────────────────────────────┘
```

## Quick Start

### 1. Start PostgreSQL Docker

```bash
docker-compose -f docker-compose.simple.yml up -d postgres
```

### 2. Configure Environment

Ensure your `.env` file has:

```env
# Database Configuration (PostgreSQL Docker)
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_SSL_MODE=disable

# Keycloak Configuration
KEYCLOAK_URL=http://10.156.235.113:8080
KEYCLOAK_EXTERNAL_URL=http://localhost:8080
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=pcSnE1ODLwQocjjbz2A54sxZcl3DRoYw

# MCP Configuration
MCP_PORT=8001
AUTH_ENABLED=true
```

### 3. Start MCP Server

```bash
# Use the provided startup script
./start_mcp_with_keycloak.sh

# Or manually
cd dhafnck_mcp_main/src
python mcp_http_server.py
```

## Authentication Flow

### 1. Login

```python
import httpx

# Login to get access token
response = httpx.post(
    "http://localhost:8001/auth/login",
    params={
        "username": "your-username",
        "password": "your-password"
    }
)
token_data = response.json()
access_token = token_data["access_token"]
```

### 2. Use MCP Tools with Token

```python
# Use token in Authorization header
headers = {"Authorization": f"Bearer {access_token}"}

# Call MCP endpoints
response = httpx.post(
    "http://localhost:8001/mcp/manage_task",
    headers=headers,
    json={"action": "list"}
)
```

### 3. Refresh Token

```python
# Refresh when token expires
response = httpx.post(
    "http://localhost:8001/auth/refresh",
    params={"refresh_token": token_data["refresh_token"]}
)
new_token_data = response.json()
```

## Keycloak Roles and Permissions

### Required Roles

- `mcp-user` - Basic MCP access
- `mcp-tools` - Execute MCP tools
- `mcp-developer` - Full development access
- `mcp-admin` - Administrative access

### Permission Mapping

| Role | Permissions |
|------|------------|
| mcp-admin | Full access to all tools and operations |
| mcp-developer | tools:*, context:*, agents:*, projects:* |
| mcp-tools | tools:execute, tools:list, context:read/write |
| mcp-user | tools:list, tools:describe, context:read |

## Setting Up Keycloak

### 1. Create Realm

1. Access Keycloak Admin Console
2. Create new realm: `mcp`

### 2. Create Client

1. Navigate to Clients
2. Create client:
   - Client ID: `mcp-backend`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
3. Configure:
   - Valid Redirect URIs: `http://localhost:8001/*`
   - Web Origins: `http://localhost:8001`
4. Copy client secret to `.env`

### 3. Create Roles

1. Navigate to Roles
2. Create roles:
   - `mcp-admin`
   - `mcp-developer`
   - `mcp-tools`
   - `mcp-user`

### 4. Create Test User

1. Navigate to Users
2. Create user
3. Set password
4. Assign roles

## Testing

### Run Test Script

```bash
cd dhafnck_mcp_main
python test_keycloak_mcp.py
```

### Expected Output

```
MCP KEYCLOAK INTEGRATION TEST
==============================================================
1. Testing Health Check...
   Status: 200
   
2. Testing Keycloak Login...
   Status: 200
   Access Token: eyJhbGciOiJSUzI1NiIsInR5cCI...
   
3. Testing MCP Tools List...
   Status: 200
   Available Tools: 15
   
All tests passed! ✅
```

## Troubleshooting

### Cannot Connect to Keycloak

1. Check Keycloak is running
2. Verify KEYCLOAK_URL in .env
3. Test connectivity: `curl http://localhost:8080/realms/mcp`

### Authentication Failed

1. Verify client secret in .env
2. Check user credentials
3. Ensure user has required roles

### Database Connection Issues

1. Ensure PostgreSQL Docker is running
2. Check DATABASE_* environment variables
3. Verify database is initialized

### MCP Tools Not Working

1. Check token has required permissions
2. Verify AUTH_ENABLED setting
3. Check server logs for errors

## Development Mode

To disable authentication for development:

```env
AUTH_ENABLED=false
```

This will bypass Keycloak and use a mock user.

## API Endpoints

### Authentication

- `POST /auth/login` - Login with username/password
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (requires token)
- `GET /auth/userinfo` - Get user info (requires token)

### MCP Tools (all require authentication)

- `GET /mcp/tools` - List available tools
- `POST /mcp/manage_task` - Task management
- `POST /mcp/manage_context` - Context management
- `POST /mcp/manage_project` - Project management
- `POST /mcp/manage_git_branch` - Git branch management
- `POST /mcp/manage_agent` - Agent management
- `POST /mcp/call_agent` - Call AI agents
- `POST /mcp/manage_compliance` - Compliance management

## Security Notes

1. **Never commit secrets** - Keep `.env` out of version control
2. **Use HTTPS in production** - Configure SSL/TLS for Keycloak
3. **Rotate secrets regularly** - Update client secrets periodically
4. **Monitor access logs** - Track authentication attempts
5. **Implement rate limiting** - Prevent brute force attacks

## Migration from Supabase

This setup replaces the previous Supabase authentication with Keycloak:

- ✅ No dependency on Supabase cloud services
- ✅ Direct PostgreSQL connection for data
- ✅ Keycloak for enterprise-grade authentication
- ✅ Role-based access control (RBAC)
- ✅ Standard OAuth2/OIDC protocols

## Support

For issues or questions:
1. Check server logs: `dhafnck_mcp_main/logs/`
2. Review this documentation
3. Test with the provided test script
4. Verify environment configuration