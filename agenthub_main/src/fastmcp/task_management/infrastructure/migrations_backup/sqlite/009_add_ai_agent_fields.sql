-- Migration: Add AI Agent System Fields to Tasks and Subtasks (SQLite)
-- Date: 2025-09-25
-- Description: Adds AI Agent system prompts and context fields to tasks and subtasks tables
-- SQLite version using TEXT for JSON fields

-- Add missing AI Agent columns to tasks table
ALTER TABLE tasks ADD COLUMN ai_system_prompt TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN ai_request_prompt TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN ai_work_context TEXT DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN ai_completion_criteria TEXT DEFAULT '';
ALTER TABLE tasks ADD COLUMN ai_execution_history TEXT DEFAULT '[]';
ALTER TABLE tasks ADD COLUMN ai_last_execution TIMESTAMP;
ALTER TABLE tasks ADD COLUMN ai_model_preferences TEXT DEFAULT '{}';

-- Add missing AI Agent columns to subtasks table
ALTER TABLE subtasks ADD COLUMN ai_system_prompt TEXT DEFAULT '';
ALTER TABLE subtasks ADD COLUMN ai_request_prompt TEXT DEFAULT '';
ALTER TABLE subtasks ADD COLUMN ai_work_context TEXT DEFAULT '{}';
ALTER TABLE subtasks ADD COLUMN ai_completion_criteria TEXT DEFAULT '';
ALTER TABLE subtasks ADD COLUMN ai_execution_history TEXT DEFAULT '[]';
ALTER TABLE subtasks ADD COLUMN ai_last_execution TIMESTAMP;
ALTER TABLE subtasks ADD COLUMN ai_model_preferences TEXT DEFAULT '{}';

-- Create indexes for performance on AI fields
CREATE INDEX IF NOT EXISTS idx_tasks_ai_last_execution ON tasks(ai_last_execution);
CREATE INDEX IF NOT EXISTS idx_subtasks_ai_last_execution ON subtasks(ai_last_execution);