#!/bin/bash

# Test API with a provided JWT token
# Usage: ./test-with-token.sh <token>

TOKEN=$1

if [ -z "$TOKEN" ]; then
    echo "❌ Token required!"
    echo "Usage: $0 <jwt-token>"
    echo ""
    echo "Steps to get your token:"
    echo "1. Login at http://localhost:3800"
    echo "2. Open browser Developer Tools (F12)"
    echo "3. Go to Application/Storage → Local Storage"
    echo "4. Find and copy the 'access_token' value"
    echo "5. Run: $0 <your-token>"
    exit 1
fi

echo "🔍 Decoding token to check user info..."
# Decode the JWT payload (second part)
PAYLOAD=$(echo "$TOKEN" | cut -d. -f2)
# Add padding if needed
PAYLOAD_PADDED=$(printf '%s' "$PAYLOAD" | sed 's/_/\//g; s/-/+/g')
case $(( ${#PAYLOAD_PADDED} % 4 )) in
    2) PAYLOAD_PADDED="${PAYLOAD_PADDED}==" ;;
    3) PAYLOAD_PADDED="${PAYLOAD_PADDED}=" ;;
esac

# Decode and show user info
echo "Token payload:"
echo "$PAYLOAD_PADDED" | base64 -d 2>/dev/null | python3 -m json.tool | grep -E "sub|email|preferred_username|name" || echo "Could not decode token"

echo ""
echo "📊 Testing API with your token..."

# Test projects endpoint
echo "1. Fetching projects:"
curl -s -X GET \
  "http://localhost:8000/api/v2/projects/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo "2. Checking current user:"
curl -s -X GET \
  "http://localhost:8000/api/v2/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo "📝 Database check:"
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp -c "SELECT 'Project user_id:' as info, user_id FROM projects LIMIT 1;"

echo ""
echo "If no projects shown but token is valid, the user_id in token doesn't match the project's user_id in database."