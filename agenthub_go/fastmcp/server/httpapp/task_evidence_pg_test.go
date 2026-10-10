package httpapp

// O3, the server half of "evidence from the client": POST /api/v2/tasks/{id}/evidence records an
// evidence_submitted entry through the ledger's ONE writer, guarded by the same `authed` wrapper as
// GET /{id}/events. There is no machine token (e5ecff63 removed it).
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and the skip says so
// loudly. Three of the four claims are claims about ROWS - the stored payload, the duplicate rule
// (which must hold against the task's LATEST entry), and the 404 for another user's task - and a fake
// would only write this comment's hypothesis back to its author.
//
// The route is driven through app.Handler(), so the path under test is the production one:
//
//	POST /api/v2/tasks/{id}/evidence -> authed -> routes.SubmitTaskEvidence -> the task-first 404
//	                                 -> taskEvidenceWriterAdapter -> one transaction: the ledger's
//	                                    per-user advisory lock, the decision, TaskEventRecorder.Record
//	GET  /api/v2/tasks/{id}/events  -> the existing ledger read the entry must be readable through
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// The project and branch the tasks in these tests hang off. Only these two rows are written by hand;
// the tasks themselves are created through POST /api/v2/tasks/, because a hand-seeded task row
// carries the database session's local `now()` while the application writes UTC and the entity
// refuses such a row - which GetTask swallows into "not found" (see task_delete_ledger_pg_test.go).
const (
	evidenceTestProjectID = "33333333-3333-4333-8333-333333333333"
	evidenceTestBranchID  = "44444444-4444-4444-8444-444444444444"
)

func evidenceSeedBranch(t *testing.T, sm *database.SessionManager, userID string) {
	t.Helper()
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'evidence project','',now(),now(),$2,'active','{}') ON CONFLICT (id) DO NOTHING`, evidenceTestProjectID, userID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'evidence branch','',now(),now(),'medium','todo','{}',0,0,$3) ON CONFLICT (id) DO NOTHING`, evidenceTestBranchID, evidenceTestProjectID, userID)
}

// evidenceUser mints a token for a UUID-shaped subject and returns it with the id the composition
// scopes rows to. The subject is a UUID on purpose: ValidateUserID returns a parseable UUID
// unchanged, so the id the routes layer resolves (currentUserID) and the id the composition scopes
// rows to are the SAME string, as they are for a real provider's subject. A non-UUID subject would
// make this test measure the raw-vs-normalized seam rather than the evidence route.
func evidenceUser(t *testing.T, subject string) (string, string) {
	t.Helper()
	token := wsTestTokenFor(t, subject, nil)
	code, user := wsRESTUser(t, "Bearer "+token)
	if code != http.StatusOK || user == "" {
		t.Fatalf("the REST bearer dependency resolved no user for %q: status = %d", subject, code)
	}
	scoped, err := domain.ValidateUserID(&user, "seeding the rows these tests use")
	if err != nil {
		t.Fatalf("mapping the user id: %v", err)
	}
	return token, scoped
}

// evidenceTaskCreate creates the task the evidence hangs off, through the production route.
func evidenceTaskCreate(t *testing.T, app *App, token, title string) string {
	t.Helper()
	code, taskID, body := taskCreate(t, app, token, title, evidenceTestBranchID)
	if code != http.StatusOK || taskID == "" {
		t.Fatalf("POST /api/v2/tasks/ = %d, id = %q, want 200 and an id: %s", code, taskID, body)
	}
	return taskID
}

// evidenceBody is a request body with the fields the wire contract names. The numstat carries tabs
// and newlines so the read-back proves the text travelled verbatim rather than through a reformat.
func evidenceBody(baseSHA, headSHA, numstat string) string {
	body, err := json.Marshal(map[string]any{
		"base_sha": baseSHA,
		"head_sha": headSHA,
		"numstat":  numstat,
		"test": map[string]any{
			"command":   "go test ./fastmcp/server/httpapp/",
			"exit_code": 0,
			"failed":    []string{"TestX", "TestY"},
		},
	})
	if err != nil {
		panic(err)
	}
	return string(body)
}

// evidencePost drives POST /api/v2/tasks/{id}/evidence and returns the status code and body. An
// empty token means NO Authorization header, which is how a client without a credential calls.
func evidencePost(t *testing.T, app *App, token, taskID, body string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost, "/api/v2/tasks/"+taskID+"/evidence", strings.NewReader(body))
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// evidenceEventsGet drives the existing per-task ledger read the entry must be readable through.
func evidenceEventsGet(t *testing.T, app *App, token, taskID string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/api/v2/tasks/"+taskID+"/events", nil)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// evidenceReadEvents decodes the read's body and returns every event of the given kind, oldest first.
func evidenceReadEvents(t *testing.T, body, kind string) []map[string]any {
	t.Helper()
	var parsed struct {
		Success bool             `json:"success"`
		Events  []map[string]any `json:"events"`
		Count   int              `json:"count"`
	}
	if err := json.Unmarshal([]byte(body), &parsed); err != nil {
		t.Fatalf("decoding the ledger read: %v (%s)", err, body)
	}
	out := []map[string]any{}
	for _, e := range parsed.Events {
		if e["kind"] == kind {
			out = append(out, e)
		}
	}
	return out
}

func evidenceApp(t *testing.T) (*App, *database.SessionManager) {
	t.Helper()
	sm := newMissedNotificationAppEnv(t)
	// Auth on, so the route resolves the caller from the minted token; with it off the development
	// fallback identity is used and a task carrying the token's user is outside its scope.
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)
	app, err := NewApp(context.Background(), sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	return app, sm
}

// TestEvidenceRouteRefusesAnUnusableCredentialLikeTheEventsRead is acceptance check 1: the guard is
// the EXISTING one, exercised through the route rather than a unit stub, and the evidence POST must
// answer exactly what the events read answers for the same probes - a route with a guard of its own
// would show up here as a disagreement.
func TestEvidenceRouteRefusesAnUnusableCredentialLikeTheEventsRead(t *testing.T) {
	app, _ := evidenceApp(t)
	// A minted token sets the JWT secret the validator needs, and it gives the test the one probe
	// that proves the guard can be passed at all: a REAL credential reaches the handler, which then
	// answers 404 for a task that does not exist.
	token, _ := evidenceUser(t, "a3f1c2d4-1111-4111-8111-000000000009")
	const taskID = "e1d0c9b8-1111-4111-8111-0000000000a1"
	body := evidenceBody("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "")

	noCredCode, noCredBody := evidencePost(t, app, "", taskID, body)
	noCredEventsCode, _ := evidenceEventsGet(t, app, "", taskID)
	badCredCode, badCredBody := evidencePost(t, app, "not-a-token", taskID, body)
	badCredEventsCode, _ := evidenceEventsGet(t, app, "not-a-token", taskID)
	validCode, validBody := evidencePost(t, app, token, taskID, body)
	t.Logf("OBSERVED no credential: POST /evidence -> %d %s | GET /events -> %d", noCredCode, noCredBody, noCredEventsCode)
	t.Logf("OBSERVED an invalid credential: POST /evidence -> %d %s | GET /events -> %d", badCredCode, badCredBody, badCredEventsCode)
	t.Logf("OBSERVED a valid credential for a task that does not exist: POST /evidence -> %d %s", validCode, validBody)

	if badCredCode != http.StatusUnauthorized {
		t.Fatalf("an unusable credential must answer 401 from the existing guard, got %d: %s", badCredCode, badCredBody)
	}
	if noCredCode != noCredEventsCode || badCredCode != badCredEventsCode {
		t.Fatalf("the evidence route must be guarded by the SAME wrapper as the events read: evidence %d/%d, events %d/%d",
			noCredCode, badCredCode, noCredEventsCode, badCredEventsCode)
	}
	if noCredCode == http.StatusCreated || badCredCode == http.StatusCreated {
		t.Fatalf("a refused credential wrote an entry: no-credential %d, bad-credential %d", noCredCode, badCredCode)
	}
	if validCode != http.StatusNotFound {
		t.Fatalf("a valid credential must reach the handler (404 for an unknown task), got %d: %s", validCode, validBody)
	}
}

// TestEvidenceRouteStoresOneEventTheLedgerReadReturns is acceptance check 3: one submission stores
// one evidence_submitted entry whose payload carries the request's own fields - the two shas, the
// numstat verbatim and the test block - readable back through the existing per-task event read.
func TestEvidenceRouteStoresOneEventTheLedgerReadReturns(t *testing.T) {
	app, sm := evidenceApp(t)
	const subject = "a3f1c2d4-1111-4111-8111-000000000001"
	token, scoped := evidenceUser(t, subject)
	evidenceSeedBranch(t, sm, scoped)
	taskID := evidenceTaskCreate(t, app, token, "the task the evidence is about")

	const baseSHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	const headSHA = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	const numstat = "12\t3\tfastmcp/server/httpapp/task_routes.go\n0\t1\tfastmcp/server/routes/task_evidence_routes.go\n"

	code, body := evidencePost(t, app, token, taskID, evidenceBody(baseSHA, headSHA, numstat))
	t.Logf("OBSERVED POST /api/v2/tasks/%s/evidence -> %d; body=%.400s", taskID, code, body)
	if code != http.StatusCreated {
		t.Fatalf("POST evidence = %d, want 201: %s", code, body)
	}

	var created map[string]any
	if err := json.Unmarshal([]byte(body), &created); err != nil {
		t.Fatalf("decoding the created event: %v (%s)", err, body)
	}
	for _, key := range []string{"id", "task_id", "seq", "kind", "actor_kind", "actor_id", "payload", "created_at"} {
		if _, has := created[key]; !has {
			t.Fatalf("the 201 body is missing %q: %s", key, body)
		}
	}
	if created["kind"] != "evidence_submitted" || created["task_id"] != taskID {
		t.Fatalf("the created event is %v/%v, want evidence_submitted/%s", created["kind"], created["task_id"], taskID)
	}
	if created["actor_kind"] != "human" || created["actor_id"] != scoped {
		t.Fatalf("a submission with no seat header belongs to the caller: actor = %v/%v, want human/%s",
			created["actor_kind"], created["actor_id"], scoped)
	}
	createdAt, isString := created["created_at"].(string)
	if !isString {
		t.Fatalf("created_at = %#v, want a string: the writer refuses a time.Time", created["created_at"])
	}
	if _, err := time.Parse(time.RFC3339, createdAt); err != nil {
		t.Fatalf("created_at = %q is not RFC3339: %v", createdAt, err)
	}

	readCode, readBody := evidenceEventsGet(t, app, token, taskID)
	t.Logf("OBSERVED GET /api/v2/tasks/%s/events -> %d; body=%.500s", taskID, readCode, readBody)
	if readCode != http.StatusOK {
		t.Fatalf("the ledger read = %d, want 200: %s", readCode, readBody)
	}
	events := evidenceReadEvents(t, readBody, "evidence_submitted")
	if len(events) != 1 {
		t.Fatalf("evidence_submitted entries read back = %d, want exactly 1: %s", len(events), readBody)
	}
	if readAt, isString := events[0]["created_at"].(string); !isString || readAt == "" {
		t.Fatalf("the read's created_at = %#v, want the same RFC3339 string shape: %s", events[0]["created_at"], readBody)
	}
	stored, _ := events[0]["payload"].(map[string]any)
	if stored == nil {
		t.Fatalf("the read returned no payload: %s", readBody)
	}
	if stored["base_sha"] != baseSHA || stored["head_sha"] != headSHA {
		t.Fatalf("payload shas = %v/%v, want %s/%s", stored["base_sha"], stored["head_sha"], baseSHA, headSHA)
	}
	if stored["numstat"] != numstat {
		t.Fatalf("payload numstat = %q, want the text `git diff --numstat` printed: %q", stored["numstat"], numstat)
	}
	test, _ := stored["test"].(map[string]any)
	if test == nil {
		t.Fatalf("the payload carries no test block: %v", stored)
	}
	if test["command"] != "go test ./fastmcp/server/httpapp/" || test["exit_code"] != float64(0) {
		t.Fatalf("test block = %v", test)
	}
	failed, _ := test["failed"].([]any)
	if len(failed) != 2 || failed[0] != "TestX" || failed[1] != "TestY" {
		t.Fatalf("test.failed = %v, want [TestX TestY]", test["failed"])
	}
}

// TestEvidenceRouteRefusesASecondSubmissionOfTheSameHeadSHA is acceptance check 2: 409 when head_sha
// equals the previous evidence's - and a DIFFERENT head_sha is still accepted, so the refusal is
// about the same evidence rather than about a task's second submission.
func TestEvidenceRouteRefusesASecondSubmissionOfTheSameHeadSHA(t *testing.T) {
	app, sm := evidenceApp(t)
	token, scoped := evidenceUser(t, "a3f1c2d4-1111-4111-8111-000000000002")
	evidenceSeedBranch(t, sm, scoped)
	taskID := evidenceTaskCreate(t, app, token, "the task whose evidence is resubmitted")

	const first = "1111111111111111111111111111111111111111"
	const second = "2222222222222222222222222222222222222222"

	code, body := evidencePost(t, app, token, taskID, evidenceBody("0000000000000000000000000000000000000000", first, "1\t0\ta.go\n"))
	t.Logf("OBSERVED the first submission -> %d", code)
	if code != http.StatusCreated {
		t.Fatalf("the first submission = %d, want 201: %s", code, body)
	}

	dupCode, dupBody := evidencePost(t, app, token, taskID, evidenceBody("0000000000000000000000000000000000000000", first, "2\t0\ta.go\n"))
	t.Logf("OBSERVED the same head_sha again -> %d %s", dupCode, dupBody)
	if dupCode != http.StatusConflict {
		t.Fatalf("a second submission of the same head_sha = %d, want 409: %s", dupCode, dupBody)
	}

	movedCode, movedBody := evidencePost(t, app, token, taskID, evidenceBody(first, second, "3\t0\ta.go\n"))
	t.Logf("OBSERVED a different head_sha -> %d", movedCode)
	if movedCode != http.StatusCreated {
		t.Fatalf("a different head_sha = %d, want 201 (the refusal is about the same evidence): %s", movedCode, movedBody)
	}

	if rows := evidenceSubmissionRows(t, sm, taskID); rows != 2 {
		t.Fatalf("evidence_submitted rows = %d, want the two accepted submissions", rows)
	}
}

// TestEvidenceRouteSerializesConcurrentDuplicates drives the decision the contract makes hardest:
// two submissions of the SAME head_sha, at the same time. The decision is taken inside the
// transaction that appends it and under the ledger's per-user append lock, so exactly one must land
// and the other must be refused - without that, both would read "no previous evidence" and both
// would append.
func TestEvidenceRouteSerializesConcurrentDuplicates(t *testing.T) {
	app, sm := evidenceApp(t)
	token, scoped := evidenceUser(t, "a3f1c2d4-1111-4111-8111-000000000003")
	evidenceSeedBranch(t, sm, scoped)
	taskID := evidenceTaskCreate(t, app, token, "the task two clients resubmit to")

	const headSHA = "3333333333333333333333333333333333333333"
	body := evidenceBody("0000000000000000000000000000000000000000", headSHA, "1\t0\ta.go\n")

	const writers = 2
	codes := make([]int, writers)
	var wg sync.WaitGroup
	start := make(chan struct{})
	for i := range writers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			codes[i], _ = evidencePost(t, app, token, taskID, body)
		}()
	}
	close(start)
	wg.Wait()
	t.Logf("OBSERVED %d concurrent submissions of one head_sha -> statuses %v", writers, codes)

	created, conflicts := 0, 0
	for _, code := range codes {
		switch code {
		case http.StatusCreated:
			created++
		case http.StatusConflict:
			conflicts++
		}
	}
	if created != 1 || conflicts != writers-1 {
		t.Fatalf("concurrent duplicates = %v, want exactly one 201 and %d x 409", codes, writers-1)
	}
	if rows := evidenceSubmissionRows(t, sm, taskID); rows != 1 {
		t.Fatalf("evidence_submitted rows = %d, want exactly the one that won", rows)
	}
}

// TestEvidenceRouteAnswers404ForAnotherUsersTask is acceptance check 4: the 404 comes from the SAME
// seam the events read uses (the task is asked for first, through the task controller), so another
// user's task is refused before anything is decided or written - and the owner can still submit to
// the very same task afterwards, which is what makes the negative specific rather than a broken route.
func TestEvidenceRouteAnswers404ForAnotherUsersTask(t *testing.T) {
	app, sm := evidenceApp(t)
	ownerToken, ownerID := evidenceUser(t, "a3f1c2d4-1111-4111-8111-000000000004")
	intruderToken, _ := evidenceUser(t, "a3f1c2d4-2222-4222-8222-000000000005")
	evidenceSeedBranch(t, sm, ownerID)
	taskID := evidenceTaskCreate(t, app, ownerToken, "the task the other user cannot see")

	body := evidenceBody("0000000000000000000000000000000000000000", "4444444444444444444444444444444444444444", "1\t0\ta.go\n")

	intruderCode, intruderBody := evidencePost(t, app, intruderToken, taskID, body)
	intruderEventsCode, _ := evidenceEventsGet(t, app, intruderToken, taskID)
	t.Logf("OBSERVED another user's POST -> %d %s | GET /events -> %d", intruderCode, intruderBody, intruderEventsCode)
	if intruderCode != http.StatusNotFound {
		t.Fatalf("another user's task = %d, want 404: %s", intruderCode, intruderBody)
	}
	if intruderEventsCode != http.StatusNotFound {
		t.Fatalf("the events read disagrees about the same task: %d", intruderEventsCode)
	}
	if rows := evidenceSubmissionRows(t, sm, taskID); rows != 0 {
		t.Fatalf("evidence_submitted rows = %d after a refused submission, want 0", rows)
	}

	missingCode, _ := evidencePost(t, app, ownerToken, "e1d0c9b8-9999-4999-8999-0000000000ff", body)
	t.Logf("OBSERVED a task that does not exist -> %d", missingCode)
	if missingCode != http.StatusNotFound {
		t.Fatalf("a task that does not exist = %d, want 404", missingCode)
	}

	ownerCode, ownerBody := evidencePost(t, app, ownerToken, taskID, body)
	t.Logf("OBSERVED the owner's submission to the same task -> %d", ownerCode)
	if ownerCode != http.StatusCreated {
		t.Fatalf("the owner = %d, want 201: %s", ownerCode, ownerBody)
	}
	if rows := evidenceSubmissionRows(t, sm, taskID); rows != 1 {
		t.Fatalf("evidence_submitted rows = %d, want the owner's one", rows)
	}
}

// TestEvidenceLedgerReadIsScopedLikeItsWrites pins the seam a NON-UUID credential walks. The ledger's
// user_id is written normalized by both of its writers (and the ledger's own StatusOf compares that
// id against tasks.user_id, which is normalized too), while the read used to filter by the RAW token
// subject - so it matched nothing and answered 200 with an empty list, silently. The default
// development identity (`dev-user-00000000-0000-0000-0000-000000000000`, keycloak_dependencies.go) is
// exactly such a subject, which is why this is measured against a real database rather than assumed.
func TestEvidenceLedgerReadIsScopedLikeItsWrites(t *testing.T) {
	app, sm := evidenceApp(t)
	const subject = "seam-probe-user" // deliberately NOT a UUID
	token, scoped := evidenceUser(t, subject)
	evidenceSeedBranch(t, sm, scoped)
	taskID := evidenceTaskCreate(t, app, token, "the task of a non-uuid subject")

	code, body := evidencePost(t, app, token, taskID,
		evidenceBody("0000000000000000000000000000000000000000", "5555555555555555555555555555555555555555", "1\t0\ta.go\n"))
	readCode, readBody := evidenceEventsGet(t, app, token, taskID)
	t.Logf("OBSERVED subject %q scoped to %q: POST /evidence -> %d; GET /events -> %d %.300s",
		subject, scoped, code, readCode, readBody)

	if code != http.StatusCreated {
		t.Fatalf("POST evidence = %d, want 201: %s", code, body)
	}
	if readCode != http.StatusOK {
		t.Fatalf("the ledger read = %d, want 200: %s", readCode, readBody)
	}
	if events := evidenceReadEvents(t, readBody, "evidence_submitted"); len(events) != 1 {
		t.Fatalf("a non-UUID subject must read back its own entry, got %d: %s", len(events), readBody)
	}
}

func evidenceSubmissionRows(t *testing.T, sm *database.SessionManager, taskID string) int {
	t.Helper()
	n := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM task_events WHERE task_id = $1::uuid AND kind = 'evidence_submitted'`, taskID).Scan(&n)
	}); err != nil {
		t.Fatalf("counting evidence_submitted rows: %v", err)
	}
	return n
}
