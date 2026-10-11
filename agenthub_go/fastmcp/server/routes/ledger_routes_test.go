package routes

// The ledger's two routes, at the layer that decides what the wire carries. These cases need NO
// database: what they pin is the ENCODING - which keys a page and an answer hold, in which order,
// and that the two answer shapes never carry each other's keys - and that is decided in this file
// rather than in the repository behind it. The route-level acceptance cases (which rows a page
// holds, who they belong to, when a decision is refused) are in httpapp/ledger_pg_test.go, where a
// real database is available.

import (
	"context"
	"strings"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	ledgerentities "agenthub/fastmcp/ledger/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"

	"agenthub/fastmcp/auth"
)

// fakeLedgerReader answers the cross-task read with whatever the test decided, and records what it
// was asked for. It embeds the interface so the methods this test never reaches need not be written.
type fakeLedgerReader struct {
	LedgerReader
	events []*taskdomain.TaskEvent
	tip    int64
	err    error

	gotUser  string
	gotAfter int64
	gotLimit int
}

func (f *fakeLedgerReader) ListUserEvents(ctx context.Context, userID string, after int64, limit int) ([]*taskdomain.TaskEvent, int64, error) {
	f.gotUser, f.gotAfter, f.gotLimit = userID, after, limit
	if f.err != nil {
		return nil, 0, f.err
	}
	return f.events, f.tip, nil
}

// fakeLedgerWriter answers the intents route with whatever the test decided.
type fakeLedgerWriter struct {
	LedgerIntentWriter
	answers []ledgerentities.Answer
	err     error

	gotUser    string
	gotIntents []ledgerentities.Intent
}

func (f *fakeLedgerWriter) SubmitIntents(ctx context.Context, userID string, intents []ledgerentities.Intent) ([]ledgerentities.Answer, error) {
	f.gotUser, f.gotIntents = userID, intents
	if f.err != nil {
		return nil, f.err
	}
	return f.answers, nil
}

// ledgerTestUser is the authenticated caller these cases run as.
func ledgerTestUser() *authdomain.User {
	user := &authdomain.User{}
	user.ID = new("user-1")
	return user
}

// ledgerTestEvents are two entries of DIFFERENT tasks, with the subtask the nullable column allows
// and a fixed instant so the encoding is a constant.
func ledgerTestEvents() []*taskdomain.TaskEvent {
	created := time.Date(2026, 10, 11, 3, 4, 5, 0, time.UTC)
	return []*taskdomain.TaskEvent{
		{
			ID: "e1", TaskID: "t1", SubtaskID: "s1", UserID: "user-1", Seq: 1, UserSeq: 2,
			Kind: taskdomain.TaskEventKindProgress, ActorKind: taskdomain.TaskEventActorSeat,
			ActorID: "room/seat", Payload: map[string]any{"note": "first"}, CreatedAt: created,
		},
		{
			ID: "e2", TaskID: "t2", UserID: "user-1", Seq: 3, UserSeq: 4,
			Kind: taskdomain.TaskEventKindHandover, ActorKind: taskdomain.TaskEventActorHuman,
			ActorID: "user-1", Payload: map[string]any{"note": "second"}, CreatedAt: created,
		},
	}
}

// TestGetLedgerEncodesTheCursorTheTipAndEveryFieldOfAnEntry pins the page byte for byte: the
// encoding is the contract a client's cursor is taken from, so a renamed or reordered key is a
// client that cannot resume rather than a cosmetic difference. The tip (9) is deliberately NOT the
// page's last user_seq (4): the tip is the user's current tip, and a page read while the ledger is
// moving still has to say where the end is.
func TestGetLedgerEncodesTheCursorTheTipAndEveryFieldOfAnEntry(t *testing.T) {
	reader := &fakeLedgerReader{events: ledgerTestEvents(), tip: 9}

	body, err := GetLedger(context.Background(), 1, 50, ledgerTestUser(), reader)
	if err != nil {
		t.Fatalf("GetLedger returned an error: %v", err)
	}
	if reader.gotUser != "user-1" || reader.gotAfter != 1 || reader.gotLimit != 50 {
		t.Fatalf("the reader must be asked for this user's cursor: user = %q, after = %d, limit = %d",
			reader.gotUser, reader.gotAfter, reader.gotLimit)
	}

	got, err := value_objects.PyJSONDumpsCompact(body)
	if err != nil {
		t.Fatalf("encoding the page: %v", err)
	}
	want := `{"success":true,"events":[` +
		`{"id":"e1","task_id":"t1","subtask_id":"s1","seq":1,"user_seq":2,"kind":"progress","actor_kind":"seat","actor_id":"room/seat","payload":{"note":"first"},"created_at":"2026-10-11T03:04:05Z"},` +
		`{"id":"e2","task_id":"t2","subtask_id":null,"seq":3,"user_seq":4,"kind":"handover","actor_kind":"human","actor_id":"user-1","payload":{"note":"second"},"created_at":"2026-10-11T03:04:05Z"}` +
		`],"count":2,"after":1,"tip":9}`
	if got != want {
		t.Fatalf("the page's encoding drifted from the contract:\ngot  = %s\nwant = %s", got, want)
	}
}

// TestGetLedgerAnswersAnEmptyLedgerWithATipOfZero is the fresh-user shape: no events and tip 0.
// A reader that answered a missing tip with a null - or with the LAST user_seq it happened to have
// seen anywhere - would leave a client unable to tell "nothing here" from "nothing new".
func TestGetLedgerAnswersAnEmptyLedgerWithATipOfZero(t *testing.T) {
	body, err := GetLedger(context.Background(), 0, 0, ledgerTestUser(), &fakeLedgerReader{})
	if err != nil {
		t.Fatalf("GetLedger returned an error: %v", err)
	}
	got, err := value_objects.PyJSONDumpsCompact(body)
	if err != nil {
		t.Fatalf("encoding the page: %v", err)
	}
	if want := `{"success":true,"events":[],"count":0,"after":0,"tip":0}`; got != want {
		t.Fatalf("an empty ledger must answer with an empty page and tip 0:\ngot  = %s\nwant = %s", got, want)
	}
}

// TestGetLedgerRefusesWhenTheReadFails is the failure path: a reader fault is a 500 and never an
// empty page, because an empty page is a claim that the user has no more work.
func TestGetLedgerRefusesWhenTheReadFails(t *testing.T) {
	reader := &fakeLedgerReader{err: context.DeadlineExceeded}
	body, err := GetLedger(context.Background(), 0, 0, ledgerTestUser(), reader)
	if err == nil {
		t.Fatal("a failing read must return an error rather than a body")
	}
	exc, ok := err.(*auth.HTTPException)
	if !ok || exc.StatusCode != 500 {
		t.Fatalf("expected a 500 HTTPException, got %#v", err)
	}
	if body != nil {
		t.Fatalf("no body on refusal, got %#v", body)
	}
}

// TestSubmitLedgerIntentsEncodesTheTwoAnswerShapesDisjointly pins the batch's encoding: one answer
// per item, in the request's order, each item carrying the keys of ONE shape and none of the other's.
// The two shapes are told apart by which key they hold, so a page that held "accepted":false beside
// an acceptance's sequence numbers would be a third shape nothing parses.
func TestSubmitLedgerIntentsEncodesTheTwoAnswerShapesDisjointly(t *testing.T) {
	writer := &fakeLedgerWriter{answers: []ledgerentities.Answer{
		ledgerentities.Acceptance(7, 3),
		ledgerentities.Refusal(ledgerentities.ReasonStaleBaseSeq, 9),
	}}
	intents := []ledgerentities.Intent{
		{ClientEventID: "c1", TaskID: "t1", Kind: ledgerentities.IntentKindProgress},
		{ClientEventID: "c2", TaskID: "t1", Kind: ledgerentities.IntentKindClaimed, BaseSeq: new(1)},
	}

	body, err := SubmitLedgerIntents(context.Background(), intents, ledgerTestUser(), writer)
	if err != nil {
		t.Fatalf("SubmitLedgerIntents returned an error: %v", err)
	}
	if writer.gotUser != "user-1" {
		t.Fatalf("the writer must be asked for this user, got %q", writer.gotUser)
	}
	if len(writer.gotIntents) != 2 || writer.gotIntents[0].ClientEventID != "c1" || writer.gotIntents[1].ClientEventID != "c2" {
		t.Fatalf("the items must reach the writer in the request's order: %+v", writer.gotIntents)
	}
	if len(body) != 2 {
		t.Fatalf("the route must answer PER ITEM: got %d answers for 2 items", len(body))
	}

	first, err := value_objects.PyJSONDumpsCompact(body[0])
	if err != nil {
		t.Fatalf("encoding the acceptance: %v", err)
	}
	second, err := value_objects.PyJSONDumpsCompact(body[1])
	if err != nil {
		t.Fatalf("encoding the refusal: %v", err)
	}
	if want := `{"accepted":true,"user_seq":7,"seq":3}`; first != want {
		t.Fatalf("the acceptance's encoding drifted:\ngot  = %s\nwant = %s", first, want)
	}
	if want := `{"rejected":true,"reason":"stale_base_seq","task_seq":9}`; second != want {
		t.Fatalf("the refusal's encoding drifted:\ngot  = %s\nwant = %s", second, want)
	}
	for _, key := range []string{`"rejected"`, `"reason"`, `"task_seq"`} {
		if strings.Contains(first, key) {
			t.Fatalf("an acceptance must carry none of the refusal's keys, found %s in %s", key, first)
		}
	}
	for _, key := range []string{`"accepted"`, `"user_seq"`, `"seq"`} {
		if strings.Contains(second, key) {
			t.Fatalf("a refusal must carry none of the acceptance's keys, found %s in %s", key, second)
		}
	}
}

// TestSubmitLedgerIntentsAnswersAnEmptyBatchWithAnEmptyList is the trivial batch: an outbox with
// nothing to drain gets an empty list rather than a null, so a client's loop does not have to treat
// "nothing queued" as a special case.
func TestSubmitLedgerIntentsAnswersAnEmptyBatchWithAnEmptyList(t *testing.T) {
	body, err := SubmitLedgerIntents(context.Background(), nil, ledgerTestUser(), &fakeLedgerWriter{})
	if err != nil {
		t.Fatalf("SubmitLedgerIntents returned an error: %v", err)
	}
	if len(body) != 0 {
		t.Fatalf("an empty batch must answer an empty list, got %d answers", len(body))
	}
}

// TestSubmitLedgerIntentsRefusesWhenTheWriteFails is the failure path, and it must NOT answer
// per-item: a batch that could not be decided has no per-item answer, and a 200 with empty answers
// would tell the client its work had been considered.
func TestSubmitLedgerIntentsRefusesWhenTheWriteFails(t *testing.T) {
	writer := &fakeLedgerWriter{err: context.DeadlineExceeded}
	body, err := SubmitLedgerIntents(context.Background(), []ledgerentities.Intent{
		{ClientEventID: "c1", TaskID: "t1", Kind: ledgerentities.IntentKindProgress},
	}, ledgerTestUser(), writer)
	if err == nil {
		t.Fatal("a failing write must return an error rather than a body")
	}
	exc, ok := err.(*auth.HTTPException)
	if !ok || exc.StatusCode != 500 {
		t.Fatalf("expected a 500 HTTPException, got %#v", err)
	}
	if body != nil {
		t.Fatalf("no body on refusal, got %#v", body)
	}
}
