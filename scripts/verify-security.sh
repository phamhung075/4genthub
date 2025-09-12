#!/bin/bash

# Security Verification Script
# Ensures no secrets are exposed in the repository

echo "🔒 Security Verification Check"
echo "=============================="

# Check if sensitive files are ignored
echo ""
echo "1. Checking git ignore status..."
if git check-ignore .mcp.json .cursor/mcp.json > /dev/null 2>&1; then
    echo "✅ MCP configuration files are properly ignored"
else
    echo "❌ WARNING: MCP configuration files are not ignored!"
fi

# Check for hardcoded secrets in tracked files
echo ""
echo "2. Scanning for potential secrets in tracked files..."
SECRET_PATTERNS=(
    "sk-[a-zA-Z0-9]{48}"
    "AIza[0-9A-Za-z_-]{35}"
    "ghp_[0-9a-zA-Z]{36}"
    "ghs_[0-9a-zA-Z]{36}"
    "Bearer [A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"
)

FOUND_SECRETS=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    if git ls-files | xargs grep -E "$pattern" 2>/dev/null | grep -v "verify-security.sh"; then
        echo "❌ Found potential secrets matching pattern: $pattern"
        FOUND_SECRETS=1
    fi
done

if [ $FOUND_SECRETS -eq 0 ]; then
    echo "✅ No hardcoded secrets found in tracked files"
fi

# Check if environment variables are used
echo ""
echo "3. Checking for environment variable usage..."
if grep -q "\${MCP_AUTH_TOKEN}" .mcp.json 2>/dev/null && \
   grep -q "\${ELEVENLABS_API_KEY}" .mcp.json 2>/dev/null; then
    echo "✅ Configuration files use environment variables"
else
    echo "⚠️  Configuration files should use environment variables"
fi

# Check if .env file exists but is not tracked
echo ""
echo "4. Checking .env file status..."
if [ -f .env ]; then
    if git ls-files --error-unmatch .env > /dev/null 2>&1; then
        echo "❌ CRITICAL: .env file is tracked in git!"
    else
        echo "✅ .env file exists but is not tracked"
    fi
else
    echo "ℹ️  No .env file found (create one for local development)"
fi

# Summary
echo ""
echo "=============================="
echo "Security Check Complete"
echo ""
echo "Remember to:"
echo "1. Never commit .env files"
echo "2. Always use environment variables for secrets"
echo "3. Rotate any exposed credentials immediately"
echo "4. Run this check before pushing to remote"