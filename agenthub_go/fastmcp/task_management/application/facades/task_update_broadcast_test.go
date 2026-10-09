package facades

// The task 'updated' frame is the frame the frontend uses to refresh a task, and the authorization
// gate matches it to a browser by the user stamped on it. The port stamped the literal "system",
// because UpdateTaskRequest carries no user id - and a "system" stamp matches NO real connection:
// Rule 1 needs connectionUserID == triggeringUserID, and Rule 2's ownership check has no
// implementation to consult (websocket_routes.go:323). Every browser is therefore denied while
// create, complete and the seat frames deliver, which is the shape of the operator's report. This
// file pins the stamp to the user who acted.

import (
	"context"
	"testing"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpBroadcastCapture records the task events the facade emits. TaskFacadeNotifier has three
// methods; the two the update path does not use are no-ops here.
type zpBroadcastCapture struct {
	tasks []services.SyncTaskEventParams
}

func (c *zpBroadcastCapture) SyncBroadcastTask(_ context.Context, p services.SyncTaskEventParams) error {
	c.tasks = append(c.tasks, p)
	return nil
}

func (c *zpBroadcastCapture) SyncBroadcastBranchEvent(string, string, string, *string, *entities.OrderedMap[any]) {
}

func (c *zpBroadcastCapture) TaskContext(context.Context, string, *string) *entities.OrderedMap[any] {
	return nil
}

// zpUpdateRepo serves a FRESH copy per read, because the facade and the use case read the task
// SEPARATELY. Sharing one pointer would let the pre-update snapshot carry the mutations the use
// case applied, which is the confusion the payload half of this row exists to remove.
type zpUpdateRepo struct {
	repositories.TaskRepository
	use_cases.ListTasksTaskRepository
	task  *entities.Task
	saves int
}

// FindByCriteria is declared by BOTH embedded interfaces with the same signature, so the fake
// states it once; the update path never calls it.
func (r *zpUpdateRepo) FindByCriteria(context.Context, map[string]any, *int) ([]*entities.Task, error) {
	return nil, nil
}

func (r *zpUpdateRepo) FindByID(context.Context, value_objects.TaskId) (*entities.Task, error) {
	cp := *r.task
	return &cp, nil
}

func (r *zpUpdateRepo) Save(context.Context, *entities.Task) (*entities.Task, error) {
	r.saves++
	return r.task, nil
}

// newUpdateFacadeUnderTest builds the real facade over the real UpdateTaskUseCase, so the test
// walks the same path a browser request does: facade -> use case -> broadcast.
func newUpdateFacadeUnderTest(t *testing.T, actor string) (*TaskApplicationFacade, *zpUpdateRepo, *zpBroadcastCapture) {
	t.Helper()
	id, err := value_objects.NewTaskId("task-1")
	if err != nil {
		t.Fatal(err)
	}
	status, err := value_objects.NewTaskStatus("todo")
	if err != nil {
		t.Fatal(err)
	}
	priority, err := value_objects.NewPriority("medium")
	if err != nil {
		t.Fatal(err)
	}
	branch, owner := "branch-1", actor
	task, err := entities.NewTask(entities.Task{
		ID: &id, Title: "a task", Description: "what the task is for", Status: &status, Priority: &priority,
		GitBranchID: &branch, UserID: &owner,
	})
	if err != nil {
		t.Fatal(err)
	}
	repo := &zpUpdateRepo{task: task}
	capture := &zpBroadcastCapture{}
	facade := NewTaskApplicationFacade(repo, nil, TaskFacadeDeps{
		UpdateTask:    use_cases.NewUpdateTaskUseCase(repo, nil),
		Notifier:      capture,
		CurrentUserID: func(context.Context) *string { return &owner },
	})
	return facade, repo, capture
}

// TestTheUpdateBroadcastIsStampedWithTheActingUser is the fail-first case: with the literal
// "system" stamp the frame is refused for every connection, so the assertion fails on the parent
// and passes once the acting user is plumbed from the request context.
func TestTheUpdateBroadcastIsStampedWithTheActingUser(t *testing.T) {
	const actor = "u-actor"
	facade, repo, capture := newUpdateFacadeUnderTest(t, actor)

	newStatus := "in_progress"
	result := facade.UpdateTask(context.Background(), dtostask.UpdateTaskRequest{TaskID: "task-1", Status: &newStatus})
	if !value_objects.PyTruthy(facadeDictGet(result, "success")) {
		t.Fatalf("UpdateTask failed: %v", result)
	}
	if repo.saves != 1 {
		t.Fatalf("the use case saved %d times, want 1", repo.saves)
	}
	if len(capture.tasks) != 1 {
		t.Fatalf("the facade emitted %d task broadcasts, want 1", len(capture.tasks))
	}
	got := capture.tasks[0]
	if got.EventType != "updated" {
		t.Fatalf("event type = %q, want updated", got.EventType)
	}
	if got.UserID != actor {
		t.Fatalf("the 'updated' frame is stamped user %q, want the acting user %q: a system stamp matches no connection (Rule 1) and there is no ownership checker to fall back on (Rule 2), so EVERY browser is denied", got.UserID, actor)
	}
}

// TestTheUpdateBroadcastCarriesThePostUpdateValues is the payload half of the row. The delivered dict
// is what the frontend writes into the task it displays, and it was built from the PRE-update fetch
// that checkForMeaningfulUpdate compares against - so after delivery was fixed, a status change would
// still have arrived carrying the status the task had before it. Only updated_at came from the new row.
func TestTheUpdateBroadcastCarriesThePostUpdateValues(t *testing.T) {
	const actor = "u-actor"
	facade, _, capture := newUpdateFacadeUnderTest(t, actor)

	newStatus := "in_progress"
	result := facade.UpdateTask(context.Background(), dtostask.UpdateTaskRequest{TaskID: "task-1", Status: &newStatus})
	if !value_objects.PyTruthy(facadeDictGet(result, "success")) {
		t.Fatalf("UpdateTask failed: %v", result)
	}
	if len(capture.tasks) != 1 {
		t.Fatalf("the facade emitted %d task broadcasts, want 1", len(capture.tasks))
	}
	payload, ok := capture.tasks[0].TaskData.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("task data is %T, want *entities.OrderedMap[any]", capture.tasks[0].TaskData)
	}
	if got := value_objects.PyStr(facadeDictGet(payload, "status")); got != newStatus {
		t.Fatalf("the delivered payload carries status %q, want the post-update %q: it is built from the pre-update fetch, and the frontend writes this dict straight into the task it displays", got, newStatus)
	}
}
