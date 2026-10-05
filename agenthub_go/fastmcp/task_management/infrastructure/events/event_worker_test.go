package events

import (
	"errors"
	"reflect"
	"sync/atomic"
	"testing"
	"time"

	domainevents "agenthub/fastmcp/task_management/domain/events"
)

type workerTestEvent struct {
	domainevents.BaseDomainEvent
	Value string `dict:"value"`
}

func (e workerTestEvent) EventType() string { return "worker_test" }
func (e workerTestEvent) ToDict() map[string]any {
	return domainevents.EventToDict(e, "worker_test")
}

func TestEventWorkerProcessesAndStatsOrder(t *testing.T) {
	var seen atomic.Int32
	handlers := map[reflect.Type][]EventWorkerHandler{
		reflect.TypeOf(workerTestEvent{}): {func(event any) error {
			seen.Add(1)
			return nil
		}},
	}
	w := NewEventWorker(handlers, 100, 1)
	w.Start()
	if !w.EnqueueEvent(workerTestEvent{BaseDomainEvent: domainevents.NewBaseDomainEvent(), Value: "x"}) {
		t.Fatal("enqueue failed")
	}
	deadline := time.Now().Add(3 * time.Second)
	for seen.Load() == 0 && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	w.Stop(30)
	if seen.Load() != 1 {
		t.Fatalf("seen = %d", seen.Load())
	}
	stats := w.GetStats()
	got := stats.Keys()
	want := []string{"events_processed", "events_failed", "events_retried", "queue_overflow_count", "queue_size", "queue_max_size", "is_running", "last_heartbeat", "dead_letter_queue_size"}
	if len(got) != len(want) {
		t.Fatalf("keys = %v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("key[%d] = %q want %q", i, got[i], want[i])
		}
	}
	if v, _ := stats.Get("events_processed"); v != 1 {
		t.Fatalf("events_processed = %v", v)
	}
	if v, _ := stats.Get("queue_max_size"); v != 100 {
		t.Fatalf("queue_max_size = %v", v)
	}
}

func TestEventWorkerDeadLetterFields(t *testing.T) {
	handlers := map[reflect.Type][]EventWorkerHandler{
		reflect.TypeOf(workerTestEvent{}): {func(event any) error { return errors.New("boom") }},
	}
	w := NewEventWorker(handlers, 10, 1)
	msg := "boom"
	t0 := time.Now().UTC()
	ev := workerTestEvent{BaseDomainEvent: domainevents.NewBaseDomainEvent(), Value: "y"}
	w.moveToDeadLetterQueue(&EventQueueItem{
		Event:          ev,
		AttemptNumber:  4,
		FirstAttemptAt: t0,
		LastError:      &msg,
	})
	dle := w.GetDeadLetterEvents()
	if len(dle) != 1 {
		t.Fatalf("dlq len = %d", len(dle))
	}
	if dle[0].EventID != ev.EventID || dle[0].EventType != "worker_test" {
		t.Fatalf("dle = %+v", dle[0])
	}
	if dle[0].AttemptCount != 5 || dle[0].ErrorMessage != "boom" {
		t.Fatalf("dle = %+v", dle[0])
	}
	if dle[0].Payload["value"] != "y" {
		t.Fatalf("payload = %+v", dle[0].Payload)
	}
}

func TestEventWorkerHandlerPanicIsRetriedAndDeadLettered(t *testing.T) {
	handlers := map[reflect.Type][]EventWorkerHandler{
		reflect.TypeOf(workerTestEvent{}): {func(event any) error {
			var m map[string]int
			m["a"] = 1
			return nil
		}},
	}
	w := NewEventWorker(handlers, 100, 1)
	item := &EventQueueItem{Event: workerTestEvent{BaseDomainEvent: domainevents.NewBaseDomainEvent()}}
	w.processSingleEvent(item)
	if item.LastError == nil || *item.LastError == "" {
		t.Fatal("a handler panic must be recorded as the failure")
	}
	empty := ""
	item.LastError = &empty
	w.moveToDeadLetterQueue(item)
	dlq := w.GetDeadLetterEvents()
	if len(dlq) != 1 || dlq[0].ErrorMessage != "Unknown error" {
		t.Fatalf("empty error text must become Unknown error: %+v", dlq)
	}
}
