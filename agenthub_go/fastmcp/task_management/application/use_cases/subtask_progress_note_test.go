package use_cases

// The note a manage_subtask update or complete carries is MANDATORY on that tool path (the schema
// declares progress_notes required for both, and the handler refuses one without it), and since O1c
// dropped the progress columns the ledger is its only home. Both use cases read the field and wrote it
// nowhere: a note the caller was REQUIRED to send reached no reader at all. These cases pin the write
// where it has to happen - one entry, in the PARENT task's ledger, naming the subtask that wrote it.

import (
	"context"
	"errors"
	"testing"

	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// subtaskNoteLedger records the ledger write a subtask update makes, including the subtask the note
// names - the part a task-level case cannot see.
type subtaskNoteLedger struct {
	writes    int
	taskID    string
	subtaskID string
	note      entities.ProgressEntry
}

func (l *subtaskNoteLedger) StatusOf(context.Context, string) (string, error) {
	return "unchanged", nil
}

func (l *subtaskNoteLedger) RecordStatusChange(context.Context, string, string, string) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

func (l *subtaskNoteLedger) RecordProgress(_ context.Context, taskID, subtaskID string, note entities.ProgressEntry) (*entities.TaskEvent, error) {
	l.writes++
	l.taskID, l.subtaskID, l.note = taskID, subtaskID, note
	return &entities.TaskEvent{}, nil
}

// NextProgressNumberInTx answers 1: the fixture's task has no note yet, and this case asserts the note
// the ledger is HANDED rather than the numbering rule (that lives in the ledger's own tests).
func (l *subtaskNoteLedger) NextProgressNumberInTx(context.Context, string) (int, error) {
	return 1, nil
}

func (l *subtaskNoteLedger) RecordGateVerdict(context.Context, string, map[string]any) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{Kind: entities.TaskEventKindGateVerdict}, nil
}

func (l *subtaskNoteLedger) ActorOf(context.Context) (entities.TaskEventActorKind, string, bool) {
	return entities.TaskEventActorHuman, "test-user", true
}

func (l *subtaskNoteLedger) Events(context.Context, string) ([]*entities.TaskEvent, error) {
	return nil, nil
}

// newSubtaskNoteFixture builds a parent task, one persisted subtask, and the seam that records what a
// note write reaches.
func newSubtaskNoteFixture(t *testing.T) (*entities.Task, *entities.Subtask, *draftSubtaskRepo, *subtaskNoteLedger) {
	t.Helper()
	task := draftNewTask(t, "parent")
	subID := value_objects.GenerateSubtaskId(*task.ID, nil)
	sub, err := entities.CreateSubtask(subID, "child", "", *task.ID, nil, nil, entities.SubtaskOptions{})
	if err != nil {
		t.Fatal(err)
	}
	return task, sub, &draftSubtaskRepo{subtasks: map[string]*entities.Subtask{subID.Value: sub}}, &subtaskNoteLedger{}
}

func TestUpdateSubtaskRecordsItsNoteInTheParentTasksLedger(t *testing.T) {
	task, sub, subRepo, ledger := newSubtaskNoteFixture(t)
	taskRepo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}
	note := "wired the parser and its case"

	resp, err := NewUpdateSubtaskUseCase(taskRepo, subRepo).
		WithLedger(StatusLedger{Tx: &ledgerFakeTx{}, Ledger: ledger, Events: ledger}).
		Execute(context.Background(), &subtaskdto.UpdateSubtaskRequest{
			TaskID: task.ID.Value, ID: sub.ID.Value, ProgressNotes: &note,
		})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if resp == nil || resp.Subtask == nil {
		t.Fatal("response carries no subtask")
	}
	if ledger.writes != 1 {
		t.Fatalf("ledger writes = %d, want 1: the note this update REQUIRES reached no reader", ledger.writes)
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
	if ledger.note.Number != 1 {
		t.Fatalf("note number = %v, want 1: a task whose ledger holds no note yet starts there", ledger.note.Number)
	}
	if want := value_objects.IsoFormat(*sub.UpdatedAt); ledger.note.Timestamp != want {
		t.Fatalf("note timestamp = %q, want the subtask's own touched instant %q", ledger.note.Timestamp, want)
	}
	if sub.UpdatedAt == nil {
		t.Fatal("the subtask was not touched: a note is a write to it")
	}
}

func TestUpdateSubtaskWithoutANoteWritesNoLedgerEntry(t *testing.T) {
	task, sub, subRepo, ledger := newSubtaskNoteFixture(t)
	taskRepo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}
	title := "renamed"

	if _, err := NewUpdateSubtaskUseCase(taskRepo, subRepo).
		WithLedger(StatusLedger{Tx: &ledgerFakeTx{}, Ledger: ledger, Events: ledger}).
		Execute(context.Background(), &subtaskdto.UpdateSubtaskRequest{
			TaskID: task.ID.Value, ID: sub.ID.Value, Title: &title,
		}); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if ledger.writes != 0 {
		t.Fatalf("ledger writes = %d, want 0: an update with no note records nothing", ledger.writes)
	}
	if sub.Title != "renamed" {
		t.Fatalf("subtask title = %q, want the update applied", sub.Title)
	}
}

func TestUpdateSubtaskRecordsNothingForAWhitespaceOnlyNote(t *testing.T) {
	task, sub, subRepo, ledger := newSubtaskNoteFixture(t)
	taskRepo := &draftTaskRepo{tasks: map[string]*entities.Task{task.ID.Value: task}}
	blank := "   \n\t "

	if _, err := NewUpdateSubtaskUseCase(taskRepo, subRepo).
		WithLedger(StatusLedger{Tx: &ledgerFakeTx{}, Ledger: ledger, Events: ledger}).
		Execute(context.Background(), &subtaskdto.UpdateSubtaskRequest{
			TaskID: task.ID.Value, ID: sub.ID.Value, ProgressNotes: &blank,
		}); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if ledger.writes != 0 {
		t.Fatalf("ledger writes = %d, want 0: a blank note is nothing to record, not an entry with an empty body", ledger.writes)
	}
	if len(subRepo.saved) == 0 {
		t.Fatal("the subtask was not saved: a blank note skips the entry, not the update")
	}
}

// The note a manage_subtask COMPLETE carries is MANDATORY on the same tool path - the tool's schema
// declares progress_notes required for complete as well - and it takes the same road into the same
// ledger: one entry, in the PARENT task's ledger, naming the subtask that wrote it, written inside the
// completion's own transaction. The sibling action used to accept that note, report success and write
// it nowhere.

func TestCompleteSubtaskRecordsItsNoteInTheParentTasksLedger(t *testing.T) {
	const parent = "22222222-2222-2222-2222-222222222222"
	const subtaskID = parent + ".001"
	note := "final review completed, structure documented"

	task := group3NewTask(parent, []string{subtaskID}, 0)
	taskRepo := &useCasesGroup3FakeTaskRepository{
		findByID: func(context.Context, value_objects.TaskId) (*entities.Task, error) { return task, nil },
		atomic:   func(context.Context, string) (bool, error) { return true, nil },
	}
	subtask := group3NewSubtask(subtaskID, parent)
	subRepo := &useCasesGroup3FakeSubtaskRepository{
		findByID: func(context.Context, string) (*entities.Subtask, error) { return subtask, nil },
	}
	ledger := &subtaskNoteLedger{}
	summary := "implemented the endpoint with tests and documented it in the changelog"

	if _, err := NewCompleteSubtaskUseCase(taskRepo, subRepo).
		WithLedger(StatusLedger{Tx: &ledgerFakeTx{}, Ledger: ledger, Events: ledger}).
		Execute(context.Background(), parent, subtaskID, nil, &summary, nil, nil, &note); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if ledger.writes != 1 {
		t.Fatalf("ledger writes = %d, want 1: the note this completion REQUIRES reached no reader", ledger.writes)
	}
	if ledger.taskID != parent {
		t.Fatalf("note recorded against %q, want the parent task %q: task_events.task_id is the parent's",
			ledger.taskID, parent)
	}
	if ledger.subtaskID != subtaskID {
		t.Fatalf("note names subtask %q, want %q: subtask_id is what tells a task's own notes from its subtask's",
			ledger.subtaskID, subtaskID)
	}
	if want := "=== Progress 1 ===\n" + note; ledger.note.Content != want {
		t.Fatalf("note content = %q, want %q", ledger.note.Content, want)
	}
	if want := value_objects.IsoFormat(*subtask.UpdatedAt); ledger.note.Timestamp != want {
		t.Fatalf("note timestamp = %q, want the completion's own touched instant %q", ledger.note.Timestamp, want)
	}
	if !subtask.IsCompleted() {
		t.Fatal("the subtask was not completed")
	}
	if subRepo.saveCalls != 1 {
		t.Fatalf("subtask save calls = %d, want 1", subRepo.saveCalls)
	}
}

func TestCompleteSubtaskWithoutALedgerRefusesRatherThanDroppingTheNote(t *testing.T) {
	const parent = "33333333-3333-3333-3333-333333333333"
	const subtaskID = parent + ".001"
	note := "final review completed, structure documented"

	task := group3NewTask(parent, []string{subtaskID}, 0)
	taskRepo := &useCasesGroup3FakeTaskRepository{
		findByID: func(context.Context, value_objects.TaskId) (*entities.Task, error) { return task, nil },
	}
	subtask := group3NewSubtask(subtaskID, parent)
	subRepo := &useCasesGroup3FakeSubtaskRepository{
		findByID: func(context.Context, string) (*entities.Subtask, error) { return subtask, nil },
	}
	summary := "implemented the endpoint with tests and documented it in the changelog"

	if _, err := NewCompleteSubtaskUseCase(taskRepo, subRepo).
		Execute(context.Background(), parent, subtaskID, nil, &summary, nil, nil, &note); !errors.Is(err, ErrLedgerNotWired) {
		t.Fatalf("err = %v, want ErrLedgerNotWired: a completion that drops its note must fail, not succeed quietly", err)
	}
	if subRepo.saveCalls != 0 {
		t.Fatalf("subtask save calls = %d, want 0: the completion must not commit beside a note it never wrote", subRepo.saveCalls)
	}
}

func TestCompleteSubtaskWithoutANoteWritesNoLedgerEntry(t *testing.T) {
	const parent = "44444444-4444-4444-4444-444444444444"
	const subtaskID = parent + ".001"

	task := group3NewTask(parent, []string{subtaskID}, 0)
	taskRepo := &useCasesGroup3FakeTaskRepository{
		findByID: func(context.Context, value_objects.TaskId) (*entities.Task, error) { return task, nil },
		atomic:   func(context.Context, string) (bool, error) { return true, nil },
	}
	subtask := group3NewSubtask(subtaskID, parent)
	subRepo := &useCasesGroup3FakeSubtaskRepository{
		findByID: func(context.Context, string) (*entities.Subtask, error) { return subtask, nil },
	}
	ledger := &subtaskNoteLedger{}
	summary := "implemented the endpoint with tests and documented it in the changelog"

	if _, err := NewCompleteSubtaskUseCase(taskRepo, subRepo).
		WithLedger(StatusLedger{Tx: &ledgerFakeTx{}, Ledger: ledger, Events: ledger}).
		Execute(context.Background(), parent, subtaskID, nil, &summary, nil, nil, nil); err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if ledger.writes != 0 {
		t.Fatalf("ledger writes = %d, want 0: a completion with no note records nothing", ledger.writes)
	}
	if subRepo.saveCalls != 1 {
		t.Fatalf("subtask save calls = %d, want 1: no note skips the entry, not the completion", subRepo.saveCalls)
	}
}
