package use_cases

import (
	"context"
	"errors"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TransactionRunner opens the one transaction a status write and its ledger entry share. Declared
// here as a shape rather than taken from the application services package, because that package
// imports this one: *database.SessionManager satisfies it.
type TransactionRunner interface {
	Transaction(ctx context.Context, fn func(ctx context.Context) error) error
}

// LedgerRecorder is the ledger as a writing use case needs it: the task's stored status, read
// inside the caller's transaction, and the two entry writes. *services.TaskEventRecorder satisfies
// it, and the recorder is the one writer of the ledger.
type LedgerRecorder interface {
	StatusOf(ctx context.Context, taskID string) (string, error)
	RecordStatusChange(ctx context.Context, taskID, oldStatus, newStatus string) (*entities.TaskEvent, error)
	RecordProgress(ctx context.Context, taskID, subtaskID string, note entities.ProgressEntry) (*entities.TaskEvent, error)
}

// LedgerProgress is one progress note a save carries into the ledger: the note as the column would
// have stored it, and the subtask that wrote it (empty for a task-level note, because the entry
// belongs to the task's ledger either way).
type LedgerProgress struct {
	SubtaskID string
	Note      entities.ProgressEntry
}

// StatusLedger is what a status-writing use case needs to make the status and its ledger entry one
// transaction: the runner that opens it and the recorder that writes the entry inside. It is wired
// from the composition root (server/httpapp/task_wiring.go). With it unset a use case writes the
// status exactly as it did before the ledger had a write side, which is what keeps every other
// caller and every other test unchanged.
type StatusLedger struct {
	Tx     TransactionRunner
	Ledger LedgerRecorder
	// Events reads the ledger's entries for one task. It belongs here because the response to a
	// progress write must carry the note that write just made, and O1c switches that note out of the
	// column: a response built from the column alone would come back one note short - its own.
	Events TaskProgressEventLister
}

// Enabled reports whether both halves are wired.
func (l StatusLedger) Enabled() bool { return l.Tx != nil && l.Ledger != nil }

// ErrLedgerNotWired is returned when a status write reaches an unwired ledger. It is an error rather
// than a quiet bare save because the quiet version was a lie: the status committed, NO entry was
// written, the call returned success and the updated frame still went out - a clean success over an
// event that does not exist, reachable by any composition site that forgot to wire the ledger, with
// no database breakage and no error anywhere to notice. Wiring it is the composition root's job and
// every production site does; a site that does not must fail where it is written, not where its
// events are missed.
var ErrLedgerNotWired = errors.New("status ledger is not wired: a status write must record its entry, and saving the status alone would be a silent success over a missing event")

// Save runs save inside the one transaction that also carries the status_changed entry for the
// transition save makes AND the progress entries for the notes it writes, so a failure of any of them
// leaves none - which is the property the negative case checks by forcing an entry's insert to fail.
//
// The task's status is read from the row inside that transaction, before and after save, so an
// entry reports the transition the ROW made rather than one this process believed it was making,
// and no entry is written when the status did not move: the ledger records changes, not saves.
// WHO the write is attributed to is the recorder's to decide, from the request itself, so a use
// case has no name to invent and passes none.
//
// The progress entries are written AFTER save, and that ordering is the whole reason they are here
// rather than at the call site: task_events.task_id has an FK to tasks.id, so a note written before
// the row it belongs to exists cannot be inserted, and one written outside this transaction could
// commit beside a save that rolled back.
func (l StatusLedger) Save(ctx context.Context, save func(context.Context) error,
	taskID string, progressNotes []LedgerProgress) error {
	if !l.Enabled() {
		return ErrLedgerNotWired
	}
	return l.Tx.Transaction(ctx, func(ctx context.Context) error {
		from, err := l.Ledger.StatusOf(ctx, taskID)
		if err != nil {
			return err
		}
		if err := save(ctx); err != nil {
			return err
		}
		to, err := l.Ledger.StatusOf(ctx, taskID)
		if err != nil {
			return err
		}
		if from != to {
			if _, err := l.Ledger.RecordStatusChange(ctx, taskID, from, to); err != nil {
				return err
			}
		}
		for _, progress := range progressNotes {
			if _, err := l.Ledger.RecordProgress(ctx, taskID, progress.SubtaskID, progress.Note); err != nil {
				return err
			}
		}
		return nil
	})
}

// SaveProgress is Save without the status half, for the two callers that have no transition to
// record: creating a task (which could not read a status from a row that does not exist yet) and
// writing a subtask note (whose transition is the subtask's, not the parent task's). It still owns
// the transaction, because the entry has to share it with the save.
func (l StatusLedger) SaveProgress(ctx context.Context, save func(context.Context) error,
	taskID string, progressNotes []LedgerProgress) error {
	if !l.Enabled() {
		return ErrLedgerNotWired
	}
	return l.Tx.Transaction(ctx, func(ctx context.Context) error {
		if err := save(ctx); err != nil {
			return err
		}
		for _, progress := range progressNotes {
			if _, err := l.Ledger.RecordProgress(ctx, taskID, progress.SubtaskID, progress.Note); err != nil {
				return err
			}
		}
		return nil
	})
}

// ledgerTaskID reads an entity's id, empty when it has none.
func ledgerTaskID(task *entities.Task) string {
	if task == nil || task.ID == nil {
		return ""
	}
	return task.ID.Value
}
