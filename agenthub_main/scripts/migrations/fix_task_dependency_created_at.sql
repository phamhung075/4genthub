-- Fix for task_dependencies.created_at NULL constraint violation
-- Issue: TaskDependency objects created without created_at timestamp
-- Solution: Add database-level DEFAULT to prevent NULL values

-- Add DEFAULT CURRENT_TIMESTAMP to created_at column
ALTER TABLE task_dependencies
ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

-- Verify the change
SELECT column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'task_dependencies' AND column_name = 'created_at';

-- Success message
SELECT '✅ Migration complete: task_dependencies.created_at now has DEFAULT CURRENT_TIMESTAMP' AS status;
