package services

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	"agenthub/fastmcp/connection_management/domain/value_objects"
)

// ServerHealthService is the domain service interface for server health operations.
type ServerHealthService interface {
	CheckServerHealth(server *entities.Server) (value_objects.ServerStatus, error)
	GetEnvironmentInfo() map[string]any
	GetAuthenticationStatus() map[string]any
	GetTaskManagementInfo() map[string]any
	ValidateServerConfiguration() map[string]any
}
