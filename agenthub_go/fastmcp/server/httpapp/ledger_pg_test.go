package httpapp

// P2 and P3 of the sync protocol (NEXT_GEN.md :441, :442), driven through app.Handler() so the path
// under test is the production one:
//
//	GET  /api/v2/ledger?after=<user_seq>&limit=   -> authed -> routes.GetLedger -> the ledger read
//	POST /api/v2/ledger/intents                   -> authed -> routes.SubmitLedgerIntents -> the
//	                                                 ledger's application service: per item, one
//	                                                 transaction holding the ledger's per-user append
//	                                                 lock, the decision, and the append
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and the skip says so
// loudly. Every claim in these cases is a claim about ROWS - which user's rows a page holds, the
// order, the tip, the reason a decision was refused, and that a resend added no second row - and a
// fake would only write these comments' hypothesis back to its author. To run them:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres go test -count=1 ./fastmcp/server/httpapp/
//
// A SKIP IS NOT A PASS: if the runner prints SKIPPED, none of these cases ran.

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// The UUID-shaped subjects these cases mint credentials for. UUIDs on purpose: ValidateUserID
// returns a parseable UUID unchanged, so the id the routes layer resolves and the id the ledger
// scopes rows to are the SAME string, as they are for a real provider's subject.
const (
	ledgerPgSubjectA = "b1e0d3c2-2222-4222-8222-00000000000a"
	ledgerPgSubjectB = "b1e0d3c2-2222-4222-8222-00000000000b"
	ledgerPgSubjectC = "b1e0d3c2-2222-4222-8222-00000000000c"
)

// --- drivers ---

// ledgerPgGet drives the cross-task read. query is the whole query string, "?after=…&limit=…" or "".
func ledgerPgGet(t *testing.T, app *App, token, query string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/api/v2/ledger"+query, nil)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// ledgerPgPostIntents drives the intents route with a raw body, so a malformed body can be sent.
func ledgerPgPostIntents(t *testing.T, app *App, token, body string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost, "/api/v2/ledger/intents", strings.NewReader(body))
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// --- fixtures written straight into the ledger ---

// ledgerPgTask creates one task through the production route and returns its id.
func ledgerPgTask(t *testing.T, app *App, sm *database.SessionManager, token, user, title string) string {
	t.Helper()
	evidenceSeedBranch(t, sm, user)
	code, id, body := taskCreate(t, app, token, title, evidenceTestBranchID)
	if code != http.StatusOK || id == "" {
		t.Fatalf("POST /api/v2/tasks/ = %d, id = %q, want 200 and an id: %s", code, id, body)
	}
	return id
}

// ledgerPgSeedEvent appends one entry straight into task_events, as the reader's fixture, and
// returns the user_seq it took. The sequence numbers are read from the ledger rather than assumed
// because the task routes write entries of their own, and a fixed number would then collide with
// one -uq_task_event_user_seq would turn the fixture into a spurious failure.
func ledgerPgSeedEvent(t *testing.T, sm *database.SessionManager, userID, taskID, kind string) int64 {
	t.Helper()
	seq := ledgerPgTip(t, sm, userID) + 1
	ledgerExec(t, sm, `INSERT INTO task_events
		(id, task_id, subtask_id, user_id, seq, user_seq, client_event_id, kind, actor_kind, actor_id, payload, created_at)
		SELECT $1::uuid, $2::uuid, NULL, $3::varchar, COALESCE(MAX("seq"), 0) + 1, $4, NULL, $5, 'human', $3::varchar, '{"fixture":true}'::jsonb, now()
		FROM task_events WHERE "user_id" = $3::varchar AND "task_id" = $2::uuid`,
		value_objects.NewUUIDv4(), taskID, userID, seq, kind)
	return seq
}

// ledgerPgTip is the user's current tip, read straight from the ledger.
func ledgerPgTip(t *testing.T, sm *database.SessionManager, userID string) int64 {
	t.Helper()
	tip := int64(0)
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT COALESCE(MAX("user_seq"), 0) FROM task_events WHERE "user_id" = $1::varchar`, userID).Scan(&tip)
	}); err != nil {
		t.Fatalf("reading the user's tip: %v", err)
	}
	return tip
}

// ledgerPgTaskSeq is the task's current seq: the number a decision's base_seq is compared against.
func ledgerPgTaskSeq(t *testing.T, sm *database.SessionManager, userID, taskID string) int {
	t.Helper()
	seq := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT COALESCE(MAX("seq"), 0) FROM task_events WHERE "user_id" = $1::varchar AND "task_id" = $2::uuid`,
			userID, taskID).Scan(&seq)
	}); err != nil {
		t.Fatalf("reading the task's seq: %v", err)
	}
	return seq
}

// ledgerPgRowCount counts the ledger rows this user holds, which is how "no second row" is proved.
func ledgerPgRowCount(t *testing.T, sm *database.SessionManager, userID string) int {
	t.Helper()
	n := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM task_events WHERE "user_id" = $1::varchar`, userID).Scan(&n)
	}); err != nil {
		t.Fatalf("counting the user's ledger rows: %v", err)
	}
	return n
}

// --- decoded shapes ---

// ledgerPgPage is GET /api/v2/ledger's body.
type ledgerPgPage struct {
	Success bool             `json:"success"`
	Events  []map[string]any `json:"events"`
	Count   int              `json:"count"`
	After   *int64           `json:"after"`
	Tip     *int64           `json:"tip"`
}

// ledgerPgNum renders an optional sequence number for the OBSERVED lines. %v on a *int64 prints the
// POINTER, and an address says nothing about the page it came from.
func ledgerPgNum(v *int64) string {
	if v == nil {
		return "nil"
	}
	return strconv.FormatInt(*v, 10)
}

func ledgerPgDecodePage(t *testing.T, body string) ledgerPgPage {
	t.Helper()
	var page ledgerPgPage
	if err := json.Unmarshal([]byte(body), &page); err != nil {
		t.Fatalf("decoding the ledger read: %v (%s)", err, body)
	}
	return page
}

// ledgerPgRawAnswers returns each answer of the intents route as the exact JSON text the server
// sent, which is what "byte for byte" compares.
func ledgerPgRawAnswers(t *testing.T, body string) []string {
	t.Helper()
	var raw []json.RawMessage
	if err := json.Unmarshal([]byte(body), &raw); err != nil {
		t.Fatalf("decoding the intents answer: %v (%s)", err, body)
	}
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		out = append(out, string(item))
	}
	return out
}

// ledgerPgAnswer is one answer decoded with POINTERS, so a case can tell "the key is absent" from
// "the key is false" - the two answer shapes are told apart by which key they carry, and a
// non-pointer bool would read both as false.
type ledgerPgAnswer struct {
	Accepted *bool   `json:"accepted"`
	UserSeq  *int64  `json:"user_seq"`
	Seq      *int    `json:"seq"`
	Rejected *bool   `json:"rejected"`
	Reason   *string `json:"reason"`
	TaskSeq  *int    `json:"task_seq"`
}

func ledgerPgDecodeAnswers(t *testing.T, body string) []ledgerPgAnswer {
	t.Helper()
	var out []ledgerPgAnswer
	if err := json.Unmarshal([]byte(body), &out); err != nil {
		t.Fatalf("decoding the intents answer: %v (%s)", err, body)
	}
	return out
}

// ledgerPgIntent is one request item.
func ledgerPgIntent(clientEventID, taskID, kind string, baseSeq *int) map[string]any {
	item := map[string]any{
		"client_event_id": clientEventID,
		"task_id":         taskID,
		"kind":            kind,
		"payload":         map[string]any{"note": kind},
	}
	if baseSeq != nil {
		item["base_seq"] = *baseSeq
	}
	return item
}

func ledgerPgPostOne(t *testing.T, app *App, token, clientEventID, taskID, kind string, baseSeq *int) (int, string) {
	t.Helper()
	body, err := json.Marshal([]map[string]any{ledgerPgIntent(clientEventID, taskID, kind, baseSeq)})
	if err != nil {
		t.Fatalf("building the request: %v", err)
	}
	return ledgerPgPostIntents(t, app, token, string(body))
}

// --- P2: the cross-task read ---

// TestLedgerReadIsOneCursorAcrossAllOfAUsersTasks is P2's check: a user's reader returns only that
// user's rows, ordered by user_seq; the same after asked twice returns the same page and the same
// tip; another user's credential returns none of the first user's rows. The CONTRAST with O1a's
// per-task read is asserted too, because crossing tasks is the whole difference between the two
// routes and the box's acceptance criterion.
func TestLedgerReadIsOneCursorAcrossAllOfAUsersTasks(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectA)

	first := ledgerPgTask(t, app, sm, token, user, "ledger P2 first task")
	second := ledgerPgTask(t, app, sm, token, user, "ledger P2 second task")

	// Three entries INTERLEAVING the two tasks. Written straight into the ledger: the case is about
	// the reader, and a fixture written through a route would make it a case about that route too.
	u1 := ledgerPgSeedEvent(t, sm, user, first, "progress")
	u2 := ledgerPgSeedEvent(t, sm, user, second, "progress")
	u3 := ledgerPgSeedEvent(t, sm, user, first, "handover")

	code, body := ledgerPgGet(t, app, token, "")
	if code != http.StatusOK {
		t.Fatalf("GET /api/v2/ledger = %d, want 200: %s", code, body)
	}
	page := ledgerPgDecodePage(t, body)
	if !page.Success || page.Count != len(page.Events) {
		t.Fatalf("the page's count must be the number of events it carries: count = %d, events = %d, body = %s",
			page.Count, len(page.Events), body)
	}
	if page.Tip == nil || *page.Tip != u3 {
		t.Fatalf("the tip must be the user's current tip %d, got %v: %s", u3, page.Tip, body)
	}
	t.Logf("OBSERVED the page: count = %d, after = %s, tip = %s, task ids = %v",
		page.Count, ledgerPgNum(page.After), ledgerPgNum(page.Tip), ledgerPgTaskIDs(page.Events))

	seen := map[string]bool{}
	previous := int64(0)
	order := []int64{}
	for _, e := range page.Events {
		got, ok := e["user_seq"].(float64)
		if !ok {
			t.Fatalf("an event carries no user_seq, so the cursor cannot be taken from it: %v", e)
		}
		if int64(got) <= previous {
			t.Fatalf("the page is not ordered by user_seq: %d follows %d (%s)", int64(got), previous, body)
		}
		previous = int64(got)
		order = append(order, int64(got))
		seen[e["task_id"].(string)] = true
	}
	if !seen[first] || !seen[second] {
		t.Fatalf("the cursor must cross ALL of the user's tasks: got task ids %v, want %q and %q",
			ledgerPgTaskIDs(page.Events), first, second)
	}
	// The three seeded entries appear in the order they were written, which is the order their
	// user_seq numbers were taken in - the interleaving is what proves the cursor is not per task.
	at := 0
	for _, want := range []int64{u1, u2, u3} {
		for at < len(order) && order[at] != want {
			at++
		}
		if at == len(order) {
			t.Fatalf("the entry at user_seq %d is missing or out of order in %v: %s", want, order, body)
		}
		at++
	}

	// The same after, asked twice, is the same page and the same tip - byte for byte, because a
	// reader that answered differently for one cursor would be a reader a client cannot resume.
	code2, body2 := ledgerPgGet(t, app, token, "?after=0")
	if code2 != http.StatusOK || body2 != body {
		t.Fatalf("the same after asked twice must answer the same bytes:\nfirst  = %s\nsecond = %s", body, body2)
	}

	// after=<user_seq> is strictly-after: the first entry is not repeated.
	code3, body3 := ledgerPgGet(t, app, token, fmt.Sprintf("?after=%d", u1))
	if code3 != http.StatusOK {
		t.Fatalf("GET /api/v2/ledger?after=%d = %d: %s", u1, code3, body3)
	}
	page3 := ledgerPgDecodePage(t, body3)
	if page3.Count != 2 {
		t.Fatalf("after=%d must return the two entries that follow it, got %d: %s", u1, page3.Count, body3)
	}
	for _, e := range page3.Events {
		if int64(e["user_seq"].(float64)) <= u1 {
			t.Fatalf("after=%d returned an entry at or before the cursor: %v", u1, e)
		}
	}

	// The contrast: O1a's per-task route does NOT cross tasks. This is the difference the box calls
	// the whole point of P2.
	code4, body4 := evidenceEventsGet(t, app, token, first)
	if code4 != http.StatusOK {
		t.Fatalf("GET /api/v2/tasks/{id}/events = %d: %s", code4, body4)
	}
	var perTask struct {
		Events []map[string]any `json:"events"`
	}
	if err := json.Unmarshal([]byte(body4), &perTask); err != nil {
		t.Fatalf("decoding the per-task read: %v (%s)", err, body4)
	}
	if len(perTask.Events) == 0 {
		t.Fatalf("the per-task read returned no entries for %s: %s", first, body4)
	}
	for _, e := range perTask.Events {
		if e["task_id"] != first {
			t.Fatalf("the per-task read returned task %v, not %q: %s", e["task_id"], first, body4)
		}
	}
	if strings.Contains(body4, second) {
		t.Fatalf("the per-task read must not carry the OTHER task (%s): %s", second, body4)
	}

	// Another user's credential returns none of the first user's rows.
	tokenB, userB := evidenceUser(t, ledgerPgSubjectB)
	code5, body5 := ledgerPgGet(t, app, tokenB, "")
	if code5 != http.StatusOK {
		t.Fatalf("GET /api/v2/ledger for the second user = %d: %s", code5, body5)
	}
	pageB := ledgerPgDecodePage(t, body5)
	if pageB.Tip == nil || *pageB.Tip != ledgerPgTip(t, sm, userB) {
		t.Fatalf("the second user's tip must be their own (%d), got %v: %s",
			ledgerPgTip(t, sm, userB), pageB.Tip, body5)
	}
	for _, e := range pageB.Events {
		if id := e["task_id"].(string); id == first || id == second {
			t.Fatalf("the second user's credential returned the first user's rows: %s", body5)
		}
		if int64(e["user_seq"].(float64)) <= u3 {
			t.Fatalf("the second user's page carries a user_seq from the first user's cursor: %s", body5)
		}
	}
	t.Logf("OBSERVED the second user's page: count = %d, tip = %s", pageB.Count, ledgerPgNum(pageB.Tip))
}

func ledgerPgTaskIDs(events []map[string]any) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, e := range events {
		id, _ := e["task_id"].(string)
		if !seen[id] {
			seen[id] = true
			out = append(out, id)
		}
	}
	return out
}

// --- P3: the intents route ---

// TestLedgerIntentsOneBatchDecidesEachItemAndAnswersTheResendFromItsRow is P3's check: one batch
// carrying an acceptable fact, a stale decision and a duplicate id yields exactly one accept, one
// rejection with its reason and the current task_seq, and the original answer returned byte for
// byte rather than a second row.
func TestLedgerIntentsOneBatchDecidesEachItemAndAnswersTheResendFromItsRow(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectC)
	task := ledgerPgTask(t, app, sm, token, user, "ledger P3 batch task")

	// One accepted decision first, so the task's history holds a DECISION the next one can be stale
	// against. Two are staged because the first may land on a task that already carries an entry of
	// another kind; what the case needs is a decision at the task's tip.
	stagedID := value_objects.NewUUIDv4()
	code, body := ledgerPgPostOne(t, app, token, stagedID, task, "claimed", new(0))
	if code != http.StatusOK {
		t.Fatalf("staging a decision = %d: %s", code, body)
	}
	staged := ledgerPgDecodeAnswers(t, body)
	if len(staged) != 1 || staged[0].Accepted == nil || !*staged[0].Accepted {
		t.Fatalf("the staged decision must be accepted, got %s", body)
	}
	tip := ledgerPgTaskSeq(t, sm, user, task)

	before := ledgerPgRowCount(t, sm, user)
	factID := value_objects.NewUUIDv4()
	staleID := value_objects.NewUUIDv4()
	batch, err := json.Marshal([]map[string]any{
		ledgerPgIntent(factID, task, "progress", nil),
		ledgerPgIntent(staleID, task, "claimed", new(tip-1)),
		ledgerPgIntent(factID, task, "progress", nil),
	})
	if err != nil {
		t.Fatalf("building the batch: %v", err)
	}
	code, body = ledgerPgPostIntents(t, app, token, string(batch))
	if code != http.StatusOK {
		t.Fatalf("POST /api/v2/ledger/intents = %d, want 200: %s", code, body)
	}
	raw := ledgerPgRawAnswers(t, body)
	if len(raw) != 3 {
		t.Fatalf("the route must answer PER ITEM: got %d answers for 3 items: %s", len(raw), body)
	}
	answers := ledgerPgDecodeAnswers(t, body)

	// 1) the acceptable fact is accepted, with the sequence numbers it took.
	if answers[0].Accepted == nil || !*answers[0].Accepted || answers[0].UserSeq == nil || answers[0].Seq == nil {
		t.Fatalf("the fact must be accepted with a user_seq and a seq, got %s", raw[0])
	}
	if answers[1].UserSeq != nil || answers[1].Seq != nil {
		t.Fatalf("a rejected item must not carry sequence numbers, got %s", raw[1])
	}
	// 2) the stale decision is rejected with its reason and the task's seq as it stands NOW.
	if answers[1].Rejected == nil || !*answers[1].Rejected {
		t.Fatalf("the stale decision must be rejected, got %s", raw[1])
	}
	if answers[1].Reason == nil || *answers[1].Reason == "" {
		t.Fatalf("a rejection must name its reason, got %s", raw[1])
	}
	current := ledgerPgTaskSeq(t, sm, user, task)
	if answers[1].TaskSeq == nil || *answers[1].TaskSeq != current {
		t.Fatalf("a rejection must carry the task's current seq %d, got %s", current, raw[1])
	}
	// 3) the duplicate returns the FIRST answer, byte for byte, rather than a second row.
	if raw[2] != raw[0] {
		t.Fatalf("a resent client_event_id must return the first answer byte for byte:\nfirst = %s\nagain = %s", raw[0], raw[2])
	}
	after := ledgerPgRowCount(t, sm, user)
	if after-before != 1 {
		t.Fatalf("the batch must write exactly ONE row (the fact); it wrote %d", after-before)
	}
	t.Logf("OBSERVED the batch: %s -> answers %s, rows %d -> %d", string(batch), body, before, after)
}

// TestLedgerIntentsStaleDecisionSucceedsOnceTheClientReReads is P3's second check: a decision staged
// on a stale base succeeds once the client re-reads. The re-read is the P2 cursor, so the two routes
// are exercised as the one loop D9 describes.
//
// IT ALSO PINS A DELIBERATE ASYMMETRY: a rejection is NOT memoised, which is what lets the resend
// above succeed at all. Only an ACCEPTED intent is remembered - by the row it wrote, keyed on
// (user_id, client_event_id) - and that is what "resending returns the first answer" protects: the
// client cannot append its fact twice. A refused decision wrote nothing, so re-staging it is the
// client's whole remedy, and the same client_event_id is answered freshly.
func TestLedgerIntentsStaleDecisionSucceedsOnceTheClientReReads(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectA)
	task := ledgerPgTask(t, app, sm, token, user, "ledger P3 stale base task")

	stagedID := value_objects.NewUUIDv4()
	if code, body := ledgerPgPostOne(t, app, token, stagedID, task, "claimed", new(0)); code != http.StatusOK {
		t.Fatalf("staging a decision = %d: %s", code, body)
	}
	tip := ledgerPgTaskSeq(t, sm, user, task)

	decisionID := value_objects.NewUUIDv4()
	code, body := ledgerPgPostOne(t, app, token, decisionID, task, "status_changed", new(tip-1))
	if code != http.StatusOK {
		t.Fatalf("the stale decision = %d: %s", code, body)
	}
	stale := ledgerPgDecodeAnswers(t, body)[0]
	if stale.Rejected == nil || !*stale.Rejected || stale.TaskSeq == nil || *stale.TaskSeq != tip {
		t.Fatalf("the decision on the stale base must be rejected with the task's current seq %d, got %s", tip, body)
	}
	rows := ledgerPgRowCount(t, sm, user)

	// A resend BEFORE the re-read answers the same rejection: nothing was written to remember, and
	// the ledger has not moved, so the decision comes out the same.
	code, again := ledgerPgPostOne(t, app, token, decisionID, task, "status_changed", new(tip-1))
	if code != http.StatusOK || again != body {
		t.Fatalf("a resend with an unchanged ledger must answer the same bytes:\nfirst = %s\nagain = %s", body, again)
	}

	// The client re-reads through the cursor, and takes the task's latest seq from it.
	code, page := ledgerPgGet(t, app, token, "")
	if code != http.StatusOK {
		t.Fatalf("the re-read = %d: %s", code, page)
	}
	fresh := 0
	for _, e := range ledgerPgDecodePage(t, page).Events {
		if e["task_id"] != task {
			continue
		}
		if seq, ok := e["seq"].(float64); ok && int(seq) > fresh {
			fresh = int(seq)
		}
	}
	if fresh != tip {
		t.Fatalf("the cursor must carry the task's latest seq %d, read %d: %s", tip, fresh, page)
	}

	// Staged again on the base it just read, the SAME client_event_id is accepted.
	code, body = ledgerPgPostOne(t, app, token, decisionID, task, "status_changed", new(fresh))
	if code != http.StatusOK {
		t.Fatalf("the re-staged decision = %d: %s", code, body)
	}
	fresh_answer := ledgerPgDecodeAnswers(t, body)[0]
	if fresh_answer.Accepted == nil || !*fresh_answer.Accepted {
		t.Fatalf("a decision on the base the client just read must be accepted, got %s", body)
	}
	if *fresh_answer.Seq != fresh+1 {
		t.Fatalf("the accepted decision must take the next seq (%d), got %s", fresh+1, body)
	}
	if got := ledgerPgRowCount(t, sm, user); got != rows+1 {
		t.Fatalf("the accepted decision must add exactly one row: %d -> %d", rows, got)
	}
}

// TestLedgerIntentsRecordsOfflineFactsUnchangedInArrivalOrder is P3's third check: a fact recorded
// offline is accepted unchanged, in arrival order. "Unchanged" is D9's own rule - the server keeps
// the client's time in the payload and adds nothing - and "arrival order" is the order of the
// array, which is the order the sequences were taken in.
func TestLedgerIntentsRecordsOfflineFactsUnchangedInArrivalOrder(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectB)
	task := ledgerPgTask(t, app, sm, token, user, "ledger P3 offline facts task")

	firstID := value_objects.NewUUIDv4()
	secondID := value_objects.NewUUIDv4()
	offline := []map[string]any{
		{
			"client_event_id": firstID,
			"task_id":         task,
			"kind":            "progress",
			"payload": map[string]any{
				"note": "recorded while the cloud was unreachable",
				"at":   "2026-10-10T21:00:00Z",
			},
		},
		{
			"client_event_id": secondID,
			"task_id":         task,
			"kind":            "handover",
			"payload": map[string]any{
				"at":     "2026-10-10T21:05:00Z",
				"next":   "read the ledger from these two entries",
				"nested": map[string]any{"n": float64(2), "flag": true},
			},
		},
	}
	body, err := json.Marshal(offline)
	if err != nil {
		t.Fatalf("building the batch: %v", err)
	}
	code, answer := ledgerPgPostIntents(t, app, token, string(body))
	if code != http.StatusOK {
		t.Fatalf("POST /api/v2/ledger/intents = %d: %s", code, answer)
	}
	answers := ledgerPgDecodeAnswers(t, answer)
	if len(answers) != 2 || answers[0].Accepted == nil || !*answers[0].Accepted ||
		answers[1].Accepted == nil || !*answers[1].Accepted {
		t.Fatalf("a fact is append-only and is never refused for being late: %s", answer)
	}
	if *answers[1].UserSeq <= *answers[0].UserSeq || *answers[1].Seq <= *answers[0].Seq {
		t.Fatalf("the batch must be recorded in ARRIVAL order, got %s", answer)
	}

	// Read back through the cursor and compare the payloads with what was sent, key for key.
	code, page := ledgerPgGet(t, app, token, fmt.Sprintf("?after=%d", *answers[0].UserSeq-1))
	if code != http.StatusOK {
		t.Fatalf("the read-back = %d: %s", code, page)
	}
	byClientID := map[string]map[string]any{}
	for _, e := range ledgerPgDecodePage(t, page).Events {
		payload, _ := e["payload"].(map[string]any)
		if payload == nil {
			continue
		}
		if e["kind"] == "progress" && payload["note"] == "recorded while the cloud was unreachable" {
			byClientID[firstID] = payload
		}
		if e["kind"] == "handover" && payload["next"] == "read the ledger from these two entries" {
			byClientID[secondID] = payload
		}
	}
	for id, want := range map[string]map[string]any{firstID: offline[0]["payload"].(map[string]any), secondID: offline[1]["payload"].(map[string]any)} {
		got, ok := byClientID[id]
		if !ok {
			t.Fatalf("the fact %s is not readable through the cursor: %s", id, page)
		}
		wantJSON, _ := json.Marshal(want)
		gotJSON, _ := json.Marshal(got)
		if string(wantJSON) != string(gotJSON) {
			t.Fatalf("the payload must be stored UNCHANGED:\nsent     = %s\nread back = %s", wantJSON, gotJSON)
		}
	}
}

// TestLedgerIntentsRefusesAnUnusableCredentialLikeTheLedgerRead is the guard check: an intent route
// with a guard of its own would show up here as a disagreement with the read beside it.
func TestLedgerIntentsRefusesAnUnusableCredentialLikeTheLedgerRead(t *testing.T) {
	app, _ := evidenceApp(t)
	// A minted token sets the JWT secret the validator needs, and it gives the test the one probe
	// that proves the guard can be passed at all - the same shape the evidence route's guard case
	// uses, because a bad credential and an unconfigured validator are different failures (401 and
	// 500) and only the first is a claim about the guard.
	token, _ := evidenceUser(t, ledgerPgSubjectC)
	const taskID = "e1d0c9b8-1111-4111-8111-0000000000a1"
	body, err := json.Marshal([]map[string]any{ledgerPgIntent(value_objects.NewUUIDv4(), taskID, "progress", nil)})
	if err != nil {
		t.Fatalf("building the request: %v", err)
	}

	noCredCode, noCredBody := ledgerPgPostIntents(t, app, "", string(body))
	noCredRead, _ := ledgerPgGet(t, app, "", "")
	badCredCode, badCredBody := ledgerPgPostIntents(t, app, "not-a-token", string(body))
	badCredRead, _ := ledgerPgGet(t, app, "not-a-token", "")
	validCode, validBody := ledgerPgPostIntents(t, app, token, string(body))
	validRead, validReadBody := ledgerPgGet(t, app, token, "")
	t.Logf("OBSERVED no credential: POST /intents -> %d %s | GET /ledger -> %d", noCredCode, noCredBody, noCredRead)
	t.Logf("OBSERVED an invalid credential: POST /intents -> %d %s | GET /ledger -> %d", badCredCode, badCredBody, badCredRead)
	t.Logf("OBSERVED a valid credential: POST /intents -> %d %s | GET /ledger -> %d %s", validCode, validBody, validRead, validReadBody)

	if badCredCode != http.StatusUnauthorized {
		t.Fatalf("an unusable credential must answer 401 from the existing guard, got %d: %s", badCredCode, badCredBody)
	}
	if noCredCode != noCredRead || badCredCode != badCredRead {
		t.Fatalf("both ledger routes must be guarded by the SAME wrapper: intents %d/%d, ledger %d/%d",
			noCredCode, badCredCode, noCredRead, badCredRead)
	}
	if noCredCode == http.StatusOK || badCredCode == http.StatusOK {
		t.Fatalf("a refused credential reached a ledger handler: no-credential %d, bad-credential %d", noCredCode, badCredCode)
	}

	// A real credential passes the guard, which is what makes the refusals above a claim about the
	// guard rather than about a route that never runs. The task does not exist, so the item is
	// refused per item rather than the request failing: that is the route's contract.
	if validCode != http.StatusOK {
		t.Fatalf("a valid credential must reach the handler, got %d: %s", validCode, validBody)
	}
	answer := ledgerPgDecodeAnswers(t, validBody)[0]
	if answer.Rejected == nil || !*answer.Rejected || answer.Reason == nil || *answer.Reason != "unknown_task" {
		t.Fatalf("a task this user cannot see must be refused per item with unknown_task, got %s", validBody)
	}
	if validRead != http.StatusOK {
		t.Fatalf("a valid credential must reach the ledger read, got %d: %s", validRead, validReadBody)
	}
	if page := ledgerPgDecodePage(t, validReadBody); page.Count != 0 {
		t.Fatalf("a user with no entries must get an empty page, got %s", validReadBody)
	}
}

// --- the subtask reference the contract names, and the body that is not a list ---

// ledgerPgSubtask inserts one subtask of taskID owned by userID and returns its id. Written straight
// into the table for the reason ledgerPgSeedEvent is: these cases are about the ledger's check, and a
// fixture written through the subtask routes would make them cases about those routes too.
//
// The two progress columns this row used to name (progress_history, progress_count) are gone from the
// table by the time these cases run - the ledger line's carry step drops them - so naming them here
// makes the fixture a case about the schema rather than about the check.
func ledgerPgSubtask(t *testing.T, sm *database.SessionManager, userID, taskID, title string) string {
	t.Helper()
	id := value_objects.NewUUIDv4()
	ledgerExec(t, sm, `INSERT INTO subtasks
		(id, task_id, title, description, status, priority, assignees, progress_percentage, progress_state,
		 progress_notes, blockers, completion_summary, impact_on_parent, insights_found, user_id,
		 created_at, updated_at)
		VALUES ($1::uuid, $2::uuid, $3, '', 'todo', 'medium', '[]'::json, 0, 'INITIAL',
		        '', '', '', '', '[]'::json, $4::varchar, now(), now())`,
		id, taskID, title, userID)
	return id
}

// ledgerPgIntentWithSubtask is ledgerPgIntent with the reference this case exists to send: a route
// case that never posts a non-null subtask_id is exactly the gap this row closes.
func ledgerPgIntentWithSubtask(clientEventID, taskID, kind, subtaskID string) map[string]any {
	item := ledgerPgIntent(clientEventID, taskID, kind, nil)
	item["subtask_id"] = subtaskID
	return item
}

// ledgerPgRowSubtask reads the subtask_id of the row one client_event_id wrote, so "the accepted row
// carries the subtask the intent named" is a claim about a row rather than about an answer.
func ledgerPgRowSubtask(t *testing.T, sm *database.SessionManager, userID, clientEventID string) string {
	t.Helper()
	subtask := ""
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT COALESCE("subtask_id"::text, '') FROM task_events
				WHERE "user_id" = $1::varchar AND "client_event_id" = $2::uuid`,
			userID, clientEventID).Scan(&subtask)
	}); err != nil {
		t.Fatalf("reading the row's subtask: %v", err)
	}
	return subtask
}

// TestLedgerIntentsRefusesASubtaskThatIsNotThisTasksOwn is the ledger MAJOR of GATE 1a370e02..4f86a1ac:
// an intent may name a subtask, and task_events' only foreign key is on task_id, so before this check
// the row landed whatever the id named - another user's subtask, or one of a different task.
//
// THE SHAPES ARE ONE CASE because the token must not tell them apart: the FALSIFICATION first (this
// task's own subtask is accepted, and the ROW carries it), then the three references that are not
// this task's, which must all answer the SAME reason - a response that distinguished "no such
// subtask" from "not yours" would answer whether a subtask exists to a user who cannot see it.
func TestLedgerIntentsRefusesASubtaskThatIsNotThisTasksOwn(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectA)
	otherToken, otherUser := evidenceUser(t, ledgerPgSubjectB)

	task := ledgerPgTask(t, app, sm, token, user, "ledger subtask task")
	sibling := ledgerPgTask(t, app, sm, token, user, "ledger subtask sibling task")

	// The other user needs a project and a branch of their OWN: evidenceSeedBranch writes its two rows
	// under fixed ids for whichever user asks first, and a task validated against another user's
	// branch is refused by the task route before this case can say anything about the ledger.
	otherProject, otherBranch := value_objects.NewUUIDv4(), value_objects.NewUUIDv4()
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1::uuid,'ledger other project','',now(),now(),$2,'active','{}')`, otherProject, otherUser)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1::uuid,$2::uuid,'ledger other branch','',now(),now(),'medium','todo','{}',0,0,$3)`,
		otherBranch, otherProject, otherUser)
	code, foreign, body := taskCreate(t, app, otherToken, "ledger subtask other user task", otherBranch)
	if code != http.StatusOK || foreign == "" {
		t.Fatalf("the other user's task: POST /api/v2/tasks/ = %d, id = %q: %s", code, foreign, body)
	}

	mine := ledgerPgSubtask(t, sm, user, task, "this task's subtask")
	stranger := ledgerPgSubtask(t, sm, otherUser, foreign, "another user's subtask")
	elsewhere := ledgerPgSubtask(t, sm, user, sibling, "a sibling task's subtask")

	acceptedID := value_objects.NewUUIDv4()
	request, err := json.Marshal([]map[string]any{ledgerPgIntentWithSubtask(acceptedID, task, "progress", mine)})
	if err != nil {
		t.Fatalf("building the request: %v", err)
	}
	code, acceptedBody := ledgerPgPostIntents(t, app, token, string(request))
	if code != http.StatusOK {
		t.Fatalf("POST /api/v2/ledger/intents = %d, want 200: %s", code, acceptedBody)
	}
	accepted := ledgerPgDecodeAnswers(t, acceptedBody)[0]
	if accepted.Accepted == nil || !*accepted.Accepted {
		t.Fatalf("a subtask of THIS task must be accepted, got %s", acceptedBody)
	}
	if got := ledgerPgRowSubtask(t, sm, user, acceptedID); got != mine {
		t.Fatalf("the accepted row must carry the subtask the intent named: got %q, want %q", got, mine)
	}

	for _, c := range []struct {
		name    string
		subtask string
	}{
		{"an unknown subtask", value_objects.NewUUIDv4()},
		{"another user's subtask", stranger},
		{"a subtask of a different task", elsewhere},
	} {
		t.Run(c.name, func(t *testing.T) {
			id := value_objects.NewUUIDv4()
			body, err := json.Marshal([]map[string]any{ledgerPgIntentWithSubtask(id, task, "progress", c.subtask)})
			if err != nil {
				t.Fatalf("building the request: %v", err)
			}
			rows := ledgerPgRowCount(t, sm, user)
			code, refusedBody := ledgerPgPostIntents(t, app, token, string(body))
			if code != http.StatusOK {
				t.Fatalf("POST /api/v2/ledger/intents = %d, want 200 (a refusal is a per-item answer): %s", code, refusedBody)
			}
			answer := ledgerPgDecodeAnswers(t, refusedBody)[0]
			if answer.Rejected == nil || !*answer.Rejected {
				t.Fatalf("a subtask that is not this task's own must be refused, got %s", refusedBody)
			}
			if answer.Reason == nil || *answer.Reason != "unknown_subtask" {
				t.Fatalf("the refusal must be unknown_subtask, got %s", refusedBody)
			}
			if answer.UserSeq != nil || answer.Seq != nil {
				t.Fatalf("a refused item must not carry sequence numbers, got %s", refusedBody)
			}
			if after := ledgerPgRowCount(t, sm, user); after != rows {
				t.Fatalf("a refused item must write no row: %d -> %d", rows, after)
			}
			t.Logf("OBSERVED %s -> %s", c.name, refusedBody)
		})
	}
	t.Logf("OBSERVED the accepted subtask: %s", acceptedBody)
}

// TestLedgerIntentsRefusesABodyThatIsNotAList pins the mount's own guard: `null` and `[]` decode into
// the same nil slice, so the route answered 200 [] for a body that is not a list at all while its
// comment claimed the 422 it already answers for `{}`. The body is decoded into a POINTER now, nil
// only for `null`, and what the route accepts is otherwise unchanged: an empty list is still a list.
func TestLedgerIntentsRefusesABodyThatIsNotAList(t *testing.T) {
	app, _ := evidenceApp(t)
	token, _ := evidenceUser(t, ledgerPgSubjectC)

	for _, c := range []struct {
		name string
		body string
		want int
	}{
		{"a literal null is not a list", "null", http.StatusUnprocessableEntity},
		{"an object is not a list", "{}", http.StatusUnprocessableEntity},
		{"malformed JSON is not a list", "[", http.StatusUnprocessableEntity},
		{"an empty list is a list", "[]", http.StatusOK},
	} {
		t.Run(c.name, func(t *testing.T) {
			code, body := ledgerPgPostIntents(t, app, token, c.body)
			if code != c.want {
				t.Fatalf("POST /api/v2/ledger/intents body %s = %d, want %d: %s", c.body, code, c.want, body)
			}
			if c.want == http.StatusOK && strings.TrimSpace(body) != "[]" {
				t.Fatalf("an empty list must answer the empty list of answers, got %s", body)
			}
			t.Logf("OBSERVED body %s -> %d %s", c.body, code, strings.TrimSpace(body))
		})
	}
}

// --- P4: the nudge ---

// TestLedgerTipArrivesAfterADecisionCommitsAndTheNextPullAdvancesTheCursor is P4's middle check: with
// the socket open the frame arrives after a decision commits, and the pull that follows it is what
// moves the client's cursor. The frame is addressed per user, so the socket is opened for the subject
// the request authenticates as - the one the ledger's writer is handed.
func TestLedgerTipArrivesAfterADecisionCommitsAndTheNextPullAdvancesTheCursor(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectA)
	task := ledgerPgTask(t, app, sm, token, user, "ledger P4 tip task")

	env := newStreamEnv(t, sm)
	c := env.connector(t, user)
	c.rigdHello(t, "rigd-p4", connectorCapabilityIngest, connectorCapabilityLedger)

	// The cursor the client holds, read the way a client reads it.
	code, body := ledgerPgGet(t, app, token, "")
	if code != http.StatusOK {
		t.Fatalf("the read before the decision = %d: %s", code, body)
	}
	cursor := ledgerPgDecodePage(t, body).Tip
	if cursor == nil {
		t.Fatalf("a read must carry a tip, got %s", body)
	}

	// Nothing is pushed on a timer: before the commit this socket hears nothing at all.
	_ = c.conn.SetReadDeadline(time.Now().Add(700 * time.Millisecond))
	if opcode, payload, err := wsTryReadFrame(c.br); err == nil {
		t.Fatalf("the socket received opcode=%d payload=%q before any commit, want nothing", opcode, payload)
	}
	_ = c.conn.SetReadDeadline(time.Now().Add(5 * time.Second))

	// A DECISION, formed against the task's current seq.
	base := ledgerPgTaskSeq(t, sm, user, task)
	code, body = ledgerPgPostOne(t, app, token, value_objects.NewUUIDv4(), task, "status_changed", new(base))
	if code != http.StatusOK {
		t.Fatalf("the decision = %d: %s", code, body)
	}
	answer := ledgerPgDecodeAnswers(t, body)[0]
	if answer.Accepted == nil || !*answer.Accepted || answer.UserSeq == nil {
		t.Fatalf("the decision must be accepted and name the user_seq it took, got %s", body)
	}

	// The frame, and WHICH number it carries: the tip the commit took.
	tip := c.recv()
	if tip["type"] != connectorLedgerTipFrame {
		t.Fatalf("the entitled socket received %v, want %s", tip, connectorLedgerTipFrame)
	}
	if tip["user_seq"] != float64(*answer.UserSeq) {
		t.Errorf("ledger_tip.user_seq = %v, want the user_seq the commit took (%d)", tip["user_seq"], *answer.UserSeq)
	}

	// And the pull the nudge is FOR: from the cursor the client held, the committed entry comes back
	// and the tip has moved past that cursor. The frame was a reason to pull, never the cursor.
	code, body = ledgerPgGet(t, app, token, "?after="+strconv.FormatInt(*cursor, 10))
	if code != http.StatusOK {
		t.Fatalf("the pull after the nudge = %d: %s", code, body)
	}
	page := ledgerPgDecodePage(t, body)
	if page.Count == 0 {
		t.Fatalf("the pull from cursor %d returned nothing, so the nudge pointed at an entry the pull cannot see: %s", *cursor, body)
	}
	if page.Tip == nil || *page.Tip < *answer.UserSeq {
		t.Fatalf("the pull's tip %s must have moved to at least the committed user_seq %d: %s",
			ledgerPgNum(page.Tip), *answer.UserSeq, body)
	}
	found := false
	for _, e := range page.Events {
		if seq, ok := e["user_seq"].(float64); ok && int64(seq) == *answer.UserSeq {
			found = true
		}
	}
	if !found {
		t.Fatalf("the entry the decision wrote (user_seq %d) is not in the pull: %s", *answer.UserSeq, body)
	}
	t.Logf("OBSERVED cursor %d -> ledger_tip user_seq=%v -> pull count=%d tip=%s",
		*cursor, tip["user_seq"], page.Count, ledgerPgNum(page.Tip))
}

// TestAClientWithNoSocketStillConvergesByPulling is P4's first check, and it is the one the frame is
// subordinate to: NO connector socket exists in this case at all, and the ledger still converges
// because the client's own GET from its cursor is the whole mechanism.
func TestAClientWithNoSocketStillConvergesByPulling(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectA)
	task := ledgerPgTask(t, app, sm, token, user, "ledger P4 pull-only task")

	code, body := ledgerPgGet(t, app, token, "")
	if code != http.StatusOK {
		t.Fatalf("the read before the decision = %d: %s", code, body)
	}
	cursor := ledgerPgDecodePage(t, body).Tip
	if cursor == nil {
		t.Fatalf("a read must carry a tip, got %s", body)
	}

	base := ledgerPgTaskSeq(t, sm, user, task)
	code, body = ledgerPgPostOne(t, app, token, value_objects.NewUUIDv4(), task, "status_changed", new(base))
	if code != http.StatusOK {
		t.Fatalf("the decision = %d: %s", code, body)
	}
	answer := ledgerPgDecodeAnswers(t, body)[0]
	if answer.Accepted == nil || !*answer.Accepted || answer.UserSeq == nil {
		t.Fatalf("the decision must be accepted and name the user_seq it took, got %s", body)
	}

	// No socket was opened and nothing was notified. The pull alone has to carry the client.
	code, body = ledgerPgGet(t, app, token, "?after="+strconv.FormatInt(*cursor, 10))
	if code != http.StatusOK {
		t.Fatalf("the pull = %d: %s", code, body)
	}
	page := ledgerPgDecodePage(t, body)
	if page.Count != 1 {
		t.Fatalf("the pull from cursor %d must return exactly the committed entry, got %d: %s", *cursor, page.Count, body)
	}
	if seq, ok := page.Events[0]["user_seq"].(float64); !ok || int64(seq) != *answer.UserSeq {
		t.Fatalf("the pulled entry must be the one the commit wrote (user_seq %d): %s", *answer.UserSeq, body)
	}
	if page.Tip == nil || *page.Tip != *answer.UserSeq {
		t.Fatalf("the tip after the pull = %s, want the committed user_seq %d: %s",
			ledgerPgNum(page.Tip), *answer.UserSeq, body)
	}
	t.Logf("OBSERVED pull-only: cursor %d -> committed user_seq %d -> pull count=%d tip=%s",
		*cursor, *answer.UserSeq, page.Count, ledgerPgNum(page.Tip))
}

// TestALedgerBatchThatAcceptedNothingNudgesNobody is the guard on the nudge ITSELF, and it is the one
// branch a mutation can otherwise delete without a red: `ledgerAcceptedTip` answering `return tip,
// true` - the reviewer's M2 - leaves every other case in this file GREEN, because all of them commit
// at least one accepted item. The property is asserted as an OUTCOME, not as an expression: an
// entitled socket receives NOTHING when the batch accepted nothing, and the very next batch that DOES
// commit is nudged on that same socket, so the silence is the guard's doing rather than a socket that
// cannot hear.
//
// The all-refused batch is a decision on a STALE base_seq: the request still answers 200, the item is
// refused, no row and no user_seq are written, and the tip does not move. A nudge here would send a
// client to pull a ledger that has nothing new in it.
func TestALedgerBatchThatAcceptedNothingNudgesNobody(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, ledgerPgSubjectA)
	task := ledgerPgTask(t, app, sm, token, user, "ledger P4 all-refused batch task")

	// A first decision so the task has a seq the second one can be stale against. It COMMITS, so it
	// nudges, and it is posted BEFORE the socket opens: a frame left in the buffer would otherwise be
	// read below as the refused batch's own.
	if code, body := ledgerPgPostOne(t, app, token, value_objects.NewUUIDv4(), task, "claimed", new(0)); code != http.StatusOK {
		t.Fatalf("staging a decision = %d: %s", code, body)
	}
	seq := ledgerPgTaskSeq(t, sm, user, task)
	rows := ledgerPgRowCount(t, sm, user)
	tip := ledgerPgTip(t, sm, user)

	env := newStreamEnv(t, sm)
	c := env.connector(t, user)
	c.rigdHello(t, "rigd-p4-noop", connectorCapabilityIngest, connectorCapabilityLedger)

	// The batch that accepts nothing: refused on its base_seq, and the request still answers 200.
	code, body := ledgerPgPostOne(t, app, token, value_objects.NewUUIDv4(), task, "status_changed", new(seq-1))
	if code != http.StatusOK {
		t.Fatalf("the stale decision = %d: %s", code, body)
	}
	refused := ledgerPgDecodeAnswers(t, body)[0]
	if refused.Rejected == nil || !*refused.Rejected {
		t.Fatalf("this case needs a batch that accepted nothing, got %s", body)
	}
	if got := ledgerPgTip(t, sm, user); got != tip {
		t.Fatalf("a refused batch must not move the tip: %d -> %d", tip, got)
	}
	if got := ledgerPgRowCount(t, sm, user); got != rows {
		t.Fatalf("a refused batch must not write a row: %d -> %d", rows, got)
	}

	// The OUTCOME: no frame at all on a socket that is entitled to them.
	_ = c.conn.SetReadDeadline(time.Now().Add(700 * time.Millisecond))
	if opcode, payload, err := wsTryReadFrame(c.br); err == nil {
		t.Fatalf("an entitled socket received opcode=%d payload=%q when the batch accepted nothing, want nothing", opcode, payload)
	}
	_ = c.conn.SetReadDeadline(time.Now().Add(5 * time.Second))

	// And it is not merely deaf: the next batch that commits is nudged here, with its own user_seq.
	code, body = ledgerPgPostOne(t, app, token, value_objects.NewUUIDv4(), task, "status_changed", new(seq))
	if code != http.StatusOK {
		t.Fatalf("the accepted decision = %d: %s", code, body)
	}
	accepted := ledgerPgDecodeAnswers(t, body)[0]
	if accepted.Accepted == nil || !*accepted.Accepted || accepted.UserSeq == nil {
		t.Fatalf("a decision on the base the task is at must be accepted, got %s", body)
	}
	nudge := c.recv()
	if nudge["type"] != connectorLedgerTipFrame {
		t.Fatalf("after a committing batch the entitled socket received %v, want %s", nudge, connectorLedgerTipFrame)
	}
	if nudge["user_seq"] != float64(*accepted.UserSeq) {
		t.Errorf("ledger_tip.user_seq = %v, want the user_seq that commit took (%d)", nudge["user_seq"], *accepted.UserSeq)
	}
	t.Logf("OBSERVED refused batch: rows %d tip %d unchanged and no frame -> then the commit's user_seq=%d arrived as %v",
		rows, tip, *accepted.UserSeq, nudge["user_seq"])
}
