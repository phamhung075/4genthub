# MCP HTTP Client Configuration Guide

## Overview

This guide provides comprehensive configuration information for the MCP HTTP Client Module, including environment variables, Keycloak setup, cache configuration, and performance tuning parameters.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Keycloak Configuration](#keycloak-configuration)
- [Cache Configuration](#cache-configuration)
- [Performance Tuning](#performance-tuning)
- [Security Configuration](#security-configuration)
- [Network Configuration](#network-configuration)
- [Development vs Production](#development-vs-production)
- [Configuration Examples](#configuration-examples)
- [Troubleshooting](#troubleshooting)

---

## Environment Variables

### Server Configuration

#### MCP_SERVER_URL
- **Description**: Base URL for the MCP server
- **Default**: `http://localhost:8000`
- **Required**: Yes
- **Example**: `https://api.example.com`

```bash
export MCP_SERVER_URL=http://localhost:8000
```

#### MCP_SERVER_TIMEOUT
- **Description**: Request timeout in seconds
- **Default**: `10`
- **Range**: 1-300
- **Example**: `30`

```bash
export MCP_SERVER_TIMEOUT=30
```

### Authentication Configuration

#### KEYCLOAK_URL
- **Description**: Keycloak server base URL
- **Default**: `http://localhost:8080`
- **Required**: Yes
- **Format**: Full URL without trailing slash

```bash
export KEYCLOAK_URL=http://localhost:8080
```

#### KEYCLOAK_REALM
- **Description**: Keycloak realm name
- **Default**: `dhafnck`
- **Required**: Yes
- **Example**: `mcp-production`

```bash
export KEYCLOAK_REALM=dhafnck
```

#### KEYCLOAK_CLIENT_ID
- **Description**: Keycloak client ID for hooks
- **Default**: `claude-hooks`
- **Required**: Yes
- **Example**: `mcp-client`

```bash
export KEYCLOAK_CLIENT_ID=claude-hooks
```

#### KEYCLOAK_CLIENT_SECRET
- **Description**: Keycloak client secret
- **Default**: None
- **Required**: Yes (critical for authentication)
- **Security**: Never log or expose this value

```bash
export KEYCLOAK_CLIENT_SECRET=your-secret-here
```

#### TOKEN_REFRESH_BEFORE_EXPIRY
- **Description**: Seconds before expiry to refresh token
- **Default**: `60`
- **Range**: 30-300
- **Example**: `120`

```bash
export TOKEN_REFRESH_BEFORE_EXPIRY=60
```

### Cache Configuration

#### FALLBACK_CACHE_TTL
- **Description**: Fallback cache TTL in seconds
- **Default**: `3600` (1 hour)
- **Range**: 300-86400
- **Example**: `7200` (2 hours)

```bash
export FALLBACK_CACHE_TTL=3600
```

#### FALLBACK_STRATEGY
- **Description**: Fallback behavior when server unavailable
- **Default**: `cache_then_skip`
- **Options**:
  - `cache_then_skip`: Use cache, then continue without MCP
  - `cache_then_error`: Use cache, then raise error
  - `skip`: Always skip MCP functionality on error

```bash
export FALLBACK_STRATEGY=cache_then_skip
```

#### SESSION_CACHE_TTL
- **Description**: Session context cache TTL
- **Default**: `3600` (1 hour)
- **Range**: 300-7200
- **Example**: `1800` (30 minutes)

```bash
export SESSION_CACHE_TTL=3600
```

#### TASK_CACHE_TTL
- **Description**: Task data cache TTL
- **Default**: `900` (15 minutes)
- **Range**: 60-3600
- **Example**: `600` (10 minutes)

```bash
export TASK_CACHE_TTL=900
```

#### GIT_CACHE_TTL
- **Description**: Git status cache TTL
- **Default**: `300` (5 minutes)
- **Range**: 60-1800
- **Example**: `180` (3 minutes)

```bash
export GIT_CACHE_TTL=300
```

### Performance Configuration

#### RATE_LIMIT_REQUESTS_PER_MINUTE
- **Description**: Maximum requests per minute
- **Default**: `100`
- **Range**: 10-1000
- **Example**: `200`

```bash
export RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

#### HTTP_MAX_RETRIES
- **Description**: Maximum HTTP retry attempts
- **Default**: `3`
- **Range**: 0-10
- **Example**: `5`

```bash
export HTTP_MAX_RETRIES=3
```

#### HTTP_POOL_CONNECTIONS
- **Description**: HTTP connection pool size
- **Default**: `10`
- **Range**: 1-50
- **Example**: `20`

```bash
export HTTP_POOL_CONNECTIONS=10
```

#### HTTP_POOL_MAXSIZE
- **Description**: Maximum pool size per host
- **Default**: `10`
- **Range**: 1-100
- **Example**: `25`

```bash
export HTTP_POOL_MAXSIZE=10
```

---

## Keycloak Configuration

### Client Setup

#### 1. Create Client in Keycloak Admin Console

1. Navigate to Keycloak Admin Console
2. Select your realm (e.g., `dhafnck`)
3. Go to **Clients** → **Create Client**
4. Configure client settings:

```json
{
  "clientId": "claude-hooks",
  "enabled": true,
  "clientAuthenticatorType": "client-secret",
  "standardFlowEnabled": false,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": true,
  "publicClient": false,
  "protocol": "openid-connect"
}
```

#### 2. Configure Client Authentication

1. Go to **Clients** → **claude-hooks** → **Credentials**
2. Set **Client Authenticator** to `Client Id and Secret`
3. Copy the generated **Client Secret**
4. Set `KEYCLOAK_CLIENT_SECRET` environment variable

#### 3. Configure Service Account Roles

1. Go to **Clients** → **claude-hooks** → **Service Account Roles**
2. Assign required roles:
   - `realm-management` → `view-users`
   - `realm-management` → `view-clients`
   - Custom roles for MCP operations

#### 4. Configure Client Scopes

Create custom scopes for MCP operations:

```json
{
  "name": "mcp:read",
  "description": "Read access to MCP resources",
  "protocol": "openid-connect",
  "attributes": {
    "include.in.token.scope": "true"
  }
}
```

```json
{
  "name": "mcp:write", 
  "description": "Write access to MCP resources",
  "protocol": "openid-connect",
  "attributes": {
    "include.in.token.scope": "true"
  }
}
```

### Realm Configuration

#### Token Settings

1. Go to **Realm Settings** → **Tokens**
2. Configure token lifespans:

```yaml
Access Token Lifespan: 5 minutes
Access Token Lifespan For Implicit Flow: 15 minutes
Client Session Idle: 30 minutes
Client Session Max: 12 hours
```

#### Security Defenses

1. Go to **Realm Settings** → **Security Defenses**
2. Configure brute force protection:

```yaml
Max Login Failures: 5
Wait Increment: 60 seconds
Quick Login Check: 1000ms
Minimum Quick Login Wait: 60 seconds
```

---

## Cache Configuration

### Cache Directory Structure

```
~/.claude/
├── .mcp_token_cache           # JWT token cache
├── .mcp_fallback_cache.json   # Fallback data cache
└── .session_cache/            # Session context cache
    ├── abc123.json           # Task cache
    ├── def456.json           # Git status cache
    └── ghi789.json           # Project context cache
```

### Cache Manager Settings

```python
# Default cache configuration
{
    "default_ttl": 3600,        # 1 hour
    "max_cache_size": 50,       # 50 MB
    "cleanup_interval": 86400   # 24 hours
}
```

### Session-Specific Caches

```python
# Task cache settings
PENDING_TASKS_KEY = "mcp_pending_tasks"
TASK_CACHE_TTL = 900  # 15 minutes

# Git status cache
GIT_STATUS_KEY = "git_status" 
GIT_CACHE_TTL = 300   # 5 minutes

# Project context cache
PROJECT_CONTEXT_KEY = "project_context_{branch_id}"
PROJECT_CACHE_TTL = 3600  # 1 hour
```

### Cache Cleanup Configuration

#### Automatic Cleanup

```bash
# Enable automatic cleanup
export CACHE_CLEANUP_INTERVAL=86400  # 24 hours

# Set maximum cache size
export SESSION_CACHE_MAX_SIZE=50     # 50 MB
```

#### Manual Cleanup Commands

```bash
# Show cache statistics
python .claude/hooks/utils/cache_manager.py --stats

# Clean expired entries
python .claude/hooks/utils/cache_manager.py --cleanup

# Clear all cache
python .claude/hooks/utils/cache_manager.py --clear
```

---

## Performance Tuning

### Connection Pooling Optimization

#### For Low-Traffic Environments
```bash
export HTTP_POOL_CONNECTIONS=5
export HTTP_POOL_MAXSIZE=5
export RATE_LIMIT_REQUESTS_PER_MINUTE=50
```

#### For High-Traffic Environments
```bash
export HTTP_POOL_CONNECTIONS=25
export HTTP_POOL_MAXSIZE=50
export RATE_LIMIT_REQUESTS_PER_MINUTE=500
```

### Retry Strategy Tuning

#### Conservative (Stable Network)
```bash
export HTTP_MAX_RETRIES=2
export MCP_SERVER_TIMEOUT=10
```

#### Aggressive (Unreliable Network)
```bash
export HTTP_MAX_RETRIES=5
export MCP_SERVER_TIMEOUT=30
```

### Cache Strategy Optimization

#### Fast Response (More Cache Hits)
```bash
export TASK_CACHE_TTL=1800      # 30 minutes
export SESSION_CACHE_TTL=7200   # 2 hours
export FALLBACK_CACHE_TTL=7200  # 2 hours
```

#### Fresh Data (Less Cache Hits)
```bash
export TASK_CACHE_TTL=300       # 5 minutes
export SESSION_CACHE_TTL=1800   # 30 minutes
export FALLBACK_CACHE_TTL=1800  # 30 minutes
```

---

## Security Configuration

### Token Security Best Practices

#### Environment Variables
```bash
# Use secure environment file
echo "KEYCLOAK_CLIENT_SECRET=your-secret" > .env
chmod 600 .env
```

#### File Permissions
```bash
# Secure token cache file
chmod 600 ~/.claude/.mcp_token_cache
```

### Network Security

#### HTTPS Configuration
```bash
# Always use HTTPS in production
export KEYCLOAK_URL=https://keycloak.example.com
export MCP_SERVER_URL=https://api.example.com
```

#### Certificate Verification
```python
# Client configuration (in code)
verify = True  # Always verify SSL certificates
```

### Credential Management

#### Docker Secrets
```yaml
# docker-compose.yml
services:
  app:
    environment:
      KEYCLOAK_CLIENT_SECRET_FILE: /run/secrets/keycloak_secret
    secrets:
      - keycloak_secret

secrets:
  keycloak_secret:
    file: ./secrets/keycloak_client_secret.txt
```

#### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-client-secret
type: Opaque
data:
  KEYCLOAK_CLIENT_SECRET: <base64-encoded-secret>
```

---

## Network Configuration

### Proxy Configuration

```bash
# HTTP proxy settings
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1,.local

# Proxy authentication
export HTTP_PROXY=http://user:pass@proxy.example.com:8080
```

### DNS Configuration

```bash
# Custom DNS resolution
export KEYCLOAK_URL=http://keycloak.internal:8080
export MCP_SERVER_URL=http://mcp-server.internal:8000
```

### Firewall Configuration

#### Required Outbound Ports
- **8080**: Keycloak (HTTP)
- **8443**: Keycloak (HTTPS)
- **8000**: MCP Server (HTTP)
- **8443**: MCP Server (HTTPS)

#### Keycloak Endpoints
- `/auth/realms/{realm}/protocol/openid-connect/token`
- `/auth/realms/{realm}/protocol/openid-connect/userinfo`
- `/auth/realms/{realm}/protocol/openid-connect/certs`

#### MCP Server Endpoints
- `/mcp/manage_task`
- `/mcp/manage_context`
- `/mcp/manage_connection`

---

## Development vs Production

### Development Configuration

```bash
# Development .env file
export KEYCLOAK_URL=http://localhost:8080
export MCP_SERVER_URL=http://localhost:8000
export KEYCLOAK_REALM=dhafnck-dev
export KEYCLOAK_CLIENT_ID=claude-hooks-dev
export KEYCLOAK_CLIENT_SECRET=dev-secret-123

# Relaxed settings for development
export MCP_SERVER_TIMEOUT=30
export RATE_LIMIT_REQUESTS_PER_MINUTE=200
export HTTP_MAX_RETRIES=2
export FALLBACK_STRATEGY=cache_then_skip

# Shorter cache TTLs for testing
export TASK_CACHE_TTL=300
export SESSION_CACHE_TTL=900
```

### Production Configuration

```bash
# Production .env file
export KEYCLOAK_URL=https://keycloak.example.com
export MCP_SERVER_URL=https://api.example.com
export KEYCLOAK_REALM=dhafnck-prod
export KEYCLOAK_CLIENT_ID=claude-hooks-prod
export KEYCLOAK_CLIENT_SECRET=${PROD_CLIENT_SECRET}

# Optimized settings for production
export MCP_SERVER_TIMEOUT=15
export RATE_LIMIT_REQUESTS_PER_MINUTE=100
export HTTP_MAX_RETRIES=3
export FALLBACK_STRATEGY=cache_then_error

# Balanced cache TTLs
export TASK_CACHE_TTL=900
export SESSION_CACHE_TTL=3600
export FALLBACK_CACHE_TTL=3600

# Connection pooling
export HTTP_POOL_CONNECTIONS=20
export HTTP_POOL_MAXSIZE=40
```

### Staging Configuration

```bash
# Staging mirrors production but with relaxed limits
export KEYCLOAK_URL=https://keycloak-staging.example.com
export MCP_SERVER_URL=https://api-staging.example.com
export KEYCLOAK_REALM=dhafnck-staging
export KEYCLOAK_CLIENT_ID=claude-hooks-staging

# Staging-specific settings
export RATE_LIMIT_REQUESTS_PER_MINUTE=150
export HTTP_MAX_RETRIES=4
export FALLBACK_STRATEGY=cache_then_skip
```

---

## Configuration Examples

### Docker Compose Example

```yaml
version: '3.8'

services:
  mcp-client:
    image: mcp-client:latest
    environment:
      # Server Configuration
      MCP_SERVER_URL: http://mcp-server:8000
      MCP_SERVER_TIMEOUT: 15
      
      # Authentication
      KEYCLOAK_URL: http://keycloak:8080
      KEYCLOAK_REALM: dhafnck
      KEYCLOAK_CLIENT_ID: claude-hooks
      KEYCLOAK_CLIENT_SECRET_FILE: /run/secrets/client_secret
      
      # Performance
      RATE_LIMIT_REQUESTS_PER_MINUTE: 100
      HTTP_POOL_CONNECTIONS: 15
      HTTP_POOL_MAXSIZE: 30
      
      # Cache
      FALLBACK_CACHE_TTL: 3600
      TASK_CACHE_TTL: 900
      FALLBACK_STRATEGY: cache_then_skip
    
    volumes:
      - cache_volume:/home/user/.claude
    
    secrets:
      - client_secret
    
    depends_on:
      - keycloak
      - mcp-server

volumes:
  cache_volume:

secrets:
  client_secret:
    file: ./secrets/keycloak_client_secret.txt
```

### Kubernetes ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-client-config
data:
  MCP_SERVER_URL: "https://api.example.com"
  MCP_SERVER_TIMEOUT: "15"
  KEYCLOAK_URL: "https://keycloak.example.com"
  KEYCLOAK_REALM: "dhafnck"
  KEYCLOAK_CLIENT_ID: "claude-hooks"
  RATE_LIMIT_REQUESTS_PER_MINUTE: "100"
  HTTP_POOL_CONNECTIONS: "20"
  HTTP_POOL_MAXSIZE: "40"
  FALLBACK_CACHE_TTL: "3600"
  TASK_CACHE_TTL: "900"
  FALLBACK_STRATEGY: "cache_then_error"
```

### Environment File Template

```bash
# .env.template
# Copy to .env and fill in actual values

# ====================
# SERVER CONFIGURATION
# ====================
MCP_SERVER_URL=http://localhost:8000
MCP_SERVER_TIMEOUT=10

# ====================
# AUTHENTICATION
# ====================
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=dhafnck
KEYCLOAK_CLIENT_ID=claude-hooks
KEYCLOAK_CLIENT_SECRET=your-secret-here
TOKEN_REFRESH_BEFORE_EXPIRY=60

# ====================
# CACHE CONFIGURATION
# ====================
FALLBACK_CACHE_TTL=3600
FALLBACK_STRATEGY=cache_then_skip
SESSION_CACHE_TTL=3600
TASK_CACHE_TTL=900
GIT_CACHE_TTL=300

# ====================
# PERFORMANCE TUNING
# ====================
RATE_LIMIT_REQUESTS_PER_MINUTE=100
HTTP_MAX_RETRIES=3
HTTP_POOL_CONNECTIONS=10
HTTP_POOL_MAXSIZE=10
```

---

## Troubleshooting

### Common Configuration Issues

#### Authentication Failures
```bash
# Check Keycloak connectivity
curl -f "${KEYCLOAK_URL}/auth/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration"

# Test client credentials
curl -X POST "${KEYCLOAK_URL}/auth/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${KEYCLOAK_CLIENT_ID}&client_secret=${KEYCLOAK_CLIENT_SECRET}"
```

#### Connection Issues
```bash
# Test MCP server connectivity
curl -f "${MCP_SERVER_URL}/mcp/manage_connection"

# Check network connectivity
ping $(echo $MCP_SERVER_URL | sed 's|http[s]*://||' | cut -d: -f1)
```

#### Cache Issues
```bash
# Check cache directory permissions
ls -la ~/.claude/
ls -la ~/.claude/.session_cache/

# Test cache functionality
python .claude/hooks/utils/cache_manager.py --test
```

### Configuration Validation

#### Environment Variable Check
```bash
#!/bin/bash
# validate_config.sh

required_vars=(
    "KEYCLOAK_URL"
    "KEYCLOAK_REALM"
    "KEYCLOAK_CLIENT_ID"
    "KEYCLOAK_CLIENT_SECRET"
    "MCP_SERVER_URL"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required variable: $var"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

echo "Configuration validation passed!"
```

#### Connection Test Script
```python
#!/usr/bin/env python3
# test_config.py

import os
from utils.mcp_client import test_mcp_connection

def validate_environment():
    """Validate all required environment variables"""
    required_vars = [
        'KEYCLOAK_URL',
        'KEYCLOAK_REALM', 
        'KEYCLOAK_CLIENT_ID',
        'KEYCLOAK_CLIENT_SECRET',
        'MCP_SERVER_URL'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("✅ All required environment variables present")
    return True

if __name__ == "__main__":
    if validate_environment():
        print("🔌 Testing MCP connection...")
        if test_mcp_connection():
            print("✅ Configuration validation successful!")
        else:
            print("❌ Connection test failed")
```

This configuration guide provides comprehensive setup information for all aspects of the MCP HTTP Client Module, ensuring proper deployment and optimal performance across different environments.