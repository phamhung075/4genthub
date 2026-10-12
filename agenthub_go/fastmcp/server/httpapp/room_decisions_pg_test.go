package httpapp

// The three acceptance cases of S1 lane 1, DB-BACKED AT THE ROUTE: real rows in the real tables,
// driven through app.Handler() so the path under test is the production one - the auth layer, the
// router, the mounted routes, the service, the tenant-scoped repository, and the DDL's own
// constraints.
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and the skip says so
// loudly. A SKIP IS NOT A PASS: this file is the acceptance, so a skip here means the acceptance did
// not run. To run it:
//
//	cd agenthub_go && bash tools/testpg/start.sh          # prints the URL when the cluster is up
//	AGENTHUB_TEST_PG_URL=<that url> SEAT_TEST_DATABASE_URL=<that url> \
//	  go test -count=1 ./fastmcp/server/httpapp/ -run RoomDecision -v
//
// WHY A REAL DATABASE, when the fake-store cases beside this file cover the refusal matrix: three of
// the acceptance claims are claims about ROWS and cannot be made anywhere else. "No row written" is
// about the stored answers and state and about the row count. "One row" is about the UNIQUE
// constraint on idempotency_key plus an UPDATE that inserts nothing. "No other room's or tenant's
// decision" is about the WHERE clause of a real query. A fake would write these comments' hypothesis
// back to its author.

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	roomDecisionPgRoomAlphaID  = "a1e0d3c2-1111-4111-8111-00000000000a"
	roomDecisionPgRoomAlpha2ID = "a1e0d3c2-1111-4111-8111-00000000000c"
	roomDecisionPgRoomBetaID   = "a1e0d3c2-1111-4111-8111-00000000000b"
	roomDecisionPgDecAlphaID   = "d1e0d3c2-3333-4333-8333-00000000000a"
	roomDecisionPgDecBetaID    = "d1e0d3c2-3333-4333-8333-00000000000b"
	roomDecisionPgSubjectA     = "c1e0d3c2-2222-4222-8222-00000000000a"
	roomDecisionPgSubjectB     = "c1e0d3c2-2222-4222-8222-00000000000b"
)

// The ask both tenants mirror: TWO questions, so the first click leaves the row pending and the
// completing click is its own step.
const roomDecisionPgQuestions = `[{"id":"q1","question":"Ship the cloud half first?","options":[{"id":"ship","label":"Ship it"},{"id":"wait","label":"Wait"}]},{"id":"q2","question":"Who reviews?","options":[{"id":"lead","label":"The lead"},{"id":"me","label":"Me"}]}]`

type roomDecisionPgEnv struct {
	app           *App
	sm            *database.SessionManager
	tokenA, userA string
	tokenB, userB string
}

// newRoomDecisionPgEnv brings up a throwaway database with the full schema, the production app over
// it, and one credential per tenant. The credential is minted for a UUID-shaped subject, so the id
// the routes resolve and the id the rows are scoped to are the same string.
func newRoomDecisionPgEnv(t *testing.T) *roomDecisionPgEnv {
	t.Helper()
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("ENV", "dev")
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)
	app, err := NewApp(context.Background(), sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	tokenA, userA := evidenceUser(t, roomDecisionPgSubjectA)
	tokenB, userB := evidenceUser(t, roomDecisionPgSubjectB)
	return &roomDecisionPgEnv{app: app, sm: sm, tokenA: tokenA, userA: userA, tokenB: tokenB, userB: userB}
}

// seed mirrors one ask into one room: the row S2's ask route will create, written straight into the
// table because that route does not exist yet. qitemID is the routed item's own id, and two rows of
// one owner may not share it: uq_room_decisions_user_qitem enforces that, so a fixture for a second
// room of the same owner must carry a second qitem id.
func (e *roomDecisionPgEnv) seed(t *testing.T, roomID, decisionID, userID, slug, qitemID, idempotencyKey string) {
	t.Helper()
	ledgerExec(t, e.sm, `INSERT INTO rooms (id, user_id, slug, name, created_at, updated_at)
		VALUES ($1::uuid, $2, $3, $4, now(), now())`, roomID, userID, slug, slug)
	ledgerExec(t, e.sm, `INSERT INTO room_decisions
		(id, user_id, room_id, rig_name, qitem_id, author_seat_key, destination, summary, detail,
		 questions, answers, state, idempotency_key, created_at)
		VALUES ($1::uuid, $2, $3::uuid, '4genthub-min', $6, 'go-dev', 'human-operator@kernel',
		 'ship the cloud half first?', 'the panel needs the answer', $4::jsonb, '{}'::jsonb, 'pending', $5, now())`,
		decisionID, userID, roomID, roomDecisionPgQuestions, idempotencyKey, qitemID)
}

// row reads one decision's state and answers straight from the table: the "no write" and "first
// answer" claims are claims about these two values.
func (e *roomDecisionPgEnv) row(t *testing.T, id string) (state string, answers string) {
	t.Helper()
	if err := e.sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "state", "answers"::text FROM "room_decisions" WHERE "id" = $1::uuid`, id).Scan(&state, &answers)
	}); err != nil {
		t.Fatalf("reading the decision row: %v", err)
	}
	return state, answers
}

// count is how many decision rows this tenant holds, which is how "one row" is proved.
func (e *roomDecisionPgEnv) count(t *testing.T, userID string) int {
	t.Helper()
	n := 0
	if err := e.sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM "room_decisions" WHERE "user_id" = $1`, userID).Scan(&n)
	}); err != nil {
		t.Fatalf("counting the tenant's decisions: %v", err)
	}
	return n
}

func (e *roomDecisionPgEnv) postAnswer(t *testing.T, token, slug, id, body string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost,
		"/api/v2/openrig/rooms/"+slug+"/decisions/"+id+"/answer", strings.NewReader(body))
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	e.app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

func (e *roomDecisionPgEnv) getDecisions(t *testing.T, token, slug string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/api/v2/openrig/rooms/"+slug+"/decisions", nil)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	rec := httptest.NewRecorder()
	e.app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// answerBody is the answer response, decoded with the contract's three keys.
type roomDecisionPgAnswer struct {
	State    string            `json:"state"`
	Answers  map[string]string `json:"answers"`
	Complete bool              `json:"complete"`
}

func decodeRoomDecisionAnswer(t *testing.T, body string) roomDecisionPgAnswer {
	t.Helper()
	var out roomDecisionPgAnswer
	if err := json.Unmarshal([]byte(body), &out); err != nil {
		t.Fatalf("decoding the answer response: %v (%s)", err, body)
	}
	return out
}

func decodeRoomDecisionRead(t *testing.T, body string) []map[string]any {
	t.Helper()
	var out struct {
		Decisions []map[string]any `json:"decisions"`
	}
	if err := json.Unmarshal([]byte(body), &out); err != nil {
		t.Fatalf("decoding the decisions read: %v (%s)", err, body)
	}
	return out.Decisions
}

// TestRoomDecisionPgUnknownOptionIs422AndWritesNothing is the acceptance's first case: the click's
// vocabulary is the STORED options, and a value outside them leaves the row exactly as it was.
func TestRoomDecisionPgUnknownOptionIs422AndWritesNothing(t *testing.T) {
	env := newRoomDecisionPgEnv(t)
	env.seed(t, roomDecisionPgRoomAlphaID, roomDecisionPgDecAlphaID, env.userA, "alpha", "qitem-pg-alpha", "agenthub:decision:qitem-pg-alpha")

	beforeState, beforeAnswers := env.row(t, roomDecisionPgDecAlphaID)

	code, body := env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID,
		`{"question_id":"q1","option_id":"rocket"}`)
	if code != http.StatusUnprocessableEntity {
		t.Fatalf("POST an unknown option = %d %s, want 422", code, body)
	}
	if !strings.Contains(body, "unknown-option") {
		t.Errorf("body = %s, want the contract's unknown-option token", body)
	}
	state, answers := env.row(t, roomDecisionPgDecAlphaID)
	if state != beforeState || answers != beforeAnswers {
		t.Fatalf("the refused click wrote: state %q -> %q, answers %s -> %s", beforeState, state, beforeAnswers, answers)
	}
	if got := env.count(t, env.userA); got != 1 {
		t.Fatalf("rows for the tenant = %d, want the one mirrored ask", got)
	}

	// A question the ask does not carry is the same kind of refusal, and writes nothing either.
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID,
		`{"question_id":"q9","option_id":"ship"}`)
	if code != http.StatusUnprocessableEntity || !strings.Contains(body, "unknown-question") {
		t.Fatalf("POST an unknown question = %d %s, want 422 unknown-question", code, body)
	}
	if state, answers := env.row(t, roomDecisionPgDecAlphaID); state != beforeState || answers != beforeAnswers {
		t.Fatalf("the second refused click wrote: state %q, answers %s", state, answers)
	}

	// The control: the SAME question with an option the ask does carry is accepted, so the refusals
	// above were about the values and not about a route that refuses everything.
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID,
		`{"question_id":"q1","option_id":"ship"}`)
	if code != http.StatusOK {
		t.Fatalf("POST a valid option = %d %s, want 200", code, body)
	}
	answer := decodeRoomDecisionAnswer(t, body)
	if answer.Answers["q1"] != "ship" || answer.State != "pending" || answer.Complete {
		t.Fatalf("valid click answered %+v, want q1=ship pending and not complete", answer)
	}
	if state, answers := env.row(t, roomDecisionPgDecAlphaID); state != "pending" || !strings.Contains(answers, `"q1": "ship"`) {
		t.Fatalf("stored row = %q %s, want the click recorded", state, answers)
	}
}

// TestRoomDecisionPgDuplicateKeyIsOneRowAndTheFirstAnswer is the acceptance's second case, told in
// the shape a retrying client produces: the same click twice, then the click that completes the ask
// and a replay of THAT click after the row has moved to answered - which must still answer with the
// first answer rather than a state refusal, because the click did land.
func TestRoomDecisionPgDuplicateKeyIsOneRowAndTheFirstAnswer(t *testing.T) {
	env := newRoomDecisionPgEnv(t)
	env.seed(t, roomDecisionPgRoomAlphaID, roomDecisionPgDecAlphaID, env.userA, "alpha", "qitem-pg-alpha", "agenthub:decision:qitem-pg-alpha")

	const click = `{"question_id":"q1","option_id":"ship","idempotency_key":"k-1"}`
	code, body := env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID, click)
	if code != http.StatusOK {
		t.Fatalf("first click = %d %s, want 200", code, body)
	}
	first := decodeRoomDecisionAnswer(t, body)
	if first.Answers["q1"] != "ship" {
		t.Fatalf("first click answered %+v, want q1=ship", first)
	}
	if got := env.count(t, env.userA); got != 1 {
		t.Fatalf("rows after the first click = %d, want 1", got)
	}

	// The same click, same key: the first answer comes back and no second row appears.
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID, click)
	if code != http.StatusOK {
		t.Fatalf("duplicate click = %d %s, want 200 with the first answer", code, body)
	}
	replay := decodeRoomDecisionAnswer(t, body)
	if replay.Answers["q1"] != "ship" || replay.State != "pending" || replay.Complete {
		t.Fatalf("duplicate click answered %+v, want the first answer unchanged", replay)
	}
	if got := env.count(t, env.userA); got != 1 {
		t.Fatalf("rows after the duplicate click = %d, want ONE (the UNIQUE key collapsed the redrive)", got)
	}

	// The click that completes the ask.
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID,
		`{"question_id":"q2","option_id":"lead","idempotency_key":"k-2"}`)
	if code != http.StatusOK {
		t.Fatalf("completing click = %d %s, want 200", code, body)
	}
	completed := decodeRoomDecisionAnswer(t, body)
	if completed.State != "answered" || !completed.Complete || completed.Answers["q2"] != "lead" {
		t.Fatalf("completing click answered %+v, want answered/complete with both answers", completed)
	}
	state, answers := env.row(t, roomDecisionPgDecAlphaID)
	if state != "answered" || !strings.Contains(answers, `"q2": "lead"`) {
		t.Fatalf("stored row = %q %s, want answered with both answers", state, answers)
	}

	// The replay of the COMPLETING click arrives after the row is `answered`. It answers with the
	// stored answer, not `state-answered`: a client retrying after a timeout is asking whether its
	// click counted, and it did.
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID,
		`{"question_id":"q2","option_id":"lead","idempotency_key":"k-2"}`)
	if code != http.StatusOK {
		t.Fatalf("replay of the completing click = %d %s, want 200 with the stored answer", code, body)
	}
	replayed := decodeRoomDecisionAnswer(t, body)
	if replayed.State != "answered" || !replayed.Complete || replayed.Answers["q2"] != "lead" {
		t.Fatalf("the replay answered %+v, want the stored answered state", replayed)
	}
	if got := env.count(t, env.userA); got != 1 {
		t.Fatalf("rows after every replay = %d, want 1", got)
	}

	// A click that would CHANGE an answer after the ask is answered is refused, and the stored
	// answers are untouched: the last accepted click is the one that completed the ask.
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecAlphaID,
		`{"question_id":"q1","option_id":"wait"}`)
	if code != http.StatusConflict || !strings.Contains(body, "state-answered") {
		t.Fatalf("changing an answered decision = %d %s, want 409 state-answered", code, body)
	}
	if state, answers := env.row(t, roomDecisionPgDecAlphaID); state != "answered" || strings.Contains(answers, `"wait"`) {
		t.Fatalf("stored row = %q %s, want the first answers kept", state, answers)
	}
}

// TestRoomDecisionPgReadNeverCrossesRoomOrTenant is the acceptance's third case at the route: two
// rooms of one tenant, one room of another, and every crossing that must not resolve.
func TestRoomDecisionPgReadNeverCrossesRoomOrTenant(t *testing.T) {
	env := newRoomDecisionPgEnv(t)
	env.seed(t, roomDecisionPgRoomAlphaID, roomDecisionPgDecAlphaID, env.userA, "alpha", "qitem-pg-alpha", "agenthub:decision:qitem-pg-alpha")
	env.seed(t, roomDecisionPgRoomAlpha2ID, "d1e0d3c2-3333-4333-8333-00000000000c", env.userA, "alpha-two", "qitem-pg-alpha-two", "agenthub:decision:qitem-pg-alpha-two")
	env.seed(t, roomDecisionPgRoomBetaID, roomDecisionPgDecBetaID, env.userB, "beta", "qitem-pg-beta", "agenthub:decision:qitem-pg-beta")

	// The caller's own room, read by the caller: exactly that room's decision.
	code, body := env.getDecisions(t, env.tokenA, "alpha")
	if code != http.StatusOK {
		t.Fatalf("GET alpha as A = %d %s", code, body)
	}
	rows := decodeRoomDecisionRead(t, body)
	if len(rows) != 1 || rows[0]["id"] != roomDecisionPgDecAlphaID {
		t.Fatalf("GET alpha as A = %v, want only alpha's decision", rows)
	}
	if rows[0]["state"] != "pending" || rows[0]["author_seat_key"] != "go-dev" {
		t.Errorf("row = %v, want the mirrored ask's own fields", rows[0])
	}

	// The SAME tenant's other room: the room scoping, not the tenant one.
	code, body = env.getDecisions(t, env.tokenA, "alpha-two")
	if code != http.StatusOK {
		t.Fatalf("GET alpha-two as A = %d %s", code, body)
	}
	other := decodeRoomDecisionRead(t, body)
	if len(other) != 1 || other[0]["id"] != "d1e0d3c2-3333-4333-8333-00000000000c" {
		t.Fatalf("GET alpha-two as A = %v, want only alpha-two's decision", other)
	}

	// Another tenant's room is not visible at all: 404 rather than an empty list.
	if code, body := env.getDecisions(t, env.tokenA, "beta"); code != http.StatusNotFound {
		t.Fatalf("GET another tenant's room as A = %d %s, want 404", code, body)
	}
	if code, body := env.getDecisions(t, env.tokenB, "alpha"); code != http.StatusNotFound {
		t.Fatalf("GET A's room as B = %d %s, want 404", code, body)
	}

	// And the write side of the same rule: B's decision answered by A, first through A's own room
	// (the row is out of scope) and then through B's room (the room is not A's).
	code, body = env.postAnswer(t, env.tokenA, "alpha", roomDecisionPgDecBetaID,
		`{"question_id":"q1","option_id":"ship"}`)
	if code != http.StatusNotFound || !strings.Contains(body, "unknown-decision") {
		t.Fatalf("answering another tenant's decision through A's room = %d %s, want 404 unknown-decision", code, body)
	}
	code, body = env.postAnswer(t, env.tokenA, "beta", roomDecisionPgDecBetaID,
		`{"question_id":"q1","option_id":"ship"}`)
	if code != http.StatusNotFound {
		t.Fatalf("answering in another tenant's room = %d %s, want 404", code, body)
	}
	// B's row is untouched by either attempt, and B can still answer it.
	if state, answers := env.row(t, roomDecisionPgDecBetaID); state != "pending" || answers != "{}" {
		t.Fatalf("B's row = %q %s, want it untouched", state, answers)
	}
	code, body = env.postAnswer(t, env.tokenB, "beta", roomDecisionPgDecBetaID,
		`{"question_id":"q1","option_id":"ship"}`)
	if code != http.StatusOK {
		t.Fatalf("B answering its own decision = %d %s, want 200", code, body)
	}
}
