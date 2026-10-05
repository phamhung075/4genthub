package event_handlers

import (
	"context"
	"sort"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Deviation (MIGRATION.md, event_handlers decision 2026-10-02): the Python
// handlers read attributes the event classes do not define (changed_fields,
// new_values, previous_values, previous_status, completion_time_seconds,
// previous_branch_id) and raise AttributeError. The Go handlers work against
// the real event fields; Python-only attributes without a counterpart are
// documented placeholders (nil/empty/zero).

// TaskEventTaskRepository is the minimal task-repository dependency used by
// TaskEventHandlers (Python `task_repository: Any | None`). The generic
// repositories.TaskRepository has none of the methods the Python calls, so only
// the five used methods are declared here.
type TaskEventTaskRepository interface {
	TrackTaskCreation(ctx context.Context, event any) error
	ArchiveTask(ctx context.Context, taskID string, occurredAt time.Time) error
	GetDependentTasks(ctx context.Context, taskID string) ([]string, error)
	TrackTaskAccess(ctx context.Context, taskID string, userID *string, accessedAt time.Time) error
	GetTaskDependencies(ctx context.Context, taskID string) ([]*entities.Task, error)
}

// TaskEventNotificationService is the minimal notification dependency used by
// TaskEventHandlers (Python `notification_service: Any | None`). No Go port
// existed, so the notify_* methods actually called by the Python are declared.
type TaskEventNotificationService interface {
	NotifyTaskAssignment(ctx context.Context, assignee, taskID, title, priority string) error
	NotifyTaskUpdated(ctx context.Context, taskID string, changedFields []string, previousValues, newValues map[string]any) error
	NotifyTaskDeleted(ctx context.Context, taskID string, deletedBy *string) error
	NotifyTaskCompleted(ctx context.Context, taskID, title string, completedBy *string, completionTime float64) error
	NotifyTaskMoved(ctx context.Context, taskID, previousBranch, newBranch string, movedBy *string) error
	NotifyTaskStarted(ctx context.Context, taskID string, startedBy *string) error
	NotifyTaskBlocked(ctx context.Context, taskID string, blockedBy *string, urgent bool) error
	NotifyTaskNeedsReview(ctx context.Context, taskID string, submittedBy *string) error
	NotifyTaskReady(ctx context.Context, taskID, message string) error
}

// TaskEventHandlers handles task-related domain events. It maintains statistics,
// tracks status transitions and completion times, and triggers follow-up actions.
type TaskEventHandlers struct {
	// mu guards the in-memory statistics maps/slices below.
	mu sync.Mutex
	// EventStore is assigned but never read (Python self.event_store), so it is
	// kept as the passed-through value.
	EventStore          any
	TaskRepository      TaskEventTaskRepository
	NotificationService TaskEventNotificationService

	// TaskStats mirrors Python's defaultdict(lambda: {created, updated, ...}).
	TaskStats map[string]map[string]int
	// StatusTransitions maps task id -> ordered transition records.
	StatusTransitions map[string][]*entities.OrderedMap[any]
	// CompletionTimes accumulates completion durations in seconds.
	CompletionTimes []float64

	// taskStatsOrder preserves the insertion order of TaskStats keys, which the
	// unordered Go map cannot express but get_task_statistics must return.
	taskStatsOrder []string
}

// NewTaskEventHandlers builds the handler with the Python default dict state.
func NewTaskEventHandlers(eventStore any, taskRepository TaskEventTaskRepository, notificationService TaskEventNotificationService) *TaskEventHandlers {
	return &TaskEventHandlers{
		EventStore:          eventStore,
		TaskRepository:      taskRepository,
		NotificationService: notificationService,
		TaskStats:           map[string]map[string]int{},
		StatusTransitions:   map[string][]*entities.OrderedMap[any]{},
		CompletionTimes:     []float64{},
	}
}

// stats returns the mutable counter map for a project key, creating it (with
// the six Python default keys) on first use.
func (h *TaskEventHandlers) stats(projectKey string) map[string]int {
	s, ok := h.TaskStats[projectKey]
	if !ok {
		s = map[string]int{
			"created": 0, "updated": 0, "completed": 0,
			"deleted": 0, "status_changes": 0, "moved": 0,
		}
		h.TaskStats[projectKey] = s
		h.taskStatsOrder = append(h.taskStatsOrder, projectKey)
	}
	return s
}

// taskEventProjectKey mirrors Python's
// `str(event.project_id) if hasattr(event, "project_id") else "unknown"`.
// No task event in domain/events exposes project_id, so every task event falls
// back to "unknown" just as the Python does.
func taskEventProjectKey() string { return "unknown" }

// taskEventUserValue mirrors Python storing `event.user_id` (str | None).
func taskEventUserValue(id *string) any {
	if id == nil {
		return nil
	}
	return *id
}

// HandleTaskCreated handles TaskCreatedEvent. Updates statistics, notifies
// assignees and initializes tracking.
func (h *TaskEventHandlers) HandleTaskCreated(ctx context.Context, event events.TaskCreatedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stats(taskEventProjectKey())["created"]++

	if h.NotificationService != nil {
		for _, assignee := range event.Assignees {
			_ = h.NotificationService.NotifyTaskAssignment(
				ctx, assignee, value_objects.PyStr(event.TaskID), event.Title, event.Priority,
			)
		}
	}

	if h.TaskRepository != nil {
		_ = h.TaskRepository.TrackTaskCreation(ctx, event)
	}
}

// HandleTaskUpdated handles TaskUpdatedEvent. Tracks changes, updates metrics
// and triggers notifications.
func (h *TaskEventHandlers) HandleTaskUpdated(ctx context.Context, event events.TaskUpdatedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stats(taskEventProjectKey())["updated"]++

	// Python reads event.changed_fields, which its TaskUpdatedEvent does not
	// expose; the Go event carries `changes`, so its keys are the changed fields.
	changedFields := make([]string, 0, len(event.Changes))
	for field := range event.Changes {
		changedFields = append(changedFields, field)
	}
	sort.Strings(changedFields)

	significantFields := map[string]bool{"status": true, "priority": true, "assignees": true, "due_date": true}
	significantChanges := []string{}
	for _, field := range changedFields {
		if significantFields[field] {
			significantChanges = append(significantChanges, field)
		}
	}

	if len(significantChanges) > 0 && h.NotificationService != nil {
		// Python reads event.previous_values/event.new_values, neither of which
		// its event defines. The Go event only carries `changes`, so previous
		// values are unavailable (nil) and the changes map is passed as new.
		_ = h.NotificationService.NotifyTaskUpdated(
			ctx, value_objects.PyStr(event.TaskID), significantChanges, nil, event.Changes,
		)
	}
}

// HandleTaskDeleted handles TaskDeletedEvent. Updates statistics, archives data
// and notifies stakeholders.
func (h *TaskEventHandlers) HandleTaskDeleted(ctx context.Context, event events.TaskDeletedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stats(taskEventProjectKey())["deleted"]++

	if h.TaskRepository != nil {
		_ = h.TaskRepository.ArchiveTask(ctx, event.TaskID, event.OccurredAt)
	}

	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskDeleted(ctx, event.TaskID, event.UserID)
	}
}

// HandleTaskStatusChanged handles TaskStatusChangedEvent. Tracks status
// transitions, updates metrics and triggers workflows.
func (h *TaskEventHandlers) HandleTaskStatusChanged(ctx context.Context, event events.TaskStatusChangedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stats(taskEventProjectKey())["status_changes"]++

	transition := entities.NewOrderedMap[any]()
	transition.Set("task_id", event.TaskID)
	transition.Set("from", event.OldStatus)
	transition.Set("to", event.NewStatus)
	transition.Set("timestamp", value_objects.IsoFormat(event.OccurredAt))
	transition.Set("user", taskEventUserValue(event.UserID))
	h.StatusTransitions[event.TaskID] = append(h.StatusTransitions[event.TaskID], transition)

	switch event.NewStatus {
	case "in_progress":
		h.handleTaskStarted(ctx, event)
	case "blocked":
		h.handleTaskBlocked(ctx, event)
	case "review":
		h.handleTaskNeedsReview(ctx, event)
	}
}

// HandleTaskCompleted handles TaskCompletedEvent. Calculates completion time,
// updates metrics and triggers follow-up actions.
func (h *TaskEventHandlers) HandleTaskCompleted(ctx context.Context, event events.TaskCompletedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stats(taskEventProjectKey())["completed"]++

	completionTime := taskEventCompletionSeconds(event)
	if completionTime != 0 {
		h.CompletionTimes = append(h.CompletionTimes, completionTime)
	}

	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskCompleted(
			ctx, event.TaskID, event.Title, event.UserID, completionTime,
		)
	}

	if h.TaskRepository != nil {
		dependentTasks, _ := h.TaskRepository.GetDependentTasks(ctx, event.TaskID)
		for _, dependentTask := range dependentTasks {
			h.checkDependenciesAndNotify(ctx, dependentTask)
		}
	}
}

// HandleTaskRetrieved handles TaskRetrievedEvent. Tracks access patterns.
func (h *TaskEventHandlers) HandleTaskRetrieved(ctx context.Context, event events.TaskRetrievedEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.TaskRepository != nil {
		_ = h.TaskRepository.TrackTaskAccess(ctx, event.TaskID, event.UserID, event.OccurredAt)
	}
}

// HandleTaskMovedToBranch handles TaskMovedToBranchEvent. Updates branch metrics
// and notifies relevant parties.
func (h *TaskEventHandlers) HandleTaskMovedToBranch(ctx context.Context, event events.TaskMovedToBranchEvent) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.stats(taskEventProjectKey())["moved"]++

	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskMoved(
			ctx, event.TaskID, event.OldBranchID, event.NewBranchID, event.UserID,
		)
	}
}

// handleTaskStarted handles the workflow when a task is started.
func (h *TaskEventHandlers) handleTaskStarted(ctx context.Context, event events.TaskStatusChangedEvent) {
	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskStarted(ctx, event.TaskID, event.UserID)
	}
}

// handleTaskBlocked handles the workflow when a task is blocked.
func (h *TaskEventHandlers) handleTaskBlocked(ctx context.Context, event events.TaskStatusChangedEvent) {
	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskBlocked(ctx, event.TaskID, event.UserID, true)
	}
}

// handleTaskNeedsReview handles the workflow when a task needs review.
func (h *TaskEventHandlers) handleTaskNeedsReview(ctx context.Context, event events.TaskStatusChangedEvent) {
	if h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskNeedsReview(ctx, event.TaskID, event.UserID)
	}
}

// checkDependenciesAndNotify checks whether all dependencies are complete and
// notifies when the task is ready to start.
func (h *TaskEventHandlers) checkDependenciesAndNotify(ctx context.Context, taskID string) {
	if h.TaskRepository == nil {
		return
	}

	dependencies, _ := h.TaskRepository.GetTaskDependencies(ctx, taskID)
	allComplete := true
	for _, dependency := range dependencies {
		if dependency.Status == nil || dependency.Status.Value != string(value_objects.TaskStatusDone) {
			allComplete = false
			break
		}
	}

	if allComplete && h.NotificationService != nil {
		_ = h.NotificationService.NotifyTaskReady(
			ctx, taskID, "All dependencies completed, task is ready to start",
		)
	}
}

// taskEventCompletionSeconds bridges Python's nonexistent
// event.completion_time_seconds to the Go TaskCompletedEvent.TimeSpentMinutes.
func taskEventCompletionSeconds(event events.TaskCompletedEvent) float64 {
	if event.TimeSpentMinutes == nil {
		return 0
	}
	return float64(*event.TimeSpentMinutes) * 60
}

// fillTaskStats writes the six statistics keys in Python insertion order.
func fillTaskStats(dst *entities.OrderedMap[any], stats map[string]int) {
	dst.Set("created", stats["created"])
	dst.Set("updated", stats["updated"])
	dst.Set("completed", stats["completed"])
	dst.Set("deleted", stats["deleted"])
	dst.Set("status_changes", stats["status_changes"])
	dst.Set("moved", stats["moved"])
}

// GetTaskStatistics returns statistics for a project or for all projects,
// preserving Python dict key order.
func (h *TaskEventHandlers) GetTaskStatistics(ctx context.Context, projectID *string) *entities.OrderedMap[any] {
	h.mu.Lock()
	defer h.mu.Unlock()
	if projectID != nil {
		key := *projectID
		stats := entities.NewOrderedMap[any]()
		if s, ok := h.TaskStats[key]; ok {
			fillTaskStats(stats, s)
		}
		out := entities.NewOrderedMap[any]()
		out.Set("project_id", key)
		out.Set("statistics", stats)
		return out
	}

	created, updated, completed, deleted, statusChanges, moved := 0, 0, 0, 0, 0, 0
	for _, s := range h.TaskStats {
		created += s["created"]
		updated += s["updated"]
		completed += s["completed"]
		deleted += s["deleted"]
		statusChanges += s["status_changes"]
		moved += s["moved"]
	}

	summary := entities.NewOrderedMap[any]()
	fillTaskStats(summary, map[string]int{
		"created": created, "updated": updated, "completed": completed,
		"deleted": deleted, "status_changes": statusChanges, "moved": moved,
	})

	completionRate := 0.0
	if created > 0 {
		completionRate = float64(completed) / float64(created)
	}
	summary.Set("completion_rate", completionRate)

	if len(h.CompletionTimes) > 0 {
		total := 0.0
		for _, t := range h.CompletionTimes {
			total += t
		}
		summary.Set("avg_completion_time_seconds", total/float64(len(h.CompletionTimes)))
	}

	byProject := entities.NewOrderedMap[any]()
	for _, key := range h.taskStatsOrder {
		s, ok := h.TaskStats[key]
		if !ok {
			continue
		}
		projectStats := entities.NewOrderedMap[any]()
		fillTaskStats(projectStats, s)
		byProject.Set(key, projectStats)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("summary", summary)
	out.Set("by_project", byProject)
	return out
}

// ProcessEvent routes a domain event to its handler by concrete Go type.
func (h *TaskEventHandlers) ProcessEvent(ctx context.Context, event events.Event) {
	switch e := event.(type) {
	case events.TaskCreatedEvent:
		h.HandleTaskCreated(ctx, e)
	case events.TaskUpdatedEvent:
		h.HandleTaskUpdated(ctx, e)
	case events.TaskDeletedEvent:
		h.HandleTaskDeleted(ctx, e)
	case events.TaskStatusChangedEvent:
		h.HandleTaskStatusChanged(ctx, e)
	case events.TaskCompletedEvent:
		h.HandleTaskCompleted(ctx, e)
	case events.TaskRetrievedEvent:
		h.HandleTaskRetrieved(ctx, e)
	case events.TaskMovedToBranchEvent:
		h.HandleTaskMovedToBranch(ctx, e)
	}
}
