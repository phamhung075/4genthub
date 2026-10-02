package infrastructure

import (
	"testing"
	"time"
)

type storeTaskEvent struct {
	AggregateID *string
	TaskID      string
	Name        string
	At          time.Time
}

func (e storeTaskEvent) ToDict() map[string]any { return map[string]any{"name": e.Name} }

type storePlainEvent struct {
	AggregateID *string
	Title       string
	At          time.Time
}

func infraStrPtr(s string) *string { return &s }

func TestEventStoreAppendAndQuery(t *testing.T) {
	s := NewEventStore(nil)
	if s.String() != "EventStore(storage_path=':memory:')" {
		t.Fatalf("String() = %q", s.String())
	}
	custom := "events.db"
	if got := NewEventStore(&custom).String(); got != "EventStore(storage_path='events.db')" {
		t.Fatalf("String() = %q", got)
	}

	aid1, aid2 := "agg-1", "agg-2"
	id1 := s.Append(storeTaskEvent{AggregateID: &aid1, TaskID: "t1", Name: "created"})
	time.Sleep(time.Millisecond)
	id2 := s.Append(storeTaskEvent{AggregateID: &aid2, TaskID: "t2", Name: "updated"})

	if got := s.GetEventByID(id1); got == nil || got.EventData["name"] != "created" {
		t.Fatalf("GetEventByID(id1) = %v", got)
	}
	if got := s.GetEventByID("missing"); got != nil {
		t.Fatalf("GetEventByID(missing) = %v", got)
	}
	if n := s.GetEventCount(nil, nil); n != 2 {
		t.Fatalf("GetEventCount = %d, want 2", n)
	}
	if n := s.GetEventCount(&aid1, nil); n != 1 {
		t.Fatalf("GetEventCount(agg-1) = %d, want 1", n)
	}
	if n := s.GetEventCount(nil, infraStrPtr("storeTaskEvent")); n != 2 {
		t.Fatalf("GetEventCount(type) = %d, want 2", n)
	}

	all := s.GetEvents(nil, nil, nil, nil, 100)
	if len(all) != 2 || all[0].EventID != id2 || all[1].EventID != id1 {
		t.Fatalf("GetEvents order = %v", all)
	}
	if limited := s.GetEvents(nil, nil, nil, nil, 1); len(limited) != 1 || limited[0].EventID != id2 {
		t.Fatalf("GetEvents limit = %v", limited)
	}

	aggEvents := s.GetAggregateEvents(aid1, nil)
	if len(aggEvents) != 1 || aggEvents[0].EventID != id1 {
		t.Fatalf("GetAggregateEvents = %v", aggEvents)
	}
	if got := s.GetEventByID(id1); got.AggregateType == nil || *got.AggregateType != "Task" {
		t.Fatalf("inferred aggregate type = %v", got.AggregateType)
	}
}

func TestEventStoreSnapshotsAndClear(t *testing.T) {
	s := NewEventStore(nil)
	sid := s.CreateSnapshot("agg", "Project", map[string]any{"state": "ok"}, 3)
	got := s.GetLatestSnapshot("agg")
	if got == nil || got.EventID != sid || got.Version != 3 {
		t.Fatalf("GetLatestSnapshot = %v", got)
	}
	if got.EventType != "ProjectSnapshot" || got.Metadata["is_snapshot"] != true {
		t.Fatalf("snapshot record = %v", got)
	}
	time.Sleep(time.Millisecond)
	sid2 := s.CreateSnapshot("agg", "Project", map[string]any{"state": "newer"}, 4)
	if got := s.GetLatestSnapshot("agg"); got.EventID != sid2 {
		t.Fatalf("latest snapshot = %s, want %s", got.EventID, sid2)
	}
	if got := s.GetLatestSnapshot("other"); got != nil {
		t.Fatalf("GetLatestSnapshot(other) = %v", got)
	}

	s.Clear()
	if n := s.GetEventCount(nil, nil); n != 0 {
		t.Fatalf("count after Clear = %d", n)
	}
}

func TestEventStoreSerializeFallbackAndQuirks(t *testing.T) {
	s := NewEventStore(nil)
	id := s.Append(storePlainEvent{Title: "t", At: time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)})
	got := s.GetEventByID(id)
	// A present-but-None aggregate_id becomes the string "None" (str(None)).
	if got.AggregateID == nil || *got.AggregateID != "None" {
		t.Fatalf("aggregate_id = %v, want \"None\"", got.AggregateID)
	}
	if got.AggregateType != nil {
		t.Fatalf("aggregate_type = %v, want nil", got.AggregateType)
	}
	if got.EventData["Title"] != "t" {
		t.Fatalf("event_data Title = %v", got.EventData["Title"])
	}
	if at, ok := got.EventData["At"].(string); !ok || at != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("event_data At = %v", got.EventData["At"])
	}
	if got.Metadata["source"] != "event_store" || got.Version != 1 {
		t.Fatalf("metadata/version = %v/%d", got.Metadata, got.Version)
	}
}

func TestEventStoreGlobal(t *testing.T) {
	ResetEventStore()
	first := GetEventStore(nil)
	if first != GetEventStore(infraStrPtr("ignored.db")) {
		t.Fatal("GetEventStore is not a singleton")
	}
	first.Append(storeTaskEvent{Name: "n"})
	ResetEventStore()
	if GetEventStore(nil) == first {
		t.Fatal("ResetEventStore did not drop the instance")
	}
}
