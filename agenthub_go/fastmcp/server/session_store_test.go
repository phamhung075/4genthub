package server

import (
	"testing"
	"time"
)

// Expectations read from Python session_store.py.

func TestSessionEventGetNumericID(t *testing.T) {
	e := &SessionEvent{EventID: "stream:12345:000002"}
	if got := e.GetNumericID(); got != 12345 {
		t.Fatalf("GetNumericID = %d, want 12345", got)
	}
	// len(parts) < 2 -> int(time.time()*1000) (positive, ms scale).
	short := &SessionEvent{EventID: "single"}
	if got := short.GetNumericID(); got <= 0 {
		t.Fatalf("GetNumericID fallback = %d, want > 0", got)
	}
}

func TestSessionEventIsExpired(t *testing.T) {
	ttl := 10.0
	notExpired := &SessionEvent{TTL: nil}
	if notExpired.IsExpired() {
		t.Fatal("nil ttl must never be expired")
	}
	longTTL := &SessionEvent{TTL: &ttl, Timestamp: zpSessionNow()}
	if longTTL.IsExpired() {
		t.Fatal("fresh event with ttl must not be expired")
	}
	old := &SessionEvent{TTL: &ttl, Timestamp: zpSessionNow() - 100}
	if !old.IsExpired() {
		t.Fatal("old event with ttl must be expired")
	}
}

func TestSessionEventToDictOrder(t *testing.T) {
	e := &SessionEvent{SessionID: "s", StreamID: "s", EventID: "s:1:000001", EventType: "message",
		EventData: nil, Timestamp: 1.5}
	want := []string{"session_id", "stream_id", "event_id", "event_type", "event_data", "timestamp", "ttl"}
	got := e.ToDict().Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
	if v, _ := e.ToDict().Get("ttl"); v != nil {
		t.Fatalf("ttl = %v, want nil", v)
	}
}

func TestMemoryEventStoreStoreAndGet(t *testing.T) {
	store := NewMemoryEventStore(3600, 2)
	id1 := store.StoreEvent("sess", map[string]any{"n": 1})
	id2 := store.StoreEvent("sess", map[string]any{"n": 2})
	id3 := store.StoreEvent("sess", map[string]any{"n": 3})
	if id1 == id2 || id2 == id3 {
		t.Fatalf("event ids must be unique: %s %s %s", id1, id2, id3)
	}
	// key uses session_id + ":stream:" + actual_stream_id.
	events := store.GetEvents("sess", strPtr("sess"), nil, 100)
	if len(events) != 2 {
		t.Fatalf("len(events) = %d, want 2 (trim to max)", len(events))
	}
	if events[0].EventData == nil {
		t.Fatal("event data must be set")
	}
}

func TestMemoryEventStoreDeleteSession(t *testing.T) {
	store := NewMemoryEventStore(3600, 1000)
	store.StoreEvent("abc", "m")
	if !store.DeleteSession("abc") {
		t.Fatal("DeleteSession = false, want true")
	}
	if got := store.GetEvents("abc", strPtr("abc"), nil, 100); len(got) != 0 {
		t.Fatalf("after delete len = %d, want 0", len(got))
	}
}

func TestReplayEventsAfter(t *testing.T) {
	store := NewMemoryEventStore(3600, 1000)
	first := store.StoreEvent("s", "m1")
	time.Sleep(2 * time.Millisecond)
	store.StoreEvent("s", "m2")
	var sent []string
	last := store.ReplayEventsAfter(first, func(m EventMessage) { sent = append(sent, m.EventID) })
	if last == nil {
		t.Fatal("lastSent = nil, want second event id")
	}
	if len(sent) != 1 {
		t.Fatalf("replayed %d, want 1", len(sent))
	}
}

func TestCreateEventStoreIsMemory(t *testing.T) {
	if _, ok := CreateEventStore(nil, true).(*MemoryEventStore); !ok {
		t.Fatal("create_event_store without Redis must return *MemoryEventStore")
	}
}

func TestSessionHealthCheckNoSession(t *testing.T) {
	CleanupGlobalEventStore()
	h := SessionHealthCheck(&Context{SessionID: ""})
	if v, _ := h.Get("overall_status"); v != "degraded" {
		t.Fatalf("overall_status = %v, want degraded", v)
	}
	if v, _ := h.Get("session_active"); v != false {
		t.Fatalf("session_active = %v, want false", v)
	}
	// warnings: no active session only (test_store not attempted without session).
	if v, _ := h.Get("warnings"); v == nil {
		t.Fatal("warnings must be present")
	}
}

func strPtr(s string) *string { return &s }
