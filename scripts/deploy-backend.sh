#!/bin/bash

set -e

echo "🐳 4genthub Backend Deployment"
echo "================================"

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

print_status "Deploying backend to $ENVIRONMENT environment"

# Load environment variables
if [ -f ".env.pro" ]; then
    export $(cat .env.pro | grep -v '^#' | xargs)
    print_status "Loaded production environment variables"
else
    print_error "Production environment file (.env.pro) not found"
fi

# Validate required environment variables
REQUIRED_VARS=("CAPROVER_SERVER_URL" "CAPROVER_PASSWORD" "CAPROVER_BACKEND_APP_NAME")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
    fi
done

# Check if CapRover CLI is installed
if ! command -v caprover &> /dev/null; then
    print_warning "CapRover CLI not found. Installing..."
    npm install -g caprover
fi

# Build Docker image if not skipped
if [ "$SKIP_BUILD" != "true" ]; then
    print_status "Building backend Docker image..."
    
    if [ -f "Dockerfile.production" ]; then
        # Build with optimizations
        DOCKER_BUILDKIT=1 docker build \
            -f Dockerfile.production \
            -t $DOCKER_NAMESPACE/4genthub-backend:latest \
            -t $DOCKER_NAMESPACE/4genthub-backend:$ENVIRONMENT \
            --build-arg SERVICE=backend \
            --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
            --build-arg VCS_REF=$(git rev-parse --short HEAD) \
            .
        print_status "Backend image built successfully"
        
        # Push to registry
        docker push $DOCKER_NAMESPACE/4genthub-backend:latest
        docker push $DOCKER_NAMESPACE/4genthub-backend:$ENVIRONMENT
        print_status "Backend image pushed to registry"
    else
        print_error "Dockerfile.production not found"
    fi
fi

# Deploy to CapRover
print_status "Deploying backend to CapRover..."

# Determine app name based on environment
if [ "$ENVIRONMENT" == "staging" ]; then
    APP_NAME="${CAPROVER_BACKEND_APP_NAME}-staging"
else
    APP_NAME=$CAPROVER_BACKEND_APP_NAME
fi

print_status "Deploying to CapRover app: $APP_NAME"

caprover deploy \
    --caproverUrl $CAPROVER_SERVER_URL \
    --caproverPassword $CAPROVER_PASSWORD \
    --caproverApp $APP_NAME \
    --imageName $DOCKER_NAMESPACE/4genthub-backend:latest || {
    print_error "Backend deployment failed"
}

print_status "Backend deployment initiated"

# Wait for deployment to complete
print_status "Waiting for backend service to start..."
sleep 60

# Health checks
print_status "Running backend health checks..."

# Determine URL based on environment
if [ "$ENVIRONMENT" == "staging" ]; then
    BACKEND_URL="https://${CAPROVER_BACKEND_APP_NAME}-staging.${CAPROVER_DOMAIN:-your-domain.com}"
else
    BACKEND_URL="https://${CAPROVER_BACKEND_APP_NAME}.${CAPROVER_DOMAIN:-your-domain.com}"
fi

# Multiple health check attempts
for i in {1..5}; do
    if curl -f --max-time 30 "$BACKEND_URL/health" > /dev/null 2>&1; then
        print_status "Backend health check passed ($i/5)"
        HEALTH_CHECK_SUCCESS=true
        break
    else
        print_warning "Backend health check failed, retrying... ($i/5)"
        sleep 30
    fi
done

if [ "$HEALTH_CHECK_SUCCESS" != "true" ]; then
    print_error "Backend health check failed after 5 attempts"
fi

# Run database migrations if production
if [ "$ENVIRONMENT" == "production" ] && [ -f "scripts/migrate-database.sh" ]; then
    print_status "Running database migrations..."
    ./scripts/migrate-database.sh || print_warning "Database migrations failed"
fi

# Verify essential endpoints
print_status "Verifying backend endpoints..."

# Check additional endpoints if they exist
ENDPOINTS=("/health" "/api/health" "/metrics")
for endpoint in "${ENDPOINTS[@]}"; do
    if curl -f --max-time 10 "$BACKEND_URL$endpoint" > /dev/null 2>&1; then
        print_status "Endpoint $endpoint is accessible"
    else
        print_warning "Endpoint $endpoint is not accessible"
    fi
done

print_status "Backend deployment completed successfully!"
echo ""
echo "📋 Backend Deployment Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   App Name: $APP_NAME"
echo "   Image: $DOCKER_NAMESPACE/4genthub-backend:latest"
echo "   URL: $BACKEND_URL"
echo ""
echo "🔗 Connected Services:"
echo "   Database: srv-captain--4genthub-postgres"
echo "   Cache: srv-captain--4genthub-redis"
echo "   Auth: ${KEYCLOAK_URL:-https://keycloak.92.5.226.7.nip.io}"
echo ""
echo "🔍 Next steps:"
echo "   1. Test API endpoints: curl $BACKEND_URL/health"
echo "   2. Check logs: caprover logs --caproverApp $APP_NAME"
echo "   3. Monitor performance in CapRover dashboard"