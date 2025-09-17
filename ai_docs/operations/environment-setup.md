# Environment Configuration Guide

## 🔐 Single Source of Truth: `.env` File

This project uses a **SINGLE `.env` file** at the root of the project as the unique source for all environment variables across all services, Docker containers, tests, and deployments.

## 📋 Quick Setup

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   ```bash
   nano .env  # or use your favorite editor
   ```

3. **NEVER commit `.env` to version control** (it's already in `.gitignore`)

## 🔑 Critical Variables to Configure

### Database Credentials
```bash
DATABASE_PASSWORD=your_secure_password_here    # Change this!
POSTGRES_PASSWORD=${DATABASE_PASSWORD}         # Docker uses this
REDIS_PASSWORD=your_redis_password_here        # Change this!
```

### ✅ Security Keys and Authentication Configuration
```bash
# Authentication Configuration
AUTH_ENABLED=true                             # Enable/disable authentication
AUTH_PROVIDER=keycloak                        # Options: keycloak, supabase, local

# Security Keys
SECRET_KEY=dev_secret_key_min_32_chars_change_in_production_environment  # Change this!
JWT_SECRET_KEY=dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50    # Change this!
APP_LOG_LEVEL=info                            # Use lowercase: debug, info, warning, error
```

**🔐 AUTHENTICATION CONFIGURATION**: 
- Use `AUTH_ENABLED=true/false` to enable/disable authentication
- Use `AUTH_PROVIDER` to specify the authentication provider (keycloak, supabase, or local)
- The deprecated `MCP_AUTH_ENABLED` has been removed - use `AUTH_ENABLED` instead

### Keycloak Configuration (when AUTH_PROVIDER=keycloak)
```bash
KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
```

### Supabase Configuration (when AUTH_PROVIDER=supabase)
```bash
SUPABASE_PROJECT_REF=your_project_ref
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key
SUPABASE_DB_PASSWORD=your_db_password
```

### API Keys (if using AI features)
```bash
OPENAI_API_KEY=sk-your-actual-key              # From OpenAI
ANTHROPIC_API_KEY=sk-ant-your-actual-key       # From Anthropic
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token    # From GitHub
```

## 🐳 Docker Integration

### Unified Docker Configuration

All Docker configurations have been **consolidated** into a single `docker-compose.yml` file with **profiles** for different deployment scenarios:

```yaml
# Unified docker-compose.yml with profiles:
services:
  postgres:
    profiles: ["postgresql"]    # Only starts with --profile postgresql
  redis:
    profiles: ["redis"]         # Only starts with --profile redis
  backend:                      # Always starts
  frontend:                     # Always starts
```

### Quick Start with Docker Menu

Use the interactive Docker menu system:
```bash
# From project root (recommended)
./docker-menu.sh

# OR from docker-system directory
cd docker-system && ./docker-menu.sh
```

### Port Configuration
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000 ⚠️ **(CHANGED from 3800)**
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Build Configurations
1. **PostgreSQL Local** - Full local development environment
2. **Supabase Cloud** ⭐ **RECOMMENDED** - Cloud database, no local DB required
3. **Supabase + Redis** - Cloud database with local Redis caching
4. **Performance Mode** - Optimized for low-resource systems

## 🧪 Test Environment

Tests use the same `.env` but with test database:
```bash
TEST_DATABASE_NAME=agenthub_test
TEST_DATABASE_URL=postgresql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${TEST_DATABASE_NAME}
```

## 🚀 Production Deployment

For production, uncomment the production overrides section in `.env`:

```bash
ENV=production
NODE_ENV=production
APP_DEBUG=false
# ⚠️ REMOVED: AUTH_ENABLED=true - Authentication is ALWAYS required
ENABLE_METRICS=true
BACKUP_ENABLED=true
```

**🔐 SECURITY NOTE**: Authentication is now **ALWAYS ENABLED** in all environments. No configuration option exists to disable it.

## 📝 Environment Variable Categories

### Core Settings
- `ENV`: Environment (dev/staging/production)
- `DATABASE_TYPE`: Database type (postgresql/supabase)
- `APP_DEBUG`: Debug mode (true/false)

### Database
- `DATABASE_HOST`: PostgreSQL host
- `DATABASE_PORT`: PostgreSQL port (5432)
- `DATABASE_NAME`: Database name
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password

### Redis Cache
- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port (6379)
- `REDIS_PASSWORD`: Redis password

### Security
- `JWT_SECRET_KEY`: Application secret key
- `JWT_SECRET`: JWT signing secret
- `AGENTHUB_TOKEN`: Application token

### Features
- `FEATURE_VISION_SYSTEM`: Enable vision system
- `FEATURE_HIERARCHICAL_CONTEXT`: Enable hierarchical context
- `FEATURE_MULTI_AGENT`: Enable multi-agent support

## 🔍 Validation

Check your configuration:

```bash
# Verify environment variables are loaded
source .env && echo $DATABASE_TYPE

# Test database connection
docker exec agenthub-postgres pg_isready -U $DATABASE_USER

# Test Redis connection
docker exec agenthub-redis redis-cli ping
```

## ⚠️ Security Best Practices

1. **Never commit `.env` to version control**
2. **Use strong, unique passwords** (minimum 16 characters)
3. **Rotate keys regularly** in production
4. **Use different credentials** for dev/staging/production
5. **Store production secrets** in secure vaults (AWS Secrets Manager, HashiCorp Vault)
6. **Limit API key permissions** to minimum required

## 🆘 Troubleshooting

### Docker Configuration Issues

#### Frontend Memory Crashes
If you see "The build failed because the process exited too early":
```bash
# Solution: Increase NODE_OPTIONS in Dockerfile
ENV NODE_OPTIONS="--max-old-space-size=1536"
```
Memory limits configured: Frontend 1024M, Backend 512M.

#### Port Already Allocated Error
If you see "port is already allocated" for 8000 or 3000:
```bash
# System automatically handles this, but manual fix:
docker stop $(docker ps -q --filter "publish=8000") $(docker ps -q --filter "publish=3000")
docker container prune -f
```

#### Log Level Errors
If you see "Invalid log level 'INFO'":
```bash
# Use lowercase in .env file:
APP_LOG_LEVEL=info  # NOT INFO
```

### Database Connection Fails
- Check `DATABASE_HOST` is correct (localhost for local, postgres for Docker)
- Verify `DATABASE_PASSWORD` matches PostgreSQL configuration
- Ensure PostgreSQL is running: `docker ps`
- For Supabase: Verify `SUPABASE_URL` and connection string format

### Redis Connection Fails
- Check `REDIS_PASSWORD` is set correctly
- Verify Redis is running: `docker ps`
- Test connection: `redis-cli -a $REDIS_PASSWORD ping`

### ✅ Authentication Status - SECURED
- Ensure `SECRET_KEY` is set (minimum 32 characters)
- ✅ **SECURITY ENHANCEMENT**: Authentication is now **ALWAYS REQUIRED** in all environments
- Verify `JWT_SECRET_KEY` is properly base64 encoded
- **NO development bypasses** - all environments require proper authentication

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/ai_docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Environment Variables](https://ai_docs.docker.com/compose/environment-variables/)
- [Supabase Setup Guide](https://supabase.com/ai_docs)