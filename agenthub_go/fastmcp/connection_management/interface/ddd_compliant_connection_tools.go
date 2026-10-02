// Package interfacelayer ports connection_management/interface/ddd_compliant_connection_tools.py.
//
// The FastMCP register_tools plumbing has no Go meaning (there is no generic FastMCP
// server type in the Go port), so only the dependency-injection wiring is ported and
// the controller is exposed for callers that have their own registration mechanism.
package interfacelayer

import (
	"agenthub/fastmcp/connection_management/application/facades"
	"agenthub/fastmcp/connection_management/infrastructure/repositories"
	"agenthub/fastmcp/connection_management/infrastructure/services"
	"agenthub/fastmcp/connection_management/interface/controllers"
)

// DDDCompliantConnectionTools wires the connection management layers.
type DDDCompliantConnectionTools struct {
	serverRepository     *repositories.InMemoryServerRepository
	connectionRepository *repositories.InMemoryConnectionRepository
	healthService        *services.MCPServerHealthService
	diagnosticsService   *services.MCPConnectionDiagnosticsService
	broadcastingService  *services.MCPStatusBroadcastingService

	connectionFacade *facades.ConnectionApplicationFacade
	Controller       *controllers.ConnectionMCPController
}

// NewDDDCompliantConnectionTools builds the tools with proper dependency injection.
func NewDDDCompliantConnectionTools() *DDDCompliantConnectionTools {
	serverRepository := repositories.NewInMemoryServerRepository()
	connectionRepository := repositories.NewInMemoryConnectionRepository()
	healthService := services.NewMCPServerHealthService()
	diagnosticsService := services.NewMCPConnectionDiagnosticsService()
	broadcastingService := services.NewMCPStatusBroadcastingService()

	connectionFacade := facades.NewConnectionApplicationFacade(
		serverRepository,
		connectionRepository,
		healthService,
		diagnosticsService,
		broadcastingService,
	)

	return &DDDCompliantConnectionTools{
		serverRepository:     serverRepository,
		connectionRepository: connectionRepository,
		healthService:        healthService,
		diagnosticsService:   diagnosticsService,
		broadcastingService:  broadcastingService,
		connectionFacade:     connectionFacade,
		Controller:           controllers.NewConnectionMCPController(connectionFacade),
	}
}
