-- ============================================================
-- SUPABASE CLEAN ALL PUBLIC TABLES (DATA ONLY)
-- ============================================================
-- Purpose: Delete ALL data from public schema tables while keeping structure
-- Date: 2025-08-19
-- ⚠️ WARNING: This will DELETE ALL DATA from public tables!

-- ============================================================
-- PHASE 1: DISABLE TRIGGERS & CONSTRAINTS TEMPORARILY
-- ============================================================

-- Disable all triggers to avoid issues during deletion
SET session_replication_role = 'replica';

-- ============================================================
-- PHASE 2: DELETE ALL DATA FROM PUBLIC TABLES
-- ============================================================

-- Delete in reverse dependency order to avoid foreign key violations

-- First, delete from tables with no dependencies (leaf tables)
DELETE FROM user_access_log WHERE 1=1;
DELETE FROM task_dependencies WHERE 1=1;
DELETE FROM subtasks WHERE 1=1;
DELETE FROM cursor_rules WHERE 1=1;

-- Delete from context tables
DELETE FROM task_contexts WHERE 1=1;
DELETE FROM branch_contexts WHERE 1=1;
DELETE FROM project_contexts WHERE 1=1;
DELETE FROM global_contexts WHERE 1=1;

-- Delete from main entity tables
DELETE FROM agents WHERE 1=1;
DELETE FROM tasks WHERE 1=1;
DELETE FROM project_git_branchs WHERE 1=1;
DELETE FROM projects WHERE 1=1;

-- Delete any other tables that might exist
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Get all tables in public schema
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename NOT IN (
            'user_access_log', 'task_dependencies', 'subtasks', 'cursor_rules',
            'task_contexts', 'branch_contexts', 'project_contexts', 'global_contexts',
            'agents', 'tasks', 'project_git_branchs', 'projects'
        )
    LOOP
        EXECUTE format('DELETE FROM %I WHERE 1=1', r.tablename);
        RAISE NOTICE 'Cleaned table: %', r.tablename;
    END LOOP;
END $$;

-- ============================================================
-- PHASE 3: RE-ENABLE TRIGGERS & CONSTRAINTS
-- ============================================================

-- Re-enable triggers
SET session_replication_role = 'origin';

-- ============================================================
-- PHASE 4: VERIFY CLEANUP
-- ============================================================

DO $$
DECLARE
    r RECORD;
    total_records INTEGER := 0;
    table_count INTEGER := 0;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '📊 PUBLIC TABLES CLEANUP SUMMARY';
    RAISE NOTICE '============================================================';
    
    FOR r IN 
        SELECT 
            tablename,
            (SELECT COUNT(*) FROM public.tasks WHERE tablename = 'tasks') as count
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I', r.tablename) INTO r.count;
        RAISE NOTICE 'Table: % | Records: %', rpad(r.tablename, 30), r.count;
        total_records := total_records + r.count;
        table_count := table_count + 1;
    END LOOP;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Total tables cleaned: %', table_count;
    RAISE NOTICE 'Total records remaining: %', total_records;
    
    IF total_records = 0 THEN
        RAISE NOTICE '';
        RAISE NOTICE '✅ SUCCESS: All public tables are now empty!';
        RAISE NOTICE '🚀 Database is clean and ready for fresh data';
    ELSE
        RAISE NOTICE '';
        RAISE NOTICE '⚠️  WARNING: Some records remain in tables';
        RAISE NOTICE 'Manual cleanup may be required';
    END IF;
    
    RAISE NOTICE '============================================================';
END $$;

-- ============================================================
-- PHASE 5: RESET SEQUENCES (IF ANY)
-- ============================================================

-- Reset any sequences that might exist
DO $$
DECLARE
    seq RECORD;
BEGIN
    FOR seq IN 
        SELECT sequencename 
        FROM pg_sequences 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE %I RESTART WITH 1', seq.sequencename);
        RAISE NOTICE 'Reset sequence: %', seq.sequencename;
    END LOOP;
END $$;

-- ============================================================
-- PHASE 6: VACUUM TABLES (OPTIONAL - RECLAIM SPACE)
-- ============================================================

-- Vacuum all tables to reclaim space and update statistics
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('VACUUM ANALYZE %I', r.tablename);
    END LOOP;
    RAISE NOTICE 'All tables vacuumed and analyzed';
END $$;

-- ============================================================
-- COMPLETE
-- ============================================================

RAISE NOTICE '';
RAISE NOTICE '🎉 PUBLIC TABLES CLEANUP COMPLETED! 🎉';
RAISE NOTICE '';
RAISE NOTICE '✅ All data deleted from public tables';
RAISE NOTICE '✅ Table structure preserved';
RAISE NOTICE '✅ Ready for fresh data';
RAISE NOTICE '';
RAISE NOTICE 'Next steps:';
RAISE NOTICE '1. Tables are empty but structure intact';
RAISE NOTICE '2. User isolation migration still applies';
RAISE NOTICE '3. Ready for new user registrations';