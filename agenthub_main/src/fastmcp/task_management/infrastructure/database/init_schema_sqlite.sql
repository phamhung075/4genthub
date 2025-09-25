-- ========================================
-- AGENTHUB COMPLETE DATABASE SCHEMA - SQLITE
-- ========================================
-- Version: 1.0 (2025-09-25)
-- Description: Complete database initialization with ALL tables, indexes, constraints, and triggers
-- Database: SQLite 3.8+
-- Includes: All ORM models + AI Agent fields + Context system + Task count triggers
-- ========================================

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
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    scopes TEXT DEFAULT '[]',  -- JSON as TEXT
    created_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    rate_limit INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT 1,
    token_metadata TEXT DEFAULT '{}'  -- JSON as TEXT
);

-- Projects table
CREATE TABLE projects (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    metadata TEXT DEFAULT '{}'  -- JSON as TEXT
);

-- Project Git Branches table (task trees)
CREATE TABLE project_git_branchs (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    assigned_agent_id TEXT,
    agent_id TEXT,  -- UUID as TEXT
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'todo',
    metadata TEXT DEFAULT '{}',  -- JSON as TEXT
    task_count INTEGER DEFAULT 0,
    completed_task_count INTEGER DEFAULT 0,
    user_id TEXT NOT NULL
);

-- Tasks table (with AI Agent fields)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    title TEXT NOT NULL CHECK (LENGTH(title) <= 200),
    description TEXT NOT NULL CHECK (LENGTH(description) <= 2000),
    git_branch_id TEXT NOT NULL REFERENCES project_git_branchs(id),
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    progress_history TEXT DEFAULT '{}',  -- JSON as TEXT
    progress_count INTEGER DEFAULT 0,
    estimated_effort TEXT DEFAULT '2 hours' NOT NULL,
    due_date TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    completion_summary TEXT DEFAULT '',
    testing_notes TEXT DEFAULT '',
    context_id TEXT,  -- UUID as TEXT
    progress_percentage INTEGER DEFAULT 0,
    progress_state TEXT DEFAULT 'INITIAL' NOT NULL,
    subtask_count INTEGER DEFAULT 0,
    user_id TEXT NOT NULL,

    -- AI Agent System Fields
    ai_system_prompt TEXT DEFAULT '',
    ai_request_prompt TEXT DEFAULT '',
    ai_work_context TEXT DEFAULT '{}',  -- JSON as TEXT
    ai_completion_criteria TEXT DEFAULT '',
    ai_execution_history TEXT DEFAULT '[]',  -- JSON as TEXT
    ai_last_execution TIMESTAMP,
    ai_model_preferences TEXT DEFAULT '{}'  -- JSON as TEXT
);

-- Subtasks table (with AI Agent fields)
CREATE TABLE subtasks (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    task_id TEXT NOT NULL REFERENCES tasks(id),
    title TEXT NOT NULL CHECK (LENGTH(title) <= 200),
    description TEXT DEFAULT '' CHECK (LENGTH(description) <= 500),
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    assignees TEXT DEFAULT '[]',  -- JSON as TEXT
    estimated_effort TEXT,
    progress_percentage INTEGER DEFAULT 0,
    progress_state TEXT DEFAULT 'INITIAL' NOT NULL,
    progress_notes TEXT DEFAULT '',
    blockers TEXT DEFAULT '',
    completion_summary TEXT DEFAULT '',
    impact_on_parent TEXT DEFAULT '',
    insights_found TEXT DEFAULT '[]',  -- JSON as TEXT
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- AI Agent System Fields
    ai_system_prompt TEXT DEFAULT '',
    ai_request_prompt TEXT DEFAULT '',
    ai_work_context TEXT DEFAULT '{}',  -- JSON as TEXT
    ai_completion_criteria TEXT DEFAULT '',
    ai_execution_history TEXT DEFAULT '[]',  -- JSON as TEXT
    ai_last_execution TIMESTAMP,
    ai_model_preferences TEXT DEFAULT '{}'  -- JSON as TEXT
);

-- Task Assignees table
CREATE TABLE task_assignees (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    task_id TEXT NOT NULL REFERENCES tasks(id),
    assignee_id TEXT NOT NULL,
    agent_id TEXT,  -- UUID as TEXT
    role TEXT DEFAULT 'contributor',
    user_id TEXT NOT NULL,
    assigned_at TIMESTAMP );

-- Task Dependencies table
CREATE TABLE task_dependencies (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    task_id TEXT NOT NULL REFERENCES tasks(id),
    depends_on_task_id TEXT NOT NULL REFERENCES tasks(id),
    dependency_type TEXT DEFAULT 'blocks',
    user_id TEXT NOT NULL,
    created_at TIMESTAMP );

-- Agents table
CREATE TABLE agents (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    role TEXT DEFAULT 'assistant',
    capabilities TEXT DEFAULT '[]',  -- JSON as TEXT
    status TEXT DEFAULT 'available',
    availability_score REAL DEFAULT 1.0,
    last_active_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata TEXT DEFAULT '{}',  -- JSON as TEXT
    user_id TEXT NOT NULL
);

-- Labels table
CREATE TABLE labels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#0066cc',
    description TEXT DEFAULT '',
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP );

-- Task Labels junction table
CREATE TABLE task_labels (
    task_id TEXT REFERENCES tasks(id),
    label_id TEXT REFERENCES labels(id),
    user_id TEXT NOT NULL,
    applied_at TIMESTAMP,
    PRIMARY KEY (task_id, label_id)
);

-- Templates table
CREATE TABLE templates (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    name TEXT NOT NULL,
    template_name TEXT NOT NULL DEFAULT '',
    template_content TEXT DEFAULT '',
    template_type TEXT DEFAULT 'general',
    type TEXT NOT NULL,
    content TEXT NOT NULL,  -- JSON as TEXT
    category TEXT DEFAULT 'general',
    tags TEXT DEFAULT '[]',  -- JSON as TEXT
    usage_count INTEGER DEFAULT 0,
    user_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'  -- JSON as TEXT
);

-- ========================================
-- CONTEXT SYSTEM TABLES
-- ========================================

-- Global Contexts table
CREATE TABLE global_contexts (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    organization_id TEXT,  -- UUID as TEXT
    organization_standards TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    security_policies TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    compliance_requirements TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    shared_resources TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    reusable_patterns TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    global_preferences TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    delegation_rules TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    nested_structure TEXT NOT NULL DEFAULT '{}',  -- JSON as TEXT
    unified_context_data TEXT DEFAULT '{}',  -- JSON as TEXT
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Project Contexts table
CREATE TABLE project_contexts (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    project_id TEXT,  -- UUID as TEXT
    parent_global_id TEXT REFERENCES global_contexts(id),
    data TEXT DEFAULT '{}',  -- JSON as TEXT
    project_info TEXT DEFAULT '{}',  -- JSON as TEXT
    team_preferences TEXT DEFAULT '{}',  -- JSON as TEXT
    technology_stack TEXT DEFAULT '{}',  -- JSON as TEXT
    project_workflow TEXT DEFAULT '{}',  -- JSON as TEXT
    local_standards TEXT DEFAULT '{}',  -- JSON as TEXT
    project_settings TEXT DEFAULT '{}',  -- JSON as TEXT
    technical_specifications TEXT DEFAULT '{}',  -- JSON as TEXT
    global_overrides TEXT DEFAULT '{}',  -- JSON as TEXT
    delegation_rules TEXT DEFAULT '{}',  -- JSON as TEXT
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1,
    inheritance_disabled BOOLEAN DEFAULT 0
);

-- Branch Contexts table
CREATE TABLE branch_contexts (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    branch_id TEXT REFERENCES project_git_branchs(id),
    parent_project_id TEXT REFERENCES project_contexts(id),
    data TEXT DEFAULT '{}',  -- JSON as TEXT
    branch_info TEXT DEFAULT '{}',  -- JSON as TEXT
    branch_workflow TEXT DEFAULT '{}',  -- JSON as TEXT
    feature_flags TEXT DEFAULT '{}',  -- JSON as TEXT
    discovered_patterns TEXT DEFAULT '{}',  -- JSON as TEXT
    branch_decisions TEXT DEFAULT '{}',  -- JSON as TEXT
    active_patterns TEXT DEFAULT '{}',  -- JSON as TEXT
    local_overrides TEXT DEFAULT '{}',  -- JSON as TEXT
    delegation_rules TEXT DEFAULT '{}',  -- JSON as TEXT
    inheritance_disabled BOOLEAN DEFAULT 0,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Task Contexts table
CREATE TABLE task_contexts (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    task_id TEXT REFERENCES tasks(id),
    parent_branch_id TEXT REFERENCES project_git_branchs(id),
    parent_branch_context_id TEXT REFERENCES branch_contexts(id),
    data TEXT DEFAULT '{}',  -- JSON as TEXT
    task_data TEXT DEFAULT '{}',  -- JSON as TEXT
    execution_context TEXT DEFAULT '{}',  -- JSON as TEXT
    discovered_patterns TEXT DEFAULT '{}',  -- JSON as TEXT
    implementation_notes TEXT DEFAULT '{}',  -- JSON as TEXT
    test_results TEXT DEFAULT '{}',  -- JSON as TEXT
    blockers TEXT DEFAULT '{}',  -- JSON as TEXT
    local_decisions TEXT DEFAULT '{}',  -- JSON as TEXT
    delegation_queue TEXT DEFAULT '{}',  -- JSON as TEXT
    local_overrides TEXT DEFAULT '{}',  -- JSON as TEXT
    delegation_triggers TEXT DEFAULT '{}',  -- JSON as TEXT
    inheritance_disabled BOOLEAN DEFAULT 0,
    force_local_only BOOLEAN DEFAULT 0,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Context Delegations table
CREATE TABLE context_delegations (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    source_level TEXT NOT NULL CHECK (source_level IN ('task', 'branch', 'project', 'global')),
    source_id TEXT NOT NULL,  -- UUID as TEXT
    source_type TEXT DEFAULT 'context',
    target_level TEXT NOT NULL CHECK (target_level IN ('task', 'branch', 'project', 'global')),
    target_id TEXT NOT NULL,  -- UUID as TEXT
    target_type TEXT DEFAULT 'context',
    delegated_data TEXT NOT NULL,  -- JSON as TEXT
    delegation_data TEXT DEFAULT '{}',  -- JSON as TEXT
    delegation_reason TEXT NOT NULL,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'auto_pattern', 'auto_threshold')),
    auto_delegated BOOLEAN DEFAULT 0,
    confidence_score REAL,
    processed BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'pending',
    approved BOOLEAN,
    processed_by TEXT,
    rejected_reason TEXT,
    error_message TEXT,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP,
    processed_at TIMESTAMP
);

-- Context Inheritance Cache table
CREATE TABLE context_inheritance_cache (
    id TEXT PRIMARY KEY,  -- UUID as TEXT
    context_id TEXT NOT NULL,  -- UUID as TEXT
    context_level TEXT NOT NULL CHECK (context_level IN ('task', 'branch', 'project', 'global')),
    context_type TEXT DEFAULT 'hierarchical',
    resolved_context TEXT NOT NULL,  -- JSON as TEXT
    resolved_data TEXT DEFAULT '{}',  -- JSON as TEXT
    dependencies_hash TEXT NOT NULL,
    resolution_path TEXT NOT NULL,
    parent_chain TEXT DEFAULT '[]',  -- JSON as TEXT
    created_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit TIMESTAMP,
    cache_size_bytes INTEGER NOT NULL,
    invalidated BOOLEAN DEFAULT 0,
    invalidation_reason TEXT,
    user_id TEXT NOT NULL,
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
-- NO SQL TRIGGERS
-- ========================================
-- All task counts, subtask counts, and cascade deletions are
-- handled in the domain layer through domain services and events.
-- This ensures clean architecture and business logic stays in code,
-- not in the database.

-- ========================================
-- NO VIEWS OR MATERIALIZED VIEWS
-- ========================================
-- All statistics and summaries are calculated in the domain layer
-- through domain services. This ensures business logic stays in code,
-- not in the database, maintaining clean architecture.


-- Database initialization complete
SELECT 'AGENTHUB SQLITE DATABASE INITIALIZED SUCCESSFULLY' as status;