package interfaces

import "context"

// IEventHandler handles events of the listed types.
type IEventHandler interface {
	Handle(ctx context.Context, event IEvent) error
	EventTypes() []string
}

// IEventBus publishes events to subscribed handlers.
type IEventBus interface {
	Publish(ctx context.Context, event IEvent) error
	PublishMany(ctx context.Context, events []IEvent) error
	Subscribe(eventType string, handler IEventHandler)
	Unsubscribe(eventType string, handler IEventHandler)
	SubscribeToAll(handler IEventHandler)
	GetHandlers(eventType string) []IEventHandler
	Start(ctx context.Context) error
	Stop(ctx context.Context) error
	IsRunning() bool
}

// IEventDispatcher dispatches an event to handlers.
type IEventDispatcher interface {
	Dispatch(ctx context.Context, event IEvent, handlers []IEventHandler) error
	DispatchInOrder(ctx context.Context, event IEvent, handlers []IEventHandler) error
	DispatchParallel(ctx context.Context, event IEvent, handlers []IEventHandler) error
}
