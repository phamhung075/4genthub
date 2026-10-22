package httpapp

// The ledger has ONE evidence writer: the evidence controller. POST /api/v2/ledger/intents must refuse
// `evidence_submitted` with the per-item reason `unsupported_kind` and append nothing.
//
// WHY THIS IS A ROUTE CASE AND NOT ONLY A VOCABULARY PIN: a fact intent owes no base_seq and reaches
// no comparison (ledger_service.go's `if in.Kind.IsFact()`), and lastEvidence (task_event_controller.go)
// reads the task's LATEST evidence row whatever writer made it. While the kind was pushable, a batch
// could therefore land a weak account of a head_sha that a named row already owned, and the next
// evidence POST would compare against that weak row instead: the 409 that keeps a head's account fixed
// was bypassed by the ledger's second writer. Measured by the reviewer while gating 82ea7ecd..5329e1d4
// (three steps, 201/200/201 at the branch tip). The domain test beside intent.go pins the vocabulary;
// this file pins the answer a caller actually receives, at a head whose latest row NAMES a command and
// at a head with no row at all, because "the refusal does not depend on what the head holds".
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and for the same reason:
// "appends nothing" is a claim about ROWS.
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// evidenceIntentSubjects are the callers, one per case, so no case reads a seq another's setup moved.
const (
	evidenceIntentNamedSubject    = "b1e0d3c2-2222-4222-8222-00000000001a"
	evidenceIntentEmptySubject    = "b1e0d3c2-2222-4222-8222-00000000001b"
	evidenceIntentDecisionSubject = "b1e0d3c2-2222-4222-8222-00000000001c"
)

// evidenceIntentPost submits an evidence_submitted FACT intent naming no test object - the payload the
// reviewer's probe planted - and returns the status code and body. The task and the client_event_id are
// both real, so the refusal being measured is the KIND gate and not an id that failed to parse; numstat
// is a JSON string, so it is the payload a well-formed client would send rather than a type probe.
func evidenceIntentPost(t *testing.T, app *App, token, clientEventID, taskID, baseSHA, headSHA string) (int, string) {
	t.Helper()
	item := map[string]any{
		"client_event_id": clientEventID,
		"task_id":         taskID,
		"kind":            "evidence_submitted",
		"payload": map[string]any{
			"base_sha": baseSHA,
			"head_sha": headSHA,
			"numstat":  "1\t0\ta.go\n",
			"test":     map[string]any{"command": "", "exit_code": 0, "failed": []string{}},
		},
	}
	body, err := json.Marshal([]map[string]any{item})
	if err != nil {
		t.Fatalf("building the batch: %v", err)
	}
	return ledgerPgPostIntents(t, app, token, string(body))
}

// evidenceIntentRefusal asserts the ONE answer of the batch is the kind refusal. The assertion is the
// reason, not the status code: the route answers 200 with per-item answers, so a 200 alone settles
// nothing. The acceptance shape is asserted absent too - an answer carrying seq numbers would say a row
// was written.
func evidenceIntentRefusal(t *testing.T, code int, body string) {
	t.Helper()
	if code != http.StatusOK {
		t.Fatalf("POST /api/v2/ledger/intents = %d, want 200 (a refusal is a per-item answer): %s", code, body)
	}
	answers := ledgerPgDecodeAnswers(t, body)
	if len(answers) != 1 {
		t.Fatalf("the batch of one item answered %d times: %s", len(answers), body)
	}
	a := answers[0]
	if a.Rejected == nil || !*a.Rejected {
		t.Fatalf("an evidence_submitted intent must be refused per item: %s", body)
	}
	if a.Reason == nil || *a.Reason != "unsupported_kind" {
		t.Fatalf("the refusal reason = %v, want unsupported_kind: %s", a.Reason, body)
	}
	if a.UserSeq != nil || a.Seq != nil || a.Accepted != nil {
		t.Fatalf("a refusal must carry no sequence numbers and no acceptance: %s", body)
	}
}

// evidenceTaskRowCount counts the task's own ledger rows, which is how "appends nothing" is proved
// against a task whose seq was already non-zero when the intent arrived.
func evidenceTaskRowCount(t *testing.T, sm *database.SessionManager, userID, taskID string) int {
	t.Helper()
	n := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM task_events WHERE "user_id" = $1::varchar AND "task_id" = $2::uuid`,
			userID, taskID).Scan(&n)
	}); err != nil {
		t.Fatalf("counting the task's ledger rows: %v", err)
	}
	return n
}

// TestEvidenceIntentIsRefusedAtAHeadANamedRowOwns is acceptance check 2: the head's latest evidence row
// names a command, the intent carries the same identity, and the answer is the kind refusal with the
// stored account and the task's seq untouched. Before the change the intent was accepted (200, a row
// appended), so this case is red on the code it replaces.
func TestEvidenceIntentIsRefusedAtAHeadANamedRowOwns(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, evidenceIntentNamedSubject)
	evidenceSeedBranch(t, sm, user)
	taskID := evidenceTaskCreate(t, app, token, "evidence intent refused at a named head")

	const baseSHA = "b0b0b0b0b1b1c1c1d1d1e1e1f1f1a1a1b1b1c1c1"
	const headSHA = "e0e0e0e0e1e1c1c1d1d1e1e1f1f1a1a1b1b1c1c1"
	if code, body := evidencePost(t, app, token, taskID, evidenceBody(baseSHA, headSHA, "1\t0\ta.go\n")); code != http.StatusCreated {
		t.Fatalf("the named row this case starts from = %d, want 201: %s", code, body)
	}
	seqBefore := ledgerPgTaskSeq(t, sm, user, taskID)
	rowsBefore := evidenceTaskRowCount(t, sm, user, taskID)
	namedBefore := evidenceLatestTestCommand(t, sm, taskID)

	code, body := evidenceIntentPost(t, app, token, "5c1e7a10-3333-4333-8333-0000000000a1", taskID, baseSHA, headSHA)
	t.Logf("OBSERVED the evidence intent at a named head -> %d %s", code, body)
	evidenceIntentRefusal(t, code, body)

	if got := ledgerPgTaskSeq(t, sm, user, taskID); got != seqBefore {
		t.Fatalf("the refusal moved the task's seq: %d -> %d", seqBefore, got)
	}
	if got := evidenceTaskRowCount(t, sm, user, taskID); got != rowsBefore {
		t.Fatalf("the refusal appended a row: %d -> %d", rowsBefore, got)
	}
	if got := evidenceLatestTestCommand(t, sm, taskID); got != namedBefore {
		t.Fatalf("the refusal changed the latest evidence account: %q -> %q", namedBefore, got)
	}
	// The account the 409 protects is still the named one: a second, different submission at this head
	// is still refused, which is the outcome the intent route must not be able to reach around.
	if code, body := evidencePost(t, app, token, taskID, evidenceBody(baseSHA, headSHA, "7\t3\tb.go\n")); code != http.StatusConflict {
		t.Fatalf("a different account at the named head = %d, want 409: %s", code, body)
	}
}

// TestEvidenceIntentIsRefusedAtAHeadWithNoRow is acceptance check 3: the refusal does not depend on what
// the head holds. The task has no evidence row at all and the kind gate still answers before anything is
// written - it is a vocabulary rule, not a comparison.
func TestEvidenceIntentIsRefusedAtAHeadWithNoRow(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, evidenceIntentEmptySubject)
	evidenceSeedBranch(t, sm, user)
	taskID := evidenceTaskCreate(t, app, token, "evidence intent refused at an empty head")

	if rows := evidenceSubmissionRows(t, sm, taskID); rows != 0 {
		t.Fatalf("the task must start with no evidence row, has %d", rows)
	}
	seqBefore := ledgerPgTaskSeq(t, sm, user, taskID)
	rowsBefore := evidenceTaskRowCount(t, sm, user, taskID)

	code, body := evidenceIntentPost(t, app, token, "5c1e7a10-3333-4333-8333-0000000000b1", taskID,
		"b0b0b0b0b1b1c1c1d1d1e1e1f1f1a1a1b1b1c1c1", "e0e0e0e0e1e1c1c1d1d1e1e1f1f1a1a1b1b1c1c1")
	t.Logf("OBSERVED the evidence intent at an empty head -> %d %s", code, body)
	evidenceIntentRefusal(t, code, body)

	if got := ledgerPgTaskSeq(t, sm, user, taskID); got != seqBefore {
		t.Fatalf("the refusal moved the task's seq: %d -> %d", seqBefore, got)
	}
	if got := evidenceTaskRowCount(t, sm, user, taskID); got != rowsBefore {
		t.Fatalf("the refusal appended a row: %d -> %d", rowsBefore, got)
	}
	if rows := evidenceSubmissionRows(t, sm, taskID); rows != 0 {
		t.Fatalf("the refusal stored %d evidence rows, want 0", rows)
	}
}

// TestDecisionStagedBeforeAControllerEvidenceRowIsAccepted is acceptance check 4's ordering half: the
// kind keeps its FACT classification after it leaves the pushable list, so a decision staged on a seq
// that the controller's own evidence row has since passed is ACCEPTED, not refused stale_base_seq.
//
// The distinction is the whole reason the constant and its FactKinds entry stay: HasNonFactAfter asks
// FactKindStrings whether anything after base_seq is not a fact, and a controller-written
// evidence_submitted row is a fact by ordering. Drop the kind from that list and every decision staged
// before an evidence write answers stale_base_seq - a client that staged on a base the ledger then
// moved forward through its OWN write would be told its base was behind a non-fact it never saw.
// Proven by mutation, not by reading: with the kind removed from FactKinds this case answers
// stale_base_seq.
func TestDecisionStagedBeforeAControllerEvidenceRowIsAccepted(t *testing.T) {
	app, sm := evidenceApp(t)
	token, user := evidenceUser(t, evidenceIntentDecisionSubject)
	evidenceSeedBranch(t, sm, user)
	taskID := evidenceTaskCreate(t, app, token, "a decision staged before a controller evidence row")

	const baseSHA = "b0b0b0b0b1b1c1c1d1d1e1e1f1f1a1a1b1b1c1c1"
	const headSHA = "e0e0e0e0e1e1c1c1d1d1e1e1f1f1a1a1b1b1c1c1"

	// The base the decision stages on: the task's seq as it stands BEFORE the controller writes.
	base := ledgerPgTaskSeq(t, sm, user, taskID)
	if code, body := evidencePost(t, app, token, taskID, evidenceBody(baseSHA, headSHA, "1\t0\ta.go\n")); code != http.StatusCreated {
		t.Fatalf("the controller's own evidence row = %d, want 201: %s", code, body)
	}
	afterEvidence := ledgerPgTaskSeq(t, sm, user, taskID)
	if afterEvidence <= base {
		t.Fatalf("the evidence row must move the task's seq past the staged base: %d -> %d", base, afterEvidence)
	}

	// The only row after base is the controller's evidence row, so the decision is not stale.
	code, body := ledgerPgPostOne(t, app, token, "5c1e7a10-3333-4333-8333-0000000000c1", taskID, "status_changed", new(base))
	t.Logf("OBSERVED a decision staged on seq %d after the controller's row -> %d %s", base, code, body)
	if code != http.StatusOK {
		t.Fatalf("POST /api/v2/ledger/intents = %d, want 200: %s", code, body)
	}
	answers := ledgerPgDecodeAnswers(t, body)
	if len(answers) != 1 {
		t.Fatalf("the batch of one item answered %d times: %s", len(answers), body)
	}
	a := answers[0]
	if a.Rejected != nil && *a.Rejected {
		reason := "<absent>"
		if a.Reason != nil {
			reason = *a.Reason
		}
		t.Fatalf("a decision staged before a controller evidence row must be accepted, got reason %q: %s", reason, body)
	}
	if a.Accepted == nil || !*a.Accepted || a.Seq == nil {
		t.Fatalf("an accepted decision must carry accepted:true and its seq: %s", body)
	}
	if got := ledgerPgTaskSeq(t, sm, user, taskID); got != afterEvidence+1 {
		t.Fatalf("the accepted decision's seq = %d, want %d (one row after the evidence row)", got, afterEvidence+1)
	}
	if latest := evidenceLatestTestCommand(t, sm, taskID); latest == "" {
		t.Fatalf("the evidence account must survive the decision: the latest row no longer names a command")
	}
}
