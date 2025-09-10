# Branch-Specific Captain Definition Setup

## Overview
The `captain-definition` file is now **untracked by Git** and should be created locally for each deployment.

## Setup for Each Branch

### Backend Branch
```bash
# Switch to backend branch
git checkout backend  # or main, or your backend branch

# Create captain-definition locally (not tracked by git)
cat > captain-definition << 'EOF'
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.backend.production"
}
EOF

# Deploy to CapRover
caprover deploy --appName dhafnck-mcp-backend
```

### Frontend Branch
```bash
# Switch to frontend branch
git checkout frontend  # or your frontend branch

# Create captain-definition locally (not tracked by git)
cat > captain-definition << 'EOF'
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.frontend.production"
}
EOF

# Deploy to CapRover
caprover deploy --appName dhafnck-mcp-frontend
```

## Alternative: Use Environment-Specific Files

Keep both files in repo but with different names:
- `captain-definition-backend` (tracked)
- `captain-definition-frontend` (tracked)

Then copy the appropriate one before deployment:

```bash
# For backend deployment
cp captain-definition-backend captain-definition
caprover deploy --appName dhafnck-mcp-backend

# For frontend deployment
cp captain-definition-frontend captain-definition
caprover deploy --appName dhafnck-mcp-frontend
```

## CapRover Dashboard Method

Instead of using files, you can configure directly in CapRover:

1. **Go to CapRover Dashboard**
2. **Navigate to your app**
3. **Click "Deployment" tab**
4. **Paste the appropriate captain-definition content**
5. **Save and deploy**

## Git Configuration

The `.gitignore` now includes:
```
captain-definition
```

This ensures:
- ✅ No conflicts between branches
- ✅ Each branch can have its own local captain-definition
- ✅ No accidental commits of wrong captain-definition

## Quick Reference

| Branch | App Name | Dockerfile Path |
|--------|----------|----------------|
| backend/main | dhafnck-mcp-backend | ./docker-system/docker/Dockerfile.backend.production |
| frontend | dhafnck-mcp-frontend | ./docker-system/docker/Dockerfile.frontend.production |