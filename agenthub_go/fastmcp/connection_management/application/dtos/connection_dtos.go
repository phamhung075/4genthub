// Package dtos ports connection_management/application/dtos/connection_dtos.py.
package dtos

import "agenthub/fastmcp/task_management/domain/entities"

// HealthCheckRequest is the request DTO for a health check operation.
type HealthCheckRequest struct {
	IncludeDetails bool
}

// NewHealthCheckRequest applies the Python default include_details=True.
func NewHealthCheckRequest(includeDetails *bool) *HealthCheckRequest {
	include := true
	if includeDetails != nil {
		include = *includeDetails
	}
	return &HealthCheckRequest{IncludeDetails: include}
}

// HealthCheckResponse is the response DTO for a health check operation.
type HealthCheckResponse struct {
	Success        bool
	Status         string
	ServerName     string
	Version        string
	UptimeSeconds  float64
	RestartCount   int
	Authentication *entities.OrderedMap[any]
	TaskManagement *entities.OrderedMap[any]
	Environment    *entities.OrderedMap[any]
	Connections    *entities.OrderedMap[any]
	Timestamp      float64
	Error          *string
}

// ServerCapabilitiesRequest is the request DTO for a server capabilities operation.
type ServerCapabilitiesRequest struct {
	IncludeDetails bool
}

// NewServerCapabilitiesRequest applies the Python default include_details=True.
func NewServerCapabilitiesRequest(includeDetails *bool) *ServerCapabilitiesRequest {
	include := true
	if includeDetails != nil {
		include = *includeDetails
	}
	return &ServerCapabilitiesRequest{IncludeDetails: include}
}

// ServerCapabilitiesResponse is the response DTO for a server capabilities operation.
type ServerCapabilitiesResponse struct {
	Success               bool
	CoreFeatures          []any
	AvailableActions      *entities.OrderedMap[[]any]
	AuthenticationEnabled bool
	MvpMode               bool
	Version               string
	TotalActions          int
	Error                 *string
}

// ConnectionHealthRequest is the request DTO for a connection health check.
type ConnectionHealthRequest struct {
	ConnectionID   *string
	IncludeDetails bool
}

// NewConnectionHealthRequest applies the Python defaults connection_id=None and
// include_details=True.
func NewConnectionHealthRequest(connectionID *string, includeDetails *bool) *ConnectionHealthRequest {
	include := true
	if includeDetails != nil {
		include = *includeDetails
	}
	return &ConnectionHealthRequest{ConnectionID: connectionID, IncludeDetails: include}
}

// ConnectionHealthResponse is the response DTO for a connection health check.
type ConnectionHealthResponse struct {
	Success         bool
	Status          string
	ConnectionInfo  *entities.OrderedMap[any]
	Diagnostics     *entities.OrderedMap[any]
	Recommendations []any
	Error           *string
}

// ServerStatusRequest is the request DTO for a server status operation.
type ServerStatusRequest struct {
	IncludeDetails bool
}

// NewServerStatusRequest applies the Python default include_details=True.
func NewServerStatusRequest(includeDetails *bool) *ServerStatusRequest {
	include := true
	if includeDetails != nil {
		include = *includeDetails
	}
	return &ServerStatusRequest{IncludeDetails: include}
}

// ServerStatusResponse is the response DTO for a server status operation.
type ServerStatusResponse struct {
	Success             bool
	ServerInfo          *entities.OrderedMap[any]
	ConnectionStats     *entities.OrderedMap[any]
	HealthStatus        *entities.OrderedMap[any]
	CapabilitiesSummary *entities.OrderedMap[any]
	Error               *string
}

// RegisterUpdatesRequest is the request DTO for registering status updates.
type RegisterUpdatesRequest struct {
	SessionID  string
	ClientInfo *entities.OrderedMap[any]
}

// RegisterUpdatesResponse is the response DTO for registering status updates.
type RegisterUpdatesResponse struct {
	Success    bool
	SessionID  string
	Registered bool
	UpdateInfo *entities.OrderedMap[any]
	Error      *string
}
