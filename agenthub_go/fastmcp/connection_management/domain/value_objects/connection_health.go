package value_objects

import (
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ConnectionHealth is the immutable connection health status.
type ConnectionHealth struct {
	Status          string // "healthy" or "unhealthy"
	ConnectionID    string
	IdleTimeSeconds float64
	DurationSeconds float64
	ClientInfo      map[string]any
	Issues          []string
	Recommendations []string
}

// NewConnectionHealth validates the values (dataclass __post_init__).
func NewConnectionHealth(status, connectionID string, idle, duration float64, clientInfo map[string]any, issues, recommendations []string) (ConnectionHealth, error) {
	if status != "healthy" && status != "unhealthy" {
		return ConnectionHealth{}, &tmvo.ValueError{Msg: "Invalid status: " + status + ". Must be 'healthy' or 'unhealthy'"}
	}
	if idle < 0 {
		return ConnectionHealth{}, &tmvo.ValueError{Msg: "Idle time seconds cannot be negative"}
	}
	if duration < 0 {
		return ConnectionHealth{}, &tmvo.ValueError{Msg: "Duration seconds cannot be negative"}
	}
	return ConnectionHealth{status, connectionID, idle, duration, clientInfo, issues, recommendations}, nil
}

func (h ConnectionHealth) IsHealthy() bool { return h.Status == "healthy" }
func (h ConnectionHealth) HasIssues() bool { return len(h.Issues) > 0 }

func nonNil(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

func (h ConnectionHealth) ToDict() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("success", true)
	d.Set("status", h.Status)
	d.Set("connection_id", h.ConnectionID)
	d.Set("idle_time_seconds", h.IdleTimeSeconds)
	d.Set("duration_seconds", h.DurationSeconds)
	d.Set("client_info", h.ClientInfo)
	d.Set("issues", nonNil(h.Issues))
	d.Set("recommendations", nonNil(h.Recommendations))
	return d
}
