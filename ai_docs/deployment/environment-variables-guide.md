# Environment Variables Guide: ENV vs NODE_ENV vs VITE_ENV

## Overview
This guide clarifies the purpose and usage of different environment variables in the 4genthub project.

## Variable Definitions

### 1. `ENV` (Backend - Python/FastAPI)
- **Purpose**: Controls the Python backend environment
- **Used by**: FastAPI, SQLAlchemy, Python logging
- **Values**: `development`, `staging`, `production`
- **Location**: Backend services only
- **Example Usage**:
  ```python
  if os.getenv("ENV") == "production":
      # Production-specific configuration
  ```

### 2. `NODE_ENV` (Frontend Build - Node.js/Vite)
- **Purpose**: Controls Node.js build process and optimizations
- **Used by**: Vite, Webpack, Node.js build tools
- **Values**: `development`, `production`, `test`
- **Location**: Build process only (NOT accessible in browser)
- **Effects**:
  - `production`: Enables minification, tree-shaking, optimizations
  - `development`: Enables source maps, hot reload, debug info
- **Example Usage**:
  ```javascript
  // In vite.config.js or build scripts
  if (process.env.NODE_ENV === 'production') {
      // Production build optimizations
  }
  ```

### 3. `VITE_ENV` (Frontend Runtime - Browser)
- **Purpose**: Controls frontend application behavior at runtime
- **Used by**: React components, frontend services
- **Values**: `development`, `staging`, `production`
- **Location**: Available in browser via `import.meta.env`
- **Example Usage**:
  ```typescript
  // In React components
  if (import.meta.env.VITE_ENV === 'production') {
      // Production-specific behavior
  }
  ```

## Key Differences

| Variable | Environment | Build Time | Runtime | Accessible In Browser |
|----------|------------|------------|---------|----------------------|
| ENV | Backend | ✓ | ✓ | ✗ |
| NODE_ENV | Frontend Build | ✓ | ✗ | ✗ |
| VITE_ENV | Frontend App | ✓ | ✓ | ✓ |

## Recommended Configuration

### Development
```bash
# Backend
ENV=development

# Frontend Build
NODE_ENV=development

# Frontend Runtime
VITE_ENV=development
```

### Production
```bash
# Backend
ENV=production

# Frontend Build
NODE_ENV=production

# Frontend Runtime
VITE_ENV=production
```

## Why Three Variables?

1. **Separation of Concerns**:
   - Backend and frontend have different environment needs
   - Build-time and runtime configurations serve different purposes

2. **Security**:
   - `NODE_ENV` and `ENV` are never exposed to the browser
   - Only `VITE_*` prefixed variables are bundled into frontend code

3. **Flexibility**:
   - Can run production builds locally (NODE_ENV=production, VITE_ENV=development)
   - Can test production behavior with development builds

## Common Patterns

### Pattern 1: Unified Production
```bash
ENV=production
NODE_ENV=production
VITE_ENV=production
```
All systems in production mode.

### Pattern 2: Production Build, Development Runtime
```bash
ENV=development
NODE_ENV=production  # Optimized build
VITE_ENV=development  # But with dev API endpoints
```
Useful for testing production builds locally.

### Pattern 3: Staging Environment
```bash
ENV=staging
NODE_ENV=production  # Production-optimized build
VITE_ENV=staging  # Staging-specific features
```
Production-like environment for testing.

## Usage in Code

### Backend (Python)
```python
import os

environment = os.getenv("ENV", "development")
if environment == "production":
    # Production database
    database_url = os.getenv("DATABASE_URL")
else:
    # Local database
    database_url = "sqlite:///local.db"
```

### Frontend Build (vite.config.js)
```javascript
export default {
  build: {
    minify: process.env.NODE_ENV === 'production',
    sourcemap: process.env.NODE_ENV !== 'production'
  }
}
```

### Frontend Runtime (React)
```typescript
import { VITE_ENV, IS_PRODUCTION } from './config/environment';

if (IS_PRODUCTION) {
  // Disable debug features
  console.log = () => {};
}

// Or directly
if (import.meta.env.VITE_ENV === 'production') {
  // Production behavior
}
```

## Migration Path

If you're currently using mixed variables:

1. **Backend**: Use `ENV` consistently
2. **Frontend Build**: Use `NODE_ENV` for build optimization
3. **Frontend Runtime**: Use `VITE_ENV` for application behavior

## CapRover Deployment

In CapRover, set these environment variables:

```bash
# Backend Container
ENV=production
DATABASE_URL=...
JWT_SECRET_KEY=...

# Frontend Container (Build Args)
NODE_ENV=production
VITE_ENV=production
VITE_API_URL=https://api.yourdomain.com
```

## Best Practices

1. **Always set all three** in production to avoid confusion
2. **Use VITE_ENV** for frontend feature flags, not NODE_ENV
3. **Keep NODE_ENV** for build optimizations only
4. **Use ENV** for backend configuration only
5. **Document** which variable controls what in your project

## Troubleshooting

### Issue: Frontend not detecting production mode
- Check `VITE_ENV`, not `NODE_ENV`
- NODE_ENV affects build, not runtime behavior

### Issue: Backend not using production database
- Check `ENV`, not `NODE_ENV`
- Backend doesn't use Node.js environment variables

### Issue: Builds not optimized
- Check `NODE_ENV=production` during build
- This controls webpack/vite optimizations

## Summary

- **ENV**: Backend environment (Python/FastAPI)
- **NODE_ENV**: Frontend build optimization (Node.js/Vite)
- **VITE_ENV**: Frontend runtime environment (React/Browser)

Use the appropriate variable for each context to maintain clear separation of concerns.