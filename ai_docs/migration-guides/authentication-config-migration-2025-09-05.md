# Authentication Configuration Migration Guide

## Date: 2025-09-05

## Overview

This guide documents the migration from the deprecated `MCP_AUTH_ENABLED` configuration variable to the new standardized `AUTH_ENABLED` and `AUTH_PROVIDER` configuration approach.

## Changes Made

### 1. Configuration Variables

#### Deprecated
- `MCP_AUTH_ENABLED` - This variable has been completely removed from the codebase

#### New Configuration
- `AUTH_ENABLED` - Controls whether authentication is enabled (true/false)
- `AUTH_PROVIDER` - Specifies the authentication provider (keycloak, supabase, or local)

### 2. Files Updated

#### Environment Configuration
- `.env` - Removed `MCP_AUTH_ENABLED` line

#### Python Scripts
- `dhafnck_mcp_main/scripts/setup/configure-postgres-keycloak-production.py`
- `dhafnck_mcp_main/scripts/setup/setup-clean-postgres-keycloak.py`
- `dhafnck_mcp_main/scripts/setup/setup-postgres-keycloak.py`
- `dhafnck_mcp_main/scripts/setup/configure-postgres-keycloak-clean.py`
- `dhafnck_mcp_main/scripts/setup/configure-postgres-keycloak.py`
- `dhafnck_mcp_main/scripts/test/test-keycloak-mcp-clean.py`
- `dhafnck_mcp_main/scripts/test/test-production-setup.py`

#### Shell Scripts
- `dhafnck_mcp_main/scripts/quick_start_postgres_keycloak.sh`
- `dhafnck_mcp_main/scripts/quick_start_production.sh`
- `dhafnck_mcp_main/scripts/setup/quickstart-postgres-keycloak.sh`
- `dhafnck_mcp_main/scripts/setup/setup-postgres-keycloak.sh`
- `docker-system/start-production.sh`

#### Documentation
- `ai_docs/api-integration/configuration.md`
- `ai_docs/operations/environment-setup.md`
- `ai_docs/index.md`

## Migration Steps

### For Existing Deployments

1. **Update your `.env` file:**
   ```bash
   # Remove this line:
   MCP_AUTH_ENABLED=true
   
   # Add these lines:
   AUTH_ENABLED=true
   AUTH_PROVIDER=keycloak  # or supabase, or local
   ```

2. **If using Keycloak, ensure these variables are set:**
   ```bash
   KEYCLOAK_URL=https://your-keycloak-instance.com
   KEYCLOAK_REALM=dhafnck-mcp
   KEYCLOAK_CLIENT_ID=mcp-backend
   KEYCLOAK_CLIENT_SECRET=your-client-secret-here
   KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
   KEYCLOAK_TOKEN_CACHE_TTL=300
   KEYCLOAK_PUBLIC_KEY_CACHE_TTL=3600
   ```

3. **If using Supabase, ensure these variables are set:**
   ```bash
   SUPABASE_URL=https://[project-ref].supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   ```

### For New Deployments

Use the updated setup scripts which already use the new configuration:
- `quick_start_postgres_keycloak.sh` for PostgreSQL + Keycloak setup
- `quick_start_production.sh` for production deployment

## Benefits of This Change

1. **Clarity**: The new naming convention is more intuitive and clearly separates authentication enablement from provider selection
2. **Flexibility**: Easy to switch between different authentication providers
3. **Consistency**: Aligns with industry-standard naming conventions
4. **Maintainability**: Reduces confusion between MCP-specific and general authentication settings

## Backward Compatibility

This is a **breaking change**. All deployments must update their configuration files to use the new variables. The old `MCP_AUTH_ENABLED` variable will no longer be recognized.

## Testing

After migration, verify authentication is working:

```bash
# Test authentication status
curl http://localhost:8001/health

# If using Keycloak, test token validation
python dhafnck_mcp_main/scripts/test/test-keycloak-mcp-clean.py

# For production setup verification
python dhafnck_mcp_main/scripts/test/test-production-setup.py
```

## Support

If you encounter any issues during migration:
1. Check that all environment variables are correctly set
2. Verify your authentication provider is accessible
3. Review the updated documentation in `ai_docs/api-integration/configuration.md`
4. Check application logs for specific error messages

## Related Documentation

- [Configuration Guide](../api-integration/configuration.md)
- [Environment Setup](../operations/environment-setup.md)
- [Authentication System Architecture](../CORE ARCHITECTURE/authentication-system.md)