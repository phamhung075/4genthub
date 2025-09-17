-- ============================================================
-- SUPABASE COMPLETE BACKUP SCRIPT
-- ============================================================
-- Purpose: Create complete backup of current Supabase data before cleanup
-- Date: 2025-08-19
-- Usage: Run this BEFORE running the cleanup script

-- ============================================================
-- PHASE 1: CREATE BACKUP SCHEMA
-- ============================================================

CREATE SCHEMA IF NOT EXISTS backup_20250819;

-- ============================================================
-- PHASE 2: BACKUP ALL MAIN TABLES
-- ============================================================

-- Backup tasks table
CREATE TABLE backup_20250819.tasks AS 
SELECT * FROM public.tasks;

-- Backup projects table  
CREATE TABLE backup_20250819.projects AS
SELECT * FROM public.projects;

-- Backup project_git_branchs table
CREATE TABLE backup_20250819.project_git_branchs AS
SELECT * FROM public.project_git_branchs;

-- Backup agents table
CREATE TABLE backup_20250819.agents AS
SELECT * FROM public.agents;

-- Backup context tables
CREATE TABLE backup_20250819.global_contexts AS
SELECT * FROM public.global_contexts;

CREATE TABLE backup_20250819.project_contexts AS
SELECT * FROM public.project_contexts;

CREATE TABLE backup_20250819.branch_contexts AS  
SELECT * FROM public.branch_contexts;

CREATE TABLE backup_20250819.task_contexts AS
SELECT * FROM public.task_contexts;

-- Backup subtasks table
CREATE TABLE backup_20250819.subtasks AS
SELECT * FROM public.subtasks;

-- Backup task_dependencies table
CREATE TABLE backup_20250819.task_dependencies AS
SELECT * FROM public.task_dependencies;

-- Backup cursor_rules table (if exists)
CREATE TABLE backup_20250819.cursor_rules AS
SELECT * FROM public.cursor_rules;

-- ============================================================
-- PHASE 3: BACKUP AUTH DATA (READ-ONLY)
-- ============================================================

-- Backup current auth users (for reference only)
CREATE TABLE backup_20250819.auth_users_snapshot AS
SELECT 
    id,
    email,
    created_at,
    updated_at,
    email_confirmed_at,
    raw_user_meta_data->>'username' as username,
    raw_user_meta_data->>'full_name' as full_name
FROM auth.users;

-- ============================================================
-- PHASE 4: CREATE BACKUP STATISTICS
-- ============================================================

CREATE TABLE backup_20250819.backup_stats AS
SELECT 
    'tasks' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.tasks
UNION ALL
SELECT 
    'projects' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record  
FROM public.projects
UNION ALL
SELECT 
    'project_git_branchs' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.project_git_branchs
UNION ALL
SELECT 
    'agents' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.agents
UNION ALL
SELECT 
    'subtasks' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.subtasks
UNION ALL
SELECT 
    'global_contexts' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.global_contexts
UNION ALL
SELECT 
    'project_contexts' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.project_contexts
UNION ALL
SELECT 
    'branch_contexts' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.branch_contexts
UNION ALL
SELECT 
    'task_contexts' as table_name,
    COUNT(*) as record_count,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM public.task_contexts
UNION ALL
SELECT 
    'task_dependencies' as table_name,
    COUNT(*) as record_count,
    NULL as oldest_record,
    NULL as newest_record
FROM public.task_dependencies;

-- ============================================================
-- PHASE 5: CREATE RESTORE SCRIPT TEMPLATE
-- ============================================================

CREATE TABLE backup_20250819.restore_instructions AS
SELECT 'restore_script' as instruction_type,
'
-- FULL RESTORE SCRIPT (USE ONLY IN EMERGENCY)
-- WARNING: This will overwrite current data

-- 1. Drop existing constraints
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS fk_tasks_user;
ALTER TABLE public.projects DROP CONSTRAINT IF EXISTS fk_projects_user;
-- ... add other constraint drops ...

-- 2. Clear current tables
TRUNCATE public.tasks CASCADE;
TRUNCATE public.projects CASCADE; 
TRUNCATE public.project_git_branchs CASCADE;
TRUNCATE public.agents CASCADE;
TRUNCATE public.global_contexts CASCADE;
TRUNCATE public.project_contexts CASCADE;
TRUNCATE public.branch_contexts CASCADE;
TRUNCATE public.task_contexts CASCADE;
TRUNCATE public.subtasks CASCADE;
TRUNCATE public.task_dependencies CASCADE;

-- 3. Restore data
INSERT INTO public.tasks SELECT * FROM backup_20250819.tasks;
INSERT INTO public.projects SELECT * FROM backup_20250819.projects;
INSERT INTO public.project_git_branchs SELECT * FROM backup_20250819.project_git_branchs;
INSERT INTO public.agents SELECT * FROM backup_20250819.agents;
INSERT INTO public.global_contexts SELECT * FROM backup_20250819.global_contexts;
INSERT INTO public.project_contexts SELECT * FROM backup_20250819.project_contexts;
INSERT INTO public.branch_contexts SELECT * FROM backup_20250819.branch_contexts;
INSERT INTO public.task_contexts SELECT * FROM backup_20250819.task_contexts;
INSERT INTO public.subtasks SELECT * FROM backup_20250819.subtasks;
INSERT INTO public.task_dependencies SELECT * FROM backup_20250819.task_dependencies;

-- 4. Recreate constraints (re-run migration script)
' as restore_sql;

-- ============================================================
-- PHASE 6: VERIFY BACKUP INTEGRITY  
-- ============================================================

DO $$
DECLARE
    v_original_count INTEGER;
    v_backup_count INTEGER;
    v_table_name TEXT;
    v_tables TEXT[] := ARRAY['tasks', 'projects', 'project_git_branchs', 'agents', 
                            'global_contexts', 'project_contexts', 'branch_contexts', 
                            'task_contexts', 'subtasks', 'task_dependencies'];
BEGIN
    RAISE NOTICE 'BACKUP VERIFICATION:';
    
    FOREACH v_table_name IN ARRAY v_tables
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM public.%I', v_table_name) INTO v_original_count;
        EXECUTE format('SELECT COUNT(*) FROM backup_20250819.%I', v_table_name) INTO v_backup_count;
        
        IF v_original_count = v_backup_count THEN
            RAISE NOTICE '✓ %: % records backed up successfully', v_table_name, v_backup_count;
        ELSE
            RAISE WARNING '✗ %: Mismatch! Original: %, Backup: %', v_table_name, v_original_count, v_backup_count;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Backup completed at: %', NOW();
    RAISE NOTICE 'Backup schema: backup_20250819';
END $$;

-- ============================================================
-- BACKUP COMPLETE
-- ============================================================

-- Show final backup summary
SELECT 
    table_name,
    record_count,
    oldest_record,
    newest_record
FROM backup_20250819.backup_stats
ORDER BY table_name;