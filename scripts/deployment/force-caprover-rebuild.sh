#!/bin/bash

# Force CapRover to rebuild frontend completely
# This script helps when CapRover is using cached Docker layers

set -e

echo "================================================"
echo "  Force CapRover Frontend Rebuild"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Add a cache-busting change to force rebuild
echo -e "${YELLOW}Step 1: Adding cache-busting timestamp to Dockerfile${NC}"
TIMESTAMP=$(date +%s)
sed -i "1s/^/# Cache bust: $TIMESTAMP\n/" docker-system/docker/Dockerfile.frontend.production

# Step 2: Commit the change
echo -e "${YELLOW}Step 2: Committing cache-busting change${NC}"
git add docker-system/docker/Dockerfile.frontend.production
git commit -m "chore: force CapRover rebuild - cache bust $TIMESTAMP"

# Step 3: Push to trigger deployment
echo -e "${YELLOW}Step 3: Pushing to trigger CapRover deployment${NC}"
git push origin main

echo ""
echo -e "${GREEN}✅ Cache-busting commit pushed!${NC}"
echo ""
echo -e "${BLUE}CapRover should now rebuild the frontend completely.${NC}"
echo -e "${BLUE}This bypasses any Docker layer caching issues.${NC}"
echo ""
echo -e "${YELLOW}What happens next:${NC}"
echo "1. CapRover pulls the new commit"
echo "2. Sees the Dockerfile has changed"
echo "3. Rebuilds from scratch (no cache)"
echo "4. Deploys the new container"
echo ""
echo -e "${YELLOW}Monitor deployment at:${NC}"
echo "https://captain.yourdomain.com/#/apps/4genthub-frontend/deployment"
echo ""
echo -e "${GREEN}After deployment completes, the frontend should use:${NC}"
echo "✅ /api/v2/tokens/ (correct)"
echo "❌ NOT /api/auth/tokens (old)"