-- ============================================================
-- SUPABASE TRUNCATE ALL PUBLIC TABLES (FASTEST METHOD)
-- ============================================================
-- Purpose: TRUNCATE all tables in public schema (fastest way to delete all data)
-- Date: 2025-08-19
-- ⚠️ WARNING: This will DELETE ALL DATA instantly!

-- ============================================================
-- TRUNCATE ALL TABLES WITH CASCADE
-- ============================================================

-- This will delete ALL data from ALL tables in public schema
-- CASCADE will handle foreign key dependencies automatically

TRUNCATE TABLE 
    projects,
    project_git_branchs,
    tasks,
    subtasks,
    task_dependencies,
    agents,
    global_contexts,
    project_contexts,
    branch_contexts,
    task_contexts,
    cursor_rules,
    user_access_log
CASCADE;

-- ============================================================
-- VERIFY CLEANUP
-- ============================================================

DO $$
DECLARE
    r RECORD;
    total_count INTEGER := 0;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '🧹 TRUNCATE RESULTS';
    RAISE NOTICE '============================================================';
    
    -- Check each table
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I', r.tablename) INTO total_count;
        IF total_count > 0 THEN
            RAISE NOTICE '❌ Table % still has % records', r.tablename, total_count;
        ELSE
            RAISE NOTICE '✅ Table % is empty', r.tablename;
        END IF;
    END LOOP;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '🎉 ALL PUBLIC TABLES TRUNCATED SUCCESSFULLY! 🎉';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables are now completely empty and ready for fresh data.';
END $$;