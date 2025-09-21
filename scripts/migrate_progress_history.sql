-- Migration script to add progress_history and progress_count columns to tasks table
-- This is a one-way migration with NO rollback support (clean break from old system)

-- Add progress_history column if it doesn't exist
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS progress_history JSON DEFAULT '{}';

-- Add progress_count column if it doesn't exist
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS progress_count INTEGER DEFAULT 0;

-- Migrate existing details data to progress_history format (if details column exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'tasks' AND column_name = 'details') THEN
        UPDATE tasks
        SET progress_history = jsonb_build_object(
            'entry_1', jsonb_build_object(
                'content', CONCAT('=== Progress 1 ===', E'\n', COALESCE(details, 'Initial task creation')),
                'timestamp', COALESCE(updated_at, created_at),
                'progress_number', 1
            )
        ),
        progress_count = 1
        WHERE progress_history = '{}' OR progress_history IS NULL;

        -- Drop the old details column (clean break - no backward compatibility)
        ALTER TABLE tasks DROP COLUMN IF EXISTS details;
    END IF;
END $$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_progress_count ON tasks(progress_count);

-- Verify the migration
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'tasks'
AND column_name IN ('progress_history', 'progress_count', 'details')
ORDER BY ordinal_position;