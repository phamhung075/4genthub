package services

// The seat friction channel's single writer contract (Directive H).
//
// There are two ways to submit friction — an HTTP POST, which the shell command uses, and an MCP
// tool call, which a seat on an MCP-capable runtime uses — and they must not be two writers. Both
// reach this service: it validates the submission, scans every free-text field for credentials,
// and stores the row. The HTTP route owns only the transport (decode, status codes); the MCP tool
// owns only its arguments. Nothing else builds a SeatFeedback row.

import (
	"context"
	"fmt"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/seat_management/domain/feedback"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/secretscan"
)

const (
	// The friction itself: long enough for a real report carrying the command that failed,
	// short enough that a page can render a list of them.
	SeatFeedbackMaxText = 2000
	// Room, seat and session names.
	SeatFeedbackMaxField = 128
)

// SeatFeedbackStore is the storage surface the channel needs. A narrow local interface, so the
// service does not depend on the whole repository package's shape.
type SeatFeedbackStore interface {
	Create(ctx context.Context, report repositories.SeatFeedback) (*repositories.SeatFeedback, error)
	List(ctx context.Context, userID string) ([]repositories.SeatFeedback, error)
}

// SeatFeedbackInput is one decoded submission. session is optional.
type SeatFeedbackInput struct {
	Room    string
	Seat    string
	Session string
	Layer   string
	Text    string
}

// SeatFeedbackPoster is who a submission is attributed to: the tenant the row is written under,
// and the machine that carried it (empty when a user token carried it).
type SeatFeedbackPoster struct {
	UserID    string
	MachineID string
}

// SeatFeedbackRejection is a submission the contract refuses. SecretField is set when the reason
// is a credential and names the field whose text held it; the message is what the caller is
// shown, and it never contains the credential.
type SeatFeedbackRejection struct {
	Message     string
	SecretField string
}

func (e *SeatFeedbackRejection) Error() string { return e.Message }

// SeatFeedbackService validates and stores friction reports.
type SeatFeedbackService struct {
	store SeatFeedbackStore
}

// NewSeatFeedbackService builds the service over a store.
func NewSeatFeedbackService(store SeatFeedbackStore) *SeatFeedbackService {
	return &SeatFeedbackService{store: store}
}

// Submit validates one submission and stores it. createdAt is supplied by the caller rather than
// read here, so the HTTP route's clock seam and the MCP tool's clock are each the one their own
// tests pin, and the stored instant is the answered instant.
func (s *SeatFeedbackService) Submit(ctx context.Context, poster SeatFeedbackPoster, input SeatFeedbackInput, createdAt time.Time) (*repositories.SeatFeedback, error) {
	report, err := s.validate(poster, input, createdAt)
	if err != nil {
		return nil, err
	}
	return s.store.Create(ctx, *report)
}

// List returns the tenant's reports newest first (the store's order).
func (s *SeatFeedbackService) List(ctx context.Context, userID string) ([]repositories.SeatFeedback, error) {
	return s.store.List(ctx, userID)
}

// validate is the whole contract: names, the layer vocabulary, the text bound, and the credential
// scan. The scan runs over EVERY free-text field, not only the body, because a seat pasting a
// config into the session name is as plausible as one pasting it into the report.
func (s *SeatFeedbackService) validate(poster SeatFeedbackPoster, input SeatFeedbackInput, createdAt time.Time) (*repositories.SeatFeedback, error) {
	if err := repositories.ValidateName("room slug", input.Room); err != nil {
		return nil, &SeatFeedbackRejection{Message: err.Error()}
	}
	if err := repositories.ValidateName("seat key", input.Seat); err != nil {
		return nil, &SeatFeedbackRejection{Message: err.Error()}
	}
	layer, err := feedback.ParseLayer(input.Layer)
	if err != nil {
		return nil, &SeatFeedbackRejection{Message: err.Error()}
	}
	text := strings.TrimSpace(input.Text)
	if text == "" {
		return nil, &SeatFeedbackRejection{Message: "text must not be empty"}
	}
	if utf8.RuneCountInString(text) > SeatFeedbackMaxText {
		return nil, &SeatFeedbackRejection{Message: fmt.Sprintf("text cannot exceed %d characters", SeatFeedbackMaxText)}
	}
	if len(input.Session) > SeatFeedbackMaxField {
		return nil, &SeatFeedbackRejection{Message: fmt.Sprintf("session cannot exceed %d characters", SeatFeedbackMaxField)}
	}

	for _, field := range []struct {
		path string
		text string
	}{
		{"room", input.Room},
		{"seat", input.Seat},
		{"session", input.Session},
		{"text", text},
	} {
		if secretscan.Contains(field.text) {
			return nil, &SeatFeedbackRejection{
				Message:     "secret detected in field " + field.path,
				SecretField: field.path,
			}
		}
	}

	return &repositories.SeatFeedback{
		UserID:    poster.UserID,
		Room:      input.Room,
		Seat:      input.Seat,
		Session:   input.Session,
		Layer:     string(layer),
		Text:      text,
		MachineID: poster.MachineID,
		CreatedAt: createdAt,
	}, nil
}
