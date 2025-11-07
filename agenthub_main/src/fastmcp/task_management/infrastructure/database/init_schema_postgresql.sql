-- ================================================================================
-- AGENTHUB DATABASE SCHEMA - POSTGRESQL
-- ================================================================================
-- AUTO-GENERATED from actual database schema
-- Generated: 2025-11-08 00:06:05
-- Database: PostgreSQL 12+
-- ================================================================================

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================================
-- SEQUENCES
-- ================================================================================

-- Sequence for task_dependencies table
CREATE SEQUENCE IF NOT EXISTS task_dependencies_id_seq;

-- ================================================================================
-- DROP TABLES
-- ================================================================================

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS user_token_balances CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS user_api_tokens CASCADE;
DROP TABLE IF EXISTS user_agent_instances CASCADE;
DROP TABLE IF EXISTS user_agent_configurations_md CASCADE;
DROP TABLE IF EXISTS token_transactions CASCADE;
DROP TABLE IF EXISTS templates CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS task_labels CASCADE;
DROP TABLE IF EXISTS task_dependencies CASCADE;
DROP TABLE IF EXISTS task_contexts CASCADE;
DROP TABLE IF EXISTS task_assignees CASCADE;
DROP TABLE IF EXISTS subtasks CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS project_git_branchs CASCADE;
DROP TABLE IF EXISTS project_contexts CASCADE;
DROP TABLE IF EXISTS missed_notifications CASCADE;
DROP TABLE IF EXISTS labels CASCADE;
DROP TABLE IF EXISTS global_contexts CASCADE;
DROP TABLE IF EXISTS context_inheritance_cache CASCADE;
DROP TABLE IF EXISTS context_delegations CASCADE;
DROP TABLE IF EXISTS branch_contexts CASCADE;
DROP TABLE IF EXISTS api_tokens CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS agent_templates CASCADE;
DROP TABLE IF EXISTS agent_import_history CASCADE;

-- ================================================================================
-- CREATE TABLES
-- ================================================================================

-- Table: agent_import_history
CREATE TABLE agent_import_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    importer_user_id UUID NOT NULL,
    source_instance_id UUID NOT NULL,
    imported_instance_id UUID NOT NULL,
    imported_at TIMESTAMP NOT NULL DEFAULT now(),
    share_token VARCHAR(64)
);

-- Table: agent_templates
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    system_prompt TEXT NOT NULL,
    tools TEXT NOT NULL,
    capabilities TEXT NOT NULL,
    rules TEXT,
    output_format TEXT,
    metadata TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Table: agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    role VARCHAR NOT NULL,
    capabilities JSONB NOT NULL,
    status VARCHAR NOT NULL,
    availability_score DOUBLE PRECISION NOT NULL,
    last_active_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    metadata JSONB NOT NULL,
    user_id VARCHAR NOT NULL
);

-- Table: api_tokens
CREATE TABLE api_tokens (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    token_hash VARCHAR NOT NULL,
    scopes JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    usage_count INTEGER NOT NULL,
    rate_limit INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,
    token_metadata JSONB NOT NULL,
    usage_stats JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Table: branch_contexts
CREATE TABLE branch_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID,
    parent_project_id UUID,
    data JSONB,
    branch_info JSONB,
    branch_workflow JSONB,
    feature_flags JSONB,
    discovered_patterns JSONB,
    branch_decisions JSONB,
    active_patterns JSONB,
    local_overrides JSONB,
    delegation_rules JSONB,
    inheritance_disabled BOOLEAN,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER
);

-- Table: context_delegations
CREATE TABLE context_delegations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_level VARCHAR NOT NULL,
    source_id UUID NOT NULL,
    source_type VARCHAR NOT NULL,
    target_level VARCHAR NOT NULL,
    target_id UUID NOT NULL,
    target_type VARCHAR NOT NULL,
    delegated_data JSONB NOT NULL,
    delegation_data JSONB NOT NULL,
    delegation_reason VARCHAR NOT NULL,
    trigger_type VARCHAR NOT NULL,
    auto_delegated BOOLEAN NOT NULL,
    confidence_score DOUBLE PRECISION,
    processed BOOLEAN NOT NULL,
    status VARCHAR NOT NULL,
    approved BOOLEAN,
    processed_by VARCHAR,
    rejected_reason VARCHAR,
    error_message VARCHAR,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP
);

-- Table: context_inheritance_cache
CREATE TABLE context_inheritance_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_id UUID NOT NULL,
    context_level VARCHAR NOT NULL,
    context_type VARCHAR NOT NULL,
    resolved_context JSONB NOT NULL,
    resolved_data JSONB NOT NULL,
    dependencies_hash VARCHAR NOT NULL,
    resolution_path VARCHAR NOT NULL,
    parent_chain JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER NOT NULL,
    last_hit TIMESTAMP NOT NULL,
    cache_size_bytes INTEGER NOT NULL,
    invalidated BOOLEAN NOT NULL,
    invalidation_reason VARCHAR,
    user_id VARCHAR NOT NULL
);

-- Table: global_contexts
CREATE TABLE global_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID,
    organization_standards JSONB NOT NULL,
    security_policies JSONB NOT NULL,
    compliance_requirements JSONB NOT NULL,
    shared_resources JSONB NOT NULL,
    reusable_patterns JSONB NOT NULL,
    global_preferences JSONB NOT NULL,
    delegation_rules JSONB NOT NULL,
    nested_structure JSONB NOT NULL,
    unified_context_data JSONB,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER NOT NULL
);

-- Table: labels
CREATE TABLE labels (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    color VARCHAR NOT NULL,
    description TEXT NOT NULL,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Table: missed_notifications
CREATE TABLE missed_notifications (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    delivered BOOLEAN NOT NULL,
    delivery_attempts INTEGER NOT NULL,
    last_attempt_at TIMESTAMP
);

-- Table: project_contexts
CREATE TABLE project_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID,
    parent_global_id UUID,
    data JSONB,
    project_info JSONB,
    team_preferences JSONB,
    technology_stack JSONB,
    project_workflow JSONB,
    local_standards JSONB,
    project_settings JSONB,
    technical_specifications JSONB,
    global_overrides JSONB,
    delegation_rules JSONB,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER,
    inheritance_disabled BOOLEAN
);

-- Table: project_git_branchs
CREATE TABLE project_git_branchs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    assigned_agent_id VARCHAR,
    agent_id UUID,
    priority VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    metadata JSONB NOT NULL,
    task_count INTEGER NOT NULL,
    completed_task_count INTEGER NOT NULL,
    user_id VARCHAR NOT NULL
);

-- Table: projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    user_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    metadata JSONB NOT NULL
);

-- Table: subtasks
CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR NOT NULL,
    priority VARCHAR NOT NULL,
    assignees JSONB NOT NULL,
    estimated_effort VARCHAR,
    progress_percentage INTEGER NOT NULL,
    progress_state VARCHAR NOT NULL,
    progress_notes TEXT NOT NULL,
    blockers TEXT NOT NULL,
    completion_summary TEXT NOT NULL,
    impact_on_parent TEXT NOT NULL,
    insights_found JSONB NOT NULL,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    ai_system_prompt TEXT NOT NULL DEFAULT ''::text,
    ai_request_prompt TEXT NOT NULL DEFAULT ''::text,
    ai_work_context JSONB NOT NULL DEFAULT '{}'::json,
    ai_completion_criteria TEXT NOT NULL DEFAULT ''::text,
    ai_execution_history JSONB NOT NULL DEFAULT '[]'::json,
    ai_last_execution TIMESTAMP,
    ai_model_preferences JSONB NOT NULL DEFAULT '{}'::json,
    progress_history JSONB NOT NULL DEFAULT '{}'::json,
    progress_count INTEGER NOT NULL DEFAULT 0
);

-- Table: task_assignees
CREATE TABLE task_assignees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL,
    assignee_id VARCHAR NOT NULL,
    agent_id UUID,
    role VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    assigned_at TIMESTAMP NOT NULL
);

-- Table: task_contexts
CREATE TABLE task_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID,
    parent_branch_id UUID,
    parent_branch_context_id UUID,
    data JSONB,
    task_data JSONB,
    execution_context JSONB,
    discovered_patterns JSONB,
    implementation_notes JSONB,
    test_results JSONB,
    blockers JSONB,
    local_decisions JSONB,
    delegation_queue JSONB,
    local_overrides JSONB,
    delegation_triggers JSONB,
    inheritance_disabled BOOLEAN,
    force_local_only BOOLEAN,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER
);

-- Table: task_dependencies
CREATE TABLE task_dependencies (
    id INTEGER PRIMARY KEY DEFAULT nextval('task_dependencies_id_seq'::regclass),
    task_id UUID NOT NULL,
    depends_on_task_id UUID NOT NULL,
    dependency_type VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Table: task_labels
CREATE TABLE task_labels (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    label_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    applied_at TIMESTAMP NOT NULL
);

-- Table: tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    git_branch_id UUID NOT NULL,
    status VARCHAR NOT NULL,
    priority VARCHAR NOT NULL,
    progress_history JSONB NOT NULL,
    progress_count INTEGER NOT NULL,
    estimated_effort VARCHAR NOT NULL,
    due_date VARCHAR,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    completion_summary TEXT NOT NULL,
    testing_notes TEXT NOT NULL,
    context_id UUID,
    progress_percentage INTEGER NOT NULL,
    progress_state VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    ai_system_prompt TEXT NOT NULL DEFAULT ''::text,
    ai_request_prompt TEXT NOT NULL DEFAULT ''::text,
    ai_work_context JSONB NOT NULL DEFAULT '{}'::json,
    ai_completion_criteria TEXT NOT NULL DEFAULT ''::text,
    ai_execution_history JSONB NOT NULL DEFAULT '[]'::json,
    ai_last_execution TIMESTAMP,
    ai_model_preferences JSONB NOT NULL DEFAULT '{}'::json,
    completed_subtasks INTEGER DEFAULT 0,
    subtask_count INTEGER DEFAULT 0
);

-- Table: templates
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    template_name VARCHAR NOT NULL,
    template_content TEXT NOT NULL,
    template_type VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    content JSONB NOT NULL,
    category VARCHAR NOT NULL,
    tags JSONB NOT NULL,
    usage_count INTEGER NOT NULL,
    user_id VARCHAR,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    created_by VARCHAR NOT NULL,
    metadata JSONB NOT NULL
);

-- Table: token_transactions
CREATE TABLE token_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    tokens_deducted INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    operation_metadata JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Table: user_agent_configurations_md
CREATE TABLE user_agent_configurations_md (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id UUID NOT NULL,
    configuration_type VARCHAR(50) NOT NULL,
    content_markdown TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Table: user_agent_instances
CREATE TABLE user_agent_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    template_id UUID NOT NULL,
    agent_name VARCHAR(200) NOT NULL,
    is_customized BOOLEAN NOT NULL,
    customization_notes TEXT,
    system_prompt TEXT NOT NULL,
    tools TEXT NOT NULL,
    capabilities TEXT NOT NULL,
    rules TEXT,
    output_format TEXT,
    metadata TEXT,
    visibility VARCHAR(50) NOT NULL,
    share_token VARCHAR(64),
    share_created_at TIMESTAMP,
    original_creator_id UUID,
    imported_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP,
    is_enabled BOOLEAN NOT NULL DEFAULT true
);

-- Table: user_api_tokens
CREATE TABLE user_api_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    token_cost INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    scopes JSONB NOT NULL,
    is_active BOOLEAN NOT NULL,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    revoked_at TIMESTAMP
);

-- Table: user_sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    refresh_token VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_info JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    last_activity TIMESTAMP NOT NULL DEFAULT now(),
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    is_active BOOLEAN NOT NULL
);

-- Table: user_token_balances
CREATE TABLE user_token_balances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    available_tokens INTEGER NOT NULL DEFAULT 0,
    monthly_quota INTEGER NOT NULL DEFAULT 10000,
    last_reset_at TIMESTAMP,
    next_reset_at TIMESTAMP,
    tokens_consumed_today INTEGER NOT NULL DEFAULT 0,
    tokens_consumed_this_month INTEGER NOT NULL DEFAULT 0,
    total_tokens_consumed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Table: users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(254) NOT NULL,
    username VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    roles JSONB NOT NULL,
    email_verified BOOLEAN NOT NULL,
    email_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    failed_login_attempts INTEGER NOT NULL,
    locked_until TIMESTAMP,
    password_changed_at TIMESTAMP,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,
    refresh_token_family VARCHAR(255),
    refresh_token_version INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    created_by VARCHAR(255),
    project_ids JSONB NOT NULL,
    default_project_id UUID,
    metadata JSONB NOT NULL
);

-- ================================================================================
-- FOREIGN KEYS
-- ================================================================================

-- Foreign keys for branch_contexts
ALTER TABLE branch_contexts ADD CONSTRAINT branch_contexts_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES project_git_branchs(id);
ALTER TABLE branch_contexts ADD CONSTRAINT branch_contexts_parent_project_id_fkey FOREIGN KEY (parent_project_id) REFERENCES project_contexts(id);

-- Foreign keys for project_contexts
ALTER TABLE project_contexts ADD CONSTRAINT project_contexts_parent_global_id_fkey FOREIGN KEY (parent_global_id) REFERENCES global_contexts(id);

-- Foreign keys for project_git_branchs
ALTER TABLE project_git_branchs ADD CONSTRAINT project_git_branchs_project_id_fkey FOREIGN KEY (project_id) REFERENCES projects(id);

-- Foreign keys for subtasks
ALTER TABLE subtasks ADD CONSTRAINT subtasks_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);

-- Foreign keys for task_assignees
ALTER TABLE task_assignees ADD CONSTRAINT task_assignees_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);

-- Foreign keys for task_contexts
ALTER TABLE task_contexts ADD CONSTRAINT task_contexts_parent_branch_context_id_fkey FOREIGN KEY (parent_branch_context_id) REFERENCES branch_contexts(id);
ALTER TABLE task_contexts ADD CONSTRAINT task_contexts_parent_branch_id_fkey FOREIGN KEY (parent_branch_id) REFERENCES project_git_branchs(id);
ALTER TABLE task_contexts ADD CONSTRAINT task_contexts_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);

-- Foreign keys for task_dependencies
ALTER TABLE task_dependencies ADD CONSTRAINT task_dependencies_depends_on_task_id_fkey FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id);
ALTER TABLE task_dependencies ADD CONSTRAINT task_dependencies_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);

-- Foreign keys for task_labels
ALTER TABLE task_labels ADD CONSTRAINT task_labels_label_id_fkey FOREIGN KEY (label_id) REFERENCES labels(id);
ALTER TABLE task_labels ADD CONSTRAINT task_labels_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id);

-- Foreign keys for tasks
ALTER TABLE tasks ADD CONSTRAINT tasks_git_branch_id_fkey FOREIGN KEY (git_branch_id) REFERENCES project_git_branchs(id);

-- Foreign keys for token_transactions
ALTER TABLE token_transactions ADD CONSTRAINT token_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

-- Foreign keys for user_api_tokens
ALTER TABLE user_api_tokens ADD CONSTRAINT user_api_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

-- Foreign keys for user_sessions
ALTER TABLE user_sessions ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

-- Foreign keys for user_token_balances
ALTER TABLE user_token_balances ADD CONSTRAINT user_token_balances_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

-- ================================================================================
-- INDEXES
-- ================================================================================

-- Indexes for agent_import_history
CREATE INDEX idx_import_history_date ON agent_import_history (imported_at);
CREATE INDEX idx_import_history_importer ON agent_import_history (importer_user_id);
CREATE INDEX idx_import_history_source ON agent_import_history (source_instance_id);

-- Indexes for agent_templates
CREATE INDEX ix_agent_templates_category ON agent_templates (category);
CREATE INDEX ix_agent_templates_category_version ON agent_templates (category, version);
CREATE UNIQUE INDEX ix_agent_templates_slug ON agent_templates (slug);
CREATE INDEX ix_agent_templates_version ON agent_templates (version);

-- Indexes for agents
CREATE INDEX idx_agent_availability ON agents (availability_score);
CREATE INDEX idx_agent_status ON agents (status);

-- Indexes for context_delegations
CREATE INDEX idx_delegation_processed ON context_delegations (processed);
CREATE INDEX idx_delegation_source ON context_delegations (source_level, source_id);
CREATE INDEX idx_delegation_target ON context_delegations (target_level, target_id);

-- Indexes for context_inheritance_cache
CREATE INDEX idx_cache_expires ON context_inheritance_cache (expires_at);
CREATE INDEX idx_cache_invalidated ON context_inheritance_cache (invalidated);
CREATE INDEX idx_cache_level ON context_inheritance_cache (context_level);
CREATE UNIQUE INDEX uq_cache_context ON context_inheritance_cache (context_id, context_level);

-- Indexes for labels
CREATE UNIQUE INDEX labels_name_key ON labels (name);

-- Indexes for missed_notifications
CREATE INDEX idx_missed_notifications_created_at ON missed_notifications (created_at);
CREATE INDEX idx_missed_notifications_user_delivered ON missed_notifications (user_id, delivered);
CREATE INDEX ix_missed_notifications_delivered ON missed_notifications (delivered);
CREATE INDEX ix_missed_notifications_user_id ON missed_notifications (user_id);

-- Indexes for project_git_branchs
CREATE INDEX idx_branches_updated_at ON project_git_branchs (updated_at);
CREATE UNIQUE INDEX uq_branch_project ON project_git_branchs (id, project_id);

-- Indexes for projects
CREATE INDEX idx_projects_updated_at ON projects (updated_at);
CREATE UNIQUE INDEX uq_project_user ON projects (id, user_id);

-- Indexes for subtasks
CREATE INDEX idx_subtask_status ON subtasks (status);
CREATE INDEX idx_subtask_task ON subtasks (task_id);
CREATE INDEX idx_subtasks_updated_at ON subtasks (updated_at);

-- Indexes for task_assignees
CREATE INDEX idx_assignee_id ON task_assignees (assignee_id);
CREATE INDEX idx_assignee_task ON task_assignees (task_id);
CREATE UNIQUE INDEX uq_task_assignee ON task_assignees (task_id, assignee_id);

-- Indexes for task_dependencies
CREATE UNIQUE INDEX uq_task_dependency ON task_dependencies (task_id, depends_on_task_id);

-- Indexes for task_labels
CREATE INDEX idx_task_label_label ON task_labels (label_id);
CREATE INDEX idx_task_label_task ON task_labels (task_id);

-- Indexes for tasks
CREATE INDEX idx_task_branch ON tasks (git_branch_id);
CREATE INDEX idx_task_created ON tasks (created_at);
CREATE INDEX idx_task_priority ON tasks (priority);
CREATE INDEX idx_task_status ON tasks (status);
CREATE INDEX idx_tasks_progress_count ON tasks (progress_count);
CREATE INDEX idx_tasks_updated_at ON tasks (updated_at);

-- Indexes for templates
CREATE INDEX idx_template_category ON templates (category);
CREATE INDEX idx_template_type ON templates (type);

-- Indexes for token_transactions
CREATE INDEX ix_token_transactions_created_at ON token_transactions (created_at);
CREATE INDEX ix_token_transactions_operation_type ON token_transactions (operation_type);
CREATE INDEX ix_token_transactions_user_created ON token_transactions (user_id, created_at);
CREATE INDEX ix_token_transactions_user_id ON token_transactions (user_id);

-- Indexes for user_agent_configurations_md
CREATE INDEX idx_configurations_md_instance ON user_agent_configurations_md (instance_id, configuration_type);
CREATE UNIQUE INDEX user_agent_configurations_md_instance_type_key ON user_agent_configurations_md (instance_id, configuration_type);

-- Indexes for user_agent_instances
CREATE UNIQUE INDEX ix_user_agent_instances_share_token ON user_agent_instances (share_token);
CREATE INDEX ix_user_agent_instances_template_id ON user_agent_instances (template_id);
CREATE INDEX ix_user_agent_instances_user_enabled ON user_agent_instances (user_id, is_enabled);
CREATE INDEX ix_user_agent_instances_user_id ON user_agent_instances (user_id);
CREATE INDEX ix_user_agent_instances_user_visibility ON user_agent_instances (user_id, visibility);
CREATE INDEX ix_user_agent_instances_visibility ON user_agent_instances (visibility);
CREATE INDEX ix_user_agent_instances_visibility_created ON user_agent_instances (visibility, created_at);
CREATE UNIQUE INDEX uq_user_agent_instances_user_template ON user_agent_instances (user_id, template_id);

-- Indexes for user_api_tokens
CREATE INDEX ix_user_api_tokens_expires_at ON user_api_tokens (expires_at);
CREATE INDEX ix_user_api_tokens_is_active ON user_api_tokens (is_active);
CREATE INDEX ix_user_api_tokens_user_id ON user_api_tokens (user_id);
CREATE UNIQUE INDEX user_api_tokens_token_hash_key ON user_api_tokens (token_hash);

-- Indexes for user_sessions
CREATE INDEX ix_user_sessions_is_active ON user_sessions (is_active);
CREATE INDEX ix_user_sessions_refresh_token ON user_sessions (refresh_token);
CREATE INDEX ix_user_sessions_session_token ON user_sessions (session_token);
CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);
CREATE UNIQUE INDEX user_sessions_refresh_token_key ON user_sessions (refresh_token);
CREATE UNIQUE INDEX user_sessions_session_token_key ON user_sessions (session_token);

-- Indexes for user_token_balances
CREATE INDEX ix_user_token_balances_user_id ON user_token_balances (user_id);
CREATE UNIQUE INDEX user_token_balances_user_id_key ON user_token_balances (user_id);

-- Indexes for users
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_password_reset_token ON users (password_reset_token);
CREATE INDEX ix_users_refresh_token_family ON users (refresh_token_family);
CREATE INDEX ix_users_status ON users (status);
CREATE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX users_email_key ON users (email);
CREATE UNIQUE INDEX users_password_reset_token_key ON users (password_reset_token);
CREATE UNIQUE INDEX users_username_key ON users (username);

-- ================================================================================
-- UNIQUE CONSTRAINTS
-- ================================================================================

-- Unique constraints for context_inheritance_cache
ALTER TABLE context_inheritance_cache ADD CONSTRAINT uq_cache_context UNIQUE (context_id, context_level);

-- Unique constraints for labels
ALTER TABLE labels ADD CONSTRAINT labels_name_key UNIQUE (name);

-- Unique constraints for project_git_branchs
ALTER TABLE project_git_branchs ADD CONSTRAINT uq_branch_project UNIQUE (id, project_id);

-- Unique constraints for projects
ALTER TABLE projects ADD CONSTRAINT uq_project_user UNIQUE (id, user_id);

-- Unique constraints for task_assignees
ALTER TABLE task_assignees ADD CONSTRAINT uq_task_assignee UNIQUE (task_id, assignee_id);

-- Unique constraints for task_dependencies
ALTER TABLE task_dependencies ADD CONSTRAINT uq_task_dependency UNIQUE (task_id, depends_on_task_id);

-- Unique constraints for user_agent_configurations_md
ALTER TABLE user_agent_configurations_md ADD CONSTRAINT user_agent_configurations_md_instance_type_key UNIQUE (instance_id, configuration_type);

-- Unique constraints for user_agent_instances
ALTER TABLE user_agent_instances ADD CONSTRAINT uq_user_agent_instances_user_template UNIQUE (user_id, template_id);

-- Unique constraints for user_api_tokens
ALTER TABLE user_api_tokens ADD CONSTRAINT user_api_tokens_token_hash_key UNIQUE (token_hash);

-- Unique constraints for user_sessions
ALTER TABLE user_sessions ADD CONSTRAINT user_sessions_refresh_token_key UNIQUE (refresh_token);
ALTER TABLE user_sessions ADD CONSTRAINT user_sessions_session_token_key UNIQUE (session_token);

-- Unique constraints for user_token_balances
ALTER TABLE user_token_balances ADD CONSTRAINT user_token_balances_user_id_key UNIQUE (user_id);

-- Unique constraints for users
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE users ADD CONSTRAINT users_password_reset_token_key UNIQUE (password_reset_token);
ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username);

-- ================================================================================
-- TABLE COMMENTS AND DOCUMENTATION
-- ================================================================================

-- Core Tables
COMMENT ON TABLE projects IS 'Main projects - organizational structure for tasks';
COMMENT ON TABLE project_git_branchs IS 'Git branches/task trees - groups of related tasks';
COMMENT ON TABLE tasks IS 'Main tasks with AI Agent system integration and progress tracking';
COMMENT ON TABLE subtasks IS 'Subtasks for granular task breakdown with AI Agent support';

-- AI Agent System Fields
COMMENT ON COLUMN tasks.ai_system_prompt IS 'System prompt for AI agent to understand task context';
COMMENT ON COLUMN tasks.ai_request_prompt IS 'Specific request prompt for AI agent execution';
COMMENT ON COLUMN tasks.ai_work_context IS 'Additional context data for AI work (JSON)';
COMMENT ON COLUMN tasks.ai_completion_criteria IS 'Criteria for AI to determine task completion';
COMMENT ON COLUMN tasks.ai_execution_history IS 'History of AI executions on this task (JSON array)';
COMMENT ON COLUMN tasks.ai_last_execution IS 'Timestamp of last AI execution on this task';
COMMENT ON COLUMN tasks.ai_model_preferences IS 'AI model preferences and configuration (JSON)';

COMMENT ON COLUMN subtasks.ai_system_prompt IS 'System prompt for AI agent to understand subtask context';
COMMENT ON COLUMN subtasks.ai_request_prompt IS 'Specific request prompt for AI agent execution';
COMMENT ON COLUMN subtasks.ai_work_context IS 'Additional context data for AI work (JSON)';
COMMENT ON COLUMN subtasks.ai_completion_criteria IS 'Criteria for AI to determine subtask completion';
COMMENT ON COLUMN subtasks.ai_execution_history IS 'History of AI executions on this subtask (JSON array)';
COMMENT ON COLUMN subtasks.ai_last_execution IS 'Timestamp of last AI execution on this subtask';

-- Progress Tracking
COMMENT ON COLUMN tasks.progress_history IS 'Timestamped progress updates (JSON)';
COMMENT ON COLUMN tasks.progress_count IS 'Number of progress entries for this task';
COMMENT ON COLUMN tasks.progress_percentage IS 'Task completion percentage (0-100)';
COMMENT ON COLUMN tasks.completed_subtasks IS 'Count of completed subtasks';
COMMENT ON COLUMN tasks.subtask_count IS 'Total count of subtasks';

COMMENT ON COLUMN subtasks.progress_history IS 'Timestamped progress updates (JSON)';
COMMENT ON COLUMN subtasks.progress_count IS 'Number of progress entries for this subtask';
COMMENT ON COLUMN subtasks.progress_percentage IS 'Subtask completion percentage (0-100)';

-- Context System
COMMENT ON TABLE global_contexts IS '4-tier context hierarchy - Global level (user-scoped)';
COMMENT ON TABLE project_contexts IS '4-tier context hierarchy - Project level';
COMMENT ON TABLE branch_contexts IS '4-tier context hierarchy - Branch level';
COMMENT ON TABLE task_contexts IS '4-tier context hierarchy - Task level';
COMMENT ON TABLE context_delegations IS 'Context delegation between hierarchy levels';
COMMENT ON TABLE context_inheritance_cache IS 'Cached resolved context with inheritance chain';

-- Agent Management
COMMENT ON TABLE agent_templates IS 'Pre-defined agent templates (33 specialized agents)';
COMMENT ON TABLE user_agent_instances IS 'User-specific agent instances created from templates';
COMMENT ON TABLE agent_import_history IS 'History of agent imports between users';
COMMENT ON TABLE agents IS 'Legacy agent tracking table';

-- Authentication & Authorization
COMMENT ON TABLE users IS 'User accounts and authentication';
COMMENT ON TABLE user_sessions IS 'Active user sessions with tokens';
COMMENT ON TABLE api_tokens IS 'API tokens for MCP authentication';
COMMENT ON TABLE user_token_balances IS 'User token balance tracking';

-- Notifications
COMMENT ON TABLE missed_notifications IS 'WebSocket notifications missed during disconnection for replay';

-- ================================================================================
-- ARCHITECTURE NOTES
-- ================================================================================

-- FOREIGN KEY BEHAVIOR:
-- All foreign keys use default ON DELETE NO ACTION behavior
-- Deletion cascades are handled explicitly in the application domain layer
-- This ensures business logic remains in code, not in database constraints
-- Application layer handles cleanup when:
--   • Projects deleted → branches → tasks → subtasks/assignees/labels/dependencies
--   • Context hierarchy deletions handled through domain services

-- NO SQL TRIGGERS OR FUNCTIONS:
-- Task counts, subtask counts, and all business logic handled in application domain layer
-- Ensures clean architecture with business rules in code, not database
-- Domain events trigger cascading operations when needed

-- TIMESTAMP MANAGEMENT:
-- created_at/updated_at managed by SQLAlchemy event handlers (timestamp_events.py)
-- completed_at manually set when status changes to 'done'
-- All timestamps stored in UTC

-- UUID TYPE:
-- Uses native PostgreSQL UUID type with uuid_generate_v4() defaults
-- UnifiedUUID type decorator in ORM handles SQLite compatibility (VARCHAR(36))

-- ================================================================================
-- SCHEMA GENERATION COMPLETE
-- ================================================================================

SELECT 'AGENTHUB POSTGRESQL DATABASE SCHEMA GENERATED' as status;