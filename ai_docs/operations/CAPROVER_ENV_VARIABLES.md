# CapRover Environment Variables Configuration

## Backend Service (agenthub-backend)

Set these environment variables in CapRover's App Config for the backend service:

```bash
# CORS Configuration - Can use wildcard since we have token authentication
# Option 1: Allow all origins (recommended for MCP with token auth)
CORS_ORIGINS=*
# Option 2: Restrict to specific origins if needed
# CORS_ORIGINS=${YOUR_FRONTEND_URL},http://localhost:3800

# Database Configuration (if using external database)
DATABASE_URL=postgresql://user:password@host:5432/dbname
DATABASE_HOST=srv-captain--postgredb  # NO http:// prefix for PostgreSQL
DATABASE_NAME=posgresdb
DATABASE_USER=posgres
DATABASE_PASSWORD=your-db-password
DATABASE_PORT=5432

# Application Settings
ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
ENV=production

# Authentication - Use 'keycloak' when Keycloak is configured
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak  # Options: keycloak, local

# MCP Configuration - Use FASTMCP_ prefix (NOT MCP_)
FASTMCP_TRANSPORT=streamable-http
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
JWT_SECRET_KEY=your-secret-key-here

# Feature Flags
FEATURE_AUTO_COMPACT=true
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_MULTI_AGENT=true
FEATURE_RATE_LIMITING=true
FEATURE_REQUEST_LOGGING=true
FEATURE_VISION_SYSTEM=true

# Keycloak Configuration (Required when AUTH_PROVIDER=keycloak)
KEYCLOAK_URL=https://keycloak.92.5.226.7.nip.io
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-api
KEYCLOAK_CLIENT_SECRET=your-actual-client-secret-from-keycloak
```

## Frontend Service (agenthub-frontend)

Set these BUILD ARGUMENTS in CapRover's App Config → Environmental Variables for the frontend service:

```bash
# CRITICAL: Frontend uses VITE_API_URL not VITE_BACKEND_URL
VITE_API_URL=${YOUR_BACKEND_URL}
VITE_BACKEND_URL=${YOUR_BACKEND_URL}
VITE_ENV=production
# NO Keycloak configuration needed - backend handles all auth
```

**IMPORTANT**: 
- The frontend code uses `VITE_API_URL` throughout. Make sure to set this variable!
- Replace `${YOUR_BACKEND_URL}` with your actual backend service URL (e.g., https://captain-app-name.your-domain.com)
- Replace `${YOUR_FRONTEND_URL}` with your actual frontend service URL

## Important Notes

1. **CORS_ORIGINS**: Must include the frontend URL(s) that will access the backend. Separate multiple origins with commas.

2. **Frontend URLs**: The frontend makes API calls at build time, so VITE_* variables must be set as BUILD ARGUMENTS, not runtime environment variables.

3. **Backend URL**: Ensure VITE_BACKEND_URL points to your deployed backend service URL, NOT localhost.

4. **Database**: If using CapRover's built-in PostgreSQL, use the internal connection string provided by CapRover.

5. **Secrets**: Generate strong, unique values for JWT_SECRET_KEY and database passwords.

## Troubleshooting CORS Issues

If you see CORS errors like "No 'Access-Control-Allow-Origin' header is present":

1. **Check CORS_ORIGINS**: Ensure CORS_ORIGINS=* is set in backend environment variables
2. **Verify Authentication Provider**: If using Keycloak, set AUTH_PROVIDER=keycloak (not local)
3. **Use Correct Variable Names**: Use FASTMCP_HOST and FASTMCP_PORT (not MCP_HOST/MCP_PORT)
4. **Database Host Format**: Use srv-captain--postgredb (NO http:// prefix for PostgreSQL)
5. **Frontend Build Variables**: Verify VITE_API_URL is set correctly during build
6. **Check Backend Logs**: Look for authentication errors that might prevent CORS headers

### Common Configuration Mistakes:

- ❌ `AUTH_PROVIDER=local` with Keycloak config → ✅ `AUTH_PROVIDER=keycloak`
- ❌ `MCP_HOST=0.0.0.0` → ✅ `FASTMCP_HOST=0.0.0.0`  
- ❌ `DATABASE_HOST=http://srv-captain--postgredb` → ✅ `DATABASE_HOST=srv-captain--postgredb`
- ❌ Missing CORS_ORIGINS → ✅ `CORS_ORIGINS=*`

## Deployment Steps

1. Deploy backend first with proper CORS_ORIGINS
2. Build and deploy frontend with correct VITE_BACKEND_URL
3. Test the connection between frontend and backend
4. Monitor logs for any errors