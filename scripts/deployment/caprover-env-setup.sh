#!/bin/bash

# CapRover Environment Configuration Script
# Sets up environment variables for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CapRover Environment Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if CapRover CLI is installed
if ! command -v caprover &> /dev/null; then
    echo -e "${YELLOW}⚠️  CapRover CLI not found. Installing...${NC}"
    npm install -g caprover
fi

# Function to prompt for input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local value

    read -p "$prompt [$default]: " value
    echo "${value:-$default}"
}

# Collect configuration
echo -e "${GREEN}Please provide your configuration:${NC}"
echo ""

CAPROVER_URL=$(prompt_with_default "CapRover URL" "https://captain.yourdomain.com")
CAPROVER_PASSWORD=$(prompt_with_default "CapRover Password" "")
FRONTEND_APP_NAME=$(prompt_with_default "Frontend App Name" "agenthub-frontend")
BACKEND_APP_NAME=$(prompt_with_default "Backend App Name" "agenthub-backend")
API_URL=$(prompt_with_default "Backend API URL" "https://api.92.5.226.7.nip.io")

# Validate inputs
if [ -z "$CAPROVER_PASSWORD" ]; then
    echo -e "${RED}❌ CapRover password is required${NC}"
    exit 1
fi

# Display configuration
echo ""
echo -e "${BLUE}Configuration Summary:${NC}"
echo "  CapRover URL: $CAPROVER_URL"
echo "  Frontend App: $FRONTEND_APP_NAME"
echo "  Backend App: $BACKEND_APP_NAME"
echo "  API URL: $API_URL"
echo ""

read -p "Continue with this configuration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Configuration cancelled${NC}"
    exit 0
fi

# Login to CapRover
echo ""
echo -e "${GREEN}Logging into CapRover...${NC}"
caprover login --caproverUrl "$CAPROVER_URL" --caproverPassword "$CAPROVER_PASSWORD"

# Configure Frontend Environment Variables
echo ""
echo -e "${GREEN}Configuring Frontend Environment Variables...${NC}"

# Create environment variables JSON
cat > /tmp/caprover-frontend-env.json <<EOF
{
  "appName": "$FRONTEND_APP_NAME",
  "envVars": [
    {
      "key": "VITE_API_URL",
      "value": "$API_URL"
    },
    {
      "key": "VITE_ENV",
      "value": "production"
    },
    {
      "key": "VITE_DEBUG",
      "value": "false"
    },
    {
      "key": "VITE_APP_NAME",
      "value": "agenthub"
    }
  ]
}
EOF

echo -e "${YELLOW}Frontend environment variables to be set:${NC}"
echo "  VITE_API_URL=$API_URL"
echo "  VITE_ENV=production"
echo "  VITE_DEBUG=false"
echo "  VITE_APP_NAME=agenthub"

# Note: CapRover CLI doesn't have direct env var commands,
# so we provide instructions for manual setup
echo ""
echo -e "${BLUE}Manual Configuration Required:${NC}"
echo ""
echo "Please follow these steps in your CapRover dashboard:"
echo ""
echo "1. Navigate to: $CAPROVER_URL"
echo "2. Login with your credentials"
echo "3. Go to Apps -> $FRONTEND_APP_NAME"
echo "4. Click on 'App Configs' tab"
echo "5. Scroll to 'Environmental Variables' section"
echo "6. Add the following variables:"
echo ""
echo "   VITE_API_URL = $API_URL"
echo "   VITE_ENV = production"
echo "   VITE_DEBUG = false"
echo "   VITE_APP_NAME = agenthub"
echo ""
echo "7. Click 'Save & Update'"
echo "8. Wait for the app to rebuild and redeploy"
echo ""

# Configure Backend Environment Variables (if needed)
echo -e "${BLUE}Backend Configuration:${NC}"
echo ""
echo "For the backend app ($BACKEND_APP_NAME), ensure these variables are set:"
echo ""
echo "   PORT = 8000"
echo "   FASTMCP_PORT = 8000"
echo "   CORS_ORIGINS = *"
echo "   ALLOWED_HOSTS = api.92.5.226.7.nip.io,localhost"
echo "   DATABASE_URL = <your-database-url>"
echo "   JWT_SECRET_KEY = <your-jwt-secret>"
echo "   KEYCLOAK_URL = <your-keycloak-url>"
echo ""

# Create a configuration file for reference
CONFIG_FILE="./caprover-env-config.txt"
cat > "$CONFIG_FILE" <<EOF
# CapRover Environment Configuration
# Generated: $(date)

## Frontend ($FRONTEND_APP_NAME)
VITE_API_URL=$API_URL
VITE_ENV=production
VITE_DEBUG=false
VITE_APP_NAME=agenthub

## Backend ($BACKEND_APP_NAME)
PORT=8000
FASTMCP_PORT=8000
CORS_ORIGINS=*
ALLOWED_HOSTS=api.92.5.226.7.nip.io,localhost
# Add your database and auth configuration

## API Endpoints
Frontend URL: https://$FRONTEND_APP_NAME.$CAPROVER_URL
Backend URL: $API_URL

## Verification
1. Check frontend console for API URL: console.log(import.meta.env.VITE_API_URL)
2. Verify API calls in Network tab point to: $API_URL
3. Test token generation: POST $API_URL/api/v2/tokens
EOF

echo -e "${GREEN}✅ Configuration saved to: $CONFIG_FILE${NC}"
echo ""
echo -e "${GREEN}✅ Environment setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Complete manual configuration in CapRover dashboard"
echo "2. Deploy your applications using:"
echo "   ./deploy-frontend.sh"
echo "   ./deploy-backend.sh"
echo "3. Verify the deployment by accessing your frontend URL"
echo ""