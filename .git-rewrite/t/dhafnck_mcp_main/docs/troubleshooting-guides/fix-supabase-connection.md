# Fix Supabase Connection After Rebuild

## The Problem
After rebuilding with docker-menu option 2, you don't see your Supabase data because:
1. The ORM model was out of sync with the actual database schema
2. Docker rebuild creates a fresh container but doesn't migrate data
3. The connection might be failing due to schema mismatches

## Solution Steps

### 1. Verify Supabase Connection
Check if the backend is actually connecting to Supabase:
```bash
docker logs dhafnck-backend | grep -i "supabase\|database"
```

### 2. Test Database Connection
```bash
docker exec dhafnck-backend python -c "
import os
os.environ['DATABASE_TYPE'] = 'supabase'
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
db = get_db_config()
print('Connected to:', db.get_database_info())
"
```

### 3. Check for Schema Issues
The main issue is the BranchContext model mismatch. The fix we applied needs to be in the container.

### 4. Rebuild Without Cache But Keep Data
Instead of using the menu, try this manual approach:

```bash
# Stop current containers
docker stop dhafnck-backend dhafnck-frontend

# Remove containers but keep data
docker rm dhafnck-backend dhafnck-frontend

# Rebuild with your Supabase config
cd docker-system/docker
docker-compose --env-file ../../.env -f docker-compose.supabase.yml build

# Start services
docker-compose --env-file ../../.env -f docker-compose.supabase.yml up -d
```

### 5. Verify Data Access
Once running, test if you can see your data:
```bash
# Check if projects exist
curl http://localhost:8000/projects/list
```

## Important Notes

1. **Schema Sync**: The ORM models MUST match your Supabase database schema exactly
2. **Environment Variables**: Ensure all SUPABASE_* variables are set in .env
3. **Database Type**: DATABASE_TYPE must be set to "supabase"
4. **No Local Data**: Supabase Cloud means data is stored remotely, not in Docker volumes

## If Data Still Missing

Your data is safe in Supabase Cloud. The issue is likely:
- Connection failure due to schema mismatch
- Wrong database being connected to
- Authentication issues with Supabase

Check Supabase Dashboard to verify your data exists there.
