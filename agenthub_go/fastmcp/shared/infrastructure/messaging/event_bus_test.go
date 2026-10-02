package messaging

import (
	"errors"
	"reflect"
	"sync"
	"testing"
	"time"
)

type testMsgEvent struct {
	DomainEvent
	Payload string
}

func newTestMsgEvent(payload string) *testMsgEvent {
	return &testMsgEvent{DomainEvent: NewDomainEvent(), Payload: payload}
}

func TestEventMetadataDefaultsAndEventName(t *testing.T) {
	m := NewEventMetadata()
	if len(m.EventID) != 36 {
		t.Fatalf("EventID = %q", m.EventID)
	}
	if m.Priority != EventPriorityNormal || m.MaxRetries != 3 || m.RetryCount != 0 {
		t.Fatalf("metadata = %+v", m)
	}
	if m.Timestamp.IsZero() {
		t.Fatal("Timestamp is zero")
	}

	if got := EventName(&testMsgEvent{}); got != "testMsgEvent" {
		t.Fatalf("EventName = %q", got)
	}
	if got := EventName(DomainEvent{}); got != "DomainEvent" {
		t.Fatalf("EventName(DomainEvent) = %q", got)
	}
	if got := (&DomainEvent{}).GetEventName(); got != "DomainEvent" {
		t.Fatalf("GetEventName = %q", got)
	}
}

func TestEventHandlerFilterAndErrors(t *testing.T) {
	reject := func(event any) bool { return false }
	calls := 0
	h := &EventHandler{Name: "h", Handler: func(event any) (any, error) { calls++; return "ok", nil }, FilterFunc: reject}
	if result, err := h.Handle("x"); result != nil || err != nil {
		t.Fatalf("filtered Handle = %v, %v", result, err)
	}
	if h.CallCount != 0 || calls != 0 {
		t.Fatal("filtered handler was invoked")
	}

	h.FilterFunc = nil
	result, err := h.Handle("x")
	if result != "ok" || err != nil || h.CallCount != 1 || h.ErrorCount != 0 {
		t.Fatalf("Handle = %v, %v calls=%d errors=%d", result, err, h.CallCount, h.ErrorCount)
	}
	if h.AvgDurationMs() < 0 {
		t.Fatalf("AvgDurationMs = %v", h.AvgDurationMs())
	}

	failing := &EventHandler{Name: "f", Handler: func(event any) (any, error) { return nil, errors.New("boom") }}
	if _, err := failing.Handle("x"); err == nil || failing.ErrorCount != 1 || failing.CallCount != 1 {
		t.Fatalf("failing handler = %v errors=%d", err, failing.ErrorCount)
	}
	zero := &EventHandler{Name: "z"}
	if zero.AvgDurationMs() != 0 {
		t.Fatalf("AvgDurationMs with no calls = %v", zero.AvgDurationMs())
	}
}

func TestEventBusProcessesEventsWithPriority(t *testing.T) {
	b := NewEventBusWith(100, true, 2)
	eventType := reflect.TypeOf(testMsgEvent{})

	var mu sync.Mutex
	var order []string
	b.Subscribe(eventType, "low", func(event any) (any, error) {
		mu.Lock()
		order = append(order, "low")
		mu.Unlock()
		return nil, nil
	}, nil, 0)
	b.Subscribe(eventType, "high", func(event any) (any, error) {
		mu.Lock()
		order = append(order, "high")
		mu.Unlock()
		return nil, nil
	}, nil, 10)
	b.Subscribe(eventType, "filtered", func(event any) (any, error) {
		mu.Lock()
		order = append(order, "filtered")
		mu.Unlock()
		return nil, nil
	}, func(event any) bool { return false }, 99)

	b.Start()
	b.Publish(newTestMsgEvent("one"), EventPriorityHigh, nil, nil)
	timeout := 2.0
	if !b.WaitForEmptyQueue(&timeout) {
		t.Fatal("WaitForEmptyQueue timed out")
	}
	b.Stop()

	mu.Lock()
	got := order
	mu.Unlock()
	if len(got) != 2 || got[0] != "high" || got[1] != "low" {
		t.Fatalf("handler order = %v", got)
	}
	metrics := b.GetMetrics()
	if metrics["events_published"] != 1 || metrics["events_processed"] != 1 || metrics["events_failed"] != 0 {
		t.Fatalf("metrics = %v", metrics)
	}
}

func TestEventBusDeadLetterQueueAndReplay(t *testing.T) {
	b := NewEventBusWith(100, true, 1)
	eventType := reflect.TypeOf(testMsgEvent{})

	shouldFail := true
	b.Subscribe(eventType, "flaky", func(event any) (any, error) {
		if shouldFail {
			return nil, errors.New("nope")
		}
		return "ok", nil
	}, nil, 0)

	event := newTestMsgEvent("dlq")
	event.Metadata.MaxRetries = 0

	b.Start()
	b.Publish(event, EventPriorityNormal, nil, nil)
	timeout := 2.0
	if !b.WaitForEmptyQueue(&timeout) {
		t.Fatal("WaitForEmptyQueue timed out")
	}
	dlq := b.GetDeadLetterQueue()
	if len(dlq) != 1 || dlq[0].Error == nil {
		t.Fatalf("dead letter queue = %v", dlq)
	}
	if metrics := b.GetMetrics(); metrics["events_failed"] != 1 || metrics["dead_letter_size"] != 1 {
		t.Fatalf("metrics = %v", metrics)
	}
	if name, ok := b.GetMetrics()["handler_errors"].(map[string]any); !ok || name["flaky"] != 1 {
		t.Fatalf("handler_errors = %v", b.GetMetrics()["handler_errors"])
	}

	shouldFail = false
	if replayed := b.ReplayDeadLetterQueue(); replayed != 1 {
		t.Fatalf("ReplayDeadLetterQueue = %d, want 1", replayed)
	}
	if !b.WaitForEmptyQueue(&timeout) {
		t.Fatal("WaitForEmptyQueue after replay timed out")
	}
	b.Stop()
	if got := b.GetDeadLetterQueue(); len(got) != 0 {
		t.Fatalf("dead letter queue after replay = %v", got)
	}

	if n := b.ClearDeadLetterQueue(); n != 0 {
		t.Fatalf("ClearDeadLetterQueue = %d, want 0", n)
	}
}

func TestEventBusSubscribeAllUnsubscribeAndMetrics(t *testing.T) {
	b := NewEventBusWith(100, true, 1)
	eventType := reflect.TypeOf(testMsgEvent{})
	b.Subscribe(eventType, "specific", func(event any) (any, error) { return nil, nil }, nil, 5)
	b.SubscribeAll("global", func(event any) (any, error) { return nil, nil }, nil, 0)

	handlers := b.GetHandlersForEvent(eventType)
	if len(handlers) != 2 || handlers[0].Name != "specific" || handlers[1].Name != "global" {
		t.Fatalf("handlers = %v", handlers)
	}

	metrics := b.GetMetrics()
	if metrics["handler_count"] != 2 || metrics["event_types"] != 1 {
		t.Fatalf("metrics = %v", metrics)
	}
	handlerMetrics, ok := metrics["handler_metrics"].(map[string]any)
	if !ok || handlerMetrics["testMsgEvent.specific"] == nil {
		t.Fatalf("handler_metrics = %v", metrics["handler_metrics"])
	}

	if !b.Unsubscribe(eventType, "specific") {
		t.Fatal("Unsubscribe = false")
	}
	if b.Unsubscribe(eventType, "missing") {
		t.Fatal("Unsubscribe(missing) = true")
	}
	if got := b.GetHandlersForEvent(eventType); len(got) != 1 || got[0].Name != "global" {
		t.Fatalf("handlers after unsubscribe = %v", got)
	}
}

func TestEventBusGlobalAndWaitTimeout(t *testing.T) {
	a := NewEventBusWith(10, true, 1)
	SetEventBus(a)
	if GetEventBus() != a {
		t.Fatal("SetEventBus did not replace the global")
	}
	b := NewEventBusWith(10, true, 1)
	SetEventBus(b)
	if GetEventBus() != b {
		t.Fatal("GetEventBus returned the old instance")
	}

	// No events pending: WaitForEmptyQueue returns immediately; a queue with an event and
	// no workers times out.
	timeout := 0.05
	if !b.WaitForEmptyQueue(&timeout) {
		t.Fatal("WaitForEmptyQueue on an empty queue returned false")
	}
	b.enqueue(newTestMsgEvent("stuck"))
	start := time.Now()
	if b.WaitForEmptyQueue(&timeout) {
		t.Fatal("WaitForEmptyQueue returned true with a pending event and no workers")
	}
	if time.Since(start) < 40*time.Millisecond {
		t.Fatalf("WaitForEmptyQueue returned after %v", time.Since(start))
	}
}
