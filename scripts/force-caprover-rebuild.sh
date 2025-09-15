#!/bin/bash

# Force CapRover to rebuild with new code
# This script ensures complete cache invalidation

echo "🚀 Forcing CapRover complete rebuild..."

# 1. Update cache bust in Dockerfile
TIMESTAMP=$(date +%s)
sed -i "1s/.*Cache bust: .*/# Cache bust: $TIMESTAMP/" docker-system/docker/Dockerfile.frontend.production

# 2. Bump version in package.json to force new build
cd dhafnck-frontend
npm version patch --no-git-tag-version
cd ..

# 3. Add cache bust to tokenService to ensure it's recompiled
echo "// Cache bust: $TIMESTAMP" >> dhafnck-frontend/src/services/tokenService.ts

# 4. Commit all changes
git add -A
git commit -m "chore: force CapRover rebuild - cache bust $TIMESTAMP

- Updated Dockerfile cache bust
- Bumped package.json version
- Added cache bust to tokenService
- Ensures /api/v2/tokens is used, not /api/auth/tokens"

# 5. Push to origin
echo "📤 Pushing to origin..."
git push origin frontend

# 6. Push to CapRover
echo "🚢 Deploying to CapRover..."
git push caprover frontend:master

echo "✅ Complete! CapRover should now rebuild with correct /api/v2/tokens endpoints"
echo ""
echo "⚠️ IMPORTANT: After deployment completes:"
echo "1. Clear your browser cache (Ctrl+Shift+R or Cmd+Shift+R)"
echo "2. Check the Network tab to verify it's calling /api/v2/tokens"
echo "3. If still seeing old endpoint, wait 2-3 minutes for CapRover to fully deploy"