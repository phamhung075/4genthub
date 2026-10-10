package routes

import (
	"context"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"

	"agenthub/fastmcp/auth"
)

// fakeEvidenceWriter records what the handler asked it to do and answers with whatever the test
// decided. It embeds the interface so the methods this test never reaches need not be written out.
type fakeEvidenceWriter struct {
	TaskEvidenceWriter
	called  bool
	taskID  string
	headSHA string
	payload map[string]any
	event   *taskdomain.TaskEvent
	err     error
}

func (f *fakeEvidenceWriter) RecordEvidence(ctx context.Context, taskID, headSHA string, payload map[string]any) (*taskdomain.TaskEvent, error) {
	f.called = true
	f.taskID = taskID
	f.headSHA = headSHA
	f.payload = payload
	if f.err != nil {
		return nil, f.err
	}
	if f.event != nil {
		return f.event, nil
	}
	return &taskdomain.TaskEvent{
		ID: "event-1", TaskID: taskID, Seq: 1,
		Kind:      taskdomain.TaskEventKindEvidenceSubmitted,
		ActorKind: taskdomain.TaskEventActorHuman, ActorID: "user-1", Payload: payload,
	}, nil
}

func evidenceRequest() TaskEvidence {
	return TaskEvidence{
		BaseSHA:     "aaa111",
		HeadSHA:     "bbb222",
		Numstat:     "3\t1\tfastmcp/server/routes/task_evidence_routes.go\n",
		TestCommand: "go test ./fastmcp/server/routes/",
		TestFailed:  []string{"TestX"},
	}
}

// TestSubmitTaskEvidenceRefusesAnInvisibleTaskWithoutRecording is the 404 negative, and it needs no
// database: the refusal comes from the same !Success branch GetTaskEvents uses, and the writer must
// never run - a bug that wrote first and filtered later could not pass this.
func TestSubmitTaskEvidenceRefusesAnInvisibleTaskWithoutRecording(t *testing.T) {
	notFound := "Task not found"
	tasks := &fakeTaskController{result: UserTaskResult{Success: false, Error: &notFound}}
	writer := &fakeEvidenceWriter{}

	body, err := SubmitTaskEvidence(context.Background(), "task-1", evidenceRequest(), &authdomain.User{}, tasks, writer)

	if err == nil {
		t.Fatal("a task the caller cannot see must return an error rather than a body")
	}
	exc, ok := err.(*auth.HTTPException)
	if !ok || exc.StatusCode != 404 {
		t.Fatalf("expected a 404 HTTPException, got %#v", err)
	}
	if body != nil {
		t.Fatalf("no body on refusal, got %#v", body)
	}
	if tasks.calls != 1 {
		t.Fatalf("the task lookup must run exactly once, ran %d", tasks.calls)
	}
	if writer.called {
		t.Fatal("THE EVIDENCE WAS WRITTEN FOR A TASK THE CALLER CANNOT SEE - the 404 must come from the task check, before the writer")
	}
}

// TestSubmitTaskEvidenceRefusesABlankSHA is the 422 for a missing/blank sha, and it must come BEFORE
// the task lookup: an unusable body is refused on its own terms, and nothing is read or written.
func TestSubmitTaskEvidenceRefusesABlankSHA(t *testing.T) {
	cases := map[string]func(TaskEvidence) TaskEvidence{
		"base_sha absent": func(e TaskEvidence) TaskEvidence { e.BaseSHA = ""; return e },
		"base_sha blank":  func(e TaskEvidence) TaskEvidence { e.BaseSHA = "   "; return e },
		"head_sha absent": func(e TaskEvidence) TaskEvidence { e.HeadSHA = ""; return e },
		"head_sha blank":  func(e TaskEvidence) TaskEvidence { e.HeadSHA = "\t\n"; return e },
	}
	for name, breakIt := range cases {
		t.Run(name, func(t *testing.T) {
			tasks := &fakeTaskController{result: UserTaskResult{Success: true}}
			writer := &fakeEvidenceWriter{}

			body, err := SubmitTaskEvidence(context.Background(), "task-1", breakIt(evidenceRequest()), &authdomain.User{}, tasks, writer)

			exc, ok := err.(*auth.HTTPException)
			if !ok || exc.StatusCode != 422 {
				t.Fatalf("expected a 422 HTTPException, got %#v", err)
			}
			if body != nil {
				t.Fatalf("no body on a refused submission, got %#v", body)
			}
			if tasks.calls != 0 || writer.called {
				t.Fatalf("a blank sha must be refused on the body alone: task lookups = %d, writer called = %v", tasks.calls, writer.called)
			}
		})
	}
}

// TestSubmitTaskEvidenceRefusesOnlyNumstatOverTheCap pins the boundary rather than a convenient
// number: the cap itself is accepted, one byte past it is refused, and the refusal NAMES the cap so a
// client can act on it. Nothing is truncated silently.
func TestSubmitTaskEvidenceRefusesOnlyNumstatOverTheCap(t *testing.T) {
	atCap := evidenceRequest()
	atCap.Numstat = strings.Repeat("x", EvidenceNumstatMaxBytes)
	tasks := &fakeTaskController{result: UserTaskResult{Success: true}}
	writer := &fakeEvidenceWriter{}
	if _, err := SubmitTaskEvidence(context.Background(), "task-1", atCap, &authdomain.User{}, tasks, writer); err != nil {
		t.Fatalf("a numstat of exactly the cap must be accepted, got %v", err)
	}
	if !writer.called {
		t.Fatal("the writer must be reached for an at-cap numstat")
	}

	overCap := evidenceRequest()
	overCap.Numstat = strings.Repeat("x", EvidenceNumstatMaxBytes+1)
	tasks = &fakeTaskController{result: UserTaskResult{Success: true}}
	writer = &fakeEvidenceWriter{}
	body, err := SubmitTaskEvidence(context.Background(), "task-1", overCap, &authdomain.User{}, tasks, writer)
	exc, ok := err.(*auth.HTTPException)
	if !ok || exc.StatusCode != 422 {
		t.Fatalf("expected a 422 HTTPException, got %#v", err)
	}
	if !strings.Contains(exc.Detail, "1048576") {
		t.Fatalf("the refusal must name the cap, got %q", exc.Detail)
	}
	if body != nil || writer.called {
		t.Fatalf("an over-cap numstat must be refused before anything is read or written")
	}
}

// TestSubmitTaskEvidenceMapsTheDuplicateToA409 is the handler's half of the duplicate rule: the
// writer's decision, taken inside its transaction, reaches the client as 409.
func TestSubmitTaskEvidenceMapsTheDuplicateToA409(t *testing.T) {
	tasks := &fakeTaskController{result: UserTaskResult{Success: true}}
	writer := &fakeEvidenceWriter{err: ErrEvidenceDuplicate}

	body, err := SubmitTaskEvidence(context.Background(), "task-1", evidenceRequest(), &authdomain.User{}, tasks, writer)

	exc, ok := err.(*auth.HTTPException)
	if !ok || exc.StatusCode != 409 {
		t.Fatalf("expected a 409 HTTPException, got %#v", err)
	}
	if body != nil {
		t.Fatalf("no body on a duplicate, got %#v", body)
	}
	if !writer.called {
		t.Fatal("the duplicate decision is the writer's, inside its transaction - the handler must reach it")
	}
}

// TestSubmitTaskEvidenceReturnsTheCreatedEventAndStoresTheRequestFields covers the positive
// direction in one place: the payload the writer is handed is the request's own fields (nested test
// block included, no bodies), and the answer is the created event in the eight keys the ledger read
// returns.
func TestSubmitTaskEvidenceReturnsTheCreatedEventAndStoresTheRequestFields(t *testing.T) {
	tasks := &fakeTaskController{result: UserTaskResult{Success: true}}
	writer := &fakeEvidenceWriter{}

	body, err := SubmitTaskEvidence(context.Background(), "task-1", evidenceRequest(), &authdomain.User{}, tasks, writer)
	if err != nil {
		t.Fatal(err)
	}

	if writer.taskID != "task-1" || writer.headSHA != "bbb222" {
		t.Fatalf("the writer got task %q head %q", writer.taskID, writer.headSHA)
	}
	wantKeys := []string{"id", "task_id", "seq", "kind", "actor_kind", "actor_id", "payload", "created_at"}
	if got := body.Keys(); strings.Join(got, ",") != strings.Join(wantKeys, ",") {
		t.Fatalf("the answer must be the event in the read's key order: got %v want %v", got, wantKeys)
	}
	if kind, _ := body.Get("kind"); kind != "evidence_submitted" {
		t.Fatalf("kind = %v, want evidence_submitted", kind)
	}

	payload, _ := body.Get("payload")
	stored, ok := payload.(map[string]any)
	if !ok {
		t.Fatalf("payload is %T, want the stored map", payload)
	}
	for _, key := range []string{"base_sha", "head_sha", "numstat"} {
		if stored[key] != writer.payload[key] {
			t.Fatalf("payload[%s] = %v, want the request's %v", key, stored[key], writer.payload[key])
		}
	}
	if stored["base_sha"] != "aaa111" || stored["head_sha"] != "bbb222" {
		t.Fatalf("the shas did not reach the payload: %v", stored)
	}
	if stored["numstat"] != "3\t1\tfastmcp/server/routes/task_evidence_routes.go\n" {
		t.Fatalf("numstat must travel verbatim, got %q", stored["numstat"])
	}
	test, ok := stored["test"].(map[string]any)
	if !ok {
		t.Fatalf("the test block must be stored nested, got %T", stored["test"])
	}
	if test["command"] != "go test ./fastmcp/server/routes/" || test["exit_code"] != 0 {
		t.Fatalf("test block = %v", test)
	}
	if failed, _ := test["failed"].([]string); len(failed) != 1 || failed[0] != "TestX" {
		t.Fatalf("test.failed = %v, want [TestX]", test["failed"])
	}
}

// TestSubmitTaskEvidenceEmitsAnEmptyFailedListWhenTheClientSentNone: the wire contract lets
// `test.failed` be absent, and the stored payload answers with an empty array rather than null, so a
// reader has one case and not two.
func TestSubmitTaskEvidenceEmitsAnEmptyFailedListWhenTheClientSentNone(t *testing.T) {
	evidence := evidenceRequest()
	evidence.TestCommand = ""
	evidence.TestFailed = nil

	tasks := &fakeTaskController{result: UserTaskResult{Success: true}}
	writer := &fakeEvidenceWriter{}
	if _, err := SubmitTaskEvidence(context.Background(), "task-1", evidence, &authdomain.User{}, tasks, writer); err != nil {
		t.Fatal(err)
	}
	test, ok := writer.payload["test"].(map[string]any)
	if !ok {
		t.Fatalf("the test block must still be stored, got %T", writer.payload["test"])
	}
	failed, ok := test["failed"].([]string)
	if !ok || failed == nil || len(failed) != 0 {
		t.Fatalf("test.failed = %#v, want an empty non-nil list", test["failed"])
	}
	if test["command"] != "" {
		t.Fatalf("an empty command must stay empty, got %v", test["command"])
	}
}
