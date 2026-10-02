// event_store_adapter.go ports task_management/infrastructure/adapters/event_store_adapter.py.
//
// EventAdapter adapts one stored infrastructure event to the domain IEvent contract.
// EventStoreAdapter adapts the infrastructure EventStore to the domain IEventStore.
// Python's `EventStore.__init__` default storage path is mirrored by the Go
// infrastructure.NewEventStore(nil) ":memory:" path.
package adapters

import (
	"time"

	"agenthub/fastmcp/task_management/domain/interfaces"
	infra "agenthub/fastmcp/task_management/infrastructure"
)

// EventAdapter is event_store_adapter.EventAdapter.
type EventAdapter struct {
	event infra.StoredEvent
}

// NewEventAdapter wraps an infrastructure event.
func NewEventAdapter(event infra.StoredEvent) *EventAdapter {
	return &EventAdapter{event: event}
}

// EventType is the event_type property.
func (a *EventAdapter) EventType() string { return a.event.EventType }

// EventData is the event_data property.
func (a *EventAdapter) EventData() map[string]any { return a.event.EventData }

// Timestamp is the timestamp property.
func (a *EventAdapter) Timestamp() time.Time { return a.event.Timestamp }

// AggregateID is the aggregate_id property. Python can hold None; the Go interface
// returns a string, so a nil aggregate id becomes the empty string.
func (a *EventAdapter) AggregateID() string {
	if a.event.AggregateID == nil {
		return ""
	}
	return *a.event.AggregateID
}

// EventStoreAdapter is event_store_adapter.EventStoreAdapter.
type EventStoreAdapter struct {
	eventStore *infra.EventStore
}

// NewEventStoreAdapter mirrors EventStoreAdapter.__init__ (EventStore()).
func NewEventStoreAdapter() *EventStoreAdapter {
	return &EventStoreAdapter{eventStore: infra.NewEventStore(nil)}
}

// eventStoreRecord carries a domain event into the infrastructure store. The Python
// adapter constructs an infrastructure Event with exactly these fields; the Go
// infrastructure store persists a StoredEvent built from them.
type eventStoreRecord struct {
	EventType   string
	EventData   map[string]any
	AggregateID string
	Timestamp   time.Time
}

// ToDict is consulted by the infrastructure EventStore serializer, so the stored
// event_data is the original domain event data rather than the record fields.
func (r eventStoreRecord) ToDict() map[string]any { return r.EventData }

// Append is append: it stores each domain event under the aggregate id. The
// infrastructure EventStore.Append derives the aggregate id from the passed value, so
// the record carries the caller's aggregate id.
func (a *EventStoreAdapter) Append(aggregateID string, events []interfaces.IEvent) error {
	for _, event := range events {
		a.eventStore.Append(eventStoreRecord{
			EventType:   event.EventType(),
			EventData:   event.EventData(),
			AggregateID: aggregateID,
			Timestamp:   event.Timestamp(),
		})
	}
	return nil
}

// GetEvents is get_events: events for an aggregate from from_version.
func (a *EventStoreAdapter) GetEvents(aggregateID string, fromVersion int) ([]interfaces.IEvent, error) {
	stored := a.eventStore.GetAggregateEvents(aggregateID, &fromVersion)
	return wrapStoredEvents(stored), nil
}

// GetAllEvents is get_all_events: all events, optionally filtered by type.
func (a *EventStoreAdapter) GetAllEvents(eventType *string) ([]interfaces.IEvent, error) {
	stored := a.eventStore.GetEvents(nil, eventType, nil, nil, -1)
	return wrapStoredEvents(stored), nil
}

// GetEventsByType is get_events_by_type.
func (a *EventStoreAdapter) GetEventsByType(eventType string) ([]interfaces.IEvent, error) {
	stored := a.eventStore.GetEvents(nil, &eventType, nil, nil, -1)
	return wrapStoredEvents(stored), nil
}

// StoreEvent is store_event: store a single event.
func (a *EventStoreAdapter) StoreEvent(event interfaces.IEvent) error {
	a.eventStore.Append(eventStoreRecord{
		EventType:   event.EventType(),
		EventData:   event.EventData(),
		AggregateID: event.AggregateID(),
		Timestamp:   event.Timestamp(),
	})
	return nil
}

func wrapStoredEvents(stored []infra.StoredEvent) []interfaces.IEvent {
	out := make([]interfaces.IEvent, 0, len(stored))
	for _, event := range stored {
		out = append(out, NewEventAdapter(event))
	}
	return out
}
