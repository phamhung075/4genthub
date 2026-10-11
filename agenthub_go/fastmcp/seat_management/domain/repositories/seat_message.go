package repositories

// Seat messages: text a window addressed to a seat, held until the client that holds that seat's
// terminal pulls it.
//
// WHY THIS IS ITS OWN STORE AND NOT THE SESSION STREAM. The stream (agent_sessions /
// agent_session_events) is CLIENT-authored: its only writer is the connector socket reporting what
// already happened at a seat, and its reader is the browser. A message to a seat is the other
// direction, and it is the first place on this axis where THE SERVER AUTHORS A ROW A CLIENT
// CONSUMES. Two consequences shape the record below, and neither is a shortcut:
//
//   - The row is keyed by the REPORTED NAMES (room, seat), not by a foreign key to a seat and not by
//     a session. No seat table carries a session column, so the server cannot address a session from
//     a seat at all, and a seat that is DOWN is exactly when a message waits — a store that needed
//     the seat, or its session, to exist would fail in the only case it is for.
//   - There is no foreign-key CASCADE, like every other table here: what happens to undelivered text
//     when a seat or a room goes is the deletion path's explicit decision, not the database's.
//
// The interface and its record live in their own file rather than in repositories.go because the
// schema slice that introduces the table is serialized separately; the conventions are that file's.

import (
	"context"
	"time"
)

// SeatMessage is one message addressed to a seat.
//
// DeliveredAt is nil while the message is PENDING and set when a client acknowledges that it has put
// the text into the seat's session. Delivery is AT-LEAST-ONCE: an unacknowledged row comes back on
// the next pull, and the client dedupes — the same contract the session stream's connector already
// imposes on the same client (internal/clientsync/connector.go). At-most-once, marking at pull,
// would lose the text SILENTLY when a client dies between the pull and the terminal, which is the
// one failure this store exists to prevent.
//
// MachineID is the machine that acknowledged the delivery, not the machine the seat runs on: under
// tenant scope any machine in the tenant may pull a seat's messages, so the ack records which one
// actually did (see the residual limit in the seat routes' own documentation).
type SeatMessage struct {
	ID          string
	UserID      string
	Room        string
	Seat        string
	Text        string
	CreatedAt   time.Time
	DeliveredAt *time.Time
	MachineID   string
}

// Pending reports whether the message has not been acknowledged by a client yet.
func (m SeatMessage) Pending() bool { return m.DeliveredAt == nil }

// SeatMessageRepository stores messages addressed to a seat.
//
// Every method is tenant-scoped by the user id it is given: a read never returns another user's
// rows, and a write never lands outside the caller's tenant.
type SeatMessageRepository interface {
	// Create stores one message and returns the stored row. CreatedAt is supplied by the caller (the
	// server clock) rather than defaulted, so a test can pin it and the stored instant is the one the
	// route answered with.
	Create(ctx context.Context, message SeatMessage) (*SeatMessage, error)
	// ListPending returns the seat's undelivered messages OLDEST FIRST — the order they were written
	// is the order a seat should receive them in — starting after the keyset (afterCreatedAt,
	// afterID) when afterCreatedAt is not the zero time. The id is the tiebreak, so two messages
	// written in the same instant still page in a stable order.
	ListPending(ctx context.Context, userID, room, seat string, afterCreatedAt time.Time, afterID string, limit int) ([]SeatMessage, error)
	// Ack marks ONE PENDING message delivered by machineID at deliveredAt, and reports whether such a
	// row was found. A second ack of the same id finds nothing, so a redelivery cannot be recorded
	// twice — and the row keeps the machine that delivered it rather than the one that acked last.
	Ack(ctx context.Context, userID, room, seat, id, machineID string, deliveredAt time.Time) (bool, error)
	// DeleteForSeat and DeleteForRoom are the application-layer cascade this schema requires wherever
	// CASCADE would otherwise be. They are deliberately unconditional: a seat or a room going away
	// takes its undelivered text with it, because the alternative — text addressed to a seat nobody
	// can reach, still waiting, forever — is not a delivery that can ever happen.
	DeleteForSeat(ctx context.Context, userID, room, seat string) error
	DeleteForRoom(ctx context.Context, userID, room string) error
}
