// Package repositories holds the room-decision domain contract: the mirrored decision row and the
// store that keeps it. The conventions are seat_management/domain/repositories's: a record and its
// interface live in their own file, and every method is tenant-scoped by the user id it is given.
package repositories

import (
	"context"
	"time"

	"agenthub/fastmcp/room_decisions/domain/decisions"
	"agenthub/fastmcp/room_decisions/domain/questions"
)

// RoomDecision is one ask mirrored from a rig, plus the answers the human clicked.
//
// It is a PROJECTION of the daemon's local queue row, never the authority: the local row is what a
// seat's work stops on, and the daemon applies the answers there. That is why IdempotencyKey is
// stored at all - it is the daemon's own decisionId, so a redriven ask collapses onto one row
// instead of authoring a second decision the human would see twice.
//
// RoomID is the room's UUID rather than its slug (the contract's stated divergence from
// seat_feedback): a decision must outlive a slug rename, because the answers are still owed after
// the room is renamed.
//
// State moves pending -> answered -> resolved/superseded, and the cloud only ever performs the first
// step: it records a click. Resolved and superseded are written when the daemon reports back.
//
// AckedAt is the DELIVERY record rather than a state: the instant the daemon reported what happened to
// this answer, which is what stops the pull handing it out again. It is a separate column from
// ResolvedAt because a DROPPED answer - one the daemon decided not to apply - is acked and never
// retried while the row's state still says what the decision itself became.
//
// Summary and Detail are empty strings when the ask carried none, rather than pointers: the panel
// renders both, and "no detail" and "" are the same thing to a reader.
type RoomDecision struct {
	ID             string
	UserID         string
	RoomID         string
	RigName        string
	QitemID        string
	AuthorSeatKey  string
	Destination    string
	Summary        string
	Detail         string
	Questions      []questions.HumanQuestion
	Answers        map[string]string
	State          decisions.State
	IdempotencyKey string
	CreatedAt      time.Time
	AnsweredAt     *time.Time
	ResolvedAt     *time.Time
	AckedAt        *time.Time
}

// AnswerDelivery is one answer handed to the daemon: the mirrored ask plus the SLUG of the room its row
// belongs to.
//
// The slug rides the delivery because the daemon has no room model at all - the cloud, not the daemon,
// holds the room - so the pull is the only place the daemon can learn which room an ask it authored
// belongs to. It reports that room back in its own display; it never resolves one.
type AnswerDelivery struct {
	RoomDecision
	RoomSlug string
}

// Complete reports whether every question has an answer, which is the condition the answer route
// reports as `complete` and the moment the row becomes `answered`.
func (d RoomDecision) Complete() bool {
	return Complete(d.Questions, d.Answers)
}

// Complete answers the same question about a candidate answers map that has not been stored yet,
// which is what the answer route needs: it decides `complete` - and with it the row's next state -
// before the write, so the stored state and the reported one are the same answer.
//
// An ask with no questions is NOT complete: a decision nobody can answer is not an answered one,
// and the question limits make the case unreachable from a validated ask anyway.
func Complete(questions []questions.HumanQuestion, answers map[string]string) bool {
	if len(questions) == 0 {
		return false
	}
	for _, question := range questions {
		if _, ok := answers[question.ID]; !ok {
			return false
		}
	}
	return true
}

// AnswerCursor is where a pull stopped: the last row it handed out, in the pull's own order
// (answered_at, then id). It is a POSITION rather than a timestamp, because two answers that landed
// in the same instant are told apart by the id - a cursor that named only the instant would either
// skip the second one or hand it out forever.
//
// The pull's order is `answered_at ASC, id ASC`: the oldest unapplied answer first, which is
// also the order that makes the cursor monotone, so a resumed pull never repeats a row it already
// handed over. at-least-once is the delivery rule, so a repeat is not an error anywhere - but it is
// waste, and the daemon's ack is what stops it.
type AnswerCursor struct {
	AnsweredAt time.Time
	ID         string
}

// RoomDecisionRepository stores mirrored decisions.
//
// Every method is tenant-scoped by the user id it is given - a read never returns another user's
// rows, and a write never lands outside the caller's tenant - and every method that names a decision
// also names its room, so a decision id from one room can never be answered through another. THE
// ANSWER LEG'S METHODS NAME NO ROOM: the daemon pulls by machine identity (its rig) and the human it
// asks, because a daemon does not know which rooms its own asks were filed in - the cloud resolved
// that from a slug at ask time.
type RoomDecisionRepository interface {
	// Create stores one mirrored ask and reports whether THIS call created it. A row already holding
	// the same (user, idempotency key) is returned unchanged with false rather than duplicated: the key
	// is the daemon's decisionId, and a redrive must not author a second decision - the wire says so
	// with `created:false`, which is how the daemon knows its earlier attempt landed.
	Create(ctx context.Context, decision RoomDecision) (*RoomDecision, bool, error)
	// Get returns one decision of this tenant and room, or nil when there is none.
	Get(ctx context.Context, userID, roomID, id string) (*RoomDecision, error)
	// GetByID returns one decision of this tenant, or nil, without naming a room: the answer leg's ack
	// and state push arrive with nothing but the decision id the pull handed out.
	GetByID(ctx context.Context, userID, id string) (*RoomDecision, error)
	// ListByRoom returns this tenant's decisions for one room, newest first. The caller's tenant is
	// the scope and not the room's owner, so a room shared with a team never exposes the owner's
	// decisions to a viewer.
	ListByRoom(ctx context.Context, userID, roomID string) ([]RoomDecision, error)
	// ListAnswers returns this tenant's answered-but-unacknowledged decisions for ONE RIG, oldest
	// first, starting after the cursor - the pull a daemon drives. The rig is in the filter because
	// the ack is destructive: a daemon that pulled another rig's answers could not apply them (its
	// local queue has no such row) and its ack would close a decision nobody applied. acked_at IS NULL
	// is the delivery filter, and `state = answered` is the work filter: a pending ask is still being
	// answered in the panel, and a closed one is not work.
	ListAnswers(ctx context.Context, userID, rigName string, after *AnswerCursor, limit int) ([]AnswerDelivery, error)
	// Acknowledge records what the daemon did with one answer - `applied` it, or decided it does not
	// apply - and is the delivery record the pull reads. It is guarded on the row being `answered` and
	// unacked, so a repeated ack changes nothing; `applied` is the only input that also closes the row
	// as resolved, which is why ONLY the daemon's own report produces `resolved`. BOTH outcomes set
	// acked_at: a dropped answer is acked and never retried, exactly as an applied one is. The bool
	// says whether THIS call is the one that acked it - an id that is unknown, or already acked, comes
	// back false with the row as it stands (nil when there is no such row).
	Acknowledge(ctx context.Context, userID, id string, applied bool, at time.Time) (*RoomDecision, bool, error)
	// SetState writes the daemon's own verdict about a mirrored ask that never became an apply: it is
	// `superseded` when the decision was answered somewhere else first (typically Slack), which is
	// what makes the panel refuse a stale click. Only the daemon writes these two states, which is
	// why this method exists at all: the cloud records clicks and never concludes.
	SetState(ctx context.Context, userID, id string, state decisions.State, at time.Time) (*RoomDecision, error)
}
