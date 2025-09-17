# 🚨 CRITICAL: CapRover Using Wrong Dockerfile!

## The Problem
Your **backend app (agenthub-backend)** is building with the **frontend Dockerfile**! This is why you see:
- Vite build output
- nginx:alpine 
- COPY failed for /app/dist

## The Solution

### Option 1: Fix in CapRover Dashboard (Easiest)

1. **Go to CapRover Dashboard**
2. **Navigate to Apps → agenthub-backend**
3. **Click on "Deployment" tab**
4. **Update the captain-definition in the web editor:**

```json
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.backend.production"
}
```

5. **Save and Deploy**

### Option 2: Fix via Git Repository

If you're deploying from Git:

1. **For Backend Branch/Repo:**
   Create `captain-definition` in the root:
   ```json
   {
     "schemaVersion": 2,
     "dockerfilePath": "./docker-system/docker/Dockerfile.backend.production"
   }
   ```

2. **For Frontend Branch/Repo:**
   Create `captain-definition` in the root:
   ```json
   {
     "schemaVersion": 2,
     "dockerfilePath": "./docker-system/docker/Dockerfile.frontend.production"
   }
   ```

### Option 3: Use Separate Branches

Create two branches in your repo:
```bash
# Backend branch
git checkout -b backend-deploy
cp captain-definition-backend captain-definition
git add captain-definition
git commit -m "Add backend captain-definition"
git push origin backend-deploy

# Frontend branch  
git checkout -b frontend-deploy
cp captain-definition-frontend captain-definition
git add captain-definition
git commit -m "Add frontend captain-definition"
git push origin frontend-deploy
```

Then in CapRover:
- **agenthub-backend** → Deploy from `backend-deploy` branch
- **agenthub-frontend** → Deploy from `frontend-deploy` branch

## Quick Verification

After fixing, the backend build should show:
```
Step X: FROM python:3.11-slim
Step X: COPY agenthub_main/pyproject.toml
Step X: RUN uv sync
```

NOT:
```
Step X: FROM node:20-alpine
Step X: npm run build
Step X: FROM nginx:alpine
```

## Additional Fix Applied

Also fixed the frontend Dockerfile:
- Changed `COPY --from=builder /app/dist` to `/app/build`
- Vite outputs to `build/` directory, not `dist/`