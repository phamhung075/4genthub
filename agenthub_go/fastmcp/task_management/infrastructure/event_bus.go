package infrastructure

import (
	"reflect"
	"sort"
	"strconv"
	"sync"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/infrastructure/events"
)

// EventSubscription is a subscription to an event type (event_bus.EventSubscription).
// Go funcs are not comparable, so a subscription is identified by Name; IsAsync is kept
// for shape parity but Go has no coroutine functions, so it is always false.
type EventSubscription struct {
	EventType reflect.Type
	Handler   func(event any)
	Name      string
	Priority  int
	IsAsync   bool
}

// EventBus is the in-memory domain event bus (event_bus.EventBus).
type EventBus struct {
	mu              sync.Mutex
	subscriptions   map[reflect.Type][]*EventSubscription
	asyncEventQueue *events.EventQueue
}

// NewEventBus creates an event bus with no subscriptions.
func NewEventBus() *EventBus {
	return &EventBus{subscriptions: map[reflect.Type][]*EventSubscription{}}
}

// SetEventQueue mirrors EventBus.set_event_queue.
func (b *EventBus) SetEventQueue(queue *events.EventQueue) {
	b.mu.Lock()
	b.asyncEventQueue = queue
	b.mu.Unlock()
}

// Subscribe mirrors EventBus.subscribe; higher priorities run first. name replaces the
// Python handler identity used by unsubscribe.
func (b *EventBus) Subscribe(eventType reflect.Type, name string, handler func(event any), priority int) {
	sub := &EventSubscription{EventType: eventType, Handler: handler, Name: name, Priority: priority}
	b.mu.Lock()
	defer b.mu.Unlock()
	b.subscriptions[eventType] = append(b.subscriptions[eventType], sub)
	sort.SliceStable(b.subscriptions[eventType], func(i, j int) bool {
		return b.subscriptions[eventType][i].Priority > b.subscriptions[eventType][j].Priority
	})
}

// Unsubscribe mirrors EventBus.unsubscribe; it returns true when a handler with the
// given name was removed.
func (b *EventBus) Unsubscribe(eventType reflect.Type, name string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	subs, ok := b.subscriptions[eventType]
	if !ok {
		return false
	}
	initialCount := len(subs)
	kept := subs[:0:0]
	for _, sub := range subs {
		if sub.Name != name {
			kept = append(kept, sub)
		}
	}
	if len(kept) == 0 {
		delete(b.subscriptions, eventType)
		return initialCount > 0
	}
	b.subscriptions[eventType] = kept
	return len(kept) < initialCount
}

// Publish mirrors the async EventBus.publish: every subscribed handler runs in priority
// order and panics are isolated from the remaining handlers.
func (b *EventBus) Publish(event any) { b.dispatch(event) }

// PublishSync mirrors EventBus.publish_sync. The async event queue is used only when
// settings.enable_async_event_queue is set and a queue is configured.
func (b *EventBus) PublishSync(event any) {
	b.mu.Lock()
	queue := b.asyncEventQueue
	b.mu.Unlock()
	if fastmcp.Settings.EnableAsyncEventQueue && queue != nil {
		if success, err := queue.PutNowait(event); err == nil && success {
			return
		}
	}
	b.dispatch(event)
}

func (b *EventBus) dispatch(event any) {
	eventType := normalizeEventType(reflect.TypeOf(event))
	if eventType == nil {
		return
	}
	b.mu.Lock()
	var all []*EventSubscription
	for _, cls := range eventTypeMRO(eventType) {
		all = append(all, b.subscriptions[cls]...)
	}
	b.mu.Unlock()

	sort.SliceStable(all, func(i, j int) bool { return all[i].Priority > all[j].Priority })
	for _, sub := range all {
		func() {
			defer func() { _ = recover() }()
			sub.Handler(event)
		}()
	}
}

// PublishBatch mirrors EventBus.publish_batch.
func (b *EventBus) PublishBatch(evts []any) {
	for _, e := range evts {
		b.Publish(e)
	}
}

// ClearSubscriptions mirrors EventBus.clear_subscriptions; a nil eventType clears all.
func (b *EventBus) ClearSubscriptions(eventType *reflect.Type) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if eventType != nil {
		delete(b.subscriptions, *eventType)
		return
	}
	b.subscriptions = map[reflect.Type][]*EventSubscription{}
}

// GetSubscriptions mirrors EventBus.get_subscriptions (exact type only).
func (b *EventBus) GetSubscriptions(eventType reflect.Type) []func(event any) {
	b.mu.Lock()
	defer b.mu.Unlock()
	subs := b.subscriptions[eventType]
	out := make([]func(event any), 0, len(subs))
	for _, sub := range subs {
		out = append(out, sub.Handler)
	}
	return out
}

// HasSubscribers mirrors EventBus.has_subscribers.
func (b *EventBus) HasSubscribers(eventType reflect.Type) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return len(b.subscriptions[eventType]) > 0
}

// StartProcessing mirrors EventBus.start_processing (handled by EventWorker).
func (b *EventBus) StartProcessing() {}

// StopProcessing mirrors EventBus.stop_processing (handled by EventWorker).
func (b *EventBus) StopProcessing() {}

// QueueEvent mirrors EventBus.queue_event.
func (b *EventBus) QueueEvent(event any) {
	b.mu.Lock()
	queue := b.asyncEventQueue
	b.mu.Unlock()
	if queue != nil {
		_, _ = queue.PutNowait(event)
		return
	}
	b.dispatch(event)
}

// String is EventBus.__repr__.
func (b *EventBus) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	total := 0
	for _, subs := range b.subscriptions {
		total += len(subs)
	}
	return "EventBus(event_types=" + strconv.Itoa(len(b.subscriptions)) +
		", total_subscriptions=" + strconv.Itoa(total) + ")"
}

// normalizeEventType maps a pointer type to its element, mirroring Python's use of the
// event class (Go event values are structs).
func normalizeEventType(t reflect.Type) reflect.Type {
	for t != nil && t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	return t
}

// eventTypeMRO approximates Python's type(event).__mro__ for Go embedding: the concrete
// type followed by its anonymous embedded struct types, breadth-first.
func eventTypeMRO(t reflect.Type) []reflect.Type {
	out := []reflect.Type{}
	seen := map[reflect.Type]bool{}
	queue := []reflect.Type{t}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		if cur == nil || seen[cur] {
			continue
		}
		seen[cur] = true
		out = append(out, cur)
		base := cur
		for base.Kind() == reflect.Pointer {
			base = base.Elem()
		}
		if base.Kind() != reflect.Struct {
			continue
		}
		for i := 0; i < base.NumField(); i++ {
			f := base.Field(i)
			if !f.Anonymous {
				continue
			}
			ft := f.Type
			for ft.Kind() == reflect.Pointer {
				ft = ft.Elem()
			}
			if ft.Kind() == reflect.Struct {
				queue = append(queue, ft)
			}
		}
	}
	return out
}

var (
	globalEventBusMu sync.Mutex
	globalEventBus   *EventBus
)

// GetEventBus returns the global event bus, creating it on first use.
func GetEventBus() *EventBus {
	globalEventBusMu.Lock()
	defer globalEventBusMu.Unlock()
	if globalEventBus == nil {
		globalEventBus = NewEventBus()
	}
	return globalEventBus
}

// ResetEventBus mirrors reset_event_bus.
func ResetEventBus() {
	globalEventBusMu.Lock()
	defer globalEventBusMu.Unlock()
	if globalEventBus != nil {
		globalEventBus.ClearSubscriptions(nil)
	}
	globalEventBus = nil
}
