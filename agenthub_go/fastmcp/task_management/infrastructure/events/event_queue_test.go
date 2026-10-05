package events

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func eventQueuePtr(f float64) *float64 { return &f }

func TestEventQueuePutGetMetrics(t *testing.T) {
	q := NewEventQueueWith(2, 0.05)
	if !q.IsEmpty() || q.IsFull() {
		t.Fatal("new queue should be empty and not full")
	}

	if ok, err := q.Put("a", true, nil); !ok || err != nil {
		t.Fatalf("Put(a) = %v, %v", ok, err)
	}
	if ok, err := q.Put("b", true, nil); !ok || err != nil {
		t.Fatalf("Put(b) = %v, %v", ok, err)
	}
	if q.Size() != 2 || !q.IsFull() {
		t.Fatalf("size=%d full=%v", q.Size(), q.IsFull())
	}

	if ok, err := q.PutNowait("c"); ok || err != nil {
		t.Fatalf("PutNowait on full = %v, %v", ok, err)
	}
	start := time.Now()
	if ok, err := q.Put("d", true, eventQueuePtr(0.02)); ok || err != nil {
		t.Fatalf("blocking Put on full = %v, %v", ok, err)
	}
	if elapsed := time.Since(start); elapsed < 15*time.Millisecond {
		t.Fatalf("blocking Put returned after %v, want >= 15ms", elapsed)
	}

	metrics := q.GetMetrics()
	if evMetric(metrics, "total_enqueued") != 2 || evMetric(metrics, "total_dropped") != 2 || evMetric(metrics, "max_size_reached") != 2 {
		t.Fatalf("metrics = %v", metrics)
	}
	if evMetric(metrics, "current_size") != 2 || evMetric(metrics, "maxsize") != 2 {
		t.Fatalf("size metrics = %v", metrics)
	}
	if evMetric(metrics, "utilization_percent") != 100.0 {
		t.Fatalf("utilization = %v", evMetric(metrics, "utilization_percent"))
	}

	if v, _ := q.GetNowait(); v != "a" {
		t.Fatalf("first dequeue = %v", v)
	}
	if v, _ := q.Get(false, nil); v != "b" {
		t.Fatalf("second dequeue = %v", v)
	}
	if v, _ := q.GetNowait(); v != nil {
		t.Fatalf("empty dequeue = %v", v)
	}
	if v, _ := q.Get(true, eventQueuePtr(0.02)); v != nil {
		t.Fatalf("blocking empty dequeue = %v", v)
	}
	if m := q.GetMetrics(); evMetric(m, "total_dequeued") != 2 || evMetric(m, "current_size") != 0 {
		t.Fatalf("dequeue metrics = %v", m)
	}
}

func TestEventQueuePauseShutdownClear(t *testing.T) {
	q := NewEventQueueWith(5, 0.01)
	_, _ = q.PutNowait("a")
	_, _ = q.PutNowait("b")
	q.Pause()
	if ok, err := q.PutNowait("c"); ok || err != nil {
		t.Fatalf("paused PutNowait = %v, %v", ok, err)
	}
	if m := q.GetMetrics(); evMetric(m, "total_dropped") != 1 {
		t.Fatalf("dropped = %v", evMetric(m, "total_dropped"))
	}
	q.Resume()
	if ok, _ := q.PutNowait("c"); !ok {
		t.Fatal("resumed PutNowait failed")
	}
	if n := q.Clear(); n != 3 {
		t.Fatalf("Clear = %d, want 3", n)
	}
	if !q.IsEmpty() {
		t.Fatal("queue not empty after Clear")
	}

	_, _ = q.PutNowait("d")
	_, _ = q.PutNowait("e")
	if remaining := q.Shutdown(false); remaining != 2 {
		t.Fatalf("Shutdown(false) = %d, want 2", remaining)
	}
	if q.State() != QueueStateShutdown {
		t.Fatalf("state = %v", q.State())
	}
	if _, err := q.PutNowait("f"); err == nil {
		t.Fatal("Put after shutdown did not raise")
	} else if _, ok := err.(*value_objects.ValueError); !ok {
		t.Fatalf("Put error type = %T", err)
	}
	if _, err := q.GetNowait(); err == nil {
		t.Fatal("Get after shutdown did not raise")
	}
	q.Resume()
	if q.State() != QueueStateShutdown {
		t.Fatal("Resume changed a shutdown queue")
	}

	q.ResetMetrics()
	if m := q.GetMetrics(); evMetric(m, "total_enqueued") != 0 || evMetric(m, "total_dropped") != 0 {
		t.Fatalf("metrics after reset = %v", m)
	}
	if repr := q.String(); repr != "EventQueue(state=shutdown, size=0/5, enqueued=0, dropped=0)" {
		t.Fatalf("String() = %q", repr)
	}
}

func evMetric(m *entities.OrderedMap[any], key string) any {
	v, _ := m.Get(key)
	return v
}

func TestEventQueueTimedGetDoesNotLoseWakeups(t *testing.T) {
	q := NewEventQueueWith(0, 0)
	d := 0.00002
	for i := 0; i < 2000; i++ {
		if v, err := q.Get(true, &d); v != nil || err != nil {
			t.Fatalf("empty queue Get = %v, %v", v, err)
		}
	}
}

func TestEventQueueNegativeTimeoutCountsError(t *testing.T) {
	q := NewEventQueueWith(5, 0.1)
	_, _ = q.Put("x", false, nil)
	neg := -1.0
	if v, _ := q.Get(true, &neg); v != nil {
		t.Fatalf("negative timeout must fail even with items, got %v", v)
	}
	if e := evMetric(q.GetMetrics(), "total_errors"); e != 1 {
		t.Fatalf("total_errors = %v", e)
	}
}
