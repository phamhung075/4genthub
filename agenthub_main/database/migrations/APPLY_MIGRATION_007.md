# How to Apply Migration 007: Agent Management Tables

## Migration File
- **File**: `007_add_agent_management_tables.sql`
- **Purpose**: Create `agent_templates` and `user_agent_instances` tables
- **Date**: 2025-11-02

## What This Migration Does

Creates two new tables for the agent management system:

### 1. `agent_templates` Table
- Stores global agent template definitions from agent-library
- Shared across all users
- Columns: id, slug, name, description, category, version, system_prompt, tools, capabilities, rules, output_format, metadata, timestamps

### 2. `user_agent_instances` Table
- Stores per-user agent instances with customizations
- One instance per template per user (UNIQUE constraint)
- **Key columns added**:
  - `is_enabled` - Boolean, default TRUE (for agent selection in call_agent)
  - `share_token` - VARCHAR(64), unique, nullable (required when visibility='public')
  - `visibility` - VARCHAR(50), default 'private' (controls sharing)
  - All configuration fields (system_prompt, tools, capabilities, rules, output_format)
  - Usage tracking (usage_count, last_used_at)
  - Import tracking (original_creator_id, imported_at)

## Apply Migration Methods

### Method 1: Through Docker Container (Recommended)

```bash
# Option A: Copy file into container and execute
docker cp agenthub_main/database/migrations/007_add_agent_management_tables.sql agenthub_postgres:/tmp/
docker exec -it agenthub_postgres psql -U agenthub_user -d agenthub -f /tmp/007_add_agent_management_tables.sql

# Option B: Execute directly via stdin
docker exec -i agenthub_postgres psql -U agenthub_user -d agenthub < agenthub_main/database/migrations/007_add_agent_management_tables.sql
```

### Method 2: Through FastAPI Startup

Add to backend startup script or run once:

```python
from sqlalchemy import create_engine, text
import os

# Get database URL from env
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)

# Read and apply migration
with open('database/migrations/007_add_agent_management_tables.sql', 'r') as f:
    migration_sql = f.read()

with engine.connect() as conn:
    conn.execute(text(migration_sql))
    conn.commit()
```

### Method 3: Manual psql Connection

If PostgreSQL is running locally:

```bash
psql -U agenthub_user -d agenthub -f agenthub_main/database/migrations/007_add_agent_management_tables.sql
```

## Verification

After applying the migration, verify the tables exist:

```sql
-- Check tables were created
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('agent_templates', 'user_agent_instances');

-- Check columns in user_agent_instances
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'user_agent_instances'
ORDER BY ordinal_position;

-- Verify indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('agent_templates', 'user_agent_instances')
ORDER BY tablename, indexname;
```

## Expected Output

You should see:
- ✅ 2 tables created: `agent_templates`, `user_agent_instances`
- ✅ 7 indexes on `agent_templates`
- ✅ 10 indexes on `user_agent_instances`
- ✅ UNIQUE constraint on (user_id, template_id)
- ✅ All required columns including `is_enabled`, `share_token`, `visibility`

## Rollback (If Needed)

```sql
-- WARNING: This will delete all agent data!
DROP TABLE IF EXISTS user_agent_instances CASCADE;
DROP TABLE IF EXISTS agent_templates CASCADE;
```

## Next Steps

After applying this migration:
1. ✅ Restart backend container: `echo "R" | ./docker-system/docker-menu.sh`
2. ✅ Backend will auto-create agent templates from agent-library on startup
3. ✅ Users can start creating instances and using the Edit Agent Dialog
4. ✅ All frontend features (edit, share_token, visibility) will work properly

## Troubleshooting

### Error: relation "user_agent_instances" already exists
- Tables may already exist from previous attempts
- Run verification queries to check current state
- If incomplete, drop and recreate using rollback then reapply

### Error: password authentication failed
- PostgreSQL not running or wrong credentials
- Check `.env` file for DATABASE_URL
- Ensure Docker container is running: `docker ps | grep postgres`

### Error: permission denied
- User doesn't have CREATE TABLE privileges
- Connect as superuser or admin to grant permissions:
  ```sql
  GRANT CREATE ON SCHEMA public TO agenthub_user;
  ```
