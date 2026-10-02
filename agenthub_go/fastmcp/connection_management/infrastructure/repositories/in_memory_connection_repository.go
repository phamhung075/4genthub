// Package repositories ports connection_management/infrastructure/repositories.
package repositories

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// InMemoryConnectionRepository is the in-memory implementation of
// ConnectionRepository. The Python dict keys are kept in insertion order, which is
// observable through get_connection_statistics/connection_ids and find_all_active.
type InMemoryConnectionRepository struct {
	connections *tmentities.OrderedMap[*entities.Connection]
}

// NewInMemoryConnectionRepository builds an empty repository.
func NewInMemoryConnectionRepository() *InMemoryConnectionRepository {
	return &InMemoryConnectionRepository{connections: tmentities.NewOrderedMap[*entities.Connection]()}
}

// FindByID returns the connection or nil.
func (r *InMemoryConnectionRepository) FindByID(connectionID string) *entities.Connection {
	v, _ := r.connections.Get(connectionID)
	return v
}

// FindAllActive returns the connections whose status is "active", in insertion order.
func (r *InMemoryConnectionRepository) FindAllActive() []*entities.Connection {
	out := []*entities.Connection{}
	for _, id := range r.connections.Keys() {
		conn, _ := r.connections.Get(id)
		if conn.Status == "active" {
			out = append(out, conn)
		}
	}
	return out
}

// SaveConnection stores the connection under its id.
func (r *InMemoryConnectionRepository) SaveConnection(connection *entities.Connection) {
	r.connections.Set(connection.ConnectionID, connection)
}

// CreateConnection creates and stores a new connection.
func (r *InMemoryConnectionRepository) CreateConnection(connectionID string, clientInfo map[string]any) *entities.Connection {
	connection := entities.CreateConnection(connectionID, clientInfo)
	r.connections.Set(connectionID, connection)
	return connection
}

// RemoveConnection deletes the connection if present.
func (r *InMemoryConnectionRepository) RemoveConnection(connectionID string) bool {
	if r.connections.Has(connectionID) {
		r.connections.Delete(connectionID)
		return true
	}
	return false
}

// GetConnectionCount counts the active connections.
func (r *InMemoryConnectionRepository) GetConnectionCount() int {
	return len(r.FindAllActive())
}

// GetConnectionStatistics mirrors the Python result shape.
func (r *InMemoryConnectionRepository) GetConnectionStatistics() map[string]any {
	allConnections := r.connections.Keys()
	activeConnections := r.FindAllActive()
	return map[string]any{
		"total_connections":    len(allConnections),
		"active_connections":   len(activeConnections),
		"inactive_connections": len(allConnections) - len(activeConnections),
		"connection_ids":       allConnections,
	}
}
