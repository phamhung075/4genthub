package exceptions

import "fmt"

// ConnectionError is the base exception for connection management domain errors.
type ConnectionError struct{ Msg string }

func (e *ConnectionError) Error() string { return e.Msg }

// ServerNotFoundError: a server cannot be found.
type ServerNotFoundError struct {
	ConnectionError
	ServerName string
}

func (e *ServerNotFoundError) Unwrap() error { return &e.ConnectionError }

func NewServerNotFoundError(serverName string) *ServerNotFoundError {
	return &ServerNotFoundError{ConnectionError{fmt.Sprintf("Server not found: %s", serverName)}, serverName}
}

// ConnectionNotFoundError: a connection cannot be found.
type ConnectionNotFoundError struct {
	ConnectionError
	ConnectionID string
}

func (e *ConnectionNotFoundError) Unwrap() error { return &e.ConnectionError }

func NewConnectionNotFoundError(connectionID string) *ConnectionNotFoundError {
	return &ConnectionNotFoundError{ConnectionError{fmt.Sprintf("Connection not found: %s", connectionID)}, connectionID}
}

// InvalidServerStatusError: the server status is invalid.
type InvalidServerStatusError struct {
	ConnectionError
	Status string
}

func (e *InvalidServerStatusError) Unwrap() error { return &e.ConnectionError }

func NewInvalidServerStatusError(status string) *InvalidServerStatusError {
	return &InvalidServerStatusError{ConnectionError{fmt.Sprintf("Invalid server status: %s", status)}, status}
}

// InvalidConnectionStatusError: the connection status is invalid.
type InvalidConnectionStatusError struct {
	ConnectionError
	Status string
}

func (e *InvalidConnectionStatusError) Unwrap() error { return &e.ConnectionError }

func NewInvalidConnectionStatusError(status string) *InvalidConnectionStatusError {
	return &InvalidConnectionStatusError{ConnectionError{fmt.Sprintf("Invalid connection status: %s", status)}, status}
}

// ServerHealthCheckFailedError: the server health check failed.
type ServerHealthCheckFailedError struct {
	ConnectionError
	Reason string
}

func (e *ServerHealthCheckFailedError) Unwrap() error { return &e.ConnectionError }

func NewServerHealthCheckFailedError(reason string) *ServerHealthCheckFailedError {
	return &ServerHealthCheckFailedError{ConnectionError{fmt.Sprintf("Server health check failed: %s", reason)}, reason}
}

// ConnectionHealthCheckFailedError: the health check of a connection failed.
type ConnectionHealthCheckFailedError struct {
	ConnectionError
	ConnectionID string
	Reason       string
}

func (e *ConnectionHealthCheckFailedError) Unwrap() error { return &e.ConnectionError }

func NewConnectionHealthCheckFailedError(connectionID, reason string) *ConnectionHealthCheckFailedError {
	return &ConnectionHealthCheckFailedError{
		ConnectionError{fmt.Sprintf("Connection health check failed for %s: %s", connectionID, reason)}, connectionID, reason}
}

// StatusBroadcastError: status broadcasting failed.
type StatusBroadcastError struct {
	ConnectionError
	Reason string
}

func (e *StatusBroadcastError) Unwrap() error { return &e.ConnectionError }

func NewStatusBroadcastError(reason string) *StatusBroadcastError {
	return &StatusBroadcastError{ConnectionError{fmt.Sprintf("Status broadcast failed: %s", reason)}, reason}
}
