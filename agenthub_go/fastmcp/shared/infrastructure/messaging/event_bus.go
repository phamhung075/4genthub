// Package messaging ports shared/infrastructure/messaging.
package messaging

import (
	"agenthub/fastmcp/utilities"
	"fmt"
	"math"
	"reflect"
	"sort"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// EventPriority enumerates event priority levels (event_bus.EventPriority).
type EventPriority int

const (
	EventPriorityLow      EventPriority = 1
	EventPriorityNormal   EventPriority = 2
	EventPriorityHigh     EventPriority = 3
	EventPriorityCritical EventPriority = 4
)

// EventMetadata is metadata for published events (event_bus.EventMetadata).
type EventMetadata struct {
	EventID       string
	Timestamp     time.Time
	Source        *string
	UserID        *string
	CorrelationID *string
	Priority      EventPriority
	RetryCount    int
	MaxRetries    int
}

// NewEventMetadata applies the Python dataclass defaults.
func NewEventMetadata() EventMetadata {
	return EventMetadata{
		EventID:    value_objects.NewUUIDv4(),
		Timestamp:  time.Now().UTC().Truncate(time.Microsecond),
		Priority:   EventPriorityNormal,
		MaxRetries: 3,
	}
}

// DomainEvent is the base domain event (event_bus.DomainEvent). Embed it in concrete
// events; because Go methods promoted from an embedded value cannot see the outer type,
// the event bus derives the event name from the concrete Go type rather than from
// GetEventName.
type DomainEvent struct {
	Metadata EventMetadata
}

// NewDomainEvent creates a base event with fresh metadata.
func NewDomainEvent() DomainEvent { return DomainEvent{Metadata: NewEventMetadata()} }

// GetMetadata exposes the event metadata.
func (e *DomainEvent) GetMetadata() *EventMetadata { return &e.Metadata }

// GetEventName is DomainEvent.get_event_name.
func (e DomainEvent) GetEventName() string { return EventName(e) }

// EventName is the dynamic class name of an event, i.e. Python's self.__class__.__name__.
func EventName(event any) string {
	t := reflect.TypeOf(event)
	for t != nil && t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	if t == nil {
		return ""
	}
	return t.Name()
}

// HandlerFunc is a Go event handler. The error return replaces the Python exception.
type HandlerFunc func(event any) (any, error)

// EventHandler wraps a handler with metadata (event_bus.EventHandler). Go funcs are not
// comparable, so Name identifies a handler.
type EventHandler struct {
	Name            string
	Handler         HandlerFunc
	EventType       reflect.Type
	FilterFunc      func(event any) bool
	Priority        int
	IsAsync         bool
	CallCount       int
	ErrorCount      int
	TotalDurationMs float64
}

// Handle mirrors EventHandler.handle; a nil result is returned when the filter rejects
// the event.
func (h *EventHandler) Handle(event any) (any, error) {
	if h.FilterFunc != nil && !h.FilterFunc(event) {
		return nil, nil
	}
	start := time.Now()
	h.CallCount++

	result, err := h.Handler(event)
	if err != nil {
		h.ErrorCount++
		return nil, err
	}
	h.TotalDurationMs += float64(time.Since(start).Microseconds()) / 1000.0
	return result, nil
}

// AvgDurationMs is EventHandler.avg_duration_ms.
func (h *EventHandler) AvgDurationMs() float64 {
	if h.CallCount == 0 {
		return 0
	}
	return h.TotalDurationMs / float64(h.CallCount)
}

// DeadLetterEntry is a failed (event, error) pair.
type DeadLetterEntry struct {
	Event any
	Error error
}

type busMetrics struct {
	EventsPublished int
	EventsProcessed int
	EventsFailed    int
	EventsRetried   int
	QueueSize       int
	DeadLetterSize  int
	HandlerErrors   map[string]int
}

// EventBus is the centralized domain event bus
// (event_bus.EventBus). Go goroutines replace asyncio workers.
type EventBus struct {
	MaxQueueSize          int
	EnableDeadLetterQueue bool
	WorkerCount           int

	mu             sync.Mutex
	handlers       map[reflect.Type][]*EventHandler
	globalHandlers []*EventHandler

	queue     chan any
	pending   sync.WaitGroup
	stopCh    chan struct{}
	workersWG sync.WaitGroup
	runMu     sync.Mutex
	isRunning bool

	dlqMu           sync.Mutex
	deadLetterQueue []DeadLetterEntry

	metricsMu sync.Mutex
	metrics   busMetrics
}

// NewEventBus applies the Python constructor defaults
// (max_queue_size=10000, enable_dead_letter_queue=True, worker_count=4).
func NewEventBus() *EventBus { return NewEventBusWith(10000, true, 4) }

// NewEventBusWith mirrors EventBus(max_queue_size, enable_dead_letter_queue, worker_count).
func NewEventBusWith(maxQueueSize int, enableDeadLetterQueue bool, workerCount int) *EventBus {
	if maxQueueSize < 0 {
		maxQueueSize = 0
	}
	return &EventBus{
		MaxQueueSize:          maxQueueSize,
		EnableDeadLetterQueue: enableDeadLetterQueue,
		WorkerCount:           workerCount,
		handlers:              map[reflect.Type][]*EventHandler{},
		queue:                 make(chan any, maxQueueSize),
		metrics:               busMetrics{HandlerErrors: map[string]int{}},
	}
}

// Start mirrors EventBus.start.
func (b *EventBus) Start() {
	b.runMu.Lock()
	if b.isRunning {
		b.runMu.Unlock()
		return
	}
	b.isRunning = true
	b.stopCh = make(chan struct{})
	stop := b.stopCh
	b.runMu.Unlock()

	for i := 0; i < b.WorkerCount; i++ {
		b.workersWG.Add(1)
		go b.processEvents(fmt.Sprintf("worker-%d", i), stop)
	}
}

// Stop mirrors EventBus.stop: it waits for the queue to empty then stops the workers.
func (b *EventBus) Stop() {
	b.runMu.Lock()
	if !b.isRunning {
		b.runMu.Unlock()
		return
	}
	b.isRunning = false
	stop := b.stopCh
	b.runMu.Unlock()

	b.pending.Wait()
	close(stop)
	b.workersWG.Wait()
}

func (b *EventBus) processEvents(workerName string, stop chan struct{}) {
	defer b.workersWG.Done()
	for {
		select {
		case <-stop:
			return
		case event := <-b.queue:
			// the worker loop catches Exception per event in Python
			utilities.SafeCall(func() { b.handleEvent(event) })
			b.pending.Done()
			b.metricsMu.Lock()
			b.metrics.QueueSize = len(b.queue)
			b.metricsMu.Unlock()
		}
	}
}

// enqueue adds an event to the queue, counting it as pending.
func (b *EventBus) enqueue(event any) {
	b.pending.Add(1)
	b.queue <- event
}

// Subscribe mirrors EventBus.subscribe; name replaces the Python callable identity.
func (b *EventBus) Subscribe(eventType reflect.Type, name string, handler HandlerFunc, filterFunc func(event any) bool, priority int) string {
	wrapper := &EventHandler{Name: name, Handler: handler, EventType: eventType, FilterFunc: filterFunc, Priority: priority}
	b.mu.Lock()
	b.handlers[eventType] = append(b.handlers[eventType], wrapper)
	sort.SliceStable(b.handlers[eventType], func(i, j int) bool {
		return b.handlers[eventType][i].Priority > b.handlers[eventType][j].Priority
	})
	b.mu.Unlock()
	return eventType.Name() + "_" + name
}

// SubscribeAll mirrors EventBus.subscribe_all.
func (b *EventBus) SubscribeAll(name string, handler HandlerFunc, filterFunc func(event any) bool, priority int) string {
	wrapper := &EventHandler{Name: name, Handler: handler, EventType: reflect.TypeOf(DomainEvent{}), FilterFunc: filterFunc, Priority: priority}
	b.mu.Lock()
	b.globalHandlers = append(b.globalHandlers, wrapper)
	sort.SliceStable(b.globalHandlers, func(i, j int) bool {
		return b.globalHandlers[i].Priority > b.globalHandlers[j].Priority
	})
	b.mu.Unlock()
	return "global_" + name
}

// Unsubscribe mirrors EventBus.unsubscribe, matching handlers by name.
func (b *EventBus) Unsubscribe(eventType reflect.Type, name string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	handlers, ok := b.handlers[eventType]
	if !ok {
		return false
	}
	originalCount := len(handlers)
	kept := handlers[:0:0]
	for _, h := range handlers {
		if h.Name != name {
			kept = append(kept, h)
		}
	}
	if len(kept) == 0 {
		delete(b.handlers, eventType)
	}
	if len(kept) > 0 {
		b.handlers[eventType] = kept
	}
	return len(kept) < originalCount
}

// Publish mirrors EventBus.publish. In Go the metadata update happens in place and the
// event is queued; QueueFull cannot occur because the send blocks like asyncio.Queue.put.
func (b *EventBus) Publish(event any, priority EventPriority, correlationID, userID *string) {
	if m := eventMetadata(event); m != nil {
		m.Priority = priority
		if correlationID != nil && *correlationID != "" {
			m.CorrelationID = correlationID
		}
		if userID != nil && *userID != "" {
			m.UserID = userID
		}
	}
	b.enqueue(event)
	b.metricsMu.Lock()
	b.metrics.EventsPublished++
	b.metrics.QueueSize = len(b.queue)
	b.metricsMu.Unlock()
}

// PublishBatch mirrors EventBus.publish_batch.
func (b *EventBus) PublishBatch(events []any, priority EventPriority) {
	for _, event := range events {
		b.Publish(event, priority, nil, nil)
	}
}

func (b *EventBus) handleEvent(event any) {
	eventType := normalizeEventType(reflect.TypeOf(event))
	handlers := b.GetHandlersForEvent(eventType)
	if len(handlers) == 0 {
		return
	}

	var errors []DeadLetterEntry
	for _, handler := range handlers {
		if _, err := handler.Handle(event); err != nil {
			b.metricsMu.Lock()
			b.metrics.HandlerErrors[handler.Name]++
			b.metricsMu.Unlock()
			errors = append(errors, DeadLetterEntry{Event: event, Error: err})
		}
	}

	if len(errors) > 0 {
		b.metricsMu.Lock()
		b.metrics.EventsFailed++
		b.metricsMu.Unlock()

		if m := eventMetadata(event); m != nil && m.RetryCount < m.MaxRetries {
			m.RetryCount++
			b.metricsMu.Lock()
			b.metrics.EventsRetried++
			b.metricsMu.Unlock()
			time.Sleep(time.Duration(math.Pow(2, float64(m.RetryCount))) * time.Second)
			b.enqueue(event)
		} else if b.EnableDeadLetterQueue {
			b.dlqMu.Lock()
			b.deadLetterQueue = append(b.deadLetterQueue, errors...)
			size := len(b.deadLetterQueue)
			b.dlqMu.Unlock()
			b.metricsMu.Lock()
			b.metrics.DeadLetterSize = size
			b.metricsMu.Unlock()
		}
	} else {
		b.metricsMu.Lock()
		b.metrics.EventsProcessed++
		b.metricsMu.Unlock()
	}
}

// GetHandlersForEvent mirrors EventBus.get_handlers_for_event.
func (b *EventBus) GetHandlersForEvent(eventType reflect.Type) []*EventHandler {
	b.mu.Lock()
	var handlers []*EventHandler
	handlers = append(handlers, b.handlers[eventType]...)
	handlers = append(handlers, b.globalHandlers...)
	b.mu.Unlock()
	sort.SliceStable(handlers, func(i, j int) bool { return handlers[i].Priority > handlers[j].Priority })
	return handlers
}

// GetDeadLetterQueue mirrors EventBus.get_dead_letter_queue.
func (b *EventBus) GetDeadLetterQueue() []DeadLetterEntry {
	b.dlqMu.Lock()
	defer b.dlqMu.Unlock()
	out := make([]DeadLetterEntry, len(b.deadLetterQueue))
	copy(out, b.deadLetterQueue)
	return out
}

// ClearDeadLetterQueue mirrors EventBus.clear_dead_letter_queue.
func (b *EventBus) ClearDeadLetterQueue() int {
	b.dlqMu.Lock()
	count := len(b.deadLetterQueue)
	b.deadLetterQueue = nil
	b.dlqMu.Unlock()
	b.metricsMu.Lock()
	b.metrics.DeadLetterSize = 0
	b.metricsMu.Unlock()
	return count
}

// ReplayDeadLetterQueue mirrors EventBus.replay_dead_letter_queue.
func (b *EventBus) ReplayDeadLetterQueue() int {
	b.dlqMu.Lock()
	events := make([]DeadLetterEntry, len(b.deadLetterQueue))
	copy(events, b.deadLetterQueue)
	b.deadLetterQueue = nil
	b.dlqMu.Unlock()

	replayed := 0
	for _, entry := range events {
		if m := eventMetadata(entry.Event); m != nil {
			m.RetryCount = 0
		}
		b.Publish(entry.Event, EventPriorityNormal, nil, nil)
		replayed++
	}
	return replayed
}

// GetMetrics mirrors EventBus.get_metrics.
func (b *EventBus) GetMetrics() map[string]any {
	b.mu.Lock()
	handlerMetrics := map[string]any{}
	for eventType, handlers := range b.handlers {
		for _, handler := range handlers {
			name := eventType.Name() + "." + handler.Name
			handlerMetrics[name] = map[string]any{
				"calls": handler.CallCount, "errors": handler.ErrorCount, "avg_duration_ms": handler.AvgDurationMs(),
			}
		}
	}
	handlerCount := len(b.globalHandlers)
	for _, handlers := range b.handlers {
		handlerCount += len(handlers)
	}
	eventTypes := len(b.handlers)
	b.mu.Unlock()

	b.metricsMu.Lock()
	m := b.metrics
	handlerErrors := map[string]any{}
	for name, count := range m.HandlerErrors {
		handlerErrors[name] = count
	}
	b.metricsMu.Unlock()

	return map[string]any{
		"events_published": m.EventsPublished, "events_processed": m.EventsProcessed,
		"events_failed": m.EventsFailed, "events_retried": m.EventsRetried,
		"queue_size": m.QueueSize, "dead_letter_size": m.DeadLetterSize,
		"handler_errors": handlerErrors, "handler_count": handlerCount,
		"event_types": eventTypes, "handler_metrics": handlerMetrics,
	}
}

// WaitForEmptyQueue mirrors EventBus.wait_for_empty_queue.
func (b *EventBus) WaitForEmptyQueue(timeout *float64) bool {
	done := make(chan struct{})
	go func() {
		b.pending.Wait()
		close(done)
	}()
	if timeout == nil {
		<-done
		return true
	}
	select {
	case <-done:
		return true
	case <-time.After(time.Duration(*timeout * float64(time.Second))):
		return false
	}
}

func normalizeEventType(t reflect.Type) reflect.Type {
	for t != nil && t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	return t
}

func eventMetadata(event any) *EventMetadata {
	if m, ok := event.(interface{ GetMetadata() *EventMetadata }); ok {
		return m.GetMetadata()
	}
	return nil
}

var (
	eventBusMu     sync.Mutex
	eventBusGlobal *EventBus
)

// GetEventBus returns the global event bus, creating it on first use.
func GetEventBus() *EventBus {
	eventBusMu.Lock()
	defer eventBusMu.Unlock()
	if eventBusGlobal == nil {
		eventBusGlobal = NewEventBus()
	}
	return eventBusGlobal
}

// SetEventBus mirrors set_event_bus.
func SetEventBus(eventBus *EventBus) {
	eventBusMu.Lock()
	defer eventBusMu.Unlock()
	eventBusGlobal = eventBus
}
