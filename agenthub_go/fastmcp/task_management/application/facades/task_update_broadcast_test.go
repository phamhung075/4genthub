package facades

// The task 'updated' frame is the frame the frontend uses to refresh a task, and the authorization
// gate matches it to a browser by the user stamped on it. The port stamped the literal "system",
// because UpdateTaskRequest carries no user id - and a "system" stamp names NO real connection:
// Rule 1 needs connectionUserID == triggeringUserID, and Rule 2 can only ask the ownership checker,
// which answers for a resource it can show belongs to that connection. Every browser was therefore
// denied while create, complete and the seat frames delivered, which is the shape of the operator's
// report. This file pins the stamp to the user who acted.

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
func (r *zpUpdateRepo) FindByCriteria(context.Context, map[string]any, repositories.ListQuery) ([]*entities.Task, error) {
	return nil, nil
}

// CountByCriteria is declared by both embedded interfaces too; the fake states both explicitly.
func (r *zpUpdateRepo) CountByCriteria(context.Context, map[string]any) (int, error) {
	return 0, nil
}

// LatestInProgressByAssignee is the resume-by-seat read; these cases name their task explicitly.
func (r *zpUpdateRepo) LatestInProgressByAssignee(context.Context, string) (*entities.Task, error) {
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

// The pass-through ledger seam, mirroring the one `f059e78c` wired into update_task_test.go and
// complete_task_test.go: a status write with no ledger is refused by design, so a fixture that
// exercises a status change must wire one. `StatusOf` reports the same status before and after the
// save, and the recorder writes its entry into nothing - the refusal stays exactly as it is, and
// there is no bypass for a caller that forgets.
type unmovedLedgerRecorder struct{}

func (unmovedLedgerRecorder) RecordProgress(context.Context, string, string, entities.ProgressEntry) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{Kind: entities.TaskEventKindProgress}, nil
}

func (unmovedLedgerRecorder) NextProgressNumberInTx(context.Context, string) (int, error) {
	return 1, nil
}

func (unmovedLedgerRecorder) StatusOf(context.Context, string) (string, error) {
	return "unchanged", nil
}

func (unmovedLedgerRecorder) RecordStatusChange(context.Context, string, string, string) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

func (unmovedLedgerRecorder) RecordGateVerdict(context.Context, string, map[string]any) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{Kind: entities.TaskEventKindGateVerdict}, nil
}

func (unmovedLedgerRecorder) ActorOf(context.Context) (entities.TaskEventActorKind, string, bool) {
	return entities.TaskEventActorHuman, "test-user", true
}

type passThroughTx struct{}

func (passThroughTx) Transaction(ctx context.Context, fn func(context.Context) error) error {
	return fn(ctx)
}

func noopStatusLedger() use_cases.StatusLedger {
	return use_cases.StatusLedger{Tx: passThroughTx{}, Ledger: unmovedLedgerRecorder{}}
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
		UpdateTask:    use_cases.NewUpdateTaskUseCase(repo, nil).WithLedger(noopStatusLedger()),
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
		t.Fatalf("the 'updated' frame is stamped user %q, want the acting user %q: a system stamp names no connection (Rule 1), and Rule 2 answers only for a resource it can show belongs to that connection, so the frame must name who acted", got.UserID, actor)
	}
	if len(got.Changed) != 1 || got.Changed[0] != "status" {
		t.Fatalf("changed = %v, want exactly the field the request set", got.Changed)
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

// TestTheDependencyBroadcastNamesTheFlag pins the add/remove_dependency emitter: the write changes no
// column of the task row, so its delta is the one has_dependencies flag.
func TestTheDependencyBroadcastNamesTheFlag(t *testing.T) {
	mainID, depID := "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
	repo := &zpDependencyRepo{tasks: map[string]*entities.Task{
		mainID: zpDependencyTask(t, mainID, "the task"),
		depID:  zpDependencyTask(t, depID, "the dependency"),
	}}
	capture := &zpBroadcastCapture{}
	facade := NewTaskApplicationFacade(repo, nil, TaskFacadeDeps{Notifier: capture})

	result := facade.AddDependency(context.Background(), mainID, depID)
	if !value_objects.PyTruthy(facadeDictGet(result, "success")) {
		t.Fatalf("AddDependency failed: %v", result)
	}
	if repo.saves != 1 {
		t.Fatalf("saved %d times, want 1", repo.saves)
	}
	if len(capture.tasks) != 1 {
		t.Fatalf("emitted %d task broadcasts, want 1", len(capture.tasks))
	}
	got := capture.tasks[0]
	if len(got.Changed) != 1 || got.Changed[0] != "has_dependencies" {
		t.Fatalf("changed = %v, want exactly [has_dependencies]", got.Changed)
	}
	full, ok := got.TaskData.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("task data is %T, want *entities.OrderedMap[any]", got.TaskData)
	}
	if v, _ := full.Get("has_dependencies"); v != true {
		t.Fatalf("has_dependencies = %#v, want true", v)
	}
}

type zpDependencyRepo struct {
	FacadeTaskRepository
	tasks map[string]*entities.Task
	saves int
}

func (r *zpDependencyRepo) FindByID(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	return r.tasks[id.Value], nil
}

func (r *zpDependencyRepo) FindByIDAllStates(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	return r.tasks[id.Value], nil
}

func (r *zpDependencyRepo) Save(_ context.Context, t *entities.Task) (*entities.Task, error) {
	r.saves++
	return t, nil
}

func zpDependencyTask(t *testing.T, idValue, title string) *entities.Task {
	t.Helper()
	id, err := value_objects.NewTaskId(idValue)
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
	branch, owner := "branch-1", "u-actor"
	task, err := entities.NewTask(entities.Task{
		ID: &id, Title: title, Description: "d", Status: &status, Priority: &priority,
		GitBranchID: &branch, UserID: &owner,
	})
	if err != nil {
		t.Fatal(err)
	}
	return task
}
