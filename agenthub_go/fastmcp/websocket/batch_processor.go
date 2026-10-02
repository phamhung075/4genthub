package websocket

import (
	"agenthub/fastmcp/utilities"
	"context"
	"sync"
	"sync/atomic"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// entityUpdate is one deduplicated entity update.
type entityUpdate struct {
	EntityID   any
	EntityType EntityType
	Action     ActionType
	Data       any
	Timestamp  time.Time
}

// BatchProcessor processes AI messages in 500ms batches with merging.
type BatchProcessor struct {
	Manager        *ConnectionManager
	SessionFactory SessionFactory

	BatchInterval   float64
	MaxBatchSize    int
	MaxBatchTimeout float64

	IsRunning    atomic.Bool
	CurrentBatch []*WSMessage
	BatchLock    sync.Mutex

	BatchesProcessed  int
	MessagesProcessed int
	AverageBatchSize  float64
	LastBatchTime     *time.Time

	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// NewBatchProcessor builds a batch processor with the Python defaults.
func NewBatchProcessor(manager *ConnectionManager, sessionFactory SessionFactory) *BatchProcessor {
	return &BatchProcessor{
		Manager:         manager,
		SessionFactory:  sessionFactory,
		BatchInterval:   0.5,
		MaxBatchSize:    50,
		MaxBatchTimeout: 2.0,
		CurrentBatch:    []*WSMessage{},
	}
}

// Start starts the batch processing background task.
func (b *BatchProcessor) Start(ctx context.Context) {
	if b.IsRunning.Load() {
		return
	}
	b.IsRunning.Store(true)
	loopCtx, cancel := context.WithCancel(ctx)
	b.cancel = cancel
	b.wg.Add(1)
	go func() {
		defer b.wg.Done()
		b.batchLoop(loopCtx)
	}()
}

// Stop stops the batch processing background task and processes any remaining messages.
func (b *BatchProcessor) Stop(ctx context.Context) {
	if !b.IsRunning.Load() {
		return
	}
	b.IsRunning.Store(false)
	if b.cancel != nil {
		b.cancel()
	}
	b.wg.Wait()
	b.processFinalBatch(ctx)
}

func (b *BatchProcessor) batchLoop(ctx context.Context) {
	for b.IsRunning.Load() {
		select {
		case <-ctx.Done():
			return
		case <-time.After(time.Duration(b.BatchInterval * float64(time.Second))):
		}
		utilities.SafeCall(func() { b.processBatch(ctx) })
	}
}

// processBatch processes the current batch. NOTE: current_batch is never populated in the
// Python source, so this always returns early; the queue is only drained by
// ForceProcessBatch or Stop. That quirk is preserved.
func (b *BatchProcessor) processBatch(ctx context.Context) {
	b.BatchLock.Lock()
	defer b.BatchLock.Unlock()

	if len(b.CurrentBatch) == 0 {
		return
	}

	batchStart := nowUTC()
	batchSize := len(b.CurrentBatch)

	batchMessages := b.collectBatchMessages(ctx)
	if len(batchMessages) == 0 {
		return
	}

	mergedBatch, err := b.mergeBatch(ctx, batchMessages)
	if err != nil {
		return
	}
	b.Manager.BroadcastBatch(ctx, mergedBatch)
	b.updateStats(batchSize, batchStart)
}

// collectBatchMessages collects messages from the AI batch queue.
func (b *BatchProcessor) collectBatchMessages(ctx context.Context) []*WSMessage {
	messages := []*WSMessage{}
	startTime := time.Now()

	for len(messages) < b.MaxBatchSize && time.Since(startTime).Seconds() < b.MaxBatchTimeout {
		message, ok := b.Manager.AIBatchQueue.GetTimeout(ctx, 100*time.Millisecond)
		if !ok {
			break
		}
		messages = append(messages, message)
	}
	return messages
}

// mergeBatch merges multiple AI messages into a single batch message.
func (b *BatchProcessor) mergeBatch(ctx context.Context, messages []*WSMessage) (*WSMessage, error) {
	if len(messages) == 0 {
		return nil, &value_objects.ValueError{Msg: "Cannot merge empty batch"}
	}

	entityUpdates := b.deduplicateUpdates(messages)
	batchID := value_objects.NewUUIDv4()

	updates := make([]*entities.OrderedMap[any], 0, entityUpdates.Len())
	for _, entityID := range entityUpdates.Keys() {
		updateData, _ := entityUpdates.Get(entityID)
		updates = append(updates, wsDict(
			"entity_id", updateData.EntityID,
			"entity_type", updateData.EntityType,
			"action", updateData.Action,
			"data", updateData.Data,
		))
	}

	var userID *string
	if len(messages) > 0 {
		userID = messages[0].Metadata.UserID
	}

	var calc *services.CascadeCalculator
	if b.SessionFactory != nil {
		if session, err := b.SessionFactory(); err == nil {
			calc = services.NewCascadeCalculator(session.Provider())
			defer session.Close(ctx)
		}
	}

	return CreateAIBatch(ctx, updates, batchID, calc, userID, b.Manager.NextSequence()), nil
}

// deduplicateUpdates keeps the latest update for each entity.
func (b *BatchProcessor) deduplicateUpdates(messages []*WSMessage) *entities.OrderedMap[entityUpdate] {
	entityUpdates := entities.NewOrderedMap[entityUpdate]()

	for _, message := range messages {
		payload := message.Payload
		primaryData := payload.Data.Primary

		entityID, ok := primaryEntityID(primaryData)
		if !ok || !value_objects.PyTruthy(entityID) {
			continue
		}

		entityUpdates.Set(value_objects.PyStr(entityID), entityUpdate{
			EntityID:   entityID,
			EntityType: payload.Entity,
			Action:     payload.Action,
			Data:       primaryData,
			Timestamp:  message.Timestamp,
		})
	}
	return entityUpdates
}

// processFinalBatch processes remaining messages when stopping.
func (b *BatchProcessor) processFinalBatch(ctx context.Context) {
	finalMessages := b.collectBatchMessages(ctx)
	if len(finalMessages) == 0 {
		return
	}
	mergedBatch, err := b.mergeBatch(ctx, finalMessages)
	if err != nil {
		return
	}
	b.Manager.BroadcastBatch(ctx, mergedBatch)
}

// updateStats updates batch processing statistics.
func (b *BatchProcessor) updateStats(batchSize int, batchStart time.Time) {
	b.BatchesProcessed++
	b.MessagesProcessed += batchSize
	b.LastBatchTime = &batchStart
	b.AverageBatchSize = (b.AverageBatchSize*float64(b.BatchesProcessed-1) + float64(batchSize)) / float64(b.BatchesProcessed)
}

// GetStats returns batch processor statistics.
func (b *BatchProcessor) GetStats() *entities.OrderedMap[any] {
	var lastBatchTime any
	if b.LastBatchTime != nil {
		lastBatchTime = value_objects.IsoFormat(*b.LastBatchTime)
	}
	queueSize := 0
	if b.Manager != nil {
		queueSize = b.Manager.AIBatchQueue.QSize()
	}
	return wsDict(
		"is_running", b.IsRunning.Load(),
		"batch_interval_ms", b.BatchInterval*1000,
		"max_batch_size", b.MaxBatchSize,
		"batches_processed", b.BatchesProcessed,
		"messages_processed", b.MessagesProcessed,
		"average_batch_size", value_objects.PyRound(b.AverageBatchSize, 2),
		"last_batch_time", lastBatchTime,
		"queue_size", queueSize,
	)
}

// ForceProcessBatch immediately processes the current batch.
func (b *BatchProcessor) ForceProcessBatch(ctx context.Context) (bool, error) {
	b.BatchLock.Lock()
	defer b.BatchLock.Unlock()

	messages := b.collectBatchMessages(ctx)
	if len(messages) == 0 {
		return false, nil
	}
	mergedBatch, err := b.mergeBatch(ctx, messages)
	if err != nil {
		return false, err
	}
	b.Manager.BroadcastBatch(ctx, mergedBatch)
	return true, nil
}

// ConfigureBatchParams updates batch processing parameters (interval is clamped to
// 0.1-5.0s, max size to 1-200, timeout to 0.5-10.0s).
func (b *BatchProcessor) ConfigureBatchParams(interval *float64, maxSize *int, maxTimeout *float64) {
	if interval != nil {
		b.BatchInterval = max(0.1, min(5.0, *interval))
	}
	if maxSize != nil {
		b.MaxBatchSize = max(1, min(200, *maxSize))
	}
	if maxTimeout != nil {
		b.MaxBatchTimeout = max(0.5, min(10.0, *maxTimeout))
	}
}
