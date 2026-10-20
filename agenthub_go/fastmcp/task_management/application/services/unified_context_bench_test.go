package services

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain"
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
	s := NewUnifiedContextService(newZucsFakeRepo(), newZucsFakeRepo(), newZucsFakeRepo(), newZucsFakeRepo(), nil, nil, nil, &user)
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

	result, _ := s.ResolveContext(ctx, "task", "task-bench", nil)
	if ok, _ := result.Get("success"); ok != true {
		b.Fatalf("resolve failed: %v", result.Keys())
	}
	contextData, _ := result.Get("context")
	if ordered, isOrdered := contextData.(*entities.OrderedMap[any]); !isOrdered || ordered.Len() == 0 {
		b.Fatalf("resolve returned no context: %T", contextData)
	}

	b.ReportAllocs()
	for b.Loop() {
		if _, err := s.ResolveContext(ctx, "task", "task-bench", nil); err != nil {
			b.Fatal(err)
		}
	}
}

// benchCaptureBroker keeps the primary a frame would deliver, so the benchmark can assert the
// size and shape the ruling caps instead of only timing the call.
type benchCaptureBroker struct{ primaries []any }

func (b *benchCaptureBroker) BroadcastDataChange(_ context.Context, _, _, _ string, _ string, data any, _ *entities.OrderedMap[any]) error {
	b.primaries = append(b.primaries, data)
	return nil
}

// benchTaskPayload is the 16-key seed shape a task event's full payload has (details excluded by
// design), widened with the 20 labels and 20 assignees the ruling's wide case names.
func benchTaskPayload(taskID, updatedAt string) *entities.OrderedMap[any] {
	labels, assignees := make([]string, 0, 20), make([]string, 0, 20)
	for i := 0; i < 20; i++ {
		labels = append(labels, fmt.Sprintf("label-%02d-of-a-wide-ticket", i))
		assignees = append(assignees, fmt.Sprintf("agent-worker-%02d", i))
	}
	m := entities.NewOrderedMap[any]()
	m.Set("id", taskID)
	m.Set("title", "a task title with a realistic length")
	m.Set("status", "in_progress")
	m.Set("priority", "medium")
	m.Set("project_id", "project-bench")
	m.Set("git_branch_id", "branch-bench")
	m.Set("subtask_count", 3)
	m.Set("completed_subtasks", 1)
	m.Set("progress_percentage", 40)
	m.Set("assignees", assignees)
	m.Set("has_dependencies", true)
	m.Set("has_context", true)
	m.Set("labels", labels)
	m.Set("created_at", "2026-10-19T10:00:00Z")
	m.Set("updated_at", updatedAt)
	m.Set("description", strings.Repeat("d", 200))
	return m
}

// benchPrimaryEmitted runs one event through SyncBroadcastTask and returns the primary it
// delivered, failing the benchmark when nothing was delivered.
func benchPrimaryEmitted(b *testing.B, svc *WebSocketNotificationService, broker *benchCaptureBroker, p SyncTaskEventParams) *entities.OrderedMap[any] {
	b.Helper()
	before := len(broker.primaries)
	if err := svc.SyncBroadcastTask(context.Background(), p); err != nil {
		b.Fatal(err)
	}
	if len(broker.primaries) != before+1 {
		b.Fatalf("%s event on %s delivered %d frames, want 1", p.EventType, p.TaskID, len(broker.primaries)-before)
	}
	primary, ok := broker.primaries[len(broker.primaries)-1].(*entities.OrderedMap[any])
	if !ok {
		b.Fatalf("primary type = %T, want an OrderedMap %s", broker.primaries[len(broker.primaries)-1], p.EventType)
	}
	if _, carried := primary.Get("details"); carried {
		b.Fatalf("%s event carried the unbounded details string", p.EventType)
	}
	if p.EventType == "updated" || p.EventType == "completed" {
		if v, carried := primary.Get("id"); !carried || v == nil {
			b.Fatalf("%s delta has no id", p.EventType)
		}
		// The refetch shape is the one exception: {id, refetch} is not a field delta.
		if refetch, _ := primary.Get("refetch"); refetch != true {
			if _, carried := primary.Get("updated_at"); !carried {
				b.Fatalf("%s delta on %s has no updated_at (keys %v)", p.EventType, p.TaskID, primary.Keys())
			}
		}
	}
	return primary
}

// benchDedupKey is the duplicate-gate key the service computes, so a sub-benchmark clears exactly
// the entry its own event leaves behind.
func benchDedupKey(p SyncTaskEventParams) string {
	identity := p.UserID
	if stamp, ok := wsDataGet(p.TaskData, "updated_at", nil).(string); ok && stamp != "" {
		identity = stamp
	}
	return p.EventType + ":task:" + p.TaskID + ":" + identity
}

// BenchmarkTaskEventDelta measures the four task-event shapes the PERF-05 spec names - status-only
// update, completion, details append, wide update - each through SyncBroadcastTask, and reports
// the emitted primary's bytes alongside ns/op. It replaces BenchmarkTaskEventFrame, whose 3-key
// payload measured the service path but never a frame (1755 ns/op, 1328 B/op, 25 allocs/op at
// d45aa05d). The one-time assertions below run before any sub-benchmark: reachability of every
// writable field, the created and deleted shapes, and the duplicate gate's two directions.
func BenchmarkTaskEventDelta(b *testing.B) {
	wsNotificationCacheMu.Lock()
	wsNotificationCache = map[string]float64{}
	wsNotificationCacheMu.Unlock()
	broker := &benchCaptureBroker{}
	svc := &WebSocketNotificationService{Broker: broker}

	// Every field a task update can change is reachable through some Changed path; the fields a
	// write cannot touch (project_id, git_branch_id, subtask_count, completed_subtasks, created_at)
	// are seeded by `created` and reached by refetch, and id/updated_at are always in a delta.
	changedNames := []string{"title", "description", "status", "priority", "details", "assignees", "labels", "progress_percentage", "has_context"}
	full := benchTaskPayload("task-bench-reach", "2026-10-19T12:00:00Z")
	for _, name := range append(append([]string{}, changedNames...), "has_dependencies") {
		delta := WebSocketPayloadBuilder{}.BuildTaskDelta(full, []string{name})
		if name == "details" {
			if v, ok := delta.Get("details_changed"); !ok || v != true {
				b.Fatalf("details is not reachable: the delta names it with details_changed, got %v", delta.Keys())
			}
			continue
		}
		if _, ok := delta.Get(name); !ok {
			b.Fatalf("%q of the full payload is not reachable through any Changed path", name)
		}
	}

	// created: the cache seed, carrying the task and never the note.
	seed := (WebSocketPayloadBuilder{}).BuildTaskPayload(wsTaskWithCreated(wsTestTask()), nil)
	if _, ok := seed.Get("details"); ok {
		b.Fatal("the created seed carries details")
	}
	created := benchPrimaryEmitted(b, svc, broker, SyncTaskEventParams{
		EventType: "created", TaskID: "t-1", UserID: "u", TaskData: seed,
	})
	for _, key := range []string{"id", "title", "status", "assignees", "labels", "updated_at"} {
		if _, ok := created.Get(key); !ok {
			b.Fatalf("created shape lacks %q: %v", key, created.Keys())
		}
	}

	// deleted: id and title are the fields the client validates, and the branch the cache filter
	// reads; details is still absent.
	delBranch, delProject := "branch-bench", "project-bench"
	deletedPayload, err := domain.NewTaskDeletePayload("task-bench-deleted", "a deleted task", &delBranch, &delProject)
	if err != nil {
		b.Fatal(err)
	}
	deleted := benchPrimaryEmitted(b, svc, broker, SyncTaskEventParams{
		EventType: "deleted", TaskID: "task-bench-deleted", UserID: "u", TaskData: deletedPayload.ModelDump(),
	})
	for _, key := range []string{"id", "title", "git_branch_id"} {
		if _, ok := deleted.Get(key); !ok {
			b.Fatalf("deleted shape lacks %q: %v", key, deleted.Keys())
		}
	}

	// The duplicate gate, both directions. One write stamped by both emitter families collapses;
	// two distinct writes inside the 5 s TTL both ship, with two different primaries.
	firstWrite := benchTaskPayload("task-bench-dedup", "2026-10-19T12:00:05Z")
	firstDelta := benchPrimaryEmitted(b, svc, broker, SyncTaskEventParams{
		EventType: "updated", TaskID: "task-bench-dedup", UserID: "system", TaskData: firstWrite, Changed: []string{"status"},
	})
	frames := len(broker.primaries)
	if err := svc.SyncBroadcastTask(context.Background(), SyncTaskEventParams{
		EventType: "updated", TaskID: "task-bench-dedup", UserID: "u-actor", TaskData: firstWrite, Changed: []string{"status"},
	}); err != nil {
		b.Fatal(err)
	}
	if len(broker.primaries) != frames {
		b.Fatal("the same write emitted by both emitter families shipped two frames")
	}
	secondWrite := benchTaskPayload("task-bench-dedup", "2026-10-19T12:00:06Z")
	secondWrite.Set("status", "done")
	secondDelta := benchPrimaryEmitted(b, svc, broker, SyncTaskEventParams{
		EventType: "updated", TaskID: "task-bench-dedup", UserID: "system", TaskData: secondWrite, Changed: []string{"status"},
	})
	if firstStatus, _ := firstDelta.Get("status"); secondDelta == firstDelta {
		b.Fatal("two distinct writes delivered the same primary")
	} else if secondStatus, _ := secondDelta.Get("status"); firstStatus == secondStatus {
		b.Fatalf("two distinct writes delivered the same status %v", firstStatus)
	}

	completedAt := "2026-10-19T12:00:02Z"
	completion := (&domain.TaskCompletePayload{ID: "task-bench-done", Title: "a task title", CompletionSummary: &completedAt,
		TestingNotes: &completedAt, CompletedAt: &completedAt}).ModelDump()
	completion.Set("updated_at", completedAt)
	wideFull := benchTaskPayload("task-bench-wide", "2026-10-19T12:00:04Z")
	wideFull.Set("description", strings.Repeat("w", 3000))
	detailsFull := benchTaskPayload("task-bench-details", "2026-10-19T12:00:03Z")
	detailsFull.Set("details", strings.Repeat("n", 41000))

	cases := []struct {
		name   string
		params SyncTaskEventParams
		limit  int // the smaller ceiling the ruling names; 0 means the cap alone
	}{
		{"status", SyncTaskEventParams{
			EventType: "updated", TaskID: "task-bench-status", UserID: "u",
			TaskData: benchTaskPayload("task-bench-status", "2026-10-19T12:00:01Z"), Changed: []string{"status"},
		}, 512},
		{"completion", SyncTaskEventParams{
			EventType: "completed", TaskID: "task-bench-done", UserID: "u", TaskData: completion,
			Changed: []string{"status", "completion_summary", "testing_notes", "completed_at"},
		}, 512},
		{"details", SyncTaskEventParams{
			EventType: "updated", TaskID: "task-bench-details", UserID: "u", TaskData: detailsFull, Changed: []string{"details"},
		}, 512},
		{"wide", SyncTaskEventParams{
			EventType: "updated", TaskID: "task-bench-wide", UserID: "u", TaskData: wideFull,
			Changed: []string{"description", "assignees", "labels"},
		}, 0},
	}

	for _, c := range cases {
		b.Run(c.name, func(b *testing.B) {
			// -count N runs a sub-benchmark N times without re-running the parent's setup, so the
			// key this case left behind on its previous run is cleared before the correctness emit.
			key := benchDedupKey(c.params)
			wsNotificationCacheMu.Lock()
			delete(wsNotificationCache, key)
			wsNotificationCacheMu.Unlock()
			primary := benchPrimaryEmitted(b, svc, broker, c.params)
			size := (WebSocketPayloadBuilder{}).EstimatePayloadSize(primary)
			if size > WebSocketTaskPayloadCap {
				if refetch, _ := primary.Get("refetch"); refetch != true {
					b.Fatalf("%s primary = %d B and is not the refetch shape: %v", c.name, size, primary.Keys())
				}
			}
			if c.limit > 0 && size > c.limit {
				b.Fatalf("%s primary = %d B, want <= %d", c.name, size, c.limit)
			}
			// The duplicate cache short-circuits a repeat of the same event inside five seconds, so
			// each iteration clears just its own key before the call; that delete is the same
			// bookkeeping the read path pays.
			b.ReportAllocs()
			for b.Loop() {
				wsNotificationCacheMu.Lock()
				delete(wsNotificationCache, key)
				wsNotificationCacheMu.Unlock()
				if err := svc.SyncBroadcastTask(context.Background(), c.params); err != nil {
					b.Fatal(err)
				}
			}
			// Reported after the loop: b.Loop resets the metrics it inherits at its first iteration.
			if raw, ok := c.params.TaskData.(*entities.OrderedMap[any]); ok {
				deltaSize := (WebSocketPayloadBuilder{}).EstimatePayloadSize(WebSocketPayloadBuilder{}.BuildTaskDelta(raw, c.params.Changed))
				b.ReportMetric(float64(deltaSize), "delta-B")
			}
			b.ReportMetric(float64(size), "primary-B")
		})
	}
}
