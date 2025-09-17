# Frontend Environment Configuration Guide

## Overview
The frontend application uses environment variables to configure API endpoints and other settings. This ensures no hardcoded addresses are used in production.

## Environment Variables

### Required Variables

#### `VITE_API_URL`
- **Description**: Backend API server URL
- **Local Development**: `http://localhost:8000`
- **Production**: Must be set to your actual API server URL
- **Example**: `https://api.92.5.226.7.nip.io`

### Optional Variables

#### `VITE_DEBUG`
- **Description**: Enable debug logging
- **Default**: `false`
- **Values**: `true` | `false`

#### `VITE_APP_NAME`
- **Description**: Application display name
- **Default**: `4genthub`

#### `VITE_ENV`
- **Description**: Current environment
- **Values**: `development` | `staging` | `production`
- **Default**: `development`

## Configuration Methods

### Local Development

Create a `.env` file in the `4genthub-frontend` directory:

```bash
# .env
VITE_API_URL=http://localhost:8000
VITE_DEBUG=true
VITE_ENV=development
```

### CapRover Production Deployment

1. **Access CapRover Dashboard**
   - Navigate to your CapRover instance
   - Select your frontend application

2. **Configure Environment Variables**
   - Go to the "App Configs" tab
   - Click on "Add Environmental Variable"
   - Add the following variables:

   ```
   VITE_API_URL = https://api.92.5.226.7.nip.io
   VITE_ENV = production
   VITE_DEBUG = false
   ```

3. **Save and Deploy**
   - Click "Save & Update"
   - The app will automatically rebuild and redeploy

### Docker Deployment

For Docker deployments, pass environment variables through docker-compose:

```yaml
services:
  frontend:
    environment:
      - VITE_API_URL=${VITE_API_URL:-http://localhost:8000}
      - VITE_ENV=${VITE_ENV:-production}
      - VITE_DEBUG=${VITE_DEBUG:-false}
```

Or via Docker run command:

```bash
docker run -e VITE_API_URL=https://api.92.5.226.7.nip.io \
           -e VITE_ENV=production \
           -e VITE_DEBUG=false \
           your-frontend-image
```

## Build-Time vs Runtime Configuration

**Important**: Vite environment variables are embedded at **build time**, not runtime. This means:

1. Variables must be set BEFORE building the application
2. Changing environment variables requires rebuilding the app
3. In CapRover, environment variables are applied during the build process

## Verification

To verify your configuration:

1. **Check Browser Console**
   ```javascript
   console.log(import.meta.env.VITE_API_URL)
   ```

2. **Inspect Network Requests**
   - Open browser DevTools
   - Check the Network tab
   - Verify API calls are going to the correct URL

3. **Check Application Logs**
   - The application logs the API URL on startup
   - Look for: `TokenService - API_BASE_URL: <your-url>`

## Common Issues

### Issue: API calls still going to localhost
**Solution**: Ensure you've rebuilt the application after setting environment variables

### Issue: 404 errors on API endpoints
**Solution**: Verify the API server is running and accessible at the configured URL

### Issue: CORS errors
**Solution**: Ensure the backend server has proper CORS configuration for your frontend domain

## Security Notes

- Never commit `.env` files with real credentials
- Use secure HTTPS URLs in production
- Rotate API keys and tokens regularly
- Use environment-specific configurations

## Files Using Environment Variables

The following files use `VITE_API_URL`:

- `/4genthub-frontend/src/services/tokenService.ts`
- `/4genthub-frontend/src/services/apiV2.ts`
- `/4genthub-frontend/src/services/mcpTokenService.ts`
- `/4genthub-frontend/src/contexts/AuthContext.tsx`
- `/4genthub-frontend/src/api-lazy.ts`

All these files follow the pattern:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

This ensures a fallback to localhost if the environment variable is not set.