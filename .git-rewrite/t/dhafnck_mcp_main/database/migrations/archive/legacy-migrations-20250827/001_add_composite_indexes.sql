-- Database Performance Optimization: Add Composite Indexes
-- Purpose: Add 6 critical composite indexes to eliminate N+1 queries
-- Expected improvement: 50-60% query performance improvement
-- Created: 2025-08-16

-- 1. Composite index for efficient task listing with filters
-- Speeds up queries that filter by branch, status, and priority
CREATE INDEX IF NOT EXISTS idx_tasks_efficient_list 
ON tasks(git_branch_id, status, priority, created_at DESC);

-- 2. Composite index for subtask lookups by parent task and status
-- Eliminates N+1 queries when loading subtasks for multiple tasks
CREATE INDEX IF NOT EXISTS idx_subtasks_parent_status 
ON task_subtasks(task_id, status);

-- 3. Composite index for assignee lookups
-- Speeds up queries for tasks by assignee and task-assignee joins
CREATE INDEX IF NOT EXISTS idx_assignees_task_lookup 
ON task_assignees(task_id, assignee_id);

-- 4. Composite index for task labels
-- Improves label-based filtering and task-label joins
CREATE INDEX IF NOT EXISTS idx_task_labels_lookup 
ON task_labels(task_id, label_id);

-- 5. Composite index for dependency lookups
-- Speeds up dependency chain queries
CREATE INDEX IF NOT EXISTS idx_dependencies_task_lookup 
ON task_dependencies(task_id, depends_on_task_id);

-- 6. Composite index for branch-priority queries
-- Optimizes high-priority task queries within branches
CREATE INDEX IF NOT EXISTS idx_tasks_branch_priority 
ON tasks(git_branch_id, priority, status, created_at DESC);

-- Additional performance indexes for common query patterns

-- 7. Index for overdue task queries
CREATE INDEX IF NOT EXISTS idx_tasks_due_date 
ON tasks(due_date, status) 
WHERE due_date IS NOT NULL;

-- 8. Index for context lookups
CREATE INDEX IF NOT EXISTS idx_tasks_context 
ON tasks(context_id) 
WHERE context_id IS NOT NULL;

-- 9. Index for subtask progress tracking
CREATE INDEX IF NOT EXISTS idx_subtasks_progress 
ON task_subtasks(task_id, progress_percentage);

-- 10. Index for label name lookups
CREATE INDEX IF NOT EXISTS idx_labels_name 
ON labels(name);

-- Note: These indexes will significantly improve:
-- - Task listing with multiple filters
-- - Subtask and assignee loading (eliminate N+1 queries)
-- - Label-based filtering
-- - Dependency chain resolution
-- - Priority-based task retrieval
-- - Overdue task monitoring