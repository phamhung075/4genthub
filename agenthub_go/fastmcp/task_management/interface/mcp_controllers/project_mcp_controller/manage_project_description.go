package project_mcp_controller

// Project Management Tool Description
// (Python manage_project_description.py).

import "agenthub/fastmcp/task_management/domain/entities"

// ManageProjectDescription mirrors MANAGE_PROJECT_DESCRIPTION.
const ManageProjectDescription = `
PROJECT MANAGEMENT - Complete lifecycle: CRUD | health monitoring | resource management | multi-project coordination

ACTIONS: create | get | list | update | delete | project_health_check | cleanup_obsolete | validate_integrity | rebalance_agents

KEY PARAMS: name (REQUIRED for create) | project_id (REQUIRED for most except create/list) | force (bypass safety for maintenance/delete)

FEATURES: Health monitoring | Resource allocation | Cross-project learning | Agent optimization

ERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error | Maintenance→safety warnings
`

// ManageProjectParametersDescription mirrors MANAGE_PROJECT_PARAMETERS_DESCRIPTION
// (Python dict, insertion order preserved).
func ManageProjectParametersDescription() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("action", "Project management action to perform. Valid values: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents")
	m.Set("project_id", "Project identifier (UUID). Required for most actions except create/list")
	m.Set("name", "Project name. Required for create, can be used instead of project_id for get action")
	m.Set("description", "Project description. Optional for create/update operations")
	m.Set("user_id", "User identifier for authentication and audit trails")
	m.Set("force", "Force parameter to bypass safety checks for maintenance and delete operations")
	return m
}

// ManageProjectParams mirrors MANAGE_PROJECT_PARAMS (Python dict, insertion order
// preserved).
func ManageProjectParams() *entities.OrderedMap[any] {
	params := ManageProjectParametersDescription()
	props := entities.NewOrderedMap[any]()

	action := entities.NewOrderedMap[any]()
	action.Set("type", "string")
	action.Set("description", params.GetAny("action"))
	props.Set("action", action)

	projectID := entities.NewOrderedMap[any]()
	projectID.Set("type", "UUID")
	projectID.Set("description", params.GetAny("project_id"))
	props.Set("project_id", projectID)

	name := entities.NewOrderedMap[any]()
	name.Set("type", "string")
	name.Set("description", params.GetAny("name"))
	props.Set("name", name)

	description := entities.NewOrderedMap[any]()
	description.Set("type", "string")
	description.Set("description", params.GetAny("description"))
	props.Set("description", description)

	userID := entities.NewOrderedMap[any]()
	userID.Set("type", "string")
	userID.Set("description", params.GetAny("user_id"))
	props.Set("user_id", userID)

	force := entities.NewOrderedMap[any]()
	force.Set("type", "string")
	force.Set("description", params.GetAny("force"))
	props.Set("force", force)

	m := entities.NewOrderedMap[any]()
	m.Set("type", "object")
	m.Set("properties", props)
	m.Set("required", []any{"action"})
	m.Set("additionalProperties", false)
	m.Set("_validation_note", "Only action required at schema level - business logic validates per action")
	return m
}

// GetManageProjectParameters mirrors get_manage_project_parameters().
func GetManageProjectParameters() *entities.OrderedMap[any] {
	return ManageProjectParams().GetAny("properties").(*entities.OrderedMap[any])
}

// GetManageProjectDescription mirrors get_manage_project_description().
func GetManageProjectDescription() string { return ManageProjectDescription }
