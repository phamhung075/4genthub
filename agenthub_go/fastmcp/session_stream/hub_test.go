package session_stream

import "testing"

func TestSubscribeUnsubscribeLeavesNoSubscription(t *testing.T) {
	h := NewSessionHub()
	q := h.Subscribe("s1")
	if len(h.subs) != 1 || len(h.subs["s1"]) != 1 {
		t.Fatalf("after subscribe: %v", h.subs)
	}
	h.Unsubscribe("s1", q)
	if _, ok := h.subs["s1"]; ok {
		t.Fatalf("idle viewer leaving left a subscription: %v", h.subs)
	}
	if len(h.subs) != 0 {
		t.Fatalf("hub not empty: %v", h.subs)
	}
	// Unsubscribing an unknown session is a no-op.
	h.Unsubscribe("missing", NewQueue(QueueSize))
}

func TestPublishDeliversInOrder(t *testing.T) {
	h := NewSessionHub()
	q := h.Subscribe("s1")
	events := []any{"a", "b"}
	h.Publish("s1", events)
	if q.QSize() != 2 {
		t.Fatalf("qsize = %d, want 2", q.QSize())
	}
	for i, want := range events {
		got, ok := q.GetNowait()
		if !ok || got != want {
			t.Fatalf("event %d = %v, %v; want %v", i, got, ok, want)
		}
	}
	if q.QSize() != 0 {
		t.Fatalf("queue not drained")
	}
}

func TestPublishUnknownSessionIsNoop(t *testing.T) {
	h := NewSessionHub()
	h.Publish("nobody", []any{"x"})
	if len(h.subs) != 0 {
		t.Fatalf("publish created a subscription: %v", h.subs)
	}
}

func TestPublishOverflowDropsSlowViewer(t *testing.T) {
	h := NewSessionHub()
	q := h.Subscribe("s1")
	events := make([]any, QueueSize+1)
	for i := range events {
		events[i] = "e"
	}
	h.Publish("s1", events)

	// The dropped viewer is unsubscribed...
	if _, ok := h.subs["s1"]; ok {
		t.Fatalf("overflowing viewer was not dropped: %v", h.subs)
	}
	// ...and left with only the OVERFLOW marker.
	if q.QSize() != 1 {
		t.Fatalf("qsize after overflow = %d, want 1 (OVERFLOW)", q.QSize())
	}
	got, _ := q.GetNowait()
	if got != any(Overflow) {
		t.Fatalf("marker = %v, want Overflow", got)
	}

	// A second viewer with room is untouched.
	q2 := h.Subscribe("s2")
	h.Publish("s2", []any{"a", "b"})
	if q2.QSize() != 2 {
		t.Fatalf("q2 qsize = %d, want 2", q2.QSize())
	}
}
