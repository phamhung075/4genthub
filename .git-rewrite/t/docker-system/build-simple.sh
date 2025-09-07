#!/bin/bash
# Simple Docker Build - No Cache, No Registry Issues

echo "🚀 Starting simple Docker build (no cache complications)..."

# Use legacy builder to avoid buildx issues
export DOCKER_BUILDKIT=0

# Build backend without any cache
docker-compose build --no-cache --force-rm backend

echo "✅ Simple build completed!"
echo "💡 If you still have issues, try: docker system prune -a"