package services

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	"agenthub/fastmcp/connection_management/domain/value_objects"
)

// ConnectionDiagnosticsService is the domain service interface for connection diagnostics.
type ConnectionDiagnosticsService interface {
	DiagnoseConnectionHealth(connection *entities.Connection) (value_objects.ConnectionHealth, error)
	GetConnectionStatistics() map[string]any
	GetReconnectionRecommendations() map[string]any
	AnalyzeConnectionPatterns(connections []*entities.Connection) map[string]any
	ValidateConnectionInfrastructure() map[string]any
}
