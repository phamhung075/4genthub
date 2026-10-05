package use_cases

import (
	"agenthub/fastmcp/config"
	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/domain/repositories"
	"agenthub/fastmcp/connection_management/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// GetServerStatusUseCase is the use case for getting comprehensive server status.
type GetServerStatusUseCase struct {
	serverRepository     repositories.ServerRepository
	connectionRepository repositories.ConnectionRepository
	healthService        services.ServerHealthService
	diagnosticsService   services.ConnectionDiagnosticsService
}

// NewGetServerStatusUseCase builds the use case.
func NewGetServerStatusUseCase(
	serverRepository repositories.ServerRepository,
	connectionRepository repositories.ConnectionRepository,
	healthService services.ServerHealthService,
	diagnosticsService services.ConnectionDiagnosticsService,
) *GetServerStatusUseCase {
	return &GetServerStatusUseCase{
		serverRepository:     serverRepository,
		connectionRepository: connectionRepository,
		healthService:        healthService,
		diagnosticsService:   diagnosticsService,
	}
}

// Execute runs the get server status use case.
func (u *GetServerStatusUseCase) Execute(request *dtos.ServerStatusRequest) (resp *dtos.ServerStatusResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connErrString(r)
			resp = &dtos.ServerStatusResponse{
				Success:             false,
				ServerInfo:          tmentities.NewOrderedMap[any](),
				ConnectionStats:     tmentities.NewOrderedMap[any](),
				HealthStatus:        tmentities.NewOrderedMap[any](),
				CapabilitiesSummary: tmentities.NewOrderedMap[any](),
				Error:               &e,
			}
		}
	}()

	server := u.serverRepository.GetCurrentServer()
	if server == nil {
		environment := connOrderedFromMap(u.healthService.GetEnvironmentInfo(), connEnvKeys)
		authentication := connOrderedFromMap(u.healthService.GetAuthenticationStatus(), connAuthKeys)
		taskManagement := connOrderedFromMap(u.healthService.GetTaskManagementInfo(), connTaskManagementKeys)
		server = u.serverRepository.CreateServer(
			config.ServerName, "2.1.0",
			environment, authentication, taskManagement,
		)
	}

	healthStatus, err := server.CheckHealth()
	if err != nil {
		panic(err)
	}

	connectionStats := u.diagnosticsService.GetConnectionStatistics()

	capabilities, err := server.GetCapabilities()
	if err != nil {
		panic(err)
	}
	capabilitiesSummary := tmentities.NewOrderedMap[any]()
	capabilitiesSummary.Set("total_features", len(capabilities.CoreFeatures))
	capabilitiesSummary.Set("total_actions", capabilities.GetTotalActionsCount())
	capabilitiesSummary.Set("authentication_enabled", capabilities.AuthenticationEnabled)

	serverInfo := tmentities.NewOrderedMap[any]()
	serverInfo.Set("name", server.Name)
	serverInfo.Set("version", server.Version)
	serverInfo.Set("uptime_seconds", server.GetUptimeSeconds())
	serverInfo.Set("restart_count", server.RestartCount)

	return &dtos.ServerStatusResponse{
		Success:             true,
		ServerInfo:          serverInfo,
		ConnectionStats:     connOrderedFromMap(connectionStats, connConnectionStatsKeys),
		HealthStatus:        healthStatus.ToDict(),
		CapabilitiesSummary: capabilitiesSummary,
	}
}
