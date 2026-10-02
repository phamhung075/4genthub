package services

import (
	"agenthub/fastmcp/utilities"
	"context"
	"sync"
	"sync/atomic"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure"
)

// StatusUpdateType mirrors the Python StatusUpdateType enum. A Python Enum becomes a
// string type with one constant per member, in declaration order.
type StatusUpdateType string

const (
	StatusUpdateTypeHeartbeat         StatusUpdateType = "heartbeat"
	StatusUpdateTypeStateChange       StatusUpdateType = "state_change"
	StatusUpdateTypeTaskUpdate        StatusUpdateType = "task_update"
	StatusUpdateTypeResourceUpdate    StatusUpdateType = "resource_update"
	StatusUpdateTypePerformanceUpdate StatusUpdateType = "performance_update"
	StatusUpdateTypeErrorReport       StatusUpdateType = "error_report"
	StatusUpdateTypeRecoveryNotice    StatusUpdateType = "recovery_notice"
)

// StatusUpdateTypeValues lists all members in declaration order, i.e. set(StatusUpdateType).
var StatusUpdateTypeValues = []StatusUpdateType{
	StatusUpdateTypeHeartbeat,
	StatusUpdateTypeStateChange,
	StatusUpdateTypeTaskUpdate,
	StatusUpdateTypeResourceUpdate,
	StatusUpdateTypePerformanceUpdate,
	StatusUpdateTypeErrorReport,
	StatusUpdateTypeRecoveryNotice,
}

// StatusUpdateCallback is the Go port of the Python `Callable | None` callback. Python
// awaits the callable with one positional notification dict; the notification is a dict
// whose key order is observable, so it is an OrderedMap.
type StatusUpdateCallback func(ctx context.Context, notification *entities.OrderedMap[any]) error

// StatusSnapshot is a point-in-time status snapshot for an agent
// (Python application/services/real_time_status_tracker.py StatusSnapshot).
type StatusSnapshot struct {
	AgentID            string
	SessionID          string
	Timestamp          time.Time
	State              entities.SessionState
	HealthScore        float64
	ActiveTasks        []string
	ResourceUsage      *entities.OrderedMap[any]
	PerformanceMetrics *entities.OrderedMap[any]
	LastError          *string
	Metadata           *entities.OrderedMap[any]
}

// StatusSubscription is a subscription for status updates.
type StatusSubscription struct {
	SubscriptionID string
	SubscriberID   string
	AgentPatterns  []string
	UpdateTypes    map[StatusUpdateType]bool
	Callback       StatusUpdateCallback
	WebhookURL     *string
	CreatedAt      time.Time
	Active         bool
}

// NewStatusSubscription applies the Python dataclass defaults: created_at is "now" and
// active is True.
func NewStatusSubscription(
	subscriptionID string,
	subscriberID string,
	agentPatterns []string,
	updateTypes map[StatusUpdateType]bool,
	callback StatusUpdateCallback,
	webhookURL *string,
) *StatusSubscription {
	return &StatusSubscription{
		SubscriptionID: subscriptionID,
		SubscriberID:   subscriberID,
		AgentPatterns:  agentPatterns,
		UpdateTypes:    updateTypes,
		Callback:       callback,
		WebhookURL:     webhookURL,
		CreatedAt:      zpRtsNow(),
		Active:         true,
	}
}

// RealTimeStatusTracker is the real-time status tracking service for agent coordination.
type RealTimeStatusTracker struct {
	EventBus                *infrastructure.EventBus
	HistoryRetentionHours   int
	SnapshotIntervalSeconds int
	AnomalyThreshold        float64

	// Active sessions tracking.
	ActiveSessions *entities.OrderedMap[*entities.AgentSession]
	SessionByAgent map[string]string

	// Status history: agent_id -> snapshots.
	StatusHistory  map[string][]*StatusSnapshot
	MaxHistorySize int

	// Subscriptions (insertion order observable through notification delivery).
	Subscriptions *entities.OrderedMap[*StatusSubscription]

	// Performance tracking.
	PerformanceBaselines map[string]map[string]float64
	AnomalyCounts        map[string]int

	// Background tasks (asyncio.Task replacements).
	running atomic.Bool
	// stateMu guards ActiveSessions, SessionByAgent, StatusHistory, Subscriptions and
	// AnomalyCounts: Python's GIL made those dict operations atomic, a Go concurrent map
	// write is a fatal error. It is only held inside the accessors below, never across a
	// callback.
	stateMu  sync.Mutex
	cancelMu sync.Mutex
	cancel   context.CancelFunc
	wg       sync.WaitGroup
}

// NewRealTimeStatusTracker mirrors __init__ defaults (24h retention, 30s interval,
// 0.8 anomaly threshold) and the max_history_size class default of 1000.
func NewRealTimeStatusTracker(
	eventBus *infrastructure.EventBus,
	historyRetentionHours int,
	snapshotIntervalSeconds int,
	anomalyThreshold float64,
) *RealTimeStatusTracker {
	return &RealTimeStatusTracker{
		EventBus:                eventBus,
		HistoryRetentionHours:   historyRetentionHours,
		SnapshotIntervalSeconds: snapshotIntervalSeconds,
		AnomalyThreshold:        anomalyThreshold,
		ActiveSessions:          entities.NewOrderedMap[*entities.AgentSession](),
		SessionByAgent:          map[string]string{},
		StatusHistory:           map[string][]*StatusSnapshot{},
		MaxHistorySize:          1000,
		Subscriptions:           entities.NewOrderedMap[*StatusSubscription](),
		PerformanceBaselines:    map[string]map[string]float64{},
		AnomalyCounts:           map[string]int{},
	}
}

// Start starts the status tracking service. Python's asyncio.create_task is replaced by
// two goroutines tracked by a WaitGroup; ctx cancellation mirrors task.cancel.
func (s *RealTimeStatusTracker) Start(ctx context.Context) {
	if s.running.Load() {
		return
	}
	s.running.Store(true)
	cctx, cancel := context.WithCancel(ctx)
	s.cancelMu.Lock()
	s.cancel = cancel
	s.cancelMu.Unlock()
	s.wg.Add(2)
	go s.monitorSessions(cctx)
	go s.cleanupOldHistory(cctx)
}

// Stop stops the status tracking service. Python cancels and awaits both background
// tasks, swallowing asyncio.CancelledError; Go cancels the context and waits.
func (s *RealTimeStatusTracker) Stop(ctx context.Context) {
	s.running.Store(false)
	s.cancelMu.Lock()
	cancel := s.cancel
	s.cancel = nil
	s.cancelMu.Unlock()
	if cancel != nil {
		cancel()
	}
	s.wg.Wait()
}

// RegisterSession registers a new agent session for tracking.
func (s *RealTimeStatusTracker) RegisterSession(ctx context.Context, session *entities.AgentSession) error {
	s.stateMu.Lock()
	s.ActiveSessions.Set(session.SessionID, session)
	s.SessionByAgent[session.AgentID] = session.SessionID
	if _, ok := s.StatusHistory[session.AgentID]; !ok {
		s.StatusHistory[session.AgentID] = []*StatusSnapshot{}
	}
	s.stateMu.Unlock()
	snapshot := s.createSnapshot(session)
	s.recordSnapshot(snapshot)
	s.notifyStatusChange(ctx, session.AgentID, StatusUpdateTypeStateChange,
		zpRtsOrderedMap("new_state", "session_started", "session_id", session.SessionID))
	return nil
}

// UnregisterSession unregisters an agent session.
func (s *RealTimeStatusTracker) UnregisterSession(ctx context.Context, sessionID string) error {
	session, ok := s.getSession(sessionID)
	if !ok || session == nil {
		return nil
	}
	agentID := session.AgentID
	snapshot := s.createSnapshot(session)
	snapshot.Metadata.Set("final_snapshot", true)
	s.recordSnapshot(snapshot)
	s.stateMu.Lock()
	s.ActiveSessions.Delete(sessionID)
	delete(s.SessionByAgent, agentID)
	s.stateMu.Unlock()
	s.notifyStatusChange(ctx, agentID, StatusUpdateTypeStateChange,
		zpRtsOrderedMap("new_state", "session_ended", "session_id", sessionID))
	return nil
}

// UpdateAgentStatus updates agent status in real-time. The dynamic parameters mirror the
// existing websocket.StatusTracker consumer interface, which passes raw payload values.
func (s *RealTimeStatusTracker) UpdateAgentStatus(ctx context.Context, agentID string, status, currentTaskID, currentActivity, metadata any) error {
	sessionID, ok := s.sessionIDFor(agentID)
	if !ok || sessionID == "" {
		return nil
	}
	session, ok := s.getSession(sessionID)
	if !ok || session == nil {
		return nil
	}
	session.State = zpRtsSessionState(status)
	if value_objects.PyTruthy(currentTaskID) {
		taskID := value_objects.PyStr(currentTaskID)
		if !session.ActiveTasks.Has(taskID) {
			_ = session.StartTask(taskID)
		}
	}
	if value_objects.PyTruthy(metadata) {
		if session.Metadata == nil {
			session.Metadata = map[string]any{}
		}
		zpRtsMergeMetadata(session.Metadata, metadata)
	}
	_ = session.UpdateHeartbeat()
	snapshot := s.createSnapshot(session)
	s.recordSnapshot(snapshot)
	data := entities.NewOrderedMap[any]()
	data.Set("status", string(session.State))
	data.Set("current_task", currentTaskID)
	data.Set("activity", currentActivity)
	s.notifyStatusChange(ctx, agentID, StatusUpdateTypeStateChange, data)
	return nil
}

// ReportTaskProgress reports a task progress update.
func (s *RealTimeStatusTracker) ReportTaskProgress(ctx context.Context, agentID, taskID string, progressPercentage float64, status string, details *string) error {
	sessionID, ok := s.sessionIDFor(agentID)
	if !ok || sessionID == "" {
		return nil
	}
	session, ok := s.getSession(sessionID)
	if !ok || session == nil {
		return nil
	}
	if status == "completed" {
		_ = session.CompleteTask(taskID, true)
	} else if status == "failed" {
		_ = session.CompleteTask(taskID, false)
	}
	data := entities.NewOrderedMap[any]()
	data.Set("task_id", taskID)
	data.Set("progress", progressPercentage)
	data.Set("status", status)
	data.Set("details", zpRtsStrOrNil(details))
	s.notifyStatusChange(ctx, agentID, StatusUpdateTypeTaskUpdate, data)
	return nil
}

// ReportResourceUsage reports a resource usage update and detects high-usage anomalies.
func (s *RealTimeStatusTracker) ReportResourceUsage(ctx context.Context, agentID, resourceType string, usedAmount, allocatedAmount float64, resourceID *string) error {
	sessionID, ok := s.sessionIDFor(agentID)
	if !ok || sessionID == "" {
		return nil
	}
	session, ok := s.getSession(sessionID)
	if !ok || session == nil {
		return nil
	}
	if resType, ok := zpRtsParseResourceType(resourceType); ok {
		session.UpdateResourceUsage(resType, usedAmount, resourceID)
	}
	usagePercentage := 0.0
	if allocatedAmount > 0 {
		usagePercentage = usedAmount / allocatedAmount * 100
	}
	if usagePercentage > s.AnomalyThreshold*100 {
		_ = s.detectAnomaly(ctx, agentID, "high_resource_usage",
			zpRtsOrderedMap("resource_type", resourceType, "usage_percentage", usagePercentage))
	}
	data := entities.NewOrderedMap[any]()
	data.Set("resource_type", resourceType)
	data.Set("usage", usedAmount)
	data.Set("allocated", allocatedAmount)
	data.Set("percentage", usagePercentage)
	s.notifyStatusChange(ctx, agentID, StatusUpdateTypeResourceUpdate, data)
	return nil
}

// ReportError reports an error from an agent and recovers the session when needed.
func (s *RealTimeStatusTracker) ReportError(ctx context.Context, agentID, errorType, errorMessage string, errorContext *entities.OrderedMap[any]) error {
	sessionID, ok := s.sessionIDFor(agentID)
	if !ok || sessionID == "" {
		return nil
	}
	session, ok := s.getSession(sessionID)
	if !ok || session == nil {
		return nil
	}
	session.Metrics.ErrorCount++
	if session.Metadata == nil {
		session.Metadata = map[string]any{}
	}
	lastError := entities.NewOrderedMap[any]()
	lastError.Set("type", errorType)
	lastError.Set("message", errorMessage)
	lastError.Set("timestamp", value_objects.IsoFormat(zpRtsNow()))
	lastError.Set("context", zpRtsOrderedOrNil(errorContext))
	session.Metadata["last_error"] = lastError
	if session.NeedsRecovery() {
		_ = s.initiateRecovery(ctx, session)
	}
	data := entities.NewOrderedMap[any]()
	data.Set("error_type", errorType)
	data.Set("error_message", errorMessage)
	data.Set("error_count", session.Metrics.ErrorCount)
	s.notifyStatusChange(ctx, agentID, StatusUpdateTypeErrorReport, data)
	return nil
}

// GetAgentStatus returns the current status for an agent, or nil when untracked.
func (s *RealTimeStatusTracker) GetAgentStatus(ctx context.Context, agentID string) *StatusSnapshot {
	sessionID, ok := s.sessionIDFor(agentID)
	if !ok || sessionID == "" {
		return nil
	}
	session, ok := s.getSession(sessionID)
	if !ok || session == nil {
		return nil
	}
	return s.createSnapshot(session)
}

// GetAllAgentStatuses returns the current status for all active agents, keyed by agent id
// in session insertion order.
func (s *RealTimeStatusTracker) GetAllAgentStatuses(ctx context.Context) *entities.OrderedMap[any] {
	statuses := entities.NewOrderedMap[any]()
	for _, session := range s.sessionsSnapshot() {
		statuses.Set(session.AgentID, s.createSnapshot(session))
	}
	return statuses
}

// GetAgentHistory returns the status history for an agent. A nil/zero hours means the
// full copy; otherwise only snapshots within the last `hours` hours.
func (s *RealTimeStatusTracker) GetAgentHistory(ctx context.Context, agentID string, hours *int) []*StatusSnapshot {
	history, ok := s.historyFor(agentID)
	if !ok {
		return []*StatusSnapshot{}
	}
	if hours != nil && *hours != 0 {
		cutoff := zpRtsNow().Add(-time.Duration(*hours) * time.Hour)
		out := []*StatusSnapshot{}
		for _, snapshot := range history {
			if !snapshot.Timestamp.Before(cutoff) {
				out = append(out, snapshot)
			}
		}
		return out
	}
	return append([]*StatusSnapshot{}, history...)
}

// SubscribeToUpdates subscribes to status updates and returns the subscription id. A
// nil/empty update_types set subscribes to every update type.
func (s *RealTimeStatusTracker) SubscribeToUpdates(ctx context.Context, subscriberID string, agentPatterns []string, updateTypes map[StatusUpdateType]bool, callback StatusUpdateCallback, webhookURL *string) string {
	if len(updateTypes) == 0 {
		updateTypes = zpRtsAllUpdateTypes()
	}
	now := zpRtsNow()
	subscription := NewStatusSubscription(
		"sub_"+subscriberID+"_"+zpRtsPyTimestamp(now),
		subscriberID,
		agentPatterns,
		updateTypes,
		callback,
		webhookURL,
	)
	subscription.CreatedAt = now
	s.stateMu.Lock()
	s.Subscriptions.Set(subscription.SubscriptionID, subscription)
	s.stateMu.Unlock()
	return subscription.SubscriptionID
}

// Unsubscribe removes a subscription.
func (s *RealTimeStatusTracker) Unsubscribe(ctx context.Context, subscriptionID string) {
	if subscription, ok := s.getSubscription(subscriptionID); ok {
		s.stateMu.Lock()
		subscription.Active = false
		s.Subscriptions.Delete(subscriptionID)
		s.stateMu.Unlock()
	}
}

// createSnapshot builds a StatusSnapshot from a session.
func (s *RealTimeStatusTracker) createSnapshot(session *entities.AgentSession) *StatusSnapshot {
	now := zpRtsNow()
	performanceMetrics := entities.NewOrderedMap[any]()
	performanceMetrics.Set("messages_sent", session.Metrics.MessagesSent)
	performanceMetrics.Set("messages_received", session.Metrics.MessagesReceived)
	performanceMetrics.Set("tasks_completed", session.Metrics.TasksCompleted)
	performanceMetrics.Set("tasks_failed", session.Metrics.TasksFailed)
	performanceMetrics.Set("error_count", session.Metrics.ErrorCount)
	performanceMetrics.Set("avg_response_time_ms", session.Metrics.AvgResponseTimeMs)

	metadata := entities.NewOrderedMap[any]()
	var projectID any
	if session.ProjectID != nil {
		projectID = *session.ProjectID
	}
	metadata.Set("project_id", projectID)
	metadata.Set("uptime_seconds", value_objects.PyTotalSeconds(now.Sub(session.StartedAt)))

	return &StatusSnapshot{
		AgentID:            session.AgentID,
		SessionID:          session.SessionID,
		Timestamp:          now,
		State:              session.State,
		HealthScore:        session.CalculateHealthScore(),
		ActiveTasks:        session.ActiveTasks.Items(),
		ResourceUsage:      zpRtsResourceUsageOrdered(session.GetResourceUsageSummary()),
		PerformanceMetrics: performanceMetrics,
		LastError:          zpRtsLastErrorMessage(session.Metadata),
		Metadata:           metadata,
	}
}

// recordSnapshot records a status snapshot and enforces max_history_size per agent.
func (s *RealTimeStatusTracker) recordSnapshot(snapshot *StatusSnapshot) {
	agentID := snapshot.AgentID
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	history, ok := s.StatusHistory[agentID]
	if !ok {
		history = []*StatusSnapshot{}
	}
	history = append(history, snapshot)
	if len(history) > s.MaxHistorySize {
		history = history[len(history)-s.MaxHistorySize:]
	}
	s.StatusHistory[agentID] = history
}

// notifyStatusChange notifies matching subscribers. Callback errors are swallowed, as
// Python catches and logs them.
func (s *RealTimeStatusTracker) notifyStatusChange(ctx context.Context, agentID string, updateType StatusUpdateType, data *entities.OrderedMap[any]) {
	for _, subscription := range s.subscriptionsSnapshot() {
		s.stateMu.Lock()
		active := subscription.Active
		s.stateMu.Unlock()
		if !active {
			continue
		}
		matches := false
		for _, pattern := range subscription.AgentPatterns {
			if s.matchesPattern(agentID, pattern) {
				matches = true
				break
			}
		}
		if !matches {
			continue
		}
		if !subscription.UpdateTypes[updateType] {
			continue
		}
		notification := entities.NewOrderedMap[any]()
		notification.Set("subscription_id", subscription.SubscriptionID)
		notification.Set("agent_id", agentID)
		notification.Set("update_type", string(updateType))
		notification.Set("timestamp", value_objects.IsoFormat(zpRtsNow()))
		notification.Set("data", data)
		if subscription.Callback != nil {
			_ = subscription.Callback(ctx, notification)
		}
	}
}

// matchesPattern checks whether an agent id matches a wildcard/prefix/exact pattern.
func (s *RealTimeStatusTracker) matchesPattern(agentID, pattern string) bool {
	if pattern == "*" {
		return true
	}
	if pattern == agentID {
		return true
	}
	if len(pattern) > 0 && pattern[len(pattern)-1] == '*' && len(agentID) >= len(pattern)-1 &&
		agentID[:len(pattern)-1] == pattern[:len(pattern)-1] {
		return true
	}
	return false
}

// detectAnomaly records an anomaly and triggers recovery after more than five.
func (s *RealTimeStatusTracker) detectAnomaly(ctx context.Context, agentID, anomalyType string, details *entities.OrderedMap[any]) error {
	count := s.incrementAnomaly(agentID)
	data := entities.NewOrderedMap[any]()
	data.Set("anomaly_type", anomalyType)
	data.Set("anomaly_count", count)
	data.Set("details", details)
	s.notifyStatusChange(ctx, agentID, StatusUpdateTypePerformanceUpdate, data)
	if count > 5 {
		sessionID, ok := s.sessionIDFor(agentID)
		if ok && sessionID != "" {
			if session, ok := s.getSession(sessionID); ok && session != nil {
				return s.initiateRecovery(ctx, session)
			}
		}
	}
	return nil
}

// initiateRecovery recovers a session and resets its anomaly count.
func (s *RealTimeStatusTracker) initiateRecovery(ctx context.Context, session *entities.AgentSession) error {
	if err := session.Recover(); err != nil {
		return err
	}
	s.stateMu.Lock()
	if _, ok := s.AnomalyCounts[session.AgentID]; ok {
		s.AnomalyCounts[session.AgentID] = 0
	}
	s.stateMu.Unlock()
	data := entities.NewOrderedMap[any]()
	data.Set("recovery_count", session.Metrics.RecoveryCount)
	data.Set("health_score", session.CalculateHealthScore())
	s.notifyStatusChange(ctx, session.AgentID, StatusUpdateTypeRecoveryNotice, data)
	return nil
}

// monitorSessions is the background task that monitors sessions.
func (s *RealTimeStatusTracker) monitorSessions(ctx context.Context) {
	defer s.wg.Done()
	for s.running.Load() {
		rec := utilities.SafeCall(func() {
			for _, session := range s.sessionsSnapshot() {
				if !session.IsAlive() {
					_ = s.UnregisterSession(ctx, session.SessionID)
					continue
				}
				if session.IsExpired() {
					_ = session.Terminate("Session expired")
					_ = s.UnregisterSession(ctx, session.SessionID)
					continue
				}
				if session.IsIdle() {
					s.notifyStatusChange(ctx, session.AgentID, StatusUpdateTypeStateChange,
						zpRtsOrderedMap("new_state", "idle", "idle_time", session.MaxIdleTime))
				}
				s.recordSnapshot(s.createSnapshot(session))
			}
		})
		pause := time.Duration(s.SnapshotIntervalSeconds) * time.Second
		if rec != nil {
			pause = 5 * time.Second // Python: brief pause before retry after an exception
		}
		if !zpRtsSleepCtx(ctx, pause) {
			return
		}
	}
}

// cleanupOldHistory is the background task that removes history older than
// history_retention_hours.
func (s *RealTimeStatusTracker) cleanupOldHistory(ctx context.Context) {
	defer s.wg.Done()
	for s.running.Load() {
		rec := utilities.SafeCall(func() {
			cutoff := zpRtsNow().Add(-time.Duration(s.HistoryRetentionHours) * time.Hour)
			s.stateMu.Lock()
			defer s.stateMu.Unlock()
			keys := make([]string, 0, len(s.StatusHistory))
			for agentID := range s.StatusHistory {
				keys = append(keys, agentID)
			}
			for _, agentID := range keys {
				kept := []*StatusSnapshot{}
				for _, snapshot := range s.StatusHistory[agentID] {
					if !snapshot.Timestamp.Before(cutoff) {
						kept = append(kept, snapshot)
					}
				}
				s.StatusHistory[agentID] = kept
				if len(kept) == 0 {
					delete(s.StatusHistory, agentID)
				}
			}
		})
		pause := time.Hour
		if rec != nil {
			pause = 300 * time.Second // Python: retry in 5 minutes after an exception
		}
		if !zpRtsSleepCtx(ctx, pause) {
			return
		}
	}
}

// GetMetrics returns tracker metrics with the Python response key order.
func (s *RealTimeStatusTracker) GetMetrics() *entities.OrderedMap[any] {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	activeSubscriptions := 0
	for _, subscription := range s.subscriptionsSnapshotLocked() {
		if subscription.Active {
			activeSubscriptions++
		}
	}
	historyEntries := 0
	for _, history := range s.StatusHistory {
		historyEntries += len(history)
	}
	totalAnomalies := 0
	for _, count := range s.AnomalyCounts {
		totalAnomalies += count
	}
	out := entities.NewOrderedMap[any]()
	out.Set("active_sessions", s.ActiveSessions.Len())
	out.Set("tracked_agents", len(s.SessionByAgent))
	out.Set("active_subscriptions", activeSubscriptions)
	out.Set("history_entries", historyEntries)
	out.Set("anomaly_agents", len(s.AnomalyCounts))
	out.Set("total_anomalies", totalAnomalies)
	return out
}

// zpRtsNow mirrors datetime.now(UTC), truncated to microseconds like the entity helper.
var zpRtsNow = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// zpRtsSleepCtx mirrors asyncio.sleep but also wakes on context cancellation.
func zpRtsSleepCtx(ctx context.Context, d time.Duration) bool {
	if d < 0 {
		d = 0
	}
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-timer.C:
		return true
	}
}

// zpRtsOrderedMap builds an insertion-ordered map from alternating key/value pairs.
func zpRtsOrderedMap(pairs ...any) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		out.Set(pairs[i].(string), pairs[i+1])
	}
	return out
}

// zpRtsOrderedOrNil keeps a nil OrderedMap as a nil interface (Python None).
func zpRtsOrderedOrNil(m *entities.OrderedMap[any]) any {
	if m == nil {
		return nil
	}
	return m
}

// zpRtsStrOrNil keeps a nil *string as a nil interface (Python None).
func zpRtsStrOrNil(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// zpRtsParseResourceType mirrors ResourceType(resource_type); ok is false on ValueError.
func zpRtsParseResourceType(value string) (entities.ResourceType, bool) {
	for _, resourceType := range entities.ResourceTypeValues {
		if string(resourceType) == value {
			return resourceType, true
		}
	}
	return entities.ResourceType(""), false
}

// zpRtsResourceUsageOrdered rebuilds the summary dict in ResourceType declaration order.
func zpRtsResourceUsageOrdered(summary map[string]float64) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for _, resourceType := range entities.ResourceTypeValues {
		if value, ok := summary[string(resourceType)]; ok {
			out.Set(string(resourceType), value)
		}
	}
	return out
}

// zpRtsAllUpdateTypes is set(StatusUpdateType).
func zpRtsAllUpdateTypes() map[StatusUpdateType]bool {
	out := map[StatusUpdateType]bool{}
	for _, updateType := range StatusUpdateTypeValues {
		out[updateType] = true
	}
	return out
}

// zpRtsPyTimestamp mirrors str(datetime.now(UTC).timestamp()).
func zpRtsPyTimestamp(t time.Time) string {
	seconds := float64(t.Unix()) + float64(t.Nanosecond()/1000)/1e6
	return value_objects.PyRepr(seconds)
}

// zpRtsSessionState normalizes the dynamic status payload to a SessionState.
func zpRtsSessionState(value any) entities.SessionState {
	if state, ok := value.(entities.SessionState); ok {
		return state
	}
	if text, ok := value.(string); ok {
		return entities.SessionState(text)
	}
	return entities.SessionState("")
}

// zpRtsMergeMetadata is dict.update for map/OrderedMap payloads.
func zpRtsMergeMetadata(dst map[string]any, src any) {
	switch m := src.(type) {
	case map[string]any:
		for key, value := range m {
			dst[key] = value
		}
	case *entities.OrderedMap[any]:
		for _, key := range m.Keys() {
			value, _ := m.Get(key)
			dst[key] = value
		}
	}
}

// zpRtsMapGet is dict.get for map/OrderedMap values.
func zpRtsMapGet(value any, key string) (any, bool) {
	switch m := value.(type) {
	case *entities.OrderedMap[any]:
		return m.Get(key)
	case map[string]any:
		v, ok := m[key]
		return v, ok
	}
	return nil, false
}

// zpRtsLastErrorMessage mirrors metadata.get("last_error", {}).get("message").
func zpRtsLastErrorMessage(metadata map[string]any) *string {
	if metadata == nil {
		return nil
	}
	lastError, ok := metadata["last_error"]
	if !ok || lastError == nil {
		return nil
	}
	message, ok := zpRtsMapGet(lastError, "message")
	if !ok || message == nil {
		return nil
	}
	text := value_objects.PyStr(message)
	return &text
}

// ---- guarded state accessors ----

func (s *RealTimeStatusTracker) sessionIDFor(agentID string) (string, bool) {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	id, ok := s.SessionByAgent[agentID]
	return id, ok
}

func (s *RealTimeStatusTracker) getSession(sessionID string) (*entities.AgentSession, bool) {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	return s.ActiveSessions.Get(sessionID)
}

func (s *RealTimeStatusTracker) sessionsSnapshot() []*entities.AgentSession {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	return s.ActiveSessions.Values()
}

func (s *RealTimeStatusTracker) historyFor(agentID string) ([]*StatusSnapshot, bool) {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	h, ok := s.StatusHistory[agentID]
	return h, ok
}

func (s *RealTimeStatusTracker) getSubscription(id string) (*StatusSubscription, bool) {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	return s.Subscriptions.Get(id)
}

func (s *RealTimeStatusTracker) subscriptionsSnapshot() []*StatusSubscription {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	return s.subscriptionsSnapshotLocked()
}

func (s *RealTimeStatusTracker) subscriptionsSnapshotLocked() []*StatusSubscription {
	return s.Subscriptions.Values()
}

func (s *RealTimeStatusTracker) incrementAnomaly(agentID string) int {
	s.stateMu.Lock()
	defer s.stateMu.Unlock()
	s.AnomalyCounts[agentID]++
	return s.AnomalyCounts[agentID]
}
