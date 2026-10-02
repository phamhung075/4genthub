package httpapp

import (
	"sync"

	connectioninterface "agenthub/fastmcp/connection_management/interface"
	"agenthub/fastmcp/task_management/domain/entities"
)

// manageConnectionToolDescription is the description the Python server publishes
// for manage_connection. ConnectionMCPController.register_tools passes it
// explicitly to @mcp.tool(description=...), so it wins over the function
// docstring in FastMCP's FunctionTool.from_function
// (connection_mcp_controller.py:47). The connection/description_loader.py
// MANAGE_CONNECTION_DESCRIPTION is not used by that registration path.
const manageConnectionToolDescription = "Basic health check endpoint for system monitoring"

// connectionToolsInstance is the process-wide DDDCompliantConnectionTools.
// The Python server builds it once in mcp_entry_point.register_ddd_connection_tools
// and keeps the connection repositories and health state for the server lifetime.
var (
	connectionToolsOnce     sync.Once
	connectionToolsInstance *connectioninterface.DDDCompliantConnectionTools
)

// connectionTools returns the shared connection management controller wiring
// (in-memory repositories/services, no database).
func connectionTools() *connectioninterface.DDDCompliantConnectionTools {
	connectionToolsOnce.Do(func() {
		connectionToolsInstance = connectioninterface.NewDDDCompliantConnectionTools()
	})
	return connectionToolsInstance
}

// connectionToolDefinition is the manage_connection tool exactly as FastMCP
// publishes it: the controller's explicit description plus the inputSchema it
// derives from manage_connection(include_details: bool = True,
// user_id: str | None = None).
func connectionToolDefinition() (map[string]any, error) {
	schema, err := plainJSON(connectionInputSchema())
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"name":        "manage_connection",
		"description": manageConnectionToolDescription,
		"inputSchema": schema,
	}, nil
}

// connectionInputSchema is the pydantic JSON schema FastMCP derives from the
// Python manage_connection signature. Both parameters have defaults, so pydantic
// emits no "required" key.
func connectionInputSchema() *entities.OrderedMap[any] {
	includeDetails := entities.NewOrderedMap[any]()
	includeDetails.Set("default", true)
	includeDetails.Set("description", "Whether to include detailed information in health response")
	includeDetails.Set("title", "Include Details")
	includeDetails.Set("type", "boolean")

	stringType := entities.NewOrderedMap[any]()
	stringType.Set("type", "string")
	nullType := entities.NewOrderedMap[any]()
	nullType.Set("type", "null")

	userID := entities.NewOrderedMap[any]()
	userID.Set("anyOf", []any{stringType, nullType})
	userID.Set("default", nil)
	userID.Set("description", "User identifier for authentication and audit trails")
	userID.Set("title", "User Id")

	properties := entities.NewOrderedMap[any]()
	properties.Set("include_details", includeDetails)
	properties.Set("user_id", userID)

	schema := entities.NewOrderedMap[any]()
	schema.Set("properties", properties)
	schema.Set("type", "object")
	return schema
}

// callManageConnection invokes ConnectionMCPController.health_check. The Python
// tool forwards include_details (default true) and user_id (default None);
// extra arguments such as action are ignored, as the controller only implements
// the health_check action.
func (a *App) callManageConnection(args map[string]any, userID *string) any {
	includeDetails := true
	if v := getOptBoolPtr(args, "include_details"); v != nil {
		includeDetails = *v
	}
	effectiveUser := getOptStringPtr(args, "user_id")
	if effectiveUser == nil {
		effectiveUser = userID
	}
	return connectionTools().Controller.HealthCheck(&includeDetails, effectiveUser)
}
