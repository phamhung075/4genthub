-- Migration: Add user-based data isolation (Simplified version for Supabase)
-- Description: Adds user_id columns to all main tables for data isolation
-- Date: 2025-08-19

-- ============================================================
-- PHASE 1: Add user_id columns to all tables
-- ============================================================

-- Add user_id to tasks table (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'tasks' AND column_name = 'user_id') THEN
        ALTER TABLE tasks ADD COLUMN user_id UUID;
    END IF;
END $$;

-- Add user_id to projects table (handle existing VARCHAR column)
DO $$ 
BEGIN
    -- Drop if exists as VARCHAR
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'projects' AND column_name = 'user_id' 
               AND data_type = 'character varying') THEN
        ALTER TABLE projects DROP COLUMN user_id;
    END IF;
    -- Add as UUID if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'projects' AND column_name = 'user_id') THEN
        ALTER TABLE projects ADD COLUMN user_id UUID;
    END IF;
END $$;

-- Add user_id to project_git_branchs table
ALTER TABLE project_git_branchs ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to context tables
ALTER TABLE global_contexts ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE project_contexts ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE branch_contexts ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE task_contexts ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to subtasks table
ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to task_dependencies table
ALTER TABLE task_dependencies ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to cursor_rules table
ALTER TABLE cursor_rules ADD COLUMN IF NOT EXISTS user_id UUID;

-- ============================================================
-- PHASE 2: Create system user and backfill data
-- ============================================================

-- Create system user in auth.users (Supabase Auth)
INSERT INTO auth.users (
    id, 
    instance_id,
    aud, 
    role,
    email, 
    encrypted_password,
    email_confirmed_at,
    created_at,
    updated_at,
    is_sso_user
)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    'system@dhafnckmcp.local',
    crypt('system_password_never_used', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    false
) ON CONFLICT (id) DO NOTHING;

-- Drop public.users table if it exists (we're using auth.users)
DROP TABLE IF EXISTS public.users CASCADE;

-- Backfill all existing data with system user ID
UPDATE tasks SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE projects SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE project_git_branchs SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE agents SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE global_contexts SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE project_contexts SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE branch_contexts SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE task_contexts SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE subtasks SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE task_dependencies SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE cursor_rules SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;

-- ============================================================
-- PHASE 3: Make user_id columns NOT NULL
-- ============================================================

ALTER TABLE tasks ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE projects ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE project_git_branchs ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE agents ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE global_contexts ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE project_contexts ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE branch_contexts ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE task_contexts ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE subtasks ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE task_dependencies ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE cursor_rules ALTER COLUMN user_id SET NOT NULL;

-- ============================================================
-- PHASE 4: Add indexes for performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_project_git_branchs_user_id ON project_git_branchs(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_global_contexts_user_id ON global_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_project_contexts_user_id ON project_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_branch_contexts_user_id ON branch_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_task_contexts_user_id ON task_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_user_id ON subtasks(user_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_user_id ON task_dependencies(user_id);
CREATE INDEX IF NOT EXISTS idx_cursor_rules_user_id ON cursor_rules(user_id);

-- ============================================================
-- PHASE 5: Add foreign key constraints
-- ============================================================

ALTER TABLE tasks ADD CONSTRAINT fk_tasks_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE projects ADD CONSTRAINT fk_projects_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE project_git_branchs ADD CONSTRAINT fk_project_git_branchs_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE agents ADD CONSTRAINT fk_agents_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE global_contexts ADD CONSTRAINT fk_global_contexts_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE project_contexts ADD CONSTRAINT fk_project_contexts_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE branch_contexts ADD CONSTRAINT fk_branch_contexts_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE task_contexts ADD CONSTRAINT fk_task_contexts_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE subtasks ADD CONSTRAINT fk_subtasks_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE task_dependencies ADD CONSTRAINT fk_task_dependencies_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE cursor_rules ADD CONSTRAINT fk_cursor_rules_user 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- ============================================================
-- PHASE 6: Create user_access_log table
-- ============================================================

CREATE TABLE IF NOT EXISTS user_access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    operation VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_access_log_user ON user_access_log(user_id, created_at DESC);
CREATE INDEX idx_user_access_log_entity ON user_access_log(entity_type, entity_id);

-- ============================================================
-- SUCCESS MESSAGE
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE 'User isolation migration completed successfully!';
END $$;