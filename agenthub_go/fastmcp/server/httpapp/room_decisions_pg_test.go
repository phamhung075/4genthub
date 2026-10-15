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
	"time"

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

// seedRoom creates just the room, with no decision in it: the row is what the ingest route makes when
// a case drives the crossing.
func (e *roomDecisionPgEnv) seedRoom(t *testing.T, roomID, userID, slug string) {
	t.Helper()
	ledgerExec(t, e.sm, `INSERT INTO rooms (id, user_id, slug, name, created_at, updated_at)
		VALUES ($1::uuid, $2, $3, $4, now(), now())`, roomID, userID, slug, slug)
}

// seed mirrors one ask into one room by writing the row straight into the table: the cases about the
// ANSWER route need a row to click on without an ask route in the path. qitemID is the routed item's
// own id, and two rows of one owner may not share it: uq_room_decisions_user_qitem enforces that, so a
// fixture for a second room of the same owner must carry a second qitem id.
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

// postJSON drives one POST through the production handler, with a bearer when the case passes one.
func (e *roomDecisionPgEnv) postJSON(t *testing.T, token, path, body string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	e.app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// getPath drives one GET the same way.
func (e *roomDecisionPgEnv) getPath(t *testing.T, token, path string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, path, nil)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	rec := httptest.NewRecorder()
	e.app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// ackedAt reads the delivery marker straight from the table: "the ack is the delivery record" is a
// claim about this column, and only a row can settle it.
func (e *roomDecisionPgEnv) ackedAt(t *testing.T, id string) *time.Time {
	t.Helper()
	var at *time.Time
	if err := e.sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "acked_at" FROM "room_decisions" WHERE "id" = $1::uuid`, id).Scan(&at)
	}); err != nil {
		t.Fatalf("reading the delivery marker: %v", err)
	}
	return at
}

// answeredAt reads the column the pull's cursor is minted from. The cursor's instant half is a claim
// about this value and not about the ask's created_at, so the acceptance compares them.
func (e *roomDecisionPgEnv) answeredAt(t *testing.T, id string) *time.Time {
	t.Helper()
	var at *time.Time
	if err := e.sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "answered_at" FROM "room_decisions" WHERE "id" = $1::uuid`, id).Scan(&at)
	}); err != nil {
		t.Fatalf("reading answered_at: %v", err)
	}
	return at
}

func (e *roomDecisionPgEnv) postAnswer(t *testing.T, token, slug, id, body string) (int, string) {
	t.Helper()
	return e.postJSON(t, token, "/api/v2/rooms/"+slug+"/decisions/"+id+"/answer", body)
}

func (e *roomDecisionPgEnv) getDecisions(t *testing.T, token, slug string) (int, string) {
	t.Helper()
	return e.getPath(t, token, "/api/v2/rooms/"+slug+"/decisions")
}

// roomDecisionPgIngest is the ask a case sends: the routed item's own id, and the idempotency key
// DERIVED from it, which is the shape the daemon mints.
func roomDecisionPgIngest(roomID, qitem string) string {
	return `{"rig":"4genthub-min","room":"` + roomID + `","qitem_id":"` + qitem + `","author_seat_key":"go-dev",` +
		`"destination":"human-operator@kernel","summary":"ship the cloud half first?",` +
		`"detail":"the panel needs the answer","questions":` + roomDecisionPgQuestions + `,` +
		`"idempotency_key":"agenthub:decision:` + qitem + `"}`
}

// postIngest drives the ask route and returns the stored row's id, the wire's `created`, and the row's
// state. It FAILS when the answer is not a success carrying a row: a created:false with no decision is
// the swallowed ask (or the nil dereference) this packet's ruling is about, never a success.
func (e *roomDecisionPgEnv) postIngest(t *testing.T, token, body string) (string, bool, string) {
	t.Helper()
	code, res := e.postJSON(t, token, "/api/v2/decisions", body)
	if code != http.StatusOK {
		t.Fatalf("ingest = %d %s, want 200", code, res)
	}
	var out struct {
		Success  bool `json:"success"`
		Created  bool `json:"created"`
		Decision struct {
			ID    string `json:"id"`
			State string `json:"state"`
		} `json:"decision"`
	}
	if err := json.Unmarshal([]byte(res), &out); err != nil {
		t.Fatalf("decoding the ingest response: %v (%s)", err, res)
	}
	if !out.Success || out.Decision.ID == "" {
		t.Fatalf("ingest answered %s, want success with a stored row's id", res)
	}
	return out.Decision.ID, out.Created, out.Decision.State
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

// idempotencyKeyOf reads a row's stored key, the correlatable value the dedupe no longer rides on.
func (e *roomDecisionPgEnv) idempotencyKeyOf(t *testing.T, id string) string {
	t.Helper()
	key := ""
	if err := e.sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "idempotency_key" FROM "room_decisions" WHERE "id" = $1::uuid`, id).Scan(&key)
	}); err != nil {
		t.Fatalf("reading the stored key: %v", err)
	}
	return key
}

// TestRoomDecisionPgTheSameQitemInTwoTenantsIsTwoAsks is the ruling's own case: the dedupe tuple is the
// EPISODE, (user_id, qitem_id), so one routed item asked about by two tenants is two asks. The
// constraint it replaces was UNIQUE (idempotency_key) alone, which is GLOBAL: the second tenant's
// insert no-opped, the loser path read that key back scoped to the SECOND tenant, found nothing, and
// the route answered created:false with no decision - one tenant's ask swallowed by another tenant's
// key, and the human never asked.
func TestRoomDecisionPgTheSameQitemInTwoTenantsIsTwoAsks(t *testing.T) {
	env := newRoomDecisionPgEnv(t)
	env.seedRoom(t, roomDecisionPgRoomAlphaID, env.userA, "alpha")
	env.seedRoom(t, roomDecisionPgRoomBetaID, env.userB, "beta")

	const shared = "qitem-pg-shared-episode"
	alphaID, created, state := env.postIngest(t, env.tokenA, roomDecisionPgIngest("alpha", shared))
	if !created || state != "pending" {
		t.Fatalf("A's ask created=%v state=%q, want its own new pending row", created, state)
	}

	// The other tenant asks about the SAME routed item: its own row, not A's, and not silence.
	betaID, created, state := env.postIngest(t, env.tokenB, roomDecisionPgIngest("beta", shared))
	if !created || state != "pending" {
		t.Fatalf("B's ask created=%v state=%q, want its own new pending row", created, state)
	}
	if betaID == alphaID {
		t.Fatalf("B's ask resolved to A's row %s, so the tenants share one dedupe key", alphaID)
	}
	// The key is stored and correlatable, and it IS the same string on both rows: what keeps them apart
	// is the episode, not the key.
	if a, b := env.idempotencyKeyOf(t, alphaID), env.idempotencyKeyOf(t, betaID); a != b {
		t.Errorf("keys = %q and %q, want the derived key the same on both rows", a, b)
	}
	if n := env.count(t, env.userA); n != 1 {
		t.Errorf("A holds %d rows, want one", n)
	}
	if n := env.count(t, env.userB); n != 1 {
		t.Errorf("B holds %d rows, want one", n)
	}
	// A's redrive still collapses onto A's own row, and never onto B's.
	if againID, againCreated, _ := env.postIngest(t, env.tokenA, roomDecisionPgIngest("alpha", shared)); againCreated || againID != alphaID {
		t.Fatalf("A's redrive created=%v id=%s, want A's own row %s with created:false", againCreated, againID, alphaID)
	}
	// Each tenant reads its own room and finds its own ask.
	if code, body := env.getDecisions(t, env.tokenA, "alpha"); code != http.StatusOK || !strings.Contains(body, alphaID) {
		t.Errorf("A's room read = %d %s, want its own ask", code, body)
	}
	if code, body := env.getDecisions(t, env.tokenB, "beta"); code != http.StatusOK || !strings.Contains(body, betaID) {
		t.Errorf("B's room read = %d %s, want its own ask", code, body)
	}
}

// TestRoomDecisionPgCrossingRoundTrip is S2's acceptance at the route: the ask arrives through the
// ingest route, the human answers it in the panel, the daemon pulls it - with the room's SLUG beside
// it and a cursor minted from that row's answered_at - acks it as applied, and the same answer is
// never handed out again. Every statement of the answer leg runs against real Postgres here: the
// insert, the acked filter, the room-slug subquery and the guarded ack UPDATE. A second ask covers the
// OTHER outcome: an answer the daemon drops is acked all the same and never retried, and its state is
// what a separate push then moves.
func TestRoomDecisionPgCrossingRoundTrip(t *testing.T) {
	env := newRoomDecisionPgEnv(t)
	env.seedRoom(t, roomDecisionPgRoomAlphaID, env.userA, "alpha")

	ingest := func(qitem string) string { return roomDecisionPgIngest("alpha", qitem) }
	type answersPage struct {
		Success bool `json:"success"`
		Answers []struct {
			DecisionID string            `json:"decision_id"`
			QitemID    string            `json:"qitem_id"`
			Room       string            `json:"room"`
			Answers    map[string]string `json:"answers"`
			AnsweredAt string            `json:"answered_at"`
		} `json:"answers"`
		Cursor string `json:"cursor"`
	}
	pull := func(t *testing.T, token string) (int, answersPage) {
		t.Helper()
		code, res := env.getPath(t, token, "/api/v2/decisions/answers?rig=4genthub-min")
		var got answersPage
		if err := json.Unmarshal([]byte(res), &got); err != nil {
			t.Fatalf("decoding the pull response: %v (%s)", err, res)
		}
		return code, got
	}

	decisionID, created, state := env.postIngest(t, env.tokenA, ingest("qitem-pg-crossing"))
	if !created || state != "pending" {
		t.Fatalf("first ingest created=%v state=%q, want a newly stored pending ask", created, state)
	}
	if n := env.count(t, env.userA); n != 1 {
		t.Fatalf("rows = %d, want the one the ingest made", n)
	}
	// The redrive: the daemon's key again is the row the first attempt made, and the response says so.
	if againID, againCreated, _ := env.postIngest(t, env.tokenA, ingest("qitem-pg-crossing")); againCreated || againID != decisionID {
		t.Fatalf("redrive answered created=%v id=%s, want the same row with created:false", againCreated, againID)
	}
	if n := env.count(t, env.userA); n != 1 {
		t.Fatalf("rows after the redrive = %d, want one", n)
	}

	// The human answers both questions in the panel: only the completing click moves the row.
	for _, click := range []string{`{"question_id":"q1","option_id":"ship"}`, `{"question_id":"q2","option_id":"lead"}`} {
		if code, body := env.postAnswer(t, env.tokenA, "alpha", decisionID, click); code != http.StatusOK {
			t.Fatalf("answer %s = %d %s, want 200", click, code, body)
		}
	}

	code, page := pull(t, env.tokenA)
	if code != http.StatusOK || !page.Success || len(page.Answers) != 1 {
		t.Fatalf("pull = %d %+v, want the one answered row", code, page)
	}
	if got := page.Answers[0]; got.DecisionID != decisionID || got.Room != "alpha" || got.Answers["q1"] != "ship" || got.AnsweredAt == "" {
		t.Fatalf("answer = %+v, want the row with its room's SLUG and its answers", got)
	}
	// The cursor's instant half is the row's ANSWERED_AT and not the ask's created_at: a keyset over the
	// wrong key loses or repeats rows, so the claim is settled against the column itself.
	answered := env.answeredAt(t, decisionID)
	if answered == nil {
		t.Fatalf("answered_at = NULL on an answered row")
	}
	if want := answered.UTC().Format(time.RFC3339Nano) + "|" + decisionID; page.Cursor != want {
		t.Fatalf("cursor = %q, want the answered_at keyset %q", page.Cursor, want)
	}

	// The ack IS the delivery record: `applied` resolves the row...
	if code, body := env.postJSON(t, env.tokenA, "/api/v2/decisions/"+decisionID+"/ack",
		`{"machine_id":"host-1","outcome":"applied"}`); code != http.StatusOK ||
		!strings.Contains(body, `"delivered":true`) || !strings.Contains(body, `"state":"resolved"`) {
		t.Fatalf("ack = %d %s, want 200 delivered with the resolved state", code, body)
	}
	if state, _ := env.row(t, decisionID); state != "resolved" {
		t.Fatalf("state = %q, want resolved: applied is the only input that resolves", state)
	}
	if at := env.ackedAt(t, decisionID); at == nil {
		t.Fatalf("acked_at = NULL, want the delivery recorded")
	}
	// ...and the row is never handed out again.
	if code, page := pull(t, env.tokenA); code != http.StatusOK || len(page.Answers) != 0 || page.Cursor != "" {
		t.Fatalf("pull after the ack = %d %+v, want a page with no answers", code, page)
	}
	// A second ack is the state, not the id.
	if code, body := env.postJSON(t, env.tokenA, "/api/v2/decisions/"+decisionID+"/ack",
		`{"machine_id":"host-1","outcome":"applied"}`); code != http.StatusConflict {
		t.Fatalf("second ack = %d %s, want 409", code, body)
	}
	// The tenant fence: another tenant pulling this rig's name gets its own empty page, not A's row.
	if code, page := pull(t, env.tokenB); code != http.StatusOK || len(page.Answers) != 0 {
		t.Fatalf("pull as the other tenant = %d %+v, want nothing", code, page)
	}

	// The second ask covers the other outcome end to end through the routes: an answer the daemon DROPS
	// is acked just the same, never retried, and keeps its state until the daemon reports one.
	droppedID, created, _ := env.postIngest(t, env.tokenA, ingest("qitem-pg-dropped"))
	if !created {
		t.Fatalf("second ingest made no row")
	}
	for _, click := range []string{`{"question_id":"q1","option_id":"wait"}`, `{"question_id":"q2","option_id":"me"}`} {
		if code, body := env.postAnswer(t, env.tokenA, "alpha", droppedID, click); code != http.StatusOK {
			t.Fatalf("answer of the second ask = %d %s, want 200", code, body)
		}
	}
	if code, body := env.postJSON(t, env.tokenA, "/api/v2/decisions/"+droppedID+"/ack",
		`{"machine_id":"host-1","outcome":"dropped","reason":"state-done"}`); code != http.StatusOK ||
		!strings.Contains(body, `"delivered":true`) || !strings.Contains(body, `"state":"answered"`) {
		t.Fatalf("dropped ack = %d %s, want 200 delivered with the state kept", code, body)
	}
	if state, _ := env.row(t, droppedID); state != "answered" {
		t.Fatalf("state = %q, want answered: a drop resolves nothing", state)
	}
	if at := env.ackedAt(t, droppedID); at == nil {
		t.Fatalf("acked_at = NULL after a dropped ack, want the delivery recorded")
	}
	if code, page := pull(t, env.tokenA); code != http.StatusOK || len(page.Answers) != 0 {
		t.Fatalf("pull after the drop = %d %+v, want no answers: a dropped answer is never retried", code, page)
	}
	// The state the daemon learned elsewhere is the separate route's job, and it lands on this row.
	if code, body := env.postJSON(t, env.tokenA, "/api/v2/decisions/"+droppedID+"/state",
		`{"machine_id":"host-1","state":"superseded","reason":"slack-first"}`); code != http.StatusOK ||
		!strings.Contains(body, `"state":"superseded"`) {
		t.Fatalf("state push = %d %s, want 200 superseded", code, body)
	}
	if state, _ := env.row(t, droppedID); state != "superseded" {
		t.Fatalf("state = %q, want superseded", state)
	}
}
