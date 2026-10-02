package value_objects

import (
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ServerStatus is the immutable server status. Details keeps Python's dict order.
type ServerStatus struct {
	Status        string // "healthy" or "unhealthy"
	ServerName    string
	Version       string
	UptimeSeconds float64
	RestartCount  int
	Details       *entities.OrderedMap[any]
}

// NewServerStatus validates the values (dataclass __post_init__).
func NewServerStatus(status, serverName, version string, uptime float64, restartCount int, details *entities.OrderedMap[any]) (ServerStatus, error) {
	if status != "healthy" && status != "unhealthy" {
		return ServerStatus{}, &tmvo.ValueError{Msg: "Invalid status: " + status + ". Must be 'healthy' or 'unhealthy'"}
	}
	if uptime < 0 {
		return ServerStatus{}, &tmvo.ValueError{Msg: "Uptime seconds cannot be negative"}
	}
	if restartCount < 0 {
		return ServerStatus{}, &tmvo.ValueError{Msg: "Restart count cannot be negative"}
	}
	return ServerStatus{status, serverName, version, uptime, restartCount, details}, nil
}

func (s ServerStatus) IsHealthy() bool { return s.Status == "healthy" }

// ToDict merges Details last (`**self.details`): equal keys replace the earlier value
// in place.
func (s ServerStatus) ToDict() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("success", true)
	d.Set("status", s.Status)
	d.Set("server_name", s.ServerName)
	d.Set("version", s.Version)
	d.Set("uptime_seconds", s.UptimeSeconds)
	d.Set("restart_count", s.RestartCount)
	if s.Details != nil {
		for _, k := range s.Details.Keys() {
			v, _ := s.Details.Get(k)
			d.Set(k, v)
		}
	}
	return d
}
