package use_cases

import (
	"time"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/domain/exceptions"
	"agenthub/fastmcp/connection_management/domain/repositories"
	"agenthub/fastmcp/connection_management/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

var connEnvKeys = []string{
	"auth_enabled", "cursor_tools_disabled", "mvp_mode",
	"database_configured", "services_configured",
}

var connAuthKeys = []string{"enabled", "mvp_mode"}

var connTaskManagementKeys = []string{
	"task_management_enabled", "enabled_tools_count", "total_tools_count", "enabled_tools",
}

var connValidateConfigKeys = []string{
	"active_connections", "server_restart_count", "uptime_seconds",
	"status", "broadcasting_enabled", "message",
}

// CheckServerHealthUseCase is the use case for checking server health.
type CheckServerHealthUseCase struct {
	serverRepository repositories.ServerRepository
	healthService    services.ServerHealthService
}

// NewCheckServerHealthUseCase builds the use case.
func NewCheckServerHealthUseCase(
	serverRepository repositories.ServerRepository,
	healthService services.ServerHealthService,
) *CheckServerHealthUseCase {
	return &CheckServerHealthUseCase{serverRepository: serverRepository, healthService: healthService}
}

// Execute runs the check server health use case.
func (u *CheckServerHealthUseCase) Execute(request *dtos.HealthCheckRequest) (resp *dtos.HealthCheckResponse) {
	defer func() {
		if r := recover(); r != nil {
			resp = connErrorHealthResponse("Unexpected error: " + connErrString(r))
		}
	}()

	server := u.serverRepository.GetCurrentServer()
	if server == nil {
		environment := connOrderedFromMap(u.healthService.GetEnvironmentInfo(), connEnvKeys)
		authentication := connOrderedFromMap(u.healthService.GetAuthenticationStatus(), connAuthKeys)
		taskManagement := connOrderedFromMap(u.healthService.GetTaskManagementInfo(), connTaskManagementKeys)
		name, _ := config.VersionInfo().Get("name")
		server = u.serverRepository.CreateServer(
			connString(name), config.Version, environment, authentication, taskManagement,
		)
		u.serverRepository.SaveServer(server)
	}

	serverStatus, err := server.CheckHealth()
	if err != nil {
		var failed *exceptions.ServerHealthCheckFailedError
		if ok := asServerHealthCheckFailed(err, &failed); ok {
			return connErrorHealthResponse(err.Error())
		}
		return connErrorHealthResponse("Unexpected error: " + err.Error())
	}

	connectionsInfo := tmentities.NewOrderedMap[any]()
	if request.IncludeDetails {
		connectionsInfo = connValidateConfiguration(u.healthService)
	}

	return &dtos.HealthCheckResponse{
		Success:        true,
		Status:         serverStatus.Status,
		ServerName:     serverStatus.ServerName,
		Version:        serverStatus.Version,
		UptimeSeconds:  serverStatus.UptimeSeconds,
		RestartCount:   serverStatus.RestartCount,
		Authentication: server.Authentication,
		TaskManagement: server.TaskManagement,
		Environment:    server.Environment,
		Connections:    connectionsInfo,
		Timestamp:      float64(time.Now().UnixNano()) / 1e9,
	}
}

// connValidateConfiguration mirrors the try/except around validate_server_configuration.
func connValidateConfiguration(healthService services.ServerHealthService) (out *tmentities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = tmentities.NewOrderedMap[any]()
			out.Set("error", connErrString(r))
		}
	}()
	return connOrderedFromMap(healthService.ValidateServerConfiguration(), connValidateConfigKeys)
}

// asServerHealthCheckFailed is errors.As without importing errors merely for this.
func asServerHealthCheckFailed(err error, target **exceptions.ServerHealthCheckFailedError) bool {
	for err != nil {
		if e, ok := err.(*exceptions.ServerHealthCheckFailedError); ok {
			*target = e
			return true
		}
		u, ok := err.(interface{ Unwrap() error })
		if !ok {
			return false
		}
		err = u.Unwrap()
	}
	return false
}

func connString(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func connErrorHealthResponse(msg string) *dtos.HealthCheckResponse {
	e := msg
	return &dtos.HealthCheckResponse{
		Success:        false,
		Status:         "error",
		ServerName:     "Unknown",
		Version:        "Unknown",
		UptimeSeconds:  0,
		RestartCount:   0,
		Authentication: tmentities.NewOrderedMap[any](),
		TaskManagement: tmentities.NewOrderedMap[any](),
		Environment:    tmentities.NewOrderedMap[any](),
		Connections:    tmentities.NewOrderedMap[any](),
		Timestamp:      float64(time.Now().UnixNano()) / 1e9,
		Error:          &e,
	}
}
