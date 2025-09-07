-- Migration: Fix missing user_id columns in task relationship tables
-- Description: Adds user_id columns to task_subtasks, task_assignees, and task_labels tables
-- Date: 2025-08-24
-- Issue: Root cause of task persistence issue - missing user_id columns in relationship tables

-- ============================================================
-- PHASE 1: Add user_id columns to relationship tables
-- ============================================================

-- Add user_id to task_subtasks table
ALTER TABLE task_subtasks ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- Add user_id to task_assignees table  
ALTER TABLE task_assignees ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- Add user_id to task_labels table
ALTER TABLE task_labels ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);

-- ============================================================
-- PHASE 2: Backfill existing data from parent tasks
-- ============================================================

-- Backfill task_subtasks.user_id from parent tasks
UPDATE task_subtasks 
SET user_id = (
    SELECT tasks.user_id 
    FROM tasks 
    WHERE tasks.id = task_subtasks.task_id
)
WHERE task_subtasks.user_id IS NULL;

-- Backfill task_assignees.user_id from parent tasks
UPDATE task_assignees 
SET user_id = (
    SELECT tasks.user_id 
    FROM tasks 
    WHERE tasks.id = task_assignees.task_id
)
WHERE task_assignees.user_id IS NULL;

-- Backfill task_labels.user_id from parent tasks
UPDATE task_labels 
SET user_id = (
    SELECT tasks.user_id 
    FROM tasks 
    WHERE tasks.id = task_labels.task_id
)
WHERE task_labels.user_id IS NULL;

-- ============================================================
-- PHASE 3: Set NOT NULL constraints
-- ============================================================

-- Make user_id columns NOT NULL
ALTER TABLE task_subtasks ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE task_assignees ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE task_labels ALTER COLUMN user_id SET NOT NULL;

-- ============================================================
-- PHASE 4: Add foreign key constraints (if auth.users exists)
-- ============================================================

-- Check if we're in a Supabase environment and add foreign key constraints
DO $$ 
BEGIN
    -- Check if we're on Supabase by looking for auth schema
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
        -- Add foreign key constraints to auth.users
        ALTER TABLE task_subtasks ADD CONSTRAINT fk_task_subtasks_user 
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        
        ALTER TABLE task_assignees ADD CONSTRAINT fk_task_assignees_user 
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        
        ALTER TABLE task_labels ADD CONSTRAINT fk_task_labels_user 
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Foreign key constraints added for Supabase environment';
    ELSE
        RAISE NOTICE 'Not on Supabase, skipping foreign key constraints to auth.users';
    END IF;
END $$;

-- ============================================================
-- PHASE 5: Add indexes for performance
-- ============================================================

-- Add indexes for user-based queries
CREATE INDEX IF NOT EXISTS idx_task_subtasks_user_id ON task_subtasks(user_id);
CREATE INDEX IF NOT EXISTS idx_task_subtasks_user_task ON task_subtasks(user_id, task_id);

CREATE INDEX IF NOT EXISTS idx_task_assignees_user_id ON task_assignees(user_id);
CREATE INDEX IF NOT EXISTS idx_task_assignees_user_task ON task_assignees(user_id, task_id);

CREATE INDEX IF NOT EXISTS idx_task_labels_user_id ON task_labels(user_id);
CREATE INDEX IF NOT EXISTS idx_task_labels_user_task ON task_labels(user_id, task_id);

-- ============================================================
-- PHASE 6: Add Row-Level Security Policies (for Supabase)
-- ============================================================

DO $$ 
BEGIN
    -- Check if we're on Supabase by looking for auth schema
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
        -- Enable RLS on relationship tables
        ALTER TABLE task_subtasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_assignees ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_labels ENABLE ROW LEVEL SECURITY;
        
        -- Create policies for task_subtasks
        CREATE POLICY "Users can view own task subtasks" ON task_subtasks
            FOR SELECT USING (auth.uid()::text = user_id::text OR user_id = '00000000-0000-0000-0000-000000000000');
        
        CREATE POLICY "Users can create own task subtasks" ON task_subtasks
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can update own task subtasks" ON task_subtasks
            FOR UPDATE USING (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can delete own task subtasks" ON task_subtasks
            FOR DELETE USING (auth.uid()::text = user_id::text);
        
        -- Create policies for task_assignees
        CREATE POLICY "Users can view own task assignees" ON task_assignees
            FOR SELECT USING (auth.uid()::text = user_id::text OR user_id = '00000000-0000-0000-0000-000000000000');
        
        CREATE POLICY "Users can create own task assignees" ON task_assignees
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can update own task assignees" ON task_assignees
            FOR UPDATE USING (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can delete own task assignees" ON task_assignees
            FOR DELETE USING (auth.uid()::text = user_id::text);
        
        -- Create policies for task_labels
        CREATE POLICY "Users can view own task labels" ON task_labels
            FOR SELECT USING (auth.uid()::text = user_id::text OR user_id = '00000000-0000-0000-0000-000000000000');
        
        CREATE POLICY "Users can create own task labels" ON task_labels
            FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can update own task labels" ON task_labels
            FOR UPDATE USING (auth.uid()::text = user_id::text);
        
        CREATE POLICY "Users can delete own task labels" ON task_labels
            FOR DELETE USING (auth.uid()::text = user_id::text);
        
        RAISE NOTICE 'Row-Level Security policies created for task relationship tables';
    ELSE
        RAISE NOTICE 'Not on Supabase, skipping RLS policies';
    END IF;
END $$;

-- ============================================================
-- VERIFICATION
-- ============================================================

-- Verify all relationship tables have user_id column with NOT NULL constraint
DO $$
DECLARE
    v_tables TEXT[] := ARRAY['task_subtasks', 'task_assignees', 'task_labels'];
    v_table TEXT;
    v_count INTEGER;
BEGIN
    FOREACH v_table IN ARRAY v_tables
    LOOP
        -- Check if user_id column exists
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = v_table AND column_name = 'user_id'
        ) THEN
            RAISE EXCEPTION 'Table % is missing user_id column', v_table;
        END IF;
        
        -- Check if user_id column is NOT NULL
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = v_table 
            AND column_name = 'user_id' 
            AND is_nullable = 'YES'
        ) THEN
            RAISE EXCEPTION 'Table % user_id column is nullable, should be NOT NULL', v_table;
        END IF;
        
        -- Check that no NULL values remain
        EXECUTE format('SELECT COUNT(*) FROM %I WHERE user_id IS NULL', v_table) INTO v_count;
        IF v_count > 0 THEN
            RAISE EXCEPTION 'Table % has % NULL user_id values', v_table, v_count;
        END IF;
        
        RAISE NOTICE 'Table % user_id column verified successfully', v_table;
    END LOOP;
    
    RAISE NOTICE 'User isolation fix migration completed successfully for task relationship tables';
END $$;