#!/bin/bash

# Script to remove hardcoded secrets from git history
# WARNING: This will rewrite git history and requires force push

set -e

echo "🔒 Starting git history cleanup to remove hardcoded secrets..."

# List of secrets to remove (partial matches for safety)
SECRETS=(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU1OTcwODQ3"
    "xQVwQQIPe9X00jzJT64CkDnt2/IDmst4TjzNDIVfg0T8ADxlsUZDK+SOtaBs6lYuEttroRNHIOGMPYmoyHHs7A=="
    "dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50"
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl9pZCI6InRva18wZWI4MTMyZmUxMzZiNzgyIg"
    "eyJhbGciOiJIUzI1NiIsImtpZCI6IkdFdmU1ZU9LeUt1UGM4bmUiLCJ0eXAiOiJKV1QifQ"
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQi"
)

# Create a temporary script for git filter-branch
cat > /tmp/filter-secrets.sh << 'EOF'
#!/bin/bash
# This script will be called for each commit

# List of secrets to remove
SECRETS=(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU1OTcwODQ3"
    "xQVwQQIPe9X00jzJT64CkDnt2/IDmst4TjzNDIVfg0T8ADxlsUZDK+SOtaBs6lYuEttroRNHIOGMPYmoyHHs7A=="
    "dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50"
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl9pZCI6InRva18wZWI4MTMyZmUxMzZiNzgyIg"
    "eyJhbGciOiJIUzI1NiIsImtpZCI6IkdFdmU1ZU9LeUt1UGM4bmUiLCJ0eXAiOiJKV1QifQ"
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQi"
)

# Process each Python file in the working directory
find . -name "*.py" -type f | while read file; do
    if [ -f "$file" ]; then
        modified=false
        for secret in "${SECRETS[@]}"; do
            if grep -q "$secret" "$file" 2>/dev/null; then
                echo "Removing secret from: $file"
                # Replace the secret with [REDACTED]
                sed -i "s|$secret|[REDACTED]|g" "$file"
                modified=true
            fi
        done
        
        if [ "$modified" = true ]; then
            git add "$file"
        fi
    fi
done
EOF

chmod +x /tmp/filter-secrets.sh

echo "🔧 Running git filter-branch to clean history..."

# Run git filter-branch to rewrite history
git filter-branch --force --tree-filter '/tmp/filter-secrets.sh' --prune-empty HEAD

echo "🧹 Cleaning up git references..."

# Clean up refs
git for-each-ref --format='%(refname)' refs/original/ | xargs -r git update-ref -d

# Clean up reflog
git reflog expire --expire=now --all

# Garbage collect
git gc --prune=now --aggressive

echo "✅ Git history cleanup completed!"
echo "⚠️  WARNING: Git history has been rewritten!"
echo "🚀 You need to force push to update the remote repository:"
echo "    git push --force-with-lease origin v0.0.2dev"

# Clean up temporary script
rm -f /tmp/filter-secrets.sh

echo "🔍 Verifying secrets removal..."
if git log -p --all | grep -E "(eyJ[a-zA-Z0-9\-_]{20,}\.|xQVwQQIPe9X00jzJT64CkDnt2)" >/dev/null 2>&1; then
    echo "❌ WARNING: Some secrets may still exist in history!"
else
    echo "✅ No secrets found in git history - cleanup successful!"
fi