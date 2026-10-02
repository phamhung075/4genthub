package events

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ConnectionEvent is the base of all connection-related domain events.
type ConnectionEvent interface {
	// Name is the Python class name (the "event_type" of the base to_dict).
	Name() string
	// ToDict is to_dict(): event_type, timestamp, then the event's attributes in
	// assignment order. Python merges `**self.__dict__` last, so the timestamp is the
	// datetime object (not its ISO string) and a field named event_type replaces the
	// class name in place.
	ToDict() *entities.OrderedMap[any]
}

func baseDict(name string, ts time.Time, fields ...any) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("event_type", name)
	d.Set("timestamp", ts)
	for i := 0; i < len(fields); i += 2 {
		d.Set(fields[i].(string), fields[i+1])
	}
	return d
}

// ServerHealthChecked is raised when server health is checked.
type ServerHealthChecked struct {
	Timestamp     time.Time
	ServerName    string
	Status        string
	UptimeSeconds float64
}

func (e ServerHealthChecked) Name() string { return "ServerHealthChecked" }
func (e ServerHealthChecked) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "server_name", e.ServerName, "status", e.Status, "uptime_seconds", e.UptimeSeconds)
}

// ConnectionHealthChecked is raised when connection health is checked.
type ConnectionHealthChecked struct {
	Timestamp       time.Time
	ConnectionID    string
	Status          string
	IdleTimeSeconds float64
}

func (e ConnectionHealthChecked) Name() string { return "ConnectionHealthChecked" }
func (e ConnectionHealthChecked) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "connection_id", e.ConnectionID, "status", e.Status, "idle_time_seconds", e.IdleTimeSeconds)
}

// StatusUpdateRequested is raised when a status update is requested.
type StatusUpdateRequested struct {
	Timestamp  time.Time
	SessionID  string
	UpdateType string
}

func (e StatusUpdateRequested) Name() string { return "StatusUpdateRequested" }
func (e StatusUpdateRequested) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "session_id", e.SessionID, "update_type", e.UpdateType)
}

// ClientRegisteredForUpdates is raised when a client registers for status updates.
type ClientRegisteredForUpdates struct {
	Timestamp  time.Time
	SessionID  string
	ClientInfo map[string]any
}

func (e ClientRegisteredForUpdates) Name() string { return "ClientRegisteredForUpdates" }
func (e ClientRegisteredForUpdates) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "session_id", e.SessionID, "client_info", e.ClientInfo)
}

// ServerCapabilitiesRequested is raised when server capabilities are requested.
type ServerCapabilitiesRequested struct {
	Timestamp        time.Time
	RequesterSession string
}

func (e ServerCapabilitiesRequested) Name() string { return "ServerCapabilitiesRequested" }
func (e ServerCapabilitiesRequested) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "requester_session", e.RequesterSession)
}

// StatusUpdateBroadcasted is raised when a status update is broadcasted. Its own
// event_type attribute replaces the class name in to_dict.
type StatusUpdateBroadcasted struct {
	Timestamp time.Time
	EventType string
	SessionID string
	Data      map[string]any
}

func (e StatusUpdateBroadcasted) Name() string { return "StatusUpdateBroadcasted" }
func (e StatusUpdateBroadcasted) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "event_type", e.EventType, "session_id", e.SessionID, "data", e.Data)
}

// ClientRegistered is raised when a client is registered.
type ClientRegistered struct {
	Timestamp  time.Time
	SessionID  string
	ClientInfo map[string]any
}

func (e ClientRegistered) Name() string { return "ClientRegistered" }
func (e ClientRegistered) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "session_id", e.SessionID, "client_info", e.ClientInfo)
}

// ClientUnregistered is raised when a client is unregistered.
type ClientUnregistered struct {
	Timestamp time.Time
	SessionID string
	Reason    string
}

func (e ClientUnregistered) Name() string { return "ClientUnregistered" }
func (e ClientUnregistered) ToDict() *entities.OrderedMap[any] {
	return baseDict(e.Name(), e.Timestamp, "session_id", e.SessionID, "reason", e.Reason)
}
