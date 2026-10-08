package entities

import "time"

// TaskEvent is one row of the append-only task-event ledger: the record of what happened to a
// task, in order. It is written through the recorder and never updated or deleted, so a reader
// can reconstruct a task's history from it without trusting any mutable column.
//
// O1a only builds this ledger and the read path over it. No existing write path emits events yet,
// which is why the whole change is additive.
type TaskEvent struct {
	ID        string
	TaskID    string
	UserID    string
	Seq       int
	Kind      TaskEventKind
	ActorKind TaskEventActorKind
	ActorID   string
	Payload   map[string]any
	CreatedAt time.Time
}

// TaskEventKind is the closed vocabulary of ledger entry kinds. The database declares the same
// set as its own type, so a value that skips these constants is refused by the DB rather than
// silently stored - the vocabulary is enforced where the bytes land, not only where they are made.
type TaskEventKind string

const (
	TaskEventKindCreated       TaskEventKind = "created"
	TaskEventKindUpdated       TaskEventKind = "updated"
	TaskEventKindStatusChanged TaskEventKind = "status_changed"
	TaskEventKindCompleted     TaskEventKind = "completed"
	TaskEventKindDeleted       TaskEventKind = "deleted"
)

// TaskEventKindValues is the vocabulary in database-declaration order.
var TaskEventKindValues = []TaskEventKind{
	TaskEventKindCreated,
	TaskEventKindUpdated,
	TaskEventKindStatusChanged,
	TaskEventKindCompleted,
	TaskEventKindDeleted,
}

// TaskEventActorKind says who caused an entry: a person, the system itself, or an agent acting
// on one's behalf. Kept separate from ActorID so a reader can group by class without parsing.
type TaskEventActorKind string

const (
	TaskEventActorUser   TaskEventActorKind = "user"
	TaskEventActorSystem TaskEventActorKind = "system"
	TaskEventActorAgent  TaskEventActorKind = "agent"
)

// TaskEventActorKindValues is the vocabulary in database-declaration order.
var TaskEventActorKindValues = []TaskEventActorKind{
	TaskEventActorUser,
	TaskEventActorSystem,
	TaskEventActorAgent,
}

// AppendTaskEvent is what a caller supplies to write one entry. It lives here rather than beside
// the repository on purpose: the recorder is an application service, and it must be able to
// describe its input without importing an infrastructure package.
//
// Seq is NOT here: the database assigns it, so no caller can invent one or leave a gap.
type AppendTaskEvent struct {
	TaskID    string
	Kind      TaskEventKind
	ActorKind TaskEventActorKind
	ActorID   string
	Payload   map[string]any
}
