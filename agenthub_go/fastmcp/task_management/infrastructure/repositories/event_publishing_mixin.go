package repositories

// Event Publishing Mixin (Python repositories/event_publishing_mixin.py): repositories publish
// the domain events raised by an entity through the global event bus.

import (
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/infrastructure"
)

// EventPublishingEntity is the entity surface the mixin uses (Python get_events). The method
// returns and clears the raised events, like Subtask.get_events.
type EventPublishingEntity interface {
	GetEvents() []events.Event
}

// EventPublishingMixin adds event publishing capabilities to repositories. Embed it by value
// and initialize it with NewEventPublishingMixin.
type EventPublishingMixin struct {
	eventBus               *infrastructure.EventBus
	eventPublishingEnabled bool
}

// NewEventPublishingMixin mirrors EventPublishingMixin.__init__ (enabled by default).
func NewEventPublishingMixin() EventPublishingMixin {
	return EventPublishingMixin{eventPublishingEnabled: true}
}

// EnableEventPublishing enables automatic event publishing after save operations.
func (m *EventPublishingMixin) EnableEventPublishing() { m.eventPublishingEnabled = true }

// DisableEventPublishing disables automatic event publishing.
func (m *EventPublishingMixin) DisableEventPublishing() { m.eventPublishingEnabled = false }

// IsEventPublishingEnabled reports whether event publishing is enabled.
func (m *EventPublishingMixin) IsEventPublishingEnabled() bool { return m.eventPublishingEnabled }

// GetEventBus lazily loads the global event bus (get_event_bus).
func (m *EventPublishingMixin) GetEventBus() *infrastructure.EventBus {
	if m.eventBus == nil {
		m.eventBus = infrastructure.GetEventBus()
	}
	return m.eventBus
}

// SetEventBus configures a custom event bus.
func (m *EventPublishingMixin) SetEventBus(bus *infrastructure.EventBus) { m.eventBus = bus }

// PublishEntityEventsAsync publishes every event raised by the entity through the async bus
// path and returns the number published. Python's per-event try/except is preserved; the Go
// bus isolates handler panics, so no event fails here.
func (m *EventPublishingMixin) PublishEntityEventsAsync(entity any) int {
	if !m.eventPublishingEnabled {
		return 0
	}
	holder, ok := entity.(EventPublishingEntity)
	if !ok {
		return 0
	}
	evts := holder.GetEvents()
	if len(evts) == 0 {
		return 0
	}
	bus := m.GetEventBus()
	published := 0
	for _, ev := range evts {
		func() {
			defer func() { _ = recover() }()
			bus.Publish(ev)
		}()
		published++
	}
	return published
}

// PublishEntityEvents publishes every event raised by the entity through the synchronous bus
// path and returns the number published.
func (m *EventPublishingMixin) PublishEntityEvents(entity any) int {
	if !m.eventPublishingEnabled {
		return 0
	}
	holder, ok := entity.(EventPublishingEntity)
	if !ok {
		return 0
	}
	evts := holder.GetEvents()
	if len(evts) == 0 {
		return 0
	}
	bus := m.GetEventBus()
	published := 0
	for _, ev := range evts {
		func() {
			defer func() { _ = recover() }()
			bus.PublishSync(ev)
		}()
		published++
	}
	return published
}

// PublishEventsBatch publishes the events of several entities and returns the total published.
func (m *EventPublishingMixin) PublishEventsBatch(entities []any) int {
	if !m.eventPublishingEnabled {
		return 0
	}
	total := 0
	for _, entity := range entities {
		total += m.PublishEntityEvents(entity)
	}
	return total
}
