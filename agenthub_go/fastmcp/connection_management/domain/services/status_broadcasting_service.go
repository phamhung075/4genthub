package services

import "agenthub/fastmcp/connection_management/domain/value_objects"

// StatusBroadcastingService is the domain service interface for status broadcasting.
type StatusBroadcastingService interface {
	RegisterClientForUpdates(sessionID string, clientInfo map[string]any) (value_objects.StatusUpdate, error)
	UnregisterClient(sessionID string) bool
	BroadcastStatusUpdate(update value_objects.StatusUpdate) bool
	GetRegisteredClientsCount() int
	GetLastBroadcastInfo() map[string]any
	ValidateBroadcastingInfrastructure() map[string]any
}
