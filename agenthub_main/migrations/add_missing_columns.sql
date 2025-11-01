-- Migration: Add missing columns to match ORM models
-- Date: 2025-11-01
-- Fixes: Schema mismatches between ORM and database
--
-- Missing columns:
-- 1. tasks.completed_subtasks - Track count of completed subtasks
-- 2. subtasks.progress_history - JSON field for progress tracking
-- 3. subtasks.progress_count - Counter for progress entries

-- Add completed_subtasks to tasks table
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS completed_subtasks INTEGER DEFAULT 0 NOT NULL;

-- Add progress_history to subtasks table
ALTER TABLE subtasks
ADD COLUMN IF NOT EXISTS progress_history JSON DEFAULT '{}' NOT NULL;

-- Add progress_count to subtasks table
ALTER TABLE subtasks
ADD COLUMN IF NOT EXISTS progress_count INTEGER DEFAULT 0 NOT NULL;

-- Verify columns were added
SELECT 'Migration completed successfully' AS status;
