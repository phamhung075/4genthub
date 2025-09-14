# Docker Deployment Guide - DhafnckMCP SSL and Environment Configuration

## Overview

This comprehensive guide covers Docker deployment configurations with specific focus on SSL settings and environment variables for different deployment scenarios. The guide addresses the recent SSL/log level fixes and provides clear instructions for both CapRover and managed PostgreSQL deployments.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [SSL Configuration by Deployment Type](#ssl-configuration-by-deployment-type)
3. [Environment Variables](#environment-variables)
4. [CapRover Deployment](#caprover-deployment)
5. [Managed PostgreSQL Deployment](#managed-postgresql-deployment)
6. [Docker Compose Configurations](#docker-compose-configurations)
7. [Environment Validation](#environment-validation)
8. [Troubleshooting](#troubleshooting)

## Quick Reference

### SSL Mode Decision Matrix

| Deployment Type | DATABASE_SSL_MODE | Reason |
|----------------|-------------------|---------|
| CapRover PostgreSQL | `disable` | CapRover PostgreSQL doesn't support SSL |
| AWS RDS | `require` | Managed service enforces SSL |
| Google Cloud SQL | `require` | Managed service enforces SSL |
| Azure Database | `require` | Managed service enforces SSL |
| Supabase | `require` | Always enforced (automatic) |
| Local Development | `disable` or `prefer` | Local PostgreSQL usually no SSL |
| Self-managed Production | `require` or `prefer` | Depends on SSL certificate setup |

### Log Level Settings

| Environment | APP_LOG_LEVEL | Use Case |
|-------------|---------------|----------|
| Development | `DEBUG` | Full debugging information |
| Staging | `INFO` | Standard operational info |
| Production | `WARNING` | Errors and warnings only |
| High-traffic Production | `ERROR` | Critical issues only |

## SSL Configuration by Deployment Type

### 1. CapRover Deployment (SSL Disabled)

CapRover's built-in PostgreSQL service typically doesn't support SSL connections. This is normal and secure within CapRover's internal network.

**Environment Configuration:**
```bash
# CapRover PostgreSQL Configuration
DATABASE_TYPE=postgresql
DATABASE_HOST=srv-captain--postgres  # CapRover internal hostname
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=postgres
DATABASE_PASSWORD=your_caprover_generated_password
DATABASE_SSL_MODE=disable  # CRITICAL: Must be disabled for CapRover
```

**Why SSL is disabled for CapRover:**
- CapRover PostgreSQL container doesn't have SSL certificates configured
- Communication happens within secure internal Docker network
- CapRover handles external SSL/TLS termination at the reverse proxy level
- Internal services communicate over encrypted Docker networks

### 2. Managed PostgreSQL Services (SSL Required)

Managed PostgreSQL services (AWS RDS, Google Cloud SQL, Azure Database, etc.) enforce SSL connections for security.

**Environment Configuration:**
```bash
# Managed PostgreSQL Configuration
DATABASE_TYPE=postgresql
DATABASE_HOST=your-db.region.provider.com  # Managed service hostname
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=postgres
DATABASE_PASSWORD=your_secure_managed_password
DATABASE_SSL_MODE=require  # CRITICAL: Must be required for managed services
```

**SSL Modes for Managed Services:**
- `require`: Encrypt connection, don't verify server certificate (most common)
- `verify-ca`: Encrypt and verify server certificate against CA
- `verify-full`: Full verification including hostname matching (most secure)

### 3. Supabase (Automatic SSL)

Supabase automatically enforces SSL regardless of the DATABASE_SSL_MODE setting.

**Environment Configuration:**
```bash
# Supabase Configuration
DATABASE_TYPE=supabase  # Special type for Supabase
SUPABASE_DB_HOST=db.your-project.supabase.co
SUPABASE_DB_USER=postgres.your-project
SUPABASE_DB_PASSWORD=your_supabase_password
# DATABASE_SSL_MODE is ignored - always uses 'require'
```

## Environment Variables

### Required Variables

All Docker deployments require these environment variables:

```bash
# Core Settings
ENV=production
NODE_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO  # Will be converted to lowercase

# Database (Choose one configuration type)
DATABASE_TYPE=postgresql  # or 'supabase'
DATABASE_HOST=your_database_host
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=postgres
DATABASE_PASSWORD=your_secure_password
DATABASE_SSL_MODE=disable  # or 'require' based on deployment type

# Backend
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_chars_long

# Authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak.com
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your_keycloak_secret

# CORS
CORS_ORIGINS=https://your-app.com
CORS_ALLOW_CREDENTIALS=true
```

### Environment Variable Validation

The Docker entrypoint script validates these critical variables:

```bash
REQUIRED_VARS="DATABASE_TYPE DATABASE_HOST DATABASE_PORT DATABASE_NAME DATABASE_USER DATABASE_PASSWORD FASTMCP_PORT JWT_SECRET_KEY"
```

**Validation Rules:**
- All required variables must be non-empty
- `JWT_SECRET_KEY` must be at least 32 characters
- `APP_LOG_LEVEL` is automatically converted to lowercase
- Database connection is tested before starting the application

### Log Level Case Conversion

The Docker entrypoint automatically converts log levels to lowercase:

```bash
# In Docker entrypoint script:
LOG_LEVEL=$(echo "${APP_LOG_LEVEL:-info}" | tr "[:upper:]" "[:lower:]")

# Examples:
# INFO -> info
# DEBUG -> debug
# WARNING -> warning
# Error -> error
```

## CapRover Deployment

### Step-by-Step CapRover Setup

1. **Create PostgreSQL Service**
   ```bash
   # In CapRover dashboard:
   # 1. Go to "One-Click Apps/Databases"
   # 2. Select "PostgreSQL"
   # 3. Set app name: "postgres"
   # 4. Note the generated password
   ```

2. **Configure Backend App**
   ```bash
   # CapRover App Environment Variables
   ENV=production
   DATABASE_TYPE=postgresql
   DATABASE_HOST=srv-captain--postgres
   DATABASE_PORT=5432
   DATABASE_NAME=dhafnck_mcp
   DATABASE_USER=postgres
   DATABASE_PASSWORD=<generated_password_from_step_1>
   DATABASE_SSL_MODE=disable  # IMPORTANT: CapRover PostgreSQL doesn't support SSL

   APP_LOG_LEVEL=INFO
   FASTMCP_PORT=8000
   JWT_SECRET_KEY=<generate_32_char_secret>

   # Update these for your CapRover domain:
   KEYCLOAK_URL=https://auth.captain.yourdomain.com
   CORS_ORIGINS=https://app.captain.yourdomain.com
   ```

3. **Configure Frontend App**
   ```bash
   # Frontend Environment Variables
   VITE_BACKEND_URL=https://api.captain.yourdomain.com
   VITE_API_URL=https://api.captain.yourdomain.com
   VITE_KEYCLOAK_URL=https://auth.captain.yourdomain.com
   VITE_KEYCLOAK_REALM=dhafnck-mcp
   VITE_KEYCLOAK_CLIENT_ID=mcp-frontend
   ```

### CapRover Docker Compose Override

If using Docker Compose with CapRover, create `docker-compose.caprover.yml`:

```yaml
version: '3.8'
services:
  backend:
    environment:
      # Override for CapRover
      DATABASE_HOST: srv-captain--postgres
      DATABASE_SSL_MODE: disable
      CORS_ORIGINS: https://app.captain.${CAPTAIN_ROOT_DOMAIN}

  # Remove postgres service since CapRover provides it
  postgres:
    deploy:
      replicas: 0
```

## Managed PostgreSQL Deployment

### AWS RDS Configuration

```bash
# AWS RDS Environment Variables
DATABASE_TYPE=postgresql
DATABASE_HOST=mydb.abc123.us-east-1.rds.amazonaws.com
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=postgres
DATABASE_PASSWORD=your_rds_password
DATABASE_SSL_MODE=require  # AWS RDS enforces SSL

# Optional: Use verify-ca for additional security
# DATABASE_SSL_MODE=verify-ca
```

### Google Cloud SQL Configuration

```bash
# Google Cloud SQL Environment Variables
DATABASE_TYPE=postgresql
DATABASE_HOST=10.1.2.3  # Private IP or public IP
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=postgres
DATABASE_PASSWORD=your_cloudsql_password
DATABASE_SSL_MODE=require  # Cloud SQL enforces SSL
```

### Azure Database Configuration

```bash
# Azure Database for PostgreSQL Environment Variables
DATABASE_TYPE=postgresql
DATABASE_HOST=myserver.postgres.database.azure.com
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=postgres@myserver  # Azure requires @server_name format
DATABASE_PASSWORD=your_azure_password
DATABASE_SSL_MODE=require  # Azure Database enforces SSL
```

## Docker Compose Configurations

### Production with CapRover

```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: docker-system/docker/Dockerfile.backend.production
    environment:
      - ENV=production
      - DATABASE_TYPE=postgresql
      - DATABASE_HOST=srv-captain--postgres
      - DATABASE_SSL_MODE=disable  # CapRover setting
      - APP_LOG_LEVEL=INFO
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    networks:
      - captain-overlay-network

  frontend:
    build:
      context: .
      dockerfile: docker-system/docker/Dockerfile.frontend.production
    environment:
      - VITE_BACKEND_URL=https://api.captain.${CAPTAIN_ROOT_DOMAIN}
    ports:
      - "3800:3800"
    networks:
      - captain-overlay-network

networks:
  captain-overlay-network:
    external: true
```

### Production with Managed PostgreSQL

```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: docker-system/docker/Dockerfile.backend.production
    environment:
      - ENV=production
      - DATABASE_TYPE=postgresql
      - DATABASE_HOST=${DATABASE_HOST}  # External managed DB
      - DATABASE_SSL_MODE=require  # Managed service setting
      - APP_LOG_LEVEL=WARNING  # Higher level for production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    ports:
      - "8000:8000"

  frontend:
    build:
      context: .
      dockerfile: docker-system/docker/Dockerfile.frontend.production
    environment:
      - VITE_BACKEND_URL=${BACKEND_URL}
    ports:
      - "3800:3800"

  # No postgres service - using external managed database
```

## Environment Validation

### Docker Entrypoint Validation Process

The Docker entrypoint script performs comprehensive validation:

1. **Required Variable Check**
   ```bash
   REQUIRED_VARS="DATABASE_TYPE DATABASE_HOST DATABASE_PORT DATABASE_NAME DATABASE_USER DATABASE_PASSWORD FASTMCP_PORT JWT_SECRET_KEY"

   for VAR in $REQUIRED_VARS; do
       eval VALUE=\$$VAR
       if [ -z "$VALUE" ]; then
           echo "❌ Missing required variable: $VAR"
           exit 1
       fi
   done
   ```

2. **Security Validation**
   ```bash
   # JWT secret length check
   if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
       echo "❌ ERROR: JWT_SECRET_KEY must be at least 32 characters"
       exit 1
   fi
   ```

3. **Database Connection Test**
   ```bash
   # PostgreSQL connection validation
   pg_isready -h ${DATABASE_HOST} -p ${DATABASE_PORT} -U ${DATABASE_USER}
   ```

4. **Log Level Conversion**
   ```bash
   # Convert to lowercase for uvicorn/gunicorn
   LOG_LEVEL=$(echo "${APP_LOG_LEVEL:-info}" | tr "[:upper:]" "[:lower:]")
   ```

### Pre-deployment Validation Script

Create a validation script to test your environment:

```bash
#!/bin/bash
# validate-docker-env.sh

echo "🔍 Validating Docker environment configuration..."

# Check required variables
REQUIRED_VARS="DATABASE_TYPE DATABASE_HOST DATABASE_SSL_MODE APP_LOG_LEVEL JWT_SECRET_KEY"
MISSING_VARS=""

for VAR in $REQUIRED_VARS; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS="$MISSING_VARS $VAR"
        echo "❌ Missing: $VAR"
    else
        echo "✅ Found: $VAR"
    fi
done

if [ -n "$MISSING_VARS" ]; then
    echo "❌ Missing required variables:$MISSING_VARS"
    exit 1
fi

# Validate JWT secret length
if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo "❌ JWT_SECRET_KEY too short (${#JWT_SECRET_KEY} chars, need 32+)"
    exit 1
fi

# Validate SSL mode
case "$DATABASE_SSL_MODE" in
    disable|require|prefer|allow|verify-ca|verify-full)
        echo "✅ Valid SSL mode: $DATABASE_SSL_MODE"
        ;;
    *)
        echo "⚠️  Unknown SSL mode: $DATABASE_SSL_MODE (will be passed to PostgreSQL)"
        ;;
esac

# Validate log level
LOG_LEVEL_LOWER=$(echo "$APP_LOG_LEVEL" | tr "[:upper:]" "[:lower:]")
case "$LOG_LEVEL_LOWER" in
    debug|info|warning|error|critical)
        echo "✅ Valid log level: $APP_LOG_LEVEL -> $LOG_LEVEL_LOWER"
        ;;
    *)
        echo "⚠️  Non-standard log level: $APP_LOG_LEVEL"
        ;;
esac

echo "✅ Environment validation completed successfully!"
```

## Troubleshooting

### Common SSL Issues

#### Issue: SSL Connection Failed
```
FATAL: SSL connection has been closed unexpectedly
```

**Solution for CapRover:**
```bash
# Set SSL mode to disable
DATABASE_SSL_MODE=disable
```

**Solution for Managed Services:**
```bash
# Ensure SSL is required
DATABASE_SSL_MODE=require

# If still failing, try:
DATABASE_SSL_MODE=prefer
```

#### Issue: Certificate Verification Failed
```
FATAL: certificate verify failed
```

**Solutions:**
```bash
# Option 1: Use require instead of verify-ca
DATABASE_SSL_MODE=require

# Option 2: Provide CA certificate (advanced)
DATABASE_SSL_MODE=verify-ca
DATABASE_SSL_CA=/path/to/ca-cert.pem
```

### Common Environment Variable Issues

#### Issue: Missing Required Variables
```
❌ Missing required variable: DATABASE_PASSWORD
```

**Solution:**
Check your `.env` file or environment configuration:
```bash
# Verify all required variables are set
env | grep DATABASE
env | grep JWT_SECRET_KEY
```

#### Issue: JWT Secret Too Short
```
❌ ERROR: JWT_SECRET_KEY must be at least 32 characters
```

**Solution:**
Generate a secure JWT secret:
```bash
# Generate 64-character random string
openssl rand -hex 32

# Or use Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### Log Level Issues

#### Issue: Invalid Log Level
```
Invalid log level: 'Info'
```

**Solution:**
The system automatically converts case, but ensure you use valid levels:
```bash
# Valid log levels (case insensitive)
APP_LOG_LEVEL=DEBUG    # -> debug
APP_LOG_LEVEL=INFO     # -> info
APP_LOG_LEVEL=WARNING  # -> warning
APP_LOG_LEVEL=ERROR    # -> error
APP_LOG_LEVEL=CRITICAL # -> critical
```

### Database Connection Issues

#### Issue: Connection Refused
```
FATAL: connection to server at "srv-captain--postgres" failed: Connection refused
```

**CapRover Solutions:**
1. Verify PostgreSQL service is running in CapRover
2. Check service name matches: `srv-captain--postgres`
3. Ensure both apps are in same CapRover network

**Managed PostgreSQL Solutions:**
1. Check security group/firewall rules
2. Verify hostname and port
3. Confirm SSL requirements

#### Issue: Authentication Failed
```
FATAL: password authentication failed
```

**Solutions:**
1. Verify username/password combination
2. For Azure: ensure username includes `@server_name`
3. For Cloud SQL: check user permissions

### Container Startup Issues

#### Issue: Health Check Failing
```
Health check failed: container is not responding
```

**Solutions:**
1. Check application logs:
   ```bash
   docker-compose logs backend
   ```

2. Verify environment variables:
   ```bash
   docker-compose exec backend env | grep DATABASE
   ```

3. Test database connectivity:
   ```bash
   docker-compose exec backend pg_isready -h $DATABASE_HOST -p $DATABASE_PORT
   ```

### Performance Issues

#### Issue: Slow Database Connections
```
Database queries are timing out
```

**Solutions for CapRover:**
```bash
# Increase connection timeout in .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=60
```

**Solutions for Managed PostgreSQL:**
```bash
# Optimize for cloud latency
DATABASE_POOL_SIZE=50
DATABASE_POOL_RECYCLE=1800
DATABASE_POOL_PRE_PING=true
```

---

## Summary

This guide provides comprehensive coverage of Docker deployment configurations with proper SSL settings for different scenarios:

1. **CapRover**: Use `DATABASE_SSL_MODE=disable`
2. **Managed PostgreSQL**: Use `DATABASE_SSL_MODE=require`
3. **Supabase**: SSL is automatically enforced
4. **Environment Variables**: All validated at startup
5. **Log Levels**: Automatically converted to lowercase

Always validate your configuration before deployment and refer to the troubleshooting section for common issues.

For additional help, see:
- [Production Deployment Guide](./production-deployment-guide.md)
- [Troubleshooting Guide](../troubleshooting-guides/production-deployment-issues.md)
- [Environment Configuration](../setup-guides/environment-configuration.md)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-09-14
**Related to:** Docker SSL/log level fixes implementation