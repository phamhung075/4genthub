#!/bin/bash

set -e

echo "🎨 agenthub Frontend Deployment"
echo "================================="

# Configuration
ENVIRONMENT=${1:-"production"}
SKIP_BUILD=${2:-"false"}
DOCKER_NAMESPACE=${3:-"your_dockerhub_username"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Validate environment
if [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "staging" ]; then
    print_error "Environment must be 'production' or 'staging'"
fi

print_status "Deploying frontend to $ENVIRONMENT environment"

# Load environment variables
if [ -f ".env.pro" ]; then
    export $(cat .env.pro | grep -v '^#' | xargs)
    print_status "Loaded production environment variables"
else
    print_error "Production environment file (.env.pro) not found"
fi

# Validate required environment variables
REQUIRED_VARS=("CAPROVER_SERVER_URL" "CAPROVER_PASSWORD" "CAPROVER_FRONTEND_APP_NAME")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
    fi
done

# Check if frontend directory exists
if [ ! -d "agenthub-frontend" ]; then
    print_error "Frontend directory 'agenthub-frontend' not found"
fi

# Check if CapRover CLI is installed
if ! command -v caprover &> /dev/null; then
    print_warning "CapRover CLI not found. Installing..."
    npm install -g caprover
fi

# Build Docker image if not skipped
if [ "$SKIP_BUILD" != "true" ]; then
    print_status "Building frontend Docker image..."

    cd agenthub-frontend

    # Determine backend URL based on environment
    if [ "$ENVIRONMENT" == "staging" ]; then
        BACKEND_URL="https://${CAPROVER_BACKEND_APP_NAME:-agenthub-backend}-staging.${CAPROVER_DOMAIN:-your-domain.com}"
    else
        BACKEND_URL="https://${CAPROVER_BACKEND_APP_NAME:-agenthub-backend}.${CAPROVER_DOMAIN:-your-domain.com}"
    fi

    # Create production environment file
    cat > .env.production << EOF
VITE_API_URL=$BACKEND_URL
VITE_KEYCLOAK_URL=${KEYCLOAK_URL:-https://keycloak.92.5.226.7.nip.io}
VITE_KEYCLOAK_REALM=${KEYCLOAK_REALM:-mcp}
VITE_KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID:-mcp-backend}
NODE_ENV=production
VITE_BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VITE_BUILD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VITE_ENV=$ENVIRONMENT
EOF

    print_status "Created frontend environment configuration"

    if [ -f "Dockerfile.production" ]; then
        # Build with optimizations
        DOCKER_BUILDKIT=1 docker build \
            -f Dockerfile.production \
            -t $DOCKER_NAMESPACE/agenthub-frontend:latest \
            -t $DOCKER_NAMESPACE/agenthub-frontend:$ENVIRONMENT \
            --build-arg SERVICE=frontend \
            --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
            --build-arg VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
            .
        print_status "Frontend image built successfully"

        # Push to registry
        docker push $DOCKER_NAMESPACE/agenthub-frontend:latest
        docker push $DOCKER_NAMESPACE/agenthub-frontend:$ENVIRONMENT
        print_status "Frontend image pushed to registry"
    else
        print_error "Dockerfile.production not found in agenthub-frontend directory"
    fi

    cd ..
fi

# Deploy to CapRover
print_status "Deploying frontend to CapRover..."

# Determine app name based on environment
if [ "$ENVIRONMENT" == "staging" ]; then
    APP_NAME="${CAPROVER_FRONTEND_APP_NAME}-staging"
else
    APP_NAME=$CAPROVER_FRONTEND_APP_NAME
fi

print_status "Deploying to CapRover app: $APP_NAME"

caprover deploy \
    --caproverUrl $CAPROVER_SERVER_URL \
    --caproverPassword $CAPROVER_PASSWORD \
    --caproverApp $APP_NAME \
    --imageName $DOCKER_NAMESPACE/agenthub-frontend:latest || {
    print_error "Frontend deployment failed"
}

print_status "Frontend deployment initiated"

# Wait for deployment to complete
print_status "Waiting for frontend service to start..."
sleep 45

# Health checks
print_status "Running frontend health checks..."

# Determine URL based on environment
if [ "$ENVIRONMENT" == "staging" ]; then
    FRONTEND_URL="https://${CAPROVER_FRONTEND_APP_NAME}-staging.${CAPROVER_DOMAIN:-your-domain.com}"
else
    FRONTEND_URL="https://${CAPROVER_FRONTEND_APP_NAME}.${CAPROVER_DOMAIN:-your-domain.com}"
fi

# Multiple health check attempts
HEALTH_CHECK_SUCCESS=false
for i in {1..5}; do
    if curl -f --max-time 30 "$FRONTEND_URL" > /dev/null 2>&1; then
        print_status "Frontend health check passed ($i/5)"
        HEALTH_CHECK_SUCCESS=true
        break
    else
        print_warning "Frontend health check failed, retrying... ($i/5)"
        sleep 20
    fi
done

if [ "$HEALTH_CHECK_SUCCESS" != "true" ]; then
    print_error "Frontend health check failed after 5 attempts"
fi

# Check static assets
print_status "Verifying frontend assets..."

# Check common static files
STATIC_PATHS=("" "/favicon.ico" "/assets" "/health")
for path in "${STATIC_PATHS[@]}"; do
    if curl -f --max-time 10 "$FRONTEND_URL$path" > /dev/null 2>&1; then
        print_status "Static path '$path' is accessible"
    else
        print_warning "Static path '$path' is not accessible"
    fi
done

# Verify the LIVE build, not merely that a path answers.
#
# WHY THIS EXISTS: every check above asks whether a URL ANSWERS, and none asks WHICH BUILD is
# answering. On 2026-10-10 that is how this script printed "Frontend deployment completed
# successfully!" against a frontend built two days and 165 commits earlier - the composer work
# missing and the deleted scripts/openrig_*.py names still on screen - while the deploy looked
# green. A reachable page proves a server, not a deploy.
print_status "Verifying the live frontend IS the build just made..."

if ! command -v python3 > /dev/null 2>&1; then
    print_error "python3 is required to verify which build is live"
fi

CENSUS="scripts/check_served_frontend.py"
if [ ! -f "$CENSUS" ]; then
    print_error "the census script is missing ($CENSUS) - cannot tell which build is live"
fi

if [ -f "agenthub-frontend/build/index.html" ]; then
    # Identity, not reachability: the served entry chunk must be THIS build's entry chunk, and every
    # script the served app is composed of must exist in it. This is the assertion a stale live
    # bundle cannot pass.
    if python3 "$CENSUS" --base-url "$FRONTEND_URL" --expect-dist agenthub-frontend/build; then
        print_status "The live frontend IS the build just made"
    else
        print_error "the LIVE frontend is NOT the build just made - a stale or mismatched bundle is being served (census above; row b70278f2)"
    fi
else
    # SKIP_BUILD leaves nothing to compare against, so identity cannot be checked. The census alone
    # still refuses a pre-fix bundle - that is the failure that mattered - but it is the weaker test,
    # so it is named as such rather than passed off as the same thing.
    print_warning "agenthub-frontend/build/index.html is absent, so identity cannot be checked; falling back to the census"
    python3 "$CENSUS" --base-url "$FRONTEND_URL" || print_error "the live frontend is not a build of HEAD - a stale bundle is being served (row b70278f2)"
fi

# Verify backend connectivity from frontend
print_status "Testing frontend-backend connectivity..."
# This is a basic connectivity test - in reality you'd test actual API calls
if [ "$ENVIRONMENT" == "staging" ]; then
    TEST_BACKEND_URL="https://${CAPROVER_BACKEND_APP_NAME:-agenthub-backend}-staging.${CAPROVER_DOMAIN:-your-domain.com}"
else
    TEST_BACKEND_URL="https://${CAPROVER_BACKEND_APP_NAME:-agenthub-backend}.${CAPROVER_DOMAIN:-your-domain.com}"
fi

if curl -f --max-time 10 "$TEST_BACKEND_URL/health" > /dev/null 2>&1; then
    print_status "Frontend can reach backend API"
else
    print_warning "Frontend cannot reach backend API - check configuration"
fi

# Performance check for production
if [ "$ENVIRONMENT" == "production" ]; then
    print_status "Running production performance check..."

    # Measure response time
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' "$FRONTEND_URL")
    echo "Frontend response time: ${RESPONSE_TIME}s"

    # Check if response time is acceptable (< 3 seconds)
    if (( $(echo "$RESPONSE_TIME > 3.0" | bc -l) )); then
        print_warning "Frontend response time exceeds 3s threshold"
    else
        print_status "Frontend response time is acceptable"
    fi
fi

print_status "Frontend deployment completed successfully!"
echo ""
echo "📋 Frontend Deployment Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   App Name: $APP_NAME"
echo "   Image: $DOCKER_NAMESPACE/agenthub-frontend:latest"
echo "   URL: $FRONTEND_URL"
echo ""
echo "🔗 Connected Services:"
echo "   Backend: ${TEST_BACKEND_URL}"
echo "   Auth: ${KEYCLOAK_URL:-https://keycloak.92.5.226.7.nip.io}"
echo ""
echo "🔍 Next steps:"
echo "   1. Test the application: open $FRONTEND_URL"
echo "   2. Check logs: caprover logs --caproverApp $APP_NAME"
echo "   3. Monitor performance in CapRover dashboard"
echo "   4. Test user authentication flow"
