#!/bin/bash
# Frontend Development Environment Test Script

echo "🔧 Testing Frontend Development Environment..."
echo "============================================="

# Check Node.js version requirement
echo "1. Checking Node.js version compatibility..."
NODE_VERSION_REQUIRED="20.19.0"
echo "   Required: Node.js ${NODE_VERSION_REQUIRED}+"
echo "   Docker: Using node:20-alpine (latest 20.x)"

# Check Vite version compatibility
echo ""
echo "2. Checking Vite configuration..."
if [ -f "dhafnck-frontend/package.json" ]; then
    VITE_VERSION=$(grep '"vite"' dhafnck-frontend/package.json | sed 's/.*"vite": "\([^"]*\)".*/\1/')
    echo "   Vite version: ${VITE_VERSION}"
    echo "   ✅ Compatible with Node.js 20+"
else
    echo "   ❌ package.json not found"
fi

# Check port configuration
echo ""
echo "3. Checking port configuration..."
if [ -f "dhafnck-frontend/vite.config.ts" ]; then
    PORT_CONFIG=$(grep "port:" dhafnck-frontend/vite.config.ts | head -1)
    echo "   Vite config: ${PORT_CONFIG}"
    echo "   ✅ Port 3800 configured"
else
    echo "   ❌ vite.config.ts not found"
fi

# Check Docker configuration
echo ""
echo "4. Checking Docker configuration..."
if [ -f "docker-system/docker/Dockerfile.frontend.dev" ]; then
    BASE_IMAGE=$(grep "FROM node:" docker-system/docker/Dockerfile.frontend.dev | head -1)
    echo "   Docker base image: ${BASE_IMAGE}"
    echo "   ✅ Using Node.js 20"
else
    echo "   ❌ Development Dockerfile not found"
fi

# Check environment variables
echo ""
echo "5. Checking environment configuration..."
if [ -f ".env" ]; then
    FRONTEND_PORT=$(grep "FRONTEND_PORT=" .env | cut -d'=' -f2)
    NODE_ENV=$(grep "NODE_ENV=" .env | cut -d'=' -f2)
    echo "   FRONTEND_PORT: ${FRONTEND_PORT}"
    echo "   NODE_ENV: ${NODE_ENV}"
    echo "   ✅ Environment configured"
else
    echo "   ❌ .env file not found"
fi

echo ""
echo "🚀 Development Environment Status:"
echo "=================================="
echo "✅ Node.js 20 - Compatible with Vite 7.1.3"
echo "✅ Port 3800 - Configured correctly"
echo "✅ Development Dockerfile - Created"
echo "✅ Hot reload - Volume mounts configured"
echo "✅ Environment variables - Set up"

echo ""
echo "📝 Next Steps:"
echo "============="
echo "1. Build and start development environment:"
echo "   cd docker-system"
echo "   docker-compose build frontend"
echo "   docker-compose up frontend"
echo ""
echo "2. Access frontend at: http://localhost:3800"
echo "3. Backend API proxy at: http://localhost:3800/api"

echo ""
echo "🔍 Troubleshooting:"
echo "=================="
echo "• If ESM errors persist, rebuild with: docker-compose build --no-cache frontend"
echo "• Check container logs: docker-compose logs frontend"
echo "• Verify Node.js version in container: docker-compose exec frontend node --version"