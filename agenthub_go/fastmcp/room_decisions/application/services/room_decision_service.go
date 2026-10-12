package services

// The room decision channel's single writer contract, the sibling of SeatFeedbackService.
//
// A rig's daemon mirrors an ask up and the human's click comes down; this service is the one place
// either is validated, and the route owns only the transport (decode, status codes). Nothing else
// builds a RoomDecision row.
//
// WHAT IS VALIDATED, AND WHY IT IS VALIDATED HERE RATHER THAN TRUSTED. The daemon already refuses a
// malformed ask before it authors a decision, so the cloud's copy of the question limits is not a
// second opinion about the daemon's data: it is the rule that a projection may not be WIDER than its
// authority. A cloud row that accepted an ask the daemon's own parser refuses would be a decision
// nobody can answer, and the human would see it in the panel.

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/room_decisions/domain/decisions"
	"agenthub/fastmcp/room_decisions/domain/questions"
	"agenthub/fastmcp/room_decisions/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/secretscan"
)

const (
	// The prose of an ask: the summary is what a list row shows, the detail is what the human
	// reads before choosing. Bounded like a friction report is - long enough for the real
	// `humanDetail`, short enough for a panel.
	RoomDecisionMaxSummary = 200
	RoomDecisionMaxDetail  = 4000
	// The names around the prose: the rig, the queue row, the asking seat, the human ref.
	RoomDecisionMaxField = 128
)

// The refusal tokens the answer contract names. They are the vocabulary a client branches on, so
// they live in one place and the route's status mapping is the only thing that reads them.
const (
	// CodeUnknownDecision is a decision id that is not in this room and tenant.
	CodeUnknownDecision = "unknown-decision"
	// CodeNotTheAskedHuman is a caller who may see the room but is not its owner: the ask is
	// addressed to the room's human, and the room's owner is who answers for them. THE ROUTE
	// RAISES THIS ONE, because "may see the room" is a room lookup rather than a decision read.
	CodeNotTheAskedHuman = "not-the-asked-human"
	// CodeUnknownQuestion is a question id the ask does not carry.
	CodeUnknownQuestion = "unknown-question"
	// CodeUnknownOption is an option id the named question does not carry. It is the refusal the
	// acceptance turns on: the click's vocabulary is the STORED options, never the client's copy.
	CodeUnknownOption = "unknown-option"
)

// RoomDecisionStore is the storage surface the channel needs: the domain repository's own four
// methods, named here so the service's dependency is the shape it uses rather than the package.
type RoomDecisionStore interface {
	Create(ctx context.Context, decision repositories.RoomDecision) (*repositories.RoomDecision, error)
	Get(ctx context.Context, userID, roomID, id string) (*repositories.RoomDecision, error)
	ListByRoom(ctx context.Context, userID, roomID string) ([]repositories.RoomDecision, error)
	RecordAnswer(ctx context.Context, userID, roomID, id string, answers map[string]string, state decisions.State, answeredAt *time.Time) (*repositories.RoomDecision, error)
}

// RoomDecisionAsk is one authored ask, before it is a row. RoomID is the resolved room UUID, and
// Questions is the authored value as the daemon sent it - it is parsed here, not by the route.
type RoomDecisionAsk struct {
	RigName        string
	QitemID        string
	AuthorSeatKey  string
	Destination    string
	Summary        string
	Detail         string
	Questions      json.RawMessage
	IdempotencyKey string
}

// RoomDecisionAnswerInput is one click: the question, the option, and the caller's retry token.
//
// IdempotencyKey is accepted and carried because the contract's click body has it, and it is NOT
// STORED, because this row has no column for it: the row's own idempotency_key is the ASK's
// (the daemon's decisionId), and the answers map is `questionId -> optionId` by the contract's own
// shape. What that means observably is stated on Answer.
type RoomDecisionAnswerInput struct {
	QuestionID     string
	OptionID       string
	IdempotencyKey string
}

// RoomDecisionAskRejection is an ask the contract refuses. SecretField is set when the reason is a
// credential and names the field whose text held it; the message never contains the credential.
type RoomDecisionAskRejection struct {
	Message     string
	SecretField string
}

func (e *RoomDecisionAskRejection) Error() string { return e.Message }

// RoomDecisionAnswerRejection is a click the contract refuses, carrying the token a client branches
// on. Code is one of the Code* constants, or `state-<state>` from decisions.RefusalCode.
type RoomDecisionAnswerRejection struct {
	Code    string
	Message string
}

func (e *RoomDecisionAnswerRejection) Error() string { return e.Code + ": " + e.Message }

// RoomDecisionService validates and stores mirrored decisions and the clicks on them.
type RoomDecisionService struct {
	store RoomDecisionStore
}

// NewRoomDecisionService builds the service over a store.
func NewRoomDecisionService(store RoomDecisionStore) *RoomDecisionService {
	return &RoomDecisionService{store: store}
}

// Create validates one ask and stores it under the caller's tenant.
//
// The questions are parsed with the daemon's own closed limits (domain/questions), so an ask the
// daemon would refuse is refused here, before any row exists - and the credential scan runs over
// the ask's prose, because a decision's detail is text a seat wrote and a seat can paste a token
// into anything.
//
// A row already carrying this ask's (user, idempotency key) is returned unchanged rather than
// duplicated: the key is the daemon's decisionId, and the mirror is durable-first, so a redrive
// after a lost answer must collapse onto the row it already made instead of authoring a second
// decision the human would be asked twice.
func (s *RoomDecisionService) Create(ctx context.Context, userID, roomID string, ask RoomDecisionAsk, createdAt time.Time) (*repositories.RoomDecision, error) {
	if strings.TrimSpace(roomID) == "" {
		return nil, &RoomDecisionAskRejection{Message: "room is required"}
	}
	for _, field := range []struct {
		path  string
		value string
	}{
		{"rig_name", ask.RigName},
		{"qitem_id", ask.QitemID},
		{"author_seat_key", ask.AuthorSeatKey},
		{"destination", ask.Destination},
		{"idempotency_key", ask.IdempotencyKey},
	} {
		trimmed := strings.TrimSpace(field.value)
		if trimmed == "" {
			return nil, &RoomDecisionAskRejection{Message: field.path + " is required"}
		}
		if utf8.RuneCountInString(trimmed) > RoomDecisionMaxField {
			return nil, &RoomDecisionAskRejection{Message: fmt.Sprintf("%s cannot exceed %d characters", field.path, RoomDecisionMaxField)}
		}
	}
	summary := strings.TrimSpace(ask.Summary)
	if utf8.RuneCountInString(summary) > RoomDecisionMaxSummary {
		return nil, &RoomDecisionAskRejection{Message: fmt.Sprintf("summary cannot exceed %d characters", RoomDecisionMaxSummary)}
	}
	detail := strings.TrimSpace(ask.Detail)
	if utf8.RuneCountInString(detail) > RoomDecisionMaxDetail {
		return nil, &RoomDecisionAskRejection{Message: fmt.Sprintf("detail cannot exceed %d characters", RoomDecisionMaxDetail)}
	}
	for _, field := range []struct {
		path string
		text string
	}{
		{"summary", summary},
		{"detail", detail},
		{"destination", ask.Destination},
	} {
		if secretscan.Contains(field.text) {
			return nil, &RoomDecisionAskRejection{
				Message:     "secret detected in field " + field.path,
				SecretField: field.path,
			}
		}
	}

	parsed, err := questions.Parse(ask.Questions)
	if err != nil {
		var rejection *questions.Rejection
		if ok := asRejection(err, &rejection); ok {
			return nil, &RoomDecisionAskRejection{Message: rejection.Message}
		}
		return nil, err
	}

	return s.store.Create(ctx, repositories.RoomDecision{
		UserID:         userID,
		RoomID:         roomID,
		RigName:        ask.RigName,
		QitemID:        ask.QitemID,
		AuthorSeatKey:  ask.AuthorSeatKey,
		Destination:    ask.Destination,
		Summary:        summary,
		Detail:         detail,
		Questions:      parsed,
		Answers:        map[string]string{},
		State:          decisions.StatePending,
		IdempotencyKey: ask.IdempotencyKey,
		CreatedAt:      createdAt.UTC(),
	})
}

// List returns the caller's decisions for one room, newest first (the store's order).
func (s *RoomDecisionService) List(ctx context.Context, userID, roomID string) ([]repositories.RoomDecision, error) {
	return s.store.ListByRoom(ctx, userID, roomID)
}

// Answer records one click and returns the row as it now stands.
//
// THE VALIDATION ORDER IS THE CONTRACT, and one step of it is placed deliberately:
//
//  1. the decision is in this room and tenant, else unknown-decision (404);
//  2. AN EXACT REPLAY - the question already holds this option - returns the stored row and writes
//     nothing. This step sits BEFORE the state check on purpose: the click that completed a
//     decision moved the row to `answered`, so a client retrying exactly that click after a timeout
//     would otherwise be told `state-answered` about a click that DID land. `state-<state>` is for a
//     click that would change the answer, not for one that is already the answer.
//  3. the row is still pending, else state-<state> (409);
//  4. the question is in the ask's stored questions, else unknown-question (422);
//  5. the option is in that question's stored options, else unknown-option (422). NO WRITE HAPPENS
//     ON ANY REFUSAL: the write is the last statement of this method.
//
// A click that CHANGES a choice is allowed while the row is pending - that is the daemon's own
// recordHumanAnswer semantics and Slack's, where a human may change their mind before the decision
// is applied. Once every question is answered the row is `answered`, the click that completed it is
// the last one accepted, and the cloud never moves a row past `answered`: `resolved` and
// `superseded` come from the daemon.
//
// ON A DUPLICATE idempotency_key, which the contract says "returns the first answer and inserts
// nothing": the answers map is `questionId -> optionId` and the row's idempotency_key column is the
// ASK's key, so a per-click key has nowhere to be stored and is not stored. What the contract
// promises observably is what this method does: the same click twice returns the answer already
// recorded and inserts nothing (the write is an UPDATE of the one row, never an insert). A second
// click on the SAME question with a DIFFERENT option, while pending, IS an answer change and is
// applied - the cloud cannot tell that click from a retry, and the daemon's apply is what decides
// whether the question was still open.
func (s *RoomDecisionService) Answer(ctx context.Context, userID, roomID, id string, input RoomDecisionAnswerInput, now time.Time) (*repositories.RoomDecision, error) {
	stored, err := s.store.Get(ctx, userID, roomID, id)
	if err != nil {
		return nil, err
	}
	if stored == nil {
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownDecision,
			Message: "no decision " + id + " in this room",
		}
	}
	if recorded, ok := stored.Answers[input.QuestionID]; ok && recorded == input.OptionID {
		return stored, nil
	}
	if stored.State != decisions.StatePending {
		return nil, &RoomDecisionAnswerRejection{
			Code:    decisions.RefusalCode(stored.State),
			Message: "this decision is already " + string(stored.State),
		}
	}
	question, ok := questions.Find(stored.Questions, input.QuestionID)
	if !ok {
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownQuestion,
			Message: "this decision has no question " + input.QuestionID,
		}
	}
	if _, ok := question.Option(input.OptionID); !ok {
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownOption,
			Message: "question " + input.QuestionID + " has no option " + input.OptionID,
		}
	}

	answers := make(map[string]string, len(stored.Answers)+1)
	for questionID, optionID := range stored.Answers {
		answers[questionID] = optionID
	}
	answers[input.QuestionID] = input.OptionID

	state := decisions.StatePending
	var answeredAt *time.Time
	if repositories.Complete(stored.Questions, answers) {
		state = decisions.StateAnswered
		at := now.UTC()
		answeredAt = &at
	}
	written, err := s.store.RecordAnswer(ctx, userID, roomID, id, answers, state, answeredAt)
	if err != nil {
		return nil, err
	}
	if written == nil {
		// The store's guarded write matched nothing and the row was gone when it looked: a decision
		// that is not there is the refusal the read at the top of this method would have given.
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownDecision,
			Message: "no decision " + id + " in this room",
		}
	}
	return written, nil
}

// asRejection is errors.As for the questions package's rejection type, kept local so this file's
// imports stay the domain packages it names.
func asRejection(err error, target **questions.Rejection) bool {
	if rejection, ok := err.(*questions.Rejection); ok {
		*target = rejection
		return true
	}
	return false
}
