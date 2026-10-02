package adapters

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/interfaces"
	infra "agenthub/fastmcp/task_management/infrastructure"
)

// stubDomainEvent is a minimal interfaces.IEvent for the adapter tests.
type stubDomainEvent struct {
	eventType   string
	eventData   map[string]any
	timestamp   time.Time
	aggregateID string
}

func (e stubDomainEvent) EventType() string         { return e.eventType }
func (e stubDomainEvent) EventData() map[string]any { return e.eventData }
func (e stubDomainEvent) Timestamp() time.Time      { return e.timestamp }
func (e stubDomainEvent) AggregateID() string       { return e.aggregateID }

// TestEventAdapterAccessors mirrors the EventAdapter property expectations read from
// event_store_adapter.py: event_type, event_data, timestamp, aggregate_id are passed
// through unchanged.
func TestEventAdapterAccessors(t *testing.T) {
	ts := time.Date(2024, 5, 1, 12, 0, 0, 0, time.UTC)
	agg := "agg-1"
	stored := infra.StoredEvent{
		EventType:   "created",
		EventData:   map[string]any{"k": "v"},
		AggregateID: &agg,
		Timestamp:   ts,
	}

	adapter := NewEventAdapter(stored)
	if got := adapter.EventType(); got != "created" {
		t.Fatalf("EventType = %q, want created", got)
	}
	if got := adapter.EventData()["k"]; got != "v" {
		t.Fatalf("EventData[k] = %v, want v", got)
	}
	if got := adapter.Timestamp(); !got.Equal(ts) {
		t.Fatalf("Timestamp = %v, want %v", got, ts)
	}
	if got := adapter.AggregateID(); got != "agg-1" {
		t.Fatalf("AggregateID = %q, want agg-1", got)
	}
}

// TestEventStoreAdapterAppendGetEvents mirrors append + get_events: an appended event
// for an aggregate is returned by get_events for that aggregate with its data intact.
func TestEventStoreAdapterAppendGetEvents(t *testing.T) {
	store := NewEventStoreAdapter()
	event := stubDomainEvent{
		eventType:   "TaskCreated",
		eventData:   map[string]any{"task_id": "t-1"},
		timestamp:   time.Now().UTC(),
		aggregateID: "t-1",
	}
	if err := store.Append("t-1", []interfaces.IEvent{event}); err != nil {
		t.Fatalf("Append error: %v", err)
	}

	events, err := store.GetEvents("t-1", 0)
	if err != nil {
		t.Fatalf("GetEvents error: %v", err)
	}
	if len(events) != 1 {
		t.Fatalf("GetEvents len = %d, want 1", len(events))
	}
	if got := events[0].EventData()["task_id"]; got != "t-1" {
		t.Fatalf("EventData[task_id] = %v, want t-1", got)
	}
	if got := events[0].AggregateID(); got != "t-1" {
		t.Fatalf("AggregateID = %q, want t-1", got)
	}

	if err := store.StoreEvent(stubDomainEvent{eventType: "x", eventData: map[string]any{}, timestamp: time.Now(), aggregateID: "t-2"}); err != nil {
		t.Fatalf("StoreEvent error: %v", err)
	}
	all, err := store.GetAllEvents(nil)
	if err != nil {
		t.Fatalf("GetAllEvents error: %v", err)
	}
	if len(all) != 2 {
		t.Fatalf("GetAllEvents len = %d, want 2", len(all))
	}
}
