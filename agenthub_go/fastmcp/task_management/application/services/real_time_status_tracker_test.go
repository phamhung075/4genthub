package services

import (
	"context"
	"fmt"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// Compile-time assertion that RealTimeStatusTracker satisfies the existing
// websocket.StatusTracker consumer shape (raw payload pass-through).
var _ interface {
	UpdateAgentStatus(context.Context, string, any, any, any, any) error
} = (*RealTimeStatusTracker)(nil)

func zpRtsTestSession(t *testing.T, agentID string) *entities.AgentSession {
	t.Helper()
	session, err := entities.NewAgentSession(entities.AgentSessionOptions{AgentID: agentID})
	if err != nil {
		t.Fatalf("NewAgentSession: %v", err)
	}
	return session
}

func zpRtsMustGet(t *testing.T, m *entities.OrderedMap[any], key string) any {
	t.Helper()
	value, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	return value
}

func TestZpRtsMatchesPattern(t *testing.T) {
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	cases := []struct {
		agentID string
		pattern string
		want    bool
	}{
		{"agent-1", "*", true},
		{"agent-1", "agent-1", true},
		{"agent-1", "agent-*", true},
		{"agent-1", "agent-1*", true},
		{"agent-1", "agent", false},
		{"agent-1", "other*", false},
		{"agent-1", "agent-2", false},
	}
	for _, tc := range cases {
		if got := tracker.matchesPattern(tc.agentID, tc.pattern); got != tc.want {
			t.Errorf("matchesPattern(%q, %q) = %v, want %v", tc.agentID, tc.pattern, got, tc.want)
		}
	}
}

func TestZpRtsGetMetricsCountsAndKeyOrder(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	session := zpRtsTestSession(t, "agent-1")
	if err := tracker.RegisterSession(ctx, session); err != nil {
		t.Fatal(err)
	}
	tracker.SubscribeToUpdates(ctx, "sub-1", []string{"*"}, nil, nil, nil)

	metrics := tracker.GetMetrics()
	wantKeys := []string{"active_sessions", "tracked_agents", "active_subscriptions", "history_entries", "anomaly_agents", "total_anomalies"}
	if got := metrics.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("metric keys = %v, want %v", got, wantKeys)
	}
	wantValues := map[string]int{
		"active_sessions": 1, "tracked_agents": 1, "active_subscriptions": 1,
		"history_entries": 1, "anomaly_agents": 0, "total_anomalies": 0,
	}
	for key, want := range wantValues {
		if got := zpRtsMustGet(t, metrics, key); got != want {
			t.Errorf("metric %q = %v, want %d", key, got, want)
		}
	}

	if err := tracker.detectAnomaly(ctx, "agent-1", "high_resource_usage", entities.NewOrderedMap[any]()); err != nil {
		t.Fatal(err)
	}
	if err := tracker.detectAnomaly(ctx, "agent-1", "high_resource_usage", nil); err != nil {
		t.Fatal(err)
	}
	after := tracker.GetMetrics()
	if got := zpRtsMustGet(t, after, "anomaly_agents"); got != 1 {
		t.Errorf("anomaly_agents = %v, want 1", got)
	}
	if got := zpRtsMustGet(t, after, "total_anomalies"); got != 2 {
		t.Errorf("total_anomalies = %v, want 2", got)
	}
}

func TestZpRtsSubscribeDefaultUpdateTypes(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)

	id := tracker.SubscribeToUpdates(ctx, "sub-1", []string{"*"}, nil, nil, nil)
	if !strings.HasPrefix(id, "sub_sub-1_") {
		t.Fatalf("subscription id = %q, want sub_sub-1_ prefix", id)
	}
	subscription, ok := tracker.Subscriptions.Get(id)
	if !ok {
		t.Fatal("subscription not stored")
	}
	if !subscription.Active {
		t.Error("new subscription should be active")
	}
	if len(subscription.UpdateTypes) != len(StatusUpdateTypeValues) {
		t.Fatalf("default update types = %d, want %d", len(subscription.UpdateTypes), len(StatusUpdateTypeValues))
	}
	for _, updateType := range StatusUpdateTypeValues {
		if !subscription.UpdateTypes[updateType] {
			t.Errorf("default subscription missing %q", updateType)
		}
	}

	customID := tracker.SubscribeToUpdates(ctx, "sub-2", []string{"*"},
		map[StatusUpdateType]bool{StatusUpdateTypeTaskUpdate: true}, nil, nil)
	custom, _ := tracker.Subscriptions.Get(customID)
	if len(custom.UpdateTypes) != 1 || !custom.UpdateTypes[StatusUpdateTypeTaskUpdate] {
		t.Fatalf("custom update types = %v", custom.UpdateTypes)
	}

	tracker.Unsubscribe(ctx, customID)
	if tracker.Subscriptions.Len() != 1 {
		t.Fatalf("subscriptions after unsubscribe = %d, want 1", tracker.Subscriptions.Len())
	}
}

func TestZpRtsResourceAnomalyThreshold(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	session := zpRtsTestSession(t, "agent-1")
	if err := tracker.RegisterSession(ctx, session); err != nil {
		t.Fatal(err)
	}

	// 80.0% is not greater than anomaly_threshold * 100 == 80.0.
	if err := tracker.ReportResourceUsage(ctx, "agent-1", "cpu_thread", 80, 100, nil); err != nil {
		t.Fatal(err)
	}
	if got := tracker.AnomalyCounts["agent-1"]; got != 0 {
		t.Fatalf("anomalies at exactly 80%% = %d, want 0", got)
	}

	// 81% exceeds the threshold.
	if err := tracker.ReportResourceUsage(ctx, "agent-1", "cpu_thread", 81, 100, nil); err != nil {
		t.Fatal(err)
	}
	if got := tracker.AnomalyCounts["agent-1"]; got != 1 {
		t.Fatalf("anomalies at 81%% = %d, want 1", got)
	}

	// allocated_amount == 0 gives 0% and never trips the threshold.
	if err := tracker.ReportResourceUsage(ctx, "agent-1", "cpu_thread", 999, 0, nil); err != nil {
		t.Fatal(err)
	}
	if got := tracker.AnomalyCounts["agent-1"]; got != 1 {
		t.Fatalf("anomalies after zero allocation = %d, want 1", got)
	}
}

func TestZpRtsHistoryMaxSize(t *testing.T) {
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	session := zpRtsTestSession(t, "agent-1")
	for i := 0; i < 1005; i++ {
		snapshot := tracker.createSnapshot(session)
		snapshot.Metadata.Set("i", i)
		tracker.recordSnapshot(snapshot)
	}
	if tracker.MaxHistorySize != 1000 {
		t.Fatalf("MaxHistorySize = %d, want 1000", tracker.MaxHistorySize)
	}
	history := tracker.StatusHistory[session.AgentID]
	if len(history) != 1000 {
		t.Fatalf("history length = %d, want 1000", len(history))
	}
	if got := zpRtsMustGet(t, history[0].Metadata, "i"); got != 5 {
		t.Errorf("first retained index = %v, want 5", got)
	}
	if got := zpRtsMustGet(t, history[999].Metadata, "i"); got != 1004 {
		t.Errorf("last retained index = %v, want 1004", got)
	}
}

func TestZpRtsSnapshotShapeAndKeyOrder(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	projectID := "proj-1"
	session, err := entities.NewAgentSession(entities.AgentSessionOptions{AgentID: "agent-1", ProjectID: &projectID})
	if err != nil {
		t.Fatal(err)
	}
	if err := tracker.RegisterSession(ctx, session); err != nil {
		t.Fatal(err)
	}
	snapshot := tracker.GetAgentStatus(ctx, "agent-1")
	if snapshot == nil {
		t.Fatal("GetAgentStatus returned nil")
	}
	if snapshot.AgentID != "agent-1" || snapshot.SessionID != session.SessionID {
		t.Fatalf("snapshot ids = %q/%q", snapshot.AgentID, snapshot.SessionID)
	}
	if snapshot.State != session.State || snapshot.HealthScore != 100 {
		t.Fatalf("state/health = %v/%v", snapshot.State, snapshot.HealthScore)
	}
	if len(snapshot.ActiveTasks) != 0 {
		t.Fatalf("active tasks = %v", snapshot.ActiveTasks)
	}
	if snapshot.ResourceUsage.Len() != 0 {
		t.Fatalf("resource usage = %d", snapshot.ResourceUsage.Len())
	}
	if snapshot.LastError != nil {
		t.Fatalf("last error = %v", *snapshot.LastError)
	}
	wantPerf := []string{"messages_sent", "messages_received", "tasks_completed", "tasks_failed", "error_count", "avg_response_time_ms"}
	if got := snapshot.PerformanceMetrics.Keys(); !reflect.DeepEqual(got, wantPerf) {
		t.Fatalf("performance keys = %v, want %v", got, wantPerf)
	}
	wantMeta := []string{"project_id", "uptime_seconds"}
	if got := snapshot.Metadata.Keys(); !reflect.DeepEqual(got, wantMeta) {
		t.Fatalf("metadata keys = %v, want %v", got, wantMeta)
	}
	if got := zpRtsMustGet(t, snapshot.Metadata, "project_id"); got != "proj-1" {
		t.Errorf("project_id = %v", got)
	}
}

func TestZpRtsGetAllStatusesKeyOrder(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	if err := tracker.RegisterSession(ctx, zpRtsTestSession(t, "agent-2")); err != nil {
		t.Fatal(err)
	}
	if err := tracker.RegisterSession(ctx, zpRtsTestSession(t, "agent-1")); err != nil {
		t.Fatal(err)
	}
	statuses := tracker.GetAllAgentStatuses(ctx)
	want := []string{"agent-2", "agent-1"}
	if got := statuses.Keys(); !reflect.DeepEqual(got, want) {
		t.Fatalf("status keys = %v, want %v", got, want)
	}
	value, _ := statuses.Get("agent-1")
	if _, ok := value.(*StatusSnapshot); !ok {
		t.Fatalf("status value type = %T", value)
	}
}

func TestZpRtsHistoryHoursFilter(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	session := zpRtsTestSession(t, "agent-1")
	if err := tracker.RegisterSession(ctx, session); err != nil {
		t.Fatal(err)
	}
	old := tracker.createSnapshot(session)
	old.Timestamp = zpRtsNow().Add(-2 * time.Hour)
	tracker.recordSnapshot(old)

	one := 1
	recent := tracker.GetAgentHistory(ctx, "agent-1", &one)
	if len(recent) != 1 {
		t.Fatalf("recent history = %d, want 1", len(recent))
	}
	full := tracker.GetAgentHistory(ctx, "agent-1", nil)
	if len(full) != 2 {
		t.Fatalf("full history = %d, want 2", len(full))
	}
	zero := 0
	zeroHours := tracker.GetAgentHistory(ctx, "agent-1", &zero)
	if len(zeroHours) != 2 {
		t.Fatalf("zero-hours history = %d, want 2", len(zeroHours))
	}
	if missing := tracker.GetAgentHistory(ctx, "nobody", nil); len(missing) != 0 {
		t.Fatalf("missing agent history = %d, want 0", len(missing))
	}
}

func TestZpRtsCallbackNotification(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	var got *entities.OrderedMap[any]
	tracker.SubscribeToUpdates(ctx, "sub-1", []string{"agent-*"}, nil,
		func(_ context.Context, notification *entities.OrderedMap[any]) error {
			got = notification
			return nil
		}, nil)
	if err := tracker.RegisterSession(ctx, zpRtsTestSession(t, "agent-1")); err != nil {
		t.Fatal(err)
	}
	if got == nil {
		t.Fatal("callback was not invoked")
	}
	wantKeys := []string{"subscription_id", "agent_id", "update_type", "timestamp", "data"}
	if keys := got.Keys(); !reflect.DeepEqual(keys, wantKeys) {
		t.Fatalf("notification keys = %v, want %v", keys, wantKeys)
	}
	if v := zpRtsMustGet(t, got, "update_type"); v != string(StatusUpdateTypeStateChange) {
		t.Errorf("update_type = %v", v)
	}
	data, ok := zpRtsMustGet(t, got, "data").(*entities.OrderedMap[any])
	if !ok {
		t.Fatal("notification data is not an OrderedMap")
	}
	if v := zpRtsMustGet(t, data, "new_state"); v != "session_started" {
		t.Errorf("new_state = %v", v)
	}
}

func TestZpRtsUpdateAgentStatusStartsTask(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	session := zpRtsTestSession(t, "agent-1")
	if err := tracker.RegisterSession(ctx, session); err != nil {
		t.Fatal(err)
	}
	if err := tracker.UpdateAgentStatus(ctx, "agent-1", entities.SessionStateBusy, "task-1", "working", map[string]any{"k": "v"}); err != nil {
		t.Fatal(err)
	}
	if session.State != entities.SessionStateBusy {
		t.Fatalf("state = %v, want busy", session.State)
	}
	if !session.ActiveTasks.Has("task-1") {
		t.Fatal("task-1 was not started")
	}
	if session.Metadata["k"] != "v" {
		t.Fatalf("metadata k = %v", session.Metadata["k"])
	}
	// Unknown agent is a no-op.
	if err := tracker.UpdateAgentStatus(ctx, "nobody", entities.SessionStateActive, nil, nil, nil); err != nil {
		t.Fatal(err)
	}
}

func TestZpRtsReportErrorRecovery(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 30, 0.8)
	session := zpRtsTestSession(t, "agent-1")
	if err := tracker.RegisterSession(ctx, session); err != nil {
		t.Fatal(err)
	}
	session.Metrics.ErrorCount = 10
	if err := tracker.ReportError(ctx, "agent-1", "boom", "bad", nil); err != nil {
		t.Fatal(err)
	}
	// error_count becomes 11 (> 10) so needs_recovery() triggers recover(), which resets it.
	if session.Metrics.ErrorCount != 0 {
		t.Fatalf("error_count = %d, want 0 after recovery", session.Metrics.ErrorCount)
	}
	if session.Metrics.RecoveryCount != 1 {
		t.Fatalf("recovery_count = %d, want 1", session.Metrics.RecoveryCount)
	}
	lastError, ok := session.Metadata["last_error"].(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("last_error type = %T", session.Metadata["last_error"])
	}
	if v := zpRtsMustGet(t, lastError, "message"); v != "bad" {
		t.Errorf("last_error message = %v", v)
	}
}

func TestZpRtsStartStop(t *testing.T) {
	ctx := context.Background()
	tracker := NewRealTimeStatusTracker(nil, 24, 3600, 0.8)
	tracker.Start(ctx)
	if !tracker.running.Load() {
		t.Fatal("tracker should be running after Start")
	}
	tracker.Start(ctx) // idempotent
	tracker.Stop(ctx)
	if tracker.running.Load() {
		t.Fatal("tracker should be stopped after Stop")
	}
}

// TestRealTimeStatusTrackerConcurrentState hammers register/subscribe/metrics/unsubscribe/
// unregister from several goroutines with the tracker started; run with -race.
func TestRealTimeStatusTrackerConcurrentState(t *testing.T) {
	tracker := NewRealTimeStatusTracker(nil, 24, 1, 0.8)
	ctx := context.Background()
	tracker.Start(ctx)
	defer tracker.Stop(ctx)

	var wg sync.WaitGroup
	for g := 0; g < 8; g++ {
		wg.Add(1)
		go func(g int) {
			defer wg.Done()
			for i := 0; i < 100; i++ {
				session := zpRtsTestSession(t, fmt.Sprintf("agent-%d-%d", g, i%5))
				_ = tracker.RegisterSession(ctx, session)
				id := tracker.SubscribeToUpdates(ctx, "sub", []string{"*"}, nil, nil, nil)
				_ = tracker.GetMetrics()
				_ = tracker.GetAllAgentStatuses(ctx)
				tracker.Unsubscribe(ctx, id)
				_ = tracker.UnregisterSession(ctx, session.SessionID)
			}
		}(g)
	}
	wg.Wait()
}
