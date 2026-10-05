package infrastructure

import (
	"fmt"
	"reflect"
	"sync"
)

// DIContainer mirrors di_container.DIContainer: a small service locator keyed by
// string or type. A mutex is added because Go maps are not safe for concurrent
// use while Python's dict operations are atomic.
type DIContainer struct {
	mu          sync.Mutex
	instances   map[any]any
	factories   map[any]func() any
	config      map[string]any
	initialized bool
}

// NewDIContainer mirrors DIContainer.__init__.
func NewDIContainer() *DIContainer {
	return &DIContainer{
		instances: map[any]any{},
		factories: map[any]func() any{},
		config:    map[string]any{},
	}
}

// DIContainerEventHandler is the minimal handler contract used by WireEventHandlers.
type DIContainerEventHandler interface {
	Handle(event any)
}

// DIContainerHandlerRegistry is the minimal registry contract used by
// WireEventHandlers (Python's `registry.handlers` dict).
type DIContainerHandlerRegistry interface {
	Handlers() map[any]any
}

// RegisterSingleton mirrors register_singleton.
func (c *DIContainer) RegisterSingleton(key any, instance any) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.instances[key] = instance
}

// RegisterFactory mirrors register_factory (factories remove any existing instance).
func (c *DIContainer) RegisterFactory(key any, factory func() any) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.factories[key] = factory
	delete(c.instances, key)
}

// RegisterInstance mirrors register_instance.
func (c *DIContainer) RegisterInstance(serviceType any, instance any) {
	c.RegisterSingleton(serviceType, instance)
}

// Get mirrors get (nil when missing).
func (c *DIContainer) Get(key any) any {
	c.mu.Lock()
	defer c.mu.Unlock()
	if factory, ok := c.factories[key]; ok {
		if _, cached := c.instances[key]; !cached {
			c.instances[key] = factory()
		}
		return c.instances[key]
	}
	if instance, ok := c.instances[key]; ok {
		return instance
	}
	return nil
}

// Has mirrors has.
func (c *DIContainer) Has(key any) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	_, inInstances := c.instances[key]
	_, inFactories := c.factories[key]
	return inInstances || inFactories
}

// Remove mirrors remove.
func (c *DIContainer) Remove(key any) {
	c.mu.Lock()
	defer c.mu.Unlock()
	delete(c.instances, key)
	delete(c.factories, key)
}

// Clear mirrors clear.
func (c *DIContainer) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.instances = map[any]any{}
	c.factories = map[any]func() any{}
	c.initialized = false
}

// GetAllServices mirrors get_all_services.
func (c *DIContainer) GetAllServices() map[any]any {
	c.mu.Lock()
	defer c.mu.Unlock()
	all := map[any]any{}
	for k, v := range c.instances {
		all[k] = v
	}
	for key, factory := range c.factories {
		if _, ok := all[key]; !ok {
			instance := factory()
			c.instances[key] = instance
			all[key] = instance
		}
	}
	return all
}

// GetOptional mirrors get_optional.
func (c *DIContainer) GetOptional(serviceType any) any {
	return c.Get(serviceType)
}

// Configure mirrors configure.
func (c *DIContainer) Configure(config map[string]any) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for k, v := range config {
		c.config[k] = v
	}
}

// Reset mirrors reset.
func (c *DIContainer) Reset() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.instances = map[any]any{}
	c.factories = map[any]func() any{}
	c.config = map[string]any{}
	c.initialized = false
}

// GetEventBus mirrors get_event_bus.
func (c *DIContainer) GetEventBus() *EventBus {
	v, _ := c.Get("event_bus").(*EventBus)
	return v
}

// GetEventStore mirrors get_event_store.
func (c *DIContainer) GetEventStore() *EventStore {
	v, _ := c.Get("event_store").(*EventStore)
	return v
}

// GetNotificationService mirrors get_notification_service.
func (c *DIContainer) GetNotificationService() *NotificationService {
	v, _ := c.Get("notification_service").(*NotificationService)
	return v
}

// InitializeInfrastructure mirrors initialize_infrastructure.
func (c *DIContainer) InitializeInfrastructure(eventStorePath *string, notificationChannels []NotificationChannel) {
	c.mu.Lock()
	if c.initialized {
		c.mu.Unlock()
		return
	}
	c.mu.Unlock()

	if eventStorePath != nil {
		c.Configure(map[string]any{"event_store_path": *eventStorePath})
	}

	eventBus := GetEventBus()
	c.RegisterSingleton("event_bus", eventBus)

	notificationService := GetNotificationService()
	c.RegisterSingleton("notification_service", notificationService)

	if eventStorePath != nil {
		eventStore := GetEventStore(eventStorePath)
		c.RegisterSingleton("event_store", eventStore)
	}

	for _, channel := range notificationChannels {
		notificationService.AddChannel(channel)
	}

	c.mu.Lock()
	c.initialized = true
	c.mu.Unlock()
}

// WireEventHandlers mirrors wire_event_handlers.
func (c *DIContainer) WireEventHandlers(registry any) {
	eventBus := c.GetEventBus()
	reg, ok := registry.(DIContainerHandlerRegistry)
	if !ok {
		return
	}
	handlers := reg.Handlers()
	for eventType, handler := range handlers {
		h, ok := handler.(DIContainerEventHandler)
		if !ok {
			continue
		}
		eventBus.Subscribe(diReflectType(eventType), fmt.Sprintf("%T", handler), func(event any) {
			h.Handle(event)
		}, 0)
	}
}

func diReflectType(eventType any) reflect.Type {
	if t, ok := eventType.(reflect.Type); ok {
		return t
	}
	return reflect.TypeOf(eventType)
}

// Repr mirrors __repr__.
func (c *DIContainer) Repr() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return fmt.Sprintf("DIContainer(instances=%d, factories=%d)", len(c.instances), len(c.factories))
}

// String mirrors __repr__.
func (c *DIContainer) String() string { return c.Repr() }

var (
	globalContainerMu sync.Mutex
	globalContainer   *DIContainer
)

// GetContainer mirrors get_container.
func GetContainer() *DIContainer {
	globalContainerMu.Lock()
	defer globalContainerMu.Unlock()
	if globalContainer == nil {
		globalContainer = NewDIContainer()
	}
	return globalContainer
}

// ResetContainer mirrors reset_container.
func ResetContainer() {
	globalContainerMu.Lock()
	defer globalContainerMu.Unlock()
	if globalContainer != nil {
		globalContainer.Reset()
	}
	globalContainer = nil
}

// GetInfrastructureEventBus mirrors get_infrastructure_event_bus.
func GetInfrastructureEventBus() *EventBus {
	return GetContainer().GetEventBus()
}

// GetInfrastructureEventStore mirrors get_infrastructure_event_store.
func GetInfrastructureEventStore() *EventStore {
	return GetContainer().GetEventStore()
}

// GetInfrastructureNotificationService mirrors get_infrastructure_notification_service.
func GetInfrastructureNotificationService() *NotificationService {
	return GetContainer().GetNotificationService()
}

// InitializeInfrastructure mirrors the module-level initialize_infrastructure.
//
// Quirk: the Python convenience function calls the async method without
// awaiting it, so initialization never runs there. Go has no coroutine to
// leave unawaited; the method is invoked directly.
func InitializeInfrastructure(eventStorePath *string, notificationChannels []NotificationChannel) *DIContainer {
	container := GetContainer()
	container.InitializeInfrastructure(eventStorePath, notificationChannels)
	return container
}
