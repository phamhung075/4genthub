# PostgreSQL Docker + Keycloak Cloud Integration Guide

## Overview

This guide provides comprehensive instructions for configuring DhafnckMCP with:
- **PostgreSQL** running in Docker container (local development)
- **Keycloak** running on cloud service (authentication)
- **MCP Server** with secure token-based authentication

## Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   Frontend      │──────▶│   MCP Server     │──────▶│  PostgreSQL     │
│  (Port 3800)    │       │   (Port 8001)    │       │  (Docker:5432)  │
└─────────────────┘       └──────────────────┘       └─────────────────┘
         │                         │
         │                         │
         └────────────┬────────────┘
                      │
                      ▼
              ┌──────────────────┐
              │  Keycloak Cloud  │
              │  (Authentication) │
              └──────────────────┘
```

## Prerequisites

- Docker and Docker Compose installed
- Access to a Keycloak cloud instance (or ability to create one)
- Python 3.9+ for MCP server
- Node.js 16+ for frontend (optional)

## Quick Start

### 1. Run Setup Script

```bash
# Make script executable
chmod +x setup-postgres-keycloak.sh

# Run setup
./setup-postgres-keycloak.sh
```

This script will:
- Create `.env.production` with secure passwords
- Set up Docker network
- Create PostgreSQL initialization scripts
- Start PostgreSQL container
- Provide Keycloak configuration instructions

### 2. Configure Keycloak Cloud

#### 2.1 Update Environment Variables

Edit `.env.production` and update Keycloak settings:

```env
KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
```

#### 2.2 Configure Keycloak Realm

In your Keycloak admin console:

1. **Create Realm**: `dhafnck-mcp`

2. **Create Client**: `mcp-backend`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Service Accounts Enabled: `true`
   - Authorization Enabled: `true`
   - Valid Redirect URIs: 
     - `http://localhost:8001/*`
     - `http://localhost:3800/*`
   - Web Origins: 
     - `http://localhost:3800`
     - `http://localhost:8001`

3. **Create Roles**:
   - `mcp-user` - Basic MCP access
   - `mcp-tools` - Tool execution access
   - `mcp-admin` - Full administrative access
   - `mcp-developer` - Developer access with all tools

4. **Create Users** and assign roles:
   ```
   Example user setup:
   - Username: developer@example.com
   - Email: developer@example.com
   - Roles: mcp-user, mcp-tools, mcp-developer
   ```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Or start with PgAdmin for database management
docker-compose --profile tools up -d
```

### 4. Test Integration

```bash
# Run test script
python test-keycloak-mcp.py
```

## Configuration Details

### PostgreSQL Configuration

PostgreSQL runs in Docker with the following default settings:

```yaml
Host: postgres (internal) / localhost (external)
Port: 5432
Database: dhafnck_mcp_prod
User: dhafnck_user
Password: [Generated secure password in .env.production]
```

### Connection Pooling

Optimized for production:

```env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

### Keycloak Token Configuration

MCP server validates tokens using RS256 algorithm:

```env
JWT_ALGORITHM=RS256
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300  # 5 minutes
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600  # 1 hour
```

## MCP Authentication Flow

### 1. Token Acquisition

```python
import requests

# Get token from Keycloak
token_response = requests.post(
    f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
    data={
        "grant_type": "password",
        "client_id": "mcp-backend",
        "client_secret": CLIENT_SECRET,
        "username": "user@example.com",
        "password": "password"
    }
)
token = token_response.json()["access_token"]
```

### 2. MCP API Call with Token

```python
# Use token for MCP API calls
headers = {"Authorization": f"Bearer {token}"}

response = requests.post(
    "http://localhost:8001/mcp/manage_project",
    json={"action": "list"},
    headers=headers
)
```

### 3. Token Validation Process

1. MCP server receives request with Bearer token
2. Validates token signature using Keycloak public key
3. Checks token expiration and audience
4. Extracts user roles and permissions
5. Grants access based on role mappings

## Role-Based Access Control

### Role Mappings

| Keycloak Role | MCP Permissions | Description |
|--------------|-----------------|-------------|
| `mcp-admin` | `*` | Full access to all MCP tools |
| `mcp-developer` | `tools:*`, `context:*`, `agents:*`, `projects:*` | Developer access |
| `mcp-tools` | `tools:execute`, `tools:list`, `context:read`, `context:write` | Tool execution |
| `mcp-user` | `tools:list`, `tools:describe`, `context:read` | Read-only access |

### Permission Examples

```python
# Admin can do everything
permissions = ["*"]

# Developer can manage projects
permissions = ["projects:create", "projects:update", "projects:delete"]

# User can only read
permissions = ["projects:list", "projects:get"]
```

## Database Management

### Using PgAdmin

1. Start PgAdmin:
   ```bash
   docker-compose --profile tools up -d pgadmin
   ```

2. Access at: http://localhost:5050
   - Email: admin@dhafnck.com
   - Password: [Check .env.production]

3. Add PostgreSQL server:
   - Host: postgres
   - Port: 5432
   - Database: dhafnck_mcp_prod
   - Username: dhafnck_user
   - Password: [From .env.production]

### Direct Database Access

```bash
# Connect to PostgreSQL
docker exec -it dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_prod

# Backup database
docker exec dhafnck-postgres pg_dump -U dhafnck_user dhafnck_mcp_prod > backup.sql

# Restore database
docker exec -i dhafnck-postgres psql -U dhafnck_user dhafnck_mcp_prod < backup.sql
```

## Monitoring & Logs

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mcp-server
docker-compose logs -f postgres
```

### Health Checks

```bash
# MCP Server health
curl http://localhost:8001/health

# PostgreSQL health
docker exec dhafnck-postgres pg_isready -U dhafnck_user
```

## Troubleshooting

### Common Issues

#### 1. Keycloak Connection Failed

**Error**: "Failed to connect to Keycloak"

**Solution**:
- Verify KEYCLOAK_URL is correct
- Check network connectivity to Keycloak cloud
- Ensure realm and client are properly configured

#### 2. PostgreSQL Connection Error

**Error**: "Database connection failed"

**Solution**:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

#### 3. Token Validation Failed

**Error**: "Invalid or expired token"

**Solution**:
- Ensure client secret is correct
- Verify user has required roles
- Check token expiration settings
- Clear token cache if needed

#### 4. Permission Denied

**Error**: "Insufficient permissions"

**Solution**:
- Add required roles to user in Keycloak
- Verify role mappings in MCP configuration
- Check permission settings in .env.production

### Debug Mode

Enable debug logging:

```env
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
SQL_DEBUG=true
```

## Production Deployment

### Security Checklist

- [ ] Change all default passwords in .env.production
- [ ] Use strong passwords (min 16 characters)
- [ ] Enable SSL for PostgreSQL connections
- [ ] Configure firewall rules
- [ ] Set up regular database backups
- [ ] Monitor logs for security events
- [ ] Keep Docker images updated
- [ ] Use secrets management for production

### Performance Tuning

1. **PostgreSQL Optimization**:
   ```sql
   -- Adjust shared_buffers (25% of RAM)
   ALTER SYSTEM SET shared_buffers = '1GB';
   
   -- Increase work_mem for complex queries
   ALTER SYSTEM SET work_mem = '10MB';
   
   -- Reload configuration
   SELECT pg_reload_conf();
   ```

2. **Connection Pool Tuning**:
   ```env
   DATABASE_POOL_SIZE=50  # Increase for high load
   DATABASE_MAX_OVERFLOW=100
   ```

3. **MCP Worker Processes**:
   ```env
   MCP_WORKERS=8  # Number of CPU cores
   ```

## Backup & Recovery

### Automated Backups

Create backup script `backup-postgres.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/dhafnck_mcp_${TIMESTAMP}.sql"

# Create backup
docker exec dhafnck-postgres pg_dump -U dhafnck_user dhafnck_mcp_prod > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

Schedule with cron:
```bash
0 2 * * * /path/to/backup-postgres.sh
```

## Migration from Supabase

If migrating from Supabase:

1. Export data from Supabase
2. Transform data format if needed
3. Import to PostgreSQL:
   ```bash
   docker exec -i dhafnck-postgres psql -U dhafnck_user dhafnck_mcp_prod < supabase_export.sql
   ```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review this documentation
- Test with: `python test-keycloak-mcp.py`
- Check PostgreSQL: `docker exec dhafnck-postgres pg_isready`

## Next Steps

1. Configure monitoring (Prometheus/Grafana)
2. Set up CI/CD pipeline
3. Implement rate limiting
4. Add API documentation (Swagger/OpenAPI)
5. Configure log aggregation (ELK stack)