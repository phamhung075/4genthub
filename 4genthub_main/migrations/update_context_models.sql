-- Migration: Update context models to match CONTEXT_DATA_MODELS.md
-- Date: 2025-09-03
-- Description: Add new JSON fields to all context tables for structured data storage

-- ========================================
-- Global Context Updates
-- ========================================
ALTER TABLE global_contexts 
ADD COLUMN IF NOT EXISTS organization_standards JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS compliance_requirements JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS shared_resources JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS reusable_patterns JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS global_preferences JSON DEFAULT '{}';

-- ========================================
-- Project Context Updates
-- ========================================
ALTER TABLE project_contexts
ADD COLUMN IF NOT EXISTS project_info JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS team_preferences JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS technology_stack JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS project_workflow JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS local_standards JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS project_settings JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS technical_specifications JSON DEFAULT '{}';

-- ========================================
-- Branch Context Updates
-- ========================================
ALTER TABLE branch_contexts
ADD COLUMN IF NOT EXISTS branch_info JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS branch_workflow JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS feature_flags JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS discovered_patterns JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS branch_decisions JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS branch_settings JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS active_patterns JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS local_overrides JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS delegation_rules JSON DEFAULT '{}';

-- ========================================
-- Task Context Updates
-- ========================================
ALTER TABLE task_contexts
ADD COLUMN IF NOT EXISTS task_data JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS execution_context JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS discovered_patterns JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS implementation_notes JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS test_results JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS blockers JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS local_decisions JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS delegation_queue JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS local_overrides JSON DEFAULT '{}',
ADD COLUMN IF NOT EXISTS delegation_triggers JSON DEFAULT '{}';