package git_branch_mcp_controller

// Git Branch Management Tool Description
// (Python manage_git_branch_description.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// ManageGitBranchDescription mirrors MANAGE_GIT_BRANCH_DESCRIPTION.
const ManageGitBranchDescription = `
GIT BRANCH MANAGEMENT - Branch operations: CRUD | agent assignment | lifecycle | statistics

ACTIONS: create | get | list | update | delete | assign_agent | unassign_agent | get_statistics | archive | restore

KEY PARAMS: project_id (REQUIRED for all) | git_branch_name (REQUIRED for create) | git_branch_id (REQUIRED for most except create/list) | agent_id (REQUIRED for assign/unassign)

AGENT ASSIGNMENT: Use git_branch_name OR git_branch_id for identification

STATISTICS: total_tasks | completed_tasks | progress_percentage

ERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error
`

// manageGitBranchParametersDescription mirrors
// MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION (dict[str, str], insertion order).
func manageGitBranchParametersDescription() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("action", "Git branch management action to perform. Valid values: create, get, list, update, delete, assign_agent, unassign_agent, get_statistics, archive, restore")
	m.Set("project_id", "Project identifier for the git branch operation")
	m.Set("git_branch_id", "Git branch identifier (UUID). Required for most actions except create/list")
	m.Set("git_branch_name", "Git branch name. Required for create, optional for update. Can be used instead of git_branch_id for agent assignment")
	m.Set("git_branch_description", "Description of the git branch. Optional for create/update operations")
	m.Set("agent_id", "Agent identifier for assignment operations. Required for assign_agent/unassign_agent actions")
	m.Set("user_id", "User identifier for authentication and audit trails")
	return m
}

// manageGitBranchParams mirrors MANAGE_GIT_BRANCH_PARAMS.
func manageGitBranchParams() *entities.OrderedMap[any] {
	descriptions := manageGitBranchParametersDescription()
	properties := entities.NewOrderedMap[any]()
	for _, key := range descriptions.Keys() {
		desc, _ := descriptions.Get(key)
		prop := entities.NewOrderedMap[any]()
		prop.Set("type", "string")
		prop.Set("description", desc)
		properties.Set(key, prop)
	}

	params := entities.NewOrderedMap[any]()
	params.Set("type", "object")
	params.Set("properties", properties)
	params.Set("required", []any{"action"})
	params.Set("additionalProperties", false)
	return params
}

// ManageGitBranchParametersDescription returns the module-level dict.
var ManageGitBranchParametersDescription = manageGitBranchParametersDescription()

// ManageGitBranchParams returns the module-level schema dict.
var ManageGitBranchParams = manageGitBranchParams()

// GetManageGitBranchParameters mirrors get_manage_git_branch_parameters().
func GetManageGitBranchParameters() any {
	v, _ := ManageGitBranchParams.Get("properties")
	return v
}

// GetManageGitBranchDescription mirrors get_manage_git_branch_description().
func GetManageGitBranchDescription() string {
	return ManageGitBranchDescription
}
