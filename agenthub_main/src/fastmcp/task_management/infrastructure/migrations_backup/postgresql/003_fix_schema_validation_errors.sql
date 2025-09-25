-- Migration: Fix Database Schema Validation Errors
-- Date: 2025-08-26
-- Description: Fixes schema mismatches between model definitions and actual database structure
-- Target: PostgreSQL (Supabase)

BEGIN TRANSACTION;

-- Create migration tracking table
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO migration_history (migration_name) 
VALUES ('003_fix_schema_validation_errors') 
ON CONFLICT (migration_name) DO NOTHING;

-- ==========================================
-- 1. Fix ContextDelegation Table
-- ==========================================

-- Add missing columns to context_delegations table
ALTER TABLE context_delegations 
ADD COLUMN IF NOT EXISTS auto_delegated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS delegated_data JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS delegation_reason VARCHAR DEFAULT '',
ADD COLUMN IF NOT EXISTS source_level VARCHAR(50) DEFAULT '',
ADD COLUMN IF NOT EXISTS target_level VARCHAR(50) DEFAULT '',
ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(50) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION DEFAULT NULL;

-- Update source_level and target_level based on existing source_type and target_type
UPDATE context_delegations 
SET 
    source_level = COALESCE(source_type, 'task'),
    target_level = COALESCE(target_type, 'branch')
WHERE source_level = '' OR target_level = '';

-- Update delegated_data from existing delegation_data
UPDATE context_delegations 
SET delegated_data = COALESCE(delegation_data, '{}');

-- Fix type mismatches - Convert VARCHAR ids to UUID where needed
-- Note: The database already has UUID types, but models expect STRING, so we align with the database

-- Drop old columns that are not in the model (keep for data migration)
-- We'll keep the extra columns for now and handle them in cleanup
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS source_type;
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS target_type;
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS status;
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS error_message;

-- Add constraints (use DO blocks for conditional constraint creation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'chk_source_level' AND table_name = 'context_delegations'
    ) THEN
        ALTER TABLE context_delegations 
        ADD CONSTRAINT chk_source_level 
        CHECK (source_level IN ('task', 'branch', 'project', 'global'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'chk_target_level' AND table_name = 'context_delegations'
    ) THEN
        ALTER TABLE context_delegations 
        ADD CONSTRAINT chk_target_level 
        CHECK (target_level IN ('task', 'branch', 'project', 'global'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'chk_trigger_type' AND table_name = 'context_delegations'
    ) THEN
        ALTER TABLE context_delegations 
        ADD CONSTRAINT chk_trigger_type 
        CHECK (trigger_type IN ('manual', 'auto_pattern', 'auto_threshold'));
    END IF;
END $$;

-- Create indexes for context_delegations (will create processed index later)
CREATE INDEX IF NOT EXISTS idx_delegation_source ON context_delegations (source_level, source_id);
CREATE INDEX IF NOT EXISTS idx_delegation_target ON context_delegations (target_level, target_id);

-- ==========================================
-- 2. Fix Template Table
-- ==========================================

-- Add missing columns to templates table
ALTER TABLE templates 
ADD COLUMN IF NOT EXISTS category VARCHAR DEFAULT 'general',
ADD COLUMN IF NOT EXISTS content JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS created_by VARCHAR DEFAULT 'system',
ADD COLUMN IF NOT EXISTS name VARCHAR DEFAULT '',
ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS type VARCHAR DEFAULT 'task',
ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0;

-- Migrate existing data to new structure
UPDATE templates 
SET 
    name = COALESCE(template_name, 'Untitled Template'),
    content = COALESCE(template_content::jsonb, '{}'),
    type = COALESCE(template_type, 'task')
WHERE name = '' OR name IS NULL;

-- Set NOT NULL constraints after data migration
ALTER TABLE templates ALTER COLUMN name SET NOT NULL;
ALTER TABLE templates ALTER COLUMN type SET NOT NULL;

-- Create indexes for templates
CREATE INDEX IF NOT EXISTS idx_template_type ON templates (type);
CREATE INDEX IF NOT EXISTS idx_template_category ON templates (category);

-- ==========================================
-- 3. Fix Agent Table Type Mismatches
-- ==========================================

-- The Agent table has id and user_id as UUID in database but model expects VARCHAR
-- Since database has UUID and this is more robust, we'll keep UUID
-- The SQLAlchemy model should be updated to match

-- Remove the extra 'role' column that's not in the model
-- ALTER TABLE agents DROP COLUMN IF EXISTS role;

-- ==========================================
-- 4. Add Missing Foreign Key Constraints
-- ==========================================

-- Add foreign key constraint for BranchContext.branch_id
-- First check if the constraint doesn't already exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_branch_contexts_branch_id'
        AND table_name = 'branch_contexts'
    ) THEN
        ALTER TABLE branch_contexts 
        ADD CONSTRAINT fk_branch_contexts_branch_id 
        FOREIGN KEY (branch_id) REFERENCES project_git_branchs(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- ==========================================
-- 5. Add processed and processed_by columns to context_delegations if missing
-- ==========================================
ALTER TABLE context_delegations 
ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS processed_by VARCHAR DEFAULT NULL,
ADD COLUMN IF NOT EXISTS rejected_reason VARCHAR DEFAULT NULL;

-- Now create the processed index after the column exists
CREATE INDEX IF NOT EXISTS idx_delegation_processed ON context_delegations (processed);

-- ==========================================
-- 6. Create additional indexes for performance
-- ==========================================

-- Context inheritance cache indexes (use correct column names)
CREATE INDEX IF NOT EXISTS idx_cache_type ON context_inheritance_cache (context_type);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON context_inheritance_cache (expires_at);

-- Task indexes (may already exist)
CREATE INDEX IF NOT EXISTS idx_task_branch ON tasks (git_branch_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_task_priority ON tasks (priority);
CREATE INDEX IF NOT EXISTS idx_task_created ON tasks (created_at);

-- Subtask indexes
CREATE INDEX IF NOT EXISTS idx_subtask_task ON task_subtasks (task_id);
CREATE INDEX IF NOT EXISTS idx_subtask_status ON task_subtasks (status);

-- Agent indexes
CREATE INDEX IF NOT EXISTS idx_agent_status ON agents (status);
CREATE INDEX IF NOT EXISTS idx_agent_availability ON agents (availability_score);

-- Task assignee indexes
CREATE INDEX IF NOT EXISTS idx_assignee_task ON task_assignees (task_id);
CREATE INDEX IF NOT EXISTS idx_assignee_id ON task_assignees (assignee_id);

-- Task label indexes
CREATE INDEX IF NOT EXISTS idx_task_label_task ON task_labels (task_id);
CREATE INDEX IF NOT EXISTS idx_task_label_label ON task_labels (label_id);

-- ==========================================
-- 7. Data Cleanup and Validation
-- ==========================================

-- Ensure all required fields have values
UPDATE context_delegations 
SET 
    delegation_reason = 'Migration: Auto-filled missing reason'
WHERE delegation_reason = '' OR delegation_reason IS NULL;

UPDATE context_delegations 
SET 
    trigger_type = 'manual'
WHERE trigger_type = '' OR trigger_type IS NULL;

-- Mark migration as completed
INSERT INTO migration_history (migration_name, applied_at) 
VALUES ('003_fix_schema_validation_errors_completed', CURRENT_TIMESTAMP)
ON CONFLICT (migration_name) DO NOTHING;

COMMIT;

-- ==========================================
-- Notes for manual cleanup (run separately if needed):
-- ==========================================
-- 
-- To remove the extra columns that are not in the model:
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS source_type;
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS target_type;
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS status;
-- ALTER TABLE context_delegations DROP COLUMN IF EXISTS error_message;
-- ALTER TABLE agents DROP COLUMN IF EXISTS role;
-- 
-- To rename template columns to match model:
-- ALTER TABLE templates RENAME COLUMN template_name TO name;
-- ALTER TABLE templates RENAME COLUMN template_content TO content; 
-- ALTER TABLE templates RENAME COLUMN template_type TO type;