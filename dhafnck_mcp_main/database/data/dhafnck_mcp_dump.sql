PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT NOT NULL DEFAULT 'default_id',
    status TEXT DEFAULT 'active',
    metadata TEXT DEFAULT '{}',
    UNIQUE(id, user_id)
);
INSERT INTO projects VALUES('default_project','DhafnckMCP System','Main system project for DhafnckMCP task management and AI agent coordination','2025-07-16 07:44:51','2025-07-16 07:44:51','system','active','{"project_type":"system","priority":"critical","environment":"production","auto_created":true}');
CREATE TABLE project_git_branchs (
    id TEXT PRIMARY KEY,  -- UUID
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_agent_id TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'todo',
    metadata TEXT DEFAULT '{}',
    task_count INTEGER DEFAULT 0,
    completed_task_count INTEGER DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(id, project_id)
);
INSERT INTO project_git_branchs VALUES('main_branch','default_project','main','Main development branch for system tasks','2025-07-16 07:44:51','2025-07-16 07:44:51','master-orchestrator-agent','high','active','{"branch_type":"main","auto_created":true,"protected":true}',0,0);
CREATE TABLE tasks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    git_branch_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    details TEXT DEFAULT '',
    estimated_effort TEXT DEFAULT '',
    due_date TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context_id TEXT,
    FOREIGN KEY (git_branch_id) REFERENCES project_git_branchs(id) ON DELETE CASCADE
);
CREATE TABLE task_subtasks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    assignees TEXT DEFAULT '[]',
    estimated_effort TEXT,
    progress_percentage INTEGER DEFAULT 0,
    progress_notes TEXT DEFAULT '',
    blockers TEXT DEFAULT '',
    completion_summary TEXT DEFAULT '',
    impact_on_parent TEXT DEFAULT '',
    insights_found TEXT DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE TABLE task_assignees (
    task_id TEXT NOT NULL,
    assignee TEXT NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, assignee),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE TABLE task_dependencies (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    dependency_type TEXT DEFAULT 'blocks',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE(task_id, depends_on_task_id)
);
CREATE TABLE project_cross_tree_dependencies (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    project_id TEXT NOT NULL,
    dependent_task_id TEXT NOT NULL,
    prerequisite_task_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (dependent_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE(project_id, dependent_task_id, prerequisite_task_id)
);
CREATE TABLE project_work_sessions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    project_id TEXT NOT NULL,
    agent_id TEXT,
    task_id TEXT,
    git_branch_id TEXT,
    status TEXT DEFAULT 'active',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    max_duration_hours INTEGER DEFAULT 8,
    notes TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    FOREIGN KEY (git_branch_id) REFERENCES project_git_branchs(id) ON DELETE SET NULL
);
CREATE TABLE project_resource_locks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    project_id TEXT NOT NULL,
    resource_name TEXT NOT NULL,
    locked_by_agent_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    notes TEXT DEFAULT '',
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, resource_name)
);
CREATE TABLE project_agents (
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    call_agent TEXT,
    capabilities TEXT DEFAULT '[]',
    specializations TEXT DEFAULT '[]',
    preferred_languages TEXT DEFAULT '[]',
    preferred_frameworks TEXT DEFAULT '[]',
    status TEXT DEFAULT 'available',
    max_concurrent_tasks INTEGER DEFAULT 1,
    current_workload INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    average_task_duration REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 100.0,
    work_hours TEXT DEFAULT '{}',
    timezone TEXT DEFAULT 'UTC',
    priority_preference TEXT DEFAULT 'high',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, project_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
INSERT INTO project_agents VALUES('master-orchestrator-agent','default_project','Uber Orchestrator Agent','Primary coordination agent for complex multi-step workflows and system orchestration','master-orchestrator-agent','["orchestration","coordination","planning","decision_making","workflow_management"]','["complex_workflows","multi_agent_coordination","strategic_planning","resource_allocation"]','[]','[]','available',10,0,0,0.0,100.0,'{}','UTC','high','2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO project_agents VALUES('@task_planning_agent','default_project','Task Planning Agent','Specialized agent for breaking down complex tasks and creating execution plans','@task_planning_agent','["task_decomposition","planning","estimation","dependency_analysis"]','["project_planning","task_breakdown","workflow_design","resource_planning"]','[]','[]','available',5,0,0,0.0,100.0,'{}','UTC','high','2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO project_agents VALUES('@coding_agent','default_project','Coding Agent','Development agent for implementing features and writing code','@coding_agent','["programming","implementation","code_writing","debugging"]','["python","typescript","api_development","database_design"]','[]','[]','available',3,0,0,0.0,100.0,'{}','UTC','high','2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO project_agents VALUES('@test_orchestrator_agent','default_project','Test Orchestrator Agent','Testing coordination agent for quality assurance and test automation','@test_orchestrator_agent','["testing","quality_assurance","test_automation","validation"]','["unit_testing","integration_testing","test_planning","qa_coordination"]','[]','[]','available',5,0,0,0.0,100.0,'{}','UTC','high','2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO project_agents VALUES('@system_architect_agent','default_project','System Architect Agent','Architecture and design agent for system design and technical decision making','@system_architect_agent','["architecture","system_design","technical_planning","pattern_recognition"]','["system_architecture","design_patterns","scalability","performance"]','[]','[]','available',3,0,0,0.0,100.0,'{}','UTC','high','2025-07-16 07:44:51','2025-07-16 07:44:51');
CREATE TABLE project_agent_assignments (
    project_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    git_branch_id TEXT NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, agent_id, git_branch_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id, project_id) REFERENCES project_agents(id, project_id) ON DELETE CASCADE,
    FOREIGN KEY (git_branch_id) REFERENCES project_git_branchs(id) ON DELETE CASCADE
);
CREATE TABLE global_contexts (
    id TEXT PRIMARY KEY DEFAULT 'global_singleton',
    organization_id TEXT NOT NULL DEFAULT 'default_org',
    
    -- Core organizational configuration
    autonomous_rules JSONB NOT NULL DEFAULT '{
        "ai_enabled": true,
        "auto_task_creation": true,
        "context_switching_threshold": 70,
        "completion_protection_threshold": 70,
        "emergency_override_threshold": 200,
        "decision_confidence_minimum": 50
    }',
    
    security_policies JSONB NOT NULL DEFAULT '{
        "mfa_required": false,
        "secure_coding_required": true,
        "audit_trail_enabled": true,
        "compliance_checks": ["basic"]
    }',
    
    coding_standards JSONB NOT NULL DEFAULT '{
        "style": "typescript_strict",
        "review_required": true,
        "test_coverage_minimum": 80,
        "documentation_required": true
    }',
    
    workflow_templates JSONB NOT NULL DEFAULT '{
        "estimation_required": true,
        "subtask_creation": "encouraged",
        "completion_summary_required": true,
        "progress_tracking_interval": 1800
    }',
    
    -- Delegation configuration
    delegation_rules JSONB NOT NULL DEFAULT '{
        "auto_delegate": {
            "security_issues": true,
            "compliance_violations": true,
            "reusable_patterns": true,
            "critical_insights": true
        },
        "thresholds": {
            "task_failure_rate": 0.3,
            "performance_critical": true,
            "security_critical": true
        },
        "escalation": {
            "max_retry_attempts": 3,
            "escalation_timeout": 3600
        }
    }',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    last_propagated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO global_contexts VALUES('global_singleton','dhafnck_mcp_org','{"ai_enabled":true,"auto_task_creation":true,"context_switching_threshold":70,"completion_protection_threshold":70,"emergency_override_threshold":200,"decision_confidence_minimum":50,"autonomous_operation":true,"agent_coordination_enabled":true,"workflow_automation":true,"smart_delegation":true}','{"mfa_required":false,"secure_coding_required":true,"audit_trail_enabled":true,"compliance_checks":["basic","security","performance"],"vulnerability_scanning":true,"access_control":"role_based","data_encryption":"at_rest_and_transit","audit_retention_days":365}','{"style":"python_pep8","review_required":true,"test_coverage_minimum":80,"documentation_required":true,"code_complexity_max":10,"function_length_max":50,"class_length_max":500,"naming_conventions":{"variables":"snake_case","functions":"snake_case","classes":"PascalCase","constants":"UPPER_SNAKE_CASE","files":"snake_case"}}','{"estimation_required":true,"subtask_creation":"encouraged","completion_summary_required":true,"progress_tracking_interval":1800,"checklist_automation":true,"template_usage":"recommended","context_inheritance":true,"performance_monitoring":true}','{"auto_delegate":{"security_issues":true,"compliance_violations":true,"reusable_patterns":true,"critical_insights":true,"performance_optimizations":true,"architectural_decisions":true},"thresholds":{"task_failure_rate":0.3,"performance_critical":true,"security_critical":true,"complexity_threshold":8,"duration_threshold_hours":24},"escalation":{"max_retry_attempts":3,"escalation_timeout":3600,"auto_reassignment":true,"notify_stakeholders":true}}','2025-07-16 07:44:51','2025-07-16 07:44:51',1,'2025-07-16 07:44:51');
CREATE TABLE project_contexts (
    project_id TEXT PRIMARY KEY,
    parent_global_id TEXT DEFAULT 'global_singleton',
    
    -- Project-specific configuration
    team_preferences JSONB NOT NULL DEFAULT '{
        "default_priority": "medium",
        "auto_assign_enabled": false,
        "notification_preferences": {
            "email": true,
            "slack": false
        },
        "working_hours": {
            "timezone": "UTC",
            "start": "09:00",
            "end": "17:00"
        }
    }',
    
    technology_stack JSONB NOT NULL DEFAULT '{
        "backend": ["python", "fastapi"],
        "frontend": ["typescript", "react"],
        "database": ["sqlite", "postgresql"],
        "infrastructure": ["docker", "github_actions"],
        "monitoring": ["prometheus", "grafana"]
    }',
    
    project_workflow JSONB NOT NULL DEFAULT '{
        "branch_strategy": "git_flow",
        "ci_cd_pipeline": "github_actions",
        "deployment_strategy": "blue_green",
        "testing_strategy": "pyramid",
        "code_review": {
            "required": true,
            "min_reviewers": 1,
            "approval_required": true
        }
    }',
    
    local_standards JSONB NOT NULL DEFAULT '{
        "naming_conventions": {
            "variables": "snake_case",
            "functions": "snake_case",
            "classes": "PascalCase",
            "files": "snake_case"
        },
        "code_organization": {
            "max_file_lines": 500,
            "max_function_lines": 50,
            "max_class_methods": 20
        }
    }',
    
    -- Override capabilities for global settings
    global_overrides JSONB NOT NULL DEFAULT '{}',
    
    -- Project-specific delegation rules
    delegation_rules JSONB NOT NULL DEFAULT '{
        "delegate_to_global": {
            "security_patterns": true,
            "reusable_components": true,
            "architectural_decisions": true,
            "compliance_patterns": true
        },
        "bubble_up_thresholds": {
            "task_failure_rate": 0.3,
            "performance_issues": "critical",
            "security_vulnerabilities": "any",
            "compliance_violations": "any"
        },
        "retention_policies": {
            "keep_successful_patterns": true,
            "archive_failed_approaches": true,
            "document_lessons_learned": true
        }
    }',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    last_inherited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    inheritance_disabled BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_global_id) REFERENCES global_contexts(id)
);
INSERT INTO project_contexts VALUES('default_project','global_singleton','{"default_priority":"medium","auto_assign_enabled":true,"notification_preferences":{"email":false,"slack":false,"system":true},"working_hours":{"timezone":"UTC","start":"00:00","end":"23:59","continuous_operation":true},"team_size":"ai_agents","collaboration_style":"autonomous"}','{"backend":["python","fastapi","sqlite"],"frontend":["typescript","react"],"database":["sqlite","postgresql"],"infrastructure":["docker","github_actions"],"monitoring":["prometheus","grafana"],"ai_framework":["transformers","llama","openai"],"mcp_tools":["dhafnck_mcp","task_management"],"testing":["pytest","unittest","integration"]}','{"branch_strategy":"git_flow","ci_cd_pipeline":"github_actions","deployment_strategy":"rolling","testing_strategy":"pyramid","code_review":{"required":true,"min_reviewers":1,"approval_required":true,"automated_checks":true},"automation":{"task_creation":true,"progress_tracking":true,"completion_detection":true,"error_handling":true}}','{"naming_conventions":{"variables":"snake_case","functions":"snake_case","classes":"PascalCase","files":"snake_case","modules":"snake_case"},"code_organization":{"max_file_lines":1000,"max_function_lines":100,"max_class_methods":30,"architecture":"domain_driven_design"},"ai_specific":{"context_awareness":true,"autonomous_decision_making":true,"learning_enabled":true,"adaptation_allowed":true}}','{}','{"delegate_to_global":{"security_patterns":true,"reusable_components":true,"architectural_decisions":true,"compliance_patterns":true,"ai_insights":true,"performance_optimizations":true},"bubble_up_thresholds":{"task_failure_rate":0.2,"performance_issues":"critical","security_vulnerabilities":"any","compliance_violations":"any","ai_learning_opportunities":"significant"},"retention_policies":{"keep_successful_patterns":true,"archive_failed_approaches":true,"document_lessons_learned":true,"share_ai_insights":true}}','2025-07-16 07:44:51','2025-07-16 07:44:51',1,'2025-07-16 07:44:51',0);
CREATE TABLE task_contexts (
    task_id TEXT PRIMARY KEY,
    
    -- Hierarchy relationships
    parent_project_id TEXT NOT NULL,
    parent_project_context_id TEXT NOT NULL,
    
    -- Task-specific data
    task_data JSONB NOT NULL DEFAULT '{
        "metadata": {},
        "objective": {},
        "requirements": {},
        "technical": {},
        "dependencies": {},
        "progress": {},
        "subtasks": {},
        "notes": {}
    }',
    
    -- Local overrides for inherited settings
    local_overrides JSONB NOT NULL DEFAULT '{}',
    
    -- Implementation and execution details
    implementation_notes JSONB NOT NULL DEFAULT '{
        "approach": "",
        "challenges": [],
        "solutions": [],
        "decisions": [],
        "learnings": []
    }',
    
    -- Delegation configuration and triggers
    delegation_triggers JSONB NOT NULL DEFAULT '{
        "patterns": {
            "security_discovery": "global",
            "team_improvement": "project",
            "reusable_utility": "project",
            "architectural_insight": "global",
            "performance_optimization": "project"
        },
        "auto_delegate": {
            "critical_errors": true,
            "security_vulnerabilities": true,
            "performance_bottlenecks": true,
            "reusable_patterns": true
        },
        "thresholds": {
            "completion_time_exceeded": 2.0,
            "error_rate_threshold": 0.1,
            "performance_degradation": 0.2
        }
    }',
    
    -- Inheritance control
    inheritance_disabled BOOLEAN DEFAULT FALSE,
    force_local_only BOOLEAN DEFAULT FALSE,
    custom_inheritance_rules JSONB DEFAULT '{}',
    
    -- Performance optimization (cached resolved context)
    resolved_context JSONB DEFAULT NULL,
    resolved_at TIMESTAMP DEFAULT NULL,
    dependencies_hash TEXT DEFAULT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    last_inherited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_project_context_id) REFERENCES project_contexts(project_id),
    FOREIGN KEY (parent_project_id) REFERENCES projects(id)
);
CREATE TABLE context_insights (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    context_id TEXT NOT NULL,
    context_type TEXT NOT NULL CHECK (context_type IN ('global', 'project', 'task')),
    
    -- Insight content
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    importance TEXT DEFAULT 'medium' CHECK (importance IN ('low', 'medium', 'high', 'critical')),
    confidence_score REAL DEFAULT 0.5,
    
    -- Source information
    source_agent TEXT DEFAULT 'system',
    source_type TEXT DEFAULT 'analysis',
    related_task_id TEXT,
    
    -- Workflow integration
    actionable BOOLEAN DEFAULT FALSE,
    action_taken BOOLEAN DEFAULT FALSE,
    action_result TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    accessed_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    
    FOREIGN KEY (related_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);
CREATE TABLE context_delegations (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    
    -- Source and target identification
    source_level TEXT NOT NULL CHECK (source_level IN ('task', 'project', 'global')),
    source_id TEXT NOT NULL,
    target_level TEXT NOT NULL CHECK (target_level IN ('task', 'project', 'global')),
    target_id TEXT NOT NULL,
    
    -- Delegation content and metadata
    delegated_data JSONB NOT NULL,
    delegation_reason TEXT NOT NULL,
    trigger_type TEXT DEFAULT 'manual' CHECK (trigger_type IN ('manual', 'auto_threshold', 'auto_pattern', 'ai_initiated')),
    confidence_score REAL DEFAULT NULL,
    
    -- Processing status and workflow
    auto_delegated BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,
    approved BOOLEAN DEFAULT NULL,
    rejected_reason TEXT DEFAULT NULL,
    
    -- Impact tracking
    impact_assessment JSONB DEFAULT '{}',
    implementation_status TEXT DEFAULT 'pending' CHECK (implementation_status IN ('pending', 'implemented', 'rejected', 'expired')),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NULL,
    implemented_at TIMESTAMP DEFAULT NULL,
    created_by TEXT DEFAULT 'system',
    processed_by TEXT DEFAULT NULL
);
CREATE TABLE context_inheritance_cache (
    context_id TEXT NOT NULL,
    context_level TEXT NOT NULL CHECK (context_level IN ('task', 'project', 'global')),
    
    -- Cached resolved context data
    resolved_context JSONB NOT NULL,
    dependencies_hash TEXT NOT NULL,
    resolution_path TEXT NOT NULL,
    
    -- Cache metadata and performance tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_size_bytes INTEGER DEFAULT 0,
    
    -- Cache invalidation tracking
    invalidated BOOLEAN DEFAULT FALSE,
    invalidation_reason TEXT DEFAULT NULL,
    
    PRIMARY KEY (context_id, context_level)
);
CREATE TABLE context_propagations (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    
    -- Source of change
    source_level TEXT NOT NULL CHECK (source_level IN ('task', 'project', 'global')),
    source_id TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'delete', 'delegation')),
    
    -- Affected contexts
    affected_contexts JSONB NOT NULL,
    
    -- Change details
    changes_summary JSONB NOT NULL,
    propagation_rules_applied JSONB DEFAULT '{}',
    
    -- Status tracking
    propagation_status TEXT DEFAULT 'pending' CHECK (propagation_status IN ('pending', 'in_progress', 'completed', 'failed')),
    completion_percentage REAL DEFAULT 0.0,
    error_details JSONB DEFAULT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP DEFAULT NULL,
    completed_at TIMESTAMP DEFAULT NULL,
    duration_ms INTEGER DEFAULT NULL
);
CREATE TABLE labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    normalized TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT 'custom',
    usage_count INTEGER DEFAULT 0,
    is_common BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO labels VALUES(621,'bug','bug','type',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(622,'feature','feature','type',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(623,'enhancement','enhancement','type',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(624,'documentation','documentation','type',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(625,'refactor','refactor','type',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(626,'test','test','type',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(627,'security','security','priority',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(628,'performance','performance','priority',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(629,'ui','ui','component',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(630,'frontend','frontend','component',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(631,'backend','backend','component',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(632,'database','database','component',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(633,'api','api','component',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(634,'urgent','urgent','priority',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(635,'low-priority','low_priority','priority',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(636,'blocked','blocked','status',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(637,'ready','ready','status',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(638,'review','review','status',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(639,'testing','testing','status',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(640,'ai','ai','technology',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(641,'automation','automation','technology',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(642,'mcp','mcp','technology',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(643,'agent','agent','technology',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(644,'context','context','technology',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(645,'workflow','workflow','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(646,'delegation','delegation','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(647,'coordination','coordination','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(648,'monitoring','monitoring','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(649,'optimization','optimization','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(650,'integration','integration','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO labels VALUES(651,'deployment','deployment','process',0,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
CREATE TABLE task_labels (
    task_id TEXT NOT NULL,
    label_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, label_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
);
CREATE TABLE templates (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    content JSONB NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    tags TEXT DEFAULT '[]',
    version INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    estimated_duration INTEGER DEFAULT NULL,
    complexity_score INTEGER DEFAULT 1,
    created_by TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT NULL
);
INSERT INTO templates VALUES('feature_implementation_template','Feature Implementation','task','{"title_pattern":"Implement {feature_name}","description_template":"Implement the {feature_name} feature according to specifications.\n\nRequirements:\n- {requirements}\n\nAcceptance Criteria:\n- {acceptance_criteria}\n\nTechnical Notes:\n- {technical_notes}","default_priority":"medium","estimated_effort":"TBD","default_labels":["feature","implementation"],"checklist_id":"feature_implementation_checklist","subtask_templates":["Design feature architecture","Implement core functionality","Add unit tests","Integration testing","Documentation update"]}','Template for implementing new features','development','["feature","implementation","development"]',1,1,0,0.0,NULL,1,'system','2025-07-16 07:44:51','2025-07-16 07:44:51',NULL);
INSERT INTO templates VALUES('bug_fix_template','Bug Fix','task','{"title_pattern":"Fix: {bug_description}","description_template":"Bug Description:\n{bug_description}\n\nSteps to Reproduce:\n1. {step1}\n2. {step2}\n3. {step3}\n\nExpected Behavior:\n{expected_behavior}\n\nActual Behavior:\n{actual_behavior}\n\nRoot Cause Analysis:\n{root_cause}","default_priority":"high","estimated_effort":"TBD","default_labels":["bug","fix"],"checklist_id":"bug_fix_checklist","subtask_templates":["Reproduce and analyze bug","Identify root cause","Implement fix","Test fix thoroughly","Regression testing"]}','Template for fixing bugs and issues','maintenance','["bug","fix","maintenance"]',1,1,0,0.0,NULL,1,'system','2025-07-16 07:44:51','2025-07-16 07:44:51',NULL);
INSERT INTO templates VALUES('research_template','Research Task','task','{"title_pattern":"Research: {research_topic}","description_template":"Research Topic: {research_topic}\n\nObjectives:\n- {objective1}\n- {objective2}\n- {objective3}\n\nScope:\n{scope}\n\nDeliverables:\n- {deliverable1}\n- {deliverable2}\n\nResources:\n{resources}","default_priority":"medium","estimated_effort":"TBD","default_labels":["research","analysis"],"checklist_id":"research_checklist","subtask_templates":["Define research scope","Gather initial information","Deep dive analysis","Document findings","Present recommendations"]}','Template for research and analysis tasks','research','["research","analysis","investigation"]',1,1,0,0.0,NULL,1,'system','2025-07-16 07:44:51','2025-07-16 07:44:51',NULL);
CREATE TABLE template_usage (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    template_id TEXT NOT NULL,
    used_by TEXT DEFAULT 'system',
    context_type TEXT DEFAULT 'task',
    context_id TEXT,
    outcome TEXT DEFAULT 'pending',
    duration_seconds INTEGER,
    feedback_score REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);
CREATE TABLE template_cache (
    cache_key TEXT PRIMARY KEY,
    template_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE checklists (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    scope TEXT DEFAULT 'task',
    priority INTEGER DEFAULT 50,
    auto_apply BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO checklists VALUES('feature_implementation_checklist','Feature Implementation Checklist','Standard checklist for implementing new features','development','task',80,1,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO checklists VALUES('bug_fix_checklist','Bug Fix Checklist','Standard checklist for fixing bugs and issues','maintenance','task',90,1,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
INSERT INTO checklists VALUES('research_checklist','Research Task Checklist','Standard checklist for research and analysis tasks','research','task',70,1,1,'2025-07-16 07:44:51','2025-07-16 07:44:51');
CREATE TABLE checklist_items (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    checklist_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    order_index INTEGER NOT NULL,
    required BOOLEAN DEFAULT TRUE,
    validation_rule TEXT DEFAULT '',
    dependencies TEXT DEFAULT '[]',
    estimated_duration INTEGER DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE
);
INSERT INTO checklist_items VALUES('65b1cb5ed58d115fe854bcb513df11d1','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('e3ec00a35f1910a7c58bd3b1611d524a','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('9b315626851f7ab932a58ff9ac8c62fb','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('03234b4f78c4f3811d6dcbd340d6d889','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('11fd16714d24ad9b9960ef2c4b1900c6','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('abf27b17af75fb35d15f70048d33c1b4','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('e0586384aa946b13789b78504432c52b','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('f0542c341c2575987a958b319e14615e','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('b50d5ef3f40d2c7213e6aec30dfbefe4','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('275909e4a1651867ce84b84fc977959b','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('242652cca4bf8409fb1b13ea85a241e9','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('c67e68f9c99ea44df06b6ea388414355','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('300b432b8bb37fd6413336967b2e21cb','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('1b20a1b86d0f40b6f6cfa48bdffb9c91','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('6262a83e17a01202b556e27a2bc42aea','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('f92de98ae4d692479ed63419d0b5544b','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('92a683f6773a01083138ffd22c461e9f','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('f1441f278ab12fcdd0100bf59442e793','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('7611d8a154666650c72dc8bc8ec84809','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('9b78ec79dbcfbe66caf3e1a780a4a79c','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('066e2da07fb9c057da8401c8da6ea6ff','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('837fc4138764a3dd118fa9aa87b9d879','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('9d3e4e792ceb6703291f2eabb959ee64','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('c73a85d0d03fe9b1aa0c16d1c2f50f20','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('9625519934ed16e514eb29aa4db55fff','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('2bab146a61043c386d79a2d95eb9948b','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('dc61f0824a0fafe749543d65c304975c','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('a6c08044161028eb2df61baa150f96da','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 15:07:05');
INSERT INTO checklist_items VALUES('11473955b379a6f88481a81805c1a099','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('3c8df9a279951450f59c708ec072990c','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('e36afeaeb8d549094a85fa3f75fffd4c','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('bad4bcf6102ad4028b9f4f8eff16e930','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('079687f12f01e6f5981c60432df83812','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('1822ed67eb7d8fdc65340ac3b6298ccc','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('fb105cc6b7b434462260bdfe699ec986','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('9a580fb5dd381da83f81773cabacda0a','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('b626fbfbf0c4ee0688db88effa68cd3c','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('ea600881e66d94bd216d1bca4f901174','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('cd394d24dc42b412119f15396af433e9','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('29081c540d30b8e195d883f540f0f669','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('5a9845aa19836d29a17c6afa3ea09cc5','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('f9ad577e89f77527496baeec70184014','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('aeb698b43760a0d75a0c1c40e4e001a5','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('8d918a07013a4d0b7560aa9183dd242c','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('ec045c360e553f7109e010044952d76e','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('466e30250ceb34e5bef7d42809872c54','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('6f09e0fb960b8e099f7b4fb19389128b','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('b58dd249394b4c45e7604d1d1dd9f611','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('ce68fde6281bb7e34f96298dda1d2190','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('a9b31c4fa6d95a0f7fa1b896e7e5a96b','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('348c186ed9f9784a0f78c087977507e5','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('7e4cb41c2e9f2d40457bb70bd1543a66','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('e7710093330d49c0a89ee5d2fbe7536d','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('4e9412725ad68c78fcff60a940b0d9a5','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('3c38e30471180b1447d110553a0088dd','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('9f5a3484d61794a9fbe66aec1b17d311','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 17:54:25');
INSERT INTO checklist_items VALUES('40d5d093d624aaa9ce976773cdfcdc25','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('ba0abe0bb9b890bba4a33739045c7a74','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('29b5c690bf0aa8178fb8f9712700da0b','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('67709851377ab32c77c8cb644db5de48','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('2e801a7c7892af38923df00b93c5cfc4','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('9fe3865c78adf69d46f179425facc846','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('67cc35c7d52536545facbcf01bfba17f','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('c16c8c5918ec7028a578538cee6892e7','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('bb69f300107987750b4c52cad64346c0','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('80bc5857eef6b61f5732b0215acfd02f','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('a54c8133a82a25ce796e9fe2fc91e3ae','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('85fae6b2286f745f52d314f302f7c810','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('c680b3a1932f1c942eb62301eca95702','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('b627a72b92a616897963e16a89cf78cd','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('030476e6f90686ec7c615c568f2d67d0','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('84e2e6e07cbdbecac45a543c7a4ab5c5','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('77f8da0cca469a0e14a792e6305bcdc4','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('5bc72d27d6677f55bcd1bbc9ae74d668','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('22623325eb6b6a7baa55ebdecfbb3ef7','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('be0f84a9fbf75cd88b81d58172eb019b','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('209c52262d678aa724b831a0f6de65a6','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('e9d6d15b7f34455f32e887c60595eeac','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('f0d6db7e0dd7131300f7cbe63197fcbc','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('942df55764aeedf4d1f96bd1a55057dd','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('ead020dd192c19b41ed5474abc64bd45','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('a4bc06c15404a24d625e88c6bf39b077','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('0b4e1d50aa39f4b0c90b27843a725394','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('434afa367739a323a9107eb6432201f9','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 17:54:33');
INSERT INTO checklist_items VALUES('bcd738d09f211ae64662c55ca32d4015','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('1e41dc0a015231be083ff11392425b3d','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('a010d1a9a277644efb39c3da230ce9b0','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('7a6cb982d18b75f173da70be8bdf2020','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('146a24c6670f0f77dcbe1dd7e8a3e168','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('942d710c6fd46133262c9e237502e4c1','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('0d389bb3215259fb8aeceefc4d8adead','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('cb0fe53ccb950083afa6dc6864c23b32','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('66e01f01c057d815e250cfb76df98d27','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('0e036bb0ef4a2aefdb772d28b17ada58','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('e47c2fb2c1d29d86de5d4591caedbca9','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('782b665694c9693bfd66771ac35935cb','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('13374f8f3f8e455f65a5a960908b605d','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('a4ec6c6b263bc4fbc6b0c0e557baaa79','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('d8c2e60bc8691941c03b186ebce81666','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('2c98ee44ba50dab2702926f07008f288','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('f1291d89a0fa7a852f0efe2a2e1b1bdd','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('c53db379b658d072e6d2a8d3a6254d13','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('b31b0fb9db7cbdc54bee5c3b8242353e','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('6cde54da4b6cf8f3e12f074088b47b5b','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('2be7a52b270ce5ae76f796cf629c297f','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('7ac81731be2b058d8c401153acaa2b83','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('42ac2c54bbabaa738c39c3289e391c47','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('1a8e0ef1bddc35e5d7c666c208110de0','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('c48411c7198efe09d25adc2395fb31f8','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('4a21869c1867d1c7540ebc18066250e3','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('3c66d9f96f1ac7ab2ae677de984099ab','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('47122938b8b7df6290a4fffed6f9fd0a','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 17:55:42');
INSERT INTO checklist_items VALUES('ae2b22b3edfb8b8a63a24ba6f44aa27c','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('10fd5a0a8bc1398373eb659a785bf30d','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('e986b4c0b601b7006692b2dc8c7319aa','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('e1c9280afe5ac88df9cd6fc5785c127c','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('00175a88d9c6288d62cf3746b25a694f','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('627a61867c57d60e5c5267f4ffa5e21f','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('60dab0aeee131e45197eb39a3277d504','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('e378db8292a666dd55e51392aa63ca00','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('4272b2bd6c37fa14f3e045d6df1f8f04','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('56fcd4205738f277163c03faeaeb1b4d','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('19aeb06dfa230573db51ba22ed8e3b07','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('4c21daa218792682d140aea17786012e','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('c01b648db8656b33742920dfad3f374e','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('aee5d7ed01c045582d7777cd59d40c50','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('f0081c40a2073847b7f584507b61b1e6','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('d6eeb6be5f36ed27aaa469d5d47aea34','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('35c538e8659f46c90111495ec9ef61fc','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('8f6039d18d4a0f0e79274883eacdd5dd','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('4eaa346cef5abacc06db4d9138244107','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('42709893cbc7dd893131e278e5600494','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('1ba6f115d832d28ca80eb905176aa978','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('62ba434bdad4b546b8356a879c1e6e58','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('5beb1f9b523f73accb274f44bc0082d0','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('bee80b92468ae48b2406de0ab0463433','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('8cae66aabe8ba6b5004a50d35235d84c','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('c51853c4dd7cf77d26400f4d5d17c942','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('cf04c6c96d46f3686854d90258b867e4','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('3e340c2098f57161f216dbabdc0d215c','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 18:53:49');
INSERT INTO checklist_items VALUES('38d8310db982104defca4deb6648e2ac','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('55565c3bd54d4fca958cc8abb8193dbf','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('05e4ca115ec79f34e899cef8e5bebfd7','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('6df9278362bc98dda854911245ab4871','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('98726c3af8f42dfdfdc38ec317ddf2be','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('3ccbb6b0224bacab3b670f3275d73800','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('57495bf1df5b163415c983f190221646','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('3245a8e0a25d1971f5277900a1b5a441','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('7d9356a9b7bf5dbcee39c269451f62da','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('d66b993cf3565fd60b0fed3067cd4211','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('977f6996269ebbcceead4876c9873bca','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('0b5ccd1b24ed5cc17b3b77d68f95f064','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('2b606e8343e3454a3913d341f95236f0','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('20a8af1350d933d34518c320776e85e6','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('98c27891aa8dc27464ecf0c6976db436','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('1167d939a6e58480c9a42201441a4034','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('45f2d232fb63180e46ac2a4c4ef39557','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('35b78ffe59e7a63ff9e66e691d5d2623','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('923871ad3e635007c57b6f75d92d2423','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('41b6605fcfed991b57e0fa0288d8374d','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('470e8e1e4e920b3456eb600943032dee','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('99af13f398b6fc77b1f286d788334ceb','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('d8b60feefec1f47de0339113894946c7','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('58efbda055de13bbbfa078c48b485156','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('1bf389d5f9440b9c5621b4e820a5cf0c','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('f6f1e7d614da9301395ad92f2efb89fd','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('8f3fad884d5807b5aa3414881b014ccb','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('5fd04d38fa0db872ee2c58f467a247e6','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 19:00:15');
INSERT INTO checklist_items VALUES('6f5beb6f620adba82270c4cea099d1c7','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('d6dd8bdfa63341d52715710a87cf9f77','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('b1fdca39110b0dc039efcb6ae879d7a5','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('adc58803cec5114e5baef7c0a3c13552','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('20b268d9302c28988f97e0053d2e4b77','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('a7257ea910611c1f9f977085688fc5fa','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('bfe6be7bb4bd05a45e6588ad78de8163','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('6149d20896ea7b43e417e26c3b9071c8','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('92e34f4f264b214e35c8ded1f384e085','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('a5d29f99bb1b91a1bbd4036ff576c37c','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('22487ae42a8e1b4404aeb686544c141d','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('1d00ee5d737e062de9d0e11f22ae59f5','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('affbd8daf9d8e4e80de983f1d14c604b','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('7389a6da5465b32a2d8be8dba7f4a908','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('1fe1d78b320c0e28dcaf5dcdb9e424d2','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('25affb20794b29a63a0bfea2d2a5c74d','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('7f0efd37ac771cea2cdd08d853cd9ff4','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('ea7f661c435ae5e38a0cc45b2b6c96e4','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('083dec53d08640f20a4747b118ece165','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('3755576b18847d0bdf62e6c8126a6d48','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('9f5496ae6099b93f343f0bd2898e6082','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('e17a68881133a144af6c347e35120d39','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('4eafe41fbc267af6e962c60925529a7c','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('224e2ec52e92a504b0476885c6e29171','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('bf37e2cb0189cf0d1ba8f5494e0494be','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('40f2a9afb4c8d7d56c7e09ae11a90abc','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('882e83333d9d92f279b3c146065afcfd','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('42db29f62e5dcedbd7d7c88ed23a574d','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 19:01:05');
INSERT INTO checklist_items VALUES('913226d600d11db75935e4c044f855eb','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('4adb95d5682245d41728b3f192a11ebd','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('5d7c321bb0af96668d50c6299f74d80a','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('b602675846fd051a4f602c2ee115eabd','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('5b4f382dbb030f267dea0719de264c9b','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('50705dfd0879d784813f15a53ce9d5cf','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('cd76daee2b26e4064b3bcdd93521b6a2','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('b2983ba6cc62847b4a97257900ff440a','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('328e138784484b721fddf1b519054d9b','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('a07629dd9c926fff3d2b02119e2044de','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('6e4db5bdbb6255a54aedf72d5b2e688e','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('d533642b627b95081a322a416dd2f437','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('d24263817c651abef9eda5ef848b5019','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('1f9f8f41d499cf4e027777fe698961d4','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('bb6a6dd3a7e2749b4f589d5cf368a1f5','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('9e70fbe57d5ab8abe296a6d07496da82','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('43b13e751660784f320ad4010c3736dc','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('4946bb7ebde7e9ce95c554ee25cebe0e','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('fba81876721b2e9f1af9253866aa20f3','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('2a23da20308c565175e60f2741cc5671','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('c261daac947eed79638f4971085488ca','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('f6894db441f76e8d4af82d2f4b0226b0','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('9dfa6c710440f346eaaa9decf5fe617f','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('cdf40406f494a72a5bc03de4c9f6383b','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('d82dc1304b831f934b28b8bef6942b06','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('4e633c77d5577378e4718457254bb84e','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('ce26df4b45fe3554315f7e731ec6daa6','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('2d0961b3ee07eaf09663a8dd2959a350','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 19:01:41');
INSERT INTO checklist_items VALUES('b331eceae87ef4a1fba0f61cbf7a1972','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('5a9683c64d655ab5fe31b2b9d4ad39c4','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('2fadc1cef82a1903b292eeabffb5315f','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('591478f76ed1451a089ab4525e8581e1','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('a2e15836e1a0a06cc7d7589e8c5368e2','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('d92123b76ae7ca505ceb70f3a24e5651','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('e60164c008809a6b11d4b709c0187c12','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('e5f5b047aa51d5ee509ce272e6a9d796','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('ac14e802d0f7db4656a76dd19f281cc3','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('2c42fef6e8da4bf28859124032135c46','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('ec63fb96d2bdfe5dfe284f0b9bf748a5','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('eb46c42a16cc0142e790c42c36643b52','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('9bf07cdf09c1d4d60f4076076c938d7d','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('e09ae63167e84d3cbc89fe40104179ea','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('0d1831fd162d75b46af9e218f3268785','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('49fcb7df286950e4cde9fd314cec25f1','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('3b50802c64c09e814849d53516c88ab8','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('88e71a33e6326dfbf28db7c1c5b00e78','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('9ad7f84228dc645ecbfa55cc16e39f8a','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('1fe5118d9e282bf733ad2b24b366b848','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('85516281284968dc7817ff1835e4ca2a','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('b82f33306337815d01a651362f773450','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('7e058b725bc05ea900353748e7ee6fb9','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('76db3254f85223bae620a6c45104dade','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('02bb2840c1f7a71b873782cedc0c3a0e','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('3dd8461efa5d70544234bc7c3399d09d','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('de9d3dcea700b8f7557c01fabc398db7','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('8959fb705a2e147860f50b041e509325','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 19:02:19');
INSERT INTO checklist_items VALUES('ec8096450c53626b14f8ddb448c182ec','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('8ad3a1eeff3e2292d6c6c7362b1d4850','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('9a2c9e65d79294c13f0051c2cee46c2c','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('a25cd43c6555b1e3d56c9247d5038d16','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('9bc5ab52a23ad8d907f2c3b114d9d4f8','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('28eb67800cb7a0dfa04e572824b0a6fd','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('ac1eff8736e9b726726cbdfe32363019','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('01438d7e185351a21d7b377fac7aab11','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('fbe4225efc493b16e9d139c0031d961b','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('ac4e30c3f5ec8e05af4b5007f64b1372','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('be9fd9d0c8ba35a72709fd08aa5a1fd7','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('8b91a6c6dc754e18af9b059fd570e279','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('8c3258b10bdf1551634cf0d04d2b4b76','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('5945a6b02087d916dca3ff5e0784956f','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('d607893941501dab5510d2b068aa9599','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('7dbe2416123cf4caa45a6f316ad25ba5','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('5a251ad29446709aabd2d11b4565adf2','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('5415531ec7b209c1e1a46f0e4c6ce521','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('d1bc4f8961598f99449fe71784406589','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('934c5d8b12e6d51d7fc488c41358e2b9','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('d06bb093ce6dc0ed5fca475806eecd09','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('3f6164c16f6d4fb89dfa79f0533c4c12','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('58cfa04297e3413e6f9dc7c09678a42e','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('745f6c59934ad6aa7f4b82198cab346e','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('3a538528071e946fd6327f59dcdf9bc2','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('be2b9d42ef7d69a926434abe3a4a0d78','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('d78df345f3cfadf2bc28fb5ad8f19097','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('a341fbf772161fcac47342a93a5b0210','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 19:04:24');
INSERT INTO checklist_items VALUES('993fb9f46bb719fdab4afe16921089b3','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('e502deac85e6393df031f9068d0f5cc5','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('1dfe5a02d2fd71917e1400365757d5ca','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('f33d4576b4720855ad3c16cc4f105c70','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('9b86bc92f760abf9d12813563ac27e65','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('4ff97c654c1d4a76144937433d0f621f','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('d4c2a43f5b9178b2878eaf1c00708056','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('9b406b95503ab1c4478152da74a8e6bb','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('09686b59df25c09c3ff722c550c06ac1','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('55423ecf2ac27a5281cb0c54bca58d64','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('45e11ca19075e2b7314bfac23ad67f1f','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('826bc3a0b99169831aad97b5827785f4','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('c094448a298cdc6599701e1cbd19515d','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('2ab64a4bc3658181a75614ff7ad4dcbd','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('900375cd9d37667247c6fb24008f63a9','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('c2c794eee4e0e83107485991ab05c453','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('2864484441e24b1840cef6f61909e766','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('85ceebe963ad9364cc3723fb152eaa1b','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('bd61a710b8a46ba26e89d0d4a3a28501','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('2fab3cee5b7f84a9d84190b1708850f4','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('d65ba792414bc7cbfb9ab29524b936a1','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('7ffbd0fe643be6e4aaae055221676276','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('a083741bcb3853b412cd4322dc668d32','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('118564120186f4f5a8c154823a53219d','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('99680aab54ec248d98c08ef9d3954df9','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('61562ef251216ae77da81f338111cfed','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('a3e5cbd150d775bac431fc4b9cb731d4','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('1c83730269d022c8d1ebaa47a6c87549','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 21:29:05');
INSERT INTO checklist_items VALUES('1cfa970677f2f70a59e777eb2d3e1166','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('8c1a73bd62d9b8cec30c9f1f957946e3','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('fca00f32efe9e4f8c917fd0680f4e23e','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('44b8c6404f4c3fc54a853982c8abe712','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('3dbb0a511387c6c1ec821c889070afe0','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('24b1921e98129aacd2ce63662527f19b','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('bca087b029c37bcdd5247f2e8edf1218','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('0c0d23a0f4e42da951ce84cc9a4f43ae','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('b8bc482c34d8434b2c7417ecf5bc9df3','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('01c31f631af4dccb412e5493fbd441ee','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('c684c3c1b6bc83eb4da86b3b6f853107','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('7cb2c85e7fbf892fd3efd04a1c8bf602','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('3e308b9feb15286650013984584419ab','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('a723f944171b73fc312dd5873e4e2495','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('d2eba272ed09dd17015d490c2488ee6b','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('757f9b59218d37a5d8c2439eaf36a56d','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('fa186f655e1973f8fd0468bb73b7bec8','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('393825d55b338b61bbef56b7979c3d8c','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('7d93ee1db9237c0245577029347c5f94','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('e1ce763244f4d5afa54508c4487ff903','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('97e3babd230bdcbc53da99d548115a98','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('fc317b31dd1f9bfee66cbacfffddc16c','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('958391b60b9dd7dfb747d8690274f170','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('c8b7df1d05a70703805ecb43fdf85552','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('d9bd0487403936cbbaa89f6ed48c58d0','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('4da516de2209a94a96d3f9ac30f2a8bd','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('d1cc143f764218cfd4aec9ca05223f27','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('b529bea475912dff006dda0603d6ee60','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-14 21:29:51');
INSERT INTO checklist_items VALUES('227204d9d0e1cd5b80f35407ad72cce9','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('778664b8f6d1a4210c638652a4fcd367','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('5da4b80288f33ebe4650c4e497f7ff14','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('d295c55c3de5d1f26cf435328b5b72fa','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('9bbcf536cfd5923c88c4a40d7a0b49b9','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('bf57b2935208586e7ea7e22f3b04ee74','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('61e85ef0d13caeb5f9c2204c0f2369c1','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('60b9ad9763f608e05f8966c1298677af','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('a81f6b8b8e6ecb959516f3985d93f120','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('d20ceaec8818bb8cf25c509544a7552d','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('44e71f5d57aa63315d4ae487e36bf7cb','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('5d6c75dddded1f110e3c3e427812a1d9','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('0fd7439d58e1cf00957f75e91f1f6c10','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('52a1d498c4a7e0af84730665eeb46e47','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('337d4331f266ee275bdf4aced71c3421','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('b80ee801acd74153667b46f1672c66b9','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('87345e624782440a30c785cf71aca518','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('0a020ab88cc263e08b6a401535431fb8','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('44aa558a36a34d02562a53af1c253221','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('f8b2bbf4aa39cbe97d5e57e6f70c7502','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('974e933791368d1b1e66d89da458e635','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('4f02fcedf6bb1898eb237d282c353533','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('c899fa2e884fb3418ace1d748d9b7299','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('16216a8c1b3157518b8c7e45984c6efc','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('3bd7f3509f454a7d8db196aeffdd4213','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('944a4168e870bcda7a54550fe3467d4d','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('ceafb212f7c86bdcb3eb7df12d38da25','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('d88ff5f931bea9854754c88a0606ee16','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 06:43:55');
INSERT INTO checklist_items VALUES('4ae0d57ea4ea146d9cc6e2cba63b7dab','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('ba47b76c871dc1453102b9480e33bfa3','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('344f39728216b7be27ef3d72162512f5','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('9d3efc8be9fcea328a19b2d66e32eb28','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('a05653770a5df48494e9d8fb58cc35f8','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('8abb17bb726ddcdc9662fa1251096c36','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('99262ca0c8bcb55ec1a19ebd4cb805f7','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('e79b904dbe9b41e26d0f2e1c6491eace','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('01e25d20f3bb1596e719b8ceea973af6','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('e58d3f972a98aadb89f688b0a8f9be83','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('8f629e6ced62ff81d9bdf07f8f9eb5bb','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('dd3461a3a1ca66741052cb77446a021e','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('9a3155c16736fc1e18babf2f960a4672','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('56f61768ce72ab811a26f48a443d46d7','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('02fce20727c18134c7b96dd767208968','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('910ea3bbc7e1c16d4e18ed0b1defc9b9','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('1812fdf94d20a61520deca755ffdbdb0','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('3b52aefc7bb980b422ab706344525d8e','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('41be47ca36cf0c7bb209db6826fe8808','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('d66f66b4ec24721cd73aeedfe5478874','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('abe61d81504ed1e3d19a18e9eba1c34c','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('ae0bed89b23dc8e27f0cbd6509d35307','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('9d1888115528e37e3624fe73ff7a2313','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('161dd59722bb760d928b0a129c531809','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('8bab0dd4ba5dea3d7cdcbcd211a24638','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('37c4eaae6e19e5c37f7b25ec6a8a3889','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('aee6d8fccb13f118076d3996cd43ecfa','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('9aa89d90a5fba7600498025335c38f59','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 06:45:26');
INSERT INTO checklist_items VALUES('597791b60481cf83e5d2536cc4d048a7','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('660f990d84ff89a9c8c2187efbd2c4c6','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('bac4e8395bf807ca86073aa6494906c1','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('f132719d912b8e38b72bf61a8faec8ae','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('e92c589912eaf242a76eb40ad7c1f349','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('625a4e724467baf9aa7933b73d119ec5','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('87d2ca06add684d626945789e144a136','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('75d271cb38b4a3f432407f8b97aa427d','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('9fe5035e7210881202a5cd6ee591a927','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('508971b0643283fa39fb5047229e068a','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('c7e314967d7c0198ce372451f929f502','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('3886b74b7a898ab3e7cb15403eba51e6','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('2fde5bcc1dfa68f6f98d23ed9f0df4a2','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('19005a7580b9ed2b8317efcad93b73bf','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('fa6fe478c76791e196f2c4ffd8dd9f58','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('2737b91a14e7b213aa20d90320cf1b55','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('cbdb789551f273f0f4b5dde9b4aa1ab7','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('a4257f370089b5dda1133ad8fd613776','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('f5e1582c7053c2d894bf5faa3c328c0e','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('d7b164fc5c2a4c6a11705171510b7089','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('40fd4535bc5d32b96fbe924b012b5b4f','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('811421360b6182fca50a8c5a545194f2','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('7c8fa0d67dbd2a6691272e7b7414ac42','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('001654ac507b002ba83cc4909c1124b0','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('819ff8110187d594270cf338882c9cb8','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('783182552925d61d9cf5040cdd80cfa9','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('4cfa3c3aba47018e0ce71172f5686fa9','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('80fe5ebc08829d192620287ff95a98f4','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 06:45:48');
INSERT INTO checklist_items VALUES('cc5ee03b67d4b3af39c53c15331b8fe6','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('9a94b426daa5253e017fa71968376661','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('9632af2b8eb60f619dba41747df4f2f6','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('6645107a2029a00177a57b82ed3d67e2','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('f3272d8af5ddc2ce6567e6c15b6d82a3','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('2055f690eb960686c62e0540e521621f','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('1e17d6d33c48784c2df98eb3860c25d5','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('73b0f21997b59f59fd9530bfdb87f31b','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('80233773ec2304f740e371d004421a44','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('1e1c13be526ed90eb3b60a78caa55691','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('76a36e18bebe3eb4f2415b4635231171','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('751c15b6c50dbb22b2f57a28d76f201c','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('0806536ed3c3faa13979dec44220351f','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('d1bbefd5ad3a94a34667193cf0187758','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('1f8e8f53e648b3db9e52b05659806ad6','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('67e49ba3a66cfd7dacb639088019d9f7','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('71cc8c5096b7692c4e46dc9a007b66eb','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('6f91772489c0e5d86a3b8e7a5415c150','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('b285a2f528ff28b7db1718268896e39c','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('fc21fe8a198c0e7c102ccbaacf22483c','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('989a4448a18b2cce52aa8286eb7b6f82','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('88e4e7455cecacf9a664aa97b227a64d','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('d5fcfa1cf3b87a6fd60d0b1c72045b87','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('4ff568ab46608cb622c154e89890125c','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('42a607b768a9b676ec96218131672beb','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('5fd9080f91dd2be9df66d38161e8785a','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('65a8da2f98376a2b5cf50db34c321e3c','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('5fc0e830cb3447e83015fd6167b0bfe7','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 06:54:00');
INSERT INTO checklist_items VALUES('c1b0eefdf311ea38ca1e878becd0eab6','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('b42728175db93d9088248c43ad3eb6df','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('c1bfe0ce6341b52a4d16bf6dad380d1c','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('7a7487de76976e908616c912bb8df2dc','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('5f1d0c060bea529e8ce91861de190705','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('96a28d26002066d60b819b3fecde590b','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('f345315dddfebeb5a61d4aff66748f72','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('64352b5f7712ac783bc1a4b2172e58de','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('7470ac7a765a827f715260e27e6eb849','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('b73e18c02553e01f7689cbda7a92cd52','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('1e19920cc8b021e81877ec04efb865a9','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('c0c29fccc4f95341951fb2665c144af9','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('09675adf087793a5b92014f8c0e4ce97','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('58dc34ed85fd1d45c34ffbd9c182f78c','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('2ff49a59fcbde3a87aeb023fd56e34dd','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('03953c2ae0a9d1468c6cbea7d2faa8bf','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('19d3f53c7fa9a880f393859559831832','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('b590b70eace8134f9a1558e0ba1f4a23','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('98ce5fd14a6c2f57d911dd5557f0546a','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('408b5b663287ff010c45f95bd5f609eb','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('896c87f831fe8a7cbb2c04b16cd814b1','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('6d2a41865681f7c8dc4ec174385a8388','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('cd70ca06329b7c27344e764851e37835','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('89c08ae537294476a76edd8f7e9e6cbc','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('f6c0226aa77e98f4f4e18f25a4b02641','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('b26111f545067d4488a10ae2c32f3941','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('cece0d0c0c9a0d5e399cbb25541c2f43','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('460ba87ef06e6c263bd588390618f14e','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 07:01:31');
INSERT INTO checklist_items VALUES('713e0546a6836dbb7162e4df59d05aa5','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('e073ffd794fa59d69faf07a4e4c103f3','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('cca3018896a4963004350ea4a27d6d66','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('bb39408e20cfec49f3a5df2bf91021fa','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('58e3042aa3b4093494892617231725ff','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('321abe43a624368c31814ec97004b6c0','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('c7f4c158441555b60638ecf4080e2176','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('73b458faf7746f6e1a1f72f5dcdf8c79','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('ced9382d75b8de038c94d6a27120450f','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('eabf38a536be805c0073105207aba889','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('42fff5b1ff5f5534a3ae4a963557cd36','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('4215fa37d16f8b8c46171db2f902fd06','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('ced6f965bb2e7a44262528983857eef6','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('65acf4f5bec52722dd10ae44f0a808f7','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('3d71791aa349bfb649a518d251c61dd7','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('c2be1bbaf316a249cd13bfe8e89af349','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('03d570d8c8430fc79f6d369c360342f7','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('91533ca4f273613a7ecdc57e3ee3ae65','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('5411a979086e7bbe91fd1b5f1cf39986','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('943e96a7218e52167d395093559d803c','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('dbdfa5b43cbb884d6d22b3b1680041a3','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('000295dbe4aa0ff46c57c89d6f81f99a','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('1f54e46fe24e058a742420c46e8c50bd','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('b49218e9b0738ea4a94058bd1e5f8f47','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('83cff197fa2c99cc538bb895d79c6a8c','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('48571d0d676ec492b5aa72366aebb1b1','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('8744dd8f6db8b1d491262237a8852060','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('fb4d038e160684fda2bf9e4b30faf4d6','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 07:41:29');
INSERT INTO checklist_items VALUES('5c242b67a1185d4075c2bf49c3dfa3a7','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('9a3367eea317d79f292d7fb900de436a','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('185a216eb4f310c2b7d7097347819ad4','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('592f397238d702596bd8e88f03a651cd','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('dd24ef23da34c2e4923353f80f490092','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('38567f463d18821ebc0be235bdf4dbb6','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('48245a2cc5b44855d2e324f5e6d328bc','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('560e7f6909a6a782451675a5d0afa27c','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('c2e4a3ea799dbfbb16cffd46df324edf','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('08120d638889fef2ecae89b8b5da6fb4','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('c671338e196baefc2e01d884756c3cae','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('dc14e3c1c8435a5ac074fae343e205c1','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('9da543271110629eaf4123958deea148','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('45fcb950fd8adf80fbcfd3ed0b187ed6','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('4e8fdd6d9b3d9cf73b7e08e97256fc13','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('b9a8cd381feee0a8d195ef36af0dfbcf','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('cb9f462d4c11ddafbef9f10e9616e94e','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('bfd889544ed56136b6d93ddb76b0002f','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('7cbff426f2968a28aa8b7f7a4c0b5cc8','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('6ab629a79437177fc6c160d707999b0e','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('5b6fe88fae1d7a5b5c53e07b6a1e492f','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('2937e933fd197092750fec927a979f14','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('0342be1542e2132f580cde6aef2a0ab5','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('7528aa2d2a8a7c0dc4825021f958acaa','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('aa6281c579099c3f6a53c2369e762f43','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('b66f89e2a823f921c925be55303f4bb6','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('691f78756ce1d21a5cc54d8ff787c92a','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('94cd93c222f08934ffdac00a9de472ee','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 08:06:30');
INSERT INTO checklist_items VALUES('962796ed25dce3aedf1d8514a827dacd','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('6a1ef45429e3247812407633e4fa3bfe','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('303527e7fe95fad4e781fcdd758cb8f1','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('d7ac2ccad3d81eb227d82a1c73b01a2b','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('b6311b54724e90aab4deac92583213d9','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('5dc901994bd406ca9de3a0a72dc438d8','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('3179bade032f057646afa2c2260294ba','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('b5f3f582b23749b9b4b41ed831a1f240','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('7bffb98fb3b2df91a7f9cdfbf2af4fe3','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('80278093efee707fdfa39d78e0c01579','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('520af93fcae9d6050d62438a41b9bf73','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('867d24a68ae6f00e27440cc1eddd2db3','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('45ed77c1d40865303d93cec57f8c6dbc','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('03b8e7ca72b424ccbdc2cb9f39dff4db','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('81a17990c65273ed5b3ae38a07588a07','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('2a5a4332b22c8331a636b991bfb0b90c','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('0f0620efb4f4322eeea923ad5687d21b','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('aabadb469e8dd741f9afc57c925c9059','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('b3c857894071dd4f8d771c2add215546','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('32152544ec47e07fa8bd3e7a9563cfc3','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('a67effe2884185d0f5c634740adb5141','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('56c4eb81680d3b5ab4ce74450cc6c785','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('014c0e82dcce6979d6b84ad76d829c98','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('3a21e41a18fb30ed381b70063a1ce970','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('60a1747b0b29e9f25175a51a1d988397','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('2f44423c648de4d838ac6806ccda2809','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('e029b240b160640f08ba510407089444','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('89ca84de2615e8f29afb97b8fe92a23a','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-15 08:07:07');
INSERT INTO checklist_items VALUES('5fdd42fe6c62e1d8d004c7d37be6d73f','feature_implementation_checklist','Requirements Analysis','Analyze and understand the feature requirements thoroughly',1,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('4afa1c70b607d071a9177ef49a218aca','feature_implementation_checklist','Design Architecture','Design the feature architecture and integration points',2,1,'','[]',7200,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('e399878eedbaf1a51f2129d286e350e3','feature_implementation_checklist','Implement Core Logic','Implement the main feature functionality',3,1,'','[]',14400,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('2ada888a83384c9e2def435df72a3310','feature_implementation_checklist','Add Unit Tests','Create comprehensive unit tests',4,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('a9fda8dad91e45e0ebb4704307eda359','feature_implementation_checklist','Integration Testing','Test feature integration with existing system',5,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('1b8dc9543fbbe9cc347cc088fab10377','feature_implementation_checklist','Performance Testing','Verify feature performance meets requirements',6,0,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('f9dd0b8fbdb0de716791589a6fe32256','feature_implementation_checklist','Security Review','Review feature for security implications',7,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('332e705a39449ddbaab6bd9ec126641f','feature_implementation_checklist','Documentation','Update relevant documentation',8,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('863b0c727c9096982585255d3e2054c3','feature_implementation_checklist','Code Review','Submit code for peer review',9,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('6d62c7176bd407074c75d2038acb8dea','feature_implementation_checklist','Deployment Preparation','Prepare feature for deployment',10,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('27aabd9d673a5625490b0e57516133d4','bug_fix_checklist','Reproduce Bug','Reproduce the bug consistently',1,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('1dcabcbdce52a6c6b204d323cd9fa1f2','bug_fix_checklist','Root Cause Analysis','Identify the root cause of the bug',2,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('e8dc2e5f3de6cc8879ccd2b4cd48869f','bug_fix_checklist','Impact Assessment','Assess the impact and scope of the bug',3,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('4e0a57064901b4702fadd33a1570fead','bug_fix_checklist','Fix Implementation','Implement the bug fix',4,1,'','[]',7200,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('f5ee5ed90b99f8f0f04dfaa5bec9dd1b','bug_fix_checklist','Fix Verification','Verify the fix resolves the issue',5,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('f329e57b67cf800a99a05144e0e3dced','bug_fix_checklist','Regression Testing','Test for any regression issues',6,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('a23c972cacc4d18c74e1c12eba96ba58','bug_fix_checklist','Edge Case Testing','Test edge cases related to the fix',7,0,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('98ea7f871c690c367ae0d1ab944fabb5','bug_fix_checklist','Documentation Update','Update any relevant documentation',8,0,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('2821a811d3edde0c70ec43cae1d2c58b','bug_fix_checklist','Stakeholder Notification','Notify relevant stakeholders',9,1,'','[]',600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('be30518a613627e52be66e485eb45d35','research_checklist','Define Scope','Clearly define the research scope and objectives',1,1,'','[]',1800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('0df6882a0ae355c3dd225809ad5df97a','research_checklist','Literature Review','Review existing literature and resources',2,1,'','[]',7200,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('9895dafaeb1624d3229d35d3fb73911f','research_checklist','Data Collection','Collect relevant data and information',3,1,'','[]',10800,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('65e8d2a6d8b502309fbaadfdf0e91124','research_checklist','Analysis','Analyze collected data and information',4,1,'','[]',14400,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('b0e422be7f373185193fc072adfb9bb1','research_checklist','Validation','Validate findings and conclusions',5,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('0e054114b216767c6b58f130d5e2f42f','research_checklist','Documentation','Document research findings and methodology',6,1,'','[]',7200,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('29a041a9d078926888018540bc785bde','research_checklist','Peer Review','Get peer review of research findings',7,0,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('ce56620ad46f8e758a263db449bf2a16','research_checklist','Recommendations','Formulate actionable recommendations',8,1,'','[]',3600,'2025-07-16 07:44:51');
INSERT INTO checklist_items VALUES('636d41de5cdb11858c400dd30ace79b3','research_checklist','Presentation','Prepare presentation of findings',9,0,'','[]',3600,'2025-07-16 07:44:51');
CREATE TABLE checklist_progress (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    checklist_id TEXT NOT NULL,
    context_type TEXT NOT NULL,
    context_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT NULL,
    completion_percentage REAL DEFAULT 0.0,
    current_item_id TEXT DEFAULT NULL,
    notes TEXT DEFAULT '',
    FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
    FOREIGN KEY (current_item_id) REFERENCES checklist_items(id),
    UNIQUE(checklist_id, context_type, context_id)
);
CREATE TABLE checklist_item_completion (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    progress_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completion_notes TEXT DEFAULT '',
    completed_at TIMESTAMP DEFAULT NULL,
    validated BOOLEAN DEFAULT FALSE,
    validation_result TEXT DEFAULT '',
    FOREIGN KEY (progress_id) REFERENCES checklist_progress(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES checklist_items(id) ON DELETE CASCADE,
    UNIQUE(progress_id, item_id)
);
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    record_id TEXT NOT NULL,
    old_values JSONB DEFAULT NULL,
    new_values JSONB DEFAULT NULL,
    changed_by TEXT DEFAULT 'system',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT DEFAULT NULL,
    ip_address TEXT DEFAULT NULL,
    user_agent TEXT DEFAULT NULL
);
CREATE TABLE coordination_requests (
    request_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    requesting_agent_id TEXT NOT NULL,
    target_agent_id TEXT,
    coordination_type TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    request_data TEXT DEFAULT '{}',
    metadata TEXT DEFAULT '{}'
);
CREATE TABLE work_assignments (
    assignment_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task_id TEXT NOT NULL,
    assigned_agent_id TEXT NOT NULL,
    assigning_agent_id TEXT DEFAULT 'system',
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deadline DATETIME,
    role TEXT,
    priority INTEGER DEFAULT 50,
    capabilities_required TEXT,
    context TEXT,
    metadata TEXT DEFAULT '{}',
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at DATETIME,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE TABLE work_handoffs (
    handoff_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task_id TEXT NOT NULL,
    from_agent_id TEXT NOT NULL,
    to_agent_id TEXT NOT NULL,
    initiated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    completed_at DATETIME,
    status TEXT NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    handoff_data TEXT DEFAULT '{}',
    context TEXT,
    metadata TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE TABLE conflict_resolutions (
    conflict_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task_id TEXT,
    conflict_type TEXT NOT NULL,
    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    resolution_strategy TEXT,
    involved_agents TEXT NOT NULL,
    conflict_details TEXT,
    resolution_details TEXT,
    resolved_by_agent_id TEXT,
    metadata TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE TABLE agent_communications (
    message_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    from_agent_id TEXT NOT NULL,
    to_agent_ids TEXT NOT NULL DEFAULT '[]',
    task_id TEXT,
    communication_type TEXT NOT NULL,
    content TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('labels',651);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_project_git_branchs_project ON project_git_branchs(project_id);
CREATE INDEX idx_project_git_branchs_name ON project_git_branchs(name, project_id);
CREATE INDEX idx_project_git_branchs_status ON project_git_branchs(status);
CREATE INDEX idx_project_git_branchs_assigned_agent ON project_git_branchs(assigned_agent_id);
CREATE INDEX idx_project_git_branchs_priority ON project_git_branchs(priority);
CREATE INDEX idx_project_git_branchs_created_at ON project_git_branchs(created_at);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_git_branch_id ON tasks(git_branch_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_context_id ON tasks(context_id);
CREATE INDEX idx_task_subtasks_task_id ON task_subtasks(task_id);
CREATE INDEX idx_task_subtasks_status ON task_subtasks(status);
CREATE INDEX idx_task_subtasks_priority ON task_subtasks(priority);
CREATE INDEX idx_task_subtasks_progress ON task_subtasks(progress_percentage);
CREATE INDEX idx_task_dependencies_task_id ON task_dependencies(task_id);
CREATE INDEX idx_task_dependencies_depends_on ON task_dependencies(depends_on_task_id);
CREATE INDEX idx_task_dependencies_type ON task_dependencies(dependency_type);
CREATE INDEX idx_project_cross_tree_deps_project ON project_cross_tree_dependencies(project_id);
CREATE INDEX idx_project_cross_tree_deps_dependent ON project_cross_tree_dependencies(dependent_task_id);
CREATE INDEX idx_project_cross_tree_deps_prerequisite ON project_cross_tree_dependencies(prerequisite_task_id);
CREATE INDEX idx_project_work_sessions_project ON project_work_sessions(project_id);
CREATE INDEX idx_project_work_sessions_agent ON project_work_sessions(agent_id);
CREATE INDEX idx_project_work_sessions_task ON project_work_sessions(task_id);
CREATE INDEX idx_project_work_sessions_status ON project_work_sessions(status);
CREATE INDEX idx_project_work_sessions_started ON project_work_sessions(started_at);
CREATE INDEX idx_project_resource_locks_project ON project_resource_locks(project_id);
CREATE INDEX idx_project_resource_locks_resource ON project_resource_locks(resource_name);
CREATE INDEX idx_project_resource_locks_agent ON project_resource_locks(locked_by_agent_id);
CREATE INDEX idx_project_resource_locks_expires ON project_resource_locks(expires_at);
CREATE INDEX idx_project_agents_project ON project_agents(project_id);
CREATE INDEX idx_project_agents_status ON project_agents(status);
CREATE INDEX idx_project_agents_workload ON project_agents(current_workload);
CREATE INDEX idx_project_agent_assignments_agent ON project_agent_assignments(agent_id);
CREATE INDEX idx_project_agent_assignments_branch ON project_agent_assignments(git_branch_id);
CREATE INDEX idx_global_contexts_org ON global_contexts(organization_id);
CREATE INDEX idx_global_contexts_updated ON global_contexts(updated_at);
CREATE INDEX idx_project_contexts_global ON project_contexts(parent_global_id);
CREATE INDEX idx_project_contexts_updated ON project_contexts(updated_at);
CREATE INDEX idx_project_contexts_inherited ON project_contexts(last_inherited);
CREATE INDEX idx_project_contexts_inheritance_disabled ON project_contexts(inheritance_disabled);
CREATE INDEX idx_task_contexts_project ON task_contexts(parent_project_context_id);
CREATE INDEX idx_task_contexts_project_id ON task_contexts(parent_project_id);
CREATE INDEX idx_task_contexts_resolved_at ON task_contexts(resolved_at);
CREATE INDEX idx_task_contexts_updated ON task_contexts(updated_at);
CREATE INDEX idx_task_contexts_inheritance ON task_contexts(inheritance_disabled, force_local_only);
CREATE INDEX idx_task_contexts_dependencies_hash ON task_contexts(dependencies_hash);
CREATE INDEX idx_context_insights_context ON context_insights(context_id, context_type);
CREATE INDEX idx_context_insights_category ON context_insights(category);
CREATE INDEX idx_context_insights_importance ON context_insights(importance);
CREATE INDEX idx_context_insights_actionable ON context_insights(actionable);
CREATE INDEX idx_context_insights_created_at ON context_insights(created_at);
CREATE INDEX idx_context_insights_expires_at ON context_insights(expires_at);
CREATE INDEX idx_delegations_source ON context_delegations(source_level, source_id);
CREATE INDEX idx_delegations_target ON context_delegations(target_level, target_id);
CREATE INDEX idx_delegations_processed ON context_delegations(processed, auto_delegated);
CREATE INDEX idx_delegations_created_at ON context_delegations(created_at);
CREATE INDEX idx_delegations_trigger_type ON context_delegations(trigger_type);
CREATE INDEX idx_delegations_status ON context_delegations(implementation_status);
CREATE INDEX idx_cache_expires ON context_inheritance_cache(expires_at);
CREATE INDEX idx_cache_dependencies ON context_inheritance_cache(dependencies_hash);
CREATE INDEX idx_cache_hit_count ON context_inheritance_cache(hit_count DESC);
CREATE INDEX idx_cache_invalidated ON context_inheritance_cache(invalidated);
CREATE INDEX idx_propagations_source ON context_propagations(source_level, source_id);
CREATE INDEX idx_propagations_status ON context_propagations(propagation_status);
CREATE INDEX idx_propagations_created_at ON context_propagations(created_at);
CREATE INDEX idx_labels_normalized ON labels(normalized);
CREATE INDEX idx_labels_category ON labels(category);
CREATE INDEX idx_labels_usage_count ON labels(usage_count DESC);
CREATE INDEX idx_task_labels_task ON task_labels(task_id);
CREATE INDEX idx_task_labels_label ON task_labels(label_id);
CREATE INDEX idx_templates_type ON templates(type);
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_active ON templates(active);
CREATE INDEX idx_templates_usage_count ON templates(usage_count DESC);
CREATE INDEX idx_template_usage_template ON template_usage(template_id);
CREATE INDEX idx_template_usage_context ON template_usage(context_type, context_id);
CREATE INDEX idx_template_cache_expires ON template_cache(expires_at);
CREATE INDEX idx_checklists_category ON checklists(category);
CREATE INDEX idx_checklists_scope ON checklists(scope);
CREATE INDEX idx_checklists_auto_apply ON checklists(auto_apply);
CREATE INDEX idx_checklist_items_checklist ON checklist_items(checklist_id);
CREATE INDEX idx_checklist_items_order ON checklist_items(order_index);
CREATE INDEX idx_checklist_progress_context ON checklist_progress(context_type, context_id);
CREATE INDEX idx_checklist_progress_completion ON checklist_progress(completion_percentage);
CREATE INDEX idx_checklist_item_completion_progress ON checklist_item_completion(progress_id);
CREATE INDEX idx_checklist_item_completion_item ON checklist_item_completion(item_id);
CREATE INDEX idx_audit_log_table ON audit_log(table_name);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);
CREATE INDEX idx_audit_log_record ON audit_log(record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);
CREATE INDEX idx_audit_log_changed_by ON audit_log(changed_by);
CREATE TRIGGER update_project_timestamp 
    AFTER UPDATE ON projects
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER update_git_branch_timestamp 
    AFTER UPDATE ON project_git_branchs
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE project_git_branchs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER update_task_timestamp 
    AFTER UPDATE ON tasks
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER update_subtask_timestamp 
    AFTER UPDATE ON task_subtasks
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE task_subtasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER update_agent_timestamp 
    AFTER UPDATE ON project_agents
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE project_agents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id AND project_id = NEW.project_id;
END;
CREATE TRIGGER update_task_on_subtask_change 
    AFTER UPDATE ON task_subtasks
    FOR EACH ROW 
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.task_id;
END;
CREATE TRIGGER update_task_count_on_insert
    AFTER INSERT ON tasks
    FOR EACH ROW
BEGIN
    UPDATE project_git_branchs 
    SET task_count = task_count + 1 
    WHERE id = NEW.git_branch_id;
END;
CREATE TRIGGER update_task_count_on_delete
    AFTER DELETE ON tasks
    FOR EACH ROW
BEGIN
    UPDATE project_git_branchs 
    SET task_count = task_count - 1 
    WHERE id = OLD.git_branch_id;
END;
CREATE TRIGGER update_completed_count_on_status_change
    AFTER UPDATE OF status ON tasks
    FOR EACH ROW
    WHEN OLD.status != NEW.status
BEGIN
    UPDATE project_git_branchs 
    SET completed_task_count = completed_task_count + 
        CASE WHEN NEW.status = 'done' THEN 1 ELSE 0 END -
        CASE WHEN OLD.status = 'done' THEN 1 ELSE 0 END
    WHERE id = NEW.git_branch_id;
END;
CREATE TRIGGER update_global_context_timestamp 
    AFTER UPDATE ON global_contexts
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE global_contexts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER update_project_context_timestamp 
    AFTER UPDATE ON project_contexts
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE project_contexts SET updated_at = CURRENT_TIMESTAMP WHERE project_id = NEW.project_id;
END;
CREATE TRIGGER update_task_context_timestamp 
    AFTER UPDATE ON task_contexts
    FOR EACH ROW 
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE task_contexts SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
END;
CREATE TRIGGER invalidate_cache_on_global_change
    AFTER UPDATE ON global_contexts
    FOR EACH ROW
BEGIN
    UPDATE context_inheritance_cache SET invalidated = 1, invalidation_reason = 'global_context_updated' 
    WHERE context_level IN ('project', 'task');
END;
CREATE TRIGGER invalidate_cache_on_project_change
    AFTER UPDATE ON project_contexts
    FOR EACH ROW
BEGIN
    UPDATE context_inheritance_cache SET invalidated = 1, invalidation_reason = 'project_context_updated'
    WHERE (context_level = 'task' AND context_id IN (
        SELECT task_id FROM task_contexts WHERE parent_project_context_id = NEW.project_id
    )) OR (context_level = 'project' AND context_id = NEW.project_id);
END;
CREATE TRIGGER invalidate_cache_on_task_change
    AFTER UPDATE ON task_contexts
    FOR EACH ROW
BEGIN
    UPDATE context_inheritance_cache SET invalidated = 1, invalidation_reason = 'task_context_updated'
    WHERE context_level = 'task' AND context_id = NEW.task_id;
END;
CREATE TRIGGER increment_label_usage
    AFTER INSERT ON task_labels
    FOR EACH ROW
BEGIN
    UPDATE labels SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.label_id;
END;
CREATE TRIGGER decrement_label_usage
    AFTER DELETE ON task_labels
    FOR EACH ROW
BEGIN
    UPDATE labels SET usage_count = usage_count - 1, updated_at = CURRENT_TIMESTAMP 
    WHERE id = OLD.label_id;
END;
CREATE TRIGGER update_template_usage_on_use
    AFTER INSERT ON template_usage
    FOR EACH ROW
BEGIN
    UPDATE templates 
    SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP 
    WHERE id = NEW.template_id;
END;
CREATE TRIGGER update_checklist_progress_on_item_completion
    AFTER UPDATE ON checklist_item_completion
    FOR EACH ROW
    WHEN NEW.completed != OLD.completed
BEGIN
    UPDATE checklist_progress 
    SET completion_percentage = (
        SELECT ROUND(
            (COUNT(CASE WHEN completed = 1 THEN 1 END) * 100.0) / COUNT(*), 2
        )
        FROM checklist_item_completion 
        WHERE progress_id = NEW.progress_id
    ),
    completed_at = CASE 
        WHEN (
            SELECT COUNT(CASE WHEN completed = 0 THEN 1 END) 
            FROM checklist_item_completion 
            WHERE progress_id = NEW.progress_id
        ) = 0 THEN CURRENT_TIMESTAMP 
        ELSE NULL 
    END
    WHERE id = NEW.progress_id;
END;
CREATE TRIGGER audit_tasks_insert
    AFTER INSERT ON tasks
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, new_values, changed_by)
    VALUES ('tasks', 'INSERT', NEW.id, json_object(
        'title', NEW.title,
        'description', NEW.description,
        'git_branch_id', NEW.git_branch_id,
        'status', NEW.status,
        'priority', NEW.priority
    ), 'system');
END;
CREATE TRIGGER audit_tasks_update
    AFTER UPDATE ON tasks
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values, changed_by)
    VALUES ('tasks', 'UPDATE', NEW.id, json_object(
        'title', OLD.title,
        'description', OLD.description,
        'status', OLD.status,
        'priority', OLD.priority
    ), json_object(
        'title', NEW.title,
        'description', NEW.description,
        'status', NEW.status,
        'priority', NEW.priority
    ), 'system');
END;
CREATE TRIGGER audit_tasks_delete
    AFTER DELETE ON tasks
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, old_values, changed_by)
    VALUES ('tasks', 'DELETE', OLD.id, json_object(
        'title', OLD.title,
        'description', OLD.description,
        'status', OLD.status,
        'priority', OLD.priority
    ), 'system');
END;
CREATE VIEW task_statistics AS
SELECT 
    p.id as project_id,
    p.name as project_name,
    ptt.id as git_branch_id,
    ptt.name as git_branch_name,
    COUNT(t.id) as total_tasks,
    COUNT(CASE WHEN t.status = 'todo' THEN 1 END) as todo_tasks,
    COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_tasks,
    COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN t.status = 'blocked' THEN 1 END) as blocked_tasks,
    ROUND(
        (COUNT(CASE WHEN t.status = 'done' THEN 1 END) * 100.0) / 
        NULLIF(COUNT(t.id), 0), 2
    ) as completion_percentage,
    COUNT(CASE WHEN t.priority = 'critical' THEN 1 END) as critical_tasks,
    COUNT(CASE WHEN t.priority = 'high' THEN 1 END) as high_priority_tasks,
    COUNT(CASE WHEN t.priority = 'medium' THEN 1 END) as medium_priority_tasks,
    COUNT(CASE WHEN t.priority = 'low' THEN 1 END) as low_priority_tasks,
    MIN(t.created_at) as oldest_task_date,
    MAX(t.created_at) as newest_task_date,
    COUNT(CASE WHEN t.due_date IS NOT NULL AND t.due_date < datetime('now') AND t.status != 'done' THEN 1 END) as overdue_tasks
FROM projects p
LEFT JOIN project_git_branchs ptt ON p.id = ptt.project_id
LEFT JOIN tasks t ON ptt.id = t.git_branch_id
GROUP BY p.id, p.name, ptt.id, ptt.name;
CREATE VIEW subtask_progress AS
SELECT 
    t.id as task_id,
    t.title as task_title,
    t.status as task_status,
    COUNT(ts.id) as total_subtasks,
    COUNT(CASE WHEN ts.status = 'todo' THEN 1 END) as todo_subtasks,
    COUNT(CASE WHEN ts.status = 'in_progress' THEN 1 END) as in_progress_subtasks,
    COUNT(CASE WHEN ts.status = 'done' THEN 1 END) as completed_subtasks,
    ROUND(
        (COUNT(CASE WHEN ts.status = 'done' THEN 1 END) * 100.0) / 
        NULLIF(COUNT(ts.id), 0), 2
    ) as subtask_completion_percentage,
    ROUND(AVG(ts.progress_percentage), 2) as average_progress_percentage,
    GROUP_CONCAT(
        CASE WHEN ts.blockers != '' AND ts.blockers IS NOT NULL 
        THEN ts.title || ': ' || ts.blockers 
        END, '; '
    ) as active_blockers
FROM tasks t
LEFT JOIN task_subtasks ts ON t.id = ts.task_id
GROUP BY t.id, t.title, t.status;
CREATE VIEW agent_workload AS
SELECT 
    pa.project_id,
    pa.id as agent_id,
    pa.name as agent_name,
    pa.status,
    pa.current_workload,
    pa.max_concurrent_tasks,
    pa.completed_tasks,
    pa.success_rate,
    pa.average_task_duration,
    COUNT(wa.id) as active_assignments,
    COUNT(CASE WHEN wa.status = 'assigned' THEN 1 END) as pending_assignments,
    COUNT(CASE WHEN wa.status = 'in_progress' THEN 1 END) as in_progress_assignments,
    COUNT(CASE WHEN wa.status = 'completed' THEN 1 END) as completed_assignments,
    ROUND(
        pa.current_workload * 100.0 / NULLIF(pa.max_concurrent_tasks, 0), 2
    ) as workload_percentage,
    CASE 
        WHEN pa.current_workload >= pa.max_concurrent_tasks THEN 'overloaded'
        WHEN pa.current_workload >= pa.max_concurrent_tasks * 0.8 THEN 'high'
        WHEN pa.current_workload >= pa.max_concurrent_tasks * 0.5 THEN 'medium'
        ELSE 'low'
    END as workload_status
FROM project_agents pa
LEFT JOIN work_assignments wa ON pa.id = wa.agent_id
GROUP BY pa.project_id, pa.id, pa.name, pa.status, pa.current_workload, 
         pa.max_concurrent_tasks, pa.completed_tasks, pa.success_rate, pa.average_task_duration;
CREATE VIEW context_health AS
SELECT 
    'global' as level,
    COUNT(*) as total_contexts,
    COUNT(CASE WHEN updated_at > datetime('now', '-1 day') THEN 1 END) as recently_updated,
    COUNT(CASE WHEN delegation_rules IS NOT NULL THEN 1 END) as with_delegation_rules,
    AVG(version) as average_version
FROM global_contexts
UNION ALL
SELECT 
    'project' as level,
    COUNT(*) as total_contexts,
    COUNT(CASE WHEN updated_at > datetime('now', '-1 day') THEN 1 END) as recently_updated,
    COUNT(CASE WHEN inheritance_disabled = 0 THEN 1 END) as with_inheritance,
    AVG(version) as average_version
FROM project_contexts
UNION ALL
SELECT 
    'task' as level,
    COUNT(*) as total_contexts,
    COUNT(CASE WHEN updated_at > datetime('now', '-1 day') THEN 1 END) as recently_updated,
    COUNT(CASE WHEN resolved_context IS NOT NULL THEN 1 END) as with_resolved_cache,
    AVG(version) as average_version
FROM task_contexts;
CREATE VIEW label_analytics AS
SELECT 
    l.id,
    l.label,
    l.category,
    l.usage_count,
    l.is_common,
    COUNT(tl.task_id) as active_task_count,
    l.usage_count - COUNT(tl.task_id) as historical_usage,
    ROUND(
        (COUNT(tl.task_id) * 100.0) / NULLIF(l.usage_count, 0), 2
    ) as current_usage_percentage,
    MIN(tl.added_at) as first_used,
    MAX(tl.added_at) as last_used,
    julianday('now') - julianday(MAX(tl.added_at)) as days_since_last_use
FROM labels l
LEFT JOIN task_labels tl ON l.id = tl.label_id
GROUP BY l.id, l.label, l.category, l.usage_count, l.is_common
ORDER BY l.usage_count DESC;
CREATE VIEW template_effectiveness AS
SELECT 
    t.id,
    t.name,
    t.type,
    t.category,
    t.usage_count,
    t.success_rate,
    t.active,
    COUNT(tu.id) as total_usages,
    COUNT(CASE WHEN tu.outcome = 'success' THEN 1 END) as successful_usages,
    COUNT(CASE WHEN tu.outcome = 'failure' THEN 1 END) as failed_usages,
    COUNT(CASE WHEN tu.outcome = 'pending' THEN 1 END) as pending_usages,
    ROUND(
        (COUNT(CASE WHEN tu.outcome = 'success' THEN 1 END) * 100.0) / 
        NULLIF(COUNT(CASE WHEN tu.outcome IN ('success', 'failure') THEN 1 END), 0), 2
    ) as actual_success_rate,
    AVG(tu.duration_seconds) as average_duration,
    AVG(tu.feedback_score) as average_feedback_score,
    julianday('now') - julianday(t.last_used) as days_since_last_use
FROM templates t
LEFT JOIN template_usage tu ON t.id = tu.template_id
WHERE t.active = 1
GROUP BY t.id, t.name, t.type, t.category, t.usage_count, t.success_rate, t.active
ORDER BY t.usage_count DESC;
CREATE VIEW checklist_analytics AS
SELECT 
    c.id,
    c.name,
    c.category,
    c.scope,
    c.auto_apply,
    COUNT(cp.id) as total_instances,
    COUNT(CASE WHEN cp.completed_at IS NOT NULL THEN 1 END) as completed_instances,
    ROUND(
        (COUNT(CASE WHEN cp.completed_at IS NOT NULL THEN 1 END) * 100.0) / 
        NULLIF(COUNT(cp.id), 0), 2
    ) as completion_rate,
    AVG(cp.completion_percentage) as average_completion_percentage,
    AVG(
        CASE WHEN cp.completed_at IS NOT NULL 
        THEN julianday(cp.completed_at) - julianday(cp.started_at) 
        END
    ) as average_completion_days,
    COUNT(ci.id) as total_items,
    AVG(
        CASE WHEN ci.estimated_duration IS NOT NULL 
        THEN ci.estimated_duration 
        END
    ) as average_estimated_duration
FROM checklists c
LEFT JOIN checklist_progress cp ON c.id = cp.checklist_id
LEFT JOIN checklist_items ci ON c.id = ci.checklist_id
WHERE c.active = 1
GROUP BY c.id, c.name, c.category, c.scope, c.auto_apply
ORDER BY completion_rate DESC;
CREATE VIEW database_health AS
SELECT 
    'tasks' as table_name,
    COUNT(*) as record_count,
    COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as recent_additions,
    COUNT(CASE WHEN updated_at > datetime('now', '-1 day') THEN 1 END) as recent_updates,
    MAX(updated_at) as last_activity
FROM tasks
UNION ALL
SELECT 
    'subtasks' as table_name,
    COUNT(*) as record_count,
    COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as recent_additions,
    COUNT(CASE WHEN updated_at > datetime('now', '-1 day') THEN 1 END) as recent_updates,
    MAX(updated_at) as last_activity
FROM task_subtasks
UNION ALL
SELECT 
    'agents' as table_name,
    COUNT(*) as record_count,
    COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as recent_additions,
    COUNT(CASE WHEN updated_at > datetime('now', '-1 day') THEN 1 END) as recent_updates,
    MAX(updated_at) as last_activity
FROM project_agents
UNION ALL
SELECT 
    'contexts' as table_name,
    (SELECT COUNT(*) FROM global_contexts) + 
    (SELECT COUNT(*) FROM project_contexts) + 
    (SELECT COUNT(*) FROM task_contexts) as record_count,
    (SELECT COUNT(*) FROM global_contexts WHERE updated_at > datetime('now', '-1 day')) +
    (SELECT COUNT(*) FROM project_contexts WHERE updated_at > datetime('now', '-1 day')) +
    (SELECT COUNT(*) FROM task_contexts WHERE updated_at > datetime('now', '-1 day')) as recent_additions,
    (SELECT COUNT(*) FROM global_contexts WHERE updated_at > datetime('now', '-1 day')) +
    (SELECT COUNT(*) FROM project_contexts WHERE updated_at > datetime('now', '-1 day')) +
    (SELECT COUNT(*) FROM task_contexts WHERE updated_at > datetime('now', '-1 day')) as recent_updates,
    (SELECT MAX(updated_at) FROM (
        SELECT updated_at FROM global_contexts 
        UNION ALL SELECT updated_at FROM project_contexts 
        UNION ALL SELECT updated_at FROM task_contexts
    )) as last_activity;
CREATE VIEW cache_performance AS
SELECT 
    context_level,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN invalidated = 0 THEN 1 END) as valid_entries,
    COUNT(CASE WHEN invalidated = 1 THEN 1 END) as invalidated_entries,
    ROUND(
        (COUNT(CASE WHEN invalidated = 0 THEN 1 END) * 100.0) / 
        NULLIF(COUNT(*), 0), 2
    ) as cache_hit_rate,
    AVG(hit_count) as average_hit_count,
    SUM(cache_size_bytes) as total_cache_size,
    COUNT(CASE WHEN expires_at < datetime('now') THEN 1 END) as expired_entries,
    MIN(created_at) as oldest_entry,
    MAX(last_hit) as most_recent_hit
FROM context_inheritance_cache
GROUP BY context_level;
CREATE VIEW recent_activity AS
SELECT 
    'task_created' as activity_type,
    t.id as entity_id,
    t.title as entity_name,
    t.created_at as activity_time,
    p.name as project_name,
    ptt.name as branch_name
FROM tasks t
JOIN project_git_branchs ptt ON t.git_branch_id = ptt.id
JOIN projects p ON ptt.project_id = p.id
WHERE t.created_at > datetime('now', '-7 days')
UNION ALL
SELECT 
    'task_completed' as activity_type,
    t.id as entity_id,
    t.title as entity_name,
    t.updated_at as activity_time,
    p.name as project_name,
    ptt.name as branch_name
FROM tasks t
JOIN project_git_branchs ptt ON t.git_branch_id = ptt.id
JOIN projects p ON ptt.project_id = p.id
WHERE t.status = 'done' AND t.updated_at > datetime('now', '-7 days')
UNION ALL
SELECT 
    'subtask_completed' as activity_type,
    ts.id as entity_id,
    ts.title as entity_name,
    ts.completed_at as activity_time,
    p.name as project_name,
    ptt.name as branch_name
FROM task_subtasks ts
JOIN tasks t ON ts.task_id = t.id
JOIN project_git_branchs ptt ON t.git_branch_id = ptt.id
JOIN projects p ON ptt.project_id = p.id
WHERE ts.status = 'done' AND ts.completed_at > datetime('now', '-7 days')
UNION ALL
SELECT 
    'agent_assigned' as activity_type,
    wa.id as entity_id,
    'Assignment to ' || wa.agent_id as entity_name,
    wa.created_at as activity_time,
    p.name as project_name,
    ptt.name as branch_name
FROM work_assignments wa
JOIN tasks t ON wa.task_id = t.id
JOIN project_git_branchs ptt ON t.git_branch_id = ptt.id
JOIN projects p ON ptt.project_id = p.id
WHERE wa.created_at > datetime('now', '-7 days')
ORDER BY activity_time DESC;
CREATE VIEW performance_bottlenecks AS
SELECT 
    'overdue_tasks' as bottleneck_type,
    COUNT(*) as count,
    'Tasks past due date' as description,
    'high' as severity
FROM tasks 
WHERE due_date IS NOT NULL 
    AND due_date < datetime('now') 
    AND status != 'done'
UNION ALL
SELECT 
    'blocked_tasks' as bottleneck_type,
    COUNT(*) as count,
    'Tasks in blocked status' as description,
    'medium' as severity
FROM tasks 
WHERE status = 'blocked'
UNION ALL
SELECT 
    'overloaded_agents' as bottleneck_type,
    COUNT(*) as count,
    'Agents at max capacity' as description,
    'high' as severity
FROM project_agents 
WHERE current_workload >= max_concurrent_tasks
UNION ALL
SELECT 
    'stale_contexts' as bottleneck_type,
    COUNT(*) as count,
    'Contexts not updated in 7 days' as description,
    'low' as severity
FROM task_contexts 
WHERE updated_at < datetime('now', '-7 days')
UNION ALL
SELECT 
    'invalidated_cache' as bottleneck_type,
    COUNT(*) as count,
    'Invalidated cache entries' as description,
    'medium' as severity
FROM context_inheritance_cache 
WHERE invalidated = 1;
CREATE VIEW executive_summary AS
SELECT 
    (SELECT COUNT(*) FROM projects WHERE status = 'active') as active_projects,
    (SELECT COUNT(*) FROM project_git_branchs) as total_branches,
    (SELECT COUNT(*) FROM tasks) as total_tasks,
    (SELECT COUNT(*) FROM tasks WHERE status = 'done') as completed_tasks,
    (SELECT COUNT(*) FROM tasks WHERE status = 'in_progress') as active_tasks,
    (SELECT COUNT(*) FROM tasks WHERE status = 'blocked') as blocked_tasks,
    (SELECT COUNT(*) FROM project_agents WHERE status = 'available') as available_agents,
    (SELECT COUNT(*) FROM project_agents WHERE current_workload >= max_concurrent_tasks) as overloaded_agents,
    ROUND(
        (SELECT COUNT(*) FROM tasks WHERE status = 'done') * 100.0 / 
        NULLIF((SELECT COUNT(*) FROM tasks), 0), 2
    ) as overall_completion_rate,
    (SELECT COUNT(*) FROM tasks WHERE due_date < datetime('now') AND status != 'done') as overdue_tasks,
    (SELECT COUNT(*) FROM coordination_requests WHERE status = 'pending') as pending_coordination_requests,
    (SELECT COUNT(*) FROM context_delegations WHERE processed = 0) as pending_delegations;
CREATE VIEW coordination_status AS
SELECT 
    cr.request_type,
    cr.priority,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN cr.status = 'pending' THEN 1 END) as pending_requests,
    COUNT(CASE WHEN cr.status = 'resolved' THEN 1 END) as resolved_requests,
    AVG(
        CASE WHEN cr.resolved_at IS NOT NULL 
        THEN julianday(cr.resolved_at) - julianday(cr.created_at) 
        END
    ) as average_resolution_days,
    MAX(cr.created_at) as last_request_time
FROM coordination_requests cr
GROUP BY cr.request_type, cr.priority
ORDER BY pending_requests DESC, total_requests DESC;
CREATE INDEX idx_coordination_requests_agent ON coordination_requests(requesting_agent_id);
CREATE INDEX idx_coordination_requests_target ON coordination_requests(target_agent_id);
CREATE INDEX idx_coordination_requests_type ON coordination_requests(coordination_type);
CREATE INDEX idx_work_assignments_task ON work_assignments(task_id);
CREATE INDEX idx_work_assignments_agent ON work_assignments(assigned_agent_id);
CREATE INDEX idx_work_assignments_completed ON work_assignments(is_completed);
CREATE INDEX idx_work_handoffs_task ON work_handoffs(task_id);
CREATE INDEX idx_work_handoffs_from_agent ON work_handoffs(from_agent_id);
CREATE INDEX idx_work_handoffs_to_agent ON work_handoffs(to_agent_id);
CREATE INDEX idx_work_handoffs_status ON work_handoffs(status);
CREATE INDEX idx_conflict_resolutions_task ON conflict_resolutions(task_id);
CREATE INDEX idx_conflict_resolutions_resolved ON conflict_resolutions(is_resolved);
CREATE INDEX idx_agent_communications_from ON agent_communications(from_agent_id);
CREATE INDEX idx_agent_communications_task ON agent_communications(task_id);
COMMIT;
