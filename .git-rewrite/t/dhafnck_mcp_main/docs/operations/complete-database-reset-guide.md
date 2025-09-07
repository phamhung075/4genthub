# Complete Supabase Database Reset Guide

## ⚠️ CRITICAL WARNING ⚠️

**THIS GUIDE WILL COMPLETELY WIPE YOUR ENTIRE SUPABASE DATABASE!**

This is a **NUCLEAR OPTION** that deletes:
- ✅ ALL data from every table
- ✅ ALL user accounts and authentication data
- ✅ ALL projects, tasks, agents, contexts
- ✅ ALL database structure (tables, indexes, functions)
- ✅ ALL Row-Level Security policies
- ✅ ALL backup data

**ONLY USE THIS IF YOU WANT A COMPLETELY FRESH START!**

## When to Use This Guide

Use this nuclear reset when:
- ✅ Starting completely fresh with new user isolation system
- ✅ Development/staging environment reset
- ✅ Corrupted data that can't be fixed
- ✅ Major schema changes requiring clean slate
- ✅ Testing new architecture from scratch

**DO NOT USE ON PRODUCTION unless you're 100% certain!**

## Prerequisites

- [ ] Supabase project with SQL Editor access
- [ ] Database administrator privileges  
- [ ] **EXPORTED any data you want to keep**
- [ ] **BACKED UP project settings and configurations**
- [ ] **CONFIRMED this is what you want to do**

## Step-by-Step Process

### Step 1: Final Data Export (If Needed)

If you need to keep ANY data, export it now:

```sql
-- Export specific data you want to keep
COPY (SELECT * FROM tasks WHERE important = true) TO '/tmp/important_tasks.csv' CSV HEADER;
COPY (SELECT * FROM projects WHERE status = 'active') TO '/tmp/active_projects.csv' CSV HEADER;
-- etc...
```

### Step 2: Execute Complete Wipe

**Location**: `scripts/supabase_complete_wipe.sql`

1. Open Supabase SQL Editor
2. **READ THE WARNINGS in the script carefully**
3. Execute the complete wipe script
4. Wait for all phases to complete
5. Verify the cleanup summary

**Phases Executed**:
1. Drop all foreign key constraints
2. Disable Row-Level Security
3. Drop all RLS policies  
4. Drop all tables CASCADE
5. Remove all user data references
6. Drop all custom functions
7. Drop all custom indexes
8. Reset any sequences
9. Verify complete cleanup
10. Prepare for fresh migration

### Step 3: Verify Complete Wipe

After running the script, verify results:

```sql
-- Check no tables remain
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check no functions remain
SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public';

-- Check database status
SELECT * FROM database_status;
```

Expected result: **Empty results** (except database_status table)

### Step 4: Apply Fresh User Isolation Migration

**Location**: `database/migrations/003_add_user_isolation.sql`

1. Run the user isolation migration script
2. This recreates all tables with user_id columns
3. Applies Row-Level Security policies
4. Creates proper indexes and constraints
5. Sets up helper functions

### Step 5: Verify New System

Test the fresh system:

1. **User Registration**:
   - Go to frontend signup page
   - Create first user account
   - Verify login works

2. **Data Isolation**:
   - Create projects and tasks
   - Register second user
   - Verify users can't see each other's data

3. **API Endpoints**:
   - Test V2 authenticated endpoints
   - Verify JWT token handling
   - Check user-scoped responses

## Expected Results

### Before Wipe
```
Tables: 15+ (tasks, projects, agents, contexts, etc.)
Data Records: 1000s (your existing data)
Users: Existing auth.users records
Structure: Legacy schema without user isolation
```

### After Wipe + Migration
```
Tables: 15+ (same tables, but with user_id columns)
Data Records: 0 (completely empty)
Users: Only new registrations
Structure: Fresh schema with full user isolation
```

## Post-Reset Verification Checklist

- [ ] No old data remains
- [ ] All tables have user_id columns
- [ ] Row-Level Security enabled on all tables
- [ ] Foreign key constraints properly set
- [ ] Indexes created for performance
- [ ] User registration works via frontend
- [ ] Data isolation works between users
- [ ] JWT authentication functioning
- [ ] V2 API endpoints responding correctly

## What's NOT Affected

The following Supabase features remain intact:
- ✅ **Auth configuration** (providers, settings)
- ✅ **Project settings** (API keys, URLs)
- ✅ **Database connection strings**
- ✅ **Edge functions** (if you have any)
- ✅ **Storage buckets** (if configured)
- ✅ **Realtime subscriptions** (configuration)

## Recovery Instructions

**There is NO recovery from this operation!**

If you realize you made a mistake:
1. You'll need to restore from external backups
2. Re-import any data you exported
3. Reconfigure any custom settings
4. Re-register all users

## Common Issues & Solutions

### Issue: Script fails with permission errors
**Solution**: Ensure you're running as database owner/admin

### Issue: Some tables won't drop due to dependencies
**Solution**: The script handles CASCADE drops, but check for external dependencies

### Issue: Auth.users table concerns
**Solution**: The script doesn't touch auth.users - that's managed by Supabase Auth service

### Issue: Frontend can't connect after wipe
**Solution**: 
- Check API URLs are still correct
- Verify auth configuration unchanged
- Test with fresh user registration

## Testing the Fresh System

### Test 1: User Registration
```bash
# Frontend test
1. Go to signup page
2. Register new user: test1@example.com
3. Verify email confirmation (if enabled)
4. Login successfully
```

### Test 2: Data Isolation
```bash
# Multi-user test
1. User 1 creates project "Project A"
2. User 2 registers and logs in
3. User 2 should NOT see "Project A"
4. User 2 creates project "Project B" 
5. User 1 should NOT see "Project B"
```

### Test 3: API Endpoints
```bash
# API test
curl -H "Authorization: Bearer <jwt_token>" \
     https://your-project.supabase.co/rest/v1/tasks

# Should return only user's tasks (empty for new user)
```

## Performance Considerations

After the wipe and fresh migration:
- ✅ **Faster queries** (no legacy data to scan)
- ✅ **Optimal indexes** (created fresh)
- ✅ **Clean statistics** (no old data skewing)
- ✅ **Efficient RLS policies** (applied to empty tables)

## Security Benefits

The fresh system provides:
- 🔒 **Complete user isolation** (RLS enforced)
- 🔒 **No legacy security holes** (clean policies)
- 🔒 **Proper foreign key constraints** (data integrity)
- 🔒 **Audit trail ready** (clean logging setup)

## Final Notes

This nuclear reset gives you:
- **100% clean slate** for new architecture
- **Perfect user isolation** from day one
- **Optimal performance** with fresh schema
- **Modern security** with proper RLS
- **Future-proof structure** for scaling

Remember: This is irreversible, but sometimes a fresh start is exactly what you need! 🚀

---

**After completing this guide, your Supabase database will be completely fresh and ready for the new user isolation system. All users will need to re-register, and you can build your data from scratch with perfect multi-tenant architecture.**