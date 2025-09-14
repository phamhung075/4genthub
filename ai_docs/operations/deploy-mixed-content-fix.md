# Deployment Instructions for Mixed Content Fix

## Problem
The frontend at `https://webapp.92.5.226.7.nip.io` is trying to make API calls to `http://api.92.5.226.7.nip.io`, which causes a mixed content error because HTTPS pages cannot make HTTP requests.

## Solution Applied
Modified `src/config/environment.ts` to automatically upgrade HTTP API URLs to HTTPS when the page is served over HTTPS.

## Deployment Steps

### Option 1: Quick Deploy (If you have CapRover CLI installed)

```bash
# From the frontend directory
cd /home/daihungpham/__projects__/agentic-project/dhafnck-frontend

# Deploy to CapRover
caprover deploy -a webapp
```

### Option 2: Manual Deploy via CapRover Web Interface

1. **Package the build**:
```bash
cd /home/daihungpham/__projects__/agentic-project/dhafnck-frontend
tar -czf frontend-fix.tar.gz captain-definition build/ nginx.conf package.json
```

2. **Upload to CapRover**:
   - Go to https://captain.92.5.226.7.nip.io (or your CapRover URL)
   - Navigate to Apps → webapp
   - Click "Deploy via Upload"
   - Upload the `frontend-fix.tar.gz` file
   - Click "Deploy Now"

### Option 3: Git Push Deploy (If configured)

```bash
# Commit the changes
cd /home/daihungpham/__projects__/agentic-project
git add dhafnck-frontend/src/config/environment.ts
git add CHANGELOG.md
git commit -m "fix: auto-upgrade HTTP to HTTPS for API calls to prevent mixed content errors"

# Push to your deployment branch
git push origin frontend
```

## Verification Steps

After deployment:

1. Open browser console (F12)
2. Navigate to https://webapp.92.5.226.7.nip.io/tokens
3. Check for any mixed content errors
4. If `VITE_DEBUG=true`, you should see a log message: "API URL auto-upgraded from HTTP to HTTPS for mixed content security"

## Permanent Fix

For a permanent solution, update the environment variable in CapRover:

1. Go to CapRover dashboard
2. Navigate to Apps → webapp
3. Click "App Configs"
4. Add/Update environment variable:
   ```
   VITE_API_URL=https://api.92.5.226.7.nip.io
   ```
5. Click "Save & Restart"

This way, the API URL will be HTTPS from the start, and no auto-upgrade will be needed.

## Files Changed

- `dhafnck-frontend/src/config/environment.ts` - Added automatic HTTP to HTTPS upgrade logic
- `CHANGELOG.md` - Documented the fix

## Build Info

- Build completed: Sep 14 22:58
- Build directory: `dhafnck-frontend/build/`
- Fix applied to prevent mixed content errors