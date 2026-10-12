package httpapp

// Route tests for the room decision channel, over in-memory stores: real requests through the
// mounted routes, no database. What is pinned here is what a consumer depends on - the two response
// shapes, the refusal tokens and statuses, and who may answer at all - and the store is inspected
// after every refusal, because "no write" is half of what the acceptance asks for.
//
// The three acceptance cases that are claims about ROWS are in room_decisions_pg_test.go, which
// needs a real database; these cases need none.

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	roomservices "agenthub/fastmcp/room_decisions/application/services"
	"agenthub/fastmcp/room_decisions/domain/decisions"
	"agenthub/fastmcp/room_decisions/domain/questions"
	roomrepo "agenthub/fastmcp/room_decisions/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// A fixed clock, so the stored instant is asserted rather than tolerated.
var roomDecisionTestNow = time.Date(2026, 10, 12, 19, 4, 5, 0, time.UTC)

const (
	roomDecisionTestRoomID  = "a1e0d3c2-1111-4111-8111-00000000000a"
	roomDecisionTestOtherID = "a1e0d3c2-1111-4111-8111-00000000000b"
	roomDecisionTestUserA   = "11111111-1111-4111-8111-111111111111"
	roomDecisionTestUserB   = "22222222-2222-4222-8222-222222222222"
	roomDecisionTestDecID   = "d1e0d3c2-3333-4333-8333-000000000001"
)

func roomDecisionTestQuestions() []questions.HumanQuestion {
	return []questions.HumanQuestion{
		{ID: "q1", Question: "Ship the cloud half first?", Options: []questions.HumanQuestionOption{
			{ID: "ship", Label: "Ship it"},
			{ID: "wait", Label: "Wait"},
		}},
		{ID: "q2", Question: "Who reviews?", Options: []questions.HumanQuestionOption{
			{ID: "lead", Label: "The lead"},
			{ID: "me", Label: "Me"},
		}},
	}
}

// fakeRoomDecisionStore is an in-memory RoomDecisionStore that records how many writes it was
// asked to make, which is how a refusal is shown to have written nothing.
type fakeRoomDecisionStore struct {
	rows         map[string]roomrepo.RoomDecision
	recordCalls  int
	lastAnswer   map[string]string
	lastRecorded decisions.State
}

func newFakeRoomDecisionStore(rows ...roomrepo.RoomDecision) *fakeRoomDecisionStore {
	store := &fakeRoomDecisionStore{rows: map[string]roomrepo.RoomDecision{}}
	for _, row := range rows {
		store.rows[row.ID] = row
	}
	return store
}

func (f *fakeRoomDecisionStore) Create(_ context.Context, decision roomrepo.RoomDecision) (*roomrepo.RoomDecision, error) {
	for _, existing := range f.rows {
		if existing.UserID == decision.UserID && existing.IdempotencyKey == decision.IdempotencyKey {
			copied := existing
			return &copied, nil
		}
	}
	if decision.ID == "" {
		decision.ID = fmt.Sprintf("rd-%04d", len(f.rows)+1)
	}
	f.rows[decision.ID] = decision
	stored := decision
	return &stored, nil
}

func (f *fakeRoomDecisionStore) Get(_ context.Context, userID, roomID, id string) (*roomrepo.RoomDecision, error) {
	row, ok := f.rows[id]
	if !ok || row.UserID != userID || row.RoomID != roomID {
		return nil, nil
	}
	copied := row
	return &copied, nil
}

func (f *fakeRoomDecisionStore) ListByRoom(_ context.Context, userID, roomID string) ([]roomrepo.RoomDecision, error) {
	out := []roomrepo.RoomDecision{}
	for _, row := range f.rows {
		if row.UserID == userID && row.RoomID == roomID {
			out = append(out, row)
		}
	}
	return out, nil
}

func (f *fakeRoomDecisionStore) RecordAnswer(_ context.Context, userID, roomID, id string, answers map[string]string, state decisions.State, answeredAt *time.Time) (*roomrepo.RoomDecision, error) {
	f.recordCalls++
	row, ok := f.rows[id]
	if !ok || row.UserID != userID || row.RoomID != roomID {
		return nil, nil
	}
	row.Answers = answers
	row.State = state
	row.AnsweredAt = answeredAt
	f.rows[id] = row
	f.lastAnswer = answers
	f.lastRecorded = state
	copied := row
	return &copied, nil
}

// fakeRoomDecisionRooms is the two-lookup room source: owner-scoped by slug, and the wider visible
// read that tells "shared with me" apart from "no such room".
type fakeRoomDecisionRooms struct {
	owned   map[string]repositories.Room
	visible map[string]repositories.Room
}

func (f *fakeRoomDecisionRooms) GetBySlug(_ context.Context, userID, slug string) (*repositories.Room, error) {
	if room, ok := f.owned[slug]; ok && room.UserID == userID {
		copied := room
		return &copied, nil
	}
	return nil, nil
}

func (f *fakeRoomDecisionRooms) GetVisibleBySlug(_ context.Context, userID, slug string) (*repositories.Room, error) {
	if room, ok := f.owned[slug]; ok && room.UserID == userID {
		copied := room
		return &copied, nil
	}
	if room, ok := f.visible[slug]; ok {
		copied := room
		return &copied, nil
	}
	return nil, nil
}

type roomDecisionFixture struct {
	t     *testing.T
	mux   *http.ServeMux
	store *fakeRoomDecisionStore
	rooms *fakeRoomDecisionRooms
	user  string
}

func newRoomDecisionFixture(t *testing.T) *roomDecisionFixture {
	t.Helper()
	f := &roomDecisionFixture{
		t:    t,
		user: roomDecisionTestUserA,
		rooms: &fakeRoomDecisionRooms{
			owned: map[string]repositories.Room{
				"alpha": {ID: roomDecisionTestRoomID, UserID: roomDecisionTestUserA, Slug: "alpha"},
			},
			// A room the caller's team shares with them: readable, never answerable.
			visible: map[string]repositories.Room{
				"shared": {ID: roomDecisionTestOtherID, UserID: roomDecisionTestUserB, Slug: "shared"},
			},
		},
	}
	return f
}

func (f *roomDecisionFixture) withRows(rows ...roomrepo.RoomDecision) *roomDecisionFixture {
	f.store = newFakeRoomDecisionStore(rows...)
	return f
}

func (f *roomDecisionFixture) mount() *roomDecisionFixture {
	f.t.Helper()
	previousUsers := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(_ context.Context, _ string) (*authdomain.User, error) {
		id := f.user
		return &authdomain.User{ID: &id, Email: "owner@example.com", Username: "owner"}, nil
	}
	previousService, previousRooms, previousNow := newRoomDecisionService, newRoomDecisionRooms, roomDecisionNow
	newRoomDecisionService = func(*database.SessionManager) (*roomservices.RoomDecisionService, error) {
		return roomservices.NewRoomDecisionService(f.store), nil
	}
	newRoomDecisionRooms = func(*database.SessionManager) (roomDecisionRooms, error) { return f.rooms, nil }
	roomDecisionNow = func() time.Time { return roomDecisionTestNow }
	f.t.Cleanup(func() {
		authinterface.GetCurrentUserUniversal = previousUsers
		newRoomDecisionService, newRoomDecisionRooms, roomDecisionNow = previousService, previousRooms, previousNow
	})
	f.mux = http.NewServeMux()
	mountRoomDecisionRoutes(f.mux, nil)
	return f
}

func (f *roomDecisionFixture) do(method, path, bearer, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if bearer != "" {
		req.Header.Set("Authorization", "Bearer "+bearer)
	}
	rec := httptest.NewRecorder()
	f.mux.ServeHTTP(rec, req)
	return rec
}

func (f *roomDecisionFixture) answer(slug, id, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	return f.do(http.MethodPost, "/api/v2/openrig/rooms/"+slug+"/decisions/"+id+"/answer", "user-jwt", body)
}

func (f *roomDecisionFixture) read(slug string) *httptest.ResponseRecorder {
	f.t.Helper()
	return f.do(http.MethodGet, "/api/v2/openrig/rooms/"+slug+"/decisions", "user-jwt", "")
}

// pendingDecision is one mirrored ask of user A in room alpha.
func pendingDecision() roomrepo.RoomDecision {
	return roomrepo.RoomDecision{
		ID:             roomDecisionTestDecID,
		UserID:         roomDecisionTestUserA,
		RoomID:         roomDecisionTestRoomID,
		RigName:        "4genthub-min",
		QitemID:        "qitem-20261012190405-abcdef0123456789",
		AuthorSeatKey:  "go-dev",
		Destination:    "human-operator@kernel",
		Summary:        "ship the cloud half first?",
		Questions:      roomDecisionTestQuestions(),
		Answers:        map[string]string{},
		State:          decisions.StatePending,
		IdempotencyKey: "agenthub:decision:qitem-20261012190405-abcdef0123456789",
		CreatedAt:      roomDecisionTestNow,
	}
}

// TestRoomDecisionReadIsThePanelsShape pins the read: the contract's own row keys, the stored
// question list verbatim (the panel offers exactly the options the cloud validated a click against),
// and answers as an object rather than null.
func TestRoomDecisionReadIsThePanelsShape(t *testing.T) {
	f := newRoomDecisionFixture(t).withRows(pendingDecision()).mount()

	rec := f.read("alpha")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET = %d %s", rec.Code, rec.Body.String())
	}
	var body struct {
		Decisions []map[string]any `json:"decisions"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode %s: %v", rec.Body.String(), err)
	}
	if len(body.Decisions) != 1 {
		t.Fatalf("decisions = %v, want the one pending ask", body.Decisions)
	}
	row := body.Decisions[0]
	want := []string{"id", "qitem_id", "author_seat_key", "summary", "detail", "questions", "answers", "state", "created_at", "answered_at"}
	if len(row) != len(want) {
		t.Fatalf("row keys = %v, want exactly %v", row, want)
	}
	for _, key := range want {
		if _, ok := row[key]; !ok {
			t.Errorf("row is missing the contract's key %q: %v", key, row)
		}
	}
	if row["state"] != "pending" || row["author_seat_key"] != "go-dev" {
		t.Errorf("row = %v", row)
	}
	if row["created_at"] != "2026-10-12T19:04:05Z" {
		t.Errorf("created_at = %v, want the RFC3339 instant", row["created_at"])
	}
	if row["answered_at"] != nil {
		t.Errorf("answered_at = %v, want null while the ask is pending", row["answered_at"])
	}
	// answers is an empty object, not null: the panel iterates it.
	answers, ok := row["answers"].(map[string]any)
	if !ok || len(answers) != 0 {
		t.Errorf("answers = %v, want an empty object", row["answers"])
	}
	// questions is the stored list verbatim, embedded as JSON rather than as a string.
	list, ok := row["questions"].([]any)
	if !ok || len(list) != 2 {
		t.Fatalf("questions = %v, want the two stored questions as a JSON array", row["questions"])
	}
	if first, ok := list[0].(map[string]any); !ok || first["id"] != "q1" {
		t.Errorf("first question = %v", list[0])
	}
}

// TestRoomDecisionReadNeverCrossesRoomOrTenant is the acceptance's third case at the route level:
// the rows are the CALLER's, so another room's ask and another tenant's ask are both absent, and a
// room the caller may not see is a 404 rather than an empty list that pretends to be one.
func TestRoomDecisionReadNeverCrossesRoomOrTenant(t *testing.T) {
	otherRoomDecision := pendingDecision()
	otherRoomDecision.ID = "d1e0d3c2-3333-4333-8333-000000000002"
	otherRoomDecision.RoomID = roomDecisionTestOtherID
	otherRoomDecision.UserID = roomDecisionTestUserB
	otherRoomDecision.IdempotencyKey = "agenthub:decision:other"

	f := newRoomDecisionFixture(t).withRows(pendingDecision(), otherRoomDecision).mount()

	// The caller's own room: exactly their one row.
	rec := f.read("alpha")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET alpha = %d %s", rec.Code, rec.Body.String())
	}
	var body struct {
		Decisions []map[string]any `json:"decisions"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if len(body.Decisions) != 1 || body.Decisions[0]["id"] != roomDecisionTestDecID {
		t.Fatalf("GET alpha answered %v, want only the caller's own ask", body.Decisions)
	}

	// A room shared with the caller: readable, and the OTHER tenant's ask is not in it.
	f.user = roomDecisionTestUserA
	shares := f.rooms.visible["shared"]
	f.rooms.owned["shared"] = shares // visible to A, owned by B
	rec = f.read("shared")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET shared = %d %s", rec.Code, rec.Body.String())
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if len(body.Decisions) != 0 {
		t.Fatalf("a viewer of a shared room read %v, want nothing: the rows are the caller's", body.Decisions)
	}

	// A room the caller has no relationship with: 404, not an empty list.
	f.rooms.owned = map[string]repositories.Room{"alpha": f.rooms.owned["alpha"]}
	other := newRoomDecisionFixture(t).withRows(pendingDecision()).mount()
	if rec := other.read("beta"); rec.Code != http.StatusNotFound {
		t.Fatalf("GET an unknown room = %d %s, want 404", rec.Code, rec.Body.String())
	}
}

// TestRoomDecisionAnswerRefusalsCarryTheContractsTokens walks the refusal matrix. Each case asserts
// the status, the token a client branches on, AND that the store was not written: a refusal that
// half-applied a click would be worse than one that failed loudly.
func TestRoomDecisionAnswerRefusalsCarryTheContractsTokens(t *testing.T) {
	answered := pendingDecision()
	answered.State = decisions.StateAnswered
	answered.Answers = map[string]string{"q1": "ship", "q2": "lead"}
	completedAt := roomDecisionTestNow.Add(time.Minute)
	answered.AnsweredAt = &completedAt

	cases := []struct {
		name    string
		slug    string
		id      string
		body    string
		status  int
		token   string
		rows    []roomrepo.RoomDecision
		noWrite bool
	}{
		{
			name: "an option outside the stored list", slug: "alpha", id: roomDecisionTestDecID,
			body: `{"question_id":"q1","option_id":"rocket"}`, status: http.StatusUnprocessableEntity,
			token: "unknown-option", rows: []roomrepo.RoomDecision{pendingDecision()}, noWrite: true,
		},
		{
			name: "a question the ask does not carry", slug: "alpha", id: roomDecisionTestDecID,
			body: `{"question_id":"q9","option_id":"ship"}`, status: http.StatusUnprocessableEntity,
			token: "unknown-question", rows: []roomrepo.RoomDecision{pendingDecision()}, noWrite: true,
		},
		{
			name: "a decision that is already answered", slug: "alpha", id: roomDecisionTestDecID,
			body: `{"question_id":"q1","option_id":"wait"}`, status: http.StatusConflict,
			token: "state-answered", rows: []roomrepo.RoomDecision{answered}, noWrite: true,
		},
		{
			name: "a decision id that is not in this room", slug: "alpha", id: "d1e0d3c2-3333-4333-8333-0000000000ff",
			body: `{"question_id":"q1","option_id":"ship"}`, status: http.StatusNotFound,
			token: "unknown-decision", rows: []roomrepo.RoomDecision{pendingDecision()},
		},
		{
			name: "an unknown body field", slug: "alpha", id: roomDecisionTestDecID,
			body: `{"question_id":"q1","option_id":"ship","answer":"ship"}`, status: http.StatusBadRequest,
			token: "unknown field", rows: []roomrepo.RoomDecision{pendingDecision()}, noWrite: true,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			f := newRoomDecisionFixture(t).withRows(tc.rows...).mount()
			rec := f.answer(tc.slug, tc.id, tc.body)
			if rec.Code != tc.status {
				t.Fatalf("status = %d, want %d: %s", rec.Code, tc.status, rec.Body.String())
			}
			if !strings.Contains(rec.Body.String(), tc.token) {
				t.Errorf("body = %s, want it to carry %q", rec.Body.String(), tc.token)
			}
			if tc.noWrite && f.store.recordCalls != 0 {
				t.Errorf("the refusal wrote %d time(s), want none", f.store.recordCalls)
			}
			if tc.noWrite {
				if stored := f.store.rows[roomDecisionTestDecID]; string(stored.State) != string(tc.rows[0].State) ||
					len(stored.Answers) != len(tc.rows[0].Answers) {
					t.Errorf("the stored row changed: %+v", stored)
				}
			}
		})
	}
}

// TestRoomDecisionAnswerIsOneClickPerCall walks a full ask: a click on the first question, the same
// click again (the retry the contract's idempotency clause is about), the click that completes the
// ask, a replay of that completing click, and finally a change that is refused because the ask is
// answered. The store is inspected throughout, because "inserts nothing" is a claim about writes.
func TestRoomDecisionAnswerIsOneClickPerCall(t *testing.T) {
	f := newRoomDecisionFixture(t).withRows(pendingDecision()).mount()

	rec := f.answer("alpha", roomDecisionTestDecID, `{"question_id":"q1","option_id":"ship","idempotency_key":"k1"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("first click = %d %s", rec.Code, rec.Body.String())
	}
	var first map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &first); err != nil {
		t.Fatal(err)
	}
	if len(first) != 3 || first["state"] != "pending" || first["complete"] != false {
		t.Fatalf("first click answered %v, want {state, answers, complete} with complete false", first)
	}
	if answers, _ := first["answers"].(map[string]any); answers["q1"] != "ship" {
		t.Fatalf("answers = %v, want q1 recorded", first["answers"])
	}
	if f.store.recordCalls != 1 {
		t.Fatalf("writes after the first click = %d, want 1", f.store.recordCalls)
	}

	// The same click again: the first answer comes back and nothing is written.
	rec = f.answer("alpha", roomDecisionTestDecID, `{"question_id":"q1","option_id":"ship","idempotency_key":"k1"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("replayed click = %d %s, want the stored answer rather than a refusal", rec.Code, rec.Body.String())
	}
	if f.store.recordCalls != 1 {
		t.Errorf("the replay wrote (%d writes), want none", f.store.recordCalls)
	}

	// The click that completes the ask: state answered, complete true, and answered_at is the clock.
	rec = f.answer("alpha", roomDecisionTestDecID, `{"question_id":"q2","option_id":"lead"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("completing click = %d %s", rec.Code, rec.Body.String())
	}
	var completed map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &completed); err != nil {
		t.Fatal(err)
	}
	if completed["state"] != "answered" || completed["complete"] != true {
		t.Fatalf("completing click answered %v, want answered/complete", completed)
	}
	if at := f.store.rows[roomDecisionTestDecID].AnsweredAt; at == nil || !at.Equal(roomDecisionTestNow) {
		t.Errorf("answered_at = %v, want the route's clock %v", at, roomDecisionTestNow)
	}

	// A replay of the completing click arrives AFTER the row moved to answered. It must answer with
	// the stored answer rather than `state-answered`: the click DID land, and a client retrying it
	// after a timeout is asking "did my click count?" - the answer is yes.
	rec = f.answer("alpha", roomDecisionTestDecID, `{"question_id":"q2","option_id":"lead"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("replay of the completing click = %d %s, want 200 with the first answer", rec.Code, rec.Body.String())
	}
	var replayed map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &replayed); err != nil {
		t.Fatal(err)
	}
	if replayed["state"] != "answered" || replayed["complete"] != true {
		t.Fatalf("the replay answered %v, want the stored answered state", replayed)
	}
	if f.store.lastRecorded != decisions.StateAnswered || f.store.recordCalls != 2 {
		t.Errorf("writes = %d (last state %q), want 2 writes and the replay writing nothing",
			f.store.recordCalls, f.store.lastRecorded)
	}

	// Changing a choice once the ask is answered is refused: the last accepted click is the one that
	// completed it, and the cloud never moves a row past answered on its own.
	rec = f.answer("alpha", roomDecisionTestDecID, `{"question_id":"q1","option_id":"wait"}`)
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), "state-answered") {
		t.Fatalf("changing an answered ask = %d %s, want 409 state-answered", rec.Code, rec.Body.String())
	}
}

// TestRoomDecisionAnswerIsOwnerOnly pins who may answer: not a viewer of a shared room (403
// not-the-asked-human - the ask is addressed to the room's human, and the owner answers for them),
// not an unknown room (404), and not an unauthenticated caller (the shared 403).
func TestRoomDecisionAnswerIsOwnerOnly(t *testing.T) {
	f := newRoomDecisionFixture(t).withRows(pendingDecision()).mount()
	body := `{"question_id":"q1","option_id":"ship"}`

	// The room is visible to the caller but owned by another tenant, so it is answerable by neither.
	f.rooms.owned["shared"] = f.rooms.visible["shared"]
	rec := f.answer("shared", roomDecisionTestDecID, body)
	if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "not-the-asked-human") {
		t.Fatalf("answering through a shared room = %d %s, want 403 not-the-asked-human", rec.Code, rec.Body.String())
	}
	if f.store.recordCalls != 0 {
		t.Errorf("the refused answer wrote %d time(s)", f.store.recordCalls)
	}

	if rec := f.answer("beta", roomDecisionTestDecID, body); rec.Code != http.StatusNotFound {
		t.Fatalf("answering in an unknown room = %d %s, want 404", rec.Code, rec.Body.String())
	}

	// No bearer at all: the shared auth failure, before any room or decision logic runs.
	rec = f.do(http.MethodPost, "/api/v2/openrig/rooms/alpha/decisions/"+roomDecisionTestDecID+"/answer", "", body)
	if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "Not authenticated") {
		t.Fatalf("unauthenticated answer = %d %s, want 403 Not authenticated", rec.Code, rec.Body.String())
	}
	if rec := f.do(http.MethodGet, "/api/v2/openrig/rooms/alpha/decisions", "", ""); rec.Code != http.StatusForbidden {
		t.Fatalf("unauthenticated read = %d, want 403", rec.Code)
	}
}
