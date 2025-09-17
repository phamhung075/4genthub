#!/bin/sh
set -e

# Optimized Docker entrypoint with lazy initialization

echo "🚀 Starting 4genthub Server (Optimized)"

# Function to check database connection
check_database() {
    python -c "
import os
import sys
import time
from sqlalchemy import create_engine

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('⚠️  No DATABASE_URL set, skipping DB check')
    sys.exit(0)

max_retries = 5
retry_delay = 2

for i in range(max_retries):
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
        sys.exit(0)
    except Exception as e:
        if i < max_retries - 1:
            print(f'⏳ Database not ready, retrying in {retry_delay}s...')
            time.sleep(retry_delay)
        else:
            print(f'❌ Database connection failed: {e}')
            sys.exit(1)
"
}

# Lazy initialization - only if needed
if [ "$SKIP_DB_CHECK" != "true" ]; then
    check_database
fi

# Execute the main command with optimizations
exec "$@"