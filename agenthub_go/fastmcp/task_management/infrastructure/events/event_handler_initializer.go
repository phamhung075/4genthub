package events

import (
	"context"
	"reflect"
	"sync"

	eventhandlers "agenthub/fastmcp/task_management/application/event_handlers"
)

// EventHandlerInitializerEventBus is the minimal event-bus contract needed by
// EventHandlerInitializer. It cannot import the parent infrastructure package
// (that package imports this one for EventQueue), so the bus is injected.
type EventHandlerInitializerEventBus interface {
	Subscribe(eventType reflect.Type, name string, handler func(event any), priority int)
}

var (
	eventHandlerInitializerMu          sync.Mutex
	eventHandlerInitializerBus         EventHandlerInitializerEventBus
	eventHandlerInitializerInitialized bool
	eventHandlerInitializerRegistered  int
)

// SetEventHandlerInitializerEventBus injects the event bus used by Initialize.
func SetEventHandlerInitializerEventBus(bus EventHandlerInitializerEventBus) {
	eventHandlerInitializerMu.Lock()
	defer eventHandlerInitializerMu.Unlock()
	eventHandlerInitializerBus = bus
}

// EventHandlerInitializer mirrors EventHandlerInitializer (Python classmethods
// become methods on a stateless value backed by package-level state).
type EventHandlerInitializer struct{}

func initSubscribe[E any](bus EventHandlerInitializerEventBus, name string, fn func(context.Context, E)) {
	bus.Subscribe(reflect.TypeOf(*new(E)), name, func(event any) {
		e, ok := event.(E)
		if !ok {
			return
		}
		fn(context.Background(), e)
	}, 10)
}

func eventHandlerInitializerInc() {
	eventHandlerInitializerMu.Lock()
	eventHandlerInitializerRegistered++
	eventHandlerInitializerMu.Unlock()
}

// Initialize mirrors EventHandlerInitializer.initialize.
func (EventHandlerInitializer) Initialize() bool {
	eventHandlerInitializerMu.Lock()
	if eventHandlerInitializerInitialized {
		eventHandlerInitializerMu.Unlock()
		return true
	}
	bus := eventHandlerInitializerBus
	eventHandlerInitializerMu.Unlock()

	if bus == nil {
		return false
	}

	// The Python initializer builds the handlers with the global event store;
	// the store lives in the parent package that cannot be imported here, so
	// the handlers are built without it.
	taskHandlers := eventhandlers.NewTaskEventHandlers(nil, nil, nil)
	agentHandlers := eventhandlers.NewAgentEventHandlers(nil, nil, nil)
	projectHandlers := eventhandlers.NewProjectEventHandlers(nil, nil, nil, nil)

	registerTaskHandlers(bus, taskHandlers)
	registerAgentHandlers(bus, agentHandlers)
	registerProjectHandlers(bus, projectHandlers)

	eventHandlerInitializerMu.Lock()
	eventHandlerInitializerInitialized = true
	eventHandlerInitializerMu.Unlock()
	return true
}

func registerTaskHandlers(bus EventHandlerInitializerEventBus, handlers *eventhandlers.TaskEventHandlers) {
	initSubscribe(bus, "TaskEventHandlers.HandleTaskCreated", handlers.HandleTaskCreated)
	eventHandlerInitializerInc()
	initSubscribe(bus, "TaskEventHandlers.HandleTaskUpdated", handlers.HandleTaskUpdated)
	eventHandlerInitializerInc()
	initSubscribe(bus, "TaskEventHandlers.HandleTaskDeleted", handlers.HandleTaskDeleted)
	eventHandlerInitializerInc()
	initSubscribe(bus, "TaskEventHandlers.HandleTaskStatusChanged", handlers.HandleTaskStatusChanged)
	eventHandlerInitializerInc()
	initSubscribe(bus, "TaskEventHandlers.HandleTaskCompleted", handlers.HandleTaskCompleted)
	eventHandlerInitializerInc()
	initSubscribe(bus, "TaskEventHandlers.HandleTaskMovedToBranch", handlers.HandleTaskMovedToBranch)
	eventHandlerInitializerInc()
}

func registerAgentHandlers(bus EventHandlerInitializerEventBus, handlers *eventhandlers.AgentEventHandlers) {
	initSubscribe(bus, "AgentEventHandlers.HandleAgentAssigned", handlers.HandleAgentAssigned)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleAgentUnassigned", handlers.HandleAgentUnassigned)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleAgentWorkloadChanged", handlers.HandleAgentWorkloadChanged)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleWorkHandoffRequested", handlers.HandleWorkHandoffRequested)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleWorkHandoffAccepted", handlers.HandleWorkHandoffAccepted)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleConflictDetected", handlers.HandleConflictDetected)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleConflictResolved", handlers.HandleConflictResolved)
	eventHandlerInitializerInc()
	initSubscribe(bus, "AgentEventHandlers.HandleAgentPerformanceEvaluated", handlers.HandleAgentPerformanceEvaluated)
	eventHandlerInitializerInc()
}

func registerProjectHandlers(bus EventHandlerInitializerEventBus, handlers *eventhandlers.ProjectEventHandlers) {
	initSubscribe(bus, "ProjectEventHandlers.HandleProjectCreated", handlers.HandleProjectCreated)
	eventHandlerInitializerInc()
	initSubscribe(bus, "ProjectEventHandlers.HandleProjectUpdated", handlers.HandleProjectUpdated)
	eventHandlerInitializerInc()
	initSubscribe(bus, "ProjectEventHandlers.HandleProjectDeleted", handlers.HandleProjectDeleted)
	eventHandlerInitializerInc()
	initSubscribe(bus, "ProjectEventHandlers.HandleProjectArchived", handlers.HandleProjectArchived)
	eventHandlerInitializerInc()
	initSubscribe(bus, "ProjectEventHandlers.HandleProjectHealthChanged", handlers.HandleProjectHealthChanged)
	eventHandlerInitializerInc()
	initSubscribe(bus, "ProjectEventHandlers.HandleProjectStatisticsUpdated", handlers.HandleProjectStatisticsUpdated)
	eventHandlerInitializerInc()
}

// IsInitialized mirrors is_initialized.
func (EventHandlerInitializer) IsInitialized() bool {
	eventHandlerInitializerMu.Lock()
	defer eventHandlerInitializerMu.Unlock()
	return eventHandlerInitializerInitialized
}

// GetHandlerCount mirrors get_handler_count.
func (EventHandlerInitializer) GetHandlerCount() int {
	eventHandlerInitializerMu.Lock()
	defer eventHandlerInitializerMu.Unlock()
	return eventHandlerInitializerRegistered
}

// Reset mirrors reset.
func (EventHandlerInitializer) Reset() {
	eventHandlerInitializerMu.Lock()
	defer eventHandlerInitializerMu.Unlock()
	eventHandlerInitializerInitialized = false
	eventHandlerInitializerRegistered = 0
}

// InitializeEventHandlers mirrors initialize_event_handlers.
func InitializeEventHandlers() bool {
	return EventHandlerInitializer{}.Initialize()
}
