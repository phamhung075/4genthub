#!/bin/bash
# Git History Token Cleanup Script
# WARNING: This rewrites Git history - use with extreme caution

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RESET='\033[0m'

echo -e "${RED}⚠️  DANGER: GIT HISTORY REWRITE OPERATION ⚠️${RESET}"
echo -e "${YELLOW}This will permanently rewrite Git history to remove exposed JWT tokens${RESET}"
echo -e "${YELLOW}All commit SHAs will change - collaborators will need to reset their repos${RESET}"
echo ""

# Create backup
BACKUP_DIR="../git-backup-$(date +%Y%m%d-%H%M%S)"
echo -e "${BLUE}Creating backup at: $BACKUP_DIR${RESET}"
git clone --mirror . "$BACKUP_DIR"

echo -e "${YELLOW}Starting Git filter-branch operation to remove JWT tokens...${RESET}"

# Use git filter-branch with a more targeted approach
git filter-branch --force --tree-filter '
    find . -type f \( -name "*.sh" -o -name "*.js" -o -name "*.ts" -o -name "*.py" -o -name "*.md" \) \
    -exec sed -i "s/Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ5[^\"]*\"/Bearer [REDACTED-JWT-TOKEN]\"/g" {} \;
' --tag-name-filter cat -- --all

echo -e "${GREEN}✅ Git history cleanup completed${RESET}"
echo -e "${BLUE}Backup created at: $BACKUP_DIR${RESET}"
echo -e "${RED}⚠️  All commit SHAs have changed - force push required${RESET}"
echo ""
echo -e "${YELLOW}Next steps:${RESET}"
echo "1. Verify cleanup with: git log --all --oneline | head -10"
echo "2. Search for remaining tokens: git log --all -p -S \"eyJhbGc\" --pickaxe-regex"
echo "3. Force push (DANGEROUS): git push --force-with-lease --all"
echo "4. Notify all collaborators to re-clone the repository"