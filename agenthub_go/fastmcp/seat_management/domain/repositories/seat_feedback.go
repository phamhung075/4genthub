package repositories

// Seat feedback (Directive H): the seat friction channel's domain contract. The interface and
// its record live in their own file rather than in repositories.go because the schema slice that
// introduces the table is serialized separately; the conventions are that file's.

import (
	"context"
	"time"
)

// SeatFeedback is one friction report submitted by a seat, its operator, or a bridge reporting
// for its seats.
//
// Layer is the layer of the platform the reporter says the friction is in, and it is a
// first-class field rather than a tag: the read side groups by it. It is validated against
// domain/feedback's closed set before the row is built.
//
// MachineID is empty when the report was submitted with a user token, and is the submitting
// machine's id when it was submitted with a machine token. It records provenance; it does not
// scope the row, because the token is already bound to one machine and the row is tenant-scoped
// by UserID like every other seat table.
type SeatFeedback struct {
	ID        string
	UserID    string
	Room      string
	Seat      string
	Session   string
	Layer     string
	Text      string
	MachineID string
	CreatedAt time.Time
}

// SeatFeedbackRepository stores seat friction reports.
//
// Every method is tenant-scoped by the user id it is given: a read never returns another user's
// rows, and a write never lands outside the caller's tenant.
type SeatFeedbackRepository interface {
	// Create stores one report. CreatedAt is supplied by the caller (the server clock) rather
	// than defaulted, so a test can pin it and the stored value is the one the route answered
	// with. The stored row is returned, id included.
	Create(ctx context.Context, report SeatFeedback) (*SeatFeedback, error)
	// List returns the user's reports newest first (created_at descending, id as a tiebreak).
	// The route groups them by layer in the vocabulary's own order; the order here is what makes
	// each group newest first without a second sort.
	List(ctx context.Context, userID string) ([]SeatFeedback, error)
}
