-- Migration 007: Remove FK constraint from agent_import_history
--
-- Purpose: Remove foreign key constraint to users table since Keycloak is
--          the source of truth for user identity. The user_id field will
--          remain as a plain UUID that references Keycloak users.
--
-- Rationale:
--   - Keycloak is the single source of truth for user authentication
--   - No need to duplicate user records in local database
--   - Simplifies architecture and eliminates sync complexity
--   - user_id is still tracked for audit purposes
--
-- Date: 2025-11-05
-- Related Issue: Agent import history recording fails due to missing users

-- Drop the foreign key constraint
ALTER TABLE agent_import_history
DROP CONSTRAINT IF EXISTS agent_import_history_importer_user_id_fkey;

-- Add comment explaining the user_id field references Keycloak
COMMENT ON COLUMN agent_import_history.importer_user_id IS
  'User UUID from Keycloak authentication (not enforced FK). References the authenticated user who imported this agent.';

-- Add comment on table for clarity
COMMENT ON TABLE agent_import_history IS
  'Tracks agent imports from marketplace. user_id references Keycloak users (auth source of truth).';
