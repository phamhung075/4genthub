package infrastructure

import (
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/infrastructure/events"
)

type busBaseEvent struct{ Value string }

type busDerivedEvent struct {
	busBaseEvent
	Extra string
}

func TestEventBusSubscribePublishPriorityAndMRO(t *testing.T) {
	b := NewEventBus()
	base := reflect.TypeOf(busBaseEvent{})

	var order []string
	b.Subscribe(base, "low", func(event any) { order = append(order, "low") }, 0)
	b.Subscribe(base, "high", func(event any) { order = append(order, "high") }, 10)
	b.Subscribe(base, "high2", func(event any) { order = append(order, "high2") }, 10)

	if !b.HasSubscribers(base) {
		t.Fatal("HasSubscribers = false")
	}
	if len(b.GetSubscriptions(base)) != 3 {
		t.Fatalf("GetSubscriptions = %d", len(b.GetSubscriptions(base)))
	}

	b.Publish(busBaseEvent{Value: "v"})
	if got := strings.Join(order, ","); got != "high,high2,low" {
		t.Fatalf("handler order = %q", got)
	}

	// Subscriptions to an embedded base type fire for the derived event (MRO).
	order = nil
	b.Publish(busDerivedEvent{busBaseEvent: busBaseEvent{Value: "v"}, Extra: "e"})
	if got := strings.Join(order, ","); got != "high,high2,low" {
		t.Fatalf("derived handler order = %q", got)
	}

	if !b.Unsubscribe(base, "high") {
		t.Fatal("Unsubscribe(high) = false")
	}
	if b.Unsubscribe(base, "nope") {
		t.Fatal("Unsubscribe(nope) = true")
	}
	if got := b.GetSubscriptions(base); len(got) != 2 {
		t.Fatalf("after unsubscribe GetSubscriptions = %d", len(got))
	}

	b.ClearSubscriptions(&base)
	if b.HasSubscribers(base) {
		t.Fatal("ClearSubscriptions left subscribers")
	}
}

func TestEventBusPanicIsolationAndBatch(t *testing.T) {
	b := NewEventBus()
	base := reflect.TypeOf(busBaseEvent{})
	after := false
	b.Subscribe(base, "panic", func(event any) { panic("boom") }, 5)
	b.Subscribe(base, "after", func(event any) { after = true }, 0)

	b.PublishBatch([]any{busBaseEvent{Value: "v1"}, busBaseEvent{Value: "v2"}})
	if !after {
		t.Fatal("handler after the panicking one did not run")
	}
}

func TestEventBusPublishSyncQueue(t *testing.T) {
	prev := fastmcp.Settings.EnableAsyncEventQueue
	defer func() { fastmcp.Settings.EnableAsyncEventQueue = prev }()

	b := NewEventBus()
	base := reflect.TypeOf(busBaseEvent{})
	called := 0
	b.Subscribe(base, "h", func(event any) { called++ }, 0)

	queue := events.NewEventQueueWith(10, 0.01)
	b.SetEventQueue(queue)

	fastmcp.Settings.EnableAsyncEventQueue = true
	b.PublishSync(busBaseEvent{Value: "queued"})
	if called != 0 {
		t.Fatalf("PublishSync ran handlers synchronously with the flag on (called=%d)", called)
	}
	if queue.Size() != 1 {
		t.Fatalf("queue size = %d, want 1", queue.Size())
	}
	_, _ = queue.GetNowait()

	fastmcp.Settings.EnableAsyncEventQueue = false
	b.PublishSync(busBaseEvent{Value: "sync"})
	if called != 1 {
		t.Fatalf("PublishSync did not run handlers (called=%d)", called)
	}
}

func TestEventBusQueueEvent(t *testing.T) {
	b := NewEventBus()
	base := reflect.TypeOf(busBaseEvent{})
	called := 0
	b.Subscribe(base, "h", func(event any) { called++ }, 0)

	b.QueueEvent(busBaseEvent{Value: "no-queue"})
	if called != 1 {
		t.Fatalf("QueueEvent without a queue called handlers %d times", called)
	}

	queue := events.NewEventQueueWith(10, 0.01)
	b.SetEventQueue(queue)
	b.QueueEvent(busBaseEvent{Value: "with-queue"})
	if called != 1 {
		t.Fatal("QueueEvent with a queue ran handlers synchronously")
	}
	if queue.Size() != 1 {
		t.Fatalf("queue size = %d, want 1", queue.Size())
	}
}

func TestEventBusGlobalResetAndRepr(t *testing.T) {
	ResetEventBus()
	first := GetEventBus()
	if first != GetEventBus() {
		t.Fatal("GetEventBus is not a singleton")
	}
	base := reflect.TypeOf(busBaseEvent{})
	first.Subscribe(base, "h", func(event any) {}, 0)
	if repr := first.String(); repr != "EventBus(event_types=1, total_subscriptions=1)" {
		t.Fatalf("String() = %q", repr)
	}
	ResetEventBus()
	if GetEventBus() == first {
		t.Fatal("ResetEventBus did not drop the instance")
	}
}
