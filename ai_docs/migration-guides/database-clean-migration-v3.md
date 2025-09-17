# Database Clean Migration Guide v3.0.0

## Overview

This guide covers the complete database clean slate migration for 4genthub v3.0.0, designed to provide a fresh development environment with proper user isolation, performance optimization, and clean architecture.

## Migration Components

### 1. Migration Scripts

- **`000_complete_database_wipe_and_fresh_init.sql`** - Complete database reset and fresh schema
- **`run_fresh_migration.py`** - Python script for safe migration execution  
- **`verify_database_setup.py`** - Comprehensive verification script
- **`README.md`** - Migration documentation

### 2. Directory Structure

```
4genthub_main/database/
├── migrations/
│   ├── 000_complete_database_wipe_and_fresh_init.sql (NEW)
│   ├── README.md (NEW)
│   └── archive/
│       └── legacy-migrations-YYYYMMDD/ (ARCHIVED LEGACY)
├── scripts/
│   ├── run_fresh_migration.py (NEW)
│   └── verify_database_setup.py (NEW)
├── schema/ (EXISTING)
└── data/ (EXISTING)
```

## Pre-Migration Checklist

- [ ] **BACKUP CRITICAL DATA** - Export any data you want to keep
- [ ] **TEST ENVIRONMENT** - Run migration on staging first
- [ ] **DATABASE ACCESS** - Ensure proper permissions for CREATE/DROP operations
- [ ] **ENVIRONMENT VARIABLES** - Set appropriate database connection strings
- [ ] **DEPENDENCY CHECK** - Ensure `psycopg2` is installed for Python scripts

## Migration Process

### Option 1: Automated Migration (Recommended)

```bash
# Set environment variables
export SUPABASE_DB_URL="postgresql://[user]:[password]@[host]:5432/[database]"

# Run migration with confirmation
cd 4genthub_main/database/scripts
python run_fresh_migration.py --supabase

# Verify setup
python verify_database_setup.py --supabase --detailed
```

### Option 2: Manual SQL Execution

```bash
# Connect to database
psql -d your_database_url

# Execute migration
\i 4genthub_main/database/migrations/000_complete_database_wipe_and_fresh_init.sql

# Verify
SELECT * FROM database_status ORDER BY wiped_at DESC LIMIT 1;
```

## What the Migration Does

### Phase 1: Complete Database Wipe
- Drops all foreign key constraints
- Disables Row Level Security
- Drops all policies  
- Drops all tables (including backups)
- Drops all custom functions
- Drops all custom indexes
- Drops all sequences

### Phase 2: Fresh Schema Creation
- Creates `database_status` tracking table
- Marks database as fresh development ready

### Phase 3: Core Schema with User Isolation
- **Projects** - User-isolated project management
- **Git Branches** - Task tree organization
- **Tasks** - Full task management with context
- **Subtasks** - Task breakdown functionality
- **Dependencies** - Task relationship management
- **Agents** - AI agent assignments

### Phase 4: Context Hierarchy
- **Global Contexts** - Per-user global context
- **Project Contexts** - Project-level contexts
- **Branch Contexts** - Git branch contexts
- **Task Contexts** - Task-specific contexts

### Phase 5: Performance Optimization
- Composite indexes for common query patterns
- Foreign key constraints with cascading deletes
- User isolation indexes for fast filtering

### Phase 6: Row Level Security (Supabase)
- Enables RLS on all tables
- Creates user isolation policies
- Ensures data privacy boundaries

### Phase 7: Utility Functions
- `get_user_task_count(user_id)` - Count user tasks
- `create_default_user_project(user_id)` - Initialize user workspace

### Phase 8: Audit Infrastructure
- User access logging table
- Performance indexes for audit queries

## Verification Steps

### Automated Verification

```bash
python verify_database_setup.py --supabase --detailed
```

Expected output:
```
✅ All required tables present (11 tables)
✅ User isolation properly implemented
✅ Key performance indexes created (25 total)
✅ Foreign key constraints properly set (10 total)
✅ Utility functions created (2 total)
✅ Row Level Security configured (8 policies)
✅ Basic database operations working

🎉 DATABASE VERIFICATION PASSED
✅ Database is ready for development and MCP tools
```

### Manual Verification

```sql
-- Check migration status
SELECT * FROM database_status ORDER BY wiped_at DESC LIMIT 1;

-- Verify table structure
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Check user isolation
SELECT table_name FROM information_schema.columns 
WHERE column_name = 'user_id' AND table_schema = 'public'
ORDER BY table_name;

-- Verify RLS policies
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;
```

## Post-Migration Testing

### 1. MCP Tools Testing

```bash
# Test project creation
mcp__4genthub_http__manage_project(action="create", name="test-project")

# Test task creation
mcp__4genthub_http__manage_task(action="create", git_branch_id="...", title="Test Task")

# Test context operations
mcp__4genthub_http__manage_context(action="create", level="task", ...)
```

### 2. User Registration Testing

- Test user registration through frontend
- Verify user data isolation
- Test cross-user data access (should fail)
- Verify RLS policies work correctly

### 3. Performance Testing

- Create sample projects, branches, and tasks
- Test query performance with indexes
- Verify foreign key constraint enforcement
- Test cascade deletes

## Troubleshooting

### Common Issues

#### Permission Errors
```
ERROR: permission denied to create table
```
**Solution**: Ensure database user has `CREATE`, `DROP` privileges.

#### Foreign Key Violations
```
ERROR: foreign key violation
```
**Solution**: Check if `auth.users` table exists (Supabase) or create system user.

#### RLS Policy Errors
```
ERROR: policy "policy_name" already exists
```
**Solution**: Run the complete wipe first, or manually drop existing policies.

#### Function Creation Errors
```
ERROR: language "plpgsql" does not exist
```
**Solution**: Enable plpgsql extension: `CREATE EXTENSION IF NOT EXISTS plpgsql;`

### Recovery Procedures

#### Partial Migration Failure
1. Check which phase failed from error logs
2. Run complete wipe again: Phase 1 of migration script
3. Re-execute full migration

#### Data Loss During Migration
1. Restore from backup if available
2. Re-run complete migration
3. Rebuild data from application layer

#### RLS Policy Issues
1. Disable RLS temporarily: `ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;`
2. Fix data issues
3. Re-enable RLS: `ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;`

## Environment-Specific Notes

### Supabase Production
- RLS policies automatically enforced
- `auth.users` table managed by Supabase Auth
- Use Supabase SQL Editor for execution
- Monitor dashboard for performance metrics

### Local Development
- RLS policies may not be available (normal)
- Create local `auth.users` table if needed
- Use connection pooling for performance
- Enable query logging for debugging

### Docker Environment
- Ensure database volume persistence
- Check container network connectivity
- Verify environment variable passing
- Use Docker logs for debugging

## Next Steps

1. **User Registration**: Test authentication flow
2. **Sample Data**: Create representative test data
3. **Performance Monitoring**: Set up query performance tracking
4. **Backup Strategy**: Implement regular backup procedures
5. **Monitoring**: Set up database health monitoring
6. **Documentation**: Update API documentation for new schema

## Schema Reference

### Core Tables Structure

#### Projects
- `id` (UUID, PK)
- `name` (VARCHAR, user-unique)
- `description` (TEXT)
- `user_id` (UUID, FK to auth.users)
- `status` (VARCHAR, default 'active')
- `metadata` (JSONB)
- Timestamps: `created_at`, `updated_at`

#### Tasks
- `id` (UUID, PK)
- `title` (VARCHAR, required)
- `description` (TEXT, required)
- `git_branch_id` (UUID, FK)
- `user_id` (UUID, FK to auth.users)
- `status` (VARCHAR, default 'todo')
- `priority` (VARCHAR, default 'medium')
- `context_id` (UUID, optional link)
- Timestamps and metadata

#### Context Hierarchy
- All context tables follow same pattern
- `user_id` for isolation
- `context_data` (JSONB) for flexible storage
- `insights` and `progress_updates` (JSONB arrays)

## Migration History

- **v3.0.0** (2025-08-27): Complete clean slate migration with user isolation
- **v2.x.x**: Legacy incremental migrations (archived)
- **v1.x.x**: Initial development migrations (archived)

---

**⚠️ Important**: This migration completely wipes existing data. Ensure you have backups of any critical information before proceeding.