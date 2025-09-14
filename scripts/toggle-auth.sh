#!/bin/bash

ACTION=${1:-status}

case $ACTION in
    disable)
        echo "🔓 Disabling authentication..."
        docker exec dhafnck-backend sh -c 'export AUTH_ENABLED=false'
        docker restart dhafnck-backend
        sleep 3
        echo "✅ Authentication disabled. You can now access projects without login."
        echo "   Go to http://localhost:3800 - you should see projects without login"
        ;;

    enable)
        echo "🔒 Enabling authentication..."
        docker exec dhafnck-backend sh -c 'export AUTH_ENABLED=true'
        docker restart dhafnck-backend
        sleep 3
        echo "✅ Authentication enabled. Login required to access projects."
        ;;

    status)
        echo "📊 Current authentication status:"
        curl -s http://localhost:8000/health | python3 -c "import sys, json; data = json.load(sys.stdin); print(f'  AUTH_ENABLED: {data.get(\"auth_enabled\", \"unknown\")}')"
        echo ""
        echo "🔍 Testing API access without token:"
        RESPONSE=$(curl -s http://localhost:8000/api/v2/projects/)
        if echo "$RESPONSE" | grep -q "Not authenticated"; then
            echo "  ✅ Authentication is ACTIVE (login required)"
        else
            echo "  🔓 Authentication is DISABLED (no login required)"
            echo "  Projects visible: $(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('projects', [])))" 2>/dev/null || echo "0")"
        fi
        ;;

    *)
        echo "Usage: $0 [disable|enable|status]"
        echo "  disable - Turn off authentication (for testing)"
        echo "  enable  - Turn on authentication (production)"
        echo "  status  - Check current auth status"
        ;;
esac