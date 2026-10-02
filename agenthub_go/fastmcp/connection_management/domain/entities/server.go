package entities

import (
	"time"

	tmentities "agenthub/fastmcp/task_management/domain/entities"

	"agenthub/fastmcp/connection_management/domain/events"
	"agenthub/fastmcp/connection_management/domain/value_objects"
)

// Server is the domain entity of the MCP server instance. The configuration dicts keep
// Python's insertion order because check_health publishes them.
type Server struct {
	Name           string
	Version        string
	StartedAt      time.Time
	RestartCount   int
	Environment    *tmentities.OrderedMap[any]
	Authentication *tmentities.OrderedMap[any]
	TaskManagement *tmentities.OrderedMap[any]

	events []events.ConnectionEvent
}

func orEmpty(m *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	if m == nil {
		return tmentities.NewOrderedMap[any]()
	}
	return m
}

// CreateServer is the factory for a new server instance.
func CreateServer(name, version string, environment, authentication, taskManagement *tmentities.OrderedMap[any]) *Server {
	return &Server{
		Name: name, Version: version, StartedAt: Now(),
		Environment: orEmpty(environment), Authentication: orEmpty(authentication), TaskManagement: orEmpty(taskManagement),
	}
}

func (s *Server) GetUptimeSeconds() float64 { return seconds(Now().Sub(s.StartedAt)) }

// CheckHealth performs the health check and records a ServerHealthChecked event.
func (s *Server) CheckHealth() (value_objects.ServerStatus, error) {
	uptime := s.GetUptimeSeconds()
	status := "unhealthy"
	if uptime > 0 {
		status = "healthy"
	}

	info := tmentities.NewOrderedMap[any]()
	info.Set("status", status)
	info.Set("uptime_seconds", uptime)
	info.Set("restart_count", s.RestartCount)
	info.Set("authentication", s.Authentication)
	info.Set("task_management", s.TaskManagement)
	info.Set("environment", s.Environment)

	s.events = append(s.events, events.ServerHealthChecked{
		Timestamp: Now(), ServerName: s.Name, Status: status, UptimeSeconds: uptime,
	})
	return value_objects.NewServerStatus(status, s.Name, s.Version, uptime, s.RestartCount, info)
}

// GetCapabilities returns the server capabilities and features.
func (s *Server) GetCapabilities() (value_objects.ServerCapabilities, error) {
	core := []string{
		"Task Management", "Project Management", "Agent Orchestration", "Cursor Rules Integration",
		"Multi-Agent Coordination", "Token-based Authentication", "Rate Limiting", "Security Logging",
		"Connection Management", "Real-time Status Updates",
	}
	actions := tmentities.NewOrderedMap[[]string]()
	actions.Set("connection_management", []string{"health_check", "server_capabilities", "connection_health", "status", "register_updates"})
	actions.Set("authentication", []string{"validate_token", "get_rate_limit_status", "revoke_token", "get_auth_status", "generate_token"})
	actions.Set("project_management", []string{"create", "get", "list", "create_tree", "get_tree_status", "orchestrate", "get_dashboard"})
	actions.Set("task_management", []string{"create", "update", "complete", "list", "search", "get_next", "add_dependency", "remove_dependency", "list_dependencies"})
	actions.Set("subtask_management", []string{"add", "update", "remove", "list"})
	actions.Set("agent_management", []string{"register", "assign", "update", "list", "get", "unassign", "unregister"})

	var enabled, mvp any = false, false
	if v, ok := s.Authentication.Get("enabled"); ok {
		enabled = v
	}
	if v, ok := s.Authentication.Get("mvp_mode"); ok {
		mvp = v
	}
	return value_objects.NewServerCapabilities(core, actions, enabled, mvp, s.Version)
}

// Restart records a server restart.
func (s *Server) Restart() {
	s.RestartCount++
	s.StartedAt = Now()
}

func (s *Server) GetEvents() []events.ConnectionEvent {
	return append([]events.ConnectionEvent{}, s.events...)
}

func (s *Server) ClearEvents() { s.events = nil }
