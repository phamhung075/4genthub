# Keycloak and PostgreSQL Configuration Guide

## Overview

This guide explains how to configure DhafnckMCP to work with:
- **PostgreSQL** running in a Docker container locally
- **Keycloak** running on a cloud service for authentication
- **MCP** tokens for API access

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│                 │     │                  │     │                  │
│   Frontend      │────▶│   MCP Server     │────▶│  PostgreSQL      │
│  (Port 3800)    │     │  (Port 8001)     │     │  (Docker Local)  │
│                 │     │                  │     │  (Port 5432)     │
└─────────────────┘     └──────────────────┘     └──────────────────┘
                               │                           
                               │                           
                               ▼                           
                        ┌──────────────────┐              
                        │                  │              
                        │   Keycloak       │              
                        │  (Cloud Service) │              
                        │                  │              
                        └──────────────────┘              
```

## Prerequisites

1. Docker and Docker Compose installed
2. Keycloak cloud instance configured
3. PostgreSQL Docker container

## Configuration Steps

### 1. Environment Variables

Create or update your `.env` file with the following configuration:

```bash
# =============================================================================
# ENVIRONMENT
# =============================================================================
ENV=production
NODE_ENV=production
APP_ENV=production

# =============================================================================
# POSTGRESQL DATABASE (Docker Container)
# =============================================================================
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost  # Use 'postgres' when running inside Docker
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp_prod
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=YourSecurePasswordHere  # CHANGE THIS!
DATABASE_SSL_MODE=prefer

# Connection URL
DATABASE_URL=postgresql://dhafnck_user:YourSecurePasswordHere@localhost:5432/dhafnck_mcp_prod?sslmode=prefer

# =============================================================================
# KEYCLOAK AUTHENTICATION (Cloud Service)
# =============================================================================
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak

# Replace with your actual Keycloak cloud instance
KEYCLOAK_URL=https://your-keycloak-instance.cloud.com
KEYCLOAK_REALM=dhafnck-mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here  # CHANGE THIS!

# Token settings
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
KEYCLOAK_SSL_VERIFY=true

# =============================================================================
# MCP SERVER
# =============================================================================
MCP_HOST=0.0.0.0
MCP_PORT=8001
JWT_SECRET_KEY=generate-a-secure-64-char-string-here  # CHANGE THIS!
```

### 2. Docker Compose Setup

The `docker-compose.yml` file is configured to:
- Run PostgreSQL in a container
- Run the MCP server with connections to both PostgreSQL and Keycloak
- Optional PgAdmin for database management

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: dhafnck-postgres
    environment:
      POSTGRES_DB: ${DATABASE_NAME}
      POSTGRES_USER: ${DATABASE_USER}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./dhafnck_mcp_main/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  mcp-server:
    build: .
    container_name: dhafnck-mcp-server
    environment:
      DATABASE_HOST: postgres  # Use service name inside Docker
      # ... other environment variables
    depends_on:
      - postgres
    ports:
      - "8001:8001"
```

### 3. Initialize PostgreSQL Database

Run the initialization script to set up the database schema:

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 5

# Initialize the database (if not auto-initialized)
docker exec -i dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_prod < dhafnck_mcp_main/scripts/init.sql
```

### 4. Configure Keycloak

In your Keycloak cloud instance:

1. **Create a Realm**:
   - Name: `dhafnck-mcp`

2. **Create a Client**:
   - Client ID: `mcp-backend`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Valid Redirect URIs: 
     - `http://localhost:8001/*`
     - `http://localhost:3800/*`

3. **Configure Client Credentials**:
   - Go to Credentials tab
   - Copy the Secret and add to `.env` as `KEYCLOAK_CLIENT_SECRET`

4. **Create Roles**:
   - `user` - Basic user role
   - `admin` - Administrative access
   - `mcp-admin` - Full MCP access

5. **Configure Users**:
   - Create test users
   - Assign appropriate roles

### 5. Start the System

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f mcp-server

# Verify health
curl http://localhost:8001/health
```

## Authentication Flow

### 1. User Login

```python
POST http://localhost:8001/auth/login
{
  "username": "user@example.com",
  "password": "password"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "roles": ["user"]
  }
}
```

### 2. MCP Token Creation

For programmatic access, create an MCP token:

```python
POST http://localhost:8001/auth/tokens
Authorization: Bearer {keycloak_token}
{
  "name": "My API Token",
  "permissions": ["read", "write"]
}

Response:
{
  "token": "mcp_token_...",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

### 3. Using Tokens

Both Keycloak tokens and MCP tokens are supported:

```python
# Using Keycloak token
GET http://localhost:8001/api/tasks
Authorization: Bearer {keycloak_token}

# Using MCP token
GET http://localhost:8001/api/tasks
Authorization: Bearer {mcp_token}
```

## Database Schema

The PostgreSQL database includes:

- **Authentication Tables**:
  - `users` - User accounts synced with Keycloak
  - `mcp_tokens` - API access tokens
  - `sessions` - Active user sessions
  - `audit_log` - Security audit trail

- **Application Tables**:
  - `projects` - Project management
  - `git_branches` - Branch tracking
  - `tasks` - Task management
  - `subtasks` - Subtask tracking
  - `contexts` - Hierarchical context system

## Troubleshooting

### Connection Issues

1. **PostgreSQL Connection Failed**:
   ```bash
   # Check if PostgreSQL is running
   docker ps | grep postgres
   
   # Test connection
   docker exec dhafnck-postgres pg_isready -U dhafnck_user
   ```

2. **Keycloak Connection Failed**:
   ```bash
   # Test Keycloak endpoint
   curl https://your-keycloak.cloud.com/realms/dhafnck-mcp/.well-known/openid-configuration
   ```

3. **MCP Server Not Starting**:
   ```bash
   # Check logs
   docker-compose logs mcp-server
   
   # Verify environment variables
   docker exec dhafnck-mcp-server env | grep KEYCLOAK
   ```

### Authentication Issues

1. **Invalid Token**:
   - Verify Keycloak configuration
   - Check token expiration
   - Ensure client secret is correct

2. **Permission Denied**:
   - Check user roles in Keycloak
   - Verify MCP token permissions

## Security Best Practices

1. **Use Strong Passwords**:
   - Database password: At least 20 characters
   - Keycloak client secret: Use generated secret
   - MCP secret key: 64+ random characters

2. **Enable SSL/TLS**:
   - Use HTTPS for Keycloak (enforced for cloud)
   - Enable SSL for PostgreSQL in production
   - Use secure cookies for sessions

3. **Regular Updates**:
   - Keep Docker images updated
   - Monitor Keycloak security advisories
   - Rotate secrets regularly

4. **Audit Logging**:
   - All authentication events are logged
   - Review audit_log table regularly
   - Set up monitoring alerts

## Maintenance

### Backup Database

```bash
# Backup PostgreSQL
docker exec dhafnck-postgres pg_dump -U dhafnck_user dhafnck_mcp_prod > backup.sql

# Restore from backup
docker exec -i dhafnck-postgres psql -U dhafnck_user dhafnck_mcp_prod < backup.sql
```

### Update Keycloak Configuration

When updating Keycloak settings:
1. Update `.env` file
2. Restart MCP server: `docker-compose restart mcp-server`
3. Clear token cache if needed

### Monitor System Health

```bash
# Check system health
curl http://localhost:8001/health

# View metrics
curl http://localhost:8001/metrics

# Check database connections
docker exec dhafnck-postgres psql -U dhafnck_user -c "SELECT count(*) FROM pg_stat_activity;"
```

## Migration from Previous Setup

If migrating from Supabase or other authentication:

1. Export user data from previous system
2. Create users in Keycloak with same emails
3. Users will need to reset passwords
4. Migrate MCP tokens if needed
5. Update frontend to use new auth endpoints

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- Review this documentation
- Check Keycloak documentation
- PostgreSQL documentation

## Next Steps

1. Configure monitoring and alerting
2. Set up automated backups
3. Implement rate limiting
4. Configure CDN for frontend
5. Set up CI/CD pipeline