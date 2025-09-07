# PostgreSQL Docker + Keycloak Cloud Production Setup

## Overview

This guide provides a clean, production-ready configuration for DhafnckMCP using:
- **PostgreSQL Docker** for local database (port 5432)
- **Keycloak Cloud** for authentication
- **MCP Server** with JWT token validation

All Supabase backward compatibility code has been removed for a cleaner architecture.

## Prerequisites

- Docker and Docker Compose installed
- Keycloak cloud instance configured
- Python 3.9+ installed
- PostgreSQL client tools (optional)

## Quick Setup

### 1. Run Automated Setup

```bash
# Run the setup script
python setup-postgres-keycloak.py
```

This script will:
- Create optimized `.env` file
- Remove Supabase references from codebase
- Setup PostgreSQL initialization script
- Start Docker services
- Run database migrations

### 2. Configure Keycloak

Update `.env` with your Keycloak cloud details:

```env
# Keycloak Cloud Configuration
KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
```

### 3. Start Services

```bash
# Start PostgreSQL only
docker-compose up -d postgres

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Test Authentication

```bash
# Test complete authentication flow
python test-mcp-keycloak-auth.py
```

## Environment Configuration

### Core Settings

```env
# Environment
ENV=production
APP_ENV=production
APP_DEBUG=false

# PostgreSQL Docker
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp_prod
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=SecurePassword2025!

# Keycloak Authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
```

## Keycloak Configuration

### 1. Create Realm

In your Keycloak admin console:

1. Create realm: `dhafnck-mcp`
2. Configure realm settings:
   - Display name: "DhafnckMCP"
   - User registration: Enabled (optional)
   - Email verification: Enabled

### 2. Create Client

1. Create client: `mcp-backend`
2. Settings:
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Valid Redirect URIs: `http://localhost:8001/*`
   - Web Origins: `http://localhost:8001`

3. Credentials:
   - Copy the client secret to `.env`

### 3. Configure Roles

Create the following realm roles:
- `user` - Basic user access
- `admin` - Administrative access
- `developer` - Developer tools access

### 4. Create Test User

1. Users → Add User
2. Set username and email
3. Credentials → Set password
4. Role Mappings → Assign roles

## PostgreSQL Docker Management

### Database Access

```bash
# Connect via psql
psql -h localhost -U dhafnck_user -d dhafnck_mcp_prod

# Access via PgAdmin (optional)
docker-compose --profile tools up -d pgadmin
# Open: http://localhost:5050
```

### Database Backup

```bash
# Backup database
docker exec dhafnck-postgres pg_dump -U dhafnck_user dhafnck_mcp_prod > backup.sql

# Restore database
docker exec -i dhafnck-postgres psql -U dhafnck_user dhafnck_mcp_prod < backup.sql
```

### Database Migrations

```bash
# Run migrations
cd dhafnck_mcp_main
python src/fastmcp/task_management/infrastructure/database/init_database.py

# Verify schema
python scripts/validate_schema.py
```

## MCP Server Configuration

### Authentication Flow

1. **Client Login**: Authenticate with Keycloak
2. **Token Exchange**: Receive JWT access token
3. **MCP Request**: Include token in Authorization header
4. **Token Validation**: MCP validates with Keycloak
5. **Access Granted**: Request processed with user context

### API Authentication

```python
import httpx
import asyncio

async def authenticate_and_call_mcp():
    # 1. Get Keycloak token
    token_response = await httpx.post(
        "https://your-keycloak.com/realms/dhafnck-mcp/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "mcp-backend",
            "client_secret": "your-secret",
            "username": "user@example.com",
            "password": "password"
        }
    )
    
    tokens = token_response.json()
    access_token = tokens["access_token"]
    
    # 2. Call MCP with token
    mcp_response = await httpx.post(
        "http://localhost:8001/mcp/manage_project",
        json={"action": "list"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    return mcp_response.json()
```

## Security Best Practices

### 1. Environment Variables

- Never commit `.env` to version control
- Use strong passwords (minimum 16 characters)
- Rotate secrets regularly
- Use different secrets for each environment

### 2. PostgreSQL Security

```sql
-- Restrict database access
REVOKE ALL ON DATABASE dhafnck_mcp_prod FROM PUBLIC;
GRANT CONNECT ON DATABASE dhafnck_mcp_prod TO dhafnck_user;

-- Use SSL for remote connections
-- Set DATABASE_SSL_MODE=require in production
```

### 3. Keycloak Security

- Enable HTTPS for all endpoints
- Configure token lifetimes appropriately
- Enable brute force protection
- Configure password policies
- Use MFA for admin accounts

### 4. Docker Security

```yaml
# docker-compose.yml security additions
services:
  postgres:
    # Run as non-root user
    user: "999:999"
    # Limit resources
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    # Use secrets instead of env vars
    secrets:
      - db_password
```

## Monitoring & Health Checks

### Health Endpoints

```bash
# MCP Server health
curl http://localhost:8001/health

# PostgreSQL health
docker exec dhafnck-postgres pg_isready -U dhafnck_user

# Keycloak realm check
curl https://your-keycloak.com/realms/dhafnck-mcp
```

### Logging

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f postgres
docker-compose logs -f mcp-server

# Export logs
docker-compose logs > logs.txt
```

## Troubleshooting

### Common Issues

#### 1. PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs dhafnck-postgres

# Test connection
psql -h localhost -U dhafnck_user -d dhafnck_mcp_prod -c "SELECT 1"
```

#### 2. Keycloak Authentication Failed

```bash
# Test Keycloak connectivity
curl https://your-keycloak.com/realms/dhafnck-mcp

# Verify client credentials
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'Client ID: {os.getenv(\"KEYCLOAK_CLIENT_ID\")}')
print(f'URL: {os.getenv(\"KEYCLOAK_URL\")}')
"
```

#### 3. MCP Token Validation Failed

```bash
# Check MCP logs for JWT errors
docker logs dhafnck-mcp-server | grep -i jwt

# Test token validation
python test-mcp-keycloak-auth.py
```

### Reset Everything

```bash
# Stop all services
docker-compose down -v

# Remove volumes
docker volume rm dhafnck_postgres_data dhafnck_mcp_logs

# Recreate from scratch
python setup-postgres-keycloak.py
docker-compose up -d
```

## Performance Optimization

### PostgreSQL Tuning

```sql
-- Add to postgresql.conf or via ALTER SYSTEM
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;

-- Reload configuration
SELECT pg_reload_conf();
```

### Connection Pooling

```env
# Add to .env for connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=1800
```

### Keycloak Caching

```env
# Token caching configuration
KEYCLOAK_TOKEN_CACHE_TTL=300  # 5 minutes
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600  # 1 hour
```

## Production Deployment Checklist

- [ ] Strong passwords in `.env`
- [ ] Keycloak HTTPS enabled
- [ ] PostgreSQL SSL enabled
- [ ] Backup strategy configured
- [ ] Monitoring setup
- [ ] Log aggregation configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Health checks passing
- [ ] Load testing completed

## Support & Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- Project Issues: [GitHub Issues](https://github.com/your-repo/issues)