package use_cases

import (
	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/domain/repositories"
	"agenthub/fastmcp/connection_management/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// GetServerCapabilitiesUseCase is the use case for getting server capabilities.
type GetServerCapabilitiesUseCase struct {
	serverRepository repositories.ServerRepository
	healthService    services.ServerHealthService
}

// NewGetServerCapabilitiesUseCase builds the use case.
func NewGetServerCapabilitiesUseCase(
	serverRepository repositories.ServerRepository,
	healthService services.ServerHealthService,
) *GetServerCapabilitiesUseCase {
	return &GetServerCapabilitiesUseCase{serverRepository: serverRepository, healthService: healthService}
}

// Execute runs the get server capabilities use case.
func (u *GetServerCapabilitiesUseCase) Execute(request *dtos.ServerCapabilitiesRequest) (resp *dtos.ServerCapabilitiesResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connErrString(r)
			resp = &dtos.ServerCapabilitiesResponse{
				Success:          false,
				CoreFeatures:     []any{},
				AvailableActions: tmentities.NewOrderedMap[[]any](),
				Version:          "Unknown",
				Error:            &e,
			}
		}
	}()

	server := u.serverRepository.GetCurrentServer()
	if server == nil {
		environment := connOrderedFromMap(u.healthService.GetEnvironmentInfo(), connEnvKeys)
		authentication := connOrderedFromMap(u.healthService.GetAuthenticationStatus(), connAuthKeys)
		taskManagement := connOrderedFromMap(u.healthService.GetTaskManagementInfo(), connTaskManagementKeys)
		server = u.serverRepository.CreateServer(
			"agenthub - Task Management & Agent Orchestration", "2.1.0",
			environment, authentication, taskManagement,
		)
		u.serverRepository.SaveServer(server)
	}

	capabilities, err := server.GetCapabilities()
	if err != nil {
		panic(err)
	}

	coreFeatures := make([]any, len(capabilities.CoreFeatures))
	for i, f := range capabilities.CoreFeatures {
		coreFeatures[i] = f
	}

	actions := tmentities.NewOrderedMap[[]any]()
	for _, k := range capabilities.AvailableActions.Keys() {
		v, _ := capabilities.AvailableActions.Get(k)
		actions.Set(k, connAnySlice(v))
	}

	return &dtos.ServerCapabilitiesResponse{
		Success:               true,
		CoreFeatures:          coreFeatures,
		AvailableActions:      actions,
		AuthenticationEnabled: connBool(capabilities.AuthenticationEnabled),
		MvpMode:               connBool(capabilities.MvpMode),
		Version:               capabilities.Version,
		TotalActions:          capabilities.GetTotalActionsCount(),
	}
}

// connBool coerces a raw capability value to bool (Python truthiness for the DTO).
func connBool(v any) bool {
	switch b := v.(type) {
	case bool:
		return b
	case nil:
		return false
	}
	return false
}
