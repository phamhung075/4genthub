#!/bin/bash

echo "=========================================="
echo "JWT SECRET UNIFICATION SCRIPT"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Backup .env file
echo "📁 Creating backup of .env file..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"
echo ""

# Extract SUPABASE_JWT_SECRET
SUPABASE_SECRET=$(grep "^SUPABASE_JWT_SECRET=" .env | cut -d'=' -f2-)

if [ -z "$SUPABASE_SECRET" ]; then
    echo "❌ Error: SUPABASE_JWT_SECRET not found in .env"
    exit 1
fi

echo "📝 Found SUPABASE_JWT_SECRET (length: ${#SUPABASE_SECRET})"
echo ""

# Update JWT_SECRET_KEY to match SUPABASE_JWT_SECRET
echo "🔧 Updating JWT_SECRET_KEY to match SUPABASE_JWT_SECRET..."

# Create a temporary file with the updated value
grep -v "^JWT_SECRET_KEY=" .env > .env.tmp
echo "JWT_SECRET_KEY=$SUPABASE_SECRET" >> .env.tmp
mv .env.tmp .env

echo "✅ JWT_SECRET_KEY updated"
echo ""

# Verify the change
echo "🔍 Verifying configuration..."
JWT_SECRET=$(grep "^JWT_SECRET_KEY=" .env | cut -d'=' -f2-)

if [ "$JWT_SECRET" = "$SUPABASE_SECRET" ]; then
    echo "✅ SUCCESS: Both secrets now match!"
    echo "   - JWT_SECRET_KEY length: ${#JWT_SECRET}"
    echo "   - SUPABASE_JWT_SECRET length: ${#SUPABASE_SECRET}"
else
    echo "❌ Error: Secrets still don't match"
    echo "   Please check .env file manually"
    exit 1
fi

echo ""
echo "🐳 Next steps:"
echo "1. Restart Docker containers to apply changes:"
echo "   docker restart dhafnck-mcp-server"
echo ""
echo "2. Verify the fix:"
echo "   python scripts/check-jwt-env.py"
echo ""
echo "✅ JWT secrets successfully unified!"