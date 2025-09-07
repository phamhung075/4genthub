-- Migration: Add Missing Foreign Key Constraints for TaskContext
-- Date: 2025-08-26
-- Description: Adds foreign key constraints for task_id and parent_branch_id in task_contexts table
-- Target: PostgreSQL (Supabase)
-- Related Issue: Foreign key constraints defined in SQLAlchemy models but missing from database

BEGIN TRANSACTION;

-- Create migration tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Record migration start
INSERT INTO migration_history (migration_name) 
VALUES ('005_add_missing_foreign_keys') 
ON CONFLICT (migration_name) DO NOTHING;

-- ==========================================
-- 1. Analyze current constraint status
-- ==========================================

-- Check existing foreign key constraints on task_contexts table
DO $$
DECLARE
    task_id_fk_exists BOOLEAN := FALSE;
    parent_branch_id_fk_exists BOOLEAN := FALSE;
    orphan_task_records INTEGER := 0;
    orphan_branch_records INTEGER := 0;
BEGIN
    -- Check if task_id foreign key constraint exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'task_contexts' 
        AND tc.constraint_type = 'FOREIGN KEY'
        AND ccu.column_name = 'task_id'
        AND ccu.table_name = 'task_contexts'
    ) INTO task_id_fk_exists;
    
    -- Check if parent_branch_id foreign key constraint exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'task_contexts' 
        AND tc.constraint_type = 'FOREIGN KEY'
        AND ccu.column_name = 'parent_branch_id'
        AND ccu.table_name = 'task_contexts'
    ) INTO parent_branch_id_fk_exists;
    
    RAISE NOTICE 'Current Foreign Key Status:';
    RAISE NOTICE '- task_id FK exists: %', task_id_fk_exists;
    RAISE NOTICE '- parent_branch_id FK exists: %', parent_branch_id_fk_exists;
END $$;

-- ==========================================
-- 2. Data integrity check and cleanup
-- ==========================================

-- Check for orphaned records that would violate foreign key constraints
DO $$
DECLARE
    orphan_task_count INTEGER := 0;
    orphan_branch_count INTEGER := 0;
    cleanup_needed BOOLEAN := FALSE;
BEGIN
    -- Check for task_contexts with invalid task_id references
    SELECT COUNT(*) INTO orphan_task_count
    FROM task_contexts tc
    WHERE tc.task_id IS NOT NULL 
    AND NOT EXISTS (
        SELECT 1 FROM tasks t 
        WHERE t.id = tc.task_id
    );
    
    -- Check for task_contexts with invalid parent_branch_id references
    SELECT COUNT(*) INTO orphan_branch_count
    FROM task_contexts tc
    WHERE tc.parent_branch_id IS NOT NULL 
    AND NOT EXISTS (
        SELECT 1 FROM project_git_branchs pgb 
        WHERE pgb.id = tc.parent_branch_id
    );
    
    RAISE NOTICE 'Data Integrity Check Results:';
    RAISE NOTICE '- Orphaned task_id references: %', orphan_task_count;
    RAISE NOTICE '- Orphaned parent_branch_id references: %', orphan_branch_count;
    
    IF orphan_task_count > 0 OR orphan_branch_count > 0 THEN
        cleanup_needed := TRUE;
        RAISE NOTICE 'Data cleanup required before adding foreign key constraints';
    ELSE
        RAISE NOTICE 'Data integrity verified - safe to add foreign key constraints';
    END IF;
END $$;

-- ==========================================
-- 3. Clean up orphaned records (if any)
-- ==========================================

-- Remove task_contexts with invalid task_id references
-- This prevents foreign key constraint violations
DELETE FROM task_contexts 
WHERE task_id IS NOT NULL 
AND NOT EXISTS (
    SELECT 1 FROM tasks t 
    WHERE t.id = task_contexts.task_id
);

-- Remove task_contexts with invalid parent_branch_id references
-- This prevents foreign key constraint violations
DELETE FROM task_contexts 
WHERE parent_branch_id IS NOT NULL 
AND NOT EXISTS (
    SELECT 1 FROM project_git_branchs pgb 
    WHERE pgb.id = task_contexts.parent_branch_id
);

-- Log cleanup results
DO $$
DECLARE
    final_orphan_task_count INTEGER := 0;
    final_orphan_branch_count INTEGER := 0;
BEGIN
    -- Verify cleanup was successful
    SELECT COUNT(*) INTO final_orphan_task_count
    FROM task_contexts tc
    WHERE tc.task_id IS NOT NULL 
    AND NOT EXISTS (
        SELECT 1 FROM tasks t 
        WHERE t.id = tc.task_id
    );
    
    SELECT COUNT(*) INTO final_orphan_branch_count
    FROM task_contexts tc
    WHERE tc.parent_branch_id IS NOT NULL 
    AND NOT EXISTS (
        SELECT 1 FROM project_git_branchs pgb 
        WHERE pgb.id = tc.parent_branch_id
    );
    
    RAISE NOTICE 'Post-cleanup Verification:';
    RAISE NOTICE '- Remaining orphaned task_id references: %', final_orphan_task_count;
    RAISE NOTICE '- Remaining orphaned parent_branch_id references: %', final_orphan_branch_count;
    
    IF final_orphan_task_count = 0 AND final_orphan_branch_count = 0 THEN
        RAISE NOTICE 'Data cleanup successful - ready to add constraints';
    ELSE
        RAISE EXCEPTION 'Data cleanup failed - cannot proceed with foreign key creation';
    END IF;
END $$;

-- ==========================================
-- 4. Add Foreign Key Constraints
-- ==========================================

-- Add foreign key constraint for task_contexts.task_id -> tasks.id
DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'task_contexts' 
        AND tc.constraint_type = 'FOREIGN KEY'
        AND ccu.column_name = 'task_id'
        AND ccu.table_name = 'task_contexts'
    ) THEN
        ALTER TABLE task_contexts
        ADD CONSTRAINT fk_task_contexts_task_id 
        FOREIGN KEY (task_id) 
        REFERENCES tasks(id) 
        ON DELETE CASCADE;
        
        RAISE NOTICE 'Added foreign key constraint: task_contexts.task_id -> tasks.id';
    ELSE
        RAISE NOTICE 'Foreign key constraint for task_id already exists';
    END IF;
END $$;

-- Add foreign key constraint for task_contexts.parent_branch_id -> project_git_branchs.id
DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'task_contexts' 
        AND tc.constraint_type = 'FOREIGN KEY'
        AND ccu.column_name = 'parent_branch_id'
        AND ccu.table_name = 'task_contexts'
    ) THEN
        ALTER TABLE task_contexts
        ADD CONSTRAINT fk_task_contexts_parent_branch_id 
        FOREIGN KEY (parent_branch_id) 
        REFERENCES project_git_branchs(id) 
        ON DELETE CASCADE;
        
        RAISE NOTICE 'Added foreign key constraint: task_contexts.parent_branch_id -> project_git_branchs.id';
    ELSE
        RAISE NOTICE 'Foreign key constraint for parent_branch_id already exists';
    END IF;
END $$;

-- ==========================================
-- 5. Create performance indexes (if they don't exist)
-- ==========================================

-- Index for task_id foreign key lookups
CREATE INDEX IF NOT EXISTS idx_task_contexts_task_id ON task_contexts (task_id);

-- Index for parent_branch_id foreign key lookups  
CREATE INDEX IF NOT EXISTS idx_task_contexts_parent_branch_id ON task_contexts (parent_branch_id);

-- Index for performance on common queries
CREATE INDEX IF NOT EXISTS idx_task_contexts_user_id ON task_contexts (user_id);

RAISE NOTICE 'Created performance indexes for foreign key columns';

-- ==========================================
-- 6. Verify constraint creation
-- ==========================================

DO $$
DECLARE
    task_id_fk_count INTEGER := 0;
    parent_branch_id_fk_count INTEGER := 0;
    total_constraints INTEGER := 0;
BEGIN
    -- Count foreign key constraints for task_id
    SELECT COUNT(*) INTO task_id_fk_count
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_name = 'task_contexts' 
    AND tc.constraint_type = 'FOREIGN KEY'
    AND ccu.column_name = 'task_id';
    
    -- Count foreign key constraints for parent_branch_id
    SELECT COUNT(*) INTO parent_branch_id_fk_count
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_name = 'task_contexts' 
    AND tc.constraint_type = 'FOREIGN KEY'
    AND ccu.column_name = 'parent_branch_id';
    
    -- Total foreign key constraints on task_contexts table
    SELECT COUNT(*) INTO total_constraints
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'task_contexts' 
    AND tc.constraint_type = 'FOREIGN KEY';
    
    RAISE NOTICE 'Foreign Key Verification Results:';
    RAISE NOTICE '- task_id foreign key constraints: %', task_id_fk_count;
    RAISE NOTICE '- parent_branch_id foreign key constraints: %', parent_branch_id_fk_count;
    RAISE NOTICE '- Total foreign key constraints on task_contexts: %', total_constraints;
    
    IF task_id_fk_count >= 1 AND parent_branch_id_fk_count >= 1 THEN
        RAISE NOTICE 'SUCCESS: All required foreign key constraints have been created';
    ELSE
        RAISE EXCEPTION 'FAILURE: Some foreign key constraints are missing';
    END IF;
END $$;

-- ==========================================
-- 7. Test constraint functionality
-- ==========================================

DO $$
DECLARE
    test_passed BOOLEAN := TRUE;
    error_message TEXT;
BEGIN
    -- Test 1: Try to insert task_context with invalid task_id (should fail)
    BEGIN
        INSERT INTO task_contexts (id, task_id, user_id, created_at) 
        VALUES ('test-invalid-task-id', 'non-existent-task-id', 'test-user', CURRENT_TIMESTAMP);
        
        -- If we reach here, the constraint didn't work
        test_passed := FALSE;
        error_message := 'Foreign key constraint for task_id is not working';
        
        -- Clean up the test record if it was inserted
        DELETE FROM task_contexts WHERE id = 'test-invalid-task-id';
    EXCEPTION
        WHEN foreign_key_violation THEN
            -- This is expected - constraint is working correctly
            RAISE NOTICE 'Test 1 PASSED: task_id foreign key constraint is working';
    END;
    
    -- Test 2: Try to insert task_context with invalid parent_branch_id (should fail)
    BEGIN
        INSERT INTO task_contexts (id, parent_branch_id, user_id, created_at) 
        VALUES ('test-invalid-branch-id', 'non-existent-branch-id', 'test-user', CURRENT_TIMESTAMP);
        
        -- If we reach here, the constraint didn't work
        test_passed := FALSE;
        error_message := 'Foreign key constraint for parent_branch_id is not working';
        
        -- Clean up the test record if it was inserted
        DELETE FROM task_contexts WHERE id = 'test-invalid-branch-id';
    EXCEPTION
        WHEN foreign_key_violation THEN
            -- This is expected - constraint is working correctly
            RAISE NOTICE 'Test 2 PASSED: parent_branch_id foreign key constraint is working';
    END;
    
    IF test_passed THEN
        RAISE NOTICE 'All foreign key constraint tests PASSED';
    ELSE
        RAISE EXCEPTION 'Foreign key constraint test FAILED: %', error_message;
    END IF;
END $$;

-- Record migration completion
INSERT INTO migration_history (migration_name, applied_at) 
VALUES ('005_add_missing_foreign_keys_completed', CURRENT_TIMESTAMP)
ON CONFLICT (migration_name) DO NOTHING;

COMMIT;

-- ==========================================
-- Migration Summary
-- ==========================================
--
-- This migration adds the following foreign key constraints to task_contexts table:
-- ✓ fk_task_contexts_task_id: task_contexts.task_id -> tasks.id (ON DELETE CASCADE)
-- ✓ fk_task_contexts_parent_branch_id: task_contexts.parent_branch_id -> project_git_branchs.id (ON DELETE CASCADE)
--
-- Additional improvements:
-- ✓ Data integrity verification and cleanup of orphaned records
-- ✓ Performance indexes for foreign key columns
-- ✓ Comprehensive constraint testing
-- ✓ Migration tracking and logging
--
-- The database schema now matches the SQLAlchemy model definitions exactly.
-- Referential integrity is enforced at the database level.
-- Performance is optimized with appropriate indexes.