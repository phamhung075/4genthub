# Database Migrations

This directory contains all database migration scripts for the 4genthub project, organized for clean development workflow.

## Migration Structure

### Current Active Migrations (v3.0.0 - Clean Development)

- **`000_complete_database_wipe_and_fresh_init.sql`** - Complete database reset and fresh schema initialization
  - **Purpose**: Clean slate database setup for fresh development
  - **Use**: Run this for complete database wipe and fresh start
  - **Includes**: User isolation, RLS policies, indexes, utility functions
  - **Status**: Ready for development use

### Legacy Migrations (Archived)

Legacy migration files have been moved to `archive/legacy-migrations-YYYYMMDD/` for reference:

- `001_add_composite_indexes.sql` - Performance indexes (incorporated into v3.0.0)
- `002_add_authentication_tables.sql` - Auth tables (superseded by Supabase auth)
- `003_add_user_isolation.sql` - User isolation (incorporated into v3.0.0)
- `003_add_user_isolation_simple.sql` - Simplified version (superseded)
- `004_fix_project_contexts_user_id.sql` - Context fixes (incorporated into v3.0.0)
- `004_fix_user_isolation_missing_columns.sql` - Column fixes (incorporated into v3.0.0)

## Migration Execution Guide

### Fresh Development Setup (Recommended)

For a completely clean development environment:

```bash
# 1. Execute the complete wipe and fresh init
psql -d your_database -f 000_complete_database_wipe_and_fresh_init.sql

# 2. Verify initialization
psql -d your_database -c "SELECT * FROM database_status ORDER BY wiped_at DESC LIMIT 1;"
```

### Supabase Specific Setup

For Supabase deployment:

1. **Complete Wipe**: Use the script via Supabase SQL Editor
2. **Verify RLS**: All tables will have Row Level Security enabled
3. **Test User Registration**: Create test user through auth flow
4. **Verify Data Isolation**: Confirm users only see their own data

## Schema Overview

The fresh schema (v3.0.0) includes:

### Core Tables
- `projects` - User projects with isolation
- `project_git_branchs` - Git branches/task trees  
- `tasks` - User tasks with full context
- `subtasks` - Task breakdown items
- `task_dependencies` - Task relationships
- `agents` - AI agent assignments

### Context Hierarchy
- `global_contexts` - Per-user global context
- `project_contexts` - Project-level contexts
- `branch_contexts` - Branch-level contexts  
- `task_contexts` - Task-specific contexts

### Utility Tables
- `database_status` - Migration tracking
- `user_access_log` - Audit logging

## Performance Features

- **Composite Indexes**: Optimized for common query patterns
- **Foreign Keys**: Referential integrity with cascading deletes
- **Row Level Security**: User data isolation (Supabase)
- **JSONB Fields**: Flexible metadata with indexing

## User Isolation Architecture

All tables include `user_id UUID` for complete data isolation:
- Users can only access their own data
- Foreign keys reference `auth.users(id)`
- RLS policies enforce user boundaries
- Cascade deletes maintain referential integrity

## Development Workflow

### Starting Fresh (Development)
1. Run `000_complete_database_wipe_and_fresh_init.sql`
2. Test user registration through frontend
3. Create sample projects and tasks
4. Verify MCP tools functionality

### Incremental Changes (Production)
- Create new numbered migration files (e.g., `001_add_feature.sql`)
- Follow semantic versioning
- Include rollback instructions
- Test on staging environment first

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure database user has CREATE, DROP permissions
2. **RLS Failures**: Verify Supabase auth is properly configured
3. **Foreign Key Violations**: Check data consistency before migration
4. **Function Errors**: Ensure plpgsql extension is enabled

### Verification Commands

```sql
-- Check migration status
SELECT * FROM database_status ORDER BY wiped_at DESC LIMIT 1;

-- Verify table creation
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Check RLS status
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

## Migration History

- **v3.0.0** (2025-08-27): Complete clean slate migration with user isolation
- **v2.x.x** (Archived): Legacy incremental migrations
- **v1.x.x** (Archived): Initial development migrations

## Support

For migration issues:
1. Check database logs
2. Verify user permissions
3. Review RLS policy configurations
4. Test with minimal data set
5. Consult troubleshooting guides in `ai_docs/troubleshooting-guides/`