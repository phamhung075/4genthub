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
	"log/slog"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
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
	// CodeInvalidCursor is a pull whose cursor is not one this channel minted. It is a refusal
	// rather than a silent first page: a daemon that resumed from a cursor it made up would be handed
	// answers it has already applied, which costs an apply and a second ack.
	CodeInvalidCursor = "invalid-cursor"
	// CodeInvalidPull is a pull that does not name the machine identity it pulls for. The route
	// resolves that identity from the caller, so this is the refusal for a credential the channel
	// cannot place rather than for a malformed body.
	CodeInvalidPull = "invalid-pull"
	// CodeUnknownState is a state push naming a state the daemon may not write. The cloud records
	// clicks and never concludes, so the only two states a push may carry are the two that mean the
	// decision is over.
	CodeUnknownState = "unknown-state"
	// CodeInvalidAck is an ack whose outcome is neither of the two the contract names, or a dropped
	// outcome whose reason is missing or outside the closed list. It is a 400 and not a conflict:
	// nothing about the decision is wrong, the report itself is.
	CodeInvalidAck = "invalid-ack"
	// CodeNotAwaitingAck is an ack naming a decision that is not awaiting delivery: an id that is not
	// there, one already acked, or one still being answered. All three are the same conflict,
	// mirroring the shipped message ack, whose rule is that THE STATE, NOT THE ID, IS WHAT A CALLER CAN
	// GET WRONG - a client retrying a dropped ack must not hear something that reads like a mistyped
	// id.
	CodeNotAwaitingAck = "not-awaiting-ack"
)

// The pull's size: how many unapplied answers one call hands over, and the ceiling a caller may ask
// for. The default is the daemon's own working batch - a poll returns what has accumulated since the
// last one, and a human answers a handful of decisions in an evening, not thousands.
const (
	RoomDecisionPullLimit    = 50
	RoomDecisionMaxPullLimit = 200
)

// ClampDecisionAnswerLimit resolves the pull's page size in ONE place, so the route's tests page by
// the numbers a client gets: a limit the caller did not give (zero or less) is the default, and one
// above the ceiling is the ceiling. It is the sibling of ClampSeatMessageLimit, which the seat-message
// pull resolves its own bounds with - one home per channel, and the route reads query parameters only.
func ClampDecisionAnswerLimit(limit int) int {
	if limit <= 0 {
		return RoomDecisionPullLimit
	}
	if limit > RoomDecisionMaxPullLimit {
		return RoomDecisionMaxPullLimit
	}
	return limit
}

// The ack's two outcomes. The tokens are the wire's own, so the route passes them through and only
// the daemon names one.
const (
	// RoomDecisionOutcomeApplied is the daemon's report that it applied the answers to its own queue
	// row. It is the only input anywhere that moves a cloud row to resolved.
	RoomDecisionOutcomeApplied = "applied"
	// RoomDecisionOutcomeDropped is the daemon's report that the answer does not apply. The row is
	// acked - so it is never handed out again - and its state is not moved by the drop itself.
	RoomDecisionOutcomeDropped = "dropped"
)

// DroppedAnswerReasons is the CLOSED list a dropped ack's reason must come from, in the contract's
// order. It is one list and not a list plus a set: five strings are cheaper to walk than to keep in
// step, and the membership check is the only reader. The reasons themselves are the daemon's to
// produce and to show a human; the cloud checks membership and stores none of them, because no
// column and no response field holds one.
var DroppedAnswerReasons = []string{
	"state-done",
	"not-the-asked-human",
	"unknown-qitem",
	"already-applied",
	"superseded",
}

func isDroppedAnswerReason(reason string) bool {
	for _, known := range DroppedAnswerReasons {
		if known == reason {
			return true
		}
	}
	return false
}

// RoomDecisionStore is the storage surface the channel needs: the domain repository's own methods,
// named here so the service's dependency is the shape it uses rather than the package.
type RoomDecisionStore interface {
	Create(ctx context.Context, decision repositories.RoomDecision) (*repositories.RoomDecision, bool, error)
	Get(ctx context.Context, userID, roomID, id string) (*repositories.RoomDecision, error)
	GetByID(ctx context.Context, userID, id string) (*repositories.RoomDecision, error)
	ListByRoom(ctx context.Context, userID, roomID string) ([]repositories.RoomDecision, error)
	ListAnswers(ctx context.Context, userID, rigName string, after *repositories.AnswerCursor, limit int) ([]repositories.AnswerDelivery, error)
	RecordAnswer(ctx context.Context, userID, roomID, id string, answers map[string]string, state decisions.State, answeredAt *time.Time) (*repositories.RoomDecision, error)
	Acknowledge(ctx context.Context, userID, id string, applied bool, at time.Time) (*repositories.RoomDecision, bool, error)
	SetState(ctx context.Context, userID, id string, state decisions.State, at time.Time) (*repositories.RoomDecision, error)
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

// DecisionChoiceSelection is the choice and confidence score returned by AI evaluation.
type DecisionChoiceSelection struct {
	SelectedOptionID string
	Confidence       float64
}

// DecisionEvaluator evaluates human questions with AI before human escalation.
type DecisionEvaluator interface {
	SelectDecisionChoices(ctx context.Context, model string, summary, detail string, qs []questions.HumanQuestion) (map[string]DecisionChoiceSelection, error)
}

// JevDecisionLogEntry records evaluation metrics for benchmarking Jev AI decisions.
type JevDecisionLogEntry struct {
	Timestamp           time.Time                          `json:"timestamp"`
	DecisionID          string                             `json:"decision_id"`
	UserID              string                             `json:"user_id"`
	RoomID              string                             `json:"room_id"`
	RigName             string                             `json:"rig_name"`
	AuthorSeatKey       string                             `json:"author_seat_key"`
	Model               string                             `json:"model"`
	ConfidenceThreshold float64                            `json:"confidence_threshold"`
	Summary             string                             `json:"summary"`
	Detail              string                             `json:"detail"`
	Choices             map[string]DecisionChoiceSelection `json:"choices"`
	AutoAnswered        bool                               `json:"auto_answered"`
	Error               string                             `json:"error,omitempty"`
}

var (
	jevLogMutex sync.Mutex
	jevLogPath  string
)

func SetJevDecisionLogPath(path string) {
	jevLogMutex.Lock()
	defer jevLogMutex.Unlock()
	jevLogPath = path
}

func getJevDecisionLogPath() string {
	jevLogMutex.Lock()
	defer jevLogMutex.Unlock()
	if jevLogPath != "" {
		return jevLogPath
	}
	if p := os.Getenv("JEV_DECISION_LOG_PATH"); p != "" {
		return p
	}
	home, _ := os.UserHomeDir()
	if home != "" {
		return filepath.Join(home, ".config", "4genthub", "jev_decisions.log")
	}
	return "jev_decisions.log"
}

func appendJevDecisionLog(entry JevDecisionLogEntry) {
	path := getJevDecisionLogPath()
	if dir := filepath.Dir(path); dir != "" && dir != "." {
		_ = os.MkdirAll(dir, 0o755)
	}

	bytes, err := json.Marshal(entry)
	if err != nil {
		return
	}

	jevLogMutex.Lock()
	defer jevLogMutex.Unlock()

	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		slog.Warn("failed to open jev decision log file", "path", path, "err", err)
		return
	}
	defer f.Close()

	_, _ = f.Write(append(bytes, '\n'))
}

// RoomDecisionService validates and stores mirrored decisions and the clicks on them.
type RoomDecisionService struct {
	store               RoomDecisionStore
	evaluator           DecisionEvaluator
	evaluatorModel      string
	confidenceThreshold float64
}

// NewRoomDecisionService builds the service over a store.
func NewRoomDecisionService(store RoomDecisionStore) *RoomDecisionService {
	return &RoomDecisionService{
		store:               store,
		evaluatorModel:      "jev-1.13.0",
		confidenceThreshold: 0.8,
	}
}

// WithEvaluator configures an AI evaluator for auto-selecting high-confidence choices.
func (s *RoomDecisionService) WithEvaluator(evaluator DecisionEvaluator, model string, minConfidence float64) *RoomDecisionService {
	s.evaluator = evaluator
	if model != "" {
		s.evaluatorModel = model
	} else {
		s.evaluatorModel = "jev-1.13.0"
	}
	if minConfidence > 0 {
		s.confidenceThreshold = minConfidence
	} else {
		s.confidenceThreshold = 0.8
	}
	return s
}

// Create validates one ask and stores it under the caller's tenant.
//
// The questions are parsed with the daemon's own closed limits (domain/questions), so an ask the
// daemon would refuse is refused here, before any row exists - and the credential scan runs over
// the ask's prose, because a decision's detail is text a seat wrote and a seat can paste a token
// into anything.
//
// A row already carrying this ask's (user, qitem_id) is returned unchanged rather than duplicated:
// that pair is the episode - one routed item asked about by one human - and it is the tuple the
// store's insert conflicts on, so a redrive after a lost answer collapses onto the row it already
// made instead of authoring a second decision the human would be asked twice. The second return
// value is the wire's `created`: true when THIS call stored the row, false when an earlier attempt
// already had, which is how the daemon learns its redrive collapsed instead of authoring a second
// ask.
//
// The idempotency key is DERIVED from the routed item rather than free: the daemon mints
// `agenthub:decision:<qitemId>` for the ask it mirrors, so a body whose key names another item is
// refused at this door, before anything is stored, rather than stored as a correlatable value that
// lies about which item it is.
func (s *RoomDecisionService) Create(ctx context.Context, userID, roomID string, ask RoomDecisionAsk, createdAt time.Time) (*repositories.RoomDecision, bool, error) {
	if strings.TrimSpace(roomID) == "" {
		return nil, false, &RoomDecisionAskRejection{Message: "room is required"}
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
			return nil, false, &RoomDecisionAskRejection{Message: field.path + " is required"}
		}
		if utf8.RuneCountInString(trimmed) > RoomDecisionMaxField {
			return nil, false, &RoomDecisionAskRejection{Message: fmt.Sprintf("%s cannot exceed %d characters", field.path, RoomDecisionMaxField)}
		}
	}
	// The key is DERIVED from the routed item: the daemon mints agenthub:decision:<qitemId> for the
	// ask it mirrors, so a body whose key names another item would store a row under a value that
	// lies about which item it is, and a reader hunting that row by the derived key would miss it.
	// The check rides this loop's trimming, and a divergence is a named refusal at the door rather
	// than a silent one in the table - the same posture the ask's limits already take.
	if expected := "agenthub:decision:" + strings.TrimSpace(ask.QitemID); strings.TrimSpace(ask.IdempotencyKey) != expected {
		return nil, false, &RoomDecisionAskRejection{Message: "idempotency_key must be agenthub:decision:<qitem_id>"}
	}
	summary := strings.TrimSpace(ask.Summary)
	if utf8.RuneCountInString(summary) > RoomDecisionMaxSummary {
		return nil, false, &RoomDecisionAskRejection{Message: fmt.Sprintf("summary cannot exceed %d characters", RoomDecisionMaxSummary)}
	}
	detail := strings.TrimSpace(ask.Detail)
	if utf8.RuneCountInString(detail) > RoomDecisionMaxDetail {
		return nil, false, &RoomDecisionAskRejection{Message: fmt.Sprintf("detail cannot exceed %d characters", RoomDecisionMaxDetail)}
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
			return nil, false, &RoomDecisionAskRejection{
				Message:     "secret detected in field " + field.path,
				SecretField: field.path,
			}
		}
	}

	parsed, err := questions.Parse(ask.Questions)
	if err != nil {
		var rejection *questions.Rejection
		if ok := asRejection(err, &rejection); ok {
			return nil, false, &RoomDecisionAskRejection{Message: rejection.Message}
		}
		return nil, false, err
	}

	stored, created, err := s.store.Create(ctx, repositories.RoomDecision{
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
	if err != nil {
		return nil, false, err
	}
	// A created:false ALWAYS carries the winner row: the store's loser path reads the episode back,
	// the same tuple it conflicted on. A nil here means the store lost a row it declined to write, and
	// the route must answer 500 rather than a success envelope with no decision in it.
	if !created && stored == nil {
		return nil, false, fmt.Errorf("room decision create: the row for %s/%s was neither written nor found", userID, ask.QitemID)
	}

	// Jev AI auto-selection: if confidence >= confidenceThreshold (default 0.8), auto-select option;
	// otherwise, leave unanswered for human decision request on 4genthub.
	// Log evaluation metrics to jev_decisions.log for benchmarking.
	if created && stored != nil && s.evaluator != nil {
		choices, evalErr := s.evaluator.SelectDecisionChoices(ctx, s.evaluatorModel, summary, detail, parsed)
		logEntry := JevDecisionLogEntry{
			Timestamp:           createdAt.UTC(),
			DecisionID:          stored.ID,
			UserID:              userID,
			RoomID:              roomID,
			RigName:             ask.RigName,
			AuthorSeatKey:       ask.AuthorSeatKey,
			Model:               s.evaluatorModel,
			ConfidenceThreshold: s.confidenceThreshold,
			Summary:             summary,
			Detail:              detail,
			Choices:             choices,
		}
		if evalErr != nil {
			logEntry.Error = evalErr.Error()
		}

		if evalErr == nil && len(choices) > 0 {
			allAutoAnswered := len(parsed) > 0
			for _, q := range parsed {
				sel, ok := choices[q.ID]
				if ok && sel.Confidence >= s.confidenceThreshold && sel.SelectedOptionID != "" {
					updated, ansErr := s.Answer(ctx, userID, roomID, stored.ID, RoomDecisionAnswerInput{
						QuestionID: q.ID,
						OptionID:   sel.SelectedOptionID,
					}, createdAt)
					if ansErr == nil && updated != nil {
						stored = updated
					} else {
						allAutoAnswered = false
					}
				} else {
					allAutoAnswered = false
				}
			}
			logEntry.AutoAnswered = allAutoAnswered
		}
		appendJevDecisionLog(logEntry)
	}

	return stored, created, nil
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

// The answer leg: the daemon pulls what the human clicked, applies it to its own queue, and acks.
//
// THE CURSOR IS A KEYSET AND NOTHING ELSE: the position is `(answered_at, id)`, rendered as
// `<RFC3339Nano>|<uuid>` and handed back verbatim. That format - and the separator, which occurs in
// neither an instant nor a UUID - is the shipped message pull's, so one daemon-side parser serves both
// pulls and there is no second encoding to keep in step. It is opaque BY CONTRACT: the caller echoes
// it and never builds one. It carries no secret (the pull is already tenant scoped) and no delivery
// state (the ack is the delivery record). The id is part of the position because two answers stored in
// the same instant must still be told apart.
const cursorSeparator = "|"

// cursorUUIDPattern is the shape a cursor's id must have. The store treats a value that is not a
// UUID as naming no row, and a pull that answered "nothing waiting" because its cursor was corrupt
// is worse than a refusal: the daemon would stop asking for work that is waiting for it.
var cursorUUIDPattern = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

// encodeAnswerCursor renders the position the next pull resumes after. The empty cursor is the first
// page, so an empty position encodes to the empty string rather than to a token that decodes to it.
func encodeAnswerCursor(cursor *repositories.AnswerCursor) string {
	if cursor == nil || cursor.ID == "" {
		return ""
	}
	return cursor.AnsweredAt.UTC().Format(time.RFC3339Nano) + cursorSeparator + cursor.ID
}

// decodeAnswerCursor parses a cursor this channel minted, and refuses everything else with the one
// sentence the contract pins - `after "<value>" must be a cursor this endpoint returned` - because a
// caller cannot act on which part of a corrupt token failed, and the token is opaque to them anyway.
func decodeAnswerCursor(raw string) (*repositories.AnswerCursor, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil, nil
	}
	refusal := fmt.Errorf("after %q must be a cursor this endpoint returned", raw)
	rawTime, id, found := strings.Cut(raw, cursorSeparator)
	if !found || !cursorUUIDPattern.MatchString(id) {
		return nil, refusal
	}
	at, err := time.Parse(time.RFC3339Nano, rawTime)
	if err != nil {
		return nil, refusal
	}
	return &repositories.AnswerCursor{AnsweredAt: at.UTC(), ID: id}, nil
}

// Pull hands one daemon the answers it has not applied yet, and the cursor to resume from.
//
// THE PULL IS AT-LEAST-ONCE BY CONSTRUCTION: a row stays in the page until its ack lands, so a
// daemon that died between applying an answer and acking it is handed the same answer again, and the
// apply is idempotent - which is why the ack, not the pull, is what ends the loop. The next cursor
// is the last row handed over, so a resumed pull never repeats one it already delivered.
//
// rigName is the machine identity the answers belong to: answers to another rig's asks are not this
// daemon's work, and an ack is destructive, so pulling them would close decisions nobody applied. The
// room each delivery names is resolved on the way out - the daemon has no room model at all, so the
// pull is the only place it can learn which room one of its own asks was filed in.
func (s *RoomDecisionService) Pull(ctx context.Context, userID, rigName, cursor string, limit int) ([]repositories.AnswerDelivery, string, error) {
	rigName = strings.TrimSpace(rigName)
	if rigName == "" {
		return nil, "", &RoomDecisionAnswerRejection{
			Code:    CodeInvalidPull,
			Message: "rig is required to pull answers",
		}
	}
	after, err := decodeAnswerCursor(cursor)
	if err != nil {
		return nil, "", &RoomDecisionAnswerRejection{Code: CodeInvalidCursor, Message: err.Error()}
	}
	list, err := s.store.ListAnswers(ctx, userID, rigName, after, ClampDecisionAnswerLimit(limit))
	if err != nil {
		return nil, "", err
	}
	next := ""
	if len(list) > 0 {
		last := list[len(list)-1]
		if last.AnsweredAt != nil {
			next = encodeAnswerCursor(&repositories.AnswerCursor{AnsweredAt: *last.AnsweredAt, ID: last.ID})
		}
	}
	return list, next, nil
}

// Acknowledge records what the daemon did with one answer and ends its delivery.
//
// THE TWO OUTCOMES ARE BOTH DELIVERY REPORTS AND ONLY ONE OF THEM CLOSES THE ROW. `applied` says the
// daemon applied the answers to its own queue row: it is the only input anywhere that moves a cloud
// row to resolved, which is what makes the daemon's own report - never the cloud's reading of a click
// - the thing that finishes a decision. `dropped` says the answer does not apply, with a reason from
// the closed list (the daemon is where a human is shown it, and the cloud stores none of it): the row
// is acked exactly the same way, so it is never handed out again and never retried, and its state is
// left to whatever the daemon pushes separately. A reason sent with `applied` means nothing and is
// ignored rather than refused - the field is shared by both outcomes, and a client that fills it in is
// not wrong about a state.
//
// AN ID THAT IS UNKNOWN AND ONE ALREADY ACKED GET THE SAME REFUSAL, and it is a conflict rather than
// a 404, mirroring the shipped message ack: neither redelivers, and a client retrying a dropped ack
// must not hear something that reads like a mistyped id.
func (s *RoomDecisionService) Acknowledge(ctx context.Context, userID, id, outcome, reason string, now time.Time) (*repositories.RoomDecision, error) {
	outcome = strings.TrimSpace(outcome)
	reason = strings.TrimSpace(reason)
	applied := false
	switch outcome {
	case RoomDecisionOutcomeApplied:
		applied = true
	case RoomDecisionOutcomeDropped:
		if reason == "" {
			return nil, &RoomDecisionAnswerRejection{
				Code:    CodeInvalidAck,
				Message: "reason is required when outcome is dropped",
			}
		}
		if !isDroppedAnswerReason(reason) {
			return nil, &RoomDecisionAnswerRejection{
				Code:    CodeInvalidAck,
				Message: "reason " + reason + " is not one of " + strings.Join(DroppedAnswerReasons, ", "),
			}
		}
	default:
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeInvalidAck,
			Message: "outcome must be " + RoomDecisionOutcomeApplied + " or " + RoomDecisionOutcomeDropped,
		}
	}
	written, acked, err := s.store.Acknowledge(ctx, userID, id, applied, now.UTC())
	if err != nil {
		return nil, err
	}
	if !acked {
		if written == nil {
			return nil, &RoomDecisionAnswerRejection{
				Code:    CodeNotAwaitingAck,
				Message: "no decision " + id + " awaiting an ack",
			}
		}
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeNotAwaitingAck,
			Message: "this decision is " + string(written.State) + " and not awaiting an ack",
		}
	}
	return written, nil
}

// SetState writes the daemon's own verdict about a decision that never became an apply - in
// practice `superseded`, which is what a decision answered somewhere else first (Slack) is, and
// what makes the panel refuse a stale click on it.
//
// ONLY THE TWO END STATES ARE ACCEPTED. `pending` and `answered` are the cloud's own, reached by
// recording clicks, and a push that named one of them would re-open a decision the daemon has
// already concluded - the one direction this channel must never move.
//
// THE ROW IS READ BEFORE THE WRITE so a push onto a decision that is already over is refused with the
// token the contract names - `state-<state>`, naming the state the row is IN rather than the one the
// caller asked for - instead of a silent no-op. The write is still guarded, so a second writer that
// concluded the row between the read and the write is the one a lost write's refusal then names.
func (s *RoomDecisionService) SetState(ctx context.Context, userID, id string, state decisions.State, now time.Time) (*repositories.RoomDecision, error) {
	switch state {
	case decisions.StateResolved, decisions.StateSuperseded:
	default:
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownState,
			Message: "the daemon may push resolved or superseded, not " + string(state),
		}
	}
	stored, err := s.store.GetByID(ctx, userID, id)
	if err != nil {
		return nil, err
	}
	if stored == nil {
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownDecision,
			Message: "no decision " + id,
		}
	}
	if stored.State == decisions.StateResolved || stored.State == decisions.StateSuperseded {
		return nil, closedDecision(stored.State)
	}
	written, err := s.store.SetState(ctx, userID, id, state, now.UTC())
	if err != nil {
		return nil, err
	}
	if written == nil {
		return nil, &RoomDecisionAnswerRejection{
			Code:    CodeUnknownDecision,
			Message: "no decision " + id,
		}
	}
	if written.State != state {
		return nil, closedDecision(written.State)
	}
	return written, nil
}

// closedDecision is the refusal a push onto a decision that is already over gets. The token is alone
// in both the code and the message, because the body the contract pins for it is
// `{"detail":"state-<state>"}` and nothing else.
func closedDecision(state decisions.State) *RoomDecisionAnswerRejection {
	token := decisions.RefusalCode(state)
	return &RoomDecisionAnswerRejection{Code: token, Message: token}
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
