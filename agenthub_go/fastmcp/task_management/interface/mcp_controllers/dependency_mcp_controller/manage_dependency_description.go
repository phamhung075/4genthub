// Package dependency_mcp_controller ports
// task_management/interface/mcp_controllers/dependency_mcp_controller.
package dependency_mcp_controller

import "agenthub/fastmcp/task_management/domain/entities"

// ManageDependencyDescription is MANAGE_DEPENDENCY_DESCRIPTION (Python).
const ManageDependencyDescription = `
DEPENDENCY MANAGEMENT - Task workflow sequencing and blocking relationships

| Action              | Required Parameters                | Optional Parameters                | Description                                      |
|---------------------|-----------------------------------|------------------------------------|--------------------------------------------------|
| add_dependency      | task_id, dependency_data (with dependency_id) | project_id, git_branch_name (default: 'main'), user_id | Add a dependency to a task                       |
| remove_dependency   | task_id, dependency_data (with dependency_id) | project_id, git_branch_name, user_id | Remove a dependency from a task                  |
| get_dependencies    | task_id                           | project_id, git_branch_name, user_id | List all dependencies for a task                 |
| clear_dependencies  | task_id                           | project_id, git_branch_name, user_id | Remove all dependencies from a task              |
| get_blocking_tasks  | task_id                           | project_id, git_branch_name, user_id | List tasks blocking the given task               |

USAGE:
• Required: Provide task_id for all actions
• add/remove: dependency_data must include dependency_id
• Optional parameters: project_id, git_branch_name, user_id (auto-derived when omitted)
• Returns: Detailed errors for missing parameters, unknown actions, or internal failures
• Business logic: Delegated to application layer

WHY DEPENDENCIES MATTER: Task dependencies enforce workflow sequencing - blocked tasks cannot start until dependencies complete. This prevents workflow violations and maintains task execution order.
`

// ManageDependencyParametersDescription is MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION (Python); key order preserved.
var ManageDependencyParametersDescription = func() *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	m.Set("action", "Dependency management action to perform. Valid actions: 'add_dependency', 'remove_dependency', 'get_dependencies', 'clear_dependencies', 'get_blocking_tasks'")
	m.Set("task_id", "[OPTIONAL] Unique identifier for the target task. Required for all actions")
	m.Set("project_id", "[OPTIONAL] Project identifier for context. Optional - derived from task if not provided")
	m.Set("git_branch_name", "[OPTIONAL] Task tree identifier for hierarchical context. Default: 'main'")
	m.Set("user_id", "[OPTIONAL] User identifier for auditing and access control. Required for multi-tenancy")
	m.Set("dependency_data", `[OPTIONAL] JSON string containing dependency_id for add/remove actions. Example: '{"dependency_id": "task-uuid"}'. Required for add_dependency and remove_dependency actions`)
	return m
}()

func dependencyParamDesc(key string) string {
	value, _ := ManageDependencyParametersDescription.Get(key)
	return value
}

func dependencyStringProperty(description string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("type", "string")
	p.Set("description", description)
	return p
}

func buildManageDependencyProperties() *entities.OrderedMap[any] {
	props := entities.NewOrderedMap[any]()
	props.Set("action", dependencyStringProperty(dependencyParamDesc("action")))
	props.Set("task_id", dependencyStringProperty(dependencyParamDesc("task_id")))
	props.Set("project_id", dependencyStringProperty(dependencyParamDesc("project_id")))
	props.Set("git_branch_name", dependencyStringProperty(dependencyParamDesc("git_branch_name")))
	props.Set("user_id", dependencyStringProperty(dependencyParamDesc("user_id")))
	props.Set("dependency_data", dependencyStringProperty(dependencyParamDesc("dependency_data")))
	return props
}

// ManageDependencyParams is MANAGE_DEPENDENCY_PARAMS (Python); key order preserved.
var ManageDependencyParams = func() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("type", "object")
	m.Set("properties", buildManageDependencyProperties())
	m.Set("required", []any{"action"})
	m.Set("additionalProperties", false)
	return m
}()

// GetManageDependencyParameters returns MANAGE_DEPENDENCY_PARAMS["properties"].
func GetManageDependencyParameters() *entities.OrderedMap[any] {
	props, _ := ManageDependencyParams.Get("properties")
	return props.(*entities.OrderedMap[any])
}

// GetManageDependencyDescription returns MANAGE_DEPENDENCY_DESCRIPTION.
func GetManageDependencyDescription() string { return ManageDependencyDescription }

// ManageDependencyParameters is MANAGE_DEPENDENCY_PARAMETERS (Python legacy); key order preserved.
var ManageDependencyParameters = func() *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	m.Set("action", "Dependency management action to perform. Valid actions: 'add_dependency', 'remove_dependency', 'get_dependencies', 'clear_dependencies', 'get_blocking_tasks'. Required. (string)")
	m.Set("task_id", "Unique identifier for the target task. Required for all actions. (string)")
	m.Set("project_id", "Project identifier for context. Optional - derived from task if not provided. (string)")
	m.Set("git_branch_name", "Task tree identifier for hierarchical context. Optional, default: 'main'. (string)")
	m.Set("user_id", "User identifier for auditing and access control. Required for multi-tenancy. (string)")
	m.Set("dependency_data", "Dictionary containing dependency_id for add/remove actions. Optional for list/clear actions. Example: {'dependency_id': 'task-uuid'}. (string)")
	return m
}()
