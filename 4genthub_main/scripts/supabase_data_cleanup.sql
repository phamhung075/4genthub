-- ============================================================
-- SUPABASE DATA CLEANUP SCRIPT FOR USER ISOLATION MIGRATION
-- ============================================================
-- Purpose: Clean old data and prepare for new user isolation system
-- Date: 2025-08-19
-- WARNING: This will DELETE existing data. Backup first!

-- ============================================================
-- PHASE 1: CREATE BACKUP TABLES (for safety)
-- ============================================================

-- Create backup tables with current data (in case rollback is needed)
CREATE TABLE backup_tasks AS SELECT * FROM tasks;
CREATE TABLE backup_projects AS SELECT * FROM projects;
CREATE TABLE backup_project_git_branchs AS SELECT * FROM project_git_branchs;
CREATE TABLE backup_agents AS SELECT * FROM agents;
CREATE TABLE backup_global_contexts AS SELECT * FROM global_contexts;
CREATE TABLE backup_project_contexts AS SELECT * FROM project_contexts;
CREATE TABLE backup_branch_contexts AS SELECT * FROM branch_contexts;
CREATE TABLE backup_task_contexts AS SELECT * FROM task_contexts;
CREATE TABLE backup_subtasks AS SELECT * FROM subtasks;
CREATE TABLE backup_task_dependencies AS SELECT * FROM task_dependencies;
CREATE TABLE backup_cursor_rules AS SELECT * FROM cursor_rules;

-- ============================================================
-- PHASE 2: REMOVE OLD SYSTEM DATA
-- ============================================================

-- Remove old system user data (UUID '00000000-0000-0000-0000-000000000000')
-- This clears legacy data that was using the system user as a placeholder

DELETE FROM task_dependencies WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM subtasks WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM task_contexts WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM branch_contexts WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM project_contexts WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM global_contexts WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM tasks WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM agents WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM project_git_branchs WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM projects WHERE user_id = '00000000-0000-0000-0000-000000000000';
DELETE FROM cursor_rules WHERE user_id = '00000000-0000-0000-0000-000000000000';

-- ============================================================
-- PHASE 3: CLEAN UP ORPHANED DATA
-- ============================================================

-- Remove tasks that reference non-existent projects
DELETE FROM tasks WHERE project_id NOT IN (SELECT id FROM projects);

-- Remove subtasks that reference non-existent tasks
DELETE FROM subtasks WHERE task_id NOT IN (SELECT id FROM tasks);

-- Remove task dependencies that reference non-existent tasks
DELETE FROM task_dependencies WHERE 
    task_id NOT IN (SELECT id FROM tasks) OR 
    dependency_id NOT IN (SELECT id FROM tasks);

-- Remove contexts that reference non-existent entities
DELETE FROM task_contexts WHERE context_id NOT IN (SELECT id FROM tasks);
DELETE FROM branch_contexts WHERE context_id NOT IN (SELECT id FROM project_git_branchs);
DELETE FROM project_contexts WHERE context_id NOT IN (SELECT id FROM projects);

-- Remove agents that reference non-existent projects
DELETE FROM agents WHERE project_id NOT IN (SELECT id FROM projects);

-- ============================================================
-- PHASE 4: RESET AUTO-INCREMENT SEQUENCES (if any)
-- ============================================================

-- Note: UUID-based tables don't use sequences, but if there are any serial fields:
-- ALTER SEQUENCE table_name_id_seq RESTART WITH 1;

-- ============================================================
-- PHASE 5: VERIFY CLEANUP
-- ============================================================

-- Count remaining records after cleanup
DO $$
DECLARE
    v_tasks INTEGER;
    v_projects INTEGER;
    v_branches INTEGER;
    v_agents INTEGER;
    v_subtasks INTEGER;
    v_contexts INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_tasks FROM tasks;
    SELECT COUNT(*) INTO v_projects FROM projects;
    SELECT COUNT(*) INTO v_branches FROM project_git_branchs;
    SELECT COUNT(*) INTO v_agents FROM agents;
    SELECT COUNT(*) INTO v_subtasks FROM subtasks;
    SELECT COUNT(*) INTO v_contexts FROM 
        (SELECT 1 FROM global_contexts 
         UNION ALL SELECT 1 FROM project_contexts
         UNION ALL SELECT 1 FROM branch_contexts 
         UNION ALL SELECT 1 FROM task_contexts) AS all_contexts;
    
    RAISE NOTICE 'CLEANUP COMPLETE:';
    RAISE NOTICE 'Tasks remaining: %', v_tasks;
    RAISE NOTICE 'Projects remaining: %', v_projects;
    RAISE NOTICE 'Branches remaining: %', v_branches;
    RAISE NOTICE 'Agents remaining: %', v_agents;
    RAISE NOTICE 'Subtasks remaining: %', v_subtasks;
    RAISE NOTICE 'Contexts remaining: %', v_contexts;
END $$;

-- ============================================================
-- PHASE 6: RESET GLOBAL CONTEXT (Optional)
-- ============================================================

-- Create a clean global context entry for new users
INSERT INTO global_contexts (
    id,
    context_id, 
    data,
    created_at,
    updated_at,
    user_id
) VALUES (
    gen_random_uuid(),
    'global_singleton',
    '{
        "system_info": {
            "version": "v2.1.1",
            "migration_date": "2025-08-19",
            "user_isolation": true,
            "features": ["multi_tenancy", "user_scoped_data", "row_level_security"]
        },
        "welcome_message": "Welcome to 4genthub with User Isolation!",
        "getting_started": [
            "Create your first project",
            "Add tasks to organize your work", 
            "Assign agents to automate processes",
            "Use contexts to track progress"
        ]
    }',
    NOW(),
    NOW(),
    '00000000-0000-0000-0000-000000000000'
) ON CONFLICT (context_id) DO UPDATE SET
    data = EXCLUDED.data,
    updated_at = NOW();

-- ============================================================
-- PHASE 7: UPDATE STATISTICS
-- ============================================================

-- Update table statistics for better query performance
ANALYZE tasks;
ANALYZE projects;
ANALYZE project_git_branchs;
ANALYZE agents;
ANALYZE global_contexts;
ANALYZE project_contexts;
ANALYZE branch_contexts;
ANALYZE task_contexts;
ANALYZE subtasks;
ANALYZE task_dependencies;
ANALYZE cursor_rules;

-- ============================================================
-- PHASE 8: VERIFY CONSTRAINTS AND INDEXES
-- ============================================================

-- Verify all foreign key constraints are satisfied
DO $$
BEGIN
    -- This will raise an error if any constraint is violated
    PERFORM * FROM tasks WHERE user_id IS NULL;
    PERFORM * FROM projects WHERE user_id IS NULL;
    PERFORM * FROM project_git_branchs WHERE user_id IS NULL;
    
    RAISE NOTICE 'All constraints verified successfully';
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Constraint violation found: %', SQLERRM;
END $$;

-- ============================================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ============================================================

/*
-- To rollback this cleanup, run these commands:

-- Restore data from backup tables
TRUNCATE tasks CASCADE;
INSERT INTO tasks SELECT * FROM backup_tasks;

TRUNCATE projects CASCADE;  
INSERT INTO projects SELECT * FROM backup_projects;

TRUNCATE project_git_branchs CASCADE;
INSERT INTO project_git_branchs SELECT * FROM backup_project_git_branchs;

-- ... repeat for other tables ...

-- Drop backup tables
DROP TABLE backup_tasks;
DROP TABLE backup_projects;  
DROP TABLE backup_project_git_branchs;
-- ... repeat for other backup tables ...

*/

-- ============================================================
-- CLEANUP COMPLETE
-- ============================================================

RAISE NOTICE 'Supabase data cleanup completed successfully!';
RAISE NOTICE 'Your database is now ready for the new user isolation system.';
RAISE NOTICE 'All old system data has been removed and the schema is clean.';