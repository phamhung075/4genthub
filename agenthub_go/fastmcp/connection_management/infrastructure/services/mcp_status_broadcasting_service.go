package services

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	"agenthub/fastmcp/connection_management/domain/value_objects"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// MCPStatusBroadcastingService is the infrastructure implementation of
// StatusBroadcastingService. `_registered_clients` is a Python dict of dicts.
type MCPStatusBroadcastingService struct {
	registeredClients map[string]map[string]any
}

// NewMCPStatusBroadcastingService builds the service with no registered clients.
func NewMCPStatusBroadcastingService() *MCPStatusBroadcastingService {
	return &MCPStatusBroadcastingService{registeredClients: map[string]map[string]any{}}
}

// RegisterClientForUpdates stores the client registration and returns the update.
func (s *MCPStatusBroadcastingService) RegisterClientForUpdates(sessionID string, clientInfo map[string]any) (value_objects.StatusUpdate, error) {
	s.registeredClients[sessionID] = map[string]any{
		"client_info":   clientInfo,
		"registered_at": tmvo.IsoFormatNaive(entities.Now()),
	}
	return value_objects.CreateClientRegistrationUpdate(sessionID, true)
}

// UnregisterClient removes the client registration.
func (s *MCPStatusBroadcastingService) UnregisterClient(sessionID string) bool {
	if _, ok := s.registeredClients[sessionID]; ok {
		delete(s.registeredClients, sessionID)
		return true
	}
	return false
}

// BroadcastStatusUpdate always succeeds (the real broadcaster is a stub).
func (s *MCPStatusBroadcastingService) BroadcastStatusUpdate(update value_objects.StatusUpdate) bool {
	return true
}

// GetRegisteredClientsCount returns the number of registered clients.
func (s *MCPStatusBroadcastingService) GetRegisteredClientsCount() int {
	return len(s.registeredClients)
}

// GetLastBroadcastInfo returns the empty broadcast info.
func (s *MCPStatusBroadcastingService) GetLastBroadcastInfo() map[string]any {
	return map[string]any{
		"last_broadcast_time": nil,
		"last_broadcast_type": nil,
		"broadcast_count":     0,
	}
}

// ValidateBroadcastingInfrastructure reports the broadcaster as available. The
// Python import fastmcp.server.connection_status_broadcaster exists, so the
// ImportError branch is unreachable in production.
func (s *MCPStatusBroadcastingService) ValidateBroadcastingInfrastructure() map[string]any {
	return map[string]any{
		"status_broadcaster_available": true,
		"registered_clients":           len(s.registeredClients),
		"broadcasting_health":          "healthy",
	}
}
