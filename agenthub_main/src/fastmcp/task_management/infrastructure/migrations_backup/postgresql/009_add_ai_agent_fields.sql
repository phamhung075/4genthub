-- Migration: Add AI Agent System Fields to Tasks and Subtasks
-- Date: 2025-09-25
-- Description: Adds AI Agent system prompts and context fields to tasks and subtasks tables
-- These fields are required by the current ORM models for AI task execution

BEGIN TRANSACTION;

-- Add missing AI Agent columns to tasks table
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS ai_request_prompt TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS ai_work_context JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS ai_completion_criteria TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS ai_execution_history JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS ai_last_execution TIMESTAMP,
ADD COLUMN IF NOT EXISTS ai_model_preferences JSONB DEFAULT '{}';

-- Add missing AI Agent columns to subtasks table
ALTER TABLE subtasks
ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS ai_request_prompt TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS ai_work_context JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS ai_completion_criteria TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS ai_execution_history JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS ai_last_execution TIMESTAMP,
ADD COLUMN IF NOT EXISTS ai_model_preferences JSONB DEFAULT '{}';

-- Create indexes for performance on AI fields
CREATE INDEX IF NOT EXISTS idx_tasks_ai_last_execution ON tasks(ai_last_execution);
CREATE INDEX IF NOT EXISTS idx_subtasks_ai_last_execution ON subtasks(ai_last_execution);

-- Add comments for documentation
COMMENT ON COLUMN tasks.ai_system_prompt IS 'System prompt for AI agent to understand task context';
COMMENT ON COLUMN tasks.ai_request_prompt IS 'Specific request prompt for AI to execute';
COMMENT ON COLUMN tasks.ai_work_context IS 'Additional context for AI work (JSON)';
COMMENT ON COLUMN tasks.ai_completion_criteria IS 'Criteria for AI to determine task completion';
COMMENT ON COLUMN tasks.ai_execution_history IS 'History of AI executions (JSON array)';
COMMENT ON COLUMN tasks.ai_last_execution IS 'Last time AI worked on this task';
COMMENT ON COLUMN tasks.ai_model_preferences IS 'AI model preferences (JSON)';

COMMENT ON COLUMN subtasks.ai_system_prompt IS 'System prompt for AI agent to understand subtask context';
COMMENT ON COLUMN subtasks.ai_request_prompt IS 'Specific request prompt for AI to execute';
COMMENT ON COLUMN subtasks.ai_work_context IS 'Additional context for AI work (JSON)';
COMMENT ON COLUMN subtasks.ai_completion_criteria IS 'Criteria for AI to determine subtask completion';
COMMENT ON COLUMN subtasks.ai_execution_history IS 'History of AI executions (JSON array)';
COMMENT ON COLUMN subtasks.ai_last_execution IS 'Last time AI worked on this subtask';
COMMENT ON COLUMN subtasks.ai_model_preferences IS 'AI model preferences (JSON)';

COMMIT;