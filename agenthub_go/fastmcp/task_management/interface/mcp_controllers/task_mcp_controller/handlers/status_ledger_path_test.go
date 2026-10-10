package handlers

// This covers the MCP tool path for a status change: the crud_handler.go UpdateTask
// handler -> the real facades.TaskApplicationFacade -> the real
// use_cases.UpdateTaskUseCase -> the status ledger. It proves the WIRING from the tool
// surface down to the ledger (the ledger's SaveStatus is reached and records the row's
// transition), NOT the database's transactional behaviour: the transaction runner here
// is a fake that just runs the unit of work, so nothing here shows that a failing entry
// insert rolls the status back. That property belongs to a real Postgres.

import (
	"context"
	"testing"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ledgerPathRepo is a task repository whose persisted status (`rows`) is kept apart from
// the entity the use case mutates, exactly as the database row is: the ledger's StatusOf
// reads the row, which still holds the old value until Save writes the new one.
//
// FindByID hands back a copy because the facade reads the task SEPARATELY from the use
// case (getTaskForUpdateComparison); sharing one pointer would let the pre-update
// snapshot carry the mutation the use case applies.
type ledgerPathRepo struct {
	repositories.TaskRepository
	task  *entities.Task
	rows  map[string]string
	saves int
}

func (r *ledgerPathRepo) FindByID(context.Context, value_objects.TaskId) (*entities.Task, error) {
	cp := *r.task
	return &cp, nil
}

func (r *ledgerPathRepo) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	r.saves++
	r.rows[task.ID.Value] = task.Status.Value
	return task, nil
}

// GetCompletedSubtaskCounts is the one method of use_cases.ListTasksTaskRepository that
// repositories.TaskRepository does not already declare; the update path never calls it.
func (r *ledgerPathRepo) GetCompletedSubtaskCounts(context.Context, []string) (map[string]int, error) {
	return nil, nil
}

// ledgerPathRecorder is the ledger as the use case drives it: the status comes from the
// repository's persisted rows, and the entry is recorded for inspection.
type ledgerPathRecorder struct {
	repo    *ledgerPathRepo
	entries []ledgerPathEntry
}

type ledgerPathEntry struct {
	taskID string
	old    string
	new    string
}

func (f *ledgerPathRecorder) StatusOf(_ context.Context, taskID string) (string, error) {
	return f.repo.rows[taskID], nil
}

func (f *ledgerPathRecorder) RecordStatusChange(_ context.Context, taskID, oldStatus, newStatus string) (*entities.TaskEvent, error) {
	f.entries = append(f.entries, ledgerPathEntry{taskID: taskID, old: oldStatus, new: newStatus})
	return &entities.TaskEvent{TaskID: taskID, Kind: entities.TaskEventKindStatusChanged}, nil
}

// ledgerPathTx runs the unit of work without a database, the seam the ledger expects.
type ledgerPathTx struct{ begun int }

func (t *ledgerPathTx) Transaction(ctx context.Context, fn func(ctx context.Context) error) error {
	t.begun++
	return fn(ctx)
}

// ledgerPathFacade is the shape shim the MCP surface needs, not a substitute for the
// facade: handlers.TaskFacade declares pointer request DTOs, a (result, error) GetTask
// and a repositories.TaskRepository accessor, while *facades.TaskApplicationFacade has
// value DTOs and a wider accessor - which is why production keeps the same forwarding
// adapter in interface/ddd_compliant_mcp_tools_wiring.go (taskMCPFacade). Every method
// here forwards to the real facade; the update path itself runs entirely inside it.
type ledgerPathFacade struct {
	*facades.TaskApplicationFacade
}

var _ TaskFacade = ledgerPathFacade{}

func (a ledgerPathFacade) CreateTask(ctx context.Context, request *dtostask.CreateTaskRequest) *entities.OrderedMap[any] {
	return a.TaskApplicationFacade.CreateTask(ctx, *request)
}

func (a ledgerPathFacade) UpdateTask(ctx context.Context, request *dtostask.UpdateTaskRequest) *entities.OrderedMap[any] {
	return a.TaskApplicationFacade.UpdateTask(ctx, *request)
}

func (a ledgerPathFacade) GetTask(ctx context.Context, taskID string, includeContext bool) (*entities.OrderedMap[any], error) {
	return a.TaskApplicationFacade.GetTask(ctx, taskID, includeContext, true), nil
}

func (a ledgerPathFacade) CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes, userID *string) *entities.OrderedMap[any] {
	return a.TaskApplicationFacade.CompleteTask(ctx, taskID, &completionSummary, testingNotes, userID)
}

func (a ledgerPathFacade) TaskRepository() repositories.TaskRepository {
	return a.TaskApplicationFacade.TaskRepository()
}

// TestUpdateTaskHandlerReachesStatusLedger drives the MCP tool call end to end: the
// handler converts the kwargs, the real facade and the real use case run, and the ledger
// entry is written with the transition the ROW made (todo -> in_progress).
func TestUpdateTaskHandlerReachesStatusLedger(t *testing.T) {
	const idValue = "88888888-8888-4888-8888-888888888888"

	id, err := value_objects.NewTaskId(idValue)
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	todo, err := value_objects.NewTaskStatus("todo")
	if err != nil {
		t.Fatalf("NewTaskStatus: %v", err)
	}
	task, err := entities.NewTask(entities.Task{ID: &id, Title: "MCP ledger subject", Description: "d", Status: &todo})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	repo := &ledgerPathRepo{task: task, rows: map[string]string{idValue: "todo"}}
	rec := &ledgerPathRecorder{repo: repo}
	tx := &ledgerPathTx{}

	useCase := use_cases.NewUpdateTaskUseCase(repo, nil).WithHooks(nil).
		WithLedger(use_cases.StatusLedger{Tx: tx, Ledger: rec})
	facade := facades.NewTaskApplicationFacade(repo, nil, facades.TaskFacadeDeps{UpdateTask: useCase})
	handler := NewCRUDHandler(&draftFormatter{})

	before := repo.rows[idValue]
	// A status change requires `details` (crud_handler.go: status != nil makes it
	// mandatory), so the call carries the progress note the tool surface demands.
	result := handler.UpdateTask(context.Background(), ledgerPathFacade{facade}, map[string]any{
		"task_id": idValue,
		"status":  "in_progress",
		"details": "moved by the MCP path",
	})
	after := repo.rows[idValue]

	t.Logf("OBSERVED mcp update_task: task %s status before=%q after=%q entries=%d saves=%d tx=%d",
		idValue, before, after, len(rec.entries), repo.saves, tx.begun)

	if before != "todo" || after != "in_progress" {
		t.Fatalf("persisted status before=%q after=%q, want todo -> in_progress", before, after)
	}
	if result == nil {
		t.Fatal("handler returned no result")
	}
	if success, _ := result.Get("success"); success != true {
		t.Fatalf("handler result success = %v, want true (result=%v)", success, result.Keys())
	}
	if len(rec.entries) != 1 {
		t.Fatalf("ledger entries = %d (%+v), want exactly 1", len(rec.entries), rec.entries)
	}
	entry := rec.entries[0]
	t.Logf("OBSERVED ledger entry: task=%s old=%q new=%q", entry.taskID, entry.old, entry.new)
	if entry.taskID != idValue || entry.old != "todo" || entry.new != "in_progress" {
		t.Fatalf("entry = %+v, want task %s old=todo new=in_progress", entry, idValue)
	}
	if tx.begun != 1 {
		t.Fatalf("transactions begun = %d, want 1", tx.begun)
	}
}
