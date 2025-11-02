# Environment Variables - Agent Management System

**Version**: 2.0.0
**Last Updated**: 2025-11-02

## Overview

Complete reference for all environment variables required by the agent management system. Variables are organized by category and include default values, validation rules, and usage examples.

---

## Core Application Variables

### DATABASE_URL
**Required**: Yes
**Type**: String (PostgreSQL connection string)
**Default**: None
**Format**: `postgresql://user:password@host:port/database`

**Description**: Primary database connection string

**Example**:
```bash
DATABASE_URL=postgresql://agenthub_user:secure_password@db.example.com:5432/agenthub
```

**Validation**:
- Must be valid PostgreSQL connection string
- Database must exist and be accessible
- User must have CREATE, SELECT, INSERT, UPDATE, DELETE permissions

---

### REDIS_URL
**Required**: Yes (for caching and sessions)
**Type**: String (Redis connection string)
**Default**: `redis://localhost:6379/0`
**Format**: `redis://[user:password@]host:port/database`

**Description**: Redis connection for caching and session management

**Example**:
```bash
# Without authentication
REDIS_URL=redis://localhost:6379/0

# With authentication
REDIS_URL=redis://:password@redis.example.com:6379/0

# Redis Cluster
REDIS_URL=redis://redis.example.com:6379/0?cluster=true
```

**Validation**:
- Must be reachable Redis instance
- Database number (0-15) must be valid

---

### SECRET_KEY
**Required**: Yes
**Type**: String (cryptographic key)
**Default**: None
**Min Length**: 32 characters

**Description**: Application secret key for signing sessions and tokens

**Example**:
```bash
# Generate secure key (recommended)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Result example
SECRET_KEY=abc123XYZ789_very_secure_random_string_here_456DEF
```

**Validation**:
- Minimum 32 characters
- Should be cryptographically random
- Must never be committed to version control
- Different key per environment (dev/staging/prod)

**Security Notes**:
- ⚠️ Changing this key invalidates all existing sessions
- ⚠️ Store in secrets manager (AWS Secrets Manager, Vault, etc.)
- ⚠️ Rotate regularly (quarterly recommended)

---

### JWT_SECRET_KEY
**Required**: Yes
**Type**: String (cryptographic key)
**Default**: None
**Min Length**: 32 characters

**Description**: Secret key for signing JWT authentication tokens

**Example**:
```bash
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

**Validation**:
- Same requirements as SECRET_KEY
- Should be different from SECRET_KEY
- Rotate independently from SECRET_KEY

---

## Agent Management Specific Variables

### AGENT_LIBRARY_PATH
**Required**: Yes
**Type**: String (filesystem path)
**Default**: `./agent-library`

**Description**: Path to agent-library directory containing YAML templates

**Example**:
```bash
# Development
AGENT_LIBRARY_PATH=/home/user/projects/agenthub/agent-library

# Docker container
AGENT_LIBRARY_PATH=/app/agent-library

# Production (mounted volume)
AGENT_LIBRARY_PATH=/mnt/shared/agent-library
```

**Validation**:
- Directory must exist
- Must contain `agents/` subdirectory
- Must be readable by application user

**Structure Expected**:
```
AGENT_LIBRARY_PATH/
└── agents/
    ├── coding-agent/
    │   ├── metadata.yaml
    │   └── contexts/
    ├── test-orchestrator-agent/
    └── ...
```

---

### ENABLE_AGENT_MARKETPLACE
**Required**: No
**Type**: Boolean
**Default**: `true`
**Valid Values**: `true`, `false`, `1`, `0`, `yes`, `no`

**Description**: Enable/disable public agent marketplace features

**Example**:
```bash
# Enable marketplace (default)
ENABLE_AGENT_MARKETPLACE=true

# Disable marketplace (private deployment)
ENABLE_AGENT_MARKETPLACE=false
```

**Impact**:
- `false`: Disables marketplace browsing and public sharing
- `false`: Users can still import via direct share tokens
- `false`: `/marketplace/agents` endpoint returns 404

---

### MAX_AGENT_IMPORT_PER_MINUTE
**Required**: No
**Type**: Integer
**Default**: `10`
**Min**: `1`
**Max**: `100`

**Description**: Rate limit for agent imports per user per minute

**Example**:
```bash
# Default rate limit
MAX_AGENT_IMPORT_PER_MINUTE=10

# More restrictive (small deployment)
MAX_AGENT_IMPORT_PER_MINUTE=5

# More permissive (enterprise)
MAX_AGENT_IMPORT_PER_MINUTE=50
```

**Validation**:
- Must be positive integer
- Recommended: 5-20 for production
- Higher values increase DoS risk

---

### SHARE_TOKEN_EXPIRY_DAYS
**Required**: No
**Type**: Integer
**Default**: `365` (1 year)
**Min**: `1`
**Max**: `3650` (10 years)

**Description**: Default expiration time for share tokens (days)

**Example**:
```bash
# Default (1 year)
SHARE_TOKEN_EXPIRY_DAYS=365

# Shorter expiry (90 days)
SHARE_TOKEN_EXPIRY_DAYS=90

# No expiry (not recommended for security)
SHARE_TOKEN_EXPIRY_DAYS=3650
```

**Notes**:
- Tokens can be revoked manually anytime
- Expiry is soft delete (data retained for audit)
- 0 or negative values disable expiry

---

### MAX_CUSTOMIZATION_SIZE_KB
**Required**: No
**Type**: Integer
**Default**: `500` (500KB)
**Min**: `10`
**Max**: `5000` (5MB)

**Description**: Maximum size for agent customization content (KB)

**Example**:
```bash
# Default
MAX_CUSTOMIZATION_SIZE_KB=500

# Larger (for complex agents)
MAX_CUSTOMIZATION_SIZE_KB=1000
```

**Validation**:
- Applies to combined markdown content
- Prevents DoS via large payloads
- Database TEXT fields support up to 1GB (PostgreSQL)

---

## Database Configuration

### DB_POOL_SIZE
**Required**: No
**Type**: Integer
**Default**: `20`
**Min**: `5`
**Max**: `100`

**Description**: SQLAlchemy connection pool size

**Example**:
```bash
# Default
DB_POOL_SIZE=20

# High traffic (increase)
DB_POOL_SIZE=50

# Low resources (decrease)
DB_POOL_SIZE=10
```

**Guidelines**:
- Formula: `(CPU cores * 2) + effective_spindle_count`
- Monitor pool exhaustion: `pool_timeout` errors
- Increase if seeing connection timeouts

---

### DB_POOL_TIMEOUT
**Required**: No
**Type**: Integer (seconds)
**Default**: `30`

**Description**: Timeout waiting for connection from pool

**Example**:
```bash
DB_POOL_TIMEOUT=30
```

---

### DB_POOL_RECYCLE
**Required**: No
**Type**: Integer (seconds)
**Default**: `3600` (1 hour)

**Description**: Recycle connections after this time

**Example**:
```bash
# Recycle every hour
DB_POOL_RECYCLE=3600

# More aggressive (cloud databases with connection limits)
DB_POOL_RECYCLE=1800
```

---

## Logging and Monitoring

### LOG_LEVEL
**Required**: No
**Type**: String
**Default**: `INFO`
**Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Description**: Application logging level

**Example**:
```bash
# Production
LOG_LEVEL=INFO

# Development/Debug
LOG_LEVEL=DEBUG

# Minimal logging
LOG_LEVEL=WARNING
```

---

### SENTRY_DSN
**Required**: No (recommended for production)
**Type**: String (Sentry DSN)
**Default**: None

**Description**: Sentry error tracking DSN

**Example**:
```bash
SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/789012
```

**Features Enabled**:
- Automatic error reporting
- Performance monitoring
- Release tracking
- User feedback

---

### DATADOG_API_KEY
**Required**: No
**Type**: String
**Default**: None

**Description**: DataDog API key for metrics and monitoring

**Example**:
```bash
DATADOG_API_KEY=abc123def456ghi789
```

---

## Security Settings

### CORS_ORIGINS
**Required**: No
**Type**: String (comma-separated URLs)
**Default**: `*` (allow all - development only!)

**Description**: Allowed CORS origins for API requests

**Example**:
```bash
# Production (specific domains)
CORS_ORIGINS=https://app.example.com,https://dashboard.example.com

# Development (allow all)
CORS_ORIGINS=*

# Multiple environments
CORS_ORIGINS=https://app.prod.com,https://app.staging.com,http://localhost:3000
```

**Security**:
- ⚠️ Never use `*` in production
- Specify exact origins (include protocol and port)
- No trailing slashes

---

### CSRF_SECRET_KEY
**Required**: Recommended for production
**Type**: String
**Default**: Uses SECRET_KEY if not set

**Description**: Separate key for CSRF token generation

**Example**:
```bash
CSRF_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

### SESSION_COOKIE_SECURE
**Required**: No
**Type**: Boolean
**Default**: `true` (production), `false` (development)

**Description**: Require HTTPS for session cookies

**Example**:
```bash
# Production (HTTPS required)
SESSION_COOKIE_SECURE=true

# Development (HTTP allowed)
SESSION_COOKIE_SECURE=false
```

---

## Performance Tuning

### CACHE_TTL_SECONDS
**Required**: No
**Type**: Integer
**Default**: `3600` (1 hour)

**Description**: Default cache TTL for agent templates

**Example**:
```bash
# 1 hour (default)
CACHE_TTL_SECONDS=3600

# 5 minutes (frequent updates)
CACHE_TTL_SECONDS=300

# 24 hours (stable templates)
CACHE_TTL_SECONDS=86400
```

---

### ENABLE_QUERY_CACHING
**Required**: No
**Type**: Boolean
**Default**: `true`

**Description**: Enable SQLAlchemy query result caching

**Example**:
```bash
ENABLE_QUERY_CACHING=true
```

---

## Feature Flags

### ENABLE_AGENT_IMPORT
**Required**: No
**Type**: Boolean
**Default**: `true`

**Description**: Enable agent import functionality

**Example**:
```bash
# Enabled (default)
ENABLE_AGENT_IMPORT=true

# Disabled (read-only marketplace)
ENABLE_AGENT_IMPORT=false
```

---

### ENABLE_AGENT_SHARING
**Required**: No
**Type**: Boolean
**Default**: `true`

**Description**: Enable agent sharing functionality

**Example**:
```bash
ENABLE_AGENT_SHARING=true
```

---

## Environment-Specific Configurations

### Development (.env.dev)

```bash
# Core
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/agenthub_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-not-for-production
JWT_SECRET_KEY=dev-jwt-key-not-for-production

# Agent Management
AGENT_LIBRARY_PATH=./agent-library
ENABLE_AGENT_MARKETPLACE=true
MAX_AGENT_IMPORT_PER_MINUTE=100
SHARE_TOKEN_EXPIRY_DAYS=30

# Logging
LOG_LEVEL=DEBUG
SENTRY_DSN=

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:3800
SESSION_COOKIE_SECURE=false

# Performance
CACHE_TTL_SECONDS=60
DB_POOL_SIZE=5
```

### Staging (.env.staging)

```bash
# Core
DATABASE_URL=postgresql://staging_user:staging_pass@staging-db:5432/agenthub_staging
REDIS_URL=redis://staging-redis:6379/0
SECRET_KEY=${STAGING_SECRET_KEY}  # from secrets manager
JWT_SECRET_KEY=${STAGING_JWT_KEY}

# Agent Management
AGENT_LIBRARY_PATH=/app/agent-library
ENABLE_AGENT_MARKETPLACE=true
MAX_AGENT_IMPORT_PER_MINUTE=20
SHARE_TOKEN_EXPIRY_DAYS=90

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=${STAGING_SENTRY_DSN}

# Security
CORS_ORIGINS=https://app-staging.example.com
SESSION_COOKIE_SECURE=true

# Performance
CACHE_TTL_SECONDS=300
DB_POOL_SIZE=10
```

### Production (.env.production)

```bash
# Core
DATABASE_URL=${PROD_DATABASE_URL}  # from AWS Secrets Manager
REDIS_URL=${PROD_REDIS_URL}
SECRET_KEY=${PROD_SECRET_KEY}
JWT_SECRET_KEY=${PROD_JWT_KEY}

# Agent Management
AGENT_LIBRARY_PATH=/mnt/shared/agent-library
ENABLE_AGENT_MARKETPLACE=true
MAX_AGENT_IMPORT_PER_MINUTE=10
SHARE_TOKEN_EXPIRY_DAYS=365

# Logging
LOG_LEVEL=WARNING
SENTRY_DSN=${PROD_SENTRY_DSN}
DATADOG_API_KEY=${PROD_DATADOG_KEY}

# Security
CORS_ORIGINS=https://app.example.com,https://dashboard.example.com
SESSION_COOKIE_SECURE=true
CSRF_SECRET_KEY=${PROD_CSRF_KEY}

# Performance
CACHE_TTL_SECONDS=3600
DB_POOL_SIZE=50
DB_POOL_RECYCLE=1800
ENABLE_QUERY_CACHING=true

# Feature Flags
ENABLE_AGENT_IMPORT=true
ENABLE_AGENT_SHARING=true
```

---

## Secrets Management

### Using AWS Secrets Manager

```bash
# Store secrets
aws secretsmanager create-secret \
  --name agenthub/production/database \
  --secret-string '{"url":"postgresql://..."}'

# Retrieve in application startup
python << 'EOF'
import boto3
import json
import os

client = boto3.client('secretsmanager', region_name='us-east-1')
response = client.get_secret_value(SecretId='agenthub/production/database')
secret = json.loads(response['SecretString'])

os.environ['DATABASE_URL'] = secret['url']
EOF
```

### Using HashiCorp Vault

```bash
# Store secret
vault kv put secret/agenthub/prod database_url="postgresql://..."

# Retrieve
vault kv get -field=database_url secret/agenthub/prod
```

---

## Validation Script

```python
#!/usr/bin/env python3
"""
Validate environment variables before deployment
"""

import os
import sys
from urllib.parse import urlparse

REQUIRED_VARS = [
    'DATABASE_URL',
    'REDIS_URL',
    'SECRET_KEY',
    'JWT_SECRET_KEY',
    'AGENT_LIBRARY_PATH',
]

def validate_env():
    errors = []

    # Check required variables exist
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            errors.append(f"Missing required variable: {var}")

    # Validate DATABASE_URL format
    db_url = os.getenv('DATABASE_URL', '')
    if db_url:
        parsed = urlparse(db_url)
        if parsed.scheme != 'postgresql':
            errors.append("DATABASE_URL must use postgresql:// scheme")

    # Validate SECRET_KEY length
    secret = os.getenv('SECRET_KEY', '')
    if len(secret) < 32:
        errors.append("SECRET_KEY must be at least 32 characters")

    # Validate AGENT_LIBRARY_PATH exists
    lib_path = os.getenv('AGENT_LIBRARY_PATH', '')
    if lib_path and not os.path.isdir(lib_path):
        errors.append(f"AGENT_LIBRARY_PATH does not exist: {lib_path}")

    # Print results
    if errors:
        print("❌ Environment validation FAILED:\n")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ Environment validation PASSED")
        sys.exit(0)

if __name__ == '__main__':
    validate_env()
```

**Usage**:
```bash
# Run before deployment
python scripts/validate_env.py

# In CI/CD
python scripts/validate_env.py || exit 1
```

---

## Troubleshooting

### "Database connection refused"

**Check**:
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL

# Test connection
psql "$DATABASE_URL" -c "SELECT 1;"
```

### "Redis connection timeout"

**Check**:
```bash
# Verify REDIS_URL
echo $REDIS_URL

# Test connection
redis-cli -u "$REDIS_URL" ping
```

### "Invalid SECRET_KEY length"

**Fix**:
```bash
# Generate new key
python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(32)}')"
```

---

## Security Best Practices

1. ✅ **Never commit secrets to version control**
   - Use `.env` files (add to `.gitignore`)
   - Use secrets managers (AWS Secrets Manager, Vault)

2. ✅ **Use different secrets per environment**
   - Dev, staging, and production must have different keys
   - Rotate regularly (quarterly minimum)

3. ✅ **Restrict access to secrets**
   - Principle of least privilege
   - Audit secret access logs

4. ✅ **Validate before deployment**
   - Run validation script
   - Test in staging first

5. ✅ **Monitor for exposed secrets**
   - Use tools like GitGuardian, TruffleHog
   - Enable GitHub secret scanning
