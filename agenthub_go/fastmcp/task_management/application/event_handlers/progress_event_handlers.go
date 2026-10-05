package event_handlers

import (
	"context"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProgressEventStore is the minimal event store used by progress handlers.
type ProgressEventStore interface {
	Append(ctx context.Context, event events.Event) error
}

// ProgressNotificationService is the minimal notification dependency.
type ProgressNotificationService interface {
	Notify(ctx context.Context, notificationType string, data map[string]any, priority string) error
}

func notifyProgress(ctx context.Context, svc ProgressNotificationService, t string, data map[string]any, priority string) {
	if svc != nil {
		_ = svc.Notify(ctx, t, data, priority)
	}
}

// ProgressUpdatedHandler handles ProgressUpdated events.
type ProgressUpdatedHandler struct {
	TaskRepository    repositories.TaskRepository
	ContextRepository repositories.ContextRepository
	EventStore        ProgressEventStore
}

// NewProgressUpdatedHandler builds the handler.
func NewProgressUpdatedHandler(taskRepository repositories.TaskRepository, contextRepository repositories.ContextRepository, eventStore ProgressEventStore) *ProgressUpdatedHandler {
	return &ProgressUpdatedHandler{TaskRepository: taskRepository, ContextRepository: contextRepository, EventStore: eventStore}
}

// Handle processes a ProgressUpdated event.
func (h *ProgressUpdatedHandler) Handle(ctx context.Context, event events.ProgressUpdated) {
	if h.EventStore != nil {
		_ = h.EventStore.Append(ctx, event)
	}
	taskID, err := value_objects.NewTaskId(event.TaskID)
	if err == nil && h.TaskRepository != nil {
		task, err := h.TaskRepository.FindByID(ctx, taskID)
		if err == nil && task != nil && task.ProgressTimeline != nil {
			for name, target := range task.ProgressTimeline.Milestones {
				if event.OldPercentage < target && target <= event.NewPercentage && !task.ProgressTimeline.IsMilestoneReached(name) {
					// milestone auto-reached: Python only logs here
				}
			}
		}
	}
	if int(event.NewPercentage/10) > int(event.OldPercentage/10) {
		h.updateContextMilestone(ctx, event)
	}
}

// updateContextMilestone is inert: Python calls task_repository.get_by_id and
// context_repository.get_by_id/update, which do not exist (AttributeError, only
// logged), so no context row is ever written. Kept faithful: no DB write.
func (h *ProgressUpdatedHandler) updateContextMilestone(ctx context.Context, event events.ProgressUpdated) {
}

// ProgressMilestoneReachedHandler handles ProgressMilestoneReached events.
type ProgressMilestoneReachedHandler struct {
	NotificationService ProgressNotificationService
	EventStore          ProgressEventStore
}

// NewProgressMilestoneReachedHandler builds the handler.
func NewProgressMilestoneReachedHandler(notificationService ProgressNotificationService, eventStore ProgressEventStore) *ProgressMilestoneReachedHandler {
	return &ProgressMilestoneReachedHandler{NotificationService: notificationService, EventStore: eventStore}
}

// Handle processes a ProgressMilestoneReached event.
func (h *ProgressMilestoneReachedHandler) Handle(ctx context.Context, event events.ProgressMilestoneReached) {
	if h.EventStore != nil {
		_ = h.EventStore.Append(ctx, event)
	}
	notifyProgress(ctx, h.NotificationService, "milestone_reached", map[string]any{
		"task_id": event.TaskID, "milestone": event.MilestoneName, "progress": event.CurrentProgress,
	}, "")
}

// ProgressStalledHandler handles ProgressStalled events.
type ProgressStalledHandler struct {
	TaskRepository      repositories.TaskRepository
	NotificationService ProgressNotificationService
}

// NewProgressStalledHandler builds the handler.
func NewProgressStalledHandler(taskRepository repositories.TaskRepository, notificationService ProgressNotificationService) *ProgressStalledHandler {
	return &ProgressStalledHandler{TaskRepository: taskRepository, NotificationService: notificationService}
}

// Handle processes a ProgressStalled event.
func (h *ProgressStalledHandler) Handle(ctx context.Context, event events.ProgressStalled) {
	taskID, err := value_objects.NewTaskId(event.TaskID)
	if err != nil || h.TaskRepository == nil {
		return
	}
	task, err := h.TaskRepository.FindByID(ctx, taskID)
	if err != nil || task == nil {
		return
	}
	notifyProgress(ctx, h.NotificationService, "progress_stalled", map[string]any{
		"task_id": event.TaskID, "duration_hours": event.StallDurationHours,
		"current_progress": event.CurrentPercentage, "blockers": event.Blockers,
	}, "high")
	// _add_blocker_insight is a no-op in Python.
}

// SubtaskProgressAggregatedHandler handles SubtaskProgressAggregated events.
type SubtaskProgressAggregatedHandler struct {
	TaskRepository    repositories.TaskRepository
	ContextRepository repositories.ContextRepository
}

// NewSubtaskProgressAggregatedHandler builds the handler.
func NewSubtaskProgressAggregatedHandler(taskRepository repositories.TaskRepository, contextRepository repositories.ContextRepository) *SubtaskProgressAggregatedHandler {
	return &SubtaskProgressAggregatedHandler{TaskRepository: taskRepository, ContextRepository: contextRepository}
}

// Handle processes a SubtaskProgressAggregated event. Inert: Python's
// task_repository.get_by_id does not exist (AttributeError, only logged), so the
// parent task is never updated. Kept faithful: no DB write.
func (h *SubtaskProgressAggregatedHandler) Handle(ctx context.Context, event events.SubtaskProgressAggregated) {
}

// ProgressTypeCompletedHandler handles ProgressTypeCompleted events.
type ProgressTypeCompletedHandler struct {
	TaskRepository      repositories.TaskRepository
	NotificationService ProgressNotificationService
}

// NewProgressTypeCompletedHandler builds the handler.
func NewProgressTypeCompletedHandler(taskRepository repositories.TaskRepository, notificationService ProgressNotificationService) *ProgressTypeCompletedHandler {
	return &ProgressTypeCompletedHandler{TaskRepository: taskRepository, NotificationService: notificationService}
}

// Handle processes a ProgressTypeCompleted event.
func (h *ProgressTypeCompletedHandler) Handle(ctx context.Context, event events.ProgressTypeCompleted) {
	taskID, err := value_objects.NewTaskId(event.TaskID)
	if err != nil || h.TaskRepository == nil {
		return
	}
	task, err := h.TaskRepository.FindByID(ctx, taskID)
	if err != nil || task == nil {
		return
	}
	notifyProgress(ctx, h.NotificationService, "progress_type_completed", map[string]any{
		"task_id": event.TaskID, "progress_type": string(event.ProgressType),
		"timestamp": value_objects.IsoFormat(event.CompletionTimestamp),
	}, "")
}

// ProgressEventHandlers is the registry for progress event handlers.
type ProgressEventHandlers struct {
	handlers map[string]func(ctx context.Context, event events.Event)
	// Keep concrete handlers accessible as in Python's registry.
	UpdatedHandler           *ProgressUpdatedHandler
	MilestoneReachedHandler  *ProgressMilestoneReachedHandler
	StalledHandler           *ProgressStalledHandler
	SubtaskAggregatedHandler *SubtaskProgressAggregatedHandler
	TypeCompletedHandler     *ProgressTypeCompletedHandler
}

// NewProgressEventHandlers builds the registry with all handlers.
func NewProgressEventHandlers(taskRepository repositories.TaskRepository, contextRepository repositories.ContextRepository, notificationService ProgressNotificationService, eventStore ProgressEventStore) *ProgressEventHandlers {
	updated := NewProgressUpdatedHandler(taskRepository, contextRepository, eventStore)
	milestone := NewProgressMilestoneReachedHandler(notificationService, eventStore)
	stalled := NewProgressStalledHandler(taskRepository, notificationService)
	aggregated := NewSubtaskProgressAggregatedHandler(taskRepository, contextRepository)
	completed := NewProgressTypeCompletedHandler(taskRepository, notificationService)
	h := &ProgressEventHandlers{
		UpdatedHandler: updated, MilestoneReachedHandler: milestone, StalledHandler: stalled,
		SubtaskAggregatedHandler: aggregated, TypeCompletedHandler: completed,
	}
	h.handlers = map[string]func(ctx context.Context, event events.Event){
		"ProgressUpdated":          func(ctx context.Context, e events.Event) { updated.Handle(ctx, e.(events.ProgressUpdated)) },
		"ProgressMilestoneReached": func(ctx context.Context, e events.Event) { milestone.Handle(ctx, e.(events.ProgressMilestoneReached)) },
		"ProgressStalled":          func(ctx context.Context, e events.Event) { stalled.Handle(ctx, e.(events.ProgressStalled)) },
		"SubtaskProgressAggregated": func(ctx context.Context, e events.Event) {
			aggregated.Handle(ctx, e.(events.SubtaskProgressAggregated))
		},
		"ProgressTypeCompleted": func(ctx context.Context, e events.Event) { completed.Handle(ctx, e.(events.ProgressTypeCompleted)) },
	}
	return h
}

// HandleEvent routes an event to the appropriate handler.
func (h *ProgressEventHandlers) HandleEvent(ctx context.Context, event events.Event) {
	if fn, ok := h.handlers[event.EventType()]; ok {
		fn(ctx, event)
	}
}

// RegisterHandler registers a custom handler for an event type.
func (h *ProgressEventHandlers) RegisterHandler(eventType string, handler func(ctx context.Context, event events.Event)) {
	h.handlers[eventType] = handler
}
