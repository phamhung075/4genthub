package services

import (
	"os"
	"strings"

	"agenthub/fastmcp/connection_management/domain/entities"
	"agenthub/fastmcp/connection_management/domain/value_objects"
)

// MCPServerHealthService is the infrastructure implementation of ServerHealthService.
type MCPServerHealthService struct{}

// NewMCPServerHealthService builds the service.
func NewMCPServerHealthService() *MCPServerHealthService { return &MCPServerHealthService{} }

// envIsTrue is os.environ.get(name, def).lower() == "true".
func envIsTrue(name, def string) bool {
	v := os.Getenv(name)
	if v == "" {
		v = def
	}
	return strings.ToLower(v) == "true"
}

// CheckServerHealth delegates to the server entity.
func (s *MCPServerHealthService) CheckServerHealth(server *entities.Server) (value_objects.ServerStatus, error) {
	return server.CheckHealth()
}

// GetEnvironmentInfo returns the sanitized environment flags.
func (s *MCPServerHealthService) GetEnvironmentInfo() map[string]any {
	authEnabled := envIsTrue("AUTH_ENABLED", "true")
	cursorToolsDisabled := envIsTrue("AGENTHUB_DISABLE_CURSOR_TOOLS", "false")
	mvpMode := envIsTrue("PRODUCTION", "false")
	databaseConfigured := os.Getenv("SUPABASE_URL") != "" || os.Getenv("DATABASE_URL") != ""
	return map[string]any{
		"auth_enabled":          authEnabled,
		"cursor_tools_disabled": cursorToolsDisabled,
		"mvp_mode":              mvpMode,
		"database_configured":   databaseConfigured,
		"services_configured": map[string]any{
			"database":        databaseConfigured,
			"authentication":  authEnabled,
			"task_management": true,
		},
	}
}

// GetAuthenticationStatus returns the auth configuration flags.
func (s *MCPServerHealthService) GetAuthenticationStatus() map[string]any {
	return map[string]any{
		"enabled":  envIsTrue("AUTH_ENABLED", "true"),
		"mvp_mode": envIsTrue("PRODUCTION", "false"),
	}
}

// GetTaskManagementInfo returns the task management info.
func (s *MCPServerHealthService) GetTaskManagementInfo() map[string]any {
	return map[string]any{
		"task_management_enabled": true,
		"enabled_tools_count":     0,
		"total_tools_count":       0,
		"enabled_tools":           []string{},
	}
}

// ValidateServerConfiguration returns the simplified configuration status.
func (s *MCPServerHealthService) ValidateServerConfiguration() map[string]any {
	connectionStats := map[string]any{
		"connections": map[string]any{"active_connections": 0},
		"server_info": map[string]any{"restart_count": 0, "uptime_seconds": 0},
	}
	statusBroadcastingActive := true
	return map[string]any{
		"active_connections":   connectionStats["connections"].(map[string]any)["active_connections"],
		"server_restart_count": connectionStats["server_info"].(map[string]any)["restart_count"],
		"uptime_seconds":       connectionStats["server_info"].(map[string]any)["uptime_seconds"],
		"status":               "healthy",
		"broadcasting_enabled": statusBroadcastingActive,
	}
}
