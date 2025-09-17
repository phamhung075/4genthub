#!/bin/bash

# Frontend Docker Build Script with Platform Detection
# Automatically detects and uses the correct platform for your system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔨 Building agenthub Frontend Docker Image${NC}"
echo "================================================="

# Detect system architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
    PLATFORM="linux/arm64"
    echo -e "${GREEN}✅ Detected ARM64 architecture (M1/M2 Mac)${NC}"
elif [[ "$ARCH" == "x86_64" ]]; then
    PLATFORM="linux/amd64"
    echo -e "${GREEN}✅ Detected AMD64 architecture (Intel/AMD)${NC}"
else
    echo -e "${YELLOW}⚠️  Unknown architecture: $ARCH, defaulting to linux/arm64${NC}"
    PLATFORM="linux/arm64"
fi

# Check for override in .dockerbuildrc
if [ -f "./docker-system/docker/.dockerbuildrc" ]; then
    source ./docker-system/docker/.dockerbuildrc
    if [ ! -z "$DOCKER_DEFAULT_PLATFORM" ]; then
        PLATFORM=$DOCKER_DEFAULT_PLATFORM
        echo -e "${YELLOW}📋 Using platform from .dockerbuildrc: $PLATFORM${NC}"
    fi
fi

echo -e "${BLUE}🎯 Building for platform: $PLATFORM${NC}"

# Build arguments
BUILD_ARGS=""
if [ -f ".env.pro" ]; then
    echo -e "${GREEN}📄 Loading production environment variables${NC}"
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]]; then
            BUILD_ARGS="$BUILD_ARGS --build-arg $line"
        fi
    done < .env.pro
fi

# Add platform build argument
BUILD_ARGS="$BUILD_ARGS --build-arg DOCKER_DEFAULT_PLATFORM=$PLATFORM"

# Build the Docker image
echo -e "${BLUE}🚀 Starting Docker build...${NC}"
docker build \
    --platform $PLATFORM \
    --file docker-system/docker/Dockerfile.frontend.production \
    $BUILD_ARGS \
    --tag agenthub-frontend:latest \
    --tag agenthub-frontend:$(date +%Y%m%d-%H%M%S) \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
    echo -e "${GREEN}📦 Tagged as: agenthub-frontend:latest${NC}"

    # Show image details
    echo ""
    echo -e "${BLUE}📊 Image Details:${NC}"
    docker images agenthub-frontend:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Build complete! Platform: $PLATFORM${NC}"
echo -e "${YELLOW}💡 To run the container:${NC}"
echo "   docker run -p 3800:3800 --env-file .env.pro agenthub-frontend:latest"