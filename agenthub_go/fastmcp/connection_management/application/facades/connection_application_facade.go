// Package facades ports connection_management/application/facades.
package facades

import (
	"agenthub/fastmcp/connection_management/application/dtos"
	usecases "agenthub/fastmcp/connection_management/application/use_cases"
	"agenthub/fastmcp/connection_management/domain/repositories"
	"agenthub/fastmcp/connection_management/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// ConnectionApplicationFacade orchestrates connection-related use cases.
type ConnectionApplicationFacade struct {
	serverRepository     repositories.ServerRepository
	connectionRepository repositories.ConnectionRepository
	healthService        services.ServerHealthService
	diagnosticsService   services.ConnectionDiagnosticsService
	broadcastingService  services.StatusBroadcastingService

	checkHealthUseCase           *usecases.CheckServerHealthUseCase
	getCapabilitiesUseCase       *usecases.GetServerCapabilitiesUseCase
	checkConnectionHealthUseCase *usecases.CheckConnectionHealthUseCase
	getStatusUseCase             *usecases.GetServerStatusUseCase
	registerUpdatesUseCase       *usecases.RegisterStatusUpdatesUseCase
}

// NewConnectionApplicationFacade builds the facade with its dependencies.
func NewConnectionApplicationFacade(
	serverRepository repositories.ServerRepository,
	connectionRepository repositories.ConnectionRepository,
	healthService services.ServerHealthService,
	diagnosticsService services.ConnectionDiagnosticsService,
	broadcastingService services.StatusBroadcastingService,
) *ConnectionApplicationFacade {
	return &ConnectionApplicationFacade{
		serverRepository:             serverRepository,
		connectionRepository:         connectionRepository,
		healthService:                healthService,
		diagnosticsService:           diagnosticsService,
		broadcastingService:          broadcastingService,
		checkHealthUseCase:           usecases.NewCheckServerHealthUseCase(serverRepository, healthService),
		getCapabilitiesUseCase:       usecases.NewGetServerCapabilitiesUseCase(serverRepository, healthService),
		checkConnectionHealthUseCase: usecases.NewCheckConnectionHealthUseCase(connectionRepository, diagnosticsService),
		getStatusUseCase:             usecases.NewGetServerStatusUseCase(serverRepository, connectionRepository, healthService, diagnosticsService),
		registerUpdatesUseCase:       usecases.NewRegisterStatusUpdatesUseCase(broadcastingService),
	}
}

func connDefaultTrue(v *bool) bool {
	if v == nil {
		return true
	}
	return *v
}

// CheckServerHealth checks server health status.
func (f *ConnectionApplicationFacade) CheckServerHealth(includeDetails *bool, userID *string) (resp *dtos.HealthCheckResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connPanicString(r)
			resp = &dtos.HealthCheckResponse{
				Success:        false,
				Status:         "error",
				ServerName:     "Unknown",
				Version:        "Unknown",
				Authentication: tmentities.NewOrderedMap[any](),
				TaskManagement: tmentities.NewOrderedMap[any](),
				Environment:    tmentities.NewOrderedMap[any](),
				Connections:    tmentities.NewOrderedMap[any](),
				Timestamp:      0,
				Error:          &e,
			}
		}
	}()
	request := dtos.NewHealthCheckRequest(includeDetails)
	return f.checkHealthUseCase.Execute(request)
}

// GetServerCapabilities returns server capabilities and features.
func (f *ConnectionApplicationFacade) GetServerCapabilities(includeDetails *bool, userID *string) (resp *dtos.ServerCapabilitiesResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connPanicString(r)
			resp = &dtos.ServerCapabilitiesResponse{
				Success:          false,
				CoreFeatures:     []any{},
				AvailableActions: tmentities.NewOrderedMap[[]any](),
				Version:          "Unknown",
				Error:            &e,
			}
		}
	}()
	request := dtos.NewServerCapabilitiesRequest(includeDetails)
	return f.getCapabilitiesUseCase.Execute(request)
}

// CheckConnectionHealth checks connection health and diagnostics.
func (f *ConnectionApplicationFacade) CheckConnectionHealth(connectionID *string, includeDetails *bool, userID *string) (resp *dtos.ConnectionHealthResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connPanicString(r)
			resp = &dtos.ConnectionHealthResponse{
				Success:         false,
				Status:          "error",
				ConnectionInfo:  tmentities.NewOrderedMap[any](),
				Diagnostics:     tmentities.NewOrderedMap[any](),
				Recommendations: []any{},
				Error:           &e,
			}
		}
	}()
	request := dtos.NewConnectionHealthRequest(connectionID, includeDetails)
	return f.checkConnectionHealthUseCase.Execute(request)
}

// GetServerStatus returns comprehensive server status.
func (f *ConnectionApplicationFacade) GetServerStatus(includeDetails *bool, userID *string) (resp *dtos.ServerStatusResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connPanicString(r)
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
	request := dtos.NewServerStatusRequest(includeDetails)
	return f.getStatusUseCase.Execute(request)
}

// RegisterForStatusUpdates registers a client for real-time status updates.
func (f *ConnectionApplicationFacade) RegisterForStatusUpdates(sessionID string, clientInfo *tmentities.OrderedMap[any], userID *string) (resp *dtos.RegisterUpdatesResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connPanicString(r)
			resp = &dtos.RegisterUpdatesResponse{
				Success:    false,
				SessionID:  sessionID,
				Registered: false,
				UpdateInfo: tmentities.NewOrderedMap[any](),
				Error:      &e,
			}
		}
	}()
	request := &dtos.RegisterUpdatesRequest{SessionID: sessionID, ClientInfo: clientInfo}
	return f.registerUpdatesUseCase.Execute(request)
}

// connPanicString mirrors Python str(e).
func connPanicString(v any) string {
	switch e := v.(type) {
	case error:
		return e.Error()
	case string:
		return e
	}
	return ""
}
