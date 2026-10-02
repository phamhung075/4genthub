package repositories

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// InMemoryServerRepository is the in-memory implementation of ServerRepository. It
// holds at most one server instance (Python keeps a single `_server`).
type InMemoryServerRepository struct {
	server *entities.Server
}

// NewInMemoryServerRepository builds an empty repository.
func NewInMemoryServerRepository() *InMemoryServerRepository {
	return &InMemoryServerRepository{}
}

// GetCurrentServer returns the stored server or nil.
func (r *InMemoryServerRepository) GetCurrentServer() *entities.Server { return r.server }

// SaveServer stores the server state.
func (r *InMemoryServerRepository) SaveServer(server *entities.Server) { r.server = server }

// CreateServer creates and stores a new server instance.
func (r *InMemoryServerRepository) CreateServer(name, version string, environment, authentication, taskManagement *tmentities.OrderedMap[any]) *entities.Server {
	server := entities.CreateServer(name, version, environment, authentication, taskManagement)
	r.server = server
	return server
}

// UpdateServerUptime re-saves the server (the entity calculates uptime dynamically).
func (r *InMemoryServerRepository) UpdateServerUptime(server *entities.Server) {
	r.SaveServer(server)
}
