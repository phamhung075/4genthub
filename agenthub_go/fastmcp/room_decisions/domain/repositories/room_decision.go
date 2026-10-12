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

// RoomDecisionRepository stores mirrored decisions.
//
// Every method is tenant-scoped by the user id it is given - a read never returns another user's
// rows, and a write never lands outside the caller's tenant - and every method that names a decision
// also names its room, so a decision id from one room can never be answered through another.
type RoomDecisionRepository interface {
	// Create stores one mirrored ask. A row already holding the same (user, idempotency key) is
	// returned unchanged rather than duplicated: the key is the daemon's decisionId, and a redrive
	// must not author a second decision.
	Create(ctx context.Context, decision RoomDecision) (*RoomDecision, error)
	// Get returns one decision of this tenant and room, or nil when there is none.
	Get(ctx context.Context, userID, roomID, id string) (*RoomDecision, error)
	// ListByRoom returns this tenant's decisions for one room, newest first. The caller's tenant is
	// the scope and not the room's owner, so a room shared with a team never exposes the owner's
	// decisions to a viewer.
	ListByRoom(ctx context.Context, userID, roomID string) ([]RoomDecision, error)
	// RecordAnswer writes one applied click: the answers map as a whole, the state, and the
	// answered-at instant when the map became complete. It is guarded on the row still being
	// pending, so two clicks that raced cannot both land; it returns the stored row either way,
	// which is what makes a repeated click answer with the first answer.
	RecordAnswer(ctx context.Context, userID, roomID, id string, answers map[string]string, state decisions.State, answeredAt *time.Time) (*RoomDecision, error)
}
