package services

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// The two PERF targets the NFR register records without a measurement:
//   PERF-02  Context Sync Overhead  UnifiedContextService.ResolveContext, whose read path is
//                                   GetContext -> entityToDict -> resolveInheritanceSync (the three
//                                   repository reads and the merge over global/project/branch).
//   PERF-05  Delta Payload          WebSocketNotificationService.SyncBroadcastTask, the frame a task
//                                   event becomes on the wire: metadata build, context lookup,
//                                   completion enrichment, broker hand-off with the whole TaskData.
//
// A benchmark does not fail CI: it prints numbers. The register cites the date and the commit of
// the run, so a stale measurement is visible as a stale citation rather than as a green gate.

// benchResolveService builds the global/project/branch/task hierarchy once, through the service's
// own create path so the entities are the shapes the read path consumes. The benchmark measures
// the read, not the writes.
func benchResolveService(b *testing.B) *UnifiedContextService {
	b.Helper()
	user := "user-bench"
	s := NewUnifiedContextService(newZucsFakeRepo(), newZucsFakeRepo(), newZucsFakeRepo(), newZucsFakeRepo(), nil, nil, nil, nil, &user)
	ctx := context.Background()

	creates := []struct {
		level, id string
		data      *entities.OrderedMap[any]
	}{
		{"project", "proj-bench", zucsOM("project_name", "bench")},
		{"branch", "branch-bench", zucsOM("project_id", "proj-bench", "git_branch_name", "bench")},
		{"task", "task-bench", zucsOM("branch_id", "branch-bench", "task_data", zucsOM("title", "bench task", "status", "in_progress"))},
	}
	for _, c := range creates {
		result, _ := s.CreateContext(ctx, c.level, c.id, c.data, nil, nil, true)
		if ok, _ := result.Get("success"); ok != true {
			b.Fatalf("create %s/%s failed: %v", c.level, c.id, result.Keys())
		}
	}
	return s
}

// BenchmarkResolveContext measures the task-level read with inheritance applied.
func BenchmarkResolveContext(b *testing.B) {
	s := benchResolveService(b)
	ctx := context.Background()

	result, _ := s.ResolveContext(ctx, "task", "task-bench", true, nil)
	if ok, _ := result.Get("success"); ok != true {
		b.Fatalf("resolve failed: %v", result.Keys())
	}
	contextData, _ := result.Get("context")
	if ordered, isOrdered := contextData.(*entities.OrderedMap[any]); !isOrdered || ordered.Len() == 0 {
		b.Fatalf("resolve returned no context: %T", contextData)
	}

	b.ReportAllocs()
	for b.Loop() {
		if _, err := s.ResolveContext(ctx, "task", "task-bench", true, nil); err != nil {
			b.Fatal(err)
		}
	}
}

// benchDiscardBroker accepts the frame and drops it, so the measurement is the frame build and not
// the transport.
type benchDiscardBroker struct{}

func (benchDiscardBroker) BroadcastDataChange(context.Context, string, string, string, string, any, *entities.OrderedMap[any]) error {
	return nil
}

// BenchmarkTaskEventFrame measures one task event through SyncBroadcastTask. The duplicate cache
// short-circuits a repeat of the same (event, entity, user) within five seconds, so each iteration
// clears just its own key before the call; that delete (one mutex and one map delete) is inside the
// timing and is the same bookkeeping the read path pays to record the event.
func BenchmarkTaskEventFrame(b *testing.B) {
	const taskID = "task-bench-frame"
	const userID = "user-bench"
	ctx := context.Background()
	svc := &WebSocketNotificationService{Broker: benchDiscardBroker{}}
	p := SyncTaskEventParams{
		EventType: "updated",
		TaskID:    taskID,
		UserID:    userID,
		TaskData:  zucsOM("title", "bench task", "status", "in_progress", "description", "bench"),
	}
	key := "updated:task:" + taskID + ":" + userID

	if err := svc.SyncBroadcastTask(ctx, p); err != nil {
		b.Fatal(err)
	}

	b.ReportAllocs()
	for b.Loop() {
		wsNotificationCacheMu.Lock()
		delete(wsNotificationCache, key)
		wsNotificationCacheMu.Unlock()
		if err := svc.SyncBroadcastTask(ctx, p); err != nil {
			b.Fatal(err)
		}
	}
}
