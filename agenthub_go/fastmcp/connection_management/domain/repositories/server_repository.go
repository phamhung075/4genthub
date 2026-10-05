package repositories

import (
	"agenthub/fastmcp/connection_management/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// ServerRepository is the repository interface of the Server aggregate.
type ServerRepository interface {
	GetCurrentServer() *entities.Server
	SaveServer(server *entities.Server)
	CreateServer(name, version string, environment, authentication, taskManagement *tmentities.OrderedMap[any]) *entities.Server
	UpdateServerUptime(server *entities.Server)
}
