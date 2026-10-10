package use_cases

// O1b: every status write path emits status_changed, with old and new, in the same transaction as
// the status. These tests drive the two use cases that write a task's status and assert both
// observations: what the status was before the call, what it is after, and what the ledger recorded
// for the transition. The fake repository keeps the persisted status separately from the entity, so
// the ledger reads the row's value - "todo" before the save, the new value after it - exactly as the
// database does. Whether a failure of the entry insert really leaves the status unchanged is a
// property of the transaction and is proven against a real Postgres, not here.

import (
	"context"
	"testing"

	dtotask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ledgerFakeRepo is a task repository whose Saved status is what the ledger reads back, the way the
// database row holds it: the entity moving through the use case does not change `rows` until Save.
type ledgerFakeRepo struct {
	repositories.TaskRepository
	task     *entities.Task
	allTasks []*entities.Task
	rows     map[string]string
	saves    []*entities.Task
}

func (f *ledgerFakeRepo) FindByID(_ context.Context, _ value_objects.TaskId) (*entities.Task, error) {
	return f.task, nil
}

func (f *ledgerFakeRepo) FindAll(_ context.Context) ([]*entities.Task, error) {
	return f.allTasks, nil
}

func (f *ledgerFakeRepo) Save(_ context.Context, task *entities.Task) (*entities.Task, error) {
	f.saves = append(f.saves, task)
	if f.rows == nil {
		f.rows = map[string]string{}
	}
	if task != nil && task.ID != nil && task.Status != nil {
		f.rows[task.ID.Value] = task.Status.Value
	}
	return task, nil
}

// ledgerFakeRecorder records the entries the real recorder would write, and reads the status out of
// the repository's persisted rows. It cannot show atomicity - the fake transaction just runs the
// unit of work - which is why the negative case is a real-Postgres test.
type ledgerFakeRecorder struct {
	repo    *ledgerFakeRepo
	entries []ledgerEntry
}

type ledgerEntry struct {
	taskID string
	old    string
	new    string
	actor  string
}

func (f *ledgerFakeRecorder) StatusOf(_ context.Context, taskID string) (string, error) {
	return f.repo.rows[taskID], nil
}

func (f *ledgerFakeRecorder) RecordStatusChange(_ context.Context, taskID, oldStatus, newStatus, actorID string) (*entities.TaskEvent, error) {
	f.entries = append(f.entries, ledgerEntry{taskID: taskID, old: oldStatus, new: newStatus, actor: actorID})
	return &entities.TaskEvent{TaskID: taskID, Kind: entities.TaskEventKindStatusChanged}, nil
}

// ledgerFakeTx counts the transactions the use case opens, the one unit of work SaveStatus needs.
type ledgerFakeTx struct {
	begun  int
	failed int
}

func (t *ledgerFakeTx) Transaction(ctx context.Context, fn func(ctx context.Context) error) error {
	t.begun++
	if err := fn(ctx); err != nil {
		t.failed++
		return err
	}
	return nil
}

// ledgerTask builds a task in the given status, which the repository also reports as persisted.
func ledgerTask(t *testing.T, idValue, status string) (*entities.Task, *ledgerFakeRepo) {
	t.Helper()
	id := createTaskMustID(t, idValue)
	st, err := value_objects.NewTaskStatus(status)
	if err != nil {
		t.Fatalf("NewTaskStatus(%q): %v", status, err)
	}
	task, err := entities.NewTask(entities.Task{ID: &id, Title: "Ledger subject", Description: "d"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	task.Status = &st
	repo := &ledgerFakeRepo{task: task, rows: map[string]string{idValue: status}}
	return task, repo
}

// TestUpdateTaskWritesStatusChangedWithOldAndNew is the write path update_task.go: the status moves
// and the entry reports the move, in one transaction.
func TestUpdateTaskWritesStatusChangedWithOldAndNew(t *testing.T) {
	const idValue = "44444444-4444-4444-4444-444444444444"
	task, repo := ledgerTask(t, idValue, "todo")
	rec := &ledgerFakeRecorder{repo: repo}
	tx := &ledgerFakeTx{}
	uc := NewUpdateTaskUseCase(repo, nil).WithLedger(StatusLedger{Tx: tx, Ledger: rec})

	before := repo.rows[idValue]
	status := "in_progress"
	if _, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue, Status: &status}); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	after := repo.rows[idValue]
	t.Logf("OBSERVED update_task: task %s status before=%q after=%q", idValue, before, after)

	if before != "todo" || after != "in_progress" {
		t.Fatalf("status before=%q after=%q, want todo -> in_progress", before, after)
	}
	if len(rec.entries) != 1 {
		t.Fatalf("entries = %d (%+v), want exactly 1", len(rec.entries), rec.entries)
	}
	if got := rec.entries[0]; got.old != "todo" || got.new != "in_progress" {
		t.Fatalf("entry = %+v, want old=todo new=in_progress", got)
	}
	if task.Status.Value != "in_progress" {
		t.Fatalf("entity status = %q, want in_progress", task.Status.Value)
	}
	if tx.begun != 1 || tx.failed != 0 {
		t.Fatalf("transactions begun=%d failed=%d, want 1 and 0", tx.begun, tx.failed)
	}
}

// TestUpdateTaskWithNoStatusMoveWritesNoEntry pins the ledger's rule that it records changes, not
// saves: the request carries the status the task already has, so nothing is recorded and the save
// still happens.
func TestUpdateTaskWithNoStatusMoveWritesNoEntry(t *testing.T) {
	const idValue = "55555555-5555-4555-8555-555555555555"
	_, repo := ledgerTask(t, idValue, "todo")
	rec := &ledgerFakeRecorder{repo: repo}
	tx := &ledgerFakeTx{}
	uc := NewUpdateTaskUseCase(repo, nil).WithLedger(StatusLedger{Tx: tx, Ledger: rec})

	status := "todo"
	if _, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{TaskID: idValue, Status: &status}); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if len(rec.entries) != 0 {
		t.Fatalf("entries = %+v, want none for an unmoved status", rec.entries)
	}
	if len(repo.saves) != 1 {
		t.Fatalf("saves = %d, want 1", len(repo.saves))
	}
}

// TestCompleteTaskWritesStatusChangedForEveryMove drives complete_task.go, which performs three
// status writes: the completing task moves todo -> in_progress and then in_progress -> done, and a
// dependent task moves blocked -> todo. Each carries its own entry, and the observations are logged
// from the rows the repository persisted.
func TestCompleteTaskWritesStatusChangedForEveryMove(t *testing.T) {
	const idA = "66666666-6666-4666-8666-666666666666"
	const idBValue = "77777777-7777-4777-8777-777777777777"
	taskA, repo := ledgerTask(t, idA, "todo")

	idB, err := value_objects.NewTaskId(idBValue)
	if err != nil {
		t.Fatalf("NewTaskId: %v", err)
	}
	taskB, err := entities.NewTask(entities.Task{ID: &idB, Title: "Dependent", Description: "d"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	blocked, _ := value_objects.NewTaskStatus("blocked")
	taskB.Status = &blocked
	taskB.Dependencies = []value_objects.TaskId{*taskA.ID}
	repo.allTasks = []*entities.Task{taskA, taskB}
	repo.rows[idBValue] = "blocked"

	rec := &ledgerFakeRecorder{repo: repo}
	tx := &ledgerFakeTx{}
	uc := NewCompleteTaskUseCase(repo, &completeTaskFakeSubtaskRepository{}, nil, nil).
		WithLedger(StatusLedger{Tx: tx, Ledger: rec})

	beforeA, beforeB := repo.rows[idA], repo.rows[idBValue]
	summary := "done"
	if _, err := uc.Execute(context.Background(), idA, &summary, nil, nil); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	t.Logf("OBSERVED complete_task: %s before=%q after=%q; %s before=%q after=%q",
		idA, beforeA, repo.rows[idA], idBValue, beforeB, repo.rows[idBValue])

	if repo.rows[idA] != "done" {
		t.Fatalf("completing task status = %q, want done", repo.rows[idA])
	}
	if repo.rows[idBValue] != "todo" {
		t.Fatalf("dependent task status = %q, want todo", repo.rows[idBValue])
	}
	want := []ledgerEntry{
		{taskID: idA, old: "todo", new: "in_progress"},
		{taskID: idA, old: "in_progress", new: "done"},
		{taskID: idBValue, old: "blocked", new: "todo"},
	}
	if len(rec.entries) != len(want) {
		t.Fatalf("entries = %+v, want %+v", rec.entries, want)
	}
	for i, w := range want {
		got := rec.entries[i]
		if got.taskID != w.taskID || got.old != w.old || got.new != w.new {
			t.Fatalf("entry %d = %+v, want %+v", i, got, w)
		}
		if got.actor != entities.TaskEventActorSystemID {
			t.Fatalf("entry %d actor = %q, want %q", i, got.actor, entities.TaskEventActorSystemID)
		}
	}
}
