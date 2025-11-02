-- Migration 007: Add Agent Management Tables
-- Date: 2025-11-02
-- Description: Create agent_templates and user_agent_instances tables for agent management system

-- ============================================================================
-- AGENT TEMPLATES TABLE
-- ============================================================================
-- Stores global agent template definitions loaded from agent-library
-- These are shared across all users and provide base configurations

CREATE TABLE IF NOT EXISTS agent_templates (
    -- Primary key
    id UUID PRIMARY KEY,

    -- Core identification
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Configuration (stored as JSON strings)
    system_prompt TEXT NOT NULL,
    tools TEXT NOT NULL,  -- JSON array
    capabilities TEXT NOT NULL,  -- JSON object
    rules TEXT,  -- JSON array, nullable
    output_format TEXT,  -- JSON object, nullable
    metadata TEXT,  -- JSON object, nullable

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for agent_templates
CREATE INDEX IF NOT EXISTS ix_agent_templates_slug ON agent_templates(slug);
CREATE INDEX IF NOT EXISTS ix_agent_templates_category ON agent_templates(category);
CREATE INDEX IF NOT EXISTS ix_agent_templates_version ON agent_templates(version);
CREATE INDEX IF NOT EXISTS ix_agent_templates_category_version ON agent_templates(category, version);

-- ============================================================================
-- USER AGENT INSTANCES TABLE
-- ============================================================================
-- Stores per-user agent instances with customizations
-- Each user can have one instance per template

CREATE TABLE IF NOT EXISTS user_agent_instances (
    -- Primary key
    id UUID PRIMARY KEY,

    -- Ownership
    user_id UUID NOT NULL,
    template_id UUID NOT NULL,

    -- Instance naming
    agent_name VARCHAR(200) NOT NULL,

    -- Customization tracking
    is_customized BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    customization_notes TEXT,

    -- Configuration (stored as JSON strings, can be customized from template)
    system_prompt TEXT NOT NULL,
    tools TEXT NOT NULL,  -- JSON array
    capabilities TEXT NOT NULL,  -- JSON object
    rules TEXT,  -- JSON array, nullable
    output_format TEXT,  -- JSON object, nullable
    metadata TEXT,  -- JSON object, nullable

    -- Sharing
    visibility VARCHAR(50) NOT NULL DEFAULT 'private',
    share_token VARCHAR(64) UNIQUE,  -- 64-character random token
    share_created_at TIMESTAMP WITH TIME ZONE,

    -- Import tracking
    original_creator_id UUID,
    imported_at TIMESTAMP WITH TIME ZONE,

    -- Usage tracking
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_user_agent_instances_user_template UNIQUE (user_id, template_id)
);

-- Indexes for user_agent_instances
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_user_id ON user_agent_instances(user_id);
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_template_id ON user_agent_instances(template_id);
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_share_token ON user_agent_instances(share_token);
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_visibility ON user_agent_instances(visibility);
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_user_visibility ON user_agent_instances(user_id, visibility);
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_visibility_created ON user_agent_instances(visibility, created_at);
CREATE INDEX IF NOT EXISTS ix_user_agent_instances_user_enabled ON user_agent_instances(user_id, is_enabled);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE agent_templates IS 'Global agent template definitions from agent-library';
COMMENT ON TABLE user_agent_instances IS 'Per-user agent instances with customizations';

COMMENT ON COLUMN agent_templates.slug IS 'URL-friendly identifier (e.g., coding-agent)';
COMMENT ON COLUMN agent_templates.tools IS 'JSON array of tool names';
COMMENT ON COLUMN agent_templates.capabilities IS 'JSON object describing capabilities';
COMMENT ON COLUMN agent_templates.rules IS 'JSON array of rules and constraints';

COMMENT ON COLUMN user_agent_instances.is_enabled IS 'Whether agent is enabled for use in call_agent tools';
COMMENT ON COLUMN user_agent_instances.share_token IS 'Unique 64-char token for sharing public instances';
COMMENT ON COLUMN user_agent_instances.visibility IS 'private or public - controls sharing';
COMMENT ON COLUMN user_agent_instances.usage_count IS 'Number of times this agent has been invoked';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables were created
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agent_templates') THEN
        RAISE NOTICE 'Table agent_templates created successfully';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_agent_instances') THEN
        RAISE NOTICE 'Table user_agent_instances created successfully';
    END IF;
END $$;
