package httpapp

// room_decisions_mount.go is the room decision channel over HTTP: a human answers, from the panel,
// the structured questions a room's daemon mirrored up for their room.
//
//	GET  /api/v2/rooms/{room}/decisions             user token, tenant-scoped by the caller
//	POST /api/v2/rooms/{room}/decisions/{id}/answer user token, one click per call
//
// The prefix is the room family's own (`/api/v2/rooms`, where `{room}` is the SLUG), the
// same root room spec and the seat routes serve: a second prefix for one entity would be a second way
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
	"strconv"
	"strings"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	roomservices "agenthub/fastmcp/room_decisions/application/services"
	roomdecisions "agenthub/fastmcp/room_decisions/domain/decisions"
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

// An ask body carries the prose a human reads, so its cap is the service's own text limits with room
// for the envelope and the questions: 4 000 runes of detail are at most 16 000 BYTES (a rune is at
// most four), and the summary, up to four questions and the identifier tokens add a few kilobytes. 64
// KiB accepts the largest ask those limits allow and still refuses a body that is not one.
const roomDecisionMaxAskBody = 1 << 16

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
	mux.HandleFunc("GET /api/v2/rooms/{room}/decisions", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRoomDecisions(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/rooms/{room}/decisions/{id}/answer", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRoomDecisionAnswer(w, r, u, sessions)
	}))
	// The crossing: the four routes a room's daemon drives. They are ROOM-scoped rather than
	// tenant-scoped because the daemon has no tenant model at all - it knows the room it runs on and the
	// decision id the cloud handed it, and the cloud, not the daemon, holds the room.
	mux.HandleFunc("POST /api/v2/decisions", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleIngestRoomDecision(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/decisions/answers", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handlePullRoomDecisionAnswers(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/decisions/{id}/ack", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleAckRoomDecision(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/decisions/{id}/state", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handlePushRoomDecisionState(w, r, u, sessions)
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
	if !decodeRoomDecisionBody(w, r, &body, roomDecisionMaxBody) {
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
// is the conflict: the decision is real, the click is too late. A malformed request - a cursor this
// channel did not mint, a pull with no room, an outcome or state the daemon may not write - is a 400,
// because nothing about the decision is wrong. An unrecognised token is a conflict too, because every
// refusal the service raises names a state or a vocabulary miss and a 500 would report a client's
// wrong click as the server's fault.
func roomDecisionRefusalStatus(code string) int {
	switch code {
	case roomservices.CodeUnknownDecision:
		return http.StatusNotFound
	case roomservices.CodeNotTheAskedHuman:
		return http.StatusForbidden
	case roomservices.CodeUnknownQuestion, roomservices.CodeUnknownOption:
		return http.StatusUnprocessableEntity
	case roomservices.CodeInvalidCursor, roomservices.CodeInvalidPull,
		roomservices.CodeInvalidAck, roomservices.CodeUnknownState:
		return http.StatusBadRequest
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

// decodeRoomDecisionBody reads one request body into out, up to max bytes. Unknown fields are refused
// rather than ignored (the feedback route's decoder does the same): a client that spells an option
// field wrong should hear so, not have its click silently treated as a missing one.
func decodeRoomDecisionBody(w http.ResponseWriter, r *http.Request, out any, max int64) bool {
	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(http.MaxBytesReader(w, r.Body, max)); err != nil {
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

// The crossing: the daemon's half of the channel, four routes, one per leg of an ask's round trip.
//
//	POST /api/v2/decisions           ingest one mirrored ask
//	GET  /api/v2/decisions/answers   pull the answers this room has not acked
//	POST /api/v2/decisions/{id}/ack  record what the daemon did with one answer
//	POST /api/v2/decisions/{id}/state push a state it learned without an answer
//
// The vocabulary is deliberately the shipped message pull's - query parameter `after`, response field
// `cursor`, the `success` envelope, `machine_id` on the write bodies - so one daemon-side parser
// serves both channels, and the refusals are the contract's: `{"detail":…}` with the MESSAGE alone,
// because the freeze pins what several of them say and the code-prefixed form the room routes use
// would change it.

// roomDecisionIngestRequest is the ask body. room is required - it names the room the ask is filed
// in - and questions is carried raw because the daemon's own closed limits are enforced by the
// service, which owns one implementation of them rather than this route owning a second - and the
// same holds for idempotency_key, whose value the service requires to derive from this body's
// qitem_id. A body carrying the retired key is refused by the strict decoder, so the wire has
// one name for the unit.
type roomDecisionIngestRequest struct {
	Room           string          `json:"room"`
	QitemID        string          `json:"qitem_id"`
	AuthorSeatKey  string          `json:"author_seat_key"`
	Destination    string          `json:"destination"`
	Summary        string          `json:"summary"`
	Detail         string          `json:"detail"`
	Questions      json.RawMessage `json:"questions"`
	IdempotencyKey string          `json:"idempotency_key"`
}

// handleIngestRoomDecision is route 1: one mirrored ask arriving from a room's daemon.
//
// THE ROOM IS RESOLVED HERE, ONCE, AND IT IS THE OWNER-SCOPED RESOLVE: the daemon writes as the
// human's own account, so a slug that is not that account's room is the 404 the contract names rather
// than somebody else's shared room. A body that names no room is refused by the service, because the
// room is the only unit this wire carries: there is no fallback name to guess from.
func handleIngestRoomDecision(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	service, rooms, ok := roomDecisionDepsFor(w, sessions)
	if !ok {
		return
	}
	callerID := userID(u)
	var body roomDecisionIngestRequest
	if !decodeRoomDecisionBody(w, r, &body, roomDecisionMaxAskBody) {
		return
	}
	slug := strings.TrimSpace(body.Room)
	room, err := rooms.GetBySlug(r.Context(), callerID, slug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if room == nil {
		writeDetail(w, http.StatusNotFound, "room \""+slug+"\" not found")
		return
	}
	stored, created, err := service.Create(r.Context(), callerID, room.ID, roomservices.RoomDecisionAsk{
		RoomName:        body.Room,
		QitemID:        body.QitemID,
		AuthorSeatKey:  body.AuthorSeatKey,
		Destination:    body.Destination,
		Summary:        body.Summary,
		Detail:         body.Detail,
		Questions:      body.Questions,
		IdempotencyKey: body.IdempotencyKey,
	}, roomDecisionNow().UTC())
	if err != nil {
		var rejection *roomservices.RoomDecisionAskRejection
		if errors.As(err, &rejection) {
			// A credential in a free-text field is the ONE refusal with its own envelope, the rule the
			// feedback route already follows; every other ask refusal is the contract's 400 detail.
			if rejection.SecretField != "" {
				writeSeatStatusError(w, http.StatusUnprocessableEntity, rejection.Message)
				return
			}
			writeDetail(w, http.StatusBadRequest, rejection.Message)
			return
		}
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("decision", roomDecisionRow(*stored))
	response.Set("created", created)
	writeJSON(w, http.StatusOK, response)
}

// handlePullRoomDecisionAnswers is route 2: one daemon takes the answers its account has not acked.
//
// THE PAGE BOUNDS COME FROM THE SERVICE (ClampDecisionAnswerLimit) rather than from this route, so the
// numbers a daemon pages by have one home and the route only reads query parameters. An empty `cursor`
// in the response says the page was the last one.
func handlePullRoomDecisionAnswers(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	service, _, ok := roomDecisionDepsFor(w, sessions)
	if !ok {
		return
	}
	limit := 0
	if raw := r.URL.Query().Get("limit"); raw != "" {
		if n, convErr := strconv.Atoi(raw); convErr == nil {
			limit = n
		}
	}
	answers, cursor, err := service.Pull(r.Context(), userID(u), r.URL.Query().Get("after"), limit)
	if err != nil {
		if !writeRoomDecisionCrossingRefusal(w, err) {
			writeDetail(w, http.StatusInternalServerError, err.Error())
		}
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("answers", roomDecisionAnswerRows(answers))
	body.Set("cursor", cursor)
	writeJSON(w, http.StatusOK, body)
}

// roomDecisionAckRequest is the ack body. machine_id is the daemon's hostId under the cloud's field
// name; the row is keyed by the decision id the pull handed out and the tenant of the bearer, so the
// machine is recorded nowhere and nothing here trusts it. reason is required only for a drop, where it
// must come from the closed list.
type roomDecisionAckRequest struct {
	MachineID string `json:"machine_id"`
	Outcome   string `json:"outcome"`
	Reason    string `json:"reason"`
}

// handleAckRoomDecision is route 3: the daemon reports what became of one answer, which is what ends
// its delivery. `applied` is the only thing anywhere that resolves a cloud row, so this call is where
// a decision finishes; a dropped answer is acked too, and never handed out again.
func handleAckRoomDecision(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	service, _, ok := roomDecisionDepsFor(w, sessions)
	if !ok {
		return
	}
	var body roomDecisionAckRequest
	if !decodeRoomDecisionBody(w, r, &body, roomDecisionMaxBody) {
		return
	}
	stored, err := service.Acknowledge(r.Context(), userID(u), r.PathValue("id"), body.Outcome, body.Reason, roomDecisionNow().UTC())
	if err != nil {
		if !writeRoomDecisionCrossingRefusal(w, err) {
			writeDetail(w, http.StatusInternalServerError, err.Error())
		}
		return
	}
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("delivered", true)
	response.Set("state", string(stored.State))
	writeJSON(w, http.StatusOK, response)
}

// roomDecisionStateRequest is the state push body: the machine, the state the daemon learned without
// an answer, and the token naming why. Only the state is acted on - there is no column for a reason,
// and the daemon is where a human reads one.
type roomDecisionStateRequest struct {
	MachineID string `json:"machine_id"`
	State     string `json:"state"`
	Reason    string `json:"reason"`
}

// handlePushRoomDecisionState is route 4: a transition the daemon learned with no answer in hand - the
// ask was answered in Slack first, or its local row was withdrawn. A push onto a decision that is
// already over is refused with `state-<state>`, naming the state the row is in.
func handlePushRoomDecisionState(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	service, _, ok := roomDecisionDepsFor(w, sessions)
	if !ok {
		return
	}
	var body roomDecisionStateRequest
	if !decodeRoomDecisionBody(w, r, &body, roomDecisionMaxBody) {
		return
	}
	stored, err := service.SetState(r.Context(), userID(u), r.PathValue("id"), roomdecisions.State(body.State), roomDecisionNow().UTC())
	if err != nil {
		if !writeRoomDecisionCrossingRefusal(w, err) {
			writeDetail(w, http.StatusInternalServerError, err.Error())
		}
		return
	}
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("state", string(stored.State))
	writeJSON(w, http.StatusOK, response)
}

// writeRoomDecisionCrossingRefusal writes a service refusal as the contract's own body, and reports
// whether it was one: the MESSAGE alone rather than the code-prefixed Error(), because the freeze pins
// what several of these say verbatim (the malformed cursor's sentence, the state push's
// `state-<state>`) and the room routes' `code: message` form would change them.
func writeRoomDecisionCrossingRefusal(w http.ResponseWriter, err error) bool {
	var rejection *roomservices.RoomDecisionAnswerRejection
	if !errors.As(err, &rejection) {
		return false
	}
	writeDetail(w, roomDecisionRefusalStatus(rejection.Code), rejection.Message)
	return true
}

// roomDecisionAnswerRows is the pulled page as the daemon reads it: the six keys the contract names,
// every one of them always present. `room` is the SLUG and not the row's room id, because the daemon
// has no room model - it never resolved one and could not use an id. `answered_at` is RFC3339Nano in
// UTC, the same instant the cursor's first half carries, null only for a row that is `answered` with
// no answered_at (which the answer contract does not produce).
func roomDecisionAnswerRows(deliveries []roomrepo.AnswerDelivery) []any {
	rows := make([]any, 0, len(deliveries))
	for _, delivery := range deliveries {
		var answeredAt any
		if delivery.AnsweredAt != nil {
			answeredAt = delivery.AnsweredAt.UTC().Format(time.RFC3339Nano)
		}
		row := entities.NewOrderedMap[any]()
		row.Set("decision_id", delivery.ID)
		row.Set("qitem_id", delivery.QitemID)
		row.Set("author_seat_key", delivery.AuthorSeatKey)
		row.Set("room", delivery.RoomSlug)
		row.Set("answers", delivery.Answers)
		row.Set("answered_at", answeredAt)
		rows = append(rows, row)
	}
	return rows
}
