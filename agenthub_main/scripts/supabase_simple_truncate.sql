-- ============================================================
-- SIMPLE TRUNCATE ALL PUBLIC TABLES
-- ============================================================
-- Purpose: Clean all data from public tables
-- Date: 2025-08-19

-- Truncate all tables (CASCADE handles foreign keys)
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

-- Verify all tables are empty
SELECT 
    tablename as "Table Name",
    (SELECT COUNT(*) FROM projects WHERE tablename = 'projects') as "Record Count"
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;