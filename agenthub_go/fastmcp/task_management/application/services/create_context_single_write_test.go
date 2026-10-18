package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// The create path's ledger, pinned (hub task 26e857b0): ONE create appends exactly ONE task-level
// context_updated event. Two writers used to reach the same context in the same request - the
// create use case's own SyncTaskMetadata and TaskApplicationFacade.CreateTask ->
// SyncContextAndGetTask - and each produced an identical event, so the ledger counted two.
//
// This test drives the SINGLE REMAINING writer end to end over the REAL UnifiedContextService: the
// task context is seeded, SyncContextAndGetTask runs, and the appender counts what the ledger
// receives. It also asserts the one write carries the fields (task_data and the metadata mirror)
// that the two writes used to split between them, so the count cannot be satisfied by dropping
// content. The other half - that the use case no longer calls SyncTaskMetadata - is pinned in
// TestCreateTaskUseCaseHooksSetContextIDAndNotify, whose expected hook sequence is now
// [context notify] with no "sync".
func TestOneCreatePathWriteAppendsOneTaskContextEvent(t *testing.T) {
	const taskID = "11111111-1111-1111-1111-111111111111"
	user := "user-1"

	repo := newZucsFakeRepo()
	repo.store[taskID] = zucsTaskContext(taskID, "todo")

	appender := &countingContextAppender{}
	svc := NewUnifiedContextService(repo, repo, repo, repo, nil, nil, nil, nil, &user).WithEventAppender(appender)

	status, err := value_objects.NewTaskStatus("todo")
	if err != nil {
		t.Fatalf("status: %v", err)
	}
	priority, err := value_objects.NewPriority("medium")
	if err != nil {
		t.Fatalf("priority: %v", err)
	}
	task := &entities.Task{
		Status:          new(status),
		Priority:        new(priority),
		Title:           "created",
		Description:     "a task the create path just wrote",
		GitBranchID:     new("branch-1"),
		EstimatedEffort: "2 hours",
		Labels:          []string{"defect"},
		Assignees:       []string{"@go-dev"},
	}
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		t.Fatalf("task id: %v", err)
	}
	task.ID = &id

	sync := zpTaskCtxSyncNew(&ctxWriteTaskRepo{task: task}, nil, &user, ctxServiceAdapter{svc}, nil)
	if _, err := sync.SyncContextAndGetTask(context.Background(), taskID, user, "project-1", "main"); err != nil {
		t.Fatalf("sync_context_and_get_task: %v", err)
	}

	if appender.count != 1 {
		t.Fatalf("context updates = %d, want exactly 1: a create must not write the same context twice (hub 26e857b0)", appender.count)
	}
	if appender.lastKind != entities.TaskEventKindContextUpdated {
		t.Fatalf("kind = %q, want context_updated", appender.lastKind)
	}
	if appender.lastPayload["level"] != "task" {
		t.Fatalf("level = %v, want task", appender.lastPayload["level"])
	}

	stored, ok := repo.store[taskID].(*entities.TaskContextUnified)
	if !ok {
		t.Fatalf("stored context is %T", repo.store[taskID])
	}
	for _, key := range []string{"title", "assignees", "estimated_effort"} {
		if _, present := stored.TaskData[key]; !present {
			t.Fatalf("the one write left %q out of task_data: %v", key, stored.TaskData)
		}
	}
}

// ctxServiceAdapter is the two-argument CreateContext the sync service's interface declares.
type ctxServiceAdapter struct{ *UnifiedContextService }

func (a ctxServiceAdapter) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error) {
	return a.UnifiedContextService.CreateContext(ctx, level, contextID, data, userID, nil, false)
}

func (a ctxServiceAdapter) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool) (*entities.OrderedMap[any], error) {
	return a.UnifiedContextService.UpdateContext(ctx, level, contextID, data, propagateChanges, nil)
}

// countingContextAppender is the ledger seam: it records how many context updates the service wrote,
// and the payload the last one carried.
type countingContextAppender struct {
	count       int
	lastKind    entities.TaskEventKind
	lastPayload map[string]any
}

func (a *countingContextAppender) Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

func (a *countingContextAppender) RecordContextUpdate(ctx context.Context, taskID, level string, version int,
	origin string, changes []entities.ContextChange, dropped int) (*entities.TaskEvent, error) {
	a.count++
	a.lastKind = entities.TaskEventKindContextUpdated
	a.lastPayload = entities.ContextUpdatePayload(level, taskID, version, origin, changes, dropped)
	return &entities.TaskEvent{}, nil
}

// ctxWriteTaskRepo serves the one read SyncContextAndGetTask's trailing get_task performs.
type ctxWriteTaskRepo struct {
	repositories.TaskRepository
	task *entities.Task
}

func (r *ctxWriteTaskRepo) FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error) {
	return r.task, nil
}

// The other half of the same defect (hub task 4138904d): a task-level progress note is readable from
// the task node. A task's details ARE its `progress` ledger events, so a note that only reached
// implementation_notes.progress_updates could never appear there. This pins the ledger write and its
// content, which is what Task.ProgressTextWith renders.
func TestAddProgressReachesTheTaskLedger(t *testing.T) {
	const taskID = "22222222-2222-2222-2222-222222222222"
	user := "user-1"

	repo := newZucsFakeRepo()
	repo.store[taskID] = zucsTaskContext(taskID, "todo")

	appender := &countingCollectionAppender{}
	svc := NewUnifiedContextService(repo, repo, repo, repo, nil, nil, nil, nil, &user).WithEventAppender(appender)

	if _, err := svc.AddProgress(context.Background(), "task", taskID, "the note a board reader must see", nil); err != nil {
		t.Fatalf("add_progress: %v", err)
	}

	var progress []entities.AppendTaskEvent
	for _, ev := range appender.events {
		if ev.Kind == entities.TaskEventKindProgress {
			progress = append(progress, ev)
		}
	}
	if len(progress) != 1 {
		t.Fatalf("progress events = %d, want exactly 1: %+v", len(progress), appender.events)
	}
	if got, _ := progress[0].Payload["content"].(string); got != "the note a board reader must see" {
		t.Fatalf("the progress event's content = %q", got)
	}
	if progress[0].TaskID != taskID {
		t.Fatalf("the progress event's task = %q", progress[0].TaskID)
	}

	// The same event, rendered the way the board item renders details.
	rendered := (&entities.Task{}).ProgressTextWith([]*entities.TaskEvent{{
		Kind:    entities.TaskEventKindProgress,
		Payload: progress[0].Payload,
	}})
	if !strings.Contains(rendered, "the note a board reader must see") {
		t.Fatalf("details do not render the note: %q", rendered)
	}
}

// countingCollectionAppender keeps every appended event, so a test can assert on the set.
type countingCollectionAppender struct {
	events []entities.AppendTaskEvent
}

func (a *countingCollectionAppender) Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	a.events = append(a.events, in)
	return &entities.TaskEvent{}, nil
}

func (a *countingCollectionAppender) RecordContextUpdate(ctx context.Context, taskID, level string, version int,
	origin string, changes []entities.ContextChange, dropped int) (*entities.TaskEvent, error) {
	a.events = append(a.events, entities.AppendTaskEvent{
		TaskID:  taskID,
		Kind:    entities.TaskEventKindContextUpdated,
		Payload: entities.ContextUpdatePayload(level, taskID, version, origin, changes, dropped),
	})
	return &entities.TaskEvent{}, nil
}
