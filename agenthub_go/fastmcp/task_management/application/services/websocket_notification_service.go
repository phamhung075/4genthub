package services

import (
	"context"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// wsNotificationCacheTTL mirrors the module-level _cache_ttl (5 seconds).
const wsNotificationCacheTTL = 5

// wsNotificationCache mirrors the module-level _notification_cache global: key -> unix
// seconds. Python's cache is process-global and unsynchronised; Go uses a mutex.
var (
	wsNotificationCacheMu sync.Mutex
	wsNotificationCache   = map[string]float64{}
)

// wsIsDuplicateNotification mirrors _is_duplicate_notification. It prunes expired keys,
// returns true for a recent duplicate, and otherwise records the notification.
func wsIsDuplicateNotification(eventType, entityType, entityID, userID string) bool {
	wsNotificationCacheMu.Lock()
	defer wsNotificationCacheMu.Unlock()

	key := eventType + ":" + entityType + ":" + entityID + ":" + userID
	currentTime := float64(time.Now().UnixNano()) / 1e9

	for k, timestamp := range wsNotificationCache {
		if currentTime-timestamp > wsNotificationCacheTTL {
			delete(wsNotificationCache, k)
		}
	}

	if last, ok := wsNotificationCache[key]; ok {
		if currentTime-last < wsNotificationCacheTTL {
			return true
		}
	}
	wsNotificationCache[key] = currentTime
	return false
}

// WebSocketNotificationContextProvider is the consumer-side port of the DB-backed
// context helpers (_get_task_context/_get_subtask_context/_get_branch_context/
// _get_branch_cascade_data). Python reaches into SQLAlchemy sessions; the application
// layer here receives a provider instead. Each method returns the Python dict as an
// OrderedMap and must apply the Python fallback values when the row is missing.
type WebSocketNotificationContextProvider interface {
	GetTaskContext(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any]
	GetSubtaskContext(ctx context.Context, subtaskID, taskID string, userID *string) *entities.OrderedMap[any]
	GetBranchContext(ctx context.Context, branchID string, userID *string) *entities.OrderedMap[any]
	GetBranchCascadeData(ctx context.Context, branchID string, userID *string) *entities.OrderedMap[any]
}

// WebSocketDataBroadcaster is the consumer-side port of websocket_routes
// broadcast_data_change. Python imports it from fastmcp.server.routes and falls back to
// an HTTP POST when the import/loop fails; the HTTP cross-process fallback has no Go
// meaning and is intentionally not ported (see the package report).
type WebSocketDataBroadcaster interface {
	BroadcastDataChange(ctx context.Context, eventType, entityType, entityID, userID string, data any, metadata *entities.OrderedMap[any]) error
}

// WebSocketNotificationService mirrors websocket_notification_service
// .WebSocketNotificationService. Provider and Broker may be nil in tests; when a
// collaborator is absent the call is a no-op, matching Python's swallowed exceptions.
type WebSocketNotificationService struct {
	Provider WebSocketNotificationContextProvider
	Broker   WebSocketDataBroadcaster
}

// BroadcastTaskEvent mirrors broadcast_task_event. The optional task_data,
// git_branch_id and project_id are pointers to model Python's None defaults.
func (s *WebSocketNotificationService) BroadcastTaskEvent(
	ctx context.Context,
	eventType, taskID, userID string,
	taskData any,
	gitBranchID, projectID *string,
) error {
	if wsIsDuplicateNotification(eventType, "task", taskID, userID) {
		return nil
	}
	if s.Broker == nil {
		return nil
	}

	metadata := entities.NewOrderedMap[any]()
	if gitBranchID != nil && *gitBranchID != "" {
		metadata.Set("git_branch_id", *gitBranchID)
	}
	if projectID != nil && *projectID != "" {
		metadata.Set("project_id", *projectID)
	}
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))

	uid := userID
	taskContext := s.taskContext(ctx, taskID, &uid)
	metadata.Set("task_title", wsContextValue(taskContext, "task_title"))
	metadata.Set("parent_branch_id", wsContextValue(taskContext, "parent_branch_id"))
	metadata.Set("parent_branch_title", wsContextValue(taskContext, "parent_branch_title"))

	return s.Broker.BroadcastDataChange(ctx, eventType, "task", taskID, userID, taskData, metadata)
}

// BroadcastSubtaskEvent mirrors broadcast_subtask_event.
func (s *WebSocketNotificationService) BroadcastSubtaskEvent(
	ctx context.Context,
	eventType, subtaskID, taskID, userID string,
	subtaskData any,
) error {
	if s.Broker == nil {
		return nil
	}
	uid := userID
	subtaskContext := s.subtaskContext(ctx, subtaskID, taskID, &uid)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("parent_task_id", taskID)
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	metadata.Set("subtask_title", wsContextValue(subtaskContext, "subtask_title"))
	metadata.Set("parent_task_title", wsContextValue(subtaskContext, "parent_task_title"))

	return s.Broker.BroadcastDataChange(ctx, eventType, "subtask", subtaskID, userID, subtaskData, metadata)
}

// BroadcastProjectEvent mirrors broadcast_project_event.
func (s *WebSocketNotificationService) BroadcastProjectEvent(
	ctx context.Context,
	eventType, projectID, userID string,
	projectData any,
) error {
	if s.Broker == nil {
		return nil
	}
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	return s.Broker.BroadcastDataChange(ctx, eventType, "project", projectID, userID, projectData, metadata)
}

// BroadcastBranchEvent mirrors broadcast_branch_event.
func (s *WebSocketNotificationService) BroadcastBranchEvent(
	ctx context.Context,
	eventType, branchID, projectID, userID string,
	branchData any,
) error {
	if s.Broker == nil {
		return nil
	}
	uid := userID
	branchContext := s.branchContext(ctx, branchID, &uid)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	metadata.Set("branch_title", wsContextValue(branchContext, "branch_title"))

	return s.Broker.BroadcastDataChange(ctx, eventType, "branch", branchID, userID, branchData, metadata)
}

// BroadcastContextEvent mirrors broadcast_context_event. The supplied metadata map is
// mutated in place (Python does `metadata["context_level"] = ...`).
func (s *WebSocketNotificationService) BroadcastContextEvent(
	ctx context.Context,
	eventType, contextID, level, userID string,
	contextData any,
	metadata *entities.OrderedMap[any],
) error {
	if s.Broker == nil {
		return nil
	}
	if metadata == nil {
		metadata = entities.NewOrderedMap[any]()
	}
	metadata.Set("context_level", level)
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	return s.Broker.BroadcastDataChange(ctx, eventType, "context", contextID, userID, contextData, metadata)
}

// BroadcastAgentEvent mirrors broadcast_agent_event.
func (s *WebSocketNotificationService) BroadcastAgentEvent(
	ctx context.Context,
	eventType, agentID, projectID, userID string,
	agentData any,
) error {
	return s.BroadcastAgentEventNoDedup(ctx, eventType, agentID, projectID, userID, agentData)
}

// SyncBroadcastBranchEvent mirrors sync_broadcast_branch_event and matches the
// zpGitBranchWebSocketNotifier consumer interface in git_branch_service.go. Python
// does no duplicate detection here.
func (s *WebSocketNotificationService) SyncBroadcastBranchEvent(
	eventType, branchID, projectID string,
	userID *string,
	branchData *entities.OrderedMap[any],
) {
	uid := ""
	if userID != nil {
		uid = *userID
	}
	_ = s.BroadcastBranchEvent(context.Background(), eventType, branchID, projectID, uid, branchData)
}

// SyncBroadcastProjectEvent mirrors sync_broadcast_project_event, which only schedules
// broadcast_project_event; it matches the project_management_service notifier.
func (s *WebSocketNotificationService) SyncBroadcastProjectEvent(
	eventType string,
	projectID any,
	userID *string,
	projectData *entities.OrderedMap[any],
) {
	uid := ""
	if userID != nil {
		uid = *userID
	}
	_ = s.BroadcastProjectEvent(context.Background(), eventType, value_objects.PyStr(projectID), uid, projectData)
}

// SyncBroadcastAgentEvent mirrors sync_broadcast_agent_event: duplicate detection on
// (event, "agent_instance", agent_id, user_id), then the broadcast with project_id,
// timestamp and agent_name metadata.
func (s *WebSocketNotificationService) SyncBroadcastAgentEvent(
	ctx context.Context,
	eventType, agentID, projectID, userID string,
	agentData any,
) error {
	if wsIsDuplicateNotification(eventType, "agent_instance", agentID, userID) {
		return nil
	}
	return s.BroadcastAgentEventNoDedup(ctx, eventType, agentID, projectID, userID, agentData)
}

// BroadcastAgentEventNoDedup builds the agent metadata and broadcasts it.
func (s *WebSocketNotificationService) BroadcastAgentEventNoDedup(
	ctx context.Context,
	eventType, agentID, projectID, userID string,
	agentData any,
) error {
	if s.Broker == nil {
		return nil
	}
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	if name := wsAgentName(agentData); name != nil {
		metadata.Set("agent_name", *name)
	}
	return s.Broker.BroadcastDataChange(ctx, eventType, "agent_instance", agentID, userID, agentData, metadata)
}

// SyncTaskEventParams carries sync_broadcast_task_event's keyword arguments.
// PreFetchedContext is used for deletion events so the deleted task is not queried;
// Metadata is copied and extended.
type SyncTaskEventParams struct {
	EventType         string
	TaskID            string
	UserID            string
	TaskData          any
	GitBranchID       *string
	ProjectID         *string
	PreFetchedContext *entities.OrderedMap[any]
	Metadata          *entities.OrderedMap[any]
}

// wsDataGet is `data.get(key, default)` for a dict-like task/subtask payload.
func wsDataGet(data any, key string, def any) any {
	switch m := data.(type) {
	case *entities.OrderedMap[any]:
		if m != nil {
			if v, ok := m.Get(key); ok {
				return v
			}
		}
	case map[string]any:
		if v, ok := m[key]; ok {
			return v
		}
	}
	return def
}

// wsPayloadTruthy is Python truthiness of the optional payload dict.
func wsPayloadTruthy(data any) bool {
	switch m := data.(type) {
	case *entities.OrderedMap[any]:
		return m != nil && m.Len() > 0
	case map[string]any:
		return len(m) > 0
	}
	return false
}

// wsAddCompletionMetadata adds the completion fields poll_mcp_websocket.py expects.
// titleDefault is metadata["task_title"] / metadata["subtask_title"].
func wsAddCompletionMetadata(metadata *entities.OrderedMap[any], data any, titleDefault any) {
	metadata.Set("status", wsDataGet(data, "status", "done"))
	metadata.Set("title", wsDataGet(data, "title", titleDefault))
	metadata.Set("completion_summary", wsDataGet(data, "completion_summary", ""))
	metadata.Set("testing_notes", wsDataGet(data, "testing_notes", ""))
	metadata.Set("progress_percentage", wsDataGet(data, "progress_percentage", 100))
	metadata.Set("assignees", wsDataGet(data, "assignees", []any{}))
	metadata.Set("description", wsDataGet(data, "description", ""))
	metadata.Set("insights_found", wsDataGet(data, "insights_found", []any{}))
	metadata.Set("blockers", wsDataGet(data, "blockers", []any{}))
}

// SyncBroadcastTask mirrors sync_broadcast_task_event: duplicate detection, context
// (pre-fetched or from the provider), metadata (custom + branch/project/timestamp +
// titles), completion enrichment, and branch cascade data for created/deleted events.
func (s *WebSocketNotificationService) SyncBroadcastTask(ctx context.Context, p SyncTaskEventParams) error {
	if wsIsDuplicateNotification(p.EventType, "task", p.TaskID, p.UserID) {
		return nil
	}

	var taskContext *entities.OrderedMap[any]
	if p.PreFetchedContext != nil && p.PreFetchedContext.Len() > 0 {
		taskContext = p.PreFetchedContext
	} else {
		uid := p.UserID
		taskContext = s.taskContext(ctx, p.TaskID, &uid)
	}

	metadata := entities.NewOrderedMap[any]()
	if p.Metadata != nil && p.Metadata.Len() > 0 {
		metadata = p.Metadata.Copy()
	}
	if p.GitBranchID != nil && *p.GitBranchID != "" {
		metadata.Set("git_branch_id", *p.GitBranchID)
	}
	if p.ProjectID != nil && *p.ProjectID != "" {
		metadata.Set("project_id", *p.ProjectID)
	}
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	metadata.Set("task_title", wsContextValue(taskContext, "task_title"))
	metadata.Set("parent_branch_id", wsContextValue(taskContext, "parent_branch_id"))
	metadata.Set("parent_branch_title", wsContextValue(taskContext, "parent_branch_title"))

	if p.EventType == "completed" && wsPayloadTruthy(p.TaskData) {
		title, _ := metadata.Get("task_title")
		wsAddCompletionMetadata(metadata, p.TaskData, title)
	}

	if (p.EventType == "created" || p.EventType == "deleted") && p.GitBranchID != nil && *p.GitBranchID != "" {
		if s.Provider != nil {
			uid := p.UserID
			if cascade := s.Provider.GetBranchCascadeData(ctx, *p.GitBranchID, &uid); cascade != nil {
				branches := []any{cascade}
				c := entities.NewOrderedMap[any]()
				c.Set("branches", branches)
				metadata.Set("cascade", c)
			}
		}
	}

	if s.Broker == nil {
		return nil
	}
	return s.Broker.BroadcastDataChange(ctx, p.EventType, "task", p.TaskID, p.UserID, p.TaskData, metadata)
}

// SyncBroadcastTaskEvent matches the SubtaskEventBroadcaster consumer interface; the
// caller supplies custom metadata (the `metadata` keyword of sync_broadcast_task_event).
func (s *WebSocketNotificationService) SyncBroadcastTaskEvent(
	ctx context.Context,
	eventType, taskID, userID string,
	taskData any,
	metadata *entities.OrderedMap[any],
) error {
	return s.SyncBroadcastTask(ctx, SyncTaskEventParams{
		EventType: eventType, TaskID: taskID, UserID: userID, TaskData: taskData, Metadata: metadata,
	})
}

// SyncBroadcastSubtaskEvent mirrors sync_broadcast_subtask_event (no duplicate
// detection): parent/title metadata plus completion enrichment with is_subtask.
func (s *WebSocketNotificationService) SyncBroadcastSubtaskEvent(
	ctx context.Context,
	eventType, subtaskID, taskID, userID string,
	subtaskData any,
) error {
	uid := userID
	subtaskContext := s.subtaskContext(ctx, subtaskID, taskID, &uid)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("parent_task_id", taskID)
	metadata.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	metadata.Set("subtask_title", wsContextValue(subtaskContext, "subtask_title"))
	metadata.Set("parent_task_title", wsContextValue(subtaskContext, "parent_task_title"))

	if eventType == "completed" && wsPayloadTruthy(subtaskData) {
		title, _ := metadata.Get("subtask_title")
		wsAddCompletionMetadata(metadata, subtaskData, title)
		metadata.Set("is_subtask", true)
	}

	if s.Broker == nil {
		return nil
	}
	return s.Broker.BroadcastDataChange(ctx, eventType, "subtask", subtaskID, userID, subtaskData, metadata)
}

// -- context helpers: provider delegate or Python fallback --

func (s *WebSocketNotificationService) taskContext(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	if s.Provider != nil {
		if c := s.Provider.GetTaskContext(ctx, taskID, userID); c != nil {
			return c
		}
	}
	return wsTaskContextFallback(taskID)
}

func (s *WebSocketNotificationService) subtaskContext(ctx context.Context, subtaskID, taskID string, userID *string) *entities.OrderedMap[any] {
	if s.Provider != nil {
		if c := s.Provider.GetSubtaskContext(ctx, subtaskID, taskID, userID); c != nil {
			return c
		}
	}
	return wsSubtaskContextFallback(subtaskID, taskID)
}

func (s *WebSocketNotificationService) branchContext(ctx context.Context, branchID string, userID *string) *entities.OrderedMap[any] {
	if s.Provider != nil {
		if c := s.Provider.GetBranchContext(ctx, branchID, userID); c != nil {
			return c
		}
	}
	return wsBranchContextFallback(branchID)
}

// wsTaskContextFallback mirrors the not-found/error branch of _get_task_context.
func wsTaskContextFallback(taskID string) *entities.OrderedMap[any] {
	c := entities.NewOrderedMap[any]()
	c.Set("task_title", "Task "+wsPrefix(taskID, 8))
	c.Set("parent_branch_id", nil)
	c.Set("parent_branch_title", "Unknown Branch")
	c.Set("parent_project_id", nil)
	c.Set("task_user_id", nil)
	return c
}

// wsSubtaskContextFallback mirrors the not-found/error branch of _get_subtask_context.
func wsSubtaskContextFallback(subtaskID, taskID string) *entities.OrderedMap[any] {
	c := entities.NewOrderedMap[any]()
	c.Set("subtask_title", "Subtask "+wsPrefix(subtaskID, 8))
	c.Set("parent_task_id", taskID)
	c.Set("parent_task_title", "Task "+wsPrefix(taskID, 8))
	return c
}

// wsBranchContextFallback mirrors the not-found/error branch of _get_branch_context.
func wsBranchContextFallback(branchID string) *entities.OrderedMap[any] {
	c := entities.NewOrderedMap[any]()
	c.Set("branch_title", "Branch "+wsPrefix(branchID, 8))
	return c
}

// wsPrefix is Python's s[:n] for str; it truncates by rune to keep UTF-8 valid slices.
func wsPrefix(s string, n int) string {
	if n <= 0 {
		return ""
	}
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}

func wsContextValue(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// wsAgentName extracts agent_data["name"] when agent_data is a mapping with a string
// name, mirroring `if agent_data and "name" in agent_data`.
func wsAgentName(agentData any) *string {
	m, ok := agentData.(*entities.OrderedMap[any])
	if !ok || m == nil {
		return nil
	}
	v, ok := m.Get("name")
	if !ok {
		return nil
	}
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

// TaskContext is _get_task_context(task_id, user_id).
func (s *WebSocketNotificationService) TaskContext(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	return s.taskContext(ctx, taskID, userID)
}
