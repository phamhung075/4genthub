-- Migration to update context models to match CONTEXT_DATA_MODELS.md
-- Date: 2025-09-03
-- Purpose: Align database schema with documented context data models

-- ============================================
-- GLOBAL CONTEXT - Add new columns if they don't exist
-- ============================================

-- Rename/add columns for GlobalContext
ALTER TABLE global_contexts 
  ADD COLUMN IF NOT EXISTS organization_standards JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS compliance_requirements JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS shared_resources JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS reusable_patterns JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS global_preferences JSON DEFAULT '{}';

-- Drop old columns if they exist (after data migration)
-- Note: Uncomment these after ensuring data is migrated
-- ALTER TABLE global_contexts DROP COLUMN IF EXISTS autonomous_rules;
-- ALTER TABLE global_contexts DROP COLUMN IF EXISTS coding_standards;
-- ALTER TABLE global_contexts DROP COLUMN IF EXISTS workflow_templates;

-- ============================================
-- PROJECT CONTEXT - Add new columns if they don't exist
-- ============================================

ALTER TABLE project_contexts
  ADD COLUMN IF NOT EXISTS project_info JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS project_settings JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS technical_specifications JSON DEFAULT '{}';

-- ============================================
-- BRANCH CONTEXT - Add new columns if they don't exist
-- ============================================

ALTER TABLE branch_contexts
  ADD COLUMN IF NOT EXISTS branch_info JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS discovered_patterns JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS branch_decisions JSON DEFAULT '{}';

-- ============================================
-- TASK CONTEXT - Add new columns if they don't exist
-- ============================================

ALTER TABLE task_contexts
  ADD COLUMN IF NOT EXISTS test_results JSON DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS blockers JSON DEFAULT '{}';

-- ============================================
-- DATA MIGRATION - Migrate existing data to new columns
-- ============================================

-- Migrate GlobalContext data
UPDATE global_contexts 
SET 
  organization_standards = COALESCE(
    CASE 
      WHEN coding_standards IS NOT NULL THEN coding_standards
      ELSE '{}'::json
    END, 
    '{}'::json
  )
WHERE organization_standards IS NULL OR organization_standards = '{}'::json;

UPDATE global_contexts
SET
  reusable_patterns = COALESCE(
    CASE
      WHEN workflow_templates IS NOT NULL THEN workflow_templates
      ELSE '{}'::json
    END,
    '{}'::json
  )
WHERE reusable_patterns IS NULL OR reusable_patterns = '{}'::json;

-- ============================================
-- INDEXES for performance
-- ============================================

CREATE INDEX IF NOT EXISTS idx_global_context_user_id ON global_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_project_context_user_id ON project_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_branch_context_user_id ON branch_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_task_context_user_id ON task_contexts(user_id);

-- Create composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_project_context_project_user ON project_contexts(project_id, user_id);
CREATE INDEX IF NOT EXISTS idx_branch_context_branch_user ON branch_contexts(branch_id, user_id);
CREATE INDEX IF NOT EXISTS idx_task_context_task_user ON task_contexts(task_id, user_id);

-- ============================================
-- COMMENTS for documentation
-- ============================================

COMMENT ON TABLE global_contexts IS 'User-scoped global organizational context - top of hierarchy';
COMMENT ON TABLE project_contexts IS 'Project-level context - inherits from global';
COMMENT ON TABLE branch_contexts IS 'Branch/feature-level context - inherits from project';
COMMENT ON TABLE task_contexts IS 'Task-level context - inherits from branch';

COMMENT ON COLUMN global_contexts.organization_standards IS 'Organization-wide standards: coding style, git workflow, testing requirements';
COMMENT ON COLUMN global_contexts.compliance_requirements IS 'Compliance requirements: GDPR, HIPAA, SOC2, etc.';
COMMENT ON COLUMN global_contexts.shared_resources IS 'Shared resources: API keys, service accounts, tools';
COMMENT ON COLUMN global_contexts.reusable_patterns IS 'Reusable patterns: design patterns, code templates';

COMMENT ON COLUMN project_contexts.project_info IS 'Project metadata: name, description, version, status';
COMMENT ON COLUMN project_contexts.team_preferences IS 'Team settings: review requirements, merge strategy';
COMMENT ON COLUMN project_contexts.technology_stack IS 'Tech stack: frontend, backend, database, infrastructure';
COMMENT ON COLUMN project_contexts.technical_specifications IS 'Technical specs: API definitions, schemas, architecture';

COMMENT ON COLUMN branch_contexts.branch_info IS 'Branch metadata: feature name, type, status, parent';
COMMENT ON COLUMN branch_contexts.discovered_patterns IS 'Patterns discovered during feature development';
COMMENT ON COLUMN branch_contexts.branch_decisions IS 'Technical decisions made for this feature';

COMMENT ON COLUMN task_contexts.task_data IS 'Task metadata: title, status, progress, assignees';
COMMENT ON COLUMN task_contexts.execution_context IS 'Execution details: files modified, tests added, current work';
COMMENT ON COLUMN task_contexts.test_results IS 'Test outcomes: coverage, passing/failing tests';
COMMENT ON COLUMN task_contexts.blockers IS 'Current impediments and dependencies';