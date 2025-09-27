# Production Environment Configuration (.env.sample.pro)

This file contains a production-ready environment configuration template. Copy the content below to create your `.env.sample.pro` file.

```bash
# =============================================================================
# agenthub PRODUCTION Environment Configuration
# =============================================================================
# Production-ready configuration with secure defaults and best practices
# Copy to .env and replace all placeholder values with your production settings
# =============================================================================

# =============================================================================
# GENERAL SETTINGS - PRODUCTION OPTIMIZED
# =============================================================================
# Production environment - ensures proper security and performance settings
ENV=production

# Container environment - auto-detected by Docker
CONTAINER_ENV=docker

# Debug mode - MUST be false in production
APP_DEBUG=false

# Production log level - reduce noise, only important events
# WARNING: Only warnings, errors, and critical issues (recommended)
# ERROR: Only errors and critical issues (high-traffic sites)
APP_LOG_LEVEL=WARNING

# Node environment for optimized builds
NODE_ENV=production

# =============================================================================
# BACKEND CONFIGURATION - PRODUCTION HARDENED
# =============================================================================

# CORS - Replace with your actual production domains
# NEVER use "*" in production unless absolutely necessary
CORS_ORIGINS=https://app.yourdomain.com,https://api.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# -----------------------------------------------------------------------------
# DATABASE - PRODUCTION POSTGRESQL (REQUIRED)
# -----------------------------------------------------------------------------
# Production should use PostgreSQL for reliability and performance
DATABASE_TYPE=postgresql

# Production database connection - Replace with your actual values
DATABASE_HOST=db.yourdomain.com
DATABASE_PORT=5432
DATABASE_NAME=agenthub_production
DATABASE_USER=agenthub_prod_user
DATABASE_PASSWORD=CHANGE_THIS_USE_SECURE_PASSWORD_MIN_32_CHARS

# SSL Mode - CRITICAL for production security
# require: Standard for cloud providers (AWS RDS, Google Cloud SQL, Azure)
# verify-ca: Enhanced security with CA verification
# verify-full: Maximum security with hostname verification
DATABASE_SSL_MODE=require

# Connection pool - Production optimized settings
DATABASE_POOL_SIZE=100              # Increase for high traffic
DATABASE_MAX_OVERFLOW=150          # Allow burst traffic
DATABASE_POOL_TIMEOUT=30           # Reduce timeout for faster failure detection
DATABASE_POOL_RECYCLE=3600         # Recycle connections every hour
DATABASE_POOL_PRE_PING=true        # Verify connections before use

# Connection settings - Production tuned
DATABASE_CONNECT_TIMEOUT=10        # Fast failure on connection issues
DATABASE_APPLICATION_NAME=agenthub_production
DATABASE_OPTIONS=-c timezone=UTC -c statement_timeout=30000
DATABASE_KEEPALIVES=1
DATABASE_KEEPALIVES_IDLE=60
DATABASE_KEEPALIVES_INTERVAL=10
DATABASE_KEEPALIVES_COUNT=5

# Performance settings - Production optimized
DATABASE_STATEMENT_TIMEOUT=30      # 30 seconds max query time
DATABASE_LOCK_TIMEOUT=10           # Fast lock timeout
DATABASE_TCP_KEEPALIVES_IDLE=300
DATABASE_TCP_KEEPALIVES_INTERVAL=30
DATABASE_TCP_KEEPALIVES_COUNT=5

# SQL Debug - MUST be false in production
SQL_DEBUG=false

# Auto-migrate - MUST be false in production (use manual migrations)
AUTO_MIGRATE=false

# -----------------------------------------------------------------------------
# SERVER SETTINGS - PRODUCTION SECURE
# -----------------------------------------------------------------------------
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000

# JWT Secret - CRITICAL: Generate unique 64+ character random string
# Example generation: openssl rand -base64 64
JWT_SECRET_KEY=CHANGE_THIS_GENERATE_UNIQUE_64_CHAR_RANDOM_STRING_FOR_PRODUCTION

# -----------------------------------------------------------------------------
# AUTHENTICATION - KEYCLOAK PRODUCTION
# -----------------------------------------------------------------------------
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak

# Replace with your production Keycloak instance
KEYCLOAK_URL=https://auth.yourdomain.com
KEYCLOAK_REALM=agenthub_production
KEYCLOAK_CLIENT_ID=mcp-backend
# CRITICAL: Use secure secret from Keycloak admin console
KEYCLOAK_CLIENT_SECRET=CHANGE_THIS_GET_FROM_KEYCLOAK_ADMIN_CONSOLE

# -----------------------------------------------------------------------------
# FEATURE FLAGS - PRODUCTION SETTINGS
# -----------------------------------------------------------------------------
FEATURE_VISION_SYSTEM=true
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_MULTI_AGENT=true
FEATURE_RATE_LIMITING=true          # CRITICAL: Enable rate limiting
FEATURE_REQUEST_LOGGING=false       # Disable verbose logging in production



# =============================================================================
# FRONTEND CONFIGURATION - PRODUCTION URLS
# =============================================================================

# Frontend port (if running separately)
FRONTEND_PORT=3800

# CRITICAL: Replace with your actual production API URL
# Examples:
# - AWS: https://api.yourdomain.com
# - CapRover: https://backend.captain.yourdomain.com
# - Custom: https://api.yourdomain.com
VITE_API_URL=https://api.yourdomain.com

# Frontend environment settings
VITE_ENV=production
VITE_DEBUG=false
VITE_APP_NAME=agenthub

# -----------------------------------------------------------------------------
# FRONTEND AUTHENTICATION - PRODUCTION
# -----------------------------------------------------------------------------
# Must match backend Keycloak configuration
VITE_KEYCLOAK_URL=https://auth.yourdomain.com
VITE_KEYCLOAK_REALM=agenthub_production
VITE_KEYCLOAK_CLIENT_ID=mcp-frontend

# -----------------------------------------------------------------------------
# FRONTEND LOGGING - PRODUCTION OPTIMIZED
# -----------------------------------------------------------------------------
VITE_LOG_ENABLED=true
VITE_LOG_LEVEL=error               # Only errors in production
VITE_LOG_SHOW_TIMESTAMP=true
VITE_LOG_SHOW_LEVEL=true
VITE_LOG_SHOW_FILE_PATH=false      # Hide file paths in production
VITE_LOG_COLORIZE=false            # No colors in production logs
VITE_LOG_TO_CONSOLE=true
VITE_LOG_TO_LOCALSTORAGE=false     # Disable local storage logging
VITE_LOG_TO_REMOTE=true             # Enable remote logging for monitoring
VITE_LOG_REMOTE_ENDPOINT=https://logs.yourdomain.com/api/logs
VITE_LOG_MAX_STORAGE_SIZE=1048576  # 1MB limit if enabled

# =============================================================================
# AI PATHS - PRODUCTION DIRECTORIES
# =============================================================================
AI_DATA=/app/logs                  # Container path for logs
AI_DOCS=/app/ai_docs               # Container path for AI docs

# =============================================================================
# PRODUCTION DEPLOYMENT CHECKLIST
# =============================================================================
# Before deploying to production, ensure:
#
# ✅ DATABASE SECURITY:
#    - [ ] Strong database password (32+ characters)
#    - [ ] DATABASE_SSL_MODE=require or higher
#    - [ ] Database user has minimal required permissions
#    - [ ] Database is not publicly accessible
#
# ✅ AUTHENTICATION:
#    - [ ] JWT_SECRET_KEY is unique and 64+ characters
#    - [ ] Keycloak is properly configured with SSL
#    - [ ] Client secrets are secure and rotated regularly
#    - [ ] AUTH_ENABLED=true
#
# ✅ NETWORK SECURITY:
#    - [ ] CORS_ORIGINS lists only your domains (no wildcards)
#    - [ ] All URLs use HTTPS (no HTTP)
#    - [ ] FEATURE_RATE_LIMITING=true
#    - [ ] Firewall rules configured properly
#
# ✅ LOGGING & MONITORING:
#    - [ ] APP_LOG_LEVEL=WARNING or ERROR
#    - [ ] SQL_DEBUG=false
#    - [ ] APP_DEBUG=false
#    - [ ] Remote logging configured (VITE_LOG_TO_REMOTE)
#
# ✅ PERFORMANCE:
#    - [ ] Database connection pool sized appropriately
#    - [ ] Statement timeouts configured
#    - [ ] AUTO_MIGRATE=false (use manual migrations)
#    - [ ] NODE_ENV=production for optimized builds
#
# ✅ DEPLOYMENT SPECIFIC:
#    AWS/GCP/Azure:
#    - [ ] Use managed PostgreSQL with automatic backups
#    - [ ] Configure security groups/VPC properly
#    - [ ] Enable monitoring and alerting
#
#    CapRover:
#    - [ ] DATABASE_HOST=srv-captain--postgres
#    - [ ] DATABASE_SSL_MODE=disable (internal network)
#    - [ ] Configure persistent volumes for data
#
#    Kubernetes:
#    - [ ] Use secrets for sensitive values
#    - [ ] Configure resource limits
#    - [ ] Set up health checks and probes
#
# ✅ BACKUP & RECOVERY:
#    - [ ] Database backup strategy in place
#    - [ ] Backup retention policy configured
#    - [ ] Recovery procedure documented and tested
#
# ✅ SECRETS MANAGEMENT:
#    - [ ] Never commit .env file to repository
#    - [ ] Use secret management service (Vault, AWS Secrets Manager)
#    - [ ] Rotate secrets regularly
#    - [ ] Document secret rotation procedure
#
# =============================================================================
# SECURITY NOTES
# =============================================================================
# 1. Generate secure random values:
#    JWT Secret: openssl rand -base64 64
#    DB Password: openssl rand -base64 32
#
# 2. Use environment-specific values:
#    Never reuse secrets between environments
#    Each environment should have unique credentials
#
# 3. Regular security audits:
#    Review and rotate secrets quarterly
#    Monitor for unauthorized access attempts
#    Keep dependencies updated
#
# 4. Principle of least privilege:
#    Database user should have minimal permissions
#    Application should not run as root
#    Network access should be restricted
#
# =============================================================================
# MONITORING RECOMMENDATIONS
# =============================================================================
# 1. Application Metrics:
#    - Response times
#    - Error rates
#    - Active users
#    - API usage patterns
#
# 2. Infrastructure Metrics:
#    - CPU and memory usage
#    - Database connection pool status
#    - Disk space
#    - Network latency
#
# 3. Security Metrics:
#    - Failed authentication attempts
#    - Rate limit violations
#    - Suspicious activity patterns
#    - SSL certificate expiration
#
# 4. Alerting Thresholds:
#    - Error rate > 1%
#    - Response time > 2 seconds
#    - Database connection pool > 80%
#    - Disk usage > 80%
#
# =============================================================================
```

## Key Differences from Development Configuration

### 1. **Security Hardening**
- `APP_DEBUG=false` - No debug information exposed
- `DATABASE_SSL_MODE=require` - Enforce SSL for database connections
- `CORS_ORIGINS` - Specific domains only, no wildcards
- `JWT_SECRET_KEY` - Must be 64+ characters
- `FEATURE_RATE_LIMITING=true` - Protect against abuse

### 2. **Performance Optimization**
- `APP_LOG_LEVEL=WARNING` - Reduced logging overhead
- `DATABASE_POOL_SIZE=100` - Larger connection pool for production
- `DATABASE_STATEMENT_TIMEOUT=30` - Prevent long-running queries
- `NODE_ENV=production` - Optimized builds
- `AUTO_MIGRATE=false` - Manual migration control

### 3. **Monitoring & Observability**
- `VITE_LOG_TO_REMOTE=true` - Centralized logging
- `VITE_LOG_LEVEL=error` - Only critical frontend errors
- Structured logging configuration for analysis

### 4. **Database Configuration**
- PostgreSQL required (no SQLite)
- SSL connections mandatory
- Optimized connection pooling
- Performance tuning parameters

### 5. **Authentication**
- Keycloak integration required
- Separate frontend/backend clients
- Secure client secrets

## Usage Instructions

1. **Copy the configuration block above** to create `.env.sample.pro` in your project root
2. **Review each section** and replace placeholder values:
   - Replace `yourdomain.com` with actual domain
   - Generate secure JWT secret: `openssl rand -base64 64`
   - Generate secure database password: `openssl rand -base64 32`
3. **Follow the deployment checklist** before going live
4. **Never commit** the actual `.env` file with real credentials

## Deployment-Specific Configurations

### For AWS/GCP/Azure
```bash
DATABASE_HOST=your-rds-instance.region.rds.amazonaws.com
DATABASE_SSL_MODE=require
```

### For CapRover
```bash
DATABASE_HOST=srv-captain--postgres
DATABASE_SSL_MODE=disable  # Internal Docker network
```

### For Kubernetes
```bash
# Use ConfigMaps and Secrets
# Don't hardcode values in .env
```

## Security Best Practices

1. **Rotate secrets quarterly**
2. **Use different credentials per environment**
3. **Enable audit logging**
4. **Monitor failed authentication attempts**
5. **Keep dependencies updated**
6. **Regular security scans**