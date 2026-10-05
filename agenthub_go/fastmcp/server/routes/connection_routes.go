// connection_routes.go ports server/routes/connection_routes.py.
//
// The FastAPI APIRouter plumbing has no Go meaning; the handler logic, response
// keys and key order are preserved. The facade is the existing Go
// ConnectionApplicationFacade; the module-level dependencies are wired like the
// Python module import.
package routes

import (
	"fmt"

	"agenthub/fastmcp/auth"
	"agenthub/fastmcp/config"
	dtos "agenthub/fastmcp/connection_management/application/dtos"
	connfacades "agenthub/fastmcp/connection_management/application/facades"
	connrepos "agenthub/fastmcp/connection_management/infrastructure/repositories"
	connservices "agenthub/fastmcp/connection_management/infrastructure/services"
	"agenthub/fastmcp/task_management/domain/entities"
)

// routesHTTPErr mirrors FastAPI's HTTPException. The name is unique to these
// route ports so it cannot collide with helpers other files in the package
// declare.
func routesHTTPErr(status int, detail string) *auth.HTTPException {
	return &auth.HTTPException{StatusCode: status, Detail: detail}
}

// connectionFacade is built exactly like the Python module-level connection_facade.
var connectionFacade = connfacades.NewConnectionApplicationFacade(
	connrepos.NewInMemoryServerRepository(),
	connrepos.NewInMemoryConnectionRepository(),
	connservices.NewMCPServerHealthService(),
	connservices.NewMCPConnectionDiagnosticsService(),
	connservices.NewMCPStatusBroadcastingService(),
)

// healthCheckFn performs the probe HealthCheck reports on. It wraps the shared
// facade so production keeps one wiring point, while tests can substitute a
// panicking probe to exercise HealthCheck's recover branch.
var healthCheckFn = func(includeDetails *bool, userID *string) *dtos.HealthCheckResponse {
	return connectionFacade.CheckServerHealth(includeDetails, userID)
}

// HealthCheck mirrors GET /health. include_details defaults to True.
func HealthCheck(includeDetails *bool) (out *entities.OrderedMap[any]) {
	include := true
	if includeDetails != nil {
		include = *includeDetails
	}
	out = entities.NewOrderedMap[any]()
	defer func() {
		if r := recover(); r != nil {
			// Python returns a basic healthy status even on error. out is the
			// named result, so this rebuilt body actually reaches the caller;
			// the name is the package-level config.ServerName constant: a
			// constant has no receiver and cannot be nil, so it is safe to read
			// inside this recover branch, where the probed health response may
			// never have been produced.
			out = entities.NewOrderedMap[any]()
			out.Set("success", true)
			out.Set("status", "healthy")
			out.Set("server_name", config.ServerName)
			out.Set("version", "unknown")
			out.Set("uptime_seconds", 0)
			out.Set("timestamp", 0)
			out.Set("error", fmt.Sprintf("%v", r))
		}
	}()

	health := healthCheckFn(&include, nil)

	out.Set("success", health.Success)
	out.Set("status", health.Status)
	out.Set("server_name", health.ServerName)
	out.Set("version", health.Version)
	out.Set("uptime_seconds", health.UptimeSeconds)
	out.Set("timestamp", health.Timestamp)

	if include {
		if health.Authentication != nil && health.Authentication.Len() > 0 {
			out.Set("authentication", health.Authentication)
		}
		if health.TaskManagement != nil && health.TaskManagement.Len() > 0 {
			out.Set("task_management", health.TaskManagement)
		}
		if health.Environment != nil && health.Environment.Len() > 0 {
			out.Set("environment", health.Environment)
		}
		if health.Connections != nil && health.Connections.Len() > 0 {
			out.Set("connections", health.Connections)
		}
	}

	if health.Error != nil && *health.Error != "" {
		out.Set("error", *health.Error)
	}
	return out
}

// ConnectionStatus mirrors GET /status.
func ConnectionStatus() (*entities.OrderedMap[any], error) {
	out := entities.NewOrderedMap[any]()
	var failure error
	func() {
		defer func() {
			if r := recover(); r != nil {
				failure = routesHTTPErr(500, fmt.Sprintf("Failed to get connection status: %v", r))
			}
		}()
		include := true
		capabilities := connectionFacade.GetServerCapabilities(&include, nil)

		caps := entities.NewOrderedMap[any]()
		caps.Set("version", capabilities.Version)
		// Python hasattr(capabilities_response, "features") is False for the DTO.
		caps.Set("features", []any{})
		// Python hasattr(capabilities_response, "limits") is False for the DTO.
		caps.Set("limits", entities.NewOrderedMap[any]())

		out.Set("success", true)
		out.Set("status", "connected")
		out.Set("capabilities", caps)
	}()
	if failure != nil {
		return nil, failure
	}
	return out, nil
}
