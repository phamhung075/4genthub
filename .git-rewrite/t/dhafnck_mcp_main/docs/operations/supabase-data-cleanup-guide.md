# Supabase Data Cleanup Guide

## Overview

This guide provides comprehensive steps to clean old data from your Supabase database and prepare it for the new user isolation system. The cleanup process removes legacy system data while preserving data integrity.

## ⚠️ WARNING - READ BEFORE PROCEEDING

**This process will DELETE existing data from your Supabase database. Always create backups before proceeding.**

## Prerequisites

1. Supabase project with SQL Editor access
2. Database administrator privileges
3. Backup storage for current data
4. Understanding of your current data structure

## Step-by-Step Process

### Step 1: Create Complete Backup

**Location**: `scripts/supabase_backup_script.sql`

1. Open Supabase SQL Editor
2. Run the backup script to create `backup_20250819` schema
3. Verify backup integrity by checking the output logs

**What it does**:
- Creates backup tables for all main data tables
- Records statistics about current data
- Creates restore instructions
- Verifies backup integrity

### Step 2: Analyze Current Data Structure

Before cleanup, understand what data you have:

```sql
-- Check current data counts
SELECT 'tasks' as table_name, COUNT(*) as count FROM tasks
UNION ALL
SELECT 'projects', COUNT(*) FROM projects  
UNION ALL
SELECT 'agents', COUNT(*) FROM agents
UNION ALL
SELECT 'contexts', COUNT(*) FROM (
    SELECT 1 FROM global_contexts
    UNION ALL SELECT 1 FROM project_contexts
    UNION ALL SELECT 1 FROM branch_contexts  
    UNION ALL SELECT 1 FROM task_contexts
) as all_contexts;
```

### Step 3: Execute Data Cleanup

**Location**: `scripts/supabase_data_cleanup.sql`

1. Review the cleanup script thoroughly
2. Execute the script in Supabase SQL Editor
3. Monitor the output for any errors
4. Verify cleanup results

**What it does**:
- Removes all system user data (UUID '00000000-0000-0000-0000-000000000000')
- Cleans up orphaned references
- Resets global context with clean welcome message
- Updates table statistics
- Verifies data integrity

### Step 4: Verify User Isolation Migration

After cleanup, apply the user isolation migration:

**Location**: `database/migrations/003_add_user_isolation.sql`

1. Run the migration script
2. Verify all tables have user_id columns
3. Check that Row-Level Security is enabled
4. Test with a new user account

## Expected Results After Cleanup

### Data Removed
- All legacy system user data
- Orphaned tasks without valid projects
- Orphaned subtasks without valid tasks
- Orphaned contexts without valid entities
- Invalid task dependencies

### Data Preserved
- Database schema structure
- User authentication data (auth.users)
- Migration history
- System configuration

### New Features Added
- Row-Level Security policies
- User-scoped data access
- Audit logging capability
- Helper functions for user management

## Verification Checklist

After completing the cleanup:

- [ ] All main tables are empty or contain only valid data
- [ ] User isolation migration applied successfully
- [ ] Row-Level Security enabled on all tables
- [ ] Foreign key constraints intact
- [ ] Indexes created for performance
- [ ] Backup data preserved in backup schema

## Testing the Clean System

1. **Create Test User**:
   ```sql
   -- User will be created via Supabase Auth UI
   ```

2. **Test Data Isolation**:
   - Create projects, tasks via frontend
   - Verify data is user-scoped
   - Test with multiple users

3. **Verify API Endpoints**:
   - Test V2 authenticated endpoints
   - Verify V1 fallback works
   - Check JWT token handling

## Rollback Instructions

If you need to restore the original data:

1. **Emergency Restore**:
   ```sql
   -- Use the restore script from backup_20250819.restore_instructions
   SELECT restore_sql FROM backup_20250819.restore_instructions;
   ```

2. **Partial Restore**:
   ```sql
   -- Restore specific table
   TRUNCATE public.tasks CASCADE;
   INSERT INTO public.tasks SELECT * FROM backup_20250819.tasks;
   ```

## Post-Cleanup Monitoring

### Monitor Database Performance
- Check query execution times
- Monitor index usage
- Watch for constraint violations

### Monitor Application Logs
- Check for authentication errors
- Verify user data isolation
- Monitor API response times

### User Experience Verification
- Test login/logout flow
- Verify data visibility per user
- Check frontend functionality

## Troubleshooting

### Common Issues

1. **Foreign Key Violations**:
   ```sql
   -- Check for orphaned references
   SELECT * FROM tasks WHERE project_id NOT IN (SELECT id FROM projects);
   ```

2. **RLS Policy Issues**:
   ```sql
   -- Verify policies exist
   SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public';
   ```

3. **Migration Errors**:
   ```sql
   -- Check migration status
   SELECT * FROM information_schema.columns WHERE column_name = 'user_id';
   ```

### Performance Issues

If queries are slow after cleanup:

```sql
-- Update statistics
ANALYZE tasks;
ANALYZE projects;
-- ... repeat for other tables

-- Check index usage
SELECT * FROM pg_stat_user_indexes WHERE relname = 'tasks';
```

## Maintenance Schedule

### Weekly
- Monitor user access patterns
- Check for orphaned data
- Review audit logs

### Monthly  
- Analyze query performance
- Update table statistics
- Clean up old audit logs

### Quarterly
- Review RLS policies
- Update backup procedures
- Performance optimization

## Security Considerations

1. **Access Control**:
   - Only database administrators should run cleanup scripts
   - Backup data contains sensitive information
   - Monitor access to backup schema

2. **Data Privacy**:
   - Cleanup removes all user data
   - Ensure compliance with data retention policies
   - Document data deletion for audit purposes

3. **Recovery Planning**:
   - Maintain backups for required retention period
   - Test restore procedures regularly
   - Document emergency procedures

## Support

If you encounter issues during cleanup:

1. Check the backup data integrity first
2. Review error logs for specific issues
3. Consult the troubleshooting section
4. Consider partial rollback if needed

Remember: The cleanup process is designed to be safe with comprehensive backups, but always proceed with caution in production environments.