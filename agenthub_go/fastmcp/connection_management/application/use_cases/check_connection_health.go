// Package use_cases ports connection_management/application/use_cases.
package use_cases

import (
	"sort"

	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/domain/repositories"
	"agenthub/fastmcp/connection_management/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// connOrderedFromMap converts a Go map to an OrderedMap, preferring the given key
// order (Python dict insertion order) and appending any remaining keys sorted.
// The domain services already reduced Python dicts to maps, so the preferred list
// restores the observable JSON key order.
func connOrderedFromMap(m map[string]any, preferred []string) *tmentities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	out := tmentities.NewOrderedMap[any]()
	seen := map[string]bool{}
	for _, k := range preferred {
		if v, ok := m[k]; ok {
			out.Set(k, v)
			seen[k] = true
		}
	}
	rest := make([]string, 0, len(m))
	for k := range m {
		if !seen[k] {
			rest = append(rest, k)
		}
	}
	sort.Strings(rest)
	for _, k := range rest {
		out.Set(k, m[k])
	}
	return out
}

// connAnySlice converts a []string (or []any) service value to []any.
func connAnySlice(v any) []any {
	switch s := v.(type) {
	case []string:
		out := make([]any, len(s))
		for i, x := range s {
			out[i] = x
		}
		return out
	case []any:
		return s
	}
	return []any{}
}

// connInt reads an int from a service map value (Python int).
func connInt(v any) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return 0
}

var connConnectionStatsKeys = []string{
	"active_connections", "total_connections", "server_restart_count",
	"uptime_seconds", "connection_health", "error",
}

// CheckConnectionHealthUseCase is the use case for checking connection health.
type CheckConnectionHealthUseCase struct {
	connectionRepository repositories.ConnectionRepository
	diagnosticsService   services.ConnectionDiagnosticsService
}

// NewCheckConnectionHealthUseCase builds the use case.
func NewCheckConnectionHealthUseCase(
	connectionRepository repositories.ConnectionRepository,
	diagnosticsService services.ConnectionDiagnosticsService,
) *CheckConnectionHealthUseCase {
	return &CheckConnectionHealthUseCase{
		connectionRepository: connectionRepository,
		diagnosticsService:   diagnosticsService,
	}
}

// Execute runs the check connection health use case.
func (u *CheckConnectionHealthUseCase) Execute(request *dtos.ConnectionHealthRequest) (resp *dtos.ConnectionHealthResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connErrString(r)
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

	connectionStats := u.diagnosticsService.GetConnectionStatistics()
	recommendations := u.diagnosticsService.GetReconnectionRecommendations()

	connectionInfo := tmentities.NewOrderedMap[any]()
	if request.ConnectionID != nil {
		connection := u.connectionRepository.FindByID(*request.ConnectionID)
		if connection != nil {
			health, err := connection.DiagnoseHealth()
			if err != nil {
				panic(err)
			}
			connectionInfo = health.ToDict()
		} else {
			connectionInfo.Set("error", "Connection "+*request.ConnectionID+" not found")
		}
	} else {
		activeConnections := u.connectionRepository.FindAllActive()
		connectionInfo.Set("active_connections", len(activeConnections))
		connectionInfo.Set("total_connections", u.connectionRepository.GetConnectionCount())
	}

	status := "healthy"
	if av, ok := connectionStats["active_connections"]; ok {
		if connInt(av) == 0 {
			status = "no_clients"
		}
	} else {
		status = "no_clients"
	}

	return &dtos.ConnectionHealthResponse{
		Success:         true,
		Status:          status,
		ConnectionInfo:  connectionInfo,
		Diagnostics:     connOrderedFromMap(connectionStats, connConnectionStatsKeys),
		Recommendations: connAnySlice(recommendations["recommendations"]),
	}
}

// connErrString mirrors Python str(e).
func connErrString(v any) string {
	switch e := v.(type) {
	case error:
		return e.Error()
	case string:
		return e
	}
	return ""
}
