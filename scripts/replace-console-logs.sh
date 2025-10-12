#!/bin/bash

# Script to replace console.log with logger service calls
# Usage: ./replace-console-logs.sh

FRONTEND_SRC="/home/daihungpham/__projects__/4genthub/agenthub-frontend/src"

# Files to process (excluding tests, mocks, and logger itself)
FILES=$(find "$FRONTEND_SRC" -type f \( -name "*.ts" -o -name "*.tsx" \) \
  ! -path "*/tests/*" \
  ! -path "*/test/*" \
  ! -name "*.test.ts" \
  ! -name "*.test.tsx" \
  ! -name "logger.ts" \
  ! -name "logger.config.ts" \
  ! -path "*/mocks/*")

echo "Files to process:"
echo "$FILES" | wc -l

# For each file, check if it has console.log
for file in $FILES; do
  if grep -q "console\.log" "$file"; then
    echo "Processing: $file"

    # Check if logger import exists
    if ! grep -q "^import logger from" "$file" && ! grep -q "^import.*logger.*from.*logger" "$file"; then
      echo "  → Need to add logger import"
    fi

    # Count console.log occurrences
    count=$(grep -c "console\.log" "$file")
    echo "  → Found $count console.log statements"
  fi
done
