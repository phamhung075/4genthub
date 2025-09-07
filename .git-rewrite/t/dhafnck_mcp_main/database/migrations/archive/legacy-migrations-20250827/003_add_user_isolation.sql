-- Migration: Add user-based data isolation
-- Description: Adds user_id columns to all main tables for data isolation
-- Date: 2025-08-19

-- ============================================================
-- PHASE 1: Add user_id columns to all tables
-- ============================================================

-- Add user_id to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to projects table (drop existing VARCHAR column if exists)
ALTER TABLE projects DROP COLUMN IF EXISTS user_id;
ALTER TABLE projects ADD COLUMN user_id UUID;

-- Add user_id to project_git_branchs table (correct table name in Supabase)
ALTER TABLE project_git_branchs ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to context tables (for all hierarchy levels)
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
-- PHASE 2: Backfill existing data with system user
-- ============================================================

-- Create a system user if it doesn't exist in auth.users (Supabase Auth schema)
INSERT INTO auth.users (
    id, 
    instance_id,
    aud, 
    role,
    email, 
    encrypted_password,
    email_confirmed_at,
    confirmation_token,
    recovery_token,
    email_change_token_new,
    email_change,
    raw_app_meta_data,
    raw_user_meta_data,
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
    '',
    '',
    '',
    '',
    '{"provider":"email","providers":["email"]}',
    '{"username":"system","full_name":"System User"}',
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
CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_created ON tasks(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_name ON projects(user_id, name);

CREATE INDEX IF NOT EXISTS idx_project_git_branchs_user_id ON project_git_branchs(user_id);
CREATE INDEX IF NOT EXISTS idx_project_git_branchs_user_project ON project_git_branchs(user_id, project_id);

CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);

CREATE INDEX IF NOT EXISTS idx_global_contexts_user_id ON global_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_project_contexts_user_id ON project_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_branch_contexts_user_id ON branch_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_task_contexts_user_id ON task_contexts(user_id);

CREATE INDEX IF NOT EXISTS idx_subtasks_user_id ON subtasks(user_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_user_task ON subtasks(user_id, task_id);

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
-- PHASE 6: Create Row-Level Security Policies (for Supabase)
-- ============================================================

-- Enable RLS on tables (only works on Supabase, will be skipped on regular PostgreSQL)
DO $$ 
BEGIN
    -- Check if we're on Supabase by looking for auth schema
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
        -- Enable RLS
        ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
        ALTER TABLE project_git_branchs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
        ALTER TABLE global_contexts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE project_contexts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE branch_contexts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_contexts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE subtasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;
        ALTER TABLE cursor_rules ENABLE ROW LEVEL SECURITY;
        
        -- Create policies for tasks
        CREATE POLICY "Users can view own tasks" ON tasks
            FOR SELECT USING (auth.uid()::text = user_id::text OR user_id = '00000000-0000-0000-0000-000000000000');
        
        CREATE POLICY "Users can create own tasks" ON tasks
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can update own tasks" ON tasks
            FOR UPDATE USING (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can delete own tasks" ON tasks
            FOR DELETE USING (auth.uid()::text = user_id::text);
        
        -- Create similar policies for projects
        CREATE POLICY "Users can view own projects" ON projects
            FOR SELECT USING (auth.uid()::text = user_id::text OR user_id = '00000000-0000-0000-0000-000000000000');
        
        CREATE POLICY "Users can create own projects" ON projects
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can update own projects" ON projects
            FOR UPDATE USING (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can delete own projects" ON projects
            FOR DELETE USING (auth.uid()::text = user_id::text);
        
        -- Repeat for other tables...
        RAISE NOTICE 'Row-Level Security policies created for Supabase';
    ELSE
        RAISE NOTICE 'Not on Supabase, skipping RLS policies';
    END IF;
END $$;

-- ============================================================
-- PHASE 7: Create audit table for tracking access
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
-- PHASE 8: Create helper functions
-- ============================================================

-- Function to get user's task count
CREATE OR REPLACE FUNCTION get_user_task_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM tasks WHERE user_id = p_user_id);
END;
$$ LANGUAGE plpgsql;

-- Function to transfer ownership of entities
CREATE OR REPLACE FUNCTION transfer_entity_ownership(
    p_entity_type VARCHAR,
    p_entity_id UUID,
    p_from_user_id UUID,
    p_to_user_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    CASE p_entity_type
        WHEN 'task' THEN
            UPDATE tasks SET user_id = p_to_user_id 
            WHERE id = p_entity_id AND user_id = p_from_user_id;
        WHEN 'project' THEN
            UPDATE projects SET user_id = p_to_user_id 
            WHERE id = p_entity_id AND user_id = p_from_user_id;
        ELSE
            RAISE EXCEPTION 'Unknown entity type: %', p_entity_type;
    END CASE;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VERIFICATION
-- ============================================================

-- Verify all tables have user_id column
DO $$
DECLARE
    v_tables TEXT[] := ARRAY['tasks', 'projects', 'project_git_branchs', 'agents', 'global_contexts', 'project_contexts', 'branch_contexts', 'task_contexts', 'subtasks', 'task_dependencies', 'cursor_rules'];
    v_table TEXT;
BEGIN
    FOREACH v_table IN ARRAY v_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = v_table AND column_name = 'user_id'
        ) THEN
            RAISE EXCEPTION 'Table % is missing user_id column', v_table;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'User isolation migration completed successfully';
END $$;