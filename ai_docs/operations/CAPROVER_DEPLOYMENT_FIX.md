# 🚨 CapRover Deployment Fix Guide

## Problem Summary
Your frontend at `https://agenthub-frontend.92.5.226.7.nip.io` is trying to connect to `localhost:8000` instead of your backend at `https://agenthub-backend.92.5.226.7.nip.io`.

## ✅ Files Already Fixed

### 1. Dockerfile.frontend.production
- ✅ Properly accepts build arguments for `VITE_API_URL`
- ✅ Sets environment variables during build
- ✅ Uses nginx for serving the built application

### 2. captain-definition Files
- ✅ `captain-definition-frontend` - Uses CapRover environment variables
- ✅ `captain-definition-backend` - Points to correct Dockerfile

### 3. Backend CORS Configuration
- ✅ Modified `mcp_entry_point.py` to read `CORS_ORIGINS` from environment
- ✅ Supports comma-separated list of allowed origins

## 🔧 CapRover Configuration Steps

### Step 1: Configure Backend App Variables

1. Go to CapRover Dashboard → Apps → `agenthub-backend`
2. Click on "App Config" → "Environmental Variables"
3. Add these variables:

```bash
# CORS Configuration - Allow all origins (security via token authentication)
CORS_ORIGINS=*
# Note: MCP server uses token-based auth, so CORS can be open
# Tokens are generated from frontend and validate all MCP access

# Database (adjust to your setup)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak

# Keycloak Configuration (if using)
KEYCLOAK_URL=https://your-keycloak-server.com
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-secret

# Server Configuration
FASTMCP_TRANSPORT=streamable-http
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
MCP_HOST=0.0.0.0
MCP_PORT=8001

# Other settings
ENV=production
APP_DEBUG=false
PYTHONUNBUFFERED=1
```

4. Click "Save & Restart"

### Step 2: Configure Frontend App Variables

1. Go to CapRover Dashboard → Apps → `agenthub-frontend`
2. Click on "App Config" → "Environmental Variables"
3. Add these BUILD variables (CRITICAL - these are build-time variables):

```bash
# CRITICAL: Frontend uses VITE_API_URL, not VITE_BACKEND_URL
VITE_API_URL=https://agenthub-backend.92.5.226.7.nip.io
VITE_BACKEND_URL=https://agenthub-backend.92.5.226.7.nip.io
VITE_ENV=production

# Keycloak (if backend handles auth, these might not be needed)
VITE_KEYCLOAK_URL=https://your-keycloak-server.com
VITE_KEYCLOAK_REALM=your-realm
VITE_KEYCLOAK_CLIENT_ID=mcp-backend
```

4. Click "Save"

### Step 3: Deploy Backend

1. Copy `captain-definition-backend` to `captain-definition` in your project root
2. Push to your backend branch/repo:
```bash
git add captain-definition
git commit -m "Add CapRover backend configuration"
git push
```
3. In CapRover, deploy from GitHub or use CapRover CLI

### Step 4: Deploy Frontend

1. Copy `captain-definition-frontend` to `captain-definition` in your project root
2. Push to your frontend branch/repo:
```bash
git add captain-definition
git commit -m "Add CapRover frontend configuration with correct API URL"
git push
```
3. In CapRover, click "Force Build" to ensure environment variables are used

### Step 5: Verify Deployment

1. **Check Backend Health:**
```bash
curl https://agenthub-backend.92.5.226.7.nip.io/health
# Should return: {"status":"healthy"}
```

2. **Check Frontend API Calls:**
- Open `https://agenthub-frontend.92.5.226.7.nip.io`
- Open browser DevTools → Network tab
- API calls should go to `https://agenthub-backend.92.5.226.7.nip.io`
- NOT to `localhost:8000`

3. **Check CORS Headers:**
```bash
curl -H "Origin: https://agenthub-frontend.92.5.226.7.nip.io" \
     -I https://agenthub-backend.92.5.226.7.nip.io/health
# Should include: Access-Control-Allow-Origin header
```

## 🐛 Troubleshooting

### Frontend Still Calling localhost:8000

**Cause:** Build didn't use environment variables

**Fix:**
1. Ensure `VITE_API_URL` is set in CapRover env variables
2. Click "Force Build" in CapRover
3. Check build logs for "Building with VITE_API_URL=..."

### CORS Errors

**Cause:** Backend doesn't allow frontend origin

**Fix:**
1. Add frontend URL to `CORS_ORIGINS` in backend env
2. Restart backend service
3. Verify with curl command above

### Backend Shows nginx Instead of Python

**Cause:** Wrong Docker image or Dockerfile

**Fix:**
1. Ensure `Dockerfile.backend.production` runs Python, not nginx
2. Check last line is: `CMD ["python", "-m", "fastmcp.server"]`
3. Force rebuild in CapRover

## 📝 Key Points

1. **Frontend uses `VITE_API_URL`** - This is what the code looks for
2. **Build-time variables** - Frontend variables must be set during Docker build
3. **CORS_ORIGINS** - Backend must explicitly allow frontend URL
4. **Force Build** - Use this in CapRover after changing env variables

## 🚀 Quick Commands

```bash
# Test backend from terminal
curl https://agenthub-backend.92.5.226.7.nip.io/health

# Test CORS
curl -H "Origin: https://agenthub-frontend.92.5.226.7.nip.io" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://agenthub-backend.92.5.226.7.nip.io/api/auth/login

# View Docker logs in CapRover
# Go to App → Logs in CapRover dashboard
```

## ✅ Success Criteria

- [ ] Backend returns health check at `/health`
- [ ] Frontend makes API calls to backend URL, not localhost
- [ ] No CORS errors in browser console
- [ ] Login/Register forms work correctly