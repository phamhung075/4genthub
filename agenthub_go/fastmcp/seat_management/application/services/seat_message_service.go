package services

// The seat message store's single writer contract.
//
// Text a window addressed to a seat is validated here, scanned for credentials, and stored; the HTTP
// route owns only the transport (decode, status codes). NOTHING ELSE BUILDS A SeatMessage row, and
// the pull and the ack come through this service too, so the page's bounds and the cursor's shape
// have one home rather than one per caller.
//
// THE DELIVERY CONTRACT IS AT-LEAST-ONCE, AND IT IS TWO CALLS RATHER THAN ONE: Pull hands out pending
// messages, and Ack records that a client put one into the seat's terminal. A client that dies
// between the two sees the message again instead of losing it — which is the one failure this store
// exists to prevent — and dedupes on its own side, exactly as the connector does for the session
// stream. At-most-once (marking at pull) would need no ack and would lose the text silently.

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/secretscan"
)

const (
	// The message itself: long enough for a real instruction, short enough that a seat's prompt and a
	// page can each hold one. The bound is the FRICTION CHANNEL'S OWN, so the two seat-keyed channels
	// do not answer differently about what a seat-size text is.
	SeatMessageMaxText = 2000

	// The pull's page: the default a caller gets when it names no limit, and the hard clamp that
	// stops any caller taking a whole backlog in one call.
	SeatMessageDefaultLimit = 50
	SeatMessageMaxLimit     = 200
)

// ErrSeatMessageNotPending is returned when an ack names an id that is not a pending message of that
// seat: it was never there, or it has already been delivered. Both are refusals, and neither
// redelivers — a client that retried a dropped ack hears "already delivered" rather than causing a
// second delivery.
var ErrSeatMessageNotPending = errors.New("seat message is not pending: unknown id, or already delivered")

// SeatMessageStore is the storage surface the store needs. A narrow local interface, so the service
// does not depend on the whole repository package's shape.
type SeatMessageStore interface {
	Create(ctx context.Context, message repositories.SeatMessage) (*repositories.SeatMessage, error)
	ListPending(ctx context.Context, userID, room, seat string, afterCreatedAt time.Time, afterID string, limit int) ([]repositories.SeatMessage, error)
	Ack(ctx context.Context, userID, room, seat, id, machineID string, deliveredAt time.Time) (bool, error)
}

// SeatMessageInput is one decoded send.
type SeatMessageInput struct {
	Room string
	Seat string
	Text string
}

// SeatMessageRejection is a request the contract refuses. SecretField is set when the reason is a
// credential and names the field whose text held it; the message never contains the credential.
type SeatMessageRejection struct {
	Message     string
	SecretField string
}

func (e *SeatMessageRejection) Error() string { return e.Message }

// SeatMessageService validates, stores and serves messages addressed to a seat.
type SeatMessageService struct {
	store SeatMessageStore
}

// NewSeatMessageService builds the service over a store.
func NewSeatMessageService(store SeatMessageStore) *SeatMessageService {
	return &SeatMessageService{store: store}
}

// Send validates one message and stores it. createdAt is supplied by the caller rather than read
// here, so the route's clock seam is the one its tests pin and the stored instant is the answered
// instant.
func (s *SeatMessageService) Send(ctx context.Context, userID string, input SeatMessageInput, createdAt time.Time) (*repositories.SeatMessage, error) {
	message, err := validateSeatMessage(userID, input, createdAt)
	if err != nil {
		return nil, err
	}
	return s.store.Create(ctx, *message)
}

// Pull returns up to the clamped limit of a seat's pending messages, OLDEST FIRST, plus the cursor to
// continue after them.
//
// THE CURSOR IS OPAQUE TO THE CALLER: it is the (created_at, id) keyset of the last row returned, and
// a client echoes it back untouched rather than composing one. An unparsable cursor is a rejection
// rather than an empty page — a caller that mangled the cursor it was handed must hear about it,
// because an empty page would read as "nothing is waiting" and silently drop the backlog.
func (s *SeatMessageService) Pull(ctx context.Context, userID, room, seat, after string, limit int) ([]repositories.SeatMessage, string, error) {
	if err := repositories.ValidateName("room slug", room); err != nil {
		return nil, "", &SeatMessageRejection{Message: err.Error()}
	}
	if err := repositories.ValidateName("seat key", seat); err != nil {
		return nil, "", &SeatMessageRejection{Message: err.Error()}
	}
	afterCreatedAt, afterID, err := decodeSeatMessageCursor(after)
	if err != nil {
		return nil, "", err
	}
	messages, err := s.store.ListPending(ctx, userID, room, seat, afterCreatedAt, afterID, ClampSeatMessageLimit(limit))
	if err != nil {
		return nil, "", err
	}
	next := ""
	if len(messages) > 0 {
		next = encodeSeatMessageCursor(messages[len(messages)-1])
	}
	return messages, next, nil
}

// Ack records that a client has put one message into the seat's session. It is the SECOND half of the
// delivery contract: the client acks AFTER the text reached the terminal, so an interruption in
// between redelivers rather than loses. MachineID is the machine that did the delivering.
func (s *SeatMessageService) Ack(ctx context.Context, userID, room, seat, id, machineID string, at time.Time) error {
	if err := repositories.ValidateName("room slug", room); err != nil {
		return &SeatMessageRejection{Message: err.Error()}
	}
	if err := repositories.ValidateName("seat key", seat); err != nil {
		return &SeatMessageRejection{Message: err.Error()}
	}
	if strings.TrimSpace(id) == "" {
		return &SeatMessageRejection{Message: "message id must not be empty"}
	}
	acked, err := s.store.Ack(ctx, userID, room, seat, id, machineID, at)
	if err != nil {
		return err
	}
	if !acked {
		return ErrSeatMessageNotPending
	}
	return nil
}

// ClampSeatMessageLimit applies the page's default and its hard clamp. It is exported so the route's
// documentation and its tests name the same numbers the service enforces.
func ClampSeatMessageLimit(limit int) int {
	if limit <= 0 {
		return SeatMessageDefaultLimit
	}
	if limit > SeatMessageMaxLimit {
		return SeatMessageMaxLimit
	}
	return limit
}

// seatMessageCursorSeparator occurs in neither an RFC3339 instant nor a UUID, so the two halves of a
// cursor cannot be read as one.
const seatMessageCursorSeparator = "|"

func encodeSeatMessageCursor(m repositories.SeatMessage) string {
	return m.CreatedAt.UTC().Format(time.RFC3339Nano) + seatMessageCursorSeparator + m.ID
}

// decodeSeatMessageCursor reads what encodeSeatMessageCursor wrote. AN EMPTY CURSOR IS THE FIRST
// PAGE rather than an error, which is what lets a client that has never pulled call the route with no
// after at all.
func decodeSeatMessageCursor(after string) (time.Time, string, error) {
	if strings.TrimSpace(after) == "" {
		return time.Time{}, "", nil
	}
	rawTime, id, found := strings.Cut(after, seatMessageCursorSeparator)
	if !found || rawTime == "" || id == "" {
		return time.Time{}, "", &SeatMessageRejection{Message: fmt.Sprintf("after %q must be a cursor this endpoint returned", after)}
	}
	at, err := time.Parse(time.RFC3339Nano, rawTime)
	if err != nil {
		return time.Time{}, "", &SeatMessageRejection{Message: fmt.Sprintf("after %q must be a cursor this endpoint returned", after)}
	}
	return at.UTC(), id, nil
}

// validateSeatMessage is the whole write contract: the names, the text, and the credential scan.
//
// THE SCAN IS THE POINT OF THIS FUNCTION. The chat window is exactly where an operator pastes a
// token, and a store that keeps one is a leak with a timestamp — so the same scan, from the same
// domain package, that the friction channel runs before it stores anything runs here over every
// free-text field, and the text is TRIMMED once and stored as the trimmed value.
func validateSeatMessage(userID string, input SeatMessageInput, createdAt time.Time) (*repositories.SeatMessage, error) {
	if err := repositories.ValidateName("room slug", input.Room); err != nil {
		return nil, &SeatMessageRejection{Message: err.Error()}
	}
	if err := repositories.ValidateName("seat key", input.Seat); err != nil {
		return nil, &SeatMessageRejection{Message: err.Error()}
	}
	text := strings.TrimSpace(input.Text)
	if text == "" {
		return nil, &SeatMessageRejection{Message: "text must not be empty"}
	}
	if utf8.RuneCountInString(text) > SeatMessageMaxText {
		return nil, &SeatMessageRejection{Message: fmt.Sprintf("text cannot exceed %d characters", SeatMessageMaxText)}
	}
	for _, field := range []struct {
		path string
		text string
	}{
		{"room", input.Room},
		{"seat", input.Seat},
		{"text", text},
	} {
		if secretscan.Contains(field.text) {
			return nil, &SeatMessageRejection{
				Message:     "secret detected in field " + field.path,
				SecretField: field.path,
			}
		}
	}
	return &repositories.SeatMessage{
		UserID:    userID,
		Room:      input.Room,
		Seat:      input.Seat,
		Text:      text,
		CreatedAt: createdAt,
	}, nil
}
