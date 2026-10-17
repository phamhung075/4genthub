// Package entities holds the ledger's OWN vocabulary: what a client's outbox may send as an intent,
// which of those are facts and which are decisions, and what the server answers for an item.
//
// IT IS THE LEDGER'S LAYER AND NOT PART OF O1a/O1b. O1a owns the table, the ORM struct, the
// repository and the PER-TASK read; O1b owns the transactional write a status change makes. Neither
// speaks about a CLIENT pushing its offline work, which is what D9's part 1 adds (architecture
// agenthub-system-architecture.md, its "#### Part 1: the sync and event model" heading) and what
// P2/P3 build.
//
// THE VOCABULARY IS THE ARCHITECTURE'S, RE-STATED HERE FOR THE ROLE IT PLAYS IN THE DECISION rather
// than copied for convenience: the DB CHECK constraint (task_event_tables.go) is the authority for
// which strings may LAND, and a test beside this file pins that every kind below is one of those
// strings, so the two cannot drift. What is added here is the CLASSIFICATION, which is the rule the
// architecture's Decisions bullet turns on - "unless every event since then is a fact"
// (ai_docs/core-architecture/agenthub-system-architecture.md) - and which no table can hold.
package entities

// IntentKind is one kind a client may push through the outbox. It is the same string the ledger
// stores as `task_events.kind`; what makes it an INTENT is that a client writes it, which is why the
// list below is smaller than the table's vocabulary: `context_updated` is written by the server (the
// context path) and a client that sent one would be inventing history it did not make. (The comment
// this replaces named `delivered` and `escalated` as server-written; the ledger measured that
// NEITHER had a writer anywhere - handoffs between seats are queue rows and an escalation is a
// task_audit_records row - and the ruling that closed the handover payload deleted both from the
// vocabulary rather than keeping a kind nothing writes.)
type IntentKind string

const (
	// Decisions: each owes a base_seq, and the server refuses one whose base is behind.
	IntentKindStatusChanged IntentKind = "status_changed"
	IntentKindGateVerdict   IntentKind = "gate_verdict"
	// Facts: append-only observations the client may record offline.
	IntentKindProgress          IntentKind = "progress"
	IntentKindEvidenceSubmitted IntentKind = "evidence_submitted"
	IntentKindHandover          IntentKind = "handover"
)

// DecisionKinds is D9's decision list (architecture agenthub-system-architecture.md, the
// "*Decisions* are ..." bullet): the intents that claim, transition or judge, and so
// cannot commute and cannot be applied out of order.
var DecisionKinds = []IntentKind{
	IntentKindStatusChanged,
	IntentKindGateVerdict,
}

// FactKinds is D9's fact list (architecture agenthub-system-architecture.md, the "*Facts* are ..."
// bullet): append-only observations a client may record offline, which
// the server accepts in arrival order and NEVER refuses for being late.
var FactKinds = []IntentKind{
	IntentKindProgress,
	IntentKindEvidenceSubmitted,
	IntentKindHandover,
}

// IntentKinds is every kind a client may send, in database-declaration order.
var IntentKinds = []IntentKind{
	IntentKindProgress,
	IntentKindStatusChanged,
	IntentKindEvidenceSubmitted,
	IntentKindGateVerdict,
	IntentKindHandover,
}

// FactKindStrings is FactKinds as the plain tokens the table stores, for the one query that asks
// "is anything after this seq NOT a fact" (the Decisions bullet's "unless every event since then is
// a fact", ai_docs/core-architecture/agenthub-system-architecture.md). The classification stays
// here; the query takes the list as an argument, so the repository has no opinion about which kinds
// are facts.
func FactKindStrings() []string {
	out := make([]string, 0, len(FactKinds))
	for _, k := range FactKinds {
		out = append(out, string(k))
	}
	return out
}

// IsIntentKind reports whether s is a kind a client may push. A kind that is in the table's
// vocabulary but not in this list (`context_updated`, the server's own write) is deliberately NOT
// one.
func IsIntentKind(s string) bool {
	for _, k := range IntentKinds {
		if string(k) == s {
			return true
		}
	}
	return false
}

// IsFact reports whether this intent is a fact: append-only, accepted in arrival order, never
// refused for being late, and owing no base_seq.
func (k IntentKind) IsFact() bool {
	for _, f := range FactKinds {
		if f == k {
			return true
		}
	}
	return false
}

// IsDecision reports whether this intent is a decision: it carries base_seq and the server refuses
// one whose base_seq is behind the task's current seq unless every event since then is a fact.
func (k IntentKind) IsDecision() bool {
	for _, d := range DecisionKinds {
		if d == k {
			return true
		}
	}
	return false
}

// Intent is one item of the batch: exactly the fields the wire contract names, already read off the
// request and nothing else. BaseSeq is a POINTER because "absent" and "0" are different things for
// a decision - 0 is the base a client that has seen nothing names, while absent is the field the
// contract requires and the client did not send, and those two get different answers.
type Intent struct {
	ClientEventID string
	TaskID        string
	SubtaskID     string
	Kind          IntentKind
	BaseSeq       *int
	// Payload is the raw `payload` value as the body carried it. It is `any` rather than a map
	// because the ledger's column is written from a map: the service refuses a payload that is not
	// an object instead of silently storing nothing, and the refusal has to be able to see what
	// arrived.
	Payload any
}

// Answer is what the server answers for ONE item, and it is one of two shapes told apart by
// Accepted: an acceptance names the sequences the row took, a refusal names the reason and the
// task's seq as it stands. There is ONE discriminator on purpose - a second boolean meaning "not
// accepted" would be a second source for the same fact.
type Answer struct {
	Accepted bool
	UserSeq  int64
	Seq      int
	Reason   string
	TaskSeq  int
}

// Acceptance is the answer for an item that was written: the user cursor it took and the task seq.
func Acceptance(userSeq int64, seq int) Answer {
	return Answer{Accepted: true, UserSeq: userSeq, Seq: seq}
}

// Refusal is the answer for an item that was not written. reason is one of the tokens below and
// taskSeq is the task's seq as it stands, which is what the client re-reads from.
func Refusal(reason string, taskSeq int) Answer {
	return Answer{Accepted: false, Reason: reason, TaskSeq: taskSeq}
}

// The refusal reasons, as stable tokens rather than sentences: a client shows one to a seat and
// branches on it, so a reason that is prose cannot be branched on.
const (
	// ReasonInvalidClientEventID: the item named no outbox key, or one that is not a UUID. Nothing
	// can be made idempotent without it, so the item is refused rather than appended keyless.
	ReasonInvalidClientEventID = "invalid_client_event_id"
	// ReasonUnsupportedKind: the kind is not one a client may push.
	ReasonUnsupportedKind = "unsupported_kind"
	// ReasonUnknownTask: the task is not one this user can see. It covers both a task id that is not
	// a UUID and another user's task - an entry must never be appended to a task its writer cannot
	// see, and the foreign key alone would allow exactly that.
	ReasonUnknownTask = "unknown_task"
	// ReasonInvalidSubtaskID: subtask_id was sent and is not a UUID.
	ReasonInvalidSubtaskID = "invalid_subtask_id"
	// ReasonUnknownSubtask: subtask_id was sent as a UUID and does not name a subtask OF THIS TASK
	// that this user can see. It covers three shapes with ONE token - a subtask that does not exist,
	// another user's subtask, and a subtask of a different task - for the reason ReasonUnknownTask
	// covers a malformed id and another user's task with one: a token that told them apart would
	// answer whether a subtask exists to a user who cannot see it.
	ReasonUnknownSubtask = "unknown_subtask"
	// ReasonInvalidPayload: payload was sent and is not an object. The ledger's payload column is
	// written from a map, so storing something else would store nothing and call it success.
	ReasonInvalidPayload = "invalid_payload"
	// ReasonBaseSeqRequired: a decision arrived without the base_seq the contract requires of it.
	ReasonBaseSeqRequired = "base_seq_required"
	// ReasonStaleBaseSeq: base_seq is behind the task's current seq and something that is not a fact
	// happened after it. The task_seq beside this reason is what the client re-reads from.
	ReasonStaleBaseSeq = "stale_base_seq"
)
