package entities

import (
	"fmt"
	"time"

	"agenthub/fastmcp/connection_management/domain/events"
	"agenthub/fastmcp/connection_management/domain/value_objects"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Now is the clock (naive local time, microsecond resolution, like datetime.now()).
var Now = func() time.Time { return time.Now().Truncate(time.Microsecond) }

// seconds is timedelta.total_seconds().
func seconds(d time.Duration) float64 { return tmvo.PyTotalSeconds(d) }

// Connection is the domain entity of a client connection.
type Connection struct {
	ConnectionID  string
	ClientInfo    map[string]any
	EstablishedAt time.Time
	LastActivity  time.Time
	Status        string
	Metadata      map[string]any

	events []events.ConnectionEvent
}

// NewConnection creates a connection with the dataclass defaults (status "active").
func NewConnection(connectionID string, clientInfo map[string]any, establishedAt, lastActivity time.Time) *Connection {
	return &Connection{
		ConnectionID: connectionID, ClientInfo: clientInfo, EstablishedAt: establishedAt,
		LastActivity: lastActivity, Status: "active", Metadata: map[string]any{},
	}
}

// CreateConnection is the factory for a new connection.
func CreateConnection(connectionID string, clientInfo map[string]any) *Connection {
	now := Now()
	return NewConnection(connectionID, clientInfo, now, now)
}

func (c *Connection) UpdateActivity() { c.LastActivity = Now() }

func (c *Connection) GetConnectionDuration() time.Duration { return Now().Sub(c.EstablishedAt) }

func (c *Connection) GetIdleTime() time.Duration { return Now().Sub(c.LastActivity) }

// IsActive: the idle time is below the threshold (Python default 30 minutes).
func (c *Connection) IsActive(activityThresholdMinutes int) bool {
	return c.GetIdleTime() < time.Duration(activityThresholdMinutes)*time.Minute
}

// DiagnoseHealth diagnoses connection health and records a ConnectionHealthChecked event.
func (c *Connection) DiagnoseHealth() (value_objects.ConnectionHealth, error) {
	idle := c.GetIdleTime()
	duration := c.GetConnectionDuration()

	healthy := true
	issues := []string{}
	recommendations := []string{}

	if idle > time.Hour {
		healthy = false
		issues = append(issues, "Connection has been idle for over 1 hour")
		recommendations = append(recommendations, "Consider reconnecting to refresh the session")
	}
	if duration > 24*time.Hour {
		issues = append(issues, "Connection has been active for over 24 hours")
		recommendations = append(recommendations, "Consider periodic reconnection for optimal performance")
	}
	if c.Status != "active" {
		healthy = false
		issues = append(issues, fmt.Sprintf("Connection status is '%s' instead of 'active'", c.Status))
		recommendations = append(recommendations, "Check client connection and network stability")
	}

	status := "unhealthy"
	if healthy {
		status = "healthy"
	}
	c.events = append(c.events, events.ConnectionHealthChecked{
		Timestamp: Now(), ConnectionID: c.ConnectionID, Status: status, IdleTimeSeconds: seconds(idle),
	})
	return value_objects.NewConnectionHealth(status, c.ConnectionID, seconds(idle), seconds(duration), c.ClientInfo, issues, recommendations)
}

func (c *Connection) Disconnect() {
	c.Status = "disconnected"
	c.UpdateActivity()
}

func (c *Connection) GetEvents() []events.ConnectionEvent {
	return append([]events.ConnectionEvent{}, c.events...)
}

func (c *Connection) ClearEvents() { c.events = nil }
