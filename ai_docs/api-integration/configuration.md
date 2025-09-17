# Configuration Guide

## Overview

This guide covers all configuration options for the 4genthub system, including environment variables, database settings, authentication, caching, and performance tuning.

## Configuration Hierarchy

### Configuration Sources (in order of precedence)
1. **Environment Variables** (highest priority)
2. **Configuration Files** (.env files)
3. **Default Values** (lowest priority)

### Configuration Files
```
config/
├── .env                    # Main configuration
├── .env.local             # Local overrides (not in git)
├── .env.development       # Development settings
├── .env.production        # Production settings
├── .env.test              # Test settings
└── settings/
    ├── database.py        # Database configuration
    ├── auth.py           # Authentication settings
    ├── cache.py          # Cache configuration
    └── logging.py        # Logging configuration
```

## Core Configuration

### Database Configuration

4genthub uses a **dual PostgreSQL architecture** designed for optimal development-production parity:

- **Production**: Supabase cloud PostgreSQL (fully managed, globally distributed)
- **Local Development**: PostgreSQL Docker container (full feature compatibility)

This architecture ensures consistent behavior across environments while leveraging cloud-managed services for production scale.

#### Database Type Selection
```bash
# Production: Supabase cloud PostgreSQL
DATABASE_TYPE=supabase       # Uses Supabase managed PostgreSQL

# Local Development: PostgreSQL Docker
DATABASE_TYPE=postgresql     # Uses local PostgreSQL container

# Legacy Support: SQLite has been removed
# DATABASE_TYPE=sqlite       # No longer supported - use postgresql instead
```

#### Production Configuration: Supabase Cloud PostgreSQL
```bash
# Supabase cloud deployment (production)
DATABASE_TYPE=supabase
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_DB_PASSWORD=your-database-password

# Alternative: Direct database URL (if preferred)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require

# Supabase-specific optimizations
SUPABASE_REGION=us-west-1    # Choose closest region
```

#### Local Development Configuration: PostgreSQL Docker
```bash
# Local development with PostgreSQL Docker
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/4genthub_dev

# Docker deployment
DATABASE_URL=postgresql://4genthub_user:password@postgres:5432/4genthub

# SSL configuration for production-like local setup
DB_SSL_MODE=disable          # Typically disabled for local development
```

#### SQLite Configuration (Deprecated - Removed)
```bash
# SQLite support has been discontinued
# Use PostgreSQL for all environments:
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:password@host:port/database

# For migration from SQLite, see migration guides in ai_docs/migration-guides/
```

#### Advanced PostgreSQL Configuration
```bash
# Async driver configuration (optional, for specific use cases)
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database

# Connection pool optimization for high-load scenarios
DB_POOL_SIZE=50             # Increase for high concurrent load
DB_MAX_OVERFLOW=100         # Additional connections beyond pool
DB_POOL_RECYCLE=7200        # Connection lifetime (2 hours)
```

#### Database Pool Configuration
```bash
# Connection pooling
DB_POOL_SIZE=20                 # Base pool size
DB_MAX_OVERFLOW=30              # Additional connections beyond pool_size
DB_POOL_TIMEOUT=30              # Seconds to wait for connection
DB_POOL_RECYCLE=3600            # Seconds before recycling connection
DB_POOL_PRE_PING=true           # Validate connections before use

# Query configuration
DB_ECHO=false                   # Log all SQL queries (debug only)
DB_ECHO_POOL=false              # Log connection pool events
DB_QUERY_TIMEOUT=30             # Query timeout in seconds
```

### Server Configuration

#### Basic Server Settings
```bash
# Server binding
HOST=0.0.0.0                    # Listen address (0.0.0.0 for all interfaces)
PORT=8000                       # Listen port

# Application settings
APP_NAME=4genthub
APP_VERSION=1.0.0
APP_DESCRIPTION="AI-driven project orchestration platform"

# Environment
ENVIRONMENT=development         # development, staging, production
DEBUG=false                     # Enable debug mode
TESTING=false                   # Enable testing mode
```

#### CORS Configuration
```bash
# CORS settings
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
CORS_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_HEADERS=["*"]
CORS_CREDENTIALS=true
```

#### Request Limits
```bash
# Request size limits
MAX_REQUEST_SIZE=10485760       # 10MB in bytes
MAX_UPLOAD_SIZE=52428800        # 50MB in bytes

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100       # Requests per minute per IP
RATE_LIMIT_BURST=10             # Burst allowance
```

### Authentication Configuration

#### Authentication Provider Settings
```bash
# Main authentication configuration
AUTH_ENABLED=true               # Enable/disable authentication
AUTH_PROVIDER=keycloak          # Options: keycloak, supabase, local

# Keycloak configuration (when AUTH_PROVIDER=keycloak)
KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=4genthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
KEYCLOAK_SSL_VERIFY=true

# Supabase configuration (when AUTH_PROVIDER=supabase)
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key  # For server-side operations
```

#### JWT Settings
```bash
# JWT configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256             # RS256 for Keycloak
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Token settings
TOKEN_EXPIRY_HOURS=24
TOKEN_REFRESH_THRESHOLD=0.5     # Refresh when 50% of lifetime remaining
TOKEN_ISSUER=4genthub
TOKEN_AUDIENCE=4genthub-users
```

#### Authentication Providers
```bash
# Bearer token authentication
AUTH_BEARER_ENABLED=true
AUTH_BEARER_REALM=4genthub

# OAuth configuration (if using OAuth)
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
OAUTH_SCOPES=["openid", "email", "profile"]

# Session configuration
SESSION_SECRET_KEY=your-session-secret
SESSION_EXPIRE_SECONDS=3600
SESSION_COOKIE_NAME=4genthub_session
SESSION_COOKIE_SECURE=true      # HTTPS only
SESSION_COOKIE_HTTPONLY=true
```

### Caching Configuration

#### Redis Cache
```bash
# Redis connection
REDIS_URL=redis://localhost:6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password

# Redis pool settings
REDIS_POOL_SIZE=10
REDIS_MAX_CONNECTIONS=20
REDIS_RETRY_ON_TIMEOUT=true
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
```

#### Cache Settings
```bash
# Cache configuration
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600          # Default TTL in seconds
CACHE_KEY_PREFIX=4genthub:
CACHE_COMPRESSION=true

# Context cache specific
CONTEXT_CACHE_TTL=1800          # 30 minutes
CONTEXT_CACHE_MAX_SIZE=1000     # Max cached contexts
CONTEXT_CACHE_ENABLED=true

# Agent cache specific
AGENT_CACHE_TTL=600             # 10 minutes
AGENT_CACHE_ENABLED=true
```

#### Memory Cache (fallback)
```bash
# In-memory cache (when Redis unavailable)
MEMORY_CACHE_ENABLED=true
MEMORY_CACHE_MAX_SIZE=500
MEMORY_CACHE_TTL=1800
```

### Logging Configuration

#### Log Levels and Format
```bash
# Logging configuration
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                 # json, text
LOG_FILE_ENABLED=true
LOG_FILE_PATH=/var/log/4genthub.log
LOG_FILE_MAX_SIZE=10485760      # 10MB
LOG_FILE_BACKUP_COUNT=5

# Console logging
LOG_CONSOLE_ENABLED=true
LOG_CONSOLE_FORMAT=text

# Request logging
LOG_REQUESTS=true
LOG_REQUEST_DETAILS=false       # Include request body/headers
LOG_RESPONSE_TIME=true
```

#### Structured Logging
```bash
# Structured logging fields
LOG_INCLUDE_TIMESTAMP=true
LOG_INCLUDE_LEVEL=true
LOG_INCLUDE_MODULE=true
LOG_INCLUDE_FUNCTION=true
LOG_INCLUDE_LINE_NUMBER=false
LOG_INCLUDE_CORRELATION_ID=true

# External logging
SENTRY_DSN=your-sentry-dsn-here
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### MCP Configuration

#### MCP Server Settings
```bash
# MCP server configuration
MCP_SERVER_NAME=4genthub
MCP_SERVER_VERSION=1.0.0
MCP_PROTOCOL_VERSION=1.0.0

# Tool configuration
MCP_TOOLS_ENABLED=true
MCP_TOOL_TIMEOUT=300            # Tool execution timeout in seconds
MCP_MAX_CONCURRENT_TOOLS=10     # Max concurrent tool executions

# Context configuration
MCP_CONTEXT_ENABLED=true
MCP_CONTEXT_MAX_SIZE=1048576    # 1MB max context size
MCP_CONTEXT_COMPRESSION=true
```

#### MCP Transport Settings
```bash
# Transport configuration
MCP_TRANSPORT=http              # http, stdio, websocket
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8000
MCP_HTTP_PATH=/mcp

# WebSocket settings (if using WebSocket transport)
MCP_WS_MAX_MESSAGE_SIZE=1048576
MCP_WS_PING_INTERVAL=30
MCP_WS_PING_TIMEOUT=10
```

## Performance Configuration

### Connection Pooling
```bash
# Database connection pooling
DB_POOL_SIZE=20                 # Base connections
DB_MAX_OVERFLOW=30              # Additional connections
DB_POOL_TIMEOUT=30              # Wait timeout
DB_POOL_RECYCLE=3600            # Connection lifetime

# HTTP client pooling
HTTP_POOL_CONNECTIONS=10
HTTP_POOL_MAXSIZE=20
HTTP_POOL_BLOCK=false
```

### Async Configuration
```bash
# Async settings
ASYNC_WORKER_COUNT=4            # Number of async workers
ASYNC_MAX_TASKS=1000            # Max concurrent tasks
ASYNC_QUEUE_SIZE=10000          # Task queue size

# Event loop configuration
EVENT_LOOP_POLICY=uvloop        # uvloop, asyncio
EVENT_LOOP_DEBUG=false
```

### Memory Management
```bash
# Memory configuration
MAX_MEMORY_USAGE=1073741824     # 1GB in bytes
MEMORY_WARNING_THRESHOLD=0.8    # Warn at 80% usage
MEMORY_CLEANUP_INTERVAL=300     # Cleanup every 5 minutes

# Garbage collection
GC_ENABLED=true
GC_THRESHOLD_0=700
GC_THRESHOLD_1=10
GC_THRESHOLD_2=10
```

## Environment-Specific Configuration

### Development Configuration
```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_CONSOLE_ENABLED=true
LOG_REQUEST_DETAILS=true

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/4genthub_dev
DB_ECHO=true

# Cache
CACHE_ENABLED=false             # Disable for development
REDIS_URL=redis://localhost:6379

# CORS (permissive for development)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]
CORS_METHODS=["*"]
CORS_HEADERS=["*"]
CORS_CREDENTIALS=true

# Security (relaxed for development)
JWT_SECRET_KEY=dev-secret-key
SESSION_COOKIE_SECURE=false
```

### Production Configuration
```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE_ENABLED=true

# Database
DATABASE_URL=postgresql+asyncpg://4genthub:${DB_PASSWORD}@4genthub-db:5432/4genthub
DB_ECHO=false
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100

# Cache
CACHE_ENABLED=true
REDIS_URL=redis://:${REDIS_PASSWORD}@4genthub-redis:6379
CONTEXT_CACHE_TTL=3600

# CORS (restrictive for production)
CORS_ORIGINS=["https://your-frontend-domain.com"]
CORS_CREDENTIALS=true

# Security
JWT_SECRET_KEY=${JWT_SECRET}
SESSION_COOKIE_SECURE=true
TOKEN_EXPIRY_HOURS=1

# External services
SENTRY_DSN=${SENTRY_DSN}
SENTRY_ENVIRONMENT=production
```

### Testing Configuration
```bash
# .env.test
ENVIRONMENT=test
DEBUG=false
LOG_LEVEL=ERROR
LOG_CONSOLE_ENABLED=false

# Test database
DATABASE_URL=postgresql://postgres:password@localhost:5432/4genthub_test
DB_ECHO=false

# Disable external services
CACHE_ENABLED=false
SENTRY_DSN=""
REDIS_URL=""

# Fast test execution
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1
CONTEXT_CACHE_ENABLED=false
```

## Security Configuration

### SSL/TLS Configuration
```bash
# SSL settings
SSL_ENABLED=true
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
SSL_CA_PATH=/path/to/ca.pem

# SSL verification
SSL_VERIFY=true
SSL_CHECK_HOSTNAME=true
SSL_MINIMUM_VERSION=TLSv1.2
```

### Security Headers
```bash
# Security headers
SECURITY_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000
HSTS_INCLUDE_SUBDOMAINS=true
CONTENT_TYPE_NOSNIFF=true
X_FRAME_OPTIONS=DENY
X_XSS_PROTECTION="1; mode=block"
```

### Compliance Configuration
```bash
# Compliance settings
COMPLIANCE_ENABLED=true
AUDIT_LOGGING_ENABLED=true
AUDIT_LOG_PATH=/var/log/audit.log
AUDIT_LOG_LEVEL=INFO

# Data retention
DATA_RETENTION_DAYS=365
LOG_RETENTION_DAYS=90
AUDIT_RETENTION_DAYS=2555       # 7 years
```

## Monitoring Configuration

### Health Checks
```bash
# Health check configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30        # Seconds
HEALTH_CHECK_TIMEOUT=10         # Seconds
HEALTH_CHECK_DATABASE=true
HEALTH_CHECK_CACHE=true
HEALTH_CHECK_EXTERNAL_APIS=true
```

### Metrics Configuration
```bash
# Metrics collection
METRICS_ENABLED=true
METRICS_PORT=9090
METRICS_PATH=/metrics
METRICS_INCLUDE_IN_BODY=false

# Prometheus configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_NAMESPACE=4genthub
PROMETHEUS_SUBSYSTEM=api

# Custom metrics
TRACK_REQUEST_DURATION=true
TRACK_DATABASE_QUERIES=true
TRACK_CACHE_OPERATIONS=true
TRACK_CONTEXT_OPERATIONS=true
```

## Configuration Validation

### Required Environment Variables
```python
# Required configuration validation
REQUIRED_VARS = [
    "DATABASE_URL",
    "JWT_SECRET_KEY",
    "HOST",
    "PORT",
    "AUTH_ENABLED",
    "AUTH_PROVIDER"
]

# Required when AUTH_PROVIDER=keycloak
KEYCLOAK_REQUIRED_VARS = [
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "KEYCLOAK_CLIENT_ID",
    "KEYCLOAK_CLIENT_SECRET"
]

# Optional with defaults
OPTIONAL_VARS = {
    "LOG_LEVEL": "INFO",
    "CACHE_ENABLED": "true",
    "DEBUG": "false",
    "ENVIRONMENT": "development",
    "KEYCLOAK_VERIFY_TOKEN_AUDIENCE": "true",
    "KEYCLOAK_TOKEN_CACHE_TTL": "300",
    "KEYCLOAK_PUBLIC_KEY_CACHE_TTL": "3600",
    "KEYCLOAK_SSL_VERIFY": "true"
```

### Configuration Schema
```python
# Configuration schema validation
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # Database
    database_url: str
    db_pool_size: int = 20
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Cache
    cache_enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith('postgresql:'):
            raise ValueError('Invalid database URL scheme. Only postgresql:// is supported.')
        return v
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError('JWT secret must be at least 32 characters')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## Configuration Examples

### Docker Compose Environment
```yaml
# docker-compose.yml
services:
  4genthub:
    environment:
      - DATABASE_URL=postgresql+asyncpg://4genthub:${DB_PASSWORD}@4genthub-db:5432/4genthub
      - REDIS_URL=redis://4genthub-redis:6379
      - JWT_SECRET_KEY=${JWT_SECRET}
      - LOG_LEVEL=INFO
      - CACHE_ENABLED=true
      - CORS_ORIGINS=["https://your-app.com"]
    env_file:
      - .env.production
```

### Kubernetes ConfigMap
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: 4genthub-config
data:
  DATABASE_URL: "postgresql+asyncpg://4genthub:password@postgres:5432/4genthub"
  REDIS_URL: "redis://redis:6379"
  LOG_LEVEL: "INFO"
  CACHE_ENABLED: "true"
  HOST: "0.0.0.0"
  PORT: "8000"
```

### GitHub Actions Environment
```yaml
# .github/workflows/deploy.yml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET }}
  REDIS_URL: ${{ secrets.REDIS_URL }}
  SENTRY_DSN: ${{ secrets.SENTRY_DSN }}
  LOG_LEVEL: "WARNING"
  ENVIRONMENT: "production"
```

## Configuration Management Best Practices

### 1. Secret Management
- **Never commit secrets** to version control
- **Use environment variables** for sensitive data
- **Rotate secrets regularly** (JWT keys, database passwords)
- **Use secret management systems** (AWS Secrets Manager, HashiCorp Vault)

### 2. Environment Separation
- **Separate configurations** for each environment
- **Use environment-specific files** (.env.development, .env.production)
- **Validate configurations** before deployment
- **Document environment differences**

### 3. Configuration Validation
- **Validate required variables** at startup
- **Use type checking** for configuration values
- **Provide clear error messages** for invalid configurations
- **Test configurations** in CI/CD pipelines

### 4. Documentation
- **Document all configuration options**
- **Provide examples** for common scenarios
- **Maintain configuration change logs**
- **Include security considerations**

## Troubleshooting Configuration Issues

### Common Configuration Problems

#### Database Connection Issues
```bash
# Test database connection
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_db():
    engine = create_async_engine('${DATABASE_URL}')
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('Database connection successful')
    await engine.dispose()

asyncio.run(test_db())
"
```

#### Cache Connection Issues
```bash
# Test Redis connection
python -c "
import redis
r = redis.from_url('${REDIS_URL}')
r.ping()
print('Redis connection successful')
"
```

#### JWT Configuration Issues
```python
# Test JWT configuration
import jwt
secret = "${JWT_SECRET_KEY}"
if len(secret) < 32:
    print("ERROR: JWT secret too short")
else:
    token = jwt.encode({"test": "data"}, secret, algorithm="HS256")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    print("JWT configuration valid")
```

### Configuration Debugging
```python
# Debug configuration loading
from src.fastmcp.task_management.config import settings

def debug_config():
    print("Configuration Debug:")
    print(f"Environment: {settings.environment}")
    print(f"Database URL: {settings.database_url[:20]}...")
    print(f"Cache Enabled: {settings.cache_enabled}")
    print(f"Log Level: {settings.log_level}")
    
    # Validate required settings
    required = ["database_url", "jwt_secret_key"]
    for var in required:
        value = getattr(settings, var, None)
        if not value:
            print(f"ERROR: {var} not configured")
        else:
            print(f"✓ {var} configured")

debug_config()
```

This configuration guide provides comprehensive coverage of all configuration options and best practices for deploying and managing the 4genthub system across different environments.