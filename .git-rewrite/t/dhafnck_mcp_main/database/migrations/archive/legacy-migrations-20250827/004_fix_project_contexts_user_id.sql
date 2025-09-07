-- Migration: Fix project_contexts user_id column type
-- Description: Ensures project_contexts.user_id is VARCHAR to match the ORM model
-- Date: 2025-08-20
-- Issue: Model defines user_id as String (VARCHAR) but migrations were trying to use UUID

-- ============================================================
-- PHASE 1: Drop existing constraints if they exist
-- ============================================================

-- Drop foreign key constraint if it exists
ALTER TABLE project_contexts DROP CONSTRAINT IF EXISTS fk_project_contexts_user;

-- Drop NOT NULL constraint temporarily
ALTER TABLE project_contexts ALTER COLUMN user_id DROP NOT NULL;

-- ============================================================
-- PHASE 2: Fix the column type
-- ============================================================

-- Check if user_id exists and what type it is
DO $$ 
BEGIN
    -- If column exists as UUID, we need to convert it
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'project_contexts' 
               AND column_name = 'user_id' 
               AND udt_name = 'uuid') THEN
        
        -- Create temporary column
        ALTER TABLE project_contexts ADD COLUMN user_id_temp VARCHAR;
        
        -- Copy data converting UUID to string
        UPDATE project_contexts SET user_id_temp = user_id::text WHERE user_id IS NOT NULL;
        
        -- Drop old column
        ALTER TABLE project_contexts DROP COLUMN user_id;
        
        -- Rename temp column
        ALTER TABLE project_contexts RENAME COLUMN user_id_temp TO user_id;
        
        RAISE NOTICE 'Converted project_contexts.user_id from UUID to VARCHAR';
        
    -- If column doesn't exist at all, add it
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'project_contexts' 
                      AND column_name = 'user_id') THEN
        
        ALTER TABLE project_contexts ADD COLUMN user_id VARCHAR;
        RAISE NOTICE 'Added project_contexts.user_id as VARCHAR';
        
    -- If it already exists as VARCHAR, nothing to do
    ELSE
        RAISE NOTICE 'project_contexts.user_id already exists as VARCHAR';
    END IF;
END $$;

-- ============================================================
-- PHASE 3: Ensure other context tables also use VARCHAR
-- ============================================================

-- Fix branch_contexts.user_id
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'branch_contexts' 
               AND column_name = 'user_id' 
               AND udt_name = 'uuid') THEN
        
        ALTER TABLE branch_contexts ADD COLUMN user_id_temp VARCHAR;
        UPDATE branch_contexts SET user_id_temp = user_id::text WHERE user_id IS NOT NULL;
        ALTER TABLE branch_contexts DROP COLUMN user_id;
        ALTER TABLE branch_contexts RENAME COLUMN user_id_temp TO user_id;
        RAISE NOTICE 'Converted branch_contexts.user_id from UUID to VARCHAR';
        
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'branch_contexts' 
                      AND column_name = 'user_id') THEN
        
        ALTER TABLE branch_contexts ADD COLUMN user_id VARCHAR;
        RAISE NOTICE 'Added branch_contexts.user_id as VARCHAR';
    END IF;
END $$;

-- Fix task_contexts.user_id
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'task_contexts' 
               AND column_name = 'user_id' 
               AND udt_name = 'uuid') THEN
        
        ALTER TABLE task_contexts ADD COLUMN user_id_temp VARCHAR;
        UPDATE task_contexts SET user_id_temp = user_id::text WHERE user_id IS NOT NULL;
        ALTER TABLE task_contexts DROP COLUMN user_id;
        ALTER TABLE task_contexts RENAME COLUMN user_id_temp TO user_id;
        RAISE NOTICE 'Converted task_contexts.user_id from UUID to VARCHAR';
        
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'task_contexts' 
                      AND column_name = 'user_id') THEN
        
        ALTER TABLE task_contexts ADD COLUMN user_id VARCHAR;
        RAISE NOTICE 'Added task_contexts.user_id as VARCHAR';
    END IF;
END $$;

-- Note: global_contexts doesn't have user_id in the model, so we leave it alone

-- ============================================================
-- PHASE 4: Add indexes for performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_project_contexts_user_id ON project_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_branch_contexts_user_id ON branch_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_task_contexts_user_id ON task_contexts(user_id);

-- ============================================================
-- VERIFICATION
-- ============================================================

DO $$
DECLARE
    v_type TEXT;
BEGIN
    -- Verify project_contexts.user_id is VARCHAR
    SELECT data_type INTO v_type
    FROM information_schema.columns 
    WHERE table_name = 'project_contexts' AND column_name = 'user_id';
    
    IF v_type = 'character varying' THEN
        RAISE NOTICE '✅ project_contexts.user_id is correctly set as VARCHAR';
    ELSE
        RAISE EXCEPTION '❌ project_contexts.user_id is % instead of VARCHAR', v_type;
    END IF;
    
    -- Verify branch_contexts.user_id is VARCHAR
    SELECT data_type INTO v_type
    FROM information_schema.columns 
    WHERE table_name = 'branch_contexts' AND column_name = 'user_id';
    
    IF v_type = 'character varying' THEN
        RAISE NOTICE '✅ branch_contexts.user_id is correctly set as VARCHAR';
    ELSE
        RAISE WARNING 'branch_contexts.user_id is % instead of VARCHAR', v_type;
    END IF;
    
    -- Verify task_contexts.user_id is VARCHAR
    SELECT data_type INTO v_type
    FROM information_schema.columns 
    WHERE table_name = 'task_contexts' AND column_name = 'user_id';
    
    IF v_type = 'character varying' THEN
        RAISE NOTICE '✅ task_contexts.user_id is correctly set as VARCHAR';
    ELSE
        RAISE WARNING 'task_contexts.user_id is % instead of VARCHAR', v_type;
    END IF;
    
    RAISE NOTICE '✅ Context tables user_id column fix completed successfully';
END $$;