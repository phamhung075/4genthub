package unified_context_controller

// Unified Context Management Description and Parameters
// (Python manage_unified_context_description.py).

import "agenthub/fastmcp/task_management/domain/entities"

// ManageUnifiedContextDescription ports MANAGE_UNIFIED_CONTEXT_DESCRIPTION.
const ManageUnifiedContextDescription = `
CONTEXT MANAGEMENT - 4-tier hierarchy (Global→Project→Branch→Task): CRUD | inheritance | caching | delegation | insights

ACTIONS: create | get | update | delete | resolve (full chain) | delegate (move between levels) | add_insight | add_progress | list

LEVELS: global (user-scoped) | project | branch | task | Each inherits from parent

KEY PARAMS: level (tier) | context_id (ID for level) | force_refresh (bypass cache) | include_inherited (full chain) | propagate_changes (cascade) | delegate_to ('delegate' action) | content ('add_insight'/'add_progress' actions)

FEATURES: Unified API | Auto-inheritance | Smart caching | Change propagation | Delegation queue | Backward compatible

ERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic
`

// ManageUnifiedContextParametersDescription ports
// MANAGE_UNIFIED_CONTEXT_PARAMETERS_DESCRIPTION.
var ManageUnifiedContextParametersDescription = newStringOrderedMap([][2]string{
	{"action", "Context management action to perform. Valid: 'create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list'"},
	{"level", "Context hierarchy level. Valid: 'global' (user-scoped), 'project', 'branch', 'task'. Determines inheritance scope and data isolation"},
	{"context_id", "Context identifier appropriate for the level. Use user_id for global, project_id for project, git_branch_id for branch, task_id for task"},
	{"data", "Context data as JSON string (automatically parsed). Supports nested structures, arrays, and complex data types"},
	{"user_id", "User identifier for authentication and audit trails. Used for user-scoped global contexts and access control"},
	{"project_id", "Project identifier for project-level context operations. Required for project, branch, and task level operations when not inferrable"},
	{"git_branch_id", "Git branch identifier for branch-level context operations. Required for branch and task level operations"},
	{"force_refresh", "Bypass cache and force fresh data retrieval. Use when cache consistency is critical. Accepts: 'true', 'false', '1', '0'"},
	{"include_inherited", "Include inherited data from parent levels in response. Enables complete context resolution with inheritance chain. Accepts: 'true', 'false', '1', '0'"},
	{"propagate_changes", "Automatically cascade changes to child levels in hierarchy. Maintains consistency across hierarchy. Accepts: 'true', 'false', '1', '0'"},
	{"delegate_to", "Target level for context delegation operations. Valid: 'global', 'project', 'branch', 'task'. Used with delegate action"},
	{"delegate_data", "Specific data to delegate to target level as JSON string. Can be subset of source context or completely new data"},
	{"delegation_reason", "Reason for context delegation for audit trails and team communication. Helps track why data was moved between hierarchy levels"},
	{"content", "Content for insight or progress operations. String content that will be categorized and added to the specified context level"},
	{"category", "Insight category for add_insight operations. Valid: 'technical', 'business', 'performance', 'risk', 'discovery'"},
	{"importance", "Importance level for insights and progress updates. Valid: 'low', 'medium', 'high', 'critical'"},
	{"agent", "Agent identifier that created the insight or progress update. String identifier for tracking agent contributions"},
	{"filters", "Filter criteria for list operations as JSON string. Supports filtering by data fields, creation dates, agents, and other metadata"},
})

// ManageUnifiedContextParams ports MANAGE_UNIFIED_CONTEXT_PARAMS.
var ManageUnifiedContextParams = newAnyOrderedMap()

func init() {
	properties := entities.NewOrderedMap[any]()
	for _, key := range []string{"action", "level", "context_id", "data", "content", "user_id", "project_id", "git_branch_id", "force_refresh", "include_inherited", "propagate_changes", "delegate_to", "delegate_data", "delegation_reason", "category", "importance", "agent", "filters"} {
		field := entities.NewOrderedMap[any]()
		field.Set("type", "string")
		if desc, ok := ManageUnifiedContextParametersDescription.Get(key); ok {
			field.Set("description", desc)
		}
		properties.Set(key, field)
	}
	required := []string{"action"}
	ManageUnifiedContextParams.Set("type", "object")
	ManageUnifiedContextParams.Set("properties", properties)
	ManageUnifiedContextParams.Set("required", required)
	ManageUnifiedContextParams.Set("additionalProperties", false)
}

// GetManageUnifiedContextParameters ports get_manage_unified_context_parameters.
func GetManageUnifiedContextParameters() *entities.OrderedMap[any] {
	v, _ := ManageUnifiedContextParams.Get("properties")
	props, _ := v.(*entities.OrderedMap[any])
	return props
}

// GetManageUnifiedContextDescription ports get_manage_unified_context_description.
func GetManageUnifiedContextDescription() string { return ManageUnifiedContextDescription }

// ManageUnifiedContextParameters ports the legacy MANAGE_UNIFIED_CONTEXT_PARAMETERS.
var ManageUnifiedContextParameters = newStringOrderedMap([][2]string{
	{"action", "Context management action to perform. Valid: 'create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list'. Each action operates within the specified hierarchy level"},
	{"level", "Context hierarchy level. Valid: 'global' (user-scoped), 'project' (project-specific), 'branch' (git branch), 'task' (task-specific). Determines inheritance scope and data isolation"},
	{"context_id", "Context identifier appropriate for the level. Use user_id for global, project_id for project, git_branch_id for branch, task_id for task. Must match the specified level"},
	{"data", "Context data as dictionary object or JSON string (automatically parsed). Supports nested structures, arrays, and complex data types. Legacy data_* parameters are automatically converted"},
	{"user_id", "User identifier for authentication and audit trails. Used for user-scoped global contexts and access control across all hierarchy levels"},
	{"project_id", "Project identifier for project-level context operations. Required for project, branch, and task level operations when not inferrable from context"},
	{"git_branch_id", "Git branch identifier for branch-level context operations. Required for branch and task level operations when creating branch-specific contexts"},
	{"force_refresh", "Bypass cache and force fresh data retrieval. Boolean, default: false. Use when cache consistency is critical or after external data changes"},
	{"include_inherited", "Include inherited data from parent levels in response. Boolean, default: false. Enables complete context resolution with inheritance chain"},
	{"propagate_changes", "Automatically cascade changes to child levels in hierarchy. Boolean, default: true. Maintains consistency across hierarchy when updating parent contexts"},
	{"delegate_to", "Target level for context delegation operations. Valid: 'global', 'project', 'branch', 'task'. Used with delegate action to move context data between levels"},
	{"delegate_data", "Specific data to delegate to target level as dictionary object or JSON string. Can be subset of source context or completely new data structure"},
	{"delegation_reason", "Reason for context delegation for audit trails and team communication. Helps track why data was moved between hierarchy levels"},
	{"content", "Content for insight or progress operations. String content that will be categorized and added to the specified context level"},
	{"category", "Insight category for add_insight operations. Valid: 'technical', 'business', 'performance', 'risk', 'discovery'. Helps organize and filter insights"},
	{"task_id", "Legacy: Context identifier for task-specific contexts. Automatically converted to context_id with level='task'. Use context_id with level parameter instead"},
	{"data_title", "Legacy: Context title data. Automatically merged into data object as {'title': value}. Use data parameter with structured content instead"},
	{"data_description", "Legacy: Context description data. Automatically merged into data object as {'description': value}. Use data parameter with structured content instead"},
	{"data_status", "Legacy: Context status data. Automatically merged into data object as {'status': value}. Use data parameter with structured content instead"},
	{"data_priority", "Legacy: Context priority data. Automatically merged into data object as {'priority': value}. Use data parameter with structured content instead"},
	{"data_tags", "Legacy: Context tags data. Automatically merged into data object as {'tags': value}. Use data parameter with structured content instead"},
	{"data_metadata", "Legacy: Context metadata. Automatically merged into data object as {'metadata': value}. Use data parameter with structured content instead"},
	{"importance", "Importance level for insights and progress updates. Valid: 'low', 'medium', 'high', 'critical'. Used for prioritization and filtering"},
	{"agent", "Agent identifier that created the insight or progress update. String identifier for tracking agent contributions and coordination"},
	{"filters", "Filter criteria for list operations as dictionary object or JSON string. Supports filtering by data fields, creation dates, agents, and other metadata"},
})

func newStringOrderedMap(pairs [][2]string) *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	for _, p := range pairs {
		m.Set(p[0], p[1])
	}
	return m
}

func newAnyOrderedMap() *entities.OrderedMap[any] { return entities.NewOrderedMap[any]() }
