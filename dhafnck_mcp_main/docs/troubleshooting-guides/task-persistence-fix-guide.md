# Task Persistence Fix Guide

## Problem Description

The task persistence issue was caused by missing `user_id` columns in task relationship tables (`task_subtasks`, `task_assignees`, and `task_labels`). This prevented proper user isolation and caused database constraint violations when creating or updating tasks with relationships.

## Root Cause

The user isolation migration (`003_add_user_isolation.sql`) missed adding `user_id` columns to the following relationship tables:
- `task_subtasks` 
- `task_assignees`
- `task_labels`

These tables are used for many-to-many relationships and need `user_id` columns for proper data isolation.

## Solution Components

### 1. Database Migration Script
**File:** `dhafnck_mcp_main/database/migrations/004_fix_user_isolation_missing_columns.sql`

**What it does:**
- Adds `user_id` columns to missing relationship tables
- Backfills existing data from parent tasks
- Sets NOT NULL constraints
- Adds foreign key constraints (for Supabase)
- Creates indexes for performance
- Adds Row-Level Security policies (for Supabase)

**Usage:**
```bash
# For PostgreSQL/Supabase
psql -d your_database < dhafnck_mcp_main/database/migrations/004_fix_user_isolation_missing_columns.sql

# For SQLite (manual execution needed)
sqlite3 your_database.db < dhafnck_mcp_main/database/migrations/004_fix_user_isolation_missing_columns.sql
```

### 2. Schema Validation Script
**File:** `dhafnck_mcp_main/scripts/validate_schema.py`

**What it does:**
- Compares SQLAlchemy models to actual database schema
- Reports mismatches between expected and actual schema
- Identifies missing `user_id` columns
- Can attempt automatic fixes for critical issues

**Usage:**
```bash
# Basic validation
python dhafnck_mcp_main/scripts/validate_schema.py

# Verbose output
python dhafnck_mcp_main/scripts/validate_schema.py --verbose

# Attempt automatic fixes
python dhafnck_mcp_main/scripts/validate_schema.py --fix

# Use custom database URL
python dhafnck_mcp_main/scripts/validate_schema.py --database-url "postgresql://user:pass@localhost/db"
```

### 3. Repository Graceful Error Handling
**File:** `dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py`

**What was updated:**
- Added graceful error handling for relationship loading
- Implemented fallback loading when joinedload operations fail
- Added try-catch blocks around relationship creation
- Added proper logging for debugging relationship issues

**Key methods:**
- `_load_task_with_relationships()` - Safe relationship loading with fallback
- `_model_to_entity()` - Graceful entity conversion
- Updated `get_task()`, `create_task()`, `update_task()` methods

### 4. Integration Test Suite
**File:** `dhafnck_mcp_main/src/tests/integration/test_task_persistence_fix.py`

**What it tests:**
- Task creation with all relationships (assignees, labels, subtasks)
- Task retrieval with missing relationships
- Subtask creation with `user_id` inclusion
- Migration backfill simulation
- Repository graceful error handling
- Complete task lifecycle after fix

**Usage:**
```bash
# Run with pytest
pytest dhafnck_mcp_main/src/tests/integration/test_task_persistence_fix.py -v

# Run standalone for debugging
python dhafnck_mcp_main/src/tests/integration/test_task_persistence_fix.py
```

## Fix Application Steps

### Step 1: Backup Database
```bash
# For PostgreSQL
pg_dump your_database > backup_before_fix.sql

# For SQLite
cp your_database.db backup_before_fix.db
```

### Step 2: Validate Current Schema
```bash
python dhafnck_mcp_main/scripts/validate_schema.py --verbose
```

### Step 3: Apply Migration
```bash
# Run the migration script
psql -d your_database < dhafnck_mcp_main/database/migrations/004_fix_user_isolation_missing_columns.sql
```

### Step 4: Verify Fix
```bash
# Re-validate schema
python dhafnck_mcp_main/scripts/validate_schema.py

# Run integration tests
pytest dhafnck_mcp_main/src/tests/integration/test_task_persistence_fix.py -v
```

### Step 5: Test Application
- Create a task with assignees and labels
- Verify task can be retrieved successfully
- Check that all relationships persist correctly

## Expected Results After Fix

### ✅ Database Schema
- All relationship tables have `user_id` columns
- All existing data has proper `user_id` values
- NOT NULL constraints are enforced
- Indexes are in place for performance

### ✅ Application Behavior
- Tasks can be created with assignees and labels without errors
- Task retrieval works even if some relationships fail to load
- Graceful degradation when schema issues exist
- Proper logging for debugging relationship issues

### ✅ Data Isolation
- Users can only see their own tasks and relationships
- Relationship data is properly isolated by `user_id`
- Row-Level Security policies protect data (Supabase)

## Troubleshooting

### Migration Fails
- **Error:** Column already exists
  - **Solution:** Safe to ignore - script uses `IF NOT EXISTS`
  
- **Error:** Cannot set NOT NULL constraint
  - **Solution:** Run backfill commands separately first

### Schema Validation Reports Issues
- **Critical Issues:** Run migration script immediately
- **Warnings:** Plan to address in next maintenance window
- **User_ID Issues:** Indicates migration needed

### Repository Errors Continue
- Check application logs for relationship loading warnings
- Verify all relationship tables have `user_id` columns
- Run integration tests to confirm fix effectiveness

### Performance Issues
- Verify indexes were created by migration
- Check query performance for relationship loading
- Consider using `selectinload` for large datasets

## Monitoring

After applying the fix, monitor for:
- Task creation success rates
- Relationship loading error logs
- Database constraint violations
- User isolation effectiveness

## Prevention

To prevent similar issues in the future:
1. Run schema validation script before deployments
2. Include relationship tables in all data isolation migrations
3. Use integration tests to verify complete workflows
4. Monitor application logs for relationship loading issues