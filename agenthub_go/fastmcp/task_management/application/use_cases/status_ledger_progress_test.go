package use_cases

// The seam wired AND remembering, for the cases that assert a response carries the note its own
// request wrote.
//
// noopLedger is deliberately a pass-through that records nothing, which is right for the eleven cases
// that are about something else. But a progress write's response now renders the note from the
// ledger (O1c moved it out of the column), so a case that asserts that note must run against a seam
// that actually holds it - otherwise it asserts the empty string and the component it is testing is
// never exercised. These two pieces are the smallest seam that is faithful: RecordProgress keeps the
// note the use case built and hands it back as the ledger's entry, in the same payload shape the
// repository writes, so ProgressTextWith merges it exactly as it merges a real row.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// progressCapturingLedger is a StatusLedger whose recorder remembers the progress note it was given
// and whose Events reader returns that note as the task's ledger entry.
type progressCapturingLedger struct {
	event *entities.TaskEvent
}

// ledgerWithProgress returns the seam wired with the capturing recorder and reader.
func ledgerWithProgress() StatusLedger {
	c := &progressCapturingLedger{}
	return StatusLedger{Tx: &ledgerFakeTx{}, Ledger: c, Events: c}
}

func (c *progressCapturingLedger) StatusOf(context.Context, string) (string, error) {
	return "unchanged", nil
}

func (c *progressCapturingLedger) RecordStatusChange(context.Context, string, string, string) (*entities.TaskEvent, error) {
	return &entities.TaskEvent{}, nil
}

func (c *progressCapturingLedger) RecordProgress(_ context.Context, _, _ string, note entities.ProgressEntry) (*entities.TaskEvent, error) {
	c.event = &entities.TaskEvent{
		Kind: entities.TaskEventKindProgress,
		Payload: map[string]any{
			"content":         note.Content,
			"progress_number": note.Number,
		},
	}
	return c.event, nil
}

// NextProgressNumberInTx answers 1, the number a task with no note yet takes: the seam stands in for a
// ledger whose only entry is the one it is about to record.
func (c *progressCapturingLedger) NextProgressNumberInTx(context.Context, string) (int, error) {
	return 1, nil
}

func (c *progressCapturingLedger) Events(context.Context, string) ([]*entities.TaskEvent, error) {
	if c.event == nil {
		return nil, nil
	}
	return []*entities.TaskEvent{c.event}, nil
}
