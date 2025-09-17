#!/bin/sh
set -e

echo "Starting 4genthub Frontend with runtime configuration..."
echo "================================================"

# Create env-config.js with actual environment variables
cat > /usr/share/nginx/html/env-config.js <<EOF
// Runtime configuration - injected at container startup
window._env_ = {
  VITE_API_URL: '${VITE_API_URL:-http://localhost:8000}',
  VITE_BACKEND_URL: '${VITE_BACKEND_URL:-${VITE_API_URL:-http://localhost:8000}}',
  VITE_KEYCLOAK_URL: '${VITE_KEYCLOAK_URL:-}',
  VITE_KEYCLOAK_REALM: '${VITE_KEYCLOAK_REALM:-}',
  VITE_KEYCLOAK_CLIENT_ID: '${VITE_KEYCLOAK_CLIENT_ID:-}',
  VITE_ENV: '${VITE_ENV:-production}',
  VITE_DEBUG: '${VITE_DEBUG:-false}',
  VITE_APP_NAME: '${VITE_APP_NAME:-4genthub}'
};
EOF

echo "Runtime configuration injected:"
echo "  VITE_API_URL: ${VITE_API_URL:-not set}"
echo "  VITE_BACKEND_URL: ${VITE_BACKEND_URL:-not set}"
echo "  VITE_KEYCLOAK_URL: ${VITE_KEYCLOAK_URL:-not set}"
echo "  VITE_ENV: ${VITE_ENV:-production}"
echo "================================================"

# Start nginx
exec nginx -g 'daemon off;'