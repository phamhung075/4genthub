# Quick Deploy to CapRover - Runtime Environment Fix

## The Fix
Your CapRover environment variables are correctly set to HTTPS, but the current deployment uses build-time variables. The fix implements runtime injection so CapRover's environment variables are actually used.

## Quick Deploy Steps

### Option 1: Via CapRover CLI (Fastest)

```bash
# 1. Navigate to frontend directory
cd /home/daihungpham/__projects__/agentic-project/agenthub-frontend

# 2. Deploy directly to CapRover
caprover deploy -a webapp

# Enter password when prompted
```

### Option 2: Via Git Push

```bash
# 1. Commit all changes
cd /home/daihungpham/__projects__/agentic-project
git add -A
git commit -m "fix: implement runtime environment variable injection for frontend"

# 2. Push to your deployment branch
git push origin frontend

# 3. CapRover will auto-build and deploy
```

### Option 3: Manual Upload

```bash
# 1. Create deployment package
cd /home/daihungpham/__projects__/agentic-project
tar -czf frontend-deploy.tar.gz \
  captain-definition.frontend \
  agenthub-frontend/build/ \
  agenthub-frontend/package.json \
  agenthub-frontend/package-lock.json \
  agenthub-frontend/index.html \
  agenthub-frontend/public/ \
  docker-system/docker/Dockerfile.frontend.production \
  scripts/frontend-docker-entrypoint.sh

# 2. Upload via CapRover Web UI
# - Go to https://captain.92.5.226.7.nip.io
# - Navigate to Apps → webapp
# - Click "Deploy via Upload"
# - Upload frontend-deploy.tar.gz
# - Click "Deploy Now"
```

## Verify Deployment

Run the verification script:
```bash
./scripts/verify-frontend-env.sh
```

Or manually check:
1. Open: https://webapp.92.5.226.7.nip.io/env-config.js
2. Should show: `VITE_API_URL: 'https://api.92.5.226.7.nip.io'`
3. Clear browser cache (Ctrl+Shift+R)
4. Try tokens page again

## What Changed

1. **Runtime Config Injection**: Environment variables are now injected at container startup, not build time
2. **No More Hardcoding**: Uses CapRover's environment variables directly
3. **HTTPS Enforcement**: Auto-upgrades HTTP to HTTPS as additional protection

## Troubleshooting

If still seeing HTTP errors after deployment:

1. **Check Docker logs in CapRover**:
   - Should show "Runtime configuration injected"
   - Should list VITE_API_URL with HTTPS

2. **Verify env-config.js**:
   ```bash
   curl https://webapp.92.5.226.7.nip.io/env-config.js
   ```
   - Should return JavaScript with HTTPS URLs

3. **Clear ALL browser data**:
   - Open DevTools → Application → Clear Storage
   - Clear everything and hard refresh

4. **Check CapRover environment variables**:
   - Apps → webapp → App Configs
   - Verify VITE_API_URL starts with https://

## Success Indicators

✅ No mixed content errors in browser console
✅ Network tab shows all API calls using HTTPS
✅ Tokens page loads without errors
✅ env-config.js contains runtime values from CapRover