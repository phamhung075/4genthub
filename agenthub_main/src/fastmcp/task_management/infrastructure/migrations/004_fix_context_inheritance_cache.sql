-- Migration: Fix ContextInheritanceCache Table Schema
-- Date: 2025-08-26
-- Description: Adds missing columns to context_inheritance_cache table to match SQLAlchemy model definition
-- Target: PostgreSQL (Supabase)
-- Related Issue: Database schema validation errors for ContextInheritanceCache table

BEGIN TRANSACTION;

-- Create migration tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Record migration start
INSERT INTO migration_history (migration_name) 
VALUES ('004_fix_context_inheritance_cache') 
ON CONFLICT (migration_name) DO NOTHING;

-- ==========================================
-- 1. Backup existing data
-- ==========================================

-- Create backup table for existing context_inheritance_cache data
CREATE TABLE IF NOT EXISTS migration_backup_context_inheritance_cache AS
SELECT * FROM context_inheritance_cache;

-- ==========================================
-- 2. Add missing columns to context_inheritance_cache table
-- ==========================================

-- Check current table structure first
-- The model defines these columns that might be missing from the database:
-- 1. context_level (String, primary_key=True)
-- 2. resolved_context (JSON, nullable=False)  
-- 3. dependencies_hash (String, nullable=False)
-- 4. resolution_path (String, nullable=False)
-- 5. hit_count (Integer, default=0)
-- 6. last_hit (DateTime, server_default=func.now())
-- 7. cache_size_bytes (Integer, nullable=False)
-- 8. invalidated (Boolean, default=False)
-- 9. invalidation_reason (String, nullable=True)

-- Add context_level as primary key if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'context_inheritance_cache' 
        AND column_name = 'context_level'
    ) THEN
        -- First add as regular column, then modify to be primary key
        ALTER TABLE context_inheritance_cache 
        ADD COLUMN context_level VARCHAR(50) DEFAULT 'task';
        
        -- Update existing rows with appropriate context levels based on context_id pattern
        UPDATE context_inheritance_cache 
        SET context_level = CASE 
            -- Global context has the specific UUID pattern
            WHEN context_id = '00000000-0000-0000-0000-000000000001' THEN 'global'
            -- We'll need to identify project, branch, and task contexts
            -- For now, default to 'task' and let the application layer handle proper categorization
            ELSE 'task'
        END;
        
        -- Make it NOT NULL after setting values
        ALTER TABLE context_inheritance_cache 
        ALTER COLUMN context_level SET NOT NULL;
        
        -- Drop existing primary key constraint if it exists
        ALTER TABLE context_inheritance_cache DROP CONSTRAINT IF EXISTS context_inheritance_cache_pkey;
        
        -- Add composite primary key (context_id, context_level)
        ALTER TABLE context_inheritance_cache 
        ADD CONSTRAINT context_inheritance_cache_pkey 
        PRIMARY KEY (context_id, context_level);
    END IF;
END $$;

-- Add resolved_context column (JSON field for cached resolved context data)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS resolved_context JSONB DEFAULT '{}';

-- Update column to be NOT NULL after adding default values
UPDATE context_inheritance_cache 
SET resolved_context = '{}' 
WHERE resolved_context IS NULL;

ALTER TABLE context_inheritance_cache 
ALTER COLUMN resolved_context SET NOT NULL;

-- Add dependencies_hash column (for cache invalidation tracking)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS dependencies_hash VARCHAR DEFAULT '';

-- Update column to be NOT NULL after adding default values
UPDATE context_inheritance_cache 
SET dependencies_hash = 'migration_placeholder' 
WHERE dependencies_hash = '' OR dependencies_hash IS NULL;

ALTER TABLE context_inheritance_cache 
ALTER COLUMN dependencies_hash SET NOT NULL;

-- Add resolution_path column (tracks how the context was resolved)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS resolution_path VARCHAR DEFAULT '';

-- Update column to be NOT NULL after adding default values
UPDATE context_inheritance_cache 
SET resolution_path = 'direct' 
WHERE resolution_path = '' OR resolution_path IS NULL;

ALTER TABLE context_inheritance_cache 
ALTER COLUMN resolution_path SET NOT NULL;

-- Add hit_count column (tracks cache usage)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS hit_count INTEGER DEFAULT 0;

-- Add last_hit column (tracks last access time)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add cache_size_bytes column (tracks memory usage)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS cache_size_bytes INTEGER DEFAULT 0;

-- Update cache_size_bytes to have a reasonable default based on resolved_context size
UPDATE context_inheritance_cache 
SET cache_size_bytes = COALESCE(LENGTH(resolved_context::text), 0)
WHERE cache_size_bytes = 0;

-- Make cache_size_bytes NOT NULL
ALTER TABLE context_inheritance_cache 
ALTER COLUMN cache_size_bytes SET NOT NULL;

-- Add invalidated column (tracks if cache entry is invalid)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS invalidated BOOLEAN DEFAULT FALSE;

-- Add invalidation_reason column (optional reason for invalidation)
ALTER TABLE context_inheritance_cache 
ADD COLUMN IF NOT EXISTS invalidation_reason VARCHAR DEFAULT NULL;

-- ==========================================
-- 3. Add constraints and indexes
-- ==========================================

-- Add check constraint for context_level values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'chk_cache_context_level' 
        AND table_name = 'context_inheritance_cache'
    ) THEN
        ALTER TABLE context_inheritance_cache 
        ADD CONSTRAINT chk_cache_context_level 
        CHECK (context_level IN ('task', 'branch', 'project', 'global'));
    END IF;
END $$;

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_cache_level ON context_inheritance_cache (context_level);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON context_inheritance_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_invalidated ON context_inheritance_cache (invalidated);
CREATE INDEX IF NOT EXISTS idx_cache_hit_count ON context_inheritance_cache (hit_count);
CREATE INDEX IF NOT EXISTS idx_cache_last_hit ON context_inheritance_cache (last_hit);

-- ==========================================
-- 4. Data validation and cleanup
-- ==========================================

-- Ensure all required fields have proper values
UPDATE context_inheritance_cache 
SET 
    resolved_context = COALESCE(resolved_context, '{}'),
    dependencies_hash = COALESCE(dependencies_hash, 'migration_default'),
    resolution_path = COALESCE(resolution_path, 'direct'),
    hit_count = COALESCE(hit_count, 0),
    last_hit = COALESCE(last_hit, CURRENT_TIMESTAMP),
    cache_size_bytes = COALESCE(cache_size_bytes, 0),
    invalidated = COALESCE(invalidated, FALSE)
WHERE 
    resolved_context IS NULL 
    OR dependencies_hash IS NULL 
    OR resolution_path IS NULL 
    OR hit_count IS NULL 
    OR last_hit IS NULL 
    OR cache_size_bytes IS NULL 
    OR invalidated IS NULL;

-- ==========================================
-- 5. Verify table structure
-- ==========================================

-- Log the final table structure for verification
DO $$
DECLARE
    column_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns 
    WHERE table_name = 'context_inheritance_cache';
    
    RAISE NOTICE 'ContextInheritanceCache table now has % columns', column_count;
END $$;

-- Record migration completion
INSERT INTO migration_history (migration_name, applied_at) 
VALUES ('004_fix_context_inheritance_cache_completed', CURRENT_TIMESTAMP)
ON CONFLICT (migration_name) DO NOTHING;

COMMIT;

-- ==========================================
-- Migration Summary
-- ==========================================
--
-- This migration adds the following columns to context_inheritance_cache:
-- ✓ context_level (VARCHAR, primary key) - identifies the context hierarchy level
-- ✓ resolved_context (JSONB, NOT NULL) - cached resolved context data  
-- ✓ dependencies_hash (VARCHAR, NOT NULL) - hash for cache invalidation
-- ✓ resolution_path (VARCHAR, NOT NULL) - path used for context resolution
-- ✓ hit_count (INTEGER, default 0) - number of cache hits
-- ✓ last_hit (TIMESTAMP, default now()) - last access timestamp
-- ✓ cache_size_bytes (INTEGER, NOT NULL) - memory size of cached data
-- ✓ invalidated (BOOLEAN, default FALSE) - invalidation status
-- ✓ invalidation_reason (VARCHAR, nullable) - reason for invalidation
--
-- The table now matches the SQLAlchemy model definition exactly.
-- Performance indexes have been added for optimal query performance.
-- A backup table has been created with existing data before modification.