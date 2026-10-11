-- 0001_baseline: the schema a live database already holds.
--
-- THIS FILE IS THE BASELINE, NOT A DELTA. On a database that already has the schema, the runner must
-- NOT execute it: the mark that records it is an owner action (Runner.MarkBaseline), because deciding
-- that a live database equals this file is a claim about production data. On a fresh database it
-- executes, which is how a new environment gets the whole schema in one recorded step.
--
-- Every statement carries IF NOT EXISTS because createAll (the Go registry's own DDL) runs before the
-- runner on this path, so the tables are usually already there when this step is reached.
--
-- Written from the runtime registry by a throwaway command in .gotmp (since deleted), then frozen:
-- applied_migrations records this file's NAME and the name is the step's identity, so this file must
-- never be renamed, reordered or edited once it has been applied anywhere.
-- TestSchemaMatchesGoDefinitions holds the registry to this file from here on.
--
-- The six ProductionTables are deliberately NOT here. They are registered as definitions but nothing
-- appends them to the runtime set, so no code path creates them today; whether a live database holds
-- them is the question the dump comparison answers, and they belong in a later step if it does.

-- agent_sessions
CREATE TABLE IF NOT EXISTS agent_sessions (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(64) NOT NULL,
	connector_id VARCHAR(64) NOT NULL,
	session_key VARCHAR(255) NOT NULL,
	name VARCHAR(255) NOT NULL,
	project VARCHAR(255),
	status VARCHAR(20) NOT NULL,
	last_seq INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	last_seen TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	room_slug VARCHAR(255),
	seat_key VARCHAR(255),
	client_cursor VARCHAR(512),
	seat_state VARCHAR(20),
	PRIMARY KEY (id),
	CONSTRAINT uq_agent_sessions_key UNIQUE (user_id, connector_id, session_key),
	CONSTRAINT ck_agent_sessions_seat_pair CHECK ((room_slug IS NULL) = (seat_key IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_agent_sessions_user_id ON agent_sessions (user_id);

-- api_tokens
CREATE TABLE IF NOT EXISTS api_tokens (
	id VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	token_hash VARCHAR NOT NULL,
	scopes JSON NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	last_used_at TIMESTAMP WITHOUT TIME ZONE,
	usage_count INTEGER NOT NULL,
	rate_limit INTEGER NOT NULL,
	usage_stats JSON NOT NULL,
	is_active BOOLEAN NOT NULL,
	token_metadata JSON NOT NULL,
	PRIMARY KEY (id)
);

-- context_delegations
CREATE TABLE IF NOT EXISTS context_delegations (
	id UUID NOT NULL,
	source_level VARCHAR NOT NULL,
	source_id UUID NOT NULL,
	source_type VARCHAR NOT NULL,
	target_level VARCHAR NOT NULL,
	target_id UUID NOT NULL,
	target_type VARCHAR NOT NULL,
	delegated_data JSON NOT NULL,
	delegation_data JSON NOT NULL,
	delegation_reason VARCHAR NOT NULL,
	trigger_type VARCHAR NOT NULL,
	auto_delegated BOOLEAN NOT NULL,
	confidence_score FLOAT,
	processed BOOLEAN NOT NULL,
	status VARCHAR NOT NULL,
	approved BOOLEAN,
	processed_by VARCHAR,
	rejected_reason VARCHAR,
	error_message VARCHAR,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	processed_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT chk_source_level CHECK (source_level IN ('task', 'branch', 'project', 'global')),
	CONSTRAINT chk_target_level CHECK (target_level IN ('task', 'branch', 'project', 'global')),
	CONSTRAINT chk_trigger_type CHECK (trigger_type IN ('manual', 'auto_pattern', 'auto_threshold'))
);
CREATE INDEX IF NOT EXISTS idx_delegation_processed ON context_delegations (processed);
CREATE INDEX IF NOT EXISTS idx_delegation_source ON context_delegations (source_level, source_id);
CREATE INDEX IF NOT EXISTS idx_delegation_target ON context_delegations (target_level, target_id);

-- context_inheritance_cache
CREATE TABLE IF NOT EXISTS context_inheritance_cache (
	id UUID NOT NULL,
	context_id UUID NOT NULL,
	context_level VARCHAR NOT NULL,
	context_type VARCHAR NOT NULL,
	resolved_context JSON NOT NULL,
	resolved_data JSON NOT NULL,
	dependencies_hash VARCHAR NOT NULL,
	resolution_path VARCHAR NOT NULL,
	parent_chain JSON NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	hit_count INTEGER NOT NULL,
	last_hit TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	cache_size_bytes INTEGER NOT NULL,
	invalidated BOOLEAN NOT NULL,
	invalidation_reason VARCHAR,
	user_id VARCHAR NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_cache_context_level CHECK (context_level IN ('task', 'branch', 'project', 'global')),
	CONSTRAINT uq_cache_context UNIQUE (context_id, context_level)
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON context_inheritance_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_invalidated ON context_inheritance_cache (invalidated);
CREATE INDEX IF NOT EXISTS idx_cache_level ON context_inheritance_cache (context_level);

-- global_contexts
CREATE TABLE IF NOT EXISTS global_contexts (
	id UUID NOT NULL,
	organization_id UUID,
	organization_standards JSON NOT NULL,
	security_policies JSON NOT NULL,
	compliance_requirements JSON NOT NULL,
	shared_resources JSON NOT NULL,
	reusable_patterns JSON NOT NULL,
	global_preferences JSON NOT NULL,
	delegation_rules JSON NOT NULL,
	nested_structure JSON NOT NULL,
	unified_context_data JSON,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	version INTEGER NOT NULL,
	PRIMARY KEY (id)
);

-- labels
CREATE TABLE IF NOT EXISTS labels (
	id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	color VARCHAR NOT NULL,
	description TEXT NOT NULL,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name)
);

-- missed_notifications
CREATE TABLE IF NOT EXISTS missed_notifications (
	id VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	message JSON NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	delivered BOOLEAN NOT NULL,
	delivery_attempts INTEGER NOT NULL,
	last_attempt_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_missed_notifications_created_at ON missed_notifications (created_at);
CREATE INDEX IF NOT EXISTS idx_missed_notifications_user_delivered ON missed_notifications (user_id, delivered);
CREATE INDEX IF NOT EXISTS ix_missed_notifications_delivered ON missed_notifications (delivered);
CREATE INDEX IF NOT EXISTS ix_missed_notifications_user_id ON missed_notifications (user_id);

-- projects
CREATE TABLE IF NOT EXISTS projects (
	id UUID NOT NULL,
	name VARCHAR NOT NULL,
	description TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	user_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	metadata JSON NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_project_user UNIQUE (id, user_id)
);

-- templates
CREATE TABLE IF NOT EXISTS templates (
	id UUID NOT NULL,
	name VARCHAR NOT NULL,
	template_name VARCHAR NOT NULL,
	template_content TEXT NOT NULL,
	template_type VARCHAR NOT NULL,
	type VARCHAR NOT NULL,
	content JSON NOT NULL,
	category VARCHAR NOT NULL,
	tags JSON NOT NULL,
	usage_count INTEGER NOT NULL,
	user_id VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	created_by VARCHAR NOT NULL,
	metadata JSON NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_template_category ON templates (category);
CREATE INDEX IF NOT EXISTS idx_template_type ON templates (type);

-- agent_session_events
CREATE TABLE IF NOT EXISTS agent_session_events (
	id SERIAL NOT NULL,
	session_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(64) NOT NULL,
	seq INTEGER NOT NULL,
	type VARCHAR(32) NOT NULL,
	payload JSON NOT NULL,
	ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_agent_session_events_seq UNIQUE (session_id, seq),
	FOREIGN KEY(session_id) REFERENCES agent_sessions (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_agent_session_events_user_session ON agent_session_events (user_id, session_id, seq);

-- project_contexts
CREATE TABLE IF NOT EXISTS project_contexts (
	id UUID NOT NULL,
	project_id UUID,
	parent_global_id UUID,
	data JSON,
	project_info JSON,
	team_preferences JSON,
	technology_stack JSON,
	project_workflow JSON,
	local_standards JSON,
	project_settings JSON,
	technical_specifications JSON,
	global_overrides JSON,
	delegation_rules JSON,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	version INTEGER,
	inheritance_disabled BOOLEAN,
	PRIMARY KEY (id),
	FOREIGN KEY(parent_global_id) REFERENCES global_contexts (id)
);

-- project_git_branchs
CREATE TABLE IF NOT EXISTS project_git_branchs (
	id UUID NOT NULL,
	project_id UUID NOT NULL,
	name VARCHAR NOT NULL,
	description TEXT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	assigned_agent_id VARCHAR,
	agent_id UUID,
	priority VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	metadata JSON NOT NULL,
	task_count INTEGER NOT NULL,
	completed_task_count INTEGER NOT NULL,
	user_id VARCHAR NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_branch_project UNIQUE (id, project_id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- branch_contexts
CREATE TABLE IF NOT EXISTS branch_contexts (
	id UUID NOT NULL,
	branch_id UUID,
	parent_project_id UUID,
	data JSON,
	branch_info JSON,
	branch_workflow JSON,
	feature_flags JSON,
	discovered_patterns JSON,
	branch_decisions JSON,
	active_patterns JSON,
	local_overrides JSON,
	delegation_rules JSON,
	inheritance_disabled BOOLEAN,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	version INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY(branch_id) REFERENCES project_git_branchs (id),
	FOREIGN KEY(parent_project_id) REFERENCES project_contexts (id)
);

-- tasks
CREATE TABLE IF NOT EXISTS tasks (
	id UUID NOT NULL,
	title VARCHAR NOT NULL,
	description TEXT NOT NULL,
	git_branch_id UUID NOT NULL,
	status VARCHAR NOT NULL,
	priority VARCHAR NOT NULL,
	progress_history JSON NOT NULL,
	progress_count INTEGER NOT NULL,
	estimated_effort VARCHAR NOT NULL,
	due_date VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	completed_at TIMESTAMP WITHOUT TIME ZONE,
	completion_summary TEXT NOT NULL,
	testing_notes TEXT NOT NULL,
	context_id UUID,
	progress_percentage INTEGER NOT NULL,
	progress_state progressstate NOT NULL,
	completed_subtasks INTEGER,
	subtask_count INTEGER,
	user_id VARCHAR NOT NULL,
	ai_system_prompt TEXT DEFAULT '' NOT NULL,
	ai_request_prompt TEXT DEFAULT '' NOT NULL,
	ai_work_context JSON DEFAULT '{}' NOT NULL,
	ai_completion_criteria TEXT DEFAULT '' NOT NULL,
	ai_execution_history JSON DEFAULT '[]' NOT NULL,
	ai_last_execution TIMESTAMP WITHOUT TIME ZONE,
	ai_model_preferences JSON DEFAULT '{}' NOT NULL,
	acceptance_criteria JSON DEFAULT '[]' NOT NULL,
	scope JSON DEFAULT '[]' NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(git_branch_id) REFERENCES project_git_branchs (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_task_branch ON tasks (git_branch_id);
CREATE INDEX IF NOT EXISTS idx_task_created ON tasks (created_at);
CREATE INDEX IF NOT EXISTS idx_task_priority ON tasks (priority);
CREATE INDEX IF NOT EXISTS idx_task_status ON tasks (status);

-- subtasks
CREATE TABLE IF NOT EXISTS subtasks (
	id UUID NOT NULL,
	task_id UUID NOT NULL,
	title VARCHAR NOT NULL,
	description TEXT NOT NULL,
	status VARCHAR NOT NULL,
	priority VARCHAR NOT NULL,
	assignees JSON NOT NULL,
	estimated_effort VARCHAR,
	progress_percentage INTEGER NOT NULL,
	progress_history JSON NOT NULL,
	progress_count INTEGER NOT NULL,
	progress_state progressstate NOT NULL,
	progress_notes TEXT NOT NULL,
	blockers TEXT NOT NULL,
	completion_summary TEXT NOT NULL,
	impact_on_parent TEXT NOT NULL,
	insights_found JSON NOT NULL,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	completed_at TIMESTAMP WITHOUT TIME ZONE,
	ai_system_prompt TEXT DEFAULT '' NOT NULL,
	ai_request_prompt TEXT DEFAULT '' NOT NULL,
	ai_work_context JSON DEFAULT '{}' NOT NULL,
	ai_completion_criteria TEXT DEFAULT '' NOT NULL,
	ai_execution_history JSON DEFAULT '[]' NOT NULL,
	ai_last_execution TIMESTAMP WITHOUT TIME ZONE,
	ai_model_preferences JSON DEFAULT '{}' NOT NULL,
	acceptance_criteria JSON DEFAULT '[]' NOT NULL,
	scope JSON DEFAULT '[]' NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_subtask_status ON subtasks (status);
CREATE INDEX IF NOT EXISTS idx_subtask_task ON subtasks (task_id);

-- task_assignees
CREATE TABLE IF NOT EXISTS task_assignees (
	id UUID NOT NULL,
	task_id UUID NOT NULL,
	assignee_id VARCHAR NOT NULL,
	agent_id UUID,
	role VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_task_assignee UNIQUE (task_id, assignee_id),
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_assignee_id ON task_assignees (assignee_id);
CREATE INDEX IF NOT EXISTS idx_assignee_task ON task_assignees (task_id);

-- task_contexts
CREATE TABLE IF NOT EXISTS task_contexts (
	id UUID NOT NULL,
	task_id UUID,
	parent_branch_id UUID,
	parent_branch_context_id UUID,
	data JSON,
	task_data JSON,
	execution_context JSON,
	discovered_patterns JSON,
	implementation_notes JSON,
	test_results JSON,
	blockers JSON,
	local_decisions JSON,
	delegation_queue JSON,
	local_overrides JSON,
	delegation_triggers JSON,
	inheritance_disabled BOOLEAN,
	force_local_only BOOLEAN,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	version INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
	FOREIGN KEY(parent_branch_id) REFERENCES project_git_branchs (id),
	FOREIGN KEY(parent_branch_context_id) REFERENCES branch_contexts (id)
);

-- task_dependencies
CREATE TABLE IF NOT EXISTS task_dependencies (
	id SERIAL NOT NULL,
	task_id UUID NOT NULL,
	depends_on_task_id UUID NOT NULL,
	dependency_type VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_task_dependency UNIQUE (task_id, depends_on_task_id),
	CONSTRAINT chk_no_self_dependency CHECK (task_id != depends_on_task_id),
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
	FOREIGN KEY(depends_on_task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- task_labels
CREATE TABLE IF NOT EXISTS task_labels (
	task_id UUID NOT NULL,
	label_id VARCHAR NOT NULL,
	user_id VARCHAR NOT NULL,
	applied_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (task_id, label_id),
	FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,
	FOREIGN KEY(label_id) REFERENCES labels (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_task_label_label ON task_labels (label_id);
CREATE INDEX IF NOT EXISTS idx_task_label_task ON task_labels (task_id);

-- task_events
CREATE TABLE IF NOT EXISTS task_events (
	id UUID NOT NULL,
	task_id UUID NOT NULL,
	subtask_id UUID,
	user_id VARCHAR(64) NOT NULL,
	seq INTEGER NOT NULL,
	user_seq BIGINT NOT NULL,
	client_event_id UUID,
	kind VARCHAR(32) NOT NULL,
	actor_kind VARCHAR(16) NOT NULL,
	actor_id VARCHAR(255) NOT NULL,
	payload JSONB,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_task_event_seq UNIQUE (task_id, seq),
	CONSTRAINT uq_task_event_user_seq UNIQUE (user_id, user_seq),
	CONSTRAINT uq_task_event_client_event UNIQUE (user_id, client_event_id),
	CONSTRAINT ck_task_event_kind CHECK (kind IN ('assigned', 'claimed', 'delivered', 'context_loaded', 'progress', 'status_changed', 'evidence_submitted', 'gate_verdict', 'escalated', 'human_decision', 'handover', 'context_updated')),
	CONSTRAINT ck_task_event_actor_kind CHECK (actor_kind IN ('seat', 'client', 'gate', 'human')),
	FOREIGN KEY(task_id) REFERENCES tasks (id)
);
CREATE INDEX IF NOT EXISTS idx_task_event_task_seq ON task_events (task_id, seq);

-- users
CREATE TABLE IF NOT EXISTS users (
	id UUID NOT NULL,
	email VARCHAR(254) NOT NULL,
	username VARCHAR(150) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	full_name VARCHAR(255),
	status VARCHAR(50) NOT NULL,
	roles JSON NOT NULL,
	email_verified BOOLEAN NOT NULL,
	email_verified_at TIMESTAMP WITHOUT TIME ZONE,
	last_login_at TIMESTAMP WITHOUT TIME ZONE,
	failed_login_attempts INTEGER NOT NULL,
	locked_until TIMESTAMP WITHOUT TIME ZONE,
	password_changed_at TIMESTAMP WITHOUT TIME ZONE,
	password_reset_token VARCHAR(255),
	password_reset_expires TIMESTAMP WITHOUT TIME ZONE,
	refresh_token_family VARCHAR(255),
	refresh_token_version INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	created_by VARCHAR(255),
	project_ids JSON NOT NULL,
	default_project_id UUID,
	metadata JSON NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email),
	UNIQUE (username),
	UNIQUE (password_reset_token),
	CONSTRAINT check_email_not_empty CHECK (length(email) > 0),
	CONSTRAINT check_username_not_empty CHECK (length(username) > 0)
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_status ON users (status);
CREATE INDEX IF NOT EXISTS ix_users_password_reset_token ON users (password_reset_token);
CREATE INDEX IF NOT EXISTS ix_users_refresh_token_family ON users (refresh_token_family);

-- user_token_balances
CREATE TABLE IF NOT EXISTS user_token_balances (
	id UUID NOT NULL,
	user_id UUID NOT NULL,
	available_tokens INTEGER NOT NULL,
	monthly_quota INTEGER NOT NULL,
	last_reset_at TIMESTAMP WITHOUT TIME ZONE,
	next_reset_at TIMESTAMP WITHOUT TIME ZONE,
	tokens_consumed_today INTEGER NOT NULL,
	tokens_consumed_this_month INTEGER NOT NULL,
	total_tokens_consumed INTEGER NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	CONSTRAINT check_available_tokens_non_negative CHECK (available_tokens >= 0),
	CONSTRAINT check_monthly_quota_non_negative CHECK (monthly_quota >= 0),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_user_token_balances_user_id ON user_token_balances (user_id);

-- rig_safeguards
CREATE TABLE IF NOT EXISTS rig_safeguards (
	user_id VARCHAR(64) NOT NULL,
	connector_id VARCHAR(64) NOT NULL,
	rig VARCHAR(255) NOT NULL,
	safeguard VARCHAR(32) NOT NULL,
	state VARCHAR(20) NOT NULL,
	pid INTEGER,
	restarts INTEGER NOT NULL,
	age_s INTEGER NOT NULL,
	last_beat_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (user_id, connector_id, rig, safeguard),
	CONSTRAINT ck_rig_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),
	CONSTRAINT ck_rig_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'bridge', 'rigd'))
);
CREATE INDEX IF NOT EXISTS ix_rig_safeguards_user_connector ON rig_safeguards (user_id, connector_id);

-- teams
CREATE TABLE IF NOT EXISTS teams (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	slug TEXT NOT NULL,
	name TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_teams_user_slug UNIQUE (user_id, slug)
);
CREATE INDEX IF NOT EXISTS ix_teams_user_id ON teams (user_id);

-- team_members
CREATE TABLE IF NOT EXISTS team_members (
	id UUID NOT NULL,
	team_id UUID NOT NULL REFERENCES teams (id),
	user_id TEXT NOT NULL,
	role TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_team_members_team_user UNIQUE (team_id, user_id),
	CONSTRAINT ck_team_members_role CHECK (role IN ('owner', 'viewer'))
);
CREATE INDEX IF NOT EXISTS ix_team_members_team_id ON team_members (team_id);
CREATE INDEX IF NOT EXISTS ix_team_members_user_id ON team_members (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_team_members_one_owner ON team_members (team_id) WHERE role = 'owner';

-- modules
CREATE TABLE IF NOT EXISTS modules (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	slug TEXT NOT NULL,
	kind TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_modules_user_slug UNIQUE (user_id, slug),
	CONSTRAINT ck_modules_kind CHECK (kind IN ('instruction', 'document', 'skill', 'tool', 'mcp', 'memory', 'policy'))
);
CREATE INDEX IF NOT EXISTS ix_modules_user_id ON modules (user_id);

-- module_versions
CREATE TABLE IF NOT EXISTS module_versions (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	module_id UUID NOT NULL REFERENCES modules (id),
	version TEXT NOT NULL,
	content TEXT NOT NULL,
	checksum TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_module_versions_module_version UNIQUE (module_id, version)
);
CREATE INDEX IF NOT EXISTS ix_module_versions_user_id ON module_versions (user_id);
CREATE INDEX IF NOT EXISTS ix_module_versions_module_id ON module_versions (module_id);

-- seat_types
CREATE TABLE IF NOT EXISTS seat_types (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	slug TEXT NOT NULL,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_seat_types_user_slug UNIQUE (user_id, slug)
);
CREATE INDEX IF NOT EXISTS ix_seat_types_user_id ON seat_types (user_id);

-- seat_type_versions
CREATE TABLE IF NOT EXISTS seat_type_versions (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	seat_type_id UUID NOT NULL REFERENCES seat_types (id),
	version TEXT NOT NULL,
	default_runtime TEXT NOT NULL,
	module_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_seat_type_versions_seat_type_version UNIQUE (seat_type_id, version)
);
CREATE INDEX IF NOT EXISTS ix_seat_type_versions_user_id ON seat_type_versions (user_id);
CREATE INDEX IF NOT EXISTS ix_seat_type_versions_seat_type_id ON seat_type_versions (seat_type_id);

-- rooms
CREATE TABLE IF NOT EXISTS rooms (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	slug TEXT NOT NULL,
	name TEXT NOT NULL,
	team_id UUID REFERENCES teams (id),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_rooms_user_slug UNIQUE (user_id, slug)
);
CREATE INDEX IF NOT EXISTS ix_rooms_user_id ON rooms (user_id);
CREATE INDEX IF NOT EXISTS ix_rooms_team_id ON rooms (team_id);

-- seats
CREATE TABLE IF NOT EXISTS seats (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	room_id UUID NOT NULL REFERENCES rooms (id),
	seat_key TEXT NOT NULL,
	seat_type_id UUID NOT NULL REFERENCES seat_types (id),
	pinned_version TEXT,
	runtime TEXT NOT NULL,
	model TEXT NOT NULL,
	permission_policy TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_seats_room_seat_key UNIQUE (room_id, seat_key),
	CONSTRAINT ck_seats_permission_policy CHECK (permission_policy IN ('locked', 'standard', 'open', 'yolo', 'none'))
);
CREATE INDEX IF NOT EXISTS ix_seats_user_id ON seats (user_id);
CREATE INDEX IF NOT EXISTS ix_seats_room_id ON seats (room_id);
CREATE INDEX IF NOT EXISTS ix_seats_seat_type_id ON seats (seat_type_id);

-- overlays
CREATE TABLE IF NOT EXISTS overlays (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	scope TEXT NOT NULL,
	room_id UUID REFERENCES rooms (id),
	seat_id UUID REFERENCES seats (id),
	ops JSONB NOT NULL DEFAULT '[]'::jsonb,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT ck_overlays_scope CHECK (scope IN ('company', 'room', 'seat')),
	CONSTRAINT ck_overlays_scope_target CHECK (
		(scope = 'company' AND room_id IS NULL AND seat_id IS NULL)
		OR (scope = 'room' AND room_id IS NOT NULL AND seat_id IS NULL)
		OR (scope = 'seat' AND seat_id IS NOT NULL AND room_id IS NULL)
	)
);
CREATE INDEX IF NOT EXISTS ix_overlays_user_id ON overlays (user_id);
CREATE INDEX IF NOT EXISTS ix_overlays_room_id ON overlays (room_id);
CREATE INDEX IF NOT EXISTS ix_overlays_seat_id ON overlays (seat_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_overlays_target ON overlays (user_id, scope, COALESCE(room_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(seat_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- seat_links
CREATE TABLE IF NOT EXISTS seat_links (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	from_seat_id UUID NOT NULL REFERENCES seats (id),
	to_seat_id UUID NOT NULL REFERENCES seats (id),
	kind TEXT NOT NULL,
	allow BOOLEAN NOT NULL DEFAULT true,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_seat_links_from_to_kind UNIQUE (from_seat_id, to_seat_id, kind),
	CONSTRAINT ck_seat_links_kind CHECK (kind IN ('delegates_to', 'spawned_by', 'can_observe', 'collaborates_with', 'escalates_to')),
	CONSTRAINT ck_seat_links_distinct CHECK (from_seat_id <> to_seat_id)
);
CREATE INDEX IF NOT EXISTS ix_seat_links_user_id ON seat_links (user_id);
CREATE INDEX IF NOT EXISTS ix_seat_links_from_seat_id ON seat_links (from_seat_id);
CREATE INDEX IF NOT EXISTS ix_seat_links_to_seat_id ON seat_links (to_seat_id);

-- resolved_seats
CREATE TABLE IF NOT EXISTS resolved_seats (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	seat_id UUID NOT NULL REFERENCES seats (id),
	hash TEXT NOT NULL,
	runtime TEXT NOT NULL,
	files JSONB NOT NULL DEFAULT '[]'::jsonb,
	policy JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_resolved_seats_seat_hash UNIQUE (seat_id, hash)
);
CREATE INDEX IF NOT EXISTS ix_resolved_seats_user_id ON resolved_seats (user_id);
CREATE INDEX IF NOT EXISTS ix_resolved_seats_seat_id ON resolved_seats (seat_id);

-- seat_settings
CREATE TABLE IF NOT EXISTS seat_settings (
	user_id TEXT NOT NULL,
	follow_latest BOOLEAN NOT NULL DEFAULT false,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (user_id)
);

-- machines
CREATE TABLE IF NOT EXISTS machines (
	user_id TEXT NOT NULL,
	machine_id TEXT NOT NULL,
	last_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	agents JSONB NOT NULL DEFAULT '[]'::jsonb,
	PRIMARY KEY (user_id, machine_id)
);

-- seat_status
CREATE TABLE IF NOT EXISTS seat_status (
	user_id TEXT NOT NULL,
	machine_id TEXT NOT NULL,
	room TEXT NOT NULL,
	seat TEXT NOT NULL,
	state TEXT NOT NULL,
	runtime TEXT NOT NULL,
	running_hash TEXT NOT NULL DEFAULT '',
	detail TEXT NOT NULL DEFAULT '',
	redacted BOOLEAN NOT NULL DEFAULT false,
	reported_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (user_id, machine_id, room, seat)
);

-- machine_edges
CREATE TABLE IF NOT EXISTS machine_edges (
	user_id TEXT NOT NULL,
	machine_id TEXT NOT NULL,
	room TEXT NOT NULL,
	from_seat TEXT NOT NULL,
	to_seat TEXT NOT NULL,
	kind TEXT NOT NULL,
	CONSTRAINT ck_machine_edges_kind CHECK (kind IN ('delegates_to', 'spawned_by', 'can_observe', 'collaborates_with', 'escalates_to')),
	CONSTRAINT ck_machine_edges_distinct CHECK (from_seat <> to_seat),
	PRIMARY KEY (user_id, machine_id, room, from_seat, to_seat, kind)
);
CREATE INDEX IF NOT EXISTS ix_machine_edges_user_room ON machine_edges (user_id, room);

-- seat_feedback
CREATE TABLE IF NOT EXISTS seat_feedback (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	room TEXT NOT NULL,
	seat TEXT NOT NULL,
	session TEXT NOT NULL DEFAULT '',
	layer TEXT NOT NULL,
	text TEXT NOT NULL,
	machine_id TEXT NOT NULL DEFAULT '',
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	CONSTRAINT ck_seat_feedback_layer CHECK (layer IN ('runtime', 'openrig', 'cloud', 'seat-context', 'workspace', 'other')),
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_seat_feedback_user_id ON seat_feedback (user_id);

-- seat_messages
CREATE TABLE IF NOT EXISTS seat_messages (
	id UUID NOT NULL,
	user_id TEXT NOT NULL,
	room TEXT NOT NULL,
	seat TEXT NOT NULL,
	text TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	delivered_at TIMESTAMP WITH TIME ZONE,
	machine_id TEXT NOT NULL DEFAULT '',
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_seat_messages_seat ON seat_messages (user_id, room, seat, created_at, id);

-- email_tokens
CREATE TABLE IF NOT EXISTS email_tokens (
	token VARCHAR(255) NOT NULL,
	email VARCHAR(255) NOT NULL,
	token_type VARCHAR(50) NOT NULL,
	token_hash VARCHAR(255) NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	used_at TIMESTAMP WITHOUT TIME ZONE,
	is_used BOOLEAN,
	token_metadata TEXT,
	user_id VARCHAR(255),
	ip_address VARCHAR(45),
	user_agent VARCHAR(500),
	PRIMARY KEY (token)
);
CREATE INDEX IF NOT EXISTS ix_email_tokens_email ON email_tokens (email);

