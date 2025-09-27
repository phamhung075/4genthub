# Runtime Environment Variable Configuration Fix

## Problem Identified
Your CapRover environment variables were correctly set to HTTPS:
- `VITE_API_URL=https://api.92.5.226.7.nip.io`

But the frontend was still using HTTP, causing mixed content errors.

## Root Cause
**Vite bundles environment variables at BUILD TIME, not runtime.** When Docker builds the image, if the environment variables aren't passed as build arguments, they get baked into the JavaScript bundle with default values.

## Solution Implemented
Implemented runtime injection of environment variables that overrides build-time values.

### Changes Made:

1. **Created Runtime Config File** (`agenthub-frontend/public/env-config.js`):
   - Placeholder file that gets replaced at container startup
   - Contains window._env_ object with environment variables

2. **Updated HTML** (`agenthub-frontend/index.html`):
   - Added `<script src="/env-config.js"></script>` to load runtime config

3. **Modified Environment Config** (`agenthub-frontend/src/config/environment.ts`):
   - Added `getEnvVar()` helper function
   - Checks runtime config first (window._env_)
   - Falls back to build-time values if runtime not available
   - Still includes HTTPS auto-upgrade for mixed content protection

4. **Updated Docker Entrypoint** (`Dockerfile.frontend.production`):
   - Modified entrypoint script to create env-config.js at startup
   - Injects actual environment variables from CapRover
   - Creates the file in /usr/share/nginx/html/

## How It Works

1. **Build Time**:
   - Vite builds with default values
   - env-config.js contains placeholders

2. **Container Startup**:
   - Docker entrypoint reads environment variables from CapRover
   - Replaces env-config.js with actual values
   - Starts nginx to serve the app

3. **Runtime**:
   - Browser loads env-config.js before main app
   - App code checks window._env_ for configuration
   - Uses runtime values instead of build-time defaults

## Deployment Instructions

### Option 1: Deploy via CapRover Web UI

1. Build and package:
```bash
cd ./agenthub-frontend
npm run build
tar -czf frontend-runtime-fix.tar.gz captain-definition build/ package.json
```

2. Upload to CapRover:
   - Go to CapRover dashboard
   - Navigate to Apps → webapp
   - Click "Deploy via Upload"
   - Upload the tar.gz file
   - Deploy

### Option 2: Git Push Deploy

```bash
cd /home/daihungpham/__projects__/agentic-project
git add -A
git commit -m "fix: implement runtime environment variable configuration for frontend"
git push origin frontend
```

Then trigger CapRover deployment.

## Verification

After deployment:

1. Check browser console for environment variables:
```javascript
console.log(window._env_);
```

2. Verify API URL is using HTTPS:
```javascript
console.log(window._env_.VITE_API_URL);
// Should output: https://api.92.5.226.7.nip.io
```

3. Check network tab - all API calls should use HTTPS

## Benefits

1. **No Rebuild Required**: Change environment variables in CapRover without rebuilding
2. **True Runtime Configuration**: Variables are read at container startup, not build time
3. **Mixed Content Protection**: Still includes HTTPS auto-upgrade as fallback
4. **Backward Compatible**: Works with both runtime and build-time configuration

## Environment Variables Now Supported at Runtime

- `VITE_API_URL` - Backend API URL
- `VITE_BACKEND_URL` - Legacy backend URL (falls back to VITE_API_URL)
- `VITE_KEYCLOAK_URL` - Keycloak authentication server
- `VITE_KEYCLOAK_REALM` - Keycloak realm
- `VITE_KEYCLOAK_CLIENT_ID` - Keycloak client ID
- `VITE_ENV` - Environment (development/staging/production)
- `VITE_DEBUG` - Debug mode flag
- `VITE_APP_NAME` - Application name

## Troubleshooting

If environment variables are still not working:

1. **Check CapRover logs**:
   - Should show "Runtime configuration injected" with values

2. **Verify env-config.js is created**:
   - Navigate to https://webapp.92.5.226.7.nip.io/env-config.js
   - Should show actual values, not placeholders

3. **Clear browser cache**:
   - Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
   - Clear site data in DevTools

4. **Check Docker image**:
   - Ensure using updated Dockerfile.frontend.production
   - Verify entrypoint script includes env-config.js creation