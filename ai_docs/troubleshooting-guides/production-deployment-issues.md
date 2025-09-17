# Production Deployment Issues - Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide addresses common production deployment issues, with special focus on SSL configuration problems and environment variable validation errors that may occur after the recent Docker SSL/log level fixes.

## Table of Contents

1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [SSL Connection Issues](#ssl-connection-issues)
3. [Environment Variable Problems](#environment-variable-problems)
4. [Log Level Configuration Issues](#log-level-configuration-issues)
5. [Database Connection Problems](#database-connection-problems)
6. [Docker Container Issues](#docker-container-issues)
7. [CapRover Specific Issues](#caprover-specific-issues)
8. [Managed PostgreSQL Issues](#managed-postgresql-issues)
9. [Authentication and Authorization](#authentication-and-authorization)
10. [Performance and Scaling Issues](#performance-and-scaling-issues)

## Quick Diagnostic Commands

Before diving into specific issues, run these diagnostic commands:

```bash
# Check container status
docker-compose ps

# View real-time logs
docker-compose logs -f backend

# Check environment variables
docker-compose exec backend env | grep -E "(DATABASE|APP_LOG|JWT)"

# Test database connectivity
docker-compose exec backend pg_isready -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER

# Check SSL connection specifically
docker-compose exec backend psql "$DATABASE_URL" -c "SELECT version();"

# Validate configuration
docker-compose exec backend cat /app/docker-entrypoint.sh
```

## SSL Connection Issues

### Issue: SSL Connection Closed Unexpectedly

**Symptoms:**
```
FATAL: SSL connection has been closed unexpectedly
could not connect to server: Connection reset by peer
```

**Root Cause:** Mismatch between SSL requirements

**Solutions by Deployment Type:**

#### For CapRover Deployment:
```bash
# CapRover PostgreSQL doesn't support SSL
DATABASE_SSL_MODE=disable

# Verify CapRover internal hostname
DATABASE_HOST=srv-captain--postgres

# Complete CapRover configuration
DATABASE_TYPE=postgresql
DATABASE_HOST=srv-captain--postgres
DATABASE_PORT=5432
DATABASE_SSL_MODE=disable  # CRITICAL for CapRover
```

#### For Managed PostgreSQL (AWS RDS, Google Cloud SQL, Azure):
```bash
# Managed services require SSL
DATABASE_SSL_MODE=require

# If certificate issues occur:
DATABASE_SSL_MODE=prefer  # Try SSL first, fallback to no SSL

# For production with proper certificates:
DATABASE_SSL_MODE=verify-ca  # Verify certificate authority
```

#### For Supabase:
```bash
# Supabase always enforces SSL (automatic)
DATABASE_TYPE=supabase
# DATABASE_SSL_MODE is ignored for Supabase
```

**Verification Steps:**
```bash
# Test SSL connection manually
openssl s_client -connect your-db-host:5432 -servername your-db-host

# Test PostgreSQL connection with specific SSL mode
psql "postgresql://user:pass@host:5432/db?sslmode=require"
```

### Issue: Certificate Verification Failed

**Symptoms:**
```
FATAL: certificate verify failed
SSL error: certificate verify failed
```

**Solutions:**
```bash
# Option 1: Use 'require' instead of 'verify-ca'
DATABASE_SSL_MODE=require

# Option 2: Disable certificate verification (not recommended for production)
DATABASE_SSL_MODE=prefer

# Option 3: Provide CA certificate (advanced)
DATABASE_SSL_MODE=verify-ca
# Mount certificate file and set path
# -v /path/to/certs:/certs
# DATABASE_SSL_CA=/certs/ca-cert.pem
```

### Issue: SSL Not Supported by Server

**Symptoms:**
```
FATAL: the database system does not support SSL connections
```

**Solution:**
```bash
# Disable SSL for databases that don't support it
DATABASE_SSL_MODE=disable

# Common for:
# - Local PostgreSQL without SSL setup
# - CapRover PostgreSQL
# - Development environments
```

## Environment Variable Problems

### Issue: Missing Required Environment Variables

**Symptoms:**
```
❌ Missing required variable: DATABASE_PASSWORD
❌ ERROR: Missing required environment variables: DATABASE_PASSWORD JWT_SECRET_KEY
```

**Required Variables List:**
```bash
DATABASE_TYPE
DATABASE_HOST
DATABASE_PORT
DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD
FASTMCP_PORT
JWT_SECRET_KEY
```

**Diagnostic Commands:**
```bash
# Check which variables are missing
env | grep -E "(DATABASE|JWT|FASTMCP)" | sort

# Verify .env file
cat .env | grep -v "^#" | grep -v "^$"

# Check Docker environment
docker-compose exec backend env | grep DATABASE
```

**Solutions:**

#### Fix Missing Variables:
```bash
# In your .env file, ensure all required variables are set:
DATABASE_TYPE=postgresql
DATABASE_HOST=your-database-host
DATABASE_PORT=5432
DATABASE_NAME=agenthub
DATABASE_USER=postgres
DATABASE_PASSWORD=your_secure_password
FASTMCP_PORT=8000
JWT_SECRET_KEY=your_jwt_secret_at_least_32_characters_long
```

#### Fix Empty Variables:
```bash
# Check for empty variables
grep "=" .env | grep "=$"

# Common mistake - space after equals sign
DATABASE_PASSWORD= secret  # WRONG
DATABASE_PASSWORD=secret   # CORRECT
```

### Issue: JWT Secret Key Too Short

**Symptoms:**
```
❌ ERROR: JWT_SECRET_KEY must be at least 32 characters for production
```

**Solution:**
```bash
# Generate a secure 64-character JWT secret
JWT_SECRET_KEY=$(openssl rand -hex 32)
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env

# Or use Node.js
node -e "console.log('JWT_SECRET_KEY=' + require('crypto').randomBytes(32).toString('hex'))"

# Or generate manually (at least 32 characters)
JWT_SECRET_KEY="your_very_secure_jwt_secret_key_for_production_at_least_32_chars"
```

### Issue: Environment Variables Not Loading

**Symptoms:**
```
Variables are set in .env but not recognized by container
```

**Solutions:**
```bash
# Ensure .env file is in correct location (project root)
ls -la .env

# Check Docker Compose env_file configuration
grep -A5 "env_file:" docker-compose.yml

# Rebuild containers to pick up new environment variables
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify variables are loaded in container
docker-compose exec backend env | grep JWT_SECRET_KEY
```

## Log Level Configuration Issues

### Issue: Invalid Log Level Error

**Symptoms:**
```
ValueError: Unknown level: 'Info'
ERROR: Invalid log level configuration
```

**Root Cause:** Case sensitivity issues with log levels

**Solution:**
The Docker entrypoint automatically handles case conversion:
```bash
# These all work (automatically converted to lowercase):
APP_LOG_LEVEL=INFO      # -> info
APP_LOG_LEVEL=Debug     # -> debug
APP_LOG_LEVEL=WARNING   # -> warning
APP_LOG_LEVEL=error     # -> error
APP_LOG_LEVEL=CRITICAL  # -> critical
```

**Valid Log Levels:**
- `DEBUG` - Detailed debugging information
- `INFO` - General operational information
- `WARNING` - Warning messages
- `ERROR` - Error messages only
- `CRITICAL` - Critical issues only

**Verification:**
```bash
# Check converted log level in container
docker-compose exec backend sh -c 'echo $APP_LOG_LEVEL | tr "[:upper:]" "[:lower:]"'

# Check if uvicorn is using correct log level
docker-compose logs backend | grep "log level"
```

### Issue: Logs Not Appearing

**Symptoms:**
```
Application seems to run but no logs are visible
```

**Solutions:**
```bash
# Check if log level is too high
APP_LOG_LEVEL=DEBUG  # Most verbose

# Ensure Python logging is configured for Docker
PYTHONUNBUFFERED=1

# Check Docker Compose logging configuration
docker-compose logs --tail=100 backend

# Verify uvicorn log configuration
# Look for this in startup logs:
# "Started server process" with log level info
```

## Database Connection Problems

### Issue: Connection Refused

**Symptoms:**
```
psycopg2.OperationalError: connection to server failed: Connection refused
could not connect to server at "localhost" port 5432: Connection refused
```

**Solutions by Deployment Type:**

#### CapRover:
```bash
# Verify PostgreSQL service name
DATABASE_HOST=srv-captain--postgres  # Exact CapRover service name

# Check if PostgreSQL service is running in CapRover dashboard
# Services → Apps → postgres (should be running)

# Verify network connectivity
docker-compose exec backend ping srv-captain--postgres
```

#### Managed PostgreSQL:
```bash
# Check hostname and port
nslookup your-database-host.amazonaws.com
telnet your-database-host.amazonaws.com 5432

# Verify security group rules (AWS) or firewall (GCP/Azure)
# - Allow inbound connections on port 5432
# - Allow connections from your application IP/network

# Test connection from local machine
psql -h your-database-host.amazonaws.com -p 5432 -U postgres -d agenthub
```

#### Docker Compose:
```bash
# Ensure database service is running
docker-compose ps postgres

# Check if services are on same network
docker network ls
docker inspect network_name

# Verify service dependency order
depends_on:
  postgres:
    condition: service_healthy
```

### Issue: Authentication Failed

**Symptoms:**
```
FATAL: password authentication failed for user "postgres"
FATAL: role "username" does not exist
```

**Solutions:**

#### Password Issues:
```bash
# Verify password doesn't contain special characters that need escaping
# If password has special chars, URL encode it:
import urllib.parse
encoded = urllib.parse.quote("password!@#$")

# Or use individual component variables instead of DATABASE_URL
DATABASE_HOST=host
DATABASE_USER=user
DATABASE_PASSWORD=password!@#$  # Raw password, will be encoded automatically
```

#### User/Role Issues:
```bash
# For Azure Database, username format is different:
DATABASE_USER=postgres@your-server-name  # Azure requires @server format

# For Google Cloud SQL with IAM authentication:
DATABASE_USER=your-service-account@project.iam  # IAM user format

# Verify user exists
psql -h host -U postgres -c "\du"  # List users
```

### Issue: Database Does Not Exist

**Symptoms:**
```
FATAL: database "agenthub" does not exist
```

**Solutions:**
```bash
# Create database manually
psql -h $DATABASE_HOST -U $DATABASE_USER -c "CREATE DATABASE agenthub;"

# Or enable auto-migration
AUTO_MIGRATE=true

# Check if database was created with different name
psql -h $DATABASE_HOST -U $DATABASE_USER -c "\l"  # List databases
```

## Docker Container Issues

### Issue: Container Exits Immediately

**Symptoms:**
```
backend_1 exited with code 1
Container agenthub-backend-1 exited unexpectedly
```

**Diagnostic Steps:**
```bash
# Check container logs
docker-compose logs backend

# Run container interactively to debug
docker-compose run --rm backend sh

# Check entrypoint script
docker-compose exec backend cat /app/docker-entrypoint.sh

# Validate environment inside container
docker-compose run --rm backend env | grep DATABASE
```

**Common Causes and Solutions:**

#### Entrypoint Script Fails:
```bash
# Check script syntax
bash -n /path/to/docker-entrypoint.sh

# Run entrypoint manually
docker-compose run --rm backend /app/docker-entrypoint.sh
```

#### Missing Dependencies:
```bash
# Check if required packages are installed
docker-compose exec backend which pg_isready
docker-compose exec backend python -c "import psycopg2"

# Rebuild image if packages are missing
docker-compose build --no-cache backend
```

### Issue: Health Check Failing

**Symptoms:**
```
Health check failed after 3 retries
Container is unhealthy
```

**Solutions:**
```bash
# Check health check endpoint manually
curl -f http://localhost:8000/health

# Check if application is binding to correct port
docker-compose exec backend netstat -tlnp | grep 8000

# Verify health check configuration in Dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${FASTMCP_PORT:-8000}/health || exit 1

# Test health check command manually
docker-compose exec backend curl -f http://localhost:8000/health
```

### Issue: Port Already in Use

**Symptoms:**
```
Error: Port 8000 is already in use
Cannot start container: port is already allocated
```

**Solutions:**
```bash
# Check what's using the port
lsof -i :8000
netstat -tlnp | grep 8000

# Kill process using the port
kill -9 $(lsof -t -i:8000)

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use different external port
```

## CapRover Specific Issues

### Issue: CapRover PostgreSQL Connection

**Symptoms:**
```
Connection refused to srv-captain--postgres
SSL connection issues with CapRover PostgreSQL
```

**Solution - Complete CapRover Configuration:**
```bash
# CapRover Backend Environment Variables:
ENV=production
DATABASE_TYPE=postgresql
DATABASE_HOST=srv-captain--postgres  # EXACT CapRover service name
DATABASE_PORT=5432
DATABASE_NAME=agenthub
DATABASE_USER=postgres
DATABASE_PASSWORD=<your_caprover_generated_password>
DATABASE_SSL_MODE=disable  # CRITICAL: CapRover PostgreSQL doesn't support SSL

APP_LOG_LEVEL=INFO
FASTMCP_PORT=8000
JWT_SECRET_KEY=<your_32_char_secret>

# Update these for your domain:
KEYCLOAK_URL=https://auth.captain.yourdomain.com
CORS_ORIGINS=https://app.captain.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=<your_keycloak_secret>
```

**Verification Steps:**
```bash
# From CapRover dashboard, check:
# 1. PostgreSQL app is running
# 2. Backend app can reach PostgreSQL
# 3. Backend app logs show successful connection

# Test connection manually in CapRover terminal:
pg_isready -h srv-captain--postgres -p 5432 -U postgres
```

### Issue: CapRover Network Connectivity

**Symptoms:**
```
Backend cannot reach postgres service
Services on different networks
```

**Solution:**
```bash
# Ensure both apps use captain-overlay-network
# In docker-compose.yml:
networks:
  captain-overlay-network:
    external: true

services:
  backend:
    networks:
      - captain-overlay-network
```

### Issue: CapRover Environment Variable Override

**Symptoms:**
```
Environment variables not taking effect in CapRover
```

**Solutions:**
```bash
# In CapRover dashboard:
# 1. Go to Apps → Your App → App Configs
# 2. Set environment variables in "Environment Variables" section
# 3. Do NOT use .env files - CapRover overrides them

# Verify variables in CapRover:
# Apps → Your App → Deployment → View Logs
# Look for environment variable output
```

## Managed PostgreSQL Issues

### Issue: AWS RDS Connection Problems

**Symptoms:**
```
Connection timeout to RDS instance
SSL handshake failure
```

**Solutions:**
```bash
# Complete AWS RDS configuration:
DATABASE_TYPE=postgresql
DATABASE_HOST=mydb.abc123.us-east-1.rds.amazonaws.com
DATABASE_PORT=5432
DATABASE_NAME=agenthub
DATABASE_USER=postgres
DATABASE_PASSWORD=your_rds_password
DATABASE_SSL_MODE=require  # RDS requires SSL

# Security group must allow inbound on port 5432
# From your application's IP or security group

# Test connection:
psql "postgresql://user:pass@mydb.abc123.us-east-1.rds.amazonaws.com:5432/agenthub?sslmode=require"
```

### Issue: Google Cloud SQL Issues

**Symptoms:**
```
Connection failed to Cloud SQL instance
IP authorization failed
```

**Solutions:**
```bash
# For private IP:
DATABASE_HOST=10.1.2.3  # Private IP from Cloud SQL

# For public IP with authorized networks:
DATABASE_HOST=35.123.45.67  # Public IP from Cloud SQL
# Add your application IPs to authorized networks

# Complete configuration:
DATABASE_TYPE=postgresql
DATABASE_HOST=your-cloud-sql-ip
DATABASE_SSL_MODE=require  # Cloud SQL requires SSL

# Test with gcloud:
gcloud sql connect your-instance --user=postgres
```

### Issue: Azure Database Connection

**Symptoms:**
```
Authentication failed with Azure Database
Username format incorrect
```

**Solution:**
```bash
# Azure requires special username format:
DATABASE_USER=postgres@your-server-name  # Include @server-name

# Complete Azure configuration:
DATABASE_TYPE=postgresql
DATABASE_HOST=myserver.postgres.database.azure.com
DATABASE_USER=postgres@myserver  # Azure format
DATABASE_PASSWORD=your_azure_password
DATABASE_SSL_MODE=require  # Azure requires SSL

# Firewall rules must allow your application IP
```

## Authentication and Authorization

### Issue: Keycloak Connection Failed

**Symptoms:**
```
Unable to connect to Keycloak server
Authentication requests failing
```

**Solutions:**
```bash
# Verify Keycloak URL is accessible
curl -f $KEYCLOAK_URL/auth/realms/agenthub/.well-known/openid_configuration

# Complete Keycloak configuration:
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak.com
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your_client_secret

# Frontend configuration must match:
VITE_KEYCLOAK_URL=https://your-keycloak.com
VITE_KEYCLOAK_REALM=agenthub
VITE_KEYCLOAK_CLIENT_ID=mcp-frontend  # Different client for frontend
```

### Issue: CORS Errors

**Symptoms:**
```
Cross-Origin Request Blocked
CORS policy error in browser
```

**Solutions:**
```bash
# Ensure CORS origins match frontend URL exactly:
CORS_ORIGINS=https://your-frontend.com,https://app.captain.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# For CapRover:
CORS_ORIGINS=https://app.captain.${CAPTAIN_ROOT_DOMAIN}

# Multiple origins:
CORS_ORIGINS=https://app.example.com,https://admin.example.com,http://localhost:3000
```

## Performance and Scaling Issues

### Issue: Database Connection Pool Exhausted

**Symptoms:**
```
QueuePool limit of size 5 overflow 10 reached
Too many connections to PostgreSQL
```

**Solutions:**
```bash
# Increase connection pool settings:
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=100
DATABASE_POOL_TIMEOUT=60
DATABASE_POOL_RECYCLE=1800
DATABASE_POOL_PRE_PING=true

# For CapRover (smaller resources):
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# For managed PostgreSQL (better resources):
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=100
```

### Issue: High Memory Usage

**Symptoms:**
```
Container running out of memory
OOMKilled errors
```

**Solutions:**
```bash
# Optimize Python memory usage:
PYTHONDONTWRITEBYTECODE=1
PYTHONHASHSEED=random

# Reduce connection pool if needed:
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Add memory limits to docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 512M
    reservations:
      memory: 256M
```

### Issue: Slow Query Performance

**Symptoms:**
```
Database queries taking too long
Request timeouts
```

**Solutions:**
```bash
# Add query timeout settings:
# In database_config.py connection settings:
"statement_timeout": "60s"
"lock_timeout": "30s"

# For cloud databases, optimize for latency:
"tcp_keepalives_idle": "600"
"tcp_keepalives_interval": "30"
"tcp_keepalives_count": "3"

# Enable connection pre-ping:
DATABASE_POOL_PRE_PING=true
```

---

## Emergency Recovery Procedures

### Complete Environment Reset

If all else fails, follow these steps for a complete reset:

```bash
# 1. Stop all services
docker-compose down -v

# 2. Remove all containers and images
docker system prune -a -f

# 3. Verify environment variables
env | grep -E "(DATABASE|JWT|APP_LOG)" | sort

# 4. Test database connectivity outside Docker
pg_isready -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER

# 5. Rebuild and start fresh
docker-compose build --no-cache
docker-compose up -d

# 6. Watch logs for errors
docker-compose logs -f
```

### Rollback to Previous Version

```bash
# If new deployment is failing:
# 1. Tag current version
git tag problematic-version

# 2. Rollback to last known good version
git checkout last-good-tag

# 3. Rebuild and deploy
docker-compose build --no-cache
docker-compose up -d
```

---

## Getting Help

If you're still experiencing issues after following this guide:

1. **Gather Information:**
   ```bash
   # Save logs
   docker-compose logs > deployment-logs.txt

   # Save configuration
   env | grep -E "(DATABASE|JWT|APP_LOG)" > environment-vars.txt

   # Save system info
   docker version > system-info.txt
   docker-compose version >> system-info.txt
   ```

2. **Check Documentation:**
   - [Docker Deployment Guide](../operations/docker-deployment-guide.md)
   - [Production Deployment Guide](../operations/production-deployment-guide.md)
   - [Database Configuration Guide](../operations/database-configuration-guide.md)

3. **Common Support Channels:**
   - Project GitHub Issues
   - Internal documentation
   - Team Slack/communication channels

---

**Document Version:** 1.0.0
**Last Updated:** 2025-09-14
**Related to:** Docker SSL/log level fixes troubleshooting