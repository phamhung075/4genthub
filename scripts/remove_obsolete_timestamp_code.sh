#!/usr/bin/env bash

set -euo pipefail

echo "=== REMOVING OBSOLETE TIMESTAMP CODE ==="
echo "WARNING: This operation performs destructive search-and-replace actions."

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

echo "→ Target project root: $PROJECT_ROOT"

# Remove manual timestamp assignments
find "$PROJECT_ROOT"/agenthub_main/src -name "*.py" -exec sed -i \
    -e '/\.updated_at\s*=\s*datetime\./d' \
    -e '/\.created_at\s*=\s*datetime\./d' {} +

# Remove timezone compatibility fallbacks
find "$PROJECT_ROOT"/agenthub_main/src -name "*.py" -exec sed -i \
    -e '/tzinfo\s*is\s*None/d' \
    -e '/replace\s*(.*tzinfo=timezone\.utc)/d' {} +

# Remove legacy initialization helpers
find "$PROJECT_ROOT"/agenthub_main/src -name "*.py" -exec sed -i \
    -e '/_initialize.*timestamp/,/^$/d' {} +

echo "=== OBSOLETE CODE REMOVAL COMPLETE ==="
echo "Next step: run the test suite to confirm behaviour."
