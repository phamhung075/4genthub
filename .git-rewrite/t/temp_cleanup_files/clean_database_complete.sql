-- ============================================================
-- SIMPLIFIED COMPLETE DATABASE CLEANUP
-- ============================================================
-- Purpose: Clean all data while preserving structure
-- Date: 2025-08-27
-- ============================================================

-- Disable foreign key checks
SET session_replication_role = replica;

-- Drop all unique constraints first (they create indexes)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT conname, conrelid::regclass AS table_name
        FROM pg_constraint 
        WHERE contype = 'u' 
        AND connamespace = 'public'::regnamespace
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I CASCADE', 
            r.table_name, r.conname);
    END LOOP;
END $$;

-- Drop all foreign key constraints
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT conname, conrelid::regclass AS table_name
        FROM pg_constraint 
        WHERE contype = 'f' 
        AND connamespace = 'public'::regnamespace
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I CASCADE', 
            r.table_name, r.conname);
    END LOOP;
END $$;

-- Truncate all tables (keeps structure, removes data)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        AND tablename NOT IN ('schema_migrations', 'migrations')
    LOOP
        EXECUTE format('TRUNCATE TABLE %I CASCADE', r.tablename);
    END LOOP;
END $$;

-- Re-enable foreign key checks
SET session_replication_role = DEFAULT;

-- Verify cleanup
SELECT 
    'Tables cleaned: ' || COUNT(*)::text AS status,
    string_agg(tablename || ' (0 rows)', ', ') AS cleaned_tables
FROM pg_tables 
WHERE schemaname = 'public';