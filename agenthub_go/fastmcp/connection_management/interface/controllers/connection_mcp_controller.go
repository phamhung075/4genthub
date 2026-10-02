package controllers

import (
	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/application/facades"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

var connCtlEnvKeys = []string{
	"auth_enabled", "cursor_tools_disabled", "mvp_mode",
	"database_configured", "services_configured",
}

var connCtlConnectionKeys = []string{
	"active_connections", "server_restart_count", "uptime_seconds",
	"status", "broadcasting_enabled",
}

// ConnectionMCPController is the simplified MCP controller for basic health monitoring.
type ConnectionMCPController struct {
	connectionFacade *facades.ConnectionApplicationFacade
}

// NewConnectionMCPController builds the controller.
func NewConnectionMCPController(connectionFacade *facades.ConnectionApplicationFacade) *ConnectionMCPController {
	return &ConnectionMCPController{connectionFacade: connectionFacade}
}

// HealthCheck is the simplified health check method (register_tools is FastMCP-specific
// and has no Go meaning, so it is not ported).
func (c *ConnectionMCPController) HealthCheck(includeDetails *bool, userID *string) (out *tmentities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = tmentities.NewOrderedMap[any]()
			out.Set("success", false)
			out.Set("status", "error")
			out.Set("message", "Health check temporarily unavailable")
			out.Set("action", "health_check")
		}
	}()
	response := c.connectionFacade.CheckServerHealth(includeDetails, userID)
	return connCtlFormatHealthCheckResponse(response)
}

// connCtlFormatHealthCheckResponse sanitizes the health check response for the MCP protocol.
func connCtlFormatHealthCheckResponse(response *dtos.HealthCheckResponse) *tmentities.OrderedMap[any] {
	if response.Success {
		sanitized := tmentities.NewOrderedMap[any]()
		sanitized.Set("success", true)
		sanitized.Set("status", response.Status)
		sanitized.Set("server_name", response.ServerName)
		sanitized.Set("version", response.Version)
		sanitized.Set("timestamp", response.Timestamp)

		if response.Authentication != nil && response.Authentication.Len() > 0 {
			auth := tmentities.NewOrderedMap[any]()
			auth.Set("enabled", connCtlGetDefault(response.Authentication, "enabled", false))
			auth.Set("mvp_mode", connCtlGetDefault(response.Authentication, "mvp_mode", false))
			sanitized.Set("authentication", auth)
		}

		if response.TaskManagement != nil && response.TaskManagement.Len() > 0 {
			tm := tmentities.NewOrderedMap[any]()
			tm.Set("task_management_enabled", connCtlGetDefault(response.TaskManagement, "task_management_enabled", true))
			sanitized.Set("task_management", tm)
		}

		if response.Environment != nil && response.Environment.Len() > 0 {
			env := tmentities.NewOrderedMap[any]()
			for _, key := range connCtlEnvKeys {
				if v, ok := response.Environment.Get(key); ok {
					env.Set(key, v)
				}
			}
			if env.Len() > 0 {
				sanitized.Set("environment", env)
			}
		}

		if response.Connections != nil && response.Connections.Len() > 0 {
			conns := tmentities.NewOrderedMap[any]()
			for _, key := range connCtlConnectionKeys {
				if v, ok := response.Connections.Get(key); ok {
					conns.Set(key, v)
				}
			}
			if conns.Len() > 0 {
				sanitized.Set("connections", conns)
			}
		}

		return sanitized
	}

	out := tmentities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("status", "error")
	out.Set("message", "Health check failed")
	out.Set("timestamp", response.Timestamp)
	return out
}

func connCtlGetDefault(m *tmentities.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}
