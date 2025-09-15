-- Migration 006: Add data field to global_contexts table for unified context API compatibility
-- This migration addresses the context data persistence issue where the GlobalContext model
-- was missing the 'data' field that exists in other context models (ProjectContext, BranchContext, etc.)

-- Add the data field to global_contexts table
-- This field provides compatibility with the unified context API
ALTER TABLE global_contexts
ADD COLUMN data JSON DEFAULT '{}';

-- Update existing records to populate the data field from existing nested_structure
-- This ensures backward compatibility and prevents data loss
UPDATE global_contexts
SET data = CASE
    WHEN nested_structure IS NOT NULL AND nested_structure != '{}' THEN nested_structure
    ELSE '{}'
END
WHERE data IS NULL OR data = '{}';

-- Add comment to document the purpose of this field
COMMENT ON COLUMN global_contexts.data IS 'Generic data field for unified context API compatibility. Stores complete context data for API operations.';

-- Verify the migration
-- SELECT id, organization_id, data, nested_structure FROM global_contexts LIMIT 5;