package httpapp

// room_decisions_mount.go is the room decision channel over HTTP: a human answers, from the panel,
// the structured questions a rig's daemon mirrored up for their room.
//
//	GET  /api/v2/openrig/rooms/{room}/decisions             user token, tenant-scoped by the caller
//	POST /api/v2/openrig/rooms/{room}/decisions/{id}/answer user token, one click per call
//
// The prefix is the room family's own (`/api/v2/openrig/rooms`, where `{room}` is the SLUG), the
// same root rigspec and the seat routes serve: a second prefix for one entity would be a second way
// to name a room.
//
// This file owns the transport only. The writer contract - the ported question limits, the bounds,
// the credential scan and the answer validation order - is RoomDecisionService, and the store is the
// tenant-scoped ORM repository.
//
// WHY THE RESPONSE SHAPES ARE NOT WRAPPED IN `success`: the answer response mirrors the daemon's
// RecordHumanAnswerResult ({state, answers, complete}) and the read mirrors what the panel renders,
// so a client that knows one side of this channel knows the other. The feedback family's `success`
// envelope would be a translation layer for no benefit.

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	roomservices "agenthub/fastmcp/room_decisions/application/services"
	roomquestions "agenthub/fastmcp/room_decisions/domain/questions"
	roomrepo "agenthub/fastmcp/room_decisions/domain/repositories"
	roomorm "agenthub/fastmcp/room_decisions/infrastructure/repositories/orm"
	"agenthub/fastmcp/seat_management/domain/repositories"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// A click body is three tokens, never a payload.
const roomDecisionMaxBody = 1 << 14

// roomDecisionRooms is the room lookup the routes need: the strict owner-scoped read for the answer
// (the caller must OWN the room it answers in), and the visible read that tells "not yours" apart
// from "no such room".
type roomDecisionRooms interface {
	GetBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
	GetVisibleBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
}

// newRoomDecisionRooms and newRoomDecisionService are package variables so tests can substitute
// fakes without a database.
var newRoomDecisionRooms = func(sessions *database.SessionManager) (roomDecisionRooms, error) {
	return seatorm.NewORMRoomRepository(sessions)
}

var newRoomDecisionService = func(sessions *database.SessionManager) (*roomservices.RoomDecisionService, error) {
	repo, err := roomorm.NewORMRoomDecisionRepository(sessions)
	if err != nil {
		return nil, err
	}
	return roomservices.NewRoomDecisionService(repo), nil
}

// roomDecisionNow is the server clock; tests substitute a fixed one.
var roomDecisionNow = time.Now

// roomDecisionAnswerRequest is the answer body. idempotency_key is optional and is the caller's
// retry token; the service's Answer records why the row has no column to store it in and what the
// contract promises observably in its place.
type roomDecisionAnswerRequest struct {
	QuestionID     string `json:"question_id"`
	OptionID       string `json:"option_id"`
	IdempotencyKey string `json:"idempotency_key"`
}

func mountRoomDecisionRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/decisions", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRoomDecisions(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/openrig/rooms/{room}/decisions/{id}/answer", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRoomDecisionAnswer(w, r, u, sessions)
	}))
}

func roomDecisionDepsFor(w http.ResponseWriter, sessions *database.SessionManager) (*roomservices.RoomDecisionService, roomDecisionRooms, bool) {
	service, err := newRoomDecisionService(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, nil, false
	}
	rooms, err := newRoomDecisionRooms(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, nil, false
	}
	return service, rooms, true
}

// handleRoomDecisions is the read: this room's decisions for the CALLER.
//
// The room is resolved through the visible read (the room routes' read rule: a room shared with the
// caller's team is readable), and the rows are then scoped to the caller's own tenant - never to the
// room owner's. A viewer of a shared room therefore reads an empty list rather than the owner's
// decisions, which is the tenancy the acceptance names.
func handleRoomDecisions(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	service, rooms, ok := roomDecisionDepsFor(w, sessions)
	if !ok {
		return
	}
	callerID := userID(u)
	roomSlug := r.PathValue("room")
	room, err := rooms.GetVisibleBySlug(r.Context(), callerID, roomSlug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if room == nil {
		writeDetail(w, http.StatusNotFound, "room \""+roomSlug+"\" not found")
		return
	}
	list, err := service.List(r.Context(), callerID, room.ID)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, roomDecisionsBody(list))
}

// handleRoomDecisionAnswer is the write: one click, validated in the contract's order by the
// service, refused with the contract's token and status.
//
// THE ROOM LOOKUP IS THE STRICT ONE. The ask is addressed to the room's human, and the room's owner
// is who answers for them, so a caller who merely shares the room is refused with
// not-the-asked-human (403) rather than being allowed to answer for somebody else's human - and a
// caller with no relationship to the room at all gets the same 404 an unknown room gets.
func handleRoomDecisionAnswer(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	service, rooms, ok := roomDecisionDepsFor(w, sessions)
	if !ok {
		return
	}
	callerID := userID(u)
	roomSlug := r.PathValue("room")
	room, err := rooms.GetBySlug(r.Context(), callerID, roomSlug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if room == nil {
		visible, err := rooms.GetVisibleBySlug(r.Context(), callerID, roomSlug)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, err.Error())
			return
		}
		if visible == nil {
			writeDetail(w, http.StatusNotFound, "room \""+roomSlug+"\" not found")
			return
		}
		writeDetail(w, http.StatusForbidden, roomservices.CodeNotTheAskedHuman+": this decision is addressed to the room's owner")
		return
	}

	var body roomDecisionAnswerRequest
	if !decodeRoomDecisionBody(w, r, &body) {
		return
	}
	stored, err := service.Answer(r.Context(), callerID, room.ID, r.PathValue("id"), roomservices.RoomDecisionAnswerInput{
		QuestionID:     body.QuestionID,
		OptionID:       body.OptionID,
		IdempotencyKey: body.IdempotencyKey,
	}, roomDecisionNow().UTC())
	if err != nil {
		var rejection *roomservices.RoomDecisionAnswerRejection
		if errors.As(err, &rejection) {
			writeDetail(w, roomDecisionRefusalStatus(rejection.Code), rejection.Error())
			return
		}
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, roomDecisionAnswerBody(*stored))
}

// roomDecisionRefusalStatus is the status the contract pairs with each refusal token. `state-<state>`
// is the conflict: the decision is real, the click is too late. An unrecognised token is a conflict
// too, because every refusal the service raises names a state or a vocabulary miss and a 500 would
// report a client's wrong click as the server's fault.
func roomDecisionRefusalStatus(code string) int {
	switch code {
	case roomservices.CodeUnknownDecision:
		return http.StatusNotFound
	case roomservices.CodeNotTheAskedHuman:
		return http.StatusForbidden
	case roomservices.CodeUnknownQuestion, roomservices.CodeUnknownOption:
		return http.StatusUnprocessableEntity
	default:
		return http.StatusConflict
	}
}

// roomDecisionsBody is the read's shape: one `decisions` array, the contract's own key list per row
// and nothing else. An empty room is an empty array, not a missing key.
func roomDecisionsBody(list []roomrepo.RoomDecision) *entities.OrderedMap[any] {
	rows := make([]any, 0, len(list))
	for _, decision := range list {
		rows = append(rows, roomDecisionRow(decision))
	}
	body := entities.NewOrderedMap[any]()
	body.Set("decisions", rows)
	return body
}

// roomDecisionRow is the row the panel renders. questions is the STORED list verbatim - the panel
// offers exactly the options the cloud validated a click against - and answers is the map it has
// recorded so far, `{}` while nothing is answered. answered_at is null while the ask is pending.
func roomDecisionRow(decision roomrepo.RoomDecision) *entities.OrderedMap[any] {
	row := entities.NewOrderedMap[any]()
	row.Set("id", decision.ID)
	row.Set("qitem_id", decision.QitemID)
	row.Set("author_seat_key", decision.AuthorSeatKey)
	row.Set("summary", decision.Summary)
	row.Set("detail", decision.Detail)
	row.Set("questions", roomDecisionQuestions(decision.Questions))
	row.Set("answers", decision.Answers)
	row.Set("state", string(decision.State))
	row.Set("created_at", decision.CreatedAt.UTC().Format(time.RFC3339))
	row.Set("answered_at", roomDecisionInstant(decision.AnsweredAt))
	return row
}

// roomDecisionQuestions renders the stored list for the response. PyJSONDumpsCompact walks strings,
// numbers, bools, slices, maps and OrderedMaps and refuses a struct outright, so the stored
// []HumanQuestion handed to it straight - which is what this row did first - fails serialization and
// turns the panel's read into a 500. recommended is set only when the ask carried it, the field's own
// omitempty rule: an absent recommendation stays absent rather than becoming a null the panel would
// have to read as "not recommended".
func roomDecisionQuestions(stored []roomquestions.HumanQuestion) []any {
	out := make([]any, 0, len(stored))
	for _, question := range stored {
		row := entities.NewOrderedMap[any]()
		row.Set("id", question.ID)
		row.Set("question", question.Question)
		options := make([]any, 0, len(question.Options))
		for _, option := range question.Options {
			entry := entities.NewOrderedMap[any]()
			entry.Set("id", option.ID)
			entry.Set("label", option.Label)
			if option.Recommended != nil {
				entry.Set("recommended", *option.Recommended)
			}
			options = append(options, entry)
		}
		row.Set("options", options)
		out = append(out, row)
	}
	return out
}

// roomDecisionAnswerBody mirrors RecordHumanAnswerResult: the state the row is in, every answer
// recorded so far, and whether the ask is complete - which is what tells the panel to stop offering
// clicks and start showing "awaiting the room".
func roomDecisionAnswerBody(decision roomrepo.RoomDecision) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("state", string(decision.State))
	body.Set("answers", decision.Answers)
	body.Set("complete", decision.Complete())
	return body
}

// roomDecisionInstant renders a nullable instant as RFC3339 in UTC, or null when the column is NULL.
func roomDecisionInstant(at *time.Time) any {
	if at == nil {
		return nil
	}
	return at.UTC().Format(time.RFC3339)
}

// decodeRoomDecisionBody reads one click body. Unknown fields are refused rather than ignored (the
// feedback route's decoder does the same): a client that spells an option field wrong should hear
// so, not have its click silently treated as a missing one.
func decodeRoomDecisionBody(w http.ResponseWriter, r *http.Request, out *roomDecisionAnswerRequest) bool {
	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(http.MaxBytesReader(w, r.Body, roomDecisionMaxBody)); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return false
	}
	dec := json.NewDecoder(buf)
	dec.DisallowUnknownFields()
	if err := dec.Decode(out); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return false
	}
	return true
}
