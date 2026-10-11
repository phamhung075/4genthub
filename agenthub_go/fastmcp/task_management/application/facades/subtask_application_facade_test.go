package facades

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func newEmptyFacade() *SubtaskApplicationFacade {
	return NewSubtaskApplicationFacade(nil, nil, nil, nil, nil)
}

func TestHandleManageSubtaskRequiresTaskID(t *testing.T) {
	f := newEmptyFacade()
	_, err := f.HandleManageSubtask(context.Background(), "create", "", nil, nil, false, nil, nil, nil)
	if err == nil || err.Error() != "Task ID is required" {
		t.Fatalf("got %v", err)
	}
	if _, ok := err.(*value_objects.ValueError); !ok {
		t.Fatalf("expected *ValueError, got %T", err)
	}
}

func TestHandleManageSubtaskUnsupportedAction(t *testing.T) {
	f := newEmptyFacade()
	_, err := f.HandleManageSubtask(context.Background(), "frobnicate", "task-1", nil, nil, false, nil, nil, nil)
	if err == nil || err.Error() != "Unsupported subtask action: frobnicate" {
		t.Fatalf("got %v", err)
	}
}

func TestHandleManageSubtaskAddAliasNormalisesToCreate(t *testing.T) {
	f := newEmptyFacade()
	data := entities.NewOrderedMap[any]()
	// Missing title -> create validation error, proving "add" routed to create.
	_, err := f.HandleManageSubtask(context.Background(), "ADD", "task-1", data, nil, false, nil, nil, nil)
	if err == nil || err.Error() != "subtask_data with title is required" {
		t.Fatalf("got %v", err)
	}
}

func TestCreateSubtaskMissingArguments(t *testing.T) {
	f := newEmptyFacade()
	_, err := f.CreateSubtask(context.Background(), CreateSubtaskParams{})
	if err == nil || !strings.Contains(err.Error(), "missing required argument: 'task_id'") {
		t.Fatalf("got %v", err)
	}
	tid := "task-1"
	_, err = f.CreateSubtask(context.Background(), CreateSubtaskParams{TaskID: &tid})
	if err == nil || !strings.Contains(err.Error(), "missing required argument: 'title'") {
		t.Fatalf("got %v", err)
	}
}

func TestDeleteSubtaskRequiresIDs(t *testing.T) {
	f := newEmptyFacade()
	if _, err := f.DeleteSubtask(context.Background(), "", "s1", nil); err == nil ||
		err.Error() != "task_id and subtask_id are required" {
		t.Fatalf("got %v", err)
	}
	if _, err := f.CompleteSubtask(context.Background(), "t1", "", nil, nil); err == nil ||
		err.Error() != "task_id and subtask_id are required" {
		t.Fatalf("got %v", err)
	}
}

// zpSubtaskRepo serves one subtask. The repository interface is wide; the update path reads by id and
// saves, so the rest is left to the embedded interface - a call the path does not make is a call this
// fake should not answer.
type zpSubtaskRepo struct {
	repositories.SubtaskRepository
	sub   *entities.Subtask
	saves int
}

func (r *zpSubtaskRepo) FindByID(context.Context, string) (*entities.Subtask, error) {
	return r.sub, nil
}

func (r *zpSubtaskRepo) Save(context.Context, *entities.Subtask) (bool, error) {
	r.saves++
	return true, nil
}

// zpNoteLedger records what a note write reaches, the subtask it names included.
type zpNoteLedger struct {
	writes    int
	taskID    string
	subtaskID string
	note      entities.ProgressEntry
}

func (l *zpNoteLedger) StatusOf(context.Context, string) (string, error) { return "unchanged", nil }

func (l *zpNoteLedger) RecordStatusChange(context.Context, string, string, string) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

func (l *zpNoteLedger) RecordProgress(_ context.Context, taskID, subtaskID string, note entities.ProgressEntry) (*entities.TaskEvent, error) {
	l.writes++
	l.taskID, l.subtaskID, l.note = taskID, subtaskID, note
	return &entities.TaskEvent{}, nil
}

func (l *zpNoteLedger) NextProgressNumberInTx(context.Context, string) (int, error) { return 1, nil }

func (l *zpNoteLedger) Events(context.Context, string) ([]*entities.TaskEvent, error) {
	return nil, nil
}

// TestHandleManageSubtaskUpdateHandsTheNoteToTheWiredLedger pins the LINK between the two halves of the
// subtask-note fix. The write itself is pinned in application/use_cases and, over a real database, in
// infrastructure/database. What neither of those can see is the wire the composition root builds: the
// subtask factory constructs the facade WITH its repositories (factories/subtask_facade_factory.go),
// which builds the update use case there and then, and only afterwards does the caller
// (server/httpapp/subtask_wiring.go) call WithLedger. A facade that kept the ledger to itself - setting
// the field but not the use case it had already built - would drop every production note silently,
// which is the shape the gate found one layer down.
func TestHandleManageSubtaskUpdateHandsTheNoteToTheWiredLedger(t *testing.T) {
	const owner = "u-owner"
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
	branch, ownerPtr := "branch-1", owner
	task, err := entities.NewTask(entities.Task{
		ID: &id, Title: "parent", Description: "the parent", Status: &status, Priority: &priority,
		GitBranchID: &branch, UserID: &ownerPtr,
	})
	if err != nil {
		t.Fatal(err)
	}
	subID := value_objects.GenerateSubtaskId(id, nil)
	sub, err := entities.CreateSubtask(subID, "child", "", id, nil, nil, entities.SubtaskOptions{})
	if err != nil {
		t.Fatal(err)
	}

	subRepo := &zpSubtaskRepo{sub: sub}
	ledger := &zpNoteLedger{}
	facade := NewSubtaskApplicationFacade(&zpUpdateRepo{task: task}, subRepo, nil, nil, &ownerPtr).
		WithLedger(use_cases.StatusLedger{Tx: passThroughTx{}, Ledger: ledger, Events: ledger})

	const note = "wired the parser and its case"
	data := entities.NewOrderedMap[any]()
	data.Set("subtask_id", sub.ID.Value)
	data.Set("progress_notes", note)

	result, err := facade.HandleManageSubtask(context.Background(), "update", task.ID.Value, data, nil, true,
		nil, nil, &ownerPtr)
	if err != nil {
		t.Fatalf("HandleManageSubtask(update): %v", err)
	}
	if !value_objects.PyTruthy(facadeDictGet(result, "success")) {
		t.Fatalf("the update failed: %v", result)
	}
	if subRepo.saves != 1 {
		t.Fatalf("the subtask was saved %d times, want 1", subRepo.saves)
	}
	if ledger.writes != 1 {
		t.Fatalf("ledger writes = %d, want 1: the facade was wired with the ledger and the note reached no reader", ledger.writes)
	}
	if ledger.taskID != task.ID.Value {
		t.Fatalf("note recorded against %q, want the parent task %q: task_events.task_id is the parent's",
			ledger.taskID, task.ID.Value)
	}
	if ledger.subtaskID != sub.ID.Value {
		t.Fatalf("note names subtask %q, want %q: subtask_id is what tells a task's own notes from its subtask's",
			ledger.subtaskID, sub.ID.Value)
	}
	if want := "=== Progress 1 ===\n" + note; ledger.note.Content != want {
		t.Fatalf("note content = %q, want %q", ledger.note.Content, want)
	}
}
