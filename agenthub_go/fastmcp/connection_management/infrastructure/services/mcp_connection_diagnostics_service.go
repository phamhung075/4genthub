// Package services ports connection_management/infrastructure/services.
package services

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	"agenthub/fastmcp/connection_management/domain/value_objects"
)

// MCPConnectionDiagnosticsService is the infrastructure implementation of
// ConnectionDiagnosticsService.
type MCPConnectionDiagnosticsService struct{}

// NewMCPConnectionDiagnosticsService builds the service.
func NewMCPConnectionDiagnosticsService() *MCPConnectionDiagnosticsService {
	return &MCPConnectionDiagnosticsService{}
}

// DiagnoseConnectionHealth delegates to the connection entity.
func (s *MCPConnectionDiagnosticsService) DiagnoseConnectionHealth(connection *entities.Connection) (value_objects.ConnectionHealth, error) {
	return connection.DiagnoseHealth()
}

// GetConnectionStatistics returns the hard-coded basic stats.
func (s *MCPConnectionDiagnosticsService) GetConnectionStatistics() map[string]any {
	return map[string]any{
		"active_connections":   0,
		"total_connections":    0,
		"server_restart_count": 0,
		"uptime_seconds":       0,
		"connection_health":    "no_clients",
	}
}

// GetReconnectionRecommendations returns the hard-coded recommendations.
func (s *MCPConnectionDiagnosticsService) GetReconnectionRecommendations() map[string]any {
	return map[string]any{
		"recommended_action": "no_action_needed",
		"recommendations": []string{
			"Server is running normally",
			"No connection issues detected",
			"Monitor connection patterns for optimization",
		},
	}
}

// AnalyzeConnectionPatterns analyzes the given connections (default activity
// threshold of 30 minutes, as Connection.is_active).
func (s *MCPConnectionDiagnosticsService) AnalyzeConnectionPatterns(connections []*entities.Connection) map[string]any {
	if len(connections) == 0 {
		return map[string]any{
			"pattern_analysis": "no_connections",
			"issues":           []string{"No active connections to analyze"},
			"recommendations": []string{
				"Establish at least one connection for pattern analysis",
			},
		}
	}

	totalConnections := len(connections)
	activeConnections := []*entities.Connection{}
	idleConnections := []*entities.Connection{}
	for _, conn := range connections {
		if conn.IsActive(30) {
			activeConnections = append(activeConnections, conn)
		} else {
			idleConnections = append(idleConnections, conn)
		}
	}

	issues := []string{}
	recommendations := []string{}
	if len(idleConnections) > len(activeConnections) {
		issues = append(issues, "More idle connections than active ones")
		recommendations = append(recommendations, "Consider cleaning up idle connections")
	}
	if totalConnections > 10 {
		issues = append(issues, "High number of connections detected")
		recommendations = append(recommendations, "Monitor connection pooling and cleanup")
	}

	return map[string]any{
		"total_connections":  totalConnections,
		"active_connections": len(activeConnections),
		"idle_connections":   len(idleConnections),
		"issues":             issues,
		"recommendations":    recommendations,
	}
}

// ValidateConnectionInfrastructure reports the infrastructure as available. The
// Python implementation imports fastmcp.server.connection_manager and
// fastmcp.server.connection_status_broadcaster, both of which exist, so the
// ImportError branch is unreachable in production.
func (s *MCPConnectionDiagnosticsService) ValidateConnectionInfrastructure() map[string]any {
	return map[string]any{
		"connection_manager_available": true,
		"status_broadcaster_available": true,
		"infrastructure_health":        "healthy",
	}
}
