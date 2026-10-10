package use_cases

// A status write must record its entry, so the ledger is not optional. Before this, an unwired
// ledger ran the save and returned SUCCESS: the status committed, no entry was written, and the
// updated frame still went out - a clean success over an event that does not exist, reachable by any
// composition site that forgot to wire it, with no error anywhere. The seam now refuses instead, and
// these two pieces are what the package's other cases use to say "wired, and about something else".

import (
	"context"
	"errors"
	"testing"

	dtotask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
)

// noopLedger is the seam wired as a pass-through: the recorder reports the same status before and
// after the save, so the unit of work runs and no entry is recorded. Cases about a use case's own
// behaviour use it; what the ledger records is measured in status_ledger_test.go and in the
// real-Postgres cases.
func noopLedger() StatusLedger {
	return StatusLedger{Tx: &ledgerFakeTx{}, Ledger: noopRecorder{}}
}

type noopRecorder struct{}

func (noopRecorder) StatusOf(context.Context, string) (string, error) { return "unchanged", nil }

func (noopRecorder) RecordStatusChange(context.Context, string, string, string) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

// TestAStatusWriteWithoutALedgerIsRefused is the acceptance for the optional-ledger defect: the
// silent path must be impossible. A use case built without WithLedger does not save and does not
// succeed - it fails, naming the seam.
func TestAStatusWriteWithoutALedgerIsRefused(t *testing.T) {
	const idValue = "55555555-5555-5555-5555-555555555555"
	entity := updateTaskNewEntity(t, idValue)
	repo := &updateTaskFakeRepo{found: entity}
	uc := NewUpdateTaskUseCase(repo, nil) // deliberately NOT wired

	status, details := "in_progress", "the note that rides a status change"
	_, err := uc.Execute(context.Background(), dtotask.UpdateTaskRequest{
		TaskID: idValue, Status: &status, Details: &details,
	})
	if err == nil {
		t.Fatal("a status write succeeded with no ledger wired: that is the silent success over a missing event")
	}
	if !errors.Is(err, ErrLedgerNotWired) {
		t.Fatalf("the refusal is not the ledger's: %v", err)
	}
}
