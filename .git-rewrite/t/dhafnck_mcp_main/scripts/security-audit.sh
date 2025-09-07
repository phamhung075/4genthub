#!/bin/bash

# Security Audit Script for DhafnckMCP
# This script checks for exposed credentials and security issues

echo "🔐 DhafnckMCP Security Audit"
echo "============================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_ROOT")"

echo "📍 Project Root: $ROOT_DIR"
echo ""

# Function to check for exposed credentials
check_credentials() {
    local pattern=$1
    local description=$2
    
    echo -n "Checking for $description... "
    
    # Search for pattern, excluding .git and node_modules
    result=$(grep -r "$pattern" "$ROOT_DIR" \
        --exclude-dir=.git \
        --exclude-dir=node_modules \
        --exclude-dir=.venv \
        --exclude-dir=__pycache__ \
        --exclude="*.pyc" \
        --exclude="security-audit.sh" \
        2>/dev/null | head -5)
    
    if [ -z "$result" ]; then
        echo -e "${GREEN}✓ Clean${NC}"
    else
        echo -e "${RED}✗ Found exposed credentials!${NC}"
        echo "$result" | head -5
        echo ""
        return 1
    fi
}

# Function to check .env file configuration
check_env_files() {
    echo "🔍 Checking .env file configuration..."
    echo ""
    
    # Check for root .env
    if [ -f "$ROOT_DIR/.env" ]; then
        echo -e "${GREEN}✓${NC} Root .env exists at $ROOT_DIR/.env"
    else
        echo -e "${YELLOW}⚠${NC} Root .env missing - create from .env.example"
    fi
    
    # Check for duplicate .env files
    echo ""
    echo "Checking for duplicate .env files..."
    env_files=$(find "$ROOT_DIR" -name ".env" -type f 2>/dev/null | grep -v node_modules | grep -v .venv)
    env_count=$(echo "$env_files" | wc -l)
    
    if [ "$env_count" -eq 1 ]; then
        echo -e "${GREEN}✓${NC} Single .env file found (good)"
    else
        echo -e "${YELLOW}⚠${NC} Multiple .env files detected:"
        echo "$env_files"
        echo "Consolidate to single root .env file"
    fi
    
    echo ""
}

# Function to check .gitignore
check_gitignore() {
    echo "🔍 Checking .gitignore configuration..."
    
    if grep -q "^\.env$" "$ROOT_DIR/.gitignore" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} .env is in .gitignore"
    else
        echo -e "${RED}✗${NC} .env is NOT in .gitignore - add it immediately!"
    fi
    
    echo ""
}

# Main audit
echo "============================"
echo "🔍 CREDENTIAL EXPOSURE CHECK"
echo "============================"
echo ""

failed=0

# Check for various credential patterns
check_credentials "github_pat_[A-Za-z0-9_]{40,}" "GitHub Personal Access Tokens" || failed=1
check_credentials "ghp_[A-Za-z0-9_]{36,}" "GitHub Personal Access Tokens (new format)" || failed=1
check_credentials "sk-[A-Za-z0-9]{48}" "OpenAI API Keys" || failed=1
check_credentials "sk-ant-[A-Za-z0-9-]{40,}" "Anthropic API Keys" || failed=1
check_credentials "sbp_[a-f0-9]{40}" "Supabase Access Tokens" || failed=1
check_credentials "eyJhbGciOiJIUzI1NiIs[A-Za-z0-9+/=]*" "JWT Tokens" || failed=1
check_credentials "postgres://[^:]+:[^@]+@" "Database URLs with passwords" || failed=1
check_credentials "postgresql://[^:]+:[^@]+@" "PostgreSQL URLs with passwords" || failed=1

echo ""
echo "============================"
echo "📁 ENVIRONMENT FILE CHECK"
echo "============================"
echo ""

check_env_files
check_gitignore

echo "============================"
echo "📊 AUDIT SUMMARY"
echo "============================"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ Security audit PASSED - No exposed credentials found${NC}"
else
    echo -e "${RED}❌ Security audit FAILED - Exposed credentials detected!${NC}"
    echo ""
    echo "IMMEDIATE ACTIONS REQUIRED:"
    echo "1. Revoke all exposed credentials"
    echo "2. Remove credentials from code"
    echo "3. Use environment variables from root .env"
    echo "4. Never commit .env to version control"
    exit 1
fi

echo ""
echo "============================"
echo "📝 RECOMMENDATIONS"
echo "============================"
echo ""
echo "1. Use single .env file at project root"
echo "2. Never commit .env to git (ensure in .gitignore)"
echo "3. Use .env.example as template"
echo "4. Rotate credentials regularly"
echo "5. Use secret management tools in production"
echo ""
echo "Security audit complete."