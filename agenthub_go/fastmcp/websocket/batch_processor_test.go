package websocket

import (
	"context"
	"testing"
	"time"
)

func dedupMessage(id string, action ActionType, ts time.Time) *WSMessage {
	return &WSMessage{
		Payload:   &WSPayload{Entity: EntityTypeTask, Action: action, Data: &WSData{Primary: wsDict("id", id)}},
		Metadata:  &WSMetadata{Source: SourceTypeMCPAI},
		Timestamp: ts,
	}
}

func TestDeduplicateUpdatesKeepsLatestInFirstPosition(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	t1 := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	t2 := t1.Add(time.Second)
	messages := []*WSMessage{
		dedupMessage("t1", ActionTypeUpdate, t1),
		dedupMessage("t2", ActionTypeCreate, t2),
		dedupMessage("t1", ActionTypeDelete, t2),
	}

	updates := b.deduplicateUpdates(messages)
	if got, want := updates.Keys(), []string{"t1", "t2"}; len(got) != 2 || got[0] != want[0] || got[1] != want[1] {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	u1, _ := updates.Get("t1")
	if u1.Action != ActionTypeDelete || !u1.Timestamp.Equal(t2) {
		t.Fatalf("t1 update = %+v, want latest delete", u1)
	}
}

func TestDeduplicateUpdatesSkipsMessagesWithoutID(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	empty := &WSMessage{
		Payload:  &WSPayload{Entity: EntityTypeTask, Action: ActionTypeUpdate, Data: &WSData{Primary: wsDict("name", "x")}},
		Metadata: &WSMetadata{},
	}
	if got := b.deduplicateUpdates([]*WSMessage{empty}).Len(); got != 0 {
		t.Fatalf("deduplicated %d updates, want 0", got)
	}
}

func TestBatchProcessorGetStatsInitial(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	stats := b.GetStats()
	wantKeys := []string{"is_running", "batch_interval_ms", "max_batch_size", "batches_processed", "messages_processed", "average_batch_size", "last_batch_time", "queue_size"}
	if got := stats.Keys(); len(got) != len(wantKeys) {
		t.Fatalf("keys = %v", got)
	} else {
		for i := range wantKeys {
			if got[i] != wantKeys[i] {
				t.Fatalf("keys = %v, want %v", got, wantKeys)
			}
		}
	}
	if v, _ := stats.Get("is_running"); v != false {
		t.Errorf("is_running = %v", v)
	}
	if v, _ := stats.Get("batch_interval_ms"); v != 500.0 {
		t.Errorf("batch_interval_ms = %v", v)
	}
	if v, _ := stats.Get("max_batch_size"); v != 50 {
		t.Errorf("max_batch_size = %v", v)
	}
	if v, _ := stats.Get("last_batch_time"); v != nil {
		t.Errorf("last_batch_time = %v, want nil", v)
	}
	if v, _ := stats.Get("queue_size"); v != 0 {
		t.Errorf("queue_size = %v", v)
	}
}

func TestBatchProcessorUpdateStats(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	ts := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	b.updateStats(10, ts)
	if b.BatchesProcessed != 1 || b.MessagesProcessed != 10 || b.AverageBatchSize != 10 {
		t.Fatalf("stats after first batch: %+v", b)
	}
	b.updateStats(20, ts)
	if b.BatchesProcessed != 2 || b.MessagesProcessed != 30 || b.AverageBatchSize != 15 {
		t.Fatalf("stats after second batch: %+v", b)
	}
}

func TestBatchProcessorConfigureClamps(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	small, big := 0.01, 10.0
	smallSize, bigSize := 0, 1000
	smallTimeout, bigTimeout := 0.1, 100.0

	b.ConfigureBatchParams(&small, &smallSize, &smallTimeout)
	if b.BatchInterval != 0.1 || b.MaxBatchSize != 1 || b.MaxBatchTimeout != 0.5 {
		t.Fatalf("lower clamp: %+v", b)
	}
	b.ConfigureBatchParams(&big, &bigSize, &bigTimeout)
	if b.BatchInterval != 5.0 || b.MaxBatchSize != 200 || b.MaxBatchTimeout != 10.0 {
		t.Fatalf("upper clamp: %+v", b)
	}
	b.ConfigureBatchParams(nil, nil, nil)
	if b.BatchInterval != 5.0 {
		t.Fatalf("nil args must not change values: %+v", b)
	}
}

// TestProcessBatchSkipsWhenCurrentBatchEmpty preserves the Python quirk: current_batch is
// never populated, so the periodic task leaves the queue untouched.
func TestProcessBatchSkipsWhenCurrentBatchEmpty(t *testing.T) {
	manager := NewConnectionManager(nil)
	b := NewBatchProcessor(manager, nil)
	manager.AIBatchQueue.Put(CreateHeartbeat(nil, 1))

	b.processBatch(context.Background())
	if got := manager.AIBatchQueue.QSize(); got != 1 {
		t.Fatalf("queue size = %d, want 1 (periodic batch must not drain the queue)", got)
	}
}

func TestForceProcessBatchDrainsQueue(t *testing.T) {
	manager := NewConnectionManager(nil)
	b := NewBatchProcessor(manager, nil)
	manager.AIBatchQueue.Put(CreateHeartbeat(nil, 1))

	ok, err := b.ForceProcessBatch(context.Background())
	if err != nil {
		t.Fatalf("ForceProcessBatch: %v", err)
	}
	if !ok {
		t.Fatalf("ForceProcessBatch = false, want true")
	}
	if got := manager.AIBatchQueue.QSize(); got != 0 {
		t.Fatalf("queue size = %d, want 0", got)
	}

	ok, err = b.ForceProcessBatch(context.Background())
	if err != nil || ok {
		t.Fatalf("empty ForceProcessBatch = %v, %v; want false, nil", ok, err)
	}
}

func TestBatchProcessorStartStop(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	ctx := context.Background()
	b.Start(ctx)
	if !b.IsRunning.Load() {
		t.Fatalf("processor should be running")
	}
	b.Start(ctx) // second start is a no-op
	b.Stop(ctx)
	if b.IsRunning.Load() {
		t.Fatalf("processor should be stopped")
	}
}

func TestMergeBatchRejectsEmpty(t *testing.T) {
	b := NewBatchProcessor(NewConnectionManager(nil), nil)
	if _, err := b.mergeBatch(context.Background(), nil); err == nil {
		t.Fatalf("mergeBatch(empty) should fail")
	}
}
