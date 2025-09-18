-- Fix CASCADE DELETE Constraints Migration
-- This migration fixes the missing CASCADE DELETE constraints that cause orphaned records

-- ================================================================================
-- TASK CONTEXTS - Fix CASCADE DELETE for task_id
-- ================================================================================

-- Drop existing constraint
ALTER TABLE task_contexts
DROP CONSTRAINT IF EXISTS task_contexts_task_id_fkey;

-- Recreate with CASCADE DELETE
ALTER TABLE task_contexts
ADD CONSTRAINT task_contexts_task_id_fkey
FOREIGN KEY (task_id)
REFERENCES tasks(id)
ON DELETE CASCADE;

-- ================================================================================
-- TASK CONTEXTS - Fix CASCADE DELETE for parent_branch_id
-- ================================================================================

-- Drop existing constraint
ALTER TABLE task_contexts
DROP CONSTRAINT IF EXISTS task_contexts_parent_branch_id_fkey;

-- Recreate with CASCADE DELETE
ALTER TABLE task_contexts
ADD CONSTRAINT task_contexts_parent_branch_id_fkey
FOREIGN KEY (parent_branch_id)
REFERENCES project_git_branchs(id)
ON DELETE CASCADE;

-- ================================================================================
-- BRANCH CONTEXTS - Fix CASCADE DELETE for branch_id
-- ================================================================================

-- Drop existing constraint
ALTER TABLE branch_contexts
DROP CONSTRAINT IF EXISTS branch_contexts_branch_id_fkey;

-- Recreate with CASCADE DELETE
ALTER TABLE branch_contexts
ADD CONSTRAINT branch_contexts_branch_id_fkey
FOREIGN KEY (branch_id)
REFERENCES project_git_branchs(id)
ON DELETE CASCADE;

-- ================================================================================
-- BRANCH CONTEXTS - Fix CASCADE DELETE for parent_project_id
-- ================================================================================

-- Drop existing constraint
ALTER TABLE branch_contexts
DROP CONSTRAINT IF EXISTS branch_contexts_parent_project_id_fkey;

-- Recreate with CASCADE DELETE
ALTER TABLE branch_contexts
ADD CONSTRAINT branch_contexts_parent_project_id_fkey
FOREIGN KEY (parent_project_id)
REFERENCES project_contexts(id)
ON DELETE CASCADE;

-- ================================================================================
-- PROJECT CONTEXTS - Fix CASCADE DELETE for parent_global_id
-- ================================================================================

-- Drop existing constraint
ALTER TABLE project_contexts
DROP CONSTRAINT IF EXISTS project_contexts_parent_global_id_fkey;

-- Recreate with CASCADE DELETE
ALTER TABLE project_contexts
ADD CONSTRAINT project_contexts_parent_global_id_fkey
FOREIGN KEY (parent_global_id)
REFERENCES global_contexts(id)
ON DELETE CASCADE;

-- ================================================================================
-- VERIFICATION QUERIES
-- ================================================================================

-- Verify all constraints are now set to CASCADE
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('task_contexts', 'branch_contexts', 'project_contexts')
ORDER BY tc.table_name, kcu.column_name;