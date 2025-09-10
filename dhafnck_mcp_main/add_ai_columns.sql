-- Add AI columns to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_request_prompt TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_work_context JSON DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_completion_criteria TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_execution_history JSON DEFAULT '[]';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_last_execution TIMESTAMP;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ai_model_preferences JSON DEFAULT '{}';

-- Add AI columns to task_subtasks table
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT DEFAULT '';
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_request_prompt TEXT DEFAULT '';
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_work_context JSON DEFAULT '{}';
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_completion_criteria TEXT DEFAULT '';
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_execution_history JSON DEFAULT '[]';
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_last_execution TIMESTAMP;
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS ai_model_preferences JSON DEFAULT '{}';