#!/bin/bash
# CapRover Pre-Deploy Script
# Automatically configures captain-definition based on app name

echo "🚀 CapRover Pre-Deploy Script Starting..."

# Get the app name from CapRover environment or command line
APP_NAME=${CAPROVER_APP_NAME:-$1}

echo "📦 Deploying to app: $APP_NAME"

# Configure captain-definition based on app name
if [[ "$APP_NAME" == *"backend"* ]]; then
    echo "🔧 Configuring for BACKEND deployment..."
    if [ -f captain-definition.backend ]; then
        cp captain-definition.backend captain-definition
        echo "✅ Backend captain-definition copied from template"
    else
        cat > captain-definition << 'EOF'
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.backend.production"
}
EOF
        echo "✅ Backend captain-definition created"
    fi
    
elif [[ "$APP_NAME" == *"frontend"* ]]; then
    echo "🎨 Configuring for FRONTEND deployment..."
    if [ -f captain-definition.frontend ]; then
        cp captain-definition.frontend captain-definition
        echo "✅ Frontend captain-definition copied from template"
    else
        cat > captain-definition << 'EOF'
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.frontend.production"
}
EOF
        echo "✅ Frontend captain-definition created"
    fi
    
else
    echo "⚠️ Warning: Unable to determine app type from name: $APP_NAME"
    echo "📝 Using existing captain-definition or backend default"
    
    # If no captain-definition exists, use backend default
    if [ ! -f captain-definition ]; then
        if [ -f captain-definition.backend ]; then
            cp captain-definition.backend captain-definition
            echo "✅ Using backend captain-definition as default"
        else
            cat > captain-definition << 'EOF'
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.backend.production"
}
EOF
            echo "✅ Default backend captain-definition created"
        fi
    fi
fi

# Display the captain-definition for verification
echo ""
echo "📄 Captain-definition content:"
cat captain-definition
echo ""
echo "✅ Pre-deploy configuration complete!"