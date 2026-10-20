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
	"net/url"
	"sort"
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
	pullCalls    int
	ackCalls     int
	stateCalls   int
	lastAnswer   map[string]string
	lastRecorded decisions.State
	// roomSlugs is what the rooms of these rows are called, the SLUG the pull hands out beside each
	// decision. A room it does not name falls back to the row's room id.
	roomSlugs map[string]string
}

func newFakeRoomDecisionStore(rows ...roomrepo.RoomDecision) *fakeRoomDecisionStore {
	store := &fakeRoomDecisionStore{rows: map[string]roomrepo.RoomDecision{}}
	for _, row := range rows {
		store.rows[row.ID] = row
	}
	return store
}

func (f *fakeRoomDecisionStore) Create(_ context.Context, decision roomrepo.RoomDecision) (*roomrepo.RoomDecision, bool, error) {
	for _, existing := range f.rows {
		if existing.UserID == decision.UserID && existing.IdempotencyKey == decision.IdempotencyKey {
			copied := existing
			return &copied, false, nil
		}
	}
	if decision.ID == "" {
		decision.ID = fmt.Sprintf("rd-%04d", len(f.rows)+1)
	}
	f.rows[decision.ID] = decision
	stored := decision
	return &stored, true, nil
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

func (f *fakeRoomDecisionStore) GetByID(_ context.Context, userID, id string) (*roomrepo.RoomDecision, error) {
	row, ok := f.rows[id]
	if !ok || row.UserID != userID {
		return nil, nil
	}
	copied := row
	return &copied, nil
}

// ListAnswers is the pull over the map: the tenant's answered, UNACKED rows, oldest first, after the
// cursor, each carrying the slug its room is known by here. The order, the cursor rule and the acked
// filter are the store's own - (answered_at, id) and acked_at IS NULL - so a route case that resumes
// from a cursor exercises the rule the SQL's comparison applies.
func (f *fakeRoomDecisionStore) ListAnswers(_ context.Context, userID, room string, after *roomrepo.AnswerCursor, limit int) ([]roomrepo.AnswerDelivery, error) {
	f.pullCalls++
	out := []roomrepo.AnswerDelivery{}
	for _, row := range f.rows {
		if row.UserID != userID || row.RoomName != room ||
			row.State != decisions.StateAnswered || row.AnsweredAt == nil || row.AckedAt != nil {
			continue
		}
		if !pullAfterCursor(row, after) {
			continue
		}
		slug := f.roomSlugs[row.RoomID]
		if slug == "" {
			slug = row.RoomID
		}
		out = append(out, roomrepo.AnswerDelivery{RoomDecision: row, RoomSlug: slug})
	}
	sort.Slice(out, func(i, j int) bool {
		left, right := *out[i].AnsweredAt, *out[j].AnsweredAt
		if !left.Equal(right) {
			return left.Before(right)
		}
		return out[i].ID < out[j].ID
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

// pullAfterCursor reports whether a row sorts after the cursor's position.
func pullAfterCursor(row roomrepo.RoomDecision, after *roomrepo.AnswerCursor) bool {
	if after == nil {
		return true
	}
	at := row.AnsweredAt.UTC()
	if at.Equal(after.AnsweredAt) {
		return row.ID > after.ID
	}
	return at.After(after.AnsweredAt)
}

// Acknowledge records a delivery the way the guarded UPDATE does: only a row still `answered` and
// unacked moves, BOTH outcomes set acked_at, and `applied` also closes the row as resolved. An id that
// is not there at all answers nil with false, which is the conflict the route reports.
func (f *fakeRoomDecisionStore) Acknowledge(_ context.Context, userID, id string, applied bool, at time.Time) (*roomrepo.RoomDecision, bool, error) {
	f.ackCalls++
	row, ok := f.rows[id]
	if !ok || row.UserID != userID {
		return nil, false, nil
	}
	acked := false
	if row.State == decisions.StateAnswered && row.AckedAt == nil {
		utc := at.UTC()
		row.AckedAt = &utc
		if applied {
			row.State, row.ResolvedAt = decisions.StateResolved, &utc
		}
		f.rows[id] = row
		acked = true
	}
	copied := row
	return &copied, acked, nil
}

// SetState writes the daemon's verdict, guarded on the row being open exactly as the UPDATE is.
func (f *fakeRoomDecisionStore) SetState(_ context.Context, userID, id string, state decisions.State, at time.Time) (*roomrepo.RoomDecision, error) {
	f.stateCalls++
	row, ok := f.rows[id]
	if !ok || row.UserID != userID {
		return nil, nil
	}
	if row.State == decisions.StatePending || row.State == decisions.StateAnswered {
		row.State = state
		if state == decisions.StateResolved {
			utc := at.UTC()
			row.ResolvedAt = &utc
		}
		f.rows[id] = row
	}
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
	return f.do(http.MethodPost, "/api/v2/rooms/"+slug+"/decisions/"+id+"/answer", "user-jwt", body)
}

func (f *roomDecisionFixture) read(slug string) *httptest.ResponseRecorder {
	f.t.Helper()
	return f.do(http.MethodGet, "/api/v2/rooms/"+slug+"/decisions", "user-jwt", "")
}

// pendingDecision is one mirrored ask of user A in room alpha.
func pendingDecision() roomrepo.RoomDecision {
	return roomrepo.RoomDecision{
		ID:             roomDecisionTestDecID,
		UserID:         roomDecisionTestUserA,
		RoomID:         roomDecisionTestRoomID,
		RoomName:       "4genthub-min",
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
			// The envelope is the contract's one for a refusal here: the plain detail body. The
			// success:false envelope belongs to the secret-in-field refusal alone, and this is the
			// case that keeps a 422 from being read as "422 means success:false".
			if strings.Contains(rec.Body.String(), `"success"`) {
				t.Errorf("body = %s, want the detail envelope and no success key", rec.Body.String())
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
	rec = f.do(http.MethodPost, "/api/v2/rooms/alpha/decisions/"+roomDecisionTestDecID+"/answer", "", body)
	if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "Not authenticated") {
		t.Fatalf("unauthenticated answer = %d %s, want 403 Not authenticated", rec.Code, rec.Body.String())
	}
	if rec := f.do(http.MethodGet, "/api/v2/rooms/alpha/decisions", "", ""); rec.Code != http.StatusForbidden {
		t.Fatalf("unauthenticated read = %d, want 403", rec.Code)
	}
}

// ---------------------------------------------------------------------------------------------
// The crossing: the four routes a room's daemon drives.
// ---------------------------------------------------------------------------------------------

// answeredDecision is one ask of user A in room alpha that the human has answered: the state the pull
// hands out, with answered_at set the way the answer contract sets it.
func answeredDecision(id string, answeredAt time.Time) roomrepo.RoomDecision {
	row := pendingDecision()
	row.ID = id
	row.State = decisions.StateAnswered
	row.Answers = map[string]string{"q1": "ship", "q2": "lead"}
	at := answeredAt.UTC()
	row.AnsweredAt = &at
	return row
}

// ingestBody is one valid ask for one room, spelled with the wire's own field names.
func ingestBody(room string) string {
	return `{"room":"` + room + `","qitem_id":"qitem-20261012190405-abcdef0123456789",` +
		`"author_seat_key":"go-dev","destination":"human-operator@kernel",` +
		`"summary":"ship the cloud half first?","detail":"the panel waits on it",` +
		`"questions":[{"id":"q1","question":"Ship it?","options":[{"id":"ship","label":"Ship it"},{"id":"wait","label":"Wait"}]}],` +
		`"idempotency_key":"agenthub:decision:qitem-20261012190405-abcdef0123456789"}`
}

// TestRoomDecisionIngestCreatesOnceAndNamesItsRoom is route 1's contract: the ask lands in the room
// the body names, a redrive collapses onto the row the first attempt made and SAYS SO with
// created:false, and the response carries the stored row.
func TestRoomDecisionIngestCreatesOnceAndNamesItsRoom(t *testing.T) {
	f := newRoomDecisionFixture(t).withRows().mount()

	rec := f.do(http.MethodPost, "/api/v2/decisions", "user-jwt", ingestBody("alpha"))
	if rec.Code != http.StatusOK {
		t.Fatalf("ingest = %d %s, want 200", rec.Code, rec.Body.String())
	}
	var first map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &first); err != nil {
		t.Fatal(err)
	}
	if first["success"] != true || first["created"] != true {
		t.Fatalf("ingest answered %v, want success with created:true", first)
	}
	decision, _ := first["decision"].(map[string]any)
	if decision == nil || decision["state"] != "pending" || decision["qitem_id"] != "qitem-20261012190405-abcdef0123456789" {
		t.Fatalf("decision = %v, want the stored pending ask", decision)
	}
	if len(f.store.rows) != 1 {
		t.Fatalf("rows = %d, want one mirrored ask", len(f.store.rows))
	}

	// The redrive: the same ask's idempotency_key again is the row the first attempt made, and the
	// response says which call stored it - that is how the daemon learns its earlier attempt landed.
	rec = f.do(http.MethodPost, "/api/v2/decisions", "user-jwt", ingestBody("alpha"))
	if rec.Code != http.StatusOK {
		t.Fatalf("redrive = %d %s, want 200", rec.Code, rec.Body.String())
	}
	var again map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &again); err != nil {
		t.Fatal(err)
	}
	if again["created"] != false {
		t.Errorf("redrive answered created=%v, want false: an earlier attempt stored it", again["created"])
	}
	if len(f.store.rows) != 1 {
		t.Errorf("the redrive made a second row: %d rows", len(f.store.rows))
	}

	// The retired key is refused by the strict decoder rather than ignored: there is one name for the
	// unit on this wire, and a body that spells the old one hears which field is unknown.
	retired := strings.Replace(ingestBody("alpha"), `"room":"alpha"`, `"rig":"alpha"`, 1)
	if rec := f.do(http.MethodPost, "/api/v2/decisions", "user-jwt", retired); rec.Code != http.StatusBadRequest ||
		!strings.Contains(rec.Body.String(), `unknown field \"rig\"`) {
		t.Fatalf("ingest carrying the retired key = %d %s, want 400 naming it", rec.Code, rec.Body.String())
	}

	// A slug that resolves to nothing is the pinned 404 rather than a silent wrong room.
	unknown := f.do(http.MethodPost, "/api/v2/decisions", "user-jwt", ingestBody("not-a-room"))
	if unknown.Code != http.StatusNotFound || !strings.Contains(unknown.Body.String(), `room \"not-a-room\" not found`) {
		t.Fatalf("ingest into an unknown room = %d %s, want 404 naming the slug", unknown.Code, unknown.Body.String())
	}

	// No bearer: the shared auth failure, before anything is read or written.
	if rec := f.do(http.MethodPost, "/api/v2/decisions", "", ingestBody("alpha")); rec.Code != http.StatusForbidden {
		t.Fatalf("unauthenticated ingest = %d, want 403", rec.Code)
	}
}

// fiveQuestionBody is an ask whose question list is over the daemon's own limit: the service enforces
// those limits at the door rather than storing an ask nobody can answer.
func fiveQuestionBody() string {
	questions := make([]string, 0, 5)
	for i := range 5 {
		questions = append(questions, fmt.Sprintf(`{"id":"q%d","question":"Ship it?","options":[{"id":"ship","label":"Ship it"},{"id":"wait","label":"Wait"}]}`, i))
	}
	return `{"room":"alpha","qitem_id":"qitem-1","author_seat_key":"go-dev","destination":"human@kernel",` +
		`"summary":"s","detail":"d","questions":[` + strings.Join(questions, ",") + `],` +
		`"idempotency_key":"agenthub:decision:qitem-1"}`
}

// TestRoomDecisionIngestRefusalsAreTheContracts pins the door: a misspelled field, a list over the
// daemon's limit and a credential each get the status and envelope the contract names, and NONE of
// them stores a row.
func TestRoomDecisionIngestRefusalsAreTheContracts(t *testing.T) {
	cases := []struct {
		name       string
		body       string
		status     int
		contains   string
		detail     string
		envelopeNo bool
	}{
		{
			name:     "a misspelled field",
			body:     strings.Replace(ingestBody("alpha"), `"qitem_id"`, `"qitem_idd"`, 1),
			status:   http.StatusBadRequest,
			contains: "qitem_idd",
		},
		{
			name:     "a fifth question",
			body:     fiveQuestionBody(),
			status:   http.StatusBadRequest,
			contains: "Ask 1 to",
		},
		{
			name: "a key that does not derive from the qitem",
			body: strings.Replace(ingestBody("alpha"),
				`"agenthub:decision:qitem-20261012190405-abcdef0123456789"`, `"agenthub:decision:another-item"`, 1),
			status: http.StatusBadRequest,
			detail: "idempotency_key must be agenthub:decision:<qitem_id>",
		},
		{
			name: "a credential in the detail",
			body: strings.Replace(ingestBody("alpha"), "the panel waits on it",
				"use AKIAIOSFODNN7EXAMPLE to read the bucket", 1),
			status:     http.StatusUnprocessableEntity,
			contains:   "secret detected in field detail",
			envelopeNo: true,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			f := newRoomDecisionFixture(t).withRows().mount()
			rec := f.do(http.MethodPost, "/api/v2/decisions", "user-jwt", tc.body)
			if rec.Code != tc.status || !strings.Contains(rec.Body.String(), tc.contains) {
				t.Fatalf("ingest = %d %s, want %d containing %q", rec.Code, rec.Body.String(), tc.status, tc.contains)
			}
			if len(f.store.rows) != 0 {
				t.Errorf("a refused ask was stored (%d row(s))", len(f.store.rows))
			}
			// A case that names an exact detail is compared AFTER DECODING, because the wire body
			// escapes < and > and this contract's message is written with them: a raw substring match
			// would pin encoding/json's escaping rather than the message a client reads.
			if tc.detail != "" {
				var decoded struct {
					Detail string `json:"detail"`
				}
				if err := json.Unmarshal(rec.Body.Bytes(), &decoded); err != nil {
					t.Fatalf("decode %s: %v", rec.Body.String(), err)
				}
				if decoded.Detail != tc.detail {
					t.Errorf("detail = %q, want %q", decoded.Detail, tc.detail)
				}
			}
			// The secret is the ONE refusal with the success:false envelope; every other contract
			// refusal is the plain detail body. Both halves are asserted: the envelope the case is
			// owed, and the absence of the other one.
			if sent := strings.Contains(rec.Body.String(), `"success":false`); sent != tc.envelopeNo {
				t.Errorf("success:false envelope = %v, want %v (%s)", sent, tc.envelopeNo, rec.Body.String())
			}
			if tc.envelopeNo && strings.Contains(rec.Body.String(), `"detail":`) {
				t.Errorf("body = %s, want the secret refusal to carry no detail key", rec.Body.String())
			}
		})
	}
}

// TestRoomDecisionPullPagesByCursorAndNeverRepeatsAnAckedAnswer is route 2: the page is the tenant's
// answered, un-acked rows with the room's SLUG beside each, the cursor is a keyset the daemon echoes
// back, and an acked row never comes out again.
func TestRoomDecisionPullPagesByCursorAndNeverRepeatsAnAckedAnswer(t *testing.T) {
	first := answeredDecision("d1e0d3c2-3333-4333-8333-000000000001", roomDecisionTestNow)
	second := answeredDecision("d1e0d3c2-3333-4333-8333-000000000002", roomDecisionTestNow.Add(time.Minute))
	f := newRoomDecisionFixture(t).withRows(first, second).mount()
	f.store.roomSlugs = map[string]string{roomDecisionTestRoomID: "alpha"}

	rec := f.do(http.MethodGet, "/api/v2/decisions/answers?room=4genthub-min&limit=1", "user-jwt", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("pull = %d %s, want 200", rec.Code, rec.Body.String())
	}
	page := decodeRoomDecisionPage(t, rec)
	rows, _ := page["answers"].([]any)
	if len(rows) != 1 {
		t.Fatalf("page = %v, want one answer for limit=1", page["answers"])
	}
	row, _ := rows[0].(map[string]any)
	if len(row) != 6 {
		t.Fatalf("answer keys = %v, want exactly the contract's six", row)
	}
	if row["decision_id"] != first.ID || row["room"] != "alpha" {
		t.Errorf("answer = %v, want the row and the room's SLUG rather than its id", row)
	}
	if row["answered_at"] != roomDecisionTestNow.Format(time.RFC3339Nano) {
		t.Errorf("answered_at = %v, want the RFC3339Nano instant", row["answered_at"])
	}
	// The cursor is the shipped keyset string, not an encoding of it: the daemon echoes what it got.
	if want := first.AnsweredAt.UTC().Format(time.RFC3339Nano) + "|" + first.ID; page["cursor"] != want {
		t.Fatalf("cursor = %v, want %q", page["cursor"], want)
	}
	cursor, _ := page["cursor"].(string)

	// Resuming hands over what follows, and nothing before it. The cursor travels as a URL query
	// value, which is how the daemon sends it back.
	rec = f.do(http.MethodGet, "/api/v2/decisions/answers?room=4genthub-min&after="+url.QueryEscape(cursor), "user-jwt", "")
	resumed := decodeRoomDecisionPage(t, rec)
	rows, _ = resumed["answers"].([]any)
	if len(rows) != 1 {
		t.Fatalf("resumed page = %v, want only the second answer", resumed["answers"])
	}
	if row, _ := rows[0].(map[string]any); row["decision_id"] != second.ID {
		t.Fatalf("resumed page = %v, want %s", rows[0], second.ID)
	}

	// The ack IS the delivery record: once it lands, the pull does not hand that answer out again.
	ack := f.do(http.MethodPost, "/api/v2/decisions/"+first.ID+"/ack", "user-jwt",
		`{"machine_id":"host-1","outcome":"applied"}`)
	if ack.Code != http.StatusOK {
		t.Fatalf("ack = %d %s, want 200", ack.Code, ack.Body.String())
	}
	fresh := decodeRoomDecisionPage(t, f.do(http.MethodGet, "/api/v2/decisions/answers?room=4genthub-min", "user-jwt", ""))
	rows, _ = fresh["answers"].([]any)
	if len(rows) != 1 {
		t.Fatalf("page after the ack = %v, want the one un-acked answer", fresh["answers"])
	}
	if row, _ := rows[0].(map[string]any); row["decision_id"] != second.ID {
		t.Fatalf("page after the ack = %v, want the second answer only", rows[0])
	}

	// A cursor this endpoint did not mint is the pinned sentence, and never a silent first page.
	bad := f.do(http.MethodGet, "/api/v2/decisions/answers?room=4genthub-min&after=not-a-cursor", "user-jwt", "")
	if bad.Code != http.StatusBadRequest || !strings.Contains(bad.Body.String(), `after \"not-a-cursor\" must be a cursor this endpoint returned`) {
		t.Fatalf("malformed cursor = %d %s, want the pinned 400", bad.Code, bad.Body.String())
	}
	// The pull names no machine and needs none: the tenant is the filter, and the page it returns is
	// whatever that tenant still owes an ack for.
	if rec := f.do(http.MethodGet, "/api/v2/decisions/answers?room=4genthub-min", "user-jwt", ""); rec.Code != http.StatusOK {
		t.Fatalf("pull naming no machine = %d %s, want 200", rec.Code, rec.Body.String())
	}
}

// TestRoomDecisionAckResolvesOnlyOnAppliedAndOnlyOnce is route 3: `applied` is the only input that
// resolves, a drop is acked all the same and never retried, and a repeat - or an id that was never
// here - hears that the STATE is what was wrong rather than that the id looks mistyped.
func TestRoomDecisionAckResolvesOnlyOnAppliedAndOnlyOnce(t *testing.T) {
	applied := answeredDecision("d1e0d3c2-3333-4333-8333-000000000001", roomDecisionTestNow)
	dropped := answeredDecision("d1e0d3c2-3333-4333-8333-000000000002", roomDecisionTestNow)
	untouched := answeredDecision("d1e0d3c2-3333-4333-8333-000000000003", roomDecisionTestNow)
	f := newRoomDecisionFixture(t).withRows(applied, dropped, untouched).mount()

	rec := f.do(http.MethodPost, "/api/v2/decisions/"+applied.ID+"/ack", "user-jwt",
		`{"machine_id":"host-1","outcome":"applied"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"delivered":true`) {
		t.Fatalf("applied ack = %d %s, want 200 delivered:true", rec.Code, rec.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["state"] != "resolved" || body["success"] != true {
		t.Errorf("applied ack answered %v, want the resolved state", body)
	}
	if stored := f.store.rows[applied.ID]; stored.State != decisions.StateResolved || stored.AckedAt == nil {
		t.Errorf("stored = %+v, want resolved and acked", stored)
	}

	// A drop is the same delivery record and NOT a resolution: the row keeps its state and is never
	// handed out again.
	rec = f.do(http.MethodPost, "/api/v2/decisions/"+dropped.ID+"/ack", "user-jwt",
		`{"machine_id":"host-1","outcome":"dropped","reason":"state-done"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("dropped ack = %d %s, want 200", rec.Code, rec.Body.String())
	}
	if stored := f.store.rows[dropped.ID]; stored.State != decisions.StateAnswered || stored.AckedAt == nil {
		t.Errorf("dropped row = %+v, want answered and acked", stored)
	}

	// A second ack, and an id that is not there: one conflict, because neither redelivers.
	for _, tc := range []struct{ name, id, body string }{
		{"a second applied ack", applied.ID, `{"machine_id":"host-1","outcome":"applied"}`},
		{"a second dropped ack", dropped.ID, `{"machine_id":"host-1","outcome":"dropped","reason":"state-done"}`},
		{"an id that was never here", "d1e0d3c2-3333-4333-8333-00000000000f", `{"machine_id":"host-1","outcome":"applied"}`},
	} {
		if rec := f.do(http.MethodPost, "/api/v2/decisions/"+tc.id+"/ack", "user-jwt", tc.body); rec.Code != http.StatusConflict {
			t.Errorf("%s = %d %s, want 409", tc.name, rec.Code, rec.Body.String())
		}
	}

	// The malformed reports: an outcome outside the pair, and a drop with no reason or one outside the
	// closed list. A misspelled body field is refused rather than ignored.
	for _, tc := range []struct{ name, body string }{
		{"an outcome that is neither", `{"machine_id":"host-1","outcome":"maybe"}`},
		{"a drop with no reason", `{"machine_id":"host-1","outcome":"dropped"}`},
		{"a drop with a reason nobody defined", `{"machine_id":"host-1","outcome":"dropped","reason":"because"}`},
		{"a misspelled field", `{"machine_id":"host-1","outcome":"applied","outcom":"typo"}`},
	} {
		if rec := f.do(http.MethodPost, "/api/v2/decisions/"+untouched.ID+"/ack", "user-jwt", tc.body); rec.Code != http.StatusBadRequest {
			t.Errorf("%s = %d %s, want 400", tc.name, rec.Code, rec.Body.String())
		}
	}
	if stored := f.store.rows[untouched.ID]; stored.AckedAt != nil || stored.State != decisions.StateAnswered {
		t.Errorf("a refused ack wrote: %+v", stored)
	}
}

// TestRoomDecisionStatePushNamesTheStateItRefused is route 4: a transition the daemon learned with no
// answer in hand lands, and a push onto a decision that is already over is refused with
// `state-<state>` - naming the state the row is IN rather than the one the caller asked for.
func TestRoomDecisionStatePushNamesTheStateItRefused(t *testing.T) {
	row := answeredDecision("d1e0d3c2-3333-4333-8333-000000000001", roomDecisionTestNow)
	other := answeredDecision("d1e0d3c2-3333-4333-8333-000000000002", roomDecisionTestNow)
	f := newRoomDecisionFixture(t).withRows(row, other).mount()

	rec := f.do(http.MethodPost, "/api/v2/decisions/"+row.ID+"/state", "user-jwt",
		`{"machine_id":"host-1","state":"superseded","reason":"slack-first"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"state":"superseded"`) {
		t.Fatalf("state push = %d %s, want 200 superseded", rec.Code, rec.Body.String())
	}
	if stored := f.store.rows[row.ID]; stored.State != decisions.StateSuperseded || stored.ResolvedAt != nil {
		t.Errorf("stored = %+v, want superseded with no resolved_at", stored)
	}

	// The same decision again: the row is over, so the push is refused with the state it is in.
	rec = f.do(http.MethodPost, "/api/v2/decisions/"+row.ID+"/state", "user-jwt",
		`{"machine_id":"host-1","state":"resolved"}`)
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), `"detail":"state-superseded"`) {
		t.Fatalf("push onto a superseded row = %d %s, want 409 state-superseded", rec.Code, rec.Body.String())
	}

	// A state the daemon may not write is a malformed push rather than a transition it got wrong, and
	// it writes nothing.
	rec = f.do(http.MethodPost, "/api/v2/decisions/"+other.ID+"/state", "user-jwt",
		`{"machine_id":"host-1","state":"pending"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("push of a cloud-only state = %d %s, want 400", rec.Code, rec.Body.String())
	}
	if stored := f.store.rows[other.ID]; stored.State != decisions.StateAnswered {
		t.Errorf("the refused push moved the row: %+v", stored)
	}

	// An id that is not there at all is the unknown decision.
	rec = f.do(http.MethodPost, "/api/v2/decisions/d1e0d3c2-3333-4333-8333-00000000000f/state", "user-jwt",
		`{"machine_id":"host-1","state":"resolved"}`)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("push onto an unknown id = %d %s, want 404", rec.Code, rec.Body.String())
	}
}

// decodeRoomDecisionPage reads one pull response.
func decodeRoomDecisionPage(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	if rec.Code != http.StatusOK {
		t.Fatalf("pull = %d %s, want 200", rec.Code, rec.Body.String())
	}
	var page map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &page); err != nil {
		t.Fatal(err)
	}
	if page["success"] != true {
		t.Fatalf("page = %v, want the success envelope", page)
	}
	return page
}
