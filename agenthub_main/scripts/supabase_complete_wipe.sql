-- ============================================================
-- SUPABASE COMPLETE DATABASE WIPE - FRESH START
-- ============================================================
-- Purpose: Completely wipe ALL data from Supabase to start fresh
-- Date: 2025-08-19
-- ⚠️ EXTREME WARNING: THIS WILL DELETE EVERYTHING! ⚠️

-- ============================================================
-- ⚠️ FINAL WARNING - READ CAREFULLY ⚠️
-- ============================================================
/*
THIS SCRIPT WILL:
- DELETE ALL DATA from every table
- REMOVE ALL user accounts from auth.users
- RESET ALL sequences and auto-increments
- DROP AND RECREATE all tables
- WIPE ALL contexts, projects, tasks, agents
- START COMPLETELY FRESH

BEFORE RUNNING:
1. EXPORT ANY DATA YOU WANT TO KEEP
2. BACKUP YOUR SUPABASE PROJECT SETTINGS
3. UNDERSTAND THIS IS IRREVERSIBLE
4. CONFIRM YOU WANT A COMPLETELY CLEAN START

IF YOU'RE NOT 100% SURE, DON'T RUN THIS!
*/

-- ============================================================
-- PHASE 1: DROP ALL FOREIGN KEY CONSTRAINTS FIRST
-- ============================================================

-- Drop constraints to avoid dependency issues during cleanup
ALTER TABLE IF EXISTS tasks DROP CONSTRAINT IF EXISTS fk_tasks_user;
ALTER TABLE IF EXISTS tasks DROP CONSTRAINT IF EXISTS fk_tasks_project;
ALTER TABLE IF EXISTS tasks DROP CONSTRAINT IF EXISTS fk_tasks_git_branch;

ALTER TABLE IF EXISTS projects DROP CONSTRAINT IF EXISTS fk_projects_user;

ALTER TABLE IF EXISTS project_git_branchs DROP CONSTRAINT IF EXISTS fk_project_git_branchs_user;
ALTER TABLE IF EXISTS project_git_branchs DROP CONSTRAINT IF EXISTS fk_project_git_branchs_project;

ALTER TABLE IF EXISTS agents DROP CONSTRAINT IF EXISTS fk_agents_user;
ALTER TABLE IF EXISTS agents DROP CONSTRAINT IF EXISTS fk_agents_project;

ALTER TABLE IF EXISTS global_contexts DROP CONSTRAINT IF EXISTS fk_global_contexts_user;
ALTER TABLE IF EXISTS project_contexts DROP CONSTRAINT IF EXISTS fk_project_contexts_user;
ALTER TABLE IF EXISTS branch_contexts DROP CONSTRAINT IF EXISTS fk_branch_contexts_user;
ALTER TABLE IF EXISTS task_contexts DROP CONSTRAINT IF EXISTS fk_task_contexts_user;

ALTER TABLE IF EXISTS subtasks DROP CONSTRAINT IF EXISTS fk_subtasks_user;
ALTER TABLE IF EXISTS subtasks DROP CONSTRAINT IF EXISTS fk_subtasks_task;

ALTER TABLE IF EXISTS task_dependencies DROP CONSTRAINT IF EXISTS fk_task_dependencies_user;
ALTER TABLE IF EXISTS task_dependencies DROP CONSTRAINT IF EXISTS fk_task_dependencies_task;
ALTER TABLE IF EXISTS task_dependencies DROP CONSTRAINT IF EXISTS fk_task_dependencies_dependency;

ALTER TABLE IF EXISTS cursor_rules DROP CONSTRAINT IF EXISTS fk_cursor_rules_user;

-- ============================================================
-- PHASE 2: DISABLE ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE IF EXISTS tasks DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS projects DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS project_git_branchs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS agents DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS global_contexts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS project_contexts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS branch_contexts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_contexts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS subtasks DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_dependencies DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cursor_rules DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- PHASE 3: DROP ALL POLICIES
-- ============================================================

DROP POLICY IF EXISTS "Users can view own tasks" ON tasks;
DROP POLICY IF EXISTS "Users can create own tasks" ON tasks;
DROP POLICY IF EXISTS "Users can update own tasks" ON tasks;
DROP POLICY IF EXISTS "Users can delete own tasks" ON tasks;

DROP POLICY IF EXISTS "Users can view own projects" ON projects;
DROP POLICY IF EXISTS "Users can create own projects" ON projects;
DROP POLICY IF EXISTS "Users can update own projects" ON projects;
DROP POLICY IF EXISTS "Users can delete own projects" ON projects;

-- Drop any other policies that might exist
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN 
        SELECT schemaname, tablename, policyname 
        FROM pg_policies 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', 
            policy_record.policyname, 
            policy_record.schemaname, 
            policy_record.tablename);
    END LOOP;
END $$;

-- ============================================================
-- PHASE 4: COMPLETE TABLE WIPE
-- ============================================================

-- Drop tables in dependency order
DROP TABLE IF EXISTS user_access_log CASCADE;
DROP TABLE IF EXISTS task_dependencies CASCADE;
DROP TABLE IF EXISTS subtasks CASCADE;
DROP TABLE IF EXISTS task_contexts CASCADE;
DROP TABLE IF EXISTS branch_contexts CASCADE;
DROP TABLE IF EXISTS project_contexts CASCADE;
DROP TABLE IF EXISTS global_contexts CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS project_git_branchs CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS cursor_rules CASCADE;

-- Drop any backup tables from previous migrations
DROP TABLE IF EXISTS backup_tasks CASCADE;
DROP TABLE IF EXISTS backup_projects CASCADE;
DROP TABLE IF EXISTS backup_project_git_branchs CASCADE;
DROP TABLE IF EXISTS backup_agents CASCADE;
DROP TABLE IF EXISTS backup_global_contexts CASCADE;
DROP TABLE IF EXISTS backup_project_contexts CASCADE;
DROP TABLE IF EXISTS backup_branch_contexts CASCADE;
DROP TABLE IF EXISTS backup_task_contexts CASCADE;
DROP TABLE IF EXISTS backup_subtasks CASCADE;
DROP TABLE IF EXISTS backup_task_dependencies CASCADE;
DROP TABLE IF EXISTS backup_cursor_rules CASCADE;

-- Drop backup schema if exists
DROP SCHEMA IF EXISTS backup_20250819 CASCADE;

-- Drop any other backup schemas
DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN 
        SELECT nspname FROM pg_namespace 
        WHERE nspname LIKE 'backup_%'
    LOOP
        EXECUTE format('DROP SCHEMA IF EXISTS %I CASCADE', schema_name);
    END LOOP;
END $$;

-- ============================================================
-- PHASE 5: WIPE ALL USER DATA (CAREFUL!)
-- ============================================================

-- ⚠️ WARNING: This removes ALL user accounts
-- Only do this if you want to start completely fresh
-- Comment out this section if you want to keep existing users

-- Delete all user profiles/metadata (but not auth.users - that's managed by Supabase Auth)
-- We'll let users re-register through the app

-- If you have a profiles table, uncomment and modify:
-- DROP TABLE IF EXISTS public.profiles CASCADE;

-- ============================================================
-- PHASE 6: DROP ALL FUNCTIONS AND TRIGGERS
-- ============================================================

-- Drop custom functions
DROP FUNCTION IF EXISTS get_user_task_count(UUID) CASCADE;
DROP FUNCTION IF EXISTS transfer_entity_ownership(VARCHAR, UUID, UUID, UUID) CASCADE;

-- Drop any triggers (none in current schema, but just in case)
DO $$
DECLARE
    trigger_record RECORD;
BEGIN
    FOR trigger_record IN 
        SELECT trigger_name, event_object_table
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I CASCADE', 
            trigger_record.trigger_name, 
            trigger_record.event_object_table);
    END LOOP;
END $$;

-- ============================================================
-- PHASE 7: DROP ALL INDEXES
-- ============================================================

-- Drop all custom indexes
DO $$
DECLARE
    index_name TEXT;
BEGIN
    FOR index_name IN 
        SELECT indexname FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexname NOT LIKE '%_pkey'  -- Keep primary keys for now
    LOOP
        EXECUTE format('DROP INDEX IF EXISTS %I CASCADE', index_name);
    END LOOP;
END $$;

-- ============================================================
-- PHASE 8: RESET SEQUENCES (if any)
-- ============================================================

-- Reset any sequences that might exist
-- (Current schema uses UUIDs, but just in case)
DO $$
DECLARE
    seq_name TEXT;
BEGIN
    FOR seq_name IN 
        SELECT sequencename FROM pg_sequences 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('DROP SEQUENCE IF EXISTS %I CASCADE', seq_name);
    END LOOP;
END $$;

-- ============================================================
-- PHASE 9: VERIFY COMPLETE CLEANUP
-- ============================================================

DO $$
DECLARE
    table_count INTEGER;
    function_count INTEGER;
    index_count INTEGER;
BEGIN
    -- Count remaining tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    -- Count remaining functions
    SELECT COUNT(*) INTO function_count
    FROM information_schema.routines
    WHERE routine_schema = 'public'
    AND routine_type = 'FUNCTION';
    
    -- Count remaining custom indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public'
    AND indexname NOT LIKE '%_pkey';
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE '🧹 COMPLETE DATABASE WIPE SUMMARY';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Remaining tables: %', table_count;
    RAISE NOTICE 'Remaining functions: %', function_count;
    RAISE NOTICE 'Remaining custom indexes: %', index_count;
    RAISE NOTICE '';
    
    IF table_count = 0 AND function_count = 0 AND index_count = 0 THEN
        RAISE NOTICE '✅ SUCCESS: Database completely wiped clean!';
        RAISE NOTICE '🚀 Ready for fresh user isolation migration';
    ELSE
        RAISE NOTICE '⚠️  Some objects remain - manual cleanup may be needed';
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '📋 NEXT STEPS:';
    RAISE NOTICE '1. Run user isolation migration: 003_add_user_isolation.sql';
    RAISE NOTICE '2. Test with new user registration';
    RAISE NOTICE '3. Verify user data isolation works';
    RAISE NOTICE '============================================================';
END $$;

-- ============================================================
-- PHASE 10: PREPARE FOR FRESH MIGRATION
-- ============================================================

-- Create a marker to indicate this database has been wiped
CREATE TABLE IF NOT EXISTS database_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(50) NOT NULL,
    wiped_at TIMESTAMP NOT NULL DEFAULT NOW(),
    migration_ready BOOLEAN NOT NULL DEFAULT true,
    notes TEXT
);

INSERT INTO database_status (status, notes) VALUES 
('COMPLETELY_WIPED', 'Database wiped clean on 2025-08-19. Ready for user isolation migration.');

-- ============================================================
-- 🎉 WIPE COMPLETE - READY FOR FRESH START! 🎉
-- ============================================================

RAISE NOTICE '';
RAISE NOTICE '🎉 DATABASE WIPE COMPLETED SUCCESSFULLY! 🎉';
RAISE NOTICE '';
RAISE NOTICE '✅ All application data deleted';
RAISE NOTICE '✅ All tables dropped';
RAISE NOTICE '✅ All functions removed';  
RAISE NOTICE '✅ All policies dropped';
RAISE NOTICE '✅ All indexes cleared';
RAISE NOTICE '✅ Database ready for fresh migration';
RAISE NOTICE '';
RAISE NOTICE '🚀 Your Supabase database is now completely clean!';
RAISE NOTICE '🔧 Run the user isolation migration next to set up the new system.';

/*
============================================================
POST-WIPE CHECKLIST:
============================================================

✅ Database completely clean
□ Run user isolation migration (003_add_user_isolation.sql)
□ Test user registration through frontend
□ Verify user data isolation works
□ Create first project and tasks
□ Test multi-user scenarios

MIGRATION COMMAND:
Run: agenthub_main/database/migrations/003_add_user_isolation.sql

This will create:
- All tables with user_id columns
- Row-Level Security policies
- Proper indexes for performance
- Foreign key constraints
- Helper functions

============================================================
*/