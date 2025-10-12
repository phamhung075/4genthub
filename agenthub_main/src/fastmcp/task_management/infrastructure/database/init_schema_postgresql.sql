-- ========================================
-- AGENTHUB COMPLETE DATABASE SCHEMA - POSTGRESQL
-- ========================================
-- Version: 1.0 (2025-09-25)
-- Description: Complete database initialization with ALL tables, indexes, constraints, and triggers
-- Database: PostgreSQL 12+
-- Includes: All ORM models + AI Agent fields + Task count triggers + Context system
-- ========================================

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables in dependency order (for clean recreate)
DROP TABLE IF EXISTS task_labels;
DROP TABLE IF EXISTS labels;
DROP TABLE IF EXISTS task_dependencies;
DROP TABLE IF EXISTS task_assignees;
DROP TABLE IF EXISTS subtasks;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS task_contexts;
DROP TABLE IF EXISTS branch_contexts;
DROP TABLE IF EXISTS project_contexts;
DROP TABLE IF EXISTS global_contexts;
DROP TABLE IF EXISTS context_delegations;
DROP TABLE IF EXISTS context_inheritance_cache;
DROP TABLE IF EXISTS project_git_branchs;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS templates;
DROP TABLE IF EXISTS api_tokens;


-- ========================================
-- CORE TABLES
-- ========================================

-- API Tokens table
CREATE TABLE api_tokens (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    token_hash VARCHAR NOT NULL,
    scopes JSONB DEFAULT '[]',
    created_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    rate_limit INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT TRUE,
    token_metadata JSONB DEFAULT '{}'
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    user_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'active',
    metadata JSONB DEFAULT '{}'
);

-- Project Git Branches table (task trees)
CREATE TABLE project_git_branchs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    name VARCHAR NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    assigned_agent_id VARCHAR,
    agent_id UUID,
    priority VARCHAR DEFAULT 'medium',
    status VARCHAR DEFAULT 'todo',
    metadata JSONB DEFAULT '{}',
    task_count INTEGER DEFAULT 0,
    completed_task_count INTEGER DEFAULT 0,
    user_id VARCHAR NOT NULL
);

-- Tasks table (with AI Agent fields)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL CHECK (LENGTH(description) <= 2000),
    git_branch_id UUID NOT NULL REFERENCES project_git_branchs(id),
    status VARCHAR NOT NULL DEFAULT 'todo',
    priority VARCHAR NOT NULL DEFAULT 'medium',
    progress_history JSONB DEFAULT '{}',
    progress_count INTEGER DEFAULT 0,
    estimated_effort VARCHAR DEFAULT '2 hours' NOT NULL,
    due_date VARCHAR,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    completion_summary TEXT DEFAULT '',
    testing_notes TEXT DEFAULT '',
    context_id UUID,
    progress_percentage INTEGER DEFAULT 0,
    progress_state VARCHAR DEFAULT 'INITIAL' NOT NULL,
    subtask_count INTEGER DEFAULT 0,
    user_id VARCHAR NOT NULL,

    -- AI Agent System Fields
    ai_system_prompt TEXT DEFAULT '',
    ai_request_prompt TEXT DEFAULT '',
    ai_work_context JSONB DEFAULT '{}',
    ai_completion_criteria TEXT DEFAULT '',
    ai_execution_history JSONB DEFAULT '[]',
    ai_last_execution TIMESTAMP,
    ai_model_preferences JSONB DEFAULT '{}'
);

-- Subtasks table (with AI Agent fields)
CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '' CHECK (LENGTH(description) <= 500),
    status VARCHAR NOT NULL DEFAULT 'todo',
    priority VARCHAR NOT NULL DEFAULT 'medium',
    assignees JSONB DEFAULT '[]',
    estimated_effort VARCHAR,
    progress_percentage INTEGER DEFAULT 0,
    progress_state VARCHAR DEFAULT 'INITIAL' NOT NULL,
    progress_notes TEXT DEFAULT '',
    blockers TEXT DEFAULT '',
    completion_summary TEXT DEFAULT '',
    impact_on_parent TEXT DEFAULT '',
    insights_found JSONB DEFAULT '[]',
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- AI Agent System Fields
    ai_system_prompt TEXT DEFAULT '',
    ai_request_prompt TEXT DEFAULT '',
    ai_work_context JSONB DEFAULT '{}',
    ai_completion_criteria TEXT DEFAULT '',
    ai_execution_history JSONB DEFAULT '[]',
    ai_last_execution TIMESTAMP,
    ai_model_preferences JSONB DEFAULT '{}'
);

-- Task Assignees table
CREATE TABLE task_assignees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    assignee_id VARCHAR NOT NULL,
    agent_id UUID,
    role VARCHAR DEFAULT 'contributor',
    user_id VARCHAR NOT NULL,
    assigned_at TIMESTAMP );

-- Task Dependencies table
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    depends_on_task_id UUID NOT NULL REFERENCES tasks(id),
    dependency_type VARCHAR DEFAULT 'blocks',
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP );

-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    description TEXT DEFAULT '',
    role VARCHAR DEFAULT 'assistant',
    capabilities JSONB DEFAULT '[]',
    status VARCHAR DEFAULT 'available',
    availability_score FLOAT DEFAULT 1.0,
    last_active_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    user_id VARCHAR NOT NULL
);

-- Labels table
CREATE TABLE labels (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    color VARCHAR DEFAULT '#0066cc',
    description TEXT DEFAULT '',
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP );

-- Task Labels junction table
CREATE TABLE task_labels (
    task_id UUID REFERENCES tasks(id),
    label_id VARCHAR REFERENCES labels(id),
    user_id VARCHAR NOT NULL,
    applied_at TIMESTAMP,
    PRIMARY KEY (task_id, label_id)
);

-- Templates table
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    template_name VARCHAR NOT NULL DEFAULT '',
    template_content TEXT DEFAULT '',
    template_type VARCHAR DEFAULT 'general',
    type VARCHAR NOT NULL,
    content JSONB NOT NULL,
    category VARCHAR DEFAULT 'general',
    tags JSONB DEFAULT '[]',
    usage_count INTEGER DEFAULT 0,
    user_id VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by VARCHAR NOT NULL,
    metadata JSONB DEFAULT '{}' );

-- ========================================
-- CONTEXT SYSTEM TABLES
-- ========================================

-- Global Contexts table
CREATE TABLE global_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID,
    organization_standards JSONB NOT NULL DEFAULT '{}',
    security_policies JSONB NOT NULL DEFAULT '{}',
    compliance_requirements JSONB NOT NULL DEFAULT '{}',
    shared_resources JSONB NOT NULL DEFAULT '{}',
    reusable_patterns JSONB NOT NULL DEFAULT '{}',
    global_preferences JSONB NOT NULL DEFAULT '{}',
    delegation_rules JSONB NOT NULL DEFAULT '{}',
    nested_structure JSONB NOT NULL DEFAULT '{}',
    unified_context_data JSONB DEFAULT '{}',
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Project Contexts table
CREATE TABLE project_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID,
    parent_global_id UUID REFERENCES global_contexts(id),
    data JSONB DEFAULT '{}',
    project_info JSONB DEFAULT '{}',
    team_preferences JSONB DEFAULT '{}',
    technology_stack JSONB DEFAULT '{}',
    project_workflow JSONB DEFAULT '{}',
    local_standards JSONB DEFAULT '{}',
    project_settings JSONB DEFAULT '{}',
    technical_specifications JSONB DEFAULT '{}',
    global_overrides JSONB DEFAULT '{}',
    delegation_rules JSONB DEFAULT '{}',
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1,
    inheritance_disabled BOOLEAN DEFAULT FALSE
);

-- Branch Contexts table
CREATE TABLE branch_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES project_git_branchs(id),
    parent_project_id UUID REFERENCES project_contexts(id),
    data JSONB DEFAULT '{}',
    branch_info JSONB DEFAULT '{}',
    branch_workflow JSONB DEFAULT '{}',
    feature_flags JSONB DEFAULT '{}',
    discovered_patterns JSONB DEFAULT '{}',
    branch_decisions JSONB DEFAULT '{}',
    active_patterns JSONB DEFAULT '{}',
    local_overrides JSONB DEFAULT '{}',
    delegation_rules JSONB DEFAULT '{}',
    inheritance_disabled BOOLEAN DEFAULT FALSE,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Task Contexts table
CREATE TABLE task_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id),
    parent_branch_id UUID REFERENCES project_git_branchs(id),
    parent_branch_context_id UUID REFERENCES branch_contexts(id),
    data JSONB DEFAULT '{}',
    task_data JSONB DEFAULT '{}',
    execution_context JSONB DEFAULT '{}',
    discovered_patterns JSONB DEFAULT '{}',
    implementation_notes JSONB DEFAULT '{}',
    test_results JSONB DEFAULT '{}',
    blockers JSONB DEFAULT '{}',
    local_decisions JSONB DEFAULT '{}',
    delegation_queue JSONB DEFAULT '{}',
    local_overrides JSONB DEFAULT '{}',
    delegation_triggers JSONB DEFAULT '{}',
    inheritance_disabled BOOLEAN DEFAULT FALSE,
    force_local_only BOOLEAN DEFAULT FALSE,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Context Delegations table
CREATE TABLE context_delegations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_level VARCHAR NOT NULL CHECK (source_level IN ('task', 'branch', 'project', 'global')),
    source_id UUID NOT NULL,
    source_type VARCHAR DEFAULT 'context',
    target_level VARCHAR NOT NULL CHECK (target_level IN ('task', 'branch', 'project', 'global')),
    target_id UUID NOT NULL,
    target_type VARCHAR DEFAULT 'context',
    delegated_data JSONB NOT NULL,
    delegation_data JSONB DEFAULT '{}',
    delegation_reason VARCHAR NOT NULL,
    trigger_type VARCHAR NOT NULL CHECK (trigger_type IN ('manual', 'auto_pattern', 'auto_threshold')),
    auto_delegated BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    processed BOOLEAN DEFAULT FALSE,
    status VARCHAR DEFAULT 'pending',
    approved BOOLEAN,
    processed_by VARCHAR,
    rejected_reason VARCHAR,
    error_message VARCHAR,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    processed_at TIMESTAMP
);

-- Context Inheritance Cache table
CREATE TABLE context_inheritance_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_id UUID NOT NULL,
    context_level VARCHAR NOT NULL CHECK (context_level IN ('task', 'branch', 'project', 'global')),
    context_type VARCHAR DEFAULT 'hierarchical',
    resolved_context JSONB NOT NULL,
    resolved_data JSONB DEFAULT '{}',
    dependencies_hash VARCHAR NOT NULL,
    resolution_path VARCHAR NOT NULL,
    parent_chain JSONB DEFAULT '[]',
    created_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit TIMESTAMP,
    cache_size_bytes INTEGER NOT NULL,
    invalidated BOOLEAN DEFAULT FALSE,
    invalidation_reason VARCHAR,
    user_id VARCHAR NOT NULL,
    UNIQUE (context_id, context_level)
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Core table indexes
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_project_git_branchs_project_id ON project_git_branchs(project_id);
CREATE INDEX idx_project_git_branchs_user_id ON project_git_branchs(user_id);

CREATE INDEX idx_tasks_git_branch_id ON tasks(git_branch_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_ai_last_execution ON tasks(ai_last_execution);

CREATE INDEX idx_subtasks_task_id ON subtasks(task_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);
CREATE INDEX idx_subtasks_user_id ON subtasks(user_id);
CREATE INDEX idx_subtasks_ai_last_execution ON subtasks(ai_last_execution);

CREATE INDEX idx_task_assignees_task_id ON task_assignees(task_id);
CREATE INDEX idx_task_assignees_assignee_id ON task_assignees(assignee_id);
CREATE INDEX idx_task_assignees_user_id ON task_assignees(user_id);

-- Context system indexes
CREATE INDEX idx_global_contexts_user_id ON global_contexts(user_id);
CREATE INDEX idx_project_contexts_project_id ON project_contexts(project_id);
CREATE INDEX idx_project_contexts_user_id ON project_contexts(user_id);
CREATE INDEX idx_branch_contexts_branch_id ON branch_contexts(branch_id);
CREATE INDEX idx_branch_contexts_user_id ON branch_contexts(user_id);
CREATE INDEX idx_task_contexts_task_id ON task_contexts(task_id);
CREATE INDEX idx_task_contexts_user_id ON task_contexts(user_id);

-- Context delegation indexes
CREATE INDEX idx_delegation_source ON context_delegations(source_level, source_id);
CREATE INDEX idx_delegation_target ON context_delegations(target_level, target_id);
CREATE INDEX idx_delegation_processed ON context_delegations(processed);

-- Context cache indexes
CREATE INDEX idx_cache_level ON context_inheritance_cache(context_level);
CREATE INDEX idx_cache_expires ON context_inheritance_cache(expires_at);
CREATE INDEX idx_cache_invalidated ON context_inheritance_cache(invalidated);

-- ========================================
-- NO SQL TRIGGERS OR FUNCTIONS
-- ========================================
-- All task counts, subtask counts, and cascade deletions are
-- handled in the domain layer through domain services and events.
-- This ensures clean architecture and business logic stays in code,
-- not in the database.

-- ========================================
-- CONSTRAINTS
-- ========================================

ALTER TABLE projects ADD CONSTRAINT uq_project_user UNIQUE (id, user_id);
ALTER TABLE project_git_branchs ADD CONSTRAINT uq_branch_project UNIQUE (id, project_id);

-- ========================================
-- COMMENTS FOR DOCUMENTATION
-- ========================================

COMMENT ON TABLE tasks IS 'Main tasks with AI Agent system integration';
COMMENT ON TABLE subtasks IS 'Subtasks with AI Agent system integration';
COMMENT ON COLUMN tasks.ai_system_prompt IS 'System prompt for AI agent context';
COMMENT ON COLUMN tasks.ai_request_prompt IS 'Specific AI execution prompt';
COMMENT ON COLUMN tasks.ai_work_context IS 'AI work context (JSON)';
COMMENT ON COLUMN tasks.ai_completion_criteria IS 'AI completion criteria';
COMMENT ON COLUMN tasks.ai_execution_history IS 'AI execution history (JSON array)';
COMMENT ON COLUMN tasks.ai_last_execution IS 'Last AI execution timestamp';
COMMENT ON COLUMN tasks.ai_model_preferences IS 'AI model preferences (JSON)';


-- Database initialization complete
SELECT 'AGENTHUB POSTGRESQL DATABASE INITIALIZED SUCCESSFULLY' as status;