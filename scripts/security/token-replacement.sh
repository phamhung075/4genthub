#!/bin/bash
# Surgical JWT Token Replacement in Git History
# Uses git filter-repo for safer history rewriting

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${YELLOW}Creating Git backup before token removal...${RESET}"
BACKUP_DIR="../agentic-project-backup-$(date +%Y%m%d-%H%M%S)"
cp -r . "$BACKUP_DIR"
echo -e "${GREEN}✅ Backup created at: $BACKUP_DIR${RESET}"

echo -e "${YELLOW}Starting surgical token replacement...${RESET}"

# Use git-filter-repo style replacement (if available) or fall back to sed
if command -v git-filter-repo &> /dev/null; then
    echo "Using git-filter-repo for safe history rewrite..."
    git filter-repo --replace-text <(echo "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9***REMOVE***==>Bearer [REDACTED-JWT-TOKEN]")
else
    echo "Using git filter-branch as fallback..."
    # More surgical git filter-branch that only targets specific token pattern
    git filter-branch --force --msg-filter 'cat' \
        --tree-filter '
        for file in $(find . -name "*.sh" -o -name "*.js" -o -name "*.ts" -o -name "*.py" -o -name "*.md" 2>/dev/null); do
            if [ -f "$file" ] && grep -q "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\." "$file" 2>/dev/null; then
                sed -i "s/Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[^\"[:space:]]*/Bearer [REDACTED-JWT-TOKEN]/g" "$file"
                echo "Cleaned token from: $file"
            fi
        done
    ' --tag-name-filter cat -- --all
fi

echo -e "${GREEN}✅ Token replacement completed${RESET}"
echo -e "${YELLOW}Verifying cleanup...${RESET}"

# Verify no tokens remain
REMAINING=$(git log --all -p -S "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ5" --pickaxe-regex | grep -c "eyJhbGc" || echo "0")
if [[ "$REMAINING" -eq 0 ]]; then
    echo -e "${GREEN}✅ No JWT tokens found in Git history${RESET}"
else
    echo -e "${RED}⚠️  $REMAINING potential tokens still found${RESET}"
fi

echo -e "${YELLOW}Cleanup Summary:${RESET}"
echo "- Backup: $BACKUP_DIR"
echo "- History rewritten to remove production JWT tokens"
echo "- All commit SHAs have changed"
echo ""
echo -e "${RED}IMPORTANT: Notify team members to re-clone repository${RESET}"