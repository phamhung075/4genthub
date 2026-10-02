package interfaces

import "time"

// IEvent is the event contract (Python properties become methods).
type IEvent interface {
	EventType() string
	EventData() map[string]any
	Timestamp() time.Time
	AggregateID() string
}

// IEventStore persists events per aggregate.
type IEventStore interface {
	Append(aggregateID string, events []IEvent) error
	// GetEvents returns the aggregate's events from fromVersion (Python default 0).
	GetEvents(aggregateID string, fromVersion int) ([]IEvent, error)
	// GetAllEvents returns all events, optionally of a single type (nil = all).
	GetAllEvents(eventType *string) ([]IEvent, error)
	GetEventsByType(eventType string) ([]IEvent, error)
	StoreEvent(event IEvent) error
}
