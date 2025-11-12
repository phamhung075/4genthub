#!/bin/bash
# Git commit with automatic re-staging of formatted files
# Usage: ./scripts/git-auto-commit.sh "commit message"

# Try to commit
if git commit "$@"; then
    echo "✅ Commit successful"
    exit 0
else
    exit_code=$?

    # Check if commit failed due to pre-commit hooks modifying files
    if git status | grep -q "Changes not staged for commit"; then
        echo "📝 Pre-commit modified files, auto-staging and retrying..."
        git add -u
        git commit "$@"
        if [ $? -eq 0 ]; then
            echo "✅ Commit successful after auto-staging"
            exit 0
        fi
    fi

    # If we get here, the commit failed for another reason
    exit $exit_code
fi
