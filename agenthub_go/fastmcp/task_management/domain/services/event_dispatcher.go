// Package services ports task_management/domain/services.
package services

import "sync"

// EventHandler is a named event callback. Python identifies a handler by function
// identity and logs handler.__name__; Go funcs are not comparable, so handlers are
// identified by Name (two handlers with the same Name are the same handler).
type EventHandler struct {
	Name string
	Fn   func(eventData any)
}

// EventDispatcher is the central dispatcher for domain events (Observer pattern).
// Python keeps an unused _async_handlers dict; it is not ported.
type EventDispatcher struct {
	mu       sync.Mutex
	handlers map[string][]EventHandler
}

// NewEventDispatcher creates a dispatcher with no handlers.
func NewEventDispatcher() *EventDispatcher {
	return &EventDispatcher{handlers: map[string][]EventHandler{}}
}

// RegisterHandler registers a handler once per event type.
func (d *EventDispatcher) RegisterHandler(eventType string, handler EventHandler) {
	d.mu.Lock()
	defer d.mu.Unlock()
	for _, h := range d.handlers[eventType] {
		if h.Name == handler.Name {
			return
		}
	}
	d.handlers[eventType] = append(d.handlers[eventType], handler)
}

// UnregisterHandler removes a handler when registered.
func (d *EventDispatcher) UnregisterHandler(eventType string, handler EventHandler) {
	d.mu.Lock()
	defer d.mu.Unlock()
	list := d.handlers[eventType]
	for i, h := range list {
		if h.Name == handler.Name {
			d.handlers[eventType] = append(list[:i:i], list[i+1:]...)
			return
		}
	}
}

// Dispatch calls every handler registered for eventType in registration order.
// A panicking handler is swallowed (Python catches Exception and logs) and the
// remaining handlers still run.
func (d *EventDispatcher) Dispatch(eventType string, eventData any) {
	d.mu.Lock()
	list := append([]EventHandler(nil), d.handlers[eventType]...)
	d.mu.Unlock()
	for _, h := range list {
		func() {
			defer func() { _ = recover() }()
			h.Fn(eventData)
		}()
	}
}

// ClearHandlers clears one event type, or all handlers when eventType is empty
// (Python truthiness of the optional argument).
func (d *EventDispatcher) ClearHandlers(eventType string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if eventType != "" {
		delete(d.handlers, eventType)
		return
	}
	d.handlers = map[string][]EventHandler{}
}

// GetHandlerCount returns the number of handlers registered for eventType.
func (d *EventDispatcher) GetHandlerCount(eventType string) int {
	d.mu.Lock()
	defer d.mu.Unlock()
	return len(d.handlers[eventType])
}

var (
	eventDispatcher     *EventDispatcher
	eventDispatcherOnce sync.Once
)

// GetEventDispatcher returns the process-wide dispatcher (singleton).
func GetEventDispatcher() *EventDispatcher {
	eventDispatcherOnce.Do(func() { eventDispatcher = NewEventDispatcher() })
	return eventDispatcher
}

// DispatchDomainEvent dispatches through the global dispatcher.
func DispatchDomainEvent(eventType string, eventData any) {
	GetEventDispatcher().Dispatch(eventType, eventData)
}
