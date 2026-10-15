package entities

import "time"

// TaskAuditKind is the closed vocabulary of the records the task lifecycle sweep writes to the
// audit trail: what the sweep did to a task, in the sweep's own words. The database declares the
// same set as a CHECK constraint, so a kind that skips these constants is refused where the bytes
// land rather than only where they are made.
type TaskAuditKind string

const (
	// TaskAuditKindEscalated is one step of the priority climb: the record names the step it reached.
	TaskAuditKindEscalated TaskAuditKind = "escalated"
	// TaskAuditKindBlocked is the sweep handing a critical task to a human; its detail IS the blocker
	// text, which is the record the blocked state keeps.
	TaskAuditKindBlocked TaskAuditKind = "blocked"
	// TaskAuditKindPruned is a completed task the sweep deleted. This is the record that keeps a
	// task's completion summary and evidence after its row is gone.
	TaskAuditKindPruned TaskAuditKind = "pruned"
)

// TaskAuditKindValues lists the vocabulary in database-declaration order, which is the order the
// CHECK constraint in the table's DDL lists: the two must not drift, because a value the Go side
// offers and the database refuses fails where the bytes land rather than where they are chosen.
var TaskAuditKindValues = []TaskAuditKind{
	TaskAuditKindEscalated,
	TaskAuditKindBlocked,
	TaskAuditKindPruned,
}

// TaskAuditRecord is one row of the task audit trail: the append-only record of what the lifecycle
// sweep did to a task. The trail is what makes "evidence is kept" true - the sweep NEVER prunes it.
//
// IT CARRIES NO FOREIGN KEY TO tasks, ON PURPOSE. The record a prune writes must OUTLIVE the row it
// describes, and the row is deleted in the same sweep: task_events, the other history, hangs off
// tasks.id and is removed by the delete cascade (task_repository.go's DeleteTask), so a record kept
// there could not survive the prune it documents. The task id here is therefore a plain id rather
// than a reference the database would remove for us.
//
// Status and Priority are the task's state AFTER the write the record describes, so a reader of the
// escalation climb sees the step each record reached, and the Detail holds the words the write
// carried: the progress note that names the step for an escalation, the blocker text for a block.
type TaskAuditRecord struct {
	ID                string
	TaskID            string
	UserID            string
	Kind              TaskAuditKind
	Title             string
	Status            string
	Priority          string
	CompletionSummary string
	// Evidence is the task's evidence as the ledger held it - one entry per evidence_submitted
	// entry, verbatim, because it is the only place evidence lives and the delete removes it.
	Evidence []map[string]any
	Detail   string

	// CreatedAt is when THIS record was written, from the writer's own clock.
	CreatedAt time.Time
	// TaskCreatedAt, TaskUpdatedAt and TaskCompletedAt are what the TASK said, kept here for the same
	// reason the summary is: the delete removes the row that carried them, and a record of a task
	// nobody can read any more is only as good as the facts it froze. TaskCompletedAt is the instant
	// the prune age was measured from, nil for a task that never completed.
	TaskCreatedAt   time.Time
	TaskUpdatedAt   time.Time
	TaskCompletedAt *time.Time
}
