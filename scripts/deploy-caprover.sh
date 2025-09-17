#!/bin/bash

set -e

echo "🚀 4genthub CapRover Deployment"
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

print_status "Deploying to $ENVIRONMENT environment"

# Load environment variables
if [ -f ".env.pro" ]; then
    export $(cat .env.pro | grep -v '^#' | xargs)
    print_status "Loaded production environment variables"
else
    print_error "Production environment file (.env.pro) not found"
fi

# Validate required environment variables
REQUIRED_VARS=("CAPROVER_SERVER_URL" "CAPROVER_PASSWORD" "CAPROVER_BACKEND_APP_NAME" "CAPROVER_FRONTEND_APP_NAME")
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

# Build Docker images if not skipped
if [ "$SKIP_BUILD" != "true" ]; then
    print_status "Building Docker images..."
    
    # Build backend
    if [ -f "Dockerfile.production" ]; then
        docker build -f Dockerfile.production -t $DOCKER_NAMESPACE/4genthub-backend:latest .
        print_status "Backend image built"
    else
        print_warning "Dockerfile.production not found, skipping backend build"
    fi
    
    # Build frontend
    if [ -f "4genthub-frontend/Dockerfile.production" ]; then
        cd 4genthub-frontend
        docker build -f Dockerfile.production -t $DOCKER_NAMESPACE/4genthub-frontend:latest .
        cd ..
        print_status "Frontend image built"
    else
        print_warning "Frontend Dockerfile.production not found, skipping frontend build"
    fi
    
    # Push images to registry
    if docker push $DOCKER_NAMESPACE/4genthub-backend:latest 2>/dev/null; then
        print_status "Backend image pushed to registry"
    else
        print_warning "Failed to push backend image"
    fi
    
    if docker push $DOCKER_NAMESPACE/4genthub-frontend:latest 2>/dev/null; then
        print_status "Frontend image pushed to registry"
    else
        print_warning "Failed to push frontend image"
    fi
fi

# Deploy to CapRover
print_status "Deploying to CapRover..."

# Deploy backend
print_status "Deploying backend..."
caprover deploy \
    --caproverUrl $CAPROVER_SERVER_URL \
    --caproverPassword $CAPROVER_PASSWORD \
    --caproverApp $CAPROVER_BACKEND_APP_NAME \
    --imageName $DOCKER_NAMESPACE/4genthub-backend:latest || print_warning "Backend deployment failed"

print_status "Backend deployment initiated"

# Deploy frontend
print_status "Deploying frontend..."
caprover deploy \
    --caproverUrl $CAPROVER_SERVER_URL \
    --caproverPassword $CAPROVER_PASSWORD \
    --caproverApp $CAPROVER_FRONTEND_APP_NAME \
    --imageName $DOCKER_NAMESPACE/4genthub-frontend:latest || print_warning "Frontend deployment failed"

print_status "Frontend deployment initiated"

# Wait for deployments to complete
print_status "Waiting for services to be ready..."
sleep 60

# Health checks
print_status "Running health checks..."

if [ -n "$BACKEND_URL" ]; then
    if curl -f $BACKEND_URL/health > /dev/null 2>&1; then
        print_status "Backend health check passed"
    else
        print_warning "Backend health check failed - check logs with: caprover logs --caproverApp $CAPROVER_BACKEND_APP_NAME"
    fi
else
    print_warning "BACKEND_URL not set, skipping backend health check"
fi

if [ -n "$FRONTEND_URL" ]; then
    if curl -f $FRONTEND_URL/health > /dev/null 2>&1; then
        print_status "Frontend health check passed"
    else
        print_warning "Frontend health check failed - check logs with: caprover logs --caproverApp $CAPROVER_FRONTEND_APP_NAME"
    fi
else
    print_warning "FRONTEND_URL not set, skipping frontend health check"
fi

# Run database migrations (if needed)
if [ -f "scripts/migrate-database.sh" ]; then
    print_status "Running database migrations..."
    ./scripts/migrate-database.sh || print_warning "Database migrations failed"
fi

print_status "Deployment completed!"
echo ""
echo "🌐 Application URLs:"
echo "   Frontend: ${FRONTEND_URL:-'Not configured'}"
echo "   Backend:  ${BACKEND_URL:-'Not configured'}"
echo "   Keycloak: ${KEYCLOAK_URL:-'Not configured'}"
echo ""
echo "🔍 Next steps:"
echo "   1. Test the application functionality"
echo "   2. Monitor logs: caprover logs --caproverApp [app-name]"
echo "   3. Set up monitoring and alerts"
echo "   4. Configure backup schedules"