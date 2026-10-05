package repositories

import "agenthub/fastmcp/connection_management/domain/entities"

// ConnectionRepository is the repository interface of the Connection aggregate.
type ConnectionRepository interface {
	FindByID(connectionID string) *entities.Connection
	FindAllActive() []*entities.Connection
	SaveConnection(connection *entities.Connection)
	CreateConnection(connectionID string, clientInfo map[string]any) *entities.Connection
	RemoveConnection(connectionID string) bool
	GetConnectionCount() int
	GetConnectionStatistics() map[string]any
}
