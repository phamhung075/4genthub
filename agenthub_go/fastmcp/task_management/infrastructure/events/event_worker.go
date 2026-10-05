package events

import (
	"fmt"
	"reflect"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	domainevents "agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RetryBackoffSchedule mirrors RETRY_BACKOFF_SCHEDULE (seconds).
var RetryBackoffSchedule = []int{0, 1, 5, 15, 30}

// EventWorkerHandler is the Go shape of a Python handler callable. Python
// handlers signal failure by raising; Go handlers return an error.
type EventWorkerHandler func(event any) error

// EventQueueItem mirrors EventQueueItem.
type EventQueueItem struct {
	Event          any
	AttemptNumber  int
	FirstAttemptAt time.Time
	LastAttemptAt  *time.Time
	LastError      *string
}

// DeadLetterEvent mirrors DeadLetterEvent.
type DeadLetterEvent struct {
	EventID        string
	EventType      string
	Payload        map[string]any
	ErrorMessage   string
	AttemptCount   int
	FirstAttemptAt time.Time
	FinalFailureAt time.Time
}

type eventWorkerSentinel struct{}

// EventWorker mirrors EventWorker.
type EventWorker struct {
	mu                sync.Mutex
	eventHandlers     map[reflect.Type][]EventWorkerHandler
	queue             *EventQueue
	maxQueueSize      int
	running           bool
	wg                sync.WaitGroup
	heartbeatInterval int
	lastHeartbeat     *time.Time
	deadLetterQueue   []DeadLetterEvent
	stats             map[string]int
	statsMu           sync.Mutex
}

// NewEventWorker mirrors EventWorker.__init__.
func NewEventWorker(eventHandlers map[reflect.Type][]EventWorkerHandler, maxQueueSize int, heartbeatInterval int) *EventWorker {
	return &EventWorker{
		eventHandlers:     eventHandlers,
		queue:             NewEventQueueWith(maxQueueSize, 0.1),
		maxQueueSize:      maxQueueSize,
		heartbeatInterval: heartbeatInterval,
		stats: map[string]int{
			"events_processed":     0,
			"events_failed":        0,
			"events_retried":       0,
			"queue_overflow_count": 0,
		},
	}
}

// Start mirrors start.
func (w *EventWorker) Start() {
	w.mu.Lock()
	if w.running {
		w.mu.Unlock()
		return
	}
	w.running = true
	w.mu.Unlock()

	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		w.processEvents()
	}()
}

// Stop mirrors stop.
func (w *EventWorker) Stop(timeout int) {
	w.mu.Lock()
	if !w.running {
		w.mu.Unlock()
		return
	}
	w.running = false
	w.mu.Unlock()

	_, _ = w.queue.Put(eventWorkerSentinel{}, false, nil)

	done := make(chan struct{})
	go func() {
		w.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(time.Duration(timeout) * time.Second):
	}
}

// EnqueueEvent mirrors enqueue_event.
func (w *EventWorker) EnqueueEvent(event any) bool {
	now := time.Now().UTC()
	item := &EventQueueItem{Event: event, FirstAttemptAt: now}
	ok, err := w.queue.Put(item, false, nil)
	if err != nil || !ok {
		w.statsMu.Lock()
		w.stats["queue_overflow_count"]++
		w.statsMu.Unlock()
		return false
	}
	return true
}

func (w *EventWorker) isRunning() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.running
}

func (w *EventWorker) processEvents() {
	for {
		w.mu.Lock()
		running := w.running
		if running {
			now := time.Now().UTC()
			w.lastHeartbeat = &now
		}
		w.mu.Unlock()
		if !running {
			break
		}

		timeout := float64(w.heartbeatInterval)
		raw, _ := w.queue.Get(true, &timeout)
		if raw == nil {
			continue
		}
		if _, ok := raw.(eventWorkerSentinel); ok {
			break
		}
		item, ok := raw.(*EventQueueItem)
		if !ok {
			continue
		}
		w.processSingleEvent(item)
	}
	w.drainQueue()
}

func (w *EventWorker) processSingleEvent(item *EventQueueItem) {
	eventType := reflect.TypeOf(item.Event)
	handlers := w.eventHandlers[eventType]
	if len(handlers) == 0 {
		w.statsMu.Lock()
		w.stats["events_processed"]++
		w.statsMu.Unlock()
		return
	}
	for _, handler := range handlers {
		now := time.Now().UTC()
		item.LastAttemptAt = &now
		if err := eventWorkerCall(handler, item.Event); err != nil {
			msg := err.Error()
			item.LastError = &msg
			w.handleEventFailure(item, err)
		} else {
			w.statsMu.Lock()
			w.stats["events_processed"]++
			w.statsMu.Unlock()
		}
	}
}

// eventWorkerCall runs a handler converting a panic into an error, the counterpart of
// Python's `except Exception` around handler(event).
func eventWorkerCall(handler EventWorkerHandler, event any) (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("%v", r)
		}
	}()
	return handler(event)
}

func (w *EventWorker) interruptibleSleep(seconds int) bool {
	if seconds <= 0 {
		return w.isRunning()
	}
	endTime := time.Now().Add(time.Duration(seconds) * time.Second)
	for time.Now().Before(endTime) && w.isRunning() {
		remaining := time.Until(endTime)
		if remaining <= 0 {
			break
		}
		d := 100 * time.Millisecond
		if remaining < d {
			d = remaining
		}
		time.Sleep(d)
	}
	return w.isRunning()
}

func (w *EventWorker) handleEventFailure(item *EventQueueItem, err error) {
	attempt := item.AttemptNumber
	maxAttempts := len(RetryBackoffSchedule)

	if attempt < maxAttempts-1 {
		backoffDelay := RetryBackoffSchedule[attempt]
		w.statsMu.Lock()
		w.stats["events_retried"]++
		w.statsMu.Unlock()

		if backoffDelay > 0 && !w.interruptibleSleep(backoffDelay) {
			return
		}
		item.AttemptNumber++
		ok, _ := w.queue.Put(item, false, nil)
		if !ok {
			w.moveToDeadLetterQueue(item)
		}
		return
	}
	w.moveToDeadLetterQueue(item)
}

func (w *EventWorker) moveToDeadLetterQueue(item *EventQueueItem) {
	w.statsMu.Lock()
	w.stats["events_failed"]++
	w.statsMu.Unlock()

	errorMessage := "Unknown error"
	if item.LastError != nil && *item.LastError != "" {
		errorMessage = *item.LastError
	}
	dle := DeadLetterEvent{
		EventID:        eventIDString(item.Event),
		EventType:      eventTypeName(item.Event),
		Payload:        eventToDict(item.Event),
		ErrorMessage:   errorMessage,
		AttemptCount:   item.AttemptNumber + 1,
		FirstAttemptAt: item.FirstAttemptAt,
		FinalFailureAt: time.Now().UTC(),
	}

	w.mu.Lock()
	w.deadLetterQueue = append(w.deadLetterQueue, dle)
	w.mu.Unlock()
}

func (w *EventWorker) drainQueue() {
	for {
		raw, _ := w.queue.GetNowait()
		if raw == nil {
			break
		}
		if _, ok := raw.(eventWorkerSentinel); ok {
			break
		}
		item, ok := raw.(*EventQueueItem)
		if !ok {
			continue
		}
		w.processSingleEvent(item)
	}
}

// GetStats mirrors get_stats (insertion order preserved).
func (w *EventWorker) GetStats() *entities.OrderedMap[any] {
	w.statsMu.Lock()
	stats := map[string]int{}
	for k, v := range w.stats {
		stats[k] = v
	}
	w.statsMu.Unlock()

	out := entities.NewOrderedMap[any]()
	out.Set("events_processed", stats["events_processed"])
	out.Set("events_failed", stats["events_failed"])
	out.Set("events_retried", stats["events_retried"])
	out.Set("queue_overflow_count", stats["queue_overflow_count"])

	size := w.queue.Size()

	out.Set("queue_size", size)
	out.Set("queue_max_size", w.maxQueueSize)
	out.Set("is_running", w.isRunning())
	w.mu.Lock()
	heartbeat := w.lastHeartbeat
	dlqSize := len(w.deadLetterQueue)
	w.mu.Unlock()
	if heartbeat == nil {
		out.Set("last_heartbeat", nil)
	} else {
		out.Set("last_heartbeat", value_objects.IsoFormat(*heartbeat))
	}
	out.Set("dead_letter_queue_size", dlqSize)
	return out
}

// GetDeadLetterEvents mirrors get_dead_letter_events.
func (w *EventWorker) GetDeadLetterEvents() []DeadLetterEvent {
	w.mu.Lock()
	defer w.mu.Unlock()
	return append([]DeadLetterEvent{}, w.deadLetterQueue...)
}

// IsHealthy mirrors is_healthy.
func (w *EventWorker) IsHealthy() bool {
	w.mu.Lock()
	running := w.running
	heartbeat := w.lastHeartbeat
	w.mu.Unlock()
	if !running || heartbeat == nil {
		return false
	}
	timeSinceHeartbeat := time.Since(*heartbeat).Seconds()
	return timeSinceHeartbeat < float64(w.heartbeatInterval*2)
}

func eventTypeName(event any) string {
	if e, ok := event.(domainevents.Event); ok {
		return e.EventType()
	}
	if event == nil {
		return "NoneType"
	}
	return fmt.Sprintf("%T", event)
}

func eventToDict(event any) map[string]any {
	if e, ok := event.(domainevents.Event); ok {
		return e.ToDict()
	}
	return map[string]any{"event_type": eventTypeName(event)}
}

func eventIDString(event any) string {
	if event == nil {
		return "None"
	}
	v := reflect.ValueOf(event)
	if v.Kind() == reflect.Pointer {
		if v.IsNil() {
			return "None"
		}
		v = v.Elem()
	}
	if v.Kind() == reflect.Struct {
		f := v.FieldByName("EventID")
		if f.IsValid() && f.Kind() == reflect.String {
			return f.String()
		}
	}
	return fmt.Sprintf("%v", event)
}

var (
	globalWorkerMu sync.Mutex
	globalWorker   *EventWorker
)

// GetEventWorker mirrors get_event_worker.
func GetEventWorker(eventHandlers map[reflect.Type][]EventWorkerHandler, maxQueueSize int, heartbeatInterval int) (*EventWorker, error) {
	globalWorkerMu.Lock()
	defer globalWorkerMu.Unlock()
	if globalWorker == nil {
		if eventHandlers == nil {
			return nil, &value_objects.ValueError{Msg: "event_handlers required when creating EventWorker"}
		}
		globalWorker = NewEventWorker(eventHandlers, maxQueueSize, heartbeatInterval)
	}
	return globalWorker, nil
}

// ShutdownEventWorker mirrors shutdown_event_worker.
func ShutdownEventWorker(timeout int) {
	globalWorkerMu.Lock()
	defer globalWorkerMu.Unlock()
	if globalWorker != nil {
		globalWorker.Stop(timeout)
		globalWorker = nil
	}
}
