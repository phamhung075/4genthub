// ORIGIN: generated from infrastructure/database/models.py (SQLAlchemy metadata) during the port
// from the Python backend. THAT GENERATOR IS GONE - no models.py and no generator script remain in
// this repository, and agenthub_main carries none either - so this FILE IS HAND-MAINTAINED now:
// edit it directly, keep each row struct and its Tables entry in step, and update the SQL to match
// the structs. The "DO NOT EDIT" marker outlived its generator by months and was corrected on
// 2026-10-10, when the agent_sessions seat pair (room_slug, seat_key, row 655227df) was added; a
// marker asserting a cause that no longer exists stops every future seat from doing ordinary work.
package database

import (
	"encoding/json"
	"time"
)

// GlobalSingletonUUID is the global context singleton UUID (used as a reference ID).
const GlobalSingletonUUID = "00000000-0000-0000-0000-000000000001"

// DefaultKind is how a column default is produced on insert (SQLAlchemy client-side default).
type DefaultKind int

const (
	DefaultNone DefaultKind = iota
	DefaultString
	DefaultInt
	DefaultFloat
	DefaultBool
	DefaultEnum // the enum member NAME is stored
	DefaultEmptyList
	DefaultEmptyDict
	DefaultUUIDv4      // str(uuid.uuid4())
	DefaultNowUTC      // datetime.now(UTC)
	DefaultNowUTCNaive // datetime.now(UTC).replace(tzinfo=None)
)

// ColumnDef describes one mapped column.
type ColumnDef struct {
	Name          string
	Attr          string // Python attribute name (differs from Name for model_metadata)
	GoField       string
	SQLType       string
	Nullable      bool
	PrimaryKey    bool
	Default       DefaultKind
	DefaultValue  string // literal source text for scalar defaults
	ServerDefault string // SQL text, "" when none
	ForeignKey    string // "table.column" or ""
	OnDelete      string
	EnumName      string // PostgreSQL enum type for Enum columns
}

// TableDef describes one mapped table.
type TableDef struct {
	Name    string
	Model   string
	Columns []ColumnDef
	// DDL is the CREATE TABLE statement followed by its CREATE INDEX statements.
	DDL []string
}

// ColumnNames lists the column names in declaration order.
func (t TableDef) ColumnNames() []string {
	names := make([]string, len(t.Columns))
	for i, c := range t.Columns {
		names[i] = c.Name
	}
	return names
}

// AgentSession is a row of agent_sessions.
type AgentSession struct {
	ID          string    `db:"id"`
	UserID      string    `db:"user_id"`
	ConnectorID string    `db:"connector_id"`
	SessionKey  string    `db:"session_key"`
	Name        string    `db:"name"`
	Project     *string   `db:"project"`
	Status      string    `db:"status"`
	LastSeq     int64     `db:"last_seq"`
	CreatedAt   time.Time `db:"created_at"`
	LastSeen    time.Time `db:"last_seen"`
	// The seat's identity, as the connector observed it: the room slug and the seat key, written
	// at ingest and null together when the connector could not name a seat. The pair is enforced by
	// ck_agent_sessions_seat_pair and by the ingest, never by this struct.
	RoomSlug *string `db:"room_slug"`
	SeatKey  *string `db:"seat_key"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *AgentSession) GetUserID() string { return r.UserID }

// APIToken is a row of api_tokens.
type APIToken struct {
	ID            string          `db:"id"`
	UserID        string          `db:"user_id"`
	Name          string          `db:"name"`
	TokenHash     string          `db:"token_hash"`
	Scopes        json.RawMessage `db:"scopes"`
	CreatedAt     time.Time       `db:"created_at"`
	ExpiresAt     time.Time       `db:"expires_at"`
	LastUsedAt    *time.Time      `db:"last_used_at"`
	UsageCount    int64           `db:"usage_count"`
	RateLimit     int64           `db:"rate_limit"`
	UsageStats    json.RawMessage `db:"usage_stats"`
	IsActive      bool            `db:"is_active"`
	TokenMetadata json.RawMessage `db:"token_metadata"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *APIToken) GetUserID() string { return r.UserID }

// ContextDelegation is a row of context_delegations.
type ContextDelegation struct {
	ID               string          `db:"id"`
	SourceLevel      string          `db:"source_level"`
	SourceID         string          `db:"source_id"`
	SourceType       string          `db:"source_type"`
	TargetLevel      string          `db:"target_level"`
	TargetID         string          `db:"target_id"`
	TargetType       string          `db:"target_type"`
	DelegatedData    json.RawMessage `db:"delegated_data"`
	DelegationData   json.RawMessage `db:"delegation_data"`
	DelegationReason string          `db:"delegation_reason"`
	TriggerType      string          `db:"trigger_type"`
	AutoDelegated    bool            `db:"auto_delegated"`
	ConfidenceScore  *float64        `db:"confidence_score"`
	Processed        bool            `db:"processed"`
	Status           string          `db:"status"`
	Approved         *bool           `db:"approved"`
	ProcessedBy      *string         `db:"processed_by"`
	RejectedReason   *string         `db:"rejected_reason"`
	ErrorMessage     *string         `db:"error_message"`
	UserID           string          `db:"user_id"`
	CreatedAt        time.Time       `db:"created_at"`
	ProcessedAt      *time.Time      `db:"processed_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *ContextDelegation) GetUserID() string { return r.UserID }

// ContextInheritanceCache is a row of context_inheritance_cache.
type ContextInheritanceCache struct {
	ID                 string          `db:"id"`
	ContextID          string          `db:"context_id"`
	ContextLevel       string          `db:"context_level"`
	ContextType        string          `db:"context_type"`
	ResolvedContext    json.RawMessage `db:"resolved_context"`
	ResolvedData       json.RawMessage `db:"resolved_data"`
	DependenciesHash   string          `db:"dependencies_hash"`
	ResolutionPath     string          `db:"resolution_path"`
	ParentChain        json.RawMessage `db:"parent_chain"`
	CreatedAt          time.Time       `db:"created_at"`
	ExpiresAt          time.Time       `db:"expires_at"`
	HitCount           int64           `db:"hit_count"`
	LastHit            time.Time       `db:"last_hit"`
	CacheSizeBytes     int64           `db:"cache_size_bytes"`
	Invalidated        bool            `db:"invalidated"`
	InvalidationReason *string         `db:"invalidation_reason"`
	UserID             string          `db:"user_id"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *ContextInheritanceCache) GetUserID() string { return r.UserID }

// GlobalContext is a row of global_contexts.
type GlobalContext struct {
	ID                     string          `db:"id"`
	OrganizationID         *string         `db:"organization_id"`
	OrganizationStandards  json.RawMessage `db:"organization_standards"`
	SecurityPolicies       json.RawMessage `db:"security_policies"`
	ComplianceRequirements json.RawMessage `db:"compliance_requirements"`
	SharedResources        json.RawMessage `db:"shared_resources"`
	ReusablePatterns       json.RawMessage `db:"reusable_patterns"`
	GlobalPreferences      json.RawMessage `db:"global_preferences"`
	DelegationRules        json.RawMessage `db:"delegation_rules"`
	NestedStructure        json.RawMessage `db:"nested_structure"`
	UnifiedContextData     json.RawMessage `db:"unified_context_data"`
	UserID                 string          `db:"user_id"`
	CreatedAt              time.Time       `db:"created_at"`
	UpdatedAt              time.Time       `db:"updated_at"`
	Version                int64           `db:"version"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *GlobalContext) GetUserID() string { return r.UserID }

// Label is a row of labels.
type Label struct {
	ID          string    `db:"id"`
	Name        string    `db:"name"`
	Color       string    `db:"color"`
	Description string    `db:"description"`
	UserID      string    `db:"user_id"`
	CreatedAt   time.Time `db:"created_at"`
	UpdatedAt   time.Time `db:"updated_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *Label) GetUserID() string { return r.UserID }

// MissedNotification is a row of missed_notifications.
type MissedNotification struct {
	ID               string          `db:"id"`
	UserID           string          `db:"user_id"`
	Message          json.RawMessage `db:"message"`
	CreatedAt        time.Time       `db:"created_at"`
	Delivered        bool            `db:"delivered"`
	DeliveryAttempts int64           `db:"delivery_attempts"`
	LastAttemptAt    *time.Time      `db:"last_attempt_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *MissedNotification) GetUserID() string { return r.UserID }

// Project is a row of projects.
type Project struct {
	ID          string          `db:"id"`
	Name        string          `db:"name"`
	Description string          `db:"description"`
	CreatedAt   time.Time       `db:"created_at"`
	UpdatedAt   time.Time       `db:"updated_at"`
	UserID      string          `db:"user_id"`
	Status      string          `db:"status"`
	Metadata    json.RawMessage `db:"metadata"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *Project) GetUserID() string { return r.UserID }

func (r *Project) GetCreatedAt() *time.Time {
	if r.CreatedAt.IsZero() {
		return nil
	}
	return &r.CreatedAt
}
func (r *Project) SetCreatedAt(t *time.Time) {
	if t == nil {
		r.CreatedAt = time.Time{}
		return
	}
	r.CreatedAt = *t
}
func (r *Project) GetUpdatedAt() *time.Time {
	if r.UpdatedAt.IsZero() {
		return nil
	}
	return &r.UpdatedAt
}
func (r *Project) SetUpdatedAt(t *time.Time) {
	if t == nil {
		r.UpdatedAt = time.Time{}
		return
	}
	r.UpdatedAt = *t
}
func (r *Project) Touch() {}

// Template is a row of templates.
type Template struct {
	ID              string          `db:"id"`
	Name            string          `db:"name"`
	TemplateName    string          `db:"template_name"`
	TemplateContent string          `db:"template_content"`
	TemplateType    string          `db:"template_type"`
	Type            string          `db:"type"`
	Content         json.RawMessage `db:"content"`
	Category        string          `db:"category"`
	Tags            json.RawMessage `db:"tags"`
	UsageCount      int64           `db:"usage_count"`
	UserID          *string         `db:"user_id"`
	CreatedAt       time.Time       `db:"created_at"`
	UpdatedAt       time.Time       `db:"updated_at"`
	CreatedBy       string          `db:"created_by"`
	Metadata        json.RawMessage `db:"metadata"`
}

// AgentSessionEvent is a row of agent_session_events.
type AgentSessionEvent struct {
	ID        int64           `db:"id"`
	SessionID string          `db:"session_id"`
	UserID    string          `db:"user_id"`
	Seq       int64           `db:"seq"`
	Type      string          `db:"type"`
	Payload   json.RawMessage `db:"payload"`
	Ts        time.Time       `db:"ts"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *AgentSessionEvent) GetUserID() string { return r.UserID }

// ProjectContext is a row of project_contexts.
type ProjectContext struct {
	ID                      string          `db:"id"`
	ProjectID               *string         `db:"project_id"`
	ParentGlobalID          *string         `db:"parent_global_id"`
	Data                    json.RawMessage `db:"data"`
	ProjectInfo             json.RawMessage `db:"project_info"`
	TeamPreferences         json.RawMessage `db:"team_preferences"`
	TechnologyStack         json.RawMessage `db:"technology_stack"`
	ProjectWorkflow         json.RawMessage `db:"project_workflow"`
	LocalStandards          json.RawMessage `db:"local_standards"`
	ProjectSettings         json.RawMessage `db:"project_settings"`
	TechnicalSpecifications json.RawMessage `db:"technical_specifications"`
	GlobalOverrides         json.RawMessage `db:"global_overrides"`
	DelegationRules         json.RawMessage `db:"delegation_rules"`
	UserID                  string          `db:"user_id"`
	CreatedAt               *time.Time      `db:"created_at"`
	UpdatedAt               *time.Time      `db:"updated_at"`
	Version                 *int64          `db:"version"`
	InheritanceDisabled     *bool           `db:"inheritance_disabled"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *ProjectContext) GetUserID() string { return r.UserID }

// ProjectGitBranch is a row of project_git_branchs.
type ProjectGitBranch struct {
	ID                 string          `db:"id"`
	ProjectID          string          `db:"project_id"`
	Name               string          `db:"name"`
	Description        string          `db:"description"`
	CreatedAt          time.Time       `db:"created_at"`
	UpdatedAt          time.Time       `db:"updated_at"`
	AssignedAgentID    *string         `db:"assigned_agent_id"`
	AgentID            *string         `db:"agent_id"`
	Priority           string          `db:"priority"`
	Status             string          `db:"status"`
	Metadata           json.RawMessage `db:"metadata"`
	TaskCount          int64           `db:"task_count"`
	CompletedTaskCount int64           `db:"completed_task_count"`
	UserID             string          `db:"user_id"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *ProjectGitBranch) GetUserID() string { return r.UserID }

func (r *ProjectGitBranch) GetCreatedAt() *time.Time {
	if r.CreatedAt.IsZero() {
		return nil
	}
	return &r.CreatedAt
}
func (r *ProjectGitBranch) SetCreatedAt(t *time.Time) {
	if t == nil {
		r.CreatedAt = time.Time{}
		return
	}
	r.CreatedAt = *t
}
func (r *ProjectGitBranch) GetUpdatedAt() *time.Time {
	if r.UpdatedAt.IsZero() {
		return nil
	}
	return &r.UpdatedAt
}
func (r *ProjectGitBranch) SetUpdatedAt(t *time.Time) {
	if t == nil {
		r.UpdatedAt = time.Time{}
		return
	}
	r.UpdatedAt = *t
}
func (r *ProjectGitBranch) Touch() {}

// BranchContext is a row of branch_contexts.
type BranchContext struct {
	ID                  string          `db:"id"`
	BranchID            *string         `db:"branch_id"`
	ParentProjectID     *string         `db:"parent_project_id"`
	Data                json.RawMessage `db:"data"`
	BranchInfo          json.RawMessage `db:"branch_info"`
	BranchWorkflow      json.RawMessage `db:"branch_workflow"`
	FeatureFlags        json.RawMessage `db:"feature_flags"`
	DiscoveredPatterns  json.RawMessage `db:"discovered_patterns"`
	BranchDecisions     json.RawMessage `db:"branch_decisions"`
	ActivePatterns      json.RawMessage `db:"active_patterns"`
	LocalOverrides      json.RawMessage `db:"local_overrides"`
	DelegationRules     json.RawMessage `db:"delegation_rules"`
	InheritanceDisabled *bool           `db:"inheritance_disabled"`
	UserID              string          `db:"user_id"`
	CreatedAt           *time.Time      `db:"created_at"`
	UpdatedAt           *time.Time      `db:"updated_at"`
	Version             *int64          `db:"version"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *BranchContext) GetUserID() string { return r.UserID }

// Task is a row of tasks.
type Task struct {
	ID                   string          `db:"id"`
	Title                string          `db:"title"`
	Description          string          `db:"description"`
	GitBranchID          string          `db:"git_branch_id"`
	Status               string          `db:"status"`
	Priority             string          `db:"priority"`
	ProgressHistory      json.RawMessage `db:"progress_history"`
	ProgressCount        int64           `db:"progress_count"`
	EstimatedEffort      string          `db:"estimated_effort"`
	DueDate              *string         `db:"due_date"`
	CreatedAt            time.Time       `db:"created_at"`
	UpdatedAt            time.Time       `db:"updated_at"`
	CompletedAt          *time.Time      `db:"completed_at"`
	CompletionSummary    string          `db:"completion_summary"`
	TestingNotes         string          `db:"testing_notes"`
	ContextID            *string         `db:"context_id"`
	ProgressPercentage   int64           `db:"progress_percentage"`
	ProgressState        string          `db:"progress_state"`
	CompletedSubtasks    *int64          `db:"completed_subtasks"`
	SubtaskCount         *int64          `db:"subtask_count"`
	UserID               string          `db:"user_id"`
	AISystemPrompt       string          `db:"ai_system_prompt"`
	AIRequestPrompt      string          `db:"ai_request_prompt"`
	AIWorkContext        json.RawMessage `db:"ai_work_context"`
	AICompletionCriteria string          `db:"ai_completion_criteria"`
	AIExecutionHistory   json.RawMessage `db:"ai_execution_history"`
	AILastExecution      *time.Time      `db:"ai_last_execution"`
	AIModelPreferences   json.RawMessage `db:"ai_model_preferences"`
	AcceptanceCriteria   json.RawMessage `db:"acceptance_criteria"`
	Scope                json.RawMessage `db:"scope"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *Task) GetUserID() string { return r.UserID }

func (r *Task) GetCreatedAt() *time.Time {
	if r.CreatedAt.IsZero() {
		return nil
	}
	return &r.CreatedAt
}
func (r *Task) SetCreatedAt(t *time.Time) {
	if t == nil {
		r.CreatedAt = time.Time{}
		return
	}
	r.CreatedAt = *t
}
func (r *Task) GetUpdatedAt() *time.Time {
	if r.UpdatedAt.IsZero() {
		return nil
	}
	return &r.UpdatedAt
}
func (r *Task) SetUpdatedAt(t *time.Time) {
	if t == nil {
		r.UpdatedAt = time.Time{}
		return
	}
	r.UpdatedAt = *t
}
func (r *Task) Touch() {}

// Subtask is a row of subtasks.
type Subtask struct {
	ID                   string          `db:"id"`
	TaskID               string          `db:"task_id"`
	Title                string          `db:"title"`
	Description          string          `db:"description"`
	Status               string          `db:"status"`
	Priority             string          `db:"priority"`
	Assignees            json.RawMessage `db:"assignees"`
	EstimatedEffort      *string         `db:"estimated_effort"`
	ProgressPercentage   int64           `db:"progress_percentage"`
	ProgressHistory      json.RawMessage `db:"progress_history"`
	ProgressCount        int64           `db:"progress_count"`
	ProgressState        string          `db:"progress_state"`
	ProgressNotes        string          `db:"progress_notes"`
	Blockers             string          `db:"blockers"`
	CompletionSummary    string          `db:"completion_summary"`
	ImpactOnParent       string          `db:"impact_on_parent"`
	InsightsFound        json.RawMessage `db:"insights_found"`
	UserID               string          `db:"user_id"`
	CreatedAt            time.Time       `db:"created_at"`
	UpdatedAt            time.Time       `db:"updated_at"`
	CompletedAt          *time.Time      `db:"completed_at"`
	AISystemPrompt       string          `db:"ai_system_prompt"`
	AIRequestPrompt      string          `db:"ai_request_prompt"`
	AIWorkContext        json.RawMessage `db:"ai_work_context"`
	AICompletionCriteria string          `db:"ai_completion_criteria"`
	AIExecutionHistory   json.RawMessage `db:"ai_execution_history"`
	AILastExecution      *time.Time      `db:"ai_last_execution"`
	AIModelPreferences   json.RawMessage `db:"ai_model_preferences"`
	AcceptanceCriteria   json.RawMessage `db:"acceptance_criteria"`
	Scope                json.RawMessage `db:"scope"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *Subtask) GetUserID() string { return r.UserID }

func (r *Subtask) GetCreatedAt() *time.Time {
	if r.CreatedAt.IsZero() {
		return nil
	}
	return &r.CreatedAt
}
func (r *Subtask) SetCreatedAt(t *time.Time) {
	if t == nil {
		r.CreatedAt = time.Time{}
		return
	}
	r.CreatedAt = *t
}
func (r *Subtask) GetUpdatedAt() *time.Time {
	if r.UpdatedAt.IsZero() {
		return nil
	}
	return &r.UpdatedAt
}
func (r *Subtask) SetUpdatedAt(t *time.Time) {
	if t == nil {
		r.UpdatedAt = time.Time{}
		return
	}
	r.UpdatedAt = *t
}
func (r *Subtask) Touch() {}

// TaskAssignee is a row of task_assignees.
type TaskAssignee struct {
	ID         string    `db:"id"`
	TaskID     string    `db:"task_id"`
	AssigneeID string    `db:"assignee_id"`
	AgentID    *string   `db:"agent_id"`
	Role       string    `db:"role"`
	UserID     string    `db:"user_id"`
	AssignedAt time.Time `db:"assigned_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *TaskAssignee) GetUserID() string { return r.UserID }

// TaskContext is a row of task_contexts.
type TaskContext struct {
	ID                    string          `db:"id"`
	TaskID                *string         `db:"task_id"`
	ParentBranchID        *string         `db:"parent_branch_id"`
	ParentBranchContextID *string         `db:"parent_branch_context_id"`
	Data                  json.RawMessage `db:"data"`
	TaskData              json.RawMessage `db:"task_data"`
	ExecutionContext      json.RawMessage `db:"execution_context"`
	DiscoveredPatterns    json.RawMessage `db:"discovered_patterns"`
	ImplementationNotes   json.RawMessage `db:"implementation_notes"`
	TestResults           json.RawMessage `db:"test_results"`
	Blockers              json.RawMessage `db:"blockers"`
	LocalDecisions        json.RawMessage `db:"local_decisions"`
	DelegationQueue       json.RawMessage `db:"delegation_queue"`
	LocalOverrides        json.RawMessage `db:"local_overrides"`
	DelegationTriggers    json.RawMessage `db:"delegation_triggers"`
	InheritanceDisabled   *bool           `db:"inheritance_disabled"`
	ForceLocalOnly        *bool           `db:"force_local_only"`
	UserID                string          `db:"user_id"`
	CreatedAt             *time.Time      `db:"created_at"`
	UpdatedAt             *time.Time      `db:"updated_at"`
	Version               *int64          `db:"version"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *TaskContext) GetUserID() string { return r.UserID }

// TaskDependency is a row of task_dependencies.
type TaskDependency struct {
	ID              int64     `db:"id"`
	TaskID          string    `db:"task_id"`
	DependsOnTaskID string    `db:"depends_on_task_id"`
	DependencyType  string    `db:"dependency_type"`
	UserID          string    `db:"user_id"`
	CreatedAt       time.Time `db:"created_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *TaskDependency) GetUserID() string { return r.UserID }

// TaskLabel is a row of task_labels.
type TaskLabel struct {
	TaskID    string    `db:"task_id"`
	LabelID   string    `db:"label_id"`
	UserID    string    `db:"user_id"`
	AppliedAt time.Time `db:"applied_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *TaskLabel) GetUserID() string { return r.UserID }

// Tables lists every mapped table in dependency (create) order.
var Tables = []TableDef{
	{Name: "agent_sessions", Model: "AgentSession", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "VARCHAR(36)", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR(64)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "connector_id", Attr: "connector_id", GoField: "ConnectorID", SQLType: "VARCHAR(64)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "session_key", Attr: "session_key", GoField: "SessionKey", SQLType: "VARCHAR(255)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR(255)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "project", Attr: "project", GoField: "Project", SQLType: "VARCHAR(255)", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR(20)", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"active\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "last_seq", Attr: "last_seq", GoField: "LastSeq", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNowUTCNaive, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "last_seen", Attr: "last_seen", GoField: "LastSeen", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNowUTCNaive, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "room_slug", Attr: "room_slug", GoField: "RoomSlug", SQLType: "VARCHAR(255)", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "seat_key", Attr: "seat_key", GoField: "SeatKey", SQLType: "VARCHAR(255)", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE agent_sessions (\n\tid VARCHAR(36) NOT NULL,\n\tuser_id VARCHAR(64) NOT NULL,\n\tconnector_id VARCHAR(64) NOT NULL,\n\tsession_key VARCHAR(255) NOT NULL,\n\tname VARCHAR(255) NOT NULL,\n\tproject VARCHAR(255),\n\tstatus VARCHAR(20) NOT NULL,\n\tlast_seq INTEGER NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tlast_seen TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\troom_slug VARCHAR(255),\n\tseat_key VARCHAR(255),\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_agent_sessions_key UNIQUE (user_id, connector_id, session_key),\n\tCONSTRAINT ck_agent_sessions_seat_pair CHECK ((room_slug IS NULL) = (seat_key IS NULL))\n)",
		"CREATE INDEX ix_agent_sessions_user_id ON agent_sessions (user_id)",
	}},
	{Name: "api_tokens", Model: "APIToken", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "token_hash", Attr: "token_hash", GoField: "TokenHash", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "scopes", Attr: "scopes", GoField: "Scopes", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNowUTC, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "expires_at", Attr: "expires_at", GoField: "ExpiresAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "last_used_at", Attr: "last_used_at", GoField: "LastUsedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "usage_count", Attr: "usage_count", GoField: "UsageCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "rate_limit", Attr: "rate_limit", GoField: "RateLimit", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "1000", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "usage_stats", Attr: "usage_stats", GoField: "UsageStats", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "is_active", Attr: "is_active", GoField: "IsActive", SQLType: "BOOLEAN", Nullable: false, PrimaryKey: false, Default: DefaultBool, DefaultValue: "true", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "token_metadata", Attr: "token_metadata", GoField: "TokenMetadata", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE api_tokens (\n\tid VARCHAR NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tname VARCHAR NOT NULL,\n\ttoken_hash VARCHAR NOT NULL,\n\tscopes JSON NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\texpires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tlast_used_at TIMESTAMP WITHOUT TIME ZONE,\n\tusage_count INTEGER NOT NULL,\n\trate_limit INTEGER NOT NULL,\n\tusage_stats JSON NOT NULL,\n\tis_active BOOLEAN NOT NULL,\n\ttoken_metadata JSON NOT NULL,\n\tPRIMARY KEY (id)\n)",
	}},
	{Name: "context_delegations", Model: "ContextDelegation", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "source_level", Attr: "source_level", GoField: "SourceLevel", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "source_id", Attr: "source_id", GoField: "SourceID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "source_type", Attr: "source_type", GoField: "SourceType", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"context\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "target_level", Attr: "target_level", GoField: "TargetLevel", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "target_id", Attr: "target_id", GoField: "TargetID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "target_type", Attr: "target_type", GoField: "TargetType", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"context\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegated_data", Attr: "delegated_data", GoField: "DelegatedData", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_data", Attr: "delegation_data", GoField: "DelegationData", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_reason", Attr: "delegation_reason", GoField: "DelegationReason", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "trigger_type", Attr: "trigger_type", GoField: "TriggerType", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "auto_delegated", Attr: "auto_delegated", GoField: "AutoDelegated", SQLType: "BOOLEAN", Nullable: false, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "confidence_score", Attr: "confidence_score", GoField: "ConfidenceScore", SQLType: "FLOAT", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "processed", Attr: "processed", GoField: "Processed", SQLType: "BOOLEAN", Nullable: false, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"pending\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "approved", Attr: "approved", GoField: "Approved", SQLType: "BOOLEAN", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "processed_by", Attr: "processed_by", GoField: "ProcessedBy", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "rejected_reason", Attr: "rejected_reason", GoField: "RejectedReason", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "error_message", Attr: "error_message", GoField: "ErrorMessage", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "processed_at", Attr: "processed_at", GoField: "ProcessedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE context_delegations (\n\tid UUID NOT NULL,\n\tsource_level VARCHAR NOT NULL,\n\tsource_id UUID NOT NULL,\n\tsource_type VARCHAR NOT NULL,\n\ttarget_level VARCHAR NOT NULL,\n\ttarget_id UUID NOT NULL,\n\ttarget_type VARCHAR NOT NULL,\n\tdelegated_data JSON NOT NULL,\n\tdelegation_data JSON NOT NULL,\n\tdelegation_reason VARCHAR NOT NULL,\n\ttrigger_type VARCHAR NOT NULL,\n\tauto_delegated BOOLEAN NOT NULL,\n\tconfidence_score FLOAT,\n\tprocessed BOOLEAN NOT NULL,\n\tstatus VARCHAR NOT NULL,\n\tapproved BOOLEAN,\n\tprocessed_by VARCHAR,\n\trejected_reason VARCHAR,\n\terror_message VARCHAR,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tprocessed_at TIMESTAMP WITHOUT TIME ZONE,\n\tPRIMARY KEY (id),\n\tCONSTRAINT chk_source_level CHECK (source_level IN ('task', 'branch', 'project', 'global')),\n\tCONSTRAINT chk_target_level CHECK (target_level IN ('task', 'branch', 'project', 'global')),\n\tCONSTRAINT chk_trigger_type CHECK (trigger_type IN ('manual', 'auto_pattern', 'auto_threshold'))\n)",
		"CREATE INDEX idx_delegation_processed ON context_delegations (processed)",
		"CREATE INDEX idx_delegation_source ON context_delegations (source_level, source_id)",
		"CREATE INDEX idx_delegation_target ON context_delegations (target_level, target_id)",
	}},
	{Name: "context_inheritance_cache", Model: "ContextInheritanceCache", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "context_id", Attr: "context_id", GoField: "ContextID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "context_level", Attr: "context_level", GoField: "ContextLevel", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "context_type", Attr: "context_type", GoField: "ContextType", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"hierarchical\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "resolved_context", Attr: "resolved_context", GoField: "ResolvedContext", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "resolved_data", Attr: "resolved_data", GoField: "ResolvedData", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "dependencies_hash", Attr: "dependencies_hash", GoField: "DependenciesHash", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "resolution_path", Attr: "resolution_path", GoField: "ResolutionPath", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "parent_chain", Attr: "parent_chain", GoField: "ParentChain", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "expires_at", Attr: "expires_at", GoField: "ExpiresAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "hit_count", Attr: "hit_count", GoField: "HitCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "last_hit", Attr: "last_hit", GoField: "LastHit", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "cache_size_bytes", Attr: "cache_size_bytes", GoField: "CacheSizeBytes", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "invalidated", Attr: "invalidated", GoField: "Invalidated", SQLType: "BOOLEAN", Nullable: false, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "invalidation_reason", Attr: "invalidation_reason", GoField: "InvalidationReason", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE context_inheritance_cache (\n\tid UUID NOT NULL,\n\tcontext_id UUID NOT NULL,\n\tcontext_level VARCHAR NOT NULL,\n\tcontext_type VARCHAR NOT NULL,\n\tresolved_context JSON NOT NULL,\n\tresolved_data JSON NOT NULL,\n\tdependencies_hash VARCHAR NOT NULL,\n\tresolution_path VARCHAR NOT NULL,\n\tparent_chain JSON NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\texpires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\thit_count INTEGER NOT NULL,\n\tlast_hit TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tcache_size_bytes INTEGER NOT NULL,\n\tinvalidated BOOLEAN NOT NULL,\n\tinvalidation_reason VARCHAR,\n\tuser_id VARCHAR NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT chk_cache_context_level CHECK (context_level IN ('task', 'branch', 'project', 'global')),\n\tCONSTRAINT uq_cache_context UNIQUE (context_id, context_level)\n)",
		"CREATE INDEX idx_cache_expires ON context_inheritance_cache (expires_at)",
		"CREATE INDEX idx_cache_invalidated ON context_inheritance_cache (invalidated)",
		"CREATE INDEX idx_cache_level ON context_inheritance_cache (context_level)",
	}},
	{Name: "global_contexts", Model: "GlobalContext", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "organization_id", Attr: "organization_id", GoField: "OrganizationID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "organization_standards", Attr: "organization_standards", GoField: "OrganizationStandards", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "security_policies", Attr: "security_policies", GoField: "SecurityPolicies", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "compliance_requirements", Attr: "compliance_requirements", GoField: "ComplianceRequirements", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "shared_resources", Attr: "shared_resources", GoField: "SharedResources", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "reusable_patterns", Attr: "reusable_patterns", GoField: "ReusablePatterns", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "global_preferences", Attr: "global_preferences", GoField: "GlobalPreferences", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_rules", Attr: "delegation_rules", GoField: "DelegationRules", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "nested_structure", Attr: "nested_structure", GoField: "NestedStructure", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "unified_context_data", Attr: "unified_context_data", GoField: "UnifiedContextData", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "1", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE global_contexts (\n\tid UUID NOT NULL,\n\torganization_id UUID,\n\torganization_standards JSON NOT NULL,\n\tsecurity_policies JSON NOT NULL,\n\tcompliance_requirements JSON NOT NULL,\n\tshared_resources JSON NOT NULL,\n\treusable_patterns JSON NOT NULL,\n\tglobal_preferences JSON NOT NULL,\n\tdelegation_rules JSON NOT NULL,\n\tnested_structure JSON NOT NULL,\n\tunified_context_data JSON,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tversion INTEGER NOT NULL,\n\tPRIMARY KEY (id)\n)",
	}},
	{Name: "labels", Model: "Label", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "color", Attr: "color", GoField: "Color", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"#0066cc\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE labels (\n\tid VARCHAR NOT NULL,\n\tname VARCHAR NOT NULL,\n\tcolor VARCHAR NOT NULL,\n\tdescription TEXT NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tPRIMARY KEY (id),\n\tUNIQUE (name)\n)",
	}},
	{Name: "missed_notifications", Model: "MissedNotification", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "message", Attr: "message", GoField: "Message", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delivered", Attr: "delivered", GoField: "Delivered", SQLType: "BOOLEAN", Nullable: false, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delivery_attempts", Attr: "delivery_attempts", GoField: "DeliveryAttempts", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "last_attempt_at", Attr: "last_attempt_at", GoField: "LastAttemptAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE missed_notifications (\n\tid VARCHAR NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tmessage JSON NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tdelivered BOOLEAN NOT NULL,\n\tdelivery_attempts INTEGER NOT NULL,\n\tlast_attempt_at TIMESTAMP WITHOUT TIME ZONE,\n\tPRIMARY KEY (id)\n)",
		"CREATE INDEX idx_missed_notifications_created_at ON missed_notifications (created_at)",
		"CREATE INDEX idx_missed_notifications_user_delivered ON missed_notifications (user_id, delivered)",
		"CREATE INDEX ix_missed_notifications_delivered ON missed_notifications (delivered)",
		"CREATE INDEX ix_missed_notifications_user_id ON missed_notifications (user_id)",
	}},
	{Name: "projects", Model: "Project", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"active\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "metadata", Attr: "model_metadata", GoField: "Metadata", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE projects (\n\tid UUID NOT NULL,\n\tname VARCHAR NOT NULL,\n\tdescription TEXT NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tstatus VARCHAR NOT NULL,\n\tmetadata JSON NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_project_user UNIQUE (id, user_id)\n)",
	}},
	{Name: "templates", Model: "Template", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "template_name", Attr: "template_name", GoField: "TemplateName", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "template_content", Attr: "template_content", GoField: "TemplateContent", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "template_type", Attr: "template_type", GoField: "TemplateType", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"general\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "type", Attr: "type", GoField: "Type", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "content", Attr: "content", GoField: "Content", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "category", Attr: "category", GoField: "Category", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"general\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "tags", Attr: "tags", GoField: "Tags", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "usage_count", Attr: "usage_count", GoField: "UsageCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_by", Attr: "created_by", GoField: "CreatedBy", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "metadata", Attr: "metadata_", GoField: "Metadata", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE templates (\n\tid UUID NOT NULL,\n\tname VARCHAR NOT NULL,\n\ttemplate_name VARCHAR NOT NULL,\n\ttemplate_content TEXT NOT NULL,\n\ttemplate_type VARCHAR NOT NULL,\n\ttype VARCHAR NOT NULL,\n\tcontent JSON NOT NULL,\n\tcategory VARCHAR NOT NULL,\n\ttags JSON NOT NULL,\n\tusage_count INTEGER NOT NULL,\n\tuser_id VARCHAR,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tcreated_by VARCHAR NOT NULL,\n\tmetadata JSON NOT NULL,\n\tPRIMARY KEY (id)\n)",
		"CREATE INDEX idx_template_category ON templates (category)",
		"CREATE INDEX idx_template_type ON templates (type)",
	}},
	{Name: "agent_session_events", Model: "AgentSessionEvent", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "INTEGER", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "session_id", Attr: "session_id", GoField: "SessionID", SQLType: "VARCHAR(36)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "agent_sessions.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR(64)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "seq", Attr: "seq", GoField: "Seq", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "type", Attr: "type", GoField: "Type", SQLType: "VARCHAR(32)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "payload", Attr: "payload", GoField: "Payload", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ts", Attr: "ts", GoField: "Ts", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNowUTCNaive, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE agent_session_events (\n\tid SERIAL NOT NULL,\n\tsession_id VARCHAR(36) NOT NULL,\n\tuser_id VARCHAR(64) NOT NULL,\n\tseq INTEGER NOT NULL,\n\ttype VARCHAR(32) NOT NULL,\n\tpayload JSON NOT NULL,\n\tts TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_agent_session_events_seq UNIQUE (session_id, seq),\n\tFOREIGN KEY(session_id) REFERENCES agent_sessions (id) ON DELETE CASCADE\n)",
		"CREATE INDEX idx_agent_session_events_user_session ON agent_session_events (user_id, session_id, seq)",
	}},
	{Name: "project_contexts", Model: "ProjectContext", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "project_id", Attr: "project_id", GoField: "ProjectID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "parent_global_id", Attr: "parent_global_id", GoField: "ParentGlobalID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "global_contexts.id", OnDelete: "", EnumName: ""},
		{Name: "data", Attr: "data", GoField: "Data", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "project_info", Attr: "project_info", GoField: "ProjectInfo", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "team_preferences", Attr: "team_preferences", GoField: "TeamPreferences", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "technology_stack", Attr: "technology_stack", GoField: "TechnologyStack", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "project_workflow", Attr: "project_workflow", GoField: "ProjectWorkflow", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "local_standards", Attr: "local_standards", GoField: "LocalStandards", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "project_settings", Attr: "project_settings", GoField: "ProjectSettings", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "technical_specifications", Attr: "technical_specifications", GoField: "TechnicalSpecifications", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "global_overrides", Attr: "global_overrides", GoField: "GlobalOverrides", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_rules", Attr: "delegation_rules", GoField: "DelegationRules", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "INTEGER", Nullable: true, PrimaryKey: false, Default: DefaultInt, DefaultValue: "1", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "inheritance_disabled", Attr: "inheritance_disabled", GoField: "InheritanceDisabled", SQLType: "BOOLEAN", Nullable: true, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE project_contexts (\n\tid UUID NOT NULL,\n\tproject_id UUID,\n\tparent_global_id UUID,\n\tdata JSON,\n\tproject_info JSON,\n\tteam_preferences JSON,\n\ttechnology_stack JSON,\n\tproject_workflow JSON,\n\tlocal_standards JSON,\n\tproject_settings JSON,\n\ttechnical_specifications JSON,\n\tglobal_overrides JSON,\n\tdelegation_rules JSON,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE,\n\tversion INTEGER,\n\tinheritance_disabled BOOLEAN,\n\tPRIMARY KEY (id),\n\tFOREIGN KEY(parent_global_id) REFERENCES global_contexts (id)\n)",
	}},
	{Name: "project_git_branchs", Model: "ProjectGitBranch", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "project_id", Attr: "project_id", GoField: "ProjectID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "projects.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "assigned_agent_id", Attr: "assigned_agent_id", GoField: "AssignedAgentID", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "agent_id", Attr: "agent_id", GoField: "AgentID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "priority", Attr: "priority", GoField: "Priority", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"medium\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"todo\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "metadata", Attr: "model_metadata", GoField: "Metadata", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_count", Attr: "task_count", GoField: "TaskCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "completed_task_count", Attr: "completed_task_count", GoField: "CompletedTaskCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE project_git_branchs (\n\tid UUID NOT NULL,\n\tproject_id UUID NOT NULL,\n\tname VARCHAR NOT NULL,\n\tdescription TEXT NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tassigned_agent_id VARCHAR,\n\tagent_id UUID,\n\tpriority VARCHAR NOT NULL,\n\tstatus VARCHAR NOT NULL,\n\tmetadata JSON NOT NULL,\n\ttask_count INTEGER NOT NULL,\n\tcompleted_task_count INTEGER NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_branch_project UNIQUE (id, project_id),\n\tFOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE\n)",
	}},
	{Name: "branch_contexts", Model: "BranchContext", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "branch_id", Attr: "branch_id", GoField: "BranchID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "project_git_branchs.id", OnDelete: "", EnumName: ""},
		{Name: "parent_project_id", Attr: "parent_project_id", GoField: "ParentProjectID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "project_contexts.id", OnDelete: "", EnumName: ""},
		{Name: "data", Attr: "data", GoField: "Data", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "branch_info", Attr: "branch_info", GoField: "BranchInfo", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "branch_workflow", Attr: "branch_workflow", GoField: "BranchWorkflow", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "feature_flags", Attr: "feature_flags", GoField: "FeatureFlags", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "discovered_patterns", Attr: "discovered_patterns", GoField: "DiscoveredPatterns", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "branch_decisions", Attr: "branch_decisions", GoField: "BranchDecisions", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "active_patterns", Attr: "active_patterns", GoField: "ActivePatterns", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "local_overrides", Attr: "local_overrides", GoField: "LocalOverrides", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_rules", Attr: "delegation_rules", GoField: "DelegationRules", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "inheritance_disabled", Attr: "inheritance_disabled", GoField: "InheritanceDisabled", SQLType: "BOOLEAN", Nullable: true, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "INTEGER", Nullable: true, PrimaryKey: false, Default: DefaultInt, DefaultValue: "1", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE branch_contexts (\n\tid UUID NOT NULL,\n\tbranch_id UUID,\n\tparent_project_id UUID,\n\tdata JSON,\n\tbranch_info JSON,\n\tbranch_workflow JSON,\n\tfeature_flags JSON,\n\tdiscovered_patterns JSON,\n\tbranch_decisions JSON,\n\tactive_patterns JSON,\n\tlocal_overrides JSON,\n\tdelegation_rules JSON,\n\tinheritance_disabled BOOLEAN,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE,\n\tversion INTEGER,\n\tPRIMARY KEY (id),\n\tFOREIGN KEY(branch_id) REFERENCES project_git_branchs (id),\n\tFOREIGN KEY(parent_project_id) REFERENCES project_contexts (id)\n)",
	}},
	{Name: "tasks", Model: "Task", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "title", Attr: "title", GoField: "Title", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "git_branch_id", Attr: "git_branch_id", GoField: "GitBranchID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "project_git_branchs.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"todo\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "priority", Attr: "priority", GoField: "Priority", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"medium\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_history", Attr: "progress_history", GoField: "ProgressHistory", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_count", Attr: "progress_count", GoField: "ProgressCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "estimated_effort", Attr: "estimated_effort", GoField: "EstimatedEffort", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"2 hours\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "due_date", Attr: "due_date", GoField: "DueDate", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "completed_at", Attr: "completed_at", GoField: "CompletedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "completion_summary", Attr: "completion_summary", GoField: "CompletionSummary", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "testing_notes", Attr: "testing_notes", GoField: "TestingNotes", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "context_id", Attr: "context_id", GoField: "ContextID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_percentage", Attr: "progress_percentage", GoField: "ProgressPercentage", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_state", Attr: "progress_state", GoField: "ProgressState", SQLType: "progressstate", Nullable: false, PrimaryKey: false, Default: DefaultEnum, DefaultValue: "\"INITIAL\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: "progressstate"},
		{Name: "completed_subtasks", Attr: "completed_subtasks", GoField: "CompletedSubtasks", SQLType: "INTEGER", Nullable: true, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "subtask_count", Attr: "subtask_count", GoField: "SubtaskCount", SQLType: "INTEGER", Nullable: true, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_system_prompt", Attr: "ai_system_prompt", GoField: "AISystemPrompt", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_request_prompt", Attr: "ai_request_prompt", GoField: "AIRequestPrompt", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_work_context", Attr: "ai_work_context", GoField: "AIWorkContext", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "{}", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_completion_criteria", Attr: "ai_completion_criteria", GoField: "AICompletionCriteria", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_execution_history", Attr: "ai_execution_history", GoField: "AIExecutionHistory", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "[]", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_last_execution", Attr: "ai_last_execution", GoField: "AILastExecution", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_model_preferences", Attr: "ai_model_preferences", GoField: "AIModelPreferences", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "{}", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "acceptance_criteria", Attr: "acceptance_criteria", GoField: "AcceptanceCriteria", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "scope", Attr: "scope", GoField: "Scope", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE tasks (\n\tid UUID NOT NULL,\n\ttitle VARCHAR NOT NULL,\n\tdescription TEXT NOT NULL,\n\tgit_branch_id UUID NOT NULL,\n\tstatus VARCHAR NOT NULL,\n\tpriority VARCHAR NOT NULL,\n\tprogress_history JSON NOT NULL,\n\tprogress_count INTEGER NOT NULL,\n\testimated_effort VARCHAR NOT NULL,\n\tdue_date VARCHAR,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tcompleted_at TIMESTAMP WITHOUT TIME ZONE,\n\tcompletion_summary TEXT NOT NULL,\n\ttesting_notes TEXT NOT NULL,\n\tcontext_id UUID,\n\tprogress_percentage INTEGER NOT NULL,\n\tprogress_state progressstate NOT NULL,\n\tcompleted_subtasks INTEGER,\n\tsubtask_count INTEGER,\n\tuser_id VARCHAR NOT NULL,\n\tai_system_prompt TEXT DEFAULT '' NOT NULL,\n\tai_request_prompt TEXT DEFAULT '' NOT NULL,\n\tai_work_context JSON DEFAULT '{}' NOT NULL,\n\tai_completion_criteria TEXT DEFAULT '' NOT NULL,\n\tai_execution_history JSON DEFAULT '[]' NOT NULL,\n\tai_last_execution TIMESTAMP WITHOUT TIME ZONE,\n\tai_model_preferences JSON DEFAULT '{}' NOT NULL,\n\tacceptance_criteria JSON DEFAULT '[]' NOT NULL,\n\tscope JSON DEFAULT '[]' NOT NULL,\n\tPRIMARY KEY (id),\n\tFOREIGN KEY(git_branch_id) REFERENCES project_git_branchs (id) ON DELETE CASCADE\n)",
		"CREATE INDEX idx_task_branch ON tasks (git_branch_id)",
		"CREATE INDEX idx_task_created ON tasks (created_at)",
		"CREATE INDEX idx_task_priority ON tasks (priority)",
		"CREATE INDEX idx_task_status ON tasks (status)",
	}},
	{Name: "subtasks", Model: "Subtask", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "title", Attr: "title", GoField: "Title", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"todo\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "priority", Attr: "priority", GoField: "Priority", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"medium\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "assignees", Attr: "assignees", GoField: "Assignees", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "estimated_effort", Attr: "estimated_effort", GoField: "EstimatedEffort", SQLType: "VARCHAR", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_percentage", Attr: "progress_percentage", GoField: "ProgressPercentage", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_history", Attr: "progress_history", GoField: "ProgressHistory", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_count", Attr: "progress_count", GoField: "ProgressCount", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultInt, DefaultValue: "0", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "progress_state", Attr: "progress_state", GoField: "ProgressState", SQLType: "progressstate", Nullable: false, PrimaryKey: false, Default: DefaultEnum, DefaultValue: "\"INITIAL\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: "progressstate"},
		{Name: "progress_notes", Attr: "progress_notes", GoField: "ProgressNotes", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "blockers", Attr: "blockers", GoField: "Blockers", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "completion_summary", Attr: "completion_summary", GoField: "CompletionSummary", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "impact_on_parent", Attr: "impact_on_parent", GoField: "ImpactOnParent", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "insights_found", Attr: "insights_found", GoField: "InsightsFound", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "completed_at", Attr: "completed_at", GoField: "CompletedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_system_prompt", Attr: "ai_system_prompt", GoField: "AISystemPrompt", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_request_prompt", Attr: "ai_request_prompt", GoField: "AIRequestPrompt", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_work_context", Attr: "ai_work_context", GoField: "AIWorkContext", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "{}", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_completion_criteria", Attr: "ai_completion_criteria", GoField: "AICompletionCriteria", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_execution_history", Attr: "ai_execution_history", GoField: "AIExecutionHistory", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "[]", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_last_execution", Attr: "ai_last_execution", GoField: "AILastExecution", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "ai_model_preferences", Attr: "ai_model_preferences", GoField: "AIModelPreferences", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "{}", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "acceptance_criteria", Attr: "acceptance_criteria", GoField: "AcceptanceCriteria", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "scope", Attr: "scope", GoField: "Scope", SQLType: "JSON", Nullable: false, PrimaryKey: false, Default: DefaultEmptyList, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE subtasks (\n\tid UUID NOT NULL,\n\ttask_id UUID NOT NULL,\n\ttitle VARCHAR NOT NULL,\n\tdescription TEXT NOT NULL,\n\tstatus VARCHAR NOT NULL,\n\tpriority VARCHAR NOT NULL,\n\tassignees JSON NOT NULL,\n\testimated_effort VARCHAR,\n\tprogress_percentage INTEGER NOT NULL,\n\tprogress_history JSON NOT NULL,\n\tprogress_count INTEGER NOT NULL,\n\tprogress_state progressstate NOT NULL,\n\tprogress_notes TEXT NOT NULL,\n\tblockers TEXT NOT NULL,\n\tcompletion_summary TEXT NOT NULL,\n\timpact_on_parent TEXT NOT NULL,\n\tinsights_found JSON NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tcompleted_at TIMESTAMP WITHOUT TIME ZONE,\n\tai_system_prompt TEXT DEFAULT '' NOT NULL,\n\tai_request_prompt TEXT DEFAULT '' NOT NULL,\n\tai_work_context JSON DEFAULT '{}' NOT NULL,\n\tai_completion_criteria TEXT DEFAULT '' NOT NULL,\n\tai_execution_history JSON DEFAULT '[]' NOT NULL,\n\tai_last_execution TIMESTAMP WITHOUT TIME ZONE,\n\tai_model_preferences JSON DEFAULT '{}' NOT NULL,\n\tacceptance_criteria JSON DEFAULT '[]' NOT NULL,\n\tscope JSON DEFAULT '[]' NOT NULL,\n\tPRIMARY KEY (id),\n\tFOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE\n)",
		"CREATE INDEX idx_subtask_status ON subtasks (status)",
		"CREATE INDEX idx_subtask_task ON subtasks (task_id)",
	}},
	{Name: "task_assignees", Model: "TaskAssignee", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "assignee_id", Attr: "assignee_id", GoField: "AssigneeID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "agent_id", Attr: "agent_id", GoField: "AgentID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "role", Attr: "role", GoField: "Role", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"contributor\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "assigned_at", Attr: "assigned_at", GoField: "AssignedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE task_assignees (\n\tid UUID NOT NULL,\n\ttask_id UUID NOT NULL,\n\tassignee_id VARCHAR NOT NULL,\n\tagent_id UUID,\n\trole VARCHAR NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tassigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_task_assignee UNIQUE (task_id, assignee_id),\n\tFOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE\n)",
		"CREATE INDEX idx_assignee_id ON task_assignees (assignee_id)",
		"CREATE INDEX idx_assignee_task ON task_assignees (task_id)",
	}},
	{Name: "task_contexts", Model: "TaskContext", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "parent_branch_id", Attr: "parent_branch_id", GoField: "ParentBranchID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "project_git_branchs.id", OnDelete: "", EnumName: ""},
		{Name: "parent_branch_context_id", Attr: "parent_branch_context_id", GoField: "ParentBranchContextID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "branch_contexts.id", OnDelete: "", EnumName: ""},
		{Name: "data", Attr: "data", GoField: "Data", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_data", Attr: "task_data", GoField: "TaskData", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "execution_context", Attr: "execution_context", GoField: "ExecutionContext", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "discovered_patterns", Attr: "discovered_patterns", GoField: "DiscoveredPatterns", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "implementation_notes", Attr: "implementation_notes", GoField: "ImplementationNotes", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "test_results", Attr: "test_results", GoField: "TestResults", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "blockers", Attr: "blockers", GoField: "Blockers", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "local_decisions", Attr: "local_decisions", GoField: "LocalDecisions", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_queue", Attr: "delegation_queue", GoField: "DelegationQueue", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "local_overrides", Attr: "local_overrides", GoField: "LocalOverrides", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "delegation_triggers", Attr: "delegation_triggers", GoField: "DelegationTriggers", SQLType: "JSON", Nullable: true, PrimaryKey: false, Default: DefaultEmptyDict, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "inheritance_disabled", Attr: "inheritance_disabled", GoField: "InheritanceDisabled", SQLType: "BOOLEAN", Nullable: true, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "force_local_only", Attr: "force_local_only", GoField: "ForceLocalOnly", SQLType: "BOOLEAN", Nullable: true, PrimaryKey: false, Default: DefaultBool, DefaultValue: "false", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "INTEGER", Nullable: true, PrimaryKey: false, Default: DefaultInt, DefaultValue: "1", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE task_contexts (\n\tid UUID NOT NULL,\n\ttask_id UUID,\n\tparent_branch_id UUID,\n\tparent_branch_context_id UUID,\n\tdata JSON,\n\ttask_data JSON,\n\texecution_context JSON,\n\tdiscovered_patterns JSON,\n\timplementation_notes JSON,\n\ttest_results JSON,\n\tblockers JSON,\n\tlocal_decisions JSON,\n\tdelegation_queue JSON,\n\tlocal_overrides JSON,\n\tdelegation_triggers JSON,\n\tinheritance_disabled BOOLEAN,\n\tforce_local_only BOOLEAN,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE,\n\tupdated_at TIMESTAMP WITHOUT TIME ZONE,\n\tversion INTEGER,\n\tPRIMARY KEY (id),\n\tFOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,\n\tFOREIGN KEY(parent_branch_id) REFERENCES project_git_branchs (id),\n\tFOREIGN KEY(parent_branch_context_id) REFERENCES branch_contexts (id)\n)",
	}},
	{Name: "task_dependencies", Model: "TaskDependency", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "INTEGER", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "depends_on_task_id", Attr: "depends_on_task_id", GoField: "DependsOnTaskID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "dependency_type", Attr: "dependency_type", GoField: "DependencyType", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultString, DefaultValue: "\"blocks\"", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "now()", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE task_dependencies (\n\tid SERIAL NOT NULL,\n\ttask_id UUID NOT NULL,\n\tdepends_on_task_id UUID NOT NULL,\n\tdependency_type VARCHAR NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_task_dependency UNIQUE (task_id, depends_on_task_id),\n\tCONSTRAINT chk_no_self_dependency CHECK (task_id != depends_on_task_id),\n\tFOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,\n\tFOREIGN KEY(depends_on_task_id) REFERENCES tasks (id) ON DELETE CASCADE\n)",
	}},
	{Name: "task_labels", Model: "TaskLabel", Columns: []ColumnDef{
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "label_id", Attr: "label_id", GoField: "LabelID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "labels.id", OnDelete: "CASCADE", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "applied_at", Attr: "applied_at", GoField: "AppliedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		"CREATE TABLE task_labels (\n\ttask_id UUID NOT NULL,\n\tlabel_id VARCHAR NOT NULL,\n\tuser_id VARCHAR NOT NULL,\n\tapplied_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\tPRIMARY KEY (task_id, label_id),\n\tFOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE CASCADE,\n\tFOREIGN KEY(label_id) REFERENCES labels (id) ON DELETE CASCADE\n)",
		"CREATE INDEX idx_task_label_label ON task_labels (label_id)",
		"CREATE INDEX idx_task_label_task ON task_labels (task_id)",
	}},
}

// EnumTypes maps each PostgreSQL enum type to its labels (enum member names).
var EnumTypes = map[string][]string{
	"progressstate": {"INITIAL", "IN_PROGRESS", "COMPLETE"},
}
