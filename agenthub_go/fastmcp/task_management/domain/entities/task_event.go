package entities

import "time"

// TaskEvent is one row of the append-only task-event ledger: the record of what happened to a
// task, in order. It is written through the recorder and never updated or deleted, so a reader
// can reconstruct a task's history from it without trusting any mutable column.
//
// O1a only builds this ledger and the read path over it. No existing write path emits events yet,
// which is why the whole change is additive.
type TaskEvent struct {
	ID            string
	TaskID        string
	SubtaskID     string
	UserID        string
	Seq           int
	UserSeq       int64
	Kind          TaskEventKind
	ActorKind     TaskEventActorKind
	ActorID       string
	ClientEventID string
	Payload       map[string]any
	CreatedAt     time.Time
}

// TaskEventKind is the closed vocabulary of ledger entry kinds. The database declares the same set
// as a CHECK constraint, so a value that skips these constants is refused where the bytes land
// rather than only where they are made.
//
// EVERY KIND HERE HAS A WRITER, and that is the rule this list was built on rather than a
// coincidence: architecture 2.5's vocabulary is the source of truth for the shape, and a kind in it
// that NO queued item writes is dead vocabulary - a CHECK widened to values nothing writes fails
// the same way a fallback that never fires does. `planned` is therefore NOT here: no O/P item
// writes it, and when a creation emit is queued it comes back with its owner and one word of DDL.
//
// THE SIX KINDS THAT REMAIN, each with its writer: `status_changed` (RecordStatusChange),
// `progress` (RecordProgress), `gate_verdict` (RecordGateVerdict), `evidence_submitted` (the
// evidence route), `context_updated` (the seat-attributed context path), and `handover` (the ledger
// outbox's handover payload). The ruling that closed the handover payload (task 31b72a0d) deleted
// the other six - assigned, claimed, delivered, context_loaded, escalated, human_decision - because
// the ledger measured that nothing writes them and every one of their facts already has a single
// home: assignment is the task's assignees column, a claim is the status_changed write, a delivery
// is a queue row, an escalation is a task_audit_records row, an owner decision is a queue row, and
// nothing loads context through the hub.
type TaskEventKind string

const (
	TaskEventKindProgress          TaskEventKind = "progress"
	TaskEventKindStatusChanged     TaskEventKind = "status_changed"
	TaskEventKindEvidenceSubmitted TaskEventKind = "evidence_submitted"
	TaskEventKindGateVerdict       TaskEventKind = "gate_verdict"
	TaskEventKindHandover          TaskEventKind = "handover"
	TaskEventKindContextUpdated    TaskEventKind = "context_updated"
)

// TaskEventKindValues is the vocabulary in database-declaration order, which is also the order the
// CHECK constraint in the table's DDL lists: the two must not drift, because a value the Go side
// offers and the database refuses fails where the bytes land rather than where they are chosen.
var TaskEventKindValues = []TaskEventKind{
	TaskEventKindProgress,
	TaskEventKindStatusChanged,
	TaskEventKindEvidenceSubmitted,
	TaskEventKindGateVerdict,
	TaskEventKindHandover,
	TaskEventKindContextUpdated,
}

// TaskEventActorKind says who caused an entry: a seat (the seat key from the MCP header), a client
// (the machine id from the request), a gate, or a person's user id. Kept separate from ActorID so a
// reader can group by class without parsing.
//
// THERE IS NO `system` HERE, ON PURPOSE. Every entry in this ledger is attributed to whoever acted:
// when the platform performs a write on a caller's behalf - completing a task unblocks a dependent
// task, for instance - the entry carries the CALLER, because that is who acted. A recorder with no
// actor to name refuses instead of stamping a class nothing acted as (see ErrNoActor), so an
// unattributable write fails loudly rather than entering the history as an anonymous fact.
type TaskEventActorKind string

const (
	TaskEventActorSeat   TaskEventActorKind = "seat"
	TaskEventActorClient TaskEventActorKind = "client"
	TaskEventActorGate   TaskEventActorKind = "gate"
	TaskEventActorHuman  TaskEventActorKind = "human"
)

// TaskEventActorKindValues is the vocabulary in database-declaration order.
var TaskEventActorKindValues = []TaskEventActorKind{
	TaskEventActorSeat,
	TaskEventActorClient,
	TaskEventActorGate,
	TaskEventActorHuman,
}

// AppendTaskEvent is what a caller supplies to write one entry. It lives here rather than beside
// the repository on purpose: the recorder is an application service, and it must be able to
// describe its input without importing an infrastructure package.
//
// Seq and UserSeq are NOT here: the database assigns both under one per-user lock, so no caller can
// invent one, take one out of order, or leave a gap. ClientEventID IS here, because it is the
// caller's own key rather than a number the ledger owns - empty means the entry carries no key, and
// the unique constraint on (user_id, client_event_id) is what refuses a resend. SubtaskID is here
// for the same reason ClientEventID is: it is part of what the caller is describing, and empty
// means the entry is about the task rather than one of its subtasks.
type AppendTaskEvent struct {
	TaskID        string
	SubtaskID     string
	Kind          TaskEventKind
	ActorKind     TaskEventActorKind
	ActorID       string
	Payload       map[string]any
	ClientEventID string
}
