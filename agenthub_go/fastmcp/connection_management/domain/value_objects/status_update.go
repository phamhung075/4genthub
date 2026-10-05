package value_objects

import (
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Now is the clock (naive local time, microsecond resolution, like datetime.now()).
var Now = func() time.Time { return time.Now().Truncate(time.Microsecond) }

var validEventTypes = []string{
	"server_health_changed", "connection_established", "connection_lost",
	"status_broadcast", "client_registered", "client_unregistered",
}

// StatusUpdate is the immutable status update event.
type StatusUpdate struct {
	EventType string
	Timestamp time.Time
	Data      *entities.OrderedMap[any]
	SessionID string
}

// NewStatusUpdate validates the values (dataclass __post_init__).
func NewStatusUpdate(eventType string, timestamp time.Time, data *entities.OrderedMap[any], sessionID string) (StatusUpdate, error) {
	if eventType == "" {
		return StatusUpdate{}, &tmvo.ValueError{Msg: "Event type cannot be empty"}
	}
	if sessionID == "" {
		return StatusUpdate{}, &tmvo.ValueError{Msg: "Session ID cannot be empty"}
	}
	valid := false
	for _, v := range validEventTypes {
		if v == eventType {
			valid = true
		}
	}
	if !valid {
		reprs := make([]string, len(validEventTypes))
		for i, v := range validEventTypes {
			reprs[i] = tmvo.PyRepr(v)
		}
		return StatusUpdate{}, &tmvo.ValueError{Msg: "Invalid event type: " + eventType + ". Must be one of [" + strings.Join(reprs, ", ") + "]"}
	}
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	return StatusUpdate{eventType, timestamp, data, sessionID}, nil
}

func (u StatusUpdate) ToDict() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("event_type", u.EventType)
	d.Set("timestamp", tmvo.IsoFormatNaive(u.Timestamp))
	d.Set("session_id", u.SessionID)
	d.Set("data", u.Data)
	return d
}

// CreateServerHealthUpdate is the factory for server health updates; details are
// merged after health_status (equal keys replace in place).
func CreateServerHealthUpdate(sessionID, healthStatus string, details *entities.OrderedMap[any]) (StatusUpdate, error) {
	data := entities.NewOrderedMap[any]()
	data.Set("health_status", healthStatus)
	if details != nil {
		for _, k := range details.Keys() {
			v, _ := details.Get(k)
			data.Set(k, v)
		}
	}
	return NewStatusUpdate("server_health_changed", Now(), data, sessionID)
}

// CreateConnectionUpdate is the factory for connection updates (event_type "connection_<event>").
func CreateConnectionUpdate(sessionID, connectionID, event string) (StatusUpdate, error) {
	data := entities.NewOrderedMap[any]()
	data.Set("connection_id", connectionID)
	return NewStatusUpdate("connection_"+event, Now(), data, sessionID)
}

// CreateClientRegistrationUpdate is the factory for client registration updates.
func CreateClientRegistrationUpdate(sessionID string, registered bool) (StatusUpdate, error) {
	eventType := "client_unregistered"
	if registered {
		eventType = "client_registered"
	}
	return NewStatusUpdate(eventType, Now(), entities.NewOrderedMap[any](), sessionID)
}
